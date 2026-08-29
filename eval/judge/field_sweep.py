#!/usr/bin/env python3
"""Run the specialist judges over a matrix, bounded by what is finite, gates first.

    python3 judge/field_sweep.py --run runs/wg-audio-... --games g1_pong \
        --aspects idiomatic fun --orders 2 --max-wall-min 90 --out judge-sweep/

Why this exists rather than a loop in a shell: four separate protections, each of
which this project has paid for the absence of.

1. **BOUNDS DENOMINATED IN WHAT IS ACTUALLY FINITE, RECORDED IN THE SUMMARY.** This
   used to be `--max-cost 60`, refusing a call when `spent + --per-call-budget > 60`
   — a sweep truncated at about 48 of *valuation* on an account where no money moves
   per token, so the threshold could not protect anything and could only cut evidence
   short (#159). The bounds are now `--max-rounds` and `--max-wall-min`, both optional
   because every mode is already finite by construction, and both written into the
   summary along with `stopped_by`, so "did this sweep stop short?" is read off the
   artifact instead of inferred from it.

2. **ONE WRITER PER ARTIFACT PATH.** Every result goes to its own file through a temp
   file and `os.replace`. Two judge processes once shared one path and produced a file
   holding two spliced JSON documents that parsed cleanly and was published (#19).

3. **GATES BEFORE RESULTS.** The sweep prints the ceiling, order-invariance and
   independence gates before any ranking, because a ranking from a judge that gives
   everything the same score, or that reorders when the presentation order changes, is
   not a result and should not be read as one.

4. **ONE DIRECTORY, ONE RUN.** Rounds accumulate into `--out` across invocations and are
   loaded back without asking where they came from, so a stored round judged from a
   different run pairs gates across two different fields and sums both into the field
   figure. `assert_out_run` refuses the mix before any mode writes or pairs, and lists
   the rounds that carry no `run` at all (they predate the provenance fields and cannot
   be checked). `field_ranks.assert_one_run` is the same question at the analysis end.

Sequential on purpose. Concurrent judge fan-out during a matrix contributed to four
trials dying on an account session limit; and there is no hurry here, because unlike a
trial a judge call can be re-run for the same money tomorrow.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import field  # noqa: E402
import tokenvalue  # noqa: E402
from aspects import ASPECTS, applicability  # noqa: E402
from judge_ledger import SUMMARY_STEMS, field_cost_usd, is_summary  # noqa: E402
from sequential import MAX_RUNS, Sampler  # noqa: E402

#: Which summary each mode writes. `judge_ledger` decides what a summary IS - a name it
#: does not recognise is read as a judge round and widens every denominator - so the two
#: spellings are ASSERTED equal at import rather than promised equal in a comment
#: (AGENTS.md rule 12: the address is an input to the check).
SUMMARIES = {"orders": "GATES.json", "sequential": "SEQUENTIAL.json",
             "repeats": "REPRODUCIBILITY.json"}
assert set(SUMMARIES.values()) == {f"{s}.json" for s in SUMMARY_STEMS}, (
    f"field_sweep writes {sorted(SUMMARIES.values())} but judge_ledger recognises "
    f"{sorted(f'{s}.json' for s in SUMMARY_STEMS)}")

HERE = Path(__file__).resolve().parent
SOURCE = Path(__file__).resolve()


class Bounds:
    """What may stop a sweep, and the record of whether anything did.

    NOTHING HERE IS DENOMINATED IN MONEY. The ceiling this replaces was
    `spent + per_call > max_cost` on a list-price valuation of tokens: it could not
    protect the resource that is actually scarce, and where it fired it truncated real
    evidence (#159, `DECISIONS.md`). Rounds and wall clock are finite; the valuation is
    not a bill.

    BOTH BOUNDS ARE OPTIONAL, and that is not a loosening. Every mode is already finite
    by construction — `--orders` plans `games x aspects x orders` calls, `--repeats`
    plans `repeats` per pair, `--sequential` is capped by `--max-runs` — so the money
    ceiling was a second bound on an already-bounded plan. These exist for the case the
    plan itself is larger than the session in front of you.

    `stopped_by` is written into the summary. No stored sweep records the ceiling it
    ran under, so answering "was this one truncated?" over the 12 summaries on disk
    meant reconstructing it from round counts. That gap closes here.
    """

    def __init__(self, max_rounds: int | None, max_wall_min: float | None) -> None:
        self.max_rounds = max_rounds
        self.max_wall_min = max_wall_min
        self.rounds = 0
        self.t0 = time.monotonic()
        self.stopped_by: str | None = None

    def wall_min(self) -> float:
        return (time.monotonic() - self.t0) / 60.0

    def may_start(self, what: str) -> bool:
        """Ask BEFORE a call. Records and prints the reason the first time it refuses."""
        if self.max_rounds is not None and self.rounds >= self.max_rounds:
            self.stopped_by = self.stopped_by or "max_rounds"
            print(f"  STOPPING before {what}: {self.rounds} rounds already run, "
                  f"--max-rounds is {self.max_rounds}", flush=True)
            return False
        if self.max_wall_min is not None and self.wall_min() >= self.max_wall_min:
            self.stopped_by = self.stopped_by or "max_wall_min"
            print(f"  STOPPING before {what}: {self.wall_min():.1f} min elapsed, "
                  f"--max-wall-min is {self.max_wall_min}", flush=True)
            return False
        return True

    def started(self) -> None:
        self.rounds += 1

    def record(self, summary: dict[str, Any], planned: int | None = None) -> None:
        summary["bounds"] = {"max_rounds": self.max_rounds,
                             "max_wall_min": self.max_wall_min,
                             "planned_rounds": planned,
                             "rounds_started": self.rounds,
                             "wall_min": round(self.wall_min(), 1)}
        summary["stopped_by"] = self.stopped_by

    def banner(self, planned: int | None) -> str:
        return (f"{planned if planned is not None else '?'} field calls planned; "
                f"--max-rounds {self.max_rounds}, --max-wall-min {self.max_wall_min}. "
                f"No bound here is denominated in money (#159).")


def _load_manifest() -> Any:
    """`tools/` is not a package, so load `manifest.py` by path, as `cmd_build` does.

    REGISTER BEFORE EXEC: `@dataclass` resolves its annotations through
    `sys.modules[cls.__module__]`, and `manifest.py` defines two. A module loaded by path
    and never registered dies at import with `AttributeError: 'NoneType' object has no
    attribute '__dict__'`.
    """
    import importlib.util as ilu
    tools = Path(__file__).resolve().parents[1] / "tools"
    spec = ilu.spec_from_file_location("_manifest", tools / "manifest.py")
    mod = ilu.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_summary(out: Path, name: str, summary: dict[str, Any]) -> None:
    """A sweep summary is a durable record of what a measurement was configured to be.

    So it is append-only, and it goes through the one module that decides what that means
    (`tools/manifest.py`). It takes the ROLLING shape, not the pinned one `suite.json`
    uses: a sweep directory accumulates rounds across invocations and its summary states
    the verdict as of the latest, so the canonical name must hold the newest record and
    the one it replaces is kept beside it as `<stem>-<stamp>.json`.

    Before this, `--repeats` run twice into one directory left exactly one
    `REPRODUCIBILITY.json`, describing the second sweep, with the first sweep's gate-0
    verdict on a set of rounds that cost real money existing nowhere (task 63).
    """
    summary["out_dir"] = out.resolve().name
    _load_manifest().write_rolling_json(out / name, summary)


def _record_cost(summary: dict[str, Any], spent: float, out: Path) -> None:
    """Two token-valuation numbers, named for the two different questions they answer.

    Both are `tokval` - the list price the tokens would carry at published API rates, on
    an account where no money moves per token (#159, `tools/tokenvalue.py`). They are kept
    because they are the only per-round resource figure the harness has, not because
    anything is owed.

    `spent` is what THIS INVOCATION generated. A round already on disk contributes 0 to it
    on purpose (see `_judge_round`), so on a resumed sweep it is not the valuation of the
    field and never was.

    It used to be stored alone, under the name `measured_cost_usd`. Three live documents
    read that name as spend: 21.05 tokval was published as the cost of ten judge calls
    worth 31.66, and the same field's four earlier rounds - 10.61 of architecture and
    audio, written eight minutes before the sweep resumed - were invisible. Five of the
    twelve stored sweep directories carry the same shape, 69.93 tokval in total - read
    2026-08-29 by `python3 judge/judge_ledger.py --tree runs/`. FINDINGS #121.

    THE FIX IS NOT A BIGGER NUMBER, IT IS TWO NAMED ONES. Re-attributing carried rounds to
    today's invocation would break the one counter here that has never been wrong. What
    was wrong was publishing an invocation counter under a name that reads as a bill.
    `judge_ledger.py` audits the pair over stored sweeps and computes the second one here,
    so the ledger and the harness cannot drift into two accountings again.
    """
    summary["charged_to_ceiling_usd"] = round(spent, 2)
    summary["field_cost_usd"] = round(field_cost_usd(str(out))[1], 2)


def _print_totals(spent: float, summary: dict[str, Any], bounds: "Bounds") -> None:
    """The closing line of every mode. Token counts stay; the money vocabulary does not."""
    print(f"\nthis invocation generated {tokenvalue.tag(spent)}; "
          f"rounds stored here are worth "
          f"{tokenvalue.tag(summary['field_cost_usd'])}")
    print(f"bounds: {summary['bounds']}, stopped_by={summary['stopped_by']}")
    print(tokenvalue.DEFINITION)


#: Paths whose contents do not outlive the thing that wrote them. Kept in sync with
#: `wholegame.assert_work_root_usable`, which refuses the same set for TRIAL work trees.
_EPHEMERAL = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")


def warn_rounds_without_provenance(out: Path) -> list[str]:
    """Stored rounds that cannot say what they saw.

    Every round written from 2026-08-22 carries `run` and a `provenance` block. Earlier
    ones do not, and two of the missing fields turned out to matter within days: `run`
    (a game names four fields in different states of repair) and `files_opened` (the only
    thing that bounded #83). A round without them is not wrong - it is unfalsifiable about
    its own inputs, which is the same defect as an aggregate without its scope.
    """
    old = []
    for f in sorted(out.glob("*.json")):
        # Not `f.name == "GATES.json"`: three modes write three different summaries, and
        # from 2026-08-23 each keeps its superseded copies beside it (task 63). One
        # predicate, shared with the ledger, rather than the name this function happened
        # to be written next to.
        if is_summary(f.name):
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if "submissions" not in d:
            continue
        missing = [k for k in ("run", "provenance", "files_opened") if not d.get(k)]
        if missing:
            old.append(f"{f.name}: no {', '.join(missing)}")
    return old


def stored_round_run(out: Path) -> dict[str, str | None]:
    """Each stored round in `out` -> the run it was judged from; None when it says none.

    Rounds written since 2026-08-22 carry top-level `run` (#80's fix at the source);
    earlier ones predate the field and are reported as None, never as a guess.

    A file is a round by SHAPE - it carries `submissions` - and a summary by NAME, via
    `judge_ledger.is_summary`, the one predicate the ledger audits sweeps with. Reading
    the three summary names here instead would be a second list that the next summary
    name silently falsifies (#38's shape; the SUMMARIES assert above holds the spellings
    this file writes equal to the ledger's, not to a third copy).
    """
    runs: dict[str, str | None] = {}
    for f in sorted(out.glob("*.json")):
        if is_summary(f.name):
            continue
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(d, dict) or "submissions" not in d:
            continue
        runs[f.name] = d.get("run") or None
    return runs


def assert_out_run(out: Path, run: str) -> list[str]:
    """REFUSE before any round is written or paired when a stored round names another run.

    Rounds accumulate into `--out` across invocations BY DESIGN (the rolling summary,
    task 63), and the resume path loads them without asking where they came from: the
    `[have]` path reads the file, the gates pair on game and aspect equality alone, and
    `field_cost_usd` sums the whole directory. So one foreign round in the directory
    pairs order-invariance and reproducibility gates across two different fields, sums
    both into the field figure, and hands `field_ranks` a directory that pools two
    games' work under one submission id (#70 - and a game is not a field either, #80:
    four stored `g2_tetris3d` fields in different states of repair). MEASURED to have
    happened: partial re-runs into existing directories are the #93/#120 shape.

    Returns the names of rounds carrying NO run - a third value, not a disagreement.
    They predate the provenance fields (#86) and cannot be checked against `--run`;
    refusing them would make the sweep unable to top up the tetris-judge corpus the
    withdrawn register cites. Fail closed on what a round CAN answer and answers
    differently; warn on what it cannot answer at all.
    """
    stored = stored_round_run(out)
    foreign = {name: r for name, r in stored.items() if r and r != run}
    if foreign:
        named = ", ".join(f"{n} (run {r})" for n, r in sorted(foreign.items()))
        raise SystemExit(
            f"refusing to sweep into {out}: {len(foreign)} stored round(s) were judged "
            f"from a run that is not '{run}': {named}.\n"
            f"Rounds accumulate into --out across invocations, and the gates here pair "
            f"on game and aspect alone - a second run in the directory pairs "
            f"order-invariance and reproducibility gates across two different fields, "
            f"sums both into field_cost_usd, and hands field_ranks two games' work "
            f"under one submission id (#70, #80). Use a fresh --out for this run.")
    return sorted(name for name, r in stored.items() if not r)


def assert_out_root_durable(out: Path) -> None:
    """A judge round is an artifact of record. It must not live where the OS reaps.

    THE GUARD FOR THIS ALREADY EXISTED AND DID NOT COVER THIS PATH.
    `assert_work_root_usable` refuses `$TMPDIR`, `/tmp` and `/var/folders` for trial work
    trees, is pinned in both directions, and was written after `$TMPDIR` deleted 80% of six
    submissions' toolchains between building and grading (#45). It names TRIAL WORK TREES.

    A judge sweep writes somewhere else, so the guard did not apply - and on 2026-08-17 a
    sweep worth 44 tokval was writing into a session-scoped scratch directory under
    `/private/tmp`,
    including the only copy of the evidence for the finding that gate verdicts are not
    reproducible. The session directory does not survive the session.

    That is AGENTS.md rule 6 in its general form: **a guard whose trigger names one
    mechanism does not cover the resource.** The resource is not "trial work trees", it is
    ANY ARTIFACT A FINDING WILL CITE, and it is now named as such in both places.
    """
    p = out.resolve()
    if any(str(p) == e or str(p).startswith(e.rstrip("/") + "/") for e in _EPHEMERAL):
        raise SystemExit(
            f"judge output root {p} is under a temporary directory the OS reaps.\n"
            f"A field round costs real money and is the artifact of record for any finding\n"
            f"that cites it; a session scratch directory does not survive the session.\n"
            f"MEASURED: $TMPDIR erosion destroyed 80% of six toolchains mid-measurement\n"
            f"(FINDINGS #45). Write to runs/<name>/ instead.")


def _atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def _judge_round(run: Path, game: str, aspect_id: str, seed: int, model: str,
                 budget: float, out_dir: Path,
                 allow_truncated: bool = False) -> tuple[dict[str, Any] | None, float]:
    """One round: build a freshly shuffled pack, judge it, store it.

    Returns `({submission_id: score}, cost_usd)`. The scores are **keyed by the real
    submission, never by the pack label.** The whole point of a round is that A..H are
    reshuffled, so `A` is a different submission every time; a sampler keyed on labels
    would accumulate win rates between positions rather than between submissions and
    would converge on nothing.

    THE TOKEN VALUATION IS RETURNED, not looked up by the caller. The first version left
    the caller to re-read the stored file, and the caller only did that for the sampled
    rounds - so the probe round of every aspect was run and never counted, which on a
    five-aspect run is about 22 tokval missing from the running total. A counter that
    under-reports is worse than none.
    """
    out_path = out_dir / f"{game}__{aspect_id}__seed{seed}.json"
    fresh = not out_path.exists()
    if not fresh:
        res = json.loads(out_path.read_text())
    else:
        with tempfile.TemporaryDirectory(prefix=f"pack-{game}-") as td:
            pack = Path(td) / "pack"
            try:
                field.build_pack(run, game, pack, seed, sees=ASPECTS[aspect_id].sees,
                                 blind_language=ASPECTS[aspect_id].blind_language,
                                 allow_truncated=allow_truncated)
            except RuntimeError as e:
                print(f"  [SKIP] {game}/{aspect_id}/round{seed}: {e}", flush=True)
                return None, 0.0
            t0 = time.monotonic()
            res = field.run_field(pack, aspect_id, model, budget=budget)
        res["wall_s"] = round(time.monotonic() - t0, 1)
        _atomic(out_path, res)
    # A round already on disk was generated by an earlier invocation, so its tokens must
    # not be counted again into this one's total.
    cost = float(res.get("cost_usd") or 0.0) if fresh else 0.0
    if not res.get("usable"):
        print(f"  [FAIL] {game}/{aspect_id}/round{seed}: {res.get('error')}", flush=True)
        return None, cost
    return {s["submission"]: float(s["score"]) for s in res["submissions"]}, cost


def repeats_main(a: Any) -> int:
    """Gate 0: judge the SAME field in the SAME order N times.

    `--orders` varies the presentation and `--sequential` samples until a decision
    resolves. Neither asks whether the judge agrees with ITSELF on unchanged input, and
    when that was measured by accident it turned out not to: on `audio`, whose evidence
    no repair had touched, four of eight scores moved and the ceiling verdict flipped
    from CEILING to "separates the field" between two runs of a byte-identical pack
    (FINDINGS #58).

    `field.reproducibility()` could already measure that. Nothing could PRODUCE it - the
    round index was the presentation seed, so every extra round was a different order.
    This closes that: a tool that can only find a defect by accident will not find it
    twice.

    IT ALSO REPORTS `field.separation()`, which had no caller anywhere in the tree.
    Repeats of one order are the only input that function accepts, so this mode was the
    one place able to feed it and did not - and every separation number this project has
    published was therefore computed by an ad-hoc script that died with its session. A
    function with no caller is a protocol with no code path, which is the defect this
    mode's own docstring names one paragraph up.
    """
    assert_out_root_durable(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    bounds = Bounds(a.max_rounds, a.max_wall_min)
    planned = len(a.games) * len(a.aspects) * a.repeats
    print(bounds.banner(planned) + "\n")
    summary: dict[str, Any] = {"mode": "repeats", "repeats": a.repeats,
                               "order_seed": a.repeat_seed,
                               "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    for game in a.games:
        for aspect_id in a.aspects:
            runs: list[dict[str, Any]] = []
            for i in range(a.repeats):
                if not bounds.may_start(f"{game}/{aspect_id} rep{i}"):
                    break
                out_path = (a.out / f"{game}__{aspect_id}__seed{a.repeat_seed}"
                                    f"__rep{i}.json")
                if out_path.exists():
                    res = json.loads(out_path.read_text())
                else:
                    with tempfile.TemporaryDirectory(prefix=f"pack-{game}-") as td:
                        pack = Path(td) / "pack"
                        try:
                            field.build_pack(a.run, game, pack, a.repeat_seed,
                                             allow_truncated=a.allow_truncated,
                                             sees=ASPECTS[aspect_id].sees,
                                             blind_language=ASPECTS[aspect_id].blind_language)
                        except RuntimeError as e:
                            print(f"  [SKIP] {game}/{aspect_id}: {e}"); break
                        t0 = time.monotonic()
                        bounds.started()
                        res = field.run_field(pack, aspect_id, a.model,
                                              budget=a.per_call_budget)
                    res["wall_s"] = round(time.monotonic() - t0, 1)
                    _atomic(out_path, res)
                    spent += float(res.get("cost_usd") or 0.0)
                if res.get("usable"):
                    runs.append(res)
                    c = field.ceiling(res)
                    print(f"  [rep {i}] {game}/{aspect_id} scores={c['scores']} "
                          f"modal={c['modal_fraction']} cumulative "
                          f"{tokenvalue.tag(spent)}", flush=True)
            key = f"{game}:{aspect_id}"
            pairs = [field.reproducibility(runs[i], runs[j])
                     for i in range(len(runs)) for j in range(i + 1, len(runs))]
            flips = sum(1 for r in pairs if r.get("ceiling_verdict_stable") is False)
            sep = field.separation(runs)
            summary[key] = {"runs": len(runs), "pairwise": pairs,
                            "ceiling_verdict_flips": flips,
                            "separation": sep,
                            "verdict": ("REPRODUCIBLE" if pairs and not flips
                                        and all(p.get("identical") for p in pairs)
                                        else "SCORES MOVE, verdict stable" if pairs and not flips
                                        else "NOT REPRODUCIBLE - the ceiling verdict "
                                             "flipped on unchanged input" if flips
                                        else "too few usable runs")}
            print(f"  [gate0] {key}: {summary[key]['verdict']}", flush=True)
            # PER ASPECT, NEVER POOLED ACROSS ASPECTS. `pooled_sd` pools across the eight
            # SUBMISSIONS of one aspect, which is a homogeneous population; the aspects
            # read different evidence and an SD across them would be rule 4's own example.
            print(f"  [sep]   {key}: {sep['verdict']}", flush=True)
    _record_cost(summary, spent, a.out)
    bounds.record(summary, planned)
    _write_summary(a.out, SUMMARIES["repeats"], summary)
    print("\n=== gate 0: reproducibility ===")
    print(json.dumps(summary, indent=2)[:3000])
    _print_totals(spent, summary, bounds)
    return 0


def sequential_main(a: Any) -> int:
    """The protocol `JUDGING.md` specifies: sample until the DECISION resolves.

    `--orders N` runs a fixed number of presentation orders. That measures
    order-invariance and nothing else — it cannot say whether a pair is ORDERED, TIED or
    UNRESOLVED, and those three are the verdicts the design turns on. This mode existed
    in `sequential.py`, fully self-tested, with **nothing calling it**; a protocol with
    no code path is a protocol that gets approximated by whoever reads the document next.
    """
    spent = 0.0
    bounds = Bounds(a.max_rounds, a.max_wall_min)
    planned = len(a.games) * len(a.aspects) * a.max_runs
    print(bounds.banner(planned) + "\n")
    summary: dict[str, Any] = {"mode": "sequential", "max_runs": a.max_runs,
                               "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    for game in a.games:
        for aspect_id in a.aspects:
            if not bounds.may_start(f"{game}/{aspect_id}"):
                break
            bounds.started()
            probe, cost = _judge_round(a.run, game, aspect_id, 0, a.model,
                                       a.per_call_budget, a.out)
            spent += cost
            if probe is None:
                summary[f"{game}:{aspect_id}"] = {"error": "no usable first round"}
                continue
            sampler = Sampler(labels=sorted(probe), max_runs=a.max_runs)
            sampler.observe_run(probe)

            def judge_once(i: int, game=game, aspect_id=aspect_id) -> dict | None:
                nonlocal spent
                if not bounds.may_start(f"{game}/{aspect_id} round{i}"):
                    return None
                bounds.started()
                scores, cost = _judge_round(a.run, game, aspect_id, i, a.model,
                                            a.per_call_budget, a.out)
                spent += cost
                return scores

            rep = sampler.run(judge_once)
            summary[f"{game}:{aspect_id}"] = rep
            print(f"  [seq] {game}/{aspect_id}: {rep.get('headline')} "
                  f"(rounds={rep.get('runs')}, cumulative {tokenvalue.tag(spent)})",
                  flush=True)
    _record_cost(summary, spent, a.out)
    bounds.record(summary, planned)
    _write_summary(a.out, SUMMARIES["sequential"], summary)
    print("\n=== sequential sampling ===")
    print(json.dumps(summary, indent=2)[:4000])
    _print_totals(spent, summary, bounds)
    return 0


#: A directory OUTSIDE every temp file below, holding one stored round from a run
#: nothing else names. The CLI row refuses against a path the subprocess reads for
#: itself; it is rebuilt at the start of check 7 so repeated runs are deterministic.
_REFUSAL_FIXTURE = Path(tempfile.gettempdir()) / "field_sweep_selftest_refusal"


def selftest() -> int:
    """The run guard, both directions, and that `main` still asks it first.

    Offline and free: every fixture is a written file in a temp directory, and the one
    subprocess invocation refuses before any judge call is reachable.
    """
    unmet: list[str] = []

    def check(name: str, got, want) -> None:
        ok = got == want
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}: got {got!r}" +
              ("" if ok else f" want {want!r}"))
        if not ok:
            unmet.append(name)

    def store_round(d: Path, name: str, run: str | None) -> None:
        round_ = {"aspect": "fun", "game": "g1_pong", "usable": True,
                  "submissions": [{"submission": "g1_pong__godot__t0", "score": 3}]}
        if run is not None:
            round_["run"] = run
        (d / name).write_text(json.dumps(round_))

    print("1. GREEN - a directory that does not exist yet refuses nothing")
    with tempfile.TemporaryDirectory() as td:
        fresh = Path(td) / "sweep"
        check("no stored rounds, no warning lines", assert_out_run(fresh, "wg-x"), [])
        check("the scan itself saw nothing", stored_round_run(fresh), {})

    print("2. GREEN - a stored round from THE SAME run is reused, not refused")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        store_round(d, "g1_pong__fun__seed0.json", "wg-x")
        check("matching run passes", assert_out_run(d, "wg-x"), [])
        check("and the scan read its run", stored_round_run(d),
              {"g1_pong__fun__seed0.json": "wg-x"})

    print("3. RED - a stored round from a DIFFERENT run refuses, before any round is written")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        store_round(d, "g1_pong__fun__seed0.json", "wg-other")
        try:
            assert_out_run(d, "wg-x")
            unmet.append("a foreign run in --out was not refused")
            print("  [FAIL] the sweep accepted a foreign stored round")
        except SystemExit as exc:
            msg = str(exc)
            print(f"  [ok ] refused: {msg.splitlines()[0][:70]}...")
            check("the refusal names the stored round", "g1_pong__fun__seed0.json" in msg, True)
            check("it names both runs", "wg-other" in msg and "wg-x" in msg, True)
            check("it names the remedy (a fresh --out)", "--out" in msg, True)

    print("4. VARIANT - a round with NO run is warned, not refused (the pre-#86 corpus)")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        store_round(d, "g1_pong__fun__seed0.json", "wg-x")
        store_round(d, "g1_pong__ux__seed1.json", None)
        check("matching + run-less passes, the run-less one listed",
              assert_out_run(d, "wg-x"), ["g1_pong__ux__seed1.json"])

    print("5. summaries are not rounds")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "GATES.json").write_text(json.dumps(
            {"mode": "orders", "run": "wg-foreign", "calls_usable": 3}))
        check("a summary naming a foreign run is invisible to the guard",
              assert_out_run(d, "wg-x"), [])
        check("and invisible to the scan", stored_round_run(d), {})

    print("6. WIRING - main() asks the guard before any mode can write or pair")
    src = SOURCE.read_text()
    lines = src.splitlines()

    # MAIN'S BODY ONLY. This selftest's own source names every needle below (the wiring
    # row above is made of them), so searching the whole file matches the searcher -
    # the reading must start at main's def, matched exactly, not by substring.
    main_start = next(n for n, ln in enumerate(lines, 1)
                      if ln == "def main() -> int:")

    def main_line_of(needle: str) -> int:
        """First occurrence in main's body - `a.out.mkdir(` and the needles also appear
        in `repeats_main` and in this selftest, and the wrong occurrence reads the
        wiring backwards (rule 12: the address is an input to the check)."""
        return next((n for n, ln in enumerate(lines, 1)
                     if n >= main_start and needle in ln), -1)

    guard_line = main_line_of("no_run = assert_out_run(")
    check("the guard is called exactly once, in main",
          "\n".join(lines[main_start - 1:]).count("no_run = assert_out_run("), 1)
    check("the call is before --repeats dispatch",
          0 < guard_line < main_line_of("return repeats_main(a)"), True)
    check("the call is before --sequential dispatch",
          0 < guard_line < main_line_of("return sequential_main(a)"), True)
    check("the call is before the orders mode writes anything",
          0 < guard_line < main_line_of("a.out.mkdir("), True)
    # THE CHECK MUST BE ABLE TO FAIL: the same reading against doctored source with the
    # call deleted must lose the guard line entirely, or the pin is one that cannot go red.
    doctored_lines = [ln for ln in lines if "no_run = assert_out_run(" not in ln]
    doctored_guard = next((n for n, ln in enumerate(doctored_lines, 1)
                           if "no_run = assert_out_run(" in ln), -1)
    check("MUTANT: deleting the call turns the wiring row red", doctored_guard, -1)

    print("7. CLI - the refusal happens before any work")
    if _REFUSAL_FIXTURE.exists():
        for p in _REFUSAL_FIXTURE.glob("*"):
            p.unlink()
    else:
        _REFUSAL_FIXTURE.mkdir(parents=True)
    store_round(_REFUSAL_FIXTURE, "g1_pong__fun__seed0.json", "wg-foreign")
    proc = subprocess.run(
        [sys.executable, str(SOURCE), "--run", "wg-this", "--games", "g1_pong",
         "--aspects", "fun", "--out", str(_REFUSAL_FIXTURE)],
        capture_output=True, text=True)
    check("the CLI refuses a foreign stored round, exit 1", proc.returncode == 1, True)
    check("stderr names the foreign run", "wg-foreign" in proc.stderr, True)
    check("nothing new was written before the refusal",
          sorted(p.name for p in _REFUSAL_FIXTURE.glob("*")),
          ["g1_pong__fun__seed0.json"])

    print(f"\n{len(unmet)} expectations unmet")
    for u_ in unmet:
        print(f"   UNMET: {u_}")
    return 1 if unmet else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", type=Path, default=None)
    ap.add_argument("--games", nargs="+", default=None)
    ap.add_argument("--aspects", nargs="+", default=None, choices=sorted(ASPECTS))
    ap.add_argument("--orders", type=int, default=2,
                    help="presentation orders per (game, aspect). 2 is the minimum "
                         "that can measure order-invariance at all.")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--model", default=field.DEFAULT_MODEL)
    # RETIRED, AND KEPT AS A REFUSAL RATHER THAN DELETED. An operator with the old
    # recipe in muscle memory, or a stored command line, would otherwise get argparse's
    # generic "unrecognized arguments" and reach for a workaround. It also keeps the flag
    # NAMED where a reader can find out what replaced it: `eval/findings/` records it, and
    # a document naming a flag that resolves to nothing is confidently wrong (AGENTS.md).
    # It participates in no decision - `sweep_bounds_control.py` asserts that against the
    # tokenised source.
    ap.add_argument("--max-cost", type=float, default=None,
                    help="RETIRED 2026-08-23 and refused if passed. It was a ceiling on a "
                         "list-price valuation of tokens, which nobody is charged, so it "
                         "could only truncate evidence (#159). Use --max-rounds or "
                         "--max-wall-min.")
    ap.add_argument("--max-rounds", type=int, default=None,
                    help="stop before starting round N+1. Optional: every mode is "
                         "already finite by construction, so this is for the case the "
                         "plan is larger than the session in front of you.")
    ap.add_argument("--max-wall-min", type=float, default=None,
                    help="stop starting rounds after this many minutes. Wall clock is "
                         "finite; the token valuation is not a bill (#159).")
    ap.add_argument("--per-call-budget", type=float, default=12.0,
                    help="passed to each judge as --max-budget-usd. NOT a bound on this "
                         "sweep and not checked here - it is held at its stored value so "
                         "new rounds stay comparable with the 97 already on disk, which "
                         "all ran under 12.0. See DECISIONS.md.")
    ap.add_argument("--sequential", action="store_true",
                    help="sample each (game, aspect) until every PAIR resolves or "
                         "--max-runs is reached, instead of a fixed --orders. This is "
                         "the protocol JUDGING.md specifies; --orders is a cheap "
                         "approximation of it that can only measure order-invariance.")
    ap.add_argument("--max-runs", type=int, default=MAX_RUNS,
                    help="hard cap on rounds per (game, aspect) in --sequential mode")
    ap.add_argument("--repeats", type=int, default=0, metavar="N",
                    help="REPRODUCIBILITY MODE: judge the same field in the SAME "
                         "presentation order N times and report how much the verdict "
                         "moves. This is gate 0 and it is the one that reinterprets the "
                         "others - see JUDGING.md.")
    ap.add_argument("--allow-truncated", action="store_true",
                    help="judge a field whose packs dropped files for length. FOR THE "
                         "CAPPED-VS-UNCAPPED CONTROL ONLY (task 09): the completeness "
                         "gate refuses such fields by default because judging one "
                         "unnoticed is FINDINGS #62. Packs built this way are stamped "
                         "knowingly_truncated in their mapping record.")
    ap.add_argument("--repeat-seed", type=int, default=0,
                    help="which presentation order --repeats re-judges")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    missing = [flag for flag, val in (("--run", a.run), ("--games", a.games),
                                      ("--aspects", a.aspects), ("--out", a.out))
               if val is None]
    if missing:
        ap.error(f"missing required arguments: {' '.join(missing)}  (or --selftest)")
    if a.max_cost is not None:
        print("--max-cost is retired. It bounded a sweep by a list-price valuation of "
              "tokens on an account where no money moves per token, so it could not "
              "protect what is scarce and could only cut evidence short (FINDINGS #159). "
              "Bound the sweep with --max-rounds or --max-wall-min instead.",
              file=sys.stderr)
        return 2
    # EVERY (task, aspect) PAIR, BEFORE ANY MODE RUNS. A sweep is the largest spender
    # here, and all three of its modes plan the same cross product, so the pairing is
    # checked once at the top rather than inside whichever loop is in front of the
    # author. `run_field` refuses the same pair again; this is the one that refuses
    # before a single round starts.
    wrong = [r for g in a.games for asp in a.aspects
             if (r := applicability(asp, g)) is not None]
    if wrong:
        print(f"refusing the sweep: {len(wrong)} (task, aspect) pair(s) do not go "
              f"together.", file=sys.stderr)
        for r in wrong:
            print(f"  {r}", file=sys.stderr)
        return 2
    # THE RUN GUARD, BEFORE ANY MODE WRITES OR PAIRS A ROUND. All three modes
    # accumulate into --out and load stored rounds back, so one foreign run in the
    # directory reaches every gate, every summary figure and every later field_ranks
    # pool (assert_out_run's docstring holds the mechanism and the measured instances).
    # This is also the caller `warn_rounds_without_provenance` never had (#86 measured
    # it invoked by nothing): the listing prints here without the operator remembering
    # to ask.
    no_run = assert_out_run(a.out, a.run.name)
    for line in warn_rounds_without_provenance(a.out):
        print(f"NO PROVENANCE: {line}", flush=True)
    if no_run:
        print(f"NO PROVENANCE: {len(no_run)} stored round(s) in {a.out} carry no run; "
              f"they cannot be checked against --run and are reused as-is when their "
              f"(game, aspect, seed) is planned.", flush=True)
    if a.repeats:
        return repeats_main(a)
    if a.sequential:
        assert_out_root_durable(a.out)
        return sequential_main(a)

    assert_out_root_durable(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    spent = 0.0
    bounds = Bounds(a.max_rounds, a.max_wall_min)
    results: list[dict[str, Any]] = []
    planned = [(g, asp, seed)
               for g in a.games for asp in a.aspects for seed in range(a.orders)]
    print(bounds.banner(len(planned)) + f" model {a.model}\n")

    for game, aspect_id, seed in planned:
        if not bounds.may_start(f"{game}/{aspect_id}/seed{seed}"):
            break
        out_path = a.out / f"{game}__{aspect_id}__seed{seed}.json"
        if out_path.exists():
            print(f"  [have] {out_path.name}")
            results.append(json.loads(out_path.read_text()))
            continue

        with tempfile.TemporaryDirectory(prefix=f"pack-{game}-") as td:
            pack = Path(td) / "pack"
            try:
                field.build_pack(a.run, game, pack, seed,
                                 allow_truncated=a.allow_truncated,
                                 sees=ASPECTS[aspect_id].sees,
                                 blind_language=ASPECTS[aspect_id].blind_language)
            except RuntimeError as e:
                print(f"  [SKIP] {game}/{aspect_id}/seed{seed}: {e}")
                continue
            t0 = time.monotonic()
            bounds.started()
            res = field.run_field(pack, aspect_id, a.model,
                                  budget=a.per_call_budget)
        res["wall_s"] = round(time.monotonic() - t0, 1)
        _atomic(out_path, res)
        cost = float(res.get("cost_usd") or 0.0)
        spent += cost
        if not res.get("usable"):
            print(f"  [FAIL] {game}/{aspect_id}/seed{seed}: {res.get('error')} "
                  f"({tokenvalue.fmt(cost)}, cumulative {tokenvalue.tag(spent)})")
            continue
        c = field.ceiling(res)
        print(f"  [done] {game}/{aspect_id}/seed{seed}  scores={c['scores']}  "
              f"distinct={c['distinct']}  {tokenvalue.fmt(cost)}  "
              f"cumulative {tokenvalue.tag(spent)}")
        results.append(res)

    usable = [r for r in results if r.get("usable")]
    gates: dict[str, Any] = {"calls_usable": len(usable),
                             "calls_attempted": len(results),
                             "started_at": started_at}
    _record_cost(gates, spent, a.out)
    for r in usable:
        key = f"{r['game']}:{r['aspect']}:seed{r['order_seed']}"
        gates[f"ceiling:{key}"] = field.ceiling(r)
        gates[f"by_stack:{key}"] = field.by_stack(r)
    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            x, y = usable[i], usable[j]
            if x["game"] != y["game"] or x["aspect"] != y["aspect"]:
                continue
            if x["order_seed"] == y["order_seed"]:
                # SAME order, two judgements: reproducibility. Reported FIRST because a
                # gate whose verdict flips on unchanged input cannot support a conclusion
                # from one run, whatever the other gates say (#58).
                gates[f"reproducibility:{x['game']}:{x['aspect']}:seed{x['order_seed']}"] \
                    = field.reproducibility(x, y)
            else:
                gates[f"order_invariance:{x['game']}:{x['aspect']}"] = \
                    field.order_invariance(x, y)
    gates["independence"] = field.independence(usable)
    bounds.record(gates, len(planned))
    _write_summary(a.out, SUMMARIES["orders"], gates)

    print("\n=== gates (read these before any ranking) ===")
    print(json.dumps(gates, indent=2))
    _print_totals(spent, gates, bounds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
