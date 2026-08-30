---
id: 218
title: 'The capture census reads half of what a judge round records: 2,308 stored Bash tool calls are invisible to its population, and its six states still sum to n'
status: done
priority: 2
refs: 'eval/judge/prompt_capture_census.py, eval/judge/field.py (run_field''s tool_calls capture, task 204), eval/RUNS.md (the 2026-08-28 pre-registration), #131, #203, #201, #53, tasks/204'
done_when: 'prompt_capture_census.py (or a named sibling it defers to) also classifies Bash and Grep targets from tool_calls beside files_opened: extract path-like arguments from cat/head/tail/less/grep/sed/awk/wc/find-style commands, classify them against the same pack layout the Read targets use, and report the result as a further column per aspect whose unit and refusal rules are stated as precisely as the existing six (a command with no extractable path is a state, not silently dropped). Re-run over the stored corpus and record the outcome either way in eval/RUNS.md beside the pre-registration it bounds: if the widened population holds an un-carried Bash read, the pre-registration figure gets a correction note; if it holds none, the 0 stands with its population honestly named. The --selftest gains a row whose answer is written out as a literal: a cat of an un-carried path inside a Bash call must land in the new column.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/98
established_by: 'PR #98 squash-merged at 8471291; census widened to the Bash/Grep half; corpus 0 stands (57 rounds, 468 calls, 179 operands, 0 un-carried); verified in orchestrator checkout; findings: none'
---

prompt_capture_census.py is titled WHAT THE NON-CODE JUDGE ROUNDS READ, and its unit is files_opened - which field.py's run_field fills from Read/NotebookRead tool calls only. tool_calls stores every call with its full target (since task 204), and the stored corpus holds far more reading done through Bash than through Grep: measured 2026-08-29 over every usable field record matching eval/runs/**/*__*__seed*.json - 97 rounds, 71 carrying tool_calls, holding 6,812 Read targets and 2,308 Bash ones. The census's six per-round states sum to the aspect's n, so it presents the Read half as the whole reading population; a judge that cats or greps an un-carried path would land in no state and the latent-null figure in eval/RUNS.md (0 un-carried reads, the 2026-08-28 pre-registration) would not move. That is the #203 shape - the analysis reading a subset of the walker's output - crossed with #201 (a filter written before a population existed excluded it silently): the Bash population was never absent from the RECORD, only from the census. The one blind-vocabulary instance a vocabulary scan found in Bash targets is crates/sim in a wg-aspect-reliability pack built before the #131 repair and already bounded by it; the other 29 vocabulary hits are stack tokens (bevy, UnityEngine, project.godot), which are visible by design - #53 measured that a judge reads the stack off the code, and blinding hides the trial-to-label mapping, not the source language. Do NOT re-file those as a leak.

## note 2026-08-30

PR #98 squash-merged. Census widened to the Bash/Grep half of the capture: 2,308 stored
Bash tool calls (97 usable rounds, 39 with a usable tool_calls capture) now classified
beside files_opened — 468 Bash/Grep calls over the pre-registered corpus, 31 exactly-200-char
commands refused whole, 337 no-path calls counted as a state, 179 operands extracted,
0 un-carried reads: the pre-registration's 0 stands with its population honestly named
(eval/RUNS.md, 2026-08-29 section). The first run's 2 itemised un-carried reads were
adjudicated extractor false positives (process-substitution punctuation; find expression
value), fixed against their corpus shapes, 0 stored read locations moved. Rounds whose
tool_calls key is absent/null/malformed are unassessable per half, counted, never clean;
the halves refuse independently. Red-first proven per review round at each prior head
through the prior extractor's own entry point; three review rounds, all threads answered
on-thread and reviewer-confirmed. Corpus byte-identical across all repairs.
Verified at head 8471291dae83e2ab9d5b572d5c1625869ee483db in an orchestrator-owned
detached checkout: --selftest exit 0; corpus 57/39/468/31/337/179/0 with per-aspect rows
identical to RUNS.md; docstat --sweep clean over 284 docs; --renumbered 0 stale of 43;
tasks.py check 217 well-formed; pr_review_state LANDED_REVIEW at the merged head.
Findings: none — the gap was born and repaired within the task; false positives recorded
in RUNS.md per the task-217 precedent.
