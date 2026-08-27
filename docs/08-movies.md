# 08 — The movies

**Status: verified.** All 4,315 frames on the disc were walked, and none is
incomplete. Output in [`reports/movies.txt`](../reports/movies.txt).

Six `.STR` files in `MOVIE/`, 87 MB, all stock Sony MDEC streams. Each video
sector carries a 32-byte stream header in front of 2,016 bytes of bitstream:

```
+0   u16  0x0160          Sony's stream marker
+2   u16  0x8001          chunk type: MDEC video
+4   u16  chunk index within the frame
+6   u16  chunks in the frame
+8   u32  frame number
+12  u32  bytes of bitstream in the frame
+16  u16  width
+18  u16  height
+20  u16  bitstream length in 32-bit units
+22  u16  0x3800          the frame's own MDEC bitstream header,
+24  u16  quantisation    repeated verbatim in every chunk of the frame
+26  u16  bitstream version
```

## The six files

| File | LBA | Frames | Size | Video sectors | Audio sectors | BS version |
|---|---|---|---|---|---|---|
| `EVA.STR` | 82,318 | 746 | 304×160 | 6,535 | 914 | **2** |
| `EVB.STR` | 89,786 | 898 | 304×160 | 7,866 | 1,153 | **3** |
| `EVC.STR` | 99,010 | 514 | 304×160 | 4,503 | 735 | **3** |
| `LOGO.STR` | 104,890 | 155 | **320×240** | 679 | 71 | **1** |
| `NAMCO.STR` | 105,666 | 170 | **256×240** | 850 | **0** | **1** |
| `OP.STR` | 106,516 | 1,832 | 304×160 | 16,048 | 2,299 | **3** |

Frame numbering is dense and complete in all six: 1..N with no gaps and no
frame short of its declared chunk count.

## Three encoders, one directory

The bitstream version field sorts the six files into three groups, and the
sector-mode tagging from [02](02-disc.md) sorts them into the *same* three
groups:

| Group | Files | BS version | Sector submode | Audio |
|---|---|---|---|---|
| A | `NAMCO.STR` | 1 | `0x08` DATA — not real-time | none |
| B | `LOGO.STR` | 1 | `0x42` RT \| VIDEO | XA on `0x64` |
| C | `EVA` | 2 | `0x48` RT \| DATA | XA on `0x64` |
| C | `EVB`, `EVC`, `OP` | 3 | `0x48` RT \| DATA | XA on `0x64` |

Two independent fields — one written by the video encoder, one by the disc
mastering tool — agree on the split. That is a chronology: the two logo movies
were made first, with an early encoder and by hand; the first event movie came
next with version 2; the bulk of the content, including the anime opening, was
encoded last with version 3.

**`NAMCO.STR` has no audio at all.** Not a silent track — no XA sectors are
interleaved into it, and its 850 sectors are plain Form 1 `DATA` with no
real-time bit. The ISO record agrees: its XA attribute word is `0D55` where
every other `.STR` on the disc is `2555`. A player that assumes every `.STR`
is a Form 2 real-time stream will mishandle exactly this one file.

`NAMCO.STR` is also the only movie at 256×240, and `LOGO.STR` the only one at
320×240; the four event movies are all 304×160, which is 38 by 10 macroblocks
and the shape a 1997 encoder would choose to keep the MDEC inside its frame
budget.

## Frame rates and budgets

`OP.STR` at 304×160 uses 16,048 video sectors for 1,832 frames — 8.76 sectors
per frame. Delivered at 150 sectors per second, that is **17.1 frames per
second**; at double speed with the interleaved audio taking its share, the
effective rate lands near the usual 15 fps of the era.

Bitstream sizes per frame:

| File | min | max | mean |
|---|---|---|---|
| `EVA.STR` | 1,720 | 18,124 | 14,403 |
| `EVB.STR` | 676 | 18,136 | 11,903 |
| `EVC.STR` | 676 | 18,144 | 12,235 |
| `LOGO.STR` | 6,480 | 8,016 | 7,172 |
| `NAMCO.STR` | 2,172 | 10,040 | 7,138 |
| `OP.STR` | 676 | 19,532 | 13,040 |

The three version-3 files share a floor of exactly 676 bytes — the size of a
frame the encoder could not compress further, which in practice means a black
one. `EVA.STR`, on version 2, never goes below 1,720. Another small
fingerprint of the version change.

## Where the movies are played from

The file registry ([05](05-containers-and-index.md)) gives them ids
1800–1805, with literal paths:

```
1800  \MOVIE\LOGO.STR;1
1801  \MOVIE\NAMCO.STR;1
1802  \MOVIE\EVA.STR;1
1803  \MOVIE\EVB.STR;1
1804  \MOVIE\EVC.STR;1
1805  \MOVIE\OP.STR;1
```

The order in the registry is not the order on the disc: `LOGO` is id 1800 but
sits after the three event movies physically, and `NAMCO` — the very first
thing a player sees — is id 1801, in the middle of the disc. The registry
order looks like the order the files were added to the project.

A debug overlay in the executable prints `movie:` alongside `MapNo:` and
`Evt No:` — see [10](10-leftovers.md).

## Reading it yourself

```sh
python tools/str_probe.py "$TOD" --str 106516 18392    # OP.STR
python tools/str_probe.py "$TOD" --str 105666 850      # NAMCO.STR
python tools/sector_map.py "$TOD" --files
```
