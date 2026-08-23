---
id: 118
title: 'FINDINGS #146 publishes a census with no producer, and it does not reproduce'
status: in_progress
priority: 4
refs: eval/findings/certifies-nothing.md lines 4223-4272, tasks/112, eval/tools/docstat.py ARCHIVE_PATHS
done_when: 'Either a producer exists that re-derives #146''s census - a script or a documented command with its population stated - and #146 cites it, or #146''s figures are marked in place as unreproducible with the population that was actually counted. #146 is archive so its published figures stay, marked, per AGENTS.md. The ''unrepairable'' subsection is narrowed to say the citation was unrecoverable rather than the claim, citing tasks/112. docstat.py --sweep and tasks.py check exit 0 unpiped.'
---

#146 states '20 rows, 2 true positives' over 'the 53 live markdown files' and names no command. Re-run at HEAD under task 112 over git-tracked *.md minus docstat.ARCHIVE_PATHS - 54 live files - the same out-of-range #NN rule gives 51 matches on 43 distinct lines before that repair and 49 on 41 after, split research/ 26, DECISIONS.md 8, .agents/ 7, eval/ 5, AGENTS.md 3. Excluding research/ and .agents/ gives 15, not 20. The gap is population, not range: the published range only widened from #145 to #151, which can only reduce rows. The conclusion #146 draws is unaffected - the false-to-true ratio is still lopsided and the naive check still should not be built - but the figures cannot be re-derived, which is AGENTS.md's count-with-no-producer failure inside the findings log itself. #146 also calls the two eval/RUNS.md #17 citations unrepairable; task 112 repaired the sentences without renumbering anything, by naming the seventh comparability break and FINDINGS #64, so the word that holds is that the CITATION was unrecoverable, not the claim.
