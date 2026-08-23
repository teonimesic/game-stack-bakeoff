# Cleanup log — what has been explored, and what was found

Every cleanup pass appends here. See `.claude/skills/prune/SKILL.md` for the procedure.

**Read this before exploring.** Its purpose is to stop the next pass re-reading ground already
covered and re-filing tasks already filed. That means **negative results matter as much as
findings**: *"read all six skills, nothing worth changing"* is a useful entry and only exists
if someone writes it.

This is the same discipline the project applies to its instruments — record what the pass
*did*, not only what it concluded. The judge's file-open log was added for an unrelated
question and two weeks later was the only reason a serious defect could be bounded.

## Format

```
## YYYY-MM-DD — <area explored>
**Looked for:** what question the pass was asking
**Read:** the files actually opened, not the ones it meant to
**Found:** what was cut, replaced, or filed — with task ids
**Cleared:** what was examined and judged sound, so nobody re-examines it
```

---

## 2026-08-23 — mechanical shapes, whole repository

**Looked for:** whether a cleanup pass could be given an instrument at all, and what the
obvious mechanical candidates are. This pass built `eval/tools/prune_scan.py` and ran it; it
is a baseline, not a thorough exploration of any one area.

**Read:** `eval/tools/docstat.py` (to check the existing sweep did not already cover this — it
does not; it asks whether names *resolve*, not whether text *earns its space*), `AGENTS.md`
pruning and archive rules, `eval/FINDINGS.md` structure.

**Found:**

- **`eval/starters/*` and `template*/` share whole documents.** `three-api.md` has 20 identical
  paragraphs across two paths; `bevy-0.19-notes.md` 8; `godot-4.7-notes.md` 5; each stack's
  `AGENTS.md` 4. **Not yet investigated and not yet filed** — these may be a deliberate copy
  with a sync step, in which case the finding is that nothing checks the copies agree. Whoever
  takes this must find out which before proposing anything, and must read `AGENTS.md` first:
  `template*/` and `eval/starters/*/` are the **product**, and editing one is a regime boundary
  requiring `verify_blind.py`.
- **A second copy of all six skills at `.agents/skills/`**, three already drifted — filed as
  **task 27** before this log existed.
- 23 functions over 90 lines, the largest `starter_parity.py:main` at 181 and
  `field.py:build_pack` at 170. Refactor candidates only; nothing is known to be wrong with
  them and `build_pack` is load-bearing for blinding.
- ~12,000 tokens sit in six sections long enough that nobody finishes them, the largest being
  `eval/FINDINGS.md` "Every finding" (~2,545) and `AGENTS.md` "Rules this project learned the
  hard way" (~2,227). The FINDINGS one is an index into the archive and is probably earning it.

**Cleared:**

- **Dead code: one candidate in the whole repository** (`eval/runner.py:349 removes_lines`),
  and even that is a candidate rather than a corpse. The other 59 hits were test fixtures the
  harness discovers by name, which is what they are for. There is no dead-code problem here.
- **TODO/FIXME markers: one**, and it is a regex *searching* for stubbed checks, not a stub.
  Nothing to do.
- `eval/findings/`, `eval/FINDINGS.md` and `eval/RUNS.md` were deliberately **not** scanned for
  staleness. Their "superseded" and "retracted" language is the subject matter, and a pass that
  tidied them would destroy the retraction record — the most valuable text here.

**Not done:** no area was read properly. Every entry above is mechanical output plus judgement
about what it means. The first real pass should pick one area from the skill's table.

## 2026-08-23 — churn, complexity and lint added to the instrument

**Looked for:** whether the cleanup pass could see code quality at all, not just prose. It could
not: there was no linter of any kind for the harness, and no complexity or churn signal anywhere.

**Read:** every `justfile` lint recipe (all four belong to the templates, i.e. the product, not
the harness), `docstat.py`'s sweep, and ruff's output over `eval/` at two rule sets.

**Found:**

- **No Python linter existed for the harness.** `ruff` installed via `uv tool install`. Wired in
  as `prune_scan.py --only lint`, **pinned** to correctness rules — an unpinned selection makes
  the number move when the tool updates, which is the `project_lines` drift again.
- **27 `subprocess.run` calls without `check=`, and 29 blind `except Exception`.** These map onto
  `AGENTS.md` rule 3 (an unread exit status) and #31 (fail-open) respectively. Filed as **task 34**
  — triage, explicitly not a mass fix.
- **`hotspot` = churn × complexity** added, plus per-function cyclomatic complexity computed
  in-tree so the scanner keeps no dependency. Top hotspots are `bot_platformer.py` (cx 282 over 5
  commits) and `judge/field.py` (cx 241 over 3), both of which are also where the work has been
  this week — which is exactly why a hotspot is a question and not a verdict.

**Cleared:**

- **The 491-issue headline is not a code-quality result.** It came from ruff's unpinned defaults:
  132 percent-format warnings and 43 "shebang present but file not executable". The pinned set
  reports 28 distinct rules. Nobody should act on the larger number.
- The absence branch of the lint category is controlled: with `ruff` unavailable it reports its own
  absence rather than an empty list, so a missing tool cannot read as a clean bill of health —
  the `-disable-audio` failure (#61), which this project has already paid for once.

**Not done:** still no area of the repository has been *read* properly. Both entries in this log
so far are instrument-building. The next pass should pick an area from the skill's table and read it.
