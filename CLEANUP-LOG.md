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

## 2026-08-24 — refs, on-disk weight, and what today's changes falsified

Area chosen because every previous pass covered documents, `tasks/` or linters, and **nobody had
looked at the repository's own refs or its disk**.

### Cleared

- **109 stray `worktree-agent-*` local branches, deleted.** Left behind by the Agent tool's
  worktree isolation, one per dispatched agent since the project started. Each was checked
  individually before deletion — `git rev-list --count main..<branch>` — and **all 109 returned 0**,
  so none carried a commit absent from `main`. Deleted under that guard rather than by pattern, and
  the guard printed what it skipped: nothing.
- **2 merged task branches, deleted with `-D`.** The guard *correctly refused* these two: their
  commits are not ancestors of `main` because the pull requests were **squash**-merged, so the
  content is on `main` and the commits are not. That is the trap now written into the dispatch
  skill, and it is worth knowing that the obvious guard reports a squash-merged branch as
  unmerged. Verified by the authoritative signal instead — both pull requests `MERGED`, both remote
  branches already gone — then removed.
- `refs/heads` is now **`main` alone**, and `git gc --prune=now` leaves `.git` at **5.3 MiB**.

### Examined and judged sound — do not redo these

- **Disk is not a problem and needs no ticket.** `eval/runs/` is **4.5G** against the operator's
  100G cap. The working tree is 4.9G total and `.git` is 5.3M of it, so nothing is in git.
- **`eval/starters/` is 377M on disk and 4.3M tracked** across 232 files. The remainder is
  `ts/node_modules` (173M), `unity/build` (96M) and `unity/Library` (70M) — all gitignored, all
  regenerable, and `node_modules` is **load-bearing**: `parity_selftest` exits 1 without it
  (`.github/workflows/README.md`). Deleting the Unity pair would reclaim ~166M against 332Gi free.
  Not worth doing.
- **`eval/instrfollow/` is live, not dead weight.** 968K tracked, referenced from `README.md`,
  `DECISIONS.md`, `docstat.py`, `tokenvalue.py` and `tasks/39`, carries its own `DESIGN.md` and
  `RESULT.md`, and was touched on 2026-08-23. Checked because nothing in this log had ever
  mentioned it.
- **`README.md`'s "bounded contribution of 0.10"** (the judge-weight argument) is correct as
  written. It is the bound the argument uses — *even at the 0.10 it briefly carried* — not a claim
  that the current weight is 0.10, which the same file states as 0.00 twenty lines above.

### Found and fixed

- **`README.md` described `.coderabbit.yaml` as "exclusion-only".** False since the review
  configuration was rewritten on 2026-08-23 at the operator's request: it is `profile: assertive`
  with **9 path instructions that direct review**, including reviewing the starter trees and the
  readability of prose. Corrected in place. **Nothing could have caught this** — the sweep checks
  that names resolve, not that a description still matches the thing it describes.

### A note on method, since it happened twice in this pass

`grep -rln "x" --include=*.py` returns *"no matches found"* under **zsh**, which tries to glob the
unquoted pattern. Same family as #164, met twice within the hour of writing it. Quote every glob
passed to a tool that does its own matching.

## 2026-08-24 (second pass) — `research/`: 3,400 lines of prior nobody had audited

Chosen because an earlier pass recorded `research/` as having no coverage, and it is the largest
body of prose here that no pass had read.

### Examined and judged sound — do not redo these

- **`research/` is a LIVE document set, not an archive**, and that is a decision rather than an
  accident: it is absent from `ARCHIVE_PATHS` in `docstat.py`. So all 13 files are inside
  `--sweep` (207 docs, green) and inside `--withdrawn` (green) — held to `README.md`'s standard,
  not `tasks/`'s. This was the pass's main question and the answer is that the discipline already
  reaches here.
- **The prior/evidence framing is explicit and consistent.** `research/AGENTS.md` states
  `DECISION.md` is a prior and not evidence; `README.md` links it as *"the prior — the bake-off is
  the evidence, and it opens with a retraction"*. A live document that is openly superseded by
  measurement is not stale prose, and nothing here should be pruned on the grounds that the
  bake-off overtook it.
- **The file table in `research/AGENTS.md` is accurate** — twelve briefs `00`–`11` plus
  `DECISION.md`, and all thirteen exist.

### Found, and recorded rather than fixed

- **85 external URLs across `research/`, and nothing validates any of them.** The exclusion is
  deliberate and its reason is sound — `linkcheck.py` skips `http(s)` because the repository is
  offline-gradeable and a network check is a different tool with a different failure mode. **The
  reason lived only in that docstring**, so a reader asking *"is anything checking these?"* at the
  register — which exists to answer exactly that — found nothing. Added as a row to
  `.github/workflows/README.md`'s deliberate-exclusions table with the consequence stated: a rotted
  source still looks sourced, which is acceptable while `research/` is a prior and would not be if
  a measurement rested on one.

No tasks filed. Nothing here is dead weight, and the one gap was a missing row rather than a
missing check.

## 2026-08-24 (third pass) — which documents does a gate actually open?

Area chosen from the previous hour's discovery rather than from the rotation: task 147 found that
`docstat.py` had never read `.github/workflows/README.md`. The obvious next question — **what else
is invisible?** — had never been asked, and it is answerable in one command.

Read-only throughout: `docstat.py` was being edited by task 147 at the time, so nothing here
touched it.

### Found

- **Every `SKILL.md` escapes the flag census.** All 10 are inside `reference_docs()` and none is
  inside `project_docs()`, which is the corpus the *"flag matches no argparse"* check reads. Proved
  with one plant and a positive control: `` `--zzqwerty-nonexistent` `` in
  `.agents/skills/prune/SKILL.md` gives **exit 0**; the identical plant in `DECISIONS.md` gives
  exit 1 naming the flag. **Skills are where commands and flags are most densely written.** Filed
  as `tasks/149` at p2, with the trap that makes it awkward — `project_docs()` feeds an exact-count
  ratchet a larger corpus would move in the passing direction — copied in from `tasks/147`.
- **The hazard was documented inside the file that had it.** `_all_skill_files()`'s docstring says
  *"`glob` does not descend into dot-directories, and every skill here lives under one. A `**`
  spelling of this returned zero files while reporting clean."* — forty lines below
  `project_docs()`, which globs `**`. Added to **#170**, because it is #169's shape a second time:
  a fact in prose beside a predicate that contradicts it is not a check.

### Examined and judged sound

- **The dot-directory census is now complete and small.** 11 tracked `.md` files live under
  dot-directories: 10 skills and the CI register. The register is task 147's; the skills are
  `tasks/149`. **There is no third case** — this is the whole population, so the class is closed
  once those two land.
- **`.agents/skills/` is a symlink target with one real copy**, and `skill_layout_control.py` pins
  that five ways. Nothing here is duplicated prose.

### Method note

The first plant used the token `zzphantomflag` and came back green in **both** files — the word
`phantom` matches the checker's own deliberately-fake allowlist, so the probe was disarmed by the
thing it was probing. A neutral token separated the two files immediately. **Name a probe after
nothing the system knows about.**

## 2026-08-25 — the git hooks, and what they actually run

Area chosen because today's work took `gates.yml` from 32 gates to 46, and the hooks claim to run
that set. Nobody had read `.githooks/` in any previous pass. Two agents held `audio.py` and
`docstat.py` at the time, so the pass stayed clear of both — except where it could not (below).

### Found

- **`pre-push` runs 5 of 46 gates, and the register says it runs "the full `gates.yml` set".**
  `run-gates.sh` invokes a hardcoded list — `docstat --selftest`, `--findings`, `--withdrawn`,
  `tasks.py check`, and `--sweep` on push only. All five are documentation checks: no mutant
  suite, no tool selftest, no control. The failure direction is the bad one — a green pre-push
  reads as *"I have run what CI will run"*. Filed as **`tasks/153`** at p2, with the tension
  stated rather than assumed: making pre-push run all 46 is not obviously right, because a gate
  people skip is worse than one nobody added, and correcting the description alone is a complete
  answer.
- **The same table's `~13s` is `24.8s` measured.** Same row, same staleness, and it belongs to
  `tasks/129` — noted there rather than filed twice.
- **`main` was RED and I found it by running the hook, not from CI.** `docstat --sweep` was
  failing on **nine** foreign flags named in `tasks/149`'s own notes — git's `--ours`/`--theirs`/
  `--merge`/`--offline`, `gh`'s `--auto`/`--body`/`--body-file`, and `--doctool`/
  `--enable-unsafe-webgpu` from the tools its census covers. The agent working 149 is cataloguing
  candidate false positives, which is its job, and every bare backticked flag it records reddens
  the gate it is fixing. All nine are genuinely other tools', so the allowlist is the designed
  home; fixed and pushed.

### Worth carrying forward

**The rule added to the tasks skill this morning — sweep after every `add` and `note` — is written
for whoever is holding the queue, and an agent writing ticket notes is also holding it.** This is
the fourth red-on-ticket-prose today and the first that arrived through an agent rather than
through me. The rule reaches agents only if they read that skill; whether it should live somewhere
they cannot miss is a question for the next `audit-docs` pass, not a change to make from a cleanup
pass.

**The hook is the mechanism that would have stopped this reaching `main`, and it is not installed
by default** — deliberately, since `core.hooksPath` is shared config and arms every worktree at
once. So the thing that catches this class is a command the operator has to have run.

## 2026-08-25 (second pass) — `eval/judge/`: the tier that carries the whole weight

No previous pass had read `eval/judge/`, which is where the play-bots live — the tier weighted
**1.00**, with tier 1 a gate and tier 3 at 0.00. Rather than skim 1,100 lines of `bot_arena.py`,
the pass asked one question it could answer: **does the tier carrying the score have the coverage
the rules demand of it?**

### Found

- **The play-bot suite has 4 variant subjects for 36 criteria; the scene probe has 8 for 15.**
  Both run mutants and variants, both exit 0, both are gated. The difference is the variant half —
  the one `AGENTS.md` rule 15 says has found *every* false negative ever adjudicated here, sixteen
  of them in one sweep (#46). Filed as **`tasks/155`** at p2, framed as a question rather than a
  defect: four well-chosen variants can beat eight badly chosen, and the four here are pointed at
  real shapes. **Concluding that 4 is sufficient, with per-criterion reasoning, closes it.**
- **The asymmetry has a cause worth naming.** The scene probe's ticket carried the mutant/variant
  rule explicitly, because it was written into the brief; the play-bot suite predates that. The
  discipline was applied to new work and never retrofitted — which is what a rule written into
  tickets rather than into a gate will always do.

### A correction the pass made against itself

The first reading was *"32 of 36 criteria have no variant"*, and that is **wrong**. Each variant is
a whole correct game run against **all** criteria, so every criterion is exercised by every
variant. The honest metric is *how many correct-but-different subjects each criterion has faced* —
4 against 8, not 4 against 36. **A ratio computed from two counts whose units were never checked
is a number with no referent**, and it would have made the ticket claim a hole that does not exist.

### Examined and judged sound

- `bot_mutants.py` exits 0 with **36 criteria pinned in both directions, 4 variants, 3 session-lock
  controls, 0 expectations unmet**. Nothing here is unpinned.
- The session-lock controls include *"every session refused, forever → every criterion NOT
  MEASURED, not FALSE"*, which is the fail-closed shape rule 7 asks for, tested rather than
  asserted.

## 2026-08-25 (third pass) — the two improvement loops, which no pass had opened

Chosen because `IMPROVEMENTS.md` and `eval/IMPROVEMENTS.md` are named in `AGENTS.md`'s index as
live mechanisms and no previous pass had read either. Both agents were holding `eval/judge/` and
the harness, so the pass stayed clear of those.

### Examined and judged sound — the loop is IDLE, not stale, and the distinction took measuring

The obvious reading was *"last touched 2026-08-23, and two days of heavy evaluator work since —
therefore stale"*. **That is wrong**, and filing it would have been a spurious ticket:

- the last matrix is **`wg-g4c-2026-08-21`** (run names carry dates; **mtimes are useless here**,
  every directory was touched by today's censuses);
- the last iteration is **15, dated 2026-08-23** — *after* that run;
- `.agents/skills/refine/SKILL.md` fires the loop on *"a matrix has finished AND been evaluated"*.

So the loop is current with respect to its documented trigger and is idle because nothing has run.
**A mechanism with no recent entries is not evidence of neglect until you check what feeds it.**

### Found — the trigger under-describes the file

**Iterations 13, 14 and 15 were not run-driven.** Iteration 13 opens by reasoning from iteration
11a about a gate reading its function's input rather than its output — a grader change with no run
between. So the skill names one trigger and the file contains iterations that trigger does not
name.

It matters now because 2026-08-24/25 produced at least three changes with the exact iteration
shape — a hypothesis, a change, and a measurement that could have refuted it (the barred-aspect
pooling exclusion, the grader's declared-event transcription, the zero-aim contract). All three are
recorded in findings, tickets and `eval/RUNS.md`; **nothing is lost.** What is undecided is whether
the loop is meant to hold them, and right now that is settled by whoever happens to be writing.

Filed as **`tasks/161`** at p3, with the explicit note that **concluding the loop is run-only
closes it** and that today's changes must **not** be retro-filed as iterations — rewriting history
into a loop that did not produce it is the narration this project removes from live documents.

### Method note

`ls -dt eval/runs/*/` returned nothing under zsh and I nearly read that as "no runs". The directory
holds **30**. Two glob failures in two days from the same shell (#164); the habit that catches it
is asking *"is this answer the same for every subject?"* before believing it.

## 2026-08-25 (fourth pass) — the open queue's own collision structure

Chosen because the queue went from 5 to 12 tickets in a few hours, almost all filed by different
agents as consequences of first contact, and the prune skill's own rule is to check the queue
before filing. Nobody had audited it **as a set**.

### Found — four tickets serialise on one file, and one may reframe two others

`158`, `159`, `160` and `166` all edit `eval/judge/bot_mutants.py`. They cannot run concurrently,
so that is **four sequential rounds however they are ordered**.

Worse, the ordering is not free: **`166` says the bots locate a game's end from the state flag *or*
a `game_over` event and score it from the flag alone**, and `158` (tetris) and `160` (arena) repair
criteria sitting on top of that. If the two-signal defect is real it may change what those two
should do. Settling `166` re-scores every g2/g3/g4 submission, so *last* is defensible — but only
if `158` and `160` are **shown** not to depend on it. Written into `166`, with batching named as an
option, because `151`/`152` were merged into one branch for exactly this reason and it worked.

**No duplicates found.** `163` and `164` both concern scene thresholds but touch disjoint files —
`163` is a tier-1 game criterion refusing a scene, `164` is the probe's reliability filter — and
each carries its own reproduction. The rest are independent.

### Examined and judged sound

- **Disk is fine and the heartbeat's 7.9G was transient.** The tree is back to **4.9G**; the
  spike was agent worktrees, which are full checkouts and vanish on removal. The first scene run
  is **9 MB** — 8.8 MB of it artifacts. A scene matrix will not be what fills this disk.
- The queue lint is green, and `tasks.py check` passes on the merged tree with 154 done.

### Method note

The disk figure came from the hourly heartbeat and was **already stale when it printed** — worktrees
had been removed between the measurement and the report. A number sampled from a directory that
several processes are creating and deleting is a reading of the moment, not of the tree; the useful
version is measured when nothing is running, which is what this pass did.

## 2026-08-26 — `eval/PROTOCOL.md`, the launch document no pass had opened

Chosen because it is the `run-matrix` skill's authoritative file, is named in `AGENTS.md`'s index,
and no previous pass had read it. Both agents were holding `eval/judge/`, so the pass stayed clear
of that.

### Examined and judged sound — it is CURRENT, and the obvious suspicion was wrong

The pass expected staleness: scenes became launchable on 2026-08-25 and the harness became
selectable on 2026-08-24, and a launch document written before either would describe a narrower
world. It does not. **`scene` appears 10 times and the harness 3**, the file was touched
2026-08-25, and the pre-flight table carries two harness rows that did not exist two days ago —
*"state the harness, and check the arm it is not"* and *"on a non-claude arm, let `preflight()`
refuse"*.

**The two statements about what bounds a trial agree with `DECISIONS.md`**: `--max-turns 1000`, no
budget cap, and *"do not pass `--max-budget-usd`"* — which is #159's conclusion, correctly
propagated into the file an operator reads before launching.

### Found — a pre-flight check that cannot fire

One row of that table asks the operator to **verify `--max-budget-usd` in the live driver's process
list**. The standing configuration never passes it, and the same file says so 66 lines below. So a
check sits in a table headed *"run every check below; each has cost trials at least once"* and
there is nothing for it to find.

**The lesson is right and its instance is stale.** Read-at-import is real and applies to
`--max-turns 1000`, which every trial does carry. Filed as **`tasks/172`** at p3, with the trap
named: the row **below** begins *"Same mechanism as the cap"*, so deleting this one orphans its
antecedent — the renaming-breaks-references shape. The ticket also asks the same question of every
other row, with *"this was the only one"* recorded as a complete answer.

### Method note

The pass's first two probes both came back **sound**, which is the outcome that makes a pass feel
wasted and is worth logging as a result: *scenes are covered* and *the harness is covered* are
facts a future reader would otherwise re-derive. The find came from the third question — not *"is
it current?"* but *"does every instruction in it still have a referent?"* — which is a different
test and the one that caught something.

## 2026-08-27 — `eval/tools/`, the instrument nobody had opened

`eval/judge/` had a pass on 2026-08-25 and `eval/tools/` never had one, though it holds the 46
scripts that produce every number this project publishes. Read for one question: **what is
actually reachable from a gate?** A tool nobody runs is not merely idle — it is a check whose
failure nobody would see, which is the duty-cycle problem the CI tier was built to fix.

### Method note — the extraction was proved before it was believed

The census is `basename` against the concatenation of `.github/workflows/*.yml` and `.githooks/*`,
and a name-based match over shell is exactly the shape rule 12 keeps catching. So it was run first
against a case whose answer is written down: `AGENTS.md` says `skill_layout_control.py` pins the
layout gate red on all five ways the layout can break, and the census reports it gated. Only then
was the negative half read.

The second pass mattered too: the first cut listed 15 ungated tools and would have been a finding
about nothing, because `heartbeat.py`, `prune_scan.py` and `disclosure.py` are manual by design.
Partitioning by **what the tool is for** — a control exists to be a gate; a census exists to be
asked — took it from 15 rows to 4.

### Found — 4 controls no gate runs, and no register entry excusing any of them

Filed as `tasks/177` (p2). `.github/workflows/README.md` promises to record every gate left out
with its reason, and none of these 4 appears in it:

| tool | reachable from | measured |
|---|---|---|
| `fragment_control.py` | nothing at all | 1.1s, exit 0, 12/12 |
| `evidence_set_control.py` | nothing at all (one prose mention in a sibling docstring) | 1.5s, exit 0, 11/11 |
| `starter_gate_control.py` | `precampaign_smoke.py`, itself ungated | — |
| `disclosure_mutants.py` | `precampaign_smoke.py`, same | — |

`fragment_control.py` is the sharpest: its own docstring says its `whole_line` mutant is *"the
design that was tried first and measured as a complete false negative, so this control is what
stops it being tried again silently"*. Nothing runs it, so nothing stops that. At ~1s it is
pre-commit money.

**The ticket is the census, not the four rows.** `tasks/175` is the same defect found independently
one tool over (`ci_minutes.py --selftest`, in no hook tier), and repairing named instances leaves
the next one — the enumeration-versus-property failure the rule audit describes. What is missing is
a producer for *"which controls does no gate run, and which does the register excuse"*.

### Examined and judged sound

- **No dead tool.** All 46 scripts in `eval/tools/` have at least 2 referencing files; nothing is
  orphaned by name. The defect here is reachability from a **gate**, not deadness.
- **The two-tier split itself.** `ci_minutes.py` derives the hook list by *running* the hook rather
  than restating it, which is the right shape and is why `tasks/175` was findable at all.
- **`precampaign_smoke.py` being ungated is defensible** — it is a pre-run smoke suite, and running
  it per commit would be the wrong tier. What is not defensible is that its two children are
  reachable *only* through it while the register says nothing.

### Disk, examined and deliberately NOT pruned

The monitor flags gitignored build output as invisible to `git status`, so it was measured:
`eval/runs` is **4.5G**, and the largest single items are `node_modules` trees inside stored trial
work directories — 173M each for the two `t2_net__typescript_three` trials alone. `.godot` caches
are trivial (24K). Outside the repo, `~/game-research-work` is 175M. The live agent worktree under
`.claude/worktrees` is 3.0G, which is one full checkout and disappears when that agent finishes.

**Deleting the `node_modules` trees would be wrong, and the reason is #45.** They are
reconstructible from `package.json`, so the naive prune test passes — but #45 is precisely a
toolchain that vanished between building and grading, and six TypeScript submissions then scored
an identical 6/14 that read as a stack characteristic. A stored trial whose dependencies are gone
does not fail loudly on re-grade; it fails in a way that looks like a property of the stack. The
prune test that matters here is the log's own: *would removing this make a future wrong conclusion
possible?* — and for this specific class of file the answer is yes, with a numbered instance.

Not pressing regardless: 593Gi free against 7.9G used. Recorded so the next pass does not
re-derive it, and so nobody deletes them for space later without meeting #45 first.

### Not opened, and the next pass should take one

`eval/suites/` (the task prompts), `eval/wholegame.py` and `eval/runner.py` (the harness itself),
and the scene layer built 2026-08-25/27 (`eval/SCENES.md`, `scene_probe.py`, `scene_prompts.py`) —
which is new enough that no pass has read it and old enough now to have accumulated its own
corrections.
