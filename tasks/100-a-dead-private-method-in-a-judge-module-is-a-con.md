---
id: 100
title: A dead private method in a judge module is a conclusion waiting to rest on it - make the census a gate
status: in_flight
priority: 3
refs: 'eval/findings/certifies-nothing.md #136, eval/judge/bot_arena.py _turn_corner, eval/judge/probe.py Bot._num, eval/tools/lint.py'
done_when: a check exists that goes RED on a tree containing PlatformerBot._approach as committed at 9fc044a and GREEN on the current tree, both run and both reported - a green with no red establishes nothing. The two current hits are each resolved by deletion or by a mechanism that is not a bare name allowlist, and the docstring measurement inside _turn_corner is preserved wherever it ends up. Whichever way it goes, the census numbers are stated in the evidence string. If the conclusion is that the check is not worth its exemptions, that is a result and closes this - say what the measured cost was.
---

FINDINGS #136: PlatformerBot._approach had no caller in any of the five commits that defined it, and two conclusions in the archive rested on repairs made to it - row 5 of the unity__t0 chain, and the re-grade sentence that falsified the pit hypothesis for #82. An AST census of private methods defined in a class minus every attribute-and-name reference in the tree is about fifty lines and names _approach at 9fc044a, the very tree that published #82. It would have fired before the re-grade was interpreted. ALREADY MEASURED, do not re-derive: over eval/judge/ the census sees 121 private methods; 3 unreferenced at 9fc044a (PlatformerBot._approach, ArenaBot._turn_corner, Bot._num) and 2 today (ArenaBot._turn_corner, Bot._num). It must treat a string mention as a use, or getattr-dispatched methods go dead spuriously. THE DESIGN QUESTION THIS NEEDS AND #136 DOES NOT ANSWER: what happens to the two current hits. _turn_corner is a cluster of three (_corners, _far_corner, _turn_corner; _far_corner is called only by _turn_corner) implementing a design that _chase's own docstring records as measured and discarded, and its docstring is the only record of that measurement - deleting it loses evidence, keeping it needs an exemption, and an exemption list is a fail-open channel by rule 7. _num is an unused base-class helper. Decide that before writing the gate, not after.

## Updated at dispatch, 2026-08-23 — where the check goes, and what you may not touch

**Read before starting; these moved after the ticket was filed.**

### Verified still true

- **`#136` still resolves to the finding this ticket means** — `eval/findings/certifies-nothing.md`,
  heading `## 136.`, the `_approach` finding. Four findings were renumbered on 2026-08-23
  (`#126→#128`, `#132→#133`, `#133→#134`, `#137→#140`) and `#136` is not among them, so the `refs`
  line is safe. **Do not take this on trust for any other number you cite** — run
  `python3 eval/tools/docstat.py --renumbered` before writing a citation.
- **The two current hits are where the ticket says.** `eval/judge/bot_arena.py:693` `_turn_corner`
  with `_corners` (686) and `_far_corner` (690), and `eval/judge/probe.py:539` `Bot._num`. Read
  them rather than the summary above: `_corners` and `_far_corner` are *not* dead — `_far_corner`
  is called at 706 and `_corners` at 691 and 707, all from inside `_turn_corner`. **The cluster is
  dead only as a whole**, which is a property the per-method census as specified cannot see, and
  deciding what to do about that is part of this task.

### File conflicts — three peers are live in the same directories

| Do not edit | Who has it | Why |
|---|---|---|
| `eval/judge/field.py` | task 104 (in flight), task 103 (queued behind it) | `EVIDENCE_BLURB` and `LABELS` are being rewritten right now |
| `eval/tools/docstat.py` | task 89 (in flight) | the fenced-flag check |
| `eval/tools/tasks_control.py`, `eval/tools/tasks_mutants.py` | tasks 105 (in flight), 106 (queued) | the mutant runner |

`eval/judge/AGENTS.md` is shared with task 104. If you need to write there, **append a new
section with its own heading** rather than editing an existing bullet, so a merge takes both sides.

### Where the check belongs, and the constraint that decides it

`eval/tools/lint.py` **is not a gate and that is deliberate** — read its docstring. It exits 0 with
findings unless `--gate` is passed, and *nothing calls `--gate`*. Its selection (`LINT_SELECT`,
`LINT_ROOT`, `LINT_EXCLUDE`) is imported from `prune_scan.py` and deliberately not restated,
because two files spelling one rule set disagree eventually (rule 12).

So `lint.py` is the wrong home for something that must go **red**. The `refs` line naming it is the
ticket's guess at a location, not a decision — treat it as one input. The shapes already in the
repository:

- **a `*_control.py`** — `findings_control.py`, `withdrawn_control.py`, `tasks_control.py` and five
  others. Each prints `N measurements, M FAILED, K NOT CHECKED` and exits non-zero on a failure.
  This is the shape that matches your `done_when`, because it can carry the red pin *and* the green
  one in the same run and report both.
- **a `docstat.py --<flag>`** — for things that sweep documents. Yours sweeps code. And `docstat.py`
  is taken by task 89.

**Decide it and say why in the commit.** A `*_control.py` that runs an AST census over
`eval/judge/` and asserts it names `PlatformerBot._approach` at `9fc044a` and does not name it at
HEAD is a shape this repository already has seven instances of; `tasks_control.py`'s new
direction 6 (commit `03cdb90`) is a worked example of pinning a historical tree by reading blobs
through `git cat-file` rather than checking anything out.

### The red pin must come from git, not from a reconstruction

`PlatformerBot._approach` does not exist at HEAD. Read it as a **blob** at `9fc044a` — the same
discipline `tasks_control.py` uses for its own positive control, and for the reason stated there:
*a defect retyped from memory is a defect you have already decided the shape of.* If the census
runs over a directory, materialise `9fc044a`'s `eval/judge/` into a scratch dir from git and point
the census at it; if a shallow clone has no such commit, that is **NOT CHECKED**, not a pass.

### Rule 15: your `done_when` asks for the mutant half only

Red-on-`9fc044a` / green-on-HEAD asks *can this check fail*. It does not ask *can it still pass on
an input it mishandles*, and every false negative this project has adjudicated has been of the
second kind. Before closing, construct at least these and record what each did:

- a method reached only by `getattr(self, name)` where `name` is built at runtime
- a method named only inside a string or a docstring
- a method referenced by an alias (`f = self._helper`) rather than called
- a method whose only caller is **itself** dead — the `_turn_corner` cluster is a live instance,
  so this one is free

A census that reports every one of those as dead is worse than no census: it will be switched off.
One that reports none of them as dead may be reporting nothing at all — say which, with numbers.

### On the exemption list

The ticket says an allowlist is fail-open by rule 7 and it is right, but **"no exemptions" is also
a decision that has to survive `_turn_corner`.** The three options are: delete the cluster and move
its measured-and-discarded docstring somewhere an archive keeps it (`eval/findings/` or
`eval/judge/AGENTS.md`); keep it behind a mechanism that is not a bare name match (a marker the
census reads, which is still an exemption but one that names *why*); or conclude the check costs
more than it protects and close this with that measurement. **All three close the task.** The one
outcome that does not is a green check whose green was bought by an unexplained allowlist entry.
