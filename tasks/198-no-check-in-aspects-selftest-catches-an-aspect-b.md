---
id: 198
title: No check in aspects_selftest catches an aspect brief that promises evidence its pack does not carry - the FUN_FRAMES notes-inheritance defect is unguarded
status: in_testing
priority: 3
refs: eval/judge/aspects.py,eval/judge/aspects_selftest.py
done_when: 'aspects_selftest.py carries a check and a mutant pair such that: (1) the reconstructed notes-inheritance mutant - fun_frames briefed with fun''s notes - is RED on the new check; (2) the live 9-aspect registry is GREEN; (3) all 10 existing mutants remain red on their existing checks and the suite still exits 0; (4) the check''s expectation is NOT derived from the subject it checks (rule 12 corollary, task 113) - it reads a property of the registry against the channel vocabulary the sees field defines, and what counts as naming a channel is stated in the check, not enumerated per aspect. The property to state: no aspect''s notes or evidence_rule name evidence its sees does not include. Per the prescribed-repair rule: the mechanism (token list, parse, vocabulary source) is the agent''s to choose - what must keep failing is the reconstructed mutant, and what must stay passing is the live registry plus the variant direction (a brief naming a channel it DOES carry must not go red).'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/79
established_by: 'aspects_selftest exit 0 unpiped: 7 checks, 13 mutants red on their named checks (incl. the empty-sees pin on architecture), green variant row; reconstructed notes-inheritance mutant red on the new check and green on all six others; live 9-aspect registry green; sweep, tasks check, dead_private_control green; CodeRabbit round 1 thread replied and resolved at 8bb392a; PR #79'
---

aspects.py:380-391 records the original defect: FUN_FRAMES was built with replace(FUN, ...) and inherited FUN's notes, which describe telemetry.json at length, while its sees is frames-only - caught by hand by building the pack and diffing it against the brief. Nothing pins that repair: check_control_briefing_is_identical compares only the blind-spot paragraph TAIL (from FRAMES_BLIND_SPOT[:60] to end), which is byte-identical by construction in both aspects, and no other check or mutant scans a brief for evidence its sees excludes. MEASURED 2026-08-28 (orchestrator, cleanup pass): reconstructed the defect as replace(ASPECTS['fun_frames'], notes=ASPECTS['fun'].notes) and ran all six check functions against it - 0 problems from every one, while 'telemetry.json' is present in the mutant brief. The 10-entry mutants() list has no member for this class either. Why it matters: the failure mode is a judge briefed on evidence the pack does not carry, which invites reasoning about absent evidence - the exact defect the pack-diff caught by hand, one refactor away from returning with every check green. Marked as measured, not inferred: the red state above is the probe output, not a prediction.

## note 2026-08-28

Done on `task-198-brief-must-not-name-absent-evidence`, PR #79.

**The check.** `check_brief_names_no_evidence_sees_excludes`, seventh in `CHECKS`. For each
aspect it takes the channels its `sees` names (`split("+")`, stripped — the same grammar
`field.build_pack` switches on), and refuses any token of `CHANNEL_TOKENS` whose channel is
not in that set, over `evidence_rule` + `notes` (lowercased). `question` is deliberately out
of scope: a control inherits its treatment's question on purpose, and a question names no
artifact.

**The vocabulary, and the measurement that chose it.** `CHANNEL_TOKENS` states, per channel,
the ARTIFACT names that count as naming it: `frames/` + `png` (frames), `telemetry`
(telemetry), `audio` (audio), `changed.txt` (code — the one harness-written file a code pack
carries and a frames/telemetry/audio pack does not; `EVIDENCE_BLURB["code"]` opens with it).
Every generic English word that can also name code evidence fires on a live brief of another
channel, measured over all 9 aspects before the tokens were fixed: "the source that triggers
them" (`audio`'s notes), "per-frame position assignment" (`framework_fluency`'s — the reason
bare `frame` is NOT a frames token), "file" (both code aspects' evidence_rules AND `audio`'s),
"manifest"/"clip"/"cue" (`audio`'s own evidence vocabulary). A vocabulary built on those is
red on the live registry before it catches anything. The artifact tokens: 0 hits across the 9
live aspects outside their own channel, 1 true positive on the mutant. A `sees` naming a
channel absent from `CHANNEL_TOKENS` is refused (fail-closed), not skipped — same intended
failure as `SCENE_ONLY`; a new channel must be stated there.

**Both directions, measured.** The reconstructed mutant
(`replace(ASPECTS['fun_frames'], notes=ASPECTS['fun'].notes)`) was re-measured green on all
six pre-existing checks before implementation (reproducing the ticket's probe), then red on
the new check with "sees='frames' but its brief names telemetry evidence (telemetry)". Live
registry: green on all 7. Suite: 12 mutants/variants each red on its named check, plus a
GREEN variant row in `main()` — one brief naming all four channels over
`sees="code+frames+telemetry+audio"` — which pins the open direction no mutant can reach:
the check fires on the exclusion, not on the naming. Exit 0 unpiped.

**Also:** one line added to the defect record in `aspects.py` (the comment above
`FUN_FRAMES`' notes) noting the rule is now pinned and by what. Nothing else touched — no
starter, no registry value, no `sees`. No finding number taken: the defect was already
recorded; this closes it. If the orchestrator wants the gap itself (a notes-inheritance
defect invisible to 6 checks) numbered, that allocation is theirs.

## note 2026-08-28

**Review round 1 (CodeRabbit, at 863028e; fixed at 8bb392a).** One thread: the empty-`sees`
refusal in the new check had no mutant — with the refusal deleted the whole suite still
exited 0, so the guard was unpinned. Confirmed by deleting it and running. The thread's
suggested mutant (`ux`, `sees=""`) does NOT pin the refusal, measured: `ux`'s brief names
`png`, so the token loop keeps the row red with the guard deleted — it would measure the
loop, not the guard. The row is pinned on `architecture` instead, whose brief names no
channel artifact (`changed.txt`/`frames/`/`png`/`telemetry`/`audio` — none appear): refusal
present → row RED, suite exit 0; refusal deleted → exactly that one row FAILs, exit 1,
other 12 rows untouched. Replied on the thread with that measurement, thread resolved,
PR body updated. 13 mutants/variants total; live registry green; exit 0 unpiped.

The transferable bit: **a mutant row proves a guard only if the row dies when the guard is
deleted.** Any aspect whose brief names any channel token produces an empty-`sees` row the
token loop catches — red under both the guard and its removal — which pins nothing. Choose
the subject whose ONLY firing path is the guard under test.
