---
id: 207
title: 'weight_sensitivity.py:8 cites FINDINGS #119 for the tier-1-gate story, which is #123'
status: in_testing
priority: 3
refs: eval/judge/weight_sensitivity.py, eval/findings/certifies-nothing.md, eval/findings/documentation.md, tasks/206
done_when: 'The citation names the finding that holds the story it is cited for, checked by reading each cited finding beside the claim that cites it; every other #119 citation surviving the 2026-08-23 renumbers in live (non-archive) code is read the same way and either confirmed correct or fixed - the spot-check rows are runner.py:20 (''the sole copy, so they stay (#119)''), docstat.py:596, docstat.py:2954, docstat.py:5100.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/87
established_by: 'PR #87: all six sites re-verified beside the cited findings, historical rows checked against the trees at their authoring commits (69de88c8, e86e09d0, 31d66bb5); post-fix grep of live paths returns only the four verified-correct #119 rows; run-gates.sh pre-push exit 0, tasks.py check exit 0, weight_sensitivity --selftest PASSED; CodeRabbit LANDED_COMMENT at head 239e94c, no defects found.'
---

Found 2026-08-29 while working task 206 (grep for surviving #119 citations in live code, after fixing the two in the judge_ledger/field_sweep pair). eval/judge/weight_sensitivity.py line 8 reads: 'On 2026-08-23 tier 1 became a GATE and overall = tier2 (#119, ...'. The tier-1-gate story ('Tier 1 is now a gate: overall = tier2') is the body of finding 123 (eval/findings/certifies-nothing.md, heading at line 3189, the sentence at line 3233). #119 is the withdrawal-register finding (eval/findings/documentation.md line 955). Same shape as the #119-meant-#121 drift the sixth cleanup pass fixed in judge_ledger.py's docstring - a citation that resolves and means something else. The module was not read whole here, so there may be more where that came from; the fix is citation-only, never renumber the finding.

## pre-dispatch note 2026-08-29

Task 206 has merged (squash f69902e; main at 60d5a2c), so the judge_ledger/field_sweep `#119`->`#121` fixes named above are ON MAIN - do not touch those two sites. The remaining known rows are exactly this ticket's five spot-checks; the module-read-anyway instruction stands, because a citation grep alone is the enumeration shape that missed the pair in the first place.

## note 2026-08-29

## Done 2026-08-29 — six citations fixed, four confirmed correct, one declined

Every wrong row was CORRECT WHEN WRITTEN on 2026-08-23 and broken the same day: the number #119 changed hands four times in one day (the gate finding, the retired-suite finding, the guarded-one-record/destroyed-other finding, and finally the withdrawal register, which holds it today). Each site was dated with blame, then the claim was read beside the finding that holds its story, and the historical claim checked against the tree at the authoring commit rather than trusted from this ticket.

Fixed (citation-only; no finding renumbered):

- eval/judge/weight_sensitivity.py:8 #119 -> #123. At 69de88c8 (the gate commit itself), certifies-nothing.md:3176 reads "## 119. In 68 trials the 0.31-weighted tier deducted..." — the gate finding.
- eval/runner.py:20 and :1077 #119 -> #122. At e86e09d0, documentation.md:956 reads "## 119. Retiring a suite would have deleted the only copy of what its trials were asked to do".
- eval/runner.py:1105 #119 -> #120. At 31d66bb5, documentation.md:956 reads "## 119. One function guarded one durable record and destroyed the other, eleven lines apart". NOTE: this is #120, not #122 — the "guarded in one file and overwritten in the other" story is the durable-records finding, and the ticket's retired-suite framing does not fit it.
- eval/tools/docstat.py:596 and :5100 #119 -> #122 (template-godot deletion = retired-suite finding).

Two rows beyond the five spot-checks (runner.py:1077 and :1105) were found by grepping every live path; the module-read-anyway instruction was also honoured — every numbered citation in weight_sensitivity.py was read beside its finding.

Confirmed correct, do not re-litigate: weight_sensitivity.py:6 -> #92, :83 -> #25 (Unity project-lock bias), :336 -> #60 (address is an input to the check) all hold their stories; docstat.py:2954 "(where #119 was the retired suite)" is a DELIBERATE historical statement about the numbering at e86e09d0, verified true of that tree, and names #122 for the modern number in the same sentence — left as written; AGENTS.md:384, DECISIONS.md:3051 and the renumber_triage.json anchors cite #119 = the withdrawal register, its current holder.

CodeRabbit round 1: LANDED_COMMENT, no line comments. Its Docstring Coverage warning (66.67% on "functions touched by this diff") was declined on the PR with the reason posted as comment 5460240872: the diff is comment/citation-only, so the touched-function set is an artifact of the heuristic, and writing docstrings into retired runner.py main() and a docstat internal is outside a citation-only ticket.
