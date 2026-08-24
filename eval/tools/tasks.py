#!/usr/bin/env python3
"""The open-work queue. One file per task, so nobody reads the whole backlog to find one item.

WHY THIS EXISTS
---------------
The first version was a single `TASKS.md`. Every agent had to read all of it to find the one
thing it needed, and a file nobody finishes reading protects nothing -- the same failure this
project already recorded for documentation. So: one file per task under `tasks/`, and a query
tool that prints the minimum.

    python3 eval/tools/tasks.py              # one line per task that is not done
    python3 eval/tools/tasks.py next         # the single item to work on, in full
    python3 eval/tools/tasks.py show 04      # one task, in full
    python3 eval/tools/tasks.py start 04                       # -> in_progress
    python3 eval/tools/tasks.py review 04 "<pull request url>"  # -> in_review
    python3 eval/tools/tasks.py testing 04 "what established it"  # -> in_testing
    python3 eval/tools/tasks.py done 04 "what established it"     # -> done, at merge
    python3 eval/tools/tasks.py note 04 -    # append a section to the BODY, from stdin
    python3 eval/tools/tasks.py add "title" --why "..." --done-when "..." [--priority 2]
    python3 eval/tools/tasks.py check        # lint; exit 1 if anything is malformed

`-` means READ IT FROM STDIN in every subcommand that takes durable text -- `note`, `testing`
and `done` alike. It used to mean that in `note` alone, so `done 04 - < account.md` stored the
literal one-character string `-` at exit 0, discarding whatever was redirected in (task 120).
See `_stdin_arg` for the sentinel and `cmd_evidence` for the two refusals that go with it.

The five statuses and what each one means are on `STATUSES` below. `.agents/skills/work/SKILL.md`
and `.agents/skills/dispatch/SKILL.md` are the two procedures that drive the transitions.

`check` fails when a task has no `done_when`. A task that cannot be completed is a permanent
excuse, which is the task-list version of a criterion that cannot fail.

IT ALSO FAILS WHEN A TICKET IS NOT ITS OWN TICKET
-------------------------------------------------
The frontmatter of a task file was gated from the start; its BODY was not, and the body is the
only part an agent is actually briefed from. On 2026-08-23 commit `436bf64` appended task 71's
entire 59-line brief to `tasks/70-set-a-size-...md` -- a filename guessed from a queue listing
title, which is AGENTS.md rule 12 -- and created `tasks/71-...md` with no body at all. `check`
exited 0 on both files for the 25m48s they stood on main -- `436bf64` 09:12:56 to `28f6598`
09:38:44 (#141) -- while `show 70` rendered a brief about trial disclosures. The duration is
the wrong measure anyway: the dispatched agent forked at `23be12c` (09:14:41), after the
misfile, and delivered at `c2bc8ce` (09:38:42), so ALL of task 71's execution ran against an
empty ticket.

So two failures, and they are the two halves of that one commit:

  * `body is empty` -- the stub `add` writes is not the task. Exact, no heuristic.
  * `body reads as task N's brief` -- `misfiled_body` below.

See `misfiled_body` for the measurement behind the threshold and for what it cannot catch.

`note` EXISTS BECAUSE THE BODY WAS WRITE-ONLY FROM AN AGENT WORKTREE
-------------------------------------------------------------------
`.agents/skills/work/SKILL.md` tells every dispatched agent to *"update the ticket with what
you learned - anything the next agent would otherwise re-derive belongs in the file"*, and
until this subcommand there was no way to obey it. Measured from a real agent worktree on
2026-08-23 (task 113): `Write`/`Edit` aimed at the shared checkout is refused by worktree
isolation; the worktree's own copy of `tasks/NNN-*.md` is a git-tracked file whose
main-checkout twin `start`/`done` rewrite concurrently, so committing an edit to it on a task
branch offers the merge a conflict in a file the merge is already rewriting; and `tasks.py`
had `next`, `show`, `start`, `done`, `list`, `add`, `check` and nothing that touched a body.

So tasks 105 and 106 both did the same thing: emptied their findings into the `established_by`
string. That is one unbroken line of prose inside YAML frontmatter, it cannot carry a backtick
(#80), and it is not where the next agent looks. A rule in an always-invoked skill that cannot
be obeyed is the rule being unusable as written, not the agents being careless.

WHAT IT DOES NOT DO, and both are deliberate:

  * It does NOT relax the isolation guard, and it does not need to. `TASKS` already resolves
    to the main checkout (`_main_worktree`), which is #94's decision; `note` writes there by
    the same mechanism `add`, `start` and `done` already use.
  * It does NOT rewrite the file. The bytes go out through `open(p, "a")` and nothing else, so
    "the rest of the file is unchanged" is true by construction rather than by a round-trip
    that happened to hold. `_set` rewrites the whole file to change one field and relies on
    `_render` reproducing every other byte; `note` does not have to rely on anything, and
    `tasks_control.py` asserts the file afterwards is the file before it plus `_note_block`
    and nothing else.

The address is resolved BY ID, never by a filename you typed. That is the whole difference
between this and the `>>` an agent would otherwise reach for: AGENTS.md rule 12's worked
example is an append aimed at a filename guessed from a queue listing title, which created a
second, malformed task. A shell append is not blocked by anything -- it is just aimed by hand.

`-` reads the note from stdin, which is the backtick-safe channel #80 is about: a quoted
heredoc carries backticks, newlines and shell metacharacters into the file verbatim, and an
argv string carrying a backtick is command substitution before this program ever runs.

THE FRONTMATTER IS YAML, AND IS READ AND WRITTEN AS YAML
-------------------------------------------------------
It did not used to be. `_parse` split each line on its first colon and `_set` wrote back an
f-string, so a value that itself contained ": " -- which is how anyone writes a sentence --
produced a block that `yaml.safe_load` rejects with ScannerError. On 2026-08-23 that was 44 of
58 files: 39 `established_by`, 5 `title`, 2 `done_when`.

Quoting the files alone does not fix it, and this was measured rather than assumed. The old
`_parse` took everything after the first colon literally, so a quoted value kept its quote
characters -- `status` became the 6-character string `"done"`, which is not in `STATUSES`, and
`int(priority)` raised. And `_set` rewrote `established_by` unquoted on every `done`, so a
file-only fix undid itself on the next queue write. It is a reader/writer defect; the files
were only its output.

So: `yaml.safe_load` in, `yaml.safe_dump` out, and PyYAML is a hard dependency -- an import
failure stops the tool rather than falling back to the regex reader, because a silent fallback
would make the repair invisible and the defect permanent.

Two properties the serialiser buys that hand-quoting does not: it is resolver-aware, so `id:
'01'` is quoted (bare `01` is octal 1 in YAML 1.1) and `refs: 'yes'` is quoted (bare `yes` is
`True`); and `width` is set high enough that a long value stays on one line, which is what keeps
`grep -h "^title:" tasks/*.md` working. The format is still grep-first. It is now also parseable
by anything that is not this file.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:      # loud, never a fallback -- see the module docstring
    raise SystemExit(
        "tasks.py requires PyYAML: python3 -m pip install pyyaml\n"
        "(The queue's frontmatter is YAML and is written by a real serialiser. Falling back "
        "to a line-splitting reader is what produced 44 unparseable files in the first place.)"
    ) from exc

ROOT = Path(__file__).resolve().parents[2]

# THE STATUS VOCABULARY, AND WHY IT IS FIVE VALUES.
#
# It was `("open", "in_flight", "done")` until 2026-08-23. Three values cannot express the
# middle of the flow the operator specified that day: an agent opens a pull request, a reviewer
# comments on it, the agent addresses the comments, and only then is the work waiting on the
# orchestrator to verify and merge. Under three values everything from "an agent picked this
# up" to "this is reviewed and waiting on you" is one indistinguishable `in_flight`, so the
# orchestrator cannot tell which branches are ITS turn without opening every pull request.
#
#   todo         nobody has it
#   in_progress  an agent is working it
#   in_review    a pull request is open and the review loop is running
#   in_testing   the agent has finished; the orchestrator has to verify and merge
#   done         merged
#
# LEGACY NAMES ARE ACCEPTED PERMANENTLY, NOT FOR A MIGRATION WINDOW. `check` fails any status
# not in STATUSES, and the queue is SHARED across every agent worktree while each worktree
# carries its own, possibly older, copy of this file. An agent forked before the rename runs
# `start`, writes `in_flight` into the shared queue, and every peer's `check` goes red at once
# on a file none of them touched. The alias costs one dict and closes that class outright.
STATUSES = ("todo", "in_progress", "in_review", "in_testing", "done")
LEGACY_STATUSES = {"open": "todo", "in_flight": "in_progress"}

#: The statuses that MUST name a pull request. Both of them do: `in_review` because the state
#: is a report on one, `in_testing` because the orchestrator merges from one. Written once, so
#: `check`'s message and the states it gates cannot disagree.
PR_REQUIRED = ("in_review", "in_testing")


def _status(v) -> str:
    """The canonical status for a value read off disk.

    Legacy names map. Anything else passes through UNCHANGED rather than defaulting to a valid
    state, so `check` still reports a typo by name -- normalising an unknown value into
    `todo` would be a fail-open channel (AGENTS.md rule 7): the queue would look well-formed
    and one task would sit in a state nobody chose.
    """
    s = _scalar(v).strip()
    return LEGACY_STATUSES.get(s, s)

# One frontmatter grammar, used by the reader and the writer alike.
_FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)

# `width` prevents PyYAML folding a long scalar across lines, which would break the grep-first
# idioms in `.claude/skills/tasks/SKILL.md`. `sort_keys=False` preserves each file's existing
# key order. `allow_unicode` keeps em-dashes as em-dashes instead of — escapes.
_DUMP = dict(sort_keys=False, allow_unicode=True, width=10 ** 9, default_flow_style=False)


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


#: A ticket's branch is `task-<id>-<slug>`, local or on any remote. Leading zeros are
#: tolerated because the queue writes `id: 01` and a branch is named from the integer.
def _branch_pattern(tid: str) -> "re.Pattern[str] | None":
    try:
        n = int(str(tid).strip())
    except (TypeError, ValueError):
        return None
    return re.compile(rf"^refs/(?:heads|remotes/[^/]+)/task-0*{n}-")


def _all_refs() -> list[str] | None:
    """Every local and remote branch ref, or None if git could not be asked.

    THE ADDRESS IS THE QUEUE'S OWN. `TASKS` is derived from `_main_worktree()`, and refs are
    shared by every worktree of that repository, so asking git at `TASKS.parent` cannot end
    up describing a different checkout from the one the tickets were read out of (rule 12).
    None is returned rather than an empty list: `[]` would say "no branch exists for any
    ticket", which is a confident, uniform answer of exactly the shape rule 12 names.
    """
    try:
        out = subprocess.run(["git", "-C", str(TASKS.parent), "for-each-ref",
                              "--format=%(refname)", "refs/heads/", "refs/remotes/"],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    return [ln.strip() for ln in out.split("\n") if ln.strip()]


#: WHAT "LANDED" IS MEASURED AGAINST, in order, and every one that resolves is used.
#
# `main` is the condition as written: the queue says merged, so `main` should hold it.
# `origin/main` covers a CI checkout with no local `main`.
#
# THE THIRD BASE IS THE CALLER'S OWN HEAD, AND IT IS RESOLVED AT THE CALLER'S ADDRESS, NOT THE
# QUEUE'S. `TASKS` is the MAIN checkout, so a bare `HEAD` asked there is `main` under another
# name -- which is what the first version of this list held, a second opinion that was a
# restatement of the first (AGENTS.md rule 12: the address is an input to the check). Every
# worktree of a repository shares one object database, so resolving the invoking worktree's
# HEAD to a SHA and comparing against that is unambiguous and needs no second git dir.
#
# It earns its place because `main` alone makes the gate unfixable from the branch that fixes
# it: the agent landing an orphaned branch cannot turn its own `check` green before the
# orchestrator merges, and a gate that stays red through correct work is a gate that gets
# bypassed. In the main checkout and in CI it resolves to the same commit as `main`, so the
# condition is unchanged exactly where it is enforced.
_LAND_BASES = ("main", "origin/main")


def _head_at(where) -> str | None:
    """The SHA of HEAD in the checkout at `where`, or None if there isn't one."""
    try:
        r = subprocess.run(["git", "-C", str(where), "rev-parse", "--verify", "-q",
                            "HEAD^{commit}"], capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    return r.stdout.strip() or None


def _caller_heads() -> list[tuple[str, str | None]]:
    """The HEADs of the checkout the PROCESS is in and of the one holding this FILE.

    TWO ADDRESSES, BOTH ASKED, BECAUSE THEY ARE ROUTINELY DIFFERENT HERE. `ROOT` comes
    from `__file__`, and `.agents/skills/work/SKILL.md` tells an agent to run the tool
    **from the main checkout by absolute path** when its own copy might be stale -- so
    `ROOT` is then the main checkout and the agent's branch HEAD is not consulted at all,
    which silently defeats the repair path this base exists to keep open. `Path.cwd()` is
    the branch the caller is actually working on.

    Neither is redundant: a git hook runs with cwd inside the repository whose commit is
    being checked, and an agent invoking the shared copy has its work at cwd and nothing
    at `ROOT`. They are de-duplicated by SHA downstream, so when they coincide -- the
    main checkout, and CI -- exactly one is named. AGENTS.md rule 12: the address is an
    input to the check, and this check has two.
    """
    return [("this checkout's HEAD", _head_at(Path.cwd())),
            (f"HEAD of {ROOT.name}", _head_at(ROOT))]


def _resolved_bases() -> list[tuple[str, str]]:
    """`(label, sha)` for every base that resolves, DE-DUPLICATED BY SHA.

    Every base is carried as a SHA, not as the name it was written with, so a name that is
    another name's commit is dropped instead of being printed as a second opinion -- which is
    what a bare `HEAD` in `_LAND_BASES` was: asked at the queue's address it IS `main`, and the
    census line named two bases where there was one.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, sha: str | None) -> None:
        if sha and sha not in seen:
            seen.add(sha)
            out.append((label, sha))

    for b in _LAND_BASES:
        try:
            r = subprocess.run(["git", "-C", str(TASKS.parent), "rev-parse", "--verify",
                                "-q", f"{b}^{{commit}}"], capture_output=True, text=True)
        except (FileNotFoundError, OSError):
            return []
        if r.returncode == 0:
            add(b, r.stdout.strip())
    # A CALLER HEAD IS ONLY A BASE IF IT EXISTS WHERE THE ANCESTRY QUERY RUNS. The query
    # runs at `TASKS.parent`; `Path.cwd()` may be a DIFFERENT repository entirely, and a
    # SHA from one repository is not an object in another -- `merge-base` then exits 128
    # for every ticket, which the three-valued `_is_ancestor` reads as "could not answer"
    # and turns the whole gate into NOT_CHECKED. Silent, total, and it looks like a clean
    # queue. Caught by `tasks_control`'s own caller-HEAD row, which runs the tool with
    # cwd in an unrelated checkout (AGENTS.md rule 12: two addresses, and only one of
    # them was being checked).
    for label, head in _caller_heads():
        if head and _head_exists_here(head):
            add(f"{label} {head[:9]}", head)
    return out


def _head_exists_here(sha: str) -> bool:
    """Is `sha` an object in the repository the ancestry query runs against?"""
    try:
        return subprocess.run(["git", "-C", str(TASKS.parent), "rev-parse", "--verify",
                               "-q", f"{sha}^{{commit}}"],
                              capture_output=True, text=True).returncode == 0
    except (FileNotFoundError, OSError):
        return False


def _is_ancestor(ref: str, bases: "list[tuple[str, str]] | None" = None) -> bool | None:
    """True / False / **None, meaning git could not answer**.

    `merge-base --is-ancestor` uses exit 0 for yes and exit 1 for no, and reserves
    anything else -- 128 for a ref that vanished between `_all_refs()` and here, or a
    corrupt object -- for an ERROR. Reading 128 as "not an ancestor" turns a git failure
    into a confident accusation: `check` would exit 1 and name a ticket whose ancestry it
    never established. A verdict this tool did not compute must not be reported as one it
    did (AGENTS.md rule 2), so an error propagates as None and `landed_status` degrades
    the ticket to NOT_CHECKED rather than to ORPHANED.
    """
    unknown = False
    for _label, rev in (_resolved_bases() if bases is None else bases):
        try:
            rc = subprocess.run(["git", "-C", str(TASKS.parent), "merge-base",
                                 "--is-ancestor", ref, rev],
                                capture_output=True, text=True).returncode
        except (FileNotFoundError, OSError):
            return None
        if rc == 0:
            return True
        if rc != 1:
            unknown = True
    return None if unknown else False


#: DIFF OPTIONS SHARED BY BOTH SIDES OF THE PATCH-ID COMPARISON, and they have to be the same
#: options or the comparison is between two different renderings of the same change. `patch-id`
#: hashes the diff TEXT, so rename detection -- on by default, and a function of how much of the
#: tree each side is asked about -- can give one side a `rename from/to` pair where the other has
#: a delete and an add. `--no-renames` removes the only option whose value differs between a
#: two-tree diff and a per-commit one.
_PATCH_DIFF = ("--no-color", "--no-renames", "--full-index")


def _patch_id(diff: str) -> str | None:
    """The patch-id of one diff, or None if there is nothing to identify."""
    if not diff.strip():
        return None
    try:
        r = subprocess.run(["git", "-C", str(TASKS.parent), "patch-id", "--stable"],
                           input=diff, capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError):
        return None
    fields = r.stdout.split()
    return fields[0] if r.returncode == 0 and fields else None


def _base_patch_ids(base_sha: str, rev: str,
                    cache: "dict | None") -> "set[str] | None":
    """Patch-ids of the commits `rev` gained since `base_sha`, or None if git failed.

    CACHED ON `(base_sha, rev)` BECAUSE THE WORK IS PER-PAIR AND THE CALLS ARE PER-REF.
    Rendering `base_sha..rev` as patches costs about 65ms per call over a 60-commit range
    (measured 2026-08-24 on a fixture of 12 orphaned refs: 288ms of `check` without the
    squash arm, 1070ms with it), and every `task-<id>-*` ref forked from the same commit
    asks for the identical answer.

    A FAILURE IS NEVER CACHED. A cached `None` would turn one transient git error into a
    verdict for every remaining ref, which is rule 7's fail-open channel: the second ref's
    answer would come from the first ref's failure with nothing saying so.
    """
    key = (base_sha, rev)
    if cache is not None and key in cache:
        return cache[key]
    try:
        log = subprocess.run(["git", "-C", str(TASKS.parent), "log", *_PATCH_DIFF,
                              "-p", "--no-merges", f"{base_sha}..{rev}"],
                             capture_output=True, text=True, check=False)
        if log.returncode != 0:
            return None
        ids = subprocess.run(["git", "-C", str(TASKS.parent), "patch-id", "--stable"],
                             input=log.stdout, capture_output=True, text=True, check=False)
    except (FileNotFoundError, OSError):
        return None
    if ids.returncode != 0:
        return None
    out = {f[0] for f in (ln.split() for ln in ids.stdout.splitlines()) if f}
    if cache is not None:
        cache[key] = out
    return out


def _squash_landed(ref: str, bases: "list[tuple[str, str]]",
                   cache: "dict | None" = None) -> bool | None:
    """Did `ref`'s CHANGES land, as a commit that is not `ref`? True / False / **None**.

    THE ANCESTRY TEST IS THE WRONG ONE UNDER SQUASH MERGES, and this repository squashes.
    `gh pr merge --squash` writes a commit with ONE parent and a tree of its own, so the
    branch tip it landed is NOT an ancestor of it -- `git branch -d` refuses such a branch
    for exactly that reason and is correct. Measured on this repository: PR #16's tip
    `58df942` is an ancestor of nothing on `main` today, while its squash commit `399280e`
    is an ancestor of `main`.

    NOT "an ancestor of nothing, ever". A later `git merge --no-ff` of a descendant of that
    tip would make it reachable again, and this arm would then be answering a question the
    ancestry arm has already answered True. That order is why the arms compose as they do.

    So this asks the question ancestry was standing in for: is the branch's combined change
    already present on the base? `merge-base .. ref` rendered as one diff has the same
    patch-id as the squash commit GitHub wrote, because they are the same change. An empty
    diff is True -- a branch introducing nothing is a branch with nothing to lose.

    THREE-VALUED FOR THE SAME REASON `_is_ancestor` IS. A git failure is not a "no", and a
    ticket whose content this could not read must degrade to NOT_CHECKED rather than become
    an accusation (AGENTS.md rule 2).

    WHAT IT CANNOT SEE. A squash whose diff differs from the branch's own -- because the base
    moved under a file the branch also edited, and the merge resolved the overlap -- has a
    different patch-id and reads False. That is fail-closed: it costs attention, never
    evidence, and it is the direction rule 7 asks for.
    """
    unknown = False
    for _label, rev in bases:
        try:
            mb = subprocess.run(["git", "-C", str(TASKS.parent), "merge-base", ref, rev],
                                capture_output=True, text=True, check=False)
            if mb.returncode != 0:
                unknown = True
                continue
            base_sha = mb.stdout.strip()
            d = subprocess.run(["git", "-C", str(TASKS.parent), "diff", *_PATCH_DIFF,
                                base_sha, ref], capture_output=True, text=True,
                               check=False)
            if d.returncode != 0:
                unknown = True
                continue
            if not d.stdout.strip():
                return True
            want = _patch_id(d.stdout)
            if want is None:
                unknown = True
                continue
            seen = _base_patch_ids(base_sha, rev, cache)
            if seen is None:
                unknown = True
                continue
            if want in seen:
                return True
        except (FileNotFoundError, OSError):
            return None
    return None if unknown else False


def _is_landed(ref: str, bases: "list[tuple[str, str]] | None" = None,
               cache: "dict | None" = None) -> bool | None:
    """Is `ref`'s work on the base, by REACHABILITY or by CONTENT? True / False / None.

    Two tests, because this repository has used two merge flows and the stored refs of both
    are still around. `git merge --no-ff` leaves the tip reachable; `gh pr merge --squash`
    leaves the content and not the tip. Either one landing is landed.

    The three values compose the only way they safely can: a True from either test wins, and
    an unanswered test outranks a False -- a ref neither test could read is NOT_CHECKED, never
    ORPHANED.

    `cache` is the caller's dict, shared across refs for one invocation. See
    `_base_patch_ids` for what it holds and what it deliberately does not.
    """
    b = _resolved_bases() if bases is None else bases
    anc = _is_ancestor(ref, b)
    if anc is True:
        return True
    sq = _squash_landed(ref, b, cache)
    if sq is True:
        return True
    if anc is None or sq is None:
        return None
    return False


def landed_status(tid: str, refs: list[str] | None, is_landed) -> tuple[str, list[str]]:
    """Has a closed ticket's work reached `main`? THREE values, never two.

    `LANDED` at least one `task-<id>-*` ref has landed -- its tip is an ancestor of the
                 base, OR its change is on the base as a squash commit. `_is_landed` is the
                 predicate `check` passes, and both flows count: the repository has used
                 both, and refs from each survive.
    `ORPHANED` such a ref exists and NONE of them has landed by either test. This is the
                 defect: a queue entry reading `done` over work `main` has never seen. Task
                 70 sat like that with 458 lines of `eval/judge/paired_verdicts.py` reachable
                 from nowhere else, and nothing compared a closed ticket against the tree.
    `NOT_CHECKED` no such ref exists -- the usual case, because a merged branch is normally
                 deleted. **It is not a pass.** `total=0 passed=0` is indistinguishable from
                 correct failure (rule 1), and a two-valued version of this check would
                 report 112 of 119 closed tickets as verified while verifying nothing.

    WHAT IT ASKS IS ARRIVAL, NOT SURVIVAL. A branch merged with `-s ours`, or one whose
    changes a later commit reverted, reads `LANDED` here and its work is absent from the tree
    today. That is the variant this cannot see (rule 15), and it is why the failure message
    says *read the diff* rather than *merge it*.

    A VERDICT IS RELATIVE TO THE REFS THE CALLER CAN SEE, AND CI CAN SEE FEWER. Measured on
    the same commit, the same day: the operator's checkout read `7 LANDED / 112 NOT_CHECKED`
    and CI read `6 LANDED / 113 NOT_CHECKED`, because task 70's branch was never pushed. **The
    defect this exists to catch reads NOT_CHECKED in CI** -- correctly, since from there no
    such ref exists. So the load-bearing instance is the git hook in the checkout that HOLDS
    the branches, and CI is a weaker copy of it, not a second opinion. Do not read a green CI
    run as covering this.
    """
    pat = _branch_pattern(tid)
    if refs is None or pat is None:
        return "NOT_CHECKED", []
    cand = sorted(r for r in refs if pat.match(r))
    if not cand:
        return "NOT_CHECKED", []
    # `is_landed` is THREE-VALUED: None means git could not answer (a ref that vanished
    # between the listing and here, a corrupt object). An unanswered ref is not a
    # negative one, so it degrades the ticket to NOT_CHECKED. Accusing on a failed read
    # is rule 2 -- inferring a state from something that is not a report of it.
    verdicts = [is_landed(r) for r in cand]
    if any(v is True for v in verdicts):
        return "LANDED", cand
    if any(v is None for v in verdicts):
        return "NOT_CHECKED", cand
    return "ORPHANED", cand


class _Malformed(Exception):
    """A task file `check` should name, rather than one `_load` should crash on."""


def _read_fm(p: Path) -> tuple[dict, str]:
    """(frontmatter mapping, body) -- the mapping as YAML sees it, the body byte-for-byte.

    The RAW mapping, with YAML's own types, because it is what `_set` writes back: preserving
    `priority: 3` as an integer rather than restringing it to `'3'` on every status change.
    `_parse` is the one that normalises for readers.
    """
    text = p.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        raise _Malformed("no frontmatter")
    try:
        fm = yaml.safe_load(m.group(1))
    # ValueError as well as YAMLError, and it is not defensive padding: `!!int '08'` scans
    # and parses cleanly, then fails in the CONSTRUCTOR on `int('08', 8)`. That escapes a
    # YAMLError-only handler and takes down `list`, `next` and `check` for every task in
    # the queue, because `_load` reads them all. One bad file must cost one bad file.
    except (yaml.YAMLError, ValueError) as exc:
        detail = str(exc).replace("\n", " ")[:160]
        raise _Malformed(f"frontmatter is not valid YAML: {detail}") from exc
    if not isinstance(fm, dict):
        raise _Malformed(f"frontmatter is {type(fm).__name__}, not a mapping")
    return fm, m.group(2)


class _PlainDigits(str):
    """An id, emitted as bare digits instead of `'01'`.

    THE ID LINE IS DELIBERATELY LEFT BYTE-FOR-BYTE AS IT WAS, and it is the one place this
    file does not let the serialiser choose. `safe_dump("01")` writes `id: '01'`, because
    bare `01` is octal 1 in YAML 1.1 and quoting is the only way a *string* survives. That
    is more correct in isolation and it breaks the shared queue: every agent worktree
    carries its own copy of this tool, three peers were mid-task on the previous one when
    this landed, and their line-splitting reader takes `'01'` literally -- so `start 01`,
    `done 01` and `show 01` all answer "no task 01" and an agent cannot close its work.
    Measured, not assumed: the old reader against migrated files differed on 175 outputs,
    and the id line was the only difference with a functional consequence.

    So the id goes out plain and comes back as an int (or as a str for `08`/`09`, which no
    resolver claims), and `_parse` pads it back to the id every caller compares against.
    The cost is that an external reader sees `id: 01` as 1 -- redundant information, since
    the id is also the filename prefix and `check` guarantees it is unique. Quoting it is a
    one-line change once no worktree is running a pre-YAML copy of this file.
    """


def _represent_plain_digits(dumper, value):
    """Emit bare digits by asking the resolver what bare digits would mean.

    A fixed tag does not work, and the round-trip assertion is what said so rather than
    review: hard-coding the int tag emitted `id: !!int '08'`, because plain `08` is not an
    octal literal and PyYAML will not silently drop a tag it cannot round-trip. Worse, that
    line then loads by calling `int('08', 8)` -- a ValueError, not a YAMLError, so it would
    have escaped `_read_fm`'s handler and crashed every command in the tool.

    Resolving the tag from the plain text instead means the emitter always agrees with
    itself: `01` and `40` carry the int tag and go out plain, `08` and `09` carry the str
    tag and go out plain, and nothing is ever tagged or quoted.
    """
    text = str(value)
    return dumper.represent_scalar(dumper.resolve(yaml.ScalarNode, text, (True, False)), text)


yaml.SafeDumper.add_representer(_PlainDigits, _represent_plain_digits)


def _id_text(raw) -> str:
    """The canonical text of an id: the two-digit, zero-padded string every caller compares.

    THE READER AND THE WRITER MUST SHARE THIS, and they did not at first. `_render` wrapped
    the id only when YAML handed it back as a `str`, which is true for `08` and `09` and
    false for `01`-`07` (octal) and `10`+ (decimal). So `_parse` read `id: 01` and correctly
    reported "01", while the next `start` or `done` on that same file wrote it back as
    `id: 1` -- values intact, file quietly renumbered, and a peer on the old reader then
    unable to find task 01 at all.

    The value round-trip did not catch it, because the value was never wrong. Only asserting
    that read-then-write reproduces the file byte-for-byte did.
    """
    if raw is None or isinstance(raw, bool):
        return ""
    if isinstance(raw, int):
        return f"{raw:02d}"
    return str(raw).strip()


def _render(fm: dict, body: str) -> str:
    out = dict(fm)
    tid = _id_text(out.get("id"))
    if tid.isdigit():
        out["id"] = _PlainDigits(tid)
    return "---\n" + yaml.dump(out, Dumper=yaml.SafeDumper, **_DUMP) + "---\n" + body


#: An ADDRESS is not a claim, and the heuristic below reads English.
#:
#: `under eval/findings/` is a path, `over eval/runs/` is a path, `docstat.py --sweep` is a
#: command. Matching THRESHOLD against them reads a preposition of PLACE as one of DEGREE,
#: and that was not hypothetical: the single reachability warning `check` printed on
#: 2026-08-23 was task 59's, on `under eval/findings/`, which compares nothing.
#:
#: A locative preposition immediately before an address belongs to the address, so it is
#: consumed with it -- dropping the path alone would leave the bare `under` still matching.
_ADDRESS = re.compile(
    r"(?:\b(?:under|over|below|above|within|in|at|from|into|to)\s+)?"
    r"(?:\S*/\S*|\S+\.(?:md|py|json|jsonl|gd|rs|ts|cs|toml|ya?ml)\b\S*|--\S+)")

#: `at all` is a lexicalised adverbial, not a quantifier over anything. It is the one place
#: in these done-whens where a UNIVERSAL word is not a determiner, and task 38's own
#: done_when ("no escape branch at all") is the instance.
_NOT_A_QUANTIFIER = re.compile(r"\bat all\b")

#: The shape that failed twice (#75): a claim over everything, or against a threshold.
UNIVERSAL = ("all", "every", "each")
THRESHOLD = ("below", "above", "exceeds", "smaller than", "larger than",
             "at least", "under", "over", "resolvable")

#: HYPOTHETICAL -- the closed class of English function words that mark a clause or a noun
#: phrase as conditional or alternative. That is what an escape branch IS: a second,
#: hypothetical clause naming what to report when the first condition is not met.
#:
#: WHY THIS IS NOT JUST A LONGER LIST, which is the option AGENTS.md argues against.
#: The list it replaces mixed two kinds of entry. Five were function words (`either`, `or`,
#: `otherwise`, `unless`, `any`); four were content phrases copied off tasks 01 and 08 --
#: `named`, `reported as`, `or the field`, `or it is`. The content phrases encode how those
#: two tasks happened to word their escape and match nothing else, which is the enumeration
#: failure exactly: task 32 wrote `naming`, one letter from `named`, and warned. So did 35
#: and 58, both of which open their escape with `if`, the commonest conditional in the
#: language and absent from the list.
#:
#: A closed grammatical class can be completed and then left alone; a set of observed
#: phrasings cannot, because the next writer's phrasing is not in it. That is the whole
#: difference, and it is why this is not (b) with better manners.
#:
#: ITS LIMIT, which the old comment did not state. An escape branch carrying NO marker --
#: "the file records the negative result with its evidence" -- is invisible here and always
#: will be; and a marker used non-hypothetically ("measured `when` re-graded offline")
#: silences a warning that should have fired. Both are why this stays a warning. A gate that
#: fails on correct input gets disabled, and a check that fires where nothing is wrong
#: spends exactly the attention a check firing correctly needs (rule 16).
#: A FREE RELATIVE IS NOT A CONDITIONAL, and this is measured rather than reasoned.
#: `whatever` and `whichever` were in this set for one day. Dropping each marker in turn
#: over the 62 done-whens then in the queue showed what each one silences: `if` silences
#: task 58, `where` silences 08, `or` silences 11 and 52, `any` silences 01, 25, 26 and 42
#: -- every one of them a real escape branch. `whatever`'s ONLY contribution was silencing
#: task 62, which has three universals and no escape at all, on "after whatever repairs
#: those entries name". A free relative names a definite-but-unspecified thing; it opens no
#: branch. Both go, as a construction rather than as a word, because `whichever` is the
#: same trap waiting for the next writer.
#:
#: The rest stay although this corpus does not exercise them. That is the difference
#: between a class and a list: an escape written with `otherwise` is the phrasing nobody
#: had yet, which is exactly how the old list failed.
HYPOTHETICAL = ("if", "unless", "when", "whenever", "where", "wherever",
                "either", "or", "otherwise", "else", "instead", "any", "none")


def _words(text: str, phrases: tuple[str, ...]) -> list[str]:
    """Which phrases occur as whole words. Substring matching is why `resolvable` fired
    inside task 08's own escape branch (`unresolvable-by-repetition`) -- the repair
    triggering the risk it repairs."""
    return [p for p in phrases
            if re.search(rf"(?<!\w){re.escape(p)}(?!\w)", text)]


def reachability_warning(done_when: str) -> str | None:
    """The message `check` should print for this done_when, or None. Pinned by
    `eval/tools/tasks_control.py` in both directions; it is a function so that it can be.

    A SMELL, DELIBERATELY NOT A DECISION PROCEDURE. Two of this project's done-whens
    demanded conditions the data could not reach. Task 08 wanted "SE below the smallest
    non-zero gap" -- unsatisfiable, because the gap shrinks as 1/n while SE shrinks as
    1/sqrt(n) (#75). Task 01 wanted "all six aspects" on a field that structurally cannot
    supply two of them. Reachability in general depends on data the task file does not
    contain, so it cannot be decided here. But BOTH were repaired the same way, by adding
    an escape branch naming the negative outcome, and that shape is checkable.
    """
    prose = _NOT_A_QUANTIFIER.sub(" ", _ADDRESS.sub(" ", (done_when or "").lower()))
    risky = _words(prose, UNIVERSAL + THRESHOLD)
    if not risky or _words(prose, HYPOTHETICAL):
        return None
    return (f"done_when says {risky[0]!r} with no alternative branch. If the data cannot "
            f"reach it there is no way to close this honestly - state what to report when "
            f"it is NOT met (#75).")


#: Word 3-grams. Shingles rather than a bag of words because the signal is phrasing, not
#: vocabulary: every ticket in this queue talks about runs, criteria, judges and trials, so
#: unigram overlap between any two of them is high and discriminates nothing.
def _shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def brief(meta_or_fm) -> str:
    """The text a body is compared against: `title` + `done_when`, and nothing else.

    NOT the body, because comparing bodies to bodies is what a misfiling makes identical.
    NOT `established_by` either: it is written at `done` time and often quotes another
    task's mechanism at length, which would make every closed task look like its neighbour.
    Title and done_when are the two fields a ticket's own author wrote about this task and
    no other.
    """
    return f"{_scalar(meta_or_fm.get('title'))} {_scalar(meta_or_fm.get('done_when'))}"


#: How far another task's brief must beat this task's own before the body is called misfiled.
#:
#: MEASURED, NOT CHOSEN. Scored over every version of every task file git has ever tracked --
#: 3175 file-versions across 81 queue snapshots on 2026-08-23 -- the margin
#: `best_other - own` separates completely:
#:
#:   | margin | what it is |
#:   |--------|------------|
#:   | 0.3615 | tasks/70 carrying task 71's brief. THE defect, and the only true positive |
#:   | 0.1399 | the highest of the other 3174: task 62, whose subject really is task 70's |
#:   | 0.1333 | task 31 vs 26, next |
#:
#: 0.25 sits 1.45x below the true positive and 1.79x above the worst false positive. It is a
#: threshold with air on both sides of it rather than one fitted to a single point, and the
#: sweep that produced it is reproducible from git alone.
MISFILED_MARGIN = 0.25

#: A brief too short to accuse anyone with. Containment over a handful of 3-grams is noise --
#: `_task_file` in `tasks_control.py` builds briefs of four words, which is two shingles, and
#: two shingles will coincide with something eventually. 8 is roughly a ten-word brief.
MISFILED_MIN_BRIEF = 8


def misfiled_body(body: str, briefs: dict[str, str], own_id: str) -> str | None:
    """The message `check` should print for this body, or None. Pinned both ways by
    `eval/tools/tasks_control.py`; it is a module-level function so that it can be.

    WHY NOT "THE BODY NAMES ANOTHER TASK ID", WHICH IS HOW THE TICKET ASKED FOR IT.
    Because it is not implementable: **58 of the 85 live bodies name another task id**,
    measured before this was written. Tickets cite their neighbours constantly -- that is the
    queue working, not failing. And the defect itself would have walked straight through it:
    the 59 lines misfiled into task 70 never say "task 71" once. A check keyed on id mentions
    fires on 68% of the queue and misses the case it was filed for.

    What actually distinguishes a misfiled body is that it is ABOUT a different task, and the
    checkable shape of that is containment: what fraction of task X's brief does this body
    restate? The misfiled 59 lines restate 45.6% of task 71's title-and-done_when -- its
    closing section is task 71's done_when in other words -- against 9.4% of task 70's own.

    ITS LIMITS, and they are the reason this reports the target rather than just failing:

      * A body misfiled into a task whose brief is VAGUE scores low against it and passes.
      * A body misfiled between two tasks with SIMILAR briefs raises `own` too, shrinking the
        margin below the threshold. Adjacent tickets are exactly where a misfiling is most
        likely and least detectable.
      * A body that is simply off-topic, resembling no task in the queue, is invisible here.
        Only `body is empty` catches the degenerate case.

    None of those are hypothetical-in-principle; they are what a variant would exploit, and a
    mutant cannot manufacture them (AGENTS.md rule 15). The empty-body check has no such gap,
    which is why the two are separate failures and not one.
    """
    bg = _shingles(body)
    if not bg:
        return None                     # empty; `check` reports that separately and exactly

    def containment(tid: str) -> float:
        fp = _shingles(briefs.get(tid, ""))
        if len(fp) < MISFILED_MIN_BRIEF:
            return 0.0
        return len(bg & fp) / len(fp)

    own = containment(own_id)
    others = sorted(((containment(t), t) for t in briefs if t != own_id), reverse=True)
    if not others:
        return None
    best, target = others[0]
    if best - own < MISFILED_MARGIN:
        return None
    return (f"body restates task {target}'s title/done_when ({best:.0%}) far more than its "
            f"own ({own:.0%}) - this reads as task {target}'s brief filed under {own_id}. "
            f"Move it, or if it belongs here say so in the body (#94, AGENTS.md rule 12).")


def _scalar(v) -> str:
    """What every caller of `_parse` has always been handed: a string, never None.

    `refs:` with nothing after it loads as None and used to read as "", so it still does.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _parse(p: Path) -> dict:
    try:
        fm, body = _read_fm(p)
    except (_Malformed, OSError, UnicodeDecodeError) as exc:
        return {"id": p.stem.split("-")[0], "path": p, "malformed": str(exc)}
    meta: dict = {"path": p, "body": body.strip()}
    for k, v in fm.items():
        meta[str(k).strip()] = _scalar(v)
    # ONE place normalises the legacy vocabulary, and it is the reader. Every caller below --
    # `check`, `next`, `list`, the marks, the summary -- then compares against STATUSES only,
    # so none of them has to carry its own copy of the alias table. A second copy is how the
    # rename would half-land: `check` accepting `in_flight` while `next` never offers one.
    if "status" in meta:
        meta["status"] = _status(meta["status"])
    # The id is bare digits on disk, so YAML hands it back as an int for `01`-`07` (octal)
    # and `10`+ (decimal), and as a str only for `08`/`09`. `_id_text` is the single place
    # that turns any of those back into the padded string `show`, `start` and `done` match on
    # -- and the same one `_render` writes with, so a read never disagrees with a write.
    meta["id"] = _id_text(fm.get("id")) or p.stem.split("-")[0]
    return meta


def _load() -> list[dict]:
    if not TASKS.is_dir():
        return []
    return sorted((_parse(p) for p in TASKS.glob("*.md")),
                  key=lambda t: (int(t.get("priority", 9) or 9), t.get("id", "")))


#: One glyph per status, and every status has one. `.get(..., "[?]")` is the only branch that
#: can print `[?]`, and after `_parse` normalises the legacy names the only way to reach it is
#: a status `check` would already have failed -- which is the intent: an unknown state is
#: visible in the listing rather than rendered as `todo`.
MARKS = {"todo": "[ ]", "in_progress": "[~]", "in_review": "[r]",
         "in_testing": "[t]", "done": "[x]"}


def _line(t: dict) -> str:
    # NO DEFAULT. A file with no `status:` at all is rejected by `check` and skipped by `next`,
    # so rendering it as `todo` in the listing made the one view a person reads disagree with
    # both of the views a tool reads -- a fail-open display of a file nothing will pick up.
    mark = MARKS.get(t.get("status"), "[?]")
    return f"  {mark} {t.get('id','??')}  p{t.get('priority','?')}  {t.get('title','(no title)')}"


def cmd_list(status: str | None) -> int:
    ts = [t for t in _load() if not t.get("malformed")]
    status = _status(status) if status else None
    show = [t for t in ts if status is None or t.get("status") == status]
    if status is None:
        show = [t for t in ts if t.get("status") != "done"]
    for t in show:
        print(_line(t))
    # Counted from STATUSES rather than from three hand-written comprehensions, so a sixth
    # state cannot be added to the vocabulary and left out of the summary -- which is how a
    # task in a new state would vanish from the one line an orchestrator actually reads.
    n = {s: sum(1 for t in ts if t.get("status") == s) for s in STATUSES}
    n_open = n["todo"]
    print(f"\n{len(show)} shown; " + ", ".join(f"{n[s]} {s}" for s in STATUSES))
    if n_open < 3:
        print("Fewer than 3 open. Running out has never yet been true here — re-read "
              "eval/FINDINGS.md for anything filed and never acted on.")
    return 0


def cmd_show(tid: str) -> int:
    for t in _load():
        if t.get("id") == tid:
            print(f"{t.get('id')}  [{t.get('status') or 'MISSING'}]  "
                  f"priority {t.get('priority','?')}")
            print(f"{t.get('title','')}\n")
            if t.get("refs"):
                print(f"refs: {t['refs']}")
            # The pull request, when there is one. Printed next to `refs` because the whole
            # point of storing it is that the ticket and the PR are reachable from each other:
            # the orchestrator finds the PR from the ticket, and CodeRabbit reads the ticket
            # from the PR body.
            if t.get("pr"):
                print(f"pr: {t['pr']}")
            print(f"done when: {t.get('done_when','MISSING')}\n")
            print(t.get("body", ""))
            return 0
    print(f"no task {tid}", file=sys.stderr)
    return 1


def cmd_next() -> int:
    for t in _load():
        if t.get("status") == "todo":
            return cmd_show(t["id"])
    print("nothing open")
    return 0


def _set(tid: str, **kw) -> int:
    """Update keys in one task's frontmatter, through the YAML writer.

    It used to be `re.sub(rf"^{k}:.*$", f"{k}: {v}")`, which is why `done` was the single
    largest producer of unparseable files: an evidence sentence contains ": " and went in
    unquoted. Every write now goes out through `safe_dump`, so a value that needs quoting
    gets quoted whatever it contains.

    A key that is already present keeps its position; a new one is appended rather than
    inserted at the top, which is the only visible difference from the old writer and is
    cosmetic -- `show` reads by key.

    IT REWRITES THE WHOLE FILE TO CHANGE ONE FIELD, AND THAT COSTS NOTHING. MEASURED.
    ---------------------------------------------------------------------------------
    The obvious objection is that a whole-file write should smear `git blame` across every
    line and so blind `docstat.py --renumbered`, which reads a citation's authoring commit
    from blame. It does not, and the reason is the round-trip property above: `_render`
    reproduces every byte it did not mean to change, so git sees a one-line edit.

    Measured 2026-08-23 on a real 102-line task file, committed, then `start` and `done`
    through this function, each committed:

      | after      | git diff --numstat | unchanged lines whose blame MOVED |
      |------------|--------------------|-----------------------------------|
      | `start`    | 1 insertion, 1 deletion | 0                            |
      | `done`     | 2 insertions, 1 deletion | 0                           |

    100 of the 102 lines stayed on the authoring commit; only `status:` and
    `established_by:` moved, and those are the two lines the calls wrote. That is exactly
    the attribution a targeted write would produce, so a targeted write would restore no
    recall -- there is none to restore. Across the whole queue the same day, only 3 of 58
    tracked files had every line on one commit, and all 3 were `open` files never yet
    written twice.

    Where `--renumbered` really does go quiet on `tasks/` is its own documented case B: a
    merge that resolves a finding-number collision lands the renumbered heading and the
    closing task's `established_by` in ONE commit, and there is no ordering inside a
    commit. At `--at 1120695^` it reports 11 `tasks/` citations, every one in the
    undecided bucket with a resolved authoring commit beside it. That is a property of
    merge resolution, not of how this function writes.

    So do not convert this to a targeted line edit. It would buy nothing measurable and it
    would give up the one property that makes the YAML round-trip safe: that the bytes
    going out are the serialiser's, not a regex's guess at them.
    """
    for t in _load():
        if t.get("id") != tid:
            continue
        p: Path = t["path"]
        try:
            fm, body = _read_fm(p)
        except _Malformed as exc:
            print(f"{tid}: {p.name} is malformed ({exc}); refusing to write", file=sys.stderr)
            return 1
        fm.update(kw)
        p.write_text(_render(fm, body), encoding="utf-8")
        print(f"{tid}: " + ", ".join(f"{k}={v}" for k, v in kw.items()))
        return 0
    print(f"no task {tid}", file=sys.stderr)
    return 1


def _note_block(text: str, heading: str | None = None) -> str:
    """The EXACT bytes `note` appends, and the only place they are spelled.

    A module-level function so `tasks_control.py` can assert that the file afterwards is the
    file before it plus this and nothing else -- rule 12, one value at one address. Building
    the expected suffix a second time in the control would pin the control against itself.

    The leading newline is what separates the section from whatever the body ended with, and
    it is correct whether or not that body ended in one: a file ending `...text` gets the
    heading on its own line, a file ending `...text\\n` gets a blank line before it. The
    trailing newline is what makes the NEXT append idempotent in the same way.
    """
    head = (heading or f"note {time.strftime('%Y-%m-%d')}").strip()
    return f"\n## {head}\n\n{text.strip()}\n"


def _stdin_arg(value: str) -> str:
    """`-` means READ IT FROM STDIN, in every subcommand that takes a durable text argument.

    THE SENTINEL IS THE PROPERTY, NOT THE SUBCOMMAND. `note` grew `-` because #80 is about a
    backtick in argv being command substitution before this program ever runs; `done` and
    `testing` write a durable record from an argv string too and had no such reading, so
    `done 112 - < account.md` was accepted and stored the LITERAL one-character string `-`,
    exit 0, no warning, discarding the whole redirected account (task 120). Two sibling
    commands disagreeing about one sentinel is the enumeration failure `AGENTS.md`'s rule
    audit keeps recording: the safe path was added where the problem had been SEEN rather
    than where the property lives.

    Reading it here, once, is what makes `-` mean the same thing everywhere -- and what stops
    the next command that takes durable text from having to remember.

    It does NOT guard `sys.stdin.isatty()`. A `-` typed at a terminal blocks on a read, which
    is loud: the agent sees it and hits Ctrl-D. The failure this closes is the silent one.
    """
    return sys.stdin.read() if value == "-" else value


def cmd_note(tid: str, text: str, heading: str | None) -> int:
    """Append a section to one ticket's BODY in the shared queue. See the module docstring.

    An empty note is REFUSED rather than written. A heading with nothing under it is a write
    that looks like a record and is not one, and `note` is reached at exactly the moment an
    agent is trying to leave a durable statement -- the same moment `done ""` would be wrong.
    It is also the only way `-` can silently produce nothing, when stdin is a closed pipe.

    THE ONE RACE IT DOES NOT CLOSE, stated rather than guarded. `open(p, "a")` cannot lose a
    concurrent `note`, but `_set` is a read-modify-write of the whole file, so a `start` or
    `done` on the SAME ticket whose read happened before this append and whose write happens
    after it would drop the section. That needs two processes writing one task file at once,
    which the one-agent-per-task dispatch does not produce, and a lock here would be an
    untested guard against a race nothing has yet run. If it ever does happen, the fix is to
    put `cmd_add`'s existing common-dir lock around `_set` and this, not to make `note` clever.
    """
    text = _stdin_arg(text)
    if not text.strip():
        print(f"{tid}: refusing to append an empty note - a heading with nothing under it "
              f"is a write that looks like a record", file=sys.stderr)
        return 1
    for t in _load():
        if t.get("id") != tid:
            continue
        p: Path = t["path"]
        if t.get("malformed"):
            print(f"{tid}: {p.name} is malformed ({t['malformed']}); refusing to write",
                  file=sys.stderr)
            return 1
        block = _note_block(text, heading)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(block)
        # The ABSOLUTE path from a worktree, for `add`'s reason: it is the only output that
        # makes visible that the section went somewhere other than here.
        try:
            shown = p.relative_to(ROOT)
        except ValueError:
            shown = p
        print(f"appended {len(block)} bytes to {shown}: {block.splitlines()[1]}")
        return 0
    print(f"no task {tid}", file=sys.stderr)
    return 1


def cmd_evidence(tid: str, status: str, value: str) -> int:
    """`testing` and `done`: move the status AND write `established_by`, or write neither.

    `established_by` is the line every later reader trusts about what closed a task, and
    until 2026-08-23 it was whatever argv happened to contain. Three shapes went in silently,
    all at exit 0 with the status flipped (task 120, measured on a scratch queue against the
    pre-fix copy before this existed; the account redirected in was 2280 characters):

      | call                       | stored           | what the caller meant   |
      |----------------------------|------------------|-------------------------|
      | `done 70 - < account.md`   | `-`, 1 character | the whole account       |
      | `testing 70 - < the same`  | `-`, 1 character | the same                |
      | `done 70 ""`               | the empty string | nothing legitimate      |

    The real instance was `done 112 - < file`, which is what filed the ticket.

    THE FIRST ROW IS #80'S SHAPE WITH A SENTINEL INSTEAD OF A BACKTICK: a durable record is
    emptied, the command reports success, and the loss is visible only to whoever re-reads
    the ticket later. It fails OPEN, which rule 7 says is the expensive direction.

    So `-` now means here exactly what it means in `note` -- read it from stdin -- and the
    two refusals below are what keep that from being a fresh way to write a wall of prose
    into YAML frontmatter:

      * EMPTY is refused. `note` already refuses one; the same moment, the same reason.
      * MULTI-LINE is refused, naming `note`. `established_by` is one unbroken line of prose
        in frontmatter and is not where the next agent looks -- tasks 105 and 106 each
        emptied a session's findings into it, which is the whole reason `note` was built
        (task 113). Accepting a heredoc here would re-open that with a nicer syntax.

    `\\r` COUNTS AS A LINE BREAK, and testing for `\\n` alone did not see it. A lone carriage
    return is an old-Mac line ending, it carries a second line, and `strip()` removes it only
    at the ends. Raised by review on PR #6 (task 120) and pinned in `evidence_rows`.

    WHITESPACE AROUND THE EVIDENCE IS TRIMMED, NOT REFUSED, and that is deliberate: a heredoc
    always ends in a newline and a redirected file often ends in a blank line, so refusing
    those would make `-` unusable for the case it exists for. `strip()` can only ever remove
    whitespace, so nothing a caller wrote is lost to it -- the refusal above still fires on
    any line break that survives the trim, which is the case that matters.

    The net effect on the call that lost the record: `done <id> - < account.md` exits 1 and
    says where the account goes, instead of exiting 0 having stored one character.

    A ONE-LINE stdin string IS accepted, and that is the half `note` cannot cover: an
    evidence sentence containing a backtick cannot be passed as argv at all (#80), and this
    is the channel that carries one.
    """
    text = _stdin_arg(value).strip()
    if not text:
        print(f"{tid}: refusing to record an empty `established_by` - the field is what a "
              f"later reader trusts about what closed this task, and `{status}` with "
              f"nothing in it is a write that looks like a record", file=sys.stderr)
        return 1
    if "\n" in text or "\r" in text:
        n = 1 + text.count("\n") + text.count("\r") - text.count("\r\n")
        print(f"{tid}: `established_by` is one unbroken line of prose in YAML frontmatter "
              f"and this is {n} lines. Put the account in the ticket BODY with "
              f"`tasks.py note {tid} -`, then pass a one-line summary here.",
              file=sys.stderr)
        return 1
    return _set(tid, status=status, established_by=text)


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
        # Written through the serialiser, so a title or done-when containing ": " -- which is
        # how 7 of them were already written -- comes out quoted instead of unparseable.
        body = _render({"id": nid, "title": a.title, "status": "todo",
                        "priority": a.priority, "refs": a.refs or "",
                        "done_when": a.done_when},
                       f"\n{a.why or ''}\n")
        try:
            with open(TASKS / f"{nid}-{slug}.md", "x", encoding="utf-8") as fh:
                fh.write(body)
        except FileExistsError:
            nid_int += 1
            continue
        # THE QUEUE IS IN THE MAIN CHECKOUT, so from an agent worktree TASKS is not under
        # ROOT and `relative_to` raises -- AFTER the file has been written and before the
        # return, so `add` created the task and exited 1 with a traceback.
        #
        # An exit code that says "failed" over a completed write is the worst shape a
        # report can take: it invites a retry, and the retry files a SECOND task,
        # reintroducing through the status channel the duplicate this shared queue exists
        # to prevent. Rule 7 -- a failure signal that does not mean failure is a channel a
        # bug can widen.
        #
        # Printing the ABSOLUTE path from a worktree is deliberate, not a fallback: it is
        # the only output that makes visible that the file went somewhere other than here.
        created = TASKS / f"{nid}-{slug}.md"
        try:
            print(f"created {created.relative_to(ROOT)}")
        except ValueError:
            print(f"created {created}")
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
            bad.append(f"{t.get('id')}: status {t.get('status')!r} not in {STATUSES} "
                       f"(legacy {sorted(LEGACY_STATUSES)} are accepted and map on read)")
        # A ticket in either PR state with no `pr:` cannot be acted on. BOTH states exist so
        # the orchestrator can find the pull request from the ticket, and `in_testing` is the
        # one it actually merges from -- so leaving it out would gate the state that only
        # reports and not the state that acts. It is not untidiness: it is a status that has
        # stopped being a locator.
        #
        # `in_testing` is included even though an agent normally arrives through `review`,
        # because nothing enforces that order: `start` then `testing` is two commands, and it
        # produces a ticket the orchestrator is told to merge with nothing to merge from.
        if t.get("status") in PR_REQUIRED and not (t.get("pr") or "").strip():
            bad.append(f"{t.get('id')}: status {t.get('status')} with no `pr` - the state "
                       f"exists so the pull request is reachable from the ticket; set it "
                       f"with `review`")
        if not t.get("title"):
            bad.append(f"{t.get('id')}: no title")
    # THE BODY IS ITS OWN TICKET. Both halves of commit 436bf64, which `check` read as clean.
    #
    # These run on `done` tasks too, unlike the reachability warning below. That exemption is
    # documented there as having cost something -- it is why task 32's false positive was
    # invisible until task 38 was filed -- and there is no reason to buy it again here: the
    # 3175-version sweep behind `MISFILED_MARGIN` found zero false positives at ANY status,
    # so skipping the archive would remove coverage and prevent nothing.
    live = [t for t in _load() if not t.get("malformed")]
    briefs = {str(t.get("id")): brief(t) for t in live}
    for t in live:
        tid = str(t.get("id"))
        if not (t.get("body") or "").strip():
            bad.append(f"{tid}: body is empty - `add` writes a stub and the stub is not the "
                       f"task. An agent dispatched to this reads a ticket with no brief")
            continue
        msg = misfiled_body(t.get("body") or "", briefs, tid)
        if msg:
            bad.append(f"{tid}: {msg}")
    # UNREACHABLE done-whens. The reasoning lives on `reachability_warning`, which is a
    # module-level function so `tasks_control.py` can pin it on wordings that are not in
    # the queue -- the two ORIGINALS it was built from are not in git, having been repaired
    # before the first commit, and a heuristic pinned only on what happens to be on disk
    # today is pinned on a moving corpus.
    #
    # A WARNING, not a failure: plenty of universals are perfectly reachable. It prints
    # from a command run on purpose, which is the difference between this and the
    # unread manifest field of #62.
    warn = []
    for t in _load():
        # `done` is skipped because a closed task's wording is not actionable -- and note
        # what that costs: it is why task 32's false positive was invisible to `check` by
        # the time task 38 was filed to fix it. A masked defect is not a fixed one.
        if t.get("status") == "done":
            continue
        msg = reachability_warning(t.get("done_when") or "")
        if msg:
            warn.append(f"{t.get('id')}: {msg}")
    if warn:
        print(f"{len(warn)} reachability warning(s):")
        for w in warn:
            print(f"  {w}")
        print()

    # A `done` TICKET WHOSE BRANCH HAS NOT REACHED `main`. See `landed_status` for what
    # the three values mean and what this cannot see. Measured on the live queue of 121
    # tickets before it shipped: 119 `done`, of which 6 LANDED, 1 ORPHANED -- task 70, the
    # true positive that caused this check to be written -- and 112 NOT_CHECKED. **0 false
    # positives.** The counts are printed rather than remembered: the population moves
    # every time a branch is deleted AND every time a peer closes a ticket in the shared
    # queue -- it was 120 done / 8 LANDED within the hour, before this had merged.
    #
    # THAT 0 DID NOT SURVIVE THE MERGE FLOW CHANGING. Once the repository became squash-only,
    # ancestry alone accused every merged ticket whose ref outlived the merge -- tasks 130,
    # 131 and 133, measured 2026-08-24 -- which is why `_is_landed` asks a second question.
    refs = _all_refs()
    bases = _resolved_bases()
    if not bases:
        refs = None                      # nothing to compare against is NOT CHECKED, not a pass
    landed = notchecked = 0
    pid_cache: dict = {}          # one per invocation; see `_base_patch_ids`
    for t in _load():
        if t.get("status") != "done":
            continue
        verdict, cand = landed_status(str(t.get("id")), refs,
                                      lambda r: _is_landed(r, bases, pid_cache))
        if verdict == "LANDED":
            landed += 1
        elif verdict == "NOT_CHECKED":
            notchecked += 1
        else:
            bad.append(f"{t.get('id')}: status done, but {', '.join(cand)} has not "
                       f"landed on main - neither an ancestor of it nor a change already "
                       f"on it. The queue says this work is merged and the tree has never "
                       f"seen it. Read the branch diff before believing either side")
    print(f"branches of `done` tickets: {landed} reachable from "
          f"{' / '.join(lbl for lbl, _ in bases) or '-'}, "
          f"{notchecked} NOT CHECKED (no `task-<id>-*` ref survives - not a pass)"
          + ("" if refs is not None else " [git unavailable: nothing was checked]"))
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
    # THE TWO MIDDLE TRANSITIONS. `review` takes the pull request because the state is
    # useless without it, and `testing` takes evidence for the same reason `done` does: it is
    # the agent's statement of what established the result, and it is what the orchestrator
    # verifies against the artifacts before merging. Storing it at `testing` rather than at
    # `done` puts it in the file at the moment the agent still has the measurement in hand.
    s = sub.add_parser("review"); s.add_argument("id"); s.add_argument("pr")
    # ONE SENTINEL, SPELLED ONCE. Both evidence arguments take `-` the way `note` does, and
    # both go through `cmd_evidence`, which is where the empty and multi-line refusals live.
    # A `-` that means "read stdin" in one sibling and a literal one-character record in
    # another is how task 120's 2280-character account became 1 character at exit 0.
    _EV_HELP = ("what established the result, in ONE line; `-` reads it from stdin, which is "
                "the only safe way to pass a backtick (#80). A multi-line account belongs in "
                "the ticket body: `tasks.py note <id> -`")
    s = sub.add_parser("testing"); s.add_argument("id")
    s.add_argument("evidence", help=_EV_HELP)
    s = sub.add_parser("done"); s.add_argument("id")
    s.add_argument("evidence", help=_EV_HELP)
    # `note` is how a dispatched agent obeys `.agents/skills/work/SKILL.md`. `-` is not a
    # convenience: an argv string containing a backtick is command substitution before this
    # program runs (#80), and stdin is the channel that carries one verbatim.
    s = sub.add_parser("note"); s.add_argument("id")
    s.add_argument("text", help="the section text; `-` reads it from stdin, which is the "
                                "only safe way to pass backticks or newlines (#80)")
    s.add_argument("--heading", help="the section heading; default `note <today>`")
    # Legacy names are accepted here too, so a habit or an old script does not fail at the
    # command line for a value the reader would have mapped anyway.
    s = sub.add_parser("list")
    s.add_argument("--status", choices=STATUSES + tuple(LEGACY_STATUSES))
    s = sub.add_parser("add")
    # `--why` is REQUIRED because it is what `add` writes into the body, and `check` now fails
    # on an empty body. A tool that creates a file its own lint rejects is a fail-open channel
    # (AGENTS.md rule 7): the failure arrives later, at whoever runs the gate next, rather than
    # at the person who can still fix it in one line.
    s.add_argument("title"); s.add_argument("--why", required=True)
    s.add_argument("--done-when", required=True)
    # `type=int` so a bad priority fails at the command line rather than as a ValueError from
    # the sort key of the next `_load`, and so it is written as a YAML integer, not a string.
    s.add_argument("--refs"); s.add_argument("--priority", type=int, default=3)
    sub.add_parser("check")
    a = ap.parse_args()

    if a.cmd == "next":
        return cmd_next()
    if a.cmd == "show":
        return cmd_show(a.id)
    if a.cmd == "start":
        return _set(a.id, status="in_progress")
    if a.cmd == "review":
        return _set(a.id, status="in_review", pr=a.pr)
    if a.cmd == "testing":
        return cmd_evidence(a.id, "in_testing", a.evidence)
    if a.cmd == "done":
        return cmd_evidence(a.id, "done", a.evidence)
    if a.cmd == "note":
        return cmd_note(a.id, a.text, a.heading)
    if a.cmd == "add":
        return cmd_add(a)
    if a.cmd == "check":
        return cmd_check()
    return cmd_list(getattr(a, "status", None))


if __name__ == "__main__":
    sys.exit(main())
