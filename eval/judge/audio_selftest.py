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

THE LOCK PATH IS PINNED HERE TOO (tasks/214). FINDINGS #25's exclusion lived only in
`probe.unusable_criteria`, and `probe.drive` appended `audio.triggered` after it: on a
lock-conflicted session every bot criterion came back `scored=False` while
`audio.triggered` alone was counted a scored failure - "the driven run emitted no events
at all" - on exactly the arm the exclusion exists to protect. 2 mutants here restore
that composition and the un-flagged `read_manifest` tuple; the fail-closed default (a
run that HAPPENED and emitted nothing) has its own rows and is not loosened.

AND SO IS THE LOCK VOCABULARY ITSELF (tasks/215). `LOCK_HINTS` was two never-compared
hand copies, each with the bare substring "lock" - an open-class member that matches
benign engine words and had 0 true positives on the stored corpus. The set is now one
closed-class definition in probe.py, and this file pins it in both directions: the 2
stored pollution true positives classify through both readers, the "Clock"/"Deadlock"
banners classify through neither, and 3 mutants (substring restored, phrase dropped,
equal-but-distinct copy) prove each pin can fail.
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
import probe  # noqa: E402

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

#: A whole declaration line: the quoted event name, then nothing or a description.
#: Written out here rather than imported from the parser under test, for the same reason
#: as the list above.
EVENT_LINE = re.compile(r'"([a-z_][a-z0-9_]*)"(?:\s+\S.*)?')

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
    names = []
    for line in body.splitlines():
        if not line.strip():
            continue
        m = EVENT_LINE.fullmatch(line.strip())
        if m is None:
            raise ValueError(f"{line!r} is inside a rendered events block and is not an "
                             f"event declaration")
        names.append(m.group(1))
    return names


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

    # The RENDERED-block reader, in the direction a comparison cannot reach. A prompt
    # carrying every declaration plus an unreadable extra line still equals the
    # transcription, so filtering nonmatching lines would agree while the contract the
    # agent was shown had changed.
    ok = wp.TASKS["g1_pong"]("rust")
    check(tuple(rendered_event_names(ok)) == EVENTS_AS_WRITTEN["g1_pong"],
          "the rendered reader disagrees with the transcription on an untouched prompt")
    # The insertion point is INSIDE the events fence. The state block a few lines above
    # holds quoted keys, so a whole-document replace would plant the line where the
    # reader is not looking and the pin would pass having tested nothing.
    cut = ok.index("```", ok.index(EVENTS_MARKER)) + 3
    for label, extra in (("a line that is not a declaration", "jump - the player jumped"),
                         ("a name with trailing garbage", '"jump"typo')):
        spoilt = ok[:cut] + "\n" + extra + ok[cut:]
        try:
            got = rendered_event_names(spoilt)
        except ValueError:
            got = None
        check(got is None,
              f"the rendered reader accepted {label} and returned {got!r}")


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

        # -- the lock path: a driven run that never happened ---------------- #
        #
        # FINDINGS #25's exclusion is computed by `unusable_criteria` INSIDE
        # `probe.drive`, and `audio.triggered` used to be appended AFTER it, composed
        # from `fired=[]` with no way to know the run had not happened. On a
        # lock-conflicted session every bot criterion came back `scored=False` while
        # `audio.triggered` alone was counted a scored failure -- "no events at all"
        # -- on the one stack whose lock signature the exclusion exists for. The
        # empty-fired branch above stays fail-closed BY CONTRACT: a run that HAPPENED
        # and emitted nothing is a real failure. The distinguishing fact is whether
        # the run happened, which only the caller knows, so it now travels with the
        # criterion as `lock_note`.
        #
        # The stub replaces `probe.ProbeSession` wholesale (`drive()` names the class
        # directly), so no engine, no child process and no `just` is needed here.
        def drive_with(session_cls: type) -> dict:
            class LockBot(probe.Bot):
                game = "g1_pong"
                criteria = [("stub.ok", "the stub criterion the bot reports")]

                def run(self, session) -> list[probe.Criterion]:
                    return [probe.Criterion("stub.ok", "the stub criterion the bot "
                                            "reports", True, "the stub ran")]

            real = probe.ProbeSession
            probe.ProbeSession = session_cls
            try:
                return probe.drive(LockBot(), good, audio_game="g1_pong")
            finally:
                probe.ProbeSession = real

        class LockRefused:
            """`__enter__` raises the one ProbeError that says nothing about the game."""

            def __init__(self, *a, **k) -> None:
                pass

            def __enter__(self):
                raise probe.ProbeError(
                    "It looks like another Unity instance is running with this "
                    "project open.", lock_conflict=True)

            def __exit__(self, *a) -> bool:
                return False

        class EngineDied(LockRefused):
            """A probe failure that is NOT a lock: the same shape, no `lock_conflict`."""

            def __enter__(self):
                raise probe.ProbeError("engine died before the tick-0 header")

        class RanButSilent:
            """A session that opened, drove and emitted nothing: the genuine empty."""

            def __init__(self, *a, **k) -> None:
                self.history = []
                self.ticks_sent = 0

            def __enter__(self):
                return self

            def __exit__(self, *a) -> bool:
                return False

            def report_stderr(self) -> str:
                return ""

        def criterion_of(out: dict, cid: str) -> dict:
            return next(c for c in out["criteria"] if c["id"] == cid)

        out = drive_with(LockRefused)
        a = criterion_of(out, "audio.triggered")
        check(a["scored"] is False and a["passed"] is False,
              f"lock_refused: audio.triggered must be excluded, not failed -- "
              f"scored={a['scored']} passed={a['passed']} ev={a['evidence'][:160]}")
        check("NOT MEASURED" in a["evidence"] and "project-lock" in a["evidence"],
              f"lock_refused: the reason must name the project lock, "
              f"got {a['evidence'][:200]!r}")
        check(criterion_of(out, "stub.ok")["scored"] is False,
              "lock_refused: the #25 exclusion must still hold for the bot's own "
              "criteria")
        check(out["total"] == 0 and out["usable"] is False
              and "audio.triggered" in out["unscored"],
              f"lock_refused: the exclusion must actually exclude -- "
              f"total={out['total']} usable={out['usable']} "
              f"unscored={sorted(out['unscored'])}")

        out = drive_with(EngineDied)
        a = criterion_of(out, "audio.triggered")
        check(a["scored"] is True and a["passed"] is False
              and "no events at all" in a["evidence"],
              f"non_lock_probe_error: a probe failure that is NOT a lock stays "
              f"scored=True failed -- scored={a['scored']} ev={a['evidence'][:160]}")
        check(criterion_of(out, "stub.ok")["scored"] is True,
              "non_lock_probe_error: the bot's own criterion stays a real failure too")

        out = drive_with(RanButSilent)
        a = criterion_of(out, "audio.triggered")
        check(a["scored"] is True and a["passed"] is False
              and "no events at all" in a["evidence"],
              f"ran_and_emitted_nothing: the fail-closed default must NOT be loosened "
              f"-- scored={a['scored']} ev={a['evidence'][:160]}")

        # MUTANT 11: the append as it stood -- composed after `unusable_criteria`
        # from `fired=[]` with no lock bit, which is the defect this section exists to
        # prevent, reproduced on demand. It must scorch the lock fixture and stay green
        # on BOTH controls: a scorch that also failed the controls would be a different
        # (and fail-closed) defect, not this one.
        real_tc = audio.triggered_criterion

        def blind_append(repo, game, fired, env=None, *, lock_note=None):
            return real_tc(repo, game, fired, env)

        audio.triggered_criterion = blind_append
        try:
            scored = {label: criterion_of(drive_with(cls), "audio.triggered")["scored"]
                      for label, cls in (("lock", LockRefused),
                                         ("nonlock", EngineDied),
                                         ("quiet", RanButSilent))}
        finally:
            audio.triggered_criterion = real_tc
        check(scored["lock"] is True,
              f"mutant 'append without the lock bit' did not scorch the lock fixture "
              f"-- audio.triggered scored={scored['lock']}")
        check(scored["nonlock"] is True and scored["quiet"] is True,
              f"mutant 'append without the lock bit' must leave both controls green -- "
              f"got {scored}")

        # -- the same hole inside audio.py: a manifest read the lock ate ------ #
        #
        # `read_manifest` retries while the failure matches LOCK_HINTS, and the block
        # above it calls that case "bias, not noise (FINDINGS #25)" -- but it returned
        # (manifest, note, exit) with no lock flag, so `triggered_criterion`'s manifest
        # branch scored it True/failed like any broken manifest. The retry implemented
        # the waiting; the verdict after the waiting did not implement the exclusion.
        # `audio.time.sleep` is stubbed so the real retry loop runs without its wall
        # clock (4s + 8s per exhausted read).
        _counter = iter(range(100))

        def manifest_repo(note: str) -> Path:
            d = case(tmp, f"manifest_lock_{next(_counter)}")
            (d / "justfile").write_text(
                f"audio-manifest:\n    @echo \"{note}\" >&2; exit 1\n")
            return d

        LOCK_NOTE = ("It looks like another Unity instance is running with this "
                     "project open.")

        real_sleep = audio.time.sleep
        audio.time.sleep = lambda _s: None
        try:
            c = audio.triggered_criterion(manifest_repo(LOCK_NOTE), "g1_pong",
                                          ["paddle_hit"])
            check(c.scored is False and c.passed is False,
                  f"manifest_lock_exhausted: a lock-eaten manifest read must be "
                  f"excluded, not failed -- scored={c.scored} ev={c.evidence[:200]}")
            check("NOT MEASURED" in c.evidence and "project-lock" in c.evidence,
                  f"manifest_lock_exhausted: the reason must name the project lock, "
                  f"got {c.evidence[:200]!r}")

            broken = audio.triggered_criterion(
                manifest_repo("audio-manifest exit 1: json: cannot unmarshal string "
                              "into Go value of type main.Manifest"),
                "g1_pong", ["paddle_hit"])
            check(broken.scored is True and broken.passed is False,
                  f"manifest_broken: a manifest that is genuinely broken stays "
                  f"scored=True failed -- scored={broken.scored} "
                  f"ev={broken.evidence[:200]}")
        finally:
            audio.time.sleep = real_sleep

        # MUTANT 12: `read_manifest` without the lock bit -- the caller cannot tell a
        # lock refusal from a broken manifest, which is exactly what the 3-tuple was.
        # It must scorch the lock-exhausted fixture and leave the broken one alone;
        # only the lock fixture is asserted under it because that is the only input
        # the removed bit discriminates.
        real_rm = audio.read_manifest

        def lock_blind_manifest(repo, env=None, timeout_s=900, attempts=3):
            m, note, code, _lock = real_rm(repo, env, timeout_s, attempts)
            return audio.ManifestRead(m, note, code, False)

        audio.read_manifest = lock_blind_manifest
        audio.time.sleep = lambda _s: None
        try:
            try:
                c = audio.triggered_criterion(manifest_repo(LOCK_NOTE), "g1_pong",
                                              ["paddle_hit"])
                scorch, ev = c.scored, c.evidence
            except Exception as ex:  # noqa: BLE001 -- cannot fire against the fixed
                scorch = None        # API; recording it is the point (capture_selftest
                ev = f"{type(ex).__name__}: {ex}"  # runs the file against the unfixed one)
        finally:
            audio.time.sleep = real_sleep
            audio.read_manifest = real_rm
        check(scorch is True,
              f"mutant 'read_manifest without the lock bit' did not scorch the "
              f"lock-exhausted manifest fixture -- scored={scorch} ev={ev[:160]}")

        # -- ONE VOCABULARY, CLOSED CLASS (tasks/215) ------------------------ #
        #
        # LOCK_HINTS lived as two hand copies -- `probe.ProbeSession`'s class
        # attribute and `audio.py`'s module tuple -- never compared, and each held
        # one open-class member: the bare substring "lock". It matches every benign
        # engine word carrying it ("Clock", "Deadlock") while on the whole stored
        # corpus it has 0 true positives and 0 records of any kind through it. A
        # match used to be only a retry on the audio side, but tasks/214 made a
        # lock-eaten read EXCLUDE `audio.triggered`, so over-breadth is now
        # fail-open on BOTH readers and only the retry cost differs. The set is
        # therefore one definition in probe.py, closed: engine refusal wordings
        # only, two of them observed verbatim in the stored pollution lines.
        EXPECTED_LOCK_HINTS = ("another unity instance",    # stored TP, 76 occurrences
                               "cannot open the same project",  # stored TP, 76 occurrences
                               "already running",
                               "resource busy")

        check(audio.LOCK_HINTS is probe.LOCK_HINTS,
              "lock_hints_one_definition: audio must alias probe's tuple, not hold "
              "a second hand copy -- two never-compared copies are how the bare "
              "'lock' member survived in both")
        check(tuple(audio.LOCK_HINTS) == EXPECTED_LOCK_HINTS,
              f"lock_hints_closed_class: the vocabulary must be exactly the four "
              f"engine refusal wordings, bare substring gone -- got "
              f"{tuple(audio.LOCK_HINTS)!r}")

        # The 2 stored true positives, verbatim, through BOTH readers: the probe
        # classifier that decides retries inside `start()`, and the audio
        # manifest-note path whose lock bit now excludes `audio.triggered`. This
        # is the pin that says the narrowing did not blunt the FINDINGS #25
        # remedy: both stored refusals still classify.
        TP1 = ("[stdout pollution] It looks like another Unity instance is "
               "running with this project open.")
        TP2 = ("[stdout pollution] Multiple Unity instances cannot open the "
               "same project.")
        for tp in (TP1, TP2):
            check(probe.ProbeSession._looks_like_lock_conflict(probe.ProbeError(tp)),
                  f"lock_tp_probe_reader: the stored pollution line must still "
                  f"classify as a lock conflict -- {tp[:80]!r}")
            m = audio.read_manifest(manifest_repo(tp))
            check(m.manifest is None and m.lock is True,
                  f"lock_tp_audio_reader: the stored pollution line must still buy "
                  f"the lock verdict on the manifest path -- lock={m.lock} "
                  f"note={m.note[:100]!r}")

        # The benign banners the bare substring used to eat: both words carry
        # "lock" inside them, neither is a refusal. On the probe path a match ends
        # a genuinely hung submission as NOT MEASURED (fail-open on the failure
        # mode this tier exists to catch); on the audio path it now excludes the
        # criterion. Both readers pinned.
        for banner in ("[stdout pollution] Clock: 60 fps",
                       "[stdout pollution] Deadlock detection: off"):
            check(not probe.ProbeSession._looks_like_lock_conflict(
                      probe.ProbeError(banner)),
                  f"benign_banner_probe_reader: {banner!r} must not classify as a "
                  f"lock conflict")
            m = audio.read_manifest(manifest_repo(banner))
            check(m.manifest is None and m.lock is False,
                  f"benign_banner_audio_reader: {banner!r} must not buy the lock "
                  f"verdict -- lock={m.lock} note={m.note[:100]!r}")

        # MUTANT 13: the bare substring back in the set. It must scorch the
        # benign-banner pins on BOTH readers -- the stored true positives classify
        # under it either way, so they are exactly the rows that cannot catch it.
        real_hints = probe.LOCK_HINTS
        probe.LOCK_HINTS = real_hints + ("lock",)
        audio.LOCK_HINTS = probe.LOCK_HINTS
        try:
            flipped = [
                probe.ProbeSession._looks_like_lock_conflict(
                    probe.ProbeError("[stdout pollution] Clock: 60 fps")),
                audio.read_manifest(
                    manifest_repo("Deadlock detection: off")).lock,
            ]
        finally:
            probe.LOCK_HINTS = real_hints
            audio.LOCK_HINTS = probe.LOCK_HINTS
        check(all(flipped),
              f"mutant 'bare lock restored' did not scorch the benign-banner pins "
              f"-- probe_and_audio={flipped}")

        # MUTANT 14: a specific phrase dropped. It must scorch the true-positive
        # pin for THAT phrase and no other -- the second stored line still
        # classifies under it, so the red row is attributable to the removal.
        probe.LOCK_HINTS = tuple(h for h in real_hints
                                 if h != "another unity instance")
        audio.LOCK_HINTS = probe.LOCK_HINTS
        try:
            tp1_gone = not probe.ProbeSession._looks_like_lock_conflict(
                probe.ProbeError(TP1))
            tp1_audio_gone = audio.read_manifest(manifest_repo(TP1)).lock is False
            tp2_still = probe.ProbeSession._looks_like_lock_conflict(
                probe.ProbeError(TP2))
        finally:
            probe.LOCK_HINTS = real_hints
            audio.LOCK_HINTS = probe.LOCK_HINTS
        check(tp1_gone and tp1_audio_gone,
              f"mutant 'phrase dropped' did not scorch the matching true-positive "
              f"pin -- probe_red={tp1_gone} audio_red={tp1_audio_gone}")
        check(tp2_still,
              "mutant 'phrase dropped' must leave the OTHER stored line classified")

        # MUTANT 15: an equal copy that is not the same object -- exactly the
        # shape the two hand copies had. It must turn the one-definition pin red.
        # (Not `tuple(t)`: on an exact tuple that IS t, and the mutant would
        # manufacture no copy to catch.)
        audio.LOCK_HINTS = tuple(list(audio.LOCK_HINTS))
        try:
            drifted = audio.LOCK_HINTS is probe.LOCK_HINTS
        finally:
            audio.LOCK_HINTS = probe.LOCK_HINTS
        check(drifted is False,
              "mutant 'equal copy' did not turn the identity pin red")

    return report()


if __name__ == "__main__":
    raise SystemExit(main())
