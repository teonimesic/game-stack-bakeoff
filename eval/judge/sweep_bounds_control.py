#!/usr/bin/env python3
"""Can a judge sweep still be stopped, and can it still be stopped by a MONEY figure?

    python3 judge/sweep_bounds_control.py

`field_sweep.py` used to refuse a call when `spent + --per-call-budget > --max-cost`,
truncating a sweep at about 48 of a *list-price valuation of tokens* on an account where
no money moves per token (#159). The bounds are now `--max-rounds` and `--max-wall-min`.

Removing a limit is the easy half and it fails silently: a sweep with no working bound
looks exactly like a sweep that was never bounded. So this asks both questions.

| direction | what it establishes |
|---|---|
| **green** | an unbounded sweep runs every planned round and records `stopped_by: None` |
| **red, rounds** | `--max-rounds N` stops at N and says so in the summary |
| **red, wall** | `--max-wall-min` stops on elapsed time and says so in the summary |
| **mutant** | with `may_start` neutered, the sweep runs past its bound and this control goes red — so the rows above are not passing on a check that cannot fail |
| **variant** | no money quantity participates in any stop decision, read off the source |

The variant is the one a mutant cannot ask. A mutant deletes the mechanism the check
names; only a variant asks whether the check still passes on input it mishandles — and
the input that matters here is a *re-introduced money ceiling* sitting beside a working
round bound, where every row above would stay green.
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import time
import tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import field_sweep  # noqa: E402

SOURCE = HERE / "field_sweep.py"

#: A stop decision denominated in money. `spent`/`cost` compared against a ceiling, or
#: any surviving `--max-cost`. CLOSED CLASS: the comparison operators and the two names
#: the old ceiling was spelled with.
MONEY_STOP = re.compile(
    r"(spent\s*\+[^\n]*[<>]|[<>]=?\s*a\.max_cost|max_cost\s*[<>]|--max-cost)")


def executable_lines(src: str) -> list[tuple[int, str]]:
    """The source with every comment and every string literal removed.

    A DOCSTRING IS PROSE, NOT A DECISION. `field_sweep.py` documents the money ceiling it
    replaced, in the module docstring and in `Bounds`, and a line-oriented grep cannot
    tell that paragraph from a live `if`. Stripping comments and strings by tokenising is
    the only reading that survives the module explaining itself - and this module has to
    explain itself, or the next reader re-derives the ceiling.
    """
    out: dict[int, list[str]] = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING, tokenize.NL,
                        tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            continue
        if tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            continue
        out.setdefault(tok.start[0], []).append(tok.string)
    return [(n, " ".join(parts)) for n, parts in sorted(out.items())]


def _drive(bounds: field_sweep.Bounds, plan: int, per_round_s: float = 0.0) -> int:
    """Run `plan` rounds through the bound, exactly as every mode does. Returns rounds run."""
    for i in range(plan):
        if not bounds.may_start(f"round{i}"):
            break
        bounds.started()
        if per_round_s:
            time.sleep(per_round_s)
    return bounds.rounds


def _mutant_may_start(self, what: str) -> bool:  # noqa: ARG001
    """The mutant: a bound that never refuses."""
    return True


def main() -> int:
    rows: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, ok, detail))

    # --- GREEN: no bound, every planned round runs -------------------------
    b = field_sweep.Bounds(None, None)
    ran = _drive(b, 7)
    summary: dict = {}
    b.record(summary, planned=7)
    check("unbounded sweep runs all 7 planned rounds", ran == 7, f"ran={ran}")
    check("unbounded sweep records stopped_by=None", summary["stopped_by"] is None,
          repr(summary["stopped_by"]))
    check("the summary carries the bounds it ran under",
          summary["bounds"]["planned_rounds"] == 7
          and summary["bounds"]["rounds_started"] == 7,
          repr(summary["bounds"]))

    # --- RED: --max-rounds stops the sweep ---------------------------------
    b = field_sweep.Bounds(3, None)
    ran = _drive(b, 7)
    summary = {}
    b.record(summary, planned=7)
    check("--max-rounds 3 stops a 7-round plan at 3", ran == 3, f"ran={ran}")
    check("--max-rounds records stopped_by=max_rounds",
          summary["stopped_by"] == "max_rounds", repr(summary["stopped_by"]))

    # --- RED: --max-wall-min stops the sweep -------------------------------
    # 0.0 minutes is not "no bound": it is a bound already exceeded, and it must refuse
    # the FIRST round rather than falling through to unbounded. `None` is the third
    # value, tested above, and conflating the two is the fail-open direction.
    b = field_sweep.Bounds(None, 0.0)
    ran = _drive(b, 7)
    summary = {}
    b.record(summary, planned=7)
    check("--max-wall-min 0 refuses the first round", ran == 0, f"ran={ran}")
    check("--max-wall-min records stopped_by=max_wall_min",
          summary["stopped_by"] == "max_wall_min", repr(summary["stopped_by"]))
    check("wall-min 0 and wall-min None are different",
          field_sweep.Bounds(None, 0.0).may_start("x") is False
          and field_sweep.Bounds(None, None).may_start("x") is True)

    # --- MUTANT: neuter may_start, the red rows must go red ----------------
    real = field_sweep.Bounds.may_start
    field_sweep.Bounds.may_start = _mutant_may_start
    try:
        mutant_rounds = _drive(field_sweep.Bounds(3, None), 7)
        mutant_wall = _drive(field_sweep.Bounds(None, 0.0), 7)
    finally:
        field_sweep.Bounds.may_start = real
    check("MUTANT (may_start always true) runs past --max-rounds",
          mutant_rounds == 7, f"ran={mutant_rounds}, expected 7")
    check("MUTANT runs past --max-wall-min", mutant_wall == 7,
          f"ran={mutant_wall}, expected 7")
    check("the mutant was reverted", field_sweep.Bounds(3, None).may_start("x") is True
          and _drive(field_sweep.Bounds(3, None), 7) == 3)

    # --- VARIANT: no money quantity decides a stop -------------------------
    src = SOURCE.read_text()
    code = executable_lines(src)
    money_stops = [f"{n}: {ln}" for n, ln in code if MONEY_STOP.search(ln)]
    check("no money quantity participates in a stop decision", not money_stops,
          "; ".join(money_stops[:3]))
    check("MONEY_STOP can still fire (it is not a dead regex)",
          bool(MONEY_STOP.search("if spent + a.per_call_budget > a.max_cost:")))
    # THE STRIPPER MUST NOT STRIP EVERYTHING. A tokeniser that returned nothing would
    # make the row above green on any source at all - the vacuous pass this project keeps
    # meeting. Pin it on a case whose answer is known in advance.
    check("stripping keeps executable lines", len(code) > 150, f"{len(code)} lines")
    demo = executable_lines('x = 1  # spent + 1 > max_cost\n"spent + 1 > max_cost"\n'
                            'if spent + b > max_cost:\n    pass\n')
    check("stripping drops a comment and a docstring, keeps the `if`",
          [ln for _, ln in demo if MONEY_STOP.search(ln)] != []
          and len([ln for _, ln in demo if MONEY_STOP.search(ln)]) == 1,
          repr(demo))

    # --- the retired flag REFUSES rather than being silently unknown -------
    # Deleting it would give argparse's generic "unrecognized arguments", which reads as a
    # typo and invites a workaround. A named refusal that says what replaced it is the
    # difference between a reader who stops and a reader who guesses.
    proc = subprocess.run(
        [sys.executable, str(SOURCE), "--run", "x", "--games", "g1_pong",
         "--aspects", "fun", "--out", "/tmp/sweep_bounds_control", "--max-cost", "60"],
        capture_output=True, text=True)
    check("--max-cost is refused, exit 2", proc.returncode == 2,
          f"exit={proc.returncode}")
    check("the refusal names what replaced it",
          "--max-rounds" in proc.stderr and "--max-wall-min" in proc.stderr,
          proc.stderr.strip()[:120])
    check("the refusal happens before any work",
          not os.path.exists("/tmp/sweep_bounds_control"))

    # --- the address is an input to the check ------------------------------
    check(f"field_sweep.py was actually read ({len(src)} bytes)", len(src) > 5000)
    check("Bounds is the only stop gate the modes call",
          src.count("bounds.may_start(") >= 4, f"{src.count('bounds.may_start(')} call sites")

    bad = [r for r in rows if not r[1]]
    for name, ok, detail in rows:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"   [{detail}]" if detail and not ok else ""))
    print(f"\n{len(rows) - len(bad)}/{len(rows)} pins green")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
