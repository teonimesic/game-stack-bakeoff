
## Specification note from task 36 (2026-08-23), before you write the check

Task 36 fixed the `AGENTS.md` indent defect and scanned the whole repository afterwards. Its
result decides how you should scope this gate, and getting it the wrong way round produces a
check that fires where nothing is wrong.

**The narrow form — "an ordered-list marker of 2+ digits whose continuation lines are indented
less than the marker width" — currently returns 0 across all 117 markdown files.** That is a
gate you can add today and it passes. `AGENTS.md` was the only file that ever crossed from
single- to double-digit markers.

**The broad form — "no root-level block indented 1-3 spaces" — fails immediately on 15 hits
across 10 files in `tasks/`.** Task 36 inspected every one and none is this defect: they are
2-space-indented lists and prose blocks introduced by a paragraph ending in a colon, with no
ordered-list item preceding them. Nothing lost a parent.

So the broad form would fail on correct input on its first run, and **a gate that fails on
correct input gets disabled** — the failure `AGENTS.md` rule 16 names and the reason
`docstat.py` already removed its path check rather than tuning it quiet.

Take the narrow form unless you can show the broad one earns its false positives. If you do take
the broad form, fix or exempt the 15 `tasks/` hits **in the same change**, and say why each
exemption is legitimate rather than adding a blanket directory skip.

The second gate — YAML frontmatter parseability — has no equivalent ambiguity: it either
`safe_load`s or it does not. Task 35 is fixing the five files that currently fail, so verify the
repository is clean before adding the gate, and pin it red against a deliberately broken fixture
rather than trusting that it would have caught the original.
