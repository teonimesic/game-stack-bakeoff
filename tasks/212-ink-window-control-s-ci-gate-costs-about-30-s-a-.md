---
id: 212
title: ink_window_control's CI gate costs about 30 s a run, and the cost is per-pixel Python in the fixture phases
status: done
priority: 5
refs: eval/judge/ink_window_control.py, eval/judge/png.py, .github/workflows/gates.yml
done_when: A producer states the gate's wall time beside the gate (the workflows README entry, dated), and either the fixture phases' cost is measured materially lower with every expectation still held and byte-identical fixture readings, or the cost is measured and declined in writing with the reason. Any change to png.ink_coverage or png.Image.differs_from is pinned against the current per-pixel values on all existing fixtures and blank-render arrangements before and after.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/93
established_by: 'PR #93 squash c9e3d43, branch head 47fc5f88bec4d57a7d10800f9f3750c6f5bb4f59; verified at that head in own detached checkout unpiped: ink gate 86/86 exit 0 at 4.58s wall (was 31.3s), --pin-dump byte-identical across two runs at 1148 lines, corpus arm --reference-shift reproduces all 67 stored mean_ink values to the digit, capture_selftest OK, runner_capture_selftest 50/50, rusage_selftest all controls hold; review round 2 clean, all 3 round-1 comments verified and fixed; merged main gates green unpiped (sweep, renumbered, tasks check, ink 86/86); no finding allocated (every measurement held equivalence; the round-1 fast-path defect was born and fixed inside this PR).'
---

Measured 2026-08-29 while working tasks/211: time python3 eval/judge/ink_window_control.py is about 30 s wall locally (29.6 s at that day's HEAD before the tasks/211 phase, 30.3 s after), against the 0.6 s the gates.yml comment and the workflows README carried until then - a figure that had gone stale against a smaller form of the file. Both documents now carry the measured figure (tasks/211). cProfile puts nearly all of it in png.ink_coverage and png.Image.differs_from over full 640x400 frames, called from the blank-arrangement, colour-drift and two-halves fixture phases (measure_sequence writes and re-reads 12-frame sets several times over). The gate runs on every push and every pull request (gates.yml), so this is a standing CI-minutes cost, not a one-off. A vectorised or row-batched ink_coverage that provably returns the same values on the existing fixtures would repay most of it; the corpus-fixture phase added by tasks/211 is about 0.6 s of the 30 and is not the target.

## note 2026-08-29

## Established (PR 93, branch task-212-vectorise-png-pixel-reads, head 47fc5f8)

The ink gate cost 31.3 s wall (29.8 s user) and cProfile put essentially all of it in the two per-pixel readers: 494 calls in png.ink_coverage (29.6 s cum) and 193 in png.Image.differs_from (26.3 s cum) over full 640x400 frames. Both are now vectorised with the stdlib only (the judging host has neither Pillow nor numpy and png.py forbids both): ink_coverage maps each channel through a 256-entry 0/1 bytes.translate table and ORs the three flag strings as integers - a word-parallel per-pixel OR that cannot carry - then bit_count (14x in the microbenchmark); differs_from gained a byte-equality fast path plus a six-way zip over channel slices (5.4x), with the original quirky channel indexing (c==2 compares alpha; c<3 reuses ch0) and the 1.0 on size mismatch preserved exactly, and two fail-closed length guards added where the old loop raised IndexError mid-loop or silently ignored trailing bytes.

The pin landed BEFORE the png change, per the ticket: _reference_ink / _reference_differs in judge/ink_window_control.py are the two functions as they shipped, loop per pixel; a reader-pin phase re-derives every fixture and blank-arrangement reading through them; --pin-dump prints every reading canonically (1083 lines on the pre-review code). The before/after dumps were byte-identical, and independently the corpus arm (--reference-shift --runs-root over the stored runs) reproduced all 67 stored mean_ink values to the digit with the same 10 moving sets eval/RUNS.md records. Mutants: shipped reader one tolerance step narrow and one step loose, both caught on a boundary frame whose channels sit at background-9/-8/+8/+9 (no fixture can see a tolerance move). Measured: gate 31.3 s to 4.6 s wall over three runs (4.6/4.578/4.541), every expectation held; post-change profile is dominated by the pin's own deliberate reference passes plus zlib. Registers carry the dated figure and producer: workflows README and the gates.yml step comment, 2026-08-29, time python3 eval/judge/ink_window_control.py.

## Review round 1 (CodeRabbit): all three comments verified against the code, all valid, all fixed in 47fc5f8

1. png.py fast path vs negative tolerance: identical data at tolerance -1 read 1.0 through the shipped loop (0 > tolerance) and 0.0 through the fast path - measured before fixing. The shortcut now fires only at tolerance >= 0. New coverage both ways: a variant row requires identical data to agree with the reference at -1/0/1/8, and a new mutant installs an unguarded fast path and is caught. Gate now 86/86 at 4.55 s, so the register figure stands.
2. pin_dump: every row labelled ca-v-cb measured a 3-channel left image (leftover a3), so 1v2/2v4/4v3/1v3 were mislabelled and the dump did not hold the mixed cases its labels claimed. The PHASE was never wrong - it already built both sides from ca/cb. Both sides now built per pair: exactly the 6 lying rows changed value; the dump also gained the identical-pair readings and a -1 reading on every consecutive pair (1148 lines now). The full diff against the pre-review dump is those 71 lines and nothing else - every fixture ink, is_flat and analyse_frames reading byte-identical.
3. gates.yml named judge/png.py twice; both are the repository-relative eval/judge/png.py now.

Review round 2 on 47fc5f8: clean, no actionable comments.

## The red required gates check is main's, not this branch - do not chase it here

The branch's first gates run (6a5298c) was green; the failing row is tasks_control's byte round trip naming tasks/216, created on main by cd4994d, which touches no file this PR changed. Main's own gates and controls are red at 14:01Z and 15:03Z on the same content. Reproduced locally with no pyyaml-version dependence: _read_fm then _render on the committed 216 file rewrites its hand-quoted title unquoted - the writer cannot reproduce a scalar a hand repair quoted (a 6.0.2-vs-6.0.3 suspicion was tested first and ruled out). The main checkout working tree already holds the canonical rewrite (the 216 agent's in_progress status write, uncommitted), so the red clears when that commits and the branch is updated. The durable property is filed as task 217. This branch deliberately does NOT touch tasks.py or the queue files: task 216 is in_progress by another agent on exactly that writer, and a second writer there is the collision the queue discipline forbids. update-branch was also deliberately skipped: it would re-run CI against the same red merge content and change nothing.

## Artifacts (all /tmp, ephemeral)

pin_before.txt / pin_after.txt (1083-line dumps, byte-identical), pin_after_review.txt (1148 lines), pin_review.diff, gate_after_review.txt (86/86 output), bench_ink.py (the microbenchmark). Re-derive instead with: python3 eval/judge/ink_window_control.py --pin-dump, and time python3 eval/judge/ink_window_control.py.

## Not established here

Whether _render should preserve quoting style or check should refuse non-canonical quoting - that is task 217's decision, with the four census rows and the repaired 214 title (which must stay quoted: it holds a space-hash) as the greens any fix owes. No finding number allocated: nothing here measured nothing; if 217's fix produces one, that is its session's call.
