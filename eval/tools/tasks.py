#!/usr/bin/env python3
"""The open-work queue. One file per task, so nobody reads the whole backlog to find one item.

WHY THIS EXISTS
---------------
The first version was a single `TASKS.md`. Every agent had to read all of it to find the one
thing it needed, and a file nobody finishes reading protects nothing -- the same failure this
project already recorded for documentation. So: one file per task under `tasks/`, and a query
tool that prints the minimum.

    python3 eval/tools/tasks.py              # one line per open task
    python3 eval/tools/tasks.py next         # the single item to work on, in full
    python3 eval/tools/tasks.py show 04      # one task, in full
    python3 eval/tools/tasks.py start 04
    python3 eval/tools/tasks.py done 04 "what established it"
    python3 eval/tools/tasks.py add "title" --why "..." --done-when "..." [--priority 2]
    python3 eval/tools/tasks.py check        # lint; exit 1 if anything is malformed

`check` fails when a task has no `done_when`. A task that cannot be completed is a permanent
excuse, which is the task-list version of a criterion that cannot fail.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUSES = ("open", "in_flight", "done")


def _main_worktree() -> Path:
    """The MAIN checkout, even when called from inside an agent's worktree.

    THE QUEUE IS SHARED STATE. IT MUST NOT BE PER-BRANCH.

    Under one-agent-per-task each agent gets its own worktree, and a tracked `tasks/`
    directory is therefore COPIED into each one. Three agents filed a "task 27" on
    2026-08-23 and none of them collided with anything, because they were writing to three
    different copies. Renumbering them at merge time is possible -- it was done four times
    that day -- but it treats a structural problem as a clerical one.

    A queue that forks per branch is not a queue. Agents cannot see what their peers have
    just filed, so they duplicate the WORK as well as the number, and every merge fights
    over the same files.

    So all reads and writes go to the main worktree's `tasks/`, by absolute path, from
    wherever they are invoked. `git worktree list --porcelain` lists the main worktree
    first; that is the documented order, not an accident of parsing.

    The consequence, and it is deliberate: filing or closing a task shows up as an
    uncommitted change in the MAIN checkout, not in the agent's branch. That is correct.
    The queue's state is a fact about the project, not about one branch's work.
    """
    try:
        out = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent),
                              "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, check=True).stdout
        for line in out.split("\n"):
            if line.startswith("worktree "):
                return Path(line[len("worktree "):].strip())
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return ROOT          # not a git checkout: degraded, but no worse than before


TASKS = _main_worktree() / "tasks"


def _taken_ids() -> set[int]:
    """Ids in use: the shared queue, plus every id git has ever tracked under `tasks/`.

    History matters as much as the current directory. A merged-and-pruned branch still
    contributed its id, and reusing a number that a finding or a commit message already
    cites would silently repoint the citation at different work.
    """
    taken: set[int] = set()
    for p in TASKS.glob("*.md"):
        m = re.match(r"(\d+)", p.stem)
        if m:
            taken.add(int(m.group(1)))
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--all", "--pretty=format:",
                              "--name-only", "--diff-filter=A", "--", "tasks/"],
                             capture_output=True, text=True, check=True).stdout
        for line in out.split("\n"):
            m = re.match(r"tasks/(\d+)", line.strip())
            if m:
                taken.add(int(m.group(1)))
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return taken


def _parse(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {"id": p.stem.split("-")[0], "path": p, "malformed": "no frontmatter"}
    meta: dict = {"path": p, "body": m.group(2).strip()}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    meta.setdefault("id", p.stem.split("-")[0])
    return meta


def _load() -> list[dict]:
    if not TASKS.is_dir():
        return []
    return sorted((_parse(p) for p in TASKS.glob("*.md")),
                  key=lambda t: (int(t.get("priority", 9) or 9), t.get("id", "")))


def _line(t: dict) -> str:
    mark = {"open": "[ ]", "in_flight": "[~]", "done": "[x]"}.get(t.get("status", "open"), "[?]")
    return f"  {mark} {t.get('id','??')}  p{t.get('priority','?')}  {t.get('title','(no title)')}"


def cmd_list(status: str | None) -> int:
    ts = [t for t in _load() if not t.get("malformed")]
    show = [t for t in ts if status is None or t.get("status") == status]
    if status is None:
        show = [t for t in ts if t.get("status") != "done"]
    for t in show:
        print(_line(t))
    n_open = sum(1 for t in ts if t.get("status") == "open")
    print(f"\n{len(show)} shown; {n_open} open, "
          f"{sum(1 for t in ts if t.get('status') == 'in_flight')} in flight, "
          f"{sum(1 for t in ts if t.get('status') == 'done')} done")
    if n_open < 3:
        print("Fewer than 3 open. Running out has never yet been true here — re-read "
              "eval/FINDINGS.md for anything filed and never acted on.")
    return 0


def cmd_show(tid: str) -> int:
    for t in _load():
        if t.get("id") == tid:
            print(f"{t.get('id')}  [{t.get('status','open')}]  priority {t.get('priority','?')}")
            print(f"{t.get('title','')}\n")
            if t.get("refs"):
                print(f"refs: {t['refs']}")
            print(f"done when: {t.get('done_when','MISSING')}\n")
            print(t.get("body", ""))
            return 0
    print(f"no task {tid}", file=sys.stderr)
    return 1


def cmd_next() -> int:
    for t in _load():
        if t.get("status") == "open":
            return cmd_show(t["id"])
    print("nothing open")
    return 0


def _set(tid: str, **kw) -> int:
    for t in _load():
        if t.get("id") != tid:
            continue
        p: Path = t["path"]
        text = p.read_text(encoding="utf-8")
        for k, v in kw.items():
            if re.search(rf"^{k}:.*$", text, re.M):
                text = re.sub(rf"^{k}:.*$", f"{k}: {v}", text, count=1, flags=re.M)
            else:
                text = text.replace("---\n", f"---\n{k}: {v}\n", 1)
        p.write_text(text, encoding="utf-8")
        print(f"{tid}: " + ", ".join(f"{k}={v}" for k, v in kw.items()))
        return 0
    print(f"no task {tid}", file=sys.stderr)
    return 1


def cmd_add(a) -> int:
    """Create a task file, refusing to overwrite one that appeared while we looked.

    Writes go to the ONE shared queue (`_main_worktree`), which is what actually fixes the
    2026-08-23 collision -- three agents each created a `task 27` because each had its own
    copy of `tasks/`. With a single directory the remaining races are ordinary, and three
    layers cover them:

    1. The id is allocated above everything in the shared queue AND everything git has ever
       tracked under `tasks/`, so a merged-and-pruned branch cannot free a cited number.
    2. A lock in the repository's COMMON git dir -- shared by every worktree -- serialises
       concurrent allocation. `mkdir` is atomic, so it is the lock primitive.
    3. Exclusive create (`O_EXCL`) on the file itself, for a photo-finish inside the lock.
    """
    TASKS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:48]

    # The common dir is shared by every worktree; `TASKS` is not. Locking the shared thing
    # is the entire point -- a lock inside a worktree protects it from nobody.
    lock = None
    try:
        common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, check=True).stdout.strip()
        lock = (ROOT / common).resolve() / "tasks-id.lock"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        lock = None
    held = False
    if lock is not None:
        for _ in range(100):
            try:
                lock.mkdir()
                held = True
                break
            except FileExistsError:
                time.sleep(0.05)
            except OSError:
                break
        else:
            # A lock we waited out is more likely stale than contended. Say so and carry
            # on: refusing to file a task because of a leftover directory would be a guard
            # that costs more than the failure it prevents.
            print(f"note: {lock} held for 5s; proceeding — layers 1 and 3 still apply",
                  file=sys.stderr)
    try:
        nid_int = max(_taken_ids() | {0}) + 1
        return _write_task(a, slug, nid_int)
    finally:
        if held:
            try:
                lock.rmdir()
            except OSError:
                pass


def _write_task(a, slug: str, nid_int: int) -> int:
    for _ in range(50):
        nid = f"{nid_int:02d}"
        if any(TASKS.glob(f"{nid}-*.md")):
            nid_int += 1
            continue
        body = (f"---\nid: {nid}\ntitle: {a.title}\nstatus: open\n"
                f"priority: {a.priority}\nrefs: {a.refs or ''}\n"
                f"done_when: {a.done_when}\n---\n\n{a.why or ''}\n")
        try:
            with open(TASKS / f"{nid}-{slug}.md", "x", encoding="utf-8") as fh:
                fh.write(body)
        except FileExistsError:
            nid_int += 1
            continue
        print(f"created {(TASKS / f'{nid}-{slug}.md').relative_to(ROOT)}")
        return 0
    print("could not allocate a free task id after 50 attempts", file=sys.stderr)
    return 1


def cmd_check() -> int:
    bad = []
    # DUPLICATE IDS. The shared queue makes these hard to create; this makes them
    # impossible to keep. Four had to be renumbered by hand on 2026-08-23 and every one was
    # found by a person looking, which is not a mechanism. A duplicate id is worse than a
    # missing task: citations resolve to two different pieces of work and both look right.
    by_id: dict[str, list[str]] = {}
    for t in _load():
        by_id.setdefault(str(t.get("id", "??")), []).append(t["path"].name)
    for tid, names in sorted(by_id.items()):
        if len(names) > 1:
            bad.append(f"id {tid} used by {len(names)} files: {', '.join(sorted(names))} — "
                       f"citations to this number resolve to more than one task")
    for t in _load():
        if t.get("malformed"):
            bad.append(f"{t['path'].name}: {t['malformed']}")
            continue
        if not t.get("done_when"):
            bad.append(f"{t.get('id')}: no `done_when` — a task that cannot be completed "
                       f"is a permanent excuse")
        if t.get("status") not in STATUSES:
            bad.append(f"{t.get('id')}: status {t.get('status')!r} not in {STATUSES}")
        if not t.get("title"):
            bad.append(f"{t.get('id')}: no title")
    # UNREACHABLE done-whens: a smell detector, deliberately not a decision procedure.
    #
    # Two of this project's done-whens demanded conditions the data could not reach.
    # Task 08 wanted "SE below the smallest non-zero gap" - unsatisfiable, because the
    # gap shrinks as 1/n while SE shrinks as 1/sqrt(n) (FINDINGS #75). Task 01 wanted
    # "all six aspects" on a field that structurally cannot supply two of them.
    #
    # Reachability in general depends on data the task file does not contain, so it
    # cannot be decided here. But BOTH were repaired the same way - by adding an escape
    # branch naming the negative outcome - and that is checkable. A done-when that makes
    # a universal claim or a threshold comparison, with no alternative branch, is the
    # shape that failed twice.
    #
    # A WARNING, not a failure: plenty of universals are perfectly reachable. It prints
    # from a command run on purpose, which is the difference between this and the
    # unread manifest field of #62.
    warn = []
    UNIVERSAL = ("all ", "every ", "each ")
    THRESHOLD = ("below", "above", "exceeds", "smaller than", "larger than",
                 "at least", "under ", "over ", "resolvable")
    ESCAPE = ("either", " or ", "otherwise", "unless", "any ", "named", "reported as",
              "or the field", "or it is")
    for t in _load():
        dw = (t.get("done_when") or "").lower()
        if not dw or t.get("status") == "done":
            continue
        risky = [w for w in UNIVERSAL + THRESHOLD if w in dw]
        if risky and not any(e in dw for e in ESCAPE):
            warn.append(f"{t.get('id')}: done_when says {risky[0]!r} with no alternative "
                        f"branch. If the data cannot reach it there is no way to close "
                        f"this honestly - state what to report when it is NOT met (#75).")
    if warn:
        print(f"{len(warn)} reachability warning(s):")
        for w in warn:
            print(f"  {w}")
        print()

    if bad:
        print(f"{len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print(f"{len(_load())} task(s), all well-formed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("next")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("start"); s.add_argument("id")
    s = sub.add_parser("done"); s.add_argument("id"); s.add_argument("evidence")
    s = sub.add_parser("list"); s.add_argument("--status", choices=STATUSES)
    s = sub.add_parser("add")
    s.add_argument("title"); s.add_argument("--why"); s.add_argument("--done-when", required=True)
    s.add_argument("--refs"); s.add_argument("--priority", default=3)
    sub.add_parser("check")
    a = ap.parse_args()

    if a.cmd == "next":
        return cmd_next()
    if a.cmd == "show":
        return cmd_show(a.id)
    if a.cmd == "start":
        return _set(a.id, status="in_flight")
    if a.cmd == "done":
        return _set(a.id, status="done", established_by=a.evidence)
    if a.cmd == "add":
        return cmd_add(a)
    if a.cmd == "check":
        return cmd_check()
    return cmd_list(getattr(a, "status", None))


if __name__ == "__main__":
    sys.exit(main())
