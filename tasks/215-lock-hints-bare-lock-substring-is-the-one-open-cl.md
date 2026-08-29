---
id: 215
title: LOCK_HINTS exists as two never-compared hand copies, and its one open-class member - the bare substring "lock" - has 0 true positives on the stored corpus while reading benign engine words as lock conflicts
status: done
priority: 5
refs: eval/judge/probe.py, eval/judge/audio.py, eval/findings/one-arm-bias.md, eval/findings/certifies-nothing.md
done_when: 'the two LOCK_HINTS tuples are one definition asserted equal at import (the #100/#114 same-object pattern) or a single shared constant, the bare "lock" substring is gone from it with every specific phrase retained, and a pinned check shows BOTH stored true-positive pollution lines still classify as lock conflicts while banners reading "Clock: 60 fps" and "Deadlock detection: off" no longer do - plus the audio.py note path re-censused, with the consequence asymmetry stated in the ticket this closes.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/96
established_by: 'PR #96 squash 4ae32ac, branch head e5d00858d49f1b0a52cec23bb139cd6a297bdd19 (branch task-215-one-lock-hints); verified at that head in own detached checkout unpiped: audio_selftest 124/124 (identity row audio.LOCK_HINTS is probe.LOCK_HINTS, exact-vocabulary row against independently transcribed EXPECTED_LOCK_HINTS, both stored Unity refusal lines classify through both readers, Clock/Deadlock banners through neither, mutants 13/14/15 each caught), bot_mutants 53/0, sweep clean, check well-formed; re-derived census over 1429 stored json files reproduces the ticket numbers (2 true-positive lines, 0 bare-lock hits, 0 lock-classified records); review round 2 clean; merged main gates green unpiped (sweep, renumbered, check, audio_selftest 124/124); no finding allocated (corpus clean; the triggers future surface, the channel-not-wrong-number split); audit_criteria.py HARNESS_SIGNATURES deliberately left alone, flagged in the ticket.'
---

`LOCK_HINTS` is defined twice by hand — probe.py:230 and audio.py:292 — five phrases
each, never asserted equal, in the shape #100/#114 repaired for static/runner (aliases
asserted the same object). The two copies have also drifted in what a match MEANS, which
is the strongest reason for one definition carrying the reasoning:

- **probe.py** (`_looks_like_lock_conflict`, probe.py:178-184): a match during
  `start()` retries ends in `lock_conflict=True` → every criterion `scored=False`,
  "NOT MEASURED ... Excluded from the score". Over-broad here is FAIL-OPEN: a submission
  that cannot be driven escapes the score, the exact direction
  `_looks_like_lock_conflict`'s docstring says the harness-note exclusion exists to
  prevent ("a note containing the word lock would otherwise make every later failure
  look like a lock conflict, which would turn fail-closed into fail-open").
- **audio.py** (`read_manifest`, audio.py:309): a match only buys another retry, then an
  honest `scored=True` failure at audio.py:615-616. Over-broad here wastes retries and
  misclassifies nothing.

The breadth question is measurable on the stored corpus, and it was (2026-08-29, the
tenth cleanup pass):

- Every `[stdout pollution]` line stored under `eval/runs/`, unique: **2**. Both are
  genuine Unity fatal refusals printed to the CHILD'S STDOUT — "It looks like another
  Unity instance is running wit..." and "Multiple Unity instances cannot open the same
  project." — and both match the SPECIFIC phrases. Without the pollution path appending
  into `_stderr_tail` (probe.py:383), which `_stderr_str` feeds into ProbeError messages,
  these would never have voted; the pollution channel is load-bearing for the #25 remedy
  and must not be narrowed away.
- Every stored `probe_stderr` string across `eval/runs/*/artifacts/*/eval/*.json`
  scanned for any hint substring: **0** lines. The bare "lock" member has **0 true
  positives and 0 stored false positives** — it has never matched anything real.
- In-process, it does match benign engine vocabulary:
  `_looks_like_lock_conflict` reads `True` for a ProbeError whose stderr tail carries
  `[stdout pollution] Clock: 60 fps` and for `[stdout pollution] Deadlock detection:
  off`. A hung engine that printed any banner containing clock/block/unlock/flock
  ("clock" is inside "clock" — the substring needs no boundary) would take the 4-retry
  path and come out `lock_conflict=True`: **a genuinely hung submission — the failure
  mode this tier exists to catch, fail-closed — excluded from the score as NOT
  MEASURED.**

**Why the bare substring and not the whole set:** the four specific phrases are a CLOSED
class — engine wordings, two of them observed verbatim on the stored corpus. The bare
substring is an open-class member, and the aspect-census derivation
(`DECISIONS.md`, and `certifies-nothing.md` at the LOCK_HINTS mentions) already priced
that family: an open-class trigger fails later rather than sooner, and by then it is
firing on correct input. This is #30's neighbour, not a restatement: #30 is about WHO
holds the lock (internal vs external party); this is about WHAT TEXT counts as the
engine's refusal, where the only member that generalises past the observed messages is
the one that also matches words no refusal uses.

**What NOT to conclude:** the stored corpus is clean — no submission was ever excluded
by the bare substring (0 stored lock-classified records at all), so nothing is
re-interpreted and no figure moves. This is the trigger's future surface, not a past
wrong number. Do not write into `eval/runs/`.

**Checks, both directions.** Pin the 2 stored true-positive lines (verbatim, in the
fixture) as STILL lock-classified after the substring goes — that is the control proving
the repair did not blunt the #25 remedy. Pin the two benign banners as NOT classified.
Pin the two copies equal (or one shared constant) so the next hint lands once. And run
`bot_mutants.py`'s serialisation check after: #25's structural fix must be untouched by
a wording-set change.

## Correction 2026-08-29, after tasks/214 landed (PR #94, squash 7518e6d)

The consequence asymmetry this ticket states for audio.py is INVERTED by 214's
landing, and the inversion strengthens the ticket. `read_manifest` now returns a
`ManifestRead` carrying a `lock` bit, and `triggered_criterion` marks a lock-eaten
read `scored=False` NOT MEASURED. So an over-broad hint match in audio.py no longer
"wastes retries and misclassifies nothing": a benign `Clock: 60 fps` banner now buys
the retries, exhausts them, comes back `lock=True`, and **excludes** the criterion —
fail-open on audio.py's side too, exactly like probe.py's. Both copies are now
fail-open on over-breadth; only the RETRY cost differs between them. The one
definition and the closed class are therefore worth more than this ticket first
priced, and the pinned greens are unchanged: the four specific phrases still carry
both stored true positives, the bare `"lock"` still has 0 stored true positives and
0 stored records of any kind through it. The tuples themselves are untouched by 214
(probe.py:234, audio.py:292; line numbers only drifted).

## note 2026-08-29

## Done — PR #96 (2 review rounds, all checks green at e5d0085)

**The repair.** `LOCK_HINTS` is one module-level tuple in `probe.py` (after `ProbeError`,
with the FINDINGS #25 reasoning and the closed-class derivation in its comment);
`audio.py` imports it; `audio_selftest.py` asserts `audio.LOCK_HINTS is probe.LOCK_HINTS`.
The bare `"lock"` member is gone; the four specific phrases are retained. The classifier
`_looks_like_lock_conflict` is now a staticmethod reading the module constant — the old
class attribute had no external reader (grepped), and reading the module global is what
lets the mutants reach the real path.

**The census, re-derived from disk 2026-08-29** (1429 stored json files under `eval/runs/`,
read-only; the ticket's numbers all reproduce):

- 2 genuine pollution refusal lines, 76 stored occurrences each, both matching SPECIFIC
  phrases ("another unity instance", "cannot open the same project"). The other 13 unique
  `[stdout pollution]` segments are harness framing (`probe unusable ...`, `Aborting
  batchmode`, `Project: <path>`), not refusal signatures.
- 152 stored `probe_stderr` values: 0 match any hint, specific or bare.
- The audio.py note channel (stored strings beginning "`just audio-manifest`"): 44, in
  exactly 2 distinct shapes, both genuine Rust compile failures (exit 101). 0 match any hint.
- 1914 stored strings contain bare `lock` and no specific phrase: all benign (Tetris
  `lock` events, `piece.locks` ids, `sfx.lock` entries, judge prose with block/unlock).
- 0 stored lock-classified records of any kind — no `NOT MEASURED ... project-lock`
  evidence exists (the 15 stored `NOT MEASURED` strings are the scene-probe and
  knockback senses). Nothing re-interpreted, no figure moves.

**Consequence asymmetry, as this ticket closes it:** the asymmetry the ticket was filed
with is inverted by 214 and stays inverted. Both copies are fail-open on over-breadth;
only the retry cost differs (probe: 4 attempts then `lock_conflict=True` → excluded;
audio: 3 attempts then `lock=True` → `audio.triggered` excluded). A benign banner that
matched would have ended a genuinely hung submission as NOT MEASURED on the probe side
and excluded `audio.triggered` on the audio side. The closed class is therefore worth
having on both readers, and the pins cover both.

**Pins, both directions** (`audio_selftest.py`, section `ONE VOCABULARY, CLOSED CLASS`):
2 stored true positives verbatim classify through the probe classifier AND buy
`lock=True` on the real `read_manifest` path; the benign `Clock: 60 fps` and
`Deadlock detection: off` banners classify through neither; MUTANT 13 (bare `lock`
restored) scorches the benign pins on both readers; MUTANT 14 (phrase dropped) scorches
its own TP pin on both readers while the OTHER stored line still classifies; MUTANT 15
(equal-but-distinct copy) turns the identity pin red. Pre-repair red/green was
established row by row with a one-off driver before the fix (7 red / 11 rows, the 4 TP
controls green).

**What the next agent should not re-derive:**

- `tuple(t)` on an exact tuple IS t — the first MUTANT 15 manufactured no copy and
  survived. Use `tuple(list(t))` when a mutant needs a distinct, equal object.
- `audio_selftest.py` must stub `audio.time.sleep` around every manifest read: 3
  exhausted reads cost 36s wall (measured 46.4s -> 10.5s after the reviewer's catch in
  round 1). The stub pattern is in the file twice now.
- `audit_criteria.py`'s `HARNESS_SIGNATURES` also names 2 lock phrases by hand. It is an
  offline audit list, not a lock classifier, and `is_harness_failure` only reads 2 of
  its 4 members; this ticket did not touch it. If that list ever grows a live reader,
  it belongs in the one-definition pattern too.
- No finding number needed: the stored corpus is clean, so this is the trigger's future
  surface, not a past wrong number (the ticket's own "What NOT to conclude").

Gate results at head e5d0085: audio_selftest 124/124 (46.4s -> 10.5s after round 1);
bot_mutants in full — 53 mutants both directions, 17 variants, 0 pending, the 3
session-lock controls ok; docstat --sweep, tasks.py check, scene_mutants 3 selftests,
scene_runner_control (48 rows), aim_contract_control (13 rows), capture_selftest 39/39,
runner_capture_selftest 50/50, dead_private_control 18 measurements 0 failed; CI
controls 15m4s pass, gates 2m30s pass, CodeRabbit pass. Review round 1 carried 2
comments, both fixed and confirmed in thread; round 2 clean.
