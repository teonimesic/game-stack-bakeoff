# eval/judge/ — grading a submission

**`JUDGING.md` is the design document for the subjective layer** — what each judge looks at, the
layer matrix, the validation gates, and what the 24-submission matrix showed about which criteria
carry information. Read it before adding or changing a judge.

Three tiers. The building agent must see none of them.

| Tier | Weight | Implemented in |
|---|---|---|
| **Programmatic** — builds, gate green, lints, tests, frames render and animate, perf probe, **audio** | **GATE — not scored** | `checks.py`, `static.py`, `probe.py`, `png.py`, `audio.py` |
| **Play-bot** — a scripted bot drives thousands of ticks and asserts the game actually plays | **1.00** | `bot_pong.py`, `bot_tetris3d.py`, `bot_arena.py` |
| **LLM judge** — one specialist per aspect, each ranking a whole eight-submission field | **0.00** | `aspects.py`, `field.py`, `field_sweep.py`, `adjudicate.py`, `anonymise.py`, `RUBRIC.md` |

`evaluate.py` runs all three. `regrade_wholegame.py` recomputes scores from stored tier files.

**Tier 1 gates; it does not score.** `overall = tier2`, and a tier-1 failure is reported as
`gate: FAIL` with the failing criterion ids rather than deducted — the derivation, the two
sweeps behind it and what would re-open it are in `RUBRIC.md`. Two consequences you will meet
before you meet the rubric: a record written before 2026-08-23 has no `gate` and no
`scoring_regime` and its `overall` is on the old 0.31/0.69 scale, so **never average across the
boundary**; and `regrade_wholegame.py` refuses to rewrite a pre-gate record without
`--accept-regime-change`, because converting one silently would leave a run directory half in
each regime with nothing on disk saying which.

**The audio criteria need `ffmpeg` and `ffprobe` on the grading machine.** Without them every
audio criterion fails with that as the recorded reason — fail-closed, never skipped, because
`total=0 passed=0` is indistinguishable from correct failure.

**`audio.*` applies only to a task that asked for sound.** `evaluate(..., audio=False)` and
`wholegame.py evaluate --no-audio` exist for re-scoring the runs that predate it; applying the
criteria retroactively would measure the task change rather than the work.

**Every audio criterion has a mutant.** `audio_selftest.py` runs 37 expectations: five criteria
plus `audio.triggered` against a healthy fixture, then against nine mutants each of which must turn
one of them red. Run it before believing an audio score. A criterion that cannot fail is worse than
absent, because it looks like success.

**`capability.py` is captured, not scored, and it is measured from OUTSIDE the submission.** Nine
fields — capture geometry, frame count, the wall/CPU/peak-RSS cost of `just film`, and the headless
probe's throughput and start-up — same names, same units, all four arms. Nothing in the submission
is ever asked to report a number about itself, because **a field the subject reports is a field
that can go missing in a stack-correlated way** (#62, #72, #77); a harness-side mechanism cannot.
`no_stack_correlated_gap()` enforces that and `capability_selftest.py` carries its mutant *and* its
variant. **Do not add a frametime or fps field** — the TS arm films on SwiftShader while the other
three film on the GPU, so it would rank the backend; `DECLINED` in that module says what would have
to change first. Adding any of this to the score is a regime boundary and needs its own task.

## What a stored command record holds: two streams, sampled apart

Every command tier 1 runs — `just check`, `verify`, `lint`, `test`, `film` — is stored by
`static.Cmd.to_dict` with **`stdout` and `stderr` as separate fields**, each sampled on its own
budget: the first `STREAM_HEAD_CHARS` characters and the last `STREAM_TAIL_CHARS`, the middle
replaced by a marker naming how many characters and lines went, and the full length of each stream
recorded beside it as `stdout_chars` / `stderr_chars`. The harness's own words — a timeout, a
binary that could not be spawned — go in `note`, never into a stream the command did not write.

**There is exactly one copy of that policy and it is not here.** `STREAM_HEAD_CHARS`,
`STREAM_TAIL_CHARS`, `_sample_stream`, `capture_fields`, `stored_stdout` and `stored_output` are
defined in **`runner.py`** and imported by this module, because the spec-change harness stores
command output too and had the identical defect (#114). Two truncation policies in one repository
is how #100 recurred; `runner_capture_selftest.py` asserts each of those names is still defined in
`runner.py` rather than re-implemented here.

It used to be one `tail` field holding the last 4000 characters of `stdout + stderr`. **A
truncation policy is a sampling policy**, and that one sampled *whichever stream the tool happened
to write second*: 15 of 16 green Rust `verify` records kept no trace of the recipe's own
`✅ verify passed`, because `cargo-nextest` fills stderr (#100). **Raising a cap is not a fix for
that class of defect** — it moves the boundary and leaves in place the rule that stdout is
sacrificed first, still correlated with a stack by a property nobody chose.

Reading stored records: `static.stored_stdout()` returns **None** for anything written before the
repair, because a line missing from a merged buffer is not evidence the command never printed it —
those records are unmeasurable, not empty. `static.stored_output()` reads either shape. In memory
`Cmd.tail` is unchanged and still means stdout-then-stderr, because the test-count and coverage
parsers read it; only the stored shape moved. Stored records cannot be repaired — the discarded
stdout was never written down — so the corpus is mixed and any sweep over it must partition on
which shape it is reading.

`judge/capture_selftest.py` pins both directions (a flood on either stream keeps the other) and
carries the mutant that proves those checks can fail. `runner_capture_selftest.py` does the same
through the other harness's entry point. Both must stay green.

## The judge is diagnostic only

It contributes **zero** to `overall` — not a token weight. Two independent reasons, either
sufficient:

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest adjacent gap of
   0.0622 on tiers 1+2 alone. Holds regardless of noise.
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability up to 0.462
   on a contested submission, against 0.000 on an uncontested one. Holds regardless of weight.

Its per-criterion verdicts **are** reported and are genuinely useful — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.
Anywhere it appears in a report, label it as diagnostic so no reader can mistake it for something
that fed the ranking.

## Validating the judge

**Verdict stability is a property of the artifact, not of the rubric.** Criteria agree when the
answer is obvious and diverge when it is borderline — which is exactly when you need them.

Consequences, all learned the expensive way:

- **Validating on clear-cut fixtures systematically overstates reliability.** A submission scoring
  13/13 unanimously proves nothing about a contested criterion. So does one scoring 0/13 — that is
  a ceiling at the floor.
- **Validate on borderline artifacts**, and report per-artifact stability rather than a global
  figure. A single instability number for "the judge" is not meaningful.
- `instability` measures forward-vs-reverse disagreement **within** a run. Run-to-run variance on
  identical input is a separate and equally large effect. Report both.
- **When a binary criterion flips run to run, read the reasons before blaming the model.** Several
  near-identical reasons with different verdicts is the signature of an unstated threshold. Rewrite
  the question — though note that rewriting the three worst criteria here did not fix them.
- A criterion every run answers identically **because the question never arose** has not been
  tested. Check that a criterion is exercised, not just that it is stable.

## Blinding

`verify_blind.py` scans for the rubric's canary GUID, its reachability from every ancestor
directory, and every criterion id the rubric defines.

- **Run it after *any* starter edit**, not just before a run. A criterion id once reached the Unity
  starter through a comment written while documenting an unrelated floating-point finding — not
  through the prompt, template or `AGENTS.md`, which are the three places the design watched.
- Run it **unpiped**. A `verify_blind.py | tail` "pass" is `tail`'s exit status.
- **Point it at a copy of the starter OUTSIDE this repository**, laid out the way a trial tree is.
  Check 2 asks whether the rubric is reachable from an ancestor, and `eval/starters/<stack>` has
  `eval/judge/RUBRIC.md` up its own path — so run in place it is red for all four stacks, on a
  condition that says nothing about the edit (measured 2026-08-23, task 67). That verdict is
  *correct about the path it was given* and useless about the question, which is rule 12: the
  address is an input to the check. Copy the four starters to a directory outside the repo and
  pass those. The error text says "see `--work-root`" — that flag is `wholegame.py`'s, not this
  tool's, and this tool takes bare paths.
- Never fix a leak mid-run. Changing a starter partway through gives later trials a different
  starter than earlier ones — a real within-run inconsistency traded for a usually-minor leak.

## Anonymisation

`anonymise.py` strips identifying structure before judging. Three things it has got wrong before:

- **Check `CODE_EXT` covers the stack's extensions.** A missing extension produced an empty file
  pack that the judge scored confidently at 0.08.
- **A criterion cannot ask about something anonymisation destroys.** `code.navigable` asked about
  file layout, which is exactly what the anonymiser removes; every run argued with the
  anonymisation instead of answering.
- **A pack is a NUMBERING, not a set of files.** Labels are `bucket/NN.ext` counted within the
  bucket, so any change to the picked set — a starter edit, an exclusion, a new extension, a
  directory added to `SKIP_DIRS` — shifts the numbering and would strand the previous pass's
  files under labels the new manifest does not list. `build_pack` clears its destination for that
  reason; `wg-g4c` accumulated 23 stale files in 222 across nine passes before it did (#95).

**Verify a stored pack by opening it, not by reading what `anonymise` said about its input.**

```
python3 judge/field.py packcheck --run runs/<run>          # unpiped: exit 1 means not clean
```

`pack_completeness` reads `files_dropped_for_length`, which #69 made 0 by construction — a gate
on the function's *input*. `pack_matches_manifest` reads the directory the judge will be handed
and asserts set equality per submission; `field.build_pack` refuses a code field that fails it,
and `--allow-truncated` does not excuse it. A pack with no manifest is **unmeasurable, not
clean**. `judge/pack_selftest.py` pins both halves and must stay green.

`evaluate.py` returns `usable: false` and excludes a tier with weight renormalisation rather than
scoring an empty pack.

**Re-packing a stored run is `repack.py`, and it is not "run the packer again".** The
starter-identical filter compares against the starter as it is NOW, so a starter that moved since
the run was packed makes template code look authored (#77) — the opposite failure to the one you
are repairing. `repack.py` computes the exclusion set as *(rebuilt origins) minus (stored
manifest) minus (files dropped for length, asserted 0)*, then requires each excluded file to be
byte-identical to its blob in the work tree's `starter baseline` commit, and **refuses** when that
corroboration is unavailable — no manifest, no work tree, a non-zero length-drop count, or a
disagreement between the two methods. A refused submission is **marked, not re-packed**. It reads
the starter path out of `report.json` rather than deriving one, because a derived path resolves
inside whatever checkout the script is running from (rule 12).

**Every judge round stored before a re-pack read a field that no longer exists.** Say so wherever
the run's results are reported; no gate can reconstruct what a stored round was shown.

## Changing weights or the rubric

Update `RUBRIC.md` **and** the grading table in `README.md`. Then **re-grade offline** — re-running
a stochastic judge to apply a weight change silently changes the verdicts too, so you would be
measuring two things at once.
