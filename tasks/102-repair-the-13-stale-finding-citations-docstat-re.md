---
id: 102
title: Repair the 13 stale finding citations docstat --renumbered DECIDES, and triage the 28 it cannot
status: in_flight
priority: 4
refs: eval/tools/docstat.py, AGENTS.md renumbering table, tasks/86
done_when: docstat.py --renumbered reports an empty DECIDED STALE list at HEAD unpiped, every replacement recorded beside the eval/findings/ heading text that establishes it rather than beside the count, and each of the 28 UNDECIDABLE rows carries either a repair or a one-line note saying which finding it meant and why history could not say
---

docstat --renumbered names 13 citations at HEAD whose number was reassigned by a merge: #126 meaning what is now #128 in DECISIONS.md x3, README.md, judge/RUBRIC.md x3, judge/AGENTS.md and .claude/skills/add-game/SKILL.md x2; #133 meaning #134 in DECISIONS.md and tasks/88; #132 meaning #133 in eval/RUNS.md. Every one still RESOLVES, which is why no other check sees them and why a reader following one lands on real work that is not the work the author meant, which is #118. Task 86 repaired only the three that collided with the number it was landing, deliberately leaving files other agents were editing that day. THE TRAP, measured under task 86 and stated in docstat's own docstring: the count cannot grade the repair. A line edited in the working tree blames to UNCOMMITTED and is skipped, and a line committed today has todays findings tree as its authoring tree and is never stale, so the number falls to zero whatever you write in place of it. Grade each replacement by reading the heading in eval/findings/.

## Updated at dispatch, 2026-08-23 — the count moved, and here is why it is not 13

`docstat.py --sweep` now reports **12**, not the 13 this ticket was filed with. The difference is
not progress: merges since filing re-authored some of the lines that carried stale citations, and
`--renumbered` decides what is stale by the **authoring tree of the line**, so a line committed
today is graded against today's numbers whatever it says.

**That is the trap this ticket must not fall into, and it is why the count cannot grade the
repair.** Once you fix a citation, the fixed line has today's authoring tree, so it drops out of
the check *whether or not you fixed it correctly*. **The count going to zero is not evidence the
repairs are right.** Grade each one by opening the finding it now cites and reading the heading.

**Findings have moved again since filing.** The log now runs to **#140**, and #137, #138, #139 and
#140 were all allocated today, two of them after a collision was resolved by renumbering. Re-run
`--sweep` yourself and work from what it prints, not from the numbers in this ticket's body.

**File conflict, live:** task 101 also edits `DECISIONS.md` and `eval/judge/RUBRIC.md` to add
`#139` citations. Merge `main` before you finish.

## What was done, 2026-08-23 — do not re-derive any of this

**The counts at HEAD were 16 decided and 51 undecidable**, not the 12 and 28 the ticket carries.
Both halves grew with the merges of that morning; work from what the tool prints.

**31 citations were wrong, not 16.** The decided half was 16 of 16 wrong, by construction. The
undecidable half was **15 of 51** — and finding those 15 is the work this ticket actually was.

### What every replacement was graded against

Not the count — the count is zero whatever you write. Each destination number below was checked
by opening `eval/findings/` and reading the heading, and each citing sentence was read against it.
The headings are quoted verbatim at `27a51b8`; re-read them with
`grep -rn "^## " eval/findings/*.md`.

| now cites | heading in `eval/findings/` that establishes it | replaced |
|---|---|---|
| **#127** | *The producer built to stop a count going stale globbed one level deep, and the cross-check that certified it had been produced by the same glob* | `#126` ×5 |
| **#128** | *Tier 2 saturates because the task is finished, not because the criteria are too few — four harder criteria built from the task's own unchecked requirements passed 8 of 8* | `#126` ×14 |
| **#131** | *The anonymiser's stack vocabulary was a list of SPELLINGS, so the Rust arm shipped its build tool's name into 22 blind packs — and every architecture round that left a file-open log opened one* | `#130` ×2 |
| **#133** | *a focus guard minimised the window the render tests read pixels from, and a frozen frame is not an empty one* | `#132` ×2 |
| **#134** | *A gate was built to stop the findings figure going stale, it checked the range, and the count went stale beside it — in words, where no check could read it* | `#133` ×3 |
| **#140** | *The census gate could catch only the wordings of the two documents it was built from, and the obvious widening was strictly worse than the enumeration it replaced* | `#137` ×5 |

The 16 decided rows: `DECISIONS.md:216,423,697` `README.md:510` `judge/RUBRIC.md:219,286`
`judge/AGENTS.md:24` `skills/add-game/SKILL.md:120,126` → **#128**;
`skills/audit-docs/SKILL.md:177,184` `DECISIONS.md:524` → **#140**;
`DECISIONS.md:579` `tasks/88:25` → **#134**; `eval/RUNS.md:1807` → **#133**;
`tasks/97:25` → **#140**.

**Where the sentence is about the act of allocation rather than a pointer** — `tasks/65:8`,
`tasks/69:8,41,48`, `tasks/80:8`, `tasks/97:8,25` — the old number is kept and the current one
added beside it. Erasing it would falsify a true statement about what was allocated; leaving it
alone would point a reader at a stranger.

### The 15, and the single property that identifies them

| | |
|---|---|
| tier-2 saturation, `#125` → `#126` → **`#128`** | `tasks/65:8`, `tasks/74:6,11`, `tasks/76:6,7` |
| the one-level glob, `#126` → **`#127`** | `tasks/69:8,41,48`, `tasks/75:6,11` |
| the anonymiser's spelling list, `#130` → **`#131`** | `tasks/73:8`, `tasks/87:6` |
| the godot focus guard, `#132` → **`#133`** | `tasks/80:8` |
| the findings-count gate, `#133` → **`#134`** | `tasks/88:8` |
| the census trigger, `#137` → **`#140`** | `tasks/97:8` |

> **Every one of the 15 is in `tasks/`, and every one is a task citing the number IT allocated
> itself.** That is not a coincidence about this corpus, it is case C of
> `_check_renumbered_citations`'s docstring made concrete: the author's numbering lived only in
> their own worktree, was never committed, and was renumbered at the merge that closed the task.
> History cannot decide these because the tree the author saw does not exist in history — and the
> row you should suspect first is a `tasks/` file talking about **its own** finding. Every one of
> the 36 rows in a **live** document was correct.

**A heuristic that looks decisive here and is not.** The undecidable row prints the heading the
author's committed tree held for that number. Comparing that against today's heading buckets 36
as "agrees" and 15 as "must read" — but `tasks/88:8` and `tasks/97:8` land in the *agrees* bucket
and are both wrong, for exactly the case-C reason above: the committed tree of that moment held a
peer's finding under that number while the author's worktree held their own. **The heuristic is a
reading order, never a verdict.**

**Five of the 51 rows are not citations at all**: `#19-#132` and `#19-#133` are RANGE endpoints,
and `_CITE_RX` cannot tell a range's upper bound from a citation. Left alone deliberately — the
regex is shared with the decided half, and the register records the class instead.

### The register, `eval/renumber_triage.json`

The undecidable list never reaches zero, so the 36 correct rows would have cost the next reader
the same full pass. Their verdicts are now recorded, **keyed by the citing text, never by a line
number** — see `DECISIONS.md`, "The undecidable half's verdicts are recorded". `--renumbered`
prints `UNTRIAGED` first; that is the only part anyone needs to read. `--sweep` gates on an entry
whose sentence no longer exists; `eval/tools/triage_control.py` is 14 controls, every red
demonstrated.

**The bug it shipped with, and the variant that now holds it shut.** The first draft matched
anchors against the row's *printed excerpt*, which `_check_renumbered_citations` truncates at 96
characters. Four adjudicated rows came back `UNTRIAGED`, indistinguishable from four nobody had
read — and `established_by` lines run to thousands of characters, so in `tasks/` that truncation
is the common case, not the corner. Rule 12 against my own matcher. `_row_line` reads the whole
line; `VARIANT past column 96` and its negative control pin both directions.

### For the orchestrator: this needs a finding number

Claim: **a citation is most likely to be stale exactly where history cannot check it, because
both conditions have one cause — the author's own uncommitted numbering.** 31 of 67 rows were
wrong; the decided half was 16/16 by construction; of the 51 rows history could not decide,
**15 were wrong and all 15 were a task citing the number it had allocated itself**, while **0 of
the 36 rows in live documents were wrong**. The mechanism is case C of
`_check_renumbered_citations`. Measured at `27a51b8^`; re-derivable from the table above.
