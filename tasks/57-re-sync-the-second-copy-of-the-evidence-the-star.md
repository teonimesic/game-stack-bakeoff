---
established_by: 'Re-synced /Users/stefano/game-research-evidence and verified by reading the destination back. Missing before: 97 files, 8,977,932 bytes - 44 starter-baseline files (all 3 runs, 22 trees), 24 in wg-g4c repack-2026-08-23-stale-files-removed, 29 wg-aspect-reliability judge rounds; plus 10 files that differed, of which REPRODUCIBILITY.json (220 vs 49,666 bytes) and sweep.log (88 vs 8,070) were stale prefixes that had SHA-verified correctly because the source was mid-sweep. Step 2 was run first: evidence_set.py classifies all 44 baseline files as evidence by its own rule, and their mtimes are 04:24:27-29 against a snapshot verified 00:08:58, so the copy predated the files and the classifier is sound. After re-sync MEASURED.json reads 14,270 files, 1,118,320,004 bytes, 14,270 SHA-256 matches, 759 harness JSON parsed, 89/89 tarballs, 22/22 starter baselines re-derived from 1,238 git blob ids. An independent read-back that does not import backup_evidence re-hashed the same 1,238 blobs with git hash-object at the destination: 0 mismatches, 68 report.json parsed. New tier 4 in backup_evidence.py matches every baseline archive against its own ls-tree, unsampled; backup_evidence_control.py pins it with 9 fixture cases built from a real git repo, all 22 real baselines, and 5 mutants each caught only by the case naming its mechanism, and it fails loudly on a runs-root holding no baselines. eval/PROTOCOL.md re-sync trigger rewritten from the event ''after any run completes'' to the resource ''the evidence set has grown or changed, whatever made it move'', with --verify-only as the mechanical form. Destination README names both exclusions: the 137.046 GB of regenerable build output, and the wg-g4b/wg-g4c work roots, which are not a gap because all 16 of those trees have both a submission.tar.gz and a starter baseline (checked per tree, never per run). The copy is additive so it is now a superset: 23 stale judge-pack files removed by task 42 are still there, listed in DEST_ONLY.txt, deleted from nowhere. Finding #115. Still same-disk, still not a backup.'
id: 57
title: 'Re-sync the second copy of the evidence: the starter baselines are not in it'
status: done
priority: 2
refs: 'eval/PROTOCOL.md re-sync section, eval/FINDINGS.md #104, tasks/17-back-up-the-evidence-and-keep-git-current.md'
done_when: the verified second copy at /Users/stefano/game-research-evidence contains every file the classifier calls evidence as of the re-sync date, including eval/runs/*/starter-baselines, re-verified by reading the destination back rather than by a copy exit code; if any class is deliberately excluded, the exclusion is named in the destination README
---

the 7.5 MB of starter baselines are the only record of the starter each agent was given and exist in exactly one place

## What is this thing?

`eval/runs/` holds every stored result this project has produced. Most of it is regenerable build
output; a small core is not. Task 17 partitioned it with `eval/tools/evidence_set.py` — a file is
evidence until something in the tree proves it regenerable — and copied that core to
`/Users/stefano/game-research-evidence`, verifying it by reading the destination back rather than
by trusting a copy's exit code. `MEASURED.json` in the destination records what that run saw.

## What is wrong, and how do we know?

The copy is a snapshot, and the most irreplaceable class of evidence in the project was created
after it. Measured 2026-08-23 by listing both trees:

| | |
|---|---|
| destination `MEASURED.json` `verified_at` | 2026-08-23T00:08:58-0300 |
| `eval/runs/*/starter-baselines` in the source | 3 directories (`wg-g4`, `wg-g4b`, `wg-g4c`) |
| the same in the destination | **0** — `find` over the whole destination returns nothing |

Those directories are the whole population of surviving starter baselines: a `git archive` of each
work tree's root commit plus its `ls-tree`, 7.5 MB for all 22 trees. `eval/FINDINGS.md` #104
established that this is the only record anywhere of the starter an agent was actually given —
`submission.tar.gz` carries no `.git/`, and `diff.patch` names which files changed, not what the
unchanged ones contained. Without it a stored judge pack cannot be honestly re-packed, which is
why `eval/judge/repack.py` refuses rather than guessing.

Two other changes also postdate the snapshot and should be checked in the same pass rather than
assumed: task 42 re-packed `wg-g4c` (222 files to 199, with the 23 removed files kept in the run
under `repack-2026-08-23-stale-files-removed`), and `_cargo-target-pristine` exists in the source
and not in the destination — that one is very likely correctly classified as regenerable, and the
point is that nobody has looked.

## Why does it matter?

Task 17 is closed, and its closure reads as "the evidence has a verified second copy". That is
true of the evidence as it stood at 00:08 on 2026-08-23 and false of the class the project spent
a whole finding establishing it could not reconstruct. The copy is also same-disk and is
documented as not a backup, so the window where a single mistake loses the baselines is real.

`eval/PROTOCOL.md` already has a "Re-sync after any run completes, before the work root is
reclaimed" section. It was not run after task 42. That is the second half of the defect: a re-sync
step that only fires on "a run completes" does not fire when a repair *creates* evidence.

## What should be done?

1. Re-run the copy and its verifier against the current `eval/runs/`, and confirm from the
   destination that all three `starter-baselines` directories arrived with matching SHA-256.
2. Check whether `evidence_set.py` classifies `starter-baselines/*.tar.gz` and
   `*.blobs.txt` as evidence *by its own rule* rather than by having been copied. If the
   classifier would drop them, that is the real bug and it is bigger than this task.
3. Widen the re-sync trigger in `eval/PROTOCOL.md` so it names the resource — evidence was
   created or changed — rather than the event "a run completed".

## What NOT to conclude

Do not read a missing file in the destination as a classifier failure until step 2 has been run.
The likeliest explanation here is simply that the copy predates the files. Establish which before
changing the classifier — a control run after the fix tests the fix, not the claim.
