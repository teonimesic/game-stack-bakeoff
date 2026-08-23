---
id: 47
title: Tell a building agent what to do when the starter's own gate is wrong, not only that it must not weaken it
status: open
priority: 3
refs: eval/FINDINGS.md #98, eval/IMPROVEMENTS.md axis 2 candidate 3, eval/tools/starter_gate_control.py
done_when: each of the four starter AGENTS.md files states the repair rule, and starter_gate_control.py demonstrates on a planted defect that the rule's preferred repair still fails while the repair it warns against goes green
---

90 stored submissions never weakened an oracle, but one repaired a red starter gate into a gate that cannot fail, and the prose says nothing about that case
