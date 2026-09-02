---
id: 233
title: Run the pre-registered severed-keyboard experiment (root IMPROVEMENTS.md iteration 1)
status: done
priority: 2
refs: 'IMPROVEMENTS.md (root), eval/judge/RUBRIC.md, #128, #46'
done_when: 'The iteration''s Method is executed: ONE completed submission extracted from its stored archive into a scratch directory (never write into eval/runs/; pick the stack whose view layer severs with the smallest edit and state the choice), only the view layer''s keyboard-to-intent wiring severed,  confirmed green on the severed copy (otherwise tier 1 fails for the wrong reason and the experiment says nothing), tiers 1 and 2 run on BOTH copies offline (regrade_wholegame.py is the offline path), and the per-criterion diff recorded as the iteration''s result in root IMPROVEMENTS.md with the falsifier''s verdict stated either way. A confirmed null is a finding (file it); do NOT go on to change any criterion - a criterion addition is a regime boundary and is a separate decision. Offline, no agent spend.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/112
established_by: 'squash bb6e990 on main. Experiment verified twice: the agent''s run, and an independent reproduction by the orchestrator at merge (both copies re-warmed and re-graded: 14/14 tier-1 + 20/20 tier-2 on each, overall 1.000 both, the severed copy''s tier-2 evidence strings byte-identical). Treatment pin re-measured: ArrowRight 2s moves 81.2% of the pristine frame vs 1.5% severed (png.differs_from tol 8), idle identical. Finding allocated #214 at merge and landed in eval/findings/certifies-nothing.md + index; counts 196 / #19-#214 across AGENTS.md, README.md x2, FINDINGS.md; IMPROVEMENTS.md iteration 1 names the allocation'
---

The play-bot tier carries the whole score and has only ever been validated on artifacts where the answer was obvious; and NO criterion in any tier exercises the device-input path: every tier-1 id and every tier-2 id is probe/simulation-path, and #128's four harder criteria replay a played tape through the same probe. The experiment was pre-registered in root IMPROVEMENTS.md (iteration 1) with method and falsifier written, and has never run - re-verified still-unrun 2026-09-02. A confirmed null means the instrument cannot tell a playable game from one whose keyboard wiring is severed, which is the strongest form of the saturation finding and would name a real gap in what the grade certifies.

## note 2026-09-02

## Result (2026-09-02): run complete — hypothesis confirmed, the falsifier did NOT fire

Root IMPROVEMENTS.md iteration 1 now carries the full MEASURED record (status line,
stack-choice census, pin table, grading table, verdict). PR:
https://github.com/teonimesic/game-stack-bakeoff/pull/112 (branch
task-233-severed-keyboard-experiment, head e00ffd41b02d841ca7deb7cce8ba0345418d4a88).
CI gates+controls green at that head.

### FINDING — needs a number from the orchestrator at merge

A submission whose real input path is severed grades IDENTICALLY to the playable
original on every tier-1 and tier-2 criterion — 0 of 35 verdict differences, all 21
tier-2 evidence strings byte-identical, overall 1.0000 on both copies. The grade
certifies the probe/simulation path, not playability. n=1: one submission
(g4_platformer__ts__t0 from wg-g4c-2026-08-21), one game, one stack (ts). Controls in
both directions: (can-fail side) the treatment pin shows the same right-arrow input
moving 81.2% of the pristine frame vs 1.5% on the severed copy, below the severed
copy's own idle drift of 1.7% — the key really is dead on the severed copy;
(can-pass side) with no keys the two copies are pixel-identical at both timestamps
(0.000000), so the sever changed nothing else. Same instrument tier 1 uses
(png.differs_from, tolerance 8).

### What was done

- Stack choice stated in IMPROVEMENTS.md: ts severs with the smallest edit (ONE deleted
  line, pressed.add in src/view/main.ts) vs rust 4 lines, godot 4, unity ~8.
- Severed copy confirmed green on just verify (140 sim + 10 render tests) before grading.
- Tiers 1+2 offline on both copies via evaluate.py --no-judge, seed 7. Pristine 14/14 +
  20/20 = 1.0000; severed identical. 3 tier-1 evidence strings differ by timing only.
- Fresh pristine grade agrees with the stored wg-g4c grading — no instrument drift.
- No criterion was added or changed (regime boundary, deferred per the ticket).

### What the next agent must not re-derive

- The experiment artifacts (both extracted copies, grading outputs, pin screenshots)
  live in a scratch directory OUTSIDE the repo and are reproducible by the method in
  IMPROVEMENTS.md; they are NOT committed and eval/runs/ was never written to.
- CodeRabbit will never review an IMPROVEMENTS.md-only diff: .coderabbit.yaml excludes
  the archive class by design (!IMPROVEMENTS.md), and review_details: true made the
  skip notice name the exact pattern. "Review skipped" on this PR is the terminal,
  correct state, not a failed round.
- The follow-up criterion (exercise the real input path, validated both directions) is
  a regime boundary awaiting its own decision — do not fold it into another task.
