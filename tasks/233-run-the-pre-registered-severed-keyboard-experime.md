---
id: 233
title: Run the pre-registered severed-keyboard experiment (root IMPROVEMENTS.md iteration 1)
status: todo
priority: 2
refs: 'IMPROVEMENTS.md (root), eval/judge/RUBRIC.md, #128, #46'
done_when: 'The iteration''s Method is executed: ONE completed submission extracted from its stored archive into a scratch directory (never write into eval/runs/; pick the stack whose view layer severs with the smallest edit and state the choice), only the view layer''s keyboard-to-intent wiring severed,  confirmed green on the severed copy (otherwise tier 1 fails for the wrong reason and the experiment says nothing), tiers 1 and 2 run on BOTH copies offline (regrade_wholegame.py is the offline path), and the per-criterion diff recorded as the iteration''s result in root IMPROVEMENTS.md with the falsifier''s verdict stated either way. A confirmed null is a finding (file it); do NOT go on to change any criterion - a criterion addition is a regime boundary and is a separate decision. Offline, no agent spend.'
---

The play-bot tier carries the whole score and has only ever been validated on artifacts where the answer was obvious; and NO criterion in any tier exercises the device-input path: every tier-1 id and every tier-2 id is probe/simulation-path, and #128's four harder criteria replay a played tape through the same probe. The experiment was pre-registered in root IMPROVEMENTS.md (iteration 1) with method and falsifier written, and has never run - re-verified still-unrun 2026-09-02. A confirmed null means the instrument cannot tell a playable game from one whose keyboard wiring is severed, which is the strongest form of the saturation finding and would name a real gap in what the grade certifies.
