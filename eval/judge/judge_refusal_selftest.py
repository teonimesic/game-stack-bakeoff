#!/usr/bin/env python3
"""Does the retired generalist judge REFUSE a game it has no brief for?

`judge.GAME_BRIEF` holds 3 entries and the suite has 4 games. Until tasks/221 the
missing fourth rendered `"(unknown game)"` as the brief and answered all 13 criteria
about a game nobody described - a placeholder-briefed tier-3 record that reads as a
measurement. `evaluate.py --game g4_platformer --with-legacy-judge` was the exposed
path: the CLI refuses by argparse choices, and the 2026-08-25 class guard
(`evaluate.assert_legacy_judge_allowed`) answers "game or scene", not "which game".

What this file checks, and how:

  THE REFUSAL IS A RECORD  judge() returns a verdict with `refused: true` - distinct
                           from the empty-pack refusal and from evaluate()'s skipped
                           marker - and evaluate() records it, because its completeness
                           gate needs judge.json present and tiers 1-2 are valid
                           whatever tier 3 answers. The fields are asserted as
                           LITERALS, so a drift in shape or in the criterion count
                           (total == 13) is a red row, not a quieter verdict.
  NOTHING IS SPENT         the refusal returns before the pack is built and before any
                           model call; spies over `judge.build_pack` and
                           `judge._run_claude` must stay silent. The submission path
                           passed below does not exist, so a guard that moved below
                           the pack build reads as an exception, not as a refusal.
  BRIEFED GAMES UNMOVED    every GAME_BRIEF entry still renders its own brief; the
                           direct index in `_brief` raises on an unbriefed game rather
                           than rendering a placeholder (the backstop behind the
                           guard), and the CLI still refuses by argparse choices.
  THE CENSUS               the extraction that partitions stored judge.json files into
                           real rounds / skipped markers / refusals / unparseable /
                           other is pinned on a fixture tree whose answer is written
                           as literals - including a wrapper directory holding a run,
                           which is the treatment every new walker over runs/ gets
                           (eval/AGENTS.md). With --runs-root the same census runs
                           over the stored tree and asserts the guard moves nothing:
                           every real round sits on a briefed game, so 0 stored
                           conclusions change. A record that cannot be parsed is
                           COUNTED (unparseable), never silently excluded, and the
                           corpus arm goes red over any nonzero count - a census that
                           reports the readable remainder as clean is the fail-open
                           shape rule 7 names.

  MUTANTS                  GAME_BRIEF extended with the unbriefed game (the guard
                           stops firing and the record reads as a measurement again);
                           the placeholder restored under the direct index; both must
                           go red.

    python3 eval/judge/judge_refusal_selftest.py                  # offline, no corpus
    python3 eval/judge/judge_refusal_selftest.py --runs-root DIR  # + the stored census

The corpus arm reads eval/runs/, which is gitignored: absent, it prints NOT ASKED
rather than a count; present but holding no judge.json, it exits 2 rather than
report 0 (rule 12 - the address is an input to the check); holding a record it
cannot parse, it goes red rather than report the rest as clean.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge  # noqa: E402

FAILS: list[str] = []
CHECKS = 0

#: The game the suite has and the brief table does not. Also the only difference
#: between the exposed path and the CLI surface, which refuses it by argparse choices.
UNBRIEFED = "g4_platformer"

#: Written by hand, not read from judge.ALL_CRITERIA: the count is part of the stored
#: record shape (every skipped marker and every real round says 13), so a criterion
#: added to the retired judge is a change this file is meant to notice.
TOTAL = 13


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


@contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


# --------------------------------------------------------------------------- #
# the refusal is a record, and nothing is spent
# --------------------------------------------------------------------------- #

SPEND: list[str] = []


def _spy_spend(*a, **kw):
    SPEND.append(a[0] if a else "?")
    raise AssertionError(f"the refusal path spent something: {SPEND}")


def refusal_record(game: str) -> dict:
    """judge() on an unbriefed game, with both spend paths wired to fail loudly.

    The paths do not exist on purpose. A guard relocated below `build_pack` makes this
    helper raise FileNotFoundError; one relocated below the model call trips the spy.
    Either is a red row about the guard's position, not a refusal.
    """
    SPEND.clear()
    with patched(judge, "build_pack", _spy_spend):
        with patched(judge, "_run_claude", _spy_spend):
            return judge.judge(Path("/nonexistent/submission"), Path("/nonexistent/starter"),
                               game, submission_id="selftest")


def test_the_refusal_is_a_record() -> None:
    print("\n[the refusal is a recorded verdict with literal fields]")
    rec = refusal_record(UNBRIEFED)
    expect("the guard answers a RECORD, not an exception", isinstance(rec, dict))
    expect("refused is true", rec.get("refused") is True, str(rec.get("refused")))
    expect("usable is false", rec.get("usable") is False, str(rec.get("usable")))
    expect("the verdict is distinct from the empty-pack refusal and the skipped "
           "marker", rec.get("refused") is True and "skipped" not in rec
           and "error" in rec, str(sorted(rec)))
    expect("passed is the literal 0", rec.get("passed") == 0, str(rec.get("passed")))
    expect(f"total is the literal {TOTAL}", rec.get("total") == TOTAL, str(rec.get("total")))
    expect("score is the literal 0.0", rec.get("score") == 0.0, str(rec.get("score")))
    expect("cost is the literal 0.0", rec.get("cost_usd") == 0.0, str(rec.get("cost_usd")))
    expect("no criteria were answered", rec.get("criteria") == [], str(rec.get("criteria")))
    expect("instability is None, not 0.0", rec.get("instability") is None,
           str(rec.get("instability")))
    expect("no pack was built", rec.get("pack") is None, str(rec.get("pack")))
    expect("the error names the game and the table",
           UNBRIEFED in str(rec.get("error")) and "GAME_BRIEF" in str(rec.get("error")),
           str(rec.get("error")))
    expect("nothing was spent on the way to the refusal", not SPEND, str(SPEND))

    # An id that is not a game at all is the same refusal - the guard reads the table,
    # not the suite.
    rec9 = refusal_record("g9_nothing")
    expect("an invented id is refused by the same guard", rec9.get("refused") is True
           and rec9.get("total") == TOTAL)


def test_briefed_games_are_unmoved() -> None:
    print("\n[briefed games still render their own brief]")
    for game, brief in judge.GAME_BRIEF.items():
        text = judge._brief(game, judge.ALL_CRITERIA, 3, 2)
        expect(f"{game}: the brief is the game's own", brief in text)
        expect(f"{game}: no placeholder anywhere in it", "(unknown game)" not in text)
    expect("the brief table holds 3 games", len(judge.GAME_BRIEF) == 3,
           str(sorted(judge.GAME_BRIEF)))

    # THE BACKSTOP. judge() refuses before _brief can run, so a missing key here means
    # judge() was bypassed; the direct index raises rather than render a placeholder.
    raised = ""
    try:
        judge._brief(UNBRIEFED, judge.ALL_CRITERIA, 3, 2)
    except KeyError as e:
        raised = type(e).__name__
    expect("an unbriefed game cannot reach a placeholder brief", raised == "KeyError",
           f"got {raised or 'no raise'}")


def test_the_cli_still_refuses() -> None:
    print("\n[the CLI surface refuses the same set]")
    import subprocess

    r = subprocess.run(
        [sys.executable, str(HERE / "judge.py"), "--submission", "x", "--starter", "y",
         "--game", UNBRIEFED],
        capture_output=True, text=True, check=False)
    expect(f"judge.py --game {UNBRIEFED} exits 2 at argparse",
           r.returncode == 2 and "invalid choice" in r.stderr,
           f"exit {r.returncode}: {r.stderr.strip()[:160]}")


# --------------------------------------------------------------------------- #
# the census, pinned on fixtures whose answer is written here
# --------------------------------------------------------------------------- #

def census(root: Path) -> dict:
    """Partition every judge.json under `root`, at any depth, by CONTENT.

    A filename census counts evaluate()'s skipped markers as rounds of whatever game
    the trial id names - the cleanup-16 pass's own first extraction reported 8
    g4_platformer rounds that way, and every one of them was a marker. The split is
    content-shaped: `refused` is judge()'s refusal, `skipped` is evaluate()'s marker,
    `usable` is a real round, and anything else is counted as other rather than
    silently folded into a neighbouring class. A file that cannot be parsed is
    counted as `unparseable` and returned - dropping it here would let a corpus of
    unreadable records read as a clean, empty census.
    """
    kinds: Counter = Counter()
    games: Counter = Counter()
    unbriefed: list[str] = []
    for f in sorted(root.rglob("judge.json")):
        try:
            d = json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            kinds["unparseable"] += 1
            continue
        if d.get("refused"):
            kinds["refused"] += 1
        elif d.get("skipped"):
            kinds["skipped"] += 1
        elif d.get("usable"):
            kinds["round"] += 1
            games[str(d.get("game"))] += 1
            if d.get("game") not in judge.GAME_BRIEF:
                unbriefed.append(str(f))
        else:
            kinds["other"] += 1
    return {"files": sum(kinds.values()), "kinds": dict(kinds), "games": dict(games),
            "rounds": kinds["round"], "briefed": kinds["round"] - len(unbriefed),
            "unbriefed": len(unbriefed), "unbriefed_paths": unbriefed,
            "skipped": kinds["skipped"], "refused": kinds["refused"],
            "unparseable": kinds["unparseable"], "other": kinds["other"]}


def fixture_tree() -> Path:
    """Six judge.json files in five classes, one of them behind a wrapper directory.

    The unbriefed round is the pre-guard shape: usable, scored, on a game the table
    does not brief - the record this repair exists to make impossible. The last file
    is not JSON at all: the census must count it as unparseable rather than drop it,
    because a census that scores only the records it could read is the fail-open
    shape rule 7 names.
    """
    root = Path(tempfile.mkdtemp(prefix="judge-refusal-fx-"))
    real = {"tier": "judge", "usable": True, "game": "g1_pong", "model": "sonnet",
            "submission_id": "fx", "passed": 7, "total": TOTAL, "score": 7 / TOTAL,
            "instability": 0.0, "criteria": [], "cost_usd": 1.0}
    marker = {"tier": "judge", "skipped": True, "usable": False, "passed": 0,
              "total": TOTAL, "score": 0.0, "criteria": [], "instability": None,
              "cost_usd": 0.0}
    pre_guard = {**real, "game": UNBRIEFED, "submission_id": "fx-pre"}
    refused = {"tier": "judge", "refused": True, "usable": False, "error": "no entry",
               "game": UNBRIEFED, "passed": 0, "total": TOTAL, "score": 0.0,
               "criteria": [], "instability": None, "pack": None, "cost_usd": 0.0}
    other = {"tier": "judge", "error": "empty pack", "usable": False, "passed": 0,
             "total": TOTAL, "score": 0.0, "criteria": [], "instability": None,
             "cost_usd": 0.0}
    for rel, blob in (
        ("run-a/artifacts/t0/eval/judge.json", real),            # briefed round
        ("run-a/artifacts/t1/eval/judge.json", marker),          # skipped marker
        ("wrap/run-b/artifacts/t0/eval/judge.json", pre_guard),  # unbriefed round
        ("wrap/run-b/artifacts/t1/eval/judge.json", refused),    # the refusal
        ("wrap/run-b/artifacts/t2/eval/judge.json", other),      # empty-pack refusal
        ("wrap/run-b/artifacts/t3/eval/judge.json",
         '{"tier": "judge", "usable": '),                        # truncated write
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(blob if isinstance(blob, str) else json.dumps(blob))
    return root


EXPECTED_FIXTURE = {"files": 6, "rounds": 2, "briefed": 1, "unbriefed": 1,
                    "skipped": 1, "refused": 1, "unparseable": 1, "other": 1}


def test_the_census_extraction() -> None:
    print("\n[the census extraction, pinned on literals]")
    root = fixture_tree()
    got = census(root)
    for key, want in EXPECTED_FIXTURE.items():
        expect(f"fixture {key} == {want}", got[key] == want, f"got {got[key]}")
    expect("the fixture's per-game split is g1_pong 1, g4_platformer 1",
           got["games"] == {"g1_pong": 1, UNBRIEFED: 1}, str(got["games"]))


def corpus_arm(runs_root: Path) -> int:
    print(f"\n[the stored census, re-derived with the guard in mind: {runs_root}]")
    got = census(runs_root)
    if got["files"] == 0:
        print(f"  no judge.json under {runs_root} - wrong address or empty tree; "
              f"refusing to report 0", file=sys.stderr)
        return 2
    print(f"  judge.json files          {got['files']}")
    print(f"  real rounds               {got['rounds']}  ({got['games']})")
    print(f"  skipped markers           {got['skipped']}")
    print(f"  refused verdicts          {got['refused']}")
    print(f"  unparseable records       {got['unparseable']}")
    print(f"  other usable=false        {got['other']}")
    expect("every record the census counted was readable - an unreadable record is a "
           "counted class, never a silent exclusion, and a nonzero count is red",
           got["unparseable"] == 0, f"{got['unparseable']} unparseable")
    expect("every real round sits on a briefed game - the guard moves nothing",
           got["unbriefed"] == 0, "unbriefed: " + "; ".join(got["unbriefed_paths"][:4]))
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("judge refusal selftest (stored census): OK")
    return 0


def test_the_corpus_arm_fails_closed() -> None:
    """The red half of the fail-closed row: a corpus with an unreadable record is red.

    Before that row existed, corpus_arm() printed OK over a corpus whose every
    judge.json was malformed - 69 files, 0 rounds, 0 anything, unbriefed 0: green. The
    probe below replays that corpus in miniature and requires the arm to go red; with
    the row removed, the arm returns 0 over the same tree and this row fails instead.
    """
    print("\n[the corpus arm fails closed on unreadable records]")
    root = Path(tempfile.mkdtemp(prefix="judge-refusal-bad-"))
    p = root / "run/artifacts/t0/eval/judge.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"tier": "judge", "usable": ')
    got = census(root)
    expect("the census counts the malformed record rather than dropping it",
           got["unparseable"] == 1 and got["files"] == 1, str(got))
    saved = list(FAILS)
    status = corpus_arm(root)
    grew = len(FAILS) - len(saved)
    FAILS[:] = saved
    expect("a corpus whose record cannot be parsed goes RED, never OK",
           status == 1 and grew == 1, f"corpus_arm returned {status}; {grew} red row(s)")


# --------------------------------------------------------------------------- #
# mutants
# --------------------------------------------------------------------------- #

def mutants() -> None:
    """Each removes one mechanism the rows above name; the row must go red."""
    print("\n[mutants: can these checks fail?]")

    # 1. THE TABLE IS EXTENDED. The repair this file exists to pin is "refuse, do not
    #    extend" - and if the table gains the unbriefed game, the guard stops firing
    #    and the record reads as a measurement again. That is the ticket-title defect,
    #    so the mutant replays it with the model stubbed: 13 passing criteria, score
    #    1.0, cost 0.
    def canned(*_a, **_kw):
        return ({"structured_output": {"criteria": [
                    {"id": cid, "evidence": "x" * 30, "reason": "r", "passed": True}
                    for cid, _q in judge.ALL_CRITERIA]}}, "")

    extended = dict(judge.GAME_BRIEF)
    extended[UNBRIEFED] = "A platformer. A runner crosses pits and high ledges."
    SPEND.clear()
    with patched(judge, "GAME_BRIEF", extended):
        with patched(judge, "build_pack",
                     lambda *a, **k: {"files_in_pack": 3, "frames": 0}):
            with patched(judge, "_run_claude", canned):
                rec = judge.judge(Path("/nonexistent/submission"),
                                  Path("/nonexistent/starter"), UNBRIEFED,
                                  submission_id="mutant")
    caught = rec.get("refused") is not True and rec.get("usable") is True \
        and rec.get("score") == 1.0
    expect("mutant 'GAME_BRIEF gains the unbriefed game' produces a record that reads "
           "as a measurement, and is caught", caught,
           f"refused={rec.get('refused')} usable={rec.get('usable')} "
           f"score={rec.get('score')}")

    # 2. THE PLACEHOLDER IS RESTORED. `__missing__` reinstates the old `.get` default
    #    under the new direct index: the backstop row must go red.
    class Placeholder(dict):
        def __missing__(self, key):
            return "(unknown game)"

    with patched(judge, "GAME_BRIEF", Placeholder(judge.GAME_BRIEF)):
        text = judge._brief(UNBRIEFED, judge.ALL_CRITERIA, 3, 2)
    caught = "(unknown game)" in text
    expect("mutant 'the placeholder brief is restored' renders it again, and is caught",
           caught)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="run the stored census over this tree (gitignored; pass the "
                         "main checkout's eval/runs from a worktree)")
    a = ap.parse_args()

    test_the_refusal_is_a_record()
    test_briefed_games_are_unmoved()
    test_the_cli_still_refuses()
    test_the_census_extraction()
    test_the_corpus_arm_fails_closed()
    mutants()

    root = a.runs_root
    if root is None:
        default = HERE.parent / "runs"
        root = default if default.is_dir() else None
    if root is not None and Path(root).is_dir():
        status = corpus_arm(Path(root))
        if status:
            return status
    else:
        print("\n[the stored census: NOT ASKED - no eval/runs here]")

    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("judge refusal selftest: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
