---
id: 78
title: Only the rust guide tells the agent the Stop hook re-runs verify; the hook is live in all four
status: in_flight
priority: 3
refs: eval/starters/*/AGENTS.md, eval/starters/*/.claude/settings.json, tasks/67
done_when: either the three guides that omit it gain the sentence and starter_parity plus verify_blind and starter_gate_control are re-run with an eval/RUNS.md regime note, or the omission is recorded as deliberate with the reason and a measurement of whether the sentence changes what an agent does
---

Measured 2026-08-23 under task 67. All four starters ship .claude/hooks/verify-gate.sh and wire it under "Stop" in .claude/settings.json, so the gate re-runs at end-of-turn in every arm. Only eval/starters/rust/AGENTS.md line 12 says so: 'A Stop hook re-runs it when you try to finish, so ending the turn red does not work.' ts, unity and godot guides never mention it - grep for 'Stop hook' across the four hits rust only.

Why it matters: this is the one-arm difference task 67 went looking for and did not find. An agent that knows ending red does not work has a reason to run verify before finishing; three arms are not told. Whether that changes behaviour is UNMEASURED - say so rather than assuming. The stored trials can be asked: agent.final_text and the transcripts record whether an arm hit the Stop gate and had to go back.

Why the existing gate cannot see it: starter_parity's near-miss heading check fires only on a heading present in every guide but one. This is a SENTENCE, present in one guide of four. The heading axis is structurally blind to both - to 1-of-4, and to anything below heading level.

Do not make the four guides identical (DECISIONS.md: stack-native by design). The question is whether this specific guidance was meant to reach every arm.
