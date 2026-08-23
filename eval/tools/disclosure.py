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
the reader adjudicates. It is **not** a classifier and its count is **not** the disclosure
rate — the hand-classified rate is 31 of 75, recorded in `eval/RUNS.md` under "DECLINED:
requiring a finish-report section in the starters". Measured against that hand pass on the
same 75 messages, this locator fires on 26: godot 3/15 (hand 3), rust 12/21 (hand 13), ts
3/23 (hand 4), unity 8/16 (hand 11). It under-reports, it under-reports in every arm, and
the shape it reports is the same one the hand pass found. Quote the hand figure for a rate;
quote this one only as "trials with at least one located passage".

It locates a **second family** the hand pass did not count: the agent reporting that the
starter arrived broken. That is where #98 was recovered from, and it is one-arm bias —
`build.compiles` and `verify.green` are the exit codes of the submission's own recipes, so
a starter red on a pristine tree costs one arm two tier-1 criteria and no other. Seven
trials carry such a passage; four of them are Rust agents in three different runs reporting
the same thing about `just run` (`tasks/81`), which nothing had noticed in ten days of
stored evidence.

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
| `no_message` | `null`, or the API's limit string. **Unmeasurable**, never "quiet" |

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
    # A SECOND FAMILY, and the one #98 was recovered from: the agent reporting that the
    # STARTER was broken before it touched anything. That is one-arm bias — a red gate on
    # a pristine tree hands every submission in that arm two automatic tier-1 failures —
    # and no tier measures it, because the agent usually repairs it and the score then
    # looks identical to an arm that never had the problem. It fires on defects the agent
    # went on to fix, deliberately: what it cost was turns and money, which nothing counts.
    ("starter", re.compile(
        r"\b(?:starter|baseline|harness|template|scaffold)\b[^.;]{0,70}?"
        r"\b(?:already\s+(?:red|broken|failing)|was\s+(?:already\s+)?(?:red|broken)"
        r"|is\s+red|broken\s+(?:in|before|on arrival))"
        r"|\b(?:was|were)\s+(?:already\s+)?(?:red|broken|failing)\b[^.;]{0,40}?"
        r"\bbefore\s+(?:I|we|any)\b"
        # Word order is not the property. The property is "it arrived broken", and the
        # corpus states it both ways round.
        r"|\b(?:was|were)\s+broken\s+in\s+the\s+(?:starter|template|harness)\b", re.I)),
]

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
    artifacts = run_dir / "artifacts"
    if not artifacts.is_dir():
        raise DisclosureError(f"no artifacts directory at {artifacts}")
    dirs = [d for d in sorted(artifacts.iterdir())
            if d.is_dir() and (d / "agent_result.json").is_file()]
    if not dirs:
        raise DisclosureError(
            f"{artifacts} holds no <trial>/agent_result.json — refusing to report 0")
    return [read_trial(d) for d in dirs]


def scan_tree(runs_dir: Path) -> list[Row]:
    if not runs_dir.is_dir():
        raise DisclosureError(
            f"no runs directory at {runs_dir} (it is gitignored; an agent worktree does "
            f"not have one — read the main checkout)")
    paths = sorted(runs_dir.glob("*/artifacts/*/agent_result.json"))
    if not paths:
        raise DisclosureError(
            f"{runs_dir} holds no */artifacts/*/agent_result.json — refusing to report 0")
    return [read_trial(p.parent) for p in paths]


# --------------------------------------------------------------------------- rendering

BANNER = (
    "--- what each agent said about its OWN work "
    "(whole message: artifacts/<trial>/agent_result.json .result) ---")

CAVEAT = (
    "A LOCATOR, NOT A VERDICT. These are the agent's own sentences that mention something\n"
    "unverified, a residual risk, or a starter that arrived broken; read them, do not count\n"
    "them. `quiet` means no cue matched, NOT that the trial disclosed nothing — the\n"
    "hand-classified rate over the stored corpus is 31 of 75 (eval/RUNS.md) and this locator\n"
    "finds 26. `NO MESSAGE` is unmeasurable, not silence: `.result` was null, or held the\n"
    "API's own limit string where agent text would be.")


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
    return (f"{len(rows)} trials: {n_p} with located passages, {n_q} quiet, "
            f"{n_n} with no agent message (unmeasurable)")


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
    lines.append("per stack, messages the agent actually wrote "
                 "(locator / read)   [hand-classified: eval/RUNS.md]")
    per_stack: dict[str, list[Row]] = collections.defaultdict(list)
    for row in rows:
        if row.status != "no_message":
            per_stack[row.stack].append(row)
    for stack in sorted(per_stack):
        group = per_stack[stack]
        located = sum(1 for r in group if r.status == "passages")
        lines.append(f"  {stack:<8} {located:>2} / {len(group)}")
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

# #98's own evidence: both graded Godot agents named the red starter gate. The `starter`
# cue must be the one that fires on them, not merely some other passage in the same
# message — otherwise the family could be dead and the row would still look pinned.
MUST_LOCATE_STARTER = [
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t0"),
    ("wg-g4c-2026-08-21T02-26-46", "g4_platformer__godot__t1"),
]

# eval/RUNS.md records archive-arena2d at a 0% hand-classified disclosure rate over its
# n=3 readable messages. All three must come back quiet, and two of them carry phrasing
# that broke earlier drafts of the cue set ("I have not committed anything", "verify
# never executes `main.ts`").
MUST_BE_QUIET = [
    ("archive-arena2d-wg-audio48", "g3_arena__rust__t0"),
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
    "Bare `cargo run -p game` failed with \"could not determine which binary to run\".",
    "## Two things worth flagging",
    # The starter family must not fire on a starter merely being mentioned, nor on a
    # defect the agent introduced and then found in its own work.
    "The starter's HUD is the worked example for anything you add.",
    "I broke the golden frame myself and re-blessed it.",
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
    # The starter family, both word orders the corpus uses.
    "**The starter baseline was already red here**, before I touched anything.",
    "- **The baseline was already red.** `tools/check.gd` called `reload()`.",
    "- **`just run` was broken in the starter** and I fixed it.",
]


def selftest(runs_dir: Path | None) -> int:
    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # ---- direction 1: the located set can be EMPTIED. A cue set that cannot go quiet is
    # a check that cannot fail, and would report every message as a disclosure.
    saved = list(CUES)
    try:
        CUES.clear()
        for text in VARIANTS_LOCATED:
            if passages(text):
                failures.append(f"mutant (cues removed) still located: {text[:60]!r}")
    finally:
        CUES[:] = saved
    # ...and with the cues restored, every one of them must come back.
    for text in VARIANTS_LOCATED:
        if not passages(text):
            failures.append(f"restored cues failed to locate: {text[:60]!r}")

    # ---- direction 1b: EVERY cue family must be load-bearing for something. Removing one
    # has to silence at least one string this file claims it locates. A family that can be
    # deleted with no expectation changing is either dead or duplicated, and both look
    # exactly like a working cue from the outside.
    for name, _ in saved:
        CUES[:] = [c for c in saved if c[0] != name]
        try:
            silenced = [t for t in VARIANTS_LOCATED if not passages(t)]
        finally:
            CUES[:] = saved
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
        for run, tid in MUST_LOCATE_STARTER:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if not any("starter" in p.cues for p in row.passages):
                failures.append(f"{run}/{tid}: #98's red-starter disclosure was not "
                                f"located by the `starter` cue")
        for run, tid in MUST_BE_QUIET:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.status != "quiet":
                failures.append(f"{run}/{tid}: documented non-discloser came back "
                                f"{row.status} {[p.text[:60] for p in row.passages]}")
        for run, tid in MUST_BE_NO_MESSAGE:
            row = read_trial(runs_dir / run / "artifacts" / tid)
            if row.status != "no_message":
                failures.append(f"{run}/{tid}: an aborted trial came back {row.status}")
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
