#!/usr/bin/env python3
"""The lint recipe for the HARNESS. One command, no flags to remember.

    python3 eval/tools/lint.py              # every site, grouped by rule
    python3 eval/tools/lint.py --counts     # the per-rule totals only
    python3 eval/tools/lint.py --rule PLW1510   # one rule, every site
    python3 eval/tools/lint.py --gate       # exit 1 if anything is reported

WHY THIS EXISTS SEPARATELY FROM `prune_scan.py --only lint`
------------------------------------------------------------
`prune_scan.py` answers *how big is each pile*. Acting on a pile needs the addresses,
and `--only lint` truncates to `--top` and never printed a file or a line number. A
session that wanted to triage had to reconstruct the ruff invocation from a docstring,
which is how a pinned rule set stops being pinned.

**The selection is NOT restated here.** `LINT_SELECT`, `LINT_ROOT` and `LINT_EXCLUDE`
are imported from `prune_scan.py`, and both entry points go through the same
`run_ruff()`. Two files spelling the same rule set will disagree eventually, and the
disagreement would look like the codebase moving rather than like a bug — AGENTS.md
rule 12, the address is an input to the check.

THIS IS NOT A GATE, AND THAT IS DELIBERATE
------------------------------------------
It exits **0** with findings unless `--gate` is passed. A gate added while the codebase
still violates it is a gate that gets switched off, and switching it off is silent. The
`--gate` flag exists so that whoever wires it into a check later does not have to touch
this file — but nothing calls it yet.

WHAT THE BASELINE MEANS
-----------------------
Every `subprocess.run` under `LINT_ROOT` carries an explicit `check=`, and every blind
`except Exception` that remains carries a `# noqa: BLE001` naming why the exception set
is open there. So a NEW hit from either rule is a site nobody has considered, which is
the only reading of a lint count that is worth anything. Triaged 2026-08-23, task 34.

The `B905`/`F401`/`F541`/`B007`/`B023`/`F841` counts were NOT triaged and are a standing
backlog, not a clean baseline. `--counts` shows them; do not read the total as a verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prune_scan  # noqa: E402

ROOT = prune_scan.ROOT


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rule", help="only this rule code, e.g. PLW1510")
    ap.add_argument("--counts", action="store_true", help="per-rule totals only")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 if anything is reported (nothing calls this yet)")
    a = ap.parse_args()

    try:
        rc, stdout, stderr = prune_scan.run_ruff()
    except OSError as e:
        # A linter that did not run must never read as a clean bill of health (#61).
        print(f"ruff did not run: {e}", file=sys.stderr)
        print("install it with `uv tool install ruff` — absence is NOT a clean result",
              file=sys.stderr)
        return 2
    if rc not in (0, 1):
        # rc 2 is "ruff refused the invocation" and comes with EMPTY stdout, which
        # parses as zero findings. MEASURED: `--select E999` gives rc=2, stdout ''.
        print(f"ruff refused the invocation (exit {rc}) — this is NOT a clean result",
              file=sys.stderr)
        print(stderr.strip()[:2000], file=sys.stderr)
        return 2
    try:
        items = json.loads(stdout or "[]")
    except json.JSONDecodeError as e:
        print(f"ruff output is not JSON: {e} — NOT a clean result", file=sys.stderr)
        return 2

    if a.rule:
        items = [it for it in items if it.get("code") == a.rule]

    by_rule: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_rule[str(it.get("code"))].append(it)

    print(f"harness lint — {prune_scan.LINT_ROOT.relative_to(ROOT)}, "
          f"--select {prune_scan.LINT_SELECT}")
    for ex in prune_scan.LINT_EXCLUDE:
        print(f"  excluded: {ex.relative_to(ROOT)}")
    print()
    for code in sorted(by_rule, key=lambda c: (-len(by_rule[c]), c)):
        hits = by_rule[code]
        print(f"{len(hits):>4}  {code}  {hits[0].get('message', '')[:70]}")
        if a.counts:
            continue
        for it in sorted(hits, key=lambda d: (d.get("filename", ""),
                                              (d.get("location") or {}).get("row", 0))):
            loc = it.get("location") or {}
            try:
                rel = Path(it.get("filename", "")).relative_to(ROOT)
            except ValueError:
                rel = Path(it.get("filename", ""))
            print(f"        {rel}:{loc.get('row')}:{loc.get('column')}")
        print()
    if not items:
        print("no findings for the pinned set")
    print(f"\n{len(items)} finding(s). Not a gate: see this file's docstring.")
    return 1 if (a.gate and items) else 0


if __name__ == "__main__":
    sys.exit(main())
