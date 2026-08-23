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

IT ALSO FAILS WHEN A TICKET IS NOT ITS OWN TICKET
-------------------------------------------------
The frontmatter of a task file was gated from the start; its BODY was not, and the body is the
only part an agent is actually briefed from. On 2026-08-23 commit `436bf64` appended task 71's
entire 59-line brief to `tasks/70-set-a-size-...md` -- a filename guessed from a queue listing
title, which is AGENTS.md rule 12 -- and created `tasks/71-...md` with no body at all. `check`
exited 0 on both files for a day, while task 71's agent worked from an empty ticket and
`show 70` rendered a brief about trial disclosures.

So two failures, and they are the two halves of that one commit:

  * `body is empty` -- the stub `add` writes is not the task. Exact, no heuristic.
  * `body reads as task N's brief` -- `misfiled_body` below.

See `misfiled_body` for the measurement behind the threshold and for what it cannot catch.

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
STATUSES = ("open", "in_flight", "done")

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
        body = _render({"id": nid, "title": a.title, "status": "open",
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
            bad.append(f"{t.get('id')}: status {t.get('status')!r} not in {STATUSES}")
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
