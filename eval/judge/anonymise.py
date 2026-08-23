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

# ---------------------------------------------------------------------------
# WHAT COUNTS AS A LEAK IS A PROPERTY, NOT A SPELLING
# ---------------------------------------------------------------------------
# This used to be a list of REGEXES, one per observed spelling: `\bbevy\b` and `\bBevy\b`
# but not `BEVY`, `\bwinit\b` but not `Winit`, and no rule at all for `cargo` or `crates`.
# So `CARGO_MANIFEST_DIR`, `CARGO_TARGET_TMPDIR`, `BEVY_ASSET_ROOT`, `crates/sim` and
# `WinitPlugin` walked through it untouched and reached 22 of 68 stored code packs, in a
# pack built for the ONE aspect that is judged with `blind_language=True` (#83, task 73).
# The module's own comment had already recorded the same class from `UnityCsReference`.
#
# A list of spellings has to be re-derived by every reader who meets a case convention
# that is not on it. So the vocabulary below is a list of NAMES -- one lowercase entry per
# engine, language, package manager, build tool, workspace directory, linter, formatter
# and test runner that belongs to exactly one arm -- and the MATCHING is the property:
#
#     a name matches wherever it forms a whole IDENTIFIER SEGMENT, in any case
#     convention, in any position inside an identifier or a path.
#
# Segments are what `_segments()` splits on: `_`, digit boundaries, and camel/Pascal
# boundaries. `CARGO_MANIFEST_DIR` -> CARGO|MANIFEST|DIR, `WinitPlugin` -> Winit|Plugin,
# `crates/sim` -> crates, sim. A name may also span several consecutive segments, so
# `TypeScript`, `MonoBehaviour`, `GDScript` and `node_modules` match without an entry for
# each casing.
#
# THE OTHER HALF, AND IT IS WHY THIS IS NOT SIMPLY A CASE-INSENSITIVE SUBSTRING SEARCH.
# Measured over the same 84 stored packs, a substring search would have rewritten:
#   * `immunity` -> `imm<engine>`   -- 54 occurrences, in all four arms; "unity" is in it
#   * `Vec3.UnitY` -> `Vec3.<engine>` -- a math constant, Unit + Y, not the engine
#   * `main.tscn`, `bestScore`, `addInitScript` -- all contain `tsc`
#   * `is_three_dimensional`, `Three tests enforce`, `you trust this macro`
# Segmentation rejects every one of them: `immunity` is a single segment, `UnitY` splits
# to Unit|Y, `tscn` is not `tsc`. Two names are excluded from the vocabulary outright
# because no segmentation can save them -- see `_LITERAL_TOKENS`.
#
# Ordering is NOT load-bearing any more. The longest run of segments wins, so
# `bevyengine/bevy#6183` rewrites both halves and can no longer half-substitute into
# `bevyengine/engine#6183`, which named the engine AND advertised that a substitution had
# happened.
_STACK_NAMES: dict[str, str] = {
    # Organisations and repositories. They CONTAIN an engine name; longest-window-wins
    # means they are found first without depending on the order of this dict.
    "bevyengine": "engineorg", "godotengine": "engineorg",
    "unitytechnologies": "engineorg", "mrdoob": "engineorg",
    # Engines.
    "bevy": "engine", "godot": "engine", "unity": "engine", "threejs": "engine",
    "unityengine": "enginecore", "unityeditor": "engineeditor",
    "monobehaviour": "enginebehaviour",
    # Rendering and windowing crates only one arm has.
    "wgpu": "gpu", "winit": "windowing",
    # Languages.
    "rust": "lang", "typescript": "lang", "gdscript": "script",
    # Build tools, package managers, workspace layout.
    "cargo": "buildtool", "crates": "pkgs", "rustup": "toolchainmgr",
    "npm": "pkgtool", "pnpm": "pkgtool", "yarn": "pkgtool",
    "nodemodules": "pkgdir", "tsconfig": "langconfig", "vite": "bundler",
    "dotnet": "runtime", "csproj": "projfile",
    # Compilers, linters, formatters.
    "rustc": "compiler", "tsc": "compiler", "clippy": "linter", "eslint": "linter",
    "gdlint": "linter", "rustfmt": "formatter", "prettier": "formatter",
    # Test runners and frameworks.
    "nextest": "testrunner", "vitest": "testrunner", "nunit": "testframework",
    "playwright": "browserdriver",
}

#: A tool's config file is conventionally `<tool>rc`, with no separator to segment on, so
#: `gdlintrc` and `prettierrc` are one segment and no window matches them. This is a
#: naming CONVENTION rather than two more spellings, which is why it is a rule and not two
#: dictionary entries.
_CONFIG_SUFFIXES = ("rc",)

#: Forms the segment matcher cannot express, kept as literal patterns.
#:
#: `three` and `Node2D`/`Node3D` are here for opposite reasons, and both reasons are
#: measured:
#:
#: * `three` is an English numeral. Segment matching would rewrite `is_three_dimensional`
#:   and `Three tests enforce` -- 118 occurrences across all four arms in the stored
#:   packs, of which the three.js ones are a minority. Only the lowercase package
#:   specifier and the uppercase namespace are unambiguous, so only those two are matched.
#:   `node` is excluded entirely for the same reason: it is the godot scene-tree noun and
#:   the linked-list noun in every arm.
#: * `Node2D` segments to Node|2|D, whose tail is a one-letter segment -- the shape that
#:   `_match_window` refuses, because refusing it is what stops `UnitY` matching `unity`.
_LITERAL_TOKENS = [
    (r"\bNode2D\b", "SceneNode2D"), (r"\bNode3D\b", "SceneNode3D"),
    (r"\bthree\b", "engine"), (r"\bTHREE\b", "ENGINE"),
]
#: `verify_blind.check_pack_skill` iterates this to scan text the judge is handed that did
#: NOT come from a submission. It is the literal half only; use `find_stack_names()` for a
#: complete answer.
_STACK_RE = [(re.compile(p), r) for p, r in _LITERAL_TOKENS]

#: Runs of identifier characters. Everything else -- `/`, `.`, `-`, quotes, whitespace --
#: separates one run from the next, so `crates/sim` is two runs and `crates` is a whole
#: segment of the first.
_RUN_RE = re.compile(r"[A-Za-z0-9_]+")
#: Segment boundaries inside one run: an acronym run (`CARGO`, `GD`), a Pascal word
#: (`Winit`, `Script`), a lowercase word, or a digit group. `_` matches nothing here and
#: is therefore skipped, which is what makes `CARGO_MANIFEST_DIR` three segments.
_SEG_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|[0-9]+")
#: How many consecutive segments one name may span. The longest entry above is two
#: (`Unity|Technologies`, `Type|Script`, `node|modules`); three leaves headroom.
_MAX_WINDOW = 3

_CANDIDATE_RE: re.Pattern[str]


def _rebuild_matcher() -> None:
    """Recompute the cheap pre-filter after `_STACK_NAMES` changes.

    Only the mutant half of `anonymise_selftest.py` changes it at runtime; the pre-filter
    is an optimisation, and one that would silently stop matching a name if it were left
    stale, so it is rebuilt rather than patched.
    """
    global _CANDIDATE_RE
    alts = sorted((re.escape(k) for k in _STACK_NAMES), key=len, reverse=True)
    _CANDIDATE_RE = re.compile("|".join(alts) if alts else r"(?!x)x", re.IGNORECASE)


_rebuild_matcher()


def _segments(run: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _SEG_RE.finditer(run)]


def _match_window(segs: list[tuple[int, int, str]], i: int) -> tuple[int, str] | None:
    """Longest run of segments at `i` that spells a stack name. Returns (width, repl)."""
    for k in range(min(_MAX_WINDOW, len(segs) - i), 0, -1):
        win = segs[i:i + k]
        # A ONE-LETTER SEGMENT IS AN AXIS OR AN INDEX, NOT A WORD. Without this,
        # `Vec3.UnitY` (Unit|Y) spells `unity` and a math constant in the Unity arm's
        # own vector type gets rewritten to the engine placeholder. `TypeScript`
        # (Type|Script) and `node_modules` are unaffected: every segment is >= 2.
        if k > 1 and any(len(s[2]) < 2 for s in win):
            continue
        joined = "".join(s[2] for s in win).lower()
        repl = _STACK_NAMES.get(joined)
        if repl is None and k == 1:
            for suf in _CONFIG_SUFFIXES:
                if joined.endswith(suf) and len(joined) > len(suf):
                    base = _STACK_NAMES.get(joined[:-len(suf)])
                    if base is not None:
                        repl = base + suf
                        break
        if repl is not None:
            return k, repl
    return None


def _shape(matched: str, repl: str) -> str:
    """Give the replacement the case convention the matched text was written in."""
    if matched.isupper():
        return repl.upper()
    if matched[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def _scrub_names(text: str, collect: list[str] | None = None) -> str:
    out: list[str] = []
    last = 0
    for run in _RUN_RE.finditer(text):
        body = run.group(0)
        # Cheap pre-filter. A window match concatenates its segments, so the name is a
        # substring of the run with `_` removed -- never of the run as written.
        if not _CANDIDATE_RE.search(body.replace("_", "")):
            continue
        segs = _segments(body)
        base = run.start()
        i = 0
        while i < len(segs):
            hit = _match_window(segs, i)
            if hit is None:
                i += 1
                continue
            k, repl = hit
            s, e = segs[i][0], segs[i + k - 1][1]
            matched = body[s:e]
            if collect is not None:
                collect.append(matched)
            out.append(text[last:base + s])
            out.append(_shape(matched, repl))
            last = base + e
            i += k
    out.append(text[last:])
    return "".join(out)


def find_stack_names(text: str) -> list[str]:
    """Every stack name in `text`, as written. Empty means the text is clean.

    This is the AUDIT half, and it is deliberately the same code path as the rewrite:
    a detector with its own vocabulary would agree with the rewriter by construction and
    measure nothing. What makes the sweep in `anonymise_selftest.py` informative is that
    it runs this over REAL STORED PACK TEXT rather than over the tokens someone thought
    of -- an unenumerated name shows up as a line that changed, or as one that did not.
    """
    found: list[str] = []
    _scrub_names(text, collect=found)
    for rx, _ in _STACK_RE:
        found.extend(m.group(0) for m in rx.finditer(text))
    return found


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
    text = _scrub_names(text)
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
