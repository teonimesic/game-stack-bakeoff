#!/usr/bin/env python3
"""Does a stored SPEC-CHANGE record still say what the command said - on BOTH streams?

This is `judge/capture_selftest.py` pointed at the other harness. `judge/static.py` stores
what the GRADER ran; `runner.py` stores what the AGENT's own gate said, in
`self_verify` and `holdout`, and until #114 it stored it the same broken way:

    sh()  ->  (p.returncode, p.stdout + p.stderr)          # runner.py, one merged buffer
    rec["self_verify"] = {..., "tail": vout[-4000:]}
    rec["holdout"]     = {..., "tail": hout[-5000:]}

THE INPUT THAT PRODUCES THE DEFECT IS ONE STREAM ARBITRARILY LARGER THAN THE OTHER.
Measured over the stored spec-change `trials/*.json` on 2026-08-23: of 26 records with
`self_verify` exit 0, the 2 that do not contain the recipe's own completion line are exactly
the 2 whose tail hit the 4000 cap, and both are the Rust template - `cargo-nextest` writes
its progress to stderr, so stdout is what the merge throws away (FINDINGS #100/#103).

A mutant that deletes the truncation cannot manufacture that input; only a VARIANT - a real
child writing 10 KB to one stream and one line to the other - can (AGENTS.md rule 15). Both
halves run here, and the variants are written to run against the UNFIXED `sh()` too, so the
defect is measured before it is repaired rather than after (AGENTS.md rule 14).

Run:

    python3 runner_capture_selftest.py                       # variants + mutants, ~10 s
    python3 runner_capture_selftest.py --submission rust=../template ...

The second form is the positive control: it runs the real `just verify` - the suites'
`verify_cmd` - in the given template, through `runner.sh`, and reports per stack, from ONE
execution, whether the completion line survives the pre-#114 policy and whether it survives
the current one. One execution, two renderings, so the comparison cannot be confounded by a
rebuild.

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import argparse
import os
import shlex
import sys
import textwrap
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import runner  # noqa: E402

FAILS: list[str] = []
CHECKS = 0

#: The line every template's `verify` recipe ends with, on stdout.
TOKEN = "✅ verify passed"

#: What `self_verify` and `holdout` capped their merged buffer at, before the repair.
PRE114_SELF_VERIFY_CAP = 4000
PRE114_HOLDOUT_CAP = 5000


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# Reading a record of either shape, and running `sh()` of either shape.
#
# Written as explicit fallbacks rather than assumptions, so this file can be run against
# the UNFIXED function and produce clean failures instead of a TypeError. The fallback
# gives the old shape the benefit of the doubt: it asks "is the line in the record AT
# ALL", which is the fair question.
# --------------------------------------------------------------------------- #

def stdout_of(d: dict[str, Any]) -> str:
    return d["stdout"] if "stdout" in d else d.get("tail", "")


def stderr_of(d: dict[str, Any]) -> str:
    return d["stderr"] if "stderr" in d else d.get("tail", "")


def pre114(out: str, err: str, cap: int = PRE114_SELF_VERIFY_CAP) -> str:
    """Exactly what `run_trial` stored before this repair: one merged buffer, last `cap`."""
    return (out + err)[-cap:]


class Ran:
    """One `sh()` call, normalised across both shapes of its return value.

    `text` is the string the parsers were handed before the repair and must still be
    handed after it. `record` is what `run_trial` writes to the trial JSON.
    """

    def __init__(self, r: Any, cap: int = PRE114_SELF_VERIFY_CAP) -> None:
        self.legacy = isinstance(r, tuple)
        if self.legacy:                                   # pre-#114: (code, merged text)
            self.code, self.text = r
            self.out, self.err, self.note = "", "", ""
            self.record: dict[str, Any] = {"exit": self.code, "tail": self.text[-cap:]}
        else:
            self.code, self.text = r.code, r.text
            self.out, self.err, self.note = r.out, r.err, r.note
            self.record = r.record()


def py(code: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(textwrap.dedent(code))}"


def run(code: str, timeout_s: int = 120, cap: int = PRE114_SELF_VERIFY_CAP) -> Ran:
    return Ran(runner.sh(py(code), HERE, timeout_s=timeout_s), cap=cap)


#: ~10 KB on one stream, one short line on the other. 10 KB is not a magic number: it is
#: comfortably past any per-stream budget AND past both pre-#114 caps, which is the only
#: property that matters.
FLOOD_LINE = "E" * 79
FLOOD_N = 128


def flood_stderr_one_stdout_line(cap: int = PRE114_SELF_VERIFY_CAP) -> Ran:
    return run(f"""
        import sys
        for _ in range({FLOOD_N}):
            sys.stderr.write({FLOOD_LINE!r} + '\\n')
        sys.stderr.write('LAST-ERR-LINE\\n')
        sys.stdout.write({TOKEN!r} + '\\n')
    """, cap=cap)


def flood_stdout_one_stderr_line() -> Ran:
    return run(f"""
        import sys
        sys.stdout.write('FIRST-OUT-LINE\\n')
        for _ in range({FLOOD_N}):
            sys.stdout.write({FLOOD_LINE!r} + '\\n')
        sys.stderr.write('the one line on stderr\\n')
    """)


# --------------------------------------------------------------------------- #
# Variants
# --------------------------------------------------------------------------- #

def test_one_stream_cannot_starve_the_other() -> None:
    print("\n[a flood on one stream must not discard the other]")

    r = flood_stderr_one_stdout_line()
    expect("self_verify: a stderr flood keeps the single stdout line",
           TOKEN in stdout_of(r.record),
           f"{len(r.out) or len(r.text)} chars out, {len(r.err)} chars err")
    expect("...and this is the case the OLD policy got wrong",
           TOKEN not in pre114(r.out or r.text, r.err),
           "if this passes, the variant is not reproducing #100 and proves nothing")
    expect("the flooded stream is still there too", "LAST-ERR-LINE" in stderr_of(r.record))

    h = flood_stderr_one_stdout_line(cap=PRE114_HOLDOUT_CAP)
    expect("holdout: the 5000-char cap loses it too, and the repair keeps it",
           TOKEN not in pre114(h.out or h.text, h.err, PRE114_HOLDOUT_CAP)
           and TOKEN in stdout_of(h.record),
           "a larger cap is a moved boundary, not a fix")

    r2 = flood_stdout_one_stderr_line()
    expect("a stdout flood keeps the single stderr line",
           "the one line on stderr" in stderr_of(r2.record),
           f"{len(r2.out) or len(r2.text)} chars out, {len(r2.err)} chars err")
    expect("...and the stderr line is not attributed to stdout",
           "the one line on stderr" not in r2.record.get("stdout", ""))


def test_streams_stay_identifiable() -> None:
    print("\n[which stream a line came from is a recorded fact, not an inference]")
    r = run("""
        import sys
        sys.stdout.write('ONLY-ON-STDOUT\\n')
        sys.stderr.write('ONLY-ON-STDERR\\n')
    """)
    d = r.record
    expect("the record has a stdout field", "stdout" in d, sorted(d))
    expect("the record has a stderr field", "stderr" in d, sorted(d))
    expect("stdout content is in the stdout field", "ONLY-ON-STDOUT" in d.get("stdout", ""))
    expect("stderr content is in the stderr field", "ONLY-ON-STDERR" in d.get("stderr", ""))
    expect("stderr content is NOT in the stdout field",
           "ONLY-ON-STDERR" not in d.get("stdout", ""))
    expect("stdout content is NOT in the stderr field",
           "ONLY-ON-STDOUT" not in d.get("stderr", ""))


def test_what_is_kept_and_what_is_dropped() -> None:
    print("\n[the sampling policy: head and tail of each stream, the middle counted]")
    r = flood_stdout_one_stderr_line()
    d = r.record
    s = stdout_of(d)
    head, tail = runner.STREAM_HEAD_CHARS, runner.STREAM_TAIL_CHARS
    expect("the head of a flooded stream survives", "FIRST-OUT-LINE" in s)
    expect("the tail of a flooded stream survives", s.rstrip().endswith(FLOOD_LINE),
           repr(s[-30:]))
    expect("what was dropped is stated as a number, not implied",
           "elided" in s and str(max(len(r.out) - head - tail, 0)) in s,
           repr(s[head:head + 120]))
    expect("the full length of each stream is recorded",
           d.get("stdout_chars") == len(r.out) and d.get("stderr_chars") == len(r.err),
           f"{d.get('stdout_chars')} vs {len(r.out)}")
    budget = head + tail
    expect("the stored sample is bounded per stream",
           len(s) <= budget + 200, f"{len(s)} stored, budget {budget}")
    expect("the budget is PER STREAM, so neither is charged for the other",
           len(stdout_of(d)) + len(stderr_of(d)) > budget
           or len(r.out) + len(r.err) <= budget,
           "a shared budget would cap the pair, not each")


def test_short_output_is_verbatim() -> None:
    print("\n[nothing is sampled when nothing needs to be]")
    r = run("""
        import sys
        sys.stdout.write('one\\ntwo\\n')
        sys.stderr.write('three\\n')
    """)
    d = r.record
    expect("short stdout is stored byte for byte", stdout_of(d) == r.out, repr(stdout_of(d)))
    expect("short stderr is stored byte for byte", stderr_of(d) == r.err, repr(stderr_of(d)))
    expect("no elision marker appears when nothing was elided",
           "elided" not in stdout_of(d) + stderr_of(d))


def test_boundary_exactly_at_budget() -> None:
    print("\n[the boundary: a stream exactly at budget is untouched]")
    budget = runner.STREAM_HEAD_CHARS + runner.STREAM_TAIL_CHARS
    at = runner.capture_fields("A" * budget, "")
    over = runner.capture_fields("A" * (budget + 1), "")
    expect("exactly at budget: kept whole", len(at["stdout"]) == budget, str(len(at["stdout"])))
    expect("one character over: elided, and it says so", "elided" in over["stdout"])


def test_the_parsers_read_exactly_what_they_read_before() -> None:
    print("\n[parse_test_counts and parse_skipped are handed the same bytes as before]")
    # nextest writes its Summary to STDERR, which is the whole of #100. A banner on
    # stdout makes the merged order matter.
    r = run("""
        import sys
        sys.stdout.write('   Compiling sim v0.1.0\\n')
        sys.stderr.write('    Starting 7 tests across 2 binaries\\n')
        sys.stderr.write('Summary [   0.017s] 7 tests run: 7 passed, 2 skipped\\n')
    """)
    merged = (r.out + r.err) if not r.legacy else r.text
    expect("`text` is byte-for-byte the old merged buffer", r.text == merged,
           f"{len(r.text)} vs {len(merged)}")
    expect("parse_test_counts is unmoved",
           runner.parse_test_counts(r.text) == runner.parse_test_counts(merged) == (7, 7),
           str(runner.parse_test_counts(r.text)))
    expect("parse_skipped is unmoved",
           runner.parse_skipped(r.text) == runner.parse_skipped(merged) == 2,
           str(runner.parse_skipped(r.text)))
    expect("...and the stored record keeps the stdout line separately",
           "Compiling sim" in r.record.get("stdout", ""),
           repr(r.record.get("stdout", "")[:60]))


def test_existing_contract_is_unchanged() -> None:
    print("\n[everything the previous capture guaranteed still holds]")
    r = run("""
        import sys
        sys.stdout.write('on stdout\\n')
        sys.stderr.write('on stderr\\n')
        sys.exit(3)
    """)
    expect("exit code is the child's", r.code == 3, str(r.code))
    expect("`text` still reads stdout-then-stderr for the parsers",
           r.text == "on stdout\non stderr\n", repr(r.text))
    expect("the record still carries the exit code", r.record.get("exit") == 3,
           str(r.record.get("exit")))

    missing = Ran(runner.sh("this-binary-does-not-exist-xyz", HERE, timeout_s=60))
    expect("a command the shell cannot find is non-zero, not an exception",
           missing.code != 0, str(missing.code))
    expect("...and what the shell said about it is kept",
           "not found" in (missing.text or "").lower(), repr(missing.text[:80]))


def test_timeout_keeps_what_was_printed() -> None:
    print("\n[a timeout: the harness's note is recorded WITHOUT eating the output]")
    r = run("""
        import sys, time
        sys.stdout.write('printed before the hang\\n')
        sys.stdout.flush()
        time.sleep(60)
    """, timeout_s=2)
    expect("exit is 124", r.code == 124, str(r.code))
    expect("`text` is the note alone, exactly as before the repair",
           r.text.startswith("TIMEOUT"), repr(r.text[:40]))
    expect("the note names the timeout, in its own field",
           "TIMEOUT" in (r.record.get("note") or ""), repr(r.record.get("note")))
    expect("the harness's words are not attributed to a stream the command never wrote",
           "TIMEOUT" not in stdout_of(r.record) + stderr_of(r.record),
           repr(stdout_of(r.record)[:60]))


def test_readers_of_the_old_shape() -> None:
    print("\n[a stored record from before the repair stays readable, and says so]")
    old = {"exit": 0, "passed": True, "tail": "some merged output"}
    new = runner.capture_fields("O\n", "E\n")
    expect("stored_output reads the old shape",
           runner.stored_output(old) == "some merged output", runner.stored_output(old))
    expect("stored_output reads the new shape",
           "O" in runner.stored_output(new) and "E" in runner.stored_output(new))
    expect("stored_stdout on an old record is None, not an empty string",
           runner.stored_stdout(old) is None, repr(runner.stored_stdout(old)))
    expect("stored_stdout on a new record is the stdout sample",
           runner.stored_stdout(new) == "O\n", repr(runner.stored_stdout(new)))


def test_one_policy_not_two() -> None:
    print("\n[the two harnesses share ONE capture policy, not two similar ones]")
    sys.path.insert(0, str(HERE / "judge"))
    try:
        import static                                       # noqa: PLC0415
    except Exception as ex:                                 # noqa: BLE001
        expect("judge/static.py imports, so the policies can be compared", False, repr(ex))
        return
    # `static.py` loads `runner.py` under its own module name, so the two are separate
    # module OBJECTS and identity is not the available test. The property that matters is
    # narrower and checkable: every one of these names must be DEFINED IN runner.py, i.e.
    # `static.py` must not carry a second implementation of any of them.
    home = str(Path(runner.__file__).resolve())
    for name in ("_sample_stream", "capture_fields", "stored_stdout", "stored_output"):
        fn = getattr(static, name, None)
        expect(f"static.{name} is defined in runner.py, not a second copy",
               fn is not None and Path(fn.__code__.co_filename).resolve() == Path(home),
               getattr(fn, "__code__", None) and fn.__code__.co_filename)
    expect("the budgets are the same numbers",
           (static.STREAM_HEAD_CHARS, static.STREAM_TAIL_CHARS)
           == (runner.STREAM_HEAD_CHARS, runner.STREAM_TAIL_CHARS),
           f"{static.STREAM_HEAD_CHARS}/{static.STREAM_TAIL_CHARS}")
    grader = static.Cmd("verify", ["just", "verify"], 0, 1.0, out="A" * 9000, err="B\n")
    harness = runner.Sh(0, out="A" * 9000, err="B\n")
    gk = {k: v for k, v in grader.to_dict().items() if k in runner.CAPTURE_FIELDS}
    hk = {k: v for k, v in harness.record().items() if k in runner.CAPTURE_FIELDS}
    expect("a grader record and a harness record capture identically", gk == hk,
           f"{sorted(gk)} vs {sorted(hk)}")
    expect("every capture key is present in both", set(gk) == set(runner.CAPTURE_FIELDS),
           f"{sorted(gk)} vs {sorted(runner.CAPTURE_FIELDS)}")


# --------------------------------------------------------------------------- #
# Mutants: can these checks fail?
# --------------------------------------------------------------------------- #

def mutants() -> None:
    """Each mutant removes one mechanism; at least one expectation must turn red."""
    print("\n[mutants: a check that cannot fail is worse than absent]")
    budget = runner.STREAM_HEAD_CHARS + runner.STREAM_TAIL_CHARS

    original = runner._sample_stream

    # 1. no truncation at all
    runner._sample_stream = lambda text, *a, **k: text        # type: ignore[assignment]
    d = runner.capture_fields("A" * 12000, "B" * 12000)
    caught = len(d["stdout"]) > budget + 200
    runner._sample_stream = original                          # type: ignore[assignment]
    expect("mutant 'no truncation' is caught by the bounded-sample check", caught,
           f"{len(d['stdout'])} chars stored")

    # 2. the pre-#114 rule, reinstated on the runner's own record
    orig_record = runner.Sh.record

    def merged(self: runner.Sh, **extra: Any) -> dict[str, Any]:
        return {"exit": self.code, "tail": (self.out + self.err)[-4000:], **extra}

    runner.Sh.record = merged                                 # type: ignore[assignment]
    real = flood_stderr_one_stdout_line()
    lost = TOKEN not in stdout_of(real.record)
    runner.Sh.record = orig_record                            # type: ignore[assignment]
    expect("mutant 'merge the streams again' loses the stdout line, and is caught", lost,
           "this is the defect #100 recorded, reproduced on demand in the runner")

    # 3. the harness's note poured back into a stream
    orig_fields = runner.capture_fields

    def note_into_stdout(out: str, err: str, note: str = "",
                         sample: Any = None) -> dict[str, Any]:
        d = orig_fields(out, err, note, sample) if sample else orig_fields(out, err, note)
        d["stdout"] = (d["stdout"] or "") + (note or "")
        d["note"] = None
        return d

    runner.capture_fields = note_into_stdout                  # type: ignore[assignment]
    t = runner.Sh(124, out="printed\n", err="", note="TIMEOUT after 2s")
    rec = t.record()
    caught_note = "TIMEOUT" in rec.get("stdout", "") and not rec.get("note")
    runner.capture_fields = orig_fields                       # type: ignore[assignment]
    expect("mutant 'attribute the harness's note to stdout' is caught", caught_note,
           repr(rec.get("stdout")))


# --------------------------------------------------------------------------- #
# The positive control: the real gate, per stack
# --------------------------------------------------------------------------- #

def submissions(pairs: list[str]) -> None:
    """Run the real `verify_cmd` in each template and report both renderings."""
    print(f"\n[positive control: `just verify` through runner.sh in {len(pairs)} template(s)]")
    rows = []
    for pair in pairs:
        stack, _, spec = pair.partition("=")
        repo, _, target = spec.partition(":")
        os.environ.setdefault("STARTER_SILENT_LAUNCH", "1")
        os.environ.setdefault("STARTER_NO_RAISE", "1")
        r = Ran(runner.sh("just verify", Path(repo), timeout_s=2400,
                          target_dir=Path(target) if target else None))
        out, err = (r.out, r.err) if not r.legacy else (r.text, "")
        rows.append((stack, r.code, len(out), len(err),
                     TOKEN in pre114(out, err), TOKEN in stdout_of(r.record)))
        print(f"  {stack:<7} exit={r.code} out={len(out)} err={len(err)} "
              f"pre114={'yes' if rows[-1][4] else 'NO '} now={'yes' if rows[-1][5] else 'NO '}",
              flush=True)
    print(f"\n  {'stack':<8}{'exit':>5}{'stdout':>9}{'stderr':>9}{'pre-#114':>10}{'now':>6}")
    for stack, code, no, ne, before, after in rows:
        print(f"  {stack:<8}{code:>5}{no:>9}{ne:>9}"
              f"{'yes' if before else 'NO':>10}{'yes' if after else 'NO':>6}")
    for stack, code, _no, _ne, _before, after in rows:
        if code == 0:
            expect(f"{stack}: a green verify records its own completion line", after)
        else:
            expect(f"{stack}: verify exited {code}, so there is no completion line to keep",
                   True, "not a positive control for this arm - report it, do not close on it")


def guarded(fn: Any) -> None:
    """Run one block; a missing attribute is a FAILED expectation, never a traceback.

    Against the UNFIXED `sh()` half of this file cannot even resolve its names, and a
    traceback there would stop the run before the variant that measures the defect. An
    error is recorded as a failure - fail-closed, never skipped.
    """
    try:
        fn()
    except Exception as ex:                                  # noqa: BLE001
        expect(f"{fn.__name__} completed", False, f"{type(ex).__name__}: {ex}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission", action="append", default=[], metavar="STACK=PATH[:TARGET]",
                    help="run the real `just verify` here; TARGET sets CARGO_TARGET_DIR")
    ap.add_argument("--no-variants", action="store_true",
                    help="skip the synthetic variants (use with --submission)")
    a = ap.parse_args()

    if not a.no_variants:
        for t in (test_one_stream_cannot_starve_the_other,
                  test_streams_stay_identifiable,
                  test_what_is_kept_and_what_is_dropped,
                  test_short_output_is_verbatim,
                  test_boundary_exactly_at_budget,
                  test_the_parsers_read_exactly_what_they_read_before,
                  test_existing_contract_is_unchanged,
                  test_timeout_keeps_what_was_printed,
                  test_readers_of_the_old_shape,
                  test_one_policy_not_two,
                  mutants):
            guarded(t)
    if a.submission:
        submissions(a.submission)

    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED:")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("runner capture selftest: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
