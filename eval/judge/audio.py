#!/usr/bin/env python3
"""The audio criteria: everything about sound that a script can answer.

Audio was a total blind spot until now - no task asked for it, no tier examined it, no
criterion mentioned it. The task prompts now require looping background music and a
sound effect for every event the game declares, published through a `just audio-manifest`
contract. This module is the deterministic half of grading that.

DESIGN RULES, each of which exists because the opposite has already cost this project a
run:

1. **Decode, never trust metadata.** A file that exists, has a `.wav` extension and a
   plausible size can still be two seconds of digital silence. Every check here runs on
   DECODED SAMPLES.

2. **`audio.distinct` compares decoded content, never filenames.** One beep copied to
   five names is the exact failure the criterion exists to catch, and it is invisible to
   any filename or even any file-hash comparison once the copies are re-encoded.

3. **Fail-closed.** A manifest that will not run, will not parse, or names a file that
   will not decode scores FALSE with the reason recorded. It is never "skipped":
   `total=0 passed=0` is indistinguishable from correct failure.

4. **Every criterion here has a mutant in `audio_selftest.py`** that makes it go red. A
   criterion that cannot fail is worse than absent, because it looks like success.

Decoding goes through `ffmpeg`, so the format the agent chose (wav, ogg, mp3, flac) is
not a constraint on the grader. If `ffmpeg` is missing, every audio criterion fails with
that as the recorded reason rather than silently passing.
"""

from __future__ import annotations

import cmath
import json
import math
import os
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probe import Criterion

# --------------------------------------------------------------------------- #
# What each game declares. These are the event names in the task prompt, which is
# a functional contract with the probe, not a rubric item - the prompt states them
# verbatim and tells the agent to spell them exactly.
# --------------------------------------------------------------------------- #

GAME_EVENTS: dict[str, tuple[str, ...]] = {
    "g1_pong": ("paddle_hit", "wall_bounce", "score_left", "score_right", "game_over"),
    "g2_tetris3d": ("spawn", "move", "rotate", "lock", "layer_clear", "game_over"),
    "g3_arena": ("fire", "enemy_hit", "enemy_dead", "player_hit", "wave_start",
                 "game_over"),
}

CRITERIA = [
    ("audio.manifest",
     "Does `just audio-manifest` emit valid JSON with an entry for every event the "
     "game declares?"),
    ("audio.files_exist",
     "Does every file the manifest references exist and decode to audio samples?"),
    ("audio.not_silent",
     "Is each clip actually audible, rather than a silent file that satisfies the "
     "contract?"),
    ("audio.distinct",
     "Are the sound effects distinct sounds, rather than one clip reused under many "
     "names?"),
    ("audio.music_loops",
     "Is the music declared looping, and long enough to be music rather than a click?"),
]

# ---- thresholds, all stated rather than implied ---------------------------- #

#: RMS floor, in linear amplitude over the whole clip. -46 dBFS. A clip quieter than
#: this is inaudible under any reasonable mix; a real effect sits 20-30 dB above it.
SILENCE_RMS = 0.005
#: Peak floor. Catches a clip that is silent except for one denormal sample.
SILENCE_PEAK = 0.02
#: Music shorter than this is a click, a sting or a truncated file - not a loop.
MUSIC_MIN_SECONDS = 2.0
#: Two clips count as THE SAME SOUND above this cosine similarity between their
#: 64-band magnitude spectra. Identical content scores 1.0 exactly; two different
#: synthesised beeps land far below. Deliberately conservative: the criterion should
#: only fire on near-identical content, because sharing one sound between two events
#: is a legitimate design choice the task explicitly permits.
SAME_SOUND_COSINE = 0.9995
#: ...and their durations must also agree this closely to count as the same sound.
SAME_SOUND_DURATION_RATIO = 0.005
#: Analysis rate. Everything is resampled here before comparison so a 44.1 kHz clip and
#: a 48 kHz encode of the same sound compare equal.
ANALYSIS_HZ = 8000
#: Cap on samples fed to the FFT (power of two): 4 seconds at the analysis rate.
FFT_N = 32768
SPECTRAL_BANDS = 64
#: Longest window decoded for analysis. Bounds the grader's cost against a submission
#: that ships a five-minute track; the REPORTED duration still comes from the file.
ANALYSIS_SECONDS = 30


class AudioError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Decoding
# --------------------------------------------------------------------------- #


@dataclass
class Clip:
    path: Path
    samples: list[float]      # mono, float, ANALYSIS_HZ, first ANALYSIS_SECONDS
    seconds: float            # the WHOLE clip, from the container
    analysed_seconds: float   # how much of it was decoded
    rms: float
    peak: float
    spectrum: list[float]     # SPECTRAL_BANDS, L2-normalised

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "seconds": round(self.seconds, 3),
                "analysed_seconds": round(self.analysed_seconds, 3),
                "rms": round(self.rms, 5), "peak": round(self.peak, 5),
                "samples": len(self.samples)}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def decode(path: Path) -> Clip:
    """Decode any container ffmpeg understands to mono float samples at ANALYSIS_HZ."""
    if not ffmpeg_available():
        raise AudioError("ffmpeg is not installed; audio cannot be decoded")
    if not path.exists():
        raise AudioError(f"no such file: {path}")
    # Analyse at most ANALYSIS_SECONDS. A submission is free to ship a five-minute
    # ambient track, and decoding all of it into a Python list of floats would make the
    # grader's cost a function of the submission's asset length. The reported duration
    # still comes from the file's own metadata, so a capped analysis never turns into a
    # wrong number.
    argv = ["ffmpeg", "-v", "error", "-i", str(path), "-t", str(ANALYSIS_SECONDS),
            "-f", "f32le", "-ac", "1", "-ar", str(ANALYSIS_HZ), "-"]
    p = subprocess.run(argv, capture_output=True, timeout=120)
    if p.returncode != 0 or not p.stdout:
        raise AudioError(
            f"ffmpeg could not decode {path.name} (exit {p.returncode}): "
            f"{p.stderr.decode('utf-8', 'replace')[:200].strip() or 'no samples'}")
    n = len(p.stdout) // 4
    samples = list(struct.unpack(f"<{n}f", p.stdout[: n * 4]))
    if not samples:
        raise AudioError(f"{path.name} decoded to zero samples")
    peak = max(abs(s) for s in samples)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    analysed = len(samples) / ANALYSIS_HZ
    return Clip(path=path, samples=samples, seconds=duration(path) or analysed,
                analysed_seconds=analysed, rms=rms, peak=peak,
                spectrum=spectrum(samples))


def duration(path: Path) -> float | None:
    """True duration from the container, in seconds, or None if it cannot be read."""
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=60)
    try:
        return float(p.stdout.strip())
    except (ValueError, AttributeError):
        return None


def _fft(values: list[complex]) -> list[complex]:
    """Iterative radix-2 FFT. `len(values)` must be a power of two."""
    n = len(values)
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    length = 2
    while length <= n:
        angle = -2j * cmath.pi / length
        step = cmath.exp(angle)
        for start in range(0, n, length):
            w = 1 + 0j
            half = length >> 1
            for k in range(start, start + half):
                u = out[k]
                v = out[k + half] * w
                out[k] = u + v
                out[k + half] = u - v
                w *= step
        length <<= 1
    return out


def spectrum(samples: list[float]) -> list[float]:
    """A SPECTRAL_BANDS-long, L2-normalised magnitude spectrum of the clip.

    This is the fingerprint `audio.distinct` compares. It is computed from decoded
    samples, so it is invariant to container, codec, sample rate, filename and file
    bytes - which is the whole point: a copy of one beep under five names is the
    failure being hunted, and it survives every cheaper comparison.
    """
    window = samples[:FFT_N]
    if not window:
        return [0.0] * SPECTRAL_BANDS
    peak = max(abs(s) for s in window) or 1.0
    padded = [complex(s / peak, 0.0) for s in window]
    padded += [0j] * (FFT_N - len(padded))
    mags = [abs(c) for c in _fft(padded)[: FFT_N // 2]]
    per = len(mags) // SPECTRAL_BANDS
    bands = [sum(mags[i * per:(i + 1) * per]) for i in range(SPECTRAL_BANDS)]
    norm = math.sqrt(sum(b * b for b in bands))
    return [b / norm for b in bands] if norm else bands


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))   # both are already L2-normalised


def same_sound(a: Clip, b: Clip) -> bool:
    lo, hi = sorted((a.analysed_seconds, b.analysed_seconds))
    if hi <= 0 or (hi - lo) / hi > SAME_SOUND_DURATION_RATIO:
        return False
    return cosine(a.spectrum, b.spectrum) >= SAME_SOUND_COSINE


def distinct_groups(clips: list[Clip]) -> list[list[Clip]]:
    """Group clips that are the same sound. Content-based, never filename-based."""
    groups: list[list[Clip]] = []
    for clip in clips:
        for g in groups:
            if same_sound(g[0], clip):
                g.append(clip)
                break
        else:
            groups.append([clip])
    return groups


# --------------------------------------------------------------------------- #
# The manifest
# --------------------------------------------------------------------------- #


#: An engine that takes a project-wide lock refuses a second session while the previous
#: one is still shutting down. That says nothing about the submission's audio, and it
#: can only happen on the stacks that take such a lock - so treating it as a failure
#: deducts from one arm of a four-way comparison and from no other. Bias, not noise
#: (FINDINGS #25). The probe reader retries for exactly this reason; so does this.
LOCK_HINTS = ("another unity instance", "cannot open the same project", "lock",
              "already running", "resource busy")


def read_manifest(repo: Path, env: dict[str, str] | None = None,
                  timeout_s: int = 900, attempts: int = 3
                  ) -> tuple[dict[str, Any] | None, str, int]:
    """Run `just audio-manifest` and parse its stdout. Returns (manifest, note, exit).

    Retries while the failure looks like an engine project lock rather than a problem
    with the manifest.
    """
    note, code = "", 1
    for attempt in range(1, attempts + 1):
        data, note, code = _read_manifest_once(repo, env, timeout_s)
        if data is not None:
            return data, "", code
        if not any(h in note.lower() for h in LOCK_HINTS):
            return None, note, code
        time.sleep(min(20.0, 4.0 * attempt))
    return None, f"after {attempts} attempts: {note}", code


def _read_manifest_once(repo: Path, env: dict[str, str] | None, timeout_s: int
                        ) -> tuple[dict[str, Any] | None, str, int]:
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(["just", "audio-manifest"], cwd=repo, capture_output=True,
                           text=True, timeout=timeout_s, env=e)
    except subprocess.TimeoutExpired:
        return None, f"`just audio-manifest` timed out after {timeout_s}s", 124
    except OSError as ex:
        return None, f"could not run `just audio-manifest`: {ex}", 127
    if p.returncode != 0:
        return None, (f"`just audio-manifest` exit {p.returncode}: "
                      f"{(p.stderr or p.stdout)[-300:].strip()}"), p.returncode
    text = p.stdout.strip()
    if not text:
        return None, "`just audio-manifest` printed nothing to stdout", p.returncode
    data = extract_object(text)
    if data is None:
        return None, (f"`just audio-manifest` stdout contains no JSON object; "
                      f"first 300 chars: {text[:300]!r}"), p.returncode
    return data, "", p.returncode


def extract_object(text: str) -> dict[str, Any] | None:
    """The manifest object out of stdout that may also carry engine noise.

    Two of the four stacks print a banner, a licence line or an asset-import notice on
    stdout before a batchmode command's real output, and `just` itself echoes recipe
    lines in some configurations. Demanding byte-pure stdout would fail those stacks and
    pass the other two for a reason that has nothing to do with their audio - a defect
    that can only fire on a subset of arms is bias, not noise (FINDINGS #25), and this
    project has already paid for that lesson twice. The probe reader tolerates the same
    pollution for the same reason.

    Prefers the largest balanced object that looks like a manifest, so a stray `{}` in a
    log line cannot win against the real thing.
    """
    try:
        whole = json.loads(text)
        if isinstance(whole, dict):
            return whole
    except json.JSONDecodeError:
        pass
    best: dict[str, Any] | None = None
    for start, ch in enumerate(text):
        if ch != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        cand = json.loads(text[start:end + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(cand, dict) and ("music" in cand or "sfx" in cand):
                        if best is None or len(cand) > len(best):
                            best = cand
                    break
    return best


def _resolve(repo: Path, ref: Any) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    p = Path(ref)
    return p if p.is_absolute() else (repo / p)


# --------------------------------------------------------------------------- #
# The criteria
# --------------------------------------------------------------------------- #


def collect(repo: Path, game: str, env: dict[str, str] | None = None
            ) -> dict[str, Any]:
    """Score the five tier-1 audio criteria for one submission.

    Returns a dict with `criteria` (list of Criterion dicts) and everything the
    verdicts were derived from, so a firing can be adjudicated against evidence
    rather than re-run.
    """
    expected = GAME_EVENTS.get(game, ())
    crit: list[Criterion] = []
    ids = dict(CRITERIA)

    def add(cid: str, ok: bool, ev: str) -> None:
        crit.append(Criterion(cid, ids[cid], ok, ev))

    def fail_all(reason: str) -> dict[str, Any]:
        for cid, _q in CRITERIA:
            add(cid, False, reason)
        return _wrap(crit, {"error": reason, "game": game, "expected_events": list(expected)})

    if not ffmpeg_available():
        return fail_all("ffmpeg is not installed on the grading machine; no audio "
                        "criterion can be evaluated (fail-closed, not skipped)")

    manifest, note, code = read_manifest(repo, env)
    info: dict[str, Any] = {"game": game, "expected_events": list(expected),
                            "manifest_exit": code, "manifest": manifest}
    if manifest is None:
        return fail_all(note)

    music = manifest.get("music") if isinstance(manifest.get("music"), dict) else None
    sfx = manifest.get("sfx") if isinstance(manifest.get("sfx"), dict) else None

    shape_problems: list[str] = []
    if music is None:
        shape_problems.append("no `music` object")
    if sfx is None:
        shape_problems.append("no `sfx` object")
    missing_events = [e for e in expected if not isinstance((sfx or {}).get(e), dict)
                      or not (sfx or {}).get(e, {}).get("file")]
    if missing_events:
        shape_problems.append(f"sfx missing an entry with a file for: "
                              f"{', '.join(missing_events)}")
    info["missing_events"] = missing_events
    info["extra_events"] = sorted(set(sfx or {}) - set(expected))
    add("audio.manifest", not shape_problems,
        ("valid JSON; music + sfx entries for all "
         f"{len(expected)} declared events ({', '.join(expected)})"
         if not shape_problems else "; ".join(shape_problems)))

    # ---- decode everything the manifest points at -------------------------- #
    refs: list[tuple[str, Path | None, Any]] = []
    if music is not None:
        refs.append(("music", _resolve(repo, music.get("file")), music.get("file")))
    for name in sorted(sfx or {}):
        entry = (sfx or {})[name]
        raw = entry.get("file") if isinstance(entry, dict) else None
        refs.append((f"sfx.{name}", _resolve(repo, raw), raw))

    clips: dict[str, Clip] = {}
    decode_errors: list[str] = []
    cache: dict[Path, Clip] = {}
    for label, path, raw in refs:
        if path is None:
            decode_errors.append(f"{label}: no file path in the manifest (got {raw!r})")
            continue
        try:
            if path not in cache:
                cache[path] = decode(path)
            clips[label] = cache[path]
        except (AudioError, subprocess.TimeoutExpired) as ex:
            decode_errors.append(f"{label}: {ex}")

    info["clips"] = {k: v.to_dict() for k, v in clips.items()}
    info["decode_errors"] = decode_errors
    add("audio.files_exist", bool(refs) and not decode_errors,
        (f"{len(clips)} of {len(refs)} referenced files exist and decode"
         if not decode_errors
         else "; ".join(decode_errors)[:400]))

    # ---- audible? ---------------------------------------------------------- #
    quiet = [f"{k} rms={v.rms:.5f} peak={v.peak:.4f}" for k, v in sorted(clips.items())
             if v.rms < SILENCE_RMS or v.peak < SILENCE_PEAK]
    add("audio.not_silent", bool(clips) and not quiet and not decode_errors,
        (f"all {len(clips)} clips above the silence floor "
         f"(rms>{SILENCE_RMS}, peak>{SILENCE_PEAK}); "
         f"quietest rms {min((c.rms for c in clips.values()), default=0):.4f}"
         if clips and not quiet
         else f"silent or near-silent: {'; '.join(quiet) or 'no clips decoded'}"))

    # ---- distinct sounds, by CONTENT --------------------------------------- #
    sfx_clips = [c for k, c in sorted(clips.items()) if k.startswith("sfx.")]
    groups = distinct_groups(sfx_clips)
    n_events = len(expected) or len(sfx_clips)
    # Sharing one sound between two events is explicitly allowed by the task, so the
    # floor is half the declared events rather than all of them. What must fail is
    # one clip reused everywhere.
    floor = max(2, math.ceil(n_events / 2)) if n_events else 0
    info["distinct_sound_groups"] = [[Path(c.path).name for c in g] for g in groups]
    add("audio.distinct", bool(sfx_clips) and len(groups) >= floor,
        (f"{len(groups)} distinct sounds across {len(sfx_clips)} sfx entries "
         f"(floor {floor}); groups by decoded content: "
         f"{info['distinct_sound_groups']}")[:400])

    # ---- music --------------------------------------------------------------#
    m = clips.get("music")
    loops = bool((music or {}).get("loops"))
    ok_music = m is not None and loops and m.seconds >= MUSIC_MIN_SECONDS
    add("audio.music_loops", ok_music,
        (f"music {Path(m.path).name} {m.seconds:.2f}s, loops={loops} "
         f"(floor {MUSIC_MIN_SECONDS}s)" if m is not None
         else f"no decodable music clip; loops={loops}"))

    return _wrap(crit, info)


def _wrap(crit: list[Criterion], info: dict[str, Any]) -> dict[str, Any]:
    npass = sum(1 for c in crit if c.passed)
    return {"passed": npass, "total": len(crit),
            "criteria": [c.to_dict() for c in crit], **info}


# --------------------------------------------------------------------------- #
# Tier 2: audio.triggered
# --------------------------------------------------------------------------- #

TRIGGERED = ("audio.triggered",
             "During a driven run, does every event the game actually emits have a "
             "playable, audible cue in its manifest?")


def triggered_criterion(repo: Path, game: str, fired: list[str],
                        env: dict[str, str] | None = None) -> Criterion:
    """An EXPERIMENT, not an observation: the play-bot has already driven the game and
    made events fire, and this asks whether each one that fired has a cue.

    What it cannot do is hear the speaker. Nothing in the probe contract exposes audio
    playback, so this criterion proves the cue exists, decodes and is audible for every
    event the run actually produced - which is strictly more than `audio.manifest`,
    because it uses the events the game emitted rather than the ones it declared.
    That limit is stated here rather than implied, so nobody reads it as proof that a
    sound was heard.
    """
    cid, question = TRIGGERED
    fired_set = sorted({e for e in fired if isinstance(e, str)})
    if not fired_set:
        return Criterion(cid, question, False,
                         "the driven run emitted no events at all, so no cue could be "
                         "checked (fail-closed)")
    manifest, note, _code = read_manifest(repo, env)
    if manifest is None:
        return Criterion(cid, question, False, note)
    sfx = manifest.get("sfx") if isinstance(manifest.get("sfx"), dict) else {}

    problems: list[str] = []
    for name in fired_set:
        entry = sfx.get(name) if isinstance(sfx, dict) else None
        if not isinstance(entry, dict) or not entry.get("file"):
            problems.append(f"{name}: fired but has no sfx entry")
            continue
        path = _resolve(repo, entry.get("file"))
        try:
            clip = decode(path) if path else None
        except (AudioError, subprocess.TimeoutExpired) as ex:
            problems.append(f"{name}: {ex}")
            continue
        if clip is None:
            problems.append(f"{name}: unusable file path {entry.get('file')!r}")
        elif clip.rms < SILENCE_RMS or clip.peak < SILENCE_PEAK:
            problems.append(f"{name}: cue is silent (rms {clip.rms:.5f})")
    return Criterion(cid, question, not problems,
                     (f"{len(fired_set)} distinct events fired "
                      f"({', '.join(fired_set)}); every one has an audible cue"
                      if not problems else "; ".join(problems))[:400])


if __name__ == "__main__":
    import sys
    print(json.dumps(collect(Path(sys.argv[1]).resolve(), sys.argv[2]), indent=2))
