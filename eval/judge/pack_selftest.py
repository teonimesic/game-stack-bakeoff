#!/usr/bin/env python3
"""Does a judge pack on disk contain exactly what its own manifest says, and can that fail?

THE INPUT THAT PRODUCES THE DEFECT IS A SECOND PASS WITH A DIFFERENT FILE SET.

`anonymise.build_pack` labels files `bucket/NN.ext` with NN counted within the bucket, so
the moment the set of picked files changes between two passes over the same destination the
numbering shifts and the previous pass's files survive under labels the new manifest does
not list. A mutant that deletes the clearing code cannot manufacture that input; only a
VARIANT - re-running the real function twice with a changed exclusion set - can (rule 15).
Every check below is written as set equality against the manifest, never as an exit code:
`build_pack` returned 0 on all nine passes over `wg-g4c` and the pack still grew.

Run:  python3 judge/pack_selftest.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import anonymise  # noqa: E402
import field  # noqa: E402

FAILS: list[str] = []


def expect(name: str, cond: bool, detail: str) -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")


def on_disk(dest: Path) -> set[str]:
    code = dest / "code"
    return {str(p.relative_to(code)) for p in code.rglob("*") if p.is_file()}


def labels(manifest: dict) -> set[str]:
    return {e["label"] for e in manifest["manifest"]}


def make_submission(root: Path, extra: dict[str, str] | None = None) -> tuple[Path, Path]:
    """A submission and the starter it was built from. Deliberately multi-bucket."""
    starter = root / "starter"
    sub = root / "sub"
    files = {
        "src/sim/world.ts": "export const world = 1;\n",
        "src/sim/physics.ts": "export const g = 9.8;\n",
        "src/view/draw.ts": "export const draw = () => {};\n",
        "tests/world.spec.ts": "it('works', () => {});\n",
        "tools/gen.py": "print('gen')\n",
        "tools/tape.mjs": "console.log('tape');\n",
        "data/levels.json": '{"levels": 3}\n',
    }
    files.update(extra or {})
    for rel, body in files.items():
        p = sub / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    (starter / "src" / "sim").mkdir(parents=True, exist_ok=True)
    (starter / "src" / "sim" / "untouched.ts").write_text("export const x = 0;\n")
    return sub, starter


# ---------------------------------------------------------------------------
# 1. POSITIVE CONTROL. A single pass must already satisfy the check, otherwise a
#    green result below would mean nothing (rule 1).
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sub, starter = make_submission(root)
    dest = root / "pack"
    m = anonymise.build_pack(sub, starter, dest, None, "t")
    expect("single-pass-set-equality", on_disk(dest) == labels(m),
           f"disk-only={sorted(on_disk(dest) - labels(m))} "
           f"manifest-only={sorted(labels(m) - on_disk(dest))}")
    print(f"1 single pass            files={len(on_disk(dest))} "
          f"manifest={len(labels(m))} equal={on_disk(dest) == labels(m)}")

# ---------------------------------------------------------------------------
# 2. THE VARIANT THAT PRODUCES THE BUG: a second pass with a CHANGED exclusion set.
#    This is the shape of every re-evaluation of a stored run - `wg-g4c` was
#    evaluated nine times, straddling the #69 cap removal and the #83 leak repair,
#    and ended with 23 files in 222 that no manifest lists.
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sub, starter = make_submission(root)
    dest = root / "pack"
    first = anonymise.build_pack(sub, starter, dest, None, "t")
    after_first = on_disk(dest)
    second = anonymise.build_pack(sub, starter, dest, None, "t",
                                  exclude_origins=frozenset({"src/sim/physics.ts",
                                                             "tools/gen.py"}))
    disk = on_disk(dest)
    stale = disk - labels(second)
    expect("second-pass-set-equality", disk == labels(second),
           f"{len(stale)} file(s) survive under labels the new manifest does not "
           f"list: {sorted(stale)}")
    expect("second-pass-no-growth", len(disk) <= len(after_first),
           f"pack grew from {len(after_first)} to {len(disk)} while the picked set shrank")
    print(f"2 changed exclusion set  pass1={len(after_first)} "
          f"pass2_manifest={len(labels(second))} on_disk={len(disk)} stale={len(stale)}")

# ---------------------------------------------------------------------------
# 3. THE OTHER DIRECTION: a second pass whose file set GROWS. Nothing may be left
#    over from the first, and nothing the manifest lists may be missing.
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sub, starter = make_submission(root)
    dest = root / "pack"
    anonymise.build_pack(sub, starter, dest, None, "t",
                         exclude_origins=frozenset({"src/sim/physics.ts",
                                                    "data/levels.json"}))
    grown = anonymise.build_pack(sub, starter, dest, None, "t")
    disk = on_disk(dest)
    expect("growing-pass-set-equality", disk == labels(grown),
           f"disk-only={sorted(disk - labels(grown))} "
           f"manifest-only={sorted(labels(grown) - disk)}")
    print(f"3 growing file set       manifest={len(labels(grown))} "
          f"on_disk={len(disk)} equal={disk == labels(grown)}")

# ---------------------------------------------------------------------------
# 4. FRAMES ARE THE SAME CHANNEL. They are copied as frame_NN.png, so a rebuild
#    from a shorter capture leaves the tail of the longer one behind. Nothing on
#    disk today carries this, which is exactly why it needs a test rather than a
#    measurement (rule 7: every uncounted channel is one a bug can widen).
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sub, starter = make_submission(root)
    dest = root / "pack"
    frames = root / "frames"
    frames.mkdir()
    for i in range(5):
        (frames / f"{i:02d}.png").write_bytes(b"\x89PNG" + bytes([i]))
    anonymise.build_pack(sub, starter, dest, frames, "t")
    for i in (3, 4):
        (frames / f"{i:02d}.png").unlink()
    m = anonymise.build_pack(sub, starter, dest, frames, "t")
    n_disk = len(list((dest / "frames").glob("*.png")))
    expect("frames-not-accumulated", n_disk == m["frames"],
           f"{n_disk} frames on disk against {m['frames']} in the manifest")
    print(f"4 shorter capture        manifest_frames={m['frames']} on_disk={n_disk}")

# ---------------------------------------------------------------------------
# 5. THE GATE MUST READ THE PACK ON DISK. `pack_completeness` reads
#    `files_dropped_for_length`, which is 0 by construction since #69 - a gate
#    reading its input rather than its output, which is why 23 stale files were
#    invisible for nine evaluations. Build a stored-run shape and plant one.
# ---------------------------------------------------------------------------
def stored_run(root: Path, game: str,
               stacks=("rust", "ts", "unity", "godot")) -> Path:
    """A run in the shape `field.build_pack` reads: eight submissions, two per stack."""
    run = root / "run"
    for stack, trial in [(s, t) for s in stacks for t in ("t0", "t1")]:
        sub = run / "artifacts" / f"{game}__{stack}__{trial}"
        code = sub / "eval" / "judge_pack" / "code"
        code.mkdir(parents=True)
        manifest = []
        for i, (b, ext) in enumerate((("sim", ".ts"), ("view", ".ts"), ("other", ".json"))):
            label = f"{b}/{i + 1:02d}{ext}"
            (code / b).mkdir(exist_ok=True)
            (code / label).write_text(f"// {stack} {trial} {label}\n")
            manifest.append({"label": label, "origin": f"real/{b}{ext}", "chars": "12"})
        (sub / "eval" / "report.json").write_text(json.dumps({
            "game": game,
            "pack": {"built": True, "files_in_pack": len(manifest),
                     "files_dropped_for_length": 0, "frames": 0,
                     "manifest": manifest}}))
    return run


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    run = stored_run(root, "g9_probe")

    # NEGATIVE CONTROL: a clean run must read clean, or the refusal below proves nothing.
    clean = field.pack_matches_manifest(run, "g9_probe")
    expect("gate-clean-on-clean-run", clean["clean"] and not clean["unmeasurable"],
           f"a freshly built run did not read clean: {clean}")

    # Now plant exactly what a second pass leaves behind: a file under a label the
    # manifest does not list.
    planted = (run / "artifacts" / "g9_probe__ts__t0" / "eval" / "judge_pack"
               / "code" / "other" / "07.json")
    planted.write_text("{}\n")
    dirty = field.pack_matches_manifest(run, "g9_probe")
    expect("gate-sees-stale-file", not dirty["clean"] and dirty["stale_total"] == 1,
           f"the gate did not see the planted file: {dirty}")
    expect("gate-names-the-stack", dirty["stale_by_stack"] == {"ts": 1},
           f"stale_by_stack={dirty['stale_by_stack']}")

    # And the gate must be reachable from the thing that spends money.
    raised = ""
    try:
        field.build_pack(run, "g9_probe", root / "field", 0, sees="code")
    except RuntimeError as e:
        raised = str(e)
    expect("field-build-refuses-stale", "STALE" in raised,
           f"field.build_pack did not refuse a stale field; it raised {raised[:120]!r}")
    print(f"5 planted stale file     clean_run={clean['clean']} "
          f"dirty_run_stale={dirty['stale_total']} refused={'STALE' in raised}")

# ---------------------------------------------------------------------------
# 6. A MANIFEST-LESS PACK IS UNMEASURABLE, NOT CLEAN. 25 stored submissions predate
#    the manifest; reporting them as clean would be a reading of an empty set dressed
#    as a reading of the field.
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    run = stored_run(root, "g9_probe")
    (run / "artifacts" / "g9_probe__rust__t0" / "eval" / "report.json").write_text(
        json.dumps({"game": "g9_probe"}))
    res = field.pack_matches_manifest(run, "g9_probe")
    expect("gate-unmeasurable-is-not-clean", not res["clean"],
           f"a submission with no manifest read as clean: {res}")
    expect("gate-names-unmeasurable", res["unmeasurable"] == ["g9_probe__rust__t0"],
           f"unmeasurable={res['unmeasurable']}")
    print(f"6 no manifest            unmeasurable={res['unmeasurable']} "
          f"clean={res['clean']}")

# ---------------------------------------------------------------------------
# 7. MUTANT: could the check above go green on a pack that IS accumulating? Rebuild
#    the pre-fix behaviour by hand - write pass 1 back over pass 2 - and require the
#    same set-equality assertion to go red. A check that cannot fail is worse than
#    absent.
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    sub, starter = make_submission(root)
    keep = root / "keep"
    dest = root / "pack"
    first = anonymise.build_pack(sub, starter, dest, None, "t")
    shutil.copytree(dest / "code", keep)
    second = anonymise.build_pack(sub, starter, dest, None, "t",
                                  exclude_origins=frozenset({"src/sim/physics.ts",
                                                             "tools/gen.py"}))
    shutil.copytree(keep, dest / "code", dirs_exist_ok=True)   # the pre-fix behaviour
    disk = on_disk(dest)
    expect("mutant-must-be-caught", disk != labels(second),
           "reinstating pass 1 over pass 2 still satisfied set equality, so the "
           "check cannot detect accumulation at all")
    print(f"7 mutant (no clearing)   manifest={len(labels(second))} "
          f"on_disk={len(disk)} caught={disk != labels(second)}")

print(f"\n{len(FAILS)} unmet expectation(s)")
for f in FAILS:
    print("  FAIL", f)
raise SystemExit(1 if FAILS else 0)
