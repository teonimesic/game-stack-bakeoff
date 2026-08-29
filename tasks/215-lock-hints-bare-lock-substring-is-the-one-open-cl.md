---
id: 215
title: LOCK_HINTS exists as two never-compared hand copies, and its one open-class member - the bare substring "lock" - has 0 true positives on the stored corpus while reading benign engine words as lock conflicts
status: todo
priority: 5
refs: eval/judge/probe.py, eval/judge/audio.py, eval/findings/one-arm-bias.md, eval/findings/certifies-nothing.md
done_when: 'the two LOCK_HINTS tuples are one definition asserted equal at import (the #100/#114 same-object pattern) or a single shared constant, the bare "lock" substring is gone from it with every specific phrase retained, and a pinned check shows BOTH stored true-positive pollution lines still classify as lock conflicts while banners reading "Clock: 60 fps" and "Deadlock detection: off" no longer do - plus the audio.py note path re-censused, with the consequence asymmetry stated in the ticket this closes.'
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
