# C1-Slim E-Paper Frame Format

The display controller takes a full-frame bitmap on every refresh. This document
specifies the exact byte layout so that tools and tests can produce or verify frames
without reverse-engineering the driver.

The authoritative implementation lives in [`src/display/frame.h`](src/display/frame.h)
and [`src/display/frame.c`](src/display/frame.c) — this document only describes the
format those files already implement.

## Geometry

| Property | Value |
|---|---|
| Width | 296 pixels |
| Height | 152 pixels |
| Bits per pixel | 1 (1 = black, 0 = white) |
| Strip height | 8 pixels |
| Strip count | `152 / 8` = 19 |
| **Frame size** | `296 × 19` = **5624 bytes** |

These match the macros in `frame.h`:

```c
#define C1_DISPLAY_WIDTH          296U
#define C1_DISPLAY_HEIGHT         152U
#define C1_DISPLAY_STRIP_HEIGHT   8U
#define C1_DISPLAY_STRIP_COUNT    (C1_DISPLAY_HEIGHT / C1_DISPLAY_STRIP_HEIGHT)
#define C1_DISPLAY_FRAME_BYTES    (C1_DISPLAY_WIDTH * C1_DISPLAY_STRIP_COUNT)
```

## Byte layout (strip-major)

The frame is stored as 19 **strips** of 8 pixel-rows each. Within a strip, pixels are
packed one byte per column, MSB-first: the most significant bit is the strip's topmost
pixel row. Strips are stored top to bottom.

For a pixel at `(x, y)`:

```
offset(x, y) = (y / 8) * 296 + x
mask(x, y)   = 0x80 >> (y % 8)      // 0x80, 0x40, 0x20, ... 0x01
```

- `bit = 1` → **black**, `bit = 0` → **white**.
- The offset formula is `strip_index * WIDTH + x`; note the row width is **296** (not
  the height), a common source of confusion.
- `152 = 19 × 8` divides evenly, so the last strip is full and there is no padding.

This is exactly what `c1_display_frame_set_pixel()` computes:

```c
offset = (size_t)(y / C1_DISPLAY_STRIP_HEIGHT) * C1_DISPLAY_WIDTH + x;
mask   = (uint8_t)(0x80U >> (y % C1_DISPLAY_STRIP_HEIGHT));
```

`c1_display_frame_clear(frame, black)` simply memsets the whole buffer to `0xFF`
(all black) or `0x00` (all white).

## Reference frames

[`tests/frames/`](tests/frames/) holds 13 reference frames (5624 bytes each). Each one
isolates a specific class of format error, so a decoder that gets the layout subtly
wrong will disagree on at least one of them. See
[`tests/frames/README.md`](tests/frames/README.md) for the per-file catalog and a
standalone verifier.

| File | Targets |
|---|---|
| `all_white` / `all_black` | bit polarity (black = 1) |
| `row0` / `row7` / `row8` | MSB-vs-LSB bit order and the strip boundary at `y = 8` |
| `row151` | the bottom edge (`152 = 19 × 8`, no partial strip) |
| `col0` / `col295` | row width taken from the wrong constant |
| `corners` | all four corners at once |
| `checker1` / `checker8` | offset formula and row/column transposition |
| `bits` | all 8 bit positions across a byte (`f[i] = i`) |
| `random` | fixed-seed pseudo-random content (regression pressure) |

## Verifying a frame

To decode any 5624-byte frame, invert the layout above:

```python
W, STRIP = 296, 8
def pixel(frame, x, y):
    return (frame[(y // STRIP) * W + x] >> (7 - (y % STRIP))) & 1   # 1 = black
```

Run the bundled checker to re-derive every reference frame from this layout and
compare it byte-for-byte:

```sh
python3 tests/frames/verify.py
```

The reference frames were cross-checked to decode identically under two independent
implementations (a Go decoder and the MIT-licensed `frame2png.py`), which is what
makes them usable as a cross-implementation conformance set.
