---
established_by: fun_frames/g2_tetris3d SEPARATES at n=7 ($10.12, 7 fresh repeats under the current brief - not pooled with the 4 stored ones, which predate the geometry note). Pooled SD 0.577 (sample stdev, RMS - the conservative convention, now pinned in separation()), SE 0.218, 18 of 28 pairs resolved, 1 marginal pair reported. #58's ceiling gate REPLACED by field.separation(), pinned 4 ways: refuses at n<2, warns below n=4, distinguishes 'not yet' from 'never'. Proved the old done-when unsatisfiable: smallest gap shrinks as 1/n while SE shrinks as 1/sqrt(n), so it passes only at n=2-3 where SE is least trustworthy - FINDINGS #75. separation() corrected its author on first use (SE<gap vs SEi+SEj).
id: 08
status: done
priority: 1
title: Repeat judgements until a difference between submissions is statistically resolvable
refs: eval/IMPROVEMENTS.md 11b, eval/FINDINGS.md #58
done_when: for each (aspect, field) attempted, the pooled SD, the SE at the n reached, and the count of submission PAIRS resolved (gap > SEi + SEj) are reported; a field where zero pairs resolve is reported as unresolvable-by-repetition with its measured gaps; and #58's ceiling gate is replaced rather than annotated
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE PROBLEM: the judge is stochastic. Judging the same field twice, with provably identical
evidence, moves scores on 1 to 5 of 8 submissions. Every gate verdict this project has recorded
is n=1, so none of them is known to be reproducible.

#58 MEASURED THE WORST CASE: 3 of 6 "does this aspect separate the field" verdicts flipped on
unchanged input, two of them because a SINGLE score out of eight moved. The cause is arithmetic —
the threshold is 0.7, and over 8 submissions the statistic can only take k/8, so 0.7 sits in the
gap between 0.625 (5 of 8) and 0.75 (6 of 8) with nothing between. 52% of measured judgements sit
on that edge.

THE GOAL: judge repeatedly until the standard error of the mean is smaller than the difference
between submissions, so "this version is better than that one" becomes a testable claim rather
than an impression.

METHOD: sequential, not fixed-n — keep adding repeats until SE crosses the target, and report the
n reached. Report SD and SE SEPARATELY per aspect. Repeats shrink SE = SD/sqrt(n); they do NOT
shrink SD, which is the judge's own reliability and has never been measured here.

THIS REPLACES #58's GATE: with an SE you test separation directly instead of through a threshold
that sits where the data cannot land. Replace it; keep the finding, which explains every earlier
round.

TWO LIMITS TO STATE IN THE WRITE-UP:
  - Precision is not validity. At high n, an aspect that tracks palette depth (#59) or a language
    prior (#53) yields a precisely measured artifact.
  - What this DOES license is within-stack A/B — template v1 against v2, same stack — because a
    per-stack prior cancels when the stack is held constant. That is what the template improvement
    loop needs. Cross-stack ranking stays barred.

COST: roughly $289 at n=8 across six aspects and two orders, ~$795 at n=22. Cost is explicitly
NOT a stopping condition. The judge already runs Sonnet, so there is no cheaper model to drop to.

WHICH FIELD TO RUN ON, AND WHY THE TASK CANNOT BE STATED FIELD-INDEPENDENTLY:

"Repeat until the difference is resolvable" only terminates when there IS a difference. Measured
from repeats already on disk (no cost):

  - pooled within-submission SD is about 0.52-0.61 on a 0-4 scale. That is the judge's own
    reliability and had never been measured here: it moves +/-0.6 on unchanged evidence.
  - on `fun_frames` / g2_tetris3d, which the aspect separates, the smallest non-zero adjacent gap
    is 0.250, so n = 7 repeats crosses it. About 3 more repeats, roughly $6.
  - on `idiomatic` / g4_platformer the gaps are approximately zero, so the required n DIVERGES.
    No amount of repetition resolves a difference that is not there.

NON-TERMINATION IS A RESULT, NOT A FAILURE. A field where no n terminates is a field whose
submissions are indistinguishable on that aspect — which is the same answer this project's four
other instruments have returned about the four stacks. Report it as a measurement, with the
measured gap, rather than as an experiment that did not finish.

So: choose the field BEFORE spending, state which of the two outcomes is expected, and report the
gap either way.

WHY THE TARGET IS "PAIRS RESOLVED" AND NOT "SE BELOW THE SMALLEST GAP" (#75):

The earlier form of this task asked for SE below the smallest between-submission gap. That is
UNREACHABLE IN PRINCIPLE, and the run that proved it is on disk:

  n | SE    | smallest gap | SE < gap?
  2 | 0.354 | 0.500        | yes
  3 | 0.333 | 0.334        | yes
  4 | 0.288 | 0.250        | no
  7 | 0.218 | 0.143        | no

A mean over n rounds can only land on k/n, so the smallest achievable gap shrinks as 1/n while
SE shrinks as 1/sqrt(n). The target recedes faster than the estimate closes on it. The criterion
is satisfiable only at n=2 and n=3 — where the measurement is least trustworthy — and permanently
unsatisfiable exactly as it becomes reliable. Same shape as #58's threshold sitting in a gap the
data cannot land in, one level up.

Report instead how many of the 28 submission pairs resolve, using the correct two-sample test
(gap > SEi + SEj, not gap > SE). On fun_frames/g2_tetris3d at n=7: SD 0.565, SE 0.214,
19 of 28 pairs resolved, stable from n=3. That answers the question the task exists for — is
this submission better than that one — for the pairs where it can be answered, and says plainly
where it cannot.
