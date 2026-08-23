---
id: 40
title: tasks/*.md frontmatter is not valid YAML, and tasks.py rewrites it that way
status: in_flight
priority: 3
refs: eval/tools/tasks.py, tasks/35, tasks/37, research/11-doc-linting-for-agents.md
done_when: python3 with yaml.safe_load parses the frontmatter of every tasks/*.md file, and still parses after a start and a done cycle have written to one; or, if moving tasks.py to a real YAML reader and writer is shown to change what tasks.py show prints or what cmd_check accepts, that measurement is recorded as the reason not to and closes the task
---

Found while doing task 35, which quoted the five SKILL.md files. The same defect is in the task queue: 21 of 38 tasks/*.md files fail yaml.safe_load with ScannerError: mapping values are not allowed here. Measured 2026-08-23. The offending keys are established_by (19 files) and done_when (2). No other key is affected - id, status, priority and title are all clean.

Quoting the files is NOT sufficient on its own, and this was demonstrated rather than assumed. tasks.py does not use a YAML parser: _parse splits each line on the first colon and takes the rest literally, and _set writes f-string k: v with no quoting. So (a) if the files are quoted, _parse returns the quote characters as part of the value - probed on task 06, status becomes the 6-character string with quotes, which is not in STATUSES, and int(priority) raises - and (b) the next tasks.py done writes established_by unquoted again, which is the key behind 19 of the 21 failures. A file-only fix undoes itself on the next queue write.

So the fix is tasks.py itself: read the frontmatter with yaml.safe_load and write it with a real serialiser, then requote the existing files. The risk to check is that tasks.py show and cmd_check must behave identically afterwards - that is why the done-when has an escape branch.

Why it matters is the same as task 35: no external tool can parse the repository. It is not a live failure, because tasks.py tolerates its own format.
