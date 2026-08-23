---
id: 40
title: tasks/*.md frontmatter is not valid YAML, and tasks.py rewrites it that way
status: done
priority: 3
refs: eval/tools/tasks.py, tasks/35, tasks/37, research/11-doc-linting-for-agents.md
done_when: python3 with yaml.safe_load parses the frontmatter of every tasks/*.md file, and still parses after a start and a done cycle have written to one; or, if moving tasks.py to a real YAML reader and writer is shown to change what tasks.py show prints or what cmd_check accepts, that measurement is recorded as the reason not to and closes the task
established_by: 'tasks.py now reads frontmatter with yaml.safe_load and writes it with yaml.safe_dump; PyYAML is a hard dependency that stops the tool rather than falling back. All 58 files re-emitted. Round trip: 58/58 files, every value the old reader saw identical under the new one, bodies byte-identical, 0 differences across 58 show outputs plus list, list --status open and check (exit 0 both). Mutant control: dropping one character of done_when turns all 58 red and writes nothing. check controls after the change: duplicate id, missing done_when, bad status all exit 1 with their pinned messages, plus two adversarial files named rather than crashed - 6/6. add/start/done verified from an agent worktree against the shared queue, exit 0, evidence round-tripped through an external yaml reader with colon, apostrophe, hash, quotes, backtick and em-dash intact. Also found and fixed: 19 values in 9 files parsed WITHOUT raising and came back truncated at a space-hash (YAML comment) - silent, plausible and wrong; and read-write idempotence caught tasks 01-07 being renumbered to id: 1 by the writer, which the value round trip could not see. Id left as bare digits so worktrees on the older tool can still find tasks by id - measured, 93 old-reader differences and none functional. FINDINGS #80 unchanged and tested: substitution is shell-layer only.'
---

Found while doing task 35, which quoted the five SKILL.md files. The same defect is in the task queue: 21 of 38 tasks/*.md files fail yaml.safe_load with ScannerError: mapping values are not allowed here. Measured 2026-08-23. The offending keys are established_by (19 files) and done_when (2). No other key is affected - id, status, priority and title are all clean.

Quoting the files is NOT sufficient on its own, and this was demonstrated rather than assumed. tasks.py does not use a YAML parser: _parse splits each line on the first colon and takes the rest literally, and _set writes f-string k: v with no quoting. So (a) if the files are quoted, _parse returns the quote characters as part of the value - probed on task 06, status becomes the 6-character string with quotes, which is not in STATUSES, and int(priority) raises - and (b) the next tasks.py done writes established_by unquoted again, which is the key behind 19 of the 21 failures. A file-only fix undoes itself on the next queue write.

So the fix is tasks.py itself: read the frontmatter with yaml.safe_load and write it with a real serialiser, then requote the existing files. The risk to check is that tasks.py show and cmd_check must behave identically afterwards - that is why the done-when has an escape branch.

Why it matters is the same as task 35: no external tool can parse the repository. It is not a live failure, because tasks.py tolerates its own format.
