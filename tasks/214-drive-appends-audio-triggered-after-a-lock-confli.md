---
id: 214
title: 'drive() appends audio.triggered after a lock-conflict unusable, so the #25 exclusion does not reach the one criterion added outside unusable_criteria'
status: in_review
priority: 5
refs: eval/judge/probe.py, eval/judge/audio.py, eval/findings/one-arm-bias.md
done_when: a fixture drives probe.drive with a stub ProbeSession whose start raises ProbeError(lock_conflict=True) and a bot declaring audio_game, and the returned audio.triggered criterion comes back scored=False with the NOT MEASURED project-lock reason instead of the current scored=True failure - while a stub that raises a NON-lock ProbeError, and a session that runs and genuinely emits no events, both leave audio.triggered scored=True failed (the fail-closed default is NOT loosened) - pinned in a selftest that runs unpiped exit 0, with a mutant restoring the current append-scorch behaviour going red on the lock fixture and green on the two controls.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/94
---

`probe.drive()` handles a probe that cannot be opened or kept alive by calling
`bot.unusable(e)` (probe.py:910), which routes through `unusable_criteria`: a
`ProbeError` carrying `lock_conflict=True` returns every bot criterion `scored=False`
with the NOT MEASURED project-lock reason — the FINDINGS #25 remedy, because a criterion
that can only fail on the arm that takes a project lock is bias rather than noise.

Then, AFTER that conversion, drive() appends one more criterion:

    if audio_game is not None:                                  # probe.py:960
        crits = [*crits, audio_mod.triggered_criterion(repo, audio_game, fired, env)]

with `fired = []` (the probe never ran, so no events were collected).
`audio.triggered_criterion`'s empty-fired branch (audio.py:610) returns
`Criterion(..., passed=False)` on the dataclass default `scored=True`. Measured
in-process against the current modules:

    triggered_criterion(repo, "g", fired=[], env=None) -> passed=False, scored=True
    unusable_criteria on the same lock error            -> passed=False, scored=False

So on an audio-class submission (evaluate.py:337 and :365 pass `audio_game` for audio
task classes) whose probe session died in a project-lock conflict, every bot criterion
is excluded from the score as #25 requires — and `audio.triggered` alone is counted as
a failure, evidence "the driven run emitted no events at all, so no cue could be checked
(fail-closed)". The evidence sentence is true and the exclusion is silently undone for
exactly the criterion that cannot inherit it, because it is composed after
`unusable_criteria` and never sees the exception.

**The same policy hole inside audio.py itself.** `triggered_criterion`'s manifest branch
(audio.py:614-616) returns `Criterion(passed=False)` with default `scored=True` when
`read_manifest` returns None — including when read_manifest (audio.py:296-312) exhausted
its retries BECAUSE every attempt matched `LOCK_HINTS`, the case that file's own comment
block (above its `LOCK_HINTS` at audio.py:292) calls "bias, not noise (FINDINGS #25)".
The retry implements the waiting; the verdict after the waiting does not implement the
exclusion. read_manifest's callers get `(None, note, code)` and no lock flag, so they
cannot tell a lock refusal from a broken manifest.

**Reachable today? No — that is why this is p5.** `grep -rl "project-lock signature"
eval/runs/` returns nothing: no stored submission ever recorded the probe-side lock path,
because `_claim_repo` (the #30 repair — one live session per repository) removed the
self-inflicted conflicts that made #25 common. What is left is the narrow window the
design cannot remove: a sibling PROCESS on the same project directory, or an engine still
shutting down inside `close()`'s grace. On that window the audio arm alone is deducted.
Same split as tasks/211 and tasks/213: the channel, not a wrong stored number.

**What NOT to conclude:** nothing stored is wrong; do not touch published figures; do
not write into `eval/runs/`. And do not "fix" this by making the empty-fired branch
`scored=False` unconditionally — a probe that RAN and emitted no events SHOULD fail this
criterion (that is the fail-closed contract, and stored audio evidence uses it). The
distinguishing fact is whether the run happened, which only the caller knows.

**Model for the fix:** `unusable_criteria` already computes the one bit needed. Carry it:
give `triggered_criterion` a lock path (a `lock_note`/flag parameter, or a classmethod
returning the NOT MEASURED criterion `unusable_criteria` builds) and have `drive()` use
it when the session ended in a `lock_conflict` ProbeError — the reason string should name
the engine and the harness, as unusable_criteria's does, not "no events at all". In
audio.py, `read_manifest` should return the lock bit (or a typed reason) so
`triggered_criterion` can mark a lock-exhausted manifest read `scored=False` with the
same NOT MEASURED wording — its own comment block already states the policy; the code
should carry it.

**Checks, both directions.** The lock fixture and its two controls are in `done_when`:
stub `probe.ProbeSession` (monkeypatch the module attribute — `drive()` names the class
directly, so the stub replaces it wholesale; a stub `__enter__` raising
`ProbeError("...", lock_conflict=True)` needs no engine, no child, no `just`), assert the
appended criterion is scored=False with the lock reason; the non-lock ProbeError control
stays scored=True failed; and a stub session that RUNS and emits nothing stays scored=True
failed. A mutant restoring today's composition (append without the lock bit) must go red
on the lock fixture and green on both controls — it is a variant question too: the
genuine-empty and bot-bug paths must be unchanged after the fix.
