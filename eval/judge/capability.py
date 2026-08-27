#!/usr/bin/env python3
"""What the evidence pipeline can see about PERFORMANCE and CAPTURE, per submission.

    python3 judge/capability.py --runs eval/runs            # distribution + gate
    python3 judge/capability.py --runs eval/runs --json     # the raw records

--------------------------------------------------------------------------------
WHY THIS IS HARNESS-SIDE AND NOT IN THE PROBE CONTRACT
--------------------------------------------------------------------------------
Task 25 asked for "the same performance fields with the same units for all four
stacks". The obvious place to put them is the probe contract in
`starters/_shared/`, so each submission reports its own numbers. That was
rejected, for three reasons, in increasing order of weight:

1. Editing `starters/` is a regime boundary. Runs before and after stop being
   comparable, and `verify_blind.py` / `starter_parity.py` have to be re-run.
   Every field below is measured from OUTSIDE, so no starter changes and every
   stored run stays in the comparison.

2. Three of these fields were ALREADY in every one of the 68 stored
   `programmatic.json` records the corpus held when this was decided. Nothing read
   them. Surfacing what the harness already writes gives a distribution today, on
   real runs, for nothing.

3. The decisive one. **A field the submission reports is a field the submission
   can fail to report, and that failure correlates with stack** - which is this
   project's most repeated defect (#62, #72, #77). A field the harness measures
   through a mechanism that is byte-identical for all four arms cannot produce a
   stack-correlated gap; the gap would have to be in the harness, where one fix
   covers every arm. Uniformity by construction beats uniformity by instruction.

--------------------------------------------------------------------------------
WHAT THESE NUMBERS ARE, AND THE ONE THING THEY ARE NOT
--------------------------------------------------------------------------------
**None of them is a frame rate, and none of them may be read across arms as one.**
`research/10-stack-capability-matrix.md` §3 established that the four arms do not
render the judged frames on comparable hardware: Rust, Unity and Godot draw on the
machine's M3 Max, and the TypeScript arm draws on **SwiftShader, a CPU
rasteriser**. Any frametime or fps field would therefore report the renderer
backend, not the stack - a 60-fold instrument effect wearing the costume of a
result. See `DECLINED` below, which is the load-bearing half of this module.

What is here instead is honest and dull: how big the capture was, how long it took
in wall, CPU and memory, and how fast the headless probe answers. Every one is
measured the same way on all four arms.

**`probe.ticks_per_second` is the one field with real cross-arm spread, and it is
not a stack ranking either.** Partitioned by game over the 68 stored submissions
(2026-08-23) the ordering is stable — Godot lowest in all four games, Rust and Unity
highest — but the WITHIN-cell spread reaches 2.8x (`g1_pong__rust`, 13,998 to
38,876), which is wider than most of the gaps between arms. And it is a round trip
over a pipe: engine, JSON encoding and IPC, not simulation cost. It says how fast a
stack answers the probe, which is what it is named after, and nothing more.

--------------------------------------------------------------------------------
TWO TASK CLASSES, AND ONLY ONE OF THEM CARRIES THE FOUR-ARM CLAIM
--------------------------------------------------------------------------------
Games and scenes are separate task classes (`eval/AGENTS.md`), and a record's class
comes from `aspects.task_class`. Every distribution below is printed per class,
because a min/median/max over both is an aggregate across a population nobody
established was homogeneous.

`GATE_TASK_CLASS` narrows exactly one question - *are all four arms present?* - to the
game submissions, because four arms is a property of the game matrix and the scene
class has been built on 1 arm. Everything else the gate asks is asked of every record,
and `population_sentence()` prints what the narrowing left out. **Excluded is not
unread**, and until 2026-08-27 it was neither: `TRIAL_RE` matched `g` alone, so the one
stored scene submission parsed to stack `?` and no per-stack partition here could see
it at all.

--------------------------------------------------------------------------------
NOTHING HERE IS A CRITERION, DELIBERATELY
--------------------------------------------------------------------------------
Capturing is cheap and reversible; scoring changes what agents optimise for and is
a regime boundary. The ticket forbids doing both in one change, because a
criterion introduced alongside its own measurement has no baseline to calibrate
against. `judge/RUBRIC.md` weighs none of this.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aspects  # noqa: E402

# --------------------------------------------------------------------------- #
# The contract
# --------------------------------------------------------------------------- #

#: field -> unit. The unit is part of the contract: "the same fields with the same
#: units for all four stacks" is the thing task 25 asked for, and a field whose unit
#: is implicit is a field two readers will disagree about.
FIELDS: dict[str, str] = {
    "capture.width_px":       "pixels",
    "capture.height_px":      "pixels",
    "capture.megapixels":     "megapixels (w*h/1e6)",
    "capture.frames":         "count of PNGs written by `just film`",
    "capture.wall_seconds":   "seconds, wall clock, whole `just film` invocation",
    "capture.cpu_seconds":    "seconds, user+system CPU, `just film` and its descendants",
    "capture.peak_rss_mb":    "MiB, peak resident set of the largest process in the "
                              "`just film` tree",
    "probe.ticks_per_second": "ticks/second answered by `just probe` over a pipe, "
                              "headless, nothing rendered",
    "probe.startup_seconds":  "seconds from `just probe` exec to its tick-0 line",
}

#: Why a field is null. The distinction is the whole point: only the first is a
#: defect in the contract.
STACK_CANNOT = "stack_cannot"            #: this arm has no mechanism. GATE FAILURE.
SUBMISSION = "submission_failed"         #: the command failed or the artifact is bad.
NOT_CAPTURED = "not_captured_in_this_run"  #: the harness did not record it back then.
REASONS = (STACK_CANNOT, SUBMISSION, NOT_CAPTURED)

#: The capture geometry every starter ships with - `VIEW_WIDTH` x `VIEW_HEIGHT`, the
#: same pair in all four of `starters/{rust,ts,unity,godot}`. It is spelled here as
#: well as there, and `capability_selftest.py` reads it back out of all four starter
#: sources and compares: a second, independent statement of the fact rather than a
#: shared object, which is what a control needs (AGENTS.md rule 12).
STARTER_DEFAULT_GEOMETRY = (640, 400)


#: Fields considered and DELIBERATELY NOT CAPTURED. This register is the answer to
#: task 25, as much as `FIELDS` is: the ticket says an honest "these are reportable
#: and these are not, here is why" closes it, and a field list nobody argued against
#: does not.
#:
#: `would_change` is what stops this becoming a graveyard: each entry names the
#: measurement that would move it back into `FIELDS`.
DECLINED: dict[str, dict[str, str]] = {
    "render.frametime_ms": {
        "why": "The TypeScript arm films on SwiftShader, a CPU rasteriser, while the "
               "other three film on the machine's M3 Max. A frametime field would "
               "report the renderer backend across arms, not the stack. It is also "
               "ill-defined here: `just film` renders 12 single frames of a "
               "deterministic replay in every arm, so there is no steady loop to "
               "measure - the number would be dominated by engine start-up.",
        "source": "research/10-stack-capability-matrix.md §3 'Which arm renders on "
                  "what'; harness.ts:287, capture.ts:50",
        "would_change": "A real GPU backend for the TS capture path (Playwright has "
                        "no WebGPU here in any of eight configurations tested), plus a "
                        "sustained-render recipe distinct from `film`.",
    },
    "render.fps": {
        "why": "Same defect as frametime_ms, and worse: it invites a direct cross-arm "
               "ranking, which is exactly the comparison the SwiftShader asymmetry "
               "makes invalid.",
        "source": "research/10-stack-capability-matrix.md §3",
        "would_change": "As render.frametime_ms.",
    },
    "render.draw_calls": {
        "why": "Three of four arms expose a counter and one does not, which is the "
               "stack-correlated gap this module exists to avoid (#62, #72, #77). "
               "three has renderer.info.render.calls, Godot has "
               "RenderingServer.get_rendering_info, Unity has UnityStats.drawCalls "
               "(editor-only). Bevy 0.19 ships no draw-call diagnostic: "
               "bevy_diagnostic exposes fps, frame_time, frame_count, entity_count "
               "and process/system cpu+mem, and nothing about draw calls.",
        "source": "bevy_diagnostic-0.19.0/src/*.rs, enumerated 2026-08-23",
        "would_change": "A draw-call diagnostic in Bevy, or a wgpu-level counter the "
                        "starter could wrap without the agent having to opt in.",
    },
    "render.vram_mb": {
        "why": "No cross-stack API. wgpu does not report device-local allocation, "
               "three reports only its own texture/geometry counts, and Unity's "
               "figure is editor-only. A number available on some arms is worse than "
               "no number.",
        "source": "research/10-stack-capability-matrix.md §6.9",
        "would_change": "Metal-level allocation accounting outside the process, which "
                        "would be uniform across all four because none of them would "
                        "be reporting it.",
    },
    "render.ray_tracing": {
        "why": "Unreachable in all four arms at the pinned versions, so the field "
               "would be a constant. Bevy's Solari needs BUFFER_BINDING_ARRAY, which "
               "Metal never sets, and fails open with a warning; Unity has no Metal "
               "DXR path though the managed API compiles; Playwright exposes no "
               "navigator.gpu; Godot has the RenderingDevice API but no renderer "
               "integration.",
        "source": "research/10-stack-capability-matrix.md §3, §5.3",
        "would_change": "A pin bump plus a hardware/driver path that does not exist "
                        "on this machine today. Task 24 recommends not pursuing it.",
    },
    "audio.spatialisation": {
        "why": "Structurally unmeasurable, and not because of the stacks. "
               "`judge/audio.py` decodes every clip with `-ac 1`, so the channel "
               "layout is discarded before any analysis runs. Worse, the shipped "
               "clip FILES are all the harness ever hears: nothing records runtime "
               "mixing, so a stereo WAV would prove authoring, never positioning.",
        "source": "judge/audio.py:147 ('-ac', '1'); "
                  "research/10-stack-capability-matrix.md §6.11",
        "would_change": "Recording the game's own output during a probe run - a "
                        "capture device, which macOS cannot route per-application "
                        "without a virtual device nobody has installed here "
                        "(starters/_shared/launch.just). Decoding stereo instead of "
                        "mono is necessary and nowhere near sufficient.",
    },
    "capture.resolution_as_a_variable": {
        "why": "Measured, not assumed, and re-measured every time this report prints "
               "- the census line below counts the records the invocation just read. "
               "Capture geometry has almost no variance across the stored corpus, so "
               "raising or varying it would move a field nothing exercises, at the "
               "cost of invalidating every stored frame comparison. It is recorded "
               "per submission (capture.width_px/height_px) precisely so that the "
               "submissions that DID change it stay visible without anything being "
               "forced to uniformity (#81).",
        "measured_by": "resolution_census",
        "source": "this module, over whichever records the invocation swept",
        "would_change": "A run in which submissions actually vary their capture "
                        "geometry. Until then the field is recorded and not scored.",
    },
}


# --------------------------------------------------------------------------- #
# One record
# --------------------------------------------------------------------------- #

@dataclass
class Observation:
    run: str
    game: str
    stack: str
    #: `"game"`, `"scene"` or `aspects.UNKNOWN_TASK`. Carried on the record rather
    #: than re-derived at each use, because every partition below needs it and a
    #: second derivation is a second thing to get wrong.
    task_class: str
    trial: str
    fields: dict[str, Any] = dc_field(default_factory=dict)
    reason: dict[str, str] = dc_field(default_factory=dict)
    why: dict[str, str] = dc_field(default_factory=dict)
    notes: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"run": self.run, "game": self.game, "stack": self.stack,
                "task_class": self.task_class, "trial": self.trial,
                "fields": self.fields, "reason": self.reason,
                "why": self.why, "notes": self.notes}


#: A trial directory name. The leading class letter is `[gs]` because THERE ARE 2 TASK
#: CLASSES: `eval/AGENTS.md` says so and `suites/scene_prompts.py` names the scenes.
#: It read `g` alone until 2026-08-27, so the one stored scene submission,
#: `s1_parallax__ts__t0`, parsed to game `?` stack `?` - a record on the `ts` arm sitting
#: in a `?` row that no per-stack partition here could see.
#:
#: The class letter is NOT decoded here. `aspects.task_class` is the project's one
#: answer to *what class is this task*, it is 3-valued, and it consults the suites
#: before falling back to the id shape.
TRIAL_RE = re.compile(r"^([gs]\d+_[a-z0-9]+)__([a-z]+)__t(\d+)$")


def parse_trial(name: str) -> tuple[str, str]:
    m = TRIAL_RE.match(name)
    return (m.group(1), m.group(2)) if m else ("?", "?")


def png_geometry(path: Path) -> tuple[int, int]:
    """Width and height from the IHDR, without decompressing the image.

    Reading the header rather than calling `png.read` is not only speed: a frame whose
    IDAT is corrupt still has a truthful geometry, and geometry is what is wanted here.
    """
    with path.open("rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise ValueError(f"{path.name} is not a PNG with a leading IHDR")
    w, h = struct.unpack(">II", head[16:24])
    return int(w), int(h)


def observe_doc(doc: dict[str, Any], *, game: str, stack: str, trial: str,
                run: str, frames_dir: Path | None = None) -> Observation:
    """Build the record from one `programmatic.json`, optionally with its frames.

    `frames_dir` wins over the document's `frames.sizes` summary wherever they
    disagree, and the disagreement is recorded. A record must never prefer a summary
    to the artifact it summarises - that is #60's shape, a correct read of the wrong
    address.

    The task class is derived from the task id rather than passed in, so no caller can
    get it wrong and every record carries one.
    """
    o = Observation(run=run, game=game, stack=stack,
                    task_class=aspects.task_class(game), trial=trial)

    def put(name: str, value: Any) -> None:
        o.fields[name] = value

    def null(name: str, kind: str, prose: str) -> None:
        o.fields[name] = None
        o.reason[name] = kind
        o.why[name] = prose

    cmds = {c.get("name"): c for c in doc.get("commands") or []}
    film = cmds.get("film")
    frames = doc.get("frames") or {}
    thru = doc.get("throughput") or {}

    # -- geometry ---------------------------------------------------------- #
    sizes = [tuple(s) for s in (frames.get("sizes") or [])]
    disk_sizes: list[tuple[int, int]] = []
    if frames_dir is not None and frames_dir.is_dir():
        pngs = sorted(frames_dir.glob("frame_*.png"))
        seen: set[tuple[int, int]] = set()
        for p in pngs:
            try:
                seen.add(png_geometry(p))
            except (OSError, ValueError) as e:
                o.notes.append(f"{p.name}: {e}")
        disk_sizes = sorted(seen)
        if disk_sizes and sizes and disk_sizes != sorted(sizes):
            o.notes.append(
                f"frames on disk are {disk_sizes} but programmatic.json 'sizes' says "
                f"{sorted(sizes)}; the files win")
    use = disk_sizes or sizes
    if len(use) == 1:
        w, h = use[0]
        put("capture.width_px", w)
        put("capture.height_px", h)
        put("capture.megapixels", round(w * h / 1e6, 4))
    elif len(use) > 1:
        for f in ("capture.width_px", "capture.height_px", "capture.megapixels"):
            null(f, SUBMISSION,
                 f"the capture has {len(use)} distinct frame geometries {use}; there is "
                 f"no single geometry to report and guessing one would be worse")
    else:
        prose = ("no frames were captured"
                 + (f"; `just film` exited {film['exit']}" if film else ""))
        for f in ("capture.width_px", "capture.height_px", "capture.megapixels"):
            null(f, SUBMISSION, prose)

    # -- frame count ------------------------------------------------------- #
    n = frames.get("count")
    if isinstance(n, int) and n > 0:
        put("capture.frames", n)
    else:
        null("capture.frames", SUBMISSION,
             f"`just film` produced {n if n is not None else 'no'} PNGs"
             + (f" and exited {film['exit']}" if film else ""))

    # -- cost of the capture ------------------------------------------------ #
    #   wall: recorded since the harness was written.
    #   cpu / peak_rss: recorded since 2026-08-23. Absent from older records, and
    #   absent uniformly across all four arms, which is what makes NOT_CAPTURED the
    #   right reason rather than a stack gap. `no_stack_correlated_gap` checks that
    #   uniformity per run rather than trusting this comment.
    if film is None:
        for f, u in (("capture.wall_seconds", "wall"), ("capture.cpu_seconds", "cpu"),
                     ("capture.peak_rss_mb", "peak rss")):
            null(f, NOT_CAPTURED, f"this record has no `film` command entry, so no {u}")
    else:
        put("capture.wall_seconds", film.get("seconds"))
        for f, k in (("capture.cpu_seconds", "cpu_seconds"),
                     ("capture.peak_rss_mb", "peak_rss_mb")):
            if k in film and film[k] is not None:
                put(f, film[k])
            else:
                null(f, NOT_CAPTURED,
                     f"`film` has no {k}: this record predates rusage capture "
                     f"(static.py, 2026-08-23)")

    # -- the probe --------------------------------------------------------- #
    if thru.get("ok"):
        put("probe.ticks_per_second", thru.get("ticks_per_second"))
        put("probe.startup_seconds", thru.get("startup_s"))
    elif thru:
        for f in ("probe.ticks_per_second", "probe.startup_seconds"):
            null(f, SUBMISSION,
                 f"the probe did not run: {str(thru.get('error'))[:160]}")
    else:
        for f in ("probe.ticks_per_second", "probe.startup_seconds"):
            null(f, NOT_CAPTURED, "this record has no `throughput` block")

    # A field that was `put` with a None value is still a null, and must be explained
    # like any other. Catching it here rather than at every call site is what keeps
    # `reason` and `fields` in step.
    for f, v in list(o.fields.items()):
        if v is None and f not in o.reason:
            o.reason[f] = NOT_CAPTURED
            o.why[f] = "the source record carried the key with a null value"
    for f in FIELDS:
        if f not in o.fields:
            null(f, NOT_CAPTURED, "not present in this record")
    return o


def sweep(root: Path) -> list[Observation]:
    """Every stored `*/eval/programmatic.json` under `root`, oldest path first."""
    out: list[Observation] = []
    for p in sorted(root.rglob("eval/programmatic.json")):
        trial = p.parent.parent.name
        game, stack = parse_trial(trial)
        try:
            rel = p.relative_to(root).parts[0]
        except ValueError:
            rel = root.name
        try:
            doc = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"skipping {p}: {e}", file=sys.stderr)
            continue
        fr = p.parent / "frames"
        out.append(observe_doc(doc, game=game, stack=stack, trial=trial, run=rel,
                               frames_dir=fr if fr.is_dir() else None))
    return out


# --------------------------------------------------------------------------- #
# The gate
# --------------------------------------------------------------------------- #

ARMS = ("rust", "ts", "unity", "godot")

#: THE FOUR-ARM CLAIM IS ABOUT THE GAME MATRIX, and it is asked of game submissions
#: only. Four arms is a property of that matrix: every game has been built on all four.
#: The scene class has been built on 1 arm (`eval/RUNS.md`), so demanding four of it
#: would go red on the state of the corpus rather than on a defect - and a check that
#: fires where nothing is wrong spends the attention a real firing needs.
#:
#: **Excluded is not unread.** The per-record and per-arm checks below run over EVERY
#: record whatever its class; only the four-arms-are-present question is narrowed, and
#: `population_sentence` states what was narrowed away so a reader can see the
#: population (AGENTS.md rule 7).
GATE_TASK_CLASS = "game"


def by_task_class(records: list[Observation]) -> dict[str, list[Observation]]:
    """Records partitioned by task class, `GATE_TASK_CLASS` first."""
    out: dict[str, list[Observation]] = defaultdict(list)
    for r in records:
        out[r.task_class].append(r)
    first = [GATE_TASK_CLASS] if GATE_TASK_CLASS in out else []
    order = first + sorted(k for k in out if k != GATE_TASK_CLASS)
    return {k: out[k] for k in order}


def gate_population(records: list[Observation],
                    ) -> tuple[list[Observation], dict[str, list[Observation]]]:
    """The records the four-arm claim is asked of, and the ones it is not, by class."""
    per_class = by_task_class(records)
    asked = per_class.get(GATE_TASK_CLASS, [])
    return asked, {k: v for k, v in per_class.items() if k != GATE_TASK_CLASS}


def population_sentence(records: list[Observation]) -> str:
    """Which records the four-arm claim was asked of, and how many were excluded."""
    asked, excluded = gate_population(records)
    parts = [f"the four-arm gate is asked of the {len(asked)} {GATE_TASK_CLASS!r} "
             f"submissions (arms {sorted({r.stack for r in asked})})"]
    if not excluded:
        parts.append("0 records excluded")
    for klass, rs in excluded.items():
        parts.append(f"{len(rs)} {klass!r} record{'' if len(rs) == 1 else 's'} excluded "
                     f"(arms {sorted({r.stack for r in rs})})")
    return "; ".join(parts)


def _by_run_class_stack(records: list[Observation],
                        ) -> dict[tuple[str, str], dict[str, list[Observation]]]:
    """Grouped by (run, task class), then by arm.

    THE CLASS IS PART OF THE GROUP KEY, not only the run. A run may launch games and
    scenes together (`wholegame.py --scenes`), and pooling the two inside one run makes
    a field populated for the games cover for the same field never captured on a
    scene's arm - the gap hidden by the population it was pooled with.
    """
    out: dict[tuple[str, str], dict[str, list[Observation]]] = defaultdict(
        lambda: defaultdict(list))
    for r in records:
        out[(r.run, r.task_class)][r.stack].append(r)
    return out


def no_stack_correlated_gap(records: list[Observation]) -> list[str]:
    """Empty means: every declared field is reportable by every arm that ran.

    Four ways to fail. Only the first is narrowed to `GATE_TASK_CLASS`:

    1. **An arm is missing entirely**, among the game submissions. Four arms is the
       claim; three arms cannot support it, and a gate that silently accepts a smaller
       field would report "clean" on exactly the runs where the question is open.

    2. **A record whose class the module cannot name.** It can be asked no per-arm
       question, so it is counted rather than quietly skipped.

    3. **A null marked `stack_cannot`.** The contract says every field is measured by
       a mechanism identical on all four arms, so this reason should be unreachable.
       If it appears, the contract is wrong and this is how you find out.

    4. **A null with no reason at all.** Fail-closed. An unexplained absence is
       indistinguishable from a stack gap, and "every reason not to count a failure is
       a channel a bug can widen" (AGENTS.md rule 7) - so an absence nobody classified
       is counted.

    And the case that must NOT fail: a field absent because the submission's own
    `film` or `probe` failed. That is data about a submission. When it happens to fall
    entirely on one arm it is reported by `stack_skew_warnings`, which is a prompt to
    look, not a verdict.

    `not_captured_in_this_run` is forgiven ACROSS runs (old records predate a field)
    but never WITHIN one: if a field is populated for one arm and never captured for
    another in the same run, the mechanism is not identical on all four arms, whatever
    the reason string says. "Within one run" means within one (run, task class) cell -
    see `_by_run_class_stack`.
    """
    problems: list[str] = []

    # 1. FOUR ARMS, asked of the game population. `population_sentence` says what that
    #    leaves out; the two checks below leave nothing out.
    asked, _excluded = gate_population(records)
    present = {r.stack for r in asked}
    for arm in ARMS:
        if arm not in present:
            problems.append(
                f"no records for the {arm!r} arm among the {len(asked)} "
                f"{GATE_TASK_CLASS!r} submissions: the claim 'reportable by all four "
                f"arms' cannot be checked against {sorted(present)}")

    # 2. EVERY record, whatever its class. A record whose class this module cannot name
    #    is one it can ask no per-arm question of, so it is counted rather than dropped.
    for r in records:
        if r.task_class == aspects.UNKNOWN_TASK:
            problems.append(
                f"{r.run}/{r.trial} ({r.stack}): the trial id parses to no task class, "
                f"so no per-arm question can be asked of it and it is counted as a gap")
        for f, v in r.fields.items():
            if v is None and f not in r.reason:
                problems.append(
                    f"{r.run}/{r.trial} ({r.stack}): {f} is null with no reason kind; "
                    f"an unexplained absence is counted as a gap")

    # 3. EVERY record, within its own (run, class) cell.
    for (run, klass), per_stack in _by_run_class_stack(records).items():
        stacks = [s for s in per_stack if s in ARMS]
        for f in FIELDS:
            populated = {s: sum(1 for r in per_stack[s] if r.fields.get(f) is not None)
                         for s in stacks}
            if not any(populated.values()):
                continue                      # nobody has it here; not a stack gap
            for s in stacks:
                if populated[s]:
                    continue
                kinds = {r.reason.get(f) for r in per_stack[s]}
                if kinds <= {SUBMISSION}:
                    continue                  # data about submissions -> skew, not gap
                problems.append(
                    f"{run} ({klass}): {f} is populated on "
                    f"{sorted(k for k in stacks if populated[k])} but on {s!r} it is "
                    f"absent with reason(s) {sorted(str(k) for k in kinds)} - the "
                    f"mechanism is not identical across arms")
    return problems


def stack_skew_warnings(records: list[Observation]) -> list[str]:
    """Fields absent on one whole arm for SUBMISSION reasons. Not a gate failure.

    Reported because it looks exactly like a stack gap from a distance, and #45's
    lesson is that when subjects sharing only the instrument agree exactly, the
    instrument is what they are reporting. This is where to start looking.
    """
    out: list[str] = []
    for (run, klass), per_stack in _by_run_class_stack(records).items():
        stacks = [s for s in per_stack if s in ARMS]
        for f in FIELDS:
            populated = {s: sum(1 for r in per_stack[s] if r.fields.get(f) is not None)
                         for s in stacks}
            if not any(populated.values()):
                continue
            for s in stacks:
                if populated[s] or not per_stack[s]:
                    continue
                if {r.reason.get(f) for r in per_stack[s]} <= {SUBMISSION}:
                    out.append(
                        f"{run} ({klass}): {f} is missing on all {len(per_stack[s])} "
                        f"{s!r} submissions because their own capture failed - a real "
                        f"absence, on one arm. Worth a look, not a gate failure")
    return out


# --------------------------------------------------------------------------- #
# Censuses - a figure a DECLINED entry rests on is COUNTED, never written down
# --------------------------------------------------------------------------- #

@dataclass
class ResolutionCensus:
    """Capture geometry over the records one invocation actually read.

    Three buckets, and the third is the reason this is a partition rather than a
    ratio: a submission whose `film` failed has NO geometry, and folding it into the
    denominator beside the ones that captured at the default makes "N of M" quietly
    mean two things. Every record lands in exactly one bucket, and the ones that are
    not at the default are named rather than counted.
    """
    default: tuple[int, int]
    total: int
    at_default: list[str] = dc_field(default_factory=list)
    varied: dict[str, list[str]] = dc_field(default_factory=dict)
    absent: dict[str, list[str]] = dc_field(default_factory=dict)

    @property
    def n_varied(self) -> int:
        return sum(len(v) for v in self.varied.values())

    @property
    def n_absent(self) -> int:
        return sum(len(v) for v in self.absent.values())

    def sentence(self) -> str:
        w, h = self.default
        varied = ", ".join(f"{g} x{len(t)}" for g, t in sorted(self.varied.items()))
        absent = ", ".join(f"{len(t)} {k}" for k, t in sorted(self.absent.items()))
        return (f"{len(self.at_default)} of the {self.total} records swept captured "
                f"at exactly the starter default {w}x{h}; {self.n_varied} varied "
                f"({varied or 'none'}); {self.n_absent} "
                f"{'has' if self.n_absent == 1 else 'have'} no geometry to compare "
                f"({absent or 'none'})")


def resolution_census(records: list[Observation],
                      default: tuple[int, int] = STARTER_DEFAULT_GEOMETRY,
                      ) -> ResolutionCensus:
    """Is capture resolution a variable submissions exercise, over THESE records?"""
    c = ResolutionCensus(default=default, total=len(records))
    for r in records:
        w = r.fields.get("capture.width_px")
        h = r.fields.get("capture.height_px")
        where = f"{r.run}/{r.trial}"
        if w is None or h is None:
            c.absent.setdefault(r.reason.get("capture.width_px") or "unclassified",
                                []).append(where)
        elif (w, h) == default:
            c.at_default.append(where)
        else:
            c.varied.setdefault(f"{w}x{h}", []).append(where)
    return c


#: A DECLINED entry may not carry a corpus figure of its own. It names a producer
#: here and the figure is counted when the report prints, from the same records the
#: header counts. `capability_selftest.py` pins both halves: that every name resolves
#: and no entry has re-acquired a frozen figure, and that the census tracks the
#: population it is handed.
CENSUSES = {"resolution_census": resolution_census}


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def distribution(records: list[Observation], field: str,
                 by: str = "stack") -> dict[str, dict[str, Any]]:
    """`n` per group alongside every aggregate, and no aggregate over a group that
    mixes populated and absent silently (AGENTS.md rule 4)."""
    groups: dict[str, list[float]] = defaultdict(list)
    total: dict[str, int] = defaultdict(int)
    for r in records:
        key = getattr(r, by)
        total[key] += 1
        v = r.fields.get(field)
        if isinstance(v, (int, float)):
            groups[key].append(float(v))
    out: dict[str, dict[str, Any]] = {}
    for key in sorted(total):
        v = sorted(groups.get(key, []))
        out[key] = {"n": total[key], "populated": len(v)}
        if v:
            out[key].update(min=round(v[0], 3), median=round(st.median(v), 3),
                            max=round(v[-1], 3))
    return out


def _fmt_table(title: str, dist: dict[str, dict[str, Any]]) -> str:
    lines = [f"  {title}"]
    for key, d in dist.items():
        body = (f"min={d['min']:>10}  med={d['median']:>10}  max={d['max']:>10}"
                if "min" in d else "no populated values")
        lines.append(f"    {key:<8} n={d['n']:>3} populated={d['populated']:>3}  {body}")
    return "\n".join(lines)


def report(records: list[Observation]) -> int:
    per_class = by_task_class(records)
    census = ", ".join(f"{len(v)} {k}" for k, v in per_class.items())
    print(f"{len(records)} stored submissions ({census or 'none'})\n")

    print("FIELDS (same name, same unit, all four arms)")
    for f, unit in FIELDS.items():
        print(f"  {f:<26} {unit}")
    print()

    # PER TASK CLASS, never pooled. A scene and a game are different task classes
    # (`eval/AGENTS.md`), so a min/median/max over both is an aggregate across a
    # population nobody established was homogeneous (AGENTS.md rule 4).
    for klass, recs in per_class.items():
        print(f"{klass} submissions ({len(recs)})")
        for f in FIELDS:
            print(_fmt_table(f, distribution(recs, f, "stack")))

        print("  capture geometry, distinct values seen")
        geo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for r in recs:
            w, h = r.fields.get("capture.width_px"), r.fields.get("capture.height_px")
            geo[r.stack][f"{w}x{h}" if w else "none"] += 1
        for stack in sorted(geo):
            inner = ", ".join(f"{k} x{v}" for k, v in
                              sorted(geo[stack].items(), key=lambda kv: -kv[1]))
            print(f"    {stack:<8} {inner}")
        print()

    warn = stack_skew_warnings(records)
    if warn:
        print(f"SKEW ({len(warn)}) - real absences that fall on one arm:")
        for w in sorted(set(warn)):
            print(f"  ! {w}")
        print()

    print(f"GATE POPULATION: {population_sentence(records)}")
    problems = no_stack_correlated_gap(records)
    if problems:
        print(f"GATE: FAILED ({len(problems)})")
        for p in problems:
            print(f"  x {p}")
        return 1
    print("GATE: no stack-correlated gap in any declared field")

    print(f"\nDECLINED - considered and deliberately not captured ({len(DECLINED)}):")
    for name, e in DECLINED.items():
        print(f"  - {name}: {e['why'].split('.')[0]}.")
        producer = e.get("measured_by")
        if not producer:
            continue
        cen = CENSUSES[producer](records)
        print(f"      {producer}(): {cen.sentence()}")
        for geo, trials in sorted(cen.varied.items()):
            for t in trials:
                print(f"        varied {geo}: {t}")
        for kind, trials in sorted(cen.absent.items()):
            for t in trials:
                print(f"        no geometry, {kind}: {t}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", required=True, type=Path,
                    help="a run directory, or the parent of several")
    ap.add_argument("--json", action="store_true", help="emit records instead of a report")
    a = ap.parse_args(argv)
    records = sweep(a.runs)
    if a.json:
        json.dump([r.to_dict() for r in records], sys.stdout, indent=2)
        print()
        return 0 if not no_stack_correlated_gap(records) else 1
    return report(records)


if __name__ == "__main__":
    raise SystemExit(main())
