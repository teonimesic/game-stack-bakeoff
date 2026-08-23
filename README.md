# Agent-oriented game development template — research, build, and bake-off

**Goal:** find the stack in which a coding agent, given a well-designed template, builds the best
game — and prove it by measurement rather than argument.

Four starter templates, one per candidate stack (`eval/starters/godot`, `rust`, `ts`, `unity`),
each tuned to its own stack's strengths rather than to a floor all four share. Blank `claude -p`
sessions build whole games in each; **a harness the building agents cannot see grades the result**,
and `eval/judge/verify_blind.py` is what checks that they cannot see it.

Netcode, multiplayer and console portability were researched (`research/`) and are not built.

**This file holds four things and nothing else: what the project is, what it has found, how to run
it, and how a submission is graded.** Anything particular to a run — what it cost, what went wrong
in it, which runs may be compared with which — is in `eval/RUNS.md`. What went wrong and what it
taught is in `eval/FINDINGS.md`. How big the stored corpus is, at any moment, is whatever
`python3 eval/tools/census.py` prints, with the population it counted beside each figure.

---

# THE RESULT: there is no best stack, and the finding is that the question does not resolve

**Four well-built templates on Opus are indistinguishable on every task put to them.**

| evidence | what it says | re-derive it with |
|---|---|---|
| **the deterministic tiers are at their ceiling** | Tier 2 is the only scored tier, and it returns **one value for every submission in 5 of 10 (run, game) groups**. Tier 1, before it became a gate, returned one value in 7 of 10 — and in **0 of 10** did both tiers vary among the trials the play-bot could measure, so the weighted sum never had two signals to combine (#92, #123). Saturation is a property of the task being finished, not of there being too few criteria: four harder criteria built from requirements the newest task states and no criterion checks passed **8 of 8** (#128) | `eval/judge/tier2_census.py`, `eval/judge/tier1_census.py` |
| **the two trials of a cell are different artifacts the instrument mostly cannot separate** | Compared criterion by criterion, the two independent trials in a cell agree on **verdicts** far more often than on **evidence strings** — the majority of which differ, and differ in substance. That control is what makes the agreement readable: identical verdicts on identical artifacts would say nothing. "Mostly", not "never" — verdict differences are not zero in every scope | the per-scope figures, with their scopes, are the `replaced_by` of `WR-paired-verdict-tie` and `WR-paired-evidence-diff` in `eval/withdrawn.json`; `python3 eval/tools/docstat.py --withdrawn` prints them |
| **cost does not discriminate, and cannot** | On the one field measured on all four stacks at once, the **between-stack range is 42% of its own within-cell noise floor**. The mechanism matters more than the ratio: **cost tracks turns at r = 0.971**, and turns vary 205–370 *within a single stack*. Cost is very nearly a restatement of how many turns an agent chose to take, so it cannot separate stacks and no *n* would fix that (#63) | no producer prints this; #63 records the field, the method and the per-stack table |
| **no subjective aspect separates the stacks** | On the only field tier 3 has judged, `value=rank order=pool`: between-stack range of mean ranks **2.100** against a mean within-stack gap of **1.925** after the instrument was repaired, **1.900** against **2.275** before. The quantity has two free method parameters, so each round is four readings; across all **eight**, the between-stack range never exceeds the within-stack gap by more than **23%**, and on **four of eight** it is smaller. No method separates these stacks and the direction is not stable enough to argue from | `eval/judge/field_ranks.py --rounds <stored rounds>`; `eval/RUNS.md` says which are stored |
| **a fourth game, unseen by the templates, changes nothing** | The fourth task was written *after* all four templates were fixed, so it is the first with no history of having been shaped, however unintentionally, around what the templates already did well. It reproduces the null | `eval/judge/RUBRIC.md` for its criteria; `eval/G4-PLATFORMER.md` for its design |

**Five instruments, five different routes, the same null.** Tier 1 (builds, lints, tests, frames,
audio), tier 2 (a scripted bot driving thousands of ticks), cost, the five-aspect LLM judge layer,
and a **fourth game none of the templates had seen** each reach it independently. None was
designed as a check on the others, and that the newest task lands in the same place is the single
strongest thing that can be said for the null.

> ⚠️ **Two rounds of the subjective layer are among those later shown to have opened pack files
> naming the submissions (#83), so nothing tier 3 has produced is defensible as a blind result.**
> It stays at weight 0.00 and contributes nothing to any score.

**The subjective layer's one positive result is about itself, not about the stacks.** Against a
measured noise floor of mean self-tau **+0.853** for the instrument judging an identical field
repeatedly, `fun` and `fun_frames` — the same question, anchors and scale, differing only in
whether the telemetry is shown — rank the field at tau **+0.043**. The telemetry is doing work,
and the submissions that move are exactly those whose telemetry was extreme: the first evidence
here that a judge read its evidence rather than its packaging. It was pre-registered before the
numbers existed, it licenses **no cross-stack ranking**, and the outcome named in advance as most
damaging to the layer did not occur. `eval/judge/JUDGING.md`, FINDINGS #68.

> ⚠️ **Results from different runs mostly may NOT be pooled, and `eval/RUNS.md` says which may.**
> Task changes, starter changes, grader changes and one machine repair each void a comparison, and
> the boundaries are numbered there. A reader who misses this will compute a number that must not
> be computed — it is the single most damaging thing this file could fail to say.
>
> The corpus also holds **two instruments, never pooled**: whole-game trial records, and the
> records of a retired spec-change suite that ran different tasks and is graded differently.
> `census.py` partitions them and sums only where a sum is meaningful; the retired suite's stored
> results remain readable (`eval/AGENTS.md`).

### Three genuine submission defects in the entire project

Across every criterion failure ever adjudicated, **exactly three are properties of the work**: one
submission that does not compile, one whose own render tests fail on assertions its agent wrote,
and one that ships analyzer violations failing its template's strict gate. **Everything else
traced to the grader** — sixteen play-bot false negatives in one sweep, three more under the audio
task, two more later, a withdrawn stack ranking that was a screenshot artifact, and five
stack-correlated signals that were all the instrument. The trial-by-trial account, including one
defect that was correctly recorded as a *template* defect until the template's lint recipe was
repaired, is in `eval/FINDINGS.md` and `eval/RUNS.md`.

### What this does and does not license

- **It does not say the stacks are equal.** A null from an instrument with zero within-cell
  resolution is the instrument's noise floor, not a measurement of equality. Proving a tie needs
  ~96 judge rounds per aspect and the deterministic tiers cannot do it at any n.
- **It does say no ordering here is reportable.** The subjective ordering flips depending on
  which aspects are counted; the deterministic tiers are saturated; cost is noise.
- **It says the starters work.** Four independent stacks, four games, agents completing every
  task to a standard that saturates every mechanical check built to catch them failing.
- **Two trials per cell detects large gaps only.** If two stacks land close, this design cannot
  separate them — and the retired spec-change suite already failed to separate four stacks that
  all scored 6/6 on it.
- **Do not assume the criteria have no false negatives left.** They are pinned in both
  directions — `python3 eval/judge/bot_mutants.py` reports **36 criteria pinned, 4 variants, 3
  session-lock controls, 0 expectations unmet** — and that has never yet been enough. Every false
  negative found here was found by adjudicating a failure against source, never by the suite.
  Assume the next one is there.

**A separate null, on this project's own instructions.** Does compliance with an always-loaded
rule fall as more rules are active at once? Measured over a pool of deterministically-checked
instructions at k = 1, 2, 4, 8, 16 plus a length control: **no — every arm scored 1.000, and the
largest decline consistent with the data is 3.3 percentage points.** What it does *not* establish
is the interesting claim: `python3 eval/tools/instruction_census.py` reports the always-loaded set
at **110–153 instructions** depending on definition (read 2026-08-23), and the experiment
reached 16. **Quote the command, not the digits** — that range has moved three times in a day
as the always-loaded documents grow, and the point survives any particular value (#144). Design,
result and controls: `eval/instrfollow/`.

---

## Where things live

| Directory | What it is |
|---|---|
| `research/` | Twelve briefs answering the original questions (`00-`…`11-`), plus `DECISION.md`. Every claim dated and sourced; unverified claims labelled. `DECISION.md` opens with a retraction — it decided on paper, and two of its eliminations were wrong. `10-stack-capability-matrix.md` is what each stack can do **at its pinned version**. |
| `eval/starters/<stack>/` | **What a whole-game trial actually copies**, one per stack. `wholegame.py` reads only this directory. Game-agnostic: a placeholder, the harness, the boundary and the `verify` gate. This is the product being measured. |
| `eval/` | The measurement harness, its findings, and every run's stored results. |
| `eval/instrfollow/` | **The instruction-count experiment.** `DESIGN.md` is pre-registered and written before any trial ran; `RESULT.md` is what came back. Its subject is a fresh agent on a fixed task outside this repository, not a trial in the matrix. |
| `eval/judge/` | Three-tier evaluation: deterministic checks, scripted play-bots, and an LLM judge. |
| `eval/RUNS.md` | **The run ledger.** Every run, what it cost, what it may be compared with, and every comparability boundary. |
| `DECISIONS.md` | Every decision that shaped this work, who made it, and why. **Read this before changing anything methodological.** |
| `eval/FINDINGS.md` | Findings #19-#148, including retractions. **Read this before trusting any number anywhere.** |
| `AGENTS.md` | The rules that are always loaded, including how these documents are kept current and what must never go stale. |
| `.coderabbit.yaml` | What a pull request here is reviewed for. Exclusion-only, and it drops the committed trial records and the archives it names — `tasks/` is an archive it deliberately keeps reviewable. `DECISIONS.md` holds the reasoning and what would re-open it. |

## Start here

- **What was decided and why?** → `DECISIONS.md`
- **What went wrong and what it taught?** → `eval/FINDINGS.md`
- **What did a given run cost, and what may I compare it with?** → `eval/RUNS.md`
- **How big is the stored corpus right now?** → `python3 eval/tools/census.py`
- **Why this stack?** → `research/DECISION.md` (the *prior*; the bake-off is the evidence)
- **What can each stack actually do at its pinned version?** → `research/10-stack-capability-matrix.md`
- **What does a building agent read?** → `eval/starters/<stack>/AGENTS.md`
- **Does the always-loaded instruction file actually get followed?** → `eval/instrfollow/RESULT.md`
- **How is a submission graded?** → `eval/judge/RUBRIC.md`
- **How does subjective judging work, and what is being changed?** → `eval/judge/JUDGING.md`
- **What is not done yet?** → `tasks/`, via `python3 eval/tools/tasks.py next`

---

## How a submission is graded

Three tiers. The building agent sees none of them — blinding is verified mechanically by
`eval/judge/verify_blind.py`, which scans for the rubric's canary GUID, its reachability from every
ancestor directory, and every criterion id the rubric defines.

| Tier | Weight | What it measures |
|---|---|---|
| **1. Programmatic** | **GATE** | Builds, gate green, lints clean, tests pass, frames render and animate, performance probe — plus, where the task asks for sound, five audio criteria (manifest complete, files decode, nothing silent, effects genuinely distinct by decoded content, music loops and is long enough). 9 criteria, or 14 with audio. **PASS/FAIL, reported with the failing ids — not part of the score.** |
| **2. Play-bot** | **1.00** | A scripted bot drives thousands of ticks and asserts the game actually plays: collisions resolve, scoring works, the match ends, replays reproduce. Where the task asks for sound, it also asserts every event the run *actually emitted* has a working cue. |
| **3. LLM judge** | **0.00** | One specialist per aspect, each ranking a whole eight-submission field for a game rather than scoring one at a time. **Diagnostic only — contributes nothing to the score, and stays at 0.00 until it passes its validation gates.** |

`overall = tier2`. **Tier 1 stopped being 0.31 of the score on 2026-08-23** (#92, #123): across 68
stored submissions it returned a single value in 7 of 10 groups, and its seven failing trials were
two build failures whose tier-2 zero says the same thing and five lint, unit-test or ink-coverage
findings on games that scored 1.000 on tier 2. It is a floor test and is now reported as one.
Re-derive with `eval/judge/weight_sensitivity.py` and `eval/judge/tier1_census.py`. **Scores stored
before that date are in the old weighted regime and are marked as such — they were not rewritten**
(`eval/RUNS.md`).

**Tier 2 is itself at its ceiling on half the corpus, and that is accepted rather than repaired.**
`eval/judge/tier2_census.py`: 5 of 10 (run, game) groups return a single value. Promoting the
withheld diagnostic criteria cannot help — they are single-valued wherever they are recorded — and
harder criteria written from the newest task's own unchecked requirements passed 8 of 8. A binary
criterion asks whether a mechanic exists; every submission implements every mechanic, so on a
saturated group `overall` certifies completion and ranks nothing (#128, `DECISIONS.md`).

**Why the judge is unweighted** (see `DECISIONS.md` and FINDINGS #21) — two independent arguments,
which fail differently:

1. **It cannot reorder anything.** Its bounded contribution is smaller than the tightest adjacent
   gap the deterministic tiers already produce. True regardless of noise.
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability 0.462 on a
   contested submission, against 0.000 on an uncontested one. True regardless of weight.

Its per-criterion verdicts are genuinely useful and are still reported — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.

---

## Running things

```bash
cd eval/starters/rust && just verify   # the one gate (any starter)

cd eval
# whole-game matrix
python3 wholegame.py run    --stacks rust,ts,unity,godot --games g1_pong --trials 1
python3 wholegame.py evaluate --run-dir runs/<name> --eval-parallel 1
python3 wholegame.py report   --run-dir runs/<name>

# spec-change bake-off - RETIRED 2026-08-23, launch path deleted with the templates.
# Its stored trials are still readable, and so is what they were asked to do.
python3 runner.py report --run-dir runs/<name>
python3 regrade.py --run-dir runs/<name> --suite suites/bakeoff-ts.toml

# the subjective layer runs SEPARATELY, after the deterministic tiers, under a ceiling
python3 judge/field_sweep.py --run runs/<name> --games g1_pong \
    --aspects idiomatic fun --orders 2 --max-cost 60 --out runs/<name>/judge-sweep

# controls - run these before believing any score
python3 judge/audio_selftest.py       # 6 audio criteria vs 9 mutants
python3 judge/bot_mutants.py          # every play-bot criterion pinned in both directions
python3 judge/capability_selftest.py  # the no-stack-gap gate, its mutant and its variant
python3 judge/rusage_selftest.py      # peak RSS / CPU against a child of known size
python3 judge/capture_selftest.py     # a flood on either stream keeps the other (#100, #103)
python3 runner_capture_selftest.py    # the same, through runner.py, and that it is ONE policy (#114)

# what the pipeline can see about capture cost - reported, scored by nothing
python3 judge/capability.py --runs runs

# re-grade stored results offline, without re-running agents
python3 judge/regrade_wholegame.py --run-dir runs/<name>
python3 judge/verify_blind.py      --run-dir runs/<name>
```

Beyond those, `eval/judge/starter_parity.py` reports whether the four starters have drifted apart
on recipes, guides, harness files and the shared launch discipline. **Capability parity is
deliberately not a goal** — each template is at its own stack's best, so the divergences it prints
are the subject of the comparison and can never fail it.

The eval drives the `claude` CLI directly, not the SDK. `--setting-sources project` is mandatory
and empirically verified: without it the operator's global `~/.claude/CLAUDE.md` leaks into every
arm and confounds the comparison.

**The matrix runs with a targeted Bash allowlist** (`just`, `cargo`, `pnpm`, `git`). An early run
without one lost 29.8% of all turns to denials, so runs across that change are **not** comparable
(`eval/RUNS.md`).

---

## The one thing this project actually learned

130 numbered findings — `python3 eval/tools/docstat.py --findings` — and all but a few are
instances of one pattern:

> **A mechanism that runs, reports success, and measures nothing.**

Held-out tests that never compiled. A Stop hook silently disabled in every trial. A judge scoring
empty file packs. A criterion asking about file layout the anonymiser had already destroyed. A
`verify_blind` "pass" read from `tail`'s exit code rather than the scanner's.

Four later findings are worse than that shape and worth separating:

- **#19** — a mechanism that measures something and hands you a number *that is wrong*. A corrupted
  artifact produced plausible, in-range readings that were published as fact before the guard
  caught them. Indistinguishable from a real result at the moment you act on it.
- **#22** — a summary statistic that was arithmetically correct and referentially empty. A mean
  computed across four real runs and four non-events described no trial that ever ran, and
  manufactured a finding that survived scrutiny until the population was split.
- **#30** — a guard whose trigger condition named an *external* cause, applied to a failure with an
  *internal* one. It ran, matched, retried and reported, and could never have fired: the lock it
  waited for was held by its own caller. A correct diagnosis with the remedy addressed to the wrong
  agent.
- **#31** — the first defects here that would have failed **open**. Everything above fails closed:
  wrong, but reported. A harness that excuses a real failure because a log note contained the word
  "lock" reports nothing at all, and produces a *higher* score than the truth on work that did not
  earn it. **A fail-closed defect costs you trials; a fail-open defect costs you the result.**

The distilled rules, in order of how much they would have saved:

1. **A negative control is necessary and not sufficient.** `total=0 passed=0` is indistinguishable
   from "correctly failing". Every task needs a positive control that proves the grader can go
   green, and ideally an adversarial one.
2. **Never infer a process's state from its artifact's state.** An artifact mid-write is
   indistinguishable from one never written. Check the exit code the process reported.
3. **A pipeline's exit status is the last stage's.** `cmd | tail` reports `tail`.
4. **Never compute a mean over a population you have not established is homogeneous.** Partition by
   terminal status first; report `n` per group.
5. **LLM judge stability is a property of the artifact, not the rubric.** Validating a judge on
   clear-cut fixtures systematically overstates its reliability, because criteria agree when the
   answer is obvious and diverge when it is borderline — which is exactly when you need them.
6. **An artifact is MORE order-invariant than a judgement, not less.** Three of the subjective
   layer's four gates are statistical, and all three passed the one aspect that turned out to be
   ranking a harness quantity. Two judges with *no evidence in common* ranked the field
   identically, twice. **Statistical validation cannot distinguish a judge that reads its
   evidence from one that does not** — only reading the evidence can (#55).
7. **A repeated identical measurement across independent subjects is not corroboration.** It is
   the signature of a shared cause, and the shared cause is usually the instrument: six
   submissions scoring an identical 6/14 was `$TMPDIR` deleting their toolchains (#45); six
   failing two criteria with byte-identical evidence was a bot that stood still until it died
   (#46).
8. **An aggregate without its scope is not a weak claim, it is an unfalsifiable one.** It cannot
   be checked, so it survives indefinitely and gets quoted as established. Four summary statistics
   here were withdrawn for exactly this, and the register of what was retired — and what to state
   instead — is `eval/withdrawn.json`, enforced by `python3 eval/tools/docstat.py --withdrawn`.
9. **A count with a producer goes stale for an hour; a count with none goes stale forever.** Write
   the command beside the number. If a quantity has no producer, that is the defect.

**How these documents are kept current, and which of them may state a retired figure, is in
`AGENTS.md`.** It is the authority; this file does not restate it.
