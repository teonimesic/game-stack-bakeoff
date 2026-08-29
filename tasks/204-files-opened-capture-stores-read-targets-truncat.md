---
id: 204
title: files_opened capture stores read targets truncated to 200 characters
status: done
priority: 4
refs: eval/judge/field.py, eval/judge/prompt_capture_census.py, DECISIONS.md
done_when: field.py stores the full read target, or a cap stated and measured above any real path length; the change pinned in a selftest (a target exceeding the old cap stores untruncated); prompt_capture_census.py kept green against the stored corpus, whose rounds remain 200-capped and whose truncated targets stay refused as malformed, never re-read as carried or un-carried; and a dated one-line note where DECISIONS.md or eval/RUNS.md holds such notes, stating the audit field changed shape and that scored rounds are unaffected (files_opened is scored by nothing). docstat.py --sweep exit 0 unpiped after.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/83
established_by: 'Orchestrator merge, verified against artifacts at branch head bbc62c36cea30b88c8ff8f575e0007820922a4a9: str(target)[:200] absent from field.py, full storage at the capture site; files_opened_selftest exit 0 green and re-turned RED by me (exit 1, 5 FAIL rows) under a re-applied cap, then restored clean; prompt_capture_census corpus re-run byte-identical to the 201/202 answers (57 rounds / 39 captures / 18 absent / 0 null / 0 malformed / 0 truncated / 0 un-carried); census selftest, blurb_selftest, ci_minutes --selftest, sweep (270 docs), tasks check all exit 0 unpiped; RUNS.md carries the dated shape-change note with the stored-corpus truncated-refusal arm kept; gates.yml 70 to 71 pinned in ci_minutes; required checks green at the head, no unresolved threads, round-2 review clean; squash-merged as fd3e1d4.'
---

field.py:1634 stores str(target)[:200] into the files_opened audit log, so a judge read whose target exceeded the cap is stored with its tail - typically the filename - gone. The census built in PR #81 (prompt_capture_census.py) had to refuse exactly-200-char targets from classification for exactly this reason, and refusal only bounds the damage: a truncated target cannot later be shown to be, or not to be, a read of un-carried evidence. The stored corpus holds 0 such targets (57 usable rounds re-read 2026-08-28), so nothing recorded is damaged - the defect is in the capture going forward. The audit-trail rule: record the inputs a component actually consumed. A capture that degrades its own entries below classifiability fails that for any future question about what a judge opened.

## note 2026-08-28 (orchestrator, before dispatch) - the line number has moved

Task 202 merged (a29b35b) and deleted pack_parity (30 lines) from field.py ABOVE the capture site, so the store this ticket is about is no longer at line 1634 - locate it by content (str(target)[:200], in the files_opened capture) rather than by the line number quoted here or in PR #81's records. prompt_capture_census.py is on main: its selftest already pins the malformed/truncated arms the done_when requires kept green, and its corpus answer at merge time was 0 truncated targets in 57 usable rounds - your change must not move that 0, and the census is the consumer that decides.

## note 2026-08-28

## note 2026-08-28 (worker, on completion) - what the next session would otherwise re-derive

**The fix is full storage, not a larger cap.** The capture at `field.py` `run_field`'s `reads.append` now stores `str(target)` with the reasoning at the site. A replacement cap at any length N would recreate the same unclassifiability at exactly N for future rounds - and the census refuses exactly-200 stored targets, so a new cap's truncations would classify as `other` and read as false un-carried leaks, the direction the census says it must not fail in. Full storage leaves no future ambiguity class; the census's 200-arm now governs only the stored corpus (everything captured before 2026-08-28 stays 200-capped and stays refused).

**The selftest was written first and run red against the capped capture** - 5 rows failed, each naming 200-character storage. The red run also caught a defect in the selftest itself: the tail-intact row asserted the fixture string (`_LONG_PATH.endswith(_TAIL)`, always true) instead of the stored target. It reads the STORED target now. If you extend this selftest, keep that direction: every row's subject is what the capture stored, never the input that produced it.

**The census changed wording, not behavior.** Its docstring, inline comment, refusal print and fixture comments said "the capture stores `str(target)[:200]`" in present tense; they now date the cap to 2026-08-28 and say stored rounds remain capped. `--selftest` green, corpus re-run against the main checkout: 57 rounds, 39 captures, 0 truncated, 0 un-carried - identical to the task 201 merge answer.

**Registering a new judge selftest moves 3 pinned counts, not 2.** `gates.yml` step + `.github/workflows/README.md` paragraph are the obvious two; `ci_minutes.py`'s own selftest carries a literal `check("gates.yml gate count", ..., 70)` that must become 71, and two README rows (the opening table, "pre-push runs 6 of 71") move with it. `ci_minutes --selftest` names each one it finds stale.

**CodeRabbit round 1 proposed a capture-format marker in `provenance`** (classify 200-char targets from marked records normally). Declined on PR #83: it is the fail-open direction (a wrongly-written marker classifies a genuinely truncated target, while today's refusal is conservative and itemises the full target), the ticket pins the refusal arm, and the case has no measured need - 0 truncated targets in 57 rounds. If the truncated column ever fires on a post-2026-08-28 round, that itemised firing is the measured trigger to reconsider. Round 2 came back clean; the run-line comment (`python3 judge/...`) is the folder-wide docstring convention, six siblings carry it - do not "fix" it again.
