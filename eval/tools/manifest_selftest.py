#!/usr/bin/env python3
"""Can `manifest.py` still lose a record, and can its audit still fail?

Three halves, because a mutant and a variant answer different questions (AGENTS.md rule 15).

**The write half** asks whether a second launch into a directory can destroy the first
launch's manifest. The MUTANT is the pre-repair writer - one line, `path.write_text(...)` -
run against the same inputs, and it must be caught here. A test that only exercises the
repaired writer cannot tell a fix from a no-op (AGENTS.md rule 14: a control run after the
fix tests the fix, not the claim).

**The rolling half** asks the same question of the other append-only shape, the one where
the canonical name holds the LATEST record and the copy it replaces is kept beside it.
Two shapes exist because two kinds of directory exist - see `manifest.py` - and the
mutant is the same bare `write_text`, because that is what both callers did until task 63:
`field_sweep.py` overwrote a sweep's gate-0 verdict on every re-run, and
`backup_evidence.py` erased what the previous sync had measured on every sync.

**The audit half** asks whether the offline check can fail, and on what. Each case is a
VARIANT - a synthetic run directory built to be wrong in one specific way - not a mutant of
the checker, because every false negative this project has adjudicated came from an input
the check mishandled rather than from a missing mechanism.

The two timezone cases are the regression test for the correction in FINDINGS #93's third
row: run directory names are chosen by the operator and have been stamped in BOTH local
time and UTC, so a checker that assumes one reads a real drift where there is none, and
`wg-audio-2026-08-14T12-29-42` was recorded as a defect it does not have.

The last case is the address guard (AGENTS.md rule 12): an audit over an empty tree must
NOT exit 0. "Examined nothing" and "found nothing wrong" print the same word.

Run:

    python3 eval/tools/manifest_selftest.py

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import manifest as M  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, what: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'}  {what}")
    if not cond:
        FAILS.append(what)


def payload(games, stacks, trials, started: dt.datetime) -> dict:
    return {"stacks": list(stacks), "games": list(games), "trials": trials,
            "model": "opus", "max_turns": 1000, "max_budget_usd": None,
            "work_root": "/tmp/x", "started_at": started.isoformat()}


def make_run(root: Path, name: str, *, declared, present, started: dt.datetime,
             legacy: bool = False, no_manifest: bool = False) -> Path:
    """declared/present are (games, stacks, trials) triples; present may be a trial-id list."""
    d = root / name
    (d / "trials").mkdir(parents=True, exist_ok=True)
    if not no_manifest:
        if legacy:
            (d / "suite.json").write_text(json.dumps(
                {"suite": "core", "template": "/t", "trials": 2}, indent=2))
        else:
            g, s, t = declared
            M.write_manifest(d, payload(g, s, t, started))
    if isinstance(present, tuple):
        g, s, t = present
        ids = [f"{game}__{stack}__t{i}" for game in g for stack in s for i in range(t)]
    else:
        ids = list(present)
    for tid in ids:
        (d / "trials" / f"{tid}.json").write_text(json.dumps({"trial_id": tid}))
    return d


def codes(audit) -> set[str]:
    return {i.code for i in audit.issues}


# --------------------------------------------------------------------------- write half

def test_write(tmp: Path) -> None:
    print("\nwrite path - a second launch must not destroy the first record")
    run = tmp / "wg-x-2026-08-20T10-00-00"
    run.mkdir(parents=True)
    t0 = dt.datetime(2026, 8, 20, 13, 0, 0, tzinfo=dt.timezone.utc)

    p1 = M.write_manifest(run, payload(["g1_pong"], ["rust", "ts"], 2, t0))
    check(p1.name == "suite.json", "first write lands on suite.json")
    first_bytes = p1.read_bytes()
    m1 = json.loads(first_bytes)
    check(m1.get("run_dir") == run.name,
          "manifest records the directory it belongs to (kills the timezone guess)")
    check(m1.get("manifest_schema") == M.SCHEMA, "manifest records its schema")

    t1 = t0 + dt.timedelta(hours=20)
    p2 = M.write_manifest(run, payload(["g3_arena"], ["unity"], 2, t1))
    check(p2 != p1, "second write lands on a DIFFERENT path")
    check(p1.read_bytes() == first_bytes,
          "second write left suite.json byte-identical (this is the whole point)")
    m2 = json.loads(p2.read_text())
    check(m2.get("supersedes") == "suite.json", "the sibling names what it supersedes")
    check(m2.get("previous_started_at") == t0.isoformat(),
          "the sibling records the started_at it did not overwrite")

    t2 = t1 + dt.timedelta(hours=1)
    p3 = M.write_manifest(run, payload(["g3_arena"], ["godot"], 2, t2))
    check(p3 not in (p1, p2), "a third write lands on a third path")
    check(p1.read_bytes() == first_bytes, "suite.json still byte-identical after three writes")
    check(len(M.read_manifests(run)) == 3, "all three manifests are discoverable")

    # Same timestamp twice: the name must still not collide.
    p4 = M.write_manifest(run, payload(["g2_tetris3d"], ["rust"], 1, t2))
    check(p4 not in (p1, p2, p3), "an identical started_at does not collide onto an existing name")

    # THE MUTANT: the pre-repair writer. If this does not destroy the record, the test
    # is not measuring what it claims to measure.
    (run / "suite.json").write_text(json.dumps(payload(["g3_arena"], ["unity"], 2, t1)))
    check(p1.read_bytes() != first_bytes,
          "MUTANT (unconditional write_text) destroys suite.json - the test can see the defect")


# ------------------------------------------------------------------------- rolling half

def test_rolling(tmp: Path) -> None:
    """The OTHER append-only shape: canonical holds the latest, the old one is kept.

    Same protected property as `test_write` - no record on disk is destroyed - and a
    different layout, because a sweep directory and a backup destination have no identity
    the canonical name is owed to. The mutant is the same one: the pre-repair writer,
    which is a bare `write_text`.
    """
    print("\nrolling path - the record a re-run replaces must survive it")
    d = tmp / "rolling"
    d.mkdir(parents=True)
    p = d / "MEASURED.json"

    v1 = {"verified_at": "2026-08-20T10:00:00+00:00", "evidence_files": 1}
    path1, kept1 = M.write_rolling_json(p, v1, quiet=True)
    check(path1 == p and kept1 is None, "first write lands on the canonical name alone")
    first_bytes = p.read_bytes()

    v2 = {"verified_at": "2026-08-21T11:30:00+00:00", "evidence_files": 2}
    _, kept2 = M.write_rolling_json(p, v2, quiet=True)
    check(kept2 is not None and kept2.read_bytes() == first_bytes,
          "the record the second write replaces is kept BYTE-IDENTICAL")
    check(kept2.name == "MEASURED-20260820T100000Z.json",
          "the kept copy is named for the time the record it holds was made, not for now")
    check(json.loads(p.read_text())["evidence_files"] == 2,
          "the canonical name holds the LATEST record (this is the shape's whole point)")
    check(json.loads(p.read_text())["superseded_record"] == kept2.name,
          "the canonical record names the copy it superseded")

    v3 = {"verified_at": "2026-08-22T09:00:00+00:00", "evidence_files": 3}
    _, kept3 = M.write_rolling_json(p, v3, quiet=True)
    check(kept3 != kept2 and kept2.read_bytes() == first_bytes,
          "a third write keeps a third copy and leaves the first one untouched")
    check(json.loads(kept3.read_text())["evidence_files"] == 2,
          "the second record survived the third write")

    # Same embedded timestamp twice: the name must not collide onto an existing file.
    _, kept4 = M.write_rolling_json(p, dict(v3, evidence_files=4), quiet=True)
    check(kept4 not in (kept2, kept3), "an identical timestamp does not collide")

    # VARIANT: a record with no timestamp field at all. `MANIFEST.sha256` is exactly this
    # - a plain checksum list - and it must still be kept, stamped from its mtime.
    t = d / "MANIFEST.sha256"
    M.write_rolling(t, "aaa  runs/one\n", quiet=True)
    os.utime(t, (1_755_000_000, 1_755_000_000))
    _, keptt = M.write_rolling(t, "bbb  runs/two\n", quiet=True)
    check(keptt is not None and keptt.read_text() == "aaa  runs/one\n",
          "a text record with no embedded timestamp is still kept, stamped from mtime")
    check(keptt.name == "MANIFEST-20250812T120000Z.sha256",
          f"the mtime stamp is UTC and the suffix survives (got {keptt.name})")

    # VARIANT: an identical restatement is NOT a new record. `--verify-only` is meant to
    # be run freely against a 1.1 MB checksum manifest; if every re-run kept a copy, the
    # guard would cost a megabyte per check and get switched off.
    before = sorted(x.name for x in d.iterdir())
    _, kept_same = M.write_rolling(t, "bbb  runs/two\n", quiet=True)
    check(kept_same is None and sorted(x.name for x in d.iterdir()) == before,
          "re-writing identical bytes keeps nothing and adds no file")

    # VARIANT: a record whose timestamp field is unparseable must still be KEPT. Refusing
    # to name it would be a reason to destroy it (AGENTS.md rule 7).
    q = d / "BROKEN.json"
    q.write_text('{"verified_at": "not a timestamp", "n": 1}')
    _, keptq = M.write_rolling_json(q, {"verified_at": "2026-08-22T09:00:00+00:00"},
                                    quiet=True)
    check(keptq is not None and json.loads(keptq.read_text())["n"] == 1,
          "a record with an unparseable timestamp is kept, not dropped")

    # THE MUTANT: the pre-repair writer, one line, run against the same inputs. If it
    # does not destroy a record here, this test cannot tell the fix from a no-op
    # (AGENTS.md rule 14).
    survivors = {x.name: x.read_bytes() for x in d.iterdir() if x.is_file()}
    p.write_text(json.dumps({"verified_at": "2026-08-23T00:00:00+00:00",
                             "evidence_files": 5}))
    now = {x.name: x.read_bytes() for x in d.iterdir() if x.is_file()}
    check(now.get(p.name) != survivors[p.name] and set(now) == set(survivors),
          "MUTANT (unconditional write_text) replaces the record and keeps no copy - "
          "the test can see the defect")


# --------------------------------------------------------------------------- audit half

def test_audit(tmp: Path) -> None:
    root = tmp / "runs"
    root.mkdir(parents=True)

    print("\naudit - clean cases must be clean")
    ok_utc = make_run(root, "wg-ok-utc-2026-08-20T10-00-00",
                      declared=(["g1_pong"], ["rust", "ts"], 2),
                      present=(["g1_pong"], ["rust", "ts"], 2),
                      started=dt.datetime(2026, 8, 20, 10, 0, 12, tzinfo=dt.timezone.utc))
    check(codes(M.audit_run(ok_utc)) == set(), "directory stamped in UTC is clean")

    ok_local = make_run(root, "wg-ok-local-2026-08-20T07-00-00",
                        declared=(["g1_pong"], ["rust"], 2),
                        present=(["g1_pong"], ["rust"], 2),
                        started=dt.datetime(2026, 8, 20, 10, 0, 1, tzinfo=dt.timezone.utc))
    check(codes(M.audit_run(ok_local)) == set(),
          "directory stamped in local time is clean (FINDINGS #93 row 3 regression)")

    print("\naudit - each variant must fail, and fail with the right code")
    mismatch = make_run(root, "wg-mismatch-2026-08-20T10-00-00",
                        declared=(["g3_arena"], ["rust", "ts", "unity", "godot"], 2),
                        present=(["g1_pong"], ["rust", "ts", "unity", "godot"], 2),
                        started=dt.datetime(2026, 8, 20, 10, 0, 5, tzinfo=dt.timezone.utc))
    check("MISMATCH" in codes(M.audit_run(mismatch)),
          "manifest naming a game with zero reports beside it -> MISMATCH")

    incomplete = make_run(root, "wg-incomplete-2026-08-20T10-00-00",
                          declared=(["g4_platformer"], ["rust", "ts", "unity", "godot"], 2),
                          present=(["g4_platformer"], ["rust", "ts"], 2),
                          started=dt.datetime(2026, 8, 20, 10, 0, 5, tzinfo=dt.timezone.utc))
    check(codes(M.audit_run(incomplete)) == {"INCOMPLETE"},
          "a strict subset of the declared trials -> INCOMPLETE and nothing else")

    drift = make_run(root, "wg-drift-2026-08-20T10-00-00",
                     declared=(["g1_pong"], ["rust"], 2),
                     present=(["g1_pong"], ["rust"], 2),
                     started=dt.datetime(2026, 8, 20, 18, 0, 0, tzinfo=dt.timezone.utc))
    check("STAMP_DRIFT" in codes(M.audit_run(drift)),
          "started_at 8h from the directory name in either basis -> STAMP_DRIFT")

    # Every manifest in the stored corpus is schema 1 - no `run_dir` field - so the
    # stamp test must carry the whole weight there. A checker that only consulted
    # `run_dir` would be green on all 18 stored directories by construction.
    drift1 = make_run(root, "wg-drift-schema1-2026-08-20T10-00-00",
                      declared=(["g1_pong"], ["rust"], 2),
                      present=(["g1_pong"], ["rust"], 2),
                      started=dt.datetime(2026, 8, 20, 18, 0, 0, tzinfo=dt.timezone.utc))
    m1 = json.loads((drift1 / "suite.json").read_text())
    del m1["run_dir"], m1["manifest_schema"]
    (drift1 / "suite.json").write_text(json.dumps(m1, indent=2))
    check(codes(M.audit_run(drift1)) == {"STAMP_DRIFT"},
          "a schema-1 manifest (no run_dir) is still placed by its stamp")

    # schema 2 carries run_dir, so a MOVED/renamed manifest is caught without any
    # timezone reasoning at all.
    moved = make_run(root, "wg-moved-2026-08-20T10-00-00",
                     declared=(["g1_pong"], ["rust"], 2),
                     present=(["g1_pong"], ["rust"], 2),
                     started=dt.datetime(2026, 8, 20, 10, 0, 3, tzinfo=dt.timezone.utc))
    m = json.loads((moved / "suite.json").read_text())
    m["run_dir"] = "wg-somewhere-else-2026-08-01T00-00-00"
    (moved / "suite.json").write_text(json.dumps(m, indent=2))
    check("MISPLACED" in codes(M.audit_run(moved)),
          "manifest whose own run_dir is not the directory it sits in -> MISPLACED")

    legacy = make_run(root, "core-2026-08-10T09-34-03", declared=None,
                      present=["t1_rally__baseline__t0"],
                      started=dt.datetime(2026, 8, 10, 9, 34, 3, tzinfo=dt.timezone.utc),
                      legacy=True)
    check(codes(M.audit_run(legacy)) == {"LEGACY_SHAPE"},
          "a pre-wholegame manifest is reported as unmeasurable, not as an error")
    check(M.audit_run(legacy).severity == "skip",
          "LEGACY_SHAPE does not turn the sweep red")

    orphan = make_run(root, "wg-orphan-2026-08-20T10-00-00", declared=None,
                      present=["g1_pong__rust__t0"],
                      started=dt.datetime(2026, 8, 20, 10, 0, 0, tzinfo=dt.timezone.utc),
                      no_manifest=True)
    check(codes(M.audit_run(orphan)) == {"NO_MANIFEST"},
          "reports with no manifest at all -> NO_MANIFEST")

    empty = make_run(root, "wg-empty-2026-08-20T10-00-00",
                     declared=(["g1_pong"], ["rust"], 2), present=[],
                     started=dt.datetime(2026, 8, 20, 10, 0, 0, tzinfo=dt.timezone.utc))
    a = M.audit_run(empty)
    check(codes(a) == {"NO_REPORTS"} and a.severity == "warn",
          "a manifest of intent with no reports at all is a warning, not an error")

    print("\naudit - marking acknowledges a defect without hiding a change")
    live = M.audit_run(mismatch)
    M.write_marker(mismatch, live, why="test", reconstructed=None)
    marked = M.audit_run(mismatch)
    check(marked.severity == "marked" and marked.marker is not None,
          "a marker that matches the live measurement downgrades ERROR -> marked")
    check(codes(marked) == codes(live),
          "marking does not erase the issue list - the codes are still reported")

    (mismatch / "trials" / "g1_pong__rust__t0.json").unlink()
    stale = M.audit_run(mismatch)
    check("MARKER_STALE" in codes(stale) and stale.severity == "error",
          "changing the directory under a marker re-reddens it (the marker is not a mute)")

    print("\naudit - a run directory is not always a child of runs/ (task 75)")
    # Answers stated before the tool is asked:
    #   archive-w/wg-nested-...   a real run, one level deeper. MUST be examined.
    #   archive-w/work/decoy      under an agent-authored name. MUST be pruned by name.
    #   <a real run>/work/decoy2  inside a run's own subtree. MUST never be reached,
    #                             because the walk stops at the run above it.
    nested = make_run(root, "archive-w/wg-nested-2026-08-20T10-00-00",
                      declared=(["g1_pong"], ["rust"], 2),
                      present=(["g1_pong"], ["rust"], 2),
                      started=dt.datetime(2026, 8, 20, 10, 0, 4, tzinfo=dt.timezone.utc))
    make_run(root, "archive-w/work/decoy", declared=(["g1_pong"], ["rust"], 1),
             present=(["g1_pong"], ["rust"], 1),
             started=dt.datetime(2026, 8, 20, 10, 0, 0, tzinfo=dt.timezone.utc))
    make_run(root, f"{ok_utc.name}/work/decoy2", declared=(["g1_pong"], ["rust"], 1),
             present=(["g1_pong"], ["rust"], 1),
             started=dt.datetime(2026, 8, 20, 10, 0, 0, tzinfo=dt.timezone.utc))
    found, pruned = M.find_run_directories(root)
    check(nested in found, "a run nested inside a wrapper directory is found")
    check(not any("decoy" in str(p) for p in found),
          "neither agent-authored decoy is mistaken for a run")
    check(any(p.name == "work" for p in pruned),
          "the pruned agent-authored directories are returned, not discarded")

    audits, _ = M.audit_tree_with_skips(root)
    nested_audit = next(a for a in audits if a.run_dir == nested)
    check(nested_audit.name == f"archive-w/{nested.name}",
          "a nested run is reported by its path relative to the swept root (rule 12)")
    check(nested_audit.severity == "ok", "and the nested run measures clean")

    # MUTANT: the pre-repair discovery, one level with iterdir(). It must lose the
    # nested run - a green audit over a tree it never opened is the defect (#126).
    original = M.find_run_directories
    M.find_run_directories = lambda rd: (
        [d for d in sorted(Path(rd).iterdir()) if M.is_run_directory(d)], [])
    mutant_audits, _ = M.audit_tree_with_skips(root)
    M.find_run_directories = original
    check(len(mutant_audits) == len(audits) - 1
          and not any(a.run_dir == nested for a in mutant_audits),
          "MUTANT: the one-level iterdir sweep silently drops the nested run")

    print("\naudit - the address is an input to the check (AGENTS.md rule 12)")
    nothing = tmp / "no-such-runs"
    rc = M.main(["audit", "--runs-dir", str(nothing)])
    check(rc == 2, "a runs-dir that does not exist exits 2, not 0")
    blank = tmp / "blank-runs"
    blank.mkdir()
    rc = M.main(["audit", "--runs-dir", str(blank)])
    check(rc == 2, "a runs-dir holding zero run directories exits 2, not 0")

    rc = M.main(["audit", "--runs-dir", str(root)])
    check(rc == 1, "a tree containing real defects exits 1")

    only_clean = tmp / "clean-runs"
    only_clean.mkdir()
    shutil.copytree(ok_utc, only_clean / ok_utc.name)
    shutil.copytree(ok_local, only_clean / ok_local.name)
    rc = M.main(["audit", "--runs-dir", str(only_clean)])
    check(rc == 0, "POSITIVE CONTROL: a tree of consistent runs exits 0")


def test_harness_uses_it() -> None:
    """The repair is only real if `cmd_build` goes through it.

    A green module with the old line still in the harness is the shape AGENTS.md calls a
    mechanism that runs, reports success, and measures nothing - the tests above would
    stay green forever while every run kept losing its manifest.
    """
    print("\nthe harness write path")
    wg = HERE.parent / "wholegame.py"
    src = wg.read_text()
    check('"suite.json").write_text' not in src,
          "wholegame.py no longer writes suite.json unconditionally")
    check("write_manifest(run_dir" in src,
          "wholegame.py builds its manifest through manifest.write_manifest")

    # BOTH harnesses, and asserted rather than promised. eval/AGENTS.md: two similar
    # policies in two files is how #100 came back.
    rn = HERE.parent / "runner.py"
    rsrc = rn.read_text()
    check('"suite.json").write_text' not in rsrc,
          "runner.py no longer writes suite.json unconditionally")
    check("write_manifest(run_dir" in rsrc,
          "runner.py builds its manifest through manifest.write_manifest")
    rc = subprocess.run([sys.executable, "-m", "py_compile", str(rn)],
                        capture_output=True, check=False)
    check(rc.returncode == 0, f"runner.py compiles ({rc.stderr.decode()[:200]})")

    # The spec-change manifest shape has `trials` and `started_at` but no matrix, so it
    # must stay LEGACY_SHAPE rather than becoming an error the day it gained a timestamp.
    tmp2 = Path(tempfile.mkdtemp(prefix="manifest-runner-shape-"))
    try:
        d = tmp2 / "core-2026-08-20T10-00-00"
        (d / "trials").mkdir(parents=True)
        M.write_manifest(d, {"suite": "core", "template": "/t", "trials": 2,
                             "started_at": "2026-08-20T10:00:04+00:00"}, quiet=True)
        check(codes(M.audit_run(d)) == {"LEGACY_SHAPE"},
              "a spec-change manifest stays LEGACY_SHAPE, not an error")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # `tools/` is not a package and `cmd_build` loads this module by path. Exercise that
    # exact mechanism rather than trusting that the import line is spelled correctly -
    # the address is an input to the check (AGENTS.md rule 12).
    # This check earned its place immediately: the first version of the loader in
    # `cmd_build` did not register the module in `sys.modules`, and `@dataclass` resolves
    # annotations through `sys.modules[cls.__module__]`, so the import died with
    # `AttributeError: 'NoneType' object has no attribute '__dict__'`. Every test above
    # was green, because they import the module normally.
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_manifest", HERE / "manifest.py")
    mod = ilu.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    check(callable(getattr(mod, "write_manifest", None)),
          "manifest.py loads by path the way cmd_build loads it")
    check("sys.modules[_mspec.name]" in src,
          "cmd_build registers the module before exec_module")

    rc = subprocess.run([sys.executable, "-m", "py_compile", str(wg)],
                        capture_output=True, check=False)
    check(rc.returncode == 0, f"wholegame.py compiles ({rc.stderr.decode()[:200]})")

    # THE TWO ROLLING WRITERS (task 63). Same reasoning as the two above: a green module
    # with the old line still in the caller is a mechanism that runs, reports success and
    # measures nothing.
    fs = HERE.parent / "judge" / "field_sweep.py"
    fsrc = fs.read_text()
    for name in ("GATES.json", "SEQUENTIAL.json", "REPRODUCIBILITY.json"):
        check(f'_atomic(a.out / "{name}"' not in fsrc,
              f"field_sweep.py no longer writes {name} through the overwriting _atomic")
    check(fsrc.count("_write_summary(a.out") == 3,
          "all three field_sweep modes write their summary through _write_summary")
    check("write_rolling_json" in fsrc,
          "field_sweep.py routes its summaries through manifest.write_rolling_json")
    check("sys.modules[spec.name] = mod" in fsrc,
          "field_sweep.py registers manifest in sys.modules before exec_module")
    rc = subprocess.run([sys.executable, "-m", "py_compile", str(fs)],
                        capture_output=True, check=False)
    check(rc.returncode == 0, f"field_sweep.py compiles ({rc.stderr.decode()[:200]})")

    be = HERE / "backup_evidence.py"
    bsrc = be.read_text()
    for name in ("MANIFEST.sha256", "DEST_ONLY.txt", "MEASURED.json"):
        check(f'"{name}").write_text' not in bsrc,
              f"backup_evidence.py no longer overwrites {name} in place")
    check(bsrc.count("MF.write_rolling") == 3,
          "all three destination records go through manifest.write_rolling*")
    rc = subprocess.run([sys.executable, "-m", "py_compile", str(be)],
                        capture_output=True, check=False)
    check(rc.returncode == 0, f"backup_evidence.py compiles ({rc.stderr.decode()[:200]})")

    # The summary names field_sweep writes and the ones judge_ledger recognises are
    # asserted equal AT IMPORT, not compared here by eye. Importing the module is what
    # runs that assertion, so this check is the address of the check (rule 12).
    rc = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); import field_sweep as F, judge_ledger as L; "
         "assert set(F.SUMMARIES.values()) == {f'{s}.json' for s in L.SUMMARY_STEMS}"
         % str(HERE.parent / "judge")],
        capture_output=True, check=False)
    check(rc.returncode == 0,
          f"field_sweep's summary names match judge_ledger's ({rc.stderr.decode()[:200]})")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="manifest-selftest-"))
    try:
        test_write(tmp)
        test_rolling(tmp)
        test_audit(tmp)
        test_harness_uses_it()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILS:
        print(f"FAILED: {len(FAILS)}")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("all expectations hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
