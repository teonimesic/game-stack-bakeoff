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
  **task 27** before this log existed. **Resolved 2026-08-23: deleted** (#99). It had no reader,
  was never once in sync, and had taken 0 content-bearing edits against the authoritative tree's
  8. `docstat.py --sweep` now fails on any `SKILL.md` outside `.claude/skills/<name>/`, so
  `prune_scan.py`'s `MIRROR` suppression was removed with it — its `dup` category was reporting
  51 suppressed hits and now reports the starter/template pairs above without them.
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
- ~~The absence branch of the lint category is controlled: with `ruff` unavailable it reports its
  own absence rather than an empty list, so a missing tool cannot read as a clean bill of health —
  the `-disable-audio` failure (#61), which this project has already paid for once.~~
  **WRONG, and corrected by task 34 the same day (#105).** One of the three ways ruff can fail to
  run was controlled. Ruff refusing an invocation exits **2** with empty stdout, and ruff pointed
  at a path that does not exist exits **0** with `[]`; both printed `lint (0)`. Left marked rather
  than replaced because the claim was published and this log is a record of what a pass believed.

**Not done:** still no area of the repository has been *read* properly. Both entries in this log
so far are instrument-building. The next pass should pick an area from the skill's table and read it.
---

## 2026-08-23 — can an external linter tell us what earns its space? (task 32)

**Looked for:** whether any existing prose or markdown linter measures something that predicts
whether an agent follows a rule — i.e. whether the cleanup pass can be given a second instrument
beyond `prune_scan.py`. The answer decides whether future passes should run a tool or keep reading.

**Read:** `AGENTS.md`, `research/AGENTS.md`, `.claude/skills/prune/SKILL.md`,
`.claude/skills/tasks/SKILL.md`, all seven `.claude/skills/*/SKILL.md` frontmatter blocks,
`eval/tools/docstat.py` (`cmd_sweep`, `_project_root_for`, the FOREIGN_FLAG_PREFIXES rationale),
`eval/tools/tasks.py:228-320`, `README.md` heading structure, `DECISIONS.md`,
`eval/PROTOCOL.md`, `eval/judge/RUBRIC.md`, `eval/judge/JUDGING.md`, `eval/IMPROVEMENTS.md`,
`code.claude.com/docs/en/memory` and `/hooks`. Ran eleven tools against real files here.

**Found** — full write-up and every number in `research/11-doc-linting-for-agents.md`:

- **Eleven linters, 14,000+ alerts, two defects.** Both found by structure/schema checks, none by
  a prose rule. Filed as **tasks 35** (five SKILL.md frontmatter blocks are invalid YAML — Vale
  aborts on them, `claude plugin validate --strict` errors, Claude Code itself tolerates it) and
  **36** (`AGENTS.md` rules 10–16 use two-digit list markers with 3-space continuations, so five
  load-bearing paragraphs are structurally outside their rule under CommonMark).
- **Task 37** — put those two checks in `docstat.py`, where mechanical doc checks already live,
  rather than adopting a linter.
- **Task 38** — two defects in `tasks.py` hit while filing the above: `add` from a worktree
  creates the file then crashes on `Path.relative_to`, and `check`'s reachability `ESCAPE`
  keyword list false-positives on two of the tasks filed today.
- **Task 39** — the untested question underneath all of it: nothing published relates readability
  metrics to agent instruction-following, and the one adjacent measured result
  (arXiv:2509.21051) is testable with this project's own harness.

**Cleared** — do not re-explore these:

- **No prose linter is worth adopting here, and the measurement is recorded.** `alex` 35/35 false
  (this repo's vocabulary is "failure", "fire", "dead"); `write-good` 137 alerts, markdown-blind;
  `proselint` 16 of 18 alerts want curly quotes, which would break grep; `vale` + Microsoft/Google
  4,234 alerts on six files including 50× "prefer 'personal digital assistant' over 'agent'";
  `typos` 161/161 false; `cspell` 17/17 false (British spellings and tool names);
  `remark-preset-lint-recommended` **zero** issues; `textlint` refuses to run without config.
- **`markdownlint` is 95.6% line-width and table padding**, and of what remains `MD018` is 19/19
  false on `#NN` citations and `MD041` 8/10 false on the `@AGENTS.md` import files.
- **The path-resolution check stays removed.** `docstat.py:195-199` records it measured
  "0 true positives, 2 false"; independent re-measurement today across the main checkout found
  265 cited paths, 68 unresolved, **0 true positives**. `agnix` implements this check and produces
  ~60 false positives here. That decision is correct and should not be revisited.
- **`docstat.py --sweep` is clean** — 95 docs, 77 flags, 6 aspects.
- **Relative markdown links: 82 checked, 0 broken.** `remark-validate-links` would find nothing.
- **No Claude Code skill or plugin is worth installing** for doc quality. A GitHub code search for
  `vale` in `**/SKILL.md` returns 0. Anthropic's own `claude-md-management` plugin has one `find`
  command and otherwise prompts the model to emit `Score: XX/100` with no mechanism behind any
  digit — the exact shape this project exists to distrust.
- **Nothing was pruned and nothing was rewritten.** The task forbade a doc rewrite, and the two
  real defects are whitespace and quoting, filed rather than done here so they can be reverted
  separately.

**Method note worth carrying forward:** the path-resolution re-measurement was first run *inside
an agent worktree*, where `eval/runs/` is not checked out, and produced a confidently wrong
picture. `AGENTS.md` rule 12 — the address is an input to the check — arriving unprompted during a
pass about checking things. **A cleanup pass that measures anything about run artifacts must run
against the main checkout.**

---

## 2026-08-23 — `tasks/`: does each closed task's evidence still hold?

**Looked for:** the first pass to read an area rather than build an instrument. One question,
asked of all **42 done tasks**: given what has been learned since it closed, does the
`established_by` string still support the closure? A closed task whose evidence was overturned is
worse than an open one — it reads as settled, and its conclusion is still authorising things.

**Read:** every `established_by` and `refs` of all 42 done tasks (dumped in full, not skimmed);
task bodies of 10, 17, 24, 45; `eval/FINDINGS.md` and the headings of all six files in
`eval/findings/`; `eval/findings/limits-and-cost.md` #87, #90 and #104 in full; `eval/PROTOCOL.md`
lines 413-605 (the evidence boundary and the reclaim section); `.claude/skills/tasks/SKILL.md`;
`git log` over `eval/findings/`. Ran three measurements: every `## NN.` heading ever added under
`eval/findings/` replayed against the current numbering; duplicate ids and titles across `tasks/`;
the shared starter `AGENTS.md` block hashed in all four arms.

**Found — 6 of 42 corrected, 36 clear.**

- **Task 10 (the lead) — evidence superseded, corrected in place.** It established *"delete a
  work tree whose own tarball exists"*. #104, recorded after it closed, established that
  `submission.tar.gz` carries no `.git/`, so the tree's `starter baseline` root commit is the only
  record anywhere of the starter an agent was given — and all eight `wg-g4c` trees had tarballs,
  so the rule declared every one safe to delete. Baselines survived for 22 trees because task 42
  ran before anyone reclaimed, which is sequencing luck, not the rule working. Not reopened: the
  work was genuinely done and `eval/PROTOCOL.md` already requires **both** the tarball and a
  preserved baseline. `established_by` now carries the supersession and points at the file.

- **A closed task silently opened a deletion permission.** `PROTOCOL.md` said *"do not reclaim
  `wg-g4c` until task 07 is closed"*. Task 07 closed on 2026-08-23, and with it the only
  protection on the trees that are #66's sole reproduction — a repaired starter answers cold by
  construction, so the warm state cannot be rebuilt at any price. Rewritten to name the resource
  instead of the task id, with the general form: **a trigger written as a task id expires the
  moment someone finishes the task, and finishing it is not the same decision as destroying the
  evidence it was measured on.** Reclaiming those trees is now explicitly an ask-the-operator
  decision.

- **Eight findings have been renumbered at merge, and nothing updates what cited them.** Parallel
  agents pick the same next number; the merge renumbers one finding; every citation of the old
  number still *resolves*, so no sweep can see it, and it now points confidently at a stranger.
  Five stale citations repaired by hand — task 25 cited #95 for what is now #97, task 34 cited
  #104 for #105, task 42 cited #103 for #104, task 45 cited #99 for #100 in both `refs` and body,
  and `PROTOCOL.md` carried a `(#103)` meaning #104. Each repair keeps the original number and
  says why it moved, so the record is corrected rather than silently rewritten. This is **#94 with
  the damage moved downstream**: the collision is caught now, and catching it is what creates the
  dangling references. Filed as **task 58** — `tasks/` was swept by grep, and `DECISIONS.md`,
  `README.md`, `eval/RUNS.md`, both `IMPROVEMENTS.md`, `research/`, the skills and the
  cross-references inside `eval/findings/` have not been looked at.

- **Task 24 — two cells overturned, corrected in place.** Its Unity narrowing ("no physics,
  particle, audio or animation module") is no longer true of the starter after task 52 added the
  audio and particlesystem modules, and its three.js instancing cell — "the largest measured
  effect in the matrix" — did not survive re-measurement (#110). The research document carries the
  corrected rows; only the task record was stale. It also says it "filed task 27" for the
  TypeScript capture defects; that is the id that collided three ways that hour (#94), and the
  work survived as **task 31**.

- **Task 17's closure no longer describes the world.** Filed as **task 57**: the verified second
  copy at `/Users/stefano/game-research-evidence` is stamped `2026-08-23T00:08:58`, and the three
  `eval/runs/*/starter-baselines` directories — the 7.5 MB that #104 exists about — are **not in
  it**. `find` over the whole destination returns zero. The evidence held when written; the
  re-sync step in `PROTOCOL.md` fires on "a run completes" and this evidence was created by a
  *repair*.

- **The `eval/FINDINGS.md` index has a blank line between the `#105` and `#106` rows**, so under
  CommonMark the last six findings are a second, headerless table; and its stated range still says
  `#19-#110` while `#111` is present, as does the matching line in `AGENTS.md`. Not touched — this
  pass may not edit the findings log. Filed as **task 59**.

**Cleared — do not re-examine these.** The other 36 done tasks' evidence stands. Named where the
reason is not obvious:

- **Already self-correcting, and the chain is intact:** 15 → 18 → 20 (each records that the
  previous fix caused or mis-diagnosed part of the next); 16 and 22 both carry a dated inline
  CORRECTION of the same wrong claim; 07 is marked superseded-in-part in #66 itself; 26's
  not-done bullet was marked wrong by 52; 33's "the 23 files are NOT removed" was superseded by
  42, which says so; 37's `.agents/skills` premise was recorded as stale by 44.
- **Superseded, but the caveat lives in the authoritative file rather than the task string,
  which is correct:** 23's rounds read `wg-g4c` before the re-pack — the comparability note is in
  `eval/RUNS.md` and the ordering caveat in task 33, and the numbers 23 reports are reliability,
  not orderings, so they are unaffected.
- **Re-measured today rather than taken on trust:** 41's "no duplicate ids, no duplicate titles"
  holds at 58 tasks, not the 40 it was measured on; 47's 218-word shared block is still
  byte-identical in all four `eval/starters/*/AGENTS.md`; 43 and 51 were re-run green by task 52's
  gate sweep on 2026-08-23.
- **Measurements that do not decay:** 01-06, 08, 09, 12-14, 19, 21, 25 (aside from its citation),
  27, 31, 32, 34-36, 44, 49, 52. Each stores a measurement with its own controls; nothing
  recorded since contradicts one.

**What this pass says about the area:** the failure mode in `tasks/` is not stale conclusions —
the evidence discipline is working, and 36 of 42 closures are supported by measurements that are
still true. It is **stale pointers**: five broken finding citations, one wrong task id, one
permission keyed to a task id, one closure that named a state rather than a rule. Every one is a
reference that survived the thing it referred to.

**Method note:** `tasks/` is a shared queue that `tasks.py` resolves to the main checkout, but an
agent worktree may only edit its own copy. So the six corrections above are on this branch and
land when it merges, while tasks 57-59 were filed with `tasks.py` — which is what reserved ids
57, 58 and 59 rather than colliding on 54, the number a worktree-local guess would have taken.

---

## 2026-08-23 — the fat sections: is the doubling earned? (task 53)

**Looked for:** `prune_scan.py --only fat` had gone from ~12,053 tokens over 6 sections in the
morning to ~24,416 in the evening of 2026-08-22. One question per section: **would a fresh agent
reading this be better off reading half of it?** Not "is it bigger".

**Read:** all 14 reported sections in full — `AGENTS.md` "Rules" (1-16), `.claude/skills/audit-docs/SKILL.md`
§1, the five `tasks/` files (08, 24, 27, 34, 52), this log's 2026-08-23 `tasks/` entry, and
read-only: `README.md` §"THE RESULT" and §"In flight", `eval/judge/JUDGING.md` §"Validation gates",
`eval/IMPROVEMENTS.md` §"Verdicts", `DECISIONS.md` §"templates at each stack's best",
`eval/FINDINGS.md` §"Every finding". Also `prune_scan.py:cat_fat` itself, and every skill's
authoritative-file declaration.

**Measured: 28,852 tokens over 14 sections before, 27,212 over 13 after.** The task's own
baselines were 12,053 and 24,416; the number had grown again before this pass started. **The
total was not the target and it barely moved — 11 of 14 sections are keeps, and that is the
result.**

This entry is itself ~1,680 tokens and therefore joins the list, putting the measured total at
**28,890 over 14** — re-read from the tool after this paragraph was written, not before. Left as it stands rather than trimmed under the 6,000-character threshold: a
record of fourteen decisions with the reason for each is dense, not padded, and shaving it to
duck a threshold is the exact move this task says not to make.

| section | tok | decision | why |
|---|---|---|---|
| `AGENTS.md` Rules 1-16 | 2,945 | **split (done)** | The turn-ceiling worked example (232 of 250 turns) sat under rule 15, which is about mutants and variants and has nothing to do with ceilings. It is the evidence for rule 8's qualifier — *hold variables constant EXCEPT a ceiling that may be binding* — which otherwise ends on an abstract two-row table. Moved, one clause reworded so "the failure this rule exists to prevent" still refers to the right rule. No text cut: every rule here carries the incident that bought it, and that is what stops the next reader talking themselves out of it |
| `.claude/skills/audit-docs/SKILL.md` §1 | 1,639 | **split (done)** | Four things under one heading: how to run the sweep, why not to hand-roll it, the two controls to re-run if you change it, and the seven checks it deliberately omits. The last is the one a reader needs when *tempted to add a path check back*, and it was unreachable at the bottom of a 6,800-character section. Now three `###` subheadings, no content changed. Off the fat list entirely. Also added the missing **authoritative-file** line — it was the only one of seven skills without one, while itself being the skill that states the rule |
| `tasks/` 24, 34, 52, 27, 08 | 8,682 | **keep ×5** | Measured rather than assumed: **50% of those 34,731 characters is `established_by`** (17,341), which the prune skill protects outright, and task 52 is 90% evidence with a 719-character brief. The rest is the question the evidence answers — delete it and the answer has no question. And **none of it is ever loaded unless a reader opens that one ticket**: the queue prints one line per task. `(preamble)` is the wrong unit here — a whole task file is not a section a reader must scroll past |
| `CLEANUP-LOG.md` 2026-08-23 `tasks/` entry | 1,820 | **keep** | Its "Cleared" list is what stops the next pass re-reading 42 closed tasks. Compressing a pass record deletes exactly the negative results this log exists to hold |
| `eval/FINDINGS.md` "Every finding" | 3,994 | **must not touch — and the scanner should not have offered it** | `cat_fat` accepts `include_archive` and never uses it, so the archive is scanned by default while the banner printed three lines above says it is excluded. The largest entry in the list, 14% of the total, is the one section the skill names as never-prune. Filed as **task 60**. Not fixed here on purpose: the before and after numbers had to come from one unchanged instrument |
| `eval/judge/JUDGING.md` "Validation gates" | 2,271 | **split — filed, not done** | Six gates each with its own evidence table under one heading; nothing below the heading is addressable, by `--outline` or by a citation. Filed as **task 61**. Four agents were in `eval/judge/` |
| `README.md` "In flight" | 2,287 | **keep — left to its owner** | Status prose carrying the four-ways-to-read-one-field caveat and the #83 blindness warning. Its length is per-number qualification, which is the part that gets dropped first and costs the most |
| `README.md` "THE RESULT" | 1,698 | **keep — left to its owner** | The headline null, five instruments, plus the withdrawn/superseded distinction. Every sentence is a claim with its population attached |
| `eval/IMPROVEMENTS.md` "Verdicts" | 1,930 | **keep — left to its owner** | Ten rows, each a foreign practice with the measurement that accepted or rejected it. A table is already the compressed form; the only way to shorten it is to drop the measurements, which turns ten verdicts into ten opinions |
| `DECISIONS.md` "templates at each stack's best" | 1,586 | **keep — left to its owner** | A decision plus the survey that later corrected two of its examples. `AGENTS.md` protects the *reasoning* in this file by name |

**Cleared — looked at and judged sound, do not re-examine:**

- **`eval/PROTOCOL.md`, `eval/judge/RUBRIC.md`, `research/` and the other six skills have no
  section over 6,000 characters at all.** The doubling is not general document bloat; it is
  concentrated in four files, and three of those are `README.md`/`DECISIONS.md`/`IMPROVEMENTS.md`,
  where long means "a number with its population and its caveat attached".
- **`docstat.py --sweep` was run unpiped before and after: exit 0, clean over 131 docs.** Its
  `--renumbered` half reports three citations of `#117` that git history says now names `#118`
  (the finding is *"Fixing the collision is what created the dangling reference"*, and #117 today
  is a different one). Two were in files this pass was editing — `AGENTS.md:291` and
  `audit-docs/SKILL.md:40` — and are repaired. **`DECISIONS.md:281` is the third and is
  untouched**, because another agent held that file.

**What this pass says about the area:** the fat list conflates three different things — a section
that rambles, a section that is dense evidence in table form, and a whole file the scanner has no
heading to split on. Only one of the fourteen was actually a reader problem (the skill), and one
more was misfiled evidence rather than excess evidence. **~24,000 of the 27,212 tokens are earned**,
and the honest output of this task is the per-section reasoning above rather than the 1,640 saved.

<!-- CONTROL for task 131: a pull request touching no filtered path. Delete with the branch. -->
