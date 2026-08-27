---
id: 160
title: fire.rate_limited counts BULLETS and asks about SHOTS, and prints the right number beside the wrong verdict
status: in_testing
priority: 2
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, tasks/155
done_when: The criterion counts fire events rather than bullet ids, or states in bot_arena.py why a bullet count is the right proxy and what a spread weapon should score; the ref_arena spread entry in PENDING_VARIANTS comes back with an empty failing set and is promoted into VARIANTS; bot_mutants.py exits 0; and the stored g3_arena verdicts are re-derived with eval/judge/tier2_census.py against the main checkout's eval/runs with before and after counts recorded here.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/47
established_by: 'bot_mutants exit 0 at the merged head cc1ca3b: 44 criteria pinned in both directions, 11 variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet, against a before of 43/10/1 with the spread pending "still red, as declared". Both new directions measured: the spread variant reads 30 shooting ticks out of 120 (30, 30) and passes; a second mutant with no interval and fire on the rising edge reads 120 (1, 120) and fails, which is the control proving an event-only count would have been fail-open. tier2_census byte-identical before and after; 12 of 16 stored g3_arena rows unchanged by construction, 0 undecidable, 4 probe failures. docstat --sweep, --findings, --withdrawn, linkcheck and tasks.py check all exit 0. PR #47, 3 review rounds, last clean.'
---

The criterion's own question is: is there a minimum interval between shots rather than one bullet per tick. bot_arena._firing_in scores it as 0 less than n_x and n_x at most 80, where n_x is the number of distinct BULLET ids created over 120 ticks of held fire. A weapon that fires a spread puts several bullets in the world per shot, which is an ordinary design for a game the g3 prompt asks to make loud, fast and readable at a glance. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a ref_arena fixture firing a three-round spread on a 4-tick cooldown fails with 90 bullets from 120 ticks of held fire (30 fire events). 30 shots in 120 ticks IS a rate limit, and the criterion prints that number in its own evidence string beside a verdict computed from the other one.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — third in line; 158 lands before you, 166 after

`158`, `160` and `166` serialise on `eval/judge/bot_mutants.py`. Order settled as **158, then 160,
then 166**; the derivation is in `tasks/166`. Rebase on `main` after 158 merges — your conflict
with it will be in the mutant registry, where both tickets add entries and both should be kept.

**166 does not reach you.** It says end-detection is read inconsistently (flag-or-event to locate
the end, flag alone to score it). `fire.rate_limited` is built in the block at `bot_arena.py` line
905 and counts over `for _ in range(ticks)` — a fixed window with no `game_over` break — so which
end signal wins cannot move your count. The loops that DO break on the flag are the wave/kills
collection at lines 465-472, which is not yours.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 158 has MERGED; branch from main and there is no rebase to do

The note above told you to rebase on `main` after 158 lands and expect a conflict in the mutant
registry. 158 merged as of now, so you branch from a `main` that already contains it and the
conflict does not arise. Ignore that paragraph.

**What 158 established that bears on your work**, because it is the same file and the same suite:

- `eval/judge/bot_mutants.py` is at **43 criteria pinned in both directions, 10 variants, 1
  pending, 3 session-lock controls, 70 criteria with a recorded hazard, 0 unmet**, exit 0. That is
  the baseline your change moves; re-run it and state the new figures rather than assuming only
  your own rows moved.
- 158's ticket said two opening budgets and there were **four** — `_play_for_a_clear` and
  `_gameover_check` each open a *fresh* `ProbeSession`, so a title card gates them from their own
  tick 0. **`bot_arena` opens 9 fresh sessions and nobody has measured whether they have the same
  defect**; that is `tasks/173`, filed rather than assumed, and it is NOT yours. If you trip over
  it while working `fire.rate_limited`, record what you saw in `tasks/173` and carry on.
- 158 added mutants for two criteria that had none, on the reasoning that **widening a limit can
  only make a criterion easier to pass**, so a criterion that had become incapable of failing would
  read as a clean run. If your repair changes what `fire.rate_limited` accepts, check it still has
  a mutant that can drive it red — `bot_mutants.py --hazards` is the producer.

Your own ticket's trap is stated in its body: the criterion counts BULLETS and asks about SHOTS,
and prints the right number beside the wrong verdict. A repair that changes the printed number
without changing what is counted leaves the verdict wrong and the evidence newly convincing.

## note 2026-08-27

## The ticket's first suggested repair is FAIL-OPEN, and that is the thing not to re-derive

`done_when` offered "the criterion counts fire events rather than bullet ids". Taken
literally that replaces a false negative with a false positive. `fire.rate_limited`
fails on a HIGH count, so whichever signal reads *lower* always excuses — and the `fire`
event can legitimately read low: a game that fires on the rising edge of a held control
emits one event for the whole 120-tick phase. `edge-vs-level` is already a recorded
`SHAPES` family, and it is `fire.spawns_bullets`'s own hazard.

So `ArenaBot._shot_ticks` counts how many of the 120 ticks were SHOOTING ticks by **two**
independent signals and the criterion takes the **larger**:

- a `fire` event on the tick — the g3 prompt defines it as *the player fired a shot this
  tick*;
- a bullet id in the snapshot that was not in it before.

Each can under-report and neither over-reports a shot the game did not take. `max` is
therefore fail-closed in the direction that matters, and it needs no "did any event
occur" branch: `max(0, spawn_ticks) == spawn_ticks` handles a game that emits no `fire`
event at all.

A second mutant, `a bullet every tick, with fire reported only on the rising edge`,
is the negative control for that choice and reads:

    120 shooting ticks out of 120 ticks of held fire (1 carried a fire event,
    120 put a new bullet id in the world), producing 120 bullets

An event-only criterion would have called that gun rate-limited on 1 shot in 120 ticks.

**Why not the union of the two tick sets, which was the other candidate.** A game whose
spawn reaches the snapshot one tick after the event that caused it has two disjoint sets,
and the union double-counts: a legal 60-shot weapon would read 120 and go red. `max`
does not. Both are equally fail-closed against the every-tick failure; `max` is the one
that survives a deferred spawn.

**What `max` does NOT answer**, and it is now the recorded hazard for the criterion: a
game emitting `fire` on every held tick regardless of its own cooldown reads 120 and goes
red. That game contradicts the event's stated meaning, so it is a contract violation
rather than a correct-but-unusual game — but it is the shape to look at first if this
criterion ever produces a surprising red.

## Measurements

Before, unchanged tree, `python3 eval/judge/bot_mutants.py`, exit 0:

    43 criteria pinned in both directions, 10 variants, 1 pending, 3 session-lock
    controls, 70 criteria with a recorded hazard, 0 expectation(s) unmet
    pending  a faster three-round spread weapon  ref_arena  still red, as declared (tasks/160)

Driving the spread fixture directly, before:

    fire.rate_limited  passed=False  scored=True
    90 bullets from 120 ticks of held fire (30 fire events)

After:

    44 criteria pinned in both directions, 11 variants, 0 pending, 3 session-lock
    controls, 70 criteria with a recorded hazard, 0 expectation(s) unmet
    variant  a faster three-round spread weapon  fire.rate_limited  ok

    spread   30 shooting ticks out of 120 ticks of held fire (30 carried a fire event,
             30 put a new bullet id in the world), producing 90 bullets
    healthy  12 shooting ticks ... (12, 12), producing 12 bullets           PASS
    norate   120 shooting ticks ... (120, 120), producing 120 bullets       FAIL
    edge     120 shooting ticks ... (1, 120), producing 120 bullets         FAIL

The new mutant flipped `fire.rate_limited` and nothing else — the suite prints a
`note: mutant ... also flipped [...]` line when a mutant disturbs a sibling, and it
printed none for this one.

## Stored verdicts: 0 move, and it is decidable from disk

`python3 eval/judge/tier2_census.py --runs-root <main checkout>/eval/runs` is
**byte-identical before and after** (`diff` exit 0), which it must be: the census reads
stored records and drives nothing. `fire.rate_limited` reads `scored on 16, failed 4,
unscored on 0` in both.

The substantive question — would a re-grade move any of them — is answerable from the
stored evidence string, which carries both numbers. `N bullets from 120 ticks of held
fire (M fire events)`. Where `N == M`, each shot produced exactly one bullet, so
`spawn_ticks <= N == M` and `max(M, spawn_ticks) == N`: the old and new verdicts are the
same expression. Over the whole stored tree:

    12 verdicts unchanged by construction, 0 undecidable from disk, 4 rows whose
    evidence is a probe failure rather than a measurement

The 4 are `wg-arena3d` Rust t0/t1 (probe exited 101 in the MAIN session) and `wg-matrix`
Unity t0/t1 (probe exited 134 in the FIRING session). Each fails its whole session, not
this criterion selectively — the census's per-trial lines list 11 of 15 failing together
for the Unity pair.

**No stored `g3_arena` submission fires a spread.** All 12 measurable ones put exactly
one bullet per shot, at 12–20 shots in 120 ticks. The variant is a constructed correct
game, not an observed one, and the ticket said so.

## What else moved

- `PENDING_VARIANTS` is now **empty**, and `--selftest` no longer takes its subject from
  `PENDING_VARIANTS[0]` — it builds a synthetic `Pending`. Without that, emptying the
  list would have stopped exercising `adjudicate_pending` **silently, at exit 0**, which
  is the shape `bot_mutants.py` exists to prevent.
- `SPREAD_WEAPON` moved above `VARIANTS` (a list literal cannot reference a name defined
  below it), and the two paragraphs of the pending header that described the *subjects*
  moved with them to `VARIANTS`, where those subjects now live.
- `DECISIONS.md`, *A known play-bot false negative is declared as a red subject*: live
  pending count 1 -> 0, and **the first re-open condition that section named has fired** —
  "every pending entry repaired and promoted". Recorded as kept: an empty list costs
  nothing to carry (the loop iterates it), `tasks/170` names adding one as one of its two
  outcomes, and what it buys is the alternative to a silent `Variant.tolerates`.
- `README.md`: the `bot_mutants` figures, which carry the producer command beside them.
- `bot_tetris3d.py`: a comment still cited the two tetris card subjects as living in
  `PENDING_VARIANTS`; `tasks/158` promoted them into `VARIANTS`.

## Not done, deliberately

- The threshold stays at **80 of 120**. Nothing in the ticket asks for it and moving it
  is a separate re-scoring event. At 80 a gun firing every other tick (60) passes; the
  `NO_RATE_LIMIT` mutant (120) fails.
- `fire.spawns_bullets` still counts bullet ids, correctly: it asks whether holding fire
  creates bullets that travel, and a bullet is the right unit for that question.
- `tasks/173` (do `bot_arena`'s 9 fresh sessions have `tasks/158`'s opening-budget
  defect?) was not touched. Nothing in this work tripped over it: `_firing_in` runs
  inside `_firing`'s session, which opens with the standard await and then steps a fixed
  `range(120)` with no `game_over` break, so an opening card could shorten what it
  measures but nothing here observed one.

## NEEDS A FINDING NUMBER — for the orchestrator to allocate

**Claim.** A criterion whose verdict fails on a HIGH count cannot safely read the smaller
of two signals for that count, and the obvious repair for `fire.rate_limited` — counting
the contracted `fire` event instead of bullet ids — is exactly that. It replaces a
measured false negative (90 bullets scored as 90 shots) with an unmeasured false
positive.

**Measurement.** `ref_arena` with `FIRE_INTERVAL` removed and `fire` emitted only on the
rising edge of the held control: `1 carried a fire event, 120 put a new bullet id in the
world`. Event-only verdict: PASS on a gun with no interval at all. Shipped verdict
(`max`): FAIL.

**Control, both directions.** The healthy reference reads `(12, 12)` and passes; the
plain `NO_RATE_LIMIT` mutant reads `(120, 120)` and fails; the spread variant reads
`(30, 30)` and passes. `python3 eval/judge/bot_mutants.py` exit 0, both mutants and the
variant in the same run.

**Why it generalises.** The ticket wrote the repair as *which field to count* — an
enumeration of the instance in front of it. The property is the direction the threshold
fails in. `AGENTS.md`'s rule audit already says a trigger written as an instance has to
be re-derived by every reader who meets a different one; this is that, inside a
`done_when`.

## note 2026-08-27

## Review loop and CI, round by round

3 rounds against PR #47, `eval/tools/pr_review_state.py --pr 47 --branch
task-160-fire-rate-limited-counts-shots --expect-head <sha> --wait`:

| round | head | verdict | comments |
|---|---|---|---|
| 1 | `6f5cb16` | `LANDED_REVIEW` at 220s | 3, all Minor, all acted on |
| 2 | `84c8507` | `LANDED_REVIEW` at 252s | 1 new, acted on; the other 3 threads acknowledged and resolved |
| 3 | `cc1ca3b` | `LANDED_COMMENT` at 158s | none - clean round |

All 4 comments were on documents and all 4 were right. Three were the readability class
`.coderabbit.yaml` asks for on purpose: prose narrating what changed rather than stating the
rule, a count spelled in words, and a tense. The fourth found a real internal contradiction:
`DECISIONS.md` said *"a criterion change moves stored verdicts across 68 graded submissions"*
while the very next paragraph said *"A closed entry may re-score 0 stored verdicts"* - and this
ticket is another instance of the second. It now reads *"a criterion change is a re-scoring event
over 68 graded submissions, carrying its own `tier2_census.py` before-and-after - whether or not
any verdict turns out to move."*

CI at `cc1ca3b`: `gates` PASS (1m54s), `CodeRabbit` PASS, `controls` still in flight when this
was handed back, with its `judge/bot_mutants` and `judge/aim_contract_control` steps already
green and only unrelated later steps outstanding.
