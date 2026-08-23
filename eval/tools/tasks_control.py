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
    created `tasks/71-...md` empty; `check` exited 0 on both for a day while task 71's agent
    worked from a ticket with no body (task 82).

THE FIVE DIRECTIONS
-------------------
1. ROUND TRIP, byte for byte, over every file in the live shared queue. Not "the values
   survive" -- the BYTES. The value round-trip was green while `_render` was rewriting
   `id: 01` as `id: 1`, because the value was never wrong (see `_id_text`). An
   `established_by` string is a durable record of what established a result, and this is
   the only direction that proves a status change cannot quietly edit one.

2. `add` FROM AN AGENT WORKTREE exits 0 and prints the created path. Run in a scratch
   git repo with its own worktree, because the defect only exists where `TASKS` and `ROOT`
   disagree -- and with the PRE-FIX copy of `tasks.py` as the positive control, since a
   green row from a harness that cannot observe the failure is rule 1's `total=0 passed=0`.

3. `check` STILL FAILS on the three things it is there to catch: a duplicate id, a missing
   `done_when`, a bad status. Each is exercised on its own scratch queue, with a
   well-formed queue as the negative control.

4. THE REACHABILITY WARNING, both ways. It must stay quiet on the four wordings that carry
   an escape branch and still fire on the two originals, on a bare universal and on a bare
   threshold. Only direction 4b -- must still WARN -- keeps a repair from being a deletion.

5. THE MISFILED-BODY CHECK, both ways, ON THE REAL BLOBS. `check` must fail on the actual
   `436bf64` pair naming both halves, and go quiet on the same two tickets as `28f6598`
   repaired them. `MISFILED_MARGIN` is pinned from BOTH sides -- the true positive at 0.36
   must fire, and the worst non-defect the history contains (task 62 against task 70's
   brief, 0.14) must not -- so raising the threshold and lowering it are each visible.
   A mutant can only show the check CAN fail; the 0.14 row and the ten-task-ids row are
   what ask whether it can still PASS (AGENTS.md rule 15).

THE CONTROLS DO NOT TOUCH THE SHARED QUEUE. `TASKS` is derived at import from
`git worktree list`, and monkeypatching a module constant that has already been derived is
how a lint once ran against the real tree while claiming a bad root (AGENTS.md rule 12). So
directions 2 and 3 build a real main-plus-worktree pair under a temporary directory and run
`tasks.py` there as a subprocess, at the address the defect actually lives at.

Usage, from anywhere:
    python3 eval/tools/tasks_control.py
    python3 eval/tools/tasks_control.py --skip-prefix   # no positive control for direction 2

Exit: 0 every direction measured and green; 1 a direction FAILED; 3 nothing failed but a
direction was NOT CHECKED. Never read 3 as a pass.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TASKS_PY = TOOLS / "tasks.py"
sys.path.insert(0, str(TOOLS))
import tasks as T                                                    # noqa: E402

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

_FM = "---\nid: {tid}\ntitle: {title}\nstatus: {status}\npriority: 3\nrefs: ''\n{dw}---\n{body}"


def _task_file(tid: str, title: str = "a title", status: str = "open",
               done_when: str | None = "something observable", body: str = "\nbody\n") -> str:
    dw = "" if done_when is None else f"done_when: {done_when}\n"
    return _FM.format(tid=tid, title=title, status=status, dw=dw, body=body)


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
    """Every file in the LIVE shared queue must survive read-then-write byte for byte."""
    if not T.TASKS.is_dir():
        return [], [f"round trip NOT CHECKED - no queue at {T.TASKS}"]
    files = sorted(T.TASKS.glob("*.md"))
    if not files:
        return [], [f"round trip NOT CHECKED - {T.TASKS} is empty"]
    broken, unparseable = [], []
    for p in files:
        original = p.read_text(encoding="utf-8")
        try:
            fm, body = T._read_fm(p)
        except T._Malformed as exc:
            unparseable.append(f"{p.name} ({exc})")
            continue
        if T._render(fm, body) != original:
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
        fm, body = T._read_fm(p)
    except T._Malformed:
        return False
    import io
    import yaml
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
        rc, out = _run_tool(wt / "eval/tools/tasks.py", "add", title,
                            "--why", "a body, so the file `add` writes passes `check`",
                            "--done-when", "an observable condition")
        return rc, out, sorted(q.name for q in (main / "tasks").glob("*.md"))

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
                 rc == 0 and ok_path and len(created) == len(created),
                 f"{printed[:150]}"))
    rows.append(("`add` wrote into the MAIN checkout's queue, not the worktree's", 0,
                 bool(created) and not (wt / "tasks").exists(),
                 f"main queue {created}; worktree tasks/ exists: {(wt / 'tasks').exists()}"))
    return rows, unchecked


def _run_tool_git(*argv: str) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(TOOLS), *argv], capture_output=True, text=True)
    return p.returncode, (p.stdout if p.returncode == 0 else (p.stderr or "")).strip()


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
        import yaml
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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-prefix", action="store_true",
                    help="skip direction 2's positive control (it needs the pre-fix blob "
                         "from git). Every arm it covers is then reported NOT CHECKED.")
    a = ap.parse_args(argv)

    print(f"queue: {T.TASKS}")
    before = sorted(p.name for p in T.TASKS.glob("*.md")) if T.TASKS.is_dir() else []

    rows: list[tuple] = []
    unchecked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="tasks-control-") as td:
        tmp = Path(td)
        for fn in (lambda: roundtrip_rows(),
                   lambda: add_rows(tmp, a.skip_prefix),
                   lambda: check_rows(tmp),
                   lambda: reachability_rows(),
                   lambda: misfiled_rows(tmp)):
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
