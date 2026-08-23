---
id: 23
title: Measure every aspect's reliability with separation(), not just fun_frames
status: in_flight
priority: 1
refs: eval/FINDINGS.md #75 #68, eval/judge/field.py separation()
done_when: each of the six aspects has a pooled SD and a resolved-pair count from repeats on a named field, OR is reported as unmeasured with the reason; and the aspects that cannot resolve any pair at achievable n are named as such
---

separation() replaced #58's ceiling gate: instead of asking whether one round's scores are bunched, it asks whether any pair of submissions is resolved at gap > SEi + SEj, using repeats.

THE GAP: it has been used on exactly ONE aspect and ONE field - fun_frames on g2_tetris3d, which gave pooled SD 0.577 and 18 of 28 pairs resolved at n=7. The other five aspects have NO measured reliability at all. Their SD is unknown, so nobody can say whether any of them is capable of resolving a difference at any n.

WHY THIS AND NOT THE OTHER CANDIDATES:
  - Bounding #83's 26 unassessable rounds further was considered and rejected. The rescue that bounded the rest worked by matching numbers quoted in fun's prose; #86 established that ux and idiomatic quote no figures, so most of the 26 are unresolvable in principle. And provenance now records run and files_opened going forward, so the gap is historical and closed at the source. Effort would buy a slightly tighter bound on rounds nobody will cite.
  - 'Is there a frames aspect that is not palette-coupled?' is already ANSWERED: fun_frames correlates -0.120 with distinct-colour counts where ux correlates +0.53 to +0.73 (#78). A usable frames aspect exists. Filing it would be re-deriving a measured result.

WHAT MAKES THIS ONE WORTH IT: tier 3 sits at weight 0.00 and the standing question is whether it could ever be re-weighted. That question is not about scores, it is about reliability - an aspect whose SD swamps every gap in the field cannot contribute at any n, and an aspect with a small SD might. separation() answers it directly and the answer is per-aspect, so it partitions the layer into 'could work' and 'cannot' rather than treating tier 3 as one thing.

COST: repeats are the only tier that costs money. fun_frames at n=7 cost about  on one field. Six aspects at n=7 on one field is roughly -70; choose the field first (a ceiling-passing one - #74 showed a saturated field cannot terminate) and report SD and SE separately per #75.

CONSTRAINT: report per aspect, never pooled. Aspects differ in what they read, and a pooled SD across aspects would be exactly the heterogeneous mean rule 4 forbids.
