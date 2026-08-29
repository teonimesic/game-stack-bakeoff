---
id: 217
title: 'tasks_control byte round trip red on main: _render rewrites a hand-quoted scalar unquoted and the red lands on every open pull request through the merge checkout'
status: todo
priority: 1
refs: eval/tools/tasks.py, eval/tools/tasks_control.py, tasks/216-tasks-py-check-passes-a-frontmatter-scalar-whos.md
done_when: Either the writer preserves the quoting style of the line it read (a scalar the file holds quoted is re-emitted quoted, byte for byte, with the four census rows from task 216 as greens and the repaired tasks/214 title - which must stay quoted because it holds a space-hash - staying byte-identical), or tasks.py check refuses a frontmatter line whose quoting differs from what the writer would emit, so the committed queue can never hold a file the writer would rewrite. In both cases tasks_control round trip is green on the committed queue, and a mutant that re-quotes one canonical scalar in a fixture queue is caught by whichever gate owns the change.
---

The required gates check is red on every pull request whose merge ref includes cd4994d, including PR 93 which touches no queue file and was green on its own first run. Main is red on its own runs at 14:01Z (1703566) and 15:03Z (cd4994d). Reproduced locally with no pyyaml-version dependence: read the committed tasks/216 file with _read_fm, re-render with _render, and the title line changes from single-quoted to unquoted - the writer cannot reproduce a scalar a hand repair quoted. The round-trip row measured 214 of 215 files in CI with CHANGED: 216-... . The immediate red clears when the 216 agent commits its own status write, which already rewrote the file in the writer's canonical form in the main checkout working tree; but the property is durable: any future hand repair that quotes a scalar the writer would emit unquoted re-reddens every open pull request at once, through a file none of them touched.
