---
established_by: 'Added a byte-identical 218-word section, When the gate itself is wrong, to all four eval/starters/*/AGENTS.md; the block hash is identical in all four (8a23fc8ac524089a). It is stated as a property of the repair, fix how the check handles the input it got wrong and do not take that input out of what the check looks at, with a mechanical test an agent can run in one turn: plant a real error in the thing the gate stopped complaining about, confirm red, remove it. Not written as the Godot incident, because a trigger written as an enumeration has to be re-derived by the next reader and because one engine named in four byte-identical files leaks that engine into three arms. THE THREE ROWS, measured on godot by eval/tools/starter_gate_control.py --stack godot, 0 FAILED: GREEN on pristine exit 0 with CHECK scripts=18 failures=0; RED on a parse error planted in the autoloaded tools/no_raise.gd exit 1; the plant DISCRIMINATES, tools/check.gd edited to skip the autoload instead of re-parsing it with the SAME plant, exit 0, the engine reporting the failed autoload while the gate does not. Row three is wg-g4c t1''s shipped repair reduced to its mechanism and proves the RED row would have reported FAILED on that submission. TWO CONTROLS ON ROW THREE ITSELF, both reporting FAILED as required: a safe edit at the same anchor, a comment with everything still re-parsed, leaves just check at exit 1; and an anchor absent from the file is refused with anchor found 0x, expected 1, rather than silently measuring the unrepaired gate. rust, ts and unity print NOT PINNED IN THE THIRD DIRECTION, reported and not failed, because their check is a compiler over a dependency graph and the plant sits in a root everything imports, so there is no per-file scope to narrow; ts re-measured green on pristine and exit 2 on its plant. GATES: judge/verify_blind.py on out-of-repo copies BLIND, 81 ids, 5 trees; judge/starter_parity.py exit 0, No drift detected on any measured axis, guide sizes 1619-2036 words, a 1.26x spread inside the 1.35x limit and narrower than the 1.30x before the edit; tools/docstat.py --sweep clean, 113 docs. DOCS: eval/RUNS.md records the ELEVENTH comparability break, the first that is not one-arm, with what it does and does not invalidate; eval/IMPROVEMENTS.md axis-2 candidate 5 updated from two directions to three; tools/precampaign_smoke.py label updated. Filed task 49: starter_parity collects just test''s exit code and never reads it, so ts reported 0/0 in this worktree and the tool still printed No drift. Branch task-47-gate-is-wrong-guidance, commit 130408d, not pushed.'
id: 47
title: Tell a building agent what to do when the starter's own gate is wrong, not only that it must not weaken it
status: done
priority: 3
refs: 'eval/FINDINGS.md #98, eval/IMPROVEMENTS.md axis 2 candidate 3, eval/tools/starter_gate_control.py'
done_when: the repair rule is present in each of the four starter AGENTS.md files in identical wording, the regime boundary is recorded in eval/RUNS.md, and starter_gate_control.py reports on a planted defect that the preferred repair still goes red while the repair the rule warns against goes green; or, if the planted defect cannot be made to distinguish the two repairs, that is reported as the result and the rule is left unwritten rather than closed
---

## What this thing is

Each of the four starters ships an `AGENTS.md` that the building agent reads during a trial. Each
ends with a Boundaries section: always / ask first / never. The never-list protects the
verification machinery - *"delete a test, or `skip()` a failing one, to make `verify` pass"*,
*"weaken a determinism assertion or widen the golden budget"*, *"lower a `gdscript/warnings/*`
level"*, *"delete a rule from `tools/boundary.gd`"*.

`eval/tools/starter_gate_control.py` is the companion on the harness side: it runs each starter's
own gate on a pristine copy, in both directions, once per campaign.

## What is wrong, and how we know

The never-list works. Measured 2026-08-23 over all 90 stored submissions with a `diff.stat`: 76 of
90 edited at least one file that decides their own tier-1 score, and every hunk in the
load-bearing files was read by hand. **Not one weakened an oracle.** The five `tools/boundary.gd`
edits changed an error-message string to name a renamed file and removed no rule; the six
`project.godot` edits changed name, description, window size and user directory and lowered no
warning level; the single `eslint.config.js` edit added a scratch directory to *ignores*.

The gap is the case the list does not cover: **what an agent should do when the starter's gate is
genuinely wrong.** That is not hypothetical - #98 is exactly it. `eval/starters/godot/tools/check.gd`
called `script.reload()` on a file the engine had already instantiated as an autoload, Godot
refused, and the loop could not tell that error from a parse error. `just check` and `just verify`
were red on an untouched tree, on one arm only.

Both Godot agents in `wg-g4c-2026-08-21T02-26-46` repaired it, and they chose differently:

- `t0` changed the call to `script.reload(true)` - `keep_state` - which re-parses for real. A
  genuine parse error still comes back.
- `t1` added a skip list so the autoloaded file is no longer re-parsed at all.

`t1`'s repair is a gate that stopped being able to fail. Measured as an adversarial variant in
#98: plant an unparseable function in `tools/no_raise.gd` and, with the skip list, `just check`
**exits 0** while the engine prints `Failed to instantiate an autoload`.

## Why it matters

The starter tells an agent it must never weaken the gate, and gives it no guidance for the one
situation where it has to touch the gate. Under that instruction one of two agents produced a
false green - a change that reads as compliance and is the worse of the two outcomes rule 7 names.
Two graded submissions came through this; the next one has the same coin to flip.

## What should be done

Add the missing half to the boundaries section in **all four** `eval/starters/*/AGENTS.md`, in the
same words in each. It should say, at minimum:

- if the gate is red before you have changed anything, say so explicitly in your final message -
  it is a defect in the template, not in your work;
- repairing it is allowed and welcome;
- **the repair must leave the check able to fail.** Prefer the repair that still detects the real
  defect over the one that stops looking. Excluding the input a check mishandles is not a repair.

Name the concrete instance, because a rule stated as its property and illustrated by its instance
survives a reader who meets a different instance (`AGENTS.md`, the 2026-08-15 rule audit).

**This is a starter change and therefore a regime boundary.** It must land in all four arms at
once, `judge/verify_blind.py` and `judge/starter_parity.py` must be re-run, and the boundary
recorded in `eval/RUNS.md`. Consider batching it with task 46 if that experiment goes ahead, so
one boundary is crossed rather than two.

### How to know it worked

The doc half cannot be verified by re-grading - no stored submission was written under the new
text. What **can** be verified is that the rule names a distinction the tooling can see. Extend
`starter_gate_control.py` so its stored table pins all three rows against a planted parse error in
the Godot autoload:

| input | expected |
|---|---|
| repaired starter, `reload(true)` | green normally, **red** on the planted defect |
| the original defect restored | red on a clean tree |
| the skip-list repair | green normally, **green on the planted defect - reported FAILED** |

Row three is the one that earns the whole task: a mutant that deletes the reload call cannot
produce it, only a variant that manufactures the input the gate mishandles can (rule 15). #98
already ran these three by hand; this task makes them a standing control.

### What not to conclude

Do **not** conclude from the 90-submission clean record that the existing never-list is dead
weight and can be pruned. A rule that has never fired is either preventing failures silently or
wasting space, and those look identical from outside; the clean record is as consistent with the
list working as with it being unnecessary. This task adds to it; it does not license removing it.

And do not conclude that `t1` was careless. It produced a green gate under an instruction that
told it only what not to do.
