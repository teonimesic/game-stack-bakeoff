#!/usr/bin/env python3
"""Can `tasks.py` still lose a value, mis-report a success, or warn where nothing is wrong?

WHY THIS EXISTS
---------------
`eval/tools/tasks.py` is the convenience layer over the open-work queue, and it is the one
tool in this repository that EVERY agent writes through concurrently. It had no control.
The three defects it has actually shipped were each found by a person noticing, which is
not a mechanism:

  * `_parse` split frontmatter on the first colon, so 44 of 58 files were unparseable by
    anything else and 9 more parsed truncated -- an external reader got a plausible wrong
    answer rather than a failure (task 40).
  * `add` printed its result `relative_to(ROOT)` while writing to the queue under the MAIN
    worktree, so from an agent worktree it created the task and exited 1 with a traceback.
    A success reporting failure invites a retry, and the retry files a SECOND task (#94,
    task 41).
  * `check`'s reachability warning decided "has an escape branch" from a nine-entry phrase
    list, four of whose entries were sentences copied off tasks 01 and 08. It warned on
    tasks 32, 35 and 58, all three of which have an escape branch (task 38).

  * `check` gated the frontmatter and never looked at the BODY, which is the only part an
    agent is briefed from. `436bf64` appended task 71's whole brief to `tasks/70-...md` and
    created `tasks/71-...md` empty; `check` exited 0 on both, printing `70 task(s), all
    well-formed`, while task 71's agent worked from a ticket with no body (task 82).

    The exposure was 25m48s on main -- `436bf64` 09:12:56 to `28f6598` 09:38:44 -- and NOT
    "for a day", which this docstring and `tasks/93` both said until #141 measured it. The
    duration is the wrong figure anyway: the dispatched agent forked at `23be12c` (09:14:41),
    after the misfile, and delivered at `c2bc8ce` (09:38:42), so ALL of its working span ran
    against the empty ticket. The same mistake eight hours earlier -- `709d51a`, an append to
    a guessed filename that did NOT exist -- was caught by this same `check` at exit 1, and
    that contrast is the finding: a wrong address that misses makes an artifact the lint can
    see, and one that hits makes a well-formed one it cannot.

THE DIRECTIONS
--------------
The heading counted five while `coverage_rows` had already made it six -- a census with no
producer, in the file whose job is to have one. It is not a cardinal any more:
`python3 eval/tools/tasks_control.py` prints the row for every direction it ran.

1. ROUND TRIP, byte for byte, over every file in the live shared queue. Not "the values
   survive" -- the BYTES. The value round-trip was green while `_render` was rewriting
   `id: 01` as `id: 1`, because the value was never wrong (see `_id_text`). An
   `established_by` string is a durable record of what established a result, and this is
   the only direction that proves a status change cannot quietly edit one.

2. THE TWO WRITES A DISPATCHED AGENT MAKES FROM ITS OWN WORKTREE, `add` and `note`. Run in
   a scratch git repo with its own worktree, because both defects only exist where `TASKS`
   and `ROOT` disagree -- and each with the copy of `tasks.py` that PREDATES its repair as
   the positive control, since a green row from a harness that cannot observe the failure
   is rule 1's `total=0 passed=0`.

   `add` exits 0 and prints the created path (#94, task 41). `note` appends a section to a
   ticket BODY, and its central row is not "the values survived" but that the file
   afterwards is the file before it PLUS the expected section and NOTHING else -- the ticket
   an agent was briefed from is a durable record, and an append that quietly reflowed it
   would be indistinguishable from one that did not. The expected bytes are stated HERE, in
   `_expected_block`, and deliberately not imported from the subject: see that function for
   the mutant that survived with 0 red rows when they were. Both refusals (unknown id, empty
   note) assert the file is untouched, because a write that reports failure and a failure
   that reports success are the two shapes rule 7 is about.

3. `check` STILL FAILS on the three things it is there to catch: a duplicate id, a missing
   `done_when`, a bad status. Each is exercised on its own scratch queue, with a
   well-formed queue as the negative control.

4. THE REACHABILITY WARNING, both ways. It must stay quiet on the four wordings that carry
   an escape branch and still fire on the two originals, on a bare universal and on a bare
   threshold. Only direction 4b -- must still WARN -- keeps a repair from being a deletion.

   4a and 4b call `reachability_warning` IN PROCESS, so between them they pin the PREDICATE
   and never ask whether `check` REPORTS what the predicate returns. That gap was measured,
   not suspected: replacing `if warn:` in `cmd_check` with `if False:` left `tasks.py`
   computing every warning and printing none, and all 34 rows this file then had stayed
   green -- exit 0, 0 FAILED (`tasks/106`). 4c runs `check` end to end on a scratch queue and
   reads its STDOUT, in both directions: the warning text printed on an unreachable
   done_when, and absent on a reachable one. Both rows also assert exit 0, because this is a
   smell and not a gate; a repair that turned it into a failure would go red here.

5. THE MISFILED-BODY CHECK, both ways, ON THE REAL BLOBS. `check` must fail on the actual
   `436bf64` pair naming both halves, and go quiet on the same two tickets as `28f6598`
   repaired them. `MISFILED_MARGIN` is pinned from BOTH sides -- the true positive at 0.36
   must fire, and the worst non-defect the history contains (task 62 against task 70's
   brief, 0.14) must not -- so raising the threshold and lowering it are each visible.
   A mutant can only show the check CAN fail; the 0.14 row and the ten-task-ids row are
   what ask whether it can still PASS (AGENTS.md rule 15).

6. #141's COVERAGE FIGURE, run rather than quoted -- how little of a task file the pre-fix
   lint ever read. It is here because the figure was published wrong in both terms and had
   no producer, so nothing in the repository could disagree with it.

7. THE 5-VALUE STATUS VOCABULARY. `check` only ever asked whether a WRONG status fails; this
   asks whether each transition WRITES the state it names, and whether `heartbeat.py` -- the
   one other file that counts statuses -- covers exactly `STATUSES`. Its map was a hardcoded
   3 keys that dropped the rest silently: over a queue with 1 file in each of the 5 states it
   counted 3.

8. THE `established_by` STRING, which direction 7 never looks at because it always passes a
   good one. `done <id> - < account.md` stored the literal one-character `-` at exit 0 over
   2280 characters of measurement, and moved the ticket to `done` while doing it (task 120).
   Every refusal row asserts exit 1 AND the file byte-identical, status included; the
   accepting rows are rule 15's variant half, including the backtick line that argv cannot
   carry at all and is the reason `-` is READ rather than rejected outright.

THE CONTROLS DO NOT TOUCH THE SHARED QUEUE. `TASKS` is derived at import from
`git worktree list`, and monkeypatching a module constant that has already been derived is
how a lint once ran against the real tree while claiming a bad root (AGENTS.md rule 12). So
directions 2 and 3 build a real main-plus-worktree pair under a temporary directory and run
`tasks.py` there as a subprocess, at the address the defect actually lives at.

Usage, from anywhere:
    python3 eval/tools/tasks_control.py
    python3 eval/tools/tasks_control.py --skip-prefix   # no positive control for direction 2
    python3 eval/tools/tasks_control.py --tasks-py PATH # grade a COPY of tasks.py

Exit: 0 every direction measured and green; 1 a direction FAILED; 3 nothing failed but a
direction was NOT CHECKED. Never read 3 as a pass.

`--tasks-py` is what makes these rows falsifiable: `eval/tools/tasks_mutants.py` writes a
mutated COPY of `tasks.py` into a tempdir and points this file at it, so every row can be
asked whether it CAN go red. The repository's own `tasks.py` is never written to (#134).
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

#: THIS FILE'S OWN DIRECTORY, and it is the GIT ADDRESS -- directions 2 and 5 read real
#: blobs out of this repository's history. It deliberately does NOT move with `--tasks-py`:
#: a mutated copy lives in a tempdir that is not a checkout, and following it there would
#: turn every blob row into NOT CHECKED, which is not a pass (AGENTS.md rule 12).
TOOLS = Path(__file__).resolve().parent

#: The REPOSITORY ROOT, for the `git -C` calls in directions 5 and 6. Derived from this
#: file rather than from `cwd`, so a control run from anywhere reads the same history.
ROOT = TOOLS.parents[1]

#: The SUBJECT: the `tasks.py` under test, rebound by `--tasks-py`. Two addresses, moving
#: independently -- the code under test and the corpus it is tested against.
TASKS_PY = TOOLS / "tasks.py"


def _load_module(name: str, path: Path):
    """Import a module BY PATH under a chosen name. The mechanism `_load_subject` uses.

    Split out because direction 6 needs a second module -- the producer behind #141's
    coverage figure -- and `sys.path` deliberately no longer carries `TOOLS`.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_subject(path: Path):
    """Import the `tasks.py` under test BY PATH, never by name.

    `sys.path.insert(0, TOOLS); import tasks` -- what stood here -- can only ever reach the
    repository's own copy, so no row below could be asked whether it can fail. Importing by
    path is also why the subject is a module-level name rebound in `main`, rather than a
    parameter threaded through five direction functions.
    """
    spec = importlib.util.spec_from_file_location("tasks_under_test", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import a tasks.py from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tasks_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


T = _load_subject(TASKS_PY)

#: Direction 6's pins -- the three terms of #141's coverage figure. They are literals here
#: and derived in `lint_coverage.py`, so the two files disagree if either drifts. The
#: commit is the same misfile `MISFILE_COMMIT` names; spelling it twice would be rule 12's
#: two-addresses defect, so direction 6 asserts them equal rather than promising it.
LC_COMMIT = "436bf64"
LC_TOTAL = 329185
LC_LINTED = 29591

#: The commit that fixed direction 2. Its parent is the positive control: the copy of
#: `tasks.py` that MUST fail the same harness, proving the harness can see the failure.
FIX_COMMIT = "466d436"

#: Task 32's done_when, recorded verbatim on 2026-08-23. It is the wording task 38 was
#: filed about, and it is pinned here as a LITERAL rather than read from the queue: the
#: queue is live, four agents write to it, and a pin that reads its own expectation from a
#: file another agent can edit is not a pin. A separate row asserts the file still says
#: this, so drift is visible rather than silent.
TASK_32_DONE_WHEN = (
    "research/11-doc-linting-for-agents.md exists, naming each tool the survey examined "
    "with its maintenance status and its measured output when run against this "
    "repository's real markdown, and stating explicitly which claims are demonstrated and "
    "which are guessed. If no tool is worth adopting, the file records that as the result "
    "with the evidence behind it, and that closes the task too")

#: (name, must_warn, done_when).
#:
#: The two ORIGINALS are reconstructions and are labelled as such: both were repaired
#: before this repository's first commit, so neither wording is in git, and the only
#: surviving statements of them are the paraphrases in `.claude/skills/tasks/SKILL.md`
#: ("SE below the smallest non-zero gap", "all six aspects"). They are reconstructed to the
#: SHAPE the check is about -- a universal or a threshold with nothing after it -- which is
#: the property under test, not the sentence.
#:
#: The four quiet rows are real wordings, and three of them are the defect: tasks 32, 35
#: and 58 each open an escape branch the old phrase list did not match.
WORDINGS: list[tuple[str, bool, str]] = [
    ("08-original (reconstructed)", True,
     "the SE for each (aspect, field) attempted is below the smallest non-zero gap "
     "between submissions"),
    ("01-original (reconstructed)", True,
     "all six aspects have a stored judge round for g3_arena and g4_platformer "
     "under eval/runs/"),
    ("universal, no escape at all", True,
     "every stored trial is re-graded and the table lists each submission"),
    ("threshold, no escape", True,
     "the pooled standard error is below 0.05"),
    # A REAL wording, and the only must-warn row here that is not reconstructed. Task 62's
    # done_when, recorded 2026-08-23: three universals, no escape branch, and it went quiet
    # for one day because "after whatever repairs those entries name" was read as one. It
    # is pinned as a literal and not re-read from the queue on purpose -- 62 is open, its
    # owner may well add an escape branch, and this row tests the predicate rather than the
    # task.
    ("62 real, a free relative is not an escape", True,
     "eval/withdrawn.json carries an entry for each of 20-of-24, the 380-paired-criteria "
     "pair (0 verdict differences and 219 of 380), each with match patterns proved against "
     "an archive anchor; docstat.py --withdrawn is green at HEAD after whatever repairs "
     "those entries name; and each entry was measured RED at a revision before its own "
     "withdrawal landed, so it is known the patterns can fire"),
    ("32 real, escape says 'If no tool'", False, TASK_32_DONE_WHEN),
    ("01 repaired, escape says 'any'", False,
     "every aspect that HAS evidence to read has a stored round for g3_arena and "
     "g4_platformer under eval/runs/, and any aspect skipped is named with the evidence "
     "it lacks"),
    ("08 repaired, escape says 'where'", False,
     "for each (aspect, field) attempted, the pooled SD, the SE at the n reached, and the "
     "count of submission PAIRS resolved (gap > SEi + SEj) are reported; a field where "
     "zero pairs resolve is reported as unresolvable-by-repetition with its measured "
     "gaps; and #58's ceiling gate is replaced rather than annotated"),
    # The two rows below pin the OTHER half of the repair. Neither is about an escape
    # branch: both are prose that carries no universal and no threshold at all, and warned
    # only because a substring match read an address as a comparison and an idiom as a
    # quantifier. Without these two rows, deleting `_ADDRESS` and `_NOT_A_QUANTIFIER` from
    # tasks.py would leave every row above green -- a mutant proved it.
    ("59 real, 'under' is a path not a threshold", False,
     "eval/FINDINGS.md's opening line names the highest finding number actually present, "
     "and the index renders as one table - verified by parsing the file and asserting the "
     "row count equals the number of entries found under eval/findings/, with the same "
     "assertion added to docstat.py --sweep so it cannot drift again"),
    ("38 real, 'at all' is an idiom not a quantifier", False,
     "tasks.py add run from inside an agent worktree exits 0 and prints the created path, "
     "and tasks.py check no longer warns on a done_when whose escape branch is phrased "
     "outside the ESCAPE keyword list, pinned in both directions against task 32's "
     "wording and against a done_when with no escape branch at all"),
    ("plain artifact condition", False,
     "research/11-doc-linting-for-agents.md exists and names the tool it adopted"),
]

_FM = ("---\nid: {tid}\ntitle: {title}\nstatus: {status}\npriority: 3\nrefs: ''\n"
       "{extra}{dw}---\n{body}")


def _task_file(tid: str, title: str = "a title", status: str = "todo",
               done_when: str | None = "something observable", body: str = "\nbody\n",
               extra: str = "") -> str:
    dw = "" if done_when is None else f"done_when: {done_when}\n"
    return _FM.format(tid=tid, title=title, status=status, dw=dw, body=body, extra=extra)


def _scratch_pair(tmp: Path) -> tuple[Path, Path]:
    """A main checkout with a `tasks/` queue, plus a worktree that does NOT have one.

    That asymmetry is the whole point of direction 2 and it is not simulated: it is a real
    `git worktree add`, so `tasks.py` resolves `TASKS` to the main checkout by exactly the
    mechanism it uses in this repository, while `ROOT` resolves to the worktree.
    """
    main, wt = tmp / "main", tmp / "wt"
    (main / "eval" / "tools").mkdir(parents=True)
    (main / "tasks").mkdir()
    git = ["git", "-C", str(main)]
    subprocess.run([*git, "init", "-q", "-b", "main", "."], check=True)
    subprocess.run([*git, "config", "user.email", "control@example.invalid"], check=True)
    subprocess.run([*git, "config", "user.name", "tasks_control"], check=True)
    (main / "README.md").write_text("scratch\n")
    subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-qm", "init"], check=True, capture_output=True)
    subprocess.run([*git, "worktree", "add", "-q", str(wt), "-b", "wt"],
                   check=True, capture_output=True)
    (wt / "eval" / "tools").mkdir(parents=True, exist_ok=True)
    return main, wt


def _run_tool(tool: Path, *argv: str) -> tuple[int, str]:
    """No pipe, no `|| echo`. The exit code IS the measurement (AGENTS.md rule 3)."""
    p = subprocess.run([sys.executable, str(tool), *argv], capture_output=True, text=True)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


# --------------------------------------------------------------------------- direction 1
def roundtrip_rows() -> tuple[list[tuple], list[str]]:
    """Every file in the LIVE shared queue must survive read-then-write byte for byte.

    The render is driven THE WAY `_set` DRIVES IT -- fm, body AND the reader's raw lines.
    A render called without them tests a writer nobody runs: before tasks/217 it stayed
    green here while the production write path (`_render(fm, body)`, no raw lines) rewrote
    a hand-quoted scalar plain and reddened every open pull request at once. A writer that
    will not accept what its own reader produces is a named FAIL, not a crash.
    """
    if not T.TASKS.is_dir():
        return [], [f"round trip NOT CHECKED - no queue at {T.TASKS}"]
    files = sorted(T.TASKS.glob("*.md"))
    if not files:
        return [], [f"round trip NOT CHECKED - {T.TASKS} is empty"]
    broken, unparseable = [], []
    for p in files:
        original = p.read_text(encoding="utf-8")
        try:
            fm, body, raw = T._read_fm(p)
        except T._Malformed as exc:
            unparseable.append(f"{p.name} ({exc})")
            continue
        try:
            rendered = T._render(fm, body, raw)
        except TypeError:
            broken.append(f"{p.name} (writer takes no raw lines)")
            continue
        if rendered != original:
            broken.append(p.name)
    rows = [(f"round trip: all {len(files)} queue files reproduce byte for byte",
             len(files) - len(broken) - len(unparseable), not broken and not unparseable,
             ("unchanged" if not broken else f"CHANGED: {', '.join(broken[:6])}")
             + (f"; unparseable: {', '.join(unparseable[:4])}" if unparseable else ""))]
    # A value-level row alongside it, so the byte row's stronger claim is visible as
    # stronger: this is the assertion that was green while ids were being renumbered.
    lost = [p.name for p in files
            if not _values_survive(p)]
    rows.append(("round trip: no frontmatter VALUE changes (the weaker claim, for contrast)",
                 len(files) - len(lost), not lost,
                 "unchanged" if not lost else f"CHANGED: {', '.join(lost[:6])}"))
    return rows, []


def _values_survive(p: Path) -> bool:
    try:
        fm, body, _raw = T._read_fm(p)
    except T._Malformed:
        return False
    import io
    reloaded = yaml.safe_load(io.StringIO(T._render(fm, body)).read().split("---\n")[1])
    return {str(k): T._scalar(v) for k, v in (reloaded or {}).items()} == \
           {str(k): T._scalar(v) for k, v in fm.items()}


# --------------------------------------------------------------------------- direction 2
def add_rows(tmp: Path, skip_prefix: bool) -> tuple[list[tuple], list[str]]:
    rows, unchecked = [], []
    main, wt = _scratch_pair(tmp / "add")

    def probe(src: Path, title: str) -> tuple[int, str, list[str]]:
        shutil.copy(src, main / "eval/tools/tasks.py")
        shutil.copy(src, wt / "eval/tools/tasks.py")
        # `--why` is passed because the CURRENT copy requires it and `check` now fails on an
        # empty body. The pre-fix positive control accepts it too -- it was optional there --
        # so one argv still exercises both copies.
        before = {q.name for q in (main / "tasks").glob("*.md")}
        rc, out = _run_tool(wt / "eval/tools/tasks.py", "add", title,
                            "--why", "a body, so the file `add` writes passes `check`",
                            "--done-when", "an observable condition")
        # What THIS invocation created, not what the queue holds: the positive control runs
        # first on the same scratch pair, so a whole-queue listing is 2 by the time the
        # current copy is probed and a `== 1` on it is false by construction. (The dead
        # `len(created) == len(created)` this replaced was that false row, abandoned rather
        # than aimed -- found by cleanup pass 37.)
        return rc, out, sorted(q.name for q in (main / "tasks").glob("*.md")
                               if q.name not in before)

    # The positive control FIRST: if the pre-fix copy passes this harness, the harness is
    # not exercising the path and the green row below would mean nothing.
    if skip_prefix:
        unchecked.append("`add` positive control NOT CHECKED - --skip-prefix was given. "
                         "Nothing here shows this harness can observe the defect at all.")
    else:
        prefix_py = tmp / "prefix_tasks.py"
        rc_g, blob = _run_tool_git("show", f"{FIX_COMMIT}^:eval/tools/tasks.py")
        if rc_g != 0:
            unchecked.append(f"`add` positive control NOT CHECKED - could not read "
                             f"{FIX_COMMIT}^:eval/tools/tasks.py ({blob[:90]}). A green "
                             f"row below is unproven, not passing.")
        else:
            prefix_py.write_text(blob if blob.endswith("\n") else blob + "\n")
            rc, out, created = probe(prefix_py, "pre fix positive control")
            rows.append((f"`add` from a worktree CAN report the defect ({FIX_COMMIT}^ "
                         f"must exit non-zero having written the file)",
                         rc, rc != 0 and len(created) == 1,
                         f"created {created}; {out.splitlines()[-1][:110] if out else ''}"))

    rc, out, created = probe(TASKS_PY, "current copy")
    printed = out.splitlines()[-1] if out else ""
    ok_path = printed.startswith("created ") and (main / "tasks").name in printed
    rows.append(("`add` from a worktree exits 0 and prints the created path", rc,
                 rc == 0 and ok_path and len(created) == 1,
                 f"{printed[:150]}"))
    rows.append(("`add` wrote into the MAIN checkout's queue, not the worktree's", 0,
                 bool(created) and not (wt / "tasks").exists(),
                 f"main queue {created}; worktree tasks/ exists: {(wt / 'tasks').exists()}"))
    return rows, unchecked


def _run_tool_git(*argv: str) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(TOOLS), *argv], capture_output=True, text=True)
    return p.returncode, (p.stdout if p.returncode == 0 else (p.stderr or "")).strip()


# ------------------------------------------------------------------- direction 2, `note`
#: The last commit before `note` existed, and direction 2's positive control for the rows
#: below. That copy of `tasks.py` has no `note` subcommand at all -- `argparse` rejects the
#: word and exits 2 -- so it MUST fail the same probe the current copy passes. Without it a
#: green row here is rule 1's `total=0 passed=0`: a harness that cannot observe the absence
#: of the capability proves nothing by reporting the capability.
PRE_NOTE_COMMIT = "ea9f853"

#: The ticket the note rows are appended to. A real body, because the property under test is
#: that the body AS DISPATCHED survives an append byte for byte -- an empty stub would make
#: "unchanged" vacuously true. Short enough that `misfiled_body` cannot reach it (its brief
#: is four words, below `MISFILED_MIN_BRIEF`), so nothing else in `check` can colour a row.
_NOTE_BODY = "\nthe brief exactly as it was dispatched, ending without a newline of its own"

#: A note that cannot be passed as argv. Backticks are command substitution before `tasks.py`
#: ever runs (#80) and a newline cannot survive a `done` evidence string at all -- which is
#: precisely what tasks 105 and 106 had to work around. `-` is the channel that carries both.
_NOTE_STDIN = (
    "The starter recipe is wrong: `just build` calls `cargo build --offline`.\n"
    "\n"
    "- measured on 4 of 12 trials\n"
    "- the next agent must not re-derive this\n")


def _expected_block(text: str, heading: str) -> str:
    """The bytes `note` is SUPPOSED to append. STATED HERE, deliberately not imported.

    IMPORTING `tasks.py`'s OWN `_note_block` MADE THESE ROWS INCAPABLE OF FAILING, and that
    was measured, not foreseen. The first version of this direction built its expected suffix
    with `T._note_block`, which reads correctly -- one value at one address, AGENTS.md rule 12
    -- and is wrong here for the opposite reason: the subject and the expectation moved
    together. `tasks_mutants.py`'s `note_no_separator`, which deletes the leading newline that
    separates the section from the body, came back SURVIVED with **0 red rows of 48**. The
    check agreed with the mutant because the mutant had edited the check.

    Rule 12 is about one FACT at one address. An expectation is not the fact; it is the
    second, independent statement of it, and a control that imports its expectation from its
    subject is not a control. Where the two must be kept in step, do it with a row that
    compares them -- never by making them the same object.

    `heading` is required rather than defaulting to today's date for a smaller reason with the
    same shape: two `strftime` calls straddling midnight would make this disagree with the
    subject over nothing. The DEFAULT heading is pinned separately, by a row that matches its
    shape with a regex rather than by recomputing the date.
    """
    return f"\n## {heading}\n\n{text.strip()}\n"


#: The default heading's shape -- `## note <ISO date>` -- and the blank line under it, with
#: the leading newline that separates the section from whatever the body ended with. Written
#: as a pattern here for `_expected_block`'s reason: it is the independent statement of the
#: format, and it is what goes red if the separator or the date is dropped.
_DEFAULT_BLOCK_RE = re.compile(r"^\n## note \d{4}-\d\d-\d\d\n\n(.*)\n$", re.S)


def note_rows(tmp: Path, skip_prefix: bool) -> tuple[list[tuple], list[str]]:
    """Can a dispatched agent append what it learned to a ticket BODY, from its worktree,
    without disturbing a byte of the ticket it was briefed from?

    Every row runs the tool from the WORKTREE and reads the file in the MAIN checkout. That
    asymmetry is the defect's address: `TASKS` and `ROOT` disagree only there, and a probe
    run in the main checkout would pass on a `note` that wrote to the wrong queue entirely.
    """
    rows, unchecked = [], []
    main, wt = _scratch_pair(tmp / "note")
    target = main / "tasks" / "70-a.md"
    original = _task_file("70", body=_NOTE_BODY)

    def probe(src: Path, *argv: str, stdin: str | None = None,
              reset: bool = True) -> tuple[int, str, str]:
        shutil.copy(src, main / "eval/tools/tasks.py")
        shutil.copy(src, wt / "eval/tools/tasks.py")
        if reset:
            target.write_text(original, encoding="utf-8")
        p = subprocess.run([sys.executable, str(wt / "eval/tools/tasks.py"), *argv],
                           capture_output=True, text=True, input=stdin)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip(), target.read_text()

    # THE POSITIVE CONTROL FIRST, for the same reason `add_rows` runs one: if the copy that
    # predates the subcommand passes this harness, the harness is not exercising it.
    if skip_prefix:
        unchecked.append("`note` positive control NOT CHECKED - --skip-prefix was given. "
                         "Nothing in the note rows shows this harness can observe the "
                         "absence of the subcommand.")
    else:
        rc_g, blob = _run_tool_git("show", f"{PRE_NOTE_COMMIT}:eval/tools/tasks.py")
        if rc_g != 0:
            unchecked.append(f"`note` positive control NOT CHECKED - could not read "
                             f"{PRE_NOTE_COMMIT}:eval/tools/tasks.py ({blob[:90]}). The "
                             f"note rows below are unproven, not passing.")
        else:
            pre_py = tmp / "pre_note_tasks.py"
            pre_py.write_text(blob if blob.endswith("\n") else blob + "\n")
            rc, out, after = probe(pre_py, "note", "70", "anything at all")
            rows.append((f"`note` CAN be reported missing ({PRE_NOTE_COMMIT} must exit "
                         f"non-zero and write nothing)", rc,
                         rc != 0 and after == original,
                         f"exit {rc}, file unchanged: {after == original}; "
                         f"{out.splitlines()[-1][:90] if out else ''}"))

    # --- the capability itself, run from the worktree.
    text = "what working this task established, in one line"
    head = "note 2026-08-23, first pass"
    expected = _expected_block(text, head)
    rc, out, after = probe(TASKS_PY, "note", "70", text, "--heading", head)
    printed = out.splitlines()[-1] if out else ""
    rows.append(("`note` from a worktree exits 0 and prints the MAIN checkout's file", rc,
                 rc == 0 and printed.startswith("appended ") and str(target) in printed,
                 printed[:150]))
    rows.append(("`note` wrote into the MAIN checkout's queue, not the worktree's", 0,
                 after != original and not (wt / "tasks").exists(),
                 f"main file grew by {len(after) - len(original)} bytes; worktree tasks/ "
                 f"exists: {(wt / 'tasks').exists()}"))

    # THE ROW THE TICKET ASKED FOR. Not "the values survived" and not "it still parses": the
    # file afterwards is the file before it PLUS the expected section and NOTHING else.
    rows.append(("the noted ticket is byte-identical plus exactly the section appended",
                 len(expected), after == original + expected,
                 "identical + block" if after == original + expected
                 else f"DIFFERS: prefix intact={after.startswith(original)}; "
                      f"suffix={after[len(original):][:70]!r}"))
    # The weaker claim beside the stronger one, as direction 1 does, because they fail
    # differently: a `note` that rewrote the frontmatter through `_render` would keep every
    # value and break the row above, which is the whole reason the row above is the byte one.
    rows.append(("`note` leaves every frontmatter value alone (the weaker claim, for "
                 "contrast)", 0, _fm_values(after) == _fm_values(original),
                 f"{_fm_values(original)} -> {_fm_values(after)}"))

    # Stacking. A second note must not replace the first, and the first must still be there
    # byte for byte -- otherwise "append" is a rewrite that happens to look like one.
    first = after
    expected2 = _expected_block("a second, later note", "note 2026-08-23, second pass")
    rc2, _out2, after2 = probe(TASKS_PY, "note", "70", "a second, later note",
                               "--heading", "note 2026-08-23, second pass", reset=False)
    rows.append(("a second `note` stacks and the first section is untouched", rc2,
                 rc2 == 0 and after2 == first + expected2,
                 "stacked" if after2 == first + expected2
                 else f"DIFFERS: {after2[len(first):][:70]!r}"))

    # THE DEFAULT HEADING, which every real invocation will use. Matched by SHAPE rather than
    # by recomputing today's date, so it cannot disagree with the subject over a clock -- and
    # the pattern carries the leading newline, which is what separates the section from the
    # body and what a mutant deleting it must go red on.
    rc_d, _out_d, after_d = probe(TASKS_PY, "note", "70", text)
    m_d = _DEFAULT_BLOCK_RE.match(after_d[len(original):])
    rows.append(("the default heading is `## note <ISO date>`, separated from the body", rc_d,
                 rc_d == 0 and after_d.startswith(original) and bool(m_d)
                 and m_d.group(1) == text,
                 f"suffix: {after_d[len(original):][:70]!r}"))

    # THE SAME CLAIM ON A BODY THAT ENDS IN A NEWLINE, which is what every real queue file
    # does. `_NOTE_BODY` deliberately does NOT, because that is the harder case for a leading
    # separator -- and a separator right for one shape and wrong for the other would pass a
    # probe that only ever fed it one. This is the variant half of rule 15: it asks whether
    # the check can still PASS on an input a mutant cannot manufacture. It writes its own
    # `original` rather than going through `probe`, which resets to the other shape.
    original_nl = _task_file("70", body=_NOTE_BODY + "\n")
    target.write_text(original_nl, encoding="utf-8")
    p_nl = subprocess.run([sys.executable, str(wt / "eval/tools/tasks.py"),
                           "note", "70", text, "--heading", head],
                          capture_output=True, text=True)
    after_nl = target.read_text()
    rows.append(("the same, on a body that DOES end in a newline", p_nl.returncode,
                 p_nl.returncode == 0 and after_nl == original_nl + expected,
                 "identical + block" if after_nl == original_nl + expected
                 else f"DIFFERS: {after_nl[len(original_nl):][:70]!r}"))

    # `-`: the channel that carries what `established_by` cannot. This is the row that
    # closes #80's half of the ticket, so it asserts the backtick and the newlines arrive.
    rc3, _out3, after3 = probe(TASKS_PY, "note", "70", "-", "--heading", head,
                               stdin=_NOTE_STDIN)
    rows.append(("`note 70 -` carries backticks and newlines from stdin verbatim", rc3,
                 rc3 == 0 and after3 == original + _expected_block(_NOTE_STDIN, head)
                 and "`just build`" in after3,
                 f"backtick present: {'`just build`' in after3}; "
                 f"lines added: {after3.count(chr(10)) - original.count(chr(10))}"))

    # The appended ticket must still pass the lint it is briefed through -- `check` reads
    # bodies now, and an append that broke `_FM_RE` or the misfiled-body comparison would be
    # a repair that costs the gate. Run in the MAIN checkout, where `check` reads the queue.
    rc4, out4 = _run_tool(main / "eval/tools/tasks.py", "check")
    rows.append(("`check` is still clean on a ticket that has been noted", rc4,
                 rc4 == 0 and "well-formed" in out4,
                 f"exit {rc4}: {out4.splitlines()[-1][:100] if out4 else '(none)'}"))

    # --- both refusals. A write that reports failure and a failure that reports success are
    # the two shapes rule 7 is about; these assert the file is untouched in each case.
    rc5, out5, after5 = probe(TASKS_PY, "note", "99", "a note for a task that is not there")
    rows.append(("`note` on an unknown id exits 1 and writes nothing", rc5,
                 rc5 == 1 and after5 == original
                 and len(list((main / "tasks").glob("*.md"))) == 1,
                 f"exit {rc5}, file unchanged: {after5 == original}; "
                 f"{out5.splitlines()[-1][:70] if out5 else ''}"))
    rc6, out6, after6 = probe(TASKS_PY, "note", "70", "-", stdin="   \n\n  \n")
    rows.append(("`note` refuses an empty note rather than writing a bare heading", rc6,
                 rc6 == 1 and after6 == original,
                 f"exit {rc6}, file unchanged: {after6 == original}; "
                 f"{out6.splitlines()[-1][:70] if out6 else ''}"))
    return rows, unchecked


def _fm_values(text: str) -> dict:
    """Every frontmatter value of a task file held as TEXT, for the contrast row above."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {"(no frontmatter)": text[:40]}
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception:                                           # noqa: BLE001
        return {"(unparseable)": m.group(1)[:40]}
    return {str(k): T._scalar(v) for k, v in (fm or {}).items()}


# --------------------------------------------------------------------------- direction 3
#: (name, files, must_fail, the phrase the failure must NAME).
#:
#: Naming matters as much as the exit code: `check` reporting "1 problem(s)" without
#: saying which file is a gate you cannot act on, and all three of these were fixed by
#: hand once already.
CHECK_CASES: list[tuple[str, dict[str, str], bool, str]] = [
    ("well-formed queue (negative control: `check` CAN exit 0)",
     {"70-a.md": _task_file("70"), "71-b.md": _task_file("71")}, False, "well-formed"),
    ("duplicate id",
     {"70-a.md": _task_file("70"), "70-b.md": _task_file("70")}, True, "used by 2 files"),
    ("missing done_when",
     {"70-a.md": _task_file("70", done_when=None)}, True, "no `done_when`"),
    ("bad status",
     {"70-a.md": _task_file("70", status="wip")}, True, "not in"),
    # THE FIVE-VALUE VOCABULARY, BOTH DIRECTIONS. The rows above only ever asked whether a
    # WRONG status fails; nothing asked whether a RIGHT one passes, so dropping a value from
    # STATUSES would have left every row green. `in_review` carries its `pr` because `check`
    # requires one -- the row below is what pins that requirement.
    ("every one of the 5 statuses (the vocabulary can still go green)",
     {"70-a.md": _task_file("70", status="todo"),
      "71-b.md": _task_file("71", status="in_progress"),
      "72-c.md": _task_file("72", status="in_review",
                            extra="pr: https://github.com/o/r/pull/1\n"),
      "73-d.md": _task_file("73", status="in_testing",
                            extra="pr: https://github.com/o/r/pull/2\n"),
      "74-e.md": _task_file("74", status="done")}, False, "well-formed"),
    # The legacy names an agent forked before 2026-08-23 still writes into the SHARED queue.
    # If this ever goes red, every peer's `check` is red on a file none of them touched.
    ("legacy `open` and `in_flight` still lint clean (a stale worktree writes them)",
     {"70-a.md": _task_file("70", status="open"),
      "71-b.md": _task_file("71", status="in_flight")}, False, "well-formed"),
    ("`in_review` with no `pr` (the state stops being a locator)",
     {"70-a.md": _task_file("70", status="in_review")}, True, "no `pr`"),
    # The state the orchestrator MERGES FROM, which is the one that matters more. Its own row,
    # not a parametrisation of the one above, so narrowing PR_REQUIRED back to `in_review`
    # alone -- the shipped-but-half-gated shape, not a deleted branch -- goes red.
    ("`in_testing` with no `pr` (the orchestrator is told to merge nothing)",
     {"70-a.md": _task_file("70", status="in_testing")}, True, "no `pr`"),
    ("both PR states WITH a `pr` still lint clean (the requirement can be satisfied)",
     {"70-a.md": _task_file("70", status="in_review",
                            extra="pr: https://github.com/o/r/pull/1\n"),
      "71-b.md": _task_file("71", status="in_testing",
                            extra="pr: https://github.com/o/r/pull/2\n")}, False, "well-formed"),
    # Direction 5's degenerate half, exercised synthetically as well as on the real blob,
    # because it must hold for a task nobody ever wrote a body for -- not only for the one
    # 436bf64 produced. `_task_file`'s brief is four words, below MISFILED_MIN_BRIEF, so the
    # containment check cannot reach these rows and this isolates the empty-body branch.
    ("empty body (the stub `add` writes, never filled in)",
     {"70-a.md": _task_file("70", body="\n\n")}, True, "body is empty"),
]


def check_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    rows = []
    for i, (name, files, must_fail, phrase) in enumerate(CHECK_CASES):
        main, _ = _scratch_pair(tmp / f"check{i}")
        shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
        for fn, text in files.items():
            (main / "tasks" / fn).write_text(text)
        rc, out = _run_tool(main / "eval/tools/tasks.py", "check")
        want_rc = 1 if must_fail else 0
        rows.append((f"`check` on {name}", rc,
                     rc == want_rc and phrase in out,
                     f"want exit {want_rc} naming {phrase!r}; got: "
                     f"{out.splitlines()[-1][:110] if out else '(no output)'}"))
    return rows, []


# --------------------------------------------------------------------------- direction 4
def _wording(name: str) -> str:
    """One `WORDINGS` row's done_when, BY NAME. Never a second copy of the text.

    4c has to be pinned on the same wordings 4a/4b are, or the two halves of this direction
    drift apart and each stays green on its own copy -- rule 12, one value at two addresses.
    A missing name is a hard failure rather than a skipped row: a pin that silently stops
    pointing at anything is the shape this whole file exists to catch.
    """
    for n, _must_warn, dw in WORDINGS:
        if n == name:
            return dw
    raise SystemExit(f"WORDINGS has no row named {name!r}, which direction 4c is pinned on")


def reachability_printed_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    """4c: does `check` PRINT what `reachability_warning` returns?

    One task per scratch queue, so nothing else in `check` can be the reason a row is red:
    a single ticket has no neighbour to lose a containment comparison against, and its body
    is non-empty. `status: open`, because `cmd_check` skips `done` deliberately.
    """
    rows = []
    # Two quiet rows, not one, and they are quiet for DIFFERENT reasons. The first carries no
    # universal and no threshold, so the predicate never gets as far as looking for an escape
    # branch; the second is a real done_when that carries both a universal AND an escape, so
    # it is the only one of the three that can go red if the escape class is dropped. A
    # negative control that cannot be made to fail is rule 1's `total=0 passed=0`, and
    # `tasks_mutants.py` runs a mutant against each of these three rows.
    cases = [
        ("an UNREACHABLE done_when: the warning text is PRINTED", True,
         _wording("universal, no escape at all")),
        ("a done_when with no universal at all: nothing is printed", False,
         _wording("plain artifact condition")),
        ("a universal WITH an escape branch (task 32's real wording): nothing is printed",
         False, _wording("32 real, escape says 'If no tool'")),
    ]
    for i, (label, must_print, dw) in enumerate(cases):
        main, _ = _scratch_pair(tmp / f"warnprint{i}")
        shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
        (main / "tasks" / "70-a.md").write_text(_task_file("70", done_when=dw))
        rc, out = _run_tool(main / "eval/tools/tasks.py", "check")
        # The HEADER and the per-task LINE, both. The header alone would survive a loop that
        # printed a count and no warnings; the line alone would survive a message that named
        # no task. `70:` is the id `check` must attribute it to.
        printed = "reachability warning(s):" in out and "70: done_when says" in out
        rows.append((f"`check` end to end on {label}", rc,
                     rc == 0 and printed == must_print,
                     f"want exit 0 and the warning "
                     f"{'PRINTED' if must_print else 'ABSENT'}; got exit {rc}, "
                     f"printed={printed}: {out.splitlines()[0][:90] if out else '(none)'}"))
    return rows, []


def reachability_rows() -> tuple[list[tuple], list[str]]:
    rows, unchecked = [], []
    for name, must_warn, dw in WORDINGS:
        msg = T.reachability_warning(dw)
        rows.append((f"reachability {'WARNS' if must_warn else 'quiet'}: {name}",
                     0, bool(msg) == must_warn,
                     (msg or "(quiet)")[:110]))
    # Does the pinned literal still match the queue? A pin that has silently drifted from
    # the thing it pins is worse than no pin, so this is reported rather than assumed.
    matches = sorted(T.TASKS.glob("32-*.md")) if T.TASKS.is_dir() else []
    if not matches:
        unchecked.append("task 32's wording NOT CHECKED against the queue - no tasks/32-*.md. "
                         "The literal in WORDINGS stands, unverified against its source.")
    else:
        m = re.search(r"^done_when: (.*)$", matches[0].read_text(), re.M)
        on_disk = (m.group(1) if m else "").strip().strip("'\"")
        rows.append(("task 32's pinned literal still matches tasks/32-*.md", 0,
                     on_disk == TASK_32_DONE_WHEN,
                     "identical" if on_disk == TASK_32_DONE_WHEN
                     else f"DRIFTED; on disk: {on_disk[:100]}"))
    return rows, unchecked


# --------------------------------------------------------------------------- direction 5
#: The commit that misfiled task 71's whole brief into `tasks/70-...md` and left `tasks/71`
#: a stub. Both halves are read as BLOBS rather than reconstructed, for the reason direction
#: 2 reads its positive control from git: a defect retyped from memory is a defect you have
#: already decided the shape of.
MISFILE_COMMIT = "436bf64"

#: The commit that repaired it. Its two files are direction 5's negative control -- the same
#: two tickets, correctly filed, which must go quiet.
REPAIR_COMMIT = "28f6598"

#: A queue snapshot holding the highest-scoring pair in the whole history that is NOT a
#: defect: task 62's body against task 70's brief, margin 0.1399. Task 62 is genuinely about
#: the DECISIONS.md row task 70 owns, so it is the nearest thing to a false positive this
#: corpus contains, and the row below is what makes lowering `MISFILED_MARGIN` toward it go
#: red. Fixed commit, not the live queue: 62 is editable by peers and a pin that moves is not
#: a pin.
NEAR_MISS_COMMIT = "fc7e0cf1"

_T70 = "tasks/70-set-a-size-for-the-within-cell-verdict-variance-.md"
_T71 = "tasks/71-nothing-reads-the-disclosures-31-of-75-completed.md"
_T62 = "tasks/62-register-the-other-three-withdrawn-readme-figure.md"
#: Ten other task ids in its body, and it is correctly filed. The row that pins what this
#: check is NOT keyed on: 58 of 85 live bodies name another task's id, so a check that fired
#: on id mentions would fire on 68% of the queue -- and would still have missed 436bf64,
#: whose 59 misfiled lines never say "task 71" once.
_T72 = "tasks/72-decide-what-the-templates-improvement-loop-is-fo.md"


def _blob(commit: str, path: str) -> str | None:
    """A blob BYTE FOR BYTE. Deliberately not `_run_tool_git`, which `.strip()`s its output.

    That strip is right for a command's report and wrong for a file: task 71's stub body is
    exactly "\\n\\n", so stripping leaves a file ending `---` with no trailing newline, and
    `_FM_RE` then reads the whole thing as "no frontmatter". The control's first run said
    the defect blob was malformed rather than misfiled -- a green-adjacent wrong answer
    produced by the harness, not by the subject.
    """
    p = subprocess.run(["git", "-C", str(TOOLS), "show", f"{commit}:{path}"],
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def _snapshot_briefs(commit: str) -> tuple[dict[str, str], dict[str, str]]:
    """(briefs, bodies) for every task file at `commit`, keyed by id. Built through
    `tasks.py`'s own `brief`, so a change to it shows up here.

    `--full-tree` because a pathspec is resolved relative to CWD and this runs `-C` into
    `eval/tools`, where `tasks/` names nothing. Without it every row below reported NOT
    CHECKED -- AGENTS.md rule 12, the address is an input to the check.
    """
    rc, out = _run_tool_git("ls-tree", "-r", "--full-tree", "--name-only", commit, "tasks/")
    if rc != 0:
        return {}, {}
    briefs, bodies = {}, {}
    for path in out.split("\n"):
        if not path.endswith(".md"):
            continue
        text = _blob(commit, path)
        if text is None:
            continue
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text if text.endswith("\n") else text + "\n",
                     re.S)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except Exception:
            continue
        if not isinstance(fm, dict):
            continue
        tid = path.split("/")[1].split("-")[0]
        briefs[tid] = T.brief(fm)
        bodies[tid] = m.group(2)
    return briefs, bodies


def misfiled_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    rows, unchecked = [], []

    # 5a/5b -- `check` end to end on the real blobs, broken then repaired. The scratch queue
    # carries the four tickets those two cite, so the containment check has real neighbours
    # to lose against rather than a two-file field.
    def scratch_check(label: str, files: dict[str, str], want_rc: int, phrases: list[str],
                      i: int) -> None:
        main, _ = _scratch_pair(tmp / f"misfiled{i}")
        shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
        for name, text in files.items():
            (main / "tasks" / name).write_text(text)
        rc, out = _run_tool(main / "eval/tools/tasks.py", "check")
        missing = [p for p in phrases if p not in out]
        rows.append((f"`check` {label}", rc, rc == want_rc and not missing,
                     f"want exit {want_rc}"
                     + (f" naming {phrases}" if phrases else "")
                     + f"; got exit {rc}: {out.splitlines()[-1][:100] if out else '(none)'}"
                     + (f"; MISSING {missing}" if missing else "")))

    neighbours = {}
    for path in (_T62, "tasks/13-pin-or-withdraw-the-380-paired-criteria-figure.md",
                 "tasks/46-pre-register-whether-a-required-finish-report-se.md"):
        text = _blob(MISFILE_COMMIT, path)
        if text is not None:
            neighbours[path.split("/")[1]] = text

    broken70, broken71 = _blob(MISFILE_COMMIT, _T70), _blob(MISFILE_COMMIT, _T71)
    fixed70, fixed71 = _blob(REPAIR_COMMIT, _T70), _blob(REPAIR_COMMIT, _T71)
    if None in (broken70, broken71, fixed70, fixed71):
        unchecked.append(
            f"the misfiled-body rows are NOT CHECKED - could not read {MISFILE_COMMIT} or "
            f"{REPAIR_COMMIT} from git. Nothing below shows this check can see the defect.")
    else:
        scratch_check("FAILS on the real 436bf64 pair, naming BOTH halves",
                      {**neighbours, _T70.split("/")[1]: broken70,
                       _T71.split("/")[1]: broken71},
                      1, ["reads as task 71's brief", "body is empty"], 0)
        # The negative control that matters most: the same two tickets, repaired. If this
        # goes red the check is not discriminating misfiling, it is disliking these files.
        scratch_check("is QUIET on the same two tickets once repaired (28f6598)",
                      {**neighbours, _T70.split("/")[1]: fixed70,
                       _T71.split("/")[1]: fixed71},
                      0, ["well-formed"], 1)

    # 5c -- `misfiled_body` directly, which is where the THRESHOLD is pinned from both sides.
    briefs, bodies = _snapshot_briefs(NEAR_MISS_COMMIT)
    mis_briefs, mis_bodies = _snapshot_briefs(MISFILE_COMMIT)
    if not mis_briefs or "70" not in mis_bodies:
        unchecked.append(f"threshold rows NOT CHECKED - no queue snapshot at {MISFILE_COMMIT}")
    else:
        msg = T.misfiled_body(mis_bodies["70"], mis_briefs, "70")
        rows.append(("threshold, upper side: the real misfiled body FIRES and names 71",
                     0, bool(msg) and "task 71" in msg, (msg or "(quiet)")[:110]))
    if not briefs or "62" not in bodies:
        unchecked.append(f"near-miss row NOT CHECKED - no queue snapshot at {NEAR_MISS_COMMIT}")
    else:
        msg = T.misfiled_body(bodies["62"], briefs, "62")
        rows.append(("threshold, lower side: the worst real NON-defect (62 vs 70, margin "
                     "0.14) stays quiet", 0, msg is None, (msg or "(quiet)")[:110]))
        if "72" in bodies:
            msg = T.misfiled_body(bodies["72"], briefs, "72")
            rows.append(("a body naming TEN other task ids stays quiet (id mentions are not "
                         "the trigger)", 0, msg is None, (msg or "(quiet)")[:110]))
        else:
            unchecked.append(f"the id-mention row NOT CHECKED - no {_T72} at "
                             f"{NEAR_MISS_COMMIT}")

    # 5d -- a brief too short to accuse anyone with.
    #
    # THE FIRST VERSION OF THIS ROW MEASURED NOTHING, and a mutant said so: setting
    # MISFILED_MIN_BRIEF to 0 left all 28 rows green. It fed a five-word brief whose shingles
    # were absent from the body, so containment was 0 with the floor and 0 without it -- the
    # floor was never the reason it was quiet. The row now uses a short brief drawn FROM the
    # body, so its containment is 1.0 and only the floor keeps it quiet.
    #
    # That is the case the floor exists for: a genuine stub ticket whose title happens to
    # share a phrase with a long neighbouring body would otherwise be "restated 100%" by it.
    # Measured on the live queue the same day, the SMALLEST real brief is 23 shingles against
    # a floor of 8, so this costs no coverage on anything anyone has actually written.
    if mis_bodies.get("70"):
        short = "the grading pipeline reads any"       # 3 shingles, all present in the body
        n_short = len(T._shingles(short))
        got = T.misfiled_body(mis_bodies["70"], {"70": mis_briefs.get("70", ""),
                                                 "71": short}, "70")
        # The row asserts its own PRECONDITION as well as its result. Otherwise dropping the
        # floor to 0 makes the premise false rather than the row red, and a row whose premise
        # a mutant can delete is a row that stops measuring silently.
        rows.append(("a brief too short to accuse with stays quiet EVEN AT 100% containment "
                     "(MISFILED_MIN_BRIEF)", n_short,
                     n_short < T.MISFILED_MIN_BRIEF and got is None,
                     f"{n_short} shingles vs floor {T.MISFILED_MIN_BRIEF}; "
                     + (got or "(quiet)")[:90]))
    return rows, unchecked


# --------------------------------------------------------------------------- direction 6
def coverage_rows() -> tuple[list[tuple], list[str]]:
    """#141's coverage figure, run rather than quoted.

    Direction 5 asks whether the repaired lint can catch the misfile. This asks the prior
    question the finding is built on: how little of a task file the lint ever read. It is
    here because the figure was published WRONG -- `27,156 of 328,692 bytes, 8.3%`, both
    terms -- and survived review for exactly as long as it took someone to re-measure at
    merge. It had no producer, so nothing in the repository could disagree with it, which
    is the defect AGENTS.md names in the "how much of anything" row rather than a slip.

    The producer's own pins live in `lint_coverage.py --selftest`; this runs them, so the
    figure cannot drift from the document without a red row here.
    """
    rows, unchecked = [], []
    # BY PATH, not by name, for the reason `_load_subject` gives: `sys.path` no longer
    # carries TOOLS, and an `import lint_coverage` that fell back to NOT CHECKED would
    # have degraded this direction silently the moment task 105 removed the insert. The
    # producer is never the subject, so it is loaded from TOOLS and not from `--tasks-py`.
    try:
        LC = _load_module("lint_coverage", TOOLS / "lint_coverage.py")
    except Exception as exc:                                    # noqa: BLE001
        return rows, [f"#141's coverage figure NOT CHECKED - eval/tools/lint_coverage.py "
                      f"did not load ({type(exc).__name__}). The published 9.0% stands "
                      f"unverified, which is not the same as verified."]
    try:
        n, lint, total = LC.measure(LC_COMMIT)
    except Exception as exc:                                    # noqa: BLE001
        return rows, [f"#141's coverage figure NOT CHECKED - reading {LC_COMMIT} from git "
                      f"failed ({type(exc).__name__}). A shallow clone has no history to "
                      f"measure and that is not the same as a passing check."]
    # Rule 12: the same commit is spelled in two constants, so assert them equal in code.
    rows.append(("#141: direction 6 measures the same commit direction 5 repairs", 0,
                 LC_COMMIT == MISFILE_COMMIT,
                 f"LC_COMMIT {LC_COMMIT} vs MISFILE_COMMIT {MISFILE_COMMIT}"))
    rows.append((f"#141: files in {LC_COMMIT}'s tasks/ tree", n, n == 70, f"{n} of 70"))
    rows.append(("#141: total bytes (the denominator, a bare count with no method in it)",
                 total, total == LC_TOTAL, f"{total:,} of {LC_TOTAL:,}"))
    rows.append(("#141: bytes the pre-fix lint evaluated", lint, lint == LC_LINTED,
                 f"{lint:,} of {LC_LINTED:,} = {100 * lint / total:.1f}%"))
    # The denominator, independently. `measure` reads blobs through `cat-file`; this reads
    # the sizes git recorded for those blobs. Two routes to one number that has no method
    # in it -- so if they ever disagree the bug is in the walk, not in the definition.
    try:
        ls = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-l", LC_COMMIT, "tasks/"],
                            capture_output=True, text=True, check=True).stdout.splitlines()
        summed = sum(int(r.split()[3]) for r in ls)
        rows.append(("#141: denominator agrees with git's own blob sizes", summed,
                     summed == total, f"ls-tree {summed:,} vs walk {total:,}"))
    except Exception as exc:                                    # noqa: BLE001
        unchecked.append(f"#141's denominator NOT CHECKED against git ls-tree "
                         f"({type(exc).__name__}).")
    # THE NUMERATOR IS METHOD-DEPENDENT AND THE DOCUMENT SAYS SO. Pinning the gap is what
    # keeps that sentence honest: if a future edit makes the two methods agree exactly, the
    # document's claim that the choice costs 47 bytes is false and this goes red.
    try:
        _, alt, _ = LC.measure(LC_COMMIT, LC.linted_bytes_via_yaml)
        rows.append(("#141: the second extraction method still lands 47 bytes away",
                     lint - alt, lint - alt == 47, f"{lint:,} - {alt:,} = {lint - alt}"))
    except Exception as exc:                                    # noqa: BLE001
        unchecked.append(f"#141's method gap NOT CHECKED ({type(exc).__name__}); PyYAML is "
                         f"the likely cause.")
    return rows, unchecked


# --------------------------------------------------------------------------- direction 7
def status_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    """The 5-value status vocabulary: its transitions, and the one other file that counts it.

    `check_rows` asks whether `check` accepts and rejects the right values. This asks the two
    questions `check` structurally cannot:

    * do `start`, `review`, `testing` and `done` actually WRITE the state they name? A
      subcommand wired to the wrong constant produces a queue that lints clean and reports the
      wrong thing -- the shape this project calls a mechanism that runs and measures nothing.
    * does `heartbeat.py` count all 5? Its map is a SECOND address for the vocabulary, and
      rule 12 says two addresses are asserted equal in code. Before this, `_tasks` held a
      hardcoded 3-key dict and dropped the rest: over a queue with 1 file in each of 5 states
      it counted 3, so a ticket in review vanished from every counter.
    """
    rows, unchecked = [], []
    main, _ = _scratch_pair(tmp / "status")
    shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
    tool = main / "eval/tools/tasks.py"
    (main / "tasks" / "70-a.md").write_text(_task_file("70"))

    # Each transition, run through the real command line, then read back off disk. `review`
    # and `testing` take an argument, so the row also proves the argument reaches the file.
    for cmd, argv, want in (("start", (), "in_progress"),
                            ("review", ("https://github.com/o/r/pull/9",), "in_review"),
                            ("testing", ("a measurement, not the word completed",), "in_testing"),
                            ("done", ("a measurement, not the word completed",), "done")):
        rc, out = _run_tool(tool, cmd, "70", *argv)
        text = (main / "tasks" / "70-a.md").read_text()
        got = re.search(r"^status:\s*(\S+)", text, re.M)
        rows.append((f"`{cmd}` writes status {want}", rc,
                     rc == 0 and got is not None and got.group(1) == want,
                     f"exit {rc}, file says {got.group(1) if got else '(none)'}; "
                     f"{out.splitlines()[-1][:70] if out else ''}"))
    rows.append(("`review` recorded the pull request in the ticket (the ticket -> PR link)", 0,
                 "https://github.com/o/r/pull/9" in
                 (main / "tasks" / "70-a.md").read_text(),
                 "pr: present" if "pull/9" in (main / "tasks" / "70-a.md").read_text()
                 else "PR URL NOT IN THE FILE"))

    # The second address. Loaded by path, never by name, for `_load_subject`'s reason.
    try:
        HB = _load_module("heartbeat_for_status", TOOLS / "heartbeat.py")
    except Exception as exc:                                    # noqa: BLE001
        return rows, [f"heartbeat's status map NOT CHECKED - eval/tools/heartbeat.py did not "
                      f"load ({type(exc).__name__}). A status counted by nothing is invisible "
                      f"in exactly the way this row exists to prevent."]
    rows.append(("heartbeat's TASK_METRIC covers EXACTLY tasks.py's STATUSES (rule 12)",
                 len(HB.TASK_METRIC), tuple(HB.TASK_METRIC) == T.STATUSES,
                 f"{tuple(HB.TASK_METRIC)} vs {T.STATUSES}"))
    # And the count itself, on a queue whose true answer is stated in advance: 1 file per
    # status plus 1 legacy alias per legacy name. Proving the extraction on a known case is
    # what rule 12's corollary asks for -- the old code returned 3 here and looked fine.
    hb_root = tmp / "hbqueue"
    (hb_root / "tasks").mkdir(parents=True)
    for i, st in enumerate(list(T.STATUSES) + list(T.LEGACY_STATUSES)):
        (hb_root / "tasks" / f"{i}-x.md").write_text(f"---\nid: 0{i}\nstatus: {st}\n---\nb\n")
    n_files = len(T.STATUSES) + len(T.LEGACY_STATUSES)
    HB.ROOT = hb_root
    counted = HB._tasks()
    rows.append((f"heartbeat counts every file in a queue holding all {n_files} spellings",
                 sum(counted.values()), sum(counted.values()) == n_files,
                 f"{sum(counted.values())} of {n_files}: {counted}"))
    rows.append(("heartbeat maps the legacy names onto the canonical states, not onto nothing",
                 counted.get("todo", 0), counted.get("todo") == 2
                 and counted.get("in_progress") == 2 and counted.get("") == 0,
                 f"todo={counted.get('todo')} in_progress={counted.get('in_progress')} "
                 f"unknown={counted.get('')}"))
    return rows, unchecked


# --------------------------------------------------------------------------- direction 8
#: The last commit before `testing`/`done` read `-`, and direction 8's positive control. That
#: copy stores the LITERAL one-character string and exits 0, so it MUST fail the rows below:
#: without it a green direction 8 is rule 1's `total=0 passed=0`, since every refusal row
#: would also pass against a `tasks.py` that had never heard of the sentinel.
PRE_EVIDENCE_COMMIT = "dce1172"

#: A real closing account: multi-line, the shape an agent redirects into `done <id> -`. Its
#: LENGTH is the measurement -- 2280 characters is what task 112's call lost to a 1-character
#: record -- so it is built by repetition rather than written out, and the row prints the
#: number it is standing in for.
_ACCOUNT = ("Established by X, measured 2026-08-23.\n\n"
            "- 114 tickets scanned, 0 degenerate\n"
            "- control: planted one, census read 1\n") * 20

#: The one-line evidence a `done` is supposed to carry, and the one-line evidence that CANNOT
#: be passed as argv: a backtick in an argv string is command substitution before `tasks.py`
#: runs (#80). The second is why `-` reads stdin here rather than being refused outright.
_INLINE = "measured: 114 rows, 0 degenerate; control planted one, census read 1"
_BACKTICK_LINE = "the census reads `established_by` over 114 tickets and returns 0"


def evidence_rows(tmp: Path, skip_prefix: bool) -> tuple[list[tuple], list[str]]:
    """Can `testing` and `done` still empty the record they exist to write?

    `status_rows` asks whether each transition writes the state it names. It passes a
    well-formed evidence string every time, so it cannot see what happens to a malformed one
    -- and the malformed one was accepted silently. Measured on this harness against
    `PRE_EVIDENCE_COMMIT`, all at exit 0 with the status flipped:

      | call                         | stored           |
      |------------------------------|------------------|
      | `done 70 - < 2280-char file` | `-`              |
      | `testing 70 - < same file`   | `-`              |
      | `done 70 ""`                 | the empty string |

    Every row therefore asserts TWO things about a refusal: exit 1, and the file byte-identical
    -- which includes the STATUS. The old code moved the ticket to `done` while destroying the
    record, so "it refused" and "it refused without closing the task" are different claims and
    only the second one is worth anything to the orchestrator.

    The three accepting rows are the variant half of rule 15. A mutant can delete a refusal;
    only an input the refusal must NOT fire on shows the repair is not just a deletion of the
    capability, and `_BACKTICK_LINE` is the input that would be lost if `-` were rejected
    outright instead of read.
    """
    rows, unchecked = [], []
    main, wt = _scratch_pair(tmp / "evidence")
    target = main / "tasks" / "70-a.md"
    # `pr:` is present because `in_testing` and `in_review` both require one, so the `check`
    # row below is measuring the evidence field and not a PR link this fixture forgot.
    original = _task_file("70", status="in_progress",
                          extra="pr: https://github.com/o/r/pull/9\n")

    def probe(src: Path, *argv: str, stdin: str | None = None) -> tuple[int, str, str]:
        shutil.copy(src, main / "eval/tools/tasks.py")
        shutil.copy(src, wt / "eval/tools/tasks.py")
        target.write_text(original, encoding="utf-8")
        p = subprocess.run([sys.executable, str(wt / "eval/tools/tasks.py"), *argv],
                           capture_output=True, text=True, input=stdin)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip(), target.read_text()

    def stored(text: str) -> str | None:
        """`established_by` as YAML sees it. Read through the parser, never off a line.

        Off a line it would be `^established_by: (.*)$`, which is the reader `tasks.py`
        already had to stop using: a value containing `": "` came back truncated and looked
        fine (task 40). A row about a durable record must not read it the lossy way.
        """
        m = T._FM_RE.match(text)
        if not m:
            return None
        v = (yaml.safe_load(m.group(1)) or {}).get("established_by")
        return None if v is None else str(v)

    # THE POSITIVE CONTROL FIRST. The pre-fix copy must lose the account on this very probe.
    if skip_prefix:
        unchecked.append("evidence positive control NOT CHECKED - --skip-prefix was given. "
                         "Nothing in the evidence rows shows this harness can observe a "
                         "2280-character account being stored as one character.")
    else:
        rc_g, blob = _run_tool_git("show", f"{PRE_EVIDENCE_COMMIT}:eval/tools/tasks.py")
        if rc_g != 0:
            unchecked.append(f"evidence positive control NOT CHECKED - could not read "
                             f"{PRE_EVIDENCE_COMMIT}:eval/tools/tasks.py ({blob[:90]}). The "
                             f"evidence rows below are unproven, not passing.")
        else:
            pre_py = tmp / "pre_evidence_tasks.py"
            pre_py.write_text(blob if blob.endswith("\n") else blob + "\n")
            rc, out, after = probe(pre_py, "done", "70", "-", stdin=_ACCOUNT)
            got = stored(after)
            rows.append((f"the 1-character record CAN be observed ({PRE_EVIDENCE_COMMIT} "
                         f"must store `-` at exit 0 over {len(_ACCOUNT)} characters)",
                         len(_ACCOUNT), rc == 0 and got == "-",
                         f"exit {rc}, established_by={got!r}; "
                         f"{out.splitlines()[-1][:60] if out else ''}"))

    # --- the refusals. Exit 1 AND the file untouched, status included.
    for name, argv, stdin in (
            (f"`done 70 -` on a {len(_ACCOUNT)}-character multi-line account",
             ("done", "70", "-"), _ACCOUNT),
            ("`testing 70 -` on the same account (the sibling, not just the reported one)",
             ("testing", "70", "-"), _ACCOUNT),
            ("`done 70 \"\"` (empty inline)", ("done", "70", ""), None),
            ("`done 70 \"   \"` (whitespace inline)", ("done", "70", "   "), None),
            ("`done 70 -` with a closed/empty stdin", ("done", "70", "-"), "")):
        rc, out, after = probe(TASKS_PY, *argv, stdin=stdin)
        rows.append((f"refused, and NOTHING written: {name}", rc,
                     rc == 1 and after == original,
                     f"exit {rc}, file unchanged: {after == original}; "
                     f"{out.splitlines()[-1][:80] if out else ''}"))

    # The message has to name where the account goes, or the refusal is just an obstacle.
    rc_m, out_m, _ = probe(TASKS_PY, "done", "70", "-", stdin=_ACCOUNT)
    rows.append(("the multi-line refusal names the alternative (`note <id> -`)", rc_m,
                 rc_m == 1 and "note 70 -" in out_m,
                 f"names it: {'note 70 -' in out_m}; {out_m.splitlines()[-1][:90]}"))

    # --- what it must still ACCEPT. Rule 15's variant half: a refusal that fires on these
    # would be a repair that removed the capability.
    for name, cmd, want_status, text in (
            ("a normal inline evidence string still stores unchanged", "done", "done",
             _INLINE),
            ("the same through `testing`", "testing", "in_testing", _INLINE)):
        rc, out, after = probe(TASKS_PY, cmd, "70", text)
        got = stored(after)
        rows.append((name, len(text), rc == 0 and got == text
                     and f"status: {want_status}" in after,
                     f"exit {rc}, len {0 if got is None else len(got)}, "
                     f"identical: {got == text}, status {want_status}: "
                     f"{f'status: {want_status}' in after}"))

    rc_s, _out_s, after_s = probe(TASKS_PY, "done", "70", "-", stdin=_INLINE + "\n")
    got_s = stored(after_s)
    rows.append(("`done 70 -` stores a ONE-LINE stdin string in full, trailing newline "
                 "stripped", len(_INLINE), rc_s == 0 and got_s == _INLINE,
                 f"exit {rc_s}, established_by={str(got_s)[:60]!r} (len "
                 f"{0 if got_s is None else len(got_s)})"))

    # THE ROW THAT SAYS WHY `-` IS READ RATHER THAN REJECTED. This string cannot reach
    # `tasks.py` through argv at all (#80); stdin is the only channel that carries it.
    rc_b, _out_b, after_b = probe(TASKS_PY, "done", "70", "-", stdin=_BACKTICK_LINE + "\n")
    got_b = stored(after_b)
    rows.append(("`done 70 -` carries a backtick that argv cannot (#80)", rc_b,
                 rc_b == 0 and got_b == _BACKTICK_LINE and "`" in (got_b or ""),
                 f"exit {rc_b}, backtick present: {'`' in (got_b or '')}, "
                 f"identical: {got_b == _BACKTICK_LINE}"))

    # ONE SENTINEL, ONE MEANING. The ticket's last requirement, asserted rather than promised:
    # the same `-` in `note` and in `done` both read stdin, on the same fixture.
    rc_n, _out_n, after_n = probe(TASKS_PY, "note", "70", "-", stdin=_ACCOUNT)
    rows.append(("`-` means stdin in `note` too, on the same fixture (the sibling agreement)",
                 rc_n, rc_n == 0 and after_n.startswith(original)
                 and _ACCOUNT.strip() in after_n,
                 f"exit {rc_n}, account in body: {_ACCOUNT.strip() in after_n}"))

    # WHITESPACE IS NOT CONTENT, AND `\r` IS NOT WHITESPACE FOR THIS PURPOSE. A heredoc always
    # ends in a newline and a redirected file often ends in a blank line, so trimming is what
    # makes `done <id> -` usable at all -- but `strip()` only ever removes whitespace, so
    # nothing a caller wrote can be lost to it. A LONE `\r` is the exception and the reason
    # for the second half of the test in `cmd_evidence`: it is an old-Mac line break, it
    # carries a second line, and `"\n" in text` cannot see it. Raised by review on PR #6; the
    # rest of that comment is declined in the thread, this half is a real hole.
    for name, stdin, want_rc in (
            ("a trailing blank line is trimmed, not refused", _INLINE + "\n\n", 0),
            ("a leading blank line is trimmed, not refused", "\n" + _INLINE, 0),
            ("a lone CR carries a second line and IS refused", "first\rsecond\n", 1)):
        rc_w, out_w, after_w = probe(TASKS_PY, "done", "70", "-", stdin=stdin)
        got_w = stored(after_w)
        ok = (rc_w == want_rc and (got_w == _INLINE if want_rc == 0
                                   else after_w == original))
        rows.append((f"stdin whitespace: {name}", rc_w, ok,
                     f"exit {rc_w}, established_by={str(got_w)[:50]!r}"
                     if want_rc == 0 else
                     f"exit {rc_w}, file unchanged: {after_w == original}; "
                     f"{out_w.splitlines()[-1][:70] if out_w else ''}"))

    # THE QUEUE A REFUSED `done` LEAVES BEHIND still lints, so a refusal is not a ticket
    # somebody has to repair by hand.
    #
    # THE ROW'S NAME IS AN ADDRESS AND IT WAS POINTING SOMEWHERE ELSE. Until PR #6's review
    # this ran straight after the `note` probe above, so it linted the ticket a SUCCESSFUL
    # note had left -- green, and about a fixture the name does not describe. That is
    # AGENTS.md rule 12 inside a control: a sound method aimed at an address nobody checked.
    # The refusal now happens here, on this fixture, with its own assertions kept.
    rc_r, out_r, after_r = probe(TASKS_PY, "done", "70", "-", stdin=_ACCOUNT)
    rows.append(("the refusal this `check` row is about: exit 1, ticket byte-identical", rc_r,
                 rc_r == 1 and after_r == original,
                 f"exit {rc_r}, file unchanged: {after_r == original}; "
                 f"{out_r.splitlines()[-1][:70] if out_r else ''}"))
    rc_c, out_c = _run_tool(main / "eval/tools/tasks.py", "check")
    rows.append(("`check` is clean on the ticket that refusal left behind", rc_c,
                 rc_c == 0 and "well-formed" in out_c,
                 f"exit {rc_c}: {out_c.splitlines()[-1][:80] if out_c else '(none)'}"))
    return rows, unchecked


#: A ref that is an ancestor, one that is not, and one belonging to another ticket. The
#: expected verdicts are stated HERE and never derived from `landed_status` -- a control that
#: builds its expectation by calling its subject has edited the check, not tested it
#: (AGENTS.md rule 12's companion, and the mutant that survived in task 113).
_ANCESTORS = {"refs/heads/task-70-merged", "refs/remotes/origin/task-1-merged",
              "refs/heads/task-70-also-merged"}

LANDED_CASES = (
    # (name, id, refs, want)
    ("a surviving branch that is NOT an ancestor is ORPHANED - THE task 70 defect",
     "70", ["refs/heads/task-70-ranking-ban-threshold"], "ORPHANED"),
    ("VARIANT: a branch that IS an ancestor still reads LANDED",
     "70", ["refs/heads/task-70-merged"], "LANDED"),
    ("VARIANT: one ancestor among several branches is enough - LANDED, not ORPHANED",
     "70", ["refs/heads/task-70-merged", "refs/heads/task-70-stray"], "LANDED"),
    ("a REMOTE-only branch is found, not missed",
     "1", ["refs/remotes/origin/task-1-merged"], "LANDED"),
    ("a remote-only branch that is not an ancestor is ORPHANED",
     "1", ["refs/remotes/origin/task-1-stray"], "ORPHANED"),
    ("no branch at all is NOT_CHECKED - the third value, never a pass",
     "70", ["refs/heads/task-99-x", "refs/heads/main"], "NOT_CHECKED"),
    ("git unavailable (refs=None) is NOT_CHECKED, not LANDED",
     "70", None, "NOT_CHECKED"),
    # THE PREFIX VARIANT. `task-7-` and `task-70-` share four characters, and a matcher that
    # forgot the trailing `-` would read one ticket's orphan as another ticket's evidence --
    # a wrong answer that looks like a right one, in both directions at once.
    ("VARIANT: id 7 does NOT claim task-70-*'s branch",
     "7", ["refs/heads/task-70-ranking-ban-threshold"], "NOT_CHECKED"),
    ("VARIANT: id 70 does NOT claim task-7-*'s branch",
     "70", ["refs/heads/task-7-something"], "NOT_CHECKED"),
    # The queue writes `id: 01`; the branch is named from the integer.
    ("a zero-padded id matches the integer-named branch",
     "01", ["refs/remotes/origin/task-1-merged"], "LANDED"),
    ("a non-numeric id is NOT_CHECKED rather than crashing the whole gate",
     "abc", ["refs/heads/task-70-merged"], "NOT_CHECKED"),
)

#: `is_ancestor` is THREE-VALUED and `None` means git could not answer. These pin the
#: third value, which no row above can reach because `_ANCESTORS` is a set and a set
#: membership test is total. Found in review of task 122: `merge-base --is-ancestor`
#: exits 128 when a ref vanishes between the listing and the query, and reading that as
#: "not an ancestor" makes `check` exit 1 naming a ticket whose ancestry it never
#: established.
LANDED_UNKNOWN_CASES = (
    ("git failing to answer is NOT_CHECKED, never ORPHANED",
     "70", ["refs/heads/task-70-vanished"], lambda r: None, "NOT_CHECKED"),
    ("VARIANT: one unanswerable ref does not suppress a real LANDED on another",
     "70", ["refs/heads/task-70-vanished", "refs/heads/task-70-merged"],
     lambda r: None if "vanished" in r else True, "LANDED"),
    ("VARIANT: a genuine False is still ORPHANED - the repair is not a blanket excuse",
     "70", ["refs/heads/task-70-stray"], lambda r: False, "ORPHANED"),
)

#: A REAL SQUASH MERGE IN THIS REPOSITORY, named by sha, so direction 11c says something about
#: git's behaviour here and not only about a fixture built to agree with it. PR #16 merged
#: 2026-08-24: `_REAL_SQUASH_TIP` is the branch tip and is an ancestor of NOTHING, while
#: `_REAL_SQUASH_COMMIT` carries the same change and is an ancestor of `main`.
#:
#: THE TWO DIFFER IN WHO CAN SEE THEM, and the rows are split along that line.
#: `_REAL_SQUASH_COMMIT` is on `main`, so every clone with history has it and its row runs
#: unconditionally. `_REAL_SQUASH_TIP` is the deleted branch's tip, reachable from nothing:
#: only the checkout that performed the merge still holds it, so its rows are behind
#: `--live-squash-refs` and report NOT CHECKED when asked for where the object is absent.
_REAL_SQUASH_TIP = "58df942db5fae6a6537c26b40096c2894b1f3c90"
_REAL_SQUASH_COMMIT = "399280e7f059aaf694fa517c331f83f875a5cfb8"


# --------------------------------------------------------------------------- direction 11
def landed_rows(tmp: Path, live_refs: bool = False) -> tuple[list[tuple], list[str]]:
    """11: can `check` see a `done` ticket whose branch never reached `main`?

    11a pins the PREDICATE in process, with a stated `_ANCESTORS` set standing in for git, so
    every row is deterministic and the id-boundary variants can be asked at all. 11b runs
    `check` end to end in a real scratch repository, because 4c measured what happens when a
    predicate is correct and nothing reports it: `if False:` left 34 green rows and a gate
    that printed nothing (`tasks/106`). 11b's merge is `--no-ff`, which is the flow this
    repository has abandoned; `_squash_rows` is 11c and covers the one it uses.

    WHAT 11b DOES NOT DO is assert the live queue's numbers. The population moves whenever a
    branch is deleted, so the figure that mattered -- 119 `done`, 6 LANDED, 1 ORPHANED, 112
    NOT_CHECKED, **0 false positives**, measured 2026-08-23 before this shipped -- is in
    `tasks.py`'s own comment beside the loop and is re-derived by running `check`, not pinned
    here where it would go stale and be repaired by widening.
    """
    rows = []
    for name, tid, refs, want in LANDED_CASES:
        got, cand = T.landed_status(tid, refs, lambda r: r in _ANCESTORS)
        rows.append((f"landed_status: {name}", 0, got == want,
                     f"want {want}, got {got} on {cand or '(no ref)'}"))
    for name, tid, refs, anc, want in LANDED_UNKNOWN_CASES:
        got, cand = T.landed_status(tid, refs, anc)
        rows.append((f"landed_status: {name}", 0, got == want,
                     f"want {want}, got {got} on {cand or '(no ref)'}"))

    # THE PRODUCER OF THE THIRD VALUE, not only its consumer. The rows above hand
    # `landed_status` a lambda returning None, so they never run `_is_ancestor` and a
    # mutant collapsing its error branch SURVIVED them -- measured, not supposed. These
    # call it against the real repository, where `merge-base --is-ancestor` on a
    # nonexistent ref exits 128 (verified: 0 self, 1 not-an-ancestor, 128 missing).
    real = _scratch_pair(tmp / "isanc")[0]
    subprocess.run(["git", "-C", str(real), "branch", "-q", "orphan-tip", "HEAD"],
                   check=True, capture_output=True)
    base = [("main", subprocess.run(["git", "-C", str(real), "rev-parse", "main"],
                                    check=True, capture_output=True,
                                    text=True).stdout.strip())]
    saved_tasks = T.TASKS
    try:
        T.TASKS = real / "tasks"
        got_missing = T._is_ancestor("refs/heads/no-such-branch-here", base)
        got_true = T._is_ancestor("refs/heads/orphan-tip", base)
    finally:
        T.TASKS = saved_tasks
    rows.append(("_is_ancestor returns None (not False) when git cannot answer", 0,
                 got_missing is None, f"got {got_missing!r} for a nonexistent ref"))
    rows.append(("VARIANT: _is_ancestor still returns True for a real ancestor", 0,
                 got_true is True, f"got {got_true!r}"))

    # THE CALLER'S HEAD IS ASKED AT THE PROCESS'S ADDRESS, NOT ONLY THE FILE'S. `ROOT`
    # comes from `__file__`, and the work skill tells an agent to run the MAIN copy of
    # the tool by absolute path -- under which `ROOT` is the main checkout and the
    # agent's own branch is never consulted, so the orphan it just fixed stays red and
    # the documented repair path is dead. Both addresses are asked now, and this row is
    # a real worktree whose HEAD is NOT reachable from the main checkout's.
    main2, wt2 = _scratch_pair(tmp / "callerhead")
    shutil.copy(TASKS_PY, main2 / "eval/tools/tasks.py")
    g2 = ["git", "-C", str(wt2)]
    (wt2 / "only-on-the-worktree.txt").write_text("x\n")
    subprocess.run([*g2, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*g2, "commit", "-qm", "work only the worktree has"],
                   check=True, capture_output=True)
    wt_head = subprocess.run([*g2, "rev-parse", "HEAD"], check=True,
                             capture_output=True, text=True).stdout.strip()
    # Run the MAIN checkout's copy, with the WORKTREE as the working directory -- the
    # exact shape the skill recommends.
    p = subprocess.run([sys.executable, str(main2 / "eval/tools/tasks.py"), "check"],
                       cwd=str(wt2), capture_output=True, text=True)
    seen = ((p.stdout or "") + (p.stderr or ""))
    rows.append(("the caller's cwd HEAD is a base, not just the file's checkout",
                 0, wt_head[:9] in seen,
                 f"worktree HEAD {wt_head[:9]} named: {wt_head[:9] in seen}; "
                 f"{next((ln for ln in seen.splitlines() if 'done` tickets' in ln), seen[:90])}"))

    # 11b. A real repository: `merged` is on main, `orphan` is not, and the queue names both
    # as `done`. Two tickets in one queue, so the same run shows the gate firing on one and
    # staying quiet on the other -- a fixture with only the failing case cannot tell a
    # working gate from one that fails everything.
    main, _ = _scratch_pair(tmp / "landed")
    shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
    git = ["git", "-C", str(main)]

    def g(*a, **kw):
        return subprocess.run([*git, *a], check=True, capture_output=True, text=True, **kw)

    g("checkout", "-q", "-b", "task-70-merged")
    (main / "merged.txt").write_text("landed\n")
    g("add", "-A"); g("commit", "-qm", "work that landed")
    g("checkout", "-q", "main")
    g("merge", "-q", "--no-ff", "-m", "merge 70", "task-70-merged")
    g("checkout", "-q", "-b", "task-71-orphan")
    (main / "orphan.txt").write_text("never landed\n")
    g("add", "-A"); g("commit", "-qm", "work that did not land")
    g("checkout", "-q", "main")

    (main / "tasks" / "70-a.md").write_text(_task_file("70", status="done"))
    (main / "tasks" / "71-a.md").write_text(_task_file("71", status="done"))
    rc, out = _run_tool(main / "eval/tools/tasks.py", "check")
    rows.append(("`check` end to end: exit 1, naming 71 and NOT 70", rc,
                 rc == 1 and "71: status done" in out and "70: status done" not in out,
                 f"exit {rc}: {[ln for ln in out.splitlines() if 'status done' in ln]}"))
    census = next((ln for ln in out.splitlines() if "done` tickets" in ln), "(absent)")
    rows.append(("...and it PRINTS the three-valued census, LANDED count included", rc,
                 "1 reachable from" in out and "NOT CHECKED" in out, census))
    # The bases are DE-DUPLICATED BY SHA. Here the queue's `main` and the caller's HEAD are the
    # same commit, so exactly one may be named: a census line claiming two bases where there is
    # one reads as corroboration and is a restatement (AGENTS.md rule 9, and rule 12 on the
    # address). This row is the reason the dedup compares SHAs and not the names.
    rows.append(("bases coinciding are named ONCE, not as two agreeing opinions", rc,
                 "reachable from main," in census,
                 census))

    # THE VARIANT: delete the orphan branch and the same queue must go quiet -- NOT_CHECKED,
    # reported, exit 0. A gate that failed on every closed ticket whose branch is gone would
    # fire on 112 of this repository's 119 and be turned off within the day.
    g("branch", "-qD", "task-71-orphan")
    rc2, out2 = _run_tool(main / "eval/tools/tasks.py", "check")
    rows.append(("VARIANT: with the branch deleted the same queue is NOT CHECKED, exit 0",
                 rc2, rc2 == 0 and "1 NOT CHECKED" in out2,
                 f"exit {rc2}: "
                 f"{next((ln for ln in out2.splitlines() if 'done` tickets' in ln), out2[:80])}"))

    rows_c, unchecked_c = _squash_rows(tmp, live_refs)
    return rows + rows_c, unchecked_c


# --------------------------------------------------------------------------- direction 11c
def _squash_rows(tmp: Path, live_refs: bool = False) -> tuple[list[tuple], list[str]]:
    """11c: the SQUASH flow, which is the one this repository merges by.

    `gh pr merge --squash` writes a commit with ONE parent and a tree of its own, so the tip
    it landed is NOT an ancestor of it -- `git branch -d` refuses such a branch and is right
    to. Ancestry alone therefore read every merged ticket as ORPHANED
    (task 140), which is fail-closed and still fatal: the count grows by one per merge, and a
    gate red for reasons unrelated to the change in front of you is a gate that gets bypassed.

    FOUR REFS, BECAUSE THE DEFECT HAS TWO FACES AND EACH NEEDS BOTH DIRECTIONS. A
    remote-tracking ref disappears on the next `fetch --prune`, so that face heals itself and
    an investigator arriving after a prune finds nothing; a LOCAL branch survives until
    somebody deletes it by hand, so that face never heals. A fixture carrying only one of them
    proves less than it looks.

    The scratch half performs a real `merge --squash` and runs anywhere. One live row runs
    anywhere too -- a real squash commit on this repository's `main` has ONE parent, which is
    the property that breaks ancestry, and it is on `main` so any clone with the history has
    it -- a shallow one reports NOT CHECKED. The
    deleted branch tip is behind `--live-squash-refs`; see the comment at that block.
    """
    rows: list[tuple] = []
    unchecked: list[str] = []

    sq, _ = _scratch_pair(tmp / "squash")
    shutil.copy(TASKS_PY, sq / "eval/tools/tasks.py")

    def g(*a):
        return subprocess.run(["git", "-C", str(sq), *a], check=True,
                              capture_output=True, text=True)

    def squashed(tid: str, name: str, keep_local: bool) -> str:
        """Branch, commit, `merge --squash` onto main, and leave ONE of the two faces."""
        g("checkout", "-q", "-b", f"task-{tid}-{name}")
        (sq / f"{name}.txt").write_text(f"work for {tid}\n")
        g("add", "-A"); g("commit", "-qm", f"work {tid}")
        tip = g("rev-parse", "HEAD").stdout.strip()
        g("checkout", "-q", "main")
        g("merge", "-q", "--squash", f"task-{tid}-{name}")
        g("commit", "-qm", f"Task {tid}: {name} (#{tid})")
        if not keep_local:
            g("branch", "-qD", f"task-{tid}-{name}")
            g("update-ref", f"refs/remotes/origin/task-{tid}-{name}", tip)
        return tip

    def unmerged(tid: str, name: str, keep_local: bool) -> str:
        g("checkout", "-q", "-b", f"task-{tid}-{name}")
        (sq / f"{name}.txt").write_text(f"work for {tid} that never landed\n")
        g("add", "-A"); g("commit", "-qm", f"work {tid}")
        tip = g("rev-parse", "HEAD").stdout.strip()
        g("checkout", "-q", "main")
        if not keep_local:
            g("branch", "-qD", f"task-{tid}-{name}")
            g("update-ref", f"refs/remotes/origin/task-{tid}-{name}", tip)
        return tip

    squashed("70", "squashed-local", keep_local=True)
    squashed("72", "squashed-remote", keep_local=False)
    unmerged("71", "orphan-local", keep_local=True)
    unmerged("73", "orphan-remote", keep_local=False)
    # TWO SIBLINGS OFF ONE COMMIT. `unmerged` branches from wherever `main` is, so 71 and 73
    # have DIFFERENT merge-bases and cannot exercise the cache at all. These two share one,
    # which is the only shape a `(base_sha, rev)` cache can collapse.
    sib_base = g("rev-parse", "main").stdout.strip()
    for suffix in ("a", "b"):
        g("checkout", "-q", "-b", f"sibling-{suffix}", sib_base)
        (sq / f"sib{suffix}.txt").write_text(f"sibling {suffix}\n")
        g("add", "-A"); g("commit", "-qm", f"sibling {suffix}")
        g("checkout", "-q", "main")
    for tid in ("70", "71", "72", "73"):
        (sq / "tasks" / f"{tid}-a.md").write_text(_task_file(tid, status="done"))

    rc, out = _run_tool(sq / "eval/tools/tasks.py", "check")
    named = sorted(ln.split(":")[0].strip() for ln in out.splitlines()
                   if "status done" in ln)
    rows.append(("SQUASH end to end: exit 1, naming ONLY the two that never landed", rc,
                 rc == 1 and named == ["71", "73"], f"exit {rc}, named {named}"))
    census = next((ln for ln in out.splitlines() if "done` tickets" in ln), "(absent)")
    rows.append(("...and both squash-merged faces count as LANDED, local and remote", rc,
                 "2 reachable from" in census, census))

    # THE PREDICATE, at the live repository's own address rather than through `check`. The
    # rows above cannot reach the third value: a set of four refs that all resolve has no
    # way to make git fail, and a consumer pinned without its producer is the `tasks/106`
    # shape that let an error-branch mutant survive direction 11 the first time.
    base = [("main", g("rev-parse", "main").stdout.strip())]
    saved = T.TASKS
    try:
        T.TASKS = sq / "tasks"
        got_sq = T._squash_landed("refs/heads/task-70-squashed-local", base)
        got_orphan = T._squash_landed("refs/heads/task-71-orphan-local", base)
        got_missing = T._squash_landed("refs/heads/no-such-branch-here", base)
        landed_orphan = T._is_landed("refs/heads/task-71-orphan-local", base)
        landed_missing = T._is_landed("refs/heads/no-such-branch-here", base)
    finally:
        T.TASKS = saved
    rows.append(("_squash_landed is True for a squash-merged tip", 0, got_sq is True,
                 f"got {got_sq!r}"))
    rows.append(("VARIANT: _squash_landed is False for work that never landed", 0,
                 got_orphan is False, f"got {got_orphan!r}"))
    rows.append(("_squash_landed returns None (not False) when git cannot answer", 0,
                 got_missing is None, f"got {got_missing!r} for a nonexistent ref"))
    rows.append(("_is_landed passes the None through - unreadable is NOT_CHECKED", 0,
                 landed_missing is None, f"got {landed_missing!r}"))
    rows.append(("VARIANT: _is_landed still returns False on a genuine orphan", 0,
                 landed_orphan is False, f"got {landed_orphan!r}"))

    # THE CACHE, which is per-invocation and keyed on `(base_sha, rev)`. Rendering a base
    # range as patches is the expensive half -- 288ms of `check` without the squash arm
    # against 1070ms with it, on 12 orphaned refs over a 60-commit range -- and every ref
    # forked from the same commit asks for the identical answer. Three rows: it collapses
    # what it should, it does NOT collapse what it should not, and it never stores a failure.
    saved = T.TASKS
    try:
        T.TASKS = sq / "tasks"
        shared: dict = {}
        v_a = T._squash_landed("refs/heads/sibling-a", base, shared)
        n_after_one = len(shared)
        v_b = T._squash_landed("refs/heads/sibling-b", base, shared)
        n_shared = len(shared)
        failed: dict = {}
        bad = T._base_patch_ids("no-such-object-here", base[0][1], failed)
    finally:
        T.TASKS = saved
    # THE HALF OF THE KEY THAT IS EASY TO DROP. Advancing `main` leaves the siblings' FORK
    # POINT unchanged and changes what they are being compared against, so `base_sha` alone
    # would answer the new question out of the old entry. A second base with a different
    # merge-base does not test this -- both halves of the key move together there, which is
    # how the first version of this row stayed green under the mutant that drops `rev`.
    (sq / "after.txt").write_text("main moved on\n")
    g("add", "-A"); g("commit", "-qm", "main advances past the siblings")
    newer = g("rev-parse", "main").stdout.strip()
    saved = T.TASKS
    try:
        T.TASKS = sq / "tasks"
        T._squash_landed("refs/heads/sibling-a", [("newer", newer)], shared)
        n_two_ranges = len(shared)
    finally:
        T.TASKS = saved
    rows.append(("the patch-id cache collapses two refs sharing one base range into 1 "
                 "entry, verdicts unchanged", 0,
                 n_after_one == 1 and n_shared == 1 and v_a is False and v_b is False,
                 f"{n_after_one} entr(y/ies) after one ref, {n_shared} after two; "
                 f"verdicts {v_a!r}/{v_b!r}"))
    rows.append(("VARIANT: the same fork point against a MOVED main is a SECOND entry - "
                 "the key is the pair, not the base", 0, n_two_ranges == 2,
                 f"{n_two_ranges} entr(y/ies)"))
    rows.append(("a git failure is NOT cached - one transient error must not become every "
                 "later ref's verdict", 0, bad is None and not failed,
                 f"got {bad!r}, cache holds {len(failed)}"))

    def here(rev: str) -> bool:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q",
                               f"{rev}^{{commit}}"], capture_output=True,
                              check=False).returncode == 0

    # THE LIVE ROW THAT RUNS EVERYWHERE, and it is the one whose answer is known in advance.
    # `_REAL_SQUASH_COMMIT` is a real `gh pr merge --squash` on this repository's `main`, so
    # any clone with the history has it -- and it has exactly ONE parent, which is the whole
    # reason the tip it landed is not an ancestor of it. If this repository ever
    # went back to `git merge --no-ff` this row would not notice, but the fixture above does
    # not depend on it: the fixture squashes for real.
    parents = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--parents", "-n", "1",
                              _REAL_SQUASH_COMMIT], capture_output=True, text=True,
                             check=False)
    if parents.returncode != 0:
        # A SHALLOW CLONE IS NOT A FAILING ROW. `gates.yml` sets `fetch-depth: 0` precisely
        # because depth 1 leaves several controls with no history to read, and reading that
        # as red would make the gate wrong about the change in front of it.
        unchecked.append(f"the one-parent row is NOT CHECKED - this clone has no "
                         f"{_REAL_SQUASH_COMMIT[:9]}. No history to read is not a pass")
    else:
        n_parents = len(parents.stdout.split()) - 1
        rows.append(("a real squash merge on this repository's main has ONE parent - why a "
                     "landed tip is not an ancestor of it", 0, n_parents == 1,
                     f"{_REAL_SQUASH_COMMIT[:9]}: {n_parents} parent(s), tip "
                     f"{_REAL_SQUASH_TIP[:9]} in this clone: {here(_REAL_SQUASH_TIP)}"))

    # THE DELETED TIP, WHICH ONLY THE MACHINE THAT MERGED IT STILL HAS. `delete_branch_on_merge`
    # removes the branch, so `58df942` is reachable from nothing and no clone that did not
    # perform the merge can fetch it -- CI included. Making these rows unconditional would
    # report NOT CHECKED (exit 3) on every machine but one, turning a correct CI run red for a
    # reason unrelated to the change in front of it, which is this ticket's own defect one
    # level up. So the flag is opt-in, the row above states whether the object is here, and
    # asking for it when it is absent is NOT CHECKED rather than a quiet pass.
    if not live_refs:
        return rows, unchecked
    main_sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "main"],
                              capture_output=True, text=True, check=False)
    if not (here(_REAL_SQUASH_TIP) and here(_REAL_SQUASH_COMMIT)
            and main_sha.returncode == 0):
        unchecked.append("--live-squash-refs asked for PR #16's pair and this clone does "
                         "not have it: the merged branch was deleted upstream, so only the "
                         "checkout that performed the merge still holds the tip")
        return rows, unchecked
    real_base = [("main", main_sha.stdout.strip())]
    saved = T.TASKS
    try:
        T.TASKS = ROOT / "tasks"
        known = T._is_ancestor(_REAL_SQUASH_COMMIT, real_base)
        anc = T._is_ancestor(_REAL_SQUASH_TIP, real_base)
        content = T._squash_landed(_REAL_SQUASH_TIP, real_base)
        verdict = T._is_landed(_REAL_SQUASH_TIP, real_base)
    finally:
        T.TASKS = saved
    rows.append(("live: PR #16's SQUASH COMMIT is an ancestor of main", 0, known is True,
                 f"{_REAL_SQUASH_COMMIT[:9]}: got {known!r}"))
    rows.append(("live: PR #16's BRANCH TIP is an ancestor of no commit on main - the "
                 "defect", 0,
                 anc is False, f"{_REAL_SQUASH_TIP[:9]}: got {anc!r}"))
    rows.append(("live: ...while its CHANGE is on main - the same real ref, both directions",
                 0, content is True, f"{_REAL_SQUASH_TIP[:9]}: got {content!r}"))
    rows.append(("live: ...so `check` reads PR #16's ticket LANDED, not ORPHANED", 0,
                 verdict is True, f"{_REAL_SQUASH_TIP[:9]}: got {verdict!r}"))
    return rows, unchecked


# --------------------------------------------------------------------------- direction 12
#: THE LINE VERSUS THE PARSE. `tasks/214`'s title was written as an UNQUOTED YAML scalar
#: containing " #" - which starts a comment - so every command in `tasks.py` displayed a
#: truncated title from the day the ticket was filed while the file always held the full
#: text, and `check` read the queue well-formed throughout (tasks/216). The census that
#: bounded it, 2026-08-29 over all 214 ticket files then in the queue: ONE lossy scalar
#: (that title), and four tickets whose unquoted scalars carry a hash following a
#: NON-whitespace character and parse whole - the green controls a fix must not redden.
#:
#: THE TRIGGER IS THE PROPERTY, NOT THE CHARACTER. "The line's content begins with the
#: value the parse kept and carries more" is the shape of comment truncation and of
#: nothing else in this corpus; a check keyed on `" #"` would redden the REPAIRED 214
#: title, which is single-quoted precisely so its ` #25` survives the read. That
#: vocabulary check is the `lossy_by_vocabulary` mutant in `tasks_mutants.py`, and the
#: green rows below are what kill it.
LOSSY_DEFECT_COMMIT = "1703566"     # files tasks/214: title unquoted, " #" mid-value
LOSSY_REPAIR_COMMIT = "cd4994d"     # same title single-quoted: full text, parses whole
_T214 = "tasks/214-drive-appends-audio-triggered-after-a-lock-confli.md"

#: The census tickets, pinned at the last commit that touched each - immutable addresses
#: like direction 5's blobs, because a live file can be rewritten by a peer and a pin
#: that moves is not a pin. 181 carries two of the four fields, which is why it is one
#: row and not two.
LOSSY_GREEN_COMMITS = (
    ("174", "43a4792", "tasks/174-the-shift-estimator-answers-for-the-whole-frame-.md",
     "refs ,#189"),
    ("181", "c9586b5", "tasks/181-agents-md-and-decisions-md-cite-findings-as-bare.md",
     "title (#NN) and done_when [#NN]"),
    ("187", "42296a7", "tasks/187-a-rate-limited-coderabbit-reports-pass-and-the-j.md",
     "refs ,#188"),
)

#: The ticket's own example of the shape that would bite hardest: a done_when losing its
#: CONDITION at exactly the citation. Synthetic because the census found the one lossy
#: scalar in a title - no real blob carries a lossy done_when - and the field generality
#: is part of what is being pinned.
LOSSY_DONE_WHEN_FIXTURE = ("tasks.py check exits 1 on this queue and docstat --findings "
                           "names #214 in its index - the condition ends at the citation")


# --------------------------------------------------------------------------- direction 13
#: THE TICKET THAT REDDENED EVERY OPEN PULL REQUEST (tasks/217). Hand-authored at cd4994d
#: with a single-quoted title AND done_when, it was byte-legal YAML that the writer could
#: not reproduce: `_render` re-emitted the title unquoted, so the byte round trip went red
#: on every merge ref carrying the file -- through a queue file none of those pull requests
#: touched. Pinned at its commit like every blob in this file: the live ticket was
#: canonicalised by the very status write that closed tasks/216, so the defect shape exists
#: at the commit and nowhere in the queue now. THAT IS WHY THIS DIRECTION EXISTS -- the
#: property is durable, and a queue that happens to be canonical proves nothing about the
#: next hand repair that quotes a scalar.
HAND_QUOTED_COMMIT = "cd4994d"
HAND_QUOTED_216 = "tasks/216-tasks-py-check-passes-a-frontmatter-scalar-whos.md"


def _fm_line(blob: str, field: str) -> str:
    """One frontmatter line, whole, `field:` included - or a hard failure.

    The fixtures below pin BY FIELD so a reflow of the surrounding blob cannot detach
    the pin from the line it is about.
    """
    m = re.search(rf"^{field}: .*$", blob, re.M)
    if m is None:
        raise SystemExit(f"fixture blob has no `{field}:` line - the pin and its "
                         f"subject have come apart")
    return m.group(0)


def _scratch_task(text: str, where: Path) -> tuple[Path, dict]:
    """A task file on disk and the meta `_parse` builds from it - the production reader.

    The predicate is pinned against what `_parse` actually hands `check`, never against a
    hand-built dict: a second construction of the parsed values is a second address for
    the one fact (AGENTS.md rule 12).
    """
    where.mkdir(parents=True, exist_ok=True)
    p = where / "70-a.md"
    p.write_text(text)
    return p, T._parse(p)


def lossy_check_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    """`check` END TO END on scratch queues holding the real lines.

    Exit 1 naming the field on the pre-repair 214 title and on a done_when truncated at
    its citation; exit 0 over the five census lines TOGETHER, because a green row of one
    shape each proves nothing about a queue that carries all of them - and because this
    is the row the vocabulary mutant must redden, via the repaired 214 title it holds.
    """
    rows: list[tuple] = []
    unchecked: list[str] = []
    defect = _blob(LOSSY_DEFECT_COMMIT, _T214)
    repaired = _blob(LOSSY_REPAIR_COMMIT, _T214)
    if defect is None or repaired is None:
        return rows, [f"direction 12's end-to-end rows NOT CHECKED - no blob at "
                      f"{LOSSY_DEFECT_COMMIT} or {LOSSY_REPAIR_COMMIT}: no history to "
                      f"read is not a pass"]

    def run(name: str, files: dict[str, str], want_rc: int, phrase: str) -> None:
        main, _ = _scratch_pair(tmp / re.sub(r"\W+", "-", name)[:40])
        shutil.copy(TASKS_PY, main / "eval/tools/tasks.py")
        for fn, text in files.items():
            (main / "tasks" / fn).write_text(text)
        rc, out = _run_tool(main / "eval/tools/tasks.py", "check")
        rows.append((name, rc, rc == want_rc and phrase in out,
                     f"want exit {want_rc} naming {phrase!r}; got exit {rc}: "
                     f"{out.splitlines()[-1][:110] if out else '(no output)'}"))

    run("`check` on a queue holding the real pre-repair 214 title (blob, not retyped)",
        {"214-a.md": defect}, 1, "`title` parses shorter")
    run("`check` on an unquoted done_when truncated at its ` #` citation",
        {"70-a.md": _task_file("70", done_when=LOSSY_DONE_WHEN_FIXTURE)},
        1, "`done_when` parses shorter")

    green = {"214-b.md": repaired}
    for tid, commit, path, _what in LOSSY_GREEN_COMMITS:
        blob = _blob(commit, path)
        if blob is None:
            unchecked.append(f"the {tid} green row NOT CHECKED - no blob at {commit}")
            continue
        green[f"{tid}-c.md"] = blob
    run("`check` on the four hash-following-non-whitespace lines and the repaired 214 "
        "title (the greens, together)", green, 0, "well-formed")

    # THE TORN-WRITE RACE, WITH THE FAULT INJECTED AT ITS LINE (review round 2, task 216).
    # A peer can rewrite a shared ticket between `_load`'s parse and `check`'s re-read, and
    # the re-read's frontmatter then fails `yaml.safe_load` INSIDE `lossy_scalar_fields` --
    # a path the malformed-file report cannot reach, because the file parsed when the queue
    # was loaded. Timing cannot be staged deterministically, so the raise is injected at
    # the exact line in a scratch copy of the subject. The requirement is the REPORTING:
    # exit 1 with the ticket NAMED and no traceback. A traceback also exits 1 -- it would be
    # read as "the check failed the queue" when it is the check itself that died -- and a
    # swallowed error would read as clean. Neither is a result.
    torn_main, _ = _scratch_pair(tmp / "lossy-torn-write")
    torn_subject = torn_main / "eval/tools/tasks.py"
    base = TASKS_PY.read_text(encoding="utf-8")
    needle = "    raw_map = yaml.safe_load(m.group(1))"
    n_needle = base.count(needle)
    if n_needle != 1:
        rows.append(("torn-write fault injection applied to the subject copy",
                     0, False,
                     f"expected exactly 1 occurrence of the raw-map read, found "
                     f"{n_needle} - the injection would not land where it names"))
    else:
        torn_subject.write_text(base.replace(
            needle, '    raise yaml.YAMLError("torn mid-write")\n' + needle))
        (torn_main / "tasks" / "70-a.md").write_text(
            _task_file("70", done_when="something observable"))
        rc, out = _run_tool(torn_subject, "check")
        rows.append(("`check` on a frontmatter that fails its second parse (injected "
                     "raise) exits 1 NAMING the ticket, not a traceback",
                     rc, rc == 1 and "frontmatter did not parse" in out
                     and "70" in out and "Traceback" not in out,
                     f"got exit {rc}; "
                     f"{'clean named report' if 'Traceback' not in out else 'TRACEBACK'}"))
    return rows, unchecked


def lossy_predicate_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    """The PREDICATE, in process, on the real lines and on the shapes around them.

    The e2e rows above ask whether `check` REPORTS what the predicate finds; these pin
    the predicate itself, the way directions 4a/4b pin `reachability_warning` - and the
    4c lesson is why both halves exist (tasks/106: computing everything, printing
    nothing, every row green).
    """
    pred = getattr(T, "lossy_scalar_fields", None)
    if pred is None:
        return [("the lossy-scalar predicate exists (`tasks.lossy_scalar_fields`)",
                 0, False,
                 "tasks.py has no lossy_scalar_fields - the mechanism this direction "
                 "pins does not exist in the subject")], []
    rows: list[tuple] = []
    unchecked: list[str] = []
    scratch = tmp / "lossy-pred"

    # THE DEFECT, read through the production reader: the parse is the truncated string
    # the queue displayed, the LINE still carries the full text, and the predicate fires
    # naming `title`. Three rows, because "fires" alone would also be true of a predicate
    # that fired on the wrong value or for the wrong reason.
    defect = _blob(LOSSY_DEFECT_COMMIT, _T214)
    if defect is None:
        unchecked.append(f"the defect predicate rows NOT CHECKED - no blob at "
                         f"{LOSSY_DEFECT_COMMIT}")
    else:
        p, meta = _scratch_task(defect, scratch / "defect")
        text = p.read_text(encoding="utf-8")
        fired = pred(text, meta)
        rows.append(("predicate FIRES on the real pre-repair 214 title, naming `title`",
                     0, "title" in fired, f"fired on {fired}"))
        rows.append(("...the parse really is the truncated string the queue displayed",
                     0, str(meta.get("title", "")).endswith("so the"),
                     f"title parses to ...{str(meta.get('title', ''))[-50:]}"))
        raw = _fm_line(text, "title")
        rows.append(("...while the LINE still carries the full text the file always held",
                     0, raw.endswith("unusable_criteria"), f"line ends: ...{raw[-50:]}"))

    # THE GREENS: the four census lines and the repaired title, each quiet, each with its
    # precondition ASSERTED - that the line pinned is still hash-bearing, so a moved blob
    # fails loudly here instead of passing vacuously.
    repaired = _blob(LOSSY_REPAIR_COMMIT, _T214)
    greens: list[tuple[str, str | None, str]] = [
        (f"tasks/{tid} at {commit}", _blob(commit, path), what)
        for tid, commit, path, what in LOSSY_GREEN_COMMITS
    ]
    greens.append(("tasks/214 repaired (single-quoted, full text)", repaired,
                   "title quoted, ` #25` inside the quotes"))
    for name, blob, what in greens:
        if blob is None:
            unchecked.append(f"predicate row NOT CHECKED - no blob for {name}")
            continue
        p, meta = _scratch_task(blob, scratch / re.sub(r"\W+", "-", name)[:30])
        text = p.read_text(encoding="utf-8")
        fired = pred(text, meta)
        hash_lines = [ln.split(":")[0] for ln in text.splitlines()
                      if re.match(r"^(title|done_when|refs): .*#", ln)]
        rows.append((f"predicate stays QUIET on {name}: {what}",
                     0, fired == [] and len(hash_lines) >= 1,
                     f"fired on {fired}; hash-bearing field line(s): {hash_lines}"))

    # THE SHAPES AROUND THE PROPERTY, each with the reason it must read the way it does.
    # Wordings rather than a parametrisation, on the reachability_rows pattern: each row
    # states the case it covers, and a mutant has to say which wording it no longer
    # respects.
    def fm(title: str, status: str = "todo", priority: str = "3",
           refs: str = "''", done_when: str = "something observable",
           body: str = "\nbody\n") -> str:
        return (f"---\nid: 70\ntitle: {title}\nstatus: {status}\npriority: {priority}\n"
                f"refs: {refs}\ndone_when: {done_when}\n---\n{body}")

    cases = [
        # An intentional-looking comment after an EMPTY value. Quiet BY DECISION: the
        # parse is "" and the remedy sentence has no surviving value to point at, while
        # the fields where emptiness is a defect are already gated by their own
        # `no title` / `no done_when` failures. Pinned so it is a decision and not an
        # accident.
        ("quiet on `refs: # see task 189` (empty parse; comment idiom, not loss)",
         fm("a title", refs="# see task 189"), []),
        # Escaped quotes make the parsed value differ from the naive unquoting WITHOUT any
        # loss. The prefix test - not inequality - is what keeps this quiet.
        ("quiet on an escaped apostrophe the naive unquote does not reproduce",
         fm("'the band''s own rows'"), []),
        # The repair as a shape: quoted, and the ` #` the quotes protect survives the read.
        # A vocabulary trigger (`" #" in line`) reddens this row - which is the point.
        ("quiet on a quoted value whose ` #` the quotes protect",
         fm("'the gate''s own #25 note'"), []),
        # A YAML COLLECTION with a trailing comment: the parse keeps the whole value and
        # loses nothing, so the predicate must stay quiet. Found in review on task 216:
        # `_parse` stringifies collections through `_scalar`, so the string "['one']" is a
        # strict prefix of the carrier "['one'] # note" and the first version FIRED here -
        # a red on a value that lost nothing. The skip reads raw yaml types, not the meta.
        ("quiet on a bracketed refs list with an inline comment (a collection has no "
         "scalar to lose)",
         fm("a title", refs="['one'] # note"), []),
        # The legacy vocabulary is remapped on read: `open` parses to `todo`. Not a
        # prefix, so quiet - a red here would fail every stale worktree's check, which is
        # the exact thing LEGACY_STATUSES exists to prevent.
        ("quiet on a legacy status remapped on read (`open` parses to `todo`)",
         fm("a title", status="open"), []),
        # EVERY scalar field, not an enumeration of the two the ticket names: a trailing
        # comment is dropped off any unquoted value and the disagreement is real wherever
        # it happens.
        ("FIRES on `priority: 3 # high` - the property covers every scalar field",
         fm("a title", priority="3 # high"), ["priority"]),
        # The check reads the FRONTMATTER BLOCK. A body quoting the shape is prose, and a
        # match there would fire on every ticket that documents this defect - this one
        # included.
        ("quiet when the shape appears in the BODY, which no frontmatter reader parses",
         fm("a title", body="\ntitle: some # prose quoted in the body\n"), []),
    ]
    for name, text, want in cases:
        _, meta = _scratch_task(text, scratch / "cases")
        fired = pred(text, meta)
        rows.append((f"predicate {name}", 0, fired == want,
                     f"fired on {fired}, want {want}"))

    # A FRONTMATTER BLOCK THAT DOES NOT PARSE. The predicate reads the block with its own
    # `yaml.safe_load` - a SECOND parse of bytes the queue already parsed once - so a peer
    # rewriting a shared ticket between `_load` and this read can fail HERE and not at the
    # load. The contract is PROPAGATE, and it fails closed in the caller (`check` names the
    # ticket and exits 1; review round 2 on task 216): swallowing a parse failure to `[]`
    # would read as "nothing lost" over a file whose contents are in doubt. The ValueError
    # fixture is not padding: `!!int '08'` scans and parses cleanly and fails in the
    # CONSTRUCTOR, escaping a YAMLError-only handler - the same shape `_read_fm` already
    # guards (its comment records the takedown of `list` and `next`).
    for what, broken in (
            ("an unterminated flow sequence (`title: [`, a yaml.YAMLError)",
             "---\nid: 70\ntitle: [\nstatus: todo\npriority: 3\nrefs: ''\n"
             "done_when: something observable\n---\n\nbody\n"),
            ("a constructor failure (`title: !!int '08'`, a ValueError)",
             "---\nid: 70\ntitle: !!int '08'\nstatus: todo\npriority: 3\nrefs: ''\n"
             "done_when: something observable\n---\n\nbody\n")):
        _, torn_meta = _scratch_task(broken, scratch / "torn")
        raised: BaseException | None = None
        try:
            pred(broken, torn_meta)
        except (yaml.YAMLError, ValueError) as exc:
            raised = exc
        rows.append((f"predicate PROPAGATES a block that does not parse: {what}",
                     0, isinstance(raised, (yaml.YAMLError, ValueError)),
                     f"raised {type(raised).__name__ if raised else 'nothing'}"))

    # THE CENSUS, RE-RUN EVERY TIME INSTEAD OF QUOTED. 0 lossy scalars over 1593 scalar
    # lines, measured 2026-08-29 (tasks/216); the row below re-derives the 0 against
    # whatever the shared queue holds now, so a peer introducing the shape turns this red
    # in the next run of this control rather than at the next lost tail.
    if not T.TASKS.is_dir():
        unchecked.append(f"live-queue scalar census NOT CHECKED - no queue at {T.TASKS}. "
                         f"Not a pass: the 0 the ticket quotes is re-derived here")
    else:
        lost: list[str] = []
        n = 0
        for t in T._load():
            if t.get("malformed"):
                continue
            try:
                text = t["path"].read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                # A file that vanished or became unreadable after `_load` must SHRINK the
                # census loudly, not quietly: a silent skip could publish a clean 0 over a
                # population that silently lost a member (review round 1, task 216).
                unchecked.append(f"live-queue scalar census skipped unreadable ticket "
                                 f"{t.get('id')} ({t['path'].name}): {exc}. Not a pass: "
                                 f"the 0 is only over tickets it could read")
                continue
            try:
                lost_keys = pred(text, t)
            except (yaml.YAMLError, ValueError) as exc:
                # The predicate parses the block a SECOND time (`lossy_scalar_fields`'s own
                # `yaml.safe_load`), so a ticket rewritten between `_load` and here can
                # fail HERE and not at the load. Same rule as the read above: the census
                # shrinks loudly rather than crashing on one member (review round 2,
                # task 216).
                unchecked.append(f"live-queue scalar census skipped ticket "
                                 f"{t.get('id')} ({t['path'].name}): its frontmatter did "
                                 f"not parse on the second read ({exc}). Not a pass: "
                                 f"the 0 is only over tickets it could read")
                continue
            n += 1
            lost += [f"{t.get('id')}.{k}" for k in lost_keys]
        rows.append((f"live queue: no frontmatter scalar parses shorter than its line "
                     f"wrote (0 of {n} tickets)", len(lost), not lost,
                     "clean" if not lost else f"LOSSY: {', '.join(sorted(lost)[:6])}"))
    return rows, unchecked


# --------------------------------------------------------------------------- direction 13
def _through_writer(blob: str, scratch: Path) -> tuple[bool, str]:
    """A blob read then re-written THE WAY `_set` WRITES IT: fm, body AND raw lines.

    One helper for every byte-identity row below, because they are all the same claim about
    different files: the writer can reproduce what it just read, quoted scalars included.
    A render called without the raw lines is the pre-217 writer, and against the cd4994d
    blob it is exactly the defect -- so a writer that will not accept its own reader's
    output is a named FAIL here, never a TypeError traceback.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    p = scratch / "through.md"
    p.write_text(blob, encoding="utf-8")
    try:
        fm, body, raw = T._read_fm(p)
    except T._Malformed as exc:
        return False, f"unparseable ({exc})"
    try:
        rendered = T._render(fm, body, raw)
    except TypeError:
        return False, ("writer takes no raw lines - a scalar the file holds quoted cannot "
                       "survive it")
    if rendered == blob:
        return True, "byte for byte"
    for d in difflib.unified_diff(blob.splitlines(), rendered.splitlines(), lineterm="", n=0):
        if d[:1] in "+-" and d[:3] not in ("+++", "---"):
            return False, f"DIFFERS: {d[:150]}"
    return False, "DIFFERS (only in line endings)"


def preservation_rows(tmp: Path) -> tuple[list[tuple], list[str]]:
    """13: the writer can reproduce a scalar a hand repair quoted (tasks/217).

    cd4994d hand-authored tasks/216 with a single-quoted title and done_when -- legal YAML,
    `check`-clean, and UNREPRODUCIBLE by the writer: `_render` re-emitted the title plain,
    so the byte round trip in CI went red on every pull request whose merge ref carried the
    file. The immediate red cleared when the 216 agent's own status write canonicalised the
    file, but the property stayed broken: any future hand repair that quotes a scalar the
    writer would emit plain re-reddens every open pull request at once, through a file none
    of them touched. The repair is in the writer -- it now re-emits, byte for byte, every
    line whose value the write did not change -- and this direction pins it on the file
    that broke, at the commit that broke it, rather than on a queue that happens to be
    canonical today.

    The rows, and why each is shaped the way it is:

    * THE BLOB REPRODUCED (the ticket's own repro, inverted): read the cd4994d 216 file
      with `_read_fm`, re-render through the production write path, and the bytes must come
      back IDENTICAL. Red under the pre-217 writer, which returns the title unquoted.
    * `_set` END TO END on a scratch queue: a status write on that ticket rewrites EXACTLY
      one line. This is the row that says preservation did not become "the writer passes
      raw bytes around": the write still happened, the changed field is in it, and
      everything else -- title and done_when included -- is the file's own bytes back.
    * VARIANTS (rule 15's other half -- the capability must survive the repair): the status
      line DID change; and a value this write DID change is still serialised canonically,
      quoted when its content needs it, because the serialiser -- not raw passthrough -- is
      what keeps `": "` inside a value from becoming an unparseable file (#141's cause).
    * THE GREENS, at the commits direction 12 pins them at: the repaired 214 title (quoted
      precisely because it holds " #") and the four census lines, each through the writer
      byte for byte. A preservation that re-quoted the unquoted, or re-canonicalised what
      it was given, would redden these -- the same pull requests, from the other side.
    """
    rows: list[tuple] = []
    unchecked: list[str] = []

    # ONE SHA, TWO CONSTANTS. `cd4994d` is both the commit that repaired 214 (direction
    # 12's LOSSY_REPAIR_COMMIT) and the one that hand-authored the quoted 216 ticket. Two
    # names for one address is rule 12's shape, so the equality is asserted, not promised.
    rows.append(("direction 13's hand-quoted fixture is direction 12's repair commit "
                 "(one sha, one address)", 0,
                 HAND_QUOTED_COMMIT == LOSSY_REPAIR_COMMIT,
                 f"{HAND_QUOTED_COMMIT} vs LOSSY_REPAIR_COMMIT {LOSSY_REPAIR_COMMIT}"))

    blob216 = _blob(HAND_QUOTED_COMMIT, HAND_QUOTED_216)
    if blob216 is None:
        unchecked.append(f"the preservation rows NOT CHECKED - no blob at "
                         f"{HAND_QUOTED_COMMIT}: no history to read is not a pass")
    else:
        ok, detail = _through_writer(blob216, tmp / "pres-through")
        rows.append(("the writer re-emits a scalar the file holds quoted, byte for byte "
                     "(the cd4994d 216 blob)", len(blob216), ok, detail))

        # END TO END through `_set`, which is the write every status transition makes.
        # Scratch queue, T.TASKS swapped the way directions 11/11c swap it; the blob is
        # the ticket, `todo`, exactly as the hand repair left it.
        sq = tmp / "pres-set"
        (sq / "tasks").mkdir(parents=True)
        target = sq / "tasks" / "216-x.md"
        target.write_text(blob216, encoding="utf-8")
        saved = T.TASKS
        try:
            T.TASKS = sq / "tasks"
            rc = T._set("216", status="in_progress")
        finally:
            T.TASKS = saved
        after = target.read_text(encoding="utf-8")
        old_lines, new_lines = blob216.splitlines(), after.splitlines()
        changed = [(x, y) for x, y in zip(old_lines, new_lines) if x != y]
        # THE EXPECTATION IS THE WHOLE FILE, NOT THE DIFF (review round 1, PR 97):
        # `zip` truncates at the shorter side, so a writer that rewrote the status line
        # AND appended or dropped trailing lines left this row green while the claim in
        # its name was false -- measured before the repair: the old condition passes a
        # writer that appends 2 junk lines. `expected` is the blob with exactly the one
        # status line replaced, and the row demands the file after `_set` equal it byte
        # for byte. `expected != blob216` asserts the substitution fired, so a pin drift
        # fails here rather than silently demanding a no-op write.
        expected = re.sub(r"^status: todo$", "status: in_progress", blob216,
                          count=1, flags=re.M)
        rows.append(("`_set` on the hand-quoted 216 ticket rewrites ONLY the status line",
                     rc, rc == 0 and expected != blob216 and after == expected
                     and len(changed) == 1
                     and changed == [("status: todo", "status: in_progress")],
                     f"exit {rc}, {len(changed)} line(s) differ, whole-file match: "
                     f"{after == expected}: {[(x[:40], y[:40]) for x, y in changed[:3]]}"))
        title_after = next((ln for ln in new_lines if ln.startswith("title:")), "(absent)")
        title_before = next((ln for ln in old_lines if ln.startswith("title:")), "(absent)")
        rows.append(("...and the quoted title line is the file's own bytes back", 0,
                     title_after == title_before and title_after.startswith("title: '"),
                     f"still quoted: {title_after.startswith('title: ' + chr(39))}; "
                     f"{title_after[:90]}"))

        # VARIANT: the write actually happened. A preservation that preserved the CHANGE
        # too would be a no-op writer -- exit 0, `status=in_progress` printed, file
        # untouched. It is the fail-open half of this mechanism and gets its own row.
        rows.append(("VARIANT: the status line DID change (preservation is not a no-op "
                     "writer)", 0, "status: in_progress" in new_lines,
                     f"file says: {next((ln for ln in new_lines if ln.startswith('status:')), '(absent)')}"))

    # VARIANT: a value this write DID change is serialised, not passed through. Raw lines
    # only ever restore what the write did not touch; anything else goes out through
    # safe_dump, which is what keeps `": "` inside a value from ending the line early.
    # Asserted as the PROPERTY -- the line is quoted and parses back to the value -- rather
    # than as PyYAML's particular quote character, which is its choice, not the mechanism.
    rendered = None
    try:
        rendered = T._render({"established_by": 'wrote ": " into a value once'},
                             "\nbody\n")
    except TypeError:
        pass
    line = next((ln for ln in (rendered or "").splitlines()
                 if ln.startswith("established_by:")), "(absent)")
    quoted = line.startswith("established_by: '") or line.startswith('established_by: "')
    value_back = None
    try:
        value_back = yaml.safe_load(line).get("established_by") if quoted else None
    except yaml.YAMLError:
        pass
    ok = value_back == 'wrote ": " into a value once'
    rows.append(("VARIANT: a changed value is written canonically, quoted when it needs it",
                 len(line) if rendered else 0, ok, f"line: {line[:100]}"))

    # THE GREENS at direction 12's pinned commits: the repaired 214 title and the four
    # census lines, each through the writer byte for byte.
    repaired214 = _blob(LOSSY_REPAIR_COMMIT, _T214)
    if repaired214 is None:
        unchecked.append(f"the 214 preservation green NOT CHECKED - no blob at "
                         f"{LOSSY_REPAIR_COMMIT}")
    else:
        ok, detail = _through_writer(repaired214, tmp / "pres-214")
        rows.append(("the repaired 214 title (quoted, ` #` inside) survives the write "
                     "path byte for byte", len(repaired214), ok, detail))
    green_blobs = []
    for tid, commit, path, _what in LOSSY_GREEN_COMMITS:
        b = _blob(commit, path)
        if b is None:
            unchecked.append(f"the {tid} preservation green NOT CHECKED - no blob at "
                             f"{commit}")
            continue
        green_blobs.append((tid, b))
    if green_blobs:
        results = [(tid, *_through_writer(b, tmp / f"pres-g{tid}")) for tid, b in green_blobs]
        bad = [(tid, d) for tid, ok, d in results if not ok]
        rows.append((f"the four census greens survive the write path byte for byte "
                     f"({', '.join(tid for tid, *_ in results)})", len(green_blobs),
                     not bad,
                     "all byte-identical" if not bad
                     else f"CHANGED: {bad[:3]}"))
    return rows, unchecked


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-prefix", action="store_true",
                    help="skip the positive controls in directions 2 and 8 (each needs a "
                         "pre-fix blob from git). Every arm they cover is then reported "
                         "NOT CHECKED.")
    ap.add_argument("--live-squash-refs", action="store_true",
                    help="additionally grade direction 11c against PR #16's real objects. "
                         "Off by default because the merged branch was deleted upstream: "
                         "only the checkout that performed the merge still has the tip, so "
                         "everywhere else this reports NOT CHECKED (exit 3) rather than a "
                         "pass. Direction 11c's fixture squashes for real and needs no flag.")
    ap.add_argument("--tasks-py", metavar="PATH",
                    help="grade this copy of tasks.py instead of the repository's. Used by "
                         "tasks_mutants.py, which writes a MUTATED copy into a tempdir; "
                         "nothing here ever writes to the file it is given.")
    a = ap.parse_args(argv)

    global TASKS_PY, T
    if a.tasks_py:
        TASKS_PY = Path(a.tasks_py).resolve()
        if not TASKS_PY.is_file():
            raise SystemExit(f"--tasks-py {TASKS_PY}: no such file")
        T = _load_subject(TASKS_PY)

    # Printed, not assumed. Both addresses, every run: the rows below are only about the
    # subject named here, and under a mutant they are about a copy in a tempdir.
    print(f"subject: {TASKS_PY}")
    print(f"queue: {T.TASKS}")
    before = sorted(p.name for p in T.TASKS.glob("*.md")) if T.TASKS.is_dir() else []

    rows: list[tuple] = []
    unchecked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="tasks-control-") as td:
        tmp = Path(td)
        for fn in (lambda: roundtrip_rows(),
                   lambda: add_rows(tmp, a.skip_prefix),
                   lambda: note_rows(tmp, a.skip_prefix),
                   lambda: check_rows(tmp),
                   lambda: reachability_rows(),
                   lambda: reachability_printed_rows(tmp),
                   lambda: misfiled_rows(tmp),
                   lambda: coverage_rows(),
                   lambda: status_rows(tmp),
                   lambda: evidence_rows(tmp, a.skip_prefix),
                   lambda: landed_rows(tmp, a.live_squash_refs),
                   lambda: lossy_check_rows(tmp),
                   lambda: lossy_predicate_rows(tmp),
                   lambda: preservation_rows(tmp)):
            r, u = fn()
            rows.extend(r)
            unchecked.extend(u)

    w = max(len(r[0]) for r in rows)
    print(f"\n{'direction':<{w}}   n   result   detail")
    print("-" * (w + 46))
    for name, n, ok, detail in rows:
        print(f"{name:<{w}}  {n:<4} {'ok  ' if ok else 'FAIL'}   {detail}")

    bad = [r for r in rows if not r[2]]
    print(f"\n{len(rows)} measurements, {len(bad)} FAILED, {len(unchecked)} NOT CHECKED")
    for name, n, ok, detail in bad:
        print(f"  FAIL {name}: {detail}")

    after = sorted(p.name for p in T.TASKS.glob("*.md")) if T.TASKS.is_dir() else []
    delta = sorted(set(after) ^ set(before))
    print(f"\nShared queue: {len(before)} files before, {len(after)} after."
          f"{' Changed while this ran: ' + ', '.join(delta) if delta else ' Untouched by this run.'}"
          f"\n(Peers write to this queue concurrently, so a delta here is reported, "
          f"not failed - nothing in this file writes to it.)")

    if unchecked:
        print(f"\nNOT CHECKED - {len(unchecked)}. Do not read the rows above as covering "
              f"these:")
        for u in unchecked:
            print(f"  {u}")
    if bad:
        return 1
    return 3 if unchecked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
