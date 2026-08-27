---
id: 176
title: docstat project_docs() globs the filesystem, so an untracked scratch .md joins a corpus a ratchet is pinned to
status: done
priority: 2
refs: eval/tools/docstat.py, tasks/160
done_when: project_docs() and _live_corpus() agree on which files are in the tree, asserted in code rather than promised in a comment; a planted untracked .md under a gitignored directory does not move the --sweep corpus count or the bare-trial-id ratchet, pinned as a control that goes red if the filter is removed; docstat.py --sweep and --selftest exit 0.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/54
established_by: 'Merged as PR #54. The defect was reproduced before the fix: project_docs() globbed ROOT/**/*.md, so any markdown lying in the working tree was a project document. At 67d4967 one untracked note at staging/task-176-note.md took --sweep from 249 documents to 250 at exit 0, and the same note under staging/findings/ citing three trial ids took the bare-trial-id ratchet from 18 to 21 and failed the sweep - a file not in the repository could move a gate that is. project_docs() and _live_corpus() now share _tracked_md(), which lists with git ls-files -z, and _corpus_pins asserts the two agree about membership. NO PINNED COUNT MOVED: on a clean checkout the glob and the index return the same 238 project documents, set difference empty both ways, so nothing was re-recorded to match a new number - which is also why the live tree cannot pin the new filter and corpus_control.py builds a throwaway git repository holding markdown that is not in it. Verified by the orchestrator on the branch: corpus_control.py exits 0 at ''7 of 7 mutants died; 0 pins wrong on the clean tree'', and I planted an untracked .md carrying two bare trial ids myself - the corpus held at 250 and the sweep stayed exit 0, where before the fix it would have joined the corpus and moved the ratchet. THREE DEFECTS FOUND ON THE WAY, all real: git ls-files C-quotes non-ASCII paths without -z so cafe.md fails endswith(''.md''), latent because the corpus holds 0 such paths but two checks were already reading git that way; _git folded a non-zero exit into '''' so a failed listing and an empty tree were the same answer, which is rule 3''s sibling; and git -C <dir> names a DIRECTORY not a repository, so an inherited GIT_DIR outranks it at exit 0 - init silently creates no .git, add writes to the other repository''s index, ls-files reads it. That third one HAPPENED during the run, leaving 6 paths staged in the worktree''s index with .gitignore replaced there. _git_at now drops every GIT_* variable and _assert_own_repo refuses on --absolute-git-dir, chosen because --show-toplevel AGREES on exactly this input, which was measured rather than assumed. The agent also ruled out its own GIT_DIR-steered writer as the cause of tasks/184''s core.bare flip - three variants of git init under an inherited GIT_DIR all leave core.bare false - and recorded that in 184 so it is not re-derived. Findings #198.'
---

project_docs() in eval/tools/docstat.py builds its list with glob over ROOT, filtered only by is_vendored and a runs/ exclusion. git ls-files does not come into it, so any markdown file sitting in a gitignored directory enters the count. Measured 2026-08-27 while working tasks/160: writing one scratch note at staging/task-160-note.md moved docstat.py --sweep from "references over 239 docs (228 project + 10 skills + 1 under .github)" to 240 (229 project), at exit 0 both times. Renaming the file to .txt put it back to 239. The helper docstring says the bare-trial-id ratchet is "pinned to an exact count a larger corpus would move", so the failure mode is not only a wrong published number: a file that is not in the repository can move a gate that is. _live_corpus() in the same module reads git ls-files and is unaffected, which is the fix shape - two spellings of one tree, and only one of them is the tree.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — `tasks/179` edits the same file; you are first and it will rebase on you

`179` repairs `docstat.py`'s findings-COUNT check, which is bound to one phrasing. Yours repairs
`project_docs()`'s corpus selection. Different defects, one file, so they cannot run concurrently.
You go first because the corpus is the input to every check in that tool, including 179's.

**Worth knowing before you change the population:** `--sweep` prints its corpus size in the summary
line and several of its checks are pinned to exact counts. At `main` right now that reads *249 docs
(238 project + 10 skills + 1 under .github)*. If your repair moves the corpus - and reading
`git ls-files` instead of globbing will - **every pinned count moves with it**, and a pin updated
to match a new number is not a check. Say which pins moved and why each new value is right, rather
than re-recording the output.

The ratchet your ticket names is the case to lead with: a pin to an exact count over a corpus that
can silently grow is a pin that reports the corpus, not the property.

## note 2026-08-27

## What landed

`project_docs()` reads `git ls-files`, not the filesystem. It and `_live_corpus()` share one
helper, `_tracked_md()`, and `_corpus_pins` asserts they agree about tree membership — 46
documents on both sides after removing the deliberate differences (`project_docs` keeps the
archive and drops dot-directories and `runs/`; `_live_corpus` does the opposite on the
archive).

**The dot-directory exclusion is now stated rather than inherited from `glob` not descending
into a dotted name.** It was always a choice; it just was not written down, and a mutant
could not remove it.

## NO PINNED COUNT MOVED, and that is the answer to the orchestrator's note

On a clean checkout the glob and the index return the **same 238** project documents — the
set difference is empty in both directions. So nothing in `--sweep`'s summary was
re-recorded to match a new number: 249 / 238 / 10 / 1 / 198 / 177 / 57 / 36 before and
after.

**That is also why the live tree cannot pin the new filter.** A mutant restoring the glob
passes every live row. The discriminating input has to be built:
`docstat._tree_fixture(tmp)` makes a throwaway git repository holding markdown that is not
in it, and `eval/tools/corpus_control.py` runs the pins with one mechanism removed.

## The measurements, in both directions

| planted | before the repair | after |
|---|---|---|
| `staging/task-176-note.md`, no ids | corpus 249 → **250** (238 → 239 project), exit 0 | corpus **249**, exit 0 |
| `staging/findings/scratch-note.md`, 3 bare trial ids | ratchet 18 → **21**, **exit 1** | ratchet **18**, exit 0 |
| the same bare id in a **tracked** file | ratchet 18 → 19, exit 1 | ratchet 18 → **19, exit 1** |

Row 3 is the positive control: the ratchet still fires. Rows 1 and 2 going quiet is the
corpus being right, not the check being off. Row 3 was produced by appending under a **fresh
`## ` heading** to `eval/findings/documentation.md` and restoring with `git checkout --`;
appending at the end of the file does nothing, because the ratchet excuses an id whose
section already names a `wg-` run.

## THREE DEFECTS FOUND ON THE WAY, and the third is the one to know about

**1. `git ls-files` C-quotes any path outside ASCII unless `-z` is passed.** `café.md` comes
back as `"caf\303\251.md"` and fails `endswith(".md")`. The obvious replacement would have
dropped such a document from the corpus silently — and `_live_corpus` and the
renumbered-citation check had **already** been reading git that way. Fixed with `-z`
everywhere. The corpus holds **0** non-ASCII paths today, so no published number was wrong;
this is latent, not live. Pinned as a variant, killed by the `no_nul` mutant.

**2. `_git` folded a non-zero exit into `""`.** A failed listing and an empty tree were the
same answer, so every check downstream would have reported itself clean over 0 documents.
`_git_at` keeps the status; `_tracked_md` raises. Killed by `empty_on_failure`.

**3. `git -C <dir>` names a DIRECTORY, NOT A REPOSITORY, and an inherited `GIT_DIR` outranks
it at exit 0 throughout.** This is worth the next agent's attention because nothing about it
is visible in a transcript:

    GIT_DIR=<other>/.git  git -C <tmp> init -q     ->  rc 0, and <tmp>/.git IS NEVER CREATED
    GIT_DIR=<other>/.git  git -C <tmp> add doc.md  ->  rc 0, staged in <other>'s INDEX
    GIT_DIR=<other>/.git  git -C <tmp> ls-files    ->  <other>'s index, not <tmp>'s

It happened. On 2026-08-27 the fixture ran once that way and left 6 fixture paths staged in
**this worktree's index** with `.gitignore` replaced there. The working tree was untouched,
so nothing but `git status` could see it; `git reset -q HEAD` recovered it. It reached the
**reader** too: `project_docs()` and `_tracked_md()` would have built the corpus from
whatever repository `GIT_DIR` named, and the first symptom was `--sweep` reporting 255
markdown paths where the tree had 249.

Two repairs, deliberately separate so a control can remove either alone:

- `_git_at` drops **every** `GIT_*` variable from the child. All of them, not the four that
  steer discovery — a list of variable names is an enumeration and the next reader meets
  `GIT_COMMON_DIR`. Nothing this module runs needs any of them.
- `_assert_own_repo` refuses in front of the one `git` call that writes, on
  `--absolute-git-dir`. **`--show-toplevel` does not work here**: under an inherited
  `GIT_DIR` with no `GIT_WORK_TREE` the work tree is the current directory, so it answers
  `<tmp>` and *agrees* on exactly the input the guard exists to catch. That was measured, not
  reasoned about — the first version of the guard used it and was green on the defect.

Pinned by 3 rows in `_corpus_pins` run with a hostile `GIT_DIR` and a victim repository to
write into, and killed by `inherit_git_env`, which removes both mechanisms because either
alone hides the other (with the guard in place the write never happens, so the row about the
victim's index stays green).

**`inherit_git_env` scrubs `GIT_*` from the PROCESS before rebinding anything**, or the
mutant that reproduces the incident would cause it: an operator with `GIT_DIR` exported
would have had it stage fixture files into their own index. Controlled with `GIT_DIR`
exported in both runs — with the scrub, exit 0, 7 of 7 dead, victim index `['victim.md']`
before and after; without it, the victim comes back holding all 6 fixture paths.

## A FINDING TO NUMBER (the orchestrator allocates it)

**Claim.** A gate that discovers its git repository rather than naming it can read, and
write, a repository the caller's environment chose. `docstat`'s corpus helper and its test
fixture both did; the fixture staged 6 paths into a live worktree's index at exit 0, and the
corpus reader would have answered about another tree.

**Measurement.** The 3-line table above, reproduced on demand by `python3
eval/tools/corpus_control.py --mutate inherit_git_env` (all 3 hostile-`GIT_DIR` rows red,
including the victim's index holding `.gitignore`, `doc.md`, `sub/nested.md`,
`"sub/n\303\270te.md"`, `.dotdir/hidden.md`, `runs/stored.md` and `gone.md` beside its own
file).

**Control.** The same run with the scrub in place: exit 0, 7 of 7 mutants dead, victim index
`['victim.md']` unchanged, worktree status unchanged.

**Why it is not just a bug.** `AGENTS.md` rule 12 says the address is an input to the check
and to assert a path spelled in two files. Every instance recorded there is an address
written in *our* code. This one was supplied by the process environment, so there was no
second spelling to compare — the defence is to refuse the environment, not to reconcile two
copies of an address.

## Behaviour change worth knowing

The corpus is the **INDEX**, not `HEAD` and not the disk. A document written and `git
add`ed is swept before it is committed, which is what the pre-commit hook needs and why
`.agents/skills/work` tells you to stage before running the gates. A document written and
never staged is not swept — it is not in the repository yet.

## Small thing

The ratchet's failure message said `Newest:` over a list ordered by path. It says `Last by
path:`.

## Register

`gates.yml` went 53 → 56. Task 183 added one on `main` while this was in review and this
adds `corpus_control`, so the merged count is **neither side's pinned number** — `python3
eval/tools/ci_minutes.py --gates` decided it, and both pins and both register sentences
state what it read.

## note 2026-08-27

## Review state at hand-back, stated rather than waited on

**2 rounds of review, both worked, and the last one came back clean.** Round 1 raised 3
comments, round 2 raised 2, all 5 real and all 5 acted on; every one has a reply in its
thread. The round after round 2's push returned `LANDED_COMMENT` at `920e12f` — the reviewer
finished and had nothing to say. That head carried the complete code diff.

**No round has arrived at the head that will land, `53a387a`,** which is a merge of `main`
plus queue files and changes no line of this branch's code. Measured: `pr_review_state.py`
expired `UNRESOLVED` (exit 13) after 20 minutes with `in_flight=0` throughout, an explicit
`@coderabbitai review` was posted, and a further 10 minutes of polling still reads
`NOT_YET`. Per `.agents/skills/work/SKILL.md` that is the shared round pool being spent, not
a clean review, so it is reported rather than waited on.

**CI is green at `53a387a`**: `gates` SUCCESS, `controls` SUCCESS (12m52s), and
`python3 eval/tools/mergeable.py 54` says *mergeable: required checks green at the current
head, branch up to date, no unresolved review thread, and GitHub agrees.*

`main` moved twice during the review and was merged in both times. The second merge is why
the branch carries `tasks/176`'s own earlier note.
