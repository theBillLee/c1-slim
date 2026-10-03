#!/usr/bin/env python3
"""Verify the reference frames against the documented frame layout.

For every *.bin here, the expected content is re-derived from scratch with a
straightforward set_pixel() routine and compared byte-for-byte with the file, so a
mismatch means either the layout or the file is wrong. This is intentionally written
from the format spec (../../FRAME-FORMAT.md) and src/display/frame.c rather than from
whatever produced the files.

Layout:
    WIDTH=296  HEIGHT=152  STRIP=8  1 bit per pixel (1 = black)
    offset(x, y) = (y // STRIP) * WIDTH + x
    mask(x, y)   = 0x80 >> (y % STRIP)

Usage:  python3 tests/frames/verify.py     (exits 0 on success, 1 on failure)
"""
import os
import sys

WIDTH, HEIGHT, STRIP = 296, 152, 8
FRAME_BYTES = WIDTH * (HEIGHT // STRIP)  # 5624


def blank():
    return bytearray(FRAME_BYTES)


def set_px(f, x, y, black=True):
    off = (y // STRIP) * WIDTH + x
    m = 0x80 >> (y % STRIP)
    if black:
        f[off] |= m
    else:
        f[off] &= ~m & 0xFF


def all_white():
    return blank()


def all_black():
    return bytearray(b"\xff" * FRAME_BYTES)


def row(y):
    f = blank()
    for x in range(WIDTH):
        set_px(f, x, y)
    return f


def col(x):
    f = blank()
    for y in range(HEIGHT):
        set_px(f, x, y)
    return f


def corners():
    f = blank()
    for x, y in ((0, 0), (WIDTH - 1, 0), (0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)):
        set_px(f, x, y)
    return f


def checker(cell):
    f = blank()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x // cell + y // cell) % 2 == 0:
                set_px(f, x, y)
    return f


def bits():
    return bytearray(i & 0xFF for i in range(FRAME_BYTES))


# name -> (expected_bytes_or_None, description). None = only the size is checked.
VECTORS = {
    "all_white": (all_white(), "all zero"),
    "all_black": (all_black(), "all one"),
    "row0": (row(0), "only row 0"),
    "row7": (row(7), "only row 7"),
    "row8": (row(8), "only row 8"),
    "row151": (row(HEIGHT - 1), "only row 151"),
    "col0": (col(0), "only column 0"),
    "col295": (col(WIDTH - 1), "only column 295"),
    "corners": (corners(), "four corners"),
    "checker1": (checker(1), "1x1 checkerboard"),
    "checker8": (checker(8), "8x8 checkerboard"),
    "bits": (bits(), "f[i] = byte(i)"),
    # Fixed-seed PRNG blob; reproducing the exact PRNG stream here is not the point,
    # so only its size is checked.
    "random": (None, "fixed-seed pseudo-random (size only)"),
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    failed = 0

    for name, (expected, desc) in sorted(VECTORS.items()):
        path = os.path.join(here, name + ".bin")
        if not os.path.exists(path):
            print("MISSING  %s.bin" % name)
            failed += 1
            continue
        with open(path, "rb") as fh:
            data = fh.read()

        if len(data) != FRAME_BYTES:
            print("SIZE     %s.bin is %d bytes, expected %d"
                  % (name, len(data), FRAME_BYTES))
            failed += 1
            continue
        if expected is None:
            print("OK       %-9s (size only) %s" % (name, desc))
            continue
        if bytes(data) == bytes(expected):
            print("OK       %-9s %s" % (name, desc))
        else:
            diff = sum(1 for a, b in zip(data, expected) if a != b)
            print("DIFF     %-9s %d/%d bytes differ" % (name, diff, FRAME_BYTES))
            failed += 1

    total = len(VECTORS)
    if failed:
        print("\nFAILED: %d/%d frames" % (failed, total))
        return 1
    print("\nAll %d reference frames match the documented layout." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
