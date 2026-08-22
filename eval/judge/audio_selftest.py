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
"""

from __future__ import annotations

import json
import math
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


PONG = audio.GAME_EVENTS["g1_pong"]

# Five clearly different sounds: different fundamentals, harmonic content and envelopes.
VOICES = [
    dict(freq=220.0, harmonics=(1.0,), decay=0.0),
    dict(freq=880.0, harmonics=(1.0, 3.0, 5.0), decay=6.0),
    dict(freq=330.0, harmonics=(1.0, 2.0), decay=2.0),
    dict(freq=1320.0, harmonics=(1.0,), decay=12.0),
    dict(freq=110.0, harmonics=(1.0, 2.0, 3.0, 4.0), decay=1.0),
]


def healthy(root: Path) -> dict:
    """A submission that should pass all five criteria."""
    sfx = {}
    for i, name in enumerate(PONG):
        p = tone(root / "audio" / f"{name}.wav", 0.35, **VOICES[i % len(VOICES)])
        sfx[name] = {"file": str(p.relative_to(root))}
    tone(root / "audio" / "music.wav", 6.0, 196.0, harmonics=(1.0, 2.0), amp=0.4)
    return {"music": {"file": "audio/music.wav", "loops": True}, "sfx": sfx}


# --------------------------------------------------------------------------- #

FAILURES: list[str] = []
CHECKS = 0


def verdicts(repo: Path) -> dict[str, tuple[bool, str]]:
    out = audio.collect(repo, "g1_pong")
    return {c["id"]: (c["passed"], c.get("evidence", "")) for c in out["criteria"]}


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


def main() -> int:
    global CHECKS
    if not audio.ffmpeg_available():
        print("ffmpeg is not installed; these tests cannot run", file=sys.stderr)
        return 2
    if subprocess.run(["just", "--version"], capture_output=True).returncode != 0:
        print("just is not installed; these tests cannot run", file=sys.stderr)
        return 2

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
        CHECKS += 1
        if not c.passed:
            FAILURES.append(f"triggered/healthy: expected PASS -- {c.evidence[:200]}")

        c = audio.triggered_criterion(m1, "g1_pong", fired_all)  # game_over unmapped
        CHECKS += 1
        if c.passed:
            FAILURES.append("triggered/missing_event: expected FAIL, got PASS")

        c = audio.triggered_criterion(m2, "g1_pong", ["paddle_hit"])  # silent cue
        CHECKS += 1
        if c.passed:
            FAILURES.append("triggered/silent_clip: expected FAIL, got PASS")

        c = audio.triggered_criterion(good, "g1_pong", [])  # nothing fired
        CHECKS += 1
        if c.passed:
            FAILURES.append("triggered/no_events: expected FAIL (fail-closed), got PASS")

    print(f"{CHECKS} expectations checked, {len(FAILURES)} unmet")
    for f in FAILURES:
        print(f"  FAIL {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
