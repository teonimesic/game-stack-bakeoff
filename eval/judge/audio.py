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
   any filename or even any file-hash comparison once the copies are re-encoded. It
   counts and floors over the SAME set - the events the task declares - because a
   criterion whose numerator and denominator come from different sets can be bought:
   2 undeclared junk entries used to convert that exact failure into a pass (tasks/152).

3. **Fail-closed.** A manifest that will not run, will not parse, or names a file that
   will not decode scores FALSE with the reason recorded. It is never "skipped":
   `total=0 passed=0` is indistinguishable from correct failure. A game whose declared
   event list is empty is refused here for the same reason.

4. **Every criterion here has a mutant in `audio_selftest.py`** that makes it go red. A
   criterion that cannot fail is worse than absent, because it looks like success. The
   ones that only a VARIANT can reach have one too (`AGENTS.md` rule 15).

5. **The declared event list is READ FROM THE PROMPTS, never transcribed.** A second
   copy of one fact drifts, and this one did, on 2 of the 4 games (tasks/151).

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
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from probe import Criterion

# --------------------------------------------------------------------------- #
# What each game declares. These are the event names in the task prompt, which is
# a functional contract with the probe, not a rubric item - the prompt states them
# verbatim and tells the agent to spell them exactly.
#
# READ FROM THE PROMPTS, NEVER TRANSCRIBED. `eval/suites/wholegame_prompts.py` is where
# a task exists, so it is the address (rule 12), and the same lazy-import shape is
# already how `aspects.py` learns which task ids the suites define. A hand-written copy
# lived here until 2026-08-25 and had drifted on 2 of the 4 games: it knew 6 of the
# arena's 9 events and none of the platformer's 8, and 30 of 59 stored audio gradings
# recorded a real declared cue as an `extra_event` because of it (tasks/151).
#
# An import failure here is fatal on purpose. Every audio criterion is graded against
# this contract, and a grader that cannot state what the task asked for must not go on
# to report that the submission satisfied it.
# --------------------------------------------------------------------------- #


def _declared_events() -> dict[str, tuple[str, ...]]:
    suites = Path(__file__).resolve().parent.parent / "suites"
    sys.path.insert(0, str(suites))
    import wholegame_prompts
    return {task: tuple(names) for task, names in wholegame_prompts.EVENTS.items()}


GAME_EVENTS: dict[str, tuple[str, ...]] = _declared_events()

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
    # check=False: the exit status is read on the next line and turned into an
    # AudioError carrying ffmpeg's own stderr, which is a better message than
    # CalledProcessError would give.
    p = subprocess.run(argv, capture_output=True, timeout=120, check=False)
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
    # check=False: None IS the documented answer for an unreadable container, and the
    # caller falls back to the analysed length. That fallback can only UNDER-report
    # (it is capped at ANALYSIS_SECONDS), so a failed ffprobe cannot turn a short clip
    # into a long one -- it fails closed.
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=60, check=False)
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


class ManifestRead(NamedTuple):
    """What one `read_manifest` returned, and HOW it failed when it did.

    `lock` is the FINDINGS #25 bit: every attempt was refused with a project-lock
    signature, so the failure is a fact about the engine and this harness rather than
    about the submission. The retry loop below always knew this - the lock signature
    was the whole reason it retried - but the tuple it returned did not carry it, so
    a caller that consumed a failed read could not tell a lock-eaten read from a
    broken manifest and scored both as failures (tasks/214). A consumer that must
    exclude rather than score reads this bit; `unusable_criteria` is the same policy
    for the probe session.
    """

    manifest: dict[str, Any] | None
    note: str
    code: int
    lock: bool = False


def read_manifest(repo: Path, env: dict[str, str] | None = None,
                  timeout_s: int = 900, attempts: int = 3) -> ManifestRead:
    """Run `just audio-manifest` and parse its stdout.

    Retries while the failure looks like an engine project lock rather than a problem
    with the manifest. `.lock` on the return says the retries exhausted on lock
    signatures: the manifest was never read, and that is not the submission's fault
    (see `ManifestRead`).
    """
    note, code = "", 1
    for attempt in range(1, attempts + 1):
        data, note, code = _read_manifest_once(repo, env, timeout_s)
        if data is not None:
            return ManifestRead(data, "", code)
        if not any(h in note.lower() for h in LOCK_HINTS):
            return ManifestRead(None, note, code)
        if attempt < attempts:
            # Between attempts only: sleeping after the last read would be 12s of
            # dead wall clock on every exhausted lock read (raised by CodeRabbit).
            time.sleep(min(20.0, 4.0 * attempt))
    return ManifestRead(None, f"after {attempts} attempts: {note}", code, lock=True)


def _read_manifest_once(repo: Path, env: dict[str, str] | None, timeout_s: int
                        ) -> tuple[dict[str, Any] | None, str, int]:
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        # check=False: the exit status is returned to the caller below, which needs the
        # code itself (124/127 vs the recipe's own) to tell a missing tool from a failing
        # recipe. CalledProcessError would collapse that distinction.
        p = subprocess.run(["just", "audio-manifest"], cwd=repo, capture_output=True,
                           text=True, timeout=timeout_s, env=e, check=False)
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
# The two rules that read the declared event list
# --------------------------------------------------------------------------- #
#
# Both are pure functions of (manifest, declared events) so that `audio_regrade_census.py`
# can apply the shipped rule to a stored grading instead of restating it. A census that
# re-implements the rule it is measuring is measuring its own copy.


def manifest_problems(manifest: dict[str, Any] | None, expected: tuple[str, ...]
                      ) -> tuple[list[str], list[str], list[str]]:
    """`audio.manifest`'s verdict, as (problems, missing_events, extra_events).

    Empty `problems` is a pass. `extra_events` is reported and never a problem: the task
    asks for an entry per declared event and forbids no others, so an extra cue is a
    design choice a submission is entitled to make (`tasks/152`).
    """
    m = manifest or {}
    music = m.get("music") if isinstance(m.get("music"), dict) else None
    sfx = m.get("sfx") if isinstance(m.get("sfx"), dict) else None
    problems: list[str] = []
    if music is None:
        problems.append("no `music` object")
    if sfx is None:
        problems.append("no `sfx` object")
    missing = [e for e in expected
               if not isinstance((sfx or {}).get(e), dict)
               or not (sfx or {}).get(e, {}).get("file")]
    if missing:
        problems.append(f"sfx missing an entry with a file for: {', '.join(missing)}")
    return problems, missing, sorted(set(sfx or {}) - set(expected))


def distinct_floor(expected: tuple[str, ...]) -> int:
    """How many distinct sounds the declared events must resolve to.

    Half of them, rounded up, never below 2: the task explicitly permits two events to
    share a sound, so the floor is not "all of them". What must fail is one clip
    everywhere.
    """
    return max(2, math.ceil(len(expected) / 2))


def distinct_ok(n_declared_clips: int, n_groups: int,
                expected: tuple[str, ...]) -> bool:
    """`audio.distinct`'s verdict. Both arguments count DECLARED events only."""
    return n_declared_clips > 0 and n_groups >= distinct_floor(expected)


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
    if not expected:
        # The contract is the declared event list. Without one there is nothing for
        # `audio.manifest` to find missing and nothing for `audio.distinct` to floor on,
        # so every criterion would report success having measured nothing - which is
        # what `g4_platformer` did for 24 stored gradings (tasks/151).
        return fail_all(
            f"{game!r} declares no events in eval/suites/wholegame_prompts.py, so there "
            f"is no audio contract to grade it against (fail-closed, not skipped). "
            f"Games with a declared event set: {sorted(GAME_EVENTS)}")

    read = read_manifest(repo, env)
    manifest, note, code = read.manifest, read.note, read.code
    # `read.lock` is deliberately NOT acted on here. Tier 1 gates: a lock-eaten
    # manifest would have to exclude all five criteria, which changes what the tier
    # is allowed to refuse - a rubric decision, not a repair this file makes on its
    # own (tasks/214 records it as the open half). `triggered_criterion`, which does
    # not gate, implements the exclusion.
    info: dict[str, Any] = {"game": game, "expected_events": list(expected),
                            "manifest_exit": code, "manifest": manifest}
    if manifest is None:
        return fail_all(note)

    music = manifest.get("music") if isinstance(manifest.get("music"), dict) else None
    sfx = manifest.get("sfx") if isinstance(manifest.get("sfx"), dict) else None

    shape_problems, missing_events, extra_events = manifest_problems(manifest, expected)
    info["missing_events"] = missing_events
    info["extra_events"] = extra_events
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
    #
    # NUMERATOR AND DENOMINATOR RANGE OVER THE SAME SET: the events the task declares.
    # Both halves used to be drawn from different sets - groups counted over every `sfx`
    # entry, floor computed from the declared events - and an undeclared entry fails no
    # criterion, so 2 unique junk entries bought a Pong submission a pass on the exact
    # failure this criterion exists to catch (tasks/152).
    #
    # The alternative repair was to fail `audio.manifest` on an undeclared entry. It was
    # not taken: the prompt asks for "an entry for every event name listed above" and
    # forbids no others, so a submission with a legitimate extra cue - a menu blip, a
    # footstep - would fail a contract it kept. That is fail-CLOSED and costs a trial;
    # this repair costs nothing and closes the loophole, because an extra entry now
    # neither helps nor hurts here. Extras are still decoded and still answer
    # `audio.files_exist` and `audio.not_silent`, whose numerator and denominator are
    # both the manifest: there an extra can only ever hurt, never buy a pass.
    #
    # Sharing one sound between two events is explicitly allowed by the task, so the
    # floor is half the declared events rather than all of them. What must fail is one
    # clip reused everywhere.
    graded = {f"sfx.{e}" for e in expected}
    sfx_clips = [c for k, c in sorted(clips.items()) if k in graded]
    ungraded = sorted(k[4:] for k in clips if k.startswith("sfx.") and k not in graded)
    groups = distinct_groups(sfx_clips)
    floor = distinct_floor(expected)
    info["distinct_sound_groups"] = [[Path(c.path).name for c in g] for g in groups]
    info["ungraded_sfx_entries"] = ungraded
    add("audio.distinct", distinct_ok(len(sfx_clips), len(groups), expected),
        (f"{len(groups)} distinct sounds across {len(sfx_clips)} of the "
         f"{len(expected)} declared events' sfx entries (floor {floor}); "
         f"{len(ungraded)} undeclared entries not counted either way; "
         f"groups by decoded content: {info['distinct_sound_groups']}")[:400])

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
                        env: dict[str, str] | None = None,
                        *, lock_note: str | None = None) -> Criterion:
    """An EXPERIMENT, not an observation: the play-bot has already driven the game and
    made events fire, and this asks whether each one that fired has a cue.

    What it cannot do is hear the speaker. Nothing in the probe contract exposes audio
    playback, so this criterion proves the cue exists, decodes and is audible for every
    event the run actually produced - which is strictly more than `audio.manifest`,
    because it uses the events the game emitted rather than the ones it declared.
    That limit is stated here rather than implied, so nobody reads it as proof that a
    sound was heard.

    `lock_note` is the one fact the `fired` list cannot carry: whether the driven run
    ever happened. A lock-conflicted session emits no events, so the empty-fired branch
    below would score this criterion failed -- "no events at all" -- on exactly the arm
    the FINDINGS #25 exclusion exists for. `probe.drive` passes the ProbeError's own
    words when the session ended in a lock conflict, and the criterion comes back
    `scored=False`: measured, reported, excluded from the score, like every bot
    criterion in the same result. The empty-fired branch keeps its fail-closed default;
    only the caller knows the difference, which is why the fact travels as an argument
    rather than being re-derived here.
    """
    cid, question = TRIGGERED
    if lock_note:
        return Criterion(
            cid, question, False,
            f"NOT MEASURED during the driven run: every attempt to open a probe "
            f"session was refused with a project-lock signature, which is a fact "
            f"about the engine and this harness rather than about the submission "
            f"(FINDINGS #25). Excluded from the score rather than counted as a "
            f"failure. {lock_note}",
            scored=False)
    fired_set = sorted({e for e in fired if isinstance(e, str)})
    if not fired_set:
        return Criterion(cid, question, False,
                         "the driven run emitted no events at all, so no cue could be "
                         "checked (fail-closed)")
    read = read_manifest(repo, env)
    if read.lock:
        return Criterion(
            cid, question, False,
            f"NOT MEASURED during the driven run: every attempt to read the audio "
            f"manifest was refused with a project-lock signature, which is a fact "
            f"about the engine and this harness rather than about the submission "
            f"(FINDINGS #25). Excluded from the score rather than counted as a "
            f"failure. {read.note}",
            scored=False)
    if read.manifest is None:
        return Criterion(cid, question, False, read.note)
    manifest = read.manifest
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
    print(json.dumps(collect(Path(sys.argv[1]).resolve(), sys.argv[2]), indent=2))
