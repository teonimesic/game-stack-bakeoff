---
id: 34
title: "Decide the harness lint baseline: 27 subprocess.run calls ignore their exit status"
status: open
priority: 2
refs: eval/tools/prune_scan.py cat_lint, AGENTS.md rule 3, eval/findings/fail-open.md
done_when: either the 27 PLW1510 and 29 BLE001 sites are triaged with each one fixed or explicitly justified in a comment, or the rule is dropped from the pinned set with the reason recorded; and a lint recipe exists that a session can run
---

WHAT THIS IS

The **harness** is the Python under `eval/` that runs trials, grades submissions and produces
every number this project publishes. It is distinct from `template*/` and `eval/starters/*/`,
which are the **product** and have their own per-stack lint recipes.

Until 2026-08-23 the harness had **no linter at all** — no `ruff`, `flake8` or `pylint` installed
or configured. `ruff` was installed that day and is now run by
`python3 eval/tools/prune_scan.py --only lint`, pinned to correctness rules rather than style.

WHAT IS WRONG, AND HOW WE KNOW

Measured 2026-08-23, on the pinned rule set:

    29  BLE001   blind `except Exception`
    27  PLW1510  `subprocess.run` without an explicit `check=` argument
    11  B905     `zip()` without `strict=`
     3  S110     `try`/`except`/`pass`
     4  F841     assigned and never used
     2  B023     function does not bind its loop variable

**These are not style.** `AGENTS.md` rule 3 exists because this project has repeatedly been
misled by an exit status nobody read, and `subprocess.run` without `check=` is precisely that:
the call returns, the `CompletedProcess` is truthy, and a failed command is indistinguishable
from a successful one unless someone inspects `.returncode`. 27 sites do not.

`BLE001` and `S110` are the **fail-open** shape recorded as #31 — the one defect class here that
costs you the result rather than costing you trials.

WHY IT MATTERS

Not every one of these is a bug. Plenty of `subprocess.run` calls are best-effort probes where a
failure genuinely does not matter, and plenty of blind excepts are deliberate. **The problem is
that the deliberate ones and the accidental ones are currently indistinguishable**, so nobody can
tell whether a given site is fine, and the count cannot go down in a way that means anything.

WHAT SHOULD BE DONE

Triage, do not mass-fix. A blanket `--fix` would touch dozens of sites, produce a large
unreviewable diff, and change behaviour at every one of the 27 `check=` sites — some of which
would then start raising where they currently continue.

For each site, one of:

- **Fix it** — the exit status or the exception matters and was being dropped.
- **Justify it** — add `check=False` explicitly, or narrow the `except` to the exception actually
  expected, with a short comment saying why a failure is acceptable there. An explicit
  `check=False` and an accidental omission look identical to a reader and different to the linter,
  which is the whole point.
- **Drop the rule** — if triage shows the rule is wrong for this codebase, remove it from the
  pinned set in `prune_scan.py:cat_lint` and record why. That is a legitimate outcome.

Then add a recipe so a session can run it without remembering the flags, and decide whether it
should gate anything. **Do not make it a gate in the same change as the triage** — a gate added
while the codebase already violates it is a gate that gets disabled.

OUTCOMES THAT COUNT AS SUCCESS

Any of: the sites are triaged; or the rules are dropped with a reason. A partial triage that
handles the 27 `PLW1510` sites and leaves `BLE001` for later is fine **if it says so**.

WHAT NOT TO CONCLUDE

**Do not read "491 issues" as "the harness is badly written."** That figure came from ruff's
unpinned default rule set and was 132 percent-format warnings and 43 shebang notices. The pinned
set reports 28 distinct rules, and the two that matter are named above. Fixing the other 463
would be churn: tokens and review attention spent moving text without making anything easier to
get right.
