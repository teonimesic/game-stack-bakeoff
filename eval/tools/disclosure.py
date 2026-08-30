#!/usr/bin/env python3
"""Surface what each agent said about its own work, beside the score it was given.

Four documents (`AGENTS.md` rule 11, `DECISIONS.md`, `eval/PROTOCOL.md`, `eval/RUNS.md`)
say to read the building agent's closing message before grading it. Until this file,
**nothing did** — 31 of 75 completed trials had written a disclosure and no grader, report
or gate opened one (`tasks/71`). Two of this project's more expensive findings (#49 via
rule 11, #98) were recovered from that field by hand, after the fact.

## What this is, and what it is not

It is a **locator**: it points at the sentences in the agent's own words that mention
something it could not verify, or a risk it is leaving behind, and prints them verbatim so
the reader adjudicates. It is **not** a classifier and its count is **not** a rate.

## TWO FAMILIES, COUNTED SEPARATELY — they answer different questions

`CUES` asks *what did the agent say about its OWN work?*; `STARTER_CUES` asks *what did
the agent say about what it was GIVEN?* A row can be in both. Each has its own
hand-classified denominator, and **the two must never be pooled**: they were until
2026-08-23, and one row located only by the starter family sat inside the figure quoted
against a hand pass that never covered it, reporting 26 where the comparable number is 25
(`tasks/94`).

| family | located | hand | where the hand pass is |
|---|---|---|---|
| unverified own work | **25 of 75** | **31 of 75** | `eval/RUNS.md`, "DECLINED: requiring a finish-report section in the starters" |
| starter arrived broken | **15 of 75** | **18 of 75** | this docstring, below |

Per stack, over the 75 messages an agent actually wrote:

| stack | read | unverified (hand) | starter (hand) |
|---|---|---|---|
| godot | 15 | 3 (3) | 2 (5) |
| rust | 21 | 11 (13) | 12 (12) |
| ts | 23 | 3 (4) | 0 (0) |
| unity | 16 | 8 (11) | 1 (1) |
| **all** | **75** | **25 (31)** | **15 (18)** |

Both under-report. Quote the hand figure for a rate; quote these only as "trials with at
least one located passage".

## The starter family's hand pass, and what it does NOT reach

All 75 readable messages were read whole on 2026-08-23 against a criterion fixed before
reading: *the agent states that something in the delivered tree — a recipe, manifest,
config or harness file — did not work as given, or had to be repaired before it would.*
Excluded deliberately: a HOST defect (#49's wedged `syspolicyd` is the other family's
job); replacing placeholder content the starter documents as replaceable; closing a
coverage gap in the gate ("`just verify` never loads `main.ts`, so I added `just smoke`");
and a defect the agent introduced itself.

**18 of 75 qualify.** The extraction was proved before the census was believed: 12 of the
18 are the Rust `just run` subfamily, and that set is **equal to** the 12 `tasks/81`
counted independently, by a different producer, before this cue set existed.

**15 of 18 are located, with no false positives.** The residual 3 are the same shape as
each other and are named here so nobody re-derives them — an inherited defect in
starter-owned code that the agent never attributes to the starter in words:

| trial | what it says | why no cue reaches it |
|---|---|---|
| `wg-arena3d` `g3_arena__godot__t0` | `capture_frame` synced once at the end, so "every filmed frame was missing its bursts" | names no given-thing and no necessity; indistinguishable in form from describing its own new code |
| `wg-audio48` `g2_tetris3d__godot__t1` | "the old latch-and-clear handed the second tick an empty intent" | "old" is the only signal that the code was inherited |
| `wg-matrix` `g1_pong__godot__t1` | `project.godot`'s derived `user://` name "warns on every single run" | a warning, not a failure, and phrased as an addition |

Widening far enough to catch these is what produced false positives in every draft: the
same sentence shapes cover an agent describing a bug in work it wrote itself. **They are a
measured miss, not an unknown one.**

## Why the starter family exists at all

#98 was recovered from it, and it is one-arm bias — `build.compiles` and `verify.green`
are the exit codes of the submission's own recipes, so a starter red on a pristine tree
costs one arm two tier-1 criteria and no other. It fires on defects the agent went on to
fix, deliberately: what those cost was turns and money, which nothing counts. Twelve Rust
agents across five runs each privately repaired the same `just run` defect
(`tasks/81`, `eval/RUNS.md`), and for ten days nothing had noticed.

## Three values, never two

A message that was never written is not a message that said nothing (#31's shape: every
reason not to count something is a channel a bug can widen). Of the 90 stored messages,
**15 carry nothing the agent wrote** — 6 are `null` and 9 hold the API's own limit string
("You've hit your weekly limit · resets …", 71 characters; one session-limit variant at
62). Anything testing merely for non-empty scores those as closing reports. So every row
is one of:

| status | means |
|---|---|
| `passages` | the agent wrote a message and it names something unverified or a residual risk |
| `quiet` | the agent wrote a message and no cue matched it — **not** proof it disclosed nothing |
| `no_message` | `null`, the API's limit string, **or never stored at all**. **Unmeasurable**, never "quiet" |

## The scan's population is the artifact DIRECTORIES

Since tasks/225: every directory under `runs/<run>/artifacts/` yields exactly one row,
and a scan's trials count equals the artifact directories it reached. A trial whose
`agent_result.json` was never stored is a `no_message` row naming the missing file —
the state `read_trial` always had a branch for, which both scanners filtered out until
2026-08-30, so those trials vanished from every count (`--run-dir` on the wg-audio run
reported 11 for a 15-directory run; the whole tree reported 91 for 98 directories).
`--full` deliberately enumerates stored messages, not trial directories: it prints what
was written and holds no counts.

## It reads the WHOLE message

The source is `runs/*/artifacts/<trial>/agent_result.json` → `.result`, untruncated.
`trials/<trial>.json` → `agent.final_text` is the **last 3000 characters**
(`wholegame.py:358`) and 43 of the 90 stored messages are longer, so it is a partial read
of nearly half the corpus. That is not hypothetical here: `wg-arena3d-2026-08-15`
`g3_arena__rust__t1` opens with *"`just verify` never ran, because this machine cannot
execute freshly compiled binaries"* at character 0 of 3912, and the truncated field loses
it. That trial is the one whose run produced #49. This module never opens `trials/`.

## It surfaces text; it does not grade it

Nothing here scores a disclosure and nothing here reaches `overall`. Making disclosure a
criterion would change what agents optimise for, and `tasks/46` declined that regime change
on cost grounds. There is no criterion id, no tier and no weight in this file, and the cue
set is a **convenience for finding the passage, not a judgement about it** — which is why
`--full` prints every message whole with no selection applied at all. If the located view
and the whole message ever disagree about what an agent said, the whole message is the
evidence.

    python3 eval/tools/disclosure.py --run-dir eval/runs/<run>     # one run, per trial
    python3 eval/tools/disclosure.py --run-dir <run> --full        # every message, whole
    python3 eval/tools/disclosure.py --run-dir <run> --trial <id>  # one message, whole
    python3 eval/tools/disclosure.py --runs-dir eval/runs          # the whole tree
    python3 eval/tools/disclosure.py --selftest                    # both directions
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = ROOT / "eval" / "runs"

# The field `wholegame.py` truncates to. Named here only so the docstring's claim is
# checkable and so nobody re-points this module at it.
TRUNCATED_FIELD_TAIL_CHARS = 3000

# The API's own abort strings, which arrive in `.result` where agent text would be.
LIMIT_RE = re.compile(r"you'?ve hit your \w+ limit", re.I)

# --------------------------------------------------------------------------- the cues
#
# Written from the RULE, not from the instances: a passage qualifies if the agent says,
# about the work it is handing over, that something was NOT verified/run/tested/heard/seen,
# or that a risk or limitation remains. Every widening below was forced by a real message
# and every narrowing by a real false positive, both named.

# Words allowed between a negated auxiliary and its verb. A closed set on purpose: an
# open `.{0,70}` window links "aren't" to the "run" in "a run where nothing happens", and
# "doesn't" to the "test" in "a determinism test fails" — three such false positives in
# the stored corpus, all fixed by closing this set.
_GAP = (r"(?:(?:been|be|yet|ever|even|able\s+to|myself|it|them|that|this|\w+ly"
        r"|(?:get|take|make|send)(?:\s+(?:a|an|the))?|the\s+\w+)\s+){0,3}")

# Verbs that carry the claim on their own, whoever the subject is.
_DONE = r"(?:verif\w+|test(?:ed)?|exercis\w+|ran|run|executed?|validat\w+)"

# Past/perfect forms only. Present-tense habituals are descriptions of the harness, not
# admissions: "`just smoke` drives the real page (verify never executes `main.ts`)" is a
# design note, and matching `execut\w+` here made it the one false positive that broke the
# documented `archive-arena2d` negative control.
_PERF = r"(?:run|ran|executed|verified|tested|exercised|validated|launched|played)"

# Verbs that only carry the claim in the first person — "I could not hear it" is a
# disclosure, "a headless driver could never see a second run" is not.
_WEAK = (r"(?:see|seen|saw|hear|heard|listen(?:ed)?|watch(?:ed)?|screenshot\w*"
         r"|play(?:ed)?|confirm(?:ed)?|inspect(?:ed)?|look(?:ed)?\s+at|driv\w+|typ\w+"
         r"|press(?:ed|es|ing)?|compile-check|launch(?:ed)?)")

_FP = r"(?:I|we)\b"

CUES: list[tuple[str, re.Pattern[str]]] = [
    ("neg", re.compile(
        r"\b(?:could|can|did|do|does|have|has|had|was|were|is|are|am|will|would)"
        r"\s*(?:not|n[’']t)\s+" + _GAP + _DONE + r"\b", re.I)),
    ("never", re.compile(
        r"\bnever\s+(?:been\s+|actually\s+|even\s+)?" + _PERF + r"\b", re.I)),
    ("unadj", re.compile(
        r"\bun(?:verified|tested|tried|exercised|proven|validated)\b", re.I)),
    # "nobody has heard it" is a disclosure; "a paddle nobody has claimed plays itself"
    # is a game description. The verb list is what separates them.
    ("nobody", re.compile(
        r"\b(?:nobody|no one|no-one)\s+has\s+(?:ever\s+)?"
        r"(?:heard|listened|seen|watched|played|run|verified|tested|checked|driven)\b",
        re.I)),
    ("unable", re.compile(
        _FP + r"[^.;]{0,25}\b(?:unable to|not able to|no way to)\b", re.I)),
    ("fpweak", re.compile(
        _FP + r"[^.;]{0,40}?\b(?:could|can|did|have|has|was|were|am)"
        r"\s*(?:not|n[’']t)\s+" + _GAP + _WEAK + r"\b", re.I)),
    # UNEXERCISED BY REAL DATA: this family fires on 0 of the 90 stored messages. It is
    # kept because the phrasing is the one `game-research-gpt`'s required finish-report
    # section asks for (`tasks/46`), so it is what a future run would produce — but it has
    # never been tested against anything an agent actually wrote, and a cue that has never
    # fired is indistinguishable from one that cannot. Only the variant below tests it.
    ("residual", re.compile(
        r"\b(?:remaining|residual|known|outstanding)\s+"
        r"(?:risk|risks|limitation|limitations|gap|gaps|caveat|caveats)\b", re.I)),
]

# ------------------------------------------- the starter-arrived-broken family, and why
#
# A SECOND FAMILY, and the one #98 was recovered from: the agent reporting that the
# STARTER was broken before it touched anything. That is one-arm bias — a red gate on a
# pristine tree hands every submission in that arm two automatic tier-1 failures — and no
# tier measures it, because the agent usually repairs it and the score then looks
# identical to an arm that never had the problem. It fires on defects the agent went on
# to fix, deliberately: what it cost was turns and money, which nothing counts.
#
# It is a SEPARATE LIST, counted separately, because it answers a different question from
# the cues above and the hand pass it is quoted against never covered it. Pooling the two
# put a row located only by this family into the figure compared with the
# what-I-could-not-verify hand pass, inflating it by one (`tasks/94`).
#
# WRITTEN FROM THE PROPERTY, NOT FROM THE WORD ORDER OF THE SENTENCES THAT PRODUCED IT.
# The first version required the artifact word to come BEFORE the breakage inside one
# 70-character window. The corpus states it both ways round and puts markdown emphasis in
# between, so "`just run` was broken in the starter" matched and "**`just run` was already
# broken** in the starter" did not — the same defect, the same run, two trials apart. And
# 8 of the 12 Rust trials that reported it phrase it as the repair rather than as the
# complaint ("`crates/game` gained `default-run`", "it needed `default-run` in the
# manifest"), which no widening of the breakage vocabulary alone can reach.

# Something the agent was handed rather than wrote.
_GIVEN = r"(?:starter|baseline|harness|template|scaffold)"
# A recipe or manifest the tree ships, NAMED — an unnamed "it" cannot be attributed to the
# tree rather than to the agent's own work.
_RECIPE = (r"(?:just\s+[a-z][\w-]*|cargo\s+run(?:\s+-p\s+`?\w+`?)?|pnpm\s+\w+"
           r"|Cargo\.toml|project\.godot|justfile|manifest)")
# "It did not work" — past tense or a state, never a present-tense habitual. `just
# audio-manifest` "refuses to print one whose files are missing" describes a gate that
# works, and matching `refus\w+` there was a measured false positive.
_BROKEN = (r"(?:broken|already\s+red|is\s+red|was\s+red|failing|unusable|ambiguous"
           r"|refused|could\s+not\s+(?:determine|choose|pick|guess))")
# Only next to a named recipe: a bare "failed" also appears in test counts and in
# comparisons against goldens that were never run.
_BROKEN_RECIPE = _BROKEN + r"|(?:failed|no\s+longer\s+guess|refuses\s+to\s+choose)"
# The repair, phrased as necessity — NOT mere addition. "`just verify` gained a `smoke`
# step" is the agent's own new work and "`crates/game` gained `default-run`" is a repair;
# "gained" cannot tell them apart, and what separates them is that the second says why
# there was no choice. So the necessity is what is matched.
_NEEDED = (r"(?:had\s+to\s+(?:go|be\s+added)|w(?:as|ere)\s+needed|needed\s+`"
           r"|could\s+no\s+longer|refused\s+to|w(?:as|ere)\s+missing|had\s+broken)")

# THREE PROPERTIES THAT MAKE A SENTENCE NOT A BREAKAGE REPORT. Each is a property of the
# sentence; none is a list of the strings that produced it:
#   - the agent attributes the behaviour to design — "`just run` is refused in this
#     environment, which the starter documents as a property of Bevy-on-macOS, not a
#     defect to repair" (`wg-g4c` rust t0, the adversarial row);
#   - it is a counterfactual rather than a report — "would have left every test green and
#     `just run` broken";
#   - the failure word is negated or is a test count — "no failed audio requests",
#     "just ci: 68 passed, 0 failed, 0 skipped".
# Scoped to this family alone: applying it to CUES would silently drop disclosures.
NOT_A_REPORT = re.compile(
    r"documents?\b|by\s+design|not\s+a\s+defect|deliberate|as\s+specified|was\s+right"
    r"|\bwould\b"
    r"|\bno\s+(?:failed|failing|broken|page\s+errors)\b"
    r"|\b\d+\s+(?:failed|failing|skipped)\b", re.I)

STARTER_CUES: list[tuple[str, re.Pattern[str]]] = [
    ("starter", re.compile(
        _GIVEN + r"[^.;]{0,90}?(?:" + _BROKEN + r")"
        r"|(?:" + _BROKEN + r")[^.;]{0,90}?" + _GIVEN, re.I)),
    # A named recipe reported as not working, with no artifact word anywhere in the
    # sentence. On the current corpus it locates NO row that `starter` or `given_fix` does
    # not also locate — recorded rather than hidden. It is kept because it is the only
    # family that can reach "`just run` was ambiguous" standing alone, which is how four
    # of the twelve trials open the paragraph; its load-bearing test is therefore a
    # variant, not a stored row.
    ("recipe_red", re.compile(
        _RECIPE + r"[^.;]{0,90}?(?:" + _BROKEN_RECIPE + r")"
        r"|(?:" + _BROKEN_RECIPE + r")[^.;]{0,90}?" + _RECIPE, re.I)),
    # The repair phrased as the fix — the shape the first version had no reach into at
    # all, and where 8 of the 12 Rust trials live.
    ("given_fix", re.compile(
        r"(?:" + _RECIPE + r"|" + _GIVEN + r")[^.;]{0,90}?(?:" + _NEEDED + r")"
        r"|(?:" + _NEEDED + r")[^.;]{0,90}?(?:" + _RECIPE + r"|" + _GIVEN + r")"
        r"|" + _GIVEN + r"[^.;]{0,40}?\bfix(?:ed)?\b"
        r"|\bfix(?:ed)?\b[^.;]{0,40}?" + _GIVEN, re.I)),
]

STARTER_FAMILY = frozenset(name for name, _ in STARTER_CUES)

# A markdown heading is worth taking whole, with its first lines of body — 10 of the 31
# hand-classified disclosures sit under one. Only headings that NAME non-verification
# count: "Two things worth flagging" appears over judgement calls and fixed bugs in ~40 of
# the 75 messages and would swamp the signal.
_HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s*|\*\*)\s*(?P<h>[^\n*]{0,90}?)"
                      r"\s*(?:\*\*)?\s*:?\s*$")
_HEAD_CUE = re.compile(
    r"(?:could\s*n[o’']?t|could\s+not|cannot|can[’']t|did\s+not|didn[’']t)"
    r"\s+(?:verify|run|test|check|confirm)"
    r"|not\s+verified|unverified|verified\s+vs|not\s+done"
    r"|remaining\s+risk|known\s+limitation|caveat", re.I)

HEADING_BODY_LINES = 3


@dataclass(frozen=True)
class Passage:
    """One located passage, in the agent's own words."""
    line: int
    cues: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class Row:
    """One trial's closing message and what was located in it."""
    run: str
    trial_id: str
    status: str                 # "passages" | "quiet" | "no_message"
    reason: str                 # why, when status is no_message
    chars: int                  # length of the whole message
    terminal_reason: str
    passages: tuple[Passage, ...]

    @property
    def stack(self) -> str:
        parts = self.trial_id.split("__")
        return parts[1] if len(parts) > 2 else "?"

    @property
    def game(self) -> str:
        return self.trial_id.split("__")[0]

    # The two families are counted separately, never pooled. A row can be in both.
    @property
    def starter_passages(self) -> tuple[Passage, ...]:
        """Passages saying something the agent was GIVEN did not work."""
        return tuple(p for p in self.passages if STARTER_FAMILY.intersection(p.cues))

    @property
    def unverified_passages(self) -> tuple[Passage, ...]:
        """Passages saying something about the agent's OWN work is unverified."""
        return tuple(p for p in self.passages
                     if set(p.cues).difference(STARTER_FAMILY))


class DisclosureError(RuntimeError):
    """The tree could not be read. Never downgraded to a count of zero."""


# --------------------------------------------------------------------------- extraction

def _units(text: str) -> list[tuple[int, str]]:
    """(line number, sentence) for every sentence of every non-blank line.

    Split per line first: these messages are markdown, and a bullet without terminal
    punctuation would otherwise be glued to the next one.
    """
    out: list[tuple[int, str]] = []
    for i, block in enumerate(text.split("\n")):
        stripped = block.strip()
        if not stripped:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", stripped):
            sentence = sentence.strip()
            if sentence:
                out.append((i, sentence))
    return out


def passages(text: str) -> tuple[Passage, ...]:
    """Every located passage, in document order. Verbatim — nothing is paraphrased."""
    lines = text.split("\n")
    found: list[Passage] = []
    claimed: set[int] = set()
    for i, line in enumerate(lines):
        match = _HEADING.match(line)
        if match and _HEAD_CUE.search(match.group("h")):
            body = " ".join(x.strip() for x in lines[i + 1:i + 1 + HEADING_BODY_LINES]
                            if x.strip())
            whole = (line.strip() + " — " + body).strip(" —")
            found.append(Passage(i, ("heading",), whole))
            claimed.add(i)
    for i, sentence in _units(text):
        if i in claimed:
            continue
        cues = tuple(name for name, pattern in CUES if pattern.search(sentence))
        if not NOT_A_REPORT.search(sentence):
            cues += tuple(name for name, pattern in STARTER_CUES
                          if pattern.search(sentence))
        if cues:
            found.append(Passage(i, cues, sentence))
    found.sort(key=lambda p: (p.line, p.text))
    return tuple(found)


def classify(result: object) -> tuple[str, str]:
    """(status, reason) for a raw `.result`, before any cue is applied.

    `no_message` is a refusal to measure, not a measurement of zero.
    """
    if result is None:
        return "no_message", "`.result` is null — the trial wrote no closing message"
    if not isinstance(result, str) or not result.strip():
        return "no_message", "`.result` is empty"
    if LIMIT_RE.search(result):
        return ("no_message",
                "`.result` holds the API's own limit string, not agent text: "
                + " ".join(result.split())[:90])
    return "ok", ""


# --------------------------------------------------------------------------- reading

def read_trial(artifact_dir: Path) -> Row:
    """One trial, read from its WHOLE stored message.

    The source is `agent_result.json` → `.result`. `trials/*.json` → `agent.final_text`
    is the last 3000 characters and is never opened here.
    """
    path = artifact_dir / "agent_result.json"
    run = artifact_dir.parents[1].name
    tid = artifact_dir.name
    if not path.is_file():
        return Row(run, tid, "no_message", f"no {path.name} stored", 0, "?", ())
    try:
        agent = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise DisclosureError(f"{path}: {exc}") from exc
    result = agent.get("result")
    terminal = str(agent.get("terminal_reason"))
    status, reason = classify(result)
    if status == "no_message":
        return Row(run, tid, "no_message", reason,
                   len(result) if isinstance(result, str) else 0, terminal, ())
    found = passages(result)
    return Row(run, tid, "passages" if found else "quiet", "",
               len(result), terminal, found)


def scan_run(run_dir: Path) -> list[Row]:
    """Every artifact directory under `<run>/artifacts/` yields exactly one row.

    The population is the DIRECTORIES, not the files in them (tasks/225): a trial
    whose `agent_result.json` was never stored is a `no_message` row carrying its
    reason — `read_trial`'s own branch — never an absence from the report. A file
    under `artifacts/` that is not a directory is not a trial and yields nothing.
    """
    artifacts = run_dir / "artifacts"
    if not artifacts.is_dir():
        raise DisclosureError(f"no artifacts directory at {artifacts}")
    dirs = [d for d in sorted(artifacts.iterdir()) if d.is_dir()]
    if not dirs:
        raise DisclosureError(
            f"{artifacts} holds no trial directories — refusing to report 0")
    return [read_trial(d) for d in dirs]


def scan_tree(runs_dir: Path) -> list[Row]:
    """Every artifact directory at `<runs>/*/artifacts/<trial>/` yields one row.

    Same property as `scan_run`, over the whole tree: the population is the
    artifact directories, so a run whose only trial never stored a message still
    appears — as `no_message` — rather than disappearing from the per-run table.
    """
    if not runs_dir.is_dir():
        raise DisclosureError(
            f"no runs directory at {runs_dir} (it is gitignored; an agent worktree does "
            f"not have one — read the main checkout)")
    dirs = sorted(d for d in runs_dir.glob("*/artifacts/*") if d.is_dir())
    if not dirs:
        raise DisclosureError(
            f"{runs_dir} holds no */artifacts/<trial> directories — refusing to report 0")
    return [read_trial(d) for d in dirs]


# --------------------------------------------------------------------------- rendering

BANNER = (
    "--- what each agent said about its OWN work "
    "(whole message: artifacts/<trial>/agent_result.json .result) ---")

CAVEAT = (
    "A LOCATOR, NOT A VERDICT. These are the agent's own sentences that mention something\n"
    "unverified, a residual risk, or a starter that arrived broken; read them, do not count\n"
    "them. `quiet` means no cue matched, NOT that the trial disclosed nothing.\n"
    "TWO FAMILIES, NEVER POOLED — over the 75 stored messages an agent actually wrote, this\n"
    "locator finds 25 unverified-own-work against a hand-classified 31 (eval/RUNS.md), and\n"
    "15 starter-arrived-broken against a hand-classified 18 (this module's docstring).\n"
    "`NO MESSAGE` is unmeasurable, not silence: `.result` was null, held the API's own\n"
    "limit string where agent text would be, or was never stored at all.")


def render_rows(rows: list[Row], indent: str = "") -> list[str]:
    """Per-trial lines. Used by `wholegame.py report` and by this module's CLI."""
    out: list[str] = []
    for row in sorted(rows, key=lambda r: (r.game, r.stack, r.trial_id)):
        if row.status == "no_message":
            out.append(f"{indent}{row.trial_id:<26} NO MESSAGE  "
                       f"[{row.terminal_reason}] {row.reason}")
            continue
        if row.status == "quiet":
            out.append(f"{indent}{row.trial_id:<26} quiet       "
                       f"({row.chars} chars read, no cue matched)")
            continue
        out.append(f"{indent}{row.trial_id:<26} {len(row.passages)} PASSAGE(S)  "
                   f"({row.chars} chars read)")
        for passage in row.passages:
            text = " ".join(passage.text.split())
            out.append(f"{indent}    [{'+'.join(passage.cues)}] {text[:400]}")
    return out


def summarise(rows: list[Row]) -> str:
    n_p = sum(1 for r in rows if r.status == "passages")
    n_q = sum(1 for r in rows if r.status == "quiet")
    n_n = sum(1 for r in rows if r.status == "no_message")
    n_u = sum(1 for r in rows if r.unverified_passages)
    n_s = sum(1 for r in rows if r.starter_passages)
    return (f"{len(rows)} trials: {n_p} with located passages, {n_q} quiet, "
            f"{n_n} with no agent message (unmeasurable)\n"
            f"  by family (a row can be in both): "
            f"{n_u} unverified-own-work, {n_s} starter-arrived-broken")


def render_tree(rows: list[Row]) -> str:
    lines = [BANNER, "", CAVEAT, "", summarise(rows), ""]
    per_run: dict[str, list[Row]] = collections.defaultdict(list)
    for row in rows:
        per_run[row.run].append(row)
    lines.append("per run (located / messages read / trials)")
    for run in sorted(per_run):
        group = per_run[run]
        readable = [r for r in group if r.status != "no_message"]
        located = [r for r in readable if r.status == "passages"]
        lines.append(f"  {run:<38} {len(located):>2} / {len(readable):>2} / {len(group)}")
    lines.append("")
    lines.append("per stack, messages the agent actually wrote — THE TWO FAMILIES ARE "
                 "COUNTED SEPARATELY")
    lines.append(f"  {'stack':<8} {'read':>4} {'unverified':>11} {'starter':>8}"
                 f"   [hand-classified: eval/RUNS.md, and this module's docstring]")
    per_stack: dict[str, list[Row]] = collections.defaultdict(list)
    for row in rows:
        if row.status != "no_message":
            per_stack[row.stack].append(row)
    for stack in sorted(per_stack):
        group = per_stack[stack]
        unver = sum(1 for r in group if r.unverified_passages)
        start = sum(1 for r in group if r.starter_passages)
        lines.append(f"  {stack:<8} {len(group):>4} {unver:>11} {start:>8}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- selftest

# Rows whose answer the documents state BEFORE this tool was written. Pinning the
# extraction on rows with a stated true value is rule 12's corollary: a census returning
# one value across a population it exists to discriminate is reporting the instrument.
MUST_LOCATE = [
    # eval/FINDINGS.md #98: both graded Godot agents said in their own words that the
    # starter's gate was red before they touched anything.
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t0"),
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t1"),
    # AGENTS.md rule 11 / #49: the arena3d agents whose toolchain never ran.
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__rust__t0"),
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__rust__t1"),
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__ts__t0"),
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__ts__t1"),
]

# (run, trial, cue) — the NAMED cue must be the one that fires, not merely some other
# passage in the same message, otherwise a family could be dead and the row still look
# pinned. Every family must appear here or in VARIANTS_LOCATED, and `disclosure_mutants`
# deletes each in turn at source.
MUST_LOCATE_BY_CUE = [
    # #98's own evidence: both graded Godot agents named the red starter gate.
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t0", "starter"),
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t1", "starter"),
    # tasks/81's 12: phrased as the repair, not as the complaint. `given_fix` is the only
    # family that reaches this row.
    ("wg-audio-2026-08-14T12-29-42", "g1_pong__unity__t0", "given_fix"),
    # ...and both word orders of the complaint, which the pre-2026-08-23 cue split.
    ("wg-matrix-2026-08-13T14-02-50", "g1_pong__rust__t0", "starter"),   # "was already
    ("wg-matrix-2026-08-13T14-02-50", "g1_pong__rust__t1", "starter"),   #  broken** in"
]

# THE ADVERSARIAL ROWS: every one of these names a starter, a recipe or both, and none of
# them reports a starter that arrived broken. `wg-g4c` rust t0 is the sharp one — it says
# `just run` IS refused and, in the same sentence, that the starter documents it as a
# property of Bevy-on-macOS rather than a defect. A cue set that cannot tell those apart
# would report the family as ~50% larger than it is.
MUST_HAVE_NO_STARTER_CUE = [
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__rust__t0"),   # documented refusal
    ("wg-audio48-2026-08-14T19-55-47", "g1_pong__godot__t1"),    # "the starter ... was right"
    ("wg-audio-2026-08-14T12-29-42", "g1_pong__godot__t0"),      # a coverage gap, closed
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__ts__t0"),     # a coverage gap, closed
    ("wg-matrix-2026-08-13T14-02-50", "g3_arena__unity__t1"),    # "0 failed" is a count
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__ts__t0"),      # the HOST was broken,
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__ts__t1"),      # not the tree — that is
    ("wg-arena3d-2026-08-15T12-46-30", "g3_arena__rust__t1"),    # the other family's job
]

# eval/RUNS.md records archive-arena2d at a 0% hand-classified rate over its n=3 readable
# messages — for the UNVERIFIED-OWN-WORK family, which is the only thing that hand pass
# covered. So the pin is on that family, not on the row's overall status: `rust__t0` says
# "`default-run` had to go into `crates/game/Cargo.toml`", which is a real member of the
# starter family and one of tasks/81's 12. Pinning it as wholly `quiet` was pinning the
# defect this file was repaired for.
MUST_HAVE_NO_UNVERIFIED_CUE = [
    ("archive-arena2d-wg-audio48", "g3_arena__rust__t0"),
    ("archive-arena2d-wg-audio48", "g3_arena__ts__t0"),
    ("archive-arena2d-wg-audio48", "g3_arena__ts__t1"),
]

# The two of those three that must ALSO be wholly quiet — they carry phrasing that broke
# earlier drafts ("I have not committed anything", "verify never executes `main.ts`").
MUST_BE_QUIET = [
    ("archive-arena2d-wg-audio48", "g3_arena__ts__t0"),
    ("archive-arena2d-wg-audio48", "g3_arena__ts__t1"),
]

# The API's own abort strings must never be read as a closing report.
MUST_BE_NO_MESSAGE = [
    ("wg-g4b-2026-08-17T19-50-43", "g4_platformer__rust__t0"),
    ("wg-cal48-2026-08-14T14-30-58", "g1_pong__ts__t0"),
    ("archive-arena2d-wg-audio48", "g3_arena__godot__t0"),
]

# Sentences a plausible-looking cue set gets WRONG. A mutant only asks whether a check can
# fail; only a variant asks whether it can still pass on an input it mishandles (rule 15).
# Every string here is copied from a stored message.
VARIANTS_QUIET = [
    "I have not committed anything — the work is staged in the working tree.",
    "I did not commit anything.",
    "Nothing is committed; the working tree is left dirty for you to review.",
    "`just smoke` (drives the real page in Chromium; verify never executes `main.ts`)",
    "A side nobody has touched is played by an autopilot.",
    "A paddle nobody has claimed plays itself — slower than a player's.",
    "I also added a test asserting the replay tape itself produces hits, so the "
    "hash-chain tests aren't hashing a run where nothing happens.",
    "`sim/sim.gd`'s header documents that as the reason AGENTS.md rule 6 doesn't apply "
    "here, and a determinism test fails if a decimal point appears in a trace line.",
    "## Two things worth flagging",
    # The starter family must not fire on a starter merely being mentioned, nor on a
    # defect the agent introduced and then found in its own work.
    "The starter's HUD is the worked example for anything you add.",
    "I broke the golden frame myself and re-blessed it.",
    # The three properties in NOT_A_REPORT, one string each, all copied from the corpus.
    "`just run` is refused in this environment (`STARTER_NO_RAISE=1`), which the starter "
    "documents as a property of Bevy-on-macOS, not a defect to repair.",
    "A crash in `Main._ready` or a missing sound file would have left every test green "
    "and `just run` broken.",
    "`just run` → played it in a real browser via `just smoke`: keys respond, no page "
    "errors, no failed audio requests.",
    "`just ci`: 68 passed, 0 failed, 0 skipped.",
    # An ADDITION is not a repair: the word "gained" alone must not carry the family.
    "**`just verify` gained a `smoke` step.**",
    "`FixedClock.advance` gained an optional per-tick observer, used only to feed sound.",
    # A present-tense habitual describes a gate that works.
    "`just audio-manifest` prints the object and refuses to print one whose files are "
    "missing or silent.",
    # A starter feature deliberately absent is not a starter that arrived broken.
    "The trimmed list had no `bevy_audio` at all, so I added the two needed.",
]

VARIANTS_LOCATED = [
    "**`just verify` has never run.** This host's `syspolicyd` is wedged.",
    "**I could not listen to the audio.** ffmpeg is not runnable in this environment.",
    "The composition should sound like a chiptune, but nobody has heard it.",
    "**I could not press keys myself.**",
    "**I could not visually confirm the running window.**",
    "That path is unexercised by any test and untested against hardware.",
    "I have no way to *hear* the audio here.",
    "The render tests are written and typecheck, but they have never executed.",
    "**`just verify` does not run on this machine, for a reason outside the repo.**",
    # The only test the `residual` family has: it fires on nothing in the stored corpus.
    "Remaining risks: the gamepad path is on you.",
    # ---- the starter family. Both word orders the corpus uses, and both phrasings.
    "**The starter baseline was already red here**, before I touched anything.",
    "- **The baseline was already red.** `tools/check.gd` called `reload()`.",
    "- **`just run` was broken in the starter** and I fixed it.",
    # The word order that the pre-2026-08-23 cue could not reach: artifact word AFTER the
    # breakage, with markdown emphasis closing in between.
    "- **`just run` was already broken** in the starter — `cargo run -p game` refuses to "
    "choose between multiple binaries.",
    "**`just run` was already broken in the starter** — `crates/game` ships two binaries "
    "and had no `default-run`.",
    # `recipe_red`'s only load-bearing test: a named recipe that did not work, with no
    # artifact word in the sentence at all. It was in VARIANTS_QUIET until 2026-08-23,
    # asserting that this family must NOT fire — which is the defect tasks/94 repaired,
    # so the expectation moved sides deliberately and is recorded here rather than
    # deleted.
    "Bare `cargo run -p game` failed with \"could not determine which binary to run\".",
    "`just run` was ambiguous — `crates/game` ships two binaries and cargo refused to "
    "pick.",
    # `given_fix`: the repair stated as the fix, which is how 8 of the 12 phrase it.
    "`default-run = \"game\"` had to go into `crates/game/Cargo.toml`.",
    "`crates/game` gained `default-run = \"game\"` — with four binaries in the crate, "
    "`just run` could no longer guess.",
    "It needed `default-run = \"game\"` in the manifest.",
    "**I fixed an input bug in the starter's runner.**",
]


def selftest(runs_dir: Path | None) -> int:
    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # ---- direction 0: the scan reaches EVERY artifact directory (tasks/225). The
    # population of a scan is the artifact DIRECTORIES it reaches, not the files in
    # them: a trial whose closing message was never stored is a `no_message` row
    # carrying its reason — never an absence — and a file under artifacts/ that is
    # not a directory is not a trial. The refusals are the other half of the same
    # property: an empty population is a refusal (exit 2), not a report of zero.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        arts = root / "run-a" / "artifacts"
        (arts / "t_full").mkdir(parents=True)
        (arts / "t_full" / "agent_result.json").write_text(
            '{"result": "I could not verify the audio."}')
        (arts / "t_bare").mkdir()                       # message never stored
        (arts / "t_bare" / "diff.patch").write_text("x")
        (arts / "stray.txt").write_text("not a trial")  # a FILE is not a trial
        (root / "run-empty" / "artifacts").mkdir(parents=True)
        empty_root = root / "empty-root"
        empty_root.mkdir()
        rows = scan_run(root / "run-a")
        check("scan_run reaches the file-less dir",
              sorted(r.trial_id for r in rows), ["t_bare", "t_full"])
        bare = [r for r in rows if r.trial_id == "t_bare"]
        check("file-less dir yields one no_message row naming the file",
              [(r.status, "agent_result.json" in r.reason) for r in bare],
              [("no_message", True)])
        check("scan_tree reaches the file-less dir",
              sorted((r.run, r.trial_id, r.status) for r in scan_tree(root)),
              [("run-a", "t_bare", "no_message"), ("run-a", "t_full", "passages")])
        for label, call in (
                ("scan_run on an artifacts dir holding no trial subdirs",
                 lambda: scan_run(root / "run-empty")),
                ("scan_run on a missing artifacts dir",
                 lambda: scan_run(root / "nope")),
                ("scan_tree on a root holding no artifact dirs",
                 lambda: scan_tree(empty_root))):
            try:
                call()
            except DisclosureError:
                continue
            failures.append(f"{label}: reported a count instead of refusing (exit 2)")

    # ---- direction 1: the located set can be EMPTIED. A cue set that cannot go quiet is
    # a check that cannot fail, and would report every message as a disclosure. BOTH
    # lists are emptied: leaving one populated would let it cover for the other.
    saved, saved_starter = list(CUES), list(STARTER_CUES)
    try:
        CUES.clear()
        STARTER_CUES.clear()
        for text in VARIANTS_LOCATED:
            if passages(text):
                failures.append(f"mutant (cues removed) still located: {text[:60]!r}")
    finally:
        CUES[:], STARTER_CUES[:] = saved, saved_starter
    # ...and with the cues restored, every one of them must come back.
    for text in VARIANTS_LOCATED:
        if not passages(text):
            failures.append(f"restored cues failed to locate: {text[:60]!r}")

    # ---- direction 1b: EVERY cue family must be load-bearing for something. Removing one
    # has to silence at least one string this file claims it locates. A family that can be
    # deleted with no expectation changing is either dead or duplicated, and both look
    # exactly like a working cue from the outside.
    for target, restore in ((CUES, saved), (STARTER_CUES, saved_starter)):
        for name, _ in restore:
            target[:] = [c for c in restore if c[0] != name]
            try:
                silenced = [t for t in VARIANTS_LOCATED if not passages(t)]
            finally:
                target[:] = restore
            if not silenced:
                failures.append(f"cue family {name!r} is load-bearing for no variant — "
                                f"removing it changes nothing this file checks")

    # ---- direction 2: the variants it must NOT fire on.
    for text in VARIANTS_QUIET:
        got = passages(text)
        if got:
            failures.append(f"false positive on {text[:60]!r}: {[p.cues for p in got]}")

    # ---- direction 3: three values, never two.
    check("null result", classify(None)[0], "no_message")
    check("empty result", classify("")[0], "no_message")
    check("weekly limit string",
          classify("You've hit your weekly limit · resets Aug 19 at 6pm")[0],
          "no_message")
    check("session limit string",
          classify("You've hit your session limit · resets 5pm (America/Sao_Paulo)")[0],
          "no_message")
    check("real message", classify("I could not verify the audio.")[0], "ok")

    # ---- direction 4: the field choice is load-bearing. A disclosure in the HEAD of a
    # long message is invisible to `agent.final_text`, which keeps the last 3000 chars.
    head_disclosure = "**`just verify` never ran** on this machine.\n"
    whole = head_disclosure + ("filler line about the game.\n" * 200)
    if not passages(whole):
        failures.append("whole message: head disclosure not located")
    if passages(whole[-TRUNCATED_FIELD_TAIL_CHARS:]):
        failures.append("control is broken: the truncated tail still holds the passage")

    # ---- direction 5: the real corpus, on rows whose answer the documents already state.
    if runs_dir is None:
        print("REAL-CORPUS PINS NOT RUN — explicitly skipped with --skip-corpus. "
              "This is a non-measurement, not a pass.")
    elif not runs_dir.is_dir():
        print(f"UNMEASURABLE: no corpus at {runs_dir}. An agent worktree has no "
              f"eval/runs/; run this in the main checkout or pass --skip-corpus.")
        return 2
    else:
        for run, tid in MUST_LOCATE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.status != "passages":
                failures.append(f"{run}/{tid}: documented discloser came back "
                                f"{row.status}")
        for run, tid, cue in MUST_LOCATE_BY_CUE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if not any(cue in p.cues for p in row.passages):
                failures.append(f"{run}/{tid}: a documented starter-arrived-broken "
                                f"report was not located by the {cue!r} cue")
        for run, tid in MUST_HAVE_NO_STARTER_CUE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.starter_passages:
                failures.append(
                    f"{run}/{tid}: adjudicated as NOT reporting a broken starter, but "
                    f"the starter family fired: "
                    f"{[(p.cues, p.text[:70]) for p in row.starter_passages]}")
        for run, tid in MUST_HAVE_NO_UNVERIFIED_CUE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.unverified_passages:
                failures.append(
                    f"{run}/{tid}: hand-classified as not disclosing anything about its "
                    f"own work, but a cue fired: "
                    f"{[(p.cues, p.text[:70]) for p in row.unverified_passages]}")
        for run, tid in MUST_BE_QUIET:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.status != "quiet":
                failures.append(f"{run}/{tid}: documented non-discloser came back "
                                f"{row.status} {[p.text[:60] for p in row.passages]}")
        for run, tid in MUST_BE_NO_MESSAGE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.status != "no_message":
                failures.append(f"{run}/{tid}: an aborted trial came back {row.status}")
        # ---- direction 5b: the SCANS, not just read_trial (tasks/225). Every artifact
        # directory on disk yields exactly one row. The walk below is the expectation,
        # written here and not imported from the scanners: the defect was the scanners'
        # own filter, so the directory listing is the independent statement of the fact.
        audio = runs_dir / "wg-audio-2026-08-14T12-29-42"
        on_disk = sorted(d.name for d in (audio / "artifacts").iterdir() if d.is_dir())
        audio_rows = {r.trial_id: r for r in scan_run(audio)}
        check("scan_run covers every artifact dir in wg-audio",
              sorted(audio_rows), on_disk)
        check("wg-audio's never-stored messages are no_message rows naming the file",
              sorted((r.trial_id, r.status, "agent_result.json" in r.reason)
                     for r in audio_rows.values()
                     if not (audio / "artifacts" / r.trial_id
                             / "agent_result.json").is_file()),
              sorted([("g2_tetris3d__godot__t0", "no_message", True),
                      ("g2_tetris3d__rust__t0", "no_message", True),
                      ("g2_tetris3d__unity__t0", "no_message", True),
                      ("g2_tetris3d__unity__t1", "no_message", True)]))
        tree_rows = scan_tree(runs_dir)
        check("scan_tree covers every artifact dir in the tree",
              sorted((r.run, r.trial_id) for r in tree_rows),
              sorted((d.parent.parent.name, d.name)
                     for d in runs_dir.glob("*/artifacts/*") if d.is_dir()))
        scene = [r for r in tree_rows if r.trial_id == "s1_parallax__ts__t0"]
        check("the scene trial whose message was never stored is named, not invisible",
              [(r.run, r.status, "agent_result.json" in r.reason) for r in scene],
              [("wg-scene-s1ts-2026-08-25", "no_message", True)])
        # The truncation control, on real data rather than a fixture.
        row = read_trial(runs_dir / "wg-arena3d-2026-08-15T12-46-30" / "artifacts"
                         / "g3_arena__rust__t1")
        raw = json.loads((runs_dir / "wg-arena3d-2026-08-15T12-46-30" / "artifacts"
                          / "g3_arena__rust__t1" / "agent_result.json").read_text())
        tail = passages((raw.get("result") or "")[-TRUNCATED_FIELD_TAIL_CHARS:])
        if len(row.passages) <= len(tail):
            failures.append(
                "wg-arena3d rust t1: the whole message no longer holds more passages "
                f"than its last {TRUNCATED_FIELD_TAIL_CHARS} characters "
                f"({len(row.passages)} vs {len(tail)}) — the truncation control is dead")

    for f in failures:
        print(f"FAIL  {f}")
    print(f"disclosure selftest: {'FAILED' if failures else 'ok'} "
          f"({len(failures)} failures)")
    return 1 if failures else 0


# --------------------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", help="one run directory")
    ap.add_argument("--runs-dir", help="the whole tree (default: eval/runs/)")
    ap.add_argument("--trial", help="with --run-dir: print this trial's WHOLE message")
    ap.add_argument("--full", action="store_true",
                    help="with --run-dir: print every trial's WHOLE message, no cues, "
                         "no selection — the uninterpreted view")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--skip-corpus", action="store_true",
                    help="selftest: record the real-corpus pins as NOT MEASURED")
    args = ap.parse_args()

    if args.selftest:
        corpus = None if args.skip_corpus else Path(
            args.runs_dir or DEFAULT_RUNS).expanduser().resolve()
        return selftest(corpus)

    try:
        if args.run_dir:
            run_dir = Path(args.run_dir).expanduser().resolve()
            if args.trial:
                path = run_dir / "artifacts" / args.trial / "agent_result.json"
                if not path.is_file():
                    print(f"disclosure: no {path}", file=sys.stderr)
                    return 2
                agent = json.loads(path.read_text())
                status, reason = classify(agent.get("result"))
                print(f"{args.trial}  read from {path}")
                if status == "no_message":
                    print(f"NO MESSAGE — {reason}")
                    return 0
                print(agent["result"])
                return 0
            if args.full:
                # NO SELECTION AT ALL. The cue set is a convenience, and a convenience
                # that is the only way to see the evidence is a filter nobody chose. This
                # prints what each agent wrote, whole, and applies no judgement to it.
                for path in sorted((run_dir / "artifacts").glob(
                        "*/agent_result.json")):
                    agent = json.loads(path.read_text())
                    status, reason = classify(agent.get("result"))
                    print(f"\n{'=' * 78}\n{path.parent.name}  ({path})")
                    print("=" * 78)
                    if status == "no_message":
                        # Say why, then show the raw value anyway: this view exists so a
                        # reader never has to take this file's word for anything.
                        print(f"[{reason}]")
                    print(repr(agent.get("result")) if status == "no_message"
                          else agent["result"])
                return 0
            rows = scan_run(run_dir)
            print(BANNER)
            print()
            print(CAVEAT)
            print()
            print("\n".join(render_rows(rows, indent="  ")))
            print()
            print(summarise(rows))
            return 0
        rows = scan_tree(Path(args.runs_dir or DEFAULT_RUNS).expanduser().resolve())
    except DisclosureError as exc:
        print(f"disclosure: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([{
            "run": r.run, "trial_id": r.trial_id, "stack": r.stack, "game": r.game,
            "status": r.status, "reason": r.reason, "chars": r.chars,
            "terminal_reason": r.terminal_reason,
            "passages": [{"line": p.line, "cues": list(p.cues), "text": p.text}
                         for p in r.passages],
        } for r in rows], indent=2))
        return 0
    print(render_tree(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
