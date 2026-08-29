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

        Since `tasks/212` this is byte translate + integer OR, not a loop per pixel:
        each channel's bytes map through a 256-entry table to a 0/1 "outside the
        tolerance band" flag (`bytes.translate`, C speed), the three flag strings OR
        together as integers - a word-parallel per-pixel OR that cannot carry, because
        every byte is 0 or 1 - and `bit_count` counts the pixels where any channel
        left its band. Byte for byte the count the shipped loop produced: that loop is
        kept as `_reference_ink` in `judge/ink_window_control.py`, which re-derives
        every fixture and blank-arrangement reading through it, and whose `--pin-dump`
        prints the readings any change to this function must reproduce exactly.
        """
        n = self.width * self.height
        if n == 0:
            return 0.0
        c, d = self.channels, self.data
        if len(d) != n * c:
            # The shipped loop would have raised IndexError part-way or silently
            # ignored trailing bytes; raise instead, before the slices below can
            # misalign the per-channel lanes.
            raise PngError(f"image data holds {len(d)} bytes, expected {n * c}")
        br, bg, bb = background

        def outside(ref: int, chan: bytes) -> bytes:
            return chan.translate(bytes(1 if abs(v - ref) > tolerance else 0
                                        for v in range(256)))

        ch0 = d[0::c]
        hits = (int.from_bytes(outside(br, ch0), "big")
                | int.from_bytes(outside(bg, d[1::c] if c > 1 else ch0), "big")
                | int.from_bytes(outside(bb, d[2::c] if c > 2 else ch0), "big"))
        return hits.bit_count() / n

    def is_flat(self, tolerance: int = 8) -> bool:
        """Is every pixel of THIS frame within `tolerance` of THIS frame's own mode?

        i.e. the frame holds one colour and nothing else.

        THE ONE ADDRESS FOR THAT DEFINITION. Since `tasks/178` `analyse_frames` measures
        `ink_coverage` against each frame's own background too, so this is the same
        quantity asked as a boolean: `is_flat` is exactly `mean_ink`'s per-frame term
        being 0.0. `judge/ink_window_control.py` asserts the two agree rather than
        leaving a sentence here promising it, and `judge/static.py` says why the
        redundancy is kept.
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
        """Fraction of pixels differing by more than `tolerance` in any of the first
        `min(3, channels)` channels of each image - the definition as always.

        Since `tasks/212`: a byte-equality fast path (identical data cannot differ
        under any non-negative tolerance, and consecutive captured frames are
        usually identical), then one pass per channel pair - the slices walk each
        channel at C speed and the comparisons run on unpacked ints, with no
        generator frame per pixel.
        `x - y > tol or y - x > tol` is `abs(x - y) > tol`. Pinned the same way as
        `ink_coverage`: `_reference_differs` in `judge/ink_window_control.py` is the
        shipped loop, and `--pin-dump` states every reading a change here must
        reproduce exactly. A data length that does not match the geometry raises
        rather than reading past it. A negative `tolerance` is outside how the
        criterion ever calls this, but it is pinned anyway: the shipped loop marks
        every pixel different there (`0 > tolerance`), so the fast path must not
        fire - identical data reads 1.0, not 0.0 (tasks/212 review round 1).
        """
        if (self.width, self.height) != (other.width, other.height):
            return 1.0
        n = self.width * self.height
        if n == 0:
            return 0.0
        a, b = self.data, other.data
        ca, cb = self.channels, other.channels
        if len(a) != n * ca or len(b) != n * cb:
            raise PngError("image data length does not match width * height * channels")
        if tolerance >= 0 and a == b:
            return 0.0
        k = min(3, ca, cb)
        tol = tolerance
        if k == 3:
            hits = sum(1 for x, y, p, q, r, s in zip(a[0::ca], b[0::cb], a[1::ca],
                                                     b[1::cb], a[2::ca], b[2::cb])
                       if x - y > tol or y - x > tol or p - q > tol or q - p > tol
                       or r - s > tol or s - r > tol)
        else:
            hits = sum(1 for t in zip(*(a[i::ca] for i in range(k)),
                                      *(b[i::cb] for i in range(k)))
                       if any(t[i] - t[k + i] > tol or t[k + i] - t[i] > tol
                              for i in range(k)))
        return hits / n


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
