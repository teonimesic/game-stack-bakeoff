"""DELIBERATELY BROKEN CONTROL FIXTURE - do not treat this as a real game.

Emits twelve valid 640x400 PNGs. Every one of them is the same flat background
colour with nothing drawn on it, and none of them differ from any other. The
SEED, TICKS and SCRIPT arguments are accepted and ignored.

    python3 film.py SEED TICKS SCRIPT OUTDIR
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

import game as g

try:  # the judge ships a PNG writer; fall back to a local copy if it is absent
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from png import write_rgb  # type: ignore
except Exception:  # pragma: no cover - only used when run outside the judge tree
    def write_rgb(path, width, height, pixels):
        raw = bytearray()
        for y in range(height):
            raw.append(0)
            raw += pixels[y * width * 3:(y + 1) * width * 3]

        def chunk(tag, body):
            return (struct.pack(">I", len(body)) + tag + body
                    + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                     + chunk(b"IEND", b""))


def blank_frame() -> bytes:
    return bytes(g.BACKGROUND) * (g.WIDTH * g.HEIGHT)


def main(argv: list) -> int:
    if len(argv) < 4:
        print("usage: film.py SEED TICKS SCRIPT OUTDIR", file=sys.stderr)
        return 2
    outdir = argv[3]
    os.makedirs(outdir, exist_ok=True)
    pixels = blank_frame()
    for index in range(g.FRAME_COUNT):
        write_rgb(os.path.join(outdir, "frame_%04d.png" % index), g.WIDTH, g.HEIGHT, pixels)
    print("film: wrote %d frames to %s" % (g.FRAME_COUNT, outdir), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
