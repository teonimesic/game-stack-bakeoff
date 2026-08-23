---
id: 84
title: The verify-gate Stop hook leaves no evidence that it ran
status: in_flight
priority: 2
refs: eval/starters/*/.claude/hooks/verify-gate.sh, eval/wholegame.py, tasks/78
done_when: either every starter's verify-gate.sh records each invocation and its verdict somewhere the harness collects and the graded diff does not see, with a control showing a green run and a blocked run are distinguishable afterwards from stored artifacts alone and a control showing the log does not appear in diff.stat or the submission tarball, or the hook is measured live in one real trial per stack and the result recorded so that 'the gate is live in all four' stops resting on file presence
---

The defect this ticket exists to fix is FINDINGS #130 - read the measurement, its extraction control and its two live probe arms there rather than here, so there is one copy of them. In one line: a Stop hook that BLOCKS is visible in the transcript, one that EXITS 0 leaves nothing anywhere, so no stored artifact separates a green gate from a gate that never ran, and 'the gate is live in all four' had only ever been inferred from file presence, which is rule 2. What this ticket adds to #130 is the fix and the constraint on it. The fix is an audit trail - AGENTS.md: record the inputs a component actually consumed, not merely the output it produced. The design constraint that makes this non-trivial and is why it is a separate ticket: the trial tree BECOMES the graded diff, so a log written into the project directory contaminates files_changed, tree.txt, diff.stat and the submission tarball, which is exactly the shape of #106. It has to land outside the tree - an env var the harness sets, or TMPDIR - and that is a starter edit plus a harness change, so it is a regime boundary with three gates.
