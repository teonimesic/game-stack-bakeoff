#!/usr/bin/env python3
"""The mutants of `tasks.py` that `tasks_control.py`'s rows are supposed to catch.

WHY THIS EXISTS. Task 82 built direction 5 of `tasks_control.py` and killed five mutants
with it -- by hand, in one session. What it left behind was a SENTENCE in a closed ticket's
`established_by` field saying they had died. Nothing in the repository could run one, so
from the moment that session ended the claim "these rows can go red" was unfalsifiable, and
the rows could be weakened, or the mechanisms they name deleted, with `tasks_control.py`
still printing `28 measurements, 0 FAILED`. AGENTS.md rule 15 says both halves run in
`judge/bot_mutants.py` BECAUSE a discipline you have to remember is one that will fail;
this is the same shape one directory over (#132: a claim that survived every grep because
it was a comment rather than a reader).

WHAT IT DOES. For each mutant: copy `tasks.py` into a tempdir, apply ONE replacement to the
COPY, run the real `tasks_control.py` against it via `--tasks-py`, and read which rows went
red. A mutant is CAUGHT only if the row NAMING ITS MECHANISM is among them -- not merely if
something, somewhere, failed. A control that is red for a reason it did not name is not
controlling that reason (`findings_control.py` learned this with three surviving mutants).

    python3 eval/tools/tasks_mutants.py                 # baseline, then every mutant
    python3 eval/tools/tasks_mutants.py --mutate NAME   # one
    python3 eval/tools/tasks_mutants.py --list

THE COPY IS THE POINT, and it is #134's constraint: the first version of the equivalent
file for `docstat.py` patched the repository's own tool in place and told the operator to
`git checkout` afterwards. That instruction was followed and it discarded an hour of
uncommitted work. Nothing here writes to `eval/tools/tasks.py`, and the run is a no-op on
the shared queue -- `<tmp>/tasks` is a SYMLINK to it so that direction 1 and the task-32 pin
still have a corpus, and every row that touches it only reads.

THE BASELINE RUNS FIRST AND IS NOT DECORATION. It grades an UNMUTATED copy through the same
tempdir, the same symlink and the same `--tasks-py` path, and it must be green. Without it,
a red row under a mutant is equally well explained by the harness: this is the variant half
(AGENTS.md rule 15) applied to the mutant runner itself. It also pins the row NAMES, which
are what every `kills` entry below is matched against.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tasks.py"
CONTROL = HERE / "tasks_control.py"

# The queue address is IMPORTED from the subject, not re-derived here. Two `parents[n]`
# expressions that differ by one is exactly how rule 12 gets paid for a second time.
sys.path.insert(0, str(HERE))
import tasks as _t  # noqa: E402

QUEUE = _t.TASKS

#: name -> (anchor, replacement, rows that MUST go red).
#:
#: Each `kills` entry is a substring of a row name printed by `tasks_control.py`. The
#: baseline run asserts every one of them exists, so a row renamed or deleted out from under
#: a mutant is a failure here rather than a silent pass -- the failure mode this whole file
#: is about.
#:
#: The counts in the comments are what task 82 recorded by hand on 2026-08-23 and what this
#: file measures now. Where they differ, the measurement is in the ticket.
MUTANTS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    # The half that actually hurt. `check` read commit 436bf64 as clean for 25m48s (#141) while
    # task 71's agent worked from a body of "\n\n"; containment cannot see an empty body,
    # because an empty body resembles nothing.
    "no_empty_body": (
        '        if not (t.get("body") or "").strip():',
        '        if False:  # MUTANT: the empty-body branch is gone',
        ("`check` on empty body", "FAILS on the real 436bf64 pair")),
    # The threshold, upper side: raise it past the one true positive the corpus contains and
    # the defect walks through. 0.50 is above 0.3615.
    "margin_up": (
        "MISFILED_MARGIN = 0.25",
        "MISFILED_MARGIN = 0.50  # MUTANT: above the 0.3615 true positive",
        ("FAILS on the real 436bf64 pair", "threshold, upper side")),
    # The threshold, lower side, and the only mutant here that is a VARIANT in disguise: it
    # asks whether the check can still stay QUIET. 0.13 is below the worst real non-defect
    # at 0.1399, so task 62 -- correctly filed, genuinely about task 70's subject -- gets
    # accused. A repair that "fixes" a miss by lowering the threshold dies on this row.
    "margin_down": (
        "MISFILED_MARGIN = 0.25",
        "MISFILED_MARGIN = 0.13  # MUTANT: below the 0.1399 worst false positive",
        ("threshold, lower side",)),
    # The floor under how short a brief may be before it can accuse anyone. Its row survived
    # this mutant on the first attempt in task 82, because the row's premise was vacuous --
    # see the comment on 5d in tasks_control.py. It is the reason that row now asserts its
    # own precondition, and the reason this mutant is worth keeping rather than assuming.
    "min_brief_zero": (
        "MISFILED_MIN_BRIEF = 8",
        "MISFILED_MIN_BRIEF = 0  # MUTANT: two coincident shingles may now accuse",
        ("MISFILED_MIN_BRIEF",)),
    # What a body is compared AGAINST. Comparing bodies to bodies is precisely what a
    # misfiling makes identical, so this is the change that would make the check agree with
    # the defect. `brief` is a module-level function so this mutant can exist.
    "brief_reads_body": (
        "    return f\"{_scalar(meta_or_fm.get('title'))} "
        "{_scalar(meta_or_fm.get('done_when'))}\"",
        "    return _scalar(meta_or_fm.get('body'))  # MUTANT: body, not title+done_when",
        ("FAILS on the real 436bf64 pair", "threshold, upper side")),
    # The REPORTING of the reachability warning, as distinct from the predicate behind it.
    # This mutation was this file's own inert mutation until `tasks/106`: direction 4 called
    # `reachability_warning` in process over 12 wordings and no row ran `check` end to end,
    # so `tasks.py` computed every warning, printed none, and the 34 rows that file then had
    # all stayed green -- exit 0, 0 FAILED. It
    # is a real mutant now because direction 4c reads `check`'s stdout on a scratch queue.
    "warn_never_printed": (
        "    if warn:",
        "    if False:  # MUTANT: warnings computed, never printed",
        ("end to end on an UNREACHABLE done_when",)),
    # The other half of direction 4c: its QUIET rows must be able to go red too, or they are
    # a negative control that cannot fail. Dropping the escape class accuses every done_when
    # that carries a universal, which is what task 38 was filed about -- so the row that must
    # notice is the one whose wording has both a universal and an escape (task 32's).
    # `note`'s CENTRAL mechanism: it appends and never rewrites. Under `"w"` the section is
    # still there and still says the right thing -- the ticket it was appended to is gone.
    # That is the shape a values-only assertion cannot see, which is why the row it kills is
    # the BYTE one and not the frontmatter-values row beside it.
    "note_truncates": (
        '        with open(p, "a", encoding="utf-8") as fh:',
        '        with open(p, "w", encoding="utf-8") as fh:  # MUTANT: rewrite, not append',
        ("byte-identical plus exactly the section", "second `note` stacks",
         "DOES end in a newline")),
    # The separator. Without the leading newline the heading runs onto whatever the body
    # ended with, so on a body with no trailing newline the section is not a section at all.
    # Both round-trip rows must notice, which is what makes them two rows and not one.
    "note_no_separator": (
        '    return f"\\n## {head}\\n\\n{text.strip()}\\n"',
        '    return f"## {head}\\n\\n{text.strip()}\\n"  # MUTANT: no leading separator',
        ("byte-identical plus exactly the section", "default heading is",
         "DOES end in a newline")),
    # The refusal. An empty note writes a dated heading with nothing under it -- a record
    # that looks like one and is not, which is exactly what `check`'s empty-body branch
    # exists to catch one level up.
    "note_empty_allowed": (
        "    if not text.strip():",
        "    if False:  # MUTANT: an empty note is written as a bare heading",
        ("refuses an empty note",)),
    # THE ADDRESS (AGENTS.md rule 12). `note` resolves the file through `_load`, which
    # resolves the queue to the MAIN checkout; pointed at the worktree's own root instead it
    # writes nowhere, and the ticket an agent thought it had annotated is untouched. This is
    # the mutant for the property that only exists where `TASKS` and `ROOT` disagree.
    "note_writes_worktree": (
        "        block = _note_block(text, heading)\n"
        '        with open(p, "a", encoding="utf-8") as fh:',
        "        block = _note_block(text, heading)\n"
        '        p = ROOT / "tasks" / p.name  # MUTANT: the worktree copy, not the queue\n'
        '        with open(p, "a", encoding="utf-8") as fh:',
        ("`note` from a worktree exits 0", "wrote into the MAIN checkout's queue",
         "byte-identical plus exactly the section")),
    # THE ADDRESS, `add` HALF (AGENTS.md rule 12; `note_writes_worktree` above is the
    # `note` half). Pointed at the worktree's own root, the ticket lands where no
    # orchestrator looks and the queue being filed into never sees it. In the scratch
    # pair the worktree has NO tasks/ directory, so the write dies with a traceback --
    # exit 1 over a queue that received nothing -- and BOTH current-copy rows must
    # notice: the one asserting exit 0 with exactly one created file, and the one
    # asserting the MAIN queue is what grew. Found by cleanup pass 38: direction 2's
    # `add` path had no mutant at all.
    "add_writes_worktree": (
        '        with open(TASKS / f"{nid}-{slug}.md", "x", encoding="utf-8") as fh:',
        '        with open(ROOT / "tasks" / f"{nid}-{slug}.md", "x", '
        'encoding="utf-8") as fh:  # MUTANT: the worktree copy, not the queue',
        ("`add` from a worktree exits 0 and prints the created path",
         "`add` wrote into the MAIN checkout's queue, not the worktree's")),
    # THE RETRY THAT FILES A SECOND TASK (#94). The repair makes `add` print the
    # ABSOLUTE path from a worktree instead of exiting 1 over a completed write; the
    # defect that repair closes is the SECOND write a misled retry makes. Restored here
    # as a second file at exit 0 -- the one mutation direction 2's current-copy row
    # exists to catch, and its only killer: the positive control runs the PRE-FIX blob,
    # which no mutation of the current copy can reach. Its first proof was a hand-built
    # mutant in one session (cleanup pass 37); this entry is what keeps the claim from
    # decaying back to a sentence, which is this file's whole reason to exist.
    "add_double_create": (
        '        created = TASKS / f"{nid}-{slug}.md"\n        try:',
        '        created = TASKS / f"{nid}-{slug}.md"\n'
        '        with open(TASKS / f"{nid}-{slug}-2.md", "x", encoding="utf-8") as fh:\n'
        '            fh.write(body)  # MUTANT: the retry files a SECOND task, at exit 0\n'
        "        try:",
        ("`add` from a worktree exits 0 and prints the created path",)),
    "escape_ignored": (
        "    if not risky or _words(prose, HYPOTHETICAL):",
        "    if not risky:  # MUTANT: an escape branch no longer silences anything",
        ("end to end on a universal WITH an escape branch",)),
    # THE LINE-VERSUS-PARSE CHECK (tasks/216), deleted. The no-op shape: `check` reads the
    # file, compares nothing, and the queue that says "all well-formed" over a truncated
    # title is exactly the 25-day state this check exists to end. Both red rows must
    # notice -- the title blob and the done_when citation -- or the check only guards the
    # field it happened to be filed from.
    "lossy_never_checked": (
        '            lost = lossy_scalar_fields(t["path"].read_text(encoding="utf-8"), t)',
        "            lost = []  # MUTANT: the line-versus-parse check never runs",
        ("`check` on a queue holding the real pre-repair 214 title",
         "`check` on an unquoted done_when truncated at its")),
    # THE TRIGGER THE TICKET RULED OUT, RESTORED. `if " #" in line` is the character
    # vocabulary: it cannot tell a hash that starts a comment from one the quotes protect,
    # so it reddens the REPAIRED 214 title and every quoted value that legitimately
    # carries " #", while agreeing with the real check on every unquoted loss. The green
    # rows are what kill it -- the variant half (AGENTS.md rule 15): a mutant that only
    # ever made red rows redder would be untestable without them.
    "lossy_by_vocabulary": (
        "        if value != carrier and carrier.startswith(value):",
        '        if " #" in line:  # MUTANT: the character vocabulary the ticket ruled out',
        ("the four hash-following-non-whitespace lines and the repaired 214 title",
         "quiet on a quoted value whose ` #` the quotes protect")),
    # THE TORN-WRITE ARM, REMOVED. A peer rewriting a shared ticket between `_load` and
    # `check`'s re-read makes the SECOND `yaml.safe_load` inside `lossy_scalar_fields`
    # fail; the handler turns that into a NAMED failure with exit 1. Delete the handler
    # and the raise escapes as a traceback -- which ALSO exits 1, so only the row that
    # reads the report (named entry present, traceback absent) can tell the check died
    # from the check failing (review round 2, task 216).
    "lossy_swallows_parse_error": (
        "        except (yaml.YAMLError, ValueError) as exc:",
        "        except () as exc:  # MUTANT: the torn-write raise escapes as a traceback",
        ("`check` on a frontmatter that fails its second parse (injected raise) exits 1 "
         "NAMING the ticket, not a traceback",)),
    # THE PRE-217 WRITER, RESTORED. `raw` accepted and ignored is exactly what shipped when
    # cd4994d hand-quoted tasks/216: every line re-canonicalised, the quoted title emitted
    # plain, and the byte round trip red on every open pull request at once. The live queue
    # is canonical today, so direction 1 stays green under this mutant -- only the rows
    # pinned to the blob that broke can see it. That is why direction 13 pins a fixture and
    # does not trust the queue's current shape (tasks/217).
    "render_discards_raw": (
        "    if raw:\n"
        "        text = _restore_lines(text, raw, out)",
        "    if False:  # MUTANT: every line re-rendered canonically, as before tasks/217\n"
        "        text = _restore_lines(text, raw, out)",
        ("re-emits a scalar the file holds quoted", "ONLY the status line")),
    # THE GUARD DELETED -- the fail-open half of the same mechanism. `_restore_lines`
    # restores a raw line only when it parses to the value NOW BEING WRITTEN; without that
    # test a `_set` status change restores the OLD line over the new value, at exit 0, with
    # `status=in_progress` printed. The rows that catch it are the one-line-diff row and
    # the variant asserting the write happened -- and the second is what separates "the
    # write was reverted" from "the write was noisy" (AGENTS.md rule 7: a reason not to
    # count a failure is a channel a bug can widen).
    "render_ignores_value_changes": (
        "            if yaml.safe_load(original) != {key: fm.get(key)}:\n"
        "                continue",
        "            if False:  # MUTANT: a changed value's old line is restored over it\n"
        "                continue",
        ("ONLY the status line", "status line DID change")),
    # ONE CANONICAL SCALAR RE-QUOTED, and the gate that owns byte changes catches it: the
    # id is emitted quoted on every file, so direction 1's live round trip goes red naming
    # every queue file while the VALUE row beside it stays green. This is the other
    # direction of the cd4994d defect -- not a quoting style the writer cannot reproduce,
    # but the writer imposing a quoting style the file did not hold (tasks/217's done_when
    # clause: caught by whichever gate owns the change).
    "id_requoted": (
        "    return dumper.represent_scalar("
        "dumper.resolve(yaml.ScalarNode, text, (True, False)), text)",
        "    return dumper.represent_scalar(\"tag:yaml.org,2002:str\", text, style=\"'\")"
        "  # MUTANT: one canonical scalar re-quoted on every file",
        ("round trip: all",)),
    # THE STATUS VOCABULARY. Dropping a value is the shape a half-landed rename takes, and it
    # is invisible to every row that only asks whether a WRONG status fails: `wip` is still
    # rejected with 4 values, or with 1. Two rows must notice -- the one that puts a file in
    # each state, and the one asserting heartbeat's map equals STATUSES.
    "status_dropped": (
        'STATUSES = ("todo", "in_progress", "in_review", "in_testing", "done")',
        'STATUSES = ("todo", "in_progress", "in_testing", "done")  # MUTANT: in_review gone',
        ("every one of the 5 statuses", "covers EXACTLY")),
    # THE LEGACY ALIASES, and this one is a VARIANT rather than a mutant (AGENTS.md rule 15):
    # it does not remove a mechanism a row names, it feeds the queue an input the check must
    # still stay QUIET on. Losing it turns every peer's `check` red on a file written by an
    # agent whose worktree forked before 2026-08-23.
    "legacy_dropped": (
        'LEGACY_STATUSES = {"open": "todo", "in_flight": "in_progress"}',
        "LEGACY_STATUSES = {}  # MUTANT: a stale worktree's `in_flight` now fails the lint",
        ("legacy `open` and `in_flight` still lint clean",
         "maps the legacy names onto the canonical states")),
    # A TRANSITION WIRED TO THE WRONG CONSTANT. `check` cannot see this: the queue lints clean
    # either way and reports a state nobody chose. Only direction 7, which reads the file back
    # after running the command, can.
    "start_writes_todo": (
        '        return _set(a.id, status="in_progress")',
        '        return _set(a.id, status="todo")  # MUTANT: `start` claims nobody has it',
        ("`start` writes status in_progress",)),
    # The pull-request locator. Without it a ticket can reach the state the orchestrator
    # merges from while naming nothing to merge.
    "review_needs_no_pr": (
        '        if t.get("status") in PR_REQUIRED and not (t.get("pr") or "").strip():',
        "        if False:  # MUTANT: neither PR state has to name its pull request",
        ("`in_review` with no `pr`", "`in_testing` with no `pr`")),
    # NARROWING the requirement back to `in_review` alone. A mutant that deletes the branch is
    # not the interesting failure here -- shipping the branch and gating only the state that
    # REPORTS, not the state that ACTS, is, and it is what the first version of this did.
    "pr_required_review_only": (
        'PR_REQUIRED = ("in_review", "in_testing")',
        'PR_REQUIRED = ("in_review",)  # MUTANT: the state merged FROM is no longer gated',
        ("`in_testing` with no `pr`",)),
    # THE SENTINEL ITSELF -- and it is exactly the pre-fix behaviour of `done`, restored for
    # `note` as well. `-` stops meaning stdin and becomes a literal one-character record, at
    # exit 0, over however many characters the caller redirected in (task 120). It is one
    # mutation because `-` is now read in ONE place; before, it was two behaviours in two
    # commands, which is what let them disagree.
    "evidence_no_stdin": (
        '    return sys.stdin.read() if value == "-" else value',
        "    return value  # MUTANT: `-` is a literal again, in every subcommand",
        ("`done 70 -` on a 2280-character multi-line account",
         "`done 70 -` stores a ONE-LINE stdin string",
         "carries a backtick that argv cannot",
         "means stdin in `note` too")),
    # THE EMPTY REFUSAL. `done <id> ""` closed a ticket with an empty `established_by` at
    # exit 0 -- a status change whose stated reason is nothing at all.
    "evidence_empty_allowed": (
        "    if not text:\n"
        '        print(f"{tid}: refusing to record an empty `established_by`',
        "    if False:  # MUTANT: an empty evidence string closes the ticket\n"
        '        print(f"{tid}: refusing to record an empty `established_by`',
        ("(empty inline)", "(whitespace inline)", "with a closed/empty stdin")),
    # THE MULTI-LINE REFUSAL, which is what turns the redirected account from a silent
    # 1-character record into an error that names `note`. Without it the account goes into
    # YAML frontmatter instead -- tasks 105 and 106's workaround, with nicer syntax.
    "evidence_multiline_allowed": (
        '    if "\\n" in text or "\\r" in text:',
        "    if False:  # MUTANT: a whole account goes into the frontmatter line",
        ("`done 70 -` on a 2280-character multi-line account",
         "`testing 70 -` on the same account",
         "names the alternative")),
    # THE `\r` HALF ON ITS OWN. Testing for `\n` alone is what the first version did, and it
    # is invisible to every account fixture here because they all use `\n`: a lone carriage
    # return is an old-Mac line break carrying a second line straight into the frontmatter.
    # Raised by review on PR #6, so the row it kills is the one added for it.
    "evidence_cr_ignored": (
        '    if "\\n" in text or "\\r" in text:',
        '    if "\\n" in text:  # MUTANT: a lone CR is not a line break',
        ("a lone CR carries a second line",)),
    # THE SECOND HALF OF EVERY REFUSAL ROW, isolated. Exit 1 is not the claim: the claim is
    # exit 1 AND the ticket untouched. The pre-fix code moved the ticket to `done` while
    # destroying the record, so a refusal that still flips the status would leave the
    # orchestrator a closed task with no reason on it and a non-zero exit nobody kept.
    "evidence_refusal_still_writes": (
        "    text = _stdin_arg(value).strip()\n"
        "    if not text:",
        "    text = _stdin_arg(value).strip()\n"
        "    _set(tid, status=status, established_by=text)  # MUTANT: written, then refused\n"
        "    if not text:",
        ("`done 70 -` on a 2280-character multi-line account",
         "`testing 70 -` on the same account",
         "(empty inline)", "(whitespace inline)", "with a closed/empty stdin")),
    # THE ORPHANED-BRANCH GATE, and the failure it is against is a two-valued version of it:
    # a `done` ticket whose branch is gone would read as verified. Under this mutant the one
    # ORPHANED ticket in direction 11's fixture reads NOT_CHECKED and `check` exits 0.
    "orphan_reads_as_not_checked": (
        '    return "ORPHANED", cand',
        '    return "NOT_CHECKED", cand  # MUTANT: an orphan is excused, not reported',
        ("a surviving branch that is NOT an ancestor is ORPHANED",
         "a remote-only branch that is not an ancestor is ORPHANED",
         "VARIANT: a genuine False is still ORPHANED",
         "end to end: exit 1, naming 71 and NOT 70")),
    # THE VARIANT HALF. Reporting every closed ticket with no surviving branch as a failure
    # would fire on 112 of this repository's 119 and be turned off the same day -- so the
    # rows that must stay QUIET have to be able to go red as well (AGENTS.md rule 15).
    "missing_branch_fails": (
        '    if not cand:\n'
        '        return "NOT_CHECKED", []',
        '    if not cand:\n'
        '        return "ORPHANED", []  # MUTANT: a deleted branch is now an accusation',
        ("no branch at all is NOT_CHECKED",
         "VARIANT: id 7 does NOT claim task-70-*'s branch",
         "VARIANT: id 70 does NOT claim task-7-*'s branch",
         "VARIANT: with the branch deleted the same queue is NOT CHECKED, exit 0")),
    # THE REPORTING, as distinct from the predicate -- the `if False:` lesson of `tasks/106`
    # applied before it can be paid for a second time. `check` still computes every verdict
    # and appends every failure; it just stops printing the census, so a reader can no longer
    # tell 112 NOT CHECKED from 112 verified.
    "landed_census_never_printed": (
        '    print(f"branches of `done` tickets: {landed} reachable from',
        '    _unused = (f"branches of `done` tickets: {landed} reachable from',
        ("PRINTS the three-valued census",
         "bases coinciding are named ONCE",
         "VARIANT: with the branch deleted the same queue is NOT CHECKED, exit 0")),
    # DE-DUPLICATING THE BASES BY NAME INSTEAD OF BY SHA, which is what the first version did:
    # `HEAD` asked at the queue's address IS `main`, so the census line named two bases where
    # there was one and read as corroboration (AGENTS.md rule 9). The names still resolve, so
    # every verdict is unchanged and only the reporting is wrong -- the shape that survives
    # anything not reading the line.
    "bases_deduped_by_name": (
        "            add(b, r.stdout.strip())",
        "            add(b, b)  # MUTANT: the label stands in for the sha",
        ("bases coinciding are named ONCE",)),
    # A GIT ERROR READ AS "NOT AN ANCESTOR". `merge-base --is-ancestor` reserves 0 and 1
    # for the answer and everything else for a failure; collapsing the two makes `check`
    # exit 1 naming a ticket whose ancestry it never established (rule 2). Found in
    # review of task 122.
    "git_error_is_not_ancestor": (
        "        if rc != 1:\n            unknown = True",
        "        # MUTANT: any non-zero exit now reads as a clean 'no'\n"
        "        if False:\n            unknown = True",
        ("_is_ancestor returns None (not False) when git cannot answer",)),
    # THE CALLER'S HEAD ASKED ONLY AT THE FILE'S ADDRESS. This is what shipped first:
    # `ROOT` comes from `__file__`, so an agent running the MAIN copy of the tool -- what
    # the work skill recommends -- never has its own branch consulted, and the orphan it
    # has just landed stays red with no way to clear it from the branch that fixed it.
    "caller_head_only_at_file": (
        '    return [("this checkout\'s HEAD", _head_at(Path.cwd())),\n'
        '            (f"HEAD of {ROOT.name}", _head_at(ROOT))]',
        '    return [(f"HEAD of {ROOT.name}", _head_at(ROOT))]  # MUTANT: cwd ignored',
        ("the caller's cwd HEAD is a base",)),
    # A BASE FROM ANOTHER REPOSITORY. Dropping the existence check lets a SHA that is not
    # an object here become a base, and then EVERY `merge-base` exits 128 -- which the
    # three-valued reader turns into NOT_CHECKED for every ticket. The gate goes silent
    # and total, and reads as a clean queue.
    # THE SQUASH ARM NEVER ASKED, which is what shipped and is task 140: ancestry alone is
    # the right test for `merge --no-ff` and the wrong one for `merge --squash`, where the
    # tip is not an ancestor of it. Under this mutant every merged ticket whose ref survives
    # reads ORPHANED -- fail-closed, one new red row per merge, and a gate bypassed as habit.
    #
    # ONLY THE CONSUMER ROWS CAN SEE IT. `_squash_landed` is untouched, so the row calling it
    # directly stays green; naming that row here left this mutant reported as SURVIVING, which
    # is the harness refusing a `kills` entry the mutant cannot reach.
    "squash_arm_never_asked": (
        "    sq = _squash_landed(ref, b, cache)\n"
        "    if sq is True:\n"
        "        return True",
        "    sq = False  # MUTANT: only ancestry is asked, as before task 140",
        ("SQUASH end to end: exit 1, naming ONLY the two that never landed",
         "both squash-merged faces count as LANDED")),
    # THE FAIL-OPEN HALF, and it is the one that costs evidence rather than attention: a
    # branch whose work is on no base at all reads LANDED, which is the task 70 defect back
    # with a green gate over it. Rule 15's variant -- the rows that must stay RED have to be
    # able to go green.
    "squash_claims_every_ref": (
        "    unknown = False\n    for _label, rev in bases:",
        "    return True  # MUTANT: every ref is claimed to have landed\n"
        "    unknown = False\n    for _label, rev in bases:",
        ("VARIANT: _squash_landed is False for work that never landed",
         "VARIANT: _is_landed still returns False on a genuine orphan",
         "SQUASH end to end: exit 1, naming ONLY the two that never landed",
         "`check` end to end: exit 1, naming 71 and NOT 70")),
    # A GIT FAILURE READ AS A CLEAN "no", the same defect `git_error_is_not_ancestor` pins on
    # the ancestry arm. `merge-base` exits 128 for a ref that vanished between the listing and
    # the query; dropping it into the False path makes `check` accuse a ticket whose content
    # it never read (rule 2).
    #
    # IT IS NAMED ON THE PRODUCER'S ROW ALONE, MEASURED. Listing `_is_landed passes the None
    # through` as well left this SURVIVING at 1 red of 111: for a ref git cannot resolve, the
    # ANCESTRY arm returns None too, so `_is_landed` degrades on that and the mutation is
    # invisible one level up. A `kills` entry naming a row the mutant cannot reach reports the
    # mutant as surviving, which is the harness working -- and it is why the composition needs
    # its own mutant (`is_landed_swallows_unknown`) rather than being covered by this one.
    "squash_git_error_is_false": (
        "            if mb.returncode != 0:\n"
        "                unknown = True\n"
        "                continue",
        "            if mb.returncode != 0:\n"
        "                continue  # MUTANT: a git failure reads as a clean 'no'",
        ("_squash_landed returns None (not False) when git cannot answer",)),
    # THE COMPOSITION SWALLOWING THE THIRD VALUE. Both arms are intact and only `_is_landed`
    # is wrong, so `_squash_landed`'s own rows stay green and the ticket still becomes an
    # accusation -- the shape that survives anything pinning the producer alone.
    "is_landed_swallows_unknown": (
        "    if anc is None or sq is None:\n        return None\n    return False",
        "    if False:  # MUTANT: an unreadable ref becomes an accusation\n"
        "        return None\n    return False",
        ("_is_landed passes the None through",)),
    # READING THE WRONG COLUMN of `git patch-id`, which prints `<patch-id> <commit-id>`. The
    # comparison then never matches, so every squash-merged branch reads ORPHANED while the
    # code still looks like it is comparing patch-ids. A wrong answer that is uniform across
    # the population is rule 12's tell.
    "patch_id_reads_the_wrong_column": (
        "    out = {f[0] for f in (ln.split() for ln in ids.stdout.splitlines()) if f}",
        "    out = {f[1] for f in (ln.split() for ln in ids.stdout.splitlines())"
        " if len(f) > 1}  # MUTANT: the commit-id column",
        ("_squash_landed is True for a squash-merged tip",
         "SQUASH end to end: exit 1, naming ONLY the two that never landed",
         "both squash-merged faces count as LANDED")),
    # THE CACHE KEY LOSING THE BASE IT WAS ASKED ABOUT. Two bases render two different
    # ranges; keyed on the base sha alone, the second one is answered out of the first one's
    # entry -- a wrong verdict that is uniform across everything sharing that fork point,
    # which is rule 12's tell and looks like a finding rather than a bug.
    "patch_cache_key_drops_the_rev": (
        "    key = (base_sha, rev)",
        "    key = base_sha  # MUTANT: one entry per fork point, whatever it was compared to",
        ("the same fork point against a MOVED main is a SECOND entry",)),
    # CACHING A FAILURE, which is rule 7's fail-open channel: one transient git error becomes
    # the stored answer for every later ref that shares the pair, with nothing saying so.
    "patch_cache_stores_failures": (
        "        if log.returncode != 0:\n            return None",
        "        if log.returncode != 0:\n"
        "            if cache is not None:\n"
        "                cache[key] = None  # MUTANT: a failure becomes an answer\n"
        "            return None",
        ("a git failure is NOT cached",)),
    "base_from_a_foreign_repo": (
        "        if head and _head_exists_here(head):",
        "        if head:  # MUTANT: a sha from any repository is accepted",
        ("`check` end to end: exit 1, naming 71 and NOT 70",
         "bases coinciding are named ONCE")),
}

#: THIS RUNNER'S OWN POSITIVE CONTROL: a mutation that must SURVIVE. `--selftest` runs it
#: and requires the control to come back FULLY GREEN -- exit 0, no red row at all -- because
#: "every mutant caught" from a harness structurally incapable of saying anything else is
#: rule 1's `total=0 passed=0`, and every mutant above is a NEGATIVE control.
#:
#: IT IS INERT BY CONSTRUCTION, AND THAT IS THE CHANGE `tasks/106` PAID FOR. Until then this
#: was a real coverage gap -- `if warn:` -> `if False:`, warnings computed and never printed
#: -- on the argument that a measured gap beats a synthetic no-op. The argument is wrong for
#: a POSITIVE control, because it couples the runner's own control to a defect somebody is
#: supposed to fix: closing the gap (direction 4c) turned the inert mutation into a caught
#: one and broke `--selftest` by design, and the work of closing it then had to carry a
#: second, unrelated repair. A positive control must not have an expiry date.
#:
#: A TRAILING COMMENT ON `MISFILED_MARGIN`'s LINE cannot expire: it changes no value, so no
#: behavioural row can ever go red on it, and no future row can "cover" it. The line is
#: chosen deliberately: `margin_up` and `margin_down` mutate THE SAME LINE and are both
#: caught, so SURVIVED here cannot be read as "nothing tests that line". It separates the
#: two claims the old design conflated -- *the runner can report a survivor* (here) and
#: *tasks.py has an untested mechanism* (a task in `tasks/`, where it can be fixed).
SELFTEST_MUTANT = (
    "MISFILED_MARGIN = 0.25",
    "MISFILED_MARGIN = 0.25  # INERT: a comment changes no value. margin_up and "
    "margin_down mutate this same line and are both caught.")

#: One row of `tasks_control.py`'s TABLE: `<name><pad>  <n>  <ok|FAIL>   <detail>`. Anchored
#: at the line start so a detail string containing the word FAIL cannot manufacture a row.
#:
#: THE FAILED ROWS ARE READ FROM THIS TABLE, NOT FROM THE SUMMARY BLOCK, and that was
#: measured rather than preferred. The summary prints `  FAIL <name>: <detail>`, so the
#: regex that parsed it -- `^  FAIL (.+?): ` -- stopped at the row name's FIRST `": "`. Every
#: round-trip row in `tasks_control.py` is named `round trip: ...`, so all of them arrived
#: here as the four characters `round`, and no `kills` entry could ever match the part that
#: distinguishes one from another. Two mutants introduced with `note` (task 113) turned those
#: rows red and were both reported SURVIVED -- the runner's own rule 12: a correct method
#: aimed at a lossy address, returning the same wrong answer for every subject.
#:
#: The table is the unambiguous address: the name is left-justified to a fixed width and the
#: separator is two or more spaces, which a row name cannot contain.
_ROW_RE = re.compile(r"^(\S.*?)\s{2,}\d+\s+(ok  |FAIL)\s", re.M)


def _write_copy(tmp: Path, name: str, mutant: str | None) -> Path:
    """A tempdir holding the copy under test, and a symlink to the real queue.

    The layout matters: `tasks.py` derives its queue from `git worktree list` and falls back
    to `parents[2]` when that fails, and a tempdir is not a checkout. So the copy goes at
    `<tmp>/<name>/eval/tools/tasks.py`, making the fallback root `<tmp>/<name>`, and
    `<tmp>/<name>/tasks` points at the real queue. Every row that reads it only reads.
    """
    root = tmp / name
    (root / "eval" / "tools").mkdir(parents=True)
    src = SOURCE.read_text()
    if mutant is not None:
        old, new, _ = MUTANTS[mutant]
        n = src.count(old)
        if n != 1:
            raise SystemExit(
                f"mutant `{mutant}` does not apply: its anchor occurs {n} times in "
                f"{SOURCE}. A no-op mutant reports a pass for a check that never changed, "
                f"and an ambiguous one mutates whichever copy came first. Fix the anchor.")
        src = src.replace(old, new, 1)
    (root / "eval" / "tools" / "tasks.py").write_text(src)
    if QUEUE.is_dir():
        (root / "tasks").symlink_to(QUEUE)
    return root / "eval" / "tools" / "tasks.py"


def _grade(copy: Path) -> tuple[int, str, list[str], list[str]]:
    """Run the REAL tasks_control.py against `copy`. Unpiped; the exit code is read as-is."""
    p = subprocess.run([sys.executable, str(CONTROL), "--tasks-py", str(copy)],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    parsed = _ROW_RE.findall(out)
    return (p.returncode, out,
            [name for name, status in parsed if status == "FAIL"],
            [name for name, _ in parsed])


def _report(out: str, limit: int = 4) -> None:
    for line in out.strip().split("\n")[-limit:]:
        print(f"        {line[:150]}")


def _cycle(tmp: Path, name: str) -> bool:
    """One mutant, graded and reported. Returns whether the row naming it went red.

    AN UNNAMED RED IS REPORTED, NOT FAILED, AND THAT IS MEASURED RATHER THAN PREFERRED.
    Raised by review on PR #6 (task 120): could a mutant that breaks more than it claims be
    reported CAUGHT for the wrong reason? It could in principle, and the price of closing it
    is the whole suite. Over the 21 mutants of that revision, **9 produced unnamed reds** --
    8 of them predating that ticket -- because a shared mechanism is exactly what several of them cut:
    `evidence_no_stdin` removes one sentinel that `note` and `done` both read, so 9 of its 13
    red rows are `note`'s. Failing on unnamed reds would turn those 9 mutants into failures
    without a single defect behind them.

    What actually guards against the case the review was worried about is the ACCEPTING rows
    (rule 15's variant half): a mutant that broke valid behaviour turns those red too, and
    they are listed by name in the report. `evidence_empty_allowed` is the worked example --
    **3 red, 0 unnamed**, exactly the 3 empty-evidence rows, with every accepting row still
    green. That is what says the mutation did what its name claims and nothing else.
    """
    old, _new, kills = MUTANTS[name]
    rc, out, failed, rows = _grade(_write_copy(tmp, name, name))
    unnamed = [f for f in failed if not any(k in f for k in kills)]
    missed = [k for k in kills if not any(k in f for f in failed)]
    caught = rc == 1 and not missed
    print(f"\n=== MUTANT {name}: {'CAUGHT' if caught else 'SURVIVED'} "
          f"(exit {rc}, {len(failed)} red of {len(rows)})")
    print(f"    removes: {old.strip()[:100]}")
    for f in failed:
        print(f"    red{'  ' if any(k in f for k in kills) else '? '} {f}")
    if missed:
        print(f"    NO ROW NAMING ITS MECHANISM WENT RED: {missed}")
        _report(out)
    if unnamed:
        print(f"    also red, not named by this mutant: {len(unnamed)}")
    return caught


def selftest(tmp: Path) -> int:
    """Can this runner report a SURVIVOR, and does it refuse a mutant that has drifted?

    Both are asked of the runner, not of `tasks.py`. A file that can only print CAUGHT
    proves nothing by printing CAUGHT six times.

    INERT IS A PROPERTY OF THE WHOLE REPORT, NOT OF ONE ROW NAME. This used to ask "did the
    row I named go red?", which is the enumeration failure AGENTS.md's rule audit describes.
    Measured while closing `tasks/106`: the new end-to-end row DID go red under the old
    inert mutation, the row it named did not, and `--selftest` printed `ok` over a mutation
    that had stopped being inert. The question is whether ANY row went red.
    """
    bad = []
    old, new = SELFTEST_MUTANT
    MUTANTS["_selftest_inert"] = (old, new, ())
    try:
        copy = _write_copy(tmp, "_selftest_inert", "_selftest_inert")
    finally:
        del MUTANTS["_selftest_inert"]
    rc, out, failed, rows = _grade(copy)
    inert = rc == 0 and not failed
    print(f"\n=== INERT MUTATION: {'SURVIVED' if inert else 'CAUGHT'} "
          f"(exit {rc}, {len(failed)} red of {len(rows)})")
    print(f"    adds: {new.strip()[:110]}")
    for f in failed:
        print(f"    red   {f}")
    if not inert:
        _report(out)
    print(f"\n  {'ok  ' if inert else 'FAIL'} the INERT mutation leaves EVERY row green")
    if not inert:
        bad.append("the inert mutation was CAUGHT. It changes no value, so this is the "
                   "harness or the anchor, not a gap somebody closed: read the red rows "
                   "above before picking a different mutation.")

    # A mutant whose anchor has drifted must REFUSE, not quietly apply nothing. A no-op
    # mutant reports a pass for a check that never changed.
    MUTANTS["_selftest_drift"] = ("A STRING THAT IS NOT IN tasks.py", "x", ("anything",))
    try:
        _write_copy(tmp, "_selftest_drift", "_selftest_drift")
        drifted_ok = False
    except SystemExit:
        drifted_ok = True
    finally:
        del MUTANTS["_selftest_drift"]
    print(f"  {'ok  ' if drifted_ok else 'FAIL'} a mutant whose anchor is absent REFUSES "
          f"rather than applying nothing")
    if not drifted_ok:
        bad.append("a drifted anchor applied silently")

    for b in bad:
        print(f"  FAIL {b}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mutate", metavar="NAME", help="one mutant instead of every one")
    ap.add_argument("--list", action="store_true", dest="list_mutants")
    ap.add_argument("--selftest", action="store_true",
                    help="this runner's own two controls: an INERT mutation must be "
                         "reported as SURVIVED, and a drifted anchor must refuse")
    a = ap.parse_args()

    if a.list_mutants:
        for name, (old, _, kills) in MUTANTS.items():
            print(f"{name:18} removes: {old.strip()[:60]}\n{'':18} killed by: "
                  f"{', '.join(kills)}")
        return 0
    if a.mutate and a.mutate not in MUTANTS:
        raise SystemExit(f"unknown mutant {a.mutate}; --list")

    names = [a.mutate] if a.mutate else list(MUTANTS)
    before = SOURCE.read_bytes()
    if not QUEUE.is_dir():
        print(f"WARNING: no queue at {QUEUE} - direction 1 and the task-32 pin will report "
              f"NOT CHECKED in every run below, including the baseline.", file=sys.stderr)

    # THREE ADDRESSES, PRINTED. What is mutated, what grades it, and what corpus it reads --
    # a correct method aimed at an unverified address is this project's commonest wrong
    # answer, and it always looks like a result (AGENTS.md rule 12).
    print(f"subject:  {SOURCE}\ncontrol:  {CONTROL}\nqueue:    {QUEUE}")

    with tempfile.TemporaryDirectory(prefix="tasks-mutants-") as td:
        tmp = Path(td)

        # THE BASELINE. Same tempdir, same symlink, same --tasks-py path, no mutation.
        print("=== BASELINE: an UNMUTATED copy, graded through the same path")
        rc, out, failed, rows = _grade(_write_copy(tmp, "_baseline", None))
        print(f"    exit {rc}, {len(rows)} rows, {len(failed)} FAILED")
        if rc != 0 or failed:
            print("    THE BASELINE IS NOT GREEN. Every result below is uninterpretable: a "
                  "red row under a mutant would be equally well explained by the harness.")
            _report(out, 12)
            return 2
        # The row names every `kills` entry is matched against must EXIST. A renamed row
        # would otherwise turn into "the mutant survived", which reads as a defect in
        # tasks.py rather than in this file.
        named = {k for _, _, kills in MUTANTS.values() for k in kills}
        missing = sorted(k for k in named if not any(k in r for r in rows))
        if missing:
            print(f"    ROW NAMES NOT FOUND in the baseline: {missing}. These are what "
                  f"`kills` is matched against; the rows were renamed or deleted.")
            return 2
        print(f"    baseline green, and all {len(named)} named rows are present")

        survivors = [name for name in names if not _cycle(tmp, name)]
        rc_self = selftest(tmp) if a.selftest else 0

    print(f"\n{len(names)} mutant(s), {len(survivors)} survived"
          + (f": {', '.join(survivors)} - tasks_control.py does not test what those rows "
             f"name" if survivors else " - every one killed by the row naming its "
             f"mechanism"))

    # #134: the constraint this file is built around. Asserted, not promised in a comment.
    if SOURCE.read_bytes() != before:
        print(f"\nFAIL {SOURCE} CHANGED during this run. A control must not be able to "
              f"damage the thing it controls; recover it with git before doing anything "
              f"else.")
        return 2
    print(f"{SOURCE.name} byte-identical before and after; the shared queue is read-only "
          f"here.")
    return 1 if (survivors or rc_self) else 0


if __name__ == "__main__":
    raise SystemExit(main())
