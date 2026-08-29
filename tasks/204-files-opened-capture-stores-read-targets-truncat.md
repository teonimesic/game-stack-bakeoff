---
id: 204
title: files_opened capture stores read targets truncated to 200 characters
status: todo
priority: 4
refs: eval/judge/field.py, eval/judge/prompt_capture_census.py, DECISIONS.md
done_when: field.py stores the full read target, or a cap stated and measured above any real path length; the change pinned in a selftest (a target exceeding the old cap stores untruncated); prompt_capture_census.py kept green against the stored corpus, whose rounds remain 200-capped and whose truncated targets stay refused as malformed, never re-read as carried or un-carried; and a dated one-line note where DECISIONS.md or eval/RUNS.md holds such notes, stating the audit field changed shape and that scored rounds are unaffected (files_opened is scored by nothing). docstat.py --sweep exit 0 unpiped after.
---

field.py:1634 stores str(target)[:200] into the files_opened audit log, so a judge read whose target exceeded the cap is stored with its tail - typically the filename - gone. The census built in PR #81 (prompt_capture_census.py) had to refuse exactly-200-char targets from classification for exactly this reason, and refusal only bounds the damage: a truncated target cannot later be shown to be, or not to be, a read of un-carried evidence. The stored corpus holds 0 such targets (57 usable rounds re-read 2026-08-28), so nothing recorded is damaged - the defect is in the capture going forward. The audit-trail rule: record the inputs a component actually consumed. A capture that degrades its own entries below classifiability fails that for any future question about what a judge opened.

## note 2026-08-28 (orchestrator, before dispatch) - the line number has moved

Task 202 merged (a29b35b) and deleted pack_parity (30 lines) from field.py ABOVE the capture site, so the store this ticket is about is no longer at line 1634 - locate it by content (str(target)[:200], in the files_opened capture) rather than by the line number quoted here or in PR #81's records. prompt_capture_census.py is on main: its selftest already pins the malformed/truncated arms the done_when requires kept green, and its corpus answer at merge time was 0 truncated targets in 57 usable rounds - your change must not move that 0, and the census is the consumer that decides.
