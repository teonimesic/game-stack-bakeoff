---
id: 203
title: field.py module docstring pack usage omits the required --aspect and fails as written
status: todo
priority: 5
refs: eval/judge/field.py
done_when: the usage line carries every required flag, and the documented pack invocation run for real from eval/ with a /tmp --out against a stored run exits 0 or refuses with the tool own message. docstat.py --sweep exit 0 unpiped after.
---

field.py:8 documents pack with --run RUN --game g1_pong --out DIR [--order-seed N], but the pack subparser declares --aspect required=True with choices (field.py:2033). Following the docstring verbatim exits 2 with the argparse error - the task 200 class: a documented invocation that cannot run as written.

## note 2026-08-28 (orchestrator, before dispatch) - what changed since filing

Tasks 202 and 204 merged (a29b35b, fd3e1d4). Both edited field.py BELOW the module docstring, so the :8 and :2033 addresses still hold - re-verify both at your head anyway. Two things the handbacks established that bear on this ticket: the documented invocation is run for real from eval/ (the folder convention, as in task 200's repair and PR #83's round-1 decline - do not "fix" the convention), and the run you point --run at lives in the main checkout's eval/runs, which a worktree does not have, so the real invocation runs against the main checkout's stored tree while the edit itself is made in your worktree.
