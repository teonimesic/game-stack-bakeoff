#!/usr/bin/env python3
"""Build a stack-blind judging pack from a submission.

Three things happen here, all of them to stop the judge bringing priors:

1. Files byte-identical to the starter are dropped. The judge grades the agent's work,
   not the harness the agent was given - otherwise every stack scores its own template.
2. Real paths are replaced with neutral ones (`sim/03.rs`, `view/01.ts`). `crates/sim/`
   versus `Assets/Sim/` versus `src/sim/` is a dead giveaway; `sim/` is not.
3. Presentation order is shuffled with a per-submission seed, so no stack is
   systematically read first.

BLINDING IS PARTIAL AND KNOWN TO BE SO. The file extension and the language syntax are
inherently visible - you cannot show a model Rust and have it not know it is Rust. What
is removed is the *labelling* and the *ordering*: the judge is never told which stack it
is looking at, never sees a stack name in the brief, and never sees two stacks together.
Anything stronger would mean paraphrasing the code, which would change the thing being
judged.
"""

from __future__ import annotations

import hashlib
import random
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# `.claude` was already here; `.codex` was not, and its hook scripts embed the ABSOLUTE
# work-tree path -- which contains the trial id, e.g. `g4_platformer__godot__t1`. That is
# not a hint about the stack, it is the answer key, and it reached 31 stored packs. #32 was
# exactly this defect in a different file. Agent-tooling directories are configuration, are
# never the authored game, and are skipped as a class rather than one name at a time.
SKIP_DIRS = {".git", "target", "node_modules", "dist", "Library", "Temp", "obj",
             ".godot", ".venv", "coverage", "artifacts", "build", "__pycache__",
             ".claude", ".github", ".codex", ".cursor", ".aider", ".vscode", ".idea"}
CODE_EXT = {".rs", ".ts", ".tsx", ".js", ".mjs", ".cs", ".gd", ".py", ".shader",
            ".wgsl", ".toml", ".json"}
# Config files carry the stack's name in every line; they add nothing to a judgement
# about code quality and would unblind instantly.
DROP_NAMES = {"Cargo.toml", "Cargo.lock", "package.json", "pnpm-lock.yaml",
              "project.godot", "tsconfig.json", "tsconfig.base.json",
              "tsconfig.sim.json", "eslint.config.js", "vitest.config.ts",
              "justfile", "AGENTS.md", "CLAUDE.md", "manifest.json",
              "packages-lock.json", ".prettierrc.json", "gdlintrc"}

# Only tokens that name the stack. Nothing that would change the meaning of the code.
_STACK_TOKENS = [
    # ORGANISATION AND REPOSITORY NAMES FIRST, because they CONTAIN the engine name and
    # the plain token rules below would only rewrite the tail. An agent cited GitHub issue
    # `bevyengine/bevy#6183` in a comment; the second token was replaced and the first was
    # not, leaving `bevyengine/engine#6183` in a supposedly language-blind pack. That is
    # worse than leaving it alone: a half-substituted string still names the engine AND
    # advertises that a substitution happened, which is a hint to decode the rest.
    #
    # Ordering is load-bearing. `neutralise()` applies these in sequence, so any pattern
    # whose match contains another pattern's match must come first.
    (r"\bbevyengine\b", "engineorg"), (r"\bgodotengine\b", "engineorg"),
    (r"\bUnityTechnologies\b", "EngineOrg"), (r"\bmrdoob\b", "engineorg"),
    (r"\bbevy(_\w+)?\b", "engine"), (r"\bBevy\b", "Engine"),
    (r"\bwgpu\b", "gpu"), (r"\bwinit\b", "windowing"),
    (r"\bthree\b", "engine"), (r"\bTHREE\b", "ENGINE"),
    (r"\bUnityEngine\b", "EngineCore"), (r"\bUnityEditor\b", "EngineEditor"),
    (r"\bMonoBehaviour\b", "EngineBehaviour"), (r"\bUnity\b", "Engine"),
    (r"\bGodot\b", "Engine"), (r"\bgodot(_\w+)?\b", "engine"),
    (r"\bGDScript\b", "Script"),
    (r"\bNode2D\b", "SceneNode2D"), (r"\bNode3D\b", "SceneNode3D"),
    # Compound identifiers that EMBED an engine name. These must come after the specific
    # rules above (UnityEngine, UnityEditor, MonoBehaviour), because the first matching
    # rule wins and a catch-all placed earlier would swallow them and lose the distinction.
    # `UnityCsReference` is the case that motivated this: `\bUnity\b` does not match
    # inside it, so it survived a language-blind pack intact.
    (r"\bUnity\w+\b", "EngineThing"), (r"\bunity[-_]\w+\b", "enginething"),
    (r"\bNUnit\b", "TestFramework"), (r"\bvitest\b", "testrunner"),
    (r"\bnextest\b", "testrunner"), (r"\bplaywright\b", "browserdriver"),
]
_STACK_RE = [(re.compile(p), r) for p, r in _STACK_TOKENS]


@dataclass
class PackFile:
    label: str      # neutral path shown to the judge
    origin: str     # the real path, kept for the audit trail (never shown)
    text: str


def _walk(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        out[str(rel)] = p
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _bucket(rel: str) -> str:
    low = rel.lower()
    if "test" in low or "spec" in low:
        return "tests"
    if "/sim" in "/" + low or low.startswith("sim") or "sim/" in low:
        return "sim"
    if any(k in low for k in ("view", "render", "game/src", "assets/view", "src/view")):
        return "view"
    return "other"


#: A trial id names the game, the STACK and the attempt: `g4_platformer__godot__t1`.
#: Anywhere one of these reaches a pack the blinding is not degraded, it is void.
_TRIAL_ID_RE = re.compile(r"\bg\d+_[a-z0-9]+__(?:rust|ts|unity|godot)__t\d+\b")
#: The work root leaks the same identity through absolute paths baked into scripts.
_WORK_PATH_RE = re.compile(r"/[^\s\"']*game-research-work[^\s\"']*")


def neutralise(text: str) -> str:
    """Rewrite stack tokens AND anything that names the trial outright.

    Skipping `.codex` (above) removes the file that motivated this, but a path can be
    baked into any file an agent writes, so the identity pattern is scrubbed everywhere
    as well. Two independent defences, because one of them is a list of directory names
    and this project has learned what a list-shaped guard misses.
    """
    text = _TRIAL_ID_RE.sub("SUBMISSION", text)
    text = _WORK_PATH_RE.sub("/WORKTREE", text)
    for rx, rep in _STACK_RE:
        text = rx.sub(rep, text)
    return text


def build_pack(submission: Path, starter: Path, dest: Path, frames_dir: Path | None,
               submission_id: str,
               exclude_origins: frozenset[str] = frozenset()) -> dict[str, object]:
    """Materialise the judge's working directory. Returns a manifest for the audit log.

    THERE IS NO CHARACTER BUDGET, and its removal is the point (#62, #69).

    There used to be a 160,000-character cap: files were written in bucket-then-shuffle
    order until it ran out and the rest were dropped. It was a pre-filter standing in
    front of an agent that already chooses what to read - the judge runs `claude -p` with
    `--max-turns 120` and `cwd` set to this pack, and is asked to read the code in A/
    through H/. It was always going to browse selectively. The cap did not protect it from
    volume; it removed files it might have chosen, by alphabetical accident, before it
    could choose.

    Measured on `g4_platformer__unity__t0`, rebuilding the same submission both ways:

        cap = 160,000    files=15   chars=160,038   dropped=17
        uncapped         files=32   chars=388,968   dropped= 0

    **More than half that submission's code was invisible to every code judgement this
    project has made.**

    Every other filter stays, because they are blinding and noise control rather than
    size: files identical to the starter, `DROP_NAMES`, non-`CODE_EXT` suffixes, empty
    files, and `neutralise()`'s stack-token rewriting.

    `files_dropped_for_length` is still reported, and is now always 0 by construction.
    That is deliberate - the completeness gate asserts it, so a budget reintroduced later
    cannot truncate silently. See `eval/IMPROVEMENTS.md`.

    THE DESTINATION IS CLEARED, NOT ADDED TO. It used to be `mkdir(exist_ok=True)`, and
    a pack is not a set of files - it is a NUMBERING: labels are `bucket/NN.ext` counted
    within the bucket, so the moment the picked set changes between two passes the
    numbering shifts and the previous pass's files stay behind under labels the new
    manifest does not list. `wg-g4c` was evaluated nine times across the #69 cap removal
    and the #83 leak repair and ended with 23 files in 222 that no manifest accounts for,
    stack-correlated, twelve of them a second copy of a live file under a second name and
    eleven carrying content nothing lists - including the `.codex` hook scripts #83
    removed. Every one of those nine passes returned normally: this class is invisible to
    an exit code and to every count the function reports about its own input, which is why
    `field.pack_matches_manifest` reads the directory instead.
    """
    # A pack destination is disposable by definition; the thing being packed is not.
    # Clearing a directory that CONTAINS the submission would delete the evidence, and
    # this is the one place where getting the address wrong is unrecoverable (rule 12).
    _dest = dest.resolve()
    for name, src in (("submission", submission), ("starter", starter)):
        if src.exists() and (_dest == src.resolve() or _dest in src.resolve().parents):
            raise ValueError(
                f"refusing to build a pack into {dest}: it contains the {name} "
                f"{src}, and building a pack clears its destination")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "code").mkdir()

    sub_files = _walk(submission)
    starter_files = _walk(starter) if starter.exists() else {}
    starter_hashes = {k: _sha(v) for k, v in starter_files.items()}

    picked: list[PackFile] = []
    counters: dict[str, int] = {}
    skipped_identical = 0
    for rel in sorted(sub_files):
        p = sub_files[rel]
        name = Path(rel).name
        # AppleDouble resource forks. macOS `tar` extraction of an archive carrying
        # extended attributes materialises a `._<name>` sidecar for every file, and they
        # inherit the real file's suffix - so `._Probe.cs` passes the CODE_EXT test and
        # lands in the pack as a code file full of binary. Rebuilding one submission from
        # its tarball produced 47 of them, inflating a 32-file pack to 78.
        #
        # No stored pack is affected: packs are built from the work tree, which has none.
        # It is filtered because "no caller does that today" is not a property of the
        # function, and the budget removal makes every such file reach the judge.
        if name.startswith("._"):
            continue
        if name in DROP_NAMES or p.suffix.lower() not in CODE_EXT:
            continue
        if rel in starter_hashes and starter_hashes[rel] == _sha(p):
            skipped_identical += 1
            continue
        # STARTER DRIFT. The starter-identical filter compares against the starter AS IT
        # IS NOW, but a pack rebuilt from an old run must be filtered against the starter
        # AS IT WAS. `starters/` changed on 2026-08-17 (launch guards), so three
        # `g3_arena` submissions gained a template file each - `tests/frame.gd` and two
        # `src/view/capture.ts` - which the ORIGINAL build recorded as starter-identical.
        # Being dropped then is proof the agent never touched them; they differ now only
        # because the starter moved underneath.
        #
        # Passed in explicitly rather than guessed, and the caller must show its working:
        # the correct exclusion set is (files in the rebuilt pack) MINUS (files in the
        # stored manifest) MINUS (files the original dropped for length), because that
        # third group is legitimately returning and must NOT be excluded.
        if rel in exclude_origins:
            skipped_identical += 1
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        b = _bucket(rel)
        counters[b] = counters.get(b, 0) + 1
        label = f"{b}/{counters[b]:02d}{p.suffix.lower()}"
        picked.append(PackFile(label, rel, neutralise(text)))

    # Order: sim first (that is where the game actually lives), then view, then tests,
    # then everything else. Shuffle within each bucket with a per-submission seed so no
    # stack is systematically read in the same order.
    rng = random.Random(hashlib.sha256(submission_id.encode()).hexdigest())
    order = {"sim": 0, "view": 1, "tests": 2, "other": 3}
    for b in order:
        group = [f for f in picked if f.label.startswith(b + "/")]
        rng.shuffle(group)
        for i, f in enumerate(group):
            f.label = f"{b}/{i + 1:02d}{Path(f.label).suffix}"
    picked.sort(key=lambda f: (order.get(f.label.split("/")[0], 9), f.label))

    written: list[dict[str, str]] = []
    used = 0
    # Always 0: nothing is dropped for length any more. Kept in the manifest so the
    # completeness gate can ASSERT it is 0 rather than being deleted as vacuous, which
    # would leave a reintroduced cap undetectable (#69).
    truncated = 0
    for f in picked:
        body = f.text
        out = dest / "code" / f.label
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        used += len(body)
        written.append({"label": f.label, "origin": f.origin, "chars": str(len(body))})

    n_frames = 0
    if frames_dir and frames_dir.exists():
        fd = dest / "frames"
        fd.mkdir(exist_ok=True)
        for i, src in enumerate(sorted(frames_dir.glob("*.png"))):
            shutil.copy(src, fd / f"frame_{i:02d}.png")
            n_frames += 1

    return {
        "submission_id": submission_id,
        "files_in_pack": len(written),
        "files_identical_to_starter_dropped": skipped_identical,
        "files_dropped_for_length": truncated,
        "chars": used,
        "frames": n_frames,
        "manifest": written,
    }
