---
id: 114
title: Make .agents the single source of skills, reached from .claude by symlink rather than copied
status: done
priority: 1
refs: '.claude/skills/ (9 skills, a real directory), .agents/skills/ (untracked, regenerated 2026-08-23 11:46), eval/tools/docstat.py GATED_DIRS and the skill-location gate, AGENTS.md ''Everything belonging to this project lives inside this project'', DECISIONS.md, eval/findings #99'
done_when: exactly one real directory holds the nine SKILL.md files and every other path to them is a symlink; Claude Code is verified to actually load a skill through whatever indirection is chosen, by invoking one and observing it, not by reasoning about it; the docstat skill-location gate accepts the new layout and still goes RED on a genuine second copy, both demonstrated; and if the verification shows Claude Code cannot follow the indirection, that is recorded with what was tried and the layout stays as it is
established_by: 'SHIPPED THE FIRST ROW OF THE TICKET TABLE, NOT THE FALLBACK: nine skills now real at .agents/skills/<name>/SKILL.md with .claude/skills a symlink to ../.agents/skills, stored by git as mode 120000. LOADER MEASURED, NOT REASONED ABOUT (the ticket called this the whole risk): claude 2.1.220, one probe skill per layout with a UNIQUE NAME so a same-named skill could not be deduplicated, and every tool but Skill denied so the token could not arrive by the model reading SKILL.md. Real .claude/skills LOADED (positive control); .claude/skills -> ../.agents/skills LOADED; per-entry symlinks LOADED; .agents/skills only with no .claude NOSKILL (negative control); .claude real with .agents a symlink LOADED. Then repeated on the REAL TREE IN A FRESH CLONE of the branch rather than a fixture: the refine skill loaded through the symlink and returned its H1 ''# Refining after a run'', the value read off disk in advance; deleting only the symlink from that same clone turned the identical prompt into NOSKILL. Whole-directory symlink chosen over per-entry because a new skill then needs no new symlink. GIT SURVIVAL: git ls-files -s reads 120000, and a fresh clone materialises a real symlink carrying 6593 characters, not one line of path text. BROKEN STATE ESTABLISHED FIRST: sweep exit 1 with exactly 9 problems, all .agents/skills, before any change. GATE MOVED AND STILL ABLE TO FAIL: the address was spelled three times in docstat.py (GATED_DIRS, the size-report glob, the location check) and is now SKILLS_REAL/SKILLS_LINKS in one place per rule 12; the location test compares realpath and _all_skill_files walks followlinks=False so a pointer contributes no paths. THE GATE GREW THE HALF THAT DID NOT EXIST: the negative control proves Claude Code does not read .agents/skills natively, so deleting the pointer leaves nine files at the authoritative address, every file-counting check clean, and no agent able to load one - docstat now asserts the pointer exists and resolves. New eval/tools/skill_layout_control.py pins both directions on the live tree, 5/5 RED then GREEN after restore: a real copy at .codex/skills, a copy one level too deep INSIDE the authoritative root (which a prefix test would pass), the pointer deleted, the pointer dangling, the pointer replaced by a real directory of copies. THE TICKET PREMISE WAS WRONG AND THIS IS THE CANDIDATE FINDING, NO NUMBER TAKEN: the mirror was TRACKED and nothing outside the repository wrote it. git log -- .agents gives bec16e3 deleting it for #99 and the task-101 merge commit re-adding all nine files as 1468 PURE INSERTIONS, because that branch forked before the deletion. Its drift was simply the pre-deletion content: FOUR files differed, not three - three by a mechanical claude->Codex substitution that also corrupted unrelated prose and produced the .Codex/skills/ path resolving nowhere, and tasks by 9 lines merged that morning. New layout is merge-safe against a repeat because a branch carrying a real .claude/skills directory conflicts with a 120000 blob instead of silently shadowing it. NOT ESTABLISHED, STATED PLAINLY: when_to_use is a Claude Code field Codex ignores (research/11 XP-SK-001), so a non-Claude reader of .agents/ gets each skill body but not its trigger - one shared copy still beats two drifting ones, but this layout does not buy trigger parity across CLIs, and the brief now says so. DOCS REPAIRED: AGENTS.md, DECISIONS.md, research/11; three renumber_triage anchors re-recorded because the rewrites moved the sentences carrying #99 - the finding untouched, only its citation site moved. CLEANUP-LOG.md and tasks/ left as archive. NOT TOUCHED per ticket: .claude/settings.json, .claude/memory, .claude/settings.local.json. GATES UNPIPED: docstat.py --sweep exit 0 over 176 docs (167 project + 9 skills); docstat.py --selftest exit 0, 0 pins wrong; skill_layout_control.py exit 0 at 5/5; withdrawn_control.py exit 0 at 54/54. PRE-EXISTING AND NOT MINE: tasks.py check exit 1 on 109 status in_review, another agent''s concurrent queue entry, confirmed against the MAIN checkout tasks.py and not only this worktree copy. Branch task-114-agents-skills-symlink.'
---

The operator's decision on 2026-08-23: .agents rather than .claude should hold the skills, so Codex, Claude and anything else read ONE source of knowledge rather than a copy each. They also ruled that no .codex/skills should exist, and that if a second path is needed it must be a symlink and not a real folder. This is the opposite conclusion from #99, which deleted a .agents mirror - and it is not a reversal of the reasoning, it is agreement with it: #99's objection was to a COPY that drifted, and a symlink cannot drift.

WHAT THIS IS

Nine skills live at `.claude/skills/<name>/SKILL.md`. `AGENTS.md` calls that *"the sole
authoritative path"* and `docstat.py --sweep` fails any `SKILL.md` found anywhere else — a gate
written after `#99`, where a `.agents/skills/` duplicate for a Codex CLI sat in the tree, was
never once in sync, had no reader, and shipped an `add-game` missing a guard that exists because a
shared preamble contaminated a single-variable experiment.

**On 2026-08-23 at 11:46 the `.agents/skills/` mirror reappeared**, untracked, regenerated by
something outside this repository — no hook and no script here writes it. It had already drifted
within hours: three of its nine files differ from the live ones, and its `dispatch` skill points
at **`.Codex/skills/tasks/SKILL.md`**, a path that does not exist anywhere. It is currently the
only reason `docstat.py --sweep` exits 1.

WHY THE OPERATOR'S DECISION IS NOT A REVERSAL OF #99

`#99`'s objection was never to the *location*. It was to a **copy**:

> a second copy is a second source of truth and only one of them gets edited

A symlink has no second copy to get edited. The finding's own escape clause says so —
*"if you want cross-tool support, add a **pointer** to `.claude/skills/`, never a copy of it"* —
and this task inverts which end the pointer lives at. **Read `#99` before starting**, and if the
design you land re-admits a real second copy anywhere, that is the thing it exists to prevent.

WHAT IS UNKNOWN AND MUST BE MEASURED, NOT REASONED ABOUT

**Whether Claude Code discovers skills through `.agents/`, or through a symlinked
`.claude/skills`, is the whole risk of this task, and it is not answered here.**

What is known from this tree, and it is thin:

- `.claude/skills/` is a **real directory** today, and Claude Code loads all nine from it.
- `AGENTS.md` at the repo root **is** read — that is a cross-tool convention several agents
  honour. That says nothing about `.agents/skills/`, which is a different mechanism.
- The `.agents/` copies were on disk all afternoon and **no duplicate skill names appeared** in
  the session's skill listing, which is weak evidence that Claude Code did not load them — weak
  because a same-named skill may simply be deduplicated.

**Do not ship a layout on the strength of that.** The `done_when` asks you to *invoke a skill and
observe it working*, because this project's standing rule is that a mechanism which runs and
reports nothing is indistinguishable from one that works. Concretely: make the change, then have a
skill actually load — a fresh session, or the operator invoking one — and confirm the content that
arrives is the content in the real directory. **Reasoning about the loader is not a measurement of
the loader.**

The likely orderings, and each has a different failure:

| layout | what has to be true |
|---|---|
| real files in `.agents/skills/`, `.claude/skills` a symlink to it | Claude Code follows a symlinked skills directory |
| real files in `.agents/skills/`, `.claude/skills/<name>` each a symlink | Claude Code follows a symlinked skill directory |
| real files stay in `.claude/skills/`, `.agents/skills` symlinks to it | nothing about Claude Code has to be true — the safest, and it satisfies "one source" while putting the pointer at the end the operator did not ask for |

The third is the fallback if the first two do not load. **Landing the fallback and saying why is a
complete result**; landing the first two without observing a skill load is not.

TWO CONSTRAINTS THAT ARE NOT NEGOTIABLE

- **No `.codex/skills` or `.Codex/skills`, as a real folder.** The operator ruled on this
  directly. The regenerated mirror already contains a reference to `.Codex/skills/` in prose;
  whatever writes it is producing a path that resolves to nothing.
- **Symlinks must survive git.** Git stores a symlink as a mode-120000 blob, so this works — but
  **verify it on a fresh clone**, because a checkout on a filesystem or a platform that does not
  support them silently materialises a text file containing the target path, and a `SKILL.md`
  that is one line of path text is a skill that loads and says nothing. Check
  `git ls-files -s` shows mode `120000`.

THE GATE HAS TO MOVE WITH THE LAYOUT, AND IT HAS TO STAY ABLE TO FAIL

`eval/tools/docstat.py` holds the address in more than one place — `GATED_DIRS` at line 192, a
glob at line 264, and the skill-location check around line 2819. **`AGENTS.md` rule 12: when a
path is spelled in two files, assert them equal in code.** They are currently spelled several
times in one file, which is the same defect with a shorter blast radius.

Whatever you change, the gate must still go **RED on a genuine second copy** — a real
`SKILL.md`, not a symlink, in a second location. Demonstrate both:

1. green on the new layout
2. red on a real duplicate planted in it, and green again after removing it

A gate relaxed to accept symlinks that also accepts copies has been deleted, not moved.

WHAT TO DO ABOUT THE UNTRACKED MIRROR ON DISK

It is the operator's file, written by their tooling. **You may delete it as part of landing this
task**, because that is what the operator asked for and its content is a stale copy of tracked
files — but say in the report exactly what you removed. **Find out what regenerates it if you
can**, and if you cannot, say so: a layout that something outside the repository overwrites every
few hours is not a layout, and `.gitignore` alone does not stop a real file shadowing a symlink.

WHAT NOT TO CONCLUDE

**Do not read "one source of knowledge" as "one file".** The nine skills are nine procedures and
they stay nine. This is about how many *copies* of each exist and how many *paths* reach them.

**Do not migrate `.claude/settings.json`, `.claude/memory/` or `.claude/settings.local.json`.**
`AGENTS.md` names those locations, `autoMemoryDirectory` is already delicate, and this ticket is
about skills. If the same argument applies to them, that is a separate ticket with its own
verification.

---

## WHAT THIS TASK ESTABLISHED — 2026-08-23, task 114

**Shipped: real files at `.agents/skills/<name>/SKILL.md`, `.claude/skills` a symlink to
`../.agents/skills`.** The first row of the ticket's table, not the fallback.

### The loader question the ticket said was the whole risk — answered by measurement

`claude` 2.1.220. One probe skill per layout with a **unique name** (so a same-named skill could
not be deduplicated, which is the weak evidence the ticket warned against), a token that exists
only inside its `SKILL.md`, and every tool but `Skill` denied so the token could not arrive by
the model reading the file:

| layout | result |
|---|---|
| real `.claude/skills/<n>/SKILL.md` — positive control | **LOADED** |
| real `.agents/skills/`, `.claude/skills` -> `../.agents/skills` | **LOADED** |
| real `.agents/skills/`, `.claude/skills/<n>` each a symlink | **LOADED** |
| real `.agents/skills/` only, no `.claude/` — negative control | **NOSKILL** |
| real `.claude/skills/`, `.agents/skills` a symlink | **LOADED** |

Then repeated on the **real tree in a fresh clone** of the branch, not a fixture: the `refine`
skill loaded through the symlink and returned its H1, `# Refining after a run`, matching the
value read off disk beforehand. Removing only the symlink from that same clone turned the same
prompt into `NOSKILL`.

**Do not re-derive this.** The transferable facts are: Claude Code **follows a symlinked skills
directory**, and it does **not** read `.agents/skills` natively. The whole-directory symlink was
chosen over the per-entry one because a new skill then needs no new symlink.

### The ticket's premise about the mirror was wrong, and the correction matters

The ticket says `.agents/skills/` was *"untracked, regenerated by something outside this
repository — no hook and no script here writes it"*. **It was tracked, and nothing outside the
repository wrote it.** `git log -- .agents` gives three commits: `bec16e3` deleted the mirror for
#99, and the commit merging **task 101** re-added all nine files as pure additions, 1468
insertions, because that branch was forked before the deletion. A merge restored what it had
never seen removed.

That is why the mirror "had already drifted": its four differing files were simply the
pre-deletion versions. Three differ only by a mechanical `claude` -> `Codex` substitution that
also corrupted unrelated prose (`the Codex CLI's --max-turns`, and the `.Codex/skills/` path that
resolves nowhere); the fourth, `tasks`, was 9 lines short of content merged that morning. **Four
files differed, not three.**

**This is a candidate finding and no number was taken** — the orchestrator allocates it. The
claim: *a directory deleted on `main` silently returns through any branch forked before the
deletion, and it comes back as an ordinary addition that no gate reads as a resurrection.* The
new layout is merge-safe against a repeat, because a branch carrying a real `.claude/skills/`
directory now conflicts with a mode-120000 blob instead of quietly shadowing it.

### The gate, and why it grew a second half

`docstat.py` spelled the skills address three times — `GATED_DIRS`, the size-report glob, and the
location check. It is now `SKILLS_REAL` / `SKILLS_LINKS` at one place, and everything derives
from it (`AGENTS.md` rule 12).

The location check compares **realpath**, not strings, and `_all_skill_files()` walks with
`followlinks=False`, so a pointer contributes no paths and cannot be mistaken for a copy.

**The half that did not exist before: the pointer is asserted.** Delete `.claude/skills` and the
nine files are still present, still at the authoritative address, and every file-counting check
reads clean — while no agent can load one. That is the vacuous pass the module exists to prevent,
and only the negative control above makes it visible.

`eval/tools/skill_layout_control.py` pins it in both directions on the live tree, 5/5: a real copy
at `.codex/skills/`, a copy one level too deep *inside* the authoritative root (which a prefix
test would pass), the pointer deleted, the pointer dangling, and the pointer replaced by a real
directory of copies — each RED, each GREEN again after restore.

### Verified, and worth not re-checking

- Git stores the link as mode **120000** (`git ls-files -s .claude/skills`), and it survives a
  fresh `git clone` as a real symlink — 6593 characters through it, not one line of path text.
- `git ls-files` returns 9 `SKILL.md` plus one entry for `.claude/skills`, so `prune_scan.py` and
  `heartbeat.py`'s `project_lines` see no duplication.

### Left undone, deliberately

- **`when_to_use` is a Claude Code field that Codex ignores** (`research/11`, §`XP-SK-001`). A
  non-Claude reader of `.agents/` gets each skill's body but not its trigger. One shared copy is
  still strictly better than two drifting ones; trigger parity across CLIs is not something this
  layout buys, and the brief now says so.
- `.claude/settings.json`, `.claude/memory/`, `.claude/settings.local.json` untouched, per the
  ticket.
- `tasks.py check` reports `109: status 'in_review' not in (...)`. Pre-existing, another agent's
  concurrent work in the shared queue, confirmed against the **main checkout's** `tasks.py` and
  not only this worktree's copy. Not touched.
