---
id: 212
title: ink_window_control's CI gate costs about 30 s a run, and the cost is per-pixel Python in the fixture phases
status: in_review
priority: 5
refs: eval/judge/ink_window_control.py, eval/judge/png.py, .github/workflows/gates.yml
done_when: A producer states the gate's wall time beside the gate (the workflows README entry, dated), and either the fixture phases' cost is measured materially lower with every expectation still held and byte-identical fixture readings, or the cost is measured and declined in writing with the reason. Any change to png.ink_coverage or png.Image.differs_from is pinned against the current per-pixel values on all existing fixtures and blank-render arrangements before and after.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/93
---

Measured 2026-08-29 while working tasks/211: time python3 eval/judge/ink_window_control.py is about 30 s wall locally (29.6 s at that day's HEAD before the tasks/211 phase, 30.3 s after), against the 0.6 s the gates.yml comment and the workflows README carried until then - a figure that had gone stale against a smaller form of the file. Both documents now carry the measured figure (tasks/211). cProfile puts nearly all of it in png.ink_coverage and png.Image.differs_from over full 640x400 frames, called from the blank-arrangement, colour-drift and two-halves fixture phases (measure_sequence writes and re-reads 12-frame sets several times over). The gate runs on every push and every pull request (gates.yml), so this is a standing CI-minutes cost, not a one-off. A vectorised or row-batched ink_coverage that provably returns the same values on the existing fixtures would repay most of it; the corpus-fixture phase added by tasks/211 is about 0.6 s of the 30 and is not the target.
