---
established_by: 'Fixed: eval/starters/godot/tools/check.gd now calls script.reload(true), keep_state. MEASURED both directions on fresh copies of the repo starter with the harness uninvolved. BEFORE: just check exit 1, CHECK scripts=18 failures=1, Cannot reload script while instances exist on res://tools/no_raise.gd; just verify exit 1. AFTER: just check exit 0, CHECK scripts=18 failures=0; just verify exit 0 with 6 of 6 render tests passing. RED CONTROL: an unparseable function planted in the AUTOLOADED tools/no_raise.gd gives exit 1, and so does one planted in sim/sim.gd, and so does an untyped declaration, the warnings-as-errors path. BLAST RADIUS: 20 stored Godot submissions across 7 runs; the NoRaise autoload arrived with the 2026-08-17 starter edit so only 4 carry the defect, wg-g4b t0 and t1 and wg-g4c t0 and t1. ZERO were graded with it unrepaired: wg-g4b holds no report.json and both trials ended api_error; both wg-g4c agents repaired the template themselves, by two DIFFERENT mechanisms, and both scored build.compiles True and verify.green True. wg-g4c-capgate re-grades those same trees. No published tier-1 Godot number needs marking. OTHER STACKS: rust, ts and unity are all exit 0 on just check and just verify from pristine copies, measured two independent ways, so the red baseline was one-arm. NEW PERMANENT CONTROL: eval/tools/starter_gate_control.py runs both directions on pristine copies of all four starters, importing wholegame.IGNORE rather than restating it, registered in tools/precampaign_smoke.py at about 160s. Pinned three ways: repaired starter green plus red on the planted autoload error; the original defect restored makes the tool report FAILED; and the skip-list repair the wg-g4c t1 agent actually shipped passes green and FAILS red, since just check exits 0 over an unparseable autoload. GATES: judge/verify_blind.py exit 0, BLIND, 81 ids, 5 trees; judge/starter_parity.py exit 0, no drift on any measured axis; tools/docstat.py --sweep exit 0, 108 docs. DOCS: FINDINGS 98 in eval/findings/one-arm-bias.md, ninth comparability break in eval/RUNS.md, precampaign list in eval/PROTOCOL.md. Branch task-43-godot-check-gate, commit 68e0dc9, not pushed.'
id: 43
title: 'Godot starter: just check is RED on the pristine template'
status: done
priority: 1
refs: eval/starters/godot/tools/check.gd, eval/starters/godot/tools/no_raise.gd, eval/starters/godot/project.godot
done_when: just check exits 0 on a fresh copy of eval/starters/godot with no agent edits, a control shows the recipe still goes RED on a planted parse error, and verify_blind.py plus starter_parity.py have been re-run and eval/RUNS.md records the regime boundary
---

MEASURED 2026-08-23 on a fresh copy of the pristine starter, twice, with the harness uninvolved: just check exits 1 with 'Cannot reload script while instances exist' on res://tools/no_raise.gd, reporting CHECK scripts=18 failures=1.

CAUSE: no_raise.gd is registered as an autoload in project.godot (NoRaise='*res://tools/no_raise.gd'), so it already has a live instance by the time tools/check.gd runs. check.gd calls script.reload() with no argument, which Godot refuses for a script with instances and which returns an error the loop cannot tell apart from a parse error. It skips only SELF.

WHY IT MATTERS RATHER THAN BEING TIDINESS: this fails the template's OWN gate, so it lands on tier 1 as build.compiles=False and verify.green=False for any Godot submission that does not repair the harness itself. In wg-g4c-2026-08-21 BOTH godot agents independently patched tools/check.gd to call script.reload(true), with near-identical reasoning in the comment. Two independent subjects making the same repair is rule 9's shape: the shared cause is the instrument. Only the Godot arm pays this tax, which is bias and not noise (FINDINGS #25).

The defect is newer than most stored evidence: no_raise.gd appears in only 4 stored godot trials (wg-g4b 2026-08-17 and wg-g4c 2026-08-21) and wg-g4b was never graded. Every earlier godot trial predates the autoload and scored build.compiles=True, so the stored record understates this.

THE FIX THE AGENTS FOUND: script.reload(true) - keep_state - which still returns ERR_PARSE_ERROR on a real parse error. Take it from the wg-g4c diff rather than reinventing it, but do NOT take it on trust: a check that cannot go red is worse than one that is red, so plant a parse error in an autoloaded script and prove the recipe still fails.

NOT FIXED HERE: editing eval/starters is a regime boundary and was not task 25's business. Found while smoke-testing the tier-1 path for task 25.

## Independent verification by the orchestrator, 2026-08-23

Confirmed statically and from the subjects' own accounts, before this was assigned.

**The mechanism is in the pristine starter.** `eval/starters/godot/project.godot:79` declares
`NoRaise="*res://tools/no_raise.gd"` as an autoload, and `eval/starters/godot/tools/check.gd:51`
calls `script.reload()` with no argument. Godot refuses to reload a script with a live instance,
`reload()` returns an error, and the compile loop counts that as a compile failure.

**BOTH Godot agents in `wg-g4c-2026-08-21T02-26-46` hit it and repaired it — by two DIFFERENT
mechanisms**, which is why a search for one of them under-reports:

| trial | repair | its own account |
|---|---|---|
| `godot__t0` | `script.reload(true)` | *"the loop reported it as a COMPILE failure. I changed it to reload(true)"* |
| `godot__t1` | a **skip list** | *"The baseline was already red. tools/check.gd called reload() on the NoRaise autoload, which has a live instance"* |

A first pass here grepped for `reload(true)`, found it in `t0` only, and nearly recorded the
claim as overstated. That is this project's most-repeated defect in miniature: **the trigger was
written as one instance of the repair rather than as the defect.** Search for the cause, not for
the fix someone happened to apply.

**Why this is priority 1.** Two independent subjects producing the same repair for the same
baseline is rule 9 — when subjects that share nothing but the instrument agree, what they are
reporting is the instrument. Any Godot submission that did NOT repair the template pays
`build.compiles=False` and `verify.green=False` on tier 1 for a defect in the starter, and no
other arm pays it. That is one-arm bias in the deterministic tier, which is the tier weighted 0.31.

**Rule 11 applies and was load-bearing here.** Both agents wrote down exactly what they had
changed and why, in `agent.final_text`, and nothing in the grading pipeline reads it. The whole
diagnosis above came from those two paragraphs plus two greps.

**Before fixing:** `eval/starters/` is a regime boundary — `verify_blind.py`, `starter_parity.py`,
and a note in `eval/RUNS.md`. Establish first how many stored Godot submissions were scored with
the defect unrepaired, because that decides whether any published tier-1 Godot number needs
marking. Do not assume it is only `wg-g4c`.
