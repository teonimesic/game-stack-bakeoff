---
id: 197
title: README.md carries 10 fenced commands naming bare judge/ paths that the path censuses never scanned
status: done
priority: 3
refs: README.md,eval/FINDINGS.md,tasks/193
done_when: 'Every command line in the README fences both declares its frame and resolves from it: pick the frame (repo root is what README is for - it is the front door), make each path resolve from it consistently INCLUDING the runs/<name> arguments, and verify by actually running the two cheapest named commands from the declared frame (the selftests with no --run argument; tokval-cheap offline tools only, nothing that spends account capacity). The update-readme skill governs any README edit. docstat.py --sweep and linkcheck.py exit 0 unpiped after.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/75
established_by: 'Verified against artifacts at 9cd7bb8b in the agent worktree: diff is README.md only (26+/23-); cd eval deleted, all paths eval/-prefixed, run args eval/runs/<name>; the two broken lines repaired to what the tools actually parse. Reproduced myself: regrade_wholegame --run-dir and verify_blind --run-dir both exit 2 unrecognized-arguments (read unpiped after a pipe ate the first reading); argparse confirms positional run_dir (regrade:112) and paths nargs=* (verify_blind:225); the new comment''s claim reproduced - verify_blind on a stored run dir reports RUBRIC REACHABLE per trial and exits 0; regrade_wholegame read-only on a stored run exits 0 dry; capability_selftest and capture_selftest run as spelled from repo root, both exit 0; sweep/linkcheck/tasks check exit 0 at the head. Review: round 1 one Minor accepted (ambiguous prints-this-line phrasing), round 2 LANDED_COMMENT clean. Known drift recorded in the ticket for a follow-up: run-matrix and evaluate-run skills invoke verify_blind bare, which has exited 2 since the tool''s first commit - outside this ticket''s README scope. Merged: update-branch for c504021+7c51c05, then --squash --auto.'
---

Root README.md carries 10 fenced lines with bare judge/ paths (python3 judge/field_sweep.py, judge/bot_mutants.py, judge/audio_selftest.py and 7 more; verified 10 in fences, 0 inline, by the orchestrator during task 193 verification). They were invisible to the task-193 filing census, which read inline backticks only - the method lesson recorded as finding #208 - and README was therefore never in that ticket document set, so the repairs stopped at the four root-frame files. judge/ does not exist at the repository root, so IF the fence frame is the repo root these are the confidently-wrong class: a reader copies and runs them and gets no such file. But the frame is the first thing to adjudicate, not assume: if the surrounding section declares a working directory (a cd eval line in the fence, or prose saying run from eval/), the bare forms may be correct-in-frame and the defect is instead the undeclared or contradictory frame. eval/AGENTS.md files judge/AGENTS.md was left bare for exactly this reason by task 193. Note the sibling args: the same fences say --run runs/<name>, which is only correct from eval/ (the stored runs are at eval/runs/) - so the fence as written is most likely INTERNALLY inconsistent: paths for one frame, arguments for another. Read the surrounding section before touching anything.

## note 2026-08-28

## note 2026-08-28 (task agent) — frames settled, PR #75

**The fence was NOT internally inconsistent in the way the ticket hypothesised.** The
`Running things` fence (README's only fence; it held all 10 bare `judge/` lines) declared
`cd eval` at line 259, and from that frame the bare `judge/` paths AND the `runs/<name>`
arguments both resolve - paths and arguments were the SAME frame, not two. The real
inconsistencies were: (1) the fence's FIRST line, `cd eval/starters/rust && just verify`,
is repo-root-frame, so pasting the whole fence breaks at the `cd eval`; (2) every other
producer command in README (lines 74, 150, 226, 232, 315) is already repo-root-frame.
Frame chosen per the ticket: repo root. `cd eval` deleted; every path carries its frame;
runs args are `eval/runs/<name>`.

**Two lines were wrong past the frame, and no frame fixed them** - found while verifying:

- `judge/regrade_wholegame.py --run-dir runs/<name>`: the tool takes a POSITIONAL
  `run_dir`; `--run-dir` exits 2 "unrecognized arguments" from any directory. Repaired to
  the positional.
- `judge/verify_blind.py --run-dir runs/<name>`: also positional (`paths`), and the TARGET
  was wrong too - verify_blind checks trial working trees and walks every ANCESTOR to the
  filesystem root, so aiming it at a stored run dir under eval/runs reports RUBRIC
  REACHABLE (true, not the question; the same false positive precampaign_smoke.py
  documents for `starters/`). It moved to its real place with the command
  `wholegame.py build` itself prints (wholegame.py:751):
  `python3 eval/judge/verify_blind.py <work-root>/<name>/*/`.

**Verification (both directions, offline, no account spend):** broken - the fence-as-written
`python3 judge/audio_selftest.py` exits 2 from the root; `--run-dir` on both tools exits 2
regardless of frame. Green - from the repo root exactly as the fence now spells them:
capability_selftest 0.26s, capture_selftest 2.25s (the two cheapest, as the ticket asks),
plus rusage 7.3s and audio 9.1s, all exit 0. Read-only end-to-end against stored runs in
the main checkout: regrade_wholegame dry-run exit 0, `runner.py report` exit 0,
`capability.py --runs` exit 0 on the four-arm wg-g4c run and exit 1 on the scene-only run
(its gate refusing a population it cannot check - the can-fail direction). Extraction
census over the repaired fence: 18 path tokens, all resolving from a repo root holding
stored runs (the 3 worktree misses are gitignored `eval/runs/*`, proven resolving in the
main checkout). `field_sweep.py`'s line was NOT executed - it spends account capacity,
which the ticket excludes; its path handling is the same `type=Path` direct-use pattern as
the four data-taking lines that were run.

**For the orchestrator - a drift found while verifying, outside this ticket's scope:**
the run-matrix and evaluate-run skills invoke `python3 judge/verify_blind.py` BARE, and
bare has exited 2 ("give trial directories, --packs, or both") since the tool's initial
commit - the invocation needs positionals (precampaign_smoke.py passes copies of the
starters). Both skills also render the eval-frame `judge/` paths this ticket's class
covers, though their frames are declared ("Run from `eval/`"), so only the bare-invocation
half is a defect. Worth a task; not repaired here.

Gates at PR #75's head, all unpiped: docstat.py --sweep (263 docs), --findings,
--withdrawn, linkcheck.py (--selftest first), tasks.py check - all exit 0. The triage
anchor `keeps the other (#100, #103)` preserved verbatim. No finding number allocated.

## note 2026-08-28

## note 2026-08-28 (task agent) — review rounds 1 and 2, handing back in_testing

**Round 1 (at fadc0cd9) landed one Minor thread, accepted and fixed.** It read the comment
above the verify_blind line and found "prints this line" ambiguous - "this line" could name
the comment itself, and the line `wholegame.py build` prints is EVAL-frame
(`judge/verify_blind.py {work_root}/*/`, wholegame.py:751) while the README line is
root-frame, so the phrase invited a false exact-match reading. The comment now states the
rule and the action without the reference: build prints the work root (true of its
`work root: ...` output, wholegame.py:737); pass its trial trees to verify_blind; never a
stored run directory. All three facts kept; the glob and the command untouched. Pushed as
9cd7bb8, one push for the one fix.

**Round 2 (at 9cd7bb8) landed CLEAN** - LANDED_COMMENT, no review object, nothing
unresolved, nothing in flight (own poll, exit 0, 158s); gates and controls SUCCESS at that
head. Loop stopped there, 2 rounds of a 5 ceiling.

**Not acted on, deliberately:** the suggestion's proposed wording folded
regrade_wholegame's provenance into the blinding comment, duplicating the section comment
already above that line; the accepted fix keeps one concern per comment. Main moved 3
commits (queue-state, tasks/ only, no overlap with this diff) - branch currency left to
the orchestrator at merge time per dispatch.

Everything else stands as in the note above: frame adjudication, the two positional-flag
defects, both-direction verification, gates. No finding number allocated; the census
method lesson was already filed as #208 by task 193.
