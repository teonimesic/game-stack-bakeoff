---
id: 107
title: README is verbose, cost-heavy and full of history - cut it to what is true now and useful to read
status: open
priority: 1
refs: README.md, eval/RUNS.md, eval/FINDINGS.md, DECISIONS.md, eval/withdrawn.json
done_when: README.md contains only what is true now and useful to a reader arriving today; the run-by-run history and the total-spend accounting are gone, each verified present in eval/RUNS.md or eval/FINDINGS.md BEFORE it is cut; docstat.py --sweep, --findings and --withdrawn each exit 0 unpiped; and the before/after line count is recorded with a table of what was cut and where it now lives
---

The operator read it on 2026-08-23 and said it is pointlessly verbose, carries a lot of total-cost information that is not useful at all, and a bunch of historical information that makes no sense either - naming 'run 27 encountered whatever' as the shape to remove. It should only contain up-to-date information that is useful to be read. At 643 lines it is roughly a third run diary, and eval/RUNS.md is 1957 lines covering every one of those runs in more detail, so most of that third is duplication of a file whose job it is.

WHAT THIS IS

`README.md` is the front door. It is 643 lines. It is the only document in the project with no
stated audience, and it has accumulated four different jobs: what the project found, how to run
it, a per-run diary, and a register of figures that turned out wrong.

WHAT IS WRONG

The operator read it on 2026-08-23 and gave three separate corrections in one sitting:

1. *"pointless verbose"*
2. *"a lot of info on total cost which is not really useful at all"*
3. *"a bunch of historical information that makes no sense either. it should only contain the
   up to date information that is useful to be read"* — with the example *"not stuff like
   'run 27 encountered whatever'"*

**Take all three at face value.** They are not a request to compress prose; they are a statement
about what belongs in this file at all. The measurements:

| | |
|---|---|
| `README.md` | **643 lines** |
| `### Done` — the run diary, lines ~215-459 | **~245 lines, 38% of the file** |
| `eval/RUNS.md` — where run history is supposed to live | **1957 lines** |
| mentions of the same six runs, README vs `eval/RUNS.md` | wg-g4c 5 vs 28 · wg-audio48 5 vs 23 · wg-arena3d 4 vs 13 · wg-matrix 5 vs 3 · wg-tetris-judge 2 vs 6 |

So the diary is mostly a thinner copy of a file that exists to hold it, and `AGENTS.md` already
names `eval/RUNS.md` as the authority for *"what every run cost and what it may be compared
with"*. The README is not the second source of truth for that and should not try to be.

WHY IT MATTERS

A front door nobody finishes reading routes nobody. This project's own rule — *a document nobody
finishes reading protects nothing* — has been applied to skills and to `AGENTS.md` and never to
the file every new reader opens first.

WHAT SHOULD BE DONE

**The operator stated the contents of this file directly. It is four things and nothing else:**

1. **what the project is about**
2. **the current found results**
3. **how to run things**
4. **how to evaluate results**

> **"The readme should not mention any particular information about the runs."** — the operator,
> 2026-08-23, clarifying after the three corrections above. This is a harder line than "cut the
> diary", and it is the specification. **No run names, no per-run costs, no terminal-status
> tallies, no trial ids, no dates of individual runs, in any section** — not in the result table,
> not in a caveat, not in a parenthesis. A result is a statement about the *stacks* or about the
> *instrument*; the run it was measured in is provenance, and provenance lives in
> `eval/RUNS.md` and `eval/FINDINGS.md`.

**The test for every line: would a reader arriving today, who has never seen this project, be
worse off without it?** Not "is it true", not "was it expensive to learn" — those are what
`eval/FINDINGS.md` and `eval/RUNS.md` are for.

This has a real consequence for the result table, so do not be surprised by it: **most rows of
`# THE RESULT` currently carry their scope inline** — run names, cell counts, dollar figures —
because a previous round of work established that an aggregate without its scope is unfalsifiable
(#113). That reasoning is sound and it does not require the scope to be *in this file*. The
resolution is a **producer or a pointer, not a run name**: state the finding, and beside it name
the command or the document that reproduces it. `python3 eval/tools/census.py` and
`eval/judge/field_ranks.py` already exist for exactly this. A finding with a producer beside it
is more checkable than one with a run name beside it, not less.

Keep, and these are the file's actual job:

- **what it is about** — the goal, the four stacks, that a harness the building agents cannot see
  grades the result
- **the current found results** — the null, the five independent routes that reach it, and what
  it does and does not license. **Stated as findings about the stacks, with producers, not with
  run provenance.**
- **how to run things** — the `Running things` block
- **how to evaluate results** — the three tiers as they stand now (tier 1 is a gate,
  `overall = tier2`, tier 3 at 0.00), and the controls to run before believing a score
- **where things live / Start here** — this is the routing that makes the four points above
  usable, and it is how a reader reaches the run history they are no longer being handed
- **the distilled rules**, if they survive the reader test — they are the project's transferable
  output and mention no run

Cut:

- **the per-run diary.** Every run's story, its cost, its terminal statuses, what went wrong in
  it. `eval/RUNS.md` has all of it. Replace the whole `### Done` section with a pointer.
- **the whole opening census table**, including `$2,773.04 to date`, the record counts, the
  terminal-status partition and the per-run directory counts. Every row of it is particular
  information about the runs. What the reader needs from it is one sentence — *the corpus is
  whole-game trials across four games and four stacks, and `python3 eval/tools/census.py` prints
  its current size with the population it counted* — and the producer makes that sentence
  self-updating, which the table never was.
- **total-spend accounting.** A receipt, not a result. **Cost survives in exactly one place: the
  finding that cost does not discriminate stacks** — the between-stack range is a fraction of its
  own within-cell noise floor, and cost tracks turns almost perfectly, so it is close to a
  restatement of how many turns an agent chose to take. That is a measurement about the stacks.
  **Re-read both figures from their source before quoting them, and cite the producer, not the
  run they came from.**
- **the ⚠️ withdrawal notices** — five of them, ~45 lines. See the constraint below: they can go
  entirely, because removing the figure is a cleaner repair than annotating it.
- **superseded-instrument commentary.** "It read 4/8 and then 5/8 before that, and both were
  correct when written" is a finding about the play-bot, and it is already one.

WHAT MUST NOT BE LOST, AND HOW TO PROVE IT

> **Verify the destination BEFORE you cut, not after.** For every block you remove, grep the
> file you believe already holds it and confirm the substance is there. If it is not, **move it
> first, in its own commit**, then cut. A cut whose content existed nowhere else is not a
> simplification, it is a deletion — and this project's whole standard is that evidence survives.

Specifically protected. **Each of these is a result or a reader-safety statement, and each has a
run-free form** — that form is what stays, not the current wording:

| protect | the run-free form |
|---|---|
| **that comparability boundaries exist** — the arena set straddles a machine repair (#49), the tier-weighting change (#123), and the Bash-allowlist change each void a comparison | ONE sentence: results from different runs mostly may not be pooled, and `eval/RUNS.md` says which may. **Name no run.** A reader who misses this will pool numbers that must not be pooled, and that is the single most damaging thing this file can fail to say |
| **that spec-change and whole-game records are two instruments and are never pooled** | keep, as a property of the corpus. The retired suite needs no history here beyond that its stored results remain readable |
| **the three genuine submission defects** | keep the *result* — across every criterion failure ever adjudicated, exactly three are properties of the work and everything else traced to the grader. **Drop the per-trial breakdown**: the trial ids, the run names, the reclassification story. That is `eval/FINDINGS.md` |
| **that the tier-3 rounds are not defensible as blind (#83)** | keep as a licensing statement on the subjective layer. It bears directly on what a reader may conclude |
| **that the null is a noise floor, not proof of equality** | keep verbatim in substance — it is the most important sentence in the file |

**The rule that resolves every hard case: if removing the run name makes the statement false, it
was history. If it makes the statement more general, it was a result badly written.**

THE GATE CONSTRAINT — read this before deleting a ⚠️ block

`eval/withdrawn.json` holds 8 register entries, each with a `match` regex list, and
`docstat.py --withdrawn` fails a **live** document that restates a retired figure without citing
the entry id in the same block. `README.md` is live.

**Removing the figure removes the obligation.** The register keeps the history — that is its
entire purpose — so a README with no `1.70/2.05`, no `20 of 24`, no `380`, no `$2,404.21` and no
`24 whole-game submissions` needs no notice about any of them. This is the intended direction:
`AGENTS.md` says live documents *"state what is true now — replace superseded content rather
than annotating it."*

Two traps:

- Several `match` lists are **conjunctions** (`WR-20-of-24` needs both `20 of 24` *and* `1.000`).
  So a bare `1.000` elsewhere is fine today **because its partner is gone**. If you keep one
  half of a pair and delete the notice, the gate fires. Run `--withdrawn` unpiped after every
  block you remove, not once at the end.
- `WR-readme-opening-counts` and `WR-readme-findings-count` are anchored to `tasks/` files, not
  to README. Deleting README text does not orphan them.

WHAT NOT TO CONCLUDE

**Do not treat the line count as the target.** A README cut to 150 lines that drops the
comparability warning is a worse document than the 643-line one, because that warning is the
thing that stops a reader computing a number they must not compute. If the honest answer for a
section is *"this is long and every line of it is load-bearing"*, keep it and say why — that
closes that section.

**Do not read "no particular information about the runs" as "no numbers".** The operator asked
for the current found *results*, and a result without a number is an opinion. What goes is the
provenance — which run, which trial, what it cost, when. What stays is the finding and the
command that reproduces it.

**Do not rewrite the result.** The null, its five independent routes, and the licensing
paragraph are the project's output. Shorten the prose around them if it is genuinely redundant;
do not restate the finding in your own words. Any number you keep must be one you re-read from
its source in this session (`AGENTS.md` rule 5) — and if you keep a count, keep the producer
command beside it.

FILE CONFLICT — one peer is live in this file

`tasks/102` is in flight and is fixing **one** citation at `README.md:510`, `#126` → `#128`.
Nothing else of theirs is in this file. Either fix that citation yourself as part of this work
(check it with `python3 eval/tools/docstat.py --renumbered` first — the published number is what
is right, never the citation), or leave line 510's paragraph structurally alone so the merge is
a one-line resolution. Say in your report which you did.

`eval/RUNS.md`, `eval/FINDINGS.md` and `DECISIONS.md` have no peer in them right now. If you
need to move content into one, you may.

WHAT EACH OUTCOME MEANS

- **The file gets substantially shorter and nothing protected is lost** — the expected result.
  Record before/after line counts and a table of what was cut against where it now lives.
- **A block turns out to exist nowhere else** — move it to the right file first, in its own
  commit, and say so. That is a finding about the documentation, not an obstacle.
- **A section resists cutting because every line is load-bearing** — a real answer. Say which
  section and what each line protects.
