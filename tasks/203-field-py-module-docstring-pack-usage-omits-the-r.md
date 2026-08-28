---
id: 203
title: field.py module docstring pack usage omits the required --aspect and fails as written
status: todo
priority: 5
refs: eval/judge/field.py
done_when: the usage line carries every required flag, and the documented pack invocation run for real from eval/ with a /tmp --out against a stored run exits 0 or refuses with the tool own message. docstat.py --sweep exit 0 unpiped after.
---

field.py:8 documents pack with --run RUN --game g1_pong --out DIR [--order-seed N], but the pack subparser declares --aspect required=True with choices (field.py:2033). Following the docstring verbatim exits 2 with the argparse error - the task 200 class: a documented invocation that cannot run as written.
