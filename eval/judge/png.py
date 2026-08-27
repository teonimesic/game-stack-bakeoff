#!/usr/bin/env python3
"""A minimal, dependency-free PNG reader.

The judging host has neither Pillow nor numpy, and adding either would make the
evaluator harder to reproduce than the thing it evaluates. Frame analysis here needs
exactly one thing - per-pixel RGB - so this decodes 8-bit non-interlaced PNGs (the only
kind any of the four render harnesses emits) and nothing else.
"""

from __future__ import annotations

import contextlib
import os
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class PngError(RuntimeError):
    pass


@dataclass
class Image:
    width: int
    height: int
    channels: int
    data: bytes  # width * height * channels, 8 bit

    def rgb(self, x: int, y: int) -> tuple[int, int, int]:
        i = (y * self.width + x) * self.channels
        d = self.data
        if self.channels >= 3:
            return d[i], d[i + 1], d[i + 2]
        return d[i], d[i], d[i]

    def ink_coverage(self, background: tuple[int, int, int],
                     tolerance: int = 8) -> float:
        """Fraction of pixels that differ from the background colour.

        The same measure the four render harnesses use in their own tests, so a frame
        that passes `renders a non-empty frame` in-repo also reads as non-empty here.
        """
        n = self.width * self.height
        if n == 0:
            return 0.0
        br, bg, bb = background
        c, d, hit = self.channels, self.data, 0
        for i in range(0, n * c, c):
            if (abs(d[i] - br) > tolerance or abs(d[i + 1 if c > 1 else i] - bg) > tolerance
                    or abs(d[i + 2 if c > 2 else i] - bb) > tolerance):
                hit += 1
        return hit / n

    def is_flat(self, tolerance: int = 8) -> bool:
        """Is every pixel of THIS frame within `tolerance` of THIS frame's own mode?

        i.e. the frame holds one colour and nothing else. Asked per frame and against
        the frame's own background, which is the whole point: `analyse_frames` measures
        `ink_coverage` against FRAME 0's background, so a blank frame in any other
        colour reads 1.0 there rather than 0.0. That is why no ceiling on `mean_ink`
        can be the guard against a blank render - 12 uniform frames measure 0.0, 0.5 or
        0.91667 depending only on how their colours are arranged, and the retired
        0.001-0.85 window admitted 2 of those 3 (`tasks/168`).
        """
        return self.ink_coverage(self.dominant_background(), tolerance) == 0.0

    def dominant_background(self) -> tuple[int, int, int]:
        """The most common pixel colour, quantised - a decent guess at the clear
        colour when we do not know the game's palette."""
        counts: dict[tuple[int, int, int], int] = {}
        c, d = self.channels, self.data
        step = max(1, (self.width * self.height) // 4000) * c
        for i in range(0, self.width * self.height * c, step):
            key = (d[i] >> 3 << 3,
                   d[i + 1 if c > 1 else i] >> 3 << 3,
                   d[i + 2 if c > 2 else i] >> 3 << 3)
            counts[key] = counts.get(key, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0] if counts else (0, 0, 0)

    def differs_from(self, other: "Image", tolerance: int = 8) -> float:
        if (self.width, self.height) != (other.width, other.height):
            return 1.0
        n = self.width * self.height
        a, b = self.data, other.data
        ca, cb = self.channels, other.channels
        diff = 0
        for p in range(n):
            ia, ib = p * ca, p * cb
            if any(abs(a[ia + k] - b[ib + k]) > tolerance
                   for k in range(min(3, ca, cb))):
                diff += 1
        return diff / n if n else 0.0


def write_rgb(path: str | Path, width: int, height: int, pixels: bytes) -> None:
    """Write an 8-bit RGB PNG. `pixels` is width*height*3 bytes, row-major, top-down.

    Used by every reference fixture, which need to produce frames without pulling in an
    image library. **Atomic** - a temporary sibling, then `os.replace` - so a kill
    part-way through leaves no half-written frame at the final path for a reader to open
    and misread (`eval/AGENTS.md`, one writer per artifact path). This is the single
    write for all 6 fixtures; each carries a fallback copy for use outside the judge
    tree, and those are atomic too.
    """
    if len(pixels) != width * height * 3:
        raise PngError(f"expected {width * height * 3} bytes, got {len(pixels)}")
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += pixels[y * width * 3:(y + 1) * width * 3]

    def chunk(tag: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        tmp.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))
        os.replace(tmp, dest)
    except BaseException:
        # The original error is what the caller needs; the half-written sibling is
        # litter in a directory something will glob. Take it away and re-raise - and
        # SUPPRESS the removal's own failure, because a cleanup that raises replaces the
        # error it was tidying up after with one about the tidying.
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def read(path: str | Path) -> Image:
    raw = Path(path).read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError(f"{path}: not a PNG")
    pos, idat, hdr, palette = 8, bytearray(), None, b""
    while pos + 8 <= len(raw):
        (length,) = struct.unpack(">I", raw[pos:pos + 4])
        ctype = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"PLTE":
            palette = body
        elif ctype == b"IEND":
            break
    if hdr is None:
        raise PngError(f"{path}: no IHDR")
    width, height, depth, colour, comp, filt, interlace = hdr
    if depth != 8:
        raise PngError(f"{path}: only 8-bit PNGs are supported (got {depth})")
    if interlace:
        raise PngError(f"{path}: interlaced PNGs are not supported")
    if colour not in _CHANNELS:
        raise PngError(f"{path}: unsupported colour type {colour}")
    ch = _CHANNELS[colour]
    stride = width * ch

    buf = zlib.decompress(bytes(idat))
    out = bytearray(stride * height)
    prev = bytearray(stride)
    p = 0
    for y in range(height):
        ftype = buf[p]
        p += 1
        line = bytearray(buf[p:p + stride])
        p += stride
        if ftype == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ftype != 0:
            raise PngError(f"{path}: bad filter type {ftype} on row {y}")
        out[y * stride:(y + 1) * stride] = line
        prev = line

    if colour == 3:  # indexed
        rgb = bytearray(width * height * 3)
        for i, idx in enumerate(out):
            rgb[i * 3:i * 3 + 3] = palette[idx * 3:idx * 3 + 3]
        return Image(width, height, 3, bytes(rgb))
    return Image(width, height, ch, bytes(out))
