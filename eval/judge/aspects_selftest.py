#!/usr/bin/env python3
"""Pin the frames-channel blind-spot briefing, in BOTH directions.

`FRAMES_BLIND_SPOT` (`aspects.py`) tells every frames-reading judge that an effect
which accumulates across ticks may be structurally absent from its evidence, because
the four arms' capture harnesses differ in what a frame can contain (task 68,
FINDINGS #107). Three properties have to hold, and none of them is visible in a
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

from aspects import ASPECTS, FRAMES_BLIND_SPOT, Aspect

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


CHECKS = (
    ("every frames aspect states its blind spot", check_every_frames_aspect_carries_it),
    ("fun and fun_frames are briefed identically", check_control_briefing_is_identical),
    ("no stack name and no arm count", check_no_stack_or_count_leak),
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
    return out


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

    print(f"\n{'PASS' if not failures else f'BROKEN: {failures} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
