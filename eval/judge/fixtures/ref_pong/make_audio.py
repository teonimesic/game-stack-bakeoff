"""Regenerate this fixture's WAV assets and its audio manifest.

    python3 make_audio.py

The fixture ships the generated `.wav` files and `audio-manifest.json`, so nothing has
to run this to use them; it exists so the assets are reproducible and so it is obvious
what they are. Pure standard library - the reference fixtures never take a dependency.

The audio criteria decode samples rather than trusting filenames (`judge/audio.py`), so
the five effects have to be genuinely DIFFERENT sounds: different fundamentals,
different harmonic content, different envelopes. One beep copied to five names is the
exact failure `audio.distinct` exists to catch.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

RATE = 22050
HERE = Path(__file__).resolve().parent

# The five event names the g1_pong task declares, each with its own voice.
VOICES: dict[str, dict] = {
    "paddle_hit":  dict(seconds=0.18, freq=440.0, harmonics=(1.0, 2.0), decay=14.0),
    "wall_bounce": dict(seconds=0.14, freq=220.0, harmonics=(1.0,), decay=18.0),
    "score_left":  dict(seconds=0.45, freq=659.25, harmonics=(1.0, 3.0, 5.0), decay=4.0),
    "score_right": dict(seconds=0.45, freq=392.0, harmonics=(1.0, 2.0, 4.0), decay=4.0),
    "game_over":   dict(seconds=0.90, freq=110.0, harmonics=(1.0, 2.0, 3.0, 4.0),
                        decay=1.6),
}

MUSIC = dict(seconds=5.0, freq=196.0, harmonics=(1.0, 2.0, 3.0), decay=0.0, amp=0.35)


def tone(path: Path, seconds: float, freq: float, *, amp: float = 0.5,
         harmonics: tuple[float, ...] = (1.0,), decay: float = 0.0) -> Path:
    """A deterministic mono 16-bit WAV. Same generator as judge/audio_selftest.py."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for i in range(int(seconds * RATE)):
        t = i / RATE
        v = sum(math.sin(2 * math.pi * freq * h * t) / h for h in harmonics)
        env = math.exp(-decay * t) if decay else 1.0
        s = max(-1.0, min(1.0, amp * env * v))
        frames += struct.pack("<h", int(s * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return path


def main() -> int:
    sfx = {}
    for name, voice in VOICES.items():
        tone(HERE / "audio" / f"{name}.wav", **voice)
        sfx[name] = {"file": f"audio/{name}.wav"}
    tone(HERE / "audio" / "music.wav", **MUSIC)
    manifest = {"music": {"file": "audio/music.wav", "loops": True}, "sfx": sfx}
    (HERE / "audio-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(sfx)} effects, one music loop, and audio-manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
