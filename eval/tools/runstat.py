#!/usr/bin/env python3
"""Report the true state of a running (or finished) matrix.

WHY THIS EXISTS
---------------
Every hand-rolled status check in this project has been wrong at least once, and each
time the wrong answer looked like a real reading. This script is the single correct
implementation; do not re-derive it at a shell prompt.

The traps it avoids, each of which produced a confident wrong diagnosis:

  pgrep -f "wholegame.py"     matches the MONITOR that greps for it, and any shell whose
                              command line contains the string. Four false readings.
  pgrep -c                    does not exist on BSD/macOS. It is a usage error that
                              prints nothing, and `|| echo 0` turns it into "0 agents"
                              while four are running. Denied in .claude/settings.json.
  pgrep -f "Unity|godot"      matches every trial agent, because the prompt names the
                              engines. Match on the process NAME for "is X running".
  find -newermt '-30 minutes' silently matches nothing on macOS. Use -mmin.
  cmd || echo 0               converts an error into a plausible in-range number.
  a.get("total_cost_usd")     is absent; the key is cost_usd. Reads as $0.00 silently.
  %cpu ~0 / frozen CPU        normal for an agent waiting on an API call OR on a running
                              tool. Only "frozen CPU *and* zero descendants" is a wedge.

Usage:
    python3 tools/runstat.py                     # newest run
    python3 tools/runstat.py --run-dir runs/X    # a specific run
    python3 tools/runstat.py --watch 300         # re-report every N seconds
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import subprocess
import sys
import time

# Where trial work trees live. This MUST track wholegame.py's `default_work`; it was
# hardcoded to the old $TMPDIR location and kept printing "no writes in last 10 min"
# through an entire build in which the agents wrote 2555 files in ten minutes. The
# glob matched nothing, and "found no trees" printed identically to "found trees,
# nothing moved" -- a probe that runs, reports, and measures nothing, in the tool
# AGENTS.md calls the only correct status check.
#
# Two defences, because naming the right path once is not a defence:
#   * the two spellings are asserted equal by the smoke suite, so moving the work root
#     again fails loudly here instead of silently reading an empty directory;
#   * "no trees found" is now a DISTINCT line from "no writes", so the failure that
#     produced this comment cannot recur silently.
WORK_ROOT = os.path.join(os.path.expanduser("~"), "game-research-work")


def _ps(fmt: str) -> list[str]:
    """Raw `ps` lines. Never piped through anything that could swallow a failure."""
    r = subprocess.run(["ps", "-Ao", fmt], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ps failed rc={r.returncode}: {r.stderr.strip()}")
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def find_drivers() -> list[dict]:
    """Real drivers only: a Python interpreter actually running wholegame.py.

    A shell whose argv merely CONTAINS "wholegame.py" is not a driver. That
    distinction is the whole point of this function.
    """
    out = []
    for ln in _ps("pid=,ppid=,etime=,command="):
        parts = ln.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, etime, cmd = parts
        if "wholegame.py" not in cmd:
            continue
        exe = cmd.split(None, 1)[0]
        base = os.path.basename(exe).lower()
        if not base.startswith("python"):
            continue  # a shell, a monitor, an editor — not a driver
        run_dir = ""
        toks = cmd.split()
        if "--run-dir" in toks:
            run_dir = toks[toks.index("--run-dir") + 1]
        out.append(
            {"pid": int(pid), "ppid": int(ppid), "etime": etime,
             "run_dir": run_dir, "cmd": cmd}
        )
    return out


def children(pid: int) -> list[int]:
    return [int(ln.split()[0]) for ln in _ps("pid=,ppid=")
            if len(ln.split()) == 2 and int(ln.split()[1]) == pid]


def proc_info(pid: int) -> dict | None:
    for ln in _ps("pid=,etime=,time=,comm="):
        parts = ln.split(None, 3)
        if len(parts) == 4 and int(parts[0]) == pid:
            return {"pid": pid, "etime": parts[1], "cpu": parts[2], "comm": parts[3]}
    return None


def engines_by_name() -> list[str]:
    """Engine binaries by PROCESS NAME. An argv match would return every agent."""
    hits = []
    for ln in _ps("pid=,comm="):
        pid, _, comm = ln.partition(" ")
        base = os.path.basename(comm.strip()).lower()
        if base in {"unity", "godot", "starter"} or base.endswith(".app"):
            hits.append(f"{pid.strip()} {comm.strip()}")
    return hits


def files_touched(tree: str, minutes: int) -> int:
    """-mmin, never -newermt. Returns -1 if the probe itself failed."""
    r = subprocess.run(
        ["find", tree, "-type", "f", "-mmin", f"-{minutes}"],
        capture_output=True, text=True,
    )
    if r.returncode not in (0, 1):
        return -1
    return len([x for x in r.stdout.splitlines() if x.strip()])


def read_trials(run_dir: str) -> list[dict]:
    rows = []
    for f in sorted(glob.glob(os.path.join(run_dir, "trials", "*.json"))):
        d = json.load(open(f))
        a = d.get("agent") or {}
        if "cost_usd" not in a and "total_cost_usd" in a:
            raise RuntimeError(f"{f}: unexpected schema — cost key moved, do not guess")
        rows.append({
            "id": d.get("trial_id", "?"),
            "stack": d.get("stack", "?"),
            "cost": a.get("cost_usd"),
            "turns": a.get("num_turns"),
            "wall_min": (d.get("wall_s") or 0) / 60.0,
            "term": a.get("terminal_reason"),
        })
    return rows


def newest_run() -> str:
    ds = [d for d in glob.glob("runs/*/") if os.path.isdir(d)]
    if not ds:
        raise SystemExit("no runs/ directories found — is the cwd eval/ ?")
    return max(ds, key=os.path.getmtime).rstrip("/")


def report(run_dir: str) -> None:
    print(f"=== {run_dir} ===")

    # A run directory that does not exist must not report as a run that has not
    # started. Those printed identically ("no trial records yet") until a mistyped
    # --run-dir returned a clean empty status for a matrix that had 8 completed
    # trials on disk. Same shape as the work-tree glob repair below: the absence of
    # the thing being measured read as a measurement.
    if not os.path.isdir(run_dir):
        raise SystemExit(f"runstat: no such run directory: {run_dir}")

    rows = read_trials(run_dir)
    if rows:
        for r in rows:
            cost = f"${r['cost']:>6.2f}" if r["cost"] is not None else "   n/a"
            turns = f"{r['turns']:>4}t" if r["turns"] is not None else "  ?t"
            print(f"  {r['id']:<26} {cost} {turns} {r['wall_min']:>6.1f}min  {r['term']}")
        # Partition before aggregating. A mean over mixed terminal reasons is meaningless.
        #
        # AND PARTITIONING BY TERMINAL REASON IS NOT ENOUGH, because one reason can hold
        # two populations. `wg-g4b` was killed by an external quota limit and printed
        #
        #     api_error n=8 total $65.57 mean $8.20
        #
        # over two trials that had worked for 53 minutes and six that never got a turn.
        # $8.20 describes no trial that has ever run - rule 4 firing INSIDE the partition
        # the tool already makes. So the mean is suppressed unless the group is
        # homogeneous in the only way that is cheap to check: did the trial do anything.
        by_term = collections.defaultdict(list)
        for r in rows:
            by_term[r["term"]].append((r["cost"] or 0.0, r["turns"] or 0))
        print()
        for term, cs in sorted(by_term.items(), key=lambda kv: str(kv[0])):
            costs = [c for c, _ in cs]
            started = [c for c, n in cs if n > 1]
            never = [c for c, n in cs if n <= 1]
            head = f"  {str(term):<18} n={len(cs):<3} total ${sum(costs):>8.2f}"
            if started and never:
                # Two populations under one label. Report both; refuse the pooled mean.
                print(f"{head}  MEAN SUPPRESSED - {len(started)} trial(s) ran, "
                      f"{len(never)} never got a turn")
                print(f"  {'':<18} ran:   n={len(started)} total ${sum(started):>8.2f}  "
                      f"mean ${sum(started)/len(started):>7.2f}")
                print(f"  {'':<18} never: n={len(never)} total ${sum(never):>8.2f}")
            else:
                print(f"{head}  mean ${sum(costs)/len(costs):>7.2f}")
    else:
        print("  no trial records yet")

    print()
    drivers = find_drivers()
    if not drivers:
        print("  driver: NONE (finished, or never started)")
    for d in drivers:
        kids = children(d["pid"])
        print(f"  driver {d['pid']} up {d['etime']}  run_dir={d['run_dir'] or '?'}")
        for k in kids:
            info = proc_info(k)
            if not info:
                continue
            gk = children(k)
            # Frozen CPU alone is not a wedge: an agent waiting on a running tool
            # consumes none. Zero descendants AND frozen CPU is the signature.
            flag = "  <-- no descendants; check CPU twice" if not gk else ""
            print(f"    child {k} ({info['comm']}) up {info['etime']} "
                  f"cpu {info['cpu']} descendants={len(gk)}{flag}")

    print()
    trees = [t for t in sorted(glob.glob(os.path.join(
        WORK_ROOT, os.path.basename(run_dir), "*"))) if os.path.isdir(t)]
    if not trees:
        # NOT the same statement as "no writes". Distinguishing them is the whole
        # repair: the merged form read as a measurement of the agents when it was a
        # measurement of the glob.
        print(f"  work trees: NONE FOUND under {WORK_ROOT}/{os.path.basename(run_dir)}")
        print("    -> this says nothing about the agents. Either the run has not "
              "prepared its trees yet,")
        print("       or --work-root differs from this tool's. Check before reading "
              "it as inactivity.")
    else:
        counts = [(os.path.basename(t), files_touched(t, 10)) for t in trees]
        active = [(n, c) for n, c in counts if c != 0]
        if active:
            print("  work trees, files written in last 10 min:")
            for n, c in active:
                print(f"    {n:<26} {'PROBE FAILED' if c < 0 else c}")
        else:
            print(f"  work trees: {len(trees)} found, no writes in last 10 min")

    eng = engines_by_name()
    print(f"\n  engine processes by name: {len(eng)}")
    for e in eng[:5]:
        print(f"    {e}   (check ancestry before assuming it is ours)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir")
    ap.add_argument("--watch", type=int, metavar="SECONDS")
    args = ap.parse_args()

    while True:
        run_dir = args.run_dir or newest_run()
        report(run_dir)
        if not args.watch:
            return 0
        print(f"\n--- sleeping {args.watch}s ---\n", flush=True)
        time.sleep(args.watch)


if __name__ == "__main__":
    sys.exit(main())
