#!/usr/bin/env python3
"""Measure how far the four game-agnostic starters have drifted apart.

This is the check the coordinator asked for, and it is not paranoia: the earlier
Pong parity ports across these four stacks drifted, and the drift was invisible
because there was nothing measuring it. In a whole-game bake-off there are no held-out
unit tests to catch it either - if one starter is more helpful than another, that
difference is silently attributed to the stack.

Five comparisons, weakest to strongest:

  1. `just` recipe names           - do all four expose the same commands?
  2. AGENTS.md size and headings   - is one guide materially more helpful?
  3. Test counts                   - does one starter ship more safety net? An axis that
                                     could not be measured on a stack is REPORTED AS
                                     UNMEASURABLE and fails the tool; see `test_counts`.
  4. Harness files present         - hook, CI, version notes, lint config
  5. THE HASH CHAIN                - drive all four starters through the identical
                                     input tape and compare the per-tick state hashes.

(5) is the one that matters. If four independently written implementations of the same
placebo rules produce the same 64-bit hash at every tick, they are not merely similar,
they are the same simulation to the last float bit. If they diverge, the numbers in the
bake-off are comparing four different games.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe import ProbeError, ProbeSession  # noqa: E402

STACKS = ("rust", "ts", "unity", "godot")


def recipes(repo: Path) -> list[str]:
    out = subprocess.run(["just", "--summary"], cwd=repo, capture_output=True,
                         text=True)
    if out.returncode != 0:
        out = subprocess.run(["just", "--list"], cwd=repo, capture_output=True,
                             text=True)
        return sorted({ln.strip().split()[0] for ln in out.stdout.splitlines()[1:]
                       if ln.strip()})
    return sorted(out.stdout.split())


def agents_md(repo: Path) -> dict[str, Any]:
    p = repo / "AGENTS.md"
    if not p.exists():
        return {"words": 0, "headings": []}
    text = p.read_text(encoding="utf-8", errors="replace")
    return {"words": len(text.split()),
            "headings": [h.strip() for h in re.findall(r"^#{2,3}\s+(.+)$", text,
                                                       re.M)]}


def guide_text(repo: Path) -> str:
    p = repo / "AGENTS.md"
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


#: NEAR-MISS HEADINGS THAT HAVE BEEN ADJUDICATED, AND THE SENTENCE THAT SETTLES EACH.
#:
#: The near-miss note below keys on heading TEXT. Heading text is the one thing this file
#: already says equality may not be demanded of - the four guides are stack-native by
#: decision (`DECISIONS.md`, "Prompts are semantically identical but stack-native, not
#: byte-identical"), so a heading present in three guides and absent from the fourth is
#: two different situations wearing the same shape:
#:
#:   a FORGOTTEN COPY   an edit landed in three guides and not the fourth. One arm ran
#:                      without guidance the other three had. A real difference between
#:                      arms that nobody chose.
#:   a WORDING CHOICE   the fourth guide covers the same ground under its own heading, or
#:                      inside another section. Nothing is missing.
#:
#: Both rows measured on 2026-08-23 are the second kind, and the note could not say so:
#: it printed "check whether this is a section one guide never got" and re-asked every
#: run, forever, for two questions already answered.
#:
#: THE ENTRY IS NOT THE VERDICT - `substance` IS. Each entry names the sentence that
#: carries the guidance, and `heading_findings` reads it out of every guide on every run.
#: An adjudication that stops being true goes RED instead of going stale, which is the
#: property the rust row of `starters/_shared/launch.just` did not have: it asserted "no
#: audio feature, nothing to silence" for four matrices and nothing read it.
#:
#: Keyed (heading, the one stack whose guide lacks that heading).
ADJUDICATED_HEADINGS: dict[tuple[str, str], dict[str, str]] = {
    ("The one command", "ts"): {
        "substance": "green means done",
        "why": ("the ts guide opens with `## Commands` in the same position - first "
                "section, straight after the preamble - and it is the same contract: a "
                "command table, then `just verify` green means done, red means not done, "
                "nothing else is evidence. A heading rename, not a missing section"),
    },
    ("Gameplay is not correctness", "unity"): {
        "substance": "gameplay is not correctness",
        "why": ("the unity guide carries the paragraph in bold at the end of `## Testing` "
                "rather than under its own heading, with the same argument and the same "
                "instruction - assert on the consequence you care about, measured over a "
                "run, not on the constant you changed"),
    },
}


def heading_findings(hsets: dict[str, set[str]], texts: dict[str, str],
                     register: dict[tuple[str, str], dict[str, str]] | None = None,
                     ) -> tuple[list[str], list[str]]:
    """Adjudicate near-miss headings. Returns (problems, notes).

    A near miss is a heading in every guide but one. Whether that matters is a question
    about the GUIDANCE, not about the heading, so the answer is looked up in `register`
    and then CHECKED against the guides themselves:

      unadjudicated   a note, never a failure. Renaming a heading is legitimate and a
                      guard that fires on correct input is a guard that gets switched off
                      (#44, #57, #72). The note says NOT ADJUDICATED so it is visibly a
                      question rather than a verdict.
      adjudicated     the registered sentence must be present in EVERY guide. Absent from
                      the stack that lacks the heading, it is the forgotten copy after
                      all; absent from one that has it, the entry names the wrong
                      sentence. Either way the register is wrong and the tool goes red.
      dead entry      the row no longer fires - the heading was renamed or added. Noted
                      so the entry can be deleted rather than left asserting nothing.
    """
    reg = ADJUDICATED_HEADINGS if register is None else register
    problems: list[str] = []
    notes: list[str] = []
    stacks = sorted(hsets)
    n = len(stacks)
    if n < 3:
        return problems, notes

    fired: set[tuple[str, str]] = set()
    near = sorted({h for h in set().union(*hsets.values())
                   if len([s for s in stacks if h in hsets[s]]) == n - 1})
    for h in near:
        without = sorted(s for s in stacks if h not in hsets[s])
        adj = reg.get((h, without[0]))
        head = (f"AGENTS.md heading in {n - 1} of {n} guides, absent from {without}: "
                f"{h!r}")
        if adj is None:
            notes.append(f"{head} - NOT ADJUDICATED, reported and not failed. Wording "
                         f"differs by stack by design, so this is a question, not a "
                         f"finding: read {without[0]}'s guide and decide whether the "
                         f"section is covered elsewhere or was never copied. Record the "
                         f"answer in starter_parity.ADJUDICATED_HEADINGS so it is asked "
                         f"once")
            continue
        fired.add((h, without[0]))
        phrase = adj["substance"].lower()
        absent = [s for s in stacks if phrase not in texts.get(s, "").lower()]
        if absent:
            # WHICH of the two failures this is, decided here rather than left to the
            # reader: they need opposite repairs, and a message that lists both is a
            # message that gets skimmed.
            if without[0] in absent:
                why_red = (f"{without[0]} has neither the heading nor {adj['substance']!r}"
                           f", so this IS the forgotten copy the axis exists to find - the "
                           f"guidance is missing from one arm and the other three have it. "
                           f"Put it in {without[0]}'s guide (a starter edit: regime "
                           f"boundary, eval/RUNS.md note, re-run the gates)")
            else:
                why_red = (f"{sorted(absent)} HAS the heading but not {adj['substance']!r}"
                           f", so the register names a sentence that is not this section's "
                           f"substance. Re-key the entry to a sentence all "
                           f"{len(stacks)} guides really carry - do not delete the check")
            problems.append(f"{head} - the adjudication for it is NO LONGER TRUE. "
                            f"{why_red}")
        else:
            notes.append(f"{head} - ADJUDICATED as wording, not a forgotten copy: "
                         f"{adj['why']}. Verified this run: all {n} guides contain "
                         f"{adj['substance']!r}")

    for (h, s) in sorted(reg):
        if s in hsets and (h, s) not in fired:
            notes.append(f"AGENTS.md heading adjudication {(h, s)!r} no longer fires - "
                         f"{h!r} is no longer a near miss absent from {s!r}. The entry now "
                         f"asserts nothing; delete it, or re-key it if the heading moved")
    return problems, notes


def harness_files(repo: Path) -> dict[str, bool]:
    return {
        "stop_hook": (repo / ".claude" / "hooks" / "verify-gate.sh").exists(),
        "claude_settings": (repo / ".claude" / "settings.json").exists(),
        "ci_workflow": (repo / ".github" / "workflows" / "ci.yaml").exists(),
        "version_notes": any((repo / "docs").glob("*notes*")) if (repo / "docs").exists()
                         else False,
        "golden_image": bool(list(repo.rglob("golden/*.png"))),
    }


#: THE THREE THINGS A TEST-COUNT ROW CAN BE. It used to be able to be one thing - a pair of
#: numbers - and `0/0` was one of the pairs, which is why this axis measured nothing for as
#: long as it existed. An absent toolchain, a suite with no tests in it, and a summary in a
#: shape no parser here knows all print `0/0`, and so does a stack that ran and passed
#: everything it had, which is none. **Unmeasured is not agreement** - the same call this
#: project already made for a judge pack with no manifest ("unmeasurable, not clean").
TESTS_RAN = "ran"                    #: exit 0 AND a count came back: the number is real
TESTS_UNMEASURABLE = "unmeasurable"  #: a problem, and it is worded as unmeasurable not drift
TESTS_NOT_MEASURED = "not_measured"  #: `--skip-tests`: the operator opted out, on the record


def test_counts(repo: Path, timeout_s: int = 1200) -> dict[str, Any]:
    """Run `just test` and say what came back - INCLUDING whether it ran at all.

    The exit code was already collected here and read by nobody; `main` printed
    `passed/total` and drew no conclusion from `0/0`. That is a live pre-campaign gate
    reporting success while measuring nothing (AGENTS.md rule 1), and the input that
    produces it is ordinary: a git worktree has no `node_modules`, because it is untracked
    and exists only in the checkout it was installed in.
    """
    import static  # local import: pulls in runner.py's parsers
    c = static.run(repo, "test", ["just", "test"], timeout_s=timeout_s)
    passed, total = static.parse_test_counts(c.tail)
    if c.code != 0:
        status = TESTS_UNMEASURABLE
        why = f"`just test` exited {c.code}" + (f" - {c.note}" if c.note else "")
    elif total == 0:
        status = TESTS_UNMEASURABLE
        # The adversarial half: exit 0 alone would have called this fine. A recipe that
        # succeeds having run no test is exactly the shape rule 1 is about.
        why = ("`just test` exited 0 but no test summary could be parsed from its output - "
               "either the suite ran nothing, or its runner prints a summary shape "
               "`runner.parse_test_counts` does not know")
    else:
        status = TESTS_RAN
        why = ""
    return {"status": status, "exit": c.code, "passed": passed, "total": total,
            "seconds": round(c.seconds, 1), "why_unmeasurable": why,
            "output_tail": "" if status == TESTS_RAN else c.tail[-400:]}


def tests_cell(t: dict[str, Any] | None) -> str:
    """The printed column. It must never render an unmeasured axis as a pair of numbers."""
    if not t:
        return "?"
    if t["status"] == TESTS_RAN:
        return f"{t['passed']}/{t['total']}"
    if t["status"] == TESTS_NOT_MEASURED:
        return "not measured"
    return f"UNMEASURABLE({t['exit']})"


TAPE: list[dict[str, Any]] = (
    [{}] * 40 + [{"nudge_up": True}] * 40 + [{}] * 40
    + [{"nudge_down": True}] * 40 + [{}] * 240
)


def hash_chain(repo: Path) -> tuple[list[str], str]:
    try:
        with ProbeSession(repo=repo, seed=7) as s:
            for inp in TAPE:
                s.step_raw(inp)
            return [t.hash for t in s.history], ""
    except ProbeError as e:
        return [], str(e)


#: Recipes every stack MUST expose, because a building agent is told to use them and the
#: grading harness calls them by name. Anything beyond this is a stack tuning its own
#: workflow, which is the point of having four templates rather than one.
CORE_RECIPES = {"verify", "test", "lint", "fmt", "probe", "film", "run"}

#: THREE AXES THIS TOOL DID NOT COVER, each found by something breaking that it had no
#: opinion about. It compared recipes and hash chains, which are the axes somebody thought
#: of; the failures came from elsewhere.
#:
#:   launch discipline  - the shared `tools/launch.just`, byte-identical in all four. A
#:                        Unity player appeared on the operator's desktop with sound
#:                        because the guard was written per-recipe instead of per-resource.
#:   capability parity  - what can each starter do WITHOUT a pin change? See
#:                        `_capabilities`. Since DECISIONS.md (2026-08-22) the four are
#:                        deliberately unequal, so this axis is REPORTED and can never
#:                        fail. The row that still matters most is audio, because the
#:                        task asks every agent for sound on a SCORED criterion: godot
#:                        and ts always could, rust gained it in task 26, and unity in
#:                        task 52 (`com.unity.modules.audio`). ALL FOUR now can, so the
#:                        audio row no longer discriminates - and that is the row to
#:                        re-read before attributing any audio result to a stack, since
#:                        every trial graded before 2026-08-23 ran with an arm that
#:                        could not compile `AudioSource` at all (measured: CS1069).
#:   capture geometry   - see tools/frame_parity.py; one submission filmed at 768x576
#:                        while 21 filmed at 640x400 (#59).
SHARED_LAUNCH = "tools/launch.just"


#: CAPABILITY DIVERGENCE IS THE DESIGN, NOT DRIFT.
#:
#: `DECISIONS.md` ("The templates are measured at each stack's best, not at a common
#: floor", 2026-08-22) settled this: every template exposes what ITS stack ships, and
#: the four are deliberately not equal. So a capability difference reported here is a
#: statement about the stacks, and the only thing this tool may do with it is SAY SO.
#:
#: Reading it as drift and "fixing" it would restore the common floor by the back door,
#: through a guard nobody voted for - and a guard that is permanently red on a condition
#: the project decided is acceptable is a guard that gets switched off (#44, #57, #72).
#:
#: Every probe reads an ARTIFACT - a manifest, a Cargo.toml - never a doc. The rust row
#: of `starters/_shared/launch.just` asserted "no audio feature, nothing to silence" for
#: four matrices, and nothing could have caught it going stale because nothing read it.
def _capabilities(root):
    """What this starter's stack can do WITHOUT the agent changing a pin.

    Returns {capability: True | False | None}. `None` means "not established here",
    which is different from `False` and must never be counted as one.
    """
    import json as _j
    s = root.name
    caps = {}
    if s == "unity":
        try:
            deps = _j.loads((root / "Packages" / "manifest.json").read_text())
            deps = deps.get("dependencies", {})
        # Narrow: absent or unreadable manifest (OSError), not JSON
        # (JSONDecodeError), or JSON that is not an object so `.get` is absent
        # (AttributeError). None means "could not tell", which is a distinct parity
        # answer from False -- and a defect in this function must not masquerade as it.
        except (OSError, _j.JSONDecodeError, AttributeError):
            deps = None
        caps["audio"] = None if deps is None else ("com.unity.modules.audio" in deps)
        caps["particles"] = (None if deps is None
                             else ("com.unity.modules.particlesystem" in deps))
        caps["physics_3d"] = None if deps is None else ("com.unity.modules.physics" in deps)
        # Built-in RP with no render-pipeline asset: lit 3D and real-time shadows are on
        # out of the box. research/10-stack-capability-matrix.md section 6.3, measured.
        caps["lit_3d"] = True
    elif s == "rust":
        try:
            txt = (root / "crates" / "game" / "Cargo.toml").read_text()
        except OSError:
            txt = None
        if txt is None:
            caps = dict.fromkeys(("audio", "particles", "physics_3d", "lit_3d"))
        else:
            # The feature list IS the capability list for this arm. `MeshMaterial3d`
            # lives in bevy_pbr, which only the `3d` bundle pulls in, and `AudioPlayer`
            # only exists behind `bevy_audio`.
            full = "default-features = false" not in txt
            caps["audio"] = full or ('"audio"' in txt) or ('"bevy_audio"' in txt)
            caps["lit_3d"] = full or ('"3d"' in txt)
            caps["particles"] = False   # bevy 0.19 ships none at any feature setting
            caps["physics_3d"] = False  # needs a crate; avian/rapier are not pinned
    elif s == "godot":
        caps["audio"] = True        # engine built-in
        caps["particles"] = True    # GPUParticles2D/3D, CPUParticles2D/3D in ClassDB
        caps["physics_3d"] = True   # Godot Physics is the default; Jolt is in-tree
        caps["lit_3d"] = True
    elif s == "ts":
        caps["audio"] = True        # Web Audio API, no dependency
        caps["particles"] = False   # `Points`/`Sprite` only; no emitter in three 0.185
        caps["physics_3d"] = False  # examples/jsm/physics/* fetch an engine from a CDN
        caps["lit_3d"] = True       # MeshStandardMaterial + lights, on SwiftShader
    return caps


def _audio_capability(root):
    """The audio row on its own. It keeps a name because it is the one capability with a
    SCORED criterion behind it, and because callers grep for it."""
    return _capabilities(root).get("audio")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--starters", type=Path,
                    default=Path(__file__).resolve().parent.parent / "starters")
    ap.add_argument("--stacks", nargs="*", default=list(STACKS))
    ap.add_argument("--skip-tests", action="store_true",
                    help="skip `just test` (slow on Unity)")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()

    present = [s for s in a.stacks if (a.starters / s).exists()]
    missing = [s for s in a.stacks if s not in present]
    report: dict[str, Any] = {"present": present, "missing": missing, "stacks": {}}
    problems: list[str] = []
    notes: list[str] = []

    # A STACK THAT WAS ASKED FOR AND IS NOT THERE IS NOT AGREEMENT EITHER. `--stacks` names
    # what to compare, so an absent one is a subject that could not be measured - the same
    # shape as `0/0`, and it printed as a header line while the tool exited 0.
    if not present:
        problems.append(f"no starter was compared at all - nothing under {a.starters} "
                        f"matched {a.stacks}. Every axis below is vacuously green over an "
                        f"empty set, which is the one result this tool must never print")
    if missing:
        problems.append(f"asked for {missing} and found no such starter under "
                        f"{a.starters} - a stack that could not be looked at cannot be "
                        f"reported as agreeing with the others; name only the stacks that "
                        f"are there if that is what you meant")

    for s in present:
        repo = a.starters / s
        d: dict[str, Any] = {
            "recipes": recipes(repo),
            "agents_md": agents_md(repo),
            "harness": harness_files(repo),
        }
        # The axis is ALWAYS in the report. `--skip-tests` records an explicit opt-out
        # rather than leaving a hole, because a missing key and a measured agreement are
        # the same thing to every reader downstream.
        d["tests"] = (test_counts(repo) if not a.skip_tests
                      else {"status": TESTS_NOT_MEASURED, "exit": None, "passed": None,
                            "total": None, "seconds": None,
                            "why_unmeasurable": "--skip-tests", "output_tail": ""})
        chain, err = hash_chain(repo)
        d["hash_chain_len"] = len(chain)
        d["hash_error"] = err
        d["_chain"] = chain
        report["stacks"][s] = d

    # 1. recipes
    sets = {s: set(report["stacks"][s]["recipes"]) for s in present}
    if sets:
        common = set.intersection(*sets.values())
        # ONLY THE CORE RECIPES ARE REQUIRED EVERYWHERE. The four templates are
        # deliberately tuned per stack, so `analyzers` (unity), `api-notes` (ts) and
        # `quick` (rust) exist on one stack by design. Requiring set equality made this
        # check fire on EVERY stack on EVERY run, which is not a guard - it is noise
        # that guarantees the tool can never go green (FINDINGS #44, #57).
        for s in present:
            missing_core = sorted(CORE_RECIPES - sets[s])
            if missing_core:
                problems.append(f"{s} is missing CORE recipes {missing_core} - every "
                                f"stack must expose the same contract to a building agent")
            notes.append(f"recipes only in {s}: {sorted(sets[s] - common)}")

    # 2. AGENTS.md
    words = {s: report["stacks"][s]["agents_md"]["words"] for s in present}
    if words:
        lo, hi = min(words.values()), max(words.values())
        if lo and hi / lo > 1.35:
            problems.append(f"AGENTS.md sizes span {lo}-{hi} words "
                            f"({hi / lo:.2f}x) - one guide may be materially more "
                            f"helpful than another")

    # 2b. AGENTS.md HEADINGS. Collected since this tool was written, named in its own
    # docstring, and read by nothing until 2026-08-23 - the same defect as the test-count
    # exit code, one axis over. Three of the four guides head the determinism section with
    # three different sentences ON PURPOSE, so heading TEXT is not a key that equality may
    # be demanded of; what is worth a human's eye is the shape a forgotten copy leaves - a
    # section that reached every stack but one.
    #
    # A near miss alone cannot tell those apart, and printing the question every run is not
    # a check. `heading_findings` looks the row up in ADJUDICATED_HEADINGS and then
    # verifies the adjudication against the guides, so a verdict that stops being true goes
    # red instead of going quiet.
    hsets = {s: set(report["stacks"][s]["agents_md"]["headings"]) for s in present}
    htexts = {s: guide_text(a.starters / s) for s in present}
    hprob, hnotes = heading_findings(hsets, htexts)
    problems.extend(hprob)
    notes.extend(hnotes)
    # WHAT THE AXIS DID, not only what it concluded: which rows it saw and which
    # adjudication it verified, so a later reader can ask what was checked on a given run
    # rather than trusting that it was.
    report["heading_near_misses"] = {
        h: sorted(s for s in present if h not in hsets[s])
        for h in sorted({h for h in set().union(*hsets.values()) if len(present) >= 3
                         and len([s for s in present if h in hsets[s]]) == len(present) - 1})
    }
    report["heading_adjudications"] = {
        f"{h} :: {s}": {**adj,
                        "substance_present_in": sorted(
                            k for k in present
                            if adj["substance"].lower() in htexts[k].lower())}
        for (h, s), adj in ADJUDICATED_HEADINGS.items() if s in present
    }

    # 3. TEST COUNTS - and the point of this block is that `0/0` is not one of the answers
    measured: dict[str, tuple[int, int]] = {}
    skipped: list[str] = []
    for s in present:
        t = report["stacks"][s]["tests"]
        if t["status"] == TESTS_RAN:
            measured[s] = (t["passed"], t["total"])
        elif t["status"] == TESTS_NOT_MEASURED:
            skipped.append(s)
        else:
            problems.append(
                f"{s}: the test-count axis is UNMEASURABLE, which is NOT the same as "
                f"agreement - {t['why_unmeasurable']}. The row would have read "
                f"{t['passed']}/{t['total']}, and two zeros are what an absent toolchain, "
                f"an empty suite and a suite nobody could start all print. Fix: run where "
                f"this stack's toolchain is installed (a git WORKTREE has no node_modules "
                f"- it is untracked and lives only in the checkout it was installed in), "
                f"or pass --skip-tests to put the opt-out on the record. Last output: "
                f"{' '.join(t['output_tail'].split())[-220:]}")
    if skipped:
        notes.append(f"test counts NOT MEASURED on {skipped} (--skip-tests). The axis is "
                     f"declared unmeasured on purpose, which is why it is a note and not a "
                     f"finding; it is NOT evidence that those starters agree on it.")
    # Reported over the stacks that MEASURED, with n stated, and never over a mixed
    # population (rule 4). It is a note and not a guard: the four suites are deliberately
    # different sizes, so a spread limit here would be permanently red (#44, #57).
    if len(measured) > 1:
        rows = ", ".join(f"{s} {p}/{tt}" for s, (p, tt) in sorted(measured.items()))
        tots = [tt for _, tt in measured.values()]
        notes.append(f"test counts over the {len(measured)} stack(s) that MEASURED: {rows}"
                     f" - spread {min(tots)}-{max(tots)} tests "
                     f"({max(tots) / min(tots):.2f}x). Reported, never failed; suite size "
                     f"is a property of the stack, and this row is here so a change in it "
                     f"is visible rather than inferred.")

    # 4. harness files
    for key in ("stop_hook", "claude_settings", "ci_workflow", "version_notes",
                "golden_image"):
        vals = {s: report["stacks"][s]["harness"][key] for s in present}
        if len(set(vals.values())) > 1:
            problems.append(f"harness file mismatch on {key}: {vals}")

    # 5. the hash chain - the one that matters
    chains = {s: report["stacks"][s]["_chain"] for s in present
              if report["stacks"][s]["_chain"]}
    failed = [s for s in present if not report["stacks"][s]["_chain"]]
    for s in failed:
        problems.append(f"{s}: probe did not run - "
                        f"{report['stacks'][s]['hash_error'][:180]}")
    if len(chains) > 1:
        ref_stack = sorted(chains)[0]
        ref = chains[ref_stack]
        for s, ch in sorted(chains.items()):
            if s == ref_stack:
                continue
            if len(ch) != len(ref):
                problems.append(f"{s}: chain length {len(ch)} vs {ref_stack} "
                                f"{len(ref)}")
                continue
            div = next((i for i, (x, y) in enumerate(zip(ref, ch)) if x != y), None)
            if div is None:
                report.setdefault("hash_identical_to", {})[s] = ref_stack
            else:
                # CROSS-STACK HASH EQUALITY IS NOT A GOAL, and DECISIONS.md says so:
                # "the requirement is within-stack determinism only - cross-stack hash
                # equality is not achievable and is not a goal. Unity's 1-ULP
                # divergence is a Mono/ARM64 property (FMA contraction) not reachable
                # from source."
                #
                # This check failed on it anyway, so the tool exited 1 on a condition
                # the project had formally decided was acceptable - and a guard that is
                # permanently red is a guard nobody reads. Reported, not failed.
                notes.append(
                    f"{s} diverges from {ref_stack} at tick {div}: "
                    f"{ref[div]} vs {ch[div]}. Cross-stack hash equality is NOT a "
                    f"goal (DECISIONS.md); within-stack determinism is what is "
                    f"enforced, and `determinism.replay` measures it per stack.")

    # -- the shared launch file must be byte-identical everywhere -------------- #
    import hashlib
    hashes = {}
    for s in present:
        f = a.starters / s / SHARED_LAUNCH
        hashes[s] = (hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                     if f.is_file() else "MISSING")
    src = a.starters / "_shared" / "launch.just"
    if src.is_file():
        hashes["_shared"] = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    distinct = set(hashes.values())
    if len(distinct) != 1:
        problems.append(f"the shared launch file differs between starters: {hashes} - "
                        f"it is ONE source (`starters/_shared/launch.just`) copied into "
                        f"each tree, and four copies that can drift is the thing it "
                        f"exists to prevent")
    else:
        # HOW MANY copies agreed, not "all four": under `--stacks ts` this line compared
        # two files and said four, which is the same overclaim the test axis was making.
        notes.append(f"shared launch discipline identical across the {len(hashes)} copies "
                     f"compared ({sorted(hashes)}): {distinct.pop()}")
    report["launch_hashes"] = hashes

    # -- capability register: reported, never failed --------------------------- #
    caps = {s: _capabilities(a.starters / s) for s in present}
    report["capabilities"] = caps
    report["audio_capability"] = {s: c.get("audio") for s, c in caps.items()}
    names = sorted({k for c in caps.values() for k in c})
    notes.append(
        "CAPABILITY PARITY IS NOT A GOAL, AND THE ROWS BELOW ARE NOT DRIFT. DECISIONS.md "
        "(2026-08-22) puts every template at its own stack's best rather than at a floor "
        "all four share, so a difference here is the SUBJECT of the comparison. Reported, "
        "never failed - a guard that fired on these would be re-imposing the common floor "
        "through the back door.")
    for cap in names:
        row = {s: caps[s].get(cap) for s in present}
        if len(set(row.values())) <= 1:
            continue
        yes = sorted(k for k, v in row.items() if v is True)
        no = sorted(k for k, v in row.items() if v is False)
        unknown = sorted(k for k, v in row.items() if v is None)
        line = f"  {cap}: {yes} yes / {no} no"
        if unknown:
            line += f" / {unknown} NOT ESTABLISHED (which is not the same as no)"
        notes.append(line)
    notes.append(
        "  audio is the row with a SCORED criterion behind it, and since task 52 all four "
        "starters carry it: rust gained it under task 26 (bevy's own default feature set), "
        "unity under task 52 (com.unity.modules.audio, +1 manifest line and +6 lock, both "
        "resolved `builtin` from the installed editor). A row that no longer varies cannot "
        "explain anything about a run graded AFTER the change - and it explains less than "
        "it looks like about runs graded BEFORE it, because when it was unequal the effect "
        "was REAL BUT MEASURED SMALL: rust's dependency work was 12-14 lines in Cargo.toml "
        "and unity's is one, while ALL FOUR stacks then author a ~300-line WAV synthesiser "
        "(ts 320, rust 340, unity 305, godot 46 on top of the engine's built-in). See "
        "eval/IMPROVEMENTS.md.")
    notes.append(
        "  particles now splits 2/2 rather than 1/3: godot and unity ship an engine "
        "particle system (GPUParticles2D; Shuriken), rust and ts ship none at any pin. "
        "That is the widest EFFORT gap in research/10-stack-capability-matrix.md and it is "
        "the reason the templates must not hand a rust or ts agent an emitter - writing "
        "one is the work being measured.")

    # -- recipe BEHAVIOUR now differs by stack; say so before it looks like drift --- #
    notes.append(
        "`run` is GATED DURING TRIALS ON RUST ONLY: Bevy 0.19 on macOS keeps the "
        "application frontmost even with the window hidden and minimised (measured three "
        "ways); godot and unity have working no-raise hooks and ts opens no window. The "
        "rust recipe refuses when STARTER_NO_RAISE=1 and explains why. Reported, not "
        "failed - it is a property of that engine on this OS. See "
        "starters/_shared/launch.just.")

    for d in report["stacks"].values():
        d.pop("_chain", None)
    report["problems"] = problems
    report["notes"] = notes

    print(f"starters present: {present}" + (f"  MISSING: {missing}" if missing else ""))
    print(f"\n{'stack':<8} {'recipes':>8} {'AGENTS':>8} {'tests':>17} {'chain':>7} "
          f"{'hook':>5} {'ci':>4}")
    for s in present:
        d = report["stacks"][s]
        print(f"{s:<8} {len(d['recipes']):>8} {d['agents_md']['words']:>8} "
              f"{tests_cell(d.get('tests')):>17} "
              f"{d['hash_chain_len']:>7} "
              f"{'yes' if d['harness']['stop_hook'] else 'NO':>5} "
              f"{'yes' if d['harness']['ci_workflow'] else 'NO':>4}")
    if report.get("hash_identical_to"):
        for s, ref in report["hash_identical_to"].items():
            print(f"\n  hash chain over {len(TAPE)} scripted ticks: {s} is "
                  f"BYTE-IDENTICAL to {ref}")
    if notes:
        print(f"\nEXPECTED AND ACCEPTED - {len(notes)} note(s), not failures:")
        for nline in notes:
            print(f"  {nline}")
    if problems:
        # Not all of these are drift. An axis that could not be measured on a stack is
        # reported here too, because the alternative is the tool saying nothing about it.
        print(f"\nDRIFT OR UNMEASURABLE - {len(problems)} finding(s):")
        for p in problems:
            print(f"  {p}")
    else:
        # WHICH axes were measured, before the sentence that says they agree. The tool
        # exited 0 on "No drift detected on any measured axis" while one stack's test
        # count was `0/0` because its toolchain was absent, and that sentence was quoted
        # into eval/RUNS.md as evidence (2026-08-23).
        n_ran = sum(1 for s in present
                    if report["stacks"][s]["tests"]["status"] == TESTS_RAN)
        print(f"\naxes measured: recipes, AGENTS.md, harness files, shared launch file and "
              f"the hash chain on {len(present)} stack(s); test counts really ran on "
              f"{n_ran} of {len(present)}.")
        print("No drift detected on any measured axis.")
    if a.json:
        a.json.write_text(json.dumps(report, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
