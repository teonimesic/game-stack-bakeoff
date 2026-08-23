# Agent-oriented game development template — research, build, and bake-off

**The question.** Give a coding agent a well-built starting template and ask it to build a whole
game. Is there a technology stack in which it builds a *better* game than in the others — and can
that be settled by measurement instead of by argument?

**The setup.** Four starting templates, one per candidate stack: Godot, Rust/Bevy, TypeScript and
Unity. A fresh `claude -p` session with no knowledge of this project is dropped into one of them
and asked to build a game. A separate grading harness, which the building agent cannot see, then
scores what came out. [`eval/judge/verify_blind.py`](eval/judge/verify_blind.py) is what checks
that it really cannot see it.

**The answer so far: no stack wins, and the honest reading is that this instrument cannot tell
the four apart.** What that does and does not mean is the next section.

Netcode, multiplayer and console portability were researched ([`research/`](research/)) and
deliberately not built.

> **What this file is.** Four things and nothing else: what the project is, what it found, how to
> run it, and how a submission is graded. Anything particular to one run — what it cost, what went
> wrong in it, which runs may be compared with which — is in [`eval/RUNS.md`](eval/RUNS.md). What
> went wrong and what it taught is in [`eval/FINDINGS.md`](eval/FINDINGS.md). How big the stored
> corpus is, at any moment, is whatever `python3 eval/tools/census.py` prints.

---

## The words this file uses

Read this once and the rest of the file parses.

| term | what it means here |
|---|---|
| **stack** | one of the four technologies under comparison: Godot, Rust/Bevy, TypeScript, Unity |
| **starter** | the template an agent is handed at the start: a placeholder game, a build recipe, and a `verify` command. It contains no grading rubric |
| **game** | one of the four things an agent is asked to build — pong, 3D tetris, an arena shooter, a platformer |
| **trial** | one agent, one stack, one game, from an empty session to finished work |
| **cell** | one (stack, game) pair. Each cell is run **twice**, by two independent agents |
| **submission** | the code one trial produced. This is what gets graded |
| **field** | the eight submissions for one game — four stacks × two trials — ranked together |
| **criterion** | one yes/no question about a submission, answered with stored evidence |
| **gate** | a check that must pass, but adds nothing to the score |
| **saturated** | every submission in a group scored the same, so the score ranks nothing |
| **noise floor** | how far apart the *two trials of the same cell* land. A between-stack difference smaller than that is not a difference |
| **blinding** | hiding which stack a submission came from, so an LLM judge cannot score the stack instead of the work |

And the three graders, which the rest of the file calls **tiers**:

| | what it asks | what it contributes |
|---|---|---|
| **tier 1 — programmatic** | does it build, lint, test, render frames and answer a probe? | **a gate.** Pass/fail, no score |
| **tier 2 — play-bot** | a script plays the game for thousands of ticks. Does it actually *play*? | **the entire score** |
| **tier 3 — LLM judge** | one specialist model per aspect ranks a whole field on taste-like questions | **nothing.** Weight 0.00 |

[How a submission is graded](#how-a-submission-is-graded) has the detail.

---

# THE RESULT: no stack wins, and the question does not resolve

**Four well-built templates on Opus are indistinguishable on every task put to them.**

Five separate instruments were pointed at the question. Four of them reach the same null by
different routes; the fifth turned out not to be usable at all.

| the instrument | what it says | how to re-derive it |
|---|---|---|
| **the play-bot tier is at its ceiling** | Tier 2 is the only scored tier, and it returns **one value for every submission in 5 of 10 (run, game) groups**. Tier 1, before it became a gate, returned one value in **7 of 10** — and in **0 of 10** did both tiers vary among the trials the play-bot could measure, so the weighted sum never had two signals to combine ([#92], [#123]). It saturates because the task is *finished*, not because there are too few questions: four harder criteria, built from things the newest game's prompt asks for and no criterion checked, passed **8 of 8** ([#128]) | `eval/judge/tier2_census.py`, `eval/judge/tier1_census.py` |
| **the two trials of a cell are different work the instrument mostly cannot separate** | Compared criterion by criterion, the two independent trials in a cell agree on **verdicts** far more often than on **evidence** — most of the evidence strings differ, and differ in substance. That control is what makes the agreement readable: identical verdicts on identical artifacts would say nothing. "Mostly", not "never" | the per-scope figures are the `replaced_by` of `WR-paired-verdict-tie` and `WR-paired-evidence-diff` in [`eval/withdrawn.json`](eval/withdrawn.json); `python3 eval/tools/docstat.py --withdrawn` prints them |
| **cost does not discriminate, and never can** | On the one measure taken on all four stacks at once, the **between-stack range is 42% of its own noise floor**. The mechanism matters more than that ratio: **cost tracks turns taken at r = 0.971**, and turns vary **205–370 within a single stack**. Cost is very nearly a restatement of how many turns an agent chose to take, so it cannot separate stacks and no number of extra trials would fix that ([#63]) | no producer prints this; [#63] holds the method and the per-stack table |
| **a fourth game, unseen by the templates, changes nothing** | The fourth game was written *after* all four templates were frozen, so it is the first with no history of having been shaped — however unintentionally — around what the templates already did well. It reproduces the null | [`eval/judge/RUBRIC.md`](eval/judge/RUBRIC.md) for its criteria, [`eval/G4-PLATFORMER.md`](eval/G4-PLATFORMER.md) for its design |
| **the LLM judge is not a fifth route** | No subjective aspect separates the stacks either — but that can no longer be offered as independent corroboration, because **the blinding failed and every one of the 84 stored judge packs carried text naming the stack**. See the warning below | [`eval/judge/JUDGING.md`](eval/judge/JUDGING.md); `eval/judge/field_ranks.py --rounds <stored rounds>` |

> ⚠️ **The subjective layer's blinding failed, and the repairs licence new rounds without
> repairing any stored one.** Pack files named the submissions ([#83]); the anonymiser's stack
> vocabulary was a list of spellings, so one arm shipped its build tool's name into 22 packs and
> **every** judge round that recorded which files it opened had opened a leaking one ([#131]);
> and the blinding hid the extension of the file the judge *opens* and none of the ones it
> *reads* — 2,083 stack-naming tokens across all 84 packs, the densest of them in a file the
> packer wrote itself ([#137]). Tier 3 stays at weight 0.00 and contributes nothing to any score.

**What the subjective layer did establish is about itself, not about the stacks.** Judging an
identical field twice, the instrument agrees with itself at a mean rank correlation of **+0.853**
— that is its noise floor. `fun` and `fun_frames` are the same question with the same anchors and
the same scale, differing only in whether the judge is shown the play telemetry, and they rank the
field at **+0.043**. The telemetry is doing the work, and the submissions that move are exactly
the ones whose telemetry was extreme: the first evidence here that a judge read its evidence
rather than its packaging. It was written down before the numbers existed, it licenses **no
cross-stack ranking**, and the outcome named in advance as most damaging to the layer did not
occur ([#68], [`eval/judge/JUDGING.md`](eval/judge/JUDGING.md)).

> ⚠️ **Results from different runs mostly may NOT be pooled.**
> [`eval/RUNS.md`](eval/RUNS.md) says which may. A change to a game, to a starter, to a grader, and
> one machine repair each void a comparison, and the boundaries are numbered there. A reader who
> misses this will compute a number that must not be computed — it is the single most damaging
> thing this file could fail to say.
>
> The corpus also holds **two instruments that are never pooled**: whole-game trial records, and
> the records of a retired suite that ran different tasks and was graded differently. `census.py`
> partitions them and sums only where a sum means something ([`eval/AGENTS.md`](eval/AGENTS.md)).

## Is it still true? What would settle it? What is being done?

**Re-checked against the stored corpus on 2026-08-23, by re-running every producer named above.**
Nothing that has landed since separates the stacks. One thing did change, and it is a subtraction:
the LLM judge can no longer be counted as an independent route to the null, because none of its
stored rounds was blind. The headline rests on four routes, not five.

Two other repairs of the period cut the same way — they removed *false differences*, not the null.
A guard that stopped a game window stealing the keyboard was minimising it instead, and macOS then
handed the same frozen frame to every screenshot, which read as six of nine render tests failing on
one stack ([#133]). And a proposed new scoring measure that did spread the field turned out to
reorder it whenever the play-bot was improved, so it was measuring the bot ([#139]).

**What would settle it — every route, priced.**

| route | what it would take | status |
|---|---|---|
| **make the play-bot tier harder** | both in-rubric repairs were tried and measured. Promoting a withheld criterion moves every score in a group by the same amount; four harder criteria passed 8 of 8 | **closed.** It is not a shortage of criteria ([#128]) |
| **a harder game, or a fifth one** | one clean eight-cell field. The price is in [DECISIONS.md](DECISIONS.md#a-harder-task-is-priced-here-and-gated-behind-a-free-pre-test--decided-2026-08-23) | **priced, not bought.** A free offline pre-test ran first and came out *against* buying it ([#139]) |
| **the LLM judge** | roughly **96 rounds per aspect** for a statistical tie ([`eval/judge/JUDGING.md`](eval/judge/JUDGING.md) prices it), and every stored round would have to be re-run, because none was blind | **not started** |
| **cost** | nothing would settle it. Cost is a proxy for turns, and turns are a per-agent choice | **closed** ([#63]) |

**What is being done about it: nothing is currently running against the stack question, and no
trial is scheduled.** `python3 eval/tools/tasks.py list` holds no item that would produce a new
stack measurement, and [`eval/IMPROVEMENTS.md`](eval/IMPROVEMENTS.md)'s latest iterations are
repairs to the blinding. The work in flight is on the instrument and on these documents. Buying
an answer is the operator's call, and the price is in the table above.

## What this does and does not license

- **It does not say the stacks are equal.** A null from an instrument with no resolution inside a
  cell is that instrument's noise floor, not a measurement of equality.
- **It does say no ordering here is reportable.** The subjective ordering flips depending on which
  aspects are counted, the deterministic tiers are saturated, and cost is noise.
- **It says the starters work.** Four independent stacks, four games, agents completing every task
  to a standard that saturates every mechanical check built to catch them failing.
- **Two trials per cell detects large gaps only.** If two stacks land close, this design cannot
  separate them — and a retired earlier suite already failed to separate four stacks that all
  scored 6/6 on it.
- **Do not assume the criteria have no false negatives left.** They are pinned in both directions
  — `python3 eval/judge/bot_mutants.py` reports **36 criteria pinned, 4 variants, 3 session-lock
  controls, 0 expectations unmet** — and that has never yet been enough. Every false negative
  found here was found by adjudicating a failure against source, never by the suite.

## Almost every failure recorded here was the grader's, not the submission's

All **16** play-bot failures ever adjudicated against source were **false negatives** — the
criterion fired on correct work. They are listed by trial and criterion in
[`eval/judge/audit_criteria.py`](eval/judge/audit_criteria.py). Add to them a withdrawn stack
ranking that was a screenshot artifact, and five stack-correlated signals that were all the
instrument.

**Three failures in the whole project are properties of the work**: one submission that does not
compile, one whose own render tests fail on assertions its agent wrote, and one that ships
analyzer violations failing its template's strict gate. *That three is a hand adjudication and
has no producer* — treat it as a reading of the record, not as a measurement. The trial-by-trial
account is in [`eval/FINDINGS.md`](eval/FINDINGS.md) and [`eval/RUNS.md`](eval/RUNS.md).

## A separate null, on this project's own instructions

Does an agent follow an always-loaded rule less well as more rules are active at once? Measured
over deterministically-checked instructions at k = 1, 2, 4, 8, 16, plus a length control:
**no — every arm scored 1.000, and the largest decline consistent with the data is 3.3 percentage
points.** What it does *not* establish is the interesting claim. `python3
eval/tools/instruction_census.py` puts the always-loaded set at **112–155 instructions** depending
on definition (read 2026-08-23), and the experiment reached 16. **Quote the command, not the
digits** — that range has moved repeatedly as the always-loaded documents grow, and the point
survives any particular value ([#144]). Design, result and controls:
[`eval/instrfollow/`](eval/instrfollow/).

---

## Start here

| question | where |
|---|---|
| What was decided, and why? | [`DECISIONS.md`](DECISIONS.md) |
| What went wrong, and what did it teach? | [`eval/FINDINGS.md`](eval/FINDINGS.md) — 139 entries. Findings #19-#157, count and range from `python3 eval/tools/docstat.py --findings` |
| What did a run cost, and what may I compare it with? | [`eval/RUNS.md`](eval/RUNS.md) |
| How big is the stored corpus right now? | `python3 eval/tools/census.py` |
| Why these four stacks? | [`research/DECISION.md`](research/DECISION.md) — the *prior*. The bake-off is the evidence, and it opens with a retraction |
| What can each stack actually do, at its pinned version? | [`research/10-stack-capability-matrix.md`](research/10-stack-capability-matrix.md) |
| What does a building agent read? | `eval/starters/<stack>/AGENTS.md` |
| Is the always-loaded instruction file actually followed? | [`eval/instrfollow/RESULT.md`](eval/instrfollow/RESULT.md) |
| How is a submission graded? | [`eval/judge/RUBRIC.md`](eval/judge/RUBRIC.md) |
| How does subjective judging work, and what is changing? | [`eval/judge/JUDGING.md`](eval/judge/JUDGING.md) |
| What is not done yet? | [`tasks/`](tasks/), via `python3 eval/tools/tasks.py next` |
| What are the always-loaded rules? | [`AGENTS.md`](AGENTS.md) |
| What is a pull request here reviewed for? | [`.coderabbit.yaml`](.coderabbit.yaml) — exclusion-only; [`DECISIONS.md`](DECISIONS.md) holds the reasoning and what would re-open it |

Two directories are worth knowing about before you open anything:

- [`eval/starters/`](eval/starters/) — **the product being measured.** One template per stack, and
  the only thing a trial copies. Game-agnostic: a placeholder, the harness, the boundary and the
  `verify` gate.
- [`eval/`](eval/) — the measurement harness, its findings, and every run's stored results.

---

## How a submission is graded

Three tiers. The building agent sees none of them, and the blinding is verified mechanically by
[`eval/judge/verify_blind.py`](eval/judge/verify_blind.py), which scans for the rubric's canary
GUID, its reachability from every ancestor directory, and every criterion id the rubric defines.

| Tier | Weight | What it measures |
|---|---|---|
| **1. Programmatic** | **GATE** | Builds, gate green, lints clean, tests pass, frames render and animate, performance probe — plus, where the game asks for sound, five audio criteria (manifest complete, files decode, nothing silent, effects genuinely distinct by decoded content, music loops and is long enough). 9 criteria, or 14 with audio. **Pass/fail, reported with the failing ids — not part of the score.** |
| **2. Play-bot** | **1.00** | A scripted bot drives thousands of ticks and asserts the game actually plays: collisions resolve, scoring works, the match ends, replays reproduce. Where the game asks for sound, it also asserts that every event the run *actually emitted* has a working cue. |
| **3. LLM judge** | **0.00** | One specialist per aspect, each ranking a whole eight-submission field rather than scoring submissions one at a time. **Diagnostic only — contributes nothing, and stays at 0.00 until it passes its validation gates.** |

`overall = tier2`. **Tier 1 stopped being 0.31 of the score on 2026-08-23** ([#92], [#123]): across
68 stored submissions it returned a single value in 7 of 10 groups, and its 7 failing trials were
2 build failures — whose tier-2 zero already says the same thing — and 5 lint, unit-test or
ink-coverage findings on games that scored 1.000 on tier 2. It is a floor test and is now reported
as one. Re-derive with `eval/judge/weight_sensitivity.py` and `eval/judge/tier1_census.py`.
**Scores stored before that date are in the old weighted regime and are marked as such; they were
not rewritten** ([`eval/RUNS.md`](eval/RUNS.md)).

**Tier 2 is itself at its ceiling on half the corpus, and that is accepted rather than repaired.**
`eval/judge/tier2_census.py` reports 5 of 10 (run, game) groups returning a single value. Promoting
the withheld diagnostic criteria cannot help — they are single-valued wherever they are recorded —
and harder criteria written from the newest game's own unchecked requirements passed 8 of 8. A
binary criterion asks whether a mechanic exists; every submission implements every mechanic, so on
a saturated group `overall` certifies completion and ranks nothing ([#128],
[DECISIONS.md](DECISIONS.md#a-saturated-tier-2-is-reported-as-a-completion-certificate-not-repaired--decided-2026-08-23)).

**Why the judge is unweighted** — two independent arguments, which fail differently ([#21],
[`DECISIONS.md`](DECISIONS.md)):

1. **It cannot reorder anything.** Its bounded contribution of 0.10 is smaller than the tightest
   adjacent gap the deterministic tiers already produce, 0.0622. True regardless of noise.
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability up to
   0.462 on a contested submission, against 0.000 on an uncontested one. True regardless of weight.

Its per-criterion verdicts are genuinely useful and are still reported — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.

---

## Running things

```bash
cd eval/starters/rust && just verify   # the one gate (any starter)

cd eval
# whole-game matrix
python3 wholegame.py run      --stacks rust,ts,unity,godot --games g1_pong --trials 1
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
are the subject of the comparison and can never fail it
([DECISIONS.md](DECISIONS.md#the-templates-are-measured-at-each-stacks-best-not-at-a-common-floor--decided-2026-08-22)).

The eval drives the `claude` CLI directly, not the SDK. `--setting-sources project` is mandatory
and empirically verified: without it the operator's global `~/.claude/CLAUDE.md` leaks into every
arm and confounds the comparison.

**The matrix runs with a targeted Bash allowlist** (`just`, `cargo`, `pnpm`, `git`). An early run
without one lost 29.8% of all turns to denials, so runs across that change are **not** comparable
([`eval/RUNS.md`](eval/RUNS.md)).

---

## The one thing this project actually learned

139 numbered findings — `python3 eval/tools/docstat.py --findings` — and all but a few are
instances of one pattern:

> **A mechanism that runs, reports success, and measures nothing.**

Held-out tests that never compiled. A Stop hook silently disabled in every trial. A judge scoring
empty file packs. A criterion asking about file layout the anonymiser had already destroyed. A
`verify_blind` "pass" read from `tail`'s exit code rather than from the scanner's.

Four findings are worse than that shape and are worth separating:

- [#19] — it measures something and the number is **wrong**. A corrupted artifact produced
  plausible, in-range readings that were published as fact. Indistinguishable from a real result at
  the moment you act on it.
- [#22] — a statistic that was arithmetically correct and **referentially empty**. A mean across
  four real runs and four non-events described no trial that ever ran.
- [#30] — a guard whose trigger named an *external* cause, applied to a failure with an *internal*
  one. It ran, matched, retried, reported, and could never have fired: the lock it waited for was
  held by its own caller.
- [#31] — the first defects here that would have failed **open**. Everything above fails closed:
  wrong, but reported. **A fail-closed defect costs you trials; a fail-open defect costs you the
  result.**

Four rules that are specific to measuring this way, and are not in [`AGENTS.md`](AGENTS.md):

1. **LLM judge stability is a property of the artifact, not of the rubric.** Validating a judge on
   clear-cut fixtures overstates its reliability, because criteria agree when the answer is obvious
   and diverge when it is borderline — which is exactly when you need them ([#21]).
2. **An artifact is MORE order-invariant than a judgement, not less.** Three of the subjective
   layer's four gates are statistical, and all three passed the one aspect that turned out to be
   ranking a harness quantity. Two judges with *no evidence in common* ranked the field
   identically, twice. **Statistical validation cannot distinguish a judge that reads its evidence
   from one that does not** — only reading the evidence can ([#55]).
3. **A repeated identical measurement across independent subjects is not corroboration.** It is the
   signature of a shared cause, and the shared cause is usually the instrument: six submissions
   scoring an identical 6/14 was a temp directory deleting their toolchains ([#45]); six failing
   two criteria with byte-identical evidence was a bot that stood still until it died ([#46]).
4. **An aggregate without its scope is not a weak claim, it is an unfalsifiable one.** It cannot be
   checked, so it survives indefinitely and gets quoted as established. Four summary statistics here
   were withdrawn for exactly this; the register of what was retired, and what to say instead, is
   [`eval/withdrawn.json`](eval/withdrawn.json), enforced by
   `python3 eval/tools/docstat.py --withdrawn`.

The rules that generalise past this project — negative controls, never inferring a process's state
from its artifact's, pipeline exit status, means over mixed populations, never quoting a value you
did not just read — are in [`AGENTS.md`](AGENTS.md), which also states how these documents are kept
current and which of them may state a retired figure. It is the authority; this file does not
restate it.

Every relative link on this page is checked by `python3 eval/tools/linkcheck.py`, path and heading
fragment both.

<!-- Finding links. Anchors are GitHub's heading rule, verified by eval/tools/linkcheck.py. -->
[#19]: eval/findings/certifies-nothing.md#19--the-failure-mode-that-is-worse-than-measuring-nothing
[#21]: eval/findings/documentation.md#21--an-llm-judges-verdict-stability-is-a-property-of-the-artifact-not-the-rubric
[#22]: eval/findings/certifies-nothing.md#22--a-summary-statistic-that-was-arithmetically-correct-and-referentially-empty
[#30]: eval/findings/one-arm-bias.md#30-a-guard-whose-trigger-names-an-external-cause-cannot-fire-on-a-failure-with-an-internal-one--and-looks-like-a-fix
[#31]: eval/findings/fail-open.md#31-the-first-defects-in-this-project-that-would-have-failed-open
[#45]: eval/findings/one-arm-bias.md#45-the-artifact-under-measurement-was-stored-somewhere-with-a-lifetime-shorter-than-the-measurement
[#46]: eval/findings/certifies-nothing.md#46-two-criteria-failed-six-submissions-for-four-kinds-of-enemy-the-bot-never-lived-long-enough-to-meet
[#55]: eval/findings/certifies-nothing.md#55-statistical-validation-of-a-judge-cannot-tell-a-judge-that-reads-its-evidence-from-one-that-does-not
[#63]: eval/findings/limits-and-cost.md#63-a-noise-floor-estimated-from-one-cell-was-wrong-by-a-factor-of-seven
[#68]: eval/findings/certifies-nothing.md#68-the-subjective-layers-first-positive-result-and-the-control-that-made-it-readable
[#83]: eval/findings/one-arm-bias.md#83-the-answer-key-was-in-the-judges-pack-again-codex-hook-scripts-carried-the-trial-id
[#92]: eval/findings/certifies-nothing.md#92-a-scored-tier-that-returns-the-same-number-for-every-submission-and-the-weight-in-front-of-it
[#123]: eval/findings/certifies-nothing.md#123-in-68-trials-the-031-weighted-tier-deducted-for-a-property-of-a-playable-game-exactly-five-times-and-every-one-of-those-five-was-a-lint-finding-a-unit-test-or-an-ink-coverage-window
[#128]: eval/findings/certifies-nothing.md#128-tier-2-saturates-because-the-task-is-finished-not-because-the-criteria-are-too-few--four-harder-criteria-built-from-the-tasks-own-unchecked-requirements-passed-8-of-8
[#131]: eval/findings/one-arm-bias.md#131-the-anonymisers-stack-vocabulary-was-a-list-of-spellings-so-the-rust-arm-shipped-its-build-tools-name-into-22-blind-packs--and-every-architecture-round-that-left-a-file-open-log-opened-one
[#133]: eval/findings/one-arm-bias.md#133-a-focus-guard-minimised-the-window-the-render-tests-read-pixels-from-and-a-frozen-frame-is-not-an-empty-one
[#137]: eval/findings/one-arm-bias.md#137-the-blinding-was-stated-as-a-property-and-implemented-as-a-suffix-so-it-hid-the-extension-of-the-file-the-judge-opens-and-none-of-the-ones-it-reads--and-the-densest-leak-was-written-by-the-packer-not-by-any-agent
[#139]: eval/findings/certifies-nothing.md#139-repairing-the-instrument-reordered-the-field-so-the-scalar-was-measuring-the-bot
[#144]: eval/findings/certifies-nothing.md#144-a-count-with-a-producer-still-goes-stale-because-the-producer-bounds-the-staleness-and-does-not-prevent-it--and-this-one-drifted-while-a-single-session-was-reading-it
