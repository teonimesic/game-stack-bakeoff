#!/usr/bin/env python3
"""Does a stored command record still say what the command said - on BOTH streams?

THE INPUT THAT PRODUCES THE DEFECT IS ONE STREAM ARBITRARILY LARGER THAN THE OTHER.

`Cmd.to_dict` used to store `(stdout + stderr)[-4000:]`, so a command that floods one
stream discards the whole of the other. It is not a hypothetical: over 68 stored
`programmatic.json` records, 17 of 62 green `just verify` runs do not contain the recipe's
own `verify passed` line, 15 of 16 of them on the Rust arm, because `cargo-nextest` writes
its progress to stderr (FINDINGS #99/#100). No score moved - the exit code is read from the
process - but the audit trail was lost, and lost in a STACK-CORRELATED way that nobody chose.

A mutant that deletes the truncation cannot manufacture that input; only a VARIANT - a real
child writing 10 KB to one stream and one line to the other - can (AGENTS.md rule 15). Both
halves run here: the variants below, then a mutant sweep that must turn at least one of them
red, because a check that cannot fail is worse than absent.

Run:

    python3 judge/capture_selftest.py                        # variants + mutants, ~10 s
    python3 judge/capture_selftest.py --submission rust=/path/to/worktree ...

The second form is the positive control: it runs the real `just verify` in the given
submissions, and reports - per stack, from ONE execution - whether the recipe's completion
line survives the pre-#100 policy and whether it survives the current one. One execution,
two renderings, so the comparison cannot be confounded by a rebuild.

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import static  # noqa: E402

FAILS: list[str] = []
CHECKS = 0

#: The line every starter's `verify` recipe ends with, on stdout.
TOKEN = "✅ verify passed"


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# Reading a record of either shape.
#
# Written as an explicit fallback rather than an assumption, so this file can be run
# against the UNFIXED function and produce clean failures instead of a KeyError. The
# fallback gives the old shape the benefit of the doubt: it asks "is the line in the
# record AT ALL", which is the fair question.
# --------------------------------------------------------------------------- #

def stdout_of(d: dict[str, Any]) -> str:
    return d["stdout"] if "stdout" in d else d.get("tail", "")


def stderr_of(d: dict[str, Any]) -> str:
    return d["stderr"] if "stderr" in d else d.get("tail", "")


def pre100(out: str, err: str) -> str:
    """Exactly what `Cmd.to_dict` stored before this repair: one merged buffer, last 4000."""
    return (out + err)[-4000:]


def py(code: str) -> list[str]:
    return [sys.executable, "-c", textwrap.dedent(code)]


HERE = Path(__file__).resolve().parent


def run(code: str, timeout_s: int = 120) -> static.Cmd:
    return static.run(HERE, "control", py(code), timeout_s=timeout_s)


#: ~10 KB on one stream, one short line on the other. 10 KB is not a magic number: it is
#: comfortably past any per-stream budget, which is the only property that matters.
FLOOD_LINE = "E" * 79
FLOOD_N = 128


def flood_stderr_one_stdout_line() -> static.Cmd:
    return run(f"""
        import sys
        for _ in range({FLOOD_N}):
            sys.stderr.write({FLOOD_LINE!r} + '\\n')
        sys.stderr.write('LAST-ERR-LINE\\n')
        sys.stdout.write({TOKEN!r} + '\\n')
    """)


def flood_stdout_one_stderr_line() -> static.Cmd:
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

    c = flood_stderr_one_stdout_line()
    d = c.to_dict()
    expect("a stderr flood keeps the single stdout line", TOKEN in stdout_of(d),
           f"{len(c.out)} chars out, {len(c.err)} chars err")
    expect("...and this is the case the OLD policy got wrong",
           TOKEN not in pre100(c.out, c.err),
           "if this passes, the variant is not reproducing #100 and proves nothing")
    expect("the flooded stream is still there too", "LAST-ERR-LINE" in stderr_of(d))

    c2 = flood_stdout_one_stderr_line()
    d2 = c2.to_dict()
    expect("a stdout flood keeps the single stderr line",
           "the one line on stderr" in stderr_of(d2),
           f"{len(c2.out)} chars out, {len(c2.err)} chars err")
    expect("...and the flooded stdout keeps its own last line",
           "the one line on stderr" not in stdout_of(d2) or "stdout" not in d2,
           "the stderr line must not be attributed to stdout")


def test_streams_stay_identifiable() -> None:
    print("\n[which stream a line came from is a recorded fact, not an inference]")
    c = run("""
        import sys
        sys.stdout.write('ONLY-ON-STDOUT\\n')
        sys.stderr.write('ONLY-ON-STDERR\\n')
    """)
    d = c.to_dict()
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
    c = flood_stdout_one_stderr_line()
    d = c.to_dict()
    s = stdout_of(d)
    expect("the head of a flooded stream survives", "FIRST-OUT-LINE" in s)
    expect("the tail of a flooded stream survives", s.rstrip().endswith(FLOOD_LINE),
           repr(s[-30:]))
    expect("what was dropped is stated as a number, not implied",
           "elided" in s and str(len(c.out) - static.STREAM_HEAD_CHARS
                                 - static.STREAM_TAIL_CHARS) in s,
           repr(s[static.STREAM_HEAD_CHARS:static.STREAM_HEAD_CHARS + 120]))
    expect("the full length of the stream is recorded",
           d.get("stdout_chars") == len(c.out) and d.get("stderr_chars") == len(c.err),
           f"{d.get('stdout_chars')} vs {len(c.out)}")
    budget = static.STREAM_HEAD_CHARS + static.STREAM_TAIL_CHARS
    expect("the stored sample is bounded per stream",
           len(s) <= budget + 200, f"{len(s)} stored, budget {budget}")
    expect("the budget is PER STREAM, so neither is charged for the other",
           len(stdout_of(d)) + len(stderr_of(d)) > budget
           or len(c.out) + len(c.err) <= budget,
           "a shared budget would cap the pair, not each")


def test_short_output_is_verbatim() -> None:
    print("\n[nothing is sampled when nothing needs to be]")
    c = run("""
        import sys
        sys.stdout.write('one\\ntwo\\n')
        sys.stderr.write('three\\n')
    """)
    d = c.to_dict()
    expect("short stdout is stored byte for byte", stdout_of(d) == c.out, repr(stdout_of(d)))
    expect("short stderr is stored byte for byte", stderr_of(d) == c.err, repr(stderr_of(d)))
    expect("no elision marker appears when nothing was elided",
           "elided" not in stdout_of(d) + stderr_of(d))


def test_boundary_exactly_at_budget() -> None:
    print("\n[the boundary: a stream exactly at budget is untouched]")
    budget = static.STREAM_HEAD_CHARS + static.STREAM_TAIL_CHARS
    at = static.Cmd("control", ["x"], 0, 0.0, out="A" * budget, err="")
    over = static.Cmd("control", ["x"], 0, 0.0, out="A" * (budget + 1), err="")
    expect("exactly at budget: kept whole", len(stdout_of(at.to_dict())) == budget,
           str(len(stdout_of(at.to_dict()))))
    expect("one character over: elided, and it says so",
           "elided" in stdout_of(over.to_dict()))


def test_existing_contract_is_unchanged() -> None:
    print("\n[everything the previous capture guaranteed still holds]")
    c = run("""
        import sys
        sys.stdout.write('on stdout\\n')
        sys.stderr.write('on stderr\\n')
        sys.exit(3)
    """)
    expect("exit code is the child's", c.code == 3, str(c.code))
    expect("`tail` still reads stdout-then-stderr for the parsers",
           c.tail == "on stdout\non stderr\n", repr(c.tail))
    expect("wall seconds recorded", c.seconds >= 0.0, str(c.seconds))
    expect("resource fields still populated", c.peak_rss_mb is not None
           and c.cpu_seconds is not None, f"{c.peak_rss_mb} {c.cpu_seconds}")

    missing = static.run(HERE, "control", ["/nonexistent/binary-xyz"])
    expect("a binary that does not exist is 127", missing.code == 127, str(missing.code))
    expect("...and the harness's own words are not attributed to the child",
           missing.note and not missing.out and not missing.err, repr(missing.note))
    expect("...and `tail` still carries that explanation",
           "could not run" in missing.tail, repr(missing.tail[:60]))


def test_timeout_keeps_what_was_printed() -> None:
    print("\n[a timeout: the harness's note is recorded WITHOUT eating the output]")
    c = run("""
        import sys, time
        sys.stdout.write('printed before the hang\\n')
        sys.stdout.flush()
        time.sleep(60)
    """, timeout_s=2)
    d = c.to_dict()
    expect("exit is 124", c.code == 124, str(c.code))
    expect("the note names the timeout", "TIMEOUT" in (d.get("note") or ""),
           repr(d.get("note")))
    expect("`tail` is the note alone, exactly as before the repair",
           c.tail.startswith("TIMEOUT"), repr(c.tail[:40]))
    expect("but what the child printed is still in the record",
           "printed before the hang" in stdout_of(d), repr(stdout_of(d)[:60]))


def test_readers_of_the_old_shape() -> None:
    print("\n[a stored record from before the repair stays readable, and says so]")
    old = {"name": "verify", "argv": ["just", "verify"], "exit": 0, "seconds": 1.0,
           "tail": "some merged output"}
    new = static.Cmd("verify", ["just", "verify"], 0, 1.0, out="O\n", err="E\n").to_dict()
    expect("stored_output reads the old shape",
           static.stored_output(old) == "some merged output", static.stored_output(old))
    expect("stored_output reads the new shape",
           "O" in static.stored_output(new) and "E" in static.stored_output(new))
    expect("stored_stdout on an old record is None, not an empty string",
           static.stored_stdout(old) is None, repr(static.stored_stdout(old)))
    expect("stored_stdout on a new record is the stdout sample",
           static.stored_stdout(new) == "O\n", repr(static.stored_stdout(new)))


# --------------------------------------------------------------------------- #
# Mutants: can these checks fail?
# --------------------------------------------------------------------------- #

def mutants() -> None:
    """Each mutant removes one mechanism; at least one expectation must turn red."""
    print("\n[mutants: a check that cannot fail is worse than absent]")
    c_out, c_err = "A" * 12000, "B" * 12000
    cmd = static.Cmd("control", ["x"], 0, 0.0, out=c_out, err=c_err)
    budget = static.STREAM_HEAD_CHARS + static.STREAM_TAIL_CHARS

    original = static._sample_stream

    # 1. no truncation at all
    static._sample_stream = lambda text, *a, **k: text          # type: ignore[assignment]
    d = cmd.to_dict()
    caught = len(d["stdout"]) > budget + 200
    static._sample_stream = original                            # type: ignore[assignment]
    expect("mutant 'no truncation' is caught by the bounded-sample check", caught,
           f"{len(d['stdout'])} chars stored")

    # 2. the pre-#100 rule, reinstated
    orig_to_dict = static.Cmd.to_dict

    def merged(self: static.Cmd) -> dict[str, Any]:
        return {"name": self.name, "argv": self.argv, "exit": self.code,
                "seconds": round(self.seconds, 1), "tail": (self.out + self.err)[-4000:]}

    static.Cmd.to_dict = merged                                 # type: ignore[assignment]
    real = flood_stderr_one_stdout_line()
    lost = TOKEN not in stdout_of(real.to_dict())
    static.Cmd.to_dict = orig_to_dict                           # type: ignore[assignment]
    expect("mutant 'merge the streams again' loses the stdout line, and is caught", lost,
           "this is the defect #100 recorded, reproduced on demand")


# --------------------------------------------------------------------------- #
# The positive control: real gates, real submissions
# --------------------------------------------------------------------------- #

def submissions(pairs: list[str]) -> int:
    """Run the real `just verify` in each submission and report both renderings."""
    print(f"\n[positive control: `just verify` in {len(pairs)} submission(s)]")
    env = dict(os.environ)
    # The trial environment owns the launch discipline (wholegame.py): silent, no raise.
    env["STARTER_SILENT_LAUNCH"] = "1"
    env["STARTER_NO_RAISE"] = "1"
    rows = []
    for pair in pairs:
        stack, _, spec = pair.partition("=")
        repo, _, target = spec.partition(":")
        e = dict(env)
        if target:
            e["CARGO_TARGET_DIR"] = target
        c = static.run(Path(repo), "verify", ["just", "verify"], timeout_s=2400, env=e)
        d = c.to_dict()
        rows.append((stack, c.code, len(c.out), len(c.err),
                     TOKEN in pre100(c.out, c.err), TOKEN in stdout_of(d)))
        print(f"  {stack:<7} exit={c.code} out={len(c.out)} err={len(c.err)} "
              f"pre100={'yes' if rows[-1][4] else 'NO '} now={'yes' if rows[-1][5] else 'NO '}"
              f"  ({c.seconds:.0f}s)", flush=True)
    print(f"\n  {'stack':<8}{'exit':>5}{'stdout':>9}{'stderr':>9}"
          f"{'pre-#100':>10}{'now':>6}")
    for stack, code, no, ne, before, after in rows:
        print(f"  {stack:<8}{code:>5}{no:>9}{ne:>9}"
              f"{'yes' if before else 'NO':>10}{'yes' if after else 'NO':>6}")
    for stack, code, _no, _ne, _before, after in rows:
        if code == 0:
            expect(f"{stack}: a green verify records its own completion line", after)
        else:
            expect(f"{stack}: verify exited {code}, so there is no completion line to keep",
                   True, "not a positive control for this arm - report it, do not close on it")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission", action="append", default=[], metavar="STACK=PATH[:TARGET]",
                    help="run the real `just verify` here; TARGET sets CARGO_TARGET_DIR")
    ap.add_argument("--no-variants", action="store_true",
                    help="skip the synthetic variants (use with --submission)")
    a = ap.parse_args()

    if not a.no_variants:
        test_one_stream_cannot_starve_the_other()
        test_streams_stay_identifiable()
        test_what_is_kept_and_what_is_dropped()
        test_short_output_is_verbatim()
        test_boundary_exactly_at_budget()
        test_existing_contract_is_unchanged()
        test_timeout_keeps_what_was_printed()
        test_readers_of_the_old_shape()
        mutants()
    if a.submission:
        submissions(a.submission)

    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED:")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("capture selftest: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
