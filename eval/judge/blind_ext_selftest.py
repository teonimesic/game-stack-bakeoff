#!/usr/bin/env python3
"""Does `blind_language` blind the extensions a file MENTIONS, and only there?

WHAT THIS EXISTS FOR. `field.build_pack`'s whole blinding for the one aspect judged
with `blind_language=True` was renaming each file to `.src`. That hid the extension
of the file the judge OPENS and nothing hid the ones it READS (#137): measured over
all 84 stored judge packs after `neutralise`, 1,876 occurrences of
`.ts`/`.gd`/`.rs`/`.cs` across 76 of them and 2,083 over the whole vocabulary across
all 84, plus a `CHANGED.txt` in each blind pack listing every authored path with its
true suffix.

FOUR HALVES, and none of them is redundant:

  1. POSITIVE   - a blind field's code and CHANGED.txt carry no arm-naming extension.
  2. MUTANT     - with the rewrite neutered, check 1 must go red. A check that cannot
                  fail is worse than no check (rule 1).
  3. VARIANT    - the same field built with `blind_language=False` must be BYTE-
                  IDENTICAL to what the old code produced. `idiomatic` cannot be
                  asked whether Rust reads like Rust with the word `.rs` removed, so
                  a leak-repair that reached it would be a worse defect than the leak.
                  A mutant cannot ask this question; only a variant can (rule 15).
  4. COLLISIONS - inputs the rewrite must NOT touch even under `blind_language`:
                  `Mutex::lock()`, `player.anim`, `import.meta.url`, and every suffix
                  shared by all four arms. Every false negative adjudicated in this
                  project has been of this kind.

Plus a VOCABULARY AUDIT that reads the four starters and fails on any arm-exclusive
authored suffix that is in neither `field.BLIND_EXT` nor `field._NOT_AN_EXTENSION`,
so the next engine format is a red test rather than a leak nobody thought to look for.

Run:  python3 judge/blind_ext_selftest.py
      python3 judge/blind_ext_selftest.py --runs-root <main checkout>/eval/runs
          ... additionally re-sweeps the stored packs and reports the count that
          would survive the blind path. `eval/runs/**` is gitignored, so a worktree's
          copy is empty and the sweep would confidently report zero.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anonymise  # noqa: E402
import field  # noqa: E402
from aspects import ASPECTS  # noqa: E402

FAILS: list[str] = []


def expect(name: str, cond: bool, detail: str) -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")


#: A worktree is forked at some commit, so a stale copy of `field.py` is a real state
#: this file will meet - and a bare AttributeError is a poor red. Against a checkout
#: that predates the repair, check 1 still runs and still measures the leak; the rest
#: say plainly that they could not.
HAS_REWRITE = hasattr(field, "blind_extensions")
if not HAS_REWRITE:
    FAILS.append("pre-change: `field.blind_extensions` does not exist in this "
                 "checkout, so checks 2-5 measured nothing. Check 1 is the "
                 "measurement of the unrepaired state.")


# The four extensions the census counted, as a pattern that survives a filename stem.
# The stem is the character right before the dot, so a `(?<![A-Za-z0-9_])` lookbehind
# here would find 10 hits where the truth is four figures - the extraction defect that
# cost the first version of this measurement (rule 12).
ARM_EXT_RE = re.compile(r"\.(ts|gd|rs|cs|tscn|meta|asmdef|csproj|toml)(?![A-Za-z0-9_])",
                        re.IGNORECASE)


# ---------------------------------------------------------------------------
# A run in the shape `field.build_pack` reads. The code carries exactly the two
# leak shapes the census found in the real corpus: a cross-file reference in a
# comment, and an import specifier.
# ---------------------------------------------------------------------------
LEAKY = {
    "rust": ('//! `render.rs` tells the HUD from the world; see tests/boundary.rs\n'
             'use crate::sim::world;  // clippy.toml bans Instant\n'),
    "ts":   ('import { f32 } from "./vec2.ts";\n'
             '// the same call `capture.ts` makes, and `trace.test.ts` lists\n'),
    "unity": ('// the shapes live in Pieces.cs, the stack in Well.cs\n'
              '// Sim.asmdef sets noEngineReferences; VertexColor.shader is imported\n'),
    "godot": ('## `tests/render_test.gd` builds this scene; `main.tscn` would not\n'
              '## see display/window/size in project.godot\n'),
}

DIFFSTAT = {
    "rust": " crates/sim/src/world.rs | 42 ++--\n Cargo.toml | 3 +\n",
    "ts": " src/sim/world.ts | 42 ++--\n public/index.html | 25 +-\n",
    "unity": " Assets/Sim/Grid.cs | 42 ++--\n Assets/Sim/Grid.cs.meta | 7 +\n",
    "godot": " sim/world.gd | 42 ++--\n main.tscn | 12 +-\n",
}

#: THE MANIFEST'S ORIGINS MUST BE REAL PATHS, and this fixture said `real/1` until
#: 2026-08-23 because nothing read the field. Task 95 made `build_pack` rebuild a
#: blind `CHANGED.txt` from origin -> label, so a placeholder origin now maps nothing
#: and the packer refuses - correctly. The first pack file of each stack is a path the
#: diff lists (it maps); the second is not (it is dropped), so both branches run here
#: as they do in a real submission, where 196 of 424 rows mapped.
ORIGINS = {
    "rust": ["crates/sim/src/world.rs", "crates/sim/src/tuning.rs"],
    "ts": ["src/sim/world.ts", "src/sim/tuning.ts"],
    "unity": ["Assets/Sim/Grid.cs", "Assets/Sim/Tuning.cs"],
    "godot": ["sim/world.gd", "sim/tuning.gd"],
}


#: A stored `judge_pack/code` label keeps the file's REAL suffix - `sim/01.ts`. The
#: `.src` rename happens when `field.build_pack` copies it into a blind field, which
#: is the behaviour check 3 pins from the other side.
STACK_EXT = {"rust": ".rs", "ts": ".ts", "unity": ".cs", "godot": ".gd"}


def stored_run(root: Path, game: str = "g9_probe") -> Path:
    """Eight submissions, two per stack, each with a leaky pack and a diff.stat."""
    run = root / "run"
    for stack in ("rust", "ts", "unity", "godot"):
        for trial in ("t0", "t1"):
            sub = run / "artifacts" / f"{game}__{stack}__{trial}"
            code = sub / "eval" / "judge_pack" / "code"
            (code / "sim").mkdir(parents=True)
            manifest = []
            for i, body in enumerate((LEAKY[stack], "// plain\n"), start=1):
                label = f"sim/{i:02d}{STACK_EXT[stack]}"
                (code / label).write_text(body)
                manifest.append({"label": label, "origin": ORIGINS[stack][i - 1],
                                 "chars": str(len(body))})
            (sub / "diff.stat").write_text(DIFFSTAT[stack])
            (sub / "eval" / "report.json").write_text(json.dumps({
                "game": game,
                "pack": {"built": True, "files_in_pack": len(manifest),
                         "files_dropped_for_length": 0, "frames": 0,
                         "manifest": manifest}}))
    return run


def pack_text(dest: Path) -> dict[str, str]:
    return {str(p.relative_to(dest)): p.read_text()
            for p in sorted(dest.rglob("*"))
            if p.is_file() and not p.name.endswith(".MAPPING.json")
            and ".claude" not in p.parts}


def leaks(texts: dict[str, str]) -> dict[str, list[str]]:
    return {k: sorted({m.group(0) for m in ARM_EXT_RE.finditer(v)})
            for k, v in texts.items() if ARM_EXT_RE.search(v)}


# ---------------------------------------------------------------------------
# 1. POSITIVE. A blind field carries no arm-naming extension anywhere.
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    run = stored_run(root)
    dest = root / "blind"
    field.build_pack(run, "g9_probe", dest, order_seed=7,
                     sees="code", blind_language=True)
    blind_texts = pack_text(dest)
    found = leaks(blind_texts)
    expect("blind-pack-has-no-arm-extension", not found,
           f"{sum(len(v) for v in found.values())} extension(s) survive: "
           f"{ {k: v for k, v in list(found.items())[:4]} }")
    changed = [k for k in blind_texts if k.endswith("CHANGED.txt")]
    expect("blind-pack-has-changed-txt", len(changed) == 8,
           f"{len(changed)} CHANGED.txt files, expected 8 - the check below is "
           f"vacuous without them")
    # THIS CHECK NO LONGER MEASURES THE EXTENSION REWRITE, and saying so is the point.
    # Task 95 made a blind `CHANGED.txt` a rebuild from the pack's origin -> label
    # manifest, so its rows are already `sim/01.src` before `blind_extensions` ever
    # sees them and this assertion would now pass with the rewrite deleted. It is kept
    # because it still pins the property a reader comes here for - a blind CHANGED.txt
    # names no true suffix - but the mechanism it exercises is the mapping, and
    # `blind_dir_selftest.py` is where that has its own mutant. A check that quietly
    # changed what it tests is this project's central failure mode; the alternative to
    # this comment is a green nobody can interpret.
    expect("blind-changed-txt-neutral",
           not any(ARM_EXT_RE.search(blind_texts[k]) for k in changed),
           "CHANGED.txt still lists true suffixes")
    # The half that already worked, pinned so a regression in it is visible here too.
    on_disk = [k for k in blind_texts if "/sim/" in k]
    expect("blind-pack-filenames-neutral",
           bool(on_disk) and all(k.endswith(field.NEUTRAL_EXT) for k in on_disk),
           f"file names in a blind pack: {on_disk[:4]}")
    print(f"1 blind field            files={len(blind_texts)} "
          f"leaking_files={len(found)} changed_txt={len(changed)} "
          f"code_files={len(on_disk)}")

    # ---------------------------------------------------------------------
    # 2. MUTANT. Neuter the rewrite; check 1 must go red.
    # ---------------------------------------------------------------------
    mfound: dict[str, list[str]] = {}
    if HAS_REWRITE:
        real = field.blind_extensions
        field.blind_extensions = lambda t: t          # type: ignore[assignment]
        try:
            mdest = root / "mutant"
            field.build_pack(run, "g9_probe", mdest, order_seed=7,
                             sees="code", blind_language=True)
            mfound = leaks(pack_text(mdest))
        finally:
            field.blind_extensions = real             # type: ignore[assignment]
        expect("mutant-turns-check-red", bool(mfound),
               "with `blind_extensions` neutered the pack still read clean, so check "
               "1 cannot fail and measures nothing")
    print(f"2 mutant (no rewrite)    leaking_files={len(mfound)} "
          f"occurrences={sum(len(v) for v in mfound.values())}")

    # ---------------------------------------------------------------------
    # 3. VARIANT. The non-blind path must be byte-identical to the old behaviour,
    #    which is `neutralise` and nothing else. Compared against the source text
    #    put through `neutralise` directly rather than against a stored golden, so
    #    the assertion cannot drift with the fixture.
    # ---------------------------------------------------------------------
    ndest = root / "plain"
    field.build_pack(run, "g9_probe", ndest, order_seed=7,
                     sees="code", blind_language=False)
    plain = pack_text(ndest)
    want_bodies = {anonymise.neutralise(b) for b in LEAKY.values()}
    got_bodies = {v for k, v in plain.items() if "/sim/" in k}
    identical = want_bodies <= got_bodies
    expect("non-blind-pack-byte-identical", identical,
           f"a non-blind pack differs from `neutralise` alone: missing "
           f"{[b[:60] for b in sorted(want_bodies - got_bodies)]}")
    kept = sorted({Path(k).suffix for k in plain if "/sim/" in k})
    expect("non-blind-pack-keeps-filenames", kept == sorted(set(STACK_EXT.values())),
           f"non-blind file suffixes are {kept}, expected the four real ones")
    still = leaks(plain)
    expect("non-blind-pack-keeps-extensions", len(still) >= 8,
           f"only {len(still)} non-blind file(s) still name an extension - the "
           f"repair has reached the aspect that must NOT be blinded")
    print(f"3 non-blind field        files={len(plain)} "
          f"byte_identical_to_neutralise={identical} suffixes_kept={kept} "
          f"files_still_naming_an_extension={len(still)}")


# ---------------------------------------------------------------------------
# 4. COLLISIONS. Text the rewrite must leave byte-identical. Each row is a real
#    shape from the stored corpus with its measured count.
# ---------------------------------------------------------------------------
UNTOUCHED = [
    ("mutex-lock-call", "*sink.0.lock().unwrap() = None;", "108 in corpus"),
    ("lock-field", "enemy.velocity = enemy.lock;", "5 in corpus"),
    ("anim-member", "if player.anim == AnimKind::Attack {", "128 in corpus, 0 files"),
    ("anim-chain", "assert_eq!(sim.player().anim, AnimKind::Walk);", "member access"),
    ("import-meta-url", "new URL('./golden/frame.png', import.meta.url)", "83 in corpus"),
    ("import-meta-bare", "// `import.meta` is ESM's namespace object", "_NOT_A_PATH"),
    ("res-call", 'var full: String = AudioBank.res(path)', "1 in corpus, a call"),
    ("shared-json", 'read("data/levels.json")', "all four arms use .json"),
    ("shared-png", "GOLDEN = 'golden/frame.png'", "all four arms"),
    ("shared-md", "see AGENTS.md and README.md", "all four arms"),
    ("shared-yaml", "ci/build.yaml", "all four arms"),
    ("longer-suffix", "config.tsconfig, vec.rsync, grid.csv, model.gdb",
     "`.ts`/`.rs`/`.cs`/`.gd` must not fire inside a longer suffix"),
]
for name, text, why in UNTOUCHED if HAS_REWRITE else []:
    got = field.blind_extensions(text)
    expect(f"untouched/{name}", got == text, f"({why}) rewritten to: {got!r}")

# And the other direction on the same function: shapes it MUST rewrite.
REWRITTEN = [
    ('import { f32 } from "./vec2.ts";', "import specifier"),
    ("// see tests/render_test.gd", "comment cross-reference"),
    ('load("res://scenes/main.tscn")', "string literal"),
    ('{"entry": "src/main.rs"}', "data file"),
    ("// the shapes live in Pieces.cs", "bare filename, no path"),
    (" Assets/Sim/Grid.cs.meta | 7 +", "diff --stat row, chained suffix"),
    ("vitest.config.mts.bak", "a real suffix under a backup suffix"),
    ("// Usage: node tools/audio-manifest.mjs   (or: just audio-manifest)",
     "a filename followed by whitespace and a parenthesis is not a call - a real "
     "pack found this and no fixture had produced it"),
]
for text, why in REWRITTEN if HAS_REWRITE else []:
    got = field.blind_extensions(text)
    expect(f"rewritten/{why}", got != text and not ARM_EXT_RE.search(got),
           f"left as {got!r}")
print(f"4 collisions             untouched={len(UNTOUCHED) * HAS_REWRITE} "
      f"rewritten={len(REWRITTEN) * HAS_REWRITE}")


# ---------------------------------------------------------------------------
# 5. VOCABULARY AUDIT, derived from the product rather than from a list of the
#    spellings somebody saw. Every suffix that is exclusive to ONE starter tree
#    must be listed as blinded or excused by name.
# ---------------------------------------------------------------------------
STARTERS = Path(__file__).resolve().parents[1] / "starters"
ARMS = ("godot", "rust", "ts", "unity")
#: Suffixes that are arm-exclusive in the starters by accident of which arm happened
#: to ship a shell script or a lockfile. They name no language and no engine format.
_NEUTRAL_SUFFIXES = {"sh", "yaml", "yml", "txt", "md", "png", "json", "just", "svg",
                     "wav", "ogg", "css", "log", "bin", "map", "ttf", "xml", "ps1",
                     "py", "gitignore"}
if STARTERS.is_dir() and HAS_REWRITE:
    where: dict[str, set[str]] = {}
    for arm in ARMS:
        for p in (STARTERS / arm).rglob("*"):
            if not p.is_file():
                continue
            if any(part in anonymise.SKIP_DIRS for part in p.relative_to(STARTERS / arm).parts):
                continue
            if p.suffix:
                where.setdefault(p.suffix.lower().lstrip("."), set()).add(arm)
    exclusive = {s for s, arms in where.items() if len(arms) == 1}
    unaccounted = sorted(exclusive - field.BLIND_EXT - set(field._NOT_AN_EXTENSION)
                         - _NEUTRAL_SUFFIXES)
    expect("vocabulary-covers-every-arm-exclusive-suffix", not unaccounted,
           f"{unaccounted} appear in exactly one starter and are neither blinded nor "
           f"excused. Add each to field.BLIND_EXT, or to field._NOT_AN_EXTENSION with "
           f"the count that decided it, or to _NEUTRAL_SUFFIXES here if it names no "
           f"language.")
    # NEGATIVE CONTROL for the audit itself: it must be able to report something.
    expect("vocabulary-audit-is-not-vacuous", len(exclusive) >= 10,
           f"only {len(exclusive)} arm-exclusive suffix(es) found under {STARTERS} - "
           f"the audit is reading an empty or wrong tree (rule 12), not a clean one")
    print(f"5 vocabulary audit       arm_exclusive={len(exclusive)} "
          f"unaccounted={len(unaccounted)}")
elif HAS_REWRITE:
    FAILS.append(f"vocabulary-audit: {STARTERS} does not exist, so the audit read "
                 f"nothing. That is unmeasured, not clean.")
else:
    print("5 vocabulary audit       skipped (pre-change checkout)")

# ---------------------------------------------------------------------------
# 6. THE INVARIANT THE REWRITE RELIES ON. It covers code and CHANGED.txt. If an
#    aspect is ever declared blind AND given frames, telemetry or audio, those
#    channels are not rewritten and this must be a red test, not a silent hole.
# ---------------------------------------------------------------------------
wrong = sorted(a.id for a in ASPECTS.values()
               if a.blind_language and set(a.sees.split("+")) != {"code"})
expect("blind-aspects-see-code-only", not wrong,
       f"{wrong} are blind_language and read a channel the extension rewrite does "
       f"not cover. Extend `field.build_pack`'s `_text` to that channel first.")
print(f"6 blind aspects            "
      f"{sorted(a.id for a in ASPECTS.values() if a.blind_language)} sees=code only: "
      f"{not wrong}")


# ---------------------------------------------------------------------------
# 7. THE PATH A HUMAN TYPES. Everything above calls `build_pack` directly, and the
#    module docstring tells a reader to run `field.py pack --aspect architecture`.
#    That CLI read the aspect's `sees` and NOT its `blind_language` until 2026-08-23,
#    so a pack built the documented way was not blinded at all (#138) - 199 of the 207
#    evidence files in a real `wg-g4c` field kept their real suffix and the content
#    carried 667 arm-naming extension tokens. Guard the resource, and verify on the
#    path that actually holds it (rule 13).
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    run = stored_run(root)
    seen: dict[str, tuple[int, int]] = {}
    for aspect_id in ("architecture", "idiomatic"):
        out = root / f"cli-{aspect_id}"
        r = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "field.py"), "pack",
             "--run", str(run), "--game", "g9_probe", "--out", str(out),
             "--aspect", aspect_id],
            capture_output=True, text=True)
        expect(f"cli-{aspect_id}-exits-0", r.returncode == 0,
               f"exit {r.returncode}: {r.stderr[-300:]}")
        code = [p for p in out.rglob("*") if p.is_file() and "/sim/" in str(p)]
        neutral = sum(1 for p in code if p.suffix == field.NEUTRAL_EXT)
        tokens = sum(len(ARM_EXT_RE.findall(p.read_text())) for p in code)
        seen[aspect_id] = (neutral, tokens)
    n_arch, t_arch = seen["architecture"]
    n_idio, t_idio = seen["idiomatic"]
    expect("cli-blind-aspect-is-blinded", n_arch == 16 and t_arch == 0,
           f"`field.py pack --aspect architecture` produced {n_arch}/16 neutral "
           f"filenames and {t_arch} extension tokens - the CLI is not passing "
           f"blind_language")
    expect("cli-non-blind-aspect-is-untouched", n_idio == 0 and t_idio > 0,
           f"`field.py pack --aspect idiomatic` produced {n_idio} neutral filenames "
           f"and {t_idio} extension tokens - the CLI is blinding an aspect that must "
           f"not be blinded")
    print(f"7 CLI entry point        architecture: {n_arch}/16 neutral names, "
          f"{t_arch} tokens | idiomatic: {n_idio} neutral names, {t_idio} tokens")


# ---------------------------------------------------------------------------
# Optional: re-sweep the stored packs and report the count under the blind path.
# ---------------------------------------------------------------------------
ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--runs-root", type=Path)
args, _ = ap.parse_known_args()
if args.runs_root and HAS_REWRITE:
    # `*/artifacts/*/eval/judge_pack/code` finds 68 of the 84: `wg-g4c-capgate` nests
    # its two arms one level deeper. The address is an input to the check (rule 12).
    before = after = declined = 0
    packs_before: set[str] = set()
    packs_after: set[str] = set()
    n_packs = 0
    for code in sorted(args.runs_root.glob("**/judge_pack/code")):
        if not code.is_dir():
            continue
        n_packs += 1
        for f in code.rglob("*"):
            if not f.is_file():
                continue
            t = anonymise.neutralise(f.read_text(errors="ignore"))
            b = len(ARM_EXT_RE.findall(t))
            blinded = field.blind_extensions(t)
            # The deliberate exclusions are counted SEPARATELY rather than quietly
            # subtracted. `import.meta` is a language construct that happens to be
            # spelled `stem.extension`; it names no file, and blinding syntax is
            # out of scope by design (`JUDGING.md`: 8 of 8 stay identifiable by
            # syntax). Every reason not to count a failure is a channel a bug can
            # widen (rule 7), so it is reported on its own line.
            for lit in field._NOT_A_PATH:
                declined += blinded.count(lit)
                blinded = blinded.replace(lit, "")
            a = len(ARM_EXT_RE.findall(blinded))
            before += b
            after += a
            if b:
                packs_before.add(str(code))
            if a:
                packs_after.add(str(code))
    print(f"\nre-sweep of stored packs ({n_packs} packs under {args.runs_root})")
    print(f"  neutralise only          : {before} occurrence(s) in "
          f"{len(packs_before)} packs")
    print(f"  + blind_extensions       : {after} occurrence(s) in "
          f"{len(packs_after)} packs")
    print(f"  declined, not a path     : {declined} ({', '.join(field._NOT_A_PATH)})")
    expect("sweep-is-not-vacuous", n_packs > 0,
           f"no judge packs under {args.runs_root} - the sweep measured nothing")
    expect("sweep-has-something-to-repair", before > 0,
           f"the pre-repair sweep found 0 occurrences in {n_packs} packs, so the "
           f"post-repair 0 below is a reading of an empty set, not a repair")
    expect("sweep-blind-path-is-clean", after == 0,
           f"{after} occurrence(s) survive the blind path in {len(packs_after)} packs")

if FAILS:
    print("\nFAIL")
    for f in FAILS:
        print(f"  - {f}")
    raise SystemExit(1)
print("\nOK")
