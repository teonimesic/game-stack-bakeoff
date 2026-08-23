---
id: 100
title: A dead private method in a judge module is a conclusion waiting to rest on it - make the census a gate
status: done
priority: 3
refs: 'eval/findings/certifies-nothing.md #136, eval/judge/bot_arena.py _turn_corner, eval/judge/probe.py Bot._num, eval/tools/lint.py'
done_when: a check exists that goes RED on a tree containing PlatformerBot._approach as committed at 9fc044a and GREEN on the current tree, both run and both reported - a green with no red establishes nothing. The two current hits are each resolved by deletion or by a mechanism that is not a bare name allowlist, and the docstring measurement inside _turn_corner is preserved wherever it ends up. Whichever way it goes, the census numbers are stated in the evidence string. If the conclusion is that the check is not worth its exemptions, that is a result and closes this - say what the measured cost was.
established_by: 'eval/tools/dead_private_control.py, 18 measurements, 0 FAILED, 0 NOT CHECKED, exit 0. RED FIRST, then green: direction 2 was run BEFORE the deletions and FAILED, naming ArenaBot._corners at bot_arena.py:686, _far_corner:690, _turn_corner:693 and Bot._num at probe.py:539 out of 122 private methods in 78 files; after the deletions it is 118 methods, 0 dead. The historical red pin reads 9fc044a as blobs through git cat-file with nothing checked out and nothing retyped: 61 files, 121 private methods, 3 dead - _approach, _num, _turn_corner - which reproduces the #136 published figure to the digit, and direction 1c pins the hit as PlatformerBot._approach at bot_platformer.py:695 rather than a namesake. THE CLUSTER PROBLEM IS SOLVED BY REACHABILITY, NOT BY AN EXEMPTION, and it is pinned from both sides on the real tree at 03cdb90: the per-method census of #136 names 1 of the 3 cluster members, forward closure from roots outside any private method body names 3 of 3. DESIGN QUESTION DECIDED: deletion, with zero exemptions of any kind - no allowlist, no marker - so nothing in the green was bought. Bot._num had exactly one occurrence in the whole repository, its own def, and went with its now-empty helpers header. The corner cluster went AFTER its measurement was moved: _turn_corner''s docstring held a different number from the one already in _chase - mean per-tick alignment 1.00 on both legs and a heading swing of exactly 0.00, against _chase''s existing 0.36 out of 2.00 for the opposite-corner design it superseded - so _chase''s docstring now records three discarded designs instead of two and names 03cdb90 as where the code is. RULE 15, ten variant rows asserting what the census DOES: 4 of 4 live-by-a-tricky-mechanism come back live (literal getattr, a dispatch table of literal names, an alias never called, a class-body bare name), 3 of 3 genuinely dead come back dead (a plain uncalled method as the true positive, a self-recursive method, a mutually recursive pair), and the 2 it gets wrong are pinned as rows rather than hidden - a name assembled at runtime reads dead (false positive, fail-closed, 0 such sites in eval/judge today since all three getattr calls take a literal or a non-private attribute) and a method named only in another method''s docstring reads live (false negative, the price of the rule that keeps the four live rows alive). A comment is NOT a reference and that is load-bearing: _approach appeared in all five trees that defined it as its own def line and as two comments, so a census reading comments would have been green on the tree that published #82. Population includes eval/judge/fixtures which lint.py excludes, deliberate so that direction 1b can assert against #136''s 121, and measured rather than assumed - fixtures contribute 0 dead of 50 methods in 29 files at 9fc044a, at 03cdb90 and at HEAD, in both modes. GATES: docstat.py --sweep clean exit 0, tasks.py check 108 tasks all well-formed exit 0, lint.py adds 0 findings for the new file, bot_mutants.py --only enemies.chase --skip-lock-controls green with healthy PASS and mutant FAIL and 0 expectations unmet. Decision and its reversal condition in DECISIONS.md, the operating guidance in a new section of eval/judge/AGENTS.md. Branch task-100-dead-private-method-census.'
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

## Done, 2026-08-23 — what shipped, and what the next agent must not re-derive

**The check is `eval/tools/dead_private_control.py`.** 18 measurements, exit 0. NOT `lint.py`:
`lint.py` exits 0 with findings by decision and its `--gate` flag has no caller, so a check that
must go red does not belong behind it. The control shape carries the red pin and the green pin in
one run, which is what `done_when` asked for.

### The four directions, and the numbers

| direction | what it establishes |
|---|---|
| 1 red pin, `9fc044a` read as blobs through `git cat-file` — nothing checked out | 61 files, **121 private methods, 3 dead** — `_approach`, `_num`, `_turn_corner`. Reproduces #136's published figure exactly, including the count, so a change to the extraction disagrees with the archive rather than quietly producing a new number. 1c asserts the hit is `PlatformerBot._approach` at `bot_platformer.py:695` and not a namesake |
| 2 green pin / the gate, live `eval/judge/` | **before** the deletions: FAILED, naming all four — `ArenaBot._corners:686`, `_far_corner:690`, `_turn_corner:693`, `Bot._num` at `probe.py:539`, out of 122. **After**: 78 files, **118 private methods, 0 dead**. The red was run first; the green is not a fix testing itself (rule 14) |
| 3 the cluster, both modes, on the real tree at `03cdb90` | shallow names **1 of 3**, reachability **3 of 3**. This is why the mode exists and it is pinned from both sides — a reachability step that over-fires breaks 2, one that is removed breaks 3b |
| 4 rule 15, ten variant rows | see below |

### THE DESIGN QUESTION, decided: deletion, no exemption of any kind

- `Bot._num` — **deleted** with its now-empty `# helpers shared by the concrete bots` header. It
  had exactly one occurrence in the whole repository: its own `def`. Nothing to preserve.
- the corner cluster — **deleted**, and the measurement moved first. `_turn_corner`'s docstring
  recorded a *different* number from the one already in `_chase` (alignment 1.00 on both legs and
  a heading swing of exactly **0.00**, against `_chase`'s existing 0.36-of-2.00 for the
  *opposite*-corner design it superseded). `_chase`'s docstring now records **three** discarded
  designs instead of two, names `03cdb90` as where the code is, and says why the third was worse.
  Evidence lands somewhere before the code goes.

No allowlist, no marker, no exemption — so there is nothing in the green that was bought.
`DECISIONS.md` carries the decision and a reversal condition: it re-opens on a real
`getattr(self, <name built at runtime>)` in `eval/judge/`, of which there are **0** today (all
three `getattr(` sites there take a literal or a non-private attribute), and the repair then is a
marker the census reads that names *why*, never a bare name list.

### Rule 15 — the census gets two things wrong, and both are pinned as rows

Ten variants, each asserting **what the census does**, so widening the string rule cannot lose
either silently:

- **correctly live** — literal `getattr(self, "_step_once")`, a `{"tick": "_handler"}` dispatch
  table, an alias `f = self._helper` never called, a bare-name reference from the class body.
- **correctly dead** — a plain uncalled method (the true positive, without which the harness is
  vacuous); a self-recursive method whose only caller is itself; a mutually-recursive pair dead as
  a whole. The last two are named live by shallow and dead by reachability, and both modes are
  asserted on each.
- **KNOWN FALSE POSITIVE** — `getattr(self, "_han" + suffix)` reads dead. Fail-closed: costs a
  minute, cannot excuse a real failure.
- **KNOWN FALSE NEGATIVE** — a method named only in another method's docstring reads live. This is
  the price of the rule that keeps the four live rows alive, and it is the direction anyone
  widening string handling must not lose.

So the answer to *"does it report all of them dead / none of them dead"* is **neither**: 4 of 4
live-by-a-tricky-mechanism come back live, 3 of 3 genuinely dead come back dead, and the 2 it gets
wrong are named.

### Facts worth not re-deriving

- **A comment is not a reference and that is load-bearing, not an oversight.** In all five trees
  that defined it, `_approach` appeared as its own `def` line and as two *comments*. A census that
  read comments would have been green on the tree that published #82.
- **The population includes `eval/judge/fixtures/`, which `lint.py` excludes.** Deliberate, and
  documented in the tool: #136's 121 counts them and direction 1b asserts against that figure.
  Measured, not assumed — the fixtures contribute **0 dead of 50 methods in 29 files** in all
  three trees (`9fc044a`, `03cdb90`, HEAD), in both modes.
- A method name defined in two classes is live for both if either is reached. Under-reports rather
  than crying wolf, which is the right direction for a gate.
- `bot_mutants.py --only enemies.chase --skip-lock-controls` is green after the deletion
  (healthy PASS / mutant FAIL SCORED, 0 expectations unmet, exit 0) — the criterion whose
  docstring absorbed the evidence still works.

### No finding number needed

Nothing here ran and measured nothing. #136 is the finding; this is its detector.
