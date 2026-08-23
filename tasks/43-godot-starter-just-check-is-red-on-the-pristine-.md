---
id: 43
title: Godot starter: just check is RED on the pristine template
status: open
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
