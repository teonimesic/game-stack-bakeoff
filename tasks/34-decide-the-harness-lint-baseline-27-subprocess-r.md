---
established_by: Triaged, not swept. 27 PLW1510: all 27 now state check= explicitly; 24 justified in place with a comment naming why a non-zero exit is the expected or handled outcome (pkill matching nothing, cp -Rc off APFS, just --summary on an older just, find exiting 1 on a permission-denied descent while still listing what it read, the agent CLI exiting non-zero after writing a gradeable submission); 3 were real. 34 BLE001/S110/S112: 14 removed from scope, 9 narrowed to the exceptions actually expected, 11 kept blind with a noqa naming why the exception set is open and where the failure is recorded. 0 rules dropped. The three real ones. (1) prune_scan.cat_lint reported a clean bill of health for two of the three ways ruff can fail to run - MEASURED: --select E999 exits 2 with empty stdout, and a non-existent path exits 0 with an empty JSON array; both printed lint (0). It now checks the address before the command and treats any exit outside 0 or 1 as a refusal. (2) wholegame.build_trial discarded the exit codes of git add -A, tar -czf and find, so a failed evidence capture was indistinguishable from an agent that changed nothing - MEASURED reachable: git add -A outside a repo exits 128, tar into a bad path exits 1 and writes no archive. The three codes are now recorded as capture_exit_codes in the trial record and printed when non-zero. (3) field.build_pack silently dropped an unreadable file from a judge pack and counted it nowhere; now except OSError, counted as code_unreadable, carried in the pack manifest. Scope correction, not a fix: eval/judge/fixtures is now excluded alongside eval/runs. Those are stand-in submissions, the same class as eval/starters, one deliberately defective; they held 14 of the 30 BLE001 and 3 of the 11 B905. Recipe: eval/tools/lint.py, one command, prints every site with file and line, --rule to filter, --counts for totals, --gate to exit 1 on findings. NOT a gate and nothing calls --gate: a gate added while the codebase still violates it is one that gets disabled. LINT_SELECT, LINT_ROOT and LINT_EXCLUDE are spelled once, in prune_scan.py, and both entry points call the same run_ruff. Controls, all run: planted a subprocess.run with no check= and a bare except Exception - reported by name at its address, and --gate exited 1; reverted, both rules exit 0 clean, as do S110 and S112. cat_lint against a removed rule selector reports ruff refused the invocation exit 2, and against a bad root reports the root does not exist - neither reads as clean. field.build_pack on a synthetic 8-submission run: clean gives code=3 code_unreadable=0 per label, a planted unreadable file gives exactly one code_unreadable=1 and it reaches the stored manifest. Verified unpiped: tasks.py check 49 well-formed; docstat.py --sweep clean, 115 docs; heartbeat.py findings_highest=104; precampaign_smoke.py 16 of 16 exercised, 0 FAILED. PLW1510 and BLE001 are now a real baseline at 0 - a new hit is a site nobody has considered. B905/F401/F541/B007/B023/F841, 44 findings, were NOT triaged and are a standing backlog, recorded as such in DECISIONS.md and in the lint.py docstring. Recorded as FINDINGS #104; the superseded absence-branch claim in CLEANUP-LOG.md is marked rather than deleted. Branch task-34-lint-baseline.
id: 34
title: "Decide the harness lint baseline: 27 subprocess.run calls ignore their exit status"
status: done
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
