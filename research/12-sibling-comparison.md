# What the sibling programme holds that this repository could use

**Task 219. Comparison snapshot: 2026-08-30.** The sibling tree at
`~/Documents/heavenstudio/game-research-gpt` is **read-only** from this repository — verified: no
file in it modified after 2026-08-29. Its git metadata does not read from this machine (exit
128, recorded in the ticket), so sibling claims below cite file paths, not commits. The
comparison covers the mechanism-bearing paths listed under "Scope of the comparison"; stored
results and caches are outside line-by-line scope. Claims about this repository cite our own
paths. Interpretations are labelled.

## The question, and the answer

Three targeted extractions from `game-research-gpt` are already landed; the table below cites
them so nobody re-files them. This document is the systematic read of everything else, under one
rule the ticket sets: a mechanism can be right there and wrong here, because **the sibling
measures a different object.**

**The measured census: 20 sibling mechanisms already exist here in a same-or-stronger form, 1 is
an adoption candidate pending ticket 220's measurement, 8 are rejected with recorded reasons,
and 7 are things the sibling has that this repository deliberately does not.** Excluded stored
results and caches are outside this conclusion.

## What the sibling is, and why that bounds the comparison

The sibling recommends a game-development **template to human developers**: one Godot 4.7.1
typed-GDScript universal project (`template/`). It supports that recommendation with a
source-backed survey (`research/source-manifest.json`), engine spikes (`research/spikes/`), a
four-agent pilot with disclosed repair rounds (`evaluation/reports/FINAL.md`), and a matched
16-cell four-engine comparison (`evaluation/cross-engine/results/FINAL.md`).

Its figures: 301 surveyed URLs with SHA-256-recorded local copies; pilot mean 0.925 before
repairs and 0.950 after; comparison means Godot 0.7875, Defold 0.7500, Bevy 0.5625, Unity
0.5125 — one stochastic run per cell, "descriptive `n=1` evidence, not a statistical
engine-superiority claim" in the comparison's own words.

This repository measures **what coding agents can build**, per stack, under a blind-graded
harness. The two measure different objects: the sibling's harness defends submitted evidence
against tampering, with fresh sessions as reviewers; this repository's harness defends the
*instrument* against its own failure modes, because the thing that cannot be trusted here is the
grader (AGENTS.md rule 9).

`research/decisions/` on the sibling side is **empty** — their durable decisions live in
`docs/adr/` (4 ADRs, each ending in reversal conditions) and the addendum/freeze discipline of
`docs/RESEARCH_SYNTHESIS.md`.

## Already-landed: do not re-file these three

| Sibling mechanism | Landed here as |
|---|---|
| Append-only machine-readable correction beside a frozen result (`evaluation/cross-engine/results/FINAL-CORRECTIONS.json`) | `eval/withdrawn.json` + `docstat.py --withdrawn` gated into `--sweep`; first live catch FINDINGS #119 (task 55) |
| Hard gates before scoring (`docs/RESEARCH_SYNTHESIS.md` Method) | Tier 1 is a GATE, `overall = tier2`; empty tier is `usable=false`, never a pass (task 29; `eval/judge/RUBRIC.md`, `DECISIONS.md`) |
| Every ADR ends with reversal conditions (`docs/adr/0001`–`0004`) | `DECISIONS.md` "Reversal conditions" section, adopted 2026-08-23, narrow scope, each row names its producer |

## ALREADY-HERE — the sibling mechanism, and this repo's equivalent

| # | Sibling mechanism (path) | Here |
|---|---|---|
| 1 | Layered evidence ladder, 10 rungs from lint to clean-room reproduction (`docs/adr/0003`) | Tier 1 programmatic criteria + play-bot + judge, `eval/judge/AGENTS.md` tier table; `judge/static.py` |
| 2 | Fail-closed scoring: missing/invalid/tampered evidence scores zero, never renormalised (`evaluation/README.md`) | `judge/static.py`: "every check is fail-closed: a command that does not run scores FALSE, never skipped"; rule 7; task 29's `usable=false` |
| 3 | Media verified by decode/magic bytes, not extension or claimed MIME (`evaluation/README.md`) | `eval/AGENTS.md`: "the audio criteria decode every clip rather than trusting its extension"; `judge/png.py` |
| 4 | The agent is never an allowed evidence producer; "status is an observation, never a self-awarded study score" (`STUDY_AGENT.md`) | Grader re-runs its own commands (`static.py`); the agent's closing message is a **locator, not a classifier** (`tools/disclosure.py`, rule 11) and scores nothing |
| 5 | Submission isolated from hidden checks; agent reads only workspace + task (`FORMAL_CELL_PROMPT.md`) | `verify_blind.py` + canary GUID in `RUBRIC.md` — blinding *tested*, not asserted; the building agent never sees any tier |
| 6 | Reviewer blind to engine identity, montage labels randomised, reviewers forbidden to read each other (`cross-engine/DESIGN.md`, `reviews/README.md`) | `judge/anonymise.py` neutralised packs; judge graded independently, one submission per session (`judge.py`); stack identity never unblinded at any phase — stronger, not weaker |
| 7 | Frozen baseline tree + source delta per submission; trees reconstruct from baseline + deltas (`baselines/`, `reconstruct_submission.py`) | "Each trial gets a fresh template copy with a baseline commit, so `git diff HEAD` isolates exactly what the agent did" (`eval/AGENTS.md`); archives not patches, verified by opening |
| 8 | Verifying the unchanged starter cannot satisfy a task criterion (`evaluation-methodology.md`) | The negative control: "held-out tests fail on the pristine starter" (`eval/AGENTS.md` controls table); `starter_gate_control.py` |
| 9 | Template parity contract + admission gate + shakedown sessions excluded from scores (`TEMPLATE_PARITY.md`) | `judge/starter_parity.py` with three-valued test axis and `UNMEASURABLE` failing the tool (#108); `parity_selftest.py`; parity adjudications re-read from the live guides |
| 10 | Automated failures cannot be overridden by review; AND-merge (`cross-engine/results/FINAL.md`) | Tier 1 gate: a gate failure neither deducts nor excludes, it names failing ids; `build.compiles` / `probe.responds` blocking marks `score_is_independent=false` (task 29) |
| 11 | Distinct requested scenarios must produce distinct render hashes; two equal replay hashes required (`TEMPLATE_PARITY.md`) | `static.py`: non-empty frames, consecutive frames differ; play-bots drive thousands of ticks and assert behaviour, so a rendered still cannot pass what a game must do |
| 12 | Reviewer reliability measured: 19/20 agreement, κ ≈ 0.643 (`reports/FINAL.md`) | Not κ — one judge model, so no second rater exists. Instead: both-criteria-orders conjunction with `instability` reported (`judge.py`), test-retest spread of six judgings (FINDINGS #21), within-cell trial-vs-trial verdict floor (`judge/paired_verdicts.py`) |
| 13 | Failed reviewer attempts recorded as data with session ids and `used_for_scoring: false` (`reviews/round2-attempts.json`) | `terminal_reason` on every trial, partitioned before any aggregate (`tools/census.py`); rule 7 — every reason not to count a failure is a channel a bug can widen |
| 14 | Preregistration: hypotheses, conditions, outcomes, stopping rule frozen before outcomes (`cross-engine/preregistration.json`) | `JUDGING.md` "PRE-REGISTERED, 2026-08-17"; IMPROVEMENTS iterations pre-register hypothesis + falsifier; "Changing what the judge is told … needs a pre-registration" (`eval/AGENTS.md`) |
| 15 | Protocol-freeze chronology disclosed when the ideal order was not achieved ("the immutable chronology does not support the literal DESIGN.md statement", `cross-engine/results/FINAL.md`) | The same discipline, practised: two-wave builds reconstructed by hand (#93, #120), the comparability-break register in `eval/RUNS.md` (the register is its own producer — read it there, not here), regime paperwork on any grading change |
| 16 | Instruction revisions only when tied to observed repeated failures, never retroactively rescored (`evaluation-methodology.md`, `reports/INSTRUCTION_REVISIONS.md`) | The refine loop: both `IMPROVEMENTS.md` files are hypothesis → change → measurement, with re-scoring events requiring their own ticket and a `tier2_census.py` before/after; "do not re-grade stored submissions to make a new scheme look better" (task 29) |
| 17 | Weighted rubric with pass threshold and critical-criterion cap of 0.49 (`evaluation/tasks/pilot/falling-block.json`) | Superseded here by the gate (row 10) — a binary gate is strictly stronger than a cap; and every weight is swept: `judge/weight_sensitivity.py`, rule 16 (inert parameter → go measure what the term has ever measured) |
| 18 | Extra records above `max_records` invalidate the criterion — no cherry-picking (`evaluation/README.md`) | Structural here: one grading per (trial, criterion, order); re-gradings append and are superseded **wholesale** (`tier1_census.py` counts them); nothing selects best-of |
| 19 | Coordinator tool hashes pinned (`coordinator-tools.json`); harness digest recorded | `tools/agent_harness_control.py` pins the claude arm's argv byte for byte; capture policy defined once in `runner.py`, imported, asserted identical (`runner_capture_selftest.py`) |
| 20 | Byte-frozen prior document versions + manifest vs manifest-current (`FINAL-GODOT-STUDY-FROZEN.md`, `docs/RESEARCH_SYNTHESIS-GODOT-STUDY-FROZEN.md`) | git history + the recorded live/archive partition (`DECISIONS.md`, `ARCHIVE_PATHS` in `docstat.py`, asserted equal by `withdrawn_control.py`); append-only manifests keep the first record and stamp the sibling (`tools/manifest.py`) |

## ADOPTED-CANDIDATE — filed

**Trial failure-cause labels, with the infrastructure-vs-agent separation folded in — ticket
220.** The sibling applies a closed failure taxonomy per output (`setup/version`, `oracle-weakened`,
`claim-not-reproduced`, `input-not-real`, … 16 labels, `research/raw/evaluation-methodology.md`)
and aggregates it in its final tables ("What actually failed", `cross-engine/results/FINAL.md`),
with one rule doing real work: *a preflight defect is recorded separately from an admitted-agent
failure, and infrastructure logs distinguish the two* (`cross-engine/DESIGN.md`). This repo keeps
re-deriving "why did these trials fail" by hand, one incident at a time — #45 `$TMPDIR`, #46 a bot
that stood still, #49 a daemon gating `execve`, #37 stalled-vs-compiling — and `terminal_reason`
partitions only how a session ended, not whose fault the outcome was. Ticket 220 asks for the
closed vocabulary, a hand labelling of the stored whole-game corpus, a cross-tabulating producer,
and **the accept/reject measurement in the ticket**: accept if a label group surfaces a pattern
not already recorded in FINDINGS/DECISIONS; reject and withdraw the vocabulary if every group
maps one-to-one onto what producers already answer. It is the only sibling mechanism this
repository lacks both the vocabulary and the producer for; adoption is decided by the
measurement ticket 220 defines, and until that runs, the status is pending. Everything else was
already built here, and the rest is rejected below.

## REJECTED — and the reason each does not transfer

| Sibling mechanism | Why it does not transfer |
|---|---|
| HMAC evidence sealing, hash-chained status events, symlink prohibition, admission tokens, byte-sorted release index (`evaluation/integrity.py`, `cross-engine-v3/formal-ops/RUNBOOK.md`) | The trust boundary it defends — an untrusted party with filesystem access between submission and score — does not exist here: one operator, one account, submissions archived by the harness, tamper-evidence from the git baseline commit plus post-hoc checks (`stop_hook.leaked_into_tree`). The sibling's own report concedes the limit: HMAC is "fail-closed coordinator custody but … not a publicly verifiable signature", and directory separation "is not a sandbox when all processes share a user" — the same user this repo runs under. Every recorded confound here came from the machine (#49), never from tampering |
| Commit-reveal commitment for reviewer blinding (`review-randomization-commitment.json` / `-reveal.json`) | Protects a mapping chosen while outcomes are in flight. Stack assignment here is static matrix configuration, not an adaptive choice; the blinding property is tested directly (canary) rather than promised by a hash |
| Clean-room / Docker reproduction lane, multi-platform export claims (`template/` presets, Docker verify) | The sibling needs shipping claims for a distributed template. This repo measures agent capability on one recorded host, and the machine's state is itself a measured variable (rule 10, #49) — a container lane would change the object rather than control it |
| Human playtest ratings as scored evidence (`human_scale`, 2–3 playthroughs in their comprehensive rubrics) | Never exercised even in the sibling's own pilots; this repo's subjective layer is deliberately a 0.00-weight diagnostic (FINDINGS #21, `RUBRIC.md`) — a human-in-the-loop tier is a budget decision no measurement here has motivated |
| Replicated expansion apparatus: 8 tasks × 3 repetitions, release-candidate engineering (`evaluation/cross-engine-v3/`) | Built, audited, **never admitted** — no formal seed drawn, terminal NO-GO, "do not continue, freeze, or publish" (`cross-engine-v3/README.md`). Their own conclusion is the transferable part, and it is already this repo's practice: the retired spec-change suite stays as history, and the n=2 design's ~0.015 resolution floor plus its re-open condition are recorded (`DECISIONS.md`) |
| Metric criteria (`zero_at` → `full_at` linear maps) and per-criterion confidence values (`evaluation/README.md`, review JSON) | Binary-only is a recorded design position ("binary criteria are calibratable; 1–5 scales are not", `RUBRIC.md`); where a magnitude matters here it is measured as a field, not scored (`capability.py`, `wallclock.py`). Confidence-per-decision is replaced by the both-orders conjunction with reported instability |
| Source manifest: every cited URL with access date and SHA-256 of local copies (`research/source-manifest.json`, 301 URLs) | Scale: this repo's briefs are an order of magnitude smaller and the claim standard is per-claim and enforced by review (`research/AGENTS.md`: date every claim, source every claim, label unverified). No incident here has been caused by an unfindable source; a manifest nobody queries is dead weight |
| Inter-rater κ between two simultaneous independent judges of one output | Unavailable in-harness, and the limitation is already recorded where the decision lives: the judge is a different model from the builder but "a genuinely independent judge would be a different lab's model, and this harness cannot provide one" (`judge.py` docstring). Row 12 lists the three reliability measurements that exist instead |

**Also noted, not a mechanism:** the sibling's most instructive failure is a caution that
validates this repo's design. Three of its 16 matched cells failed — engines "implementing
credible independent loopback peers" — because the frozen collector required a numeric
`observations.independent_processes >= 2` at one key and the submissions supplied a different
field name or a Boolean (`cross-engine/results/FINAL.md`, "What actually failed"). A grader that
requires a *reported observation* in a specific shape will fail correct work on field-name
mismatches. The play-bot tier accepts no reported observation at all — it drives the game and
reads what happens — which is why this failure shape is structurally absent here. INTERPRETATION,
not measured: no experiment was run.

## What the sibling has that this repo deliberately does not

Where the absence is a **decision**, it is recorded as one; the point of this section is that a
reader of the sibling should not mistake these for oversights.

1. **Cryptographic custody of evidence.** Rejected above; the decision behind it is the
   single-operator trust model, and the recorded evidence that our confounds are machine-shaped,
   not adversary-shaped (#49), is what makes that model defensible rather than merely cheaper.
2. **Multi-platform and clean-room lanes.** The sibling's product ships; ours measures. Its own
   report models the honesty required either way — a portability table separating "what is
   evidenced" from "what is not evidenced" (`reports/FINAL.md`).
3. **A scored subjective tier.** Their review tier carries real weight (launch 20 / core 35 /
   loop 20 / render 15 / workflow 10); ours carries 0.00 and is diagnostic. Decided on
   measurement (FINDINGS #21; task 29), not on scepticism about models.
4. **Repair rounds and repairability estimates.** Their round two measures repair-with-review;
   ours measures fresh capability per trial and refuses to re-grade stored work to flatter a new
   scheme (task 29). Mixing the two objects is exactly the comparability break their report warns
   about ("must not be reported as fresh baseline pass@1").
5. **A replicated, release-engineered expansion.** They built the 8×3 apparatus and then
   published it as terminal NO-GO rather than running it underpriced. This repo's equivalent
   decision is n=2 with a recorded floor and a re-open condition.
6. **A networking task.** Their four tasks include authoritative networking; our four games have
   none. That is a task-set scope decision belonging to `suites/wholegame_prompts.py` and the
   `add-game` loop — a multiplayer task would enter on this repo's own evidence about what the
   game set fails to discriminate, not because the sibling has one.
7. **A cost-of-custody budget for compliance machinery.** Their harness carries admission
   audits, security audits, release indices and review packets (`cross-engine-v3/audits/`,
   `godot-defold-confirmation-v1/formal/`). The sibling spent that surface on a study that never
   admitted a formal session. This repo's gate register (`.github/workflows/README.md`) states
   the same trade in the opposite direction: every gate must earn its duty cycle, and a gate
   excluded with a reason is fine.

## What not to conclude

- **Different does not mean better.** Every row above was decided against this repo's measurement
  loop, not against the sibling's quality — which is high. Their fail-closed custody model is the
  right design for a threat model they actually have; this repo's refusal to build one is right
  for the one it actually has.
- **The sibling's headline numbers are not comparable with ours.** Different judge (fresh review
  sessions with a weighted rubric vs deterministic bots + a 0.00-weight diagnostic), different
  task set, different scale (16 and 4 cells vs the stored matrix), and their own report labels the
  cross-engine result "descriptive only". No figure from this read may be quoted beside a figure
  from `eval/RUNS.md`.
- **Nothing adopted here is adopted directly from the note.** The one candidate went through the
  queue as ticket 220 with its own accept/reject measurement; any change this comparison
  motivates to starters, criteria or prompts goes through the refine loop with a measurement
  before and after. That regime caution is from the ticket, and it stands.

## Scope of the comparison

Sibling side, inside line-by-line scope: `README.md`, `NOTICE.md`, `study-build.json` (shape;
`ruff.toml` is a lint config, and `tools/lint.py` covers that question here); `docs/` (both
syntheses, all 4 ADRs); the `evaluation/` README, all 6 harness modules' function inventories,
the 7 schema files, one pilot task spec whole, `reports/FINAL.md`,
`reports/FINAL-GODOT-STUDY-FROZEN.md` (head), `INSTRUCTION_REVISIONS.md`, `reviews/` (README,
round2-attempts, one adjudication record), `cross-engine/DESIGN.md`, `TEMPLATE_PARITY.md`,
`preregistration.json` (structure), `STUDY_AGENT.md`, `FORMAL_CELL_PROMPT.md`,
`results/FINAL.md`, the commitment/reveal pair; `cross-engine-v3/README.md`,
`formal-ops/RUNBOOK.md`, and the audits and drafts by name; `research/SOURCES.md`,
`raw/evaluation-methodology.md` whole, and `raw/`, `sources/`, `spikes/` by inventory;
`research/decisions/` is empty; `scripts/evaluation/*.py` at docstring level.

Sibling side, outside line-by-line scope: data dumps under `evaluation/runs/`, the
`baselines/*.json` bodies, `.formal-run-*`, cache images, and Unity `Library/` trees — stored
results and caches, not mechanisms, and outside every conclusion above.

This repository side: `AGENTS.md`, `eval/AGENTS.md`,
`eval/judge/AGENTS.md`, `RUBRIC.md`, `DECISIONS.md` (reversal-conditions and rubric sections),
`tasks/29`, `tasks/55`, `research/11`, and the judge modules named in the pointers.
