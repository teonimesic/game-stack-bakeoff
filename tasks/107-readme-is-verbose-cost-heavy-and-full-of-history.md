---
id: 107
title: README is verbose, cost-heavy and full of history - cut it to what is true now and useful to read
status: done
priority: 1
refs: README.md, eval/RUNS.md, eval/FINDINGS.md, DECISIONS.md, eval/withdrawn.json
done_when: README.md contains only what is true now and useful to a reader arriving today; the run-by-run history and the total-spend accounting are gone, each verified present in eval/RUNS.md or eval/FINDINGS.md BEFORE it is cut; docstat.py --sweep, --findings and --withdrawn each exit 0 unpiped; and the before/after line count is recorded with a table of what was cut and where it now lives
established_by: 'README.md cut from 643 to 281 lines (56%), branch task-107-readme-cut. Every destination was verified BEFORE the cut and the table of what-was-cut-against-where-it-lives is appended to the ticket. One block existed nowhere else - the end-to-end fixture control table, 0.796/0.401/0.089 returned README.md and no other file across the repo - and it was MOVED to eval/judge/RUBRIC.md in its own preceding commit 92912f9, annotated with the pre-2026-08-23 weighted scheme it was measured under. Every number kept was re-read from its source this session: tier2_census 5 of 10 groups saturated; tier1_census 68 submissions, 7 failing trials, 2 blocking at t2=0.0 and 5 at t2=1.000; the cost figures recomputed straight from the eight stored trial records giving mean within-cell gap 21.1525, between-stack range 8.9139, r=0.9709, turns 205-370, reproducing finding 63 exactly; field_ranks giving 2.100/1.925 post-repair and 1.900/2.275 pre-repair with the 23-percent and four-of-eight claims re-checked across all eight readings; bot_mutants 36 criteria, 4 variants, 3 session-lock controls, 0 unmet. GATES, all unpiped and exit 0: docstat --sweep, --findings, --withdrawn, tasks.py check, withdrawn_control.py. PINNED IN BOTH DIRECTIONS: planting 20-of-24 plus 1.000 in README turns --withdrawn to exit 1 naming WR-20-of-24, and restoring returns exit 0; rewriting the findings range to 19-110 turns --findings to exit 1 naming README.md, and restoring returns exit 0. FOUR STALE THINGS FIXED IN PASSING: README:510 cited 126 where the published number is 128, fixed here because the paragraph had to be rewritten anyway and README is now absent from --renumbered DECIDED STALE; a starter_parity claim of 401 lines of shared scaffolding that the tool has never printed, the 401 being hash lines of a 400-tick determinism tape; Eleven briefs where research holds twelve; and the always-loaded instruction count, which its own single-commit producer instruction_census.py now reports at 108-151 against the 73-113 carried in README.md and eval/instrfollow/RESULT.md, both corrected. That last one is a candidate finding and needs a number allocated at merge. ALSO REPAIRED: two AGENTS.md rows naming a README status section that no longer exists.'
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

---

## DONE 2026-08-23 — 643 lines to 281, on branch `task-107-readme-cut`

**643 → 281 lines, a 56% cut.** `docstat.py --sweep`, `--findings`, `--withdrawn` and
`tasks.py check` all exit 0 unpiped after the change.

### What was cut, and where it now lives — each destination verified BEFORE the cut

| cut from README | lines | where it lives now | how that was verified |
|---|---|---|---|
| opening census table (record counts, terminal-status partition, per-run directory counts, `$2,773.04 to date`) | ~15 | `python3 eval/tools/census.py`; `eval/RUNS.md` cumulative table | ran `census.py` (exit 0); read `eval/RUNS.md` lines 1-60 |
| the two ⚠️ notices under it (`WR-readme-opening-counts`, `WR-tree-census-one-level`) | ~20 | `eval/withdrawn.json`, anchors in `tasks/64-*` and `eval/findings/certifies-nothing.md` | `--withdrawn` prints both entries with their `replaced_by` |
| three ⚠️ notices in `# THE RESULT` (`WR-tier3-pair`, `WR-paired-verdict-tie`, `WR-paired-evidence-diff`, `WR-20-of-24`) | ~45 | same register | same; `--withdrawn` exit 0 after each removal |
| `### Done` — the whole run diary: spec-change bake-off, matrix #1 and its per-game cost table, `just film`, audio, criterion repairs, capability capture | ~100 | `eval/RUNS.md` (per-run), `eval/FINDINGS.md` (#25-#27, #29, #97), `eval/judge/RUBRIC.md` (criteria) | grepped `$11.30/$19.49/$13.62` → `eval/RUNS.md:445-447` and `eval/findings/limits-and-cost.md:79` |
| `### In flight` — specialist-judge ledgers, the superseded partial sweep, matrices #2/#3, the arena rewrite, g4 launch pricing, the aspect-reliability sweep | ~130 | `eval/RUNS.md` (§ Specialist-judge calls, per-run sections), `eval/judge/JUDGING.md` (reliability table at 1119-1124; `12 of the 15` packs at 333) | grepped `0.418`, `0.536`, `12 of the 15`, `0.853`, `+0.043` — all present outside README |
| `### Tier 3's first positive result` | ~17 | `eval/judge/JUDGING.md:776-788`, FINDINGS #68 | grepped `+0.853` and `+0.043` |
| `### ⚠️ The arena set is NOT comparable across stacks` | ~11 | `eval/RUNS.md:253`, FINDINGS #49 | read the RUNS.md heading |
| `### The measured numbers behind the result above` per-cell table | ~11 | `eval/RUNS.md` | run ledger holds every cell |
| per-trial breakdown of the three genuine submission defects | ~18 | `eval/RUNS.md:796-807, 1302`, `eval/findings/one-arm-bias.md:1098` | grepped `genuine submission defect` |
| `## Keeping this current` table | ~19 | `AGENTS.md`, "Keep the documentation current" — a superset, with the withdrawal-register row README never had | read `AGENTS.md` |
| end-to-end fixture control table (`ref_pong` 0.956 …) | 9 | **MOVED FIRST**, own commit `92912f9` → `eval/judge/RUBRIC.md`, under "Controls that must pass before any run is believed" | grepping `0.796` across the repo returned **README.md only**. See below |

### The one block that existed nowhere else

`0.796`, `0.401` and `0.089` appeared in **README.md and no other file**, and no script
reprints them — the table was assembled by hand from four evaluations. It was moved to
`eval/judge/RUBRIC.md` in its own commit before anything was cut, annotated with the scoring
scheme it was measured under: these are pre-2026-08-23 weighted `overall` values and tier 1 is
now a gate, so they may not be compared with a new reading. What they establish is
**monotonicity**, not a level, which is why they are worth keeping at all.

### Numbers kept, each re-read from its source in this session (rule 5)

| figure | producer run this session | result |
|---|---|---|
| tier-2 saturation, 5 of 10 groups | `eval/judge/tier2_census.py --runs eval/runs` | 10 groups, 5 saturated, VERDICT SATURATED |
| tier-1 floor test, 7 of 10 / 0 of 10 / 68 submissions / 7 failing trials | `eval/judge/tier1_census.py --runs eval/runs` | 68 submissions, n=7 failing: 2 blocking build failures at t2=0.0, and 5 at t2=1.000 — two TS unit-test, two lint, one ink-coverage |
| cost 42%, r = 0.971, turns 205-370 | recomputed directly from the eight stored trial records of the one four-stack field | mean within-cell gap **$21.1525**, between-stack range **$8.9139** (42.1%), r = **0.9709**, turns 205-370 — reproduces #63 exactly |
| tier-3 pair 2.100/1.925 and 1.900/2.275 | `eval/judge/field_ranks.py --rounds .../post` and `/pre` | exact; 23% max excess and "smaller on four of eight" both re-checked across all 8 readings |
| 36 criteria, 4 variants, 3 session-lock controls | `python3 eval/judge/bot_mutants.py` | "36 criteria pinned in both directions, 4 variants, 3 session-lock controls, 0 expectation(s) unmet" |
| 123 numbered findings, `#19-#141` | `docstat.py --findings` | agrees, exit 0 |

### Four stale things found on the way, all fixed

1. **`README.md:510` cited `#126`; the published number is `#128`.** Fixed here rather than
   left for `tasks/102` — the paragraph had to be rewritten anyway to remove run names, so
   leaving line 510 structurally alone was not available. Verified by reading the index row:
   `#128` is "Tier 2 saturates because the task is finished…", which is what the sentence
   claims. `README.md` no longer appears in `--renumbered`'s DECIDED STALE list. The remaining
   README row, the UNDECIDABLE `#103` inside the `Running things` code block, was left for
   `tasks/102`'s triage.
2. **`starter_parity.py` "proves Rust, TS and Godot are byte-identical on 401 lines of shared
   scaffolding; Unity matches on 400 of 401".** The tool prints no such thing. The 401 lines
   are the **hash lines of a 400-tick determinism tape** (`eval/starters/unity/Assets/Sim/Sim.cs:87`),
   not lines of scaffolding, and today's run says only "hash chain over 400 scripted ticks:
   rust is BYTE-IDENTICAL to godot", with unity diverging at tick 53 by one ULP — while the
   same output states that **cross-stack hash equality is deliberately not a requirement**.
   Replaced with the tool's own verdict: no drift on any measured axis, and capability parity
   is not a goal.
3. **`Eleven briefs`** — `research/` holds twelve (`00-` … `11-`).
4. **The always-loaded instruction count.** `README.md` and `eval/instrfollow/RESULT.md` both
   said **73–113** (`AGENTS.md` alone 39–60). `python3 eval/tools/instruction_census.py` today
   reports **108–151** (`AGENTS.md` alone 43–66), and `git log` shows the tool has exactly one
   commit and has never changed — so the always-loaded documents grew by roughly 40 instructions
   and neither document re-ran the producer sitting next to the number. Both are corrected, with
   the command and the date beside the figure. **This is a candidate finding and needs a number
   allocated by the orchestrator** — see the report.

### What the next agent must not re-derive

- **`--withdrawn`'s traps are real and both were hit-tested.** `WR-20-of-24` needs *both*
  `20 of 24` and `1.000`; the new README states `1.000` twice and is green because the partner
  is gone. `WR-readme-opening-counts` needs both `24 whole-game submissions` and **`three
  games`** — the phrase "three games" is now a live tripwire in `README.md`, which is why the
  file says "four games" where it means the game count. Run `--withdrawn` after any edit that
  reintroduces either phrase.
- **`RANGE_DOCS` in `docstat.py` requires `README.md` to state `Findings #A-#B`.** Deleting
  that sentence fails `--findings`. It is in the "Where things live" table.
- **`--sweep` does not check file paths.** One phantom path (`eval/RUDIC`-style: `eval/RUBRIC.md`
  for `eval/judge/RUBRIC.md`) was written and survived a green sweep. It was caught by a
  throwaway extractor over every backticked path in the file, proven in both directions on one
  known-present and one known-absent path first (AGENTS.md rule 12). Do that before trusting a
  README path.
- **The per-scope replacements for the withdrawn paired-criteria figures (436/5/332 and
  232/0/120) exist in `eval/withdrawn.json` and in no findings body.** `eval/findings/`'s #50
  states the *withdrawn* figures, which is correct for the archive. If those replacements are
  ever needed in prose, the register is the source.
