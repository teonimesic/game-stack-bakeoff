---
id: 27
title: anonymise.build_pack never clears its destination, so judge packs accumulate earlier passes
status: open
priority: 2
refs: eval/judge/anonymise.py build_pack, eval/judge/field.py build_pack, eval/FINDINGS.md #90 #62 #83
done_when: anonymise.build_pack leaves a destination containing exactly the files its own manifest lists, for every submission of at least two runs, verified by set equality against the manifest and not by an exit code; re-running evaluate twice in a row over one submission with a changed exclusion set leaves no file from the first pass, pinned by a fixture that fails before the fix; the completeness gate reads the pack that is on disk rather than anonymise's input counts, so a stale file is a gate failure and not an invisible one; and the 23 stale files already on disk in wg-g4c are either removed with the run re-packed, or the run is marked in eval/RUNS.md as carrying them with the per-stack counts stated
---

anonymise.build_pack does dest.mkdir(parents=True, exist_ok=True) and never removes what is
already there. Every re-evaluation of a run therefore writes a fresh pack ON TOP of the previous
one. Labels are assigned per bucket as NN.ext with NN unique within the bucket, so as soon as the
file SET changes between passes the numbering shifts and the previous pass's files survive under
labels the new manifest does not list.

Measured 2026-08-23 across 68 submissions in 6 runs. Five runs are clean. wg-g4c-2026-08-21,
which was evaluated nine times and straddles both the #69 cap removal and the #83 leak repair,
carries 23 stale files in 222 - 10.4 percent - and the deficit is stack-correlated:

    unity 10 | godot 8 | ts 3 | rust 2

Of the 23, twelve are byte-identical to a live file, so the judge is shown the same code twice
under two names; eleven carry content no manifest lists.

Three consequences, in order of how much they cost:

1. The audit trail is wrong. The manifest is the record of what the judge was shown and it
   under-reports by ten percent on this field.
2. Any cross-stack ordering from idiomatic or architecture on wg-g4c is confounded by how much
   of each submission the judge was shown. That is #62's shape through a third mechanism, and
   pack_completeness cannot see it because it reads files_dropped_for_length, which is 0.
3. It defeats a repair silently. The eleven unlisted files include the .codex hook scripts that
   #83 identified as the answer key; the repair removed them from what anonymise WRITES and could
   not remove them from what was already on disk. Blinding is not in fact compromised here - the
   neutraliser reduces the leaking path to /WORKTREE at field.build_pack time, verified by grep on
   the built pack - but that is a second mechanism catching it, not the repair working.

The .src filename collisions first noticed on this field are a SYMPTOM of this and not a separate
defect: rebuilt from the manifests, all 68 submissions produce 0 collisions under
with_suffix('.src'); rebuilt from what is on disk, 15. Every colliding pair is one live file and
one stale one. Worth one line in the fix: with_suffix is only accidentally injective, and it stays
safe only while bucket numbering is unique regardless of extension.

Reliability measurements are NOT affected - the pack is identical across repeats of one round, so
this adds no variance. It is the orderings that are confounded.
