---
id: 203
title: field.py module docstring pack usage omits the required --aspect and fails as written
status: done
priority: 5
refs: eval/judge/field.py
done_when: the usage line carries every required flag, and the documented pack invocation run for real from eval/ with a /tmp --out against a stored run exits 0 or refuses with the tool own message. docstat.py --sweep exit 0 unpiped after.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/84
established_by: 'Orchestrator verification, all claims reproduced at head 82b75d4bd (worktree), unpiped. RED: documented pack line without --aspect exits 2 at argparse (first attempt read exit 1 only because --run was aimed at the worktree''s nonexistent eval/runs - the address, not the tool). GREEN: the documented line run from eval/ against the main checkout''s stored wg-g4c-2026-08-21T02-26-46 packed the full g4_platformer field, 8 labels A-H, knowingly_truncated false, exit 0. Both refusals: --aspect fidelity refuses via applicability (scene aspect, game task), --aspect nonsense_aspect refuses at argparse choices, exit 2 both (re-run unpiped after a piped read swallowed the status - rule 3). The g1_pong substitution rationale verified: wg-audio-2026-08-14T12-29-42 refuses with TRUNCATION HAS RETURNED, 3 of 8 submissions dropped files for length. Sweep exit 0 over 270 docs, tasks check exit 0, CodeRabbit round 1 clean at the exact head range. Merged squash as 2a653bf. Findings decision at merge: no new finding - one more instance of task 200''s documented-invocation-that-cannot-run class; the remedy, run the documented line before publishing it, is already recorded there.'
---

field.py:8 documents pack with --run RUN --game g1_pong --out DIR [--order-seed N], but the pack subparser declares --aspect required=True with choices (field.py:2033). Following the docstring verbatim exits 2 with the argparse error - the task 200 class: a documented invocation that cannot run as written.

## note 2026-08-28 (orchestrator, before dispatch) - what changed since filing

Tasks 202 and 204 merged (a29b35b, fd3e1d4). Both edited field.py BELOW the module docstring, so the :8 and :2033 addresses still hold - re-verify both at your head anyway. Two things the handbacks established that bear on this ticket: the documented invocation is run for real from eval/ (the folder convention, as in task 200's repair and PR #83's round-1 decline - do not "fix" the convention), and the run you point --run at lives in the main checkout's eval/runs, which a worktree does not have, so the real invocation runs against the main checkout's stored tree while the edit itself is made in your worktree.

## note 2026-08-28

## note 2026-08-28 (agent, on handback)

Both addresses held at my head (field.py:8 usage line; pack subparser with the required
--aspect), as the pre-dispatch note predicted. Fixed the docstring line only: it now carries
`--aspect idiomatic`, coherent with the run line below it, and a pairing applicability()
accepts for g1_pong (verified directly: idiomatic is a game aspect, g1_pong a game task).
Code untouched.

**No stored g1_pong field can be packed under the current regime - data vintage, not the
command.** The exit-0 proof therefore substitutes the game placeholder. Measured:

- `wg-matrix-2026-08-13T14-02-50` g1_pong: refuses `pack/manifest parity is UNMEASURABLE for
  8 submission(s)` - predates `pack.manifest` in eval/report.json.
- `wg-audio-2026-08-14T12-29-42` g1_pong: refuses `TRUNCATION HAS RETURNED - 3 of 8
  submissions dropped files for length` - its stored `files_dropped_for_length` predates the
  #69 budget removal, and the gate reads the stored counts.
- `wg-g4c-2026-08-21T02-26-46` g4_platformer: full modern field (8 submissions, code packs,
  manifests, all `files_dropped_for_length` 0) - the documented line packs it, exit 0, eight
  A-H directories at the pack top level, mapping stored separately.

Both refusals are the tool's own messages, which the done-when admits, so the ticket passes on
the refusal half for g1_pong and on the exit-0 half for the substituted game. **If a future
task wants the docstring's example game to be packable end-to-end against a stored run, the
defect is that no post-#69 g1_pong field exists in eval/runs - not this docstring.**

Harness note for the next agent in a worktree: the sandbox refuses `cd .../eval && <cmd>` (it
parses the path's trailing `eval` as the shell builtin), so the folder convention is
reproduced with `os.chdir(<abs>/eval)` inside python and `subprocess.run([sys.executable,
"judge/field.py", ...])` - same cwd semantics as the documented invocation.

Review round 1: LANDED_COMMENT, "No actionable comments were generated", no push since.
