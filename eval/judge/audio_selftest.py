#!/usr/bin/env python3
"""Mutation tests for the audio criteria. Run: `python3 judge/audio_selftest.py`.

THE POINT OF THIS FILE. Every criterion in `audio.py` is paired here with a mutant that
must make it go RED, and with a healthy fixture that must make it go GREEN. A criterion
validated only against good input is indistinguishable from a criterion that cannot
fail, and this project has shipped that mistake enough times to stop guessing:

    #19  a mechanism that measures something and hands you a wrong number
    #25  a criterion that could only ever fire on one arm
    #26  the only signal the subjective tier produced was an artifact

Positive control, negative control, adversarial control - all three, for each of the six
audio criteria. Exit code is 0 only if every expectation holds.

MUTANTS ARE NOT ENOUGH, AND THIS FILE IS WHERE THAT WAS MEASURED. A mutant removes the
mechanism a criterion names; it cannot manufacture an input the criterion mishandles
(`AGENTS.md` rule 15). Nine mutants ran green here across every audio criterion while
`audio.distinct` could be bought with 2 junk manifest entries, because the input that
defeats it - all declared events on one clip PLUS unique undeclared extras - is a
VARIANT, and no mutation of `audio.py` constructs it. The variants are marked `VARIANT`
below and are the half that catches this class.

THE DECLARED EVENT LIST IS PINNED BY HAND HERE, ON PURPOSE. `audio.GAME_EVENTS` is now
read out of `eval/suites/wholegame_prompts.py`, which is the right address for the fact
(rule 12) - and a check that reads its expectation from its subject is not a check
(task 113). `EVENTS_AS_WRITTEN` is transcribed from the prompt text by hand, so it is a
second, independent statement of the same thing, and the row that compares them is what
would have caught the 2-game drift that `tasks/151` reports.
"""

from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audio  # noqa: E402

RATE = 22050


def tone(path: Path, seconds: float, freq: float, *, rate: int = RATE,
         amp: float = 0.5, harmonics: tuple[float, ...] = (1.0,),
         decay: float = 0.0) -> Path:
    """A deterministic WAV. Different `freq`/`harmonics` give different spectra."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        v = sum(math.sin(2 * math.pi * freq * h * t) / h for h in harmonics)
        env = math.exp(-decay * t) if decay else 1.0
        s = max(-1.0, min(1.0, amp * env * v))
        frames += struct.pack("<h", int(s * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


def silence(path: Path, seconds: float) -> Path:
    return tone(path, seconds, 440.0, amp=0.0)


def make_repo(root: Path, manifest: dict | str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "justfile").write_text(
        "set shell := [\"bash\", \"-uc\"]\n\n"
        "audio-manifest:\n"
        "    @cat audio-manifest.json\n")
    text = manifest if isinstance(manifest, str) else json.dumps(manifest, indent=2)
    (root / "audio-manifest.json").write_text(text)
    return root


#: The declared events, TRANSCRIBED BY HAND from the `_G*_EVENTS` blocks in
#: `eval/suites/wholegame_prompts.py`, in the order they are listed there.
#:
#: This is deliberately a copy, and it is the only copy that may exist. `audio.py` reads
#: the real list out of the prompts, so the two are independent statements of one fact
#: and `pin_declared_events` is the row that compares them - which is what task 113 says
#: to do where an expectation must be kept in step with its subject, rather than making
#: them the same object. When a prompt's event list legitimately changes, this list is
#: edited too, and that edit is the whole point: a grading contract should not move
#: without somebody saying so.
EVENTS_AS_WRITTEN: dict[str, tuple[str, ...]] = {
    "g1_pong": ("paddle_hit", "wall_bounce", "score_left", "score_right", "game_over"),
    "g2_tetris3d": ("spawn", "move", "rotate", "lock", "layer_clear", "game_over"),
    "g3_arena": ("fire", "enemy_spawn", "enemy_hit", "enemy_dead", "player_hit",
                 "wall_graze", "multiplier", "wave_start", "game_over"),
    "g4_platformer": ("jump", "land", "attack", "enemy_hit", "enemy_dead",
                      "player_hit", "stage_clear", "game_over"),
}

#: Every fixture below is built from `EVENTS_AS_WRITTEN`, never from `audio.GAME_EVENTS`.
#: A fixture that asks the grader which events to ship cannot catch a grader that has the
#: wrong list: it would omit exactly the cues the grader has forgotten to look for, and
#: `audio.manifest` would go green on both halves of one mistake.
PONG = EVENTS_AS_WRITTEN["g1_pong"]

#: One event name per line, at the start of the line, in double quotes. Written out here
#: rather than imported from the parser under test, for the same reason as the list above.
EVENT_LINE = re.compile(r'^"([a-z_][a-z0-9_]*)"')

#: What `_probe_section` says immediately before it renders the events block.
EVENTS_MARKER = "is a list of strings drawn from:"

# Clearly different sounds: different fundamentals, harmonic content and envelopes.
# There are at least as many as the largest declared event set, so a healthy fixture is
# all-distinct on every game rather than sitting on `audio.distinct`'s floor - a positive
# control one clip away from failing tells you nothing when it goes green.
VOICES = [
    dict(freq=220.0, harmonics=(1.0,), decay=0.0),
    dict(freq=880.0, harmonics=(1.0, 3.0, 5.0), decay=6.0),
    dict(freq=330.0, harmonics=(1.0, 2.0), decay=2.0),
    dict(freq=1320.0, harmonics=(1.0,), decay=12.0),
    dict(freq=110.0, harmonics=(1.0, 2.0, 3.0, 4.0), decay=1.0),
    dict(freq=660.0, harmonics=(1.0, 5.0), decay=4.0),
    dict(freq=165.0, harmonics=(1.0, 3.0), decay=0.5),
    dict(freq=2200.0, harmonics=(1.0,), decay=20.0),
    dict(freq=440.0, harmonics=(1.0, 2.0, 3.0, 5.0, 7.0), decay=8.0),
]


def healthy(root: Path, game: str = "g1_pong") -> dict:
    """A submission that should pass all five criteria."""
    sfx = {}
    for i, name in enumerate(EVENTS_AS_WRITTEN[game]):
        p = tone(root / "audio" / f"{name}.wav", 0.35, **VOICES[i % len(VOICES)])
        sfx[name] = {"file": str(p.relative_to(root))}
    tone(root / "audio" / "music.wav", 6.0, 196.0, harmonics=(1.0, 2.0), amp=0.4)
    return {"music": {"file": "audio/music.wav", "loops": True}, "sfx": sfx}


def add_extras(root: Path, manifest: dict, count: int) -> dict:
    """`count` undeclared `sfx` entries, each a sound unlike any other in the fixture.

    The task forbids no extra entry, so these must not fail `audio.manifest` - and they
    must not be counted by `audio.distinct` either way.
    """
    for i in range(count):
        p = tone(root / "audio" / f"extra{i}.wav", 0.35 + 0.01 * i,
                 freq=147.0 + 91.0 * i, harmonics=(1.0, 2.0, 5.0), decay=3.0 + i)
        manifest["sfx"][f"undeclared_extra_{i}"] = {"file": str(p.relative_to(root))}
    return manifest


# --------------------------------------------------------------------------- #

FAILURES: list[str] = []
CHECKS = 0


def verdicts(repo: Path, game: str = "g1_pong") -> dict[str, tuple[bool, str]]:
    out = audio.collect(repo, game)
    return {c["id"]: (c["passed"], c.get("evidence", "")) for c in out["criteria"]}


def check(ok: bool, msg: str) -> None:
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILURES.append(msg)


def rendered_event_names(text: str) -> list[str]:
    """The event names out of a RENDERED prompt's events block.

    Independent of how `wholegame_prompts.EVENTS` is built: it goes through
    `_probe_section`, so it also answers whether the block the grader parsed is the block
    the building agent was actually shown. Isolating the fenced block matters - the state
    block a few lines above holds quoted JSON keys that a whole-document scan would read
    as event names.
    """
    i = text.index(EVENTS_MARKER)
    rest = text[i + len(EVENTS_MARKER):]
    start = rest.index("```") + 3
    body = rest[start:rest.index("```", start)]
    return [m.group(1) for m in
            (EVENT_LINE.match(line.strip()) for line in body.splitlines())
            if m is not None]


def pin_declared_events() -> None:
    """`audio.GAME_EVENTS` against a hand-written list, and against the rendered prompts.

    THE ROW THAT WOULD HAVE CAUGHT `tasks/151`. A transcription is a second address for
    one fact, so `audio.py` no longer keeps one - but the check for that fact must not be
    the fact itself, or the check goes green on whatever the subject says (task 113).
    """
    suites = Path(__file__).resolve().parent.parent / "suites"
    sys.path.insert(0, str(suites))
    import wholegame_prompts as wp

    check(set(audio.GAME_EVENTS) == set(wp.TASKS),
          f"GAME_EVENTS covers {sorted(audio.GAME_EVENTS)}, the suite defines "
          f"{sorted(wp.TASKS)} - a game with no declared events reaches the grader with "
          f"a criterion that cannot fail")
    check(set(EVENTS_AS_WRITTEN) == set(wp.TASKS),
          f"EVENTS_AS_WRITTEN covers {sorted(EVENTS_AS_WRITTEN)}, the suite defines "
          f"{sorted(wp.TASKS)} - a new game needs its list transcribed here too")
    # The PARSER, both ways. A block that stops being readable must raise rather than
    # return the names it could still find: a short list is a grading contract missing an
    # event, which is the fail-open this whole change is about.
    good = '```\n"jump"    the player left the ground\n"land"    and came down\n```'
    check(wp._declared_events("t", good) == ("jump", "land"),
          f"the parser on a well-formed block returned {wp._declared_events('t', good)}")
    for label, bad in (
            ("no fence", '"jump"  the player left the ground'),
            ("one fence", '```\n"jump"  the player left the ground'),
            ("a line that is not a declaration",
             '```\n"jump"  the player left the ground\njump - the player jumped\n```'),
            ("an empty fence", "```\n```"),
            ("a repeated name", '```\n"jump"  a\n"jump"  b\n```')):
        try:
            got = wp._declared_events("t", bad)
        except ValueError:
            got = None
        check(got is None,
              f"the parser accepted a block with {label} and returned {got!r} - a "
              f"partial parse is a declared event the grader will never look for")

    widest = max(len(v) for v in EVENTS_AS_WRITTEN.values())
    check(len(VOICES) >= widest,
          f"{len(VOICES)} voices for a widest declared event set of {widest}: a healthy "
          f"fixture would reuse a sound and sit on audio.distinct's floor, so its green "
          f"would stop meaning the submission is fine")
    for game in sorted(wp.TASKS):
        got = tuple(audio.GAME_EVENTS.get(game, ()))
        want = EVENTS_AS_WRITTEN.get(game, ())
        check(got == want,
              f"{game}: audio.GAME_EVENTS is {got}, the prompt as transcribed by hand "
              f"declares {want}")
        for stack in wp.STACKS:
            shown = tuple(rendered_event_names(wp.TASKS[game](stack)))
            check(shown == want,
                  f"{game}/{stack}: the RENDERED prompt declares {shown}, the "
                  f"transcription says {want}")


def expect(label: str, got: dict[str, tuple[bool, str]], cid: str, want: bool) -> None:
    global CHECKS
    CHECKS += 1
    passed, ev = got[cid]
    if passed != want:
        FAILURES.append(
            f"{label}: {cid} was {'PASS' if passed else 'FAIL'}, expected "
            f"{'PASS' if want else 'FAIL'} -- evidence: {ev[:200]}")


def case(tmp: Path, name: str):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def report() -> int:
    print(f"{CHECKS} expectations checked, {len(FAILURES)} unmet")
    for f in FAILURES:
        print(f"  FAIL {f}")
    return 1 if FAILURES else 0


def main() -> int:
    # BEFORE the tool guards, because it needs neither tool. A skip must not take the
    # cheapest check down with it: the declared-event pins read two Python modules, and
    # a machine without ffmpeg can still say whether the grader knows what the task asked
    # for. Their failures survive the skip below and turn it into a 1.
    pin_declared_events()

    if not audio.ffmpeg_available():
        print("ffmpeg is not installed; the fixture tests cannot run", file=sys.stderr)
        return report() or 2
    # check=False: a non-zero exit here means "just is absent", which is a skip (2), not
    # a crash. The status is read on this line.
    if subprocess.run(["just", "--version"], capture_output=True,
                      check=False).returncode != 0:
        print("just is not installed; the fixture tests cannot run", file=sys.stderr)
        return report() or 2

    with tempfile.TemporaryDirectory(prefix="audio-selftest-") as td:
        tmp = Path(td)

        # -- POSITIVE CONTROL: the grader can go green ---------------------- #
        good = case(tmp, "good")
        make_repo(good, healthy(good))
        g = verdicts(good)
        for cid, _q in audio.CRITERIA:
            expect("healthy", g, cid, True)

        # -- MUTANT 1: manifest missing one declared event ------------------ #
        m1 = case(tmp, "missing_event")
        man = healthy(m1)
        del man["sfx"]["game_over"]
        make_repo(m1, man)
        v = verdicts(m1)
        expect("missing_event", v, "audio.manifest", False)
        expect("missing_event", v, "audio.not_silent", True)   # the rest still hold

        # -- MUTANT 2: one cue is a silent file ----------------------------- #
        m2 = case(tmp, "silent_clip")
        man = healthy(m2)
        silence(m2 / "audio" / "paddle_hit.wav", 0.35)
        make_repo(m2, man)
        v = verdicts(m2)
        expect("silent_clip", v, "audio.not_silent", False)
        expect("silent_clip", v, "audio.manifest", True)

        # -- MUTANT 3: ALL music silent ------------------------------------- #
        m3 = case(tmp, "silent_music")
        man = healthy(m3)
        silence(m3 / "audio" / "music.wav", 6.0)
        make_repo(m3, man)
        expect("silent_music", verdicts(m3), "audio.not_silent", False)

        # -- MUTANT 4: one beep under five names ---------------------------- #
        # NOT byte copies: each is re-encoded at a DIFFERENT SAMPLE RATE, so any
        # filename, size or file-hash comparison would call them five different
        # sounds. Only decoded-content comparison catches this.
        m4 = case(tmp, "one_beep_many_names")
        sfx = {}
        for i, name in enumerate(PONG):
            p = tone(m4 / "audio" / f"{name}.wav", 0.35, 440.0,
                     rate=[22050, 24000, 32000, 44100, 48000][i])
            sfx[name] = {"file": str(p.relative_to(m4))}
        tone(m4 / "audio" / "music.wav", 6.0, 196.0, harmonics=(1.0, 2.0))
        make_repo(m4, {"music": {"file": "audio/music.wav", "loops": True}, "sfx": sfx})
        v = verdicts(m4)
        expect("one_beep_many_names", v, "audio.distinct", False)
        expect("one_beep_many_names", v, "audio.manifest", True)
        expect("one_beep_many_names", v, "audio.files_exist", True)
        expect("one_beep_many_names", v, "audio.not_silent", True)

        # -- MUTANT 5: a referenced file does not exist --------------------- #
        m5 = case(tmp, "missing_file")
        man = healthy(m5)
        (m5 / "audio" / "wall_bounce.wav").unlink()
        make_repo(m5, man)
        v = verdicts(m5)
        expect("missing_file", v, "audio.files_exist", False)
        expect("missing_file", v, "audio.manifest", True)

        # -- MUTANT 6: music not declared looping --------------------------- #
        m6 = case(tmp, "music_not_looping")
        man = healthy(m6)
        man["music"]["loops"] = False
        make_repo(m6, man)
        expect("music_not_looping", verdicts(m6), "audio.music_loops", False)

        # -- MUTANT 7: "music" is a click ----------------------------------- #
        m7 = case(tmp, "music_is_a_click")
        man = healthy(m7)
        tone(m7 / "audio" / "music.wav", 0.2, 196.0)
        make_repo(m7, man)
        expect("music_is_a_click", verdicts(m7), "audio.music_loops", False)

        # -- MUTANT 8: no manifest recipe at all ---------------------------- #
        m8 = case(tmp, "no_recipe")
        (m8 / "justfile").write_text("default:\n    @echo hi\n")
        v = verdicts(m8)
        for cid, _q in audio.CRITERIA:
            expect("no_recipe", v, cid, False)

        # -- MUTANT 9: manifest is not JSON --------------------------------- #
        m9 = case(tmp, "not_json")
        make_repo(m9, "this is not json")
        v = verdicts(m9)
        for cid, _q in audio.CRITERIA:
            expect("not_json", v, cid, False)

        # -- VARIANT 1: one beep under five names PLUS two unique extras ---- #
        #
        # THE INPUT NO MUTANT CAN CONSTRUCT (`AGENTS.md` rule 15), and the reason this
        # section exists. Mutant 4 above is the same submission without the extras, and
        # it was red for the whole time this was green: `audio.distinct` counted groups
        # over every `sfx` entry and floored on the declared events, so 2 undeclared
        # junk entries lifted a 1-group Pong manifest to 3 groups against a floor of 3
        # and bought a pass on the exact failure the criterion exists to catch
        # (`tasks/152`). Fail-open, which is the direction that costs the result.
        v1 = case(tmp, "one_beep_plus_extras")
        sfx = {}
        one = tone(v1 / "audio" / "one.wav", 0.35, 440.0)
        for name in PONG:
            sfx[name] = {"file": str(one.relative_to(v1))}
        tone(v1 / "audio" / "music.wav", 6.0, 196.0, harmonics=(1.0, 2.0), amp=0.4)
        man = add_extras(
            v1, {"music": {"file": "audio/music.wav", "loops": True}, "sfx": sfx}, 2)
        make_repo(v1, man)
        v = verdicts(v1)
        expect("one_beep_plus_extras", v, "audio.distinct", False)
        # ...and every other criterion still holds, so the failure is attributable.
        expect("one_beep_plus_extras", v, "audio.manifest", True)
        expect("one_beep_plus_extras", v, "audio.files_exist", True)
        expect("one_beep_plus_extras", v, "audio.not_silent", True)

        # -- VARIANT 2: a healthy submission that also ships extras --------- #
        #
        # The other direction, and the reason the repair does not simply fail undeclared
        # entries. The prompt asks for an entry per declared event and forbids no others,
        # so extra cues are a design choice a submission is entitled to make. A repair
        # that failed them would be fail-CLOSED and would cost trials.
        v2 = case(tmp, "healthy_plus_extras")
        make_repo(v2, add_extras(v2, healthy(v2), 2))
        v = verdicts(v2)
        for cid, _q in audio.CRITERIA:
            expect("healthy_plus_extras", v, cid, True)

        # -- g4_platformer: green, and red on a manifest missing a cue ------ #
        #
        # `GAME_EVENTS` had no `g4_platformer` key, so `expected` was empty and
        # `audio.manifest` could not fail on this game at all - 24 stored gradings deep
        # (`tasks/151`). The green half matters as much: 8 declared events, 8 distinct
        # sounds, floor 4 - a real platformer still passes.
        g4 = case(tmp, "g4_healthy")
        make_repo(g4, healthy(g4, "g4_platformer"))
        v = verdicts(g4, "g4_platformer")
        for cid, _q in audio.CRITERIA:
            expect("g4_healthy", v, cid, True)

        g4m = case(tmp, "g4_missing_event")
        man = healthy(g4m, "g4_platformer")
        del man["sfx"]["stage_clear"]
        make_repo(g4m, man)
        v = verdicts(g4m, "g4_platformer")
        expect("g4_missing_event", v, "audio.manifest", False)
        expect("g4_missing_event", v, "audio.not_silent", True)

        # -- g3_arena: green on all 9, red on the 6 the grader used to know -- #
        #
        # The arena prompt declares 9 events and the transcription in `audio.py` held 6,
        # so a submission shipping exactly those 6 passed `audio.manifest` while missing
        # 3 cues the task asked for. VARIANT 3 is that submission - another input no
        # mutant constructs - and the green row above it is what says the wider
        # expectation has not simply made the criterion unpassable.
        g3ok = case(tmp, "g3_healthy")
        make_repo(g3ok, healthy(g3ok, "g3_arena"))
        v = verdicts(g3ok, "g3_arena")
        for cid, _q in audio.CRITERIA:
            expect("g3_healthy", v, cid, True)

        g3 = case(tmp, "g3_six_of_nine")
        man = healthy(g3, "g3_arena")
        for gone in ("enemy_spawn", "wall_graze", "multiplier"):
            del man["sfx"][gone]
        make_repo(g3, man)
        v = verdicts(g3, "g3_arena")
        expect("g3_six_of_nine", v, "audio.manifest", False)
        expect("g3_six_of_nine", v, "audio.files_exist", True)

        # -- MUTANT 10: a task the suite declares no events for ------------- #
        #
        # Fail-closed, not skipped. Nothing is missing when nothing is expected, so a
        # grader with no contract would report five passes having measured none of them.
        v = verdicts(good, "g9_probe")
        for cid, _q in audio.CRITERIA:
            expect("unknown_game", v, cid, False)

        # -- NOT a mutant: engine noise on stdout must still be read -------- #
        # Two of the four stacks print a banner before a batchmode command's real
        # output. A grader that demanded byte-pure stdout would fail those two for a
        # reason unrelated to their audio - a defect that can only fire on a subset of
        # arms is bias, not noise (FINDINGS #25).
        noisy = case(tmp, "noisy_stdout")
        man = healthy(noisy)
        make_repo(noisy, "Engine 6000.0.45f1 (batchmode)\nLicense check OK\n"
                         + json.dumps(man) + "\n")
        v = verdicts(noisy)
        for cid, _q in audio.CRITERIA:
            expect("noisy_stdout", v, cid, True)

        # -- audio.triggered: green, then three ways red -------------------- #
        fired_all = list(PONG)
        c = audio.triggered_criterion(good, "g1_pong", fired_all)
        check(c.passed, f"triggered/healthy: expected PASS -- {c.evidence[:200]}")

        c = audio.triggered_criterion(m1, "g1_pong", fired_all)  # game_over unmapped
        check(not c.passed, "triggered/missing_event: expected FAIL, got PASS")

        c = audio.triggered_criterion(m2, "g1_pong", ["paddle_hit"])  # silent cue
        check(not c.passed, "triggered/silent_clip: expected FAIL, got PASS")

        c = audio.triggered_criterion(good, "g1_pong", [])  # nothing fired
        check(not c.passed,
              "triggered/no_events: expected FAIL (fail-closed), got PASS")

    return report()


if __name__ == "__main__":
    raise SystemExit(main())
