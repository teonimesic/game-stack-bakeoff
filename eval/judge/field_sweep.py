#!/usr/bin/env python3
"""Run the specialist judges over a matrix, with a hard cost ceiling and gates first.

    python3 judge/field_sweep.py --run runs/wg-audio-... --games g1_pong \
        --aspects idiomatic fun --orders 2 --max-cost 60 --out judge-sweep/

Why this exists rather than a loop in a shell: three separate protections, each of
which this project has paid for the absence of.

1. **A COST CEILING THAT IS CHECKED BEFORE EACH CALL.** Field calls are the only part
   of the evaluation that spends money. `--max-cost` is enforced against measured
   spend so far, not against an estimate, and the sweep stops rather than overrunning.

2. **ONE WRITER PER ARTIFACT PATH.** Every result goes to its own file through a temp
   file and `os.replace`. Two judge processes once shared one path and produced a file
   holding two spliced JSON documents that parsed cleanly and was published (#19).

3. **GATES BEFORE RESULTS.** The sweep prints the ceiling, order-invariance and
   independence gates before any ranking, because a ranking from a judge that gives
   everything the same score, or that reorders when the presentation order changes, is
   not a result and should not be read as one.

Sequential on purpose. Concurrent judge fan-out during a matrix contributed to four
trials dying on an account session limit; and there is no hurry here, because unlike a
trial a judge call can be re-run for the same money tomorrow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import field  # noqa: E402
from aspects import ASPECTS  # noqa: E402
from sequential import MAX_RUNS, Sampler  # noqa: E402


#: Paths whose contents do not outlive the thing that wrote them. Kept in sync with
#: `wholegame.assert_work_root_usable`, which refuses the same set for TRIAL work trees.
_EPHEMERAL = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")


def assert_out_root_durable(out: Path) -> None:
    """A judge round is an artifact of record. It must not live where the OS reaps.

    THE GUARD FOR THIS ALREADY EXISTED AND DID NOT COVER THIS PATH.
    `assert_work_root_usable` refuses `$TMPDIR`, `/tmp` and `/var/folders` for trial work
    trees, is pinned in both directions, and was written after `$TMPDIR` deleted 80% of six
    submissions' toolchains between building and grading (#45). It names TRIAL WORK TREES.

    A judge sweep writes somewhere else, so the guard did not apply - and on 2026-08-17 a
    $44 sweep was writing into a session-scoped scratch directory under `/private/tmp`,
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

    THE COST IS RETURNED, not looked up by the caller. The first version left the
    caller to re-read the stored file, and the caller only did that for the sampled
    rounds - so the probe round of every aspect was spent and never counted, which on a
    five-aspect run is about $22 missing from a figure whose entire job is to stop the
    ceiling being passed. A spend counter that under-reports is worse than none.
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
    # A round already on disk was paid for by an earlier invocation, so it must not be
    # charged again to this one's ceiling.
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
    """
    assert_out_root_durable(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    summary: dict[str, Any] = {"mode": "repeats", "repeats": a.repeats,
                               "order_seed": a.repeat_seed}
    for game in a.games:
        for aspect_id in a.aspects:
            runs: list[dict[str, Any]] = []
            for i in range(a.repeats):
                if spent + a.per_call_budget > a.max_cost:
                    print(f"  STOPPING {game}/{aspect_id}: ${spent:.2f} + "
                          f"${a.per_call_budget:.2f} exceeds ${a.max_cost:.2f}", flush=True)
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
                        res = field.run_field(pack, aspect_id, a.model,
                                              budget=a.per_call_budget)
                    res["wall_s"] = round(time.monotonic() - t0, 1)
                    _atomic(out_path, res)
                    spent += float(res.get("cost_usd") or 0.0)
                if res.get("usable"):
                    runs.append(res)
                    c = field.ceiling(res)
                    print(f"  [rep {i}] {game}/{aspect_id} scores={c['scores']} "
                          f"modal={c['modal_fraction']} cumulative ${spent:.2f}", flush=True)
            key = f"{game}:{aspect_id}"
            pairs = [field.reproducibility(runs[i], runs[j])
                     for i in range(len(runs)) for j in range(i + 1, len(runs))]
            flips = sum(1 for r in pairs if r.get("ceiling_verdict_stable") is False)
            summary[key] = {"runs": len(runs), "pairwise": pairs,
                            "ceiling_verdict_flips": flips,
                            "verdict": ("REPRODUCIBLE" if pairs and not flips
                                        and all(p.get("identical") for p in pairs)
                                        else "SCORES MOVE, verdict stable" if pairs and not flips
                                        else "NOT REPRODUCIBLE - the ceiling verdict "
                                             "flipped on unchanged input" if flips
                                        else "too few usable runs")}
            print(f"  [gate0] {key}: {summary[key]['verdict']}", flush=True)
    summary["measured_cost_usd"] = round(spent, 2)
    _atomic(a.out / "REPRODUCIBILITY.json", summary)
    print("\n=== gate 0: reproducibility ===")
    print(json.dumps(summary, indent=2)[:3000])
    print(f"\nmeasured spend: ${spent:.2f}")
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
    summary: dict[str, Any] = {"mode": "sequential", "max_runs": a.max_runs}
    for game in a.games:
        for aspect_id in a.aspects:
            if spent + a.per_call_budget > a.max_cost:
                print(f"  STOPPING before {game}/{aspect_id}: measured ${spent:.2f} + "
                      f"${a.per_call_budget:.2f} exceeds the ${a.max_cost:.2f} ceiling",
                      flush=True)
                break
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
                if spent + a.per_call_budget > a.max_cost:
                    print(f"  STOPPING {game}/{aspect_id}: measured ${spent:.2f} + "
                          f"${a.per_call_budget:.2f} exceeds the ${a.max_cost:.2f} "
                          f"ceiling", flush=True)
                    return None
                scores, cost = _judge_round(a.run, game, aspect_id, i, a.model,
                                            a.per_call_budget, a.out)
                spent += cost
                return scores

            rep = sampler.run(judge_once)
            summary[f"{game}:{aspect_id}"] = rep
            print(f"  [seq] {game}/{aspect_id}: {rep.get('headline')} "
                  f"(rounds={rep.get('runs')}, cumulative ${spent:.2f})", flush=True)
    summary["measured_cost_usd"] = round(spent, 2)
    _atomic(a.out / "SEQUENTIAL.json", summary)
    print("\n=== sequential sampling ===")
    print(json.dumps(summary, indent=2)[:4000])
    print(f"\nmeasured spend: ${spent:.2f}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--games", nargs="+", required=True)
    ap.add_argument("--aspects", nargs="+", required=True, choices=sorted(ASPECTS))
    ap.add_argument("--orders", type=int, default=2,
                    help="presentation orders per (game, aspect). 2 is the minimum "
                         "that can measure order-invariance at all.")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default=field.DEFAULT_MODEL)
    ap.add_argument("--max-cost", type=float, default=60.0,
                    help="hard ceiling in USD, checked against MEASURED spend before "
                         "every call")
    ap.add_argument("--per-call-budget", type=float, default=12.0)
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
    if a.repeats:
        return repeats_main(a)
    if a.sequential:
        assert_out_root_durable(a.out)
        return sequential_main(a)

    assert_out_root_durable(a.out)
    a.out.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    results: list[dict[str, Any]] = []
    planned = [(g, asp, seed)
               for g in a.games for asp in a.aspects for seed in range(a.orders)]
    print(f"{len(planned)} field calls planned; ceiling ${a.max_cost:.2f}, "
          f"${a.per_call_budget:.2f} per call, model {a.model}\n")

    for game, aspect_id, seed in planned:
        if spent + a.per_call_budget > a.max_cost:
            print(f"STOPPING before {game}/{aspect_id}/seed{seed}: measured spend "
                  f"${spent:.2f} + ${a.per_call_budget:.2f} would exceed the "
                  f"${a.max_cost:.2f} ceiling.")
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
            res = field.run_field(pack, aspect_id, a.model,
                                  budget=a.per_call_budget)
        res["wall_s"] = round(time.monotonic() - t0, 1)
        _atomic(out_path, res)
        cost = float(res.get("cost_usd") or 0.0)
        spent += cost
        if not res.get("usable"):
            print(f"  [FAIL] {game}/{aspect_id}/seed{seed}: {res.get('error')} "
                  f"(${cost:.2f}, cumulative ${spent:.2f})")
            continue
        c = field.ceiling(res)
        print(f"  [done] {game}/{aspect_id}/seed{seed}  scores={c['scores']}  "
              f"distinct={c['distinct']}  ${cost:.2f}  cumulative ${spent:.2f}")
        results.append(res)

    usable = [r for r in results if r.get("usable")]
    gates: dict[str, Any] = {"measured_cost_usd": round(spent, 2),
                             "calls_usable": len(usable),
                             "calls_attempted": len(results)}
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
    _atomic(a.out / "GATES.json", gates)

    print("\n=== gates (read these before any ranking) ===")
    print(json.dumps(gates, indent=2))
    print(f"\nmeasured spend: ${spent:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
