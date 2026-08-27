---
id: 176
title: docstat project_docs() globs the filesystem, so an untracked scratch .md joins a corpus a ratchet is pinned to
status: todo
priority: 2
refs: eval/tools/docstat.py, tasks/160
done_when: project_docs() and _live_corpus() agree on which files are in the tree, asserted in code rather than promised in a comment; a planted untracked .md under a gitignored directory does not move the --sweep corpus count or the bare-trial-id ratchet, pinned as a control that goes red if the filter is removed; docstat.py --sweep and --selftest exit 0.
---

project_docs() in eval/tools/docstat.py builds its list with glob over ROOT, filtered only by is_vendored and a runs/ exclusion. git ls-files does not come into it, so any markdown file sitting in a gitignored directory enters the count. Measured 2026-08-27 while working tasks/160: writing one scratch note at staging/task-160-note.md moved docstat.py --sweep from "references over 239 docs (228 project + 10 skills + 1 under .github)" to 240 (229 project), at exit 0 both times. Renaming the file to .txt put it back to 239. The helper docstring says the bare-trial-id ratchet is "pinned to an exact count a larger corpus would move", so the failure mode is not only a wrong published number: a file that is not in the repository can move a gate that is. _live_corpus() in the same module reads git ls-files and is unaffected, which is the fix shape - two spellings of one tree, and only one of them is the tree.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — `tasks/179` edits the same file; you are first and it will rebase on you

`179` repairs `docstat.py`'s findings-COUNT check, which is bound to one phrasing. Yours repairs
`project_docs()`'s corpus selection. Different defects, one file, so they cannot run concurrently.
You go first because the corpus is the input to every check in that tool, including 179's.

**Worth knowing before you change the population:** `--sweep` prints its corpus size in the summary
line and several of its checks are pinned to exact counts. At `main` right now that reads *249 docs
(238 project + 10 skills + 1 under .github)*. If your repair moves the corpus - and reading
`git ls-files` instead of globbing will - **every pinned count moves with it**, and a pin updated
to match a new number is not a check. Say which pins moved and why each new value is right, rather
than re-recording the output.

The ratchet your ticket names is the case to lead with: a pin to an exact count over a corpus that
can silently grow is a pin that reports the corpus, not the property.
