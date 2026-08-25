---
id: 150
title: skill_layout_control mutates the real tree, so an interrupted run leaves the repository broken and blames the skills
status: in_testing
priority: 3
refs: eval/tools/skill_layout_control.py, eval/tools/docstat.py cmd_selftest, tasks/147
done_when: 'An interrupted skill_layout_control.py leaves the tree either unplanted or self-identifying: either the plant/restore is made crash-safe (restore from the index, or a marker file the tool itself detects and repairs on next run), or the baseline red path prints the exact repair command and the fact that a previous interrupted run is the likely cause. Established by KILLING the process mid-plant - SIGTERM during the run, not a simulated failure - and showing docstat.py --sweep is green afterwards, or red with the repair named. The 5/5 plants must still be caught.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/28
established_by: 'SIGTERM at 78s mid-plant on the live tree: exit 143, git status clean, docstat.py --sweep exit 0, state file cleared; SIGKILL at 97s leaves the tree broken and the next run repairs it and reaches 5/5; skill_layout_selftest.py 113/113 over 11 sections with real SIGINT/SIGTERM/SIGHUP/SIGKILL; pre-push gates exit 0 at the merged head 3c1aa48'
---

It plants each way the skill layout can break INTO THE WORKING TREE and restores afterwards. Killed mid-plant - a timeout, a Ctrl-C, a crash - it leaves .claude/skills as a real directory of copies, and every later docstat.py --sweep is exit 1 with 11 rows saying a real skill file exists outside .agents/skills. Measured on task 147: a 2-minute Bash timeout killed it at exit 143, and the next four gate runs were red for a reason that had nothing to do with the change under test. The rows point at the skills, so the reader looks there; the repair is rm -rf .claude/skills followed by git checkout -- .claude/skills, which nothing tells them. docstat.py --selftest solved the same problem the other way and says so in its docstring: it mutates copies in memory and asserts eval/FINDINGS.md's size and mtime are unchanged, precisely so that a crash between plant and restore cannot leave the archive edited. A symlink plant cannot be done in memory, so the fix here is not the same - but the tree can be restored from the index rather than from a variable, and the failure can name itself.

## note 2026-08-25

## What the next agent should not re-derive

### The broken state, and the exact reproduction

`skill_layout_control.py` runs 11 sweeps at ~10.3s each, so the plant windows are
predictable: baseline 0-10s, then plant *n* is IN PLACE from roughly `(2n-1)*10.3` to
`2n*10.3`. **SIGTERM at 78s lands inside plant 4** (`DanglingPointer`) and **at 97s inside
plant 5** (`PointerAsRealCopy`, the shape `tasks/147` hit). The timing drifts by a few
seconds between runs, so read the log to see which plant it caught rather than assuming.

Before the fix, a SIGTERM at 97s gave exit 143, `.claude/skills` a real directory, and
`docstat.py --sweep` exit 1 with **11 rows, 10 of them naming a `SKILL.md`** — and the run's
redirected log file was **completely empty**, because stdout is block-buffered into a file.
The one artifact that would have said which plant was in place died with the process.

### The three mechanisms, and which failure each covers

| | covers |
|---|---|
| `hold()` — `flock(LOCK_EX\|LOCK_NB)` on `<git dir>/skill_layout_control.lock` | a second run of the tool in the same work tree |
| the SIGINT/SIGTERM/SIGHUP handler | every catchable interruption: a Bash timeout, Ctrl-C, a killed CI step |
| the state file, `<git dir>/skill_layout_control_state.json` | SIGKILL, which nothing can catch |

**The division of labour falls out of `flock` rather than being arranged: the lock says who
owns the tree NOW, the state file says what the last owner was in the middle of.** The kernel
releases an `flock` when the holder dies, SIGKILL included, so a crashed run leaves the lock
free and its state file behind — which is exactly what makes `resume` correct.

**Never advise deleting the lock file.** `flock` is held on the open file description's
inode, so unlinking the path leaves a live holder's lock where it was and hands the next run
a fresh inode to lock and plant against. The tool said this for one round; the reason it must
not is now a comment above the `raise`.

**Both durable files live in the GIT DIRECTORY, not the work tree**, so they cannot reach
`git status`, `.gitignore` or a document corpus, and `--absolute-git-dir` keeps two worktrees
apart. `.gitignore`'s own header says every entry is build output or oversized evidence, and
neither of these is either — that is why they are not there.

### `repair()` restores from the INDEX, and it is the ordinary path

There is no separate recovery code to rot: `repair()` is what runs between plants as well, so
an ordinary run exercises the crash repair five times. It removes the planted FILE and then
only the parent directories it left EMPTY, stopping at the first that still holds anything —
`rm -rf .codex` deletes a `.codex/` tree another agent owns, by a command the tool itself
prints. `assert_inside()` refuses a symlinked path component, and the leaf must be a regular
file. `_copy_skill_to()` refuses to plant over anything already there.

### `docstat.py --sweep` DOES NOT FOLLOW `cwd`

It derives its root from its own `__file__`. So `sweep(fixture)` sweeps **this repository**,
not the fixture — which is why `skill_layout_selftest.py` stubs the plant runner through
`cmd_run`'s `plants` seam instead of running the real sweeps against a fixture. Anything
future that tries to drive the control against a temporary tree hits this first.

### Three of the five review rounds found defects in the PINS, not in the tool

Worth reading before writing the next control here, because all three are shapes this
project already has rules for and all three were committed anyway:

1. **A row that could not detect the damage it was written for.**
   `sorted(os.listdir(outside/tasks)) == ["SKILL.md"]` is byte-identical before and after an
   unguarded plant copies its own `SKILL.md` over the victim. Compare CONTENT.
2. **A pin that aborted instead of reporting.** Under a mutant, `repair()` raised
   `NotADirectoryError`, which escaped a `RuntimeError` handler and killed the section — a
   suite that stops early prints a smaller count with nothing saying why. `Pins.refuses()` is
   three-valued now and `cmd_selftest` records a dead section as one failed pin.
3. **A population imported from the subject.** The signal pin looped over `slc._SIGNALS`, so
   the mutant that shrinks it to `(SIGTERM,)` came back **SURVIVED, 0 red of 6**, having
   quietly taken the pin from 14 rows to 6. `CAUGHT` is now stated in the selftest and
   COMPARED with `slc._SIGNALS` in a row. Applied to the SOURCE that mutant is 7 red of 15 —
   **and an in-process monkeypatch only reaches the parent**, because
   `_skill_layout_child.py` imports the module fresh.

### A candidate finding, no number taken

**A long-running tool's own log is discarded by stdout buffering exactly when it is most
needed.** The interrupted run at exit 143 wrote a zero-byte log; nothing recorded which plant
was in place, so the repair had to be re-derived from the tree. `say()` flushes every line
now. The general claim is about any tool here that a timeout may kill mid-run and whose
output is redirected — the class is "what the instrument DID", which `AGENTS.md` already has
a section for. The orchestrator allocates the number if it wants one.

### What was deliberately NOT done

The descriptor-relative `openat`/`O_NOFOLLOW` rewrite CodeRabbit asked for in round 3. The
race needs a process that can already create paths inside this working tree, and that process
can append a line to `skill_layout_control.py` and have it run as the tool, or replace
`.claude/skills` outright with no race at all. There is no privilege boundary between the tool
and the attacker posited. **If this ever runs as a different user, or over a tree with a
genuinely untrusted second writer, that rewrite is the right fix** — the thread on PR #28
carries the argument.
