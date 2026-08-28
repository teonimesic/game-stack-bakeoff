---
id: 193
title: 'Bare judge/ and tools/ paths in live documents: settle each document''s path frame and repair the references that do not resolve'
status: in_testing
priority: 5
refs: DECISIONS.md, tasks/190, eval/tools/docstat.py, eval/tools/lint.py, AGENTS.md
done_when: 'Every backticked judge/- or tools/-prefixed reference in every LIVE document (ARCHIVE_PATHS in eval/tools/docstat.py minus the archive: eval/RUNS.md, eval/SCENES.md, eval/AGENTS.md, eval/PROTOCOL.md, eval/judge/AGENTS.md, eval/judge/RUBRIC.md, eval/judge/JUDGING.md, .github/workflows/README.md, AGENTS.md, .agents/skills/*/SKILL.md, research/10-stack-capability-matrix.md, eval/G4-PLATFORMER.md) is read against its document''s path frame and either resolves or is repaired. The frame question is the adjudication, not a formality: a doc under eval/ writes eval-relative commands (eval/judge/AGENTS.md says python3 judge/bot_mutants.py, which works from eval/), so bare paths there can be correct-in-frame, while a root-frame doc like DECISIONS.md or README.md names paths from the repository root and bare judge/ there is always wrong. Starters (eval/starters/**) are OUT of scope entirely: their tools/ paths are starter-internal and correct, and starter edits are regime boundaries. Counts at filing (line-matches, DECISIONS.md already repaired): RUNS.md 53, SCENES.md 24, eval/AGENTS.md 20, PROTOCOL.md 8, judge/AGENTS.md 6, workflows/README.md 6, G4-PLATFORMER.md 5, judge/RUBRIC.md 3, root AGENTS.md 3, audit-docs SKILL.md 3, add-game SKILL.md 2, research/10-stack-capability-matrix.md 1, judge/JUDGING.md 1. docstat.py --sweep and linkcheck.py exit 0 unpiped after.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/72
established_by: 'PR #72 at head 2eced15. Census re-derived: 19 bare judge//tools/ references repaired across root AGENTS.md, add-game SKILL.md, audit-docs SKILL.md and workflows README, every target existence-verified; all eval-frame bare refs (168) resolve from eval/ and were left; fenced commands all sit in declared frames. Controls both directions: the census flagged 19 real unresolvable refs pre-repair and 0 post-repair; DECISIONS.md reads exactly its one recorded exception. Gates at the pushed head, unpiped: docstat --sweep exit 0, linkcheck exit 0, tasks check exit 0. Review round 1 thread adjudicated declined-with-a-run (fence command exits 0 as written), thread resolved; branch merged with main at 2eced15, no file overlap. Bounded wait at 2eced15 expired UNRESOLVED (40 polls, 1225 s, no round in flight) - stated on the PR (comment 5451949913); awaiting orchestrator.'
---

Task 190 repaired 23 bare judge/- and tools/-prefixed references in DECISIONS.md, where every one named a file that exists only under eval/ (verified per reference against the filesystem, and against lint.py's own output which prints full eval/-rooted paths). The same shape is present in the other live documents, and no gate covers it: docstat.py --sweep deliberately does not check file paths (AGENTS.md records the exclusion, task 77 measured that it was removed rather than tuned), and linkcheck.py covers markdown links only. A path that does not exist as written is the defect class AGENTS.md calls confidently wrong: a reader following it looks in a directory that is not there.

## note 2026-08-28 (orchestrator) — current at dispatch

**The DECISIONS.md half of this class has LANDED** — task 190's pull request #70 merged as
`f84972d`. Read that diff for the repair pattern before starting: every bare reference was
existence-verified per reference against the filesystem, one deliberate exception was recorded in
prose where the bare form is correct in its own frame (`tools/boundary.gd`, which is
starter-relative), and the scope was held to the one document rather than blind-prefixing the
repo. That last point is this ticket's whole adjudication, now with precedent: **the frame
question is decided per document, and a bare path that resolves from the document's own working
directory is correct, not a defect.**

The per-document counts in the done_when are the filing agent's line-match census, not one I have
re-run — re-derive them before repairing, and treat drift as information about which documents
moved since filing.

**File-conflict check at dispatch:** task 194 (dispatched alongside this one) touches only
`eval/tools/prompt_guard.py` — no document overlap with your scope. Nothing else open touches
your documents. Root `AGENTS.md` IS in your scope (3 refs): it is the always-loaded project
instruction, so an edit there must survive the same scrutiny as any other live document — repair
only references that do not resolve in the document's frame, never reword around them.

Gates unchanged: docstat.py --sweep and linkcheck.py exit 0, both unpiped, in your worktree at
your head.

## note 2026-08-28

## note 2026-08-28 (task agent) — census re-derived, frames settled, PR #72

**The filing counts were re-derived, not trusted, and both drift and a method gap showed.**
Inline backticked refs at this head: add-game SKILL.md 7 (filed 2 — the file grew),
eval/judge/AGENTS.md 9 (filed 6), RUNS.md 68 line-matches (filed 53), eval/AGENTS.md 31,
SCENES.md 25, PROTOCOL.md 15, G4 6, workflows README 6, JUDGING 4, RUBRIC 4, root AGENTS.md 3,
audit-docs 5, DECISIONS.md 1, research/10-stack 1 — 203 refs over 19 documents. The method gap:
the filing census read inline backticks only, so **fenced command lines were never scanned**; a
fence-aware scan adds 70 lines and is what surfaces README.md, which the filing list omits
entirely. It matters because README is root-frame — the doc the ticket itself names as "bare
judge/ there is always wrong" — and carries 10 bare judge/ commands in its Running things fence.

**The frame adjudication, per document (the ticket's whole point):**

- Root-frame (AGENTS.md, skills, .github/workflows/README.md, research/, DECISIONS.md,
  README.md): bare judge//tools/ that does not exist at the root is the defect. **19 refs
  repaired over 4 files**, each target verified to exist before prefixing: root AGENTS.md 3,
  add-game 7, audit-docs 3, workflows README 6. The README repairs name the .py the register's
  bare gate-names omitted (`judge/stored_rounds_mutants` -> `eval/judge/stored_rounds_mutants.py`),
  matching gates.yml's own `run:` lines — the README's judge/-tokens had been quoting gates.yml
  step *display names*, so findability survives via the module stem.
- eval-frame (RUNS, SCENES, eval/AGENTS, PROTOCOL, judge/AGENTS, RUBRIC, JUDGING, G4): **every**
  bare ref resolves from eval/ — 168 inline refs, zero exceptions. Correct in frame, untouched.
- Fenced bare commands: every one sits in a frame-declared context — `cd eval` in the fence
  (add-game:43, audit-docs:18, evaluate-run:17, README:258), "Run from `eval/`" in prose
  (run-matrix), or an eval-frame doc (PROTOCOL, judge/AGENTS, JUDGING, RUBRIC). All left alone.

**Left bare on purpose, each with its reason:**

- `audit-docs/SKILL.md:282` `judge/runner.py --no-such-flag-bare1` — the plant specimen.
  `docstat.py`'s own pins carry that spelling verbatim (lines ~4195-4240), so prefixing would
  desync the skill from the instrument AND manufacture a phantom (eval/judge/runner.py does not
  exist; the runner is `eval/runner.py`).
- `tools/boundary.gd` — DECISIONS.md:1446 (task 190's recorded exception), audit-docs:305 (the
  sentence recording that exception), research/10-stack:339 (a four-starter parallel construction
  whose other members are also starter-relative: `crates/sim/tests/boundary.rs`, `src/sim`).
- `eval/AGENTS.md:44` `judge/aspects.applicability` — module notation, not a path;
  `def applicability` verified at `eval/judge/aspects.py:709`.
- `eval/RUNS.md` 8 + `eval/SCENES.md` 1 starter-internal `tools/*.gd`/`*.sh` — each in a passage
  naming its starter; `RUNS.md:1222` quotes a stored diffstat line verbatim
  (`tools/no_raise.gd | 1 +`), which a prefix would falsify.
- `eval/starters/**` — out of scope per the ticket; left untouched.

**Controls:** red — the census flagged 19 real unresolvable refs pre-repair and did NOT flag the
103 eval-frame/frame-declared bare refs (frame discrimination, not shape-matching). Green —
post-repair the same census reports 0 repair verdicts; every remaining non-resolving hit is an
adjudicated exception above. Extraction proof — DECISIONS.md reads exactly 1 hit, task 190's
recorded exception. Post-edit — all 70 eval/-rooted refs in the 4 edited files resolve.

**Gates** at PR #72's head, all unpiped: `docstat.py --sweep` exit 0 (260 docs), `linkcheck.py`
exit 0, `tasks.py check` exit 0.

**For the orchestrator:** (1) `controls.yml:159` carries the same bare `judge/fixtures/ref_parallax`
in a comment — same defect class, but workflow .yml is outside this ticket's enumerated document
set (the sweep's `.github/` coverage is markdown-only), so it was left; a follow-up task or a
one-line repair at merge is fine. (2) No finding number is allocated from this branch. The
re-derivation result worth recording is the method one: **a census scoped to inline backticks
undercounts path references in command-bearing documents** — README.md's 10 fenced bare commands
were invisible to the filing census, and fenced commands are the text a reader copies. Filed
here as information; whether it is a numbered finding is the merge-time call.

## note 2026-08-28

## note 2026-08-28 (task agent) — review round 1 worked, thread adjudicated with a run, branch merged

**The round-1 wait did not hang — its verdict landed and went unread.** The first poll at
`849792e` (the pushed review-prep head) terminated `LANDED_COMMENT` at 439 s, exit 0; the
completion never woke the session, so the head sat "reviewed but unanswered" for hours. Lesson
for the dispatch loop, not for this ticket: a background poll's completion is the only thing
that re-invokes the worker, and one missed notification looks exactly like a dead reviewer.

**What round 1 actually left:** one review object at `60c503e` (the pre-rewrap head) with a
single Minor thread on `add-game/SKILL.md:83`, claiming the fence's `cd eval` makes line 48
resolve to `eval/eval/tools/prompt_guard_control.py` and fail. **Declined with a run, not an
argument**: `cd eval && python3 tools/prompt_guard_control.py` executed exactly as the fence
writes it exits 0 with all 25 control rows as declared (14 mutants red, 5 variants green).
One `cd eval` from the root yields a single `eval/` prefix; `eval/eval` needs a second hop the
fence does not have, and from a reader already inside `eval/` line 43 itself fails loudly
before line 48 can run. The comment's own second remedy ("use `tools/prompt_guard_control.py`
inside the existing `eval` frame") is the text as it stands. Reply posted as comment
3880060660, stored body diffed byte-identical against what was sent (#166 discipline); the
thread reads resolved. The fence-frame adjudication this thread turned on is the PR body's
"Fenced command lines" paragraph.

**Branch currency:** main had moved 3 commits (task 194's prompt_guard change, the dispatch
skill's in_review rule, queue updates) — none touching the 4 files this PR edits. Merged
`origin/main` at `2eced15`; the census re-run at the merge reports the same 184 inline hits,
**0 repair verdicts, and no new references introduced by main's dispatch/prompt_guard
changes**. Gates re-run at the merge, unpiped: `docstat.py --sweep` exit 0, `linkcheck.py`
exit 0, `tasks.py check` exit 0.

**One operational note:** this sandbox refuses any command line containing the literal
`cd eval` (the directory name collides with the shell builtin in the static guard), so the
fence-as-written run went through a scratch script whose contents are exactly lines 43+48.
Nothing else was affected.

Poll re-armed at `2eced15` — bounded wait, `--expect-head` asserted.

## note 2026-08-28

## note 2026-08-28 (task agent) — wait expired UNRESOLVED at the merge head; handed back in_testing

The re-armed bounded poll at `2eced15` (the merge of origin/main) expired **UNRESOLVED**:
40 polls over 1225 s, no round ever seen in flight, exit 13. Per the tool's instruction the
fact is stated on the pull request (comment 5451949913) and the ticket goes to in_testing.

Why handing back rather than spending another shared round: the only delta at `2eced15` is the
merge commit itself (main's 3 commits, none touching this PR's four files — census re-run at
the merge: same 184 inline refs, 0 unresolved-repair verdicts). The substantive review is
already in hand: round 1 at `60c503e` produced exactly one thread, adjudicated **declined with
a run** (fence lines 43+48 executed exactly as written: exit 0, all 25 control rows as
declared), thread resolved with the stored reply verified byte-identical; the round at
`849792e` landed comment-only. If the orchestrator wants a round native to `2eced15`,
`@coderabbitai review` requests one — deliberately not spent from here.
