---
id: 116
title: DECISIONS.md Open section states a launched game as not launched, and carries a duplicated paragraph fragment
status: done
priority: 3
refs: DECISIONS.md Open section, eval/judge/tier1_census.py, eval/judge/tier2_census.py, AGENTS.md Keep the documentation current
done_when: the g4 bullet in DECISIONS.md's Open section states what is true now - re-read from a producer run in the session, not from memory - and the duplicated fragment is gone, with docstat.py --sweep, --findings and --withdrawn green and no new figure introduced without its producer
established_by: 'DECISIONS.md Open section repaired: the g4 bullet states LAUNCHED with 698.21 dollars re-derived from total_cost_usd over eval/runs/wg-g4*/artifacts/*/agent_result.json (extraction pinned against RUNS.md''s documented wg-g4c 421.00 and per-trial 36.16-77.60), and the half-overwritten rubric-ceiling paragraph is one coherent paragraph carrying tier1_census.py''s 61 of 68 and tier2_census.py''s 5 of 10 groups / 35 of 68, both re-run in-session against the main checkout. eval/G4-PLATFORMER.md''s title and status line carried the same defect and are repaired. Gates green unpiped: docstat.py --sweep --findings --withdrawn --renumbered, linkcheck.py, tasks.py check, withdrawn_control.py 54/54 - all green BEFORE the fix too, so no gate sees this class; measured and filed as task 119. Branch task-116-decisions-open-section, commit 0089573'
---

Found while re-checking README's headline for task 115. The Open section says 'g4, the platformer, is designed and NOT launched. Launching needs approval and at least two calibration trials; the honest cost range is 800-1900 dollars (#42)'. The platformer has since run: tier1_census and tier2_census both report a g4_platformer group of 8 trials, and the harder-task pricing section a few hundred lines above quotes its field as a completed 8/8. The same bullet also carries a duplicated, half-overwritten paragraph - the sentence '40 of 56 matrix trials at the ceiling with zero variance, not merely near it (#92)' appears twice, the second time as an orphan continuing a sentence that already ended. AGENTS.md says DECISIONS.md states what is true now and superseded content is replaced, not annotated, so both are live defects in an always-cited document. Out of scope for 115, which was README only.

## what established it, 2026-08-23 — do not re-derive

**Both figures were re-read from producers in-session**, not from memory, against the **main
checkout's** `eval/runs` — it is gitignored, so a worktree copy is empty (rule 12):

- `python3 eval/judge/tier1_census.py --runs-root <main>/eval/runs` → 68 stored submissions,
  7 failing trials sitting in 3 groups, 7 of 10 groups single-valued. So tier 1 is at 1.0 on
  **61 of 68**.
- `python3 eval/judge/tier2_census.py --runs-root <main>/eval/runs` → 10 groups, 5 saturated,
  **35 of 68** trials (8+3+8+8+8). Verdict `SATURATED`.

Both exit 0 unpiped.

**The duplicated fragment: the SECOND half was the newer and correct text and the FIRST half was
the stale one** — the opposite of what an edit-order guess would say. The stale half read *"Tier 2
is still at the ceiling on 24 of 56 — `wg-audio48` and `wg-g4c` entire"*; the true figure is 35 of
68, because `wg-audio` g1_pong (8) and g2_tetris3d (3) are saturated too and the 24-of-56 reading
omitted them. **Do not restore the deleted half.**

**g4 spend — extraction pinned on a known answer before it was believed.** Cost lives at
`agent_result.json` → `total_cost_usd`; it is *not* nested under `.agent` and *not* in
`trials/*.json`. A first sweep of the wrong key returned $0.00 for all three runs — uniformly,
which is the tell. Summing over `eval/runs/wg-g4*/artifacts/*/agent_result.json` reproduces
`eval/RUNS.md`'s documented `wg-g4c` $421.00 and its per-trial $36.16–$77.60 exactly. `wg-g4`
$211.64 / 4 `completed`; `wg-g4b` $65.57 / 8 `api_error`; `wg-g4c` $421.00 / 8 `completed`.
Summing the unrounded floats gives $698.22; the documented **$698.21** is the sum of the three
rounded run totals. Same figure, different rounding order — $698.21 is used, matching
`eval/RUNS.md` line 51 and `DECISIONS.md`'s own pricing table.

**#42's $800–1,900 is not the comparable figure and must not be reported as an overshoot**: it
priced a **24-trial** matrix. What was bought is one 8-cell field plus two runs that produced
nothing gradeable.

**"Score 1.000" is ambiguous on `wg-g4c` and the two readings disagree.** Tier 2 is 1.000 on 8 of
8; stored `overall` under the pre-gate weighted scheme is 1.000 on only **6 of 8** — the
withdrawal register entry `WR-20-of-24` records exactly this and demands the scheme be stated
with the count. Both edited passages now say **tier 2 = 1.000** explicitly. `DECISIONS.md`'s
"Task set and judging protocol" paragraph and the saturated-tier-2 section still carry the bare
phrasing; it is unambiguous from their context and was deliberately left alone.

**Out of ticket, done anyway.** `eval/G4-PLATFORMER.md` carried the same defect more prominently —
its H1 said *"(BUILT, for review before launch)"* and its line 3 said *"Nothing has been
launched."* The header is replaced; the 371-line body is explicitly marked as the preserved
pre-launch brief rather than rewritten, because its pre-registration section *"What would make
this game worth its cost even if it ties"* is only evidence while it stays as written.

**No gate caught either defect.** `docstat.py --sweep`, `--findings`, `--withdrawn`,
`--renumbered`, `linkcheck.py`, `tasks.py check` and `withdrawn_control.py` all exit 0 both
before and after the repair. The measurement of what *would* catch it — and why the obvious
sentence-level detector is a complete false negative — is **task 119**.
