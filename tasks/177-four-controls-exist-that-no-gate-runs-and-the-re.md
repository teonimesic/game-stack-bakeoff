---
id: 177
title: Four controls exist that no gate runs and the register does not record as excluded, and nothing produces that list
status: in_testing
priority: 2
refs: .github/workflows/README.md,eval/tools/fragment_control.py,eval/tools/evidence_set_control.py,eval/tools/ci_minutes.py,tasks/175
done_when: 'A producer answers ''which controls does no gate run, and which of those does the register record as deliberately excluded'' - most naturally a flag on `ci_minutes.py`, which already reads the workflows and already derives the hook list by RUNNING the hook rather than restating it. It must be pinned in both directions: a planted ungated control goes red, and a control recorded as excluded in the register stays green. Then each of the four above is either placed in a tier with its measured runtime added to the register''s cost column, or recorded as excluded with the reason. `fragment_control.py` and `evidence_set_control.py` at about a second each are the two where ''excluded'' would need a real argument. Coordinate with `tasks/175`: whichever runs second should find the other already done rather than re-deciding it.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/49
established_by: 'PR #49, 5 review rounds: ci_minutes.py --controls censuses 40 git-tracked controls, 36 gated, 4 ungated and all 4 recorded; fragment_control.py (0.42s) and runner_capture_selftest.py (2.26s) added to gates.yml (51 -> 53); live plant red/green/stale in all 3 directions; mutation sweep 23/23; --selftest 63 -> 94 mutants, 33 -> 55 variants'
---

Found by the cleanup pass of 2026-08-27, the first to open `eval/tools/`.

`.github/workflows/README.md` is the register: what runs in which tier, what each costs, and every gate deliberately left out WITH THE REASON. AGENTS.md tells a session to read it before adding a gate, before concluding one is missing, and before assuming a green run covered something. The register's promise is only as good as something checking it, and nothing does.

Measured: of the 46 scripts in `eval/tools/`, 15 are invoked by no workflow and no git hook. Most of those are manual by design (`heartbeat.py`, `prune_scan.py`, `disclosure.py`). Four are not - they are CONTROLS, whose entire purpose is to be run as a gate, and none of the four is named anywhere in the register:

| tool | reachable from | runtime |
|---|---|---|
| `fragment_control.py` | **nothing at all** | 1.1s, exit 0, 12/12 |
| `evidence_set_control.py` | **nothing at all** (one prose mention in a sibling's docstring) | 1.5s, exit 0, 11/11 |
| `starter_gate_control.py` | `precampaign_smoke.py`, which is itself ungated | not run here |
| `disclosure_mutants.py` | `precampaign_smoke.py`, same | not run here |

The first two are the sharp cases. `fragment_control.py`'s own docstring says why it exists: it pins `docstat._check_duplicate_fragment` in both directions, and its `whole_line` mutant is 'the design that was tried first and measured as a complete false negative, so this control is what stops it being tried again silently'. Nothing runs it, so nothing stops that. Both cost about a second, which is pre-commit money.

The extraction was proved on a known case before being believed: `skill_layout_control.py`, which AGENTS.md says pins the layout gate red, is correctly detected as gated.

**The general defect is that this census has no producer.** `tasks/175` is one instance of the same shape found independently, one tool over - and fixing 175 alone leaves the next one, which is the enumeration-versus-property failure AGENTS.md's rule audit describes. A list of ungated controls that a human compiled is a list that goes stale the next time somebody adds a control.

## note 2026-08-27

Done on `task-177-ungated-controls-census`, PR #49. `python3 eval/tools/ci_minutes.py
--controls` is the producer; `ci_minutes --selftest` runs the live census, so it gates
through a step that already existed rather than a new one.

**The ticket's own census was wrong, in both directions, and that is the ticket's point.**
It listed 4 ungated controls over `eval/tools/` alone and said none was named in the
register. Measured: the population is **40** git-tracked scripts across the whole of
`eval/`, **6** were ungated, and the register had carried rows for **4** of the 6 since
commit `68232bd` — the commit that introduced CI. The 2 real gaps were
`eval/tools/fragment_control.py` and `eval/runner_capture_selftest.py`, and the second is
one the `eval/tools/`-only scan could not reach. Both are now in `gates.yml` (0.42s and
2.26s locally, 3 readings each). `gates.yml` goes 51 → 53.

The ticket's runtime for `evidence_set_control.py` (1.5s, exit 0, 11/11) was read in the
main checkout, which has `eval/runs/`. **In any checkout it exits 2 in 0.06s** — the
register's stated reason for excluding it is correct as written, and the same is true of
`disclosure_mutants`.

**Do not re-derive these design decisions.** Each was measured, and each has a mutant:

- **Gated means NAMED, not reachable.** A transitive reading over string literals was
  built first: it makes `starter_gate_control` and `disclosure_mutants` children of
  `precampaign_smoke.py` — itself ungated, so it changes no answer — while opening a
  fail-open channel. Of the 21 places a non-docstring literal under `eval/` names a
  control, 3 are prose and 3 are `ci_minutes.py`'s own selftest fixtures. The known-good
  row is `evidence_set_control.py`, which the gated `backup_evidence_control.py` cites in
  its **module docstring**: a literal-following census calls it gated on that alone.
- **The population is `git ls-files`, not a filesystem walk.** `eval/starters/ts/node_modules`
  is untracked and gigabytes.
- **A gate command is read as a shell reads it, and the token it RUNS is matched as a
  resolved path.** Quoting, `./`, `//`, `..`, absolute and executed-directly all name the
  script; a different address, a path `echo`/`cat` is merely holding, and a
  repository-relative interpreter name nothing. `_program_run` reuses
  `SCOPE_INTERPRETERS` and the rule `scope_invocation_problems` applies to the scope step.
- **A bare register name excuses a control only while one control answers to it.** Two
  controls can come to share a stem across `eval/tools/` and `eval/judge/`; the repair a
  red row asks for is to write the repository-relative path, which is read too.
- **A qualified span excuses a MODE, never the script** — and the two spellings behave
  differently. `tasks_control --live-squash-refs` reduces to a stem matching nothing;
  `host_perf_probe.py --caps` reduces to the script's own stem, and only that shape can
  excuse a whole script by accident. The selftest fixture carries both, because with only
  the first the guard was unpinned and a mutant deleting it survived.
- **An exclusion is a name AND a reason.** A blank `why` cell records that somebody
  noticed and excuses nothing.

**What the review cost and what it found.** 5 rounds, 8 defects, every one real and every
one reproduced before being fixed. Rounds 3, 4 and 5 each found a fail-closed gap in the
NEW code rather than in the original change, all in one family: an input this census reads
that can be malformed — an unparseable workflow, a hook tier that listed nothing, a
register that is missing or not UTF-8, a row with no reason, an ambiguous stem, a command
that merely holds a path. If another round is spent, that is where it should look.

**Three of my own pins were reading the wrong field, and the mutation sweep is what found
them.** Not the selftest — the selftest was green. `/private/tmp/.../mutate.py` applied
each mutation to the live file and re-ran `--selftest`; it is worth rebuilding for the next
check of this shape. The survivors were: a refusal pin that passed an INVALID register, so
an unreadable register was a second cause of the same red and the guard could be deleted
green; a pin that read the `stale` LIST while the mutant left the list correct and only
stopped reporting it; and a fixture whose mode row could not reach the guard it was
pointed at. Assert the DIAGNOSIS and the EXIT STATUS, not the intermediate field.

**A procedural mistake worth not repeating.** The live plant control was reverted with
`git checkout -- .github/workflows/gates.yml`, which restored from the index and silently
took the two real gate steps with it. Back up the file you are about to plant into and
restore from your own copy; `git checkout` is the wrong instrument when the file also
carries your work.

**Filed:** `tasks/180` — 7 tools carry a `--selftest` MODE that no gate runs (`census.py`,
`disclosure.py`, `instruction_census.py`, `judge_ledger.py`, `tier1_census.py`,
`tier2_census.py`, `linkcheck.py --selftest`). Deliberately outside this census: the
property here is a closed class of file stems, and whether a selftest mode belongs in a
tier is decided by opening each tool.

**Coordination with `tasks/175`:** it was still `todo`, so this ran first. It asks whether
`ci_minutes --selftest` runs in a HOOK tier; nothing here decides it, and this branch adds
no hook command. Its agent will find the hook table and coverage sentence where it expects
them, at the new count of 53.

**A finding to number, if the orchestrator agrees it is one.** The register's promise that
every excluded gate is recorded with the reason had no measurement behind it for the whole
life of CI, and 2 controls sat outside both the tiers and the exclusion table — one of them
existing specifically so that a design measured as a complete false negative could not be
retried silently. The general shape: a document that a rule tells every session to trust is
a document that needs a producer, and "read it before concluding a gate is missing" is not
one.
