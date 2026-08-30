---
id: 225
title: disclosure scan_run/scan_tree silently drop artifact dirs that hold no agent_result.json
status: done
priority: 4
refs: 'tasks/71,tasks/177,findings #98,findings #49'
done_when: '1. python3 eval/tools/disclosure.py --run-dir eval/runs/wg-audio-2026-08-14T12-29-42 reports 15 trials (not 11), with the 4 file-less dirs present as no_message rows whose reason names the missing agent_result.json. 2. --runs-dir eval/runs reports 98 trials total (not 91) and the per-run table shows wg-g4-2026-08-17T09-38-32 at /6 and wg-scene-s1ts-2026-08-25 including s1_parallax__ts__t0 as no_message. 3. The refusals are unchanged: an artifacts dir holding NO trial subdirs still exits 2 via DisclosureError (scan_run''s empty-population guard), a missing artifacts dir still exits 2, and the new rows must not be invented for paths that are not artifact dirs. 4. Every existing pin holds: --selftest (with corpus) exits 0 — MUST_LOCATE, MUST_LOCATE_BY_CUE, MUST_HAVE_NO_STARTER_CUE, MUST_HAVE_NO_UNVERIFIED_CUE, MUST_BE_QUIET, MUST_BE_NO_MESSAGE all unchanged, and the locator''s published figures still reproduce (unverified 25, starter 15 over the 91 stored messages). 5. The can-fail half: a mutant that suppresses the missing-file row path (e.g. the old is_file filter restored) must be caught by disclosure_mutants.py or by a new selftest row — state which, and show it red before the fix and green after. 6. docstat --sweep, --renumbered, tasks.py check all exit 0.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/105
established_by: 'Merged as #105 squash c254eb4. Verified at branch head 687eacfa in own detached checkout: red-first 11 rows at main (fileless dirs invisible); fixed wg-audio 15 trials (5/5/5) with 4 no-agent_result.json rows, tree 98 (33/43/22), wg-g4 6 (3/1/2), scene 1 (0/0/1); refusals exit 2 for both truly-empty and missing artifacts; --selftest exit 0 with main''s runs symlinked into the detached checkout; disclosure_mutants.py pass three directions incl. CORPUS_ONLY_MUTANTS sed to set() -> exit 1 naming tail+family_split (true split 10/2, not six); sweep/renumbered/tasks check 0 at head. Round 1 comment (docstring coverage claim) verified true and fixed by the offline half; verdict NOT_YET at merged head (no round yet), merged on artifact verification per hand-back semantics. No new finding: the 7 recovered directories never carried a stored message, so no published figure moves.'
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

## note 2026-08-30

## Round 1 review — FIXED in 750c1b4

CodeRabbit (comment 3889972037) found the docstring claiming `scan_filter`/`scan_glob`
"stay pinned with --skip-corpus" while `main()` exited before applying any mutant when
the corpus was absent, and never passed `--skip-corpus`. Correct, and finding-shaped:
**a coverage claim nothing runs is not a claim.** My proof at round 0 was a
session-local one-off script — a demonstration, not a gate, and it proved the scan
mutants are catchable offline, not that anything enforces it.

The fix makes the offline pass the enforcement:

- `main()` runs an **offline half in every checkout** (worktree, no corpus included)
  over **all twelve** mutants against the selftest's fixture half (`--skip-corpus`),
  then requires the offline survivors to equal `CORPUS_ONLY_MUTANTS` **exactly**.
  Under-declaration (an undeclared survivor) exits 1; over-declaration (a declared
  mutant that dies offline — which would have silently exempted it from the offline
  pin) exits 1 as a stale entry to trim. A missing corpus still exits 2, after the
  offline half ran and agreed — not before any mutant was applied.
- The corpus half still applies all twelve against the real stored messages, and the
  final green line reports the re-derived split beside the set it matched.

Two measurements the round shook out:

- The true offline split is **10/2** (`tail`, `family_split`), not the "six caught only
  by a real stored message" the docstring carried at round 0. That figure had been
  propagated from an old `precampaign_smoke.py` label and was never measured — the
  counts rule fired on my own text. Corrected 2026-08-30 with the method stated, and
  the measurement is now re-derived on every run of the file.
- Closing the set turned out to matter in the other direction too: with only a
  fail-closed default and no equality check, the repair for this comment could have
  been "declare everything corpus-only", which quietly removes the offline pin from
  all twelve.

Controls, all four directions: committed state 12/12 caught against the corpus with
the offline half re-measuring 10, exit 0; no corpus → offline half runs, UNMEASURABLE
names the address and the two declared mutants, exit 2; set emptied → `OFFLINE-PIN
MISMATCH … undeclared ['tail', 'family_split']`, exit 1; `gap` wrongly added →
`… stale declarations (trim): ['gap']`, exit 1.
