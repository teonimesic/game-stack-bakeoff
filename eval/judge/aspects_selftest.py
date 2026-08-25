#!/usr/bin/env python3
"""Pin the frames-channel blind-spot briefing, in BOTH directions.

`FRAMES_BLIND_SPOT` (`aspects.py`) tells every frames-reading judge that an effect
which accumulates across ticks may be structurally absent from its evidence, because
the four arms' capture harnesses differ in what a frame can contain (task 68,
FINDINGS #107). Four properties have to hold, and none of them is visible in a
judge's output:

  1. EVERY frames-reading aspect carries it. An aspect that cannot know its own
     blind spot will keep scoring across it.
  2. `fun` and `fun_frames` carry BYTE-IDENTICAL copies. `fun_frames` is `fun`'s
     control with the telemetry withheld; a control whose briefing differs from its
     treatment's is not a control, and the difference would be indistinguishable
     from a real effect in the tau between them.
  3. It names no stack and counts no arms. The judge is blinded to which submission
     is which (FINDINGS #32), and "three of the four" hands over the partition just
     as surely as "Bevy" does.
  4. A control DECLARES what it controls, in `control_for`, where code can read it.
     `field_ranks` decides what may be pooled from that field and nothing else; while
     the exclusion lived only in a prose comment, 5 control rounds went into a pooled
     figure over 30 (task 90).

Two more, about the second task class:

  5. AN ASPECT IS ASKED ONLY OF ITS OWN TASK CLASS. A scene has no player and a game
     has no scene brief, so `applicability()` refuses the cross pairs -- and it refuses
     an id it cannot classify rather than reading it as a game. The fallback that lets
     the judge fixtures' synthetic `g9_probe` through is corroborated here against the
     suites, not trusted: every task the suites define must get the same class from
     both channels.

  6. A CROSS-STACK BAR IS DECLARED TO CODE, in `cross_stack_bar`, and carries its
     reason. `idiomatic`'s bar lived in `JUDGING.md` and `RUBRIC.md` prose from #53
     onward and no code could read it; `framework_fluency` is barred by construction
     before its first round. `field_ranks.report` prints the reason beside every figure
     it produces for a barred aspect.

Each check is run against the live aspects (must pass) AND against a mutant built to
break exactly that check (must fail). A check that cannot fail is worse than absent.

Rule 15: the count check also gets a VARIANT -- an input it is not obviously built
for, rather than a removal of the thing it names.

    python3 eval/judge/aspects_selftest.py        # unpiped; exit 1 means broken
"""

from __future__ import annotations

import re
import sys
from dataclasses import replace

import aspects as aspects_mod
from aspects import ASPECTS, FRAMES_BLIND_SPOT, Aspect, applicability, task_class

#: THE EXPECTATION, WRITTEN OUT RATHER THAN DERIVED FROM THE THING IT CHECKS.
#:
#: Reading `Aspect.task_class` back to decide what `Aspect.task_class` should be is the
#: shape that made a mutant come back SURVIVED with 0 red rows of 48 (task 113): a
#: control that imports its expectation from its subject cannot disagree with it. So the
#: split is stated here, independently, and everything not named is expected to be a
#: game aspect -- which means adding a scene aspect without stating it here goes RED,
#: and that is the intended failure rather than a maintenance cost.
SCENE_ONLY = ("fidelity", "motion", "framework_fluency")

#: The same, for the cross-stack bar, and for the same reason.
#:
#: `idiomatic` was barred on measurement (#53) and the bar lived only in `JUDGING.md`
#: and `RUBRIC.md` prose; `framework_fluency` is barred by construction, because the
#: question IS which engine's APIs are in the source.
BARRED_CROSS_STACK = ("idiomatic", "framework_fluency")

#: A bar has to carry a REASON, not a marker. Below this it is a boolean spelled long.
_MIN_BAR_CHARS = 40

#: Names that would tell a blinded judge which stack it is looking at.
STACK_WORDS = ("godot", "bevy", "rust", "unity", "typescript", "three.js", "cargo",
               "gdscript", "c#", "csharp", "playwright", "chromium", "webgl")

#: Phrasings that leak the SIZE of the partition without naming a stack.
COUNT_LEAKS = re.compile(
    r"\b(one|two|three|four|1|2|3|4)\s+(of\s+the\s+)?(four|4)\b|\bfour\s+(arms|stacks|"
    r"harnesses|engines|templates)\b",
    re.IGNORECASE,
)


def frames_aspects(aspects: dict[str, Aspect]) -> dict[str, Aspect]:
    return {i: a for i, a in aspects.items() if "frames" in a.sees}


def check_every_frames_aspect_carries_it(aspects: dict[str, Aspect]) -> list[str]:
    reading = frames_aspects(aspects)
    if not reading:
        return ["no aspect reads frames at all - the check has nothing to measure"]
    return [
        f"{i}: sees {a.sees!r} but its notes do not carry FRAMES_BLIND_SPOT"
        for i, a in reading.items()
        if FRAMES_BLIND_SPOT not in a.notes
    ]


def check_control_briefing_is_identical(aspects: dict[str, Aspect]) -> list[str]:
    treatment, control = aspects.get("fun"), aspects.get("fun_frames")
    if treatment is None or control is None:
        return ["fun / fun_frames are not both defined - the control pair is gone"]

    def paragraph(aspect: Aspect) -> str | None:
        index = aspect.notes.find(FRAMES_BLIND_SPOT[:60])
        return None if index < 0 else aspect.notes[index:]

    a, b = paragraph(treatment), paragraph(control)
    if a is None or b is None:
        return ["fun / fun_frames: one of the pair has no blind-spot paragraph"]
    if a != b:
        return [
            "fun / fun_frames blind-spot paragraphs DIFFER - the control is "
            f"distinguishable from its treatment ({len(a)} vs {len(b)} chars)"
        ]
    return []


def check_control_declaration(aspects: dict[str, Aspect]) -> list[str]:
    """`control_for` must be usable by code, not merely readable by a person.

    `field_ranks.assert_poolable` refuses to pool a control with a scored aspect, and it
    decides which is which from this field alone. Three ways that goes wrong silently:

      * nothing is marked, so the guard has nothing to exclude. That was the state until
        2026-08-23 - the exclusion lived in a comment, `runs/wg-aspect-reliability` pooled
        5 control rounds into 30, and `Aspect` carried a never-set field named
        `diagnostic_only` that collided with an unrelated one on the play bots (task 90).
      * a control names an aspect that does not exist, so "read it against its treatment"
        cannot be done.
      * a control controls a control, which has no meaning and would make the scored /
        control split stop partitioning `ASPECTS`.
    """
    controls = {i: a.control_for for i, a in aspects.items() if a.control_for}
    if not controls:
        return ["no aspect sets `control_for`: field_ranks has nothing to exclude, and "
                "a pooled figure will absorb any control silently"]
    problems = []
    for identifier, target in controls.items():
        if target not in aspects:
            problems.append(f"{identifier}: control_for={target!r}, which is not an aspect")
        elif aspects[target].control_for:
            problems.append(f"{identifier}: controls {target!r}, which is itself a control")
        elif identifier == target:
            problems.append(f"{identifier}: is its own control")
    return problems


def check_no_stack_or_count_leak(aspects: dict[str, Aspect]) -> list[str]:
    problems = []
    for identifier, aspect in frames_aspects(aspects).items():
        text = f"{aspect.question}\n{aspect.evidence_rule}\n{aspect.notes}".lower()
        for word in STACK_WORDS:
            if word in text:
                problems.append(f"{identifier}: brief names the stack {word!r}")
        leak = COUNT_LEAKS.search(text)
        if leak is not None:
            problems.append(
                f"{identifier}: brief leaks the partition size ({leak.group(0)!r})"
            )
    return problems


def check_task_class_is_enforced(aspects: dict[str, Aspect]) -> list[str]:
    """A scene aspect is asked only of scenes, and `applicability` is what says no.

    Three things, and the third is the one a mutant cannot reach on its own:

      * the declared class matches `SCENE_ONLY`, which is stated above rather than read
        back off the aspect;
      * `applicability` admits exactly the same-class pairs over the REAL task ids, so
        the guard agrees with the declaration instead of being a second opinion;
      * an id it cannot classify is REFUSED. A field is one judge invocation over all 8
        submissions, and reading an unrecognised id as a game is the fail-open
        direction (rule 7).
    """
    problems: list[str] = []
    for identifier, aspect in sorted(aspects.items()):
        want = "scene" if identifier in SCENE_ONLY else "game"
        if aspect.task_class != want:
            problems.append(
                f"{identifier}: task_class={aspect.task_class!r}, expected {want!r}. "
                f"Either the aspect moved class or SCENE_ONLY was not updated with it")
    tasks = sorted(aspects_mod._task_classes())
    if not tasks:
        return problems + ["no task ids resolved from eval/suites/, so the guard is "
                           "being asked about an empty population"]
    for identifier, aspect in sorted(aspects.items()):
        for task in tasks:
            refused = applicability(identifier, task, registry=aspects)
            same = task_class(task) == aspect.task_class
            if same and refused:
                problems.append(f"{identifier} on {task}: same class, refused anyway "
                                f"({refused[:80]})")
            if not same and not refused:
                problems.append(f"{identifier} on {task}: {aspect.task_class} aspect "
                                f"admitted on a {task_class(task)}")
        if not applicability(identifier, "an-id-no-suite-defines", registry=aspects):
            problems.append(f"{identifier}: admitted a task id whose class cannot be "
                            f"established - the guard fails open")
    return problems


def check_cross_stack_bar_is_declared(aspects: dict[str, Aspect]) -> list[str]:
    """A bar on ranking stacks must be readable by code, and must carry its reason.

    `field_ranks.report` prints the reason beside every figure it produces for a barred
    aspect. A bare boolean would make the report say "barred" and send the reader off to
    find out why, which is how `idiomatic`'s bar stayed in prose from #53 onward.
    """
    problems: list[str] = []
    for identifier, aspect in sorted(aspects.items()):
        bar = aspect.cross_stack_bar.strip()
        if identifier in BARRED_CROSS_STACK and not bar:
            problems.append(f"{identifier}: no cross_stack_bar, so nothing in code "
                            f"knows its ordering must not be read across stacks")
        if identifier not in BARRED_CROSS_STACK and bar:
            problems.append(f"{identifier}: declares a cross-stack bar that "
                            f"BARRED_CROSS_STACK does not expect - state it there, "
                            f"where a reader looks for the list")
        if bar and len(bar) < _MIN_BAR_CHARS:
            problems.append(f"{identifier}: cross_stack_bar is {len(bar)} chars "
                            f"({bar!r}) - a bar has to say why, not merely that")
    return problems


def id_shape_agrees(classes: dict[str, str]) -> list[str]:
    """Does `g<N>_` / `s<N>_` give the same class as the suites that define the tasks?

    `aspects._ID_SHAPE` is the fallback that lets the judge fixtures' synthetic
    `g9_probe` field through a guard that would otherwise refuse every fixture. A
    fallback nothing corroborates is a second source of truth; this is the row that
    compares the two channels rather than making them the same object (rule 12).

    Takes the map as an ARGUMENT so `main` can drive it with a doctored one and prove
    it can say no.
    """
    return [f"{task}: the suites call it a {want}, its id shape says "
            f"{aspects_mod._SHAPE_CLASS.get((task or ' ')[0], 'nothing')}"
            for task, want in sorted(classes.items())
            if aspects_mod._SHAPE_CLASS.get((task or " ")[0]) != want]


CHECKS = (
    ("every frames aspect states its blind spot", check_every_frames_aspect_carries_it),
    ("fun and fun_frames are briefed identically", check_control_briefing_is_identical),
    ("no stack name and no arm count", check_no_stack_or_count_leak),
    ("a control is declared to code, and names a real treatment",
     check_control_declaration),
    ("an aspect is asked only of its own task class", check_task_class_is_enforced),
    ("a cross-stack bar is declared to code, with its reason",
     check_cross_stack_bar_is_declared),
)


def mutants() -> list[tuple[str, str, dict[str, Aspect]]]:
    """(check it must break, description, aspects). Each MUST make its check fail."""
    live = dict(ASPECTS)
    out: list[tuple[str, str, dict[str, Aspect]]] = []

    stripped = dict(live)
    stripped["ux"] = replace(live["ux"], notes=live["ux"].notes.replace(
        FRAMES_BLIND_SPOT, ""))
    out.append(("every frames aspect states its blind spot",
                "ux loses the blind-spot paragraph", stripped))

    drifted = dict(live)
    drifted["fun_frames"] = replace(live["fun_frames"], notes=live["fun_frames"].notes
                                    + " One extra sentence, in the control only.")
    out.append(("fun and fun_frames are briefed identically",
                "fun_frames gains a sentence fun does not have", drifted))

    named = dict(live)
    named["ux"] = replace(live["ux"], notes=live["ux"].notes
                          + " In the Godot arm this is worse.")
    out.append(("no stack name and no arm count", "ux names Godot", named))

    # THE VARIANT. Not a removal of the mechanism the check names: an input the
    # check was not obviously built for. The blind spot is honestly described, no
    # stack is named -- and the phrasing still tells the judge how big the split is.
    counted = dict(live)
    counted["ux"] = replace(live["ux"], notes=live["ux"].notes
                            + " Three of the four harnesses draw only once.")
    out.append(("no stack name and no arm count",
                "VARIANT: ux counts the arms without naming one", counted))

    # THE TASK-90 STATE, reconstructed: the control is still defined, still briefed
    # identically, still runnable - and no longer says so to code. Every other check here
    # stays green on it, which is exactly why it survived in a comment for as long as it did.
    unmarked = dict(live)
    unmarked["fun_frames"] = replace(live["fun_frames"], control_for="")
    out.append(("a control is declared to code, and names a real treatment",
                "fun_frames stops declaring what it controls (the task-90 state)",
                unmarked))

    # A VARIANT for the same check: the field IS set, so a "is anything marked?" test
    # passes, and the value points at nothing a reader could compare against.
    dangling = dict(live)
    dangling["fun_frames"] = replace(live["fun_frames"], control_for="fun_but_not_really")
    out.append(("a control is declared to code, and names a real treatment",
                "VARIANT: fun_frames controls an aspect that does not exist", dangling))

    reclassed = dict(live)
    reclassed["fidelity"] = replace(live["fidelity"], task_class="game")
    out.append(("an aspect is asked only of its own task class",
                "fidelity is reclassified as a game aspect", reclassed))

    # A VARIANT for the same check: not a swap between the two classes, which is what a
    # mutant reaches for, but a THIRD value. Nothing rejects it at construction, the
    # aspect still declares a class, and `applicability` then refuses every real task -
    # a guard that has become a wall, which no cross-pair test would notice.
    third = dict(live)
    third["motion"] = replace(live["motion"], task_class="either")
    out.append(("an aspect is asked only of its own task class",
                "VARIANT: motion declares a class that is neither", third))

    unbarred = dict(live)
    unbarred["framework_fluency"] = replace(live["framework_fluency"],
                                            cross_stack_bar="")
    out.append(("a cross-stack bar is declared to code, with its reason",
                "framework_fluency stops declaring its bar (the #53 state)", unbarred))

    # A VARIANT: the field IS set, so "is anything marked?" passes, and what it holds
    # is a marker rather than a reason - the boolean this field exists not to be.
    marker = dict(live)
    marker["idiomatic"] = replace(live["idiomatic"], cross_stack_bar="yes")
    out.append(("a cross-stack bar is declared to code, with its reason",
                "VARIANT: idiomatic's bar is a marker, not a reason", marker))
    return out


#: What every non-aspect instrument is for, stated HERE rather than read back out of
#: `aspects.INSTRUMENTS`. A check whose expectation comes from its subject cannot fail on
#: a mutant of the subject (AGENTS.md rule 12's corollary, task 113).
INSTRUMENT_CLASS = {"playbot": "game", "scene_probe": "scene", "legacy_judge": "game"}


def instruments_are_guarded(instruments: dict[str, str]) -> list[str]:
    """`applicability` answers for a deterministic instrument exactly as for an aspect.

    Four questions, and the last is the one the play-bot needed: an instrument admitted
    on the wrong class is the state `evaluate.BOTS[task]` was in, where the only refusal
    was a `KeyError` from a dict that happened to hold four keys.
    """
    problems: list[str] = []
    if sorted(instruments) != sorted(INSTRUMENT_CLASS):
        problems.append(f"instrument registry is {sorted(instruments)}, this check "
                        f"expects {sorted(INSTRUMENT_CLASS)} - add the new instrument "
                        f"here with the class it may be run against")
        return problems
    for identifier, want in sorted(INSTRUMENT_CLASS.items()):
        if instruments[identifier] != want:
            problems.append(f"{identifier}: declared {instruments[identifier]!r}, "
                            f"expected {want!r}")
    for identifier, want in sorted(instruments.items()):
        for task in sorted(aspects_mod._task_classes()):
            refused = aspects_mod.applicability(identifier, task)
            same = task_class(task) == want
            if same and refused:
                problems.append(f"{identifier} on {task}: same class, refused anyway "
                                f"({refused[:80]})")
            if not same and not refused:
                problems.append(f"{identifier} on {task}: a {want} instrument was "
                                f"admitted on a {task_class(task)}")
        if not aspects_mod.applicability(identifier, "an-id-no-suite-defines"):
            problems.append(f"{identifier}: admitted a task id whose class cannot be "
                            f"established - the guard fails open")
    if not aspects_mod.applicability("not-an-instrument-at-all", "g1_pong"):
        problems.append("an unknown instrument id was admitted")
    return problems


def main() -> int:
    failures = 0

    print("live aspects - every check must PASS")
    for name, check in CHECKS:
        problems = check(dict(ASPECTS))
        print(f"  {'ok  ' if not problems else 'FAIL'}  {name}")
        for problem in problems:
            print(f"          {problem}")
        failures += bool(problems)

    print("\nmutants and variants - each must make ITS check FAIL")
    by_name = dict(CHECKS)
    for target, description, aspects in mutants():
        problems = by_name[target](aspects)
        caught = bool(problems)
        print(f"  {'ok  ' if caught else 'FAIL'}  {description}")
        if not caught:
            print(f"          '{target}' passed a mutant - the check measures nothing")
        failures += not caught

    # THE ID-SHAPE FALLBACK, corroborated rather than trusted, in both directions. It is
    # driven from here rather than from CHECKS because its subject is the task map, not
    # the aspect set, and a mutant of it is a doctored map.
    print("\nthe id-shape fallback agrees with the suites")
    live_map = aspects_mod._task_classes()
    live_problems = id_shape_agrees(live_map)
    print(f"  {'ok  ' if not live_problems else 'FAIL'}  "
          f"{len(live_map)} task id(s) classified by both channels")
    for problem in live_problems:
        print(f"          {problem}")
    failures += bool(live_problems)

    doctored = dict(live_map)
    doctored[sorted(t for t in live_map if t.startswith("s"))[0]] = "game"
    print(f"  {'ok  ' if id_shape_agrees(doctored) else 'FAIL'}  "
          f"MUTANT: a scene task the map calls a game is caught")
    failures += not id_shape_agrees(doctored)

    # DETERMINISTIC INSTRUMENTS, driven from here for the same reason the id-shape
    # fallback is: its subject is the instrument map, not the aspect set.
    print("\nnon-aspect instruments are guarded by the same function")
    live_instruments = dict(aspects_mod.INSTRUMENTS)
    inst_problems = instruments_are_guarded(live_instruments)
    print(f"  {'ok  ' if not inst_problems else 'FAIL'}  "
          f"{len(live_instruments)} instrument(s) declare a class and are refused "
          f"off it")
    for problem in inst_problems:
        print(f"          {problem}")
    failures += bool(inst_problems)

    # MUTANT: the scene probe is declared a game instrument. Nothing raises, every id
    # still resolves, and `evaluate` would drive a scene probe at a game.
    reclassed = dict(live_instruments)
    reclassed["scene_probe"] = "game"
    caught = bool(instruments_are_guarded(reclassed))
    print(f"  {'ok  ' if caught else 'FAIL'}  "
          f"MUTANT: scene_probe is declared a game instrument")
    failures += not caught

    print(f"\n{'PASS' if not failures else f'BROKEN: {failures} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
