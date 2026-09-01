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

## 2026-08-27 (second pass) — `eval/wholegame.py`, the harness no pass had opened

1,365 lines that build every trial, and no pass had read it. Read for one question: **which of its
21 CLI flags no longer earns its space?** A flag that parses and does nothing is the worst shape a
dead option can take, because it accepts input silently.

### Found — 5 flags bound to the code by a STRING, and one of them is an arm dimension

Filed as `tasks/183` (p2). `wholegame.py` reads `scenes`, `harness`, `turn_limit`, `only` and
`prompt_file` through `getattr(a, "<name>", <default>)` rather than `a.<name>`. The defensive form
buys nothing: the four subcommands that reach this code — plan, build, evaluate, report — are built
in **one loop** at line 1282 with every one of those flags inside it, and the only other subparser,
`concurrency-check`, dispatches elsewhere and never reaches `cmd_build`. No legitimate call can find
the attribute missing.

What the default *can* do is absorb a rename. `getattr(a, "harness", None) or HARNESS` would, if the
dest ever moved, build every trial with the **default harness** — silently, with no crash and no
warning, producing a completed run whose recorded arm is wrong. `eval/RUNS.md` records the harness
as an arm dimension, and the second harness exists precisely so runs can be compared across it.

**This is rule 12 in code rather than in a check:** the address is a string, the string is not
asserted against the thing it names, and the failure is silent.

### Examined and judged sound

- **No dead flag.** All 21 are read and all 21 reach behaviour. 14 are documented in the four main
  docs; the 7 that are not (`--judge-model`, `--k`, `--no-audio`, `--no-judge`, `--prompt-file`,
  `--seed`, `--starter`, `--turn-limit`) are development and repair options rather than run
  configuration, and `--turn-limit`'s own help text points at `AGENTS.md` rule 8 for why it must not
  be used to match an earlier run's ceiling.
- **`--scenes` defaulting to NONE** while `--games` defaults to all is deliberate and the reason is
  written at the declaration and again in `select_tasks()`: a scene is not a cheap addition to a
  game run.
- **The `$TMPDIR` comment above `default_work`** gives BOTH reasons the work root is what it is, and
  says why it gives both — "a comment giving one of two reasons is how the next person simplifies
  this back into /tmp". That is #45's evidence and must not be pruned.

### Method note — the census was wrong twice before it was right, both times rule 12

The first pass matched `args.<dest>` and reported **14 of 21 flags never read**, including
`--run-dir` and `--stacks`, which the standing build command demonstrably uses. The namespace is
bound to **`a`**, not `args`. The second pass matched any `\w+\.<dest>` and reported **3** never
read — `harness`, `scenes`, `turn-limit` — which are read by `getattr` with a string and are
invisible to an attribute regex. The third pass found them, and the thing the first two were wrong
about turned out to BE the finding.

**Both wrong answers were uniform across a population that should have varied**, which is rule 9
pointed at my own instrument, and it is the third time in this session I have hit that. The reason
it kept getting caught quickly is that a known-good row was available each time: I know `--run-dir`
works and I know `--scenes` works, so a census reporting them dead is reporting itself.

## 2026-08-27 (third pass) — `eval/runner.py`, the other half of the harness

1,136 lines, and the pass on `wholegame.py` earlier today left it as the obvious pair. Read for one
question, chosen because #194 had just established that stored records are what every census reads:
**what does the runner WRITE into a record, and is any of it read by nothing?**

### Method note — the census was wrong once, and the flaw was mine again

The first cut asked *"does any file OTHER than `runner.py` mention this field name"* and reported 3
dead fields: `corr`, `duration_ms`, `n_tasks`. Excluding `runner.py` from its own consumers is the
error — `corr` and `n_tasks` are returned by `paired_delta()` and consumed at line 984, in-process,
inside the same file. Live, both of them.

The extraction was validated first on two rows whose answer is known — `cost_usd` at 131 consumers
and `terminal_reason` at 124 — which is why the three zeros stood out as worth checking rather than
worth believing.

### Found — one field genuinely read by nothing, holding 4.4 hours of evidence

Filed as `tasks/186` (p3). Both harnesses time a trial, under different names, and only one is read:

| written by | field | consumers outside its own module |
|---|---|---|
| `wholegame.py:450` | `wall_s` | **6+** — `RUBRIC.md`, `capability.py`, `bot_mutants.py`, `BAKEOFF.md`, two findings files |
| `runner.py:726` | `duration_ms` | **0, anywhere** |

`agent.duration_ms` is positive in **47 of 55** non-whole-game trial records and **0 of 84**
whole-game ones; min 36s, median 332s, max 659s, **4.4 hours** in total. `ci_minutes.py`'s
`run_duration_ms` is GitHub Actions' field for a workflow run and unrelated — checked, not assumed.

It is #83's shape: a capture nobody has read since 2026-08-12, of a quantity `eval/RUNS.md` treats as
a **comparison metric**. A comparison spanning the two harnesses must know the two names are the same
thing, and nothing says so — not the names, not the docs, not a producer. Live rather than
historical, because a second harness became a recorded arm dimension on 2026-08-25.

### Examined and judged sound

- **`paired_delta()`** — `n_tasks`, `mean`, `se`, `ci95` and `corr` are all consumed by the report at
  line 984. `corr` is `nan` for fewer than 2 common tasks and the caller handles it.
- **Field coverage otherwise.** Of 36 record fields the runner writes, 33 have consumers outside the
  module, several with 100+ — the record is read, not written into a void.

### CORRECTION, 2026-08-27 - this pass's finding was wrong in both halves (#203)

`tasks/186` was worked and the agent re-derived the claim from the artifacts. The entry above is left
standing with the correction beneath it rather than edited, because what a pass concluded is the
record.

- **`duration_ms` is not a second name for `wall_s`.** It is a **third quantity held by a different
  party** - the agent CLI's report of its own internal run, nested inside the timing script's
  stopwatch. Over 157 paired observations `wall_s - duration_ms/1000` is min 0.9 s, median 1.1 s, max
  6.5 s, negative on none. Additive overhead, not a naming inconsistency - and "reconciling the two
  names" would have destroyed a real nesting.
- **The population was undercounted, by a trap this repository has already numbered.** This pass
  globbed `eval/runs/*/trials/*.json` and reported 47 of 55 records / 4.4 hours. The true figures are
  **71 of 71 and 7.36 hours**: two run directories are wrappers holding others, which `#126` and
  `#127` record by file and by number. Reproduced at merge time - shallow 139 files / 47 carrying,
  deep 163 / 71.
- **The self-report is not absent from the live harness either.** `wholegame.py` leaves it in
  `artifacts/<tid>/agent_result.json`, present in 86 of 91 whole-game records.

**No shipped walker was at fault** - every one that gates something already handles the nesting. The
defect was in the one-off shell pipeline this pass wrote to look at the tree, which is the population
no gate covers.

> **A cleanup pass's own census has no control, and it is the measurement most likely to be believed,
> because it is the one that becomes a ticket.** Reconcile a hand-rolled walk against a shipped
> walker over the same tree before filing; the disagreement is the control.


### Not opened, and the next pass should take one

`eval/suites/` (the task prompts — note that editing one is a regime boundary, so a pass there files
tickets and changes nothing), and the scene layer, which has now absorbed five repairs in three days
(`tasks/162`, `163`, `164`, `174`, `178`) and has never been read as a whole.

## 2026-08-28 — the scene layer, read whole after five repairs; nothing found, and the reason is the finding

4,168 lines across `eval/SCENES.md`, `suites/scene_prompts.py`, `judge/scene_probe.py` and
`judge/scene_mutants.py`. It had absorbed `tasks/162`, `163`, `164`, `174` and `178` in three days and
no pass had read it as a whole. Read for one question: **does the documentation still agree with the
code after five repairs?**

### Cleared — no defect found, and the checks that could have found one were run

- **`prompt_guard.py` exits 0.** That is the shipped gate relating `SCENES.md` to the rendered
  prompts, and it is what a coherence question about this layer should be asked through.
- **Every `UPPER_SNAKE` constant `SCENES.md` names exists.** `MIN_LAYERS`, `MIN_PAIRS_PER_LAYER`,
  `RUBRIC_TERMS` (`tools/prompt_guard.py:77`), `WEIGHTS` (`judge/evaluate.py:84`); `RLIMIT_CPU` is
  Python's own and legitimately foreign, like git's flags in `FOREIGN_FLAGS_EXACT`.
- **`SCENES.md` does not restate the 660-tick count** that `scene_prompts.py` owns — correct, and the
  opposite of the defect this log usually finds.

### Method note — BOTH novel checks reproduced a documented-bad method, and one was documented in advance

This is the pass's actual result, and it is about the passes rather than about the scene layer.

1. **Constants.** The first census searched `eval/*.py eval/**/*.py` and reported `RUBRIC_TERMS` and
   `WEIGHTS` defined nowhere. Git's pathspec is fnmatch: `*` does not cross `/` without `:(glob)`
   magic, so `eval/**/*.py` never matched `eval/tools/prompt_guard.py`. **Third cleanup census in a
   row wrong on its population** — after `--sweep`'s flag census, the `runner.py` field census, and
   now this.
2. **Criterion ids.** The second census harvested `word.word` in backticks and reported 7 missing —
   of which `static.collect`, `field.run_field` and `anonymise.find_stack_names` are
   **module.function references**, not criteria. `.agents/skills/audit-docs/SKILL.md` already says,
   in the entry recording why criterion-id checking was never implemented: *"the id set cannot come
   from string literals in `judge/*.py` — that pattern harvests `re.search` and `aspects.py` as
   criterion ids"*. **The documentation predicted this pass's error before the pass made it.**

> **A cleanup pass invents a check per area, so it is the place where a known-bad method gets
> re-invented.** The gap it looked at is a recorded deliberate exclusion; the method it reached for
> is the one the exclusion warns against. **Read `audit-docs`'s exclusion list before building a
> novel doc check** — it is a list of methods already tried and rejected, not only of gaps.

Neither wrong census was filed, because each was validated against a case whose answer was known
first. That is the only reason this entry says "nothing found" rather than carrying two false
findings — and it is `#203`'s lesson from six hours ago, applied.

### Not opened, and the next pass should take one

`eval/suites/wholegame_prompts.py` and the game prompts (editing one is a regime boundary, so a pass
there files tickets and changes nothing), and `research/`, whose last pass was 2026-08-24 and which
`.github/workflows/README.md` records as having 85 unvalidated external URLs.

## 2026-08-28 (second pass) — `eval/suites/wholegame_prompts.py`, the file the previous pass pointed at

The 2026-08-28 scene-layer pass ended with "Not opened, and the next pass should take one:
`eval/suites/wholegame_prompts.py` and the game prompts". This pass read that file whole — all 698
lines — plus its seven importers, and the queue was checked for duplicates first (135, 136, 141 all
touch this area; all closed).

### Cleared — the structures most likely to rot are the ones that were checked, and they are sound

- **One `_preamble(stack)`.** The #41 shared-preamble defect — four stacks carrying near-copies that
  drifted — was repaired by making the preamble a single function. Verified across all four
  `g1_pong`/`g2_tetris3d`/`g3_arena`/`g4_platformer` builders: none carries its own preamble text.
- **`EVENTS` is parsed from the prompt blocks at import, fail-closed.** No fence, unreadable line,
  no names, or duplicate raises at import; `set(EVENTS) != set(TASKS)` also raises. This is the
  single-address discipline tasks/151 bought after audio.py's transcription drift — the event-name
  address is the block itself, and the parser is the only thing that re-derives it.
- **The INPUT_TYPE/STATE_HOME deletion (task 141) is documented in place** with its reasoning and
  names its producer, `prompt_guard.py --identity`.
- **`rendered/` snapshots have a live reader** (`prompt_guard.py --snapshot/--diff`) and recent
  maintenance (tasks 166, 143).
- **The probe contract is not duplicated into the scene layer.** `scene_prompts.py` imports the
  vocabulary dicts from `wholegame_prompts` and re-exports them ("one concept, said in four [stack
  wordings], copied zero times", its own docstring), rather than holding a second copy.
- **The G1 state-field wording survived the rally.counts repair.** The prompt defines `rally` as
  "the number of consecutive paddle hits since the last point" — a scoring hit IS the point, so the
  field's definition and the criterion's non-scoring domain agree without edit. Checked because
  tasks/188 rewrote the criterion's prose in two documents; neither needed a third repair here.

### Found — one defect, filed as task 194

`prompt_guard.py:44` defines its own `STACKS = ("rust", "ts", "unity", "godot")` two lines below
`import wholegame_prompts as W`, and never reads `W.STACKS`. Every other consumer takes the tuple
from `wholegame_prompts` (`wholegame.py` via `P.STACKS`; `scene_prompts.py` by import and
re-export). prompt_guard is the tool that asserts prompt identity across stacks, and the population
count it prints is derived from its own copy — so a fifth stack added in `wholegame_prompts` leaves
it silently checking the old four and printing a clean-sounding wrong number. Rule 12's
assert-them-equal discipline, applied to a value instead of a path. **Not fixed here: this pass's
brief is a regime-boundary-adjacent area, and the repair belongs behind a ticket where its selftest
can be written.**

### Examined and judged too thin to file

- `wholegame_prompts.py`'s docstring says "Companion to `prompts.py`" and does not mention
  `scene_prompts.py`. The relationship is documented from the other side (scene_prompts' docstring
  has a "WHY THIS IS A SEPARATE MODULE" section), and `prompt_guard.py --identity` counts both
  families. A third sentence in a third docstring would restate what the module graph already says.
- `SPRITE_NOTE`/`THREE_D_NOTE`/`RENDER_NOTE`/`AUDIO_NOTE` consumers: each used by exactly the games
  its comment names; each defined for all four stacks.

### Disk answer carried over from the pass's start

The repository's 5.0G is `eval/runs/` at 4.5G — stored trial evidence, protected. Git's own
size-pack is 4.84 MiB; agent worktrees 15M; `~/game-research-work` 175M. Nothing prunable.

### Not opened, and the next pass should take one

`eval/judge/aspects.py` (749 lines) — the aspect/weighting layer, which consumes the prompt
vocabulary (`import wholegame_prompts` at :654) and has never been a pass's area; this log names it
only in passing. Same regime caution as this pass: it is the instrument, so a pass there reads and
files tickets and changes nothing.

## 2026-08-28 (third pass) — `eval/judge/aspects.py` (749 lines, read in full)

The pass the second pass's pointer asked for. The aspect/weighting layer had never been an
area. Read in full, plus its selftest (aspects_selftest.py, ~420 lines) and the guard-side
of evaluate.py. Regime caution held: this is the instrument — read, file, change nothing.

### Found — filed as tasks 198 and 199

- **198 (p3): no check catches an aspect brief that promises evidence its pack does not
  carry.** The original FUN_FRAMES defect (notes inherited from FUN describing
  `telemetry.json` while `sees="frames"`, aspects.py:380-391) was caught by hand and
  pinned by nothing: `check_control_briefing_is_identical` compares only the blind-spot
  paragraph TAIL, byte-identical by construction. Measured in-pass: the reconstructed
  mutant `replace(ASPECTS['fun_frames'], notes=ASPECTS['fun'].notes)` passes all six
  checks with 0 problems while the mutant brief contains `telemetry.json`, and the
  10-entry `mutants()` list has no member of this class. The ticket carries the red state
  as a measurement, the property to state (brief names no evidence its `sees` excludes),
  and the rule-12-corollary constraint on the check's expectation.
- **199 (p5): `aspects.py:719` says `scene_runner_control.py --paths` "prints the
  runner's 3"; the tool prints 6 guarded routes** (P1-P6, measured in-pass). The
  docstring's own "6 paths applicability is called from" enumeration was separately
  verified TRUE (evaluate.py:345 documents the tier-2 dispatch's transitive coverage;
  5 grep-level call sites cover the 6 routes) — recorded in the ticket so nobody
  re-derives it. Only the pointer's count is stale.

Also filed in-pass, from task 197's handback rather than this area: **200 (p4)** —
run-matrix and evaluate-run skills invoke `verify_blind.py` bare, which has exited 2 since
the tool's first commit; the two skills and README's fence also disagree about frame.

### Examined and judged sound — recorded so the next pass does not redo it

- **The "6 paths" claim in the applicability docstring** — true; see 199.
- **`INSTRUMENTS` vs `INSTRUMENT_CLASS` in the selftest** — a deliberate mirror that
  forces a selftest edit when an instrument is added (its own comment names the policy,
  aspects_selftest.py:337-339). Not a second source of truth drift risk; it is the
  tripwire.
- **All five derived sets** (`SCORED_ASPECTS`, `CONTROL_ASPECTS`, `GAME_ASPECTS`,
  `SCENE_ASPECTS`, `CROSS_STACK_BARRED`) are comprehensions over the one registry —
  #38's shape held everywhere it applies here.
- **`task_class()` three-valued + `_ID_SHAPE` fallback** — the fallback is corroborated
  against the suites on all real ids by the selftest, and the synthetic-`g9_probe`
  fixture case is named as why it exists.
- **`FRAMEWORK_FLUENCY` on `SCALE` rather than `SCENE_SCALE`** — deliberate: it sees
  code and asks a code question (which engine APIs appear); its two scene peers ask
  about the rendering and use the scene scale.
- **`AUDIO` defaulting to game class** — the SCENES block states scenes have no sound,
  and `applicability()` refuses audio on a scene task.
- **`sys.path.insert` in `_task_classes()`** — lazy, cached, and the same house pattern
  as `wholegame.py:57-60` (which inserts four paths) and `runner.py:76`. Not filed.
- **The selftest's 10 mutants and 4 variants** — every one is a removal or a
  third-value variant in the rule-15 sense; none is a mere restatement. The gap is 198's,
  and it is an ABSENT check, not a weak one.

### Disk

Unchanged from the second pass's answer earlier today: repo 5.0G, `eval/runs/` 4.5G of it
(stored trial evidence, protected), git size-pack 4.84 MiB. Nothing prunable.

### Not opened — the next pass should take one

`eval/judge/field.py` — **2157 lines**, the largest file in the judge tree (packer, run
harness, `applicability` caller at :1465 and :2058). It has never been a pass's area
either, and it sits directly upstream of everything this pass read. Same regime caution:
the instrument, so read and file, change nothing.

## 2026-08-28 (fourth pass) — `eval/judge/field.py` (2157 lines, read in full)

The pass the third pass's pointer asked for. The packer, run harness and gates module for
the subjective layer — the file the #83/#131/#137 leak lineage lives in, and `build_pack`
(cx 241 in the 2026-08-23 instrument pass) — read in full, plus greps for every
caller claim the file or its neighbours make. Regime caution held: read, file, change
nothing.

**Looked for:** one question, from this log's own framing of the file: **does the packer's
record of what it does match what it does?** Every docstring and comment that claims a
mechanism — wired into the path, refused, pinned, recorded — was checked against the code
and the callers, not against the neighbouring prose.

**Read:** all 2157 lines; `blurb_selftest.py`'s pin sites for `judge_prompt`;
`field_sweep.py`'s call sites; `eval/tools/frame_parity.py` (header and `geometry()`);
`JUDGING.md:895-924`; `DECISIONS.md`'s money-figure section; `git log -S "pack_parity("`
over `field.py`; a walk over every stored usable `fun_frames`/`audio` judge round with a
`files_opened` capture.

### Found — filed as tasks 201, 202, 203

- **201 (p3): `JUDGE_PROMPT` tells every judge to "read the code in A/ through H/",
  whatever the pack carries.** `_brief` was repaired for exactly this — its `looked_at`
  map keys the closing instruction on the pack's `sees`, and its own comment names the
  failure ("I could not find the source" read as a finding about the submission) — but the
  `claude -p` prompt, the FIRST text the judge reads, kept the hardcoded wording, and
  `blurb_selftest.py` pins it only for state-dependence, never for evidence agreement.
  Measured latent null recorded in the ticket: **0 of the 14 captured rounds** contain a
  read of evidence the pack does not carry.
- **202 (p3): the live documents describe a geometry gate the code deliberately
  replaced.** `JUDGING.md:910-918` says `pack_parity` runs inside `build_pack`, that mixed
  geometry is **refused**, and that the remedy for the 420x640 trial is to re-film and
  re-judge; `frame_parity.py:6` carries the refuse claim. The code measures geometry per
  label from the FIRST frame and annotates the brief — refusing recorded as wrong in
  `build_pack`'s own comment. `pack_parity` has no caller at any committed revision. Two
  real losses ride with the stale prose: an uncalled function whose docstring claims path
  membership, and `uniform_within_submission` — which `frame_parity.geometry()` computes
  and nothing on the current path can see.
- **203 (p5): the module docstring's `pack` usage omits required `--aspect`** — the
  documented invocation exits 2; the task 200 class.

### Cleared — examined and judged sound, so the next pass does not redo it

- **The judge spend ceiling is DECIDED, not overlooked.** `run_field` passes
  `--max-budget-usd 12.0` on every judge call and `field_sweep.py` exposes
  `--per-call-budget` with the same default. The money-figure decision in `DECISIONS.md`
  holds it explicitly: retained at its stored value for comparability with the rounds on
  disk, since changing what the judge is told needs a pre-registration of its own. Not
  re-opened.
- **`ceiling()` superseded by `separation()` by design**, kept for the stored rounds and
  marked superseded in its own docstring; the #74/#58 reasoning is in place.
- **`separation()`'s free parameters are stated and measured** — the SD convention with
  its three-convention comparison, `marginal_pairs` exposing boundary pairs, the low-n
  gate. The #92/#123 discipline, applied before this pass reached the file.
- **`CHANGED.txt`'s header is concatenated outside `_text`** — the one exception to "one
  function for every piece of text this pack writes"; the headers are harness constants
  with no submission content. Harmless as written.
- **`files_opened` counts Read/NotebookRead only; `tool_calls` keeps every targeted
  tool_use**, Bash commands and Glob patterns included, so the raw audit store is complete
  and only the convenience count is narrower.
- **Two loud-not-stored failures, noted and not filed:** a missing/unreadable MAPPING file
  or a mapping without `game` raises before any spend rather than returning a stored
  refusal; and `packcheck`'s per-game line omits `frames_mismatched`, so a frames-only
  defect prints `clean=False` with no cause named. Both fail closed and cost a traceback,
  not a result.
- **The blinding machinery itself** — `blind_extensions`' closed-class membership rules,
  the manifest-mapped `CHANGED.txt`, the mapping-outside-pack refusal, the zero-mapped-row
  fail-closed guard, the empty-evidence per-label refusal — read whole and judged sound;
  each carries its measurement and its failure mode at the site. The leak lineage does not
  continue in this file.

### Method note

The first scan of the stored rounds classified reads with `startswith('frames/')` and came
back reporting non-frame reads in EVERY round — the stored targets are absolute
`/var/folders/...` paths, so the filter was wrong everywhere at once, which is rule 9's
tell aimed at my own instrument, the fourth census in this log to fail that way. Re-pointed
at the two forms the corpus actually stores (absolute and `./`-prefixed), the same walk
reported zero. And `git log -S` over `pack_parity(` returning only the initial squash is
what dated the JUDGING.md claim: no committed revision ever called it, so the "wired into
the path (2026-08-21)" paragraph describes working-tree state that no commit carries.

### Not opened, and the next pass should take one

The stored-round analysis half of the subjective layer — `eval/judge/field_ranks.py` and
`field_sweep.py`, the consumers of what this pass's file produces — and `eval/suites/`
(the game prompts), which the 2026-08-28 second pass's pointer still names; regime-boundary
rules as before.

## 2026-08-28 (fifth pass) — the stored-round analysis half: `eval/judge/field_ranks.py` (743 lines) and `field_sweep.py` (619), both read in full

**Looked for:** the question the fourth pass left on this half — does the analysis layer's
record of what it does match what it does, and does anything here still earn its space —
plus the one class the fourth pass's own finding (#210) makes me read for everywhere now:
a mechanism claim no caller backs.

**Read:** both files whole; `assert_poolable`'s guard site and every selftest pin; the
gate-pairing loop and the `[have]` resume path in `field_sweep.main`; the stored corpus for
the one field the pair depends on and never reads — top-level `run` in 30 of 30
`wg-aspect-reliability` rounds (all one run), 0 of 10 `wg-tetris-judge-2026-08-17/pre`
rounds (they predate the provenance fix); the whole tree for callers of
`warn_rounds_without_provenance` (code and markdown); `CLEANUP-LOG.md` coverage of
`judge_ledger.py` and `sequential.py` (none).

### Found — filed as task 205 (p2)

**The pair never asks whether the rounds they pool or pair share a run.**
`field_ranks._by_stack` joins every round in a directory by submission id across all
rounds; `assert_poolable` partitions by aspect class and nothing else. `field_sweep`
accumulates rounds into `--out` across invocations by design, keyed by a filename with no
run component, and its gates pair on game+aspect equality only — so the designed `[have]`
resume path re-run against a different stored run produces order-invariance and
reproducibility gates across two fields, a directory valuation summing both, and a
directory `field_ranks` then pools into per-submission means across different games' work.
This is #70's join and #80's third namespace at the analysis layer, in the tool
`DECISIONS.md` names as THE producer for tier-3 figures and the withdrawn register points
operators at. #80 fixed the capture (every round carries `run` since 2026-08-22); no
consumer reads it — the same gap the files_opened capture had before #83 asked its
question. Folded into the same ticket: **`warn_rounds_without_provenance` has no caller
anywhere** — cited in #86 and task 19's record as a mechanism that reports, measured once
by calling it by hand, and invoked by nothing since; it is the absent-data half of the same
check (report rounds that cannot answer the run question at all). The guard must
warn-absent rather than refuse when `run` is missing, or the tool becomes unable to read
the tetris-judge corpus the withdrawn register cites.

### Cleared — examined and judged sound, so the next pass does not redo it

- **`assert_poolable` is a model of guard placement** — at the resource (`figures`), not
  beside one caller (rule 13 argued in its own docstring); unknown ids refused even alone,
  with the PR #24 review catch recorded at the pin.
- **Barred-aspect reporting**: per-stack means in alphabetical order, never sorted by
  value — the comment names the ranking the bar exists to withhold; the bar appears in the
  header, on the per-aspect row, and in the refusal, so a reader reaching one number
  directly still sees it.
- **`_round_stats`' `len(v) == 2` gap filter**: a stack with three submissions silently
  contributes no gap. Same principle as #102 — a gap that is not uniquely defined is
  skipped rather than approximated — and the per-stack line still prints every arm. Cell
  shape is 2. Not filed.
- **No-retry resume semantics** in both sweep modes: a stored unusable round is loaded as
  `[have]` and never re-run. Deliberate and fail-visible (`calls_usable` vs
  `calls_attempted`, the `[FAIL]` line); the alternative is re-spending on a judge call or
  hand-deleting a stored round, and the file's own docstring argues judge calls are cheap
  but stored rounds are the record.
- **The #159 discipline is total in `field_sweep`**: retired `--max-cost` kept as a
  refusal with the reason on the flag, `Bounds` documented as finite-by-construction,
  `stopped_by` written into every summary, the two tokval numbers named per #119, and
  `SUMMARIES` asserted equal to `judge_ledger.SUMMARY_STEMS` at import (rule 12 in code).
- **`_judge_round` returns its own cost** — the docstring records the under-count it
  replaced (~22 tokval of probe rounds never counted) and why a counter that under-reports
  is worse than none.
- Both selftest/import baselines green at HEAD `59732aa` (`field_ranks --selftest`
  0 unmet; sweep import with its `SUMMARIES` assert).

### Method note

The cross-run question came from asking of `_by_stack` what #70 asked of pack labels:
what is the join key, and what namespace is it unique within? The submission id is unique
within a run and nothing else in the file constrains the directory to one run — the same
one-line question the fourth pass applied to `pack_parity`'s callers. The corpus
measurement (30/30 vs 0/10) was run before filing, because a guard that refuses on absent
`run` would break the tool against the withdrawn register's own "instead" commands.

### Not opened, and the next pass should take one

`eval/judge/judge_ledger.py` and `eval/judge/sequential.py` — the two modules
`field_sweep` imports and this log has never opened (`judge_ledger` decides what a
summary IS and is the tokval producer every money-figure citation names; `sequential`
holds the sampling protocol the sweep executes). Neither appears anywhere in this log.

## 2026-08-29 (sixth pass) — the ledger and the sampling protocol

**Area:** `eval/judge/judge_ledger.py` and `eval/judge/sequential.py`, the fifth pass's
named pointer — the two modules `field_sweep` imports that this log had never opened.
Both read whole (469 + 235 lines).

### Found

- **A citation that resolves and means something else** (`#118`'s own shape):
  `judge_ledger.py`'s docstring cited "FINDINGS #119" for the
  ceiling-counter-read-as-spend story; #119 has been the withdrawal-register finding
  since the 2026-08-23 renumbers, and the story lives in **#121** (`limits-and-cost.md`,
  same numbers: 25.55/21.05, 5 directories, $69.93). **Fixed in place** (one line,
  citation only — never renumber the finding), sweep and selftest re-run green.
- **The same docstring carried a stale count with its producer one command away**:
  "Measured over the 11 stored sweep directories ... 69.94 tokval" against a 2026-08-29
  read of 12 directories / 69.93. Rewritten with the read date and the producer command
  rather than bare digits.
- Both latent defects in the ledger itself filed as **task 206**: a round with no
  `cost_usd` counts as 0.00 silently (`_cost = float(j.get("cost_usd") or 0.0)` — the
  fallback shape the module's own `read_counter` refuses one function up), and
  `explain_gap`'s subset-sum fallback is 2^n, reachable from `--tree` on a future
  ~30-round directory with a positive gap and no clean mtime split.

### Cleared — examined and judged sound

- **`sequential.py` is not unpinned.** The pointer's suspicion ("a protocol with nothing
  calling it") is answered by `sequential_selftest.py`: 6 simulation checks — clear
  ordering, true tie, saturated→`TIED_EXACT`, near-tie not called TIED, budget-cut
  reports NOT RESOLVED never a tie, failed runs never count as observations — gated at
  `gates.yml:342`. What it does not pin directly (Wilson's half-widths at the four n the
  comment cites; the hardcoded `n_for_statistical_tie: 96` going stale if TIE_MARGIN
  moves) is noted and deliberately NOT filed: the simulations constrain the interval
  end-to-end and the 96 is derived in the adjacent comment; a pin would be nice-to-have.
- **The corpus the ledger walks is clean on the latent path**: 97 stored rounds, 0 with
  a missing or null `cost_usd` (measured, not assumed).
- **`--tree runs/` today**: 12 director(ies), 97 stored rounds, field 334.41 tokval,
  5 counters under-report by 69.93, exit 0, 2.3 s. The pre-directory reading AMBIGUOUS
  with one carried round is the designed `cp` case — the mtime split correctly refuses
  to be evidence, and selftest case 8 pins exactly that shape.
- **`is_summary`'s prefix rule, the canonical-only counter read, MIN_SPLIT_S's
  copy-proofing, and the two-numbers-never-one split**: each carries its reasoning in
  place and a pin; `field_sweep`'s import-time `SUMMARIES` assert holds the stem set
  equal across the two modules (rule 12 in code). `Pair.check`'s ORDERED-before-TIED
  precedence is correct by inspection and exercised by simulations; `winner`'s
  `rate or 0` dead branch (ORDERED implies n ≥ 4 implies rate not None) is harmless.

### Method note

The pointer came from the import graph: what does the instrument I just read actually
pull in? The citation check that found the #119→#121 drift was the same question the
fourth and fifth passes applied to code — every name in a claim, resolved against what
it names today rather than when it was written. `docstat --renumbered` did not flag
this one; the citation was written fresh, and only reading the finding beside the claim
separates those.

### Not opened, and the next pass should take one

`eval/judge/paired_verdicts.py` and `eval/judge/capability.py` — the producers the
withdrawn register's "instead" commands point operators at (`WR-paired-verdict-tie`,
`WR-paired-evidence-diff`, `WR-capture-default-62-of-68`). A stale citation is a
wrong door; a wrong producer behind a corrected citation is the room behind it.
Neither appears in this log.

## 2026-08-29 (seventh pass) — the rooms behind the register's corrected citations

**Area:** `eval/judge/paired_verdicts.py` (463 lines) and `eval/judge/capability.py`
(766 lines), both read whole — the sixth pass's named pointer, and the producers three
withdrawal-register entries point operators at (`WR-paired-verdict-tie`,
`WR-paired-evidence-diff`, `WR-capture-default-62-of-68`). The sixth pass's framing held:
a stale citation is a wrong door; this pass opened the rooms.

### Found

- **Two latent fail-open channels in `paired_verdicts.load()`, filed as task 209.** A
  report whose trial id does not split into `game__stack__slot` is `continue`d away at
  the walk, and a criterion carrying `id` without `passed` is dropped from BOTH sides of
  a cell — the second vanishing from paired AND unpaired. Neither is counted or named
  anywhere, in a module whose docstring spends three refusals on refusing to smooth
  things over. The sibling module solved the first shape (capability's gate counts a
  record whose class it cannot name, "counted rather than quietly skipped").
- **capability's gate docstring overclaims `stack_cannot`, filed as task 210.** The
  docstring's "Four ways to fail" lists a `stack_cannot` null third, and the constant's
  own comment says "GATE FAILURE" — but no predicate fires on the reason as such. It is
  caught only through the per-field asymmetry path, which needs a populated arm beside
  it; a `stack_cannot` every arm of a cell marks exits 0.
- **Both measured LATENT on the stored corpus** (2026-08-29, by script over the tree):
  85 report.json walked, 0 malformed tids, 0 passed-less criteria, 0 `stack_cannot`
  reasons, 0 unknown-class records. Nothing live is miscounted; both tickets are about
  the channel, not a wrong number, which is why each is p5.

### Cleared — examined and judged sound

- **The 85-vs-69 walk-count difference between the two producers is designed behaviour,
  verified rather than assumed.** The 16 extra report.json are exactly
  `wg-g4c-capgate/capped` and `/uncapped`'s arms — no trial JSONs, no programmatic.json —
  and paired_verdicts walks them, reads terminal reason `unknown`, and excludes them BY
  NAME in its EXCLUDED CELLS. That is the docstring's refusal 3 demonstrated by the
  corpus it was written from. A reader comparing the two modules' corpus counts now has
  the reconciliation in writing.
- **Every figure the withdrawal register quotes from these modules reproduces today,
  unpiped:** paired's corpus pins 436/5/332 (matrix ALL_TIERS), 232/0/120, 280/4/176, and
  the discriminating delta-156 pin; capability's resolution census "64 of the 69 records
  swept captured at exactly the starter default 640x400; 3 varied (420x640, 720x540,
  768x576); 2 have no geometry" — the exact sentence `WR-capture-default-62-of-68`
  quotes. The register's corrected citations point at rooms that hold.
- **Both selftests are gated, and the one deliberate exclusion is stated where a reader
  meets it:** `gates.yml:321` runs capability_selftest; `gates.yml:412` runs
  paired_verdicts' SYNTHETIC half, with "(corpus pins need eval/runs)" in the step name —
  the reason the corpus half is CI-absent is the name of the step, not a silent gap.
  Both exited 0 unpiped this pass.
- **capability's structural defences held under reading:** `STARTER_DEFAULT_GEOMETRY`
  is double-stated (constant here, sources in the starters) and capability_selftest
  asserts the two agree per arm — rule 12 in code, run green; `observe_doc` lets frames
  on disk beat the summary and records the disagreement (#60's shape, guarded);
  the null-reason catch-all keeps `fields` and `reason` in step; `distribution` prints
  `n` and `populated` separately rather than aggregating over a mixed group (rule 4);
  every table is per task class and `_by_run_class_stack` keys class into the group key,
  so a game field cannot cover a scene gap. Task 185's TRIAL_RE fix is in the shipped
  code (the `[gs]` class letter).
- **paired's refusals are pinned, not narrated:** the tier-set refusal has the delta-156
  corpus pin as its discriminating test ("were these equal the first refusal would be
  decoration", in the code); suite changes are reported as `unpaired-criteria` rather
  than dropped; pooled rows are labelled COUNT-not-rate in the output itself; and the
  docstring carries its own corrected arithmetic ("said six times until re-derived" —
  12 against 2, the real comparison), which is the self-correction living beside the
  claim it fixed.

### Method note

The pointer came from the withdrawal register: three `instead:` commands name producers,
and the pass ran each one rather than reading code cold. That ordering found the
85-vs-69 question (two producers, one corpus, two counts) before any code reading —
and the answer was designed behaviour, which would have been easy to "fix" into a defect
from the code alone. The two filed channels were found the other way round: reading the
drop sites against the sibling module's handling of the identical shape.

### Not opened, and the next pass should take one

`eval/judge/ink_window_control.py` — the last withdrawal-register `instead:` producer
this log has not opened (`WR-ink-arrangement-0-91667` points at it). Taking it completes
the register-coverage thread this pass and the sixth pass followed: every corrected
citation in `eval/withdrawn.json` has then had its room opened and read.

## 2026-08-29 (eighth pass) — the last register room: `ink_window_control.py`, and the register-coverage thread closes

**Area:** `eval/judge/ink_window_control.py` (1118 lines, read whole) — the seventh
pass's named pointer, and the producer `WR-ink-arrangement-0-91667` points operators
at. With this pass every corrected citation in `eval/withdrawn.json` has had its room
opened and read; the thread the sixth and seventh passes followed is done.

### Found

- **One latent crash channel, filed as task 211.** The corpus arm — the producer for
  every ink figure the documents quote — reads the frames block with
  `.get("frames", {})` and then calls `.get` on the result. A stored record whose
  `programmatic` holds `"frames": null` returns None from the first `.get` (the key
  exists, so the default never applies) and raises at line 881: exit 1, every healthy
  record's figures lost with the malformed one. The same chain sits at the failure
  listing (line 896) and in `reference_shift` (line 966), masked by the corpus crash.
  It is the #176 shape — one unreadable record turning a producer off — in a module
  whose standard everywhere else is name-and-count. Reproduced on a fixture tree
  BEFORE filing; 0 of 69 stored records carry it, so latent, hence p5.

### Cleared — examined and judged sound

- **The register entry's figures reproduce unpiped, all three arms, exit 0.** The bare
  run: 56/56 expectations held. The phase the entry names read all 4 arrangements at
  **0.0, every one FAILING**, with the retired frame-0 readings 0.0 / 0.91667 / 0.5 /
  0.5 — the two 0.5s printed ADMITTED by the retired window, which is the entry's
  whole point — and `the arrangement no longer moves the number at all`. COLOUR_DRIFT
  read 0.00001, flat 1 of 12, 0.91665 under the retired reference, exactly as
  `COLOUR_DRIFT_INK` and `COLOUR_DRIFT_UNDER_FRAME0` state.
- **The corpus arm over the stored tree: 85 gradings over 69 submissions, 16
  superseded, 0 skipped, 0 paths not a run.** `task_class` read from the record on 1
  and inferred from the id shape on 68 — counted out loud, not silently read as games.
  All 4 historical `render.nonempty` firings named with the bound each hit and the
  re-grade verdict: the two `wg-arena3d` rust rows at 0 frames on the floor, the
  `wg-g4c` platformer and the scene on the retired 0.85 ceiling, both PASSing under
  the floor — the scene keeping its other 3 gate failures, so the re-grade moves no
  story.
- **`eval/RUNS.md`'s break-25 section reproduces row-for-row against the producer** —
  the 10-mover table value by value, 67 readable frame sets and 2 without (the same
  rust cells), lowest value under either reference 0.00811 (the "8x the floor"
  sentence), and the retired ceiling refusing 1 of 67 under the new reference, the
  scene at 0.85042. A live document's figures re-derived rather than trusted, and
  none had drifted.
- **The module's defences held under reading, and each is a rule in code:** the
  phase-count guard (every phase declares its count; a dropped phase exits 1 —
  #212's lesson, which landed the same day, already applied here); `_frame0_inks`
  RE-MEASURES the retired reference instead of trusting the table column it
  adjudicates; `reference_shift` refuses to report a shift (-1) unless its frame-0 arm
  first reproduces all 67 stored values to the digit, and proved them today; NOT ASKED
  vs `0 firings` kept distinct; the restored-0.85 mutant is the real pre-change body,
  not a stub returning a number; and the bound census pins the WHOLE tally including
  an explicit `task_class: 0`, so a reclassification that keeps the total (measured
  live: `no_bound=9, starter=1`) still goes red.
- **It is wired, and the wiring resolves:** `gates.yml:338` runs it bare on every push
  and PR — the control's duty cycle is CI, not memory — with the corpus arm CI-absent
  by design (`eval/runs` gitignored) and the reason stated in the docstring and the
  output. DECISIONS.md and RUBRIC.md name it as what re-opens the ceiling decision and
  as the derivation's producer; `png.py`, `static.py` and `SCENES.md` point back at it
  for the same numbers.

### Method note

The seventh pass's ordering held: run the register's producer before reading code
cold, and the entry's answers were verified before anything was judged. The channel
was found the other way round — reading the drop sites against the module's own
name-and-count standard — and the reproduction CORRECTED the ticket's scope once: the
`reference_shift` chain looked like a second channel until `tier1_census.load_gradings`'
skip of a null `programmatic` showed it unreachable except behind the corpus crash. A
null `programmatic` never reaches either arm; `frames`-inside-a-dict is the one shape.

### Not opened, and the next pass should take one

`eval/judge/static.py` (767 lines) — the tier-1 implementation itself: `collect`,
`analyse_frames`, `nonempty_verdict`, `INK_FLOOR` and the bound registry this pass and
the ink control exercise from outside. No pass has opened it, and it now carries three
backward references to the module this pass read. Its companion reader `eval/judge/png.py`
(208 lines) can ride along.

## 2026-08-29 (ninth pass) — `static.py`, the tier-1 implementation, and the one `echo 0` in it

Subject: `eval/judge/static.py` (767 lines), read whole. `eval/judge/png.py` was the
pointer's ride-along and is **deferred**: tasks/212 is in flight in that file this
pass, and reading a file an agent is reshaping produces findings about a moving
target.

### Found

**tasks/213 — `static.run`'s waiter turns an unobservable exit status into exit 0.**
The waiter thread catches `(ChildProcessError, OSError)` and `reaped.put((0, None))`;
the main flow decodes status 0 as `waitstatus_to_exitcode(0)` = 0, so `build.compiles`,
`verify.green`, `lint.clean` and `tests.green` — the tier that GATES — would each
record `exit 0` from a command whose status was never observed, with empty streams and
no note. AGENTS.md rule 3's sibling verbatim, and the only `put` of a fabricated status
in the module. **Measured before filing**: an in-process probe forced `os.wait4` to
raise, ran `sh -c "exit 3"` through `static.run`, and read back exit 0 / note empty /
streams empty, while the unforced control read the true 3. Latent today (the module
suppresses Popen's own waitpid, so nothing double-reaps; that is why p5), but the
authors defended the Popen side of this exact race and left the wait4 side fail-open.
The fix model is the module's own spawn-failure branch three lines up: 127, harness-
named note, peak/cpu staying None as the third value.

### Examined and judged sound

- **`nonempty_verdict`'s `float(frame_info.get("mean_ink", 0.0))`** — the same
  `.get(key, default)` shape tasks/211 fixed in `ink_window_control.py`, but here the
  null crash is guarded at the one call site that can reach it with a stored record
  (`ink_window_control.py:932`: `ink is None` → NOT REGRADABLE, with a comment naming
  the exact raise it prevents). Every other caller passes a computed float. Absent
  reads 0.0 and fails the floor — fail-closed. A defensive move inside the function
  would be tidier; it is not a channel.
- **`assert_frame_criteria_geometry_safe`'s source-scanning discovery** — reads the
  module's own source for `add(...)` calls touching `frame_info`/`frames`, and checks
  BOTH directions: an undeclared frame-derived criterion fails, and a registered id
  that no longer appears fails too (#38's shape). The known scope limit — a frame
  criterion added via `crit.append` rather than `add()` would be invisible to
  discovery — is documented in the docstring, and `collect`'s audio block is the only
  append site (not frame-derived).
- **`TIER1_BOUND_POPULATION`** — complete at 14 (9 + 5 audio), closed vocabulary of 5
  populations, `task_class` deliberately empty, and `assert_tier1_bounds_declared`
  enforces the registry against both `CRITERIA` lists mechanically, including the
  audio-import-failure case, which lands as a problem row (fail-closed) rather than a
  quiet skip.
- **The capture policy** — `STREAM_*`/`_sample_stream`/`capture_fields` are ALIASES of
  `runner.py`'s functions, asserted same-object by `runner_capture_selftest.py`; the
  `Cmd.tail` parser view is preserved byte-for-byte and documented as the pre-#100
  view, with the separated streams what gets STORED.
- **`_MAXRSS_TO_MIB`** — the macOS/Linux ru_maxrss unit split is measured, not
  trusted: `rusage_selftest.py` asserts it against a child allocating a known 400 MiB.
- **The INK_FLOOR comment block's figures** — reproduce against its named producer as
  of this same day: 66 game frame sets with frames on disk, 67 total readable, 10
  movers under the reference change, lowest 0.00811 (8x the floor), the retired 0.85
  refusing exactly 1 set (the scene at 0.85042). Verified by the eighth pass's
  producer runs hours earlier; not re-run here, quoted from that run.
- **`assert_task_class`** — refuses an unplaceable class BEFORE spending a toolchain,
  and `ink_window_control.py` mutants the fallback (`lambda k: "game"`) to prove the
  refusal is load-bearing.
- **`analyse_frames`' unreadable-set branch** — a whole-corrupt set reads mean_ink 0.0
  (fails the floor), records per-frame decode errors, and `render.frames` reads
  `errors` separately, so a corrupt PNG is a finding about the submission, never a
  grader crash.

### Method note

The probe-first ordering from the seventh and eighth passes held again: the channel
was found by reading the module against the rules it itself cites (the `Cmd` docstring
names the "never 0.0" rule the waiter breaks one field over), and the probe that
established it ran a command with a KNOWN exit before anything was filed. The
`.get(key, default)` non-obviousness (found in `nonempty_verdict`) was chased to
reachability BEFORE judging it a defect, and the chase cleared it — the second pass in
a row where the obvious first finding was the false one.

### Not opened, and the next pass should take one

`eval/judge/png.py` (208 lines) — deferred this pass because tasks/212 may reshape it;
take it once 212 has landed, reading the landed form. Alternate if it is still in
flight: `eval/judge/probe.py`, the ProbeSession behind `probe_throughput`, which no
pass has opened and which `static.py` and the render harnesses all lean on.

## 2026-08-29 (tenth pass) — `eval/judge/probe.py`, the ProbeSession and the scripted play-bot tier

989 lines read whole (the ninth pass's recorded alternate — png.py was still in flight
under tasks/212 at the hour this pass ran, so its pointer's alternate applied).

### Found

Two tickets, both measured before filing, both latent (nothing stored is wrong):

- **tasks/214** — `drive()` appends `audio.triggered` AFTER the lock-conflict exclusion
  has already run over the bot criteria (probe.py:960-962 composes outside
  `unusable_criteria`), so the #25 scored=False remedy does not reach the one criterion
  that cannot inherit it. Measured in-process: `triggered_criterion(..., fired=[])`
  (the audio.py:610 empty-fired branch) returns `passed=False, scored=True` while
  `unusable_criteria` on the same lock error returns `scored=False`; the manifest branch
  (audio.py:614-616, exhausted via read_manifest:296-312) has the same hole, under that
  file's own "bias, not noise" comment. Reachable only on the narrow window
  `_claim_repo` (#30) cannot remove — `grep -rl "project-lock signature" eval/runs/`
  is empty.
- **tasks/215** — `LOCK_HINTS`' bare `"lock"` substring is the set's one open-class
  member: censused over every stored `[stdout pollution]` line (2 unique, BOTH genuine
  Unity refusals, BOTH matching the specific phrases, 0 on the bare substring) and every
  stored `probe_stderr` string (0 hint hits), and demonstrated in-process that
  "Clock: 60 fps" and "Deadlock detection: off" classify as lock conflicts — which in
  probe.py ends in `lock_conflict=True` → every criterion excluded as NOT MEASURED, the
  fail-open direction the `_looks_like_lock_conflict` docstring says the harness-note
  exclusion exists to prevent. The two definitions (probe.py:230, audio.py:292) are
  hand copies never asserted equal, and they have already drifted in what a match
  MEANS (exclusion vs extra retries). The pollution channel itself is load-bearing —
  Unity prints its refusal on STDOUT, so without probe.py:383 the #25 remedy never sees
  its own messages; the ticket narrows the set, never the channel.

### Examined and judged sound

- **`Tick.parse`** — strict on the four required keys, `state`/`events` types, and
  non-object lines, each with the offending line prefix quoted at 200 chars.
- **The session-guard lifecycle** — `_claim_repo`'s three cases (same-thread supersede
  with `superseded` making later `step()`s raise a BOT-BUG message rather than a
  submission defect; cross-thread wait with `lock_wait_s`; cross-process flock whose
  timeout starts anyway with a note, because the in-process lock is the one that
  matters), and `_release_repo` releasing child-gone-first (close() waits/kills before
  unlocking, so the next session sees a released project, not a closing one).
- **The fresh-queue-per-attempt fix** (probe.py:193-197) — a refused attempt's reader
  thread owns the old queue and would otherwise hand its EOF sentinel to the next
  attempt's first read.
- **`_read_line`** — total-budget check per poll, per-line deadline, EOF named with the
  child's poll code, blank lines skipped, and the pollution skip RECORDING rather than
  failing (with the storage and the vote path that makes it load-bearing, above).
- **The end-condition two-phase design** — idle-then-press with the press phase READ
  THROUGH THE RESET, every tick of both phases read (not endpoints — the CodeRabbit
  #40 raises are in the field comments), the settle window small ON PURPOSE with the
  pacing arithmetic in the comment, and `end_condition_holds` REFUSING a session whose
  `state.game_over` is not True at entry — fail-closed at the one place the state-flag
  and event readings could disagree (the tasks/166 and tasks/157 history is in the
  block comment and matches the code).
- **`Criterion.scored` / `unusable_criteria`** — diagnostic-only as measured-but-
  unscored, lock conflict as measured-but-excluded, and `drive()`'s "unscored" map
  existing so a shrinking `total` cannot read as a quiet pass.
- **`drive()`'s blind `except Exception`** — deliberate, commented as the rule-7 trade
  (a bot bug costs a trial, never a false pass), and the dedicated play session
  scoring nothing with `play_session_error` recorded so a missing representative play
  is distinguishable from one never asked for (#52's separation is intact).
- **`Bot.not_established`** — the honest third verdict for an experiment that cannot be
  set up, scored=False by construction rather than by excuse.

### Method note

The probe-first ordering held a third time, and the corpus census changed the finding
instead of merely confirming it: the reading had flagged the stdout-pollution channel
itself as the defect (harness-labelled text in the buffer the docstring calls
child-only), and the census showed the channel is the #25 remedy's load-bearing member —
2 of 2 true positives, both on specific phrases — so the ticket aims at the one hint
that has never matched anything real instead. The `.get`-shaped suspicion did not arise
this pass; the composition-order defect (tasks/214) was found by tracing what `drive()`
appends AFTER the try/except, which is where the exclusion has already happened.

### Not opened, and the next pass should take one

`eval/judge/png.py` (208 lines) — still the primary pointer, once tasks/212 has landed
so the landed form is what gets read. Alternate if 212 is somehow still open:
`eval/judge/scene_probe.py`, which this pass found but did not open.

### Addendum (same day, on the pass's own ticket)

tasks/214's title exposed a queue-format channel: it was written as an unquoted YAML
scalar containing "so the #25 exclusion...", and ` #` starts a comment in a plain
scalar, so the PARSED title has been cut at "so the" since the ticket was created —
with `tasks.py check` green throughout and the full bytes on disk. Filed as tasks/216
(property check: parsed value shorter than the raw line), with the four census rows
where a hash follows a non-whitespace character (174, 181 x2, 187) as the green
controls; the repaired 214 title is the only lossy scalar in the queue.

## 2026-08-29 (eleventh pass) — `eval/judge/png.py`, the dependency-free PNG reader

258 lines read whole (the tenth pass's recorded pointer, taken now that tasks/212 has
landed — this is the post-212 vectorised form), plus a caller census over every
`png.`-touching file outside `eval/runs/` (11 consumer files, from
`ink_window_control.py`'s 106 references down to `capability.py`'s deliberate
header-only read).

### Found

Nothing. No ticket filed — the first pass since the log began that returns one. The
three suspicions the read raised were each resolved by measurement rather than
argument:

- **Are filter types 1-4 in `read()` dead code?** No. `write_rgb` emits filter 0 only,
  but `read()`'s non-fixture callers read frames produced by SUBMISSIONS
  (`static.py analyse_frames`, `hud_check.py corner_ink`, `field.py`'s geometry
  label, `frame_parity.py`), and the four render harnesses are four independent PNG
  producers. A decoder that handled only filter 0 would turn one submission's
  filtered output into a false "unreadable frames" finding. The five-way decode is
  tolerance of real producer variety, not untested surface — and the bit-exact
  fixture/corpus reproduction through `--pin-dump` (tasks/212) exercises the reader
  end to end.
- **Does `body = raw[pos+8:pos+8+length]` silently truncate on a malformed chunk
  length?** It truncates, but never silently in effect: a truncated IHDR fails
  `struct.unpack` (needs exactly 13 bytes); a truncated IDAT fails
  `zlib.decompress`; a truncated PLTE yields a short palette and therefore an Image
  whose data length disagrees with its geometry — which fails CLOSED through the
  length guards tasks/212 added to `ink_coverage` and `differs_from` (PngError naming
  the lengths), or raises IndexError in the two per-pixel `rgb()` loops
  (`scene_probe.py:171`, `hud_check.py:39`). Every path terminates in a raised
  exception; no silent wrong number is reachable. The 212 guards closed this channel
  as a side effect of fixing a different one — worth recording so the next reader
  does not re-derive it.
- **Who consumes `rgb()` per pixel, and is the cost bounded?** Two callers, both
  bounded: `hud_check.py` iterates a fixed 230x64 corner box; `scene_probe.py` samples
  probe points. Neither walks a full frame.

### Examined and judged sound

- **`is_flat` / `analyse_frames` redundancy** — the docstring's THE-ONE-ADDRESS claim
  and `static.py`'s fail-closed-redundancy comment agree, and
  `ink_window_control.py` asserts the implication in code rather than a sentence
  promising it (rule 12's own medicine, applied).
- **`differs_from`'s k==3 / k<3 split** — the `zip`-truncation worry is closed by the
  length guard above it: exact `len == n*channels` is what makes every channel slice
  exactly `n` long, so both branches pair `n` elements.
- **`dominant_background` determinism** — `max` over a dict iterates insertion order,
  so a tie resolves identically for identical input; the `>>3<<3` quantisation and
  the ~4000-sample step are the documented cheapness, and the c==1 channel-reuse
  quirk matches `ink_coverage`'s deliberate style.
- **`write_rgb` atomicity** — tmp sibling + `os.replace`, cleanup that suppresses its
  own OSError so the original error survives; the one writer for the fixtures, and
  the ref_arena fallback copy follows the same shape.
- **The consumer error policies** — `analyse_frames` records each unreadable frame
  per-frame with the reason (a corrupt PNG is a finding about the submission, never a
  grader crash); `field.py` narrows to `(PngError, OSError)` because geometry is a
  label; `capability.py` reads the header without `png.read` deliberately, and says
  so. `skill_layout_control.py`'s `_differs_from_index` is an unrelated name-collision.

### Method note

The census-first discipline is what turned three would-be tickets into zero: each
suspicion named a mechanism, and the caller census said whether the mechanism is
reachable and what it terminates in. The pass's one general observation: tasks/212's
length guards were added for byte-translate alignment, and they are ALSO what makes a
truncated-PLTE Image fail closed — a repair's blast radius includes channels nobody
aimed it at, and the place to record that is the log, not a comment in png.py claiming
credit.

### Not opened, and the next pass should take one

`eval/judge/scene_probe.py` (1,600+ lines — the largest unexamined file in
`eval/judge/`; two passes in a row have deferred it). Its `rgb()` call, `differs_from`
use and `frames_a` accumulation were touched only at the census level here.

## 2026-08-29 (twelfth pass) — `eval/judge/scene_probe.py`, the tier-2 scene probe

1,784 lines read whole (64 functions — the pointer recorded by the eleventh pass,
deferred twice before that), plus a constant census over `eval/` for the capture
contract and a check of what actually runs the pinning harness.

### Found

Nothing. The pass's one candidate died on reachability:

- **`contract_frame_ticks` collapses below 12 distinct ticks if a scene ever declares
  `ticks <= 10** (`(i*ticks)//(CONTRACT_FRAMES-1)` collides), which would hold
  `frames_usable` False forever — and `why_frames_unusable` would then print
  self-contradictory prose ("produced 12 frames, not the contracted 12"). Measured:
  `ticks=10` yields 11 distinct ticks; `ticks=660` (both scenes) yields 12. NOT FILED —
  the trigger is a configuration nobody has chosen (`CONTRACT_FRAMES` is
  single-declared; no second scene exists), the failure is fail-closed (criteria fall
  back to their telemetry halves), and the defect is the prose, which is
  self-announcing when it fires. This is the dividing line against tasks/214 and
  tasks/215, which were filed: those triggered on data the project HOLDS and failed
  SILENTLY. This one triggers on nothing and fails loudly.

### Examined and judged sound

- **`_walk` as the only offset-subtraction site** — the tasks/162 repair holds: the
  unwrap is per-tick against the layer's own `span`, maps into `(-span/2, span/2]` via
  `ceil` (the `round` half-to-even trap is documented and avoided), and a layer is
  walked only by carrying finite `offset` and positive `span` on EVERY trace line — the
  hole/truncation/duplicate-id table in its docstring matches the one `lines[lid] !=
  len(trace_a)` comparison that enforces it.
- **The not_established / fail table is enforced everywhere** — a broken film recipe
  fails (`image_only` gets FALSE with the reason); an experiment that cannot be set up
  (`no frame in the light ramp`, `no own rows`, `leaning < 5 deg`, `no usable screen
  box`) is `scored=False` via `not_established`. No criterion conflates them after the
  read.
- **The Nyquist precondition runs BEFORE the agreement test**, with the
  aliased-agrees-with-itself variant named as the reason; the stationary-object blind
  spot is excluded BY NAME and counted (`blind`), not widened into a tolerance; a
  median shift of exactly 0 is RELIABLE — the fail-open channel round `image_parallax`
  is documented closed.
- **`measured_twice` is recorded, never inferred** — `image_ran` is called by exactly
  the criteria listed in `both_halves` on both scenes (traced each call site), and
  `drive()` clears the set per call, so a re-driven Scene cannot report a stale image
  half.
- **`seed.pair` as ONE four-part conjunction** — same-seed hashes AND cross-seed hashes
  AND same-seed frame bytes AND cross-seed frame bytes, with both film comparisons
  required together before `image_ran` fires (one alone is the half the other exists to
  reject).
- **`drive()` fails closed** — `ProbeError` → `unusable_criteria`; anything else →
  `all_false` with the exception in the evidence; the lock conflict is the one unscored
  channel (#25). `state_at` on a missing tick returns `{}`, which starves the layer
  into `no_offset` reasons rather than inventing motion; a trace hole fails
  `layers.depth_ordered` by name.
- **Degenerate-distribution guards in `_wheels`** — the `[1,1,1,5]` speed swing with an
  empty slow half is caught BEFORE `statistics.median` raises, with the reasoning in
  the comment (an uncaught StatisticsError inside `drive`'s blind except would score
  every criterion false — published wrong number, the worse direction).
- **`_refracts` measures its control before trusting its measurement** — the bare-strip
  drift gate refuses the comparison when the backdrop itself moved between the two
  frames, so `structure`/`change` are never read off a confounded pair.

### Measurement

The docstring's "pinned in BOTH directions by `scene_mutants.py`" is a live claim:
`controls.yml` runs the full scene_mutants suite, its `--census-selftest` and its
`--reliability-selftest` on every push, and both `controls` and `gates` are green at
the HEAD this pass read. `CONTRACT_FRAMES`/`contract_frame_ticks` are declared in this
file only — no second copy exists to drift (the starters' parity with the contract is
`frame_parity.py`'s running control).

### Method note

This is the third channel declined for the same reason, which is worth stating as the
policy it has become: **a latent channel gets a ticket when its trigger is data the
project holds and its failure is silent; it gets a log line when its trigger is a
configuration nobody has chosen or its failure is self-announcing.** The queue is for
channels that can fire on what exists, not for prose defects in worlds that do not
exist.

### Not opened, and the next pass should take one

`eval/judge/field.py` (2,173 lines) — now the largest unexamined file in the judge
tree, and the ninth pass's census touched only its two `png` references. Alternate:
`eval/judge/scene_mutants.py` (1,423), whose suites run green but whose own body no
pass has read.

## Pass 13 — 2026-08-29 — `eval/judge/field.py`

The pointer from pass 12: the largest unexamined file in the judge tree. Read in full
(2,173 lines, 31 defs/classes) — the pack/run/gates CLI, the blinding inputs consumed
from the pack side, `run_field`'s five pre-spend guards, and the four gates.

### What was read and judged sound

- **`run_field`'s guard order** — mapping-leak refusal → `applicability()` BEFORE the
  `ASPECTS[aspect_id]` subscript (an unknown id is a stored `usable: False`, not a
  KeyError) → `sees` match → scene-statement CONTENT comparison (existence is not the
  resource; `UnicodeError` named beside `OSError`) → the `knowingly_truncated` third
  value refused rather than read as false (#62's direction, closed).
- **`_provenance`** — every field answers "what did this round actually see": brief
  hash, scene-statement hash, `sees`, geometry, truncation flag, budget, turns.
- **`separation()`** — SE-based pair resolution replacing #58's modal threshold; the SD
  convention stated with the measured spread across the three candidates; `marginal_pairs`
  within 10% of threshold made visible; the low-n warning names #74's flattering n=2.
- **`reproducibility()`** — refuses a different `order_seed` and points at
  `order_invariance` by name, so the two questions cannot be silently swapped.
- **`_tau`/`independence()`** — tie-aware with `comparable_pairs` reported; saturated
  aspects gate the whole verdict first; per-pair not over the minimum; order-seed basis
  recorded, collapsed orders listed.
- **`ceiling()`** kept, marked SUPERSEDED with why; `by_stack` is a labelled per-cell
  display, not an aggregate a gate reads.

### Suspicions raised and measured to nothing

- `separation()`/`reproducibility()` are absent from `main()`'s `gates` branch — but
  `field_sweep.py` calls both (lines 448, 451, 826), and its own comment records that
  the no-caller gap was found and repaired. The sweep is the path that holds them.
- `judge_prompt`'s bucket clause silently omits a `sees` bucket with no wording —
  pinned by `blurb_selftest.py` (rendered prompt per aspect over the whole registry,
  lines 639–660) plus a mutant proving `run_field` passes the pack's own `sees` into
  the argv (lines 693–704).
- `_atomic`'s crash litter (`<out>.<pid>.tmp`) — does not match `*.json` globs, so no
  reader can pick up a half-write; the rename itself already guarantees the misread
  png.py's writer guards against.
- The `--max-budget-usd 12.0` default on every judge call — a ceiling in a unit that
  does not bind (#159), observed per-call judge spend sits far under it, and it is
  recorded per round in `provenance.per_call_budget_usd`, so it is visible rather than
  silent.

### What was found, and filed

**`files_opened` is half of what a judge round records, and the census that claims
"what the rounds read" reads only that half.** Measured before filing, over every
usable field record matching `eval/runs/**/*__*__seed*.json`: 97 rounds, 71 carrying
`tool_calls`, holding 6,812 Read/NotebookRead targets and **2,308 Bash** ones — the
second-largest population in the corpus, all stored with full targets (since task 204)
and read by no census. `prompt_capture_census.py` is titled "WHAT THE NON-CODE JUDGE
ROUNDS READ" and its six states sum to the aspect's n over `files_opened` alone, so a
judge that `cat`s or `grep`s an un-carried path lands in no state and the latent-null
figure in `eval/RUNS.md` would not move. Latent channel, trigger is data the project
holds, failure silent — a ticket under the pass-12 policy: **tasks/218**.

The vocabulary scan that bounded it: 30 Bash targets touch stack tokens (`bevy`,
`UnityEngine`, `project.godot`) — visible by design (#53), not a blind leak; the one
`crates/sim` hit is in a pre-#131-repair pack that finding already bounded. The ticket
says both, so nobody re-files them.

Incidental corroboration from the same census: 393 `Agent` tool calls across stored
judge rounds — the subagent capability `JUDGE_PROMPT` offers was verified by a probe at
the time, and the corpus confirms it in the wild.

### Not opened, and the next pass should take one

`eval/judge/scene_mutants.py` (1,423 lines) — pass 12's alternate, twice passed over.
Its suites run green in CI, but no pass has read what its mutants actually mutate.
Alternate after that: `eval/judge/audio_selftest.py` (875), then `capability.py` (790).

## Pass 14 — 2026-08-30 — `eval/judge/scene_mutants.py` (1,423 lines, read whole)

Pass 13's pointer: its suites run green in CI, but no pass had read what its mutants
actually mutate. With this pass the scene layer is read whole — pass 12 read
`scene_probe.py`, this pass reads the suite that pins it.

### Found

- **All four invocations are gated; pass 12's log entry understates the wiring.**
  `controls.yml` runs the full suite (`:130`), `--census-selftest` (`:136`),
  `--reliability-selftest` (`:144`) **and `--attribution-selftest` (`:152`)**, and the CI
  register names the last two. Pass 12's entry names only three. The defect was in this
  log, not in CI; recorded here rather than editing the standing entry.
- **The stored scene-gradings population moved 0 → 1 since the suite was written**
  (`wg-scene-s1ts-2026-08-25/.../playbot.json`, tier `scene_probe`, measured through the
  suite's own `stored_scene_gradings`). The census handles it honestly — at n=1 it prints
  "extend this census" rather than a number — and with one subject no number is computable
  (rule 4). The extension question is gated behind task 145 (the operator's scene-matrix
  decision), so no ticket is filed ahead of it.
- **Coverage, measured statically against the registry:** 15 criteria / 23 mutants /
  0 uncovered / 11 variants; 10 criteria carry a single mutant. That is the same shape the
  play-bot suite has, and the variant-count question for the family is already
  `tasks/155`'s. Nothing new filed.

### Cleared — examined and judged sound, do not redo it

- **The patch discipline is fail-closed at both layers.** `apply_patches` and `_probe_with`
  each assert the target appears exactly once, so a drifted fixture or a drifted
  `scene_probe.py` SystemExits instead of silently not mutating (#41's shape, refused at
  the suite level). CI green at merged main proves every target still bites today.
- **The positive control runs first, per scene, and an UNSCORED mutant is an escape, not a
  catch** (docstring and the explicit expectation at the scoring site). Extra verdict flips
  outside a mutant's declared `collateral` are reported, and a criterion with no mutant is
  itself a problem row — the coverage refusal at the end of `main`.
- **The census states its own population's limit in its output** — "FIXTURES, NOT
  SUBMISSIONS", NOT ASKED distinguished from 0, and the stored tier read by PARSING each
  json rather than string-matching serialisations, with the enumeration trap named in the
  comment above it. `census()`'s problem count is deliberately not folded into `main`'s
  exit code: an open question is the census's output, and `census_selftest` consumes the
  count as its API.
- **The two offline selftests are rule 12 and #150 made code.** Subjects are hand-written
  records whose answers are stated before anything runs; the mutants edit the SHIPPED
  `scene_probe.py`, never the table; a mutant that raises is a distinct caught verdict
  with the divide-by-zero mechanism named, not a harness crash; and the `no_offset` case
  records the day a declared reason key was reachable by no evidence string.
- **The attribution table flows through `_bands`, not straight into `_own_band`**, with the
  bypass it prevents named (rows the profile can never sample); variant tolerances are
  per-criterion with the reason in `notes`, and a tolerance that never fires prints as
  dead — rule 7 made visible. The three real-submission lessons (`tasks/162`, `164`,
  `174`) live in the suite as variants the probe once failed, each marked "NO MUTANT
  COULD HAVE FOUND THIS" with the reason.
- **The docstring's `python3 judge/scene_mutants.py` shorthand** — checked against
  siblings (bot_mutants.py identical) before being judged; house convention, not the
  tasks/203 class.

### Method note

The pass's one live suspicion — the attribution selftest ungated — came from reading pass
12's log summary and died on the register and the workflow file. The log's own
incompleteness was the only defect, which is why the correction is recorded here: a
pointer's accuracy is part of what a later pass inherits.

### Not opened, and the next pass should take one

`eval/judge/audio_selftest.py` (875 lines) — the corrected pointer: pass 13 listed
`capability.py` as the alternate, but pass 7 (2026-08-29, seventh) already read it whole.
Alternate after that: none named — the judge tree's larger unread files are gone through;
the pass after audio_selftest should pick from `eval/suites/` (regime-boundary rules as
before) or re-derive from the import graph.

## Pass 15 — 2026-08-30 — `eval/judge/audio_selftest.py` (876 lines, read whole)

Pass 14's pointer, taken as named. The file is the mutation suite for the audio criteria,
and it is where four of this project's disciplines are simultaneously load-bearing: rule 15
(mutants are not enough — the variants are the half that catches `tasks/152`'s
junk-entries buy), the task-113 rule (an expectation kept in step with its subject by a
ROW THAT COMPARES THEM — `EVENTS_AS_WRITTEN` is transcribed by hand and compared to both
`audio.GAME_EVENTS` and the RENDERED prompts, which is what caught `tasks/151`), the
closed-class rule (LOCK_HINTS pinned in both directions through both readers, with 3
mutants: substring restored, phrase dropped, equal-but-distinct copy), and rule 7 (the
fail-closed default — a run that HAPPENED and emitted nothing — has its own rows, so the
lock exclusion cannot quietly loosen it).

### Found

Nothing to file. The one live suspicion — the docstring says "six audio criteria" while
`healthy()`'s docstring says "all five" — died on the frame, not on the prose: `collect()`
carries 5 criteria and `audio.triggered` is the sixth, driven through `probe.drive` below;
each docstring is right in its own frame, and the positive controls loop
`audio.CRITERIA` directly, so they adapt if either count moves. Manufacturing a pin for a
docstring prose count is the task-92 lesson (the quantifier trigger went 26 red with no
true positive), not a gap.

### Cleared, by reading rather than by trusting CI

- **Every mutant kills by a row naming its mechanism, and the two hardest mutants assert
  their CONTROLS stay green** — mutant 11 (append without the lock bit) must scorch the
  lock fixture *and* leave both non-lock controls green, with the reason stated (a scorch
  that also failed the controls would be a different, fail-closed defect); mutant 14
  (phrase dropped) must leave the OTHER stored line classified, so the red row is
  attributable to the removal.
- **The stub boundary is chosen, not accidental**: `drive_with` replaces
  `probe.ProbeSession` wholesale because `drive()` names the class directly — no engine,
  no child process, no `just` on the lock paths; the manifest-lock paths stub
  `audio.time.sleep` instead so the REAL retry loop runs (4s+8s per exhausted read,
  measured, not skipped).
- **`MUTANT 15`'s comment encodes a real Python trap**: `tuple(t)` on an exact tuple IS
  `t`, so the equal-copy mutant would manufacture nothing; the file builds the copy
  through `list()`.
- **No dead weight**: every helper (`tone`, `silence`, `add_extras`, `VOICES`, `PONG`,
  `EVENT_LINE`, `EVENTS_MARKER`) has a consumer; all imports are used.

### Measured

`python3 eval/judge/audio_selftest.py` unpiped, this pass: **124 expectations checked,
0 unmet, exit 0.** The suite is also gated in `controls.yml` on every pull request, so
this file's green does not depend on anyone remembering it.

### Not opened, and the next pass should take it

`eval/judge/judge.py` (449 lines) — **zero coverage in 15 passes** (the only file in
`eval/judge/` the log has never once named), and `git log` shows it untouched since task
34's lint triage, near the repo's start. Two live documents cite it
(`research/12-sibling-comparison.md` rows 6 and 12 quote its docstring and its
one-submission-per-session discipline). A pass should read it whole and answer: is the
grading entry point live, and if it is, what does it mean that everything around it
changed while it did not? Alternates after: re-derive from the import graph.
`eval/suites/` is otherwise gone through — `wholegame_prompts.py` pass 2, the scene layer
pass 12 (`scene_prompts.py` inside the 4,168-line layer read). The one remainder is
`suites/prompts.py` (97 lines, the FIRST bake-off's per-stack prompt vocabulary, predating
the whole-game suite) — no pass has read it; too small to be a pointer on its own, but it
is the tree's one unexamined file.

## Pass 16 — 2026-08-30 — `eval/judge/judge.py` (449 lines, read whole)

The pass-15 pointer, taken: zero coverage in 15 passes, unchanged since task 34's lint
triage, cited by two live documents. The pointer's question — *is the grading entry
point live, and what does its stillness mean?* — has a definite answer.

### The answer: retired, not stale

`judge.py` is the RETIRED 13-criterion generalist judge (`aspects.INSTRUMENTS`:
`legacy_judge`), opt-in behind `--with-legacy-judge` and default-skipped — `evaluate.py`
writes a skipped marker (`game: None, usable: False, passed: 0/13, no model`) when it
does not run. Its stillness is retirement plus the 2026-08-25 instruments decision
moving its guarding to the class axis; the two live documents that cite it
(`research/12` rows 6 and 12) quote its docstring, which is unchanged and still
accurate. The docstring's six constraints are each visible in the code (DEFAULT_MODEL
`sonnet` against builders on `opus`; the SCHEMA orders evidence and reason before
`passed`; `_pass_one` drops a pass with under 20 characters of evidence; the
forward/reverse conjunction with `instability`; `build_pack` for blindness), and the
docstring's "thirteen failures" matches `len(ALL_CRITERIA)`. The `--out` help text
carries a real incident (spliced JSON from two judges aimed at one path) with its own
repair — atomic write plus refuse-unless-empty.

### Found: one ticket

**The game axis of the guard is missing (tasks/221).** The 2026-08-25 decision guarded
the CLASS axis — `legacy_judge: "game"` — but `judge()` itself renders
`GAME_BRIEF.get(game, "(unknown game)")`: `GAME_BRIEF` holds 3 entries, the suite has 4
games, and `g4_platformer` passes the class guard into 13 criteria answered against a
placeholder brief. The CLI surface refuses it (`argparse` choices are the
`GAME_BRIEF` keys); only the `evaluate.py` path is exposed. Measured before filing: the
stored corpus holds **25 real judge rounds (g1_pong 9, g3_arena 8, g2_tetris3d 8), every
one on a briefed game; 0 fired, and 44 of the 69 stored `judge.json` files are skipped
markers, not rounds.** The repair is the refusal, not a g4 brief — `GAME_BRIEF` is a
retired instrument's table, and extending it would change what a re-run of old rounds
would mean.

### Method note: the pass's own first census was wrong, and the correction is the lesson

The first extraction counted `judge.json` FILENAMES and reported **8 g4_platformer judge
rounds** — the exact trap the corpus then disproved: those 8 files are `evaluate.py`'s
skipped markers, byte-shaped `game: None / usable: False / 0/13 / model: None`, and no
kept pack or brief exists behind them. Re-counted by content, the real/skipped split
emerged and every real round's game checked against `GAME_BRIEF`. Rule 2 — never infer a
process's state from an artifact's state — applied to a census this pass ran itself,
which is the pass-12 corollary (verifying is not safer than making) measured once more:
the trap fired in the first 30 seconds of a cleanup pass, on the tool side of a
`find | sed`.

### Not opened, and the next pass should take it

`eval/judge/bot_mutants.py` (2,904 lines) — **the largest file in the judge tree and no
pass has ever read it whole**; it is the enforcement tool for AGENTS.md rule 15 (the
mutant/variant halves), cited by the rule itself, and its last entries in this log are
someone else's counts of it, never a read. Alternates after: `eval/judge/field.py`
(2,173 lines — the capture, cited 9 times, read around but not through) and
`eval/judge/blurb_selftest.py` (1,573 lines).

## Pass 17 — 2026-08-30 — `eval/judge/bot_mutants.py` (2,904 lines, read whole)

The pass-16 pointer, taken: the largest file in the judge tree, the enforcement tool for
AGENTS.md rule 15's two halves, cited by the rule itself — and until now read only in
fragments, its own log entries being other passes' counts of it. Read whole across this
session.

### What it holds, and what holds it up

Four registries and three written-tape families. `MUTANTS` (53 entries over 45 criteria,
the summary line naming MUTANTS not criteria since `tasks/170`); `VARIANTS` (17
correct-but-unusual games, every criterion required to pass on each); `PENDING_VARIANTS`
(**empty, and that is a legal state** — every declared false negative has been repaired,
the last promoted by `tasks/160`); `HAZARDS` (70 per-criterion answers to "what correct
game would mis-score this?", grouped by 11 shapes, with `--hazards` the producer for the
per-criterion figure). The tape families exist where a mutant needs a game the fixtures'
physics cannot be steered into: `rally_tapes` (a rally of one hit, hits on consecutive
ticks, a hit tick that also carries the point), `EndTapeSession` (the
`end_condition_holds` refusal), `grace_tapes` (`match.ends` through the score-locator's
window).

The load-bearing bits, each verified rather than merely read:

- **`hazard_gate` is bidirectional and its selftest pins it red 8 ways** — live-vs-registry
  both directions, duplicate keys, undefined shapes, orphan subjects no criterion claims,
  `covered_by` naming nothing / a cross-fixture label / one real plus one bogus / the same
  label twice. The red pins use synthetic entries, never live data.
- **`_apply` refuses to apply a patch whose target does not appear exactly once** — a
  mutation that silently fails to mutate raises.
- **`adjudicate_pending` goes red on the EMPTY set** (a landed repair must be promoted into
  `VARIANTS`) and on any changed shape; and because `PENDING_VARIANTS` is legitimately
  empty, the selftest borrows a synthetic `Pending` rather than `PENDING_VARIANTS[0]`, so
  the check did not quietly stop running when the list emptied.
- **The 512/513 grace rows are hardcoded on purpose** — a row built from
  `bot_pong.GRACE_BUDGET` would stay green through exactly the edit it exists to catch.
- **`read_end_signal` pins "drove 0 ticks" because nothing else moves**: verdict and
  evidence are byte-identical with the guard deleted — and the file says plainly that this
  escape happened when the control was first written. The tick count is the half that
  pins it.
- **The one waiver channel (`Variant.tolerates`) is currently carried by no variant**
  (the pit variant's six tolerances were removed at task 76), and a tolerance that stops
  firing self-announces — `fired for NOTHING - the tolerance is dead` — rather than
  failing silently.

### Found: no ticket

Two cosmetic notes, neither a defect under the pass-12 bar (latent channel + data held +
silent failure): `variant_rows` is initialised twice in `main` (lines 2744 and 2806,
nothing appended between — no data can be lost); and `hazard_census`'s bare-shape
difference prints only shapes that have rows, so a `SHAPES` definition whose rows were all
replaced would vanish from the census — but `hazard_gate` pins every live criterion to an
entry, so that drift cannot happen silently, and the census is an aid, not a gate.

### Gates at HEAD 70fa421, unpiped

`--selftest` 36/36 exit 0 (registry 8 + pending 3 + `unmet` 3 + rally tapes 10 + end
signal 3 + grace tapes 8 — a different 36 from any criteria count in an older entry);
`--hazards` exit 0 (70 criteria, 45 with a mutant, 17 variants, 0 pending); full suite
exit 0 — **53 mutants pinned in both directions, 17 variants, 3 session-lock controls,
0 unmet**. The four `also flipped [...]` notes (e.g. `PF_ALWAYS_ACTIVE` flipping the four
contact-cluster criteria) are the suite's designed informational report about undeclared
side effects, not undeclared failures — the mutant's own target went PASS→FAIL scored.

### Not opened, and the next pass should take it

`eval/judge/field.py` (2,173 lines, confirmed) — the pass-16 alternate and the
capture-side counterpart of this pass's subject: cited throughout `eval/IMPROVEMENTS.md`,
imported by six selftest modules (`blind_dir`, `blind_ext`, `blurb`, `field_sweep`,
`files_opened`, `pack`), read around by every one of them and through by no pass.
Alternate after: `eval/judge/blurb_selftest.py` (1,573 lines).

## Pass 18 — 2026-08-30 — `eval/judge/field.py` re-read: the pointer was stale, and that is the finding

This pass began by following pass 17's pointer to `eval/judge/field.py` — and the file had
already been read whole, by **pass 13, one day earlier**. `git diff 080faef..HEAD --
eval/judge/field.py` is empty: the read below was of a byte-identical file. The pass-17
pointer was written without checking the log this entry is part of, which is the third
instance of one defect:

- pass 13 listed `capability.py` as its alternate; pass 7 had already read it (found by
  pass 14, which recorded: *"a pointer's accuracy is part of what a later pass inherits"*).
- pass 13 itself pointed at `field.py` as "the largest unexamined file in the judge tree"
  — correctly, at the time.
- pass 17 pointed back at `field.py`, which pass 13's own heading records as read. The
  pass-14 correction was the rule that should have caught this and did not — because it
  lived as prose inside a past entry, four passes upstream, which is where a correction
  goes to stop firing. Same failure as a rule violated by the person who had just written
  it: evidence about where the rule lived, not about the reader.

**Repaired where the pass actually runs**, `.agents/skills/prune/SKILL.md` step 3: a
recorded pointer is a claim, not a decision — before following it, `grep "^## Pass"
CLEANUP-LOG.md | grep <candidate path>`; a hit means it is a prior subject, the pointer is
void, and the voiding is recorded in the new entry. The check is against the headings, not
prose mentions, because alternates and pin sites name files that were never read.

### What the re-read itself established

The file is unchanged, and pass 13's judgements stand as written: the five pre-spend
guards and their order, `_provenance`, `separation()`'s stated-and-measured SD convention
with `marginal_pairs`, `reproducibility()` refusing a seed mismatch by name, tie-aware
`_tau` returning `None` (not `0.0`) at zero comparable pairs, `independence()` judged
per-pair with saturated aspects gating first, and `ceiling()` kept SUPERSEDED with its
reasons. Two things pass 13 did not record, both below the ticket bar (self-announcing,
pre-spend, write nothing):

- **`run_field`'s first line is the one refusal outside the file's own contract.**
  `json.loads(mapping_path(pack).read_text())` is unguarded, and the docstring states the
  design it violates: *"a refusal that is a stored record can be read afterwards and a
  traceback cannot."* A missing or corrupt MAPPING raises instead of returning
  `{"usable": False}`. Loud on stderr, fires before any spend, nothing written — and the
  offline path already classifies a pack without a manifest as "unmeasurable, not clean"
  via `packcheck`. The `mapping["game"]` subscript (vs `.get` at the applicability call)
  is the same shape. Cosmetic; filed here so the next reader does not re-derive it.
- **`--max-budget-usd 12.0` on judge calls checked against DECISIONS.md** and consistent:
  the no-money-figure decision records the judge budget by name — *"held at its stored
  value so new rounds stay comparable with the 97 on disk"* — distinct from the build-side
  ban. Pass 13 measured the same thing from the spend side; the decision is the third
  statement of it.

tasks/218, filed from pass 13's read of this file, is done (PR #98) — the capture census
now reads the Bash/Grep half it was missing.

### Gates at HEAD a3cc3a1, unpiped

Seven suites that import or drive this module, all exit 0: `blurb_selftest.py`,
`blind_dir_selftest.py`, `blind_ext_selftest.py`, `files_opened_selftest.py`,
`pack_selftest.py`, `field_sweep.py --selftest`, `sweep_bounds_control.py` (20/20). Plus
the module's own live gate: `field.py packcheck --run eval/runs/wg-g4c-2026-08-21T02-26-46`
→ `clean=True`, exit 0 — the 23-stale-files state named in `pack_matches_manifest`'s
comment is historical; today's packs match their manifests.

### Not opened, and the next pass should take one

`eval/judge/blurb_selftest.py` (1,573 lines) — named twice as an alternate (passes 16 and
17), verified against the log's headings before naming it here: never a subject. It pins
`judge_prompt`'s wording and `run_field`'s argv, which makes it the capture-side
selftest this pass's gates just exercised black-box. Alternate after that: re-derive from
the import graph — the judge tree's larger unread files are gone through.

## Pass 19 — 2026-08-30 — `eval/judge/blurb_selftest.py` (1,573 lines, read whole)

The pass-18 pointer, taken — and verified against the log's *every* heading before being
followed, not only the `## Pass` ones: passes 1-12 use `## 2026-08-DD (nth pass) — …`, and
the repaired grep must read both formats. blurb_selftest.py had been named twice as an
alternate and had pinned other files' checks since the sixth pass; it had never been a
subject.

### What it holds, and what holds it up

The selftest for **judge-facing pack text** — every sentence a judge reads about the pack
must describe the packer that built it. Born from the 2026-08-22 defect: `EVIDENCE_BLURB`
went on warning every code judge about a size budget for a period after #69 removed the
budget, in the damaging direction (invited to discount an absence it was seeing in full).
Its 13 checks:

- **The subject is the resource, written as one.** `judge_facing_texts()` collects every
  text that speaks to the judge — BRIEF.md, the sampling skill, the `claude -p` prompt,
  SCENE.md — and "a further judge-facing text is covered the moment it is added here". The
  rule-audit lesson (trigger as property, not enumeration) applied where the enumeration
  would have been a list of the two constants that were wrong.
- **Check 1 is keyed on `(sees, blind_language)`, not `sees`** — the fixture's own
  #138-shaped defect, caught here and documented: keyed on `sees` alone it built one code
  pack and checked `architecture`'s brief against it.
- **`measured_incomplete()` reads the stored reports through this file's own code**, not
  through `pack_completeness` — the wiring defect being pinned is that the claim was not a
  function of the packer's state, so the check cannot take the packer's word for the state.
- **Check 4 is aimed at the claims, not the rendered brief** — and the comment carries the
  measurement that chose the address: the obvious one (rendered text) false-positives 3×
  on the skill's past-tense history paragraph; the shipped one (present-tense claims) is
  0 FP live, 2 TP pre-repair. The task-92 lesson applied in code, with the corpus counts
  recorded.
- **Expectations spelled out here, reconciled by rows** — `FRAMES_AUDIENCE_GAME/SCENE` and
  `PROMPT_EVIDENCE_WORDING` are the second, independent statement of constants in
  field.py, with `audiences-still-agree` and `prompt-wordings-still-agree` keeping the two
  in step (the task-113 pattern: a row, never a shared object).
- **The argv row reads what `run_field` hands `claude -p`**, not `judge_prompt`'s return —
  the address the defect lived at — driven with `_StubJudge` so the guards and argv build
  execute and nothing is spent; and its mutant drops the pack from the call to prove the
  row can see exactly that.
- **Mutant 3c(a) is pinned red ONLY on non-code aspects** and asserted green on the
  code-seeing ones: "a pin that went red on those too would not be distinguishing a wrong
  prompt from a right one."
- **Check 7 is a variant (rule 15)**: `dropped=4` is a stored number in
  `eval/report.json` — no mutant can manufacture it, and it is the only input reaching
  `allow_truncated`.
- **`STATEMENT_STATES`' third column is WHICH refusal**, which is what makes `undecodable`
  a test: `read_text` defaults to the locale codec, so on a non-UTF-8 host the
  invalid-byte statement would decode and take the mismatch branch — the column asserts
  the branch, not just the refusal.
- **The scene-leak variant asks whether the leak SURVIVES the packer** — every other piece
  of pack text goes through `neutralise`, so only a leaking statement driven through the
  real `build_pack` can show the statement must be written raw (laundering it would leave
  the blinding gate reading text the harness had already cleaned).
- **Check 13's census pins are literals beside the fixture**, and the population-
  accounting row is read off the census's OWN output (each row's n must equal
  same+moved+unbuildable, rows must sum to the headline) — "summing the literals would
  only prove they add up". `_SEES_BY_ASPECT` is kept local so a future `sees` change shows
  as a mismatch here rather than silently reclassifying 63 stored rounds. The census
  refuses exit 2 on an empty/missing root — UNMEASURED, not clean.

### Found: no ticket. Two cosmetic notes

- **The fixture's shape keys are hardcoded to the registry's current assignments**:
  `packs[("frames", False)]` for the argv mutant, `("code", True)` for the blind-shape
  mutants, `("s1_parallax", <fidelity sees>, False)` for the statement states. A future
  change to any aspect's `blind_language` or `sees` that dissolves one of those shapes
  turns this selftest into a KeyError rather than a named row — loud and self-announcing,
  so below the bar, but the coupling is to the registry, not to the fixture.
- **Check 3b calls `judge_facing_texts` three times per text** (iterate, then t0, then t1)
  — two redundant rebuilds per row; SKILL.md reads from disk each time anyway. Nothing
  turns on it.

### Gates at HEAD a239547, unpiped

`blurb_selftest.py` exit 0; `stored_rounds_mutants.py` exit 0 (all 7 mutants caught, each
reddening a named census expectation; control green); and the census producer run LIVE:
`blurb_selftest.py --stored-rounds eval/runs` exit 0 — 97 rounds, 40 code-seeing, 14
hashed, 26 unassessable — **matching `eval/RUNS.md`'s published table (lines 567, 574-577)
to the digit**, population sentences included. The table task 132 bought the producer for
is current.

### Not opened, and the next pass should take one

`eval/judge/prompt_capture_census.py` (998 lines) — verified against every heading: never
a subject. It is the census pass 13 filed tasks/218 against and the file tasks/218's
merged PR #98 just widened to the Bash/Grep half of the capture; reading the widened
census is the closest look anyone has taken at the repair since it landed. Alternate:
`capability_selftest.py` (798, never a subject), then `paired_verdicts.py` (772).

## Pass 20 — 2026-08-30 — `eval/judge/prompt_capture_census.py` (998 lines, read whole)

The pass-19 pointer, taken. Began by closing pass 19's loose end: the pass-18
pointer-verification repair in `.agents/skills/prune/SKILL.md` used the single-format
grep (`^## Pass`), and pass 19 found passes 1-12 headed their entries
`## 2026-08-DD (nth pass) — …` — the repair could not see the oldest third of the log it
checks. The grep is now format-agnostic (`^## `), with the one-pass-later catch recorded
beside it: a check written for the format its author happened to see is an enumeration
again.

### What the file holds, and what holds it up

The latent-null producer for the 2026-08-28 pre-registration: did any stored NON-CODE
judge round read evidence its pack did not carry, through `files_opened` (the Read half)
or — since tasks/218's PR #98 — through `tool_calls` Bash/Grep calls (the second table).
Its defences, each read rather than trusted:

- **Every reason not to classify is a counted state with its own column.** absent / null
  / malformed on BOTH capture keys independently (a round malformed on one half still
  contributes the other — the fixture pins all four directions); 200-char targets
  refused per TARGET on the Read half, 200-char commands refused WHOLE on the Bash half
  (different units, stated where each is counted); no-path a state, never a drop.
  `.get` is used nowhere the absent/null distinction matters — membership checks, after
  that exact collapse was caught in the fixture.
- **The extractor's every branch is a selftest literal**, including the two adjudicated
  corpus false positives pinned AT their commands (`wc -l < <(ls A/frames)` extracting
  the substitution's operand, `find -iname "brief.md"`'s expression value), the PR #98
  review rounds (attached `-epat` spellings; `-e`/`-f` consuming a value only on
  pattern-first verbs, so `cat -e` and `tail -f` still extract), and the redirect
  spellings with a quoted `>` staying data.
- **The stated limits are limits, with compensating controls**: no pack root in the
  record, so classification is by shape and every un-carried read is itemised with its
  full target/command; one shell level, so nested interpreters land in no-path, counted;
  the fixture's outside-the-pack mimic pins the shape-not-location decision as a decision.
- **Exit 2 on an empty population** — UNMEASURED, not clean — and `--runs-root`'s help
  names the worktree trap (a worktree's `eval/runs` is gitignored and empty, which would
  read as UNMEASURED).

### Found — filed as tasks/222

**`bash_operand_paths`' docstring claims the split "at `;`, `|`, `&&`, `||` and
newlines"; the main shlex path does not split at newlines.** shlex emits no token for a
newline, so newline-joined commands arrive at `_segments` as ONE segment — and a
pattern-first verb after the newline loses its pattern-slot protection: demonstrated
in-process, `cat A/audio.json\nsed 's/x/y/' B/audio.json` extracts the sed SCRIPT
`s/x/y/` as a path operand, which classifies `other` — a phantom un-carried leak moving
the pre-registration's 0. The unbalanced-quote fallback DOES split newlines, so the two
tokeniser paths disagree about the same command. Measured before filing: within the
census's population (57 non-code rounds, 437 usable Bash calls) 3 commands hold newlines
and 0 collapse to the shape — every published figure stands; corpus-wide including
code-seeing rounds outside the population, 3 of 1,833 collapse, all in `idiomatic`
rounds, all extracting nothing. Latent, phantom-POSITIVE direction, trigger shape held
by the corpus, third member of a family this file has repaired and pinned twice —
ticket, not log line.

### Gates at HEAD 9e4b24c, unpiped

`--selftest` exit 0 (every classifier and extractor branch answered as stated; fixture
rows for both tables). Live census over `eval/runs` exit 0: **57 non-code rounds, 468
Bash/Grep calls, 31 truncated commands refused whole, 337 no-path, 179 operands, 0
un-carried on BOTH halves** — matching the pre-registered figures to the digit, with
the pre-registration's 0 standing on the widened corpus. Wired at `gates.yml:448` with
its register row (`workflows/README.md:110`).

### Method note

The defect came from asking one question of the tokeniser the docstring invites: what
does the main path do that the fallback does differently? The two paths exist for
unbalanced quotes, and comparing them showed the newline handling is one of the things
that differs — the docstring describes the fallback's behaviour, the code runs the main
one. The population-specific count ran before filing, because a channel whose trigger
the population has never drawn files as a channel, not as a wrong number.

### Not opened, and the next pass should take one

`eval/judge/capability_selftest.py` (798 lines) — verified against every heading
format: never a subject. Pass 7 read `capability.py` whole and verified its selftest's
GATING and two pins (the geometry double-statement, the TRIAL_RE fix) from the outside;
no pass has read the selftest itself. Alternate: re-derive from the import graph.

## Pass 21 — 2026-08-30 — `eval/judge/capability_selftest.py` (799 lines, read whole)

The pass-20 pointer, taken — never a subject; pass 7 read `capability.py` whole and
this suite's gating from the outside, and tasks/210's repair landed with its pins here.
Found nothing to file: the suite is the mutant/variant discipline (rule 15) applied
without a gap, and every expectation is an independent statement rather than a read-back
of its subject.

### What it holds, and what holds it up

The controls for `capability.py`'s whole claim — *every field it declares is reportable
by all four arms* — which its own docstring names as the exact shape this project ships
and retracts: a check that runs, reports success, and could not have failed.

- **Every gate carries positive / MUTANT / VARIANT, and the variants are the discriminating
  half**: film failures spread across stacks stay GREEN (data about submissions), a
  one-stack SUBMISSION failure stays GREEN on the gate but is reported as skew naming the
  arm — the distinction the file exists for. The scene gap test goes further: the same
  one-arm absence is RED when it is a mechanism gap inside the scene population and skew
  when it is a submission failure, and the game population of the same run is GREEN on its
  own — the per-(run, class) grouping pinned from both sides.
- **`census_disagreements` is the task-113 pattern done right**: the census's expectation
  is re-derived from the records by independent logic, never from the census's own
  buckets — AND the fixture's counts are also stated as literals ahead of the run, so a
  wrong re-derivation cannot agree with a wrong census.
- **Excluded is not unread (rule 7, in code)**: the scene record excluded from the
  four-arm claim still fails the gate on an unexplained null; a record of no known class
  at all is swept, counted, and named in a gate failure rather than dropped into a `?` row
  nothing partitions.
- **tasks/210's uniform `stack_cannot` row** — the cell where the asymmetry path has
  nothing to compare against, which read `[]` at exit 0 before the reason scan — is
  pinned RED per record naming field and reason, on every arm that marks it, including on
  SCENE records; and the asymmetry-path string is asserted ALONGSIDE the reason scan in
  the plain mutant, so a repair that replaced one mechanism with the other would be a
  regression only that row sees.
- **The DECLINED register cannot carry a frozen figure**: `FROZEN_FIGURE` ("N of M")
  is refused in DECLINED prose (tasks/182's 62-of-68 literal, which printed two screens
  under a computed header reading 69 — produced-looking rather than produced), the
  `measured_by` names must resolve to `CENSUSES` callables with a negative control
  proving a dead name goes red, and the innocent-text VARIANT pins digits that are not
  corpus figures ("Three of four arms", "12 frames at 640x400") staying green — the
  census's own sentence format ("2 of the 5") cannot trip it either, since `of the`
  breaks the pattern.
- **`STARTER_DEFAULT_GEOMETRY` is a double statement compared by a row**: the four
  starter sources are read for their `VIEW_WIDTH`/`VIEW_HEIGHT` declarations and asserted
  equal to the constant — rule 12's medicine, and the starters (the product) are read,
  never edited.
- **The disk test pins summary-versus-artifact**: a PNG header disagreeing with
  `programmatic.json`'s `sizes` — the pixels win, and the disagreement is recorded in the
  record's notes rather than hidden.

### Below the bar, recorded so the next reader does not re-derive it

- `test_gate_mutant` et al. mutate `Observation` objects from `field_set()` in place —
  safe only because `field_set()` rebuilds fresh records per call; noted as a property a
  future refactor to a shared fixture would break.
- The docstring's `python3 judge/capability_selftest.py` shorthand is the house
  convention (checked against siblings in pass 14), not the tasks/203 class.

### Gates at HEAD a3e0f1a, unpiped

`capability_selftest.py` exit 0, all controls hold, every row PASS; wired at
`gates.yml:321`.

### Not opened, and the next pass should take one

`eval/judge/evaluate.py` (580 lines) — the grading dispatch that wires `judge.py`,
`field.py`, `static.py` and the scene probe into the tiers; named in six passes'
findings (the skipped markers pass 16 counted, the tier-2 dispatch pass 3 verified from
the guard side) and never read whole. Verified against every heading: never a subject.
Alternate: `eval/judge/tier1_census.py` (770 lines), the floor-test producer AGENTS.md
rule 16 names, never a subject either.

## Pass 22 — 2026-08-30 — `eval/judge/evaluate.py` (580 lines, read whole)

The grading dispatch: tier 1 collected as a gate, tier 2 dispatched per task by
`TIER2_INSTRUMENT`, the legacy judge off by default, the pack always built, the record
combined and completeness-gated.

### Sound — the load-bearing list

- **`gate_verdict` is fail-closed on an empty tier**: `total=0 passed=0` is not a pass
  (rule 1); `scored=False` is excluded from the question rather than counted as a
  failure, and the engine project-lock exception is named as the only thing that flag
  can mark (#25). `blocking_failed` drives `score_is_independent`, which is the honest
  way to say "tier 2's 0.00 restates the gate".
- **`TIER2_INSTRUMENT` is a second statement, compared by a guard**: written per task id
  and refused by `aspects.applicability` before anything is driven — a check that cannot
  fail if derived from the class it polices (the task-113 shape, done right). An
  unplaceable task id is refused before pack, score or stored record exist, and the
  error says why ("the trial is paid for by then").
- **The legacy-judge refusal fires at the top of `evaluate()`**, before tiers 1 and 2
  have spent anything — rule 13's guard-the-resource-on-the-path-that-holds-it, applied
  to the third runner path.
- **`STALE_CACHES` is dropped before any command runs**, with the measured defect
  narrated (Unity `Library/` penalising exactly the agents that did what the audio task
  asked) and the call's original wrong placement recorded: a truthful log line from a
  repair after the measurement is indistinguishable from no repair.
- **The judge pack's `except` is deliberately blind and recorded, not swallowed** —
  `build_pack` walks a tree the harness did not write, so the exception set is open by
  construction; the failure lands in `rec["pack"]` with the type name and the
  deterministic tiers still get written.
- **The completeness gate writes before it raises**: the partial record is stamped
  `tiers_complete=false` on disk, then the RuntimeError fires — fail-closed and
  recoverable, the tier-3-died-mid-run failure it was bought with named in place.
- **`SCORING_REGIME` is stamped on every record** and `gate_line` is never silent about
  an absent, unusable or failed gate.

### Examined and judged sound

The dated decision-time figures — the USER RULING's bounded-0.10-vs-gap-0.0622 and
spread 0.000/0.308/0.462; the gate decision's 68-trials/7-failures and 2-of-2 vs 5-of-5
corroboration; the retired judge's $1.75/$42 — all sit in decision blocks that name their
producers (`weight_sensitivity.py`, `tier1_census.py`) as re-runnable, and the producers
re-derive them over the grown corpus (rule 16's companion). The $42 is a straight
per-submission constant, not the retrospective-mean projection that `WR-g1pong-round1-13-15`
withdrew.

### THE FINDING — tasks/223, p4

**`summarise()` reports a renormalisation the gate regime removed, on every default
run.** The NOTE branch (:517-521) keys on `judge_usable`, which is False on every default
run by construction (the skipped tier-3 literal carries `usable: False`), so every
standard evaluation's stdout prints "the remaining weights were renormalised" plus
`reason:` from `overall_excludes_judge_because` — read at :520, set nowhere in the
repository. Under `WEIGHTS = {"playbot": 1.0}` there is nothing to renormalise and the
judge cannot affect `overall` at all; the combine-step comment at :428-431 states the
same stale account two paragraphs above the file's own correct one at :452-459. The
record's arithmetic is correct and no stored number moves — the defect is the reporting
path telling every reader of every summary something false about how the score was
built. Scope guard recorded in the ticket: `judge_usable`'s False-on-skip semantics is
load-bearing at `eval/tools/scene_runner_control.py:340` and must not change.

### Noted, not ticketed

`--with-legacy-judge --no-judge` together silently no-ops the legacy judge
(:571) — the accepted-but-ignored shape, but in the safe direction (no spend), and
`--no-judge` is explicit user intent for exactly that outcome.

### Gates at HEAD ad38dda, unpiped

`docstat.py --sweep` exit 0 (289 docs); `docstat.py --renumbered` exit 0, 0 stale
0 untriaged; `tasks.py check` exit 0.

### Not opened, and the next pass should take one

`eval/judge/tier1_census.py` (770 lines) — pass 21's alternate, the floor-test producer
AGENTS.md rule 16 names, never a subject (verified against every heading: 0 hits).
Alternate: `eval/wholegame.py`, the runner the queue's whole-game trials drive, larger
than anything read so far.

## Pass 23 — 2026-08-30 — `eval/judge/tier1_census.py` (770 lines, read whole)

The floor-test producer behind AGENTS.md rule 16's companion paragraph, and the tool
whose verdict decided tier 1 should become a gate rather than a smaller number (#123).
Read whole; **judged sound; no ticket.** This is the cleanest census in the repo —
every defect class this log has recorded elsewhere is already defended here, usually
in a form naming the incident that bought it.

Sound, with the failure each property answers:

- `--runs-root` is **required**, and the requirement names its failure: a worktree's
  empty gitignored `runs/` would report zero failures everywhere — the
  instrument-reporting-itself shape of rule 9, at the exact moment the tool exists to
  catch (rule 12: the address is an input). The root is printed beside every count.
- The search is **depth-independent** (the #126 repair) and counts what it skips —
  `Library/`, `Bee`, agent-authored trees — with the skipped count printed, never
  dropped: a skip nobody counts is the defect being replaced.
- **One row per submission**, deduped on the graded work tree rather than the report
  path, with superseded gradings held out of the headline **and printed** with their
  agreement/disagreement — and when the deduped verdict and the pooled verdict
  disagree, **both are printed**. On this corpus they do disagree (FLOOR-ONLY deduped,
  DISCRIMINATES pooled, on the superseded wg-g4c-capgate rows), and the tool shows the
  disagreement instead of choosing a winner (rules 4 and 9).
- Blocked and playbot-unusable trials are held out of the variance question, with the
  holdout count visible per group rather than silently pooled in.
- `ordering_change` asks the weight question **at w1=0** — the endpoint
  `weight_sensitivity.py` deliberately excludes by sweeping the open interval. The
  gate regime sits outside that interval, so FLIPS=0 over [0,1) never said anything
  about it; this sibling is the only producer that does. REVERSED is the outcome that
  counts against the change, and it has its own positive control in the selftest.
- Selftest: 27 checks, every fixture's answer stated in advance, a **positive control
  for the headline** (a constructed group must flip to DISCRIMINATES — the guard
  against an always-FLOOR-ONLY check, which is rule 15's "can it still pass" half),
  and six mutants each of whose module globals is restored before the assertion runs.
- `OLD_W1 = 0.31` is kept as a literal, not imported: the scheme it reproduces is
  gone from `evaluate.py`, so there is nothing to import it from — a number whose
  provenance is a comment is honest about that.

Live at HEAD ffe5294, unpiped: 69 stored submissions, 85 gradings on disk, 16
superseded and held out, 0 skipped; blocking 2x2 = 2 blocked at t2=0.00 / 0 blocked at
t2>0, 0 unblocked-failed at t2=0.00 / **6 unblocked-failed at t2>0** — the figure the
AGENTS.md rule-16 paragraph quotes as "6 failed nothing tier 2 depends on", reproduced
by its producer; ordering reversed 0, coarsened 3, identical 8; 11 groups, 0 varying
under both tiers; **VERDICT: FLOOR-ONLY** (pooled: DISCRIMINATES, printed beside it).

### Below the bar, recorded so the next reader does not re-derive it

- `blocking_2x2` reads `float(r["t2"] or 0.0)` — an **absent** tier-2 would enter the
  t2=0.00 cells as if measured, where `groups()` holds `None` out. Not reachable in
  the stored corpus today (every stored grading writes a `tier_scores` block; the 2x2
  cells total the same 8 failing rows the headline counts). It becomes reachable the
  day any writer emits criteria without tier scores, and the cells it would inflate
  are precisely the ones that corroborate the blocking decision — log line, not
  ticket, because the data the channel would eat does not exist yet.
- The per-group `blocked` column is `len(g) - len(live)`, which also holds out
  playbot-unusable trials — a wider holdout under a narrower name. The 2x2 is the
  report that separates the two reasons; read the column as "not in the variance
  population", not as "build-blocked".

### The pointer discipline, fired at the writer this time

Pass 22's alternate (the paragraph above) named `eval/wholegame.py` — **void**: that
file was the subject of the 2026-08-27 (second pass) entry, and pass 23's own
pre-flight grep found the two headings it heads. The step-3 grep had been run against
the pointer this pass FOLLOWED (`tier1_census.py`, 0 hits) and not against the
alternate it PROPOSED — the check covered the claims being consumed, not the claims
being written. Third instance of this exact failure (pass 13's alternate, pass 17's
pointer), and the first committed by the session that had just re-derived the rule.

### Gates at HEAD ffe5294, unpiped

`tier1_census.py --selftest` 27/27 exit 0; live census figures as above;
`docstat.py --sweep` and `--renumbered` and `tasks.py check` re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/weight_sensitivity.py` — the other rule-16 producer, cited in three
passes' prose (16, 22, 23) and never a subject (verified against every heading
before writing this: 0 hits). Alternate: `eval/judge/regrade_wholegame.py`, the
offline re-scoring path `evaluate.py`'s docstring leans on, likewise verified 0 hits.

## Pass 24 — 2026-08-30 — `eval/judge/weight_sensitivity.py` (379 lines, read whole)

The other rule-16 producer: the sweep whose FLIPS=0 answer retired the
`0.31/0.69` split it was built for. Read whole; **judged sound; no ticket.**
Where tier1_census was the cleanest census, this is the best-documented tool in
the judge tree — its docstring does the one thing almost no tool here does:
**it pre-states what its own output must not be read as.**

Sound, with the property each one answers:

- The docstring names its own misuse and forbids it (:12-17): the sweep covers
  the OPEN interval deliberately, the gate scheme IS w1=0, so **`FLIPS=0` was
  not evidence for the gate change and must not be quoted as if it were** — and
  it names the tool that asks the endpoint question (`tier1_census.py`). It
  also states the output is not a stack ranking (`DECISIONS.md` bars that) and
  its orderings are not results. A reader cannot reach the wrong conclusion
  without passing the sentence that says not to.
- **UNIDENTIFIABLE is a distinct verdict, not folded into STABLE** (:158-163):
  tier 1 constant means "the weight is inert HERE and we cannot tell whether
  0.31 was right", which calls for the opposite action from "the weight is
  defensible by not mattering". This is #92's finding as a type in the return
  value, not a paragraph in a log.
- The **positive control states its geometry** (:242-257): a reversal crosses
  a tie, so a clean flip is THREE orderings and not two — the selftest asserts
  the sequence A>B, A=B, B>A and the tie's location near w1=0.5. (The comment
  records that asserting two was the test's own error and the sweep was right.)
- The **endpoint false positive has a regression guard** (:295-308): the fixture
  is "the shape of 3 of the 10 real stored groups" that the first version's
  closed-interval sweep called FLIPS. The fix is tested both ways — not a flip,
  AND the endpoint orderings are still computed and printed beside the verdict,
  because "everything ties once tier 2 is dropped" is a fact about tier 1's
  discriminating power worth seeing. Between this tool (endpoints shown,
  excluded from the verdict) and tier1_census (asks AT the endpoint), the pair
  covers the whole interval with no gap and no double count.
- `--runs-root` is **refused, not guessed** (:331-350), naming #60 and the
  worktree-empty-`runs/` failure in the help text, exit 2 with the repair in
  the message — the same rule-12 pattern as its sibling, independently written.
- An unusable playbot tier is **excluded as bias, not noise** (#25 named, :79-83),
  flagged through and counted per group in the printed head.
- Ties are **grouped, not broken by name** (:107-117), with the reason stated:
  tie→strict and strict→tie are different events, and the sweep must tell them
  apart.
- Partition by (run, game) **before** sweeping (rule 4 in the docstring) — which
  is why this reports 11 small groups rather than one confident line.
- Its address is `artifacts/*/eval/report.json`, **one file per trial**, so the
  superseded-grading dedup tier1_census needs does not arise here; a re-grade
  rewrites the same file and leaves one record.

Live at HEAD 843e67d, unpiped: selftest 12/12; `--all --runs-root <main>` over
the stored corpus: **groups: 11, FLIPS=0, STABLE=3, UNIDENTIFIABLE=8** — the
figure AGENTS.md rule 16 publishes ("says the same thing at 8 of 11"),
reproduced by its producer. Sampled groups confirm the informative shape: the
matrix groups print tier-1 distinct values 1 (hence UNIDENTIFIABLE) with the
w1=1 endpoint collapsing to a four-way tie — tier 1 never discriminated
anything there, visible in the tool's own output.

### Below the bar, recorded so the next reader does not re-derive it

- The comment at :65-66 names `_orderings`, "which records the bracketing w1
  pair" — **no function of that name exists**; the mechanism is `sweep`'s
  `seen` list and `_ordering` (singular). Same-file comment rot, the weak
  local cousin of the #38 class: a reader is 40 lines from the real name.
- `load_trials` drops a report missing either tier key (:88-89) and **counts
  the drop nowhere** — the "a skip nobody counts" shape tier1_census prints
  and this one does not. Measured today: 69 report.json files under
  `eval/runs/*/artifacts/*/eval/`, 69 with both keys, 0 skipped (the same 69
  tier1_census counts — the producers agree on the population). An
  all-missing directory exits 1 visibly; a *mixed* one narrows the group
  under a printed n that cannot show it.
- Homogeneity is claimed from the (run, game) partition alone, and the stored
  records carry **no turn-budget field at all** (measured over all 69 record
  key sets), so a budget-mixed group would be indistinguishable here rather
  than mixed. The #35 heterogeneity lived in run-configuration records this
  tool never reads. Not reachable on today's corpus; the claim "one
  homogeneous group" in `sweep`'s docstring is currently true by absence of
  the field, not by a check.

### Gates at HEAD 843e67d, unpiped

`weight_sensitivity.py --selftest` 12/12 exit 0; `--all` figures as above;
`docstat.py --sweep`, `--renumbered` and `tasks.py check` re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/regrade_wholegame.py` — the offline re-scoring path the pass-23
entry named as alternate, re-verified against every heading before writing
this entry: 0 hits. Alternate: `eval/judge/paired_verdicts.py`, the producer
two withdrawal-register entries name as their replacement, if it has not been
a subject — verify before following, the discipline pass 23 finally paid for.

## Pass 25 — 2026-08-30 — `eval/judge/regrade_wholegame.py` (119 lines, read whole)

The offline re-scoring path: rebuilds `report.json`'s `overall` from the stored
per-tier JSON instead of paying for re-runs that would also re-roll the
stochastic judge tier. Read whole; **one defect, ticketed (task 224, p4,
dispatched this session)** — the rest is sound, and three of its properties are
the project's hardest-won rules implemented in a *writer*, which is rarer than
in a checker.

Sound, with the rule each one answers:

- **It rebuilds from the tier files, not from the embedded copy** (:38-39) —
  "the embedded copy is what we are correcting". A repair that read its own
  subject's claim as input would be circular; this reads the primary sources
  and rewrites the derived record (the `rewrite_reports` pattern the docstring
  cites).
- **A regrade across a regime boundary is refused by default** (:51-62), in
  the best blocked comment in the judge tree: "A REGRADE ACROSS A REGIME
  BOUNDARY IS NOT A REGRADE, IT IS A RE-SCORING." The boundary is detected from
  the record's own `scoring_regime` field — stamped by `evaluate.py`, compared
  against the live constant — not from a path or a date; the refusal printout
  names what to record in `eval/RUNS.md`; and task 29's `established_by`
  records the guard as part of the regime landing, so this is a bought control
  that has held.
- **The unmeasured-tier guard is recomputed, never inherited** (:74-84), with
  #31 named as the class: a regraded report predating `playbot_usable` would
  silently lose the flag and the guard would stop firing — excusing trials
  back into the aggregates, which is fail-open, the direction that costs the
  result. A writer that re-derives a guard rather than copying the record
  forward.
- **Dry run by default**, `--write` required, and the summary line states
  which mode ran (:103-104).
- **Atomic write** (:27-30): pid-suffixed temp + `os.replace` — the
  artifact-mid-write ambiguity of rule 2 has no window here.
- The **diff is printed per trial** with `*` on every row that would move and
  the judge (diagnostic) column beside it: the operator sees what the rewrite
  does before and while doing it.
- `rec.pop("overall_no_judge", None)` (:86) — the legacy second statement of
  the score is **removed**, not left stale beside the new one. One statement
  per live record.
- The gate verdict is **recomputed from the rebuilt tier data** (:71), and
  `judge_is_diagnostic_only = True` is a constant of this regime with the
  regime field stamped into the same record — a future reader can tell the
  constant from a measurement.

Live at HEAD a26c7ac, unpiped: on the pre-regime run
(`wg-matrix-2026-08-13T14-02-50`) all 24 reports are detected as crossings,
held back, "LEFT ALONE", with the RUNS.md instruction printed, and the
old-vs-new diff shows exactly the rows the 0.31 weight used to move; on the
post-regime run (`wg-scene-s1ts-2026-08-25`) one row reads old==new 0.8333
with judge diagnostic 0.000. Dry-run writes nothing — mtime and size of a
`report.json` unchanged across a run.

### The defect: success on nothing, at exit 0

Pointed at a run directory holding no reports — and at a path that does not
exist — the tool prints the empty table plus "0 report(s) inspected (dry run;
pass --write)" and **exits 0, on both shapes, reproduced unpiped**. Missing
dir, empty dir and real run dir are indistinguishable from the output, and
exit 0 reads as completion; under `--write` the failure direction is the worst
one this tool has: **a regrade believed done was not done.** The siblings
refuse exactly this input (`weight_sensitivity.py` exits 1 on an empty
population; `tier1_census.py` requires `--runs-root` naming the failure), and
**nothing tests this file at all** — no selftest, no fixture, no mutant
anywhere in the repository; its only pins are doc references (README:292's
usage line, task 197's verification that the line parses). Filed as
**task 224**; the ticket states what must still FAIL after the fix, not the
mechanism, and pins the regime-guard behaviour with controls so the repair
cannot disturb it.

### Below the bar, recorded so the next reader does not re-derive it

- `float(tiers[k].get("score", 0.0))` (:46) reads an **absent** score as 0.0,
  and an empty tier file is treated as `{}` (:45) which also reads 0.0 — the
  absent-vs-zero shape pass 23 recorded for `tier1_census.py`'s 2x2. Measured
  today: 207 non-empty tier files under `eval/runs/*/`, **0 missing a score
  key**. Unreachable in the stored corpus; would matter only on truncated or
  foreign input, and the dry-run diff is the visibility if it ever happens.
- `judge_is_diagnostic_only` is hard-coded True (:73). True under this regime
  by construction; the `scoring_regime` field written beside it is what keeps
  it honest if the regime ever changes again.

### Gates at HEAD a26c7ac, unpiped

Both dry-runs and the two empty-shape controls as above; the tier-file census
(207/0) as above; `docstat.py --sweep`, `--renumbered` and `tasks.py check`
re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/paired_verdicts.py` — the producer two withdrawal-register entries
name as their replacement (WR-paired-verdict-tie, WR-paired-evidence-diff),
verified against every heading before writing this: 0 hits. Alternate:
`eval/judge/anonymise.py`, the anonymiser whose dropped-manifest made #62
findable, verified the same just now — the two candidates I checked besides
these (`census.py`, `field_ranks`) are prior subjects and were rejected.

## Pass 26 — 2026-08-30 — `eval/judge/paired_verdicts.py` (773 lines, read whole)

The producer built to retire a hand-done recount: the 2026-08-22 within-cell
figures four documents quoted had no command that computed them, and
reproducing `436` a day later meant reverse-engineering which tier set it had
summed. **Judged sound; no ticket.** Of the producers read in passes 21-26,
this is the one the others should be measured against — its three refusals are
each tied to a specific wrong published number, and the docstring corrects its
own draft in public ("This said 'six times' until it was re-derived").

Sound, with the property each one answers:

- **The tier set is part of the figure** (refusal 1): `436` reproduces only by
  summing all three tiers, 156 of which are LLM-judge criteria at weight 0.00;
  the deterministic recount of the same run is 280/4. The corpus pins assert
  BOTH readings and the **156 delta between them** — "were these equal, the
  tier set would not matter and the first refusal would be decoration".
- **A cross-game sum is a count, never a rate** (refusal 2): the pooled rows
  are printed — they are what the published figures were — labelled "a COUNT,
  not a rate", with the reason (criterion counts differ per game; a pooled
  rate weights the biggest game hardest) and the per-game rates above.
- **A cell whose trials did not both complete is not a cell** (refusal 3):
  terminal reason comes from the BUILD record (`trials/<tid>.json`), never the
  report (#22's reasoning); a missing JSON reads `unknown`, never `completed`;
  and the wg-g4c-capgate arms — byte-identical diff lists, 3× the highest real
  cell's rate — are excluded by name. Today's live run shows both nested arms
  reached and their cells excluded.
- **`--runs-root` is required and refused, not guessed** (:754-766), and the
  empty population **exits 2** with the path named — the exact shape task
  224 (pass 25) found missing from `regrade_wholegame.py`. Same repository,
  same discipline, one tool has it and one does not; the ticket cites the
  sibling and this pass confirms the sibling's behaviour live.
- **The walk is `**/`**, naming the nested arms a single `*/` misses, pinned
  by an `r6/armA` fixture (:63-65, :670-671).
- **Every record the walk reaches but cannot classify is named**: undecodable,
  non-mapping, unusable trial id, malformed tier block, criteria of wrong
  shape, `id` without `passed`, non-string ids — with the hash-collision
  reason stated (`true` and `1` hash the same, so either would let two
  different records share one key). "A record the module cannot name is a
  counted problem with its name attached." The skip channels are announced
  empty over the stored tree by every selftest run that prints no note — the
  dated docstring claim re-derives itself each run.
- **RECORDED vs SCOREABLE is kept distinct**, and the four quadrants are all
  pinned: a criterion only one side recorded is a suite difference (r2); a
  malformed record is still a record, so one malformed side is not a suite
  change (r9); a suite difference stays counted when the side that recorded it
  recorded it malformed (r10); both sides malformed reaches no denominator but
  is named (r8). The skip label's own scope was corrected — "not counted
  anywhere below" was wrong for skips — and the corrected label is pinned.
- **The positive control, mutants and variants are labelled as such** in the
  check names, and one check knows what its own mutant would look like: r7's
  skip check counts to 2 because "were `rows == []` the only expectation, a
  walker that stopped globbing would pass this fixture too".
- **Evidence-diff is built in as the independence control**: without it, a
  verdict tie is equally consistent with the grader having read the same file
  twice — rule 9's question, asked by the instrument itself.
- The **4 deterministic verdict differences are named per criterion** in the
  live output — a count you can open, not just a number.
- Selftest without `--runs-root` runs the synthetic half and **says the pins
  did not run** — a skipped section that announces itself, never one that
  reads as run.

Live at HEAD b0e0004, unpiped: `--selftest --runs-root <main>/eval/runs` —
**38/38 checks, 5/5 corpus pins**, every published figure reproduced with its
tier set (wg-matrix ALL_TIERS 436/5/332, DETERMINISTIC 280/4/176; wg-audio48
232/0/120 both); the full report over the stored tree names the nested
excluded arms and all 4 deterministic differences. Exit 0.

### Below the bar

Nothing that survives scrutiny. The only candidate — pooled "0 paired" rows
under excluded-cell runs reading, to a skimming reader, like a measured
perfect tie — is exactly what the "EXCLUDED CELLS (not counted anywhere
below)" header above each one exists to prevent; the label is the defence and
it is pinned. The corpus pins hard-code figures for named runs and would fail
loudly if those records were ever legitimately re-graded — which is a pin
doing its job, not a defect.

### Gates at HEAD b0e0004, unpiped

`paired_verdicts.py --selftest --runs-root <main>` 38/38 + 5 pins exit 0;
full-report exit 0; `docstat.py --sweep`, `--renumbered`, `tasks.py check`
re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/anonymise.py` — the anonymiser whose dropped-manifest made #62
findable four matrices late (the audit-trail paragraph in AGENTS.md is about
it), verified against every heading before writing this: 0 hits. Alternate:
`eval/judge/disclosure.py`, the rule-11 locator whose two-questions-two-counts
caveats are load-bearing in AGENTS.md and worth reading at the source,
verified 0 hits just now.

## Pass 27 — 2026-08-30 — `eval/judge/anonymise.py` (461 lines, read whole)

The anonymiser the AGENTS.md audit-trail paragraph is about: the dropped-file
manifest it returns is the capture that made #62 findable four matrices late.
Read whole; **judged sound; no ticket.** Driven live at the function level, not
only through its selftest.

### Examined and judged sound, with the probe that held each one up

- **The manifest is the audit trail, and its always-0 counter is deliberate.**
  `files_dropped_for_length` is 0 by construction since #69 removed the cap and
  is kept so the completeness gate can ASSERT it — a budget reintroduced later
  cannot truncate silently. The counter of an absence that must stay absent,
  kept instead of deleted as vacuous. `field.py`'s `pack_matches_manifest` is
  the independent reader of the same property (disk set == manifest set), and
  the docstring names it.
- **The destination guard is rule 12 in a writer** (`:356-364`): refuses dest
  == submission/starter and dest an ANCESTOR of either, because "this is the
  one place where getting the address wrong is unrecoverable". Verified live
  both shapes refused. The condition matches its message — my first probe
  built `dest` INSIDE the submission and called the pass a defect; the guard's
  stated purpose is a dest that CONTAINS the submission (clearing deletes the
  evidence), and building into a subdirectory of the submission mutates
  nothing it does not own. The probe was the wrong shape; the guard is right.
- **The #69 numbering property holds live**: two passes into one dest with the
  submission shrunk between them — zero stale files, disk==manifest, labels
  renumbered. The docstring's claim (a pack is a NUMBERING, not a set) is
  enforced by the clear, and the corpus damage that bought it (wg-g4c's 23
  unaccounted files over nine passes) is named where the clear was added.
- **The segment matcher is the closed-class rule in code** — a vocabulary of
  38 one-arm names matched as IDENTIFIER SEGMENTS in any case convention, with
  `_match_window` refusing one-letter segments (what stops `Vec3.UnitY`
  spelling `unity`) and `_LITERAL_TOKENS` holding the two forms segmentation
  cannot save (`three` the numeral, `Node2D`). Every negative control in its
  own comment reproduces live: immunity, UnitY, tscn, bestScore,
  is_three_dimensional, bare `node` — all clean; CARGO_MANIFEST_DIR,
  WinitPlugin, crates/sim, bevyengine/bevy#6183, TypeScript, gdlintrc — all
  found. The substring search the comment measures this against would have
  rewritten `immunity` 54 times.
- **`find_stack_names` is the same code path as the rewrite, deliberately** —
  a detector with its own vocabulary would agree with the rewriter by
  construction and measure nothing; the compensating control is the selftest's
  sweep over REAL stored pack text (85 packs, 0 leaking, run green today).
- **The selftest is gated and measures in both directions**: 38 names × 3 case
  forms with 0 surviving, 38 drop-one-name mutants with 0 silent, 128 real
  leak lines 0 surviving, **400 innocent lines 0 corrupted** (the variant half
  — a scrubber that also rewrites `immunity` would die here), idempotence over
  528 lines, then the stored sweep. Wired at `gates.yml:298`.
- **Identity is defended twice, on purpose**: `_TRIAL_ID_RE` (the answer-key
  shape `g4_platformer__godot__t1`) and `_WORK_PATH_RE` (absolute work-tree
  paths baked into scripts), because "one of them is a list of directory names
  and this project has learned what a list-shaped guard misses" — the `.codex`
  skip is the list; the regexes are the property. `verify_blind.py` consumes
  all three (`:145`, `:150`, `:162`).
- The shuffle seed is `sha256(submission_id)` — per-submission, deterministic,
  re-derivable; ordering cannot systematically favour a stack, and a re-pack
  reproduces byte-identical order.
- **`exclude_origins` (starter drift)** is passed in explicitly and the caller
  must show its working — the comment derives the correct set as (rebuilt pack)
  MINUS (stored manifest) MINUS (legitimately returning length drops), so the
  filter cannot silently widen.

### Below the bar, recorded so the next reader does not re-derive it

- **`except OSError: continue` at `:410-411`** drops an unreadable file from
  the pack with no count anywhere — an ERROR read as a filter decision (rule
  7's shape; every other drop here is a deterministic class). Probed live with
  a `chmod 000` code file: absent from manifest and disk, nothing reports it.
  **Censused before judging it**: `find eval/runs -type f ! -perm -400` → **0
  files** in the entire stored tree. Latent, no held trigger, silent → log
  line under the pass-12 policy, not a ticket.
- The other uncounted drops — `DROP_NAMES`, non-`CODE_EXT`, empty files,
  AppleDouble `._` — are deliberate presentation filters, and the manifest
  records what the judge actually sees; only the OSError case converts an
  error into a filter.
- "Bee" (named in `tier1_census.py`'s skip list) is Unity's `Library/Bee`
  toolchain tree — covered here by `SKIP_DIRS`' `Library`. Checked because the
  two skip lists overlap imperfectly and the census comment does not say so.

### Gates at HEAD 8ba1eb2, unpiped

`anonymise_selftest.py` 7 checks, 0 unmet, exit 0; function-level probes as
above (guards, numbering, matcher controls, OSError probe); `docstat.py
--sweep`, `--renumbered`, `tasks.py check` re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/verify_blind.py` — named twice as an alternate (passes 27 and the
entry above), verified 0 heading hits before writing this. Alternate:
`eval/judge/repack.py`, also verified 0.

## Pass 28 — 2026-08-30 — `eval/tools/disclosure.py` (896 lines, read whole)

The rule-11 locator: the tool built because "31 of 75 completed trials had
written a disclosure and no grader, report or gate opened one". **One defect,
ticketed (task 225, p4, dispatched this session)** — the rest is sound, and
its selftest is one of the two-directional exemplars the log keeps naming.

### The pointer had the wrong directory, not the wrong file

Pass 26's alternate named `eval/judge/disclosure.py`; the file lives at
`eval/tools/disclosure.py`. The subject was still valid — the heading grep is
path-agnostic and no heading had ever named any `disclosure.py` — but the
path was found wrong on contact, by following the import graph
(`wholegame.py:68`) instead of the pointer. Recorded per pass 14's rule: a
pointer's accuracy is part of what a later pass inherits. Third wrong-pointer
instance this log (pass 13's alternate, pass 17's pointer, pass 22's
alternate) — this one a directory, the others files that were already read.

### Found — filed as tasks/225

**Both scanners silently drop artifact directories that hold no
`agent_result.json`.** `scan_run` filters on `is_file()` and `scan_tree` on
the glob, so such a trial produces no row at all — while `read_trial` carries
a branch for exactly this state (`:419-420`, status `no_message`, reason "no
agent_result.json stored") that is unreachable from every CLI path. Measured
before filing: **98 artifact dirs under `eval/runs/*/artifacts/*/`, 91 carry
the file, 7 do not** across 3 runs — one of them (`s1_parallax__ts__t0`) a
fully graded trial with `submission.tar.gz` and `eval/` present and no
closing message stored. Reproduced live: `--run-dir` on
`wg-audio-2026-08-14T12-29-42` prints **"11 trials" for a run holding 15
artifact dirs**; the whole-tree table prints `wg-g4` as `3 / 4 / 4` for a
6-dir run; `wholegame.py:1062` inherits the short count. The tool's whole
ethic — no_message is UNMEASURABLE never silence, 0 is refused — names this
population as the one that must never be invisible, and the channel makes it
invisible. Diagnostic-only, so p4; ticket states the property (every artifact
dir yields exactly one row; trials count == dirs reached) and pins the
refusals, the corpus pins and the 25/15 figures as must-not-move.

### Examined and judged sound

- **Three values, never two** — `classify()` refuses null, empty and the
  API's limit string as `no_message`, pinned by unit checks AND three real
  corpus rows (`MUST_BE_NO_MESSAGE`) covering both limit-string variants.
- **The field choice is load-bearing and tested on real data** — the selftest
  proves a head-of-message disclosure invisible to the 3000-char tail, and
  its corpus control asserts the whole message still holds more passages than
  the tail for the exact trial (#49's run) whose disclosure sits at character
  0 of 3912.
- **Direction 1b of the selftest is the dead-or-duplicated check**: removing
  ANY single cue family must silence at least one variant, or the family is
  dead and looks alive from outside. Combined with direction 1's
  empty-BOTH-lists mutant (so neither family can cover for the other) and
  `disclosure_mutants` deleting each cue at source, the cue set cannot rot
  silently.
- **Written from the property, with every widening and narrowing named** —
  the closed `_GAP` set (three stored false positives fixed by closing it),
  `_PERF` past-tense-only (the habitual that broke the archive-arena2d
  control), first-person `_WEAK`, `NOT_A_REPORT`'s three sentence properties
  scoped to the starter family alone because applying them to CUES "would
  silently drop disclosures".
- **The two never-pooled families** carry their own denominators and the
  tasks/94 correction (26 vs 25) is told where the pooling happened.
- **The two documented dead zones are recorded, not hidden**: `residual`
  fires on 0 of 90 stored messages (kept because it is what a future run's
  required section would produce) and `recipe_red` locates no row the other
  starter cues do not — each with its variant-only load-bearing test named.
- **Refusal discipline**: both scanners raise rather than report an empty
  population, `--skip-corpus` prints "a non-measurement, not a pass", and a
  missing corpus exits 2. `wholegame.py:1063-1065` catches the raise and
  prints the same distinction.

### Below the bar, recorded so the next reader does not re-derive it

- A heading passage includes its first 3 body lines, and those lines are not
  marked claimed — a body sentence carrying a cue appears twice (inside the
  heading passage AND as its own sentence). Trial-level located/quiet counts
  are unaffected; the doubled sentence is visible verbatim twice in the
  output, so it self-announces.
- `--run-dir X --json` silently ignores `--json` (it is consulted only on the
  tree path). Accepted-but-ignored, rule 13's companion shape — but any JSON
  consumer fails loudly on the text it receives instead.
- `--trial` and `--full` `json.loads` without the `DisclosureError` wrap — a
  corrupt file is a bare traceback, loud and pre-output, where `read_trial`
  wraps the same read.
- The CAVEAT/docstring figures (75 readable, 90 messages) are dated hand-pass
  numbers; the live tree now holds 91 messages (one more rust since
  2026-08-23). Expected drift of a dated figure recorded with its date — the
  hand-classified columns cannot be re-derived by the tool, which is why the
  CAVEAT quotes both.

### Live at HEAD 332c467, unpiped

`--selftest` exit 0 with corpus (variants, mutants, three values, truncation
control, all corpus pins); published locator figures reproduce exactly —
unverified 25, starter 15, per-stack 3/11/3/8; the 98/91/7 census and the
11-of-15 reproduction as above.

### Gates at HEAD 332c467, unpiped

`docstat.py --sweep`, `--renumbered`, `tasks.py check` re-run at commit time.

### Not opened, and the next pass should take one

`eval/judge/verify_blind.py` — the blinding gate, named as alternate in the
two entries above, verified 0 heading hits before writing this. It consumes
`anonymise`'s exports and the pack's rendered text; task 200 found the skills
invoking it bare at exit 2. Alternate: `eval/judge/repack.py`, verified 0
hits.

## Pass 29 — 2026-08-30 — `eval/judge/verify_blind.py` (261 lines, read whole)

The blinding gate. Three checks on trial trees — the RUBRIC canary, rubric
reachability from any ancestor, the criterion vocabulary — plus `check_pack_skill`
over judge packs. Run-matrix and evaluate-run invoke it as a gate on every run,
unpiped, exit code preserved; both carry task 200's fix (measured: both skills
copy starters to a blind dir and pass `"$blind"/s/*/`; bare invocation exits 2
with `give trial directories, --packs, or both`).

### Judged sound, measured live

- **Positive control**: starter copies per the skill's own recipe — exit 0, BLIND,
  84 criterion ids, 5 trial trees.
- **Negative controls, built by hand — all fire.** Canary GUID planted in a trial
  tree: exit 1 naming the file. `ball.wall_bounce` planted in the ts tree:
  exit 1, CRITERION ID. `RUBRIC.md` planted at an ancestor (`s/judge/`): exit 1,
  RUBRIC REACHABLE, with the move-outside-the-repository message.
- **The vocabulary covers the graders.** 84 rubric ids vs 48 `Criterion(`
  literals across `eval/judge/*.py`: the only defined-but-unvocabularyd id is
  `stub.ok`, an `audio_selftest.py` fixture, not a criterion. The harmful
  direction — a real criterion id the scan would miss — is empty today.
- **The 4 MB silent skip holds nothing.** `_files` drops text files over 4 MB
  without counting them; every file over 4 MB under `eval/runs/` outside
  SKIP_DIRS is `.tar.gz`/`.diff`/`.patch`, none in TEXT_EXT. Latent channel,
  no held data — recorded, not ticketed.
- Fail-closed where it claims to be: `canary()` SystemExits if RUBRIC loses its
  CANARY line; `scan()` records an unreadable file as a hit; the `--packs` half
  can already fail in `blurb_selftest.py` (fresh pack green, leaky pack red).
- One unreachable shape, recorded one clause: the ancestor walk breaks before
  scanning the filesystem root's children.

### The defect — filed as task 226 (p3)

**The trial-tree half has no can-fail proof anywhere in the repository.** Grep
for the canary across every `eval/judge/*_selftest.py`, `*_mutants.py`,
`*_control.py`: zero hits. The register's census cannot see the file either:
`ci_minutes --controls` censuses `_control`/`_mutants`/`_selftest` stems and
scripts declaring a `--selftest` mode — `verify_blind.py` is in neither
population, and it has no `left out` row (consistent with the table's own
rules, which is exactly why nothing asks). So a scan that stopped being able to
fail prints BLIND at exit 0 on every future run and nothing disagrees — #39's
shape, pre-emptively, on the gate behind README's blinding claim. This pass
proved by hand, in three commands, that all three checks can still fail; that
proof exists nowhere the next session can run it. Task 224 was this same class
offline (a tool nothing exercised); this one sits on every run.

Also folded into the ticket: check 3's `and ids` silently no-ops on an empty
vocabulary — the selftest's floor pin (84 today) is what catches it.

### Examined and judged sound, no ticket

`ci_minutes --controls`' exclusion machinery (`.github/workflows/README.md`
:357-470, read whole): closed stem class, `--selftest` population decided on
each script's syntax tree not the word, exclusion = name AND reason, the table
found by its header cells, bare-name ambiguity goes red naming both candidates.
`blurb_selftest.py`'s `verify_blind --packs` pins (can-fail and green both
asserted on real files). No action on any of them.

**Next pass pointer:** `eval/judge/repack.py` (353 lines), named as alternate
in the pass-28 entry, re-verified 0 heading hits before writing this.

## Pass 30 — 2026-08-30 — `eval/judge/repack.py` (353 lines, read whole)

The tool that re-packs a stored run's judge packs with the starter-drift exclusion set
COMPUTED rather than guessed (#77 is the failure it exists to prevent). Judged **sound**.
The design that earns it: the exclusion formula's two terms both come from the same
packer, so the tool never trusts their difference alone — every excluded file must ALSO
be byte-identical to its blob in the work tree's `starter baseline` commit, and the
`--starters` override is read only as a fallback while the baseline commit stays the
anchor.

### Live verification, all unpiped, all at main HEAD 94d7905

- **Positive control with a known-good answer**: `wg-scene-s1ts-2026-08-25` (1 submission,
  work tree alive, starter frozen since 2026-08-23) with `--starters eval/starters` →
  exit 0, `stored=24 rebuilt=24 exclude=0 corroborated=True labels_reproduce=True` —
  exactly the shape a no-drift run must produce.
- **Refusal axes, each fired live**: work trees deleted → all 8 `wg-g4c` submissions
  REFUSED "no work tree on disk; cannot corroborate", exit 1. Recorded starter path gone
  (a deleted agent worktree) → REFUSED naming the RECORDED path and the missing override,
  rule 12 in the refusal text. `pack.manifest` stripped from a COPY of the run → REFUSED
  "UNRECOVERABLE, not empty". Override starter replaced by the work tree's own authored
  content → all 24 origins REFUSED as orphaned, "the starter moved toward the submission",
  exit 1. Truncated run name → exit 2 "`run` takes a PATH, not a run name" (#96's guard,
  still holding).
- **The override self-corrects, three probes**: polluting the override with a NEW file →
  exit 0 (nothing compares against a file the work tree lacks). Modifying a packed file's
  starter copy → exit 0 unchanged, because `hud.ts` is AUTHORED and starter pollution
  cannot flip authored work. The mechanism in both: the drop rule compares work-tree bytes
  to the starter, but the CORROBORATION compares to the baseline commit — a wrong override
  can mislabel template as authored, and the baseline then certifies the exclusion is
  exactly the untouched file, which is the correct outcome, not a silent pass.

### Examined and judged sound, no ticket

- **plan/write asymmetry**: `plan()` tolerates a missing `pack.submission_id` (falls back
  to `{game}-{name}`) while `write()` indexes it directly — a KeyError on `--write` for a
  pack that the dry run passed. Bounded against stored data: 44 of 44 packs with a
  manifest carry `submission_id`, so the shape is unreachable today. Latent and loud
  (crashes, no corruption); logged, not ticketed.
- **Register invisibility**: `repack.py` has no `_control/_mutants/_selftest` stem and
  declares no `--selftest`, so `ci_minutes --controls` cannot see it — the same class as
  pass 29's finding about `verify_blind.py`. The difference is the duty cycle:
  `verify_blind` gates every run and its silent loss would be invisible; `repack` is a
  manual recovery tool whose failures are loud (exit 1, printed refusals, `packcheck`
  after), ran once, and its refusal machinery was re-proven by hand here. No `--selftest`
  demanded.

### What the refusals taught about stored history

The 2026-08-23 `wg-g4c` re-pack is now **unrepeatable**: its work trees are gone, so a
re-run refuses all 8 submissions. That is the tool working — an exclusion set that cannot
be corroborated must not be computed, and the refusal is what stands between the stored
result and a re-pack that would reclassify template code as authored. The `repack-2026-08-23-stale-files-removed/`
directory flagged by `verify_blind --packs` is the deliberate audit copy of removed leaked
files (#95), and `packcheck`'s CARGO/Rust hits are #131's recorded unrepaired stored-pack
state — neither is a defect, and `--packs` gates packs at build time, not over stored
history.

**Next pass pointer:** `eval/tools/evidence_set_control.py` (366 lines), one of the four
RECORDED-bare files in the register's first population — gated nowhere, named only in the
left-out table, so it gets no CI attention at all. 0 heading hits, re-verified before
writing this.

## Pass 31 — 2026-08-30 — `eval/tools/evidence_set_control.py` (366 lines, read whole)

One of the four RECORDED-bare files — named in the register's left-out table, gated
nowhere. The pass question: does the recorded reason still hold, and can the controls
still fail? Judged **sound**, no ticket.

### Live verification, all unpiped

- **Bare**: exit 0, 11/11 controls, `git classified 7,465 paths ignored across the
  suite` — the suite-level positive control is armed, not the degenerate one-bucket
  pass. The real-trees cases run with `require_both=False` for a documented reason
  (a rust work tree genuinely contains nothing its .gitignore names), and the
  adversarial + synthetic cases carry the per-case control instead.
- **All four mutants killed**: `dir_only`, `anchored`, `depth`, `last_wins` each
  exit 0 `mutant killed`. These mutate the imported module in-process — nothing on
  disk changes, nothing to restore.
- **The recorded reason still holds**: `--runs-root /tmp/does-not-exist` → exit 2.
  The register's row says the control is `UNMEASURABLE` without `eval/runs/`, which
  is gitignored and never in a CI checkout — that is why it is recorded rather than
  gated, and it is still true.
- **Rule 12 by construction**: the control takes `RUNS = ES.DEFAULT_RUNS_ROOT` from
  the module it controls, so both address one tree unless a caller overrides one;
  no path is spelled twice.

### Examined, latent, logged

The one defect shape found: `git_partition` un-quotes C-quoted paths with
`unicode_escape`, which turns git's octal escapes into mojibake (`\303\251` → `Ã©`,
not `é`) — a non-ASCII filename would disagree between git's side and os.walk's side
and redden a correct control. Bounded: **0 non-ASCII filenames** in any work tree
the control reads, and the failure direction is a RED control (costs attention,
never silently passes). Logged, not ticketed. The synthetic precedence fixture
remains the load-bearing piece: its own comment records that three of the four
mutants were INERT against real .gitignore files before it existed — the variant
half of rule 15, written where the next maintainer will read it.

**Next pass pointer:** `eval/tools/precampaign_smoke.py` (357 lines), touched by
merged PR #105 three days ago and never read by a cleanup pass — the most recently
changed unexamined tool. 0 heading hits, re-verified before writing this.

## Pass 32 — 2026-08-30 — `eval/tools/precampaign_smoke.py` (357 lines, read whole)

The once-per-campaign pre-flight: 4 in-process assertions plus 16 subprocess rows, each
carrying a comment naming the defect that bought it (#56's dead `plan`, #60's work-root
drift, #108's 0/0 axis, #98's pristine-red godot gate, #100/#114's capture policies).
Judged **sound**. Its honesty is structural: the docstring and the closing banner both say
a green row means the gate is ALIVE, never that it PASSED, and the `prompt_guard` row
names itself "LIVENESS ONLY - scratch, deleted; NOT the launch artifact" so the 2026-08-17
misreading (#45, #57) cannot recur by resemblance.

### Live verification, all unpiped, from `eval/` as the file runs its rows

- `--list` exit 0, 19 rows. **Address census over the file's own references**: all 14
  script paths exist, the hardcoded `runs/wg-arena3d-2026-08-15T12-46-30` resolves, and
  `frame_parity --run` over it exits 0 (`PARITY: every submission filmed at the same
  size`) — the "known-uniform" claim in the row's comment is still true.
- **All 4 `plan` rows exit 0** — the command that was dead for an entire regime (#56),
  which is why this file exists, still runs.
- 6 cheap selftest rows re-run directly, all exit 0: `audio_selftest`, `capture_selftest`,
  `runner_capture_selftest`, `sequential_selftest`, `agent_harness_control`,
  `hook_audit_control`. The in-process assertions pass: work roots agree, 4 games declare
  end-condition criteria, 3 frame criteria geometry-invariant, 14 tier-1 bounds declare
  populations (none class-dependent).
- **Not re-run here, stated**: `starter_parity` (outlived a 2-minute shell budget; the
  smoke allows it 900s), `parity_selftest` and `starter_gate_control` (machine-heavy —
  15-20 min of `just warm`/`just verify` per stack). None of the three is CI-gated
  (grep over controls.yml: no matches), which is the point — this file is their only
  schedule. The disclosure and docstat rows were verified at task 225 and in every gate
  run this week.

### Two probe errors of mine, recorded because both are rule-12 firing at me

I first ran `frame_parity` from the repository root, read its exit 2 as a defect in the
file, and reported it as a found defect mid-pass. The address is cwd-relative BY DESIGN —
the smoke runs every row with `cwd=eval`, where it resolves and passes. Then `timeout`
turned all 7 selftest rows into uniform 127s: macOS has no GNU `timeout`, and seven
identical failures across seven different tools was the instrument reporting itself
(rule 9). Nothing in the file was wrong; both scares were mine.

### Examined and judged sound, no ticket

The file is not in the register's census and cannot be: it is a runner, not a selftest,
and its own liveness is enforced by `PROTOCOL.md` line 11 mandating it before a matrix —
the correct mechanism for a thing whose class is "run once per campaign".

**Next pass pointer:** `eval/tools/runstat.py` (412 lines) — the tool #60 is named for,
the one whose false-quiet sentence this file's `check_work_root_agreement` guards; it has
never been read whole by a pass, and the work-root move that broke it is three findings
deep. 0 heading hits, re-verified before writing this.

## Pass 33 — 2026-08-30 — `eval/tools/runstat.py` (412 lines, read whole)

The run diagnostic #60 is named for — partition by terminal reason, then watch drivers,
engines and work trees. Judged **sound**. Every defect class this project has named is
already embodied in it, and the docstring carries the trap list as a list of things the
tool refuses to do rather than as history:

- `files_touched` runs `find -mmin` and returns **-1 on probe failure**, never 0, and the
  report prints `PROBE FAILED` for it — the `|| echo 0` shape rule 3 forbids, caught by
  construction.
- A missing `--run-dir` raises `SystemExit` naming the path: absence must not read as
  "not started".
- `read_trials` raises `cost key moved, do not guess` on a `total_cost_usd` field —
  schema drift refuses rather than silently reading nothing.
- `report()` partitions by terminal reason, and when a group mixes trials that ran with
  trials that never took a turn it **suppresses the pooled mean** (rule 4), keeps `n` at
  the population, prints the ran-subset mean separately, and writes
  `NO READABLE FIGURE in k record(s)` where a zero would lie.
- Drivers are found by matching the python interpreter actually running `wholegame.py`
  and taking its `--run-dir` — `pgrep -f runstat`-style name matching would match this
  tool itself; engines are matched by process NAME, never the command line.
- `WORK_ROOT` carries the two-defence comment; the merged "no trees found / no writes"
  sentence is two sentences, and the NONE FOUND arm states outright that it says nothing
  about the agents — the exact #60 repair.
- Every report prints the `tokenvalue.DEFINITION` line (#159): the tool cannot emit a
  `$` figure without its definition travelling with it.

### Live verification, all unpiped, from `eval/` where `runs/` resolves

- `--selftest` (added with the aggregation hardening): **15/15 pins green, exit 0**. The
  mutant is the old `c or 0.0` expression itself, evaluated beside the real aggregation
  on the same records; the pin asserts the mutant WOULD have printed a 5.00 mean and the
  real output does not. Fixtures are written tmp-then-`os.replace`, the same policy as
  every artifact here — "a fixture is not a reason to keep a second policy".
- Newest run (`wg-scene-s1ts-2026-08-25`, the held task-145 scene run): a
  `harness_kill_external` trial renders as an `n/a` row, the group prints
  `NO READABLE FIGURE in 1 record(s)` with no total, and the definition line prints. The
  fail-closed shapes are live, not just pinned.
- Negative control `--run-dir runs/no-such-run-dir`: exit 1,
  `runstat: no such run directory: runs/no-such-run-dir`.
- The NONE FOUND arm: `wg-audio48-2026-08-14T19-55-47` (16 completed trials, one group,
  total 486.27 mean 30.39 over the readable population) prints
  `work trees: NONE FOUND under /Users/stefano/game-research-work/...` with the
  "says nothing about the agents" warning — both arms of the merged-sentence defect seen
  live and distinct. A first control aimed at `runs/wg-matrix-2026-08-13` also refused:
  that name is not a directory directly under `eval/runs/`, so the refusal is the tool
  naming its address, not a defect.

### Examined and judged sound, no ticket

`--watch` re-reports the same `--run-dir` each tick, which is correct for the only thing
it is for (watching one run to completion). The selftest is registered in the
`ci_minutes` census the same way the other tool selftests are; CI green on the last push
is the register's own assertion, and `--controls` is re-run below as part of this pass's
gates.

**Next pass pointer:** `eval/tools/cost_census.py` (1,910 lines) — the producer for the
cost result, the between-stack range over the within-cell floor, grouped per
(run directory, game) and never pooled; `runstat` reads the same `agent.cost_usd` key it
aggregates, and no pass has ever read it whole. 0 heading hits, re-verified before
writing this.

## Pass 34 — 2026-08-30 — eval/tools/cost_census.py (1,910 lines, read whole)

The producer for the cost result: between-stack range over the within-cell floor, grouped
per (run directory, game) and never pooled; an ordering adjudication over three units
(run, game, connected component) by exact permutation with a refusal before allocating past
2,000,000 assignments and a lazy walk under it.

**Sound on its own terms.** Every guard checked live in source and exercise: records are
`isinstance`-dict-tested before field reads (a JSON string `"a game"` substring-matches the
presence test); `_is_number` refuses bool/NaN/Infinity (all three parse as JSON literals);
every refusal is a named `CostCensusError` naming its file and field; a 1-trial cell
contributes nothing rather than a 0 gap; CLI-reachable thresholds (<2 stacks, <2 trials per
cell) refuse rather than report; exclusions are counted by label (terminal reason,
`harness {name}`, `no cost_usd`), never dropped; ranks are rank vectors, never mean rank
(rule 4); `range_exceeds_floor` keeps its comparison when the floor is zero (ratio would be
undefined); `pearson` strict-zips, returns None not 0.0, refuses <3 points; the permutation
path counts the identity assignment so p can never be 0; the drop-one-cluster floor is
computed, not closed-form (ties break the closed form); leader margins are decided by rank,
not `means[0]` — the tie-on-name bug is documented in its O5. The selftest writes expected
values as literals, pins the renderer separately from the producer, and pins child-process
RSS growth (25 MB ceiling) because the permutation runs in a child.

**Live reproduction over the stored tree, all unpiped:** the producer reproduces the
docstring's every figure — 7 qualifying groups; between-stack range 42%–254%, lowest
wg-g4c platformer; 5 of 7 groups exceed their floor, the below-line group 96%
(wg-matrix/g2_tetris3d); ts cheapest in 5 of 7; r(cost, turns) 0.653–0.971; exclusion table
absent 4, api_error 9, budget_exhausted 1, harness prime-agent 1, harness_kill_external 1,
max_turns 1. `--ordering` matches its docstring: run unit p_any 0.0156 (its own floor),
drop-one-cluster 0.0625; game unit 0.0469 < α; component unit floor 0.25 — "the question is
unasked"; ts leads 5 of 7, beats floor in 0 of 5. Missing-tree control exits 2.

**The defect, and it is between producers, not inside either.** The two producers disagree
on the same tree today: `census.py` counts WHOLE-GAME **91**, `cost_census.py` reads
whole-game **92**. Root cause read from the record:
`eval/runs/wg-scene-s1ts-2026-08-25/trials/s1_parallax__ts__t0.json` carries BOTH
`game: s1_parallax` AND `task_class: scene`. census.py classifies off `task_class_of()`
(its selftest Direction 8 plants exactly this both-fields shape and pins it to SCENE);
cost_census tests `WHOLEGAME_KEY not in d` — field presence. cost_census.py:120 still says
"Same test as census.py, deliberately", and the test stopped being the same when the first
scene record landed on 2026-08-25. Second channel, same shape: `NOT_A_RUN` is defined
independently at cost_census.py:124 and census.py:144, identical today, nothing asserting
it — four lines below the file's own TOKVAL_HARNESS comment that names exactly this failure
shape ("restating the rule in both, with nothing asserting they agree, is how one tree
comes to have two totals and neither reports a disagreement"). **No cost figure moves**:
the record is excluded before grouping (harness_kill_external) and its cost is None, so
every range, ratio and p above is unchanged — the damage is the population count and the
exclusion table's scope, which a future scene record grows wrong by N. **Task 227 filed**
(one shared classifier + asserted NOT_A_RUN, both-fields selftest pins, mutant turned red,
producers re-run agreeing); finding to allocate when it lands.

How it was found matters: no gate reads two producers against each other, so the
disagreement was invisible to every check that ran green over both files — rule 12's shape
(a partition restated in two files, a comment promising they match) caught by reading the
pair whole, which is what these passes are for.

**Live verification this pass:** `cost_census.py --selftest` → 0 failures; the producer
and `--ordering` runs above; missing-tree control exit 2; `census.py` over the tree for the
91-vs-92 measurement; the disputed record read whole.

**Next pass pointer:** `eval/tools/manifest.py` (859 lines) — the append-only manifest
guard (#77 → #93): the resource stated as "any durable record of what a measurement was
configured to be is append-only", write path reserving the name with `O_EXCL` and
superseding on collision, an `audit` mode sweeping eval/runs, selftest in
`manifest_selftest.py`. The audit-trail exemplar AGENTS.md cites, and no pass has read it
whole. 0 heading hits, re-verified before writing this.

## Pass 35 — 2026-08-30 — eval/tools/pr_review_state.py (1,123 lines, read whole)

Pointer moved before the pass: pass 34 pointed here at `eval/tools/manifest.py` (859
lines), but PR #107 touches that file, so a read of it now would be superseded at merge.
`pr_review_state.py` had 0 prior coverage (`grep -cin pr_review_state` over this log
before this entry: 0). This is the rule-12 tool born of task 127 — the poll that takes
its address (`--pr` AND `--branch`) as arguments every invocation, after 16 polls of
`not yet` at exit 0 about another agent's pull request.

**Sound on its own terms, and the strongest selftest discipline in the tree:**

- The address is asserted, not assumed, and every refusal names its cause — the A-rows
  pin the FIRST WORD of each (`WRONG PR`, `NO HEAD SHA`, `NO BRANCH`, `STALE HEAD`,
  `EXPECTED HEAD NOT A FULL SHA`), including a variant that would pass an `in` test
  (A3, branch prefix) and one that passes a length test (A6, 40 non-hex characters).
- The `raises` helper requires a NAMED refusal: a stray traceback is a red row saying
  "raised X instead of a named refusal", and no-raise is red too. Where a cause can
  drift it is asserted by `firstword`; `raises` alone is used only on single-arm rows.
  This is task 227's masking lesson (a pin satisfied by a refusal of the wrong cause)
  already applied, before that lesson was written — recorded, not a defect.
- `attempt` turns a crash into a red VALUE, so a mutant dying on a traceback is
  diagnosed rather than silently scored as caught (the `drop_field` lesson, task 92).
- The failed-round arm (#185) keeps the REAL bytes — `meshery/meshery#21612`'s
  `coderabbitai[bot]` failure comment — because this repository's own instance was
  rewritten in place and is gone. B19 pins it at the head it names, AND pins
  `by_comment=1` beside it: the second row is WHY the old check read a dead round as a
  clean landing. Failure blocks are dated by the block's OWN last sha, so a previous
  round's failure beside this head's clean summary does not suppress (B20, B21), two
  blocks in one comment do not let the second overrule the first (B24), and a block
  naming no sha still counts — fail-closed where the evidence is missing (rule 7, B23).
- `--ignore-notice` governs STOPPING, never landing, and the variants prove it cannot
  become "wait for ever" in either of its uses (F7, F10: silence still expires loudly
  on the quiet bound).
- The wait is silence-bounded (quiet 1200s, flight 3600s latched), and F1b pins the RED
  half of the bound change: the retired 15-minute clock returns UNRESOLVED on the
  19m26s review that actually landed (task 130's timeline).
- E1c is the row that is easy to forget exists: every gh call carries a finite timeout,
  because handling a timeout is not the same as asking for one — without it the
  conversion above is unreachable and every gh call blocks forever.
- The census refuses at its own listing cap (H0: `gh pr list` honours `--limit`
  silently, so a full page means TRUNCATED), and refuses per-row when its two API reads
  disagree about the branch (H2) — the address assertion carried into the bulk mode.
- I1 pins flag FORWARDING from the CLI into `wait_for`: every function-level row calls
  it directly, so replacing the kwarg with a constant would leave them all green while
  the flag did nothing. G3 compares the result contract against a SECOND literal rather
  than the same object — the task 113 lesson, stated at the row.
- The printed count is what ran (`ran[0]`), never a constant; 100 checks, 21 of them
  variants.

**Measured live, 2026-08-30, unpiped:**

- `--selftest` → exit 0, `ok (0 failures, 100 checks, 21 of them variants)`.
- Positive control with a known answer held in advance: `--pr 107 --branch
  task-227-one-partition-two-producers` → exit 0, `LANDED_COMMENT by_review=0
  by_comment=1 in_flight=0 failed=0 notice=Review limit reached`, head
  `12ce5d9871...` — byte-for-byte the answer this session already held.
- Negative control on the same address: `--branch task-999-wrong-branch-on-purpose` →
  exit 1, refusal names both branches and says "You are polling somebody else's pull
  request."

**Found: nothing.** Cleared whole: docstring and guard/verdict tables, `_gh` /
`parse_pages` / fetchers, `check_address`, `alert_headings`, `failed_rounds`,
`classify`, `poll`, `render`, `_emit`, `wait_for`, `census`, the full selftest, and
`main` (whose `--ignore-notice` help text carries the exclusion-not-discard reasoning
for the comment arm: CodeRabbit posts NO review object when it finds nothing
actionable, so the arm is narrowed one observed mechanism at a time).

Next pointer: `eval/tools/mergeable.py` (942 lines; `grep -cin mergeable` over this
log before this entry: 0; heading verified — "Is this pull request safe to merge?
Green is not the question that failed"). Note for the next pass: PR #107 does not
touch it.

## Pass 36 — 2026-08-31 — eval/tools/mergeable.py (942 lines, read whole)

Pointer picked at the end of pass 35. `grep -cin mergeable` over this log read 1
before this entry — pass 35's own pointer line; no pass had READ the file. It is the
merge gate born of the #12/#13 incident (both pull requests green against a main
containing neither; merging #13 broke main), and like pass 35's subject it is a rule-12
descendant with its lessons pinned at the rows.

**Sound on its own terms:**

- Two gated questions, and the second is the one that catches the incident: required
  checks green AT THE CURRENT HEAD, and the branch not behind its base. `mergeable_state
  = behind` is treated as corroboration only, because GitHub returns it only where
  up-to-date branches are required — the commit comparison is pinned as the real test.
- The #42 row is the design's best move: when every named check passes and GitHub still
  refuses (`required_conversation_resolution`), the tool reports ITS OWN blocker list as
  INCOMPLETE and says do not merge on its say-so. `REFUSING_STATES` is the closed class
  the host returns; the named checks are the enumeration, and the row exists because the
  enumeration has already been incomplete once.
- The review-state half is reported and never gated, with `DECISIONS.md` carrying the
  reason: the squash merge itself makes the final head unreviewed, so gating on it fires
  where nothing is wrong. PR #62 decided this — its status description reads
  `Review completed`, byte-identical to a really-reviewed pull request's, at a head no
  round finished on. Description strings are an open class; the tool QUOTES them, never
  parses them, and names `pr_review_state.py` as the producer of the verdict.
- Rule 12 throughout: `REVIEWER` carries the `[bot]` suffix with a mutant proving the
  suffix-less filter selects nothing from the recorded reviews; the head passed to the
  status endpoint is the already-read head, never re-resolved; and the commit list must
  END AT THE HEAD before a gap measured in it means anything — `/pulls/<n>/commits`
  caps at 250, and counting in a truncated list is a number in range, the most
  dangerous shape a broken measurement takes.
- Selftest: green-first row; the known-answer pair #60/#63 recorded as verbatim API
  payloads and read against BOTH ("a reading that answers the same way on both is
  reporting the instrument"); mutants patch THIS module's globals, with the first-run
  SURVIVED recorded at the row (an `import mergeable` under `__main__` builds a second
  module object nothing executes); `REQUIRED` is pinned against the workflows that
  exist.

**Measured live, 2026-08-31, unpiped:**

- `--selftest` → exit 0, 75 rows, all ok.
- Independent expectation derived first: `git rev-list --count 12ce5d9..origin/main` = 3
  (main moved twice after the PR's last push).
- `mergeable.py 107` → behind by 3, refusal names the gap, exit 1 — agrees with the
  independent count. Rollup: `controls SUCCESS`, `gates SUCCESS`, `CodeRabbit SUCCESS —
  'Review rate limited'`, quoted rather than judged on.

**What the live run found that the queue view could not:** 1 unresolved review thread on
`eval/RUNS.md` (`coderabbitai`, trivial — state the wallclock section's current
contract instead of its history). Checked against the branch head before acting: the
asked-for text is present at 12ce5d98, where `wallclock.py` "takes its tree walk from
`census.py` and its population partition from the one shared classifier in
`eval/agent_harness.py`" — the agent's round-2 change, never formally resolved because
the review limit meant no round to re-read it. Replied on the thread with that evidence
and resolved it; independent re-read: 0 unresolved threads. **This mattered:
`required_conversation_resolution` would have refused the merge the moment it was
approved.** The #42 shape, live, on our own pull request.

Merge-path note for when approval comes: the PR is 3 commits behind main, so the
sequence is update branch → CI green at the NEW head → squash (a green run at the old
head is a statement about a commit nobody is merging — this tool's own first lesson).

**Found: nothing wrong in the file.** Cleared whole: docstring, `_gh`, `pr_facts`,
`base_head`/`behind_by`, `check_problems`, `staleness_problems`,
`unresolved_threads`/`conversation_problems`, `agreement_problems`, `head_statuses`,
`rollup_rows`/`unrequired_notes`, `reviewer_reviews*`, `branch_commits`, `review_notes`,
`report`, the full selftest with its three recorded pull requests, and `main`.

Next pointer: `eval/tools/tasks_control.py` (2,307 lines; `grep -cin tasks_control`
over this log before this entry: 0; heading verified — "Can `tasks.py` still lose a
value, mis-report a success, or warn where nothing is wrong?"). PR #107 does not touch
it.

## Pass 37 — 2026-08-31 — eval/tools/tasks_control.py (2,307 lines, read whole) — 1 DEFECT FOUND AND FIXED

Pointer from pass 36, no deferral needed: PR #107 does not touch this file. Read in two
chunks, judged, then verified live.

**Sound.** The strongest control discipline in the tree, and nothing below it was found
wanting: positive controls read as blobs from the commits that PREDATE each repair
(`466d436^`, `ea9f853`, `dce1172`) so every green row is provable as observable; expected
bytes stated in this file, never imported from the subject (the `_expected_block` comment
carries the measured mutant that survived when they were); directions 2/3 run the subject
as a subprocess in a real main-plus-worktree pair because the defects only exist where
`TASKS` and `ROOT` disagree; `_blob` does not `.strip()` (the `"\n\n"` stub lesson);
direction 11's three-valued git answers pinned at both the consumer and the producer;
11c's patch-id cache keyed on the pair with the moved-main variant, failures not cached;
the torn-write injection asserts its own needle occurs exactly once; the `_set` row
demands the whole expected file, not a diff (the `zip` truncation lesson); the live-queue
censuses re-run rather than quoted and shrink loudly on unreadable tickets; exit 3
fail-closed ("Never read 3 as a pass").

**THE FIND — a dead count assertion on the exact defect direction 2 exists for.** The
current-copy `add` row asserted `len(created) == len(created)` — a tautology — while its
name claims "exits 0 and prints the created path" and the defect the direction exists for
is #94's "the retry files a SECOND task". A future `add` that wrote two files at exit 0
would have kept every row green: row 1's count term was dead, `ok_path` reads only the
last printed line, and row 2 asserts `bool(created)`, true for 2. The positive control
(line 402) asserts `len(created) == 1`, proving the harness CAN observe the count — the
green row just never asked.

Two repairs were needed, and the second is the lesson:

1. The obvious fix, `len(created) == 1`, is **false by construction**: the positive
   control runs first on the same scratch pair, so by the time the current copy is probed
   the whole-queue listing holds 2. The full harness run caught my own first fix red on
   the healthy copy — and that construction is almost certainly how the tautology was
   born: an `== 1` that could not pass, abandoned as `== ==` instead of re-aimed.
2. The fact the row names is what THIS invocation created, so `probe` now returns the
   DELTA (files beyond a pre-invocation snapshot) and the row asserts `len(created) == 1`
   on that. Both probes get sharper: the positive control's `== 1` now means "wrote
   exactly one file" rather than "the queue holds one file".

**Verified, both halves, in the state the harness actually runs** (positive control ON —
my first probe used `--skip-prefix` and so exercised a state the full run never produces,
which is why its green half passed and the full run then failed; rule 14's shape, on me):

- healthy repo `tasks.py`, control ON: all three `add` rows ok=True;
- a double-create mutant (second exclusive write before `return 0`, injected via
  `--tasks-py`'s mechanism into a tempdir copy, needle count asserted == 1 first): the
  current-copy row FAILS while row 2 stays green over its two files — the demonstration
  that before the fix nothing in this direction asked;
- full run after the repair: **140 measurements, 0 FAILED, 0 NOT CHECKED, exit 0**,
  shared queue untouched (226 before, 226 after).

Next pointer: `eval/tools/tasks_mutants.py` (711 lines; `grep -in tasks_mutants` over
this log before this entry: 0 as a subject — line 660 is a different context; heading
verified — "The mutants of `tasks.py` that `tasks_control.py`'s rows are supposed to
catch."). The natural companion: this pass read the check whole; next pass reads the
thing that asks whether the checks can still fail.

## Pass 38 — 2026-08-31 — eval/tools/tasks_mutants.py (740 lines; 711 read whole, then 2 mutants ADDED) — 1 GAP FOUND AND CLOSED

Pointer from pass 37, no deferral: PR #107 does not touch it. Read whole in one read,
judged, then verified live — the first pass in this loop to end with the suite itself
changed rather than only judged.

**Sound.** The runner is built to the same standard as the control it grades, and nothing
below it was found wanting: the queue address is IMPORTED from the subject, never
re-derived (`QUEUE = _t.TASKS`; two `parents[n]` expressions differing by one is how rule
12 gets paid for a second time); every anchor has its occurrence count asserted == 1
before injection, and the refusal names the hazard (a no-op mutant reports a pass for a
check that never changed); the baseline runs first through the same tempdir, the same
symlink and the same `--tasks-py` path, its greenness gates everything below, and it
additionally asserts every `kills` entry matches some live row — so a renamed row becomes
a failure here rather than a silent "the mutant survived", which would read as a defect
in `tasks.py`; failed rows are parsed from the TABLE and not the summary, measured via
the task-113 truncation that turned every round-trip row into the four characters
`round`; unnamed reds are reported, not failed, and that is measured (9 of 21 mutants
produced them at task 120 — a shared mechanism cut by several mutants at once — with the
ACCEPTING rows named as what actually guards the wrong-reason catch); the runner's own
positive control is inert BY CONSTRUCTION (a trailing comment on `MISFILED_MARGIN`'s
line, which `margin_up`/`margin_down` already prove is killable) so it cannot expire the
way the pre-`tasks/106` real mutation did; `--selftest` also asks the drifted-anchor
refusal; #134 is asserted at the end over bytes, not promised in a comment; three
addresses (subject, control, queue) print on every run.

**THE FIND — direction 2's `add` path had no mutant at all.** Pass 37 repaired the
current-copy row's dead count assertion and proved the row can go red with a hand-built
double-create mutant — a proof that lived in this log as prose and decayed back to
unfalsifiable the moment that session ended. That is precisely the state this file's
docstring exists to end (task 82: five mutants killed "by hand, in one session", leaving
behind a sentence). The positive control cannot carry the claim: it runs the PRE-FIX blob
from git, which no mutation of the current copy can reach, so the repaired row's only
runnable killer had to live here. The address row had the same asymmetry — `note`'s half
had `note_writes_worktree`; `add`'s half had nothing.

**The fix, two mutants** (inserted after `note_writes_worktree`, their mechanism sibling):

- `add_double_create` — a second exclusive write of `body` after the first, at exit 0:
  #94's retry-files-a-second-task shape, restored.
- `add_writes_worktree` — the open pointed at `ROOT / "tasks"` instead of `TASKS`. In
  the scratch pair the worktree has NO `tasks/` directory (verified in `_scratch_pair`
  before writing it: a fresh `git init` repo whose worktree checks out README only), so
  the write dies in a traceback at exit 1 over a queue that received nothing — the
  fail-closed shape, and both current-copy rows must notice it.

**Verified, every half measured and none predicted:**

- Full PRE-change suite at HEAD: baseline green (140 rows, 0 FAILED), **41 mutants,
  0 survived**, inert mutation SURVIVED with 0 red, drifted anchor refuses, `tasks.py`
  byte-identical before and after. (Notably it was ~25 min of block-buffered silence
  while alive — `ps` over the tempdir path, not the output file, is what showed it
  grading mutant 40 of 41.)
- `--mutate add_double_create --selftest`: CAUGHT, **1 red of 140, 0 unnamed** — only
  the row naming it, with the address row correctly still green over its one file —
  plus selftest ok.
- `--mutate add_writes_worktree`: CAUGHT, **2 red of 140, 0 unnamed** — both
  current-copy rows, as designed.
- Named-rows arithmetic checked rather than assumed: 64 distinct `kills` names, up 2
  from 62; the set deduplicates by design and 17 names are shared across mutants.
- Gates: `docstat.py --sweep`, `docstat.py --renumbered`, `tasks.py check`,
  `ci_minutes.py --controls` — all exit 0.

Next pointer: `eval/tools/findings_control.py` (496 lines; grep over this log before
this entry: 0 mentions of any kind; heading verified — "End-to-end controls for
`docstat.py --findings`, the producer for the findings count."). Three passes have now
sat inside the tasks toolchain; this is the sibling control harness for the findings
count and has never been looked at.

## Pass 39 — 2026-08-31 — eval/tools/findings_control.py (496 lines, read whole; 1 guard ADDED) — 1 LATENT HAZARD FOUND AND CLOSED

Pointer from pass 38, no deferral: PR #107's changed files (census pair, manifest,
wallclock, harness, RUNS) do not include it. Never once a subject before this pass.
Read in one read, judged, then verified live.

**Sound.** The known answer stated in this file before anything measures it
(`KNOWN_COUNT`/`KNOWN_LO`/`KNOWN_HI`); every fixture case carries its expected exit AND
the output substring naming the reason, so a green exit over the wrong mechanism cannot
pass; the green cases additionally parse the JSON payload and assert the producer
REPORTS the stated count and highest — "an exit code alone would pass on a tool that
counted nothing and found nothing to disagree with" is written in the code, and the
`.get`-with-default alternative is named and rejected (rule 3's sibling); the
`--count-triggers` variant asserts the SHAPE of the output (shipped row 0, quantifier
row ≥1) because an extractor that has stopped matching reports 0 on every row, which is
also what a clean corpus reports; `_git` drops ALL `GIT_*` variables with the
enumeration lesson stated in place ("the next reader meets `GIT_COMMON_DIR`") and is
written out rather than imported so the control stays an independent reader of the
subject; `hostile_git_env` carries its own red half — it reproduces the vulnerable shape
against a decoy index before asserting `_git` is immune, "without which the green one is
a check that cannot fail"; REAL TREE is skipped under a mutant with the reason printed
(it would grade the unmutated tool); the mutants run on COPIES, with the in-place-patch
lesson recorded in `build`'s docstring. The all-mutants run was read per-mutant, not
only at its summary: failure counts vary (3,1,2,2,1,1,1,1,9) and every mutant reddens
exactly the rows naming its mechanism — `count_from_the_index` and
`no_index_reconciliation` both redden only COUNTED TWICE, which is the pair of survivors
that row was built for, per its own docstring.

**THE FIND — the mutant anchors are checked for PRESENCE, never for UNIQUENESS.**
`build` applied `src.replace(old, new, 1)` behind `if old not in src` — so an anchor
occurring twice mutates whichever copy came first, silently, and the controls then grade
a mutation this file did not name. Both sibling runners assert this and refuse:
`tasks_mutants._write_copy` ("an ambiguous one mutates whichever copy came first. Fix
the anchor.") and the torn-write injection in `tasks_control` (needle count asserted ==
1). The hazard is latent — all 9 live anchors were measured at exactly 1 occurrence in
`docstat.py` before the fix — and the red half was demonstrated before fixing: a probe
mutant anchored on a string occurring twice applied to the first copy with no refusal.

**The fix**: `src.count(old)` before replace; `n == 0` keeps the existing refusal
verbatim; `n > 1` refuses with the sibling's wording and the measured rationale named.

**Verified, red first:**

- RED (before the fix): probe mutant on a 2× anchor applied silently, first copy only,
  1 line mutated of 2 occurrences.
- GREEN (after): the same probe refuses, naming the count; the absent-anchor refusal
  still fires with its original message; plain controls **21 controls, 0 failed,
  exit 0**; `--all-mutants` **9 mutants, 0 survived, all caught, exit 0**.
- Task 228 filed: the two refusals are pinned by nothing permanent (this file has no
  `--selftest`; `tasks_mutants` pins its drift refusal that way) — the ticket carries
  the `ci_minutes --controls` selftest-census consideration.

Next pointer: `eval/tools/heartbeat.py` (402 lines; grep over this log before this
entry: one passing mention, the "manual by design" line — never a subject; heading
verified — "The hourly heartbeat's measurement, as a file rather than a shell string in
a monitor."). The monitors have driven every one of these passes for a week; the tool
that decides "is new work happening" has never itself been read.

## Pass 40 — 2026-09-01 — eval/tools/heartbeat.py (402 lines, read whole) — 1 STALE COUNT FIXED IN AGENTS.md, 1 ADDRESS GAP FILED (task 229)

Pointer from pass 39, no deferral. Never once a subject before this pass (one passing
mention, the "manual by design" line). Read in one read, judged, then every count
verified against an independent measurement, unpiped.

**Sound.** The work-tree refusal is a property probe — `git rev-parse
--is-inside-work-tree` asked AT the main checkout — not the `core.bare` marker, with the
second confounder (`core.worktree`) named, both settings reported as facts beside the
repair, and the why-not-a-hook asymmetry reasoned in place (`git commit` exits 128
before any hook runs, so the state the guard detects is the one a hook cannot fire in).
`TASK_METRIC` is a map asserted equal to `tasks.STATUSES` on every run (rule 12 in
code), legacy aliases mapped, and unknown statuses bucketed into `tasks_unknown` rather
than dropped — the 3-of-5 incident is recorded where the fix is. `_tracked_files` runs
`ls-files` with `check=True` rather than returning a plausible zero; the symlink skip
(`.claude/skills`, mode-120000, task 114) is deliberate and distinguished by
`is_symlink()` from the warned tracked-but-unreadable skip; outputs are counted, not
source (`judge_rounds`/`graded_submissions` via `rglob`), for the recorded reason that
judge rounds land inside existing run directories and move no source count.

**Verified live — every count reproduced independently:** tracked 872 = 872
(`git ls-files`); findings 194, highest #212 (agrees with `docstat.py --findings` run at
HEAD); task statuses todo 1 / inflight 0 / in_review 1 / in_testing 1 / done 224 /
unknown 0, matching `grep -h '^status:' tasks/*.md | sort | uniq -c` exactly; runs 16 =
top-level `wg-*` directories; judge_rounds 97 = `find eval/runs -name '*__seed*.json'`;
graded_submissions 85 = `find eval/runs -name report.json`; skills 10 = `ls
.claude/skills`.

**THE FIND 1 — AGENTS.md said "nine files" twice; the producer says 10.**
`heartbeat.py` prints `skills=10`, `docstat.py --sweep` reads 10 `SKILL.md` files, and
`DECISIONS.md` pins "all 10 `SKILL.md` files" — the tenth skill (`update-readme`)
landed after the sentence was written, and no gate reads this wording, so the
hand-typed cardinal went stale in the project's most-loaded document. This is the
README line-187 shape. FIXED directly in this pass by **dropping the cardinals** rather
than pinning 10: a count that grew once silently will grow again, the sentence's claim
("one set of files"; "the files are still there") is the part that matters, and no
producer is named at the sentence to keep a pinned 10 honest.

**THE FIND 2 — the refusal probes one address; the counts read another.**
`_assert_main_checkout_is_a_work_tree` verifies the MAIN checkout; `collect()` then
counts `ROOT`, derived from `__file__` — the tree the RUNNING COPY lives in. The two
are never compared. From a linked worktree's copy (agent worktrees are full checkouts)
the refusal passes — the main checkout IS a work tree — and every count goes
branch-local: findings, tasks and `project_lines` become plausible-and-wrong (read as
work disappearing), and a fresh worktree has no `eval/runs/` so the three output counts
read 0. The docstring's "excluded by construction" is a property of the invocation
address, not of the metric, and AGENTS.md states it as the latter. FILED as task 229,
with the red-first demonstration and a `--selftest` pin required (task 228's pattern,
including its ci_minutes census consideration).

Noted, not filed: `runs` counts top-level `wg-*` only while `census.py` searches at any
depth. Measured zero nested `wg-*` directories today, and the two `rglob` output counts
would still move if one landed — a proxy by this file's own docstring. Revisit only if
a nested run directory ever appears.

Next pointer: `eval/tools/census.py` (749 lines; grep over this log before this entry:
zero mentions, never a subject; heading verified — "Count what the stored tree actually
holds, so no document has to remember."). It is the producer behind AGENTS.md's
keep-current table and one withdrawn register entry (WR-tree-census-one-level is about
its numbers) — the tool whose figures live documents quote has never itself been read.
