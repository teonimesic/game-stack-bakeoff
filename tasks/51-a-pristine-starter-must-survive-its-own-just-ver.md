---
id: 51
title: A pristine starter must survive its own just verify unchanged
status: in_flight
priority: 2
refs: 
done_when: starter_gate_control.py runs just verify twice on a pristine copy of each arm and fails if the first run modified any tracked file; red today on rust and godot before the task-26 repair, green after
---

FINDINGS #106. All four arms run fmt (auto-fix) inside verify, so verify is idempotent only on an already-formatted tree. Two of the two arms checkable without installing dependencies were dirty: crates/game/src/main.rs under rustfmt and tools/no_raise.gd under gdformat. The agent's first verify, and the Stop hook's, therefore commits a change to a file the agent never opened, and git diff HEAD is what separates authored work from template code. ts and unity are unchecked because their formatters need dependencies installed. starter_gate_control.py already had the right shape and pointed at just check, which touches no formatting.
