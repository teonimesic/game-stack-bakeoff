---
id: 225
title: disclosure scan_run/scan_tree silently drop artifact dirs that hold no agent_result.json
status: in_review
priority: 4
refs: 'tasks/71,tasks/177,findings #98,findings #49'
done_when: '1. python3 eval/tools/disclosure.py --run-dir eval/runs/wg-audio-2026-08-14T12-29-42 reports 15 trials (not 11), with the 4 file-less dirs present as no_message rows whose reason names the missing agent_result.json. 2. --runs-dir eval/runs reports 98 trials total (not 91) and the per-run table shows wg-g4-2026-08-17T09-38-32 at /6 and wg-scene-s1ts-2026-08-25 including s1_parallax__ts__t0 as no_message. 3. The refusals are unchanged: an artifacts dir holding NO trial subdirs still exits 2 via DisclosureError (scan_run''s empty-population guard), a missing artifacts dir still exits 2, and the new rows must not be invented for paths that are not artifact dirs. 4. Every existing pin holds: --selftest (with corpus) exits 0 — MUST_LOCATE, MUST_LOCATE_BY_CUE, MUST_HAVE_NO_STARTER_CUE, MUST_HAVE_NO_UNVERIFIED_CUE, MUST_BE_QUIET, MUST_BE_NO_MESSAGE all unchanged, and the locator''s published figures still reproduce (unverified 25, starter 15 over the 91 stored messages). 5. The can-fail half: a mutant that suppresses the missing-file row path (e.g. the old is_file filter restored) must be caught by disclosure_mutants.py or by a new selftest row — state which, and show it red before the fix and green after. 6. docstat --sweep, --renumbered, tasks.py check all exit 0.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/105
---

eval/tools/disclosure.py is the locator behind AGENTS.md rule 11's report section: it reads artifacts/<trial>/agent_result.json .result WHOLE (the field wholegame.py truncates to 3000 chars), applies two never-pooled cue families, and prints three values (passages / quiet / no_message) on the ethic that no_message is UNMEASURABLE, never silence, and that the tool REFUSES to report 0. Both scanners violate that ethic for the one state the module has a branch for. scan_run filters artifact dirs on (d/agent_result.json).is_file() and scan_tree globs */artifacts/*/agent_result.json — so a trial directory with NO agent_result.json is dropped from the scan with no count and no name, and read_trial's own branch for exactly this state (:419-420, status no_message, reason 'no agent_result.json stored') is unreachable from both of them and from every CLI path. MEASURED at HEAD fe88597: eval/runs holds 98 artifact dirs at runs/<r>/artifacts/<t>/, 91 carry agent_result.json, 7 do not — wg-audio-2026-08-14T12-29-42 x4, wg-g4-2026-08-17T09-38-32 x2, wg-scene-s1ts-2026-08-25 x1 (that one a fully graded trial: eval/, diff.patch, submission.tar.gz all present, closing message never stored). Reproduced live: --run-dir on wg-audio-2026-08-14T12-29-42 prints '11 trials' for a run holding 15 artifact dirs; the whole-tree per-run table prints wg-g4 as '3 / 4 / 4' for a 6-dir run. wholegame.py:1062 (the report section) inherits the short count. WHY IT MATTERS: the tool exists because trials with no readable disclosure were invisible to every reader (tasks/71); this channel recreates that invisibility one level down — the trial whose message was never stored becomes invisible rather than NO MESSAGE. Nothing graded moves (disclosure is diagnostic-only, no criterion id, no weight), but every 'N trials' the tool prints is silently short of the run's artifact-dir population, and the trigger population is held by the corpus TODAY, not hypothetical. THE FIX IS A PROPERTY, NOT A MECHANISM: every artifact directory a scan reaches yields exactly one row; a dir lacking agent_result.json is a no_message row carrying its reason, counted in summarise's no_message total; a scan's trials count equals the number of artifact directories it reached. Do not narrow the scan population to make the counts agree — the missing row is the defect.

## note 2026-08-30

## Account, 2026-08-30 (branch task-225-disclosure-fileless-artifact-rows, PR #105)

**The fix is the property, as the ticket stated it.** Both scanners now take the artifact
DIRECTORIES as the population: `scan_run` filters on `d.is_dir()` alone and `scan_tree`
globs `*/artifacts/*` then filters to directories; `read_trial`'s existing no-file branch
(reason `no agent_result.json stored`) is finally reachable. No count was reconciled by
narrowing anything. `wholegame.py report` needed no edit — it inherits complete rows, and
the wg-audio report now reads 15 trials with the 4 never-stored rows named.

**done_when numbers, measured after the fix against the live corpus:**
1. wg-audio run: **15 trials** (5 located / 5 quiet / 5 no-message); the 4 file-less rows
   read `NO MESSAGE [?] no agent_result.json stored`.
2. Tree: **98 trials** (33 located / 43 quiet / 22 no-message — the original 15 plus the
   7 recovered). Per-run table: `wg-g4-2026-08-17T09-38-32  3 / 4 / 6`;
   `wg-scene-s1ts-2026-08-25  0 / 0 / 1`, with `s1_parallax__ts__t0` a no_message row.
3. Refusals re-proven by fixture: empty artifacts dir, missing artifacts dir and a
   root with no artifact dirs each still exit 2 via DisclosureError; a stray FILE under
   `artifacts/` yields no row (the fixture plants one).
4. Every existing pin holds: selftest with corpus exits 0; published figures reproduce
   (25 unverified-own-work, 15 starter-arrived-broken).

**Red before the fix: 7 failures, all on the new pins, every existing pin green.** New
selftest direction 0 is a fixture (tempdir run: `t_full` with a message, `t_bare` without,
a stray `stray.txt` file, an empty artifacts run, an empty root) and runs offline; new
direction 5b is the real-corpus half: the scanners' row set must equal the artifact
directories WALKED — the walk is written in the selftest, not imported from the scanners,
so the expectation is not the subject reading itself (task 113's shape). Plus two rows
whose answer the ticket stated in advance: the 4 wg-audio trial ids, and the scene row.

**The can-fail half is in disclosure_mutants.py**, as the ticket allowed: `scan_filter`
restores the old is_file filter at source, `scan_glob` restores the old file glob as
`p.parent`. Both CAUGHT against the corpus, and — proven separately — both caught with
`--skip-corpus` too, because a trial with no stored message carries no text for a cue
test to miss; only the scan-population pins can see this class of loss. Mutants 10 -> 12;
the harness docstring table and precampaign_smoke.py's label/comment counts bumped.

**Corpus drift note for the next reader:** the census at HEAD still reads 98/91/7 — the
same numbers the ticket measured at fe88597 (one run, `wg-harness-probe-primeagent-
2026-08-24`, predates the ticket's census and stores its file). The 7 file-less rows are
stored artifacts and will not change; new runs add rows but not to these pins. The two
scan-population pins compare the scan against a fresh walk each time, so they survive
corpus growth by construction; the name-pinned rows (wg-audio's 4, the scene trial) hold
because stored results are not rewritten.

**Deliberately left alone:** `--full` still enumerates stored messages (91), not trial
directories (98) — it is the no-selection raw view and holds no counts; the module
docstring now says so, so nobody reads it as a census. `read_trial`'s `terminal_reason`
for a file-less row stays `?` rather than opening `trials/<trial>.json` — the module
never opens `trials/`, by its own contract.

Gates at the pushed head f30448a (branch merged with origin/main c33e55b first — that
commit is the cleanup pass that FILED this ticket, docs only, no conflict): docstat
--selftest/--sweep/--renumbered/--findings/--withdrawn exit 0; lint --gate --rule
invalid-syntax exit 0; tasks.py check exit 0; disclosure selftest with corpus and with
--skip-corpus exit 0; disclosure_mutants 12/12 caught.
