# 06 — Graphics

**Status: verified.** Every image on the disc is a stock Sony TIM or CLT, and
each one is self-describing: parsing them needs no external metadata, only the
codec. 443 distinct VRAM rectangles were recovered by decoding the whole disc.
Output in [`reports/vram-map.txt`](../reports/vram-map.txt),
[`reports/vram-rects.csv`](../reports/vram-rects.csv) and
[`reports/pic.txt`](../reports/pic.txt).

## There is no texture format

The game has no image format of its own. A packed block decodes into a TIM,
and the TIM is handed to the GPU. That is the whole pipeline.

```
u32  id       0x10 = TIM, 0x11 = CLT (a palette on its own)
u32  flags    bits 0-2 pixel mode (0 = 4bpp, 1 = 8bpp, 2 = 16bpp),
              bit 3 = a CLUT block follows
block:
    u32  bytes in this block, header included
    u16  VRAM x, u16 VRAM y
    u16  width in 16-bit units, u16 height
    ...  pixels
```

Because a TIM carries its own destination coordinates, **the disc contains its
own VRAM allocation map**. Nothing at run time decides where a texture goes;
the packing was decided when the asset was built, and it is baked into every
copy of it.

That has a measurable consequence. Decode every block on the disc, read the
coordinates out of every TIM, and you get the game's complete video-memory
budget — 443 distinct rectangles across 47,481 images.

## The VRAM map

One character per 64×16 cell of the PlayStation's 1024×512 16-bit frame
buffer, shaded by total words written. Blank means no image on the disc ever
writes there. This is a union over the whole game, not a snapshot: only one
map, one battle or one menu is resident at a time.

```
    0   256 512 768
  0     *@@@@@@@@@@@
 16     *@@@@@@@@@@@
 32     *@@#@@@@@@@@
 48     *@@#@@@@@@@@
 64     *@@@@@**@@@@
 ...
240     *@@@@@*%@@@@
256     @@@@@@@@@@
 ...
464     @@@@@@@@@@
480 @@@@@@@@@@@@@@
496 @@@@@@@@@@@@@@ @
```

Three regions stand out.

**`(0,0)`–`(255,255)` is never a texture destination.** Not one of the 47,481
images on the disc writes a word into it. The block immediately to its right,
`(256,0)`–`(319,255)`, is written by exactly *one* image in the entire corpus.
At boot the game calls `SetDefDrawEnv` and `SetDefDispEnv` with `(0, 0, 320,
240)` — so the first frame buffer sits precisely in the band the artists left
alone.

**`(640,256)`–`(1023,479)` is empty too.** 384×224 of unused video memory in
the lower right, adjacent to the busiest texture pages. That is where a second
320×240 buffer would fit, and it is one of the open questions
([99](99-open-questions.md)) whether it is the back buffer or simply slack.

**The bottom two rows are palettes.** `y = 480` and `y = 496` are almost
entirely CLUTs: 256-colour tables at `(0,480)`, `(0,496)`, `(256,480)`,
`(256,496)`, and dozens of 16-colour tables squeezed between them. The single
busiest rectangle on the disc is a 16-colour CLUT at `(320,255)` — written by
7,187 different images, the last scanline before the texture region proper.

## The busiest rectangles

| Rectangle | Words | Images | What |
|---|---|---|---|
| `(320,255)` | 16×1 | 7,187 | 16-colour CLUT, the shared one |
| `(320,0)` | 64×32 | 4,692 | a 256×32 4bpp page |
| `(704,232)` | 16×1 | 1,903 | 16-colour CLUT |
| `(496,191)` | 16×1 | 1,493 | 16-colour CLUT |
| `(768,0)` | 128×256 | 1,286 | a 256×256 8bpp page |
| `(0,480)` | 256×1 | 1,302 | 256-colour CLUT |
| `(768,256)` | 128×256 | 1,202 | a 256×256 8bpp page |

The two 256×256 8bpp pages at `(768,0)` and `(768,256)` are the character
texture slots — over a thousand different images take turns in each.

## The `PIC` directory

Seven files, loaded by name through the `\PIC\%s.D;1` template and the file
registry ([05](05-containers-and-index.md)).

| File | id | Structure | Contents |
|---|---|---|---|
| `MC.D` | 1000 | one block → container of 15 | the main font and menu graphics |
| `I.D` | 1001 | container of 458 | item icons, 32×32 4bpp, 336 distinct |
| `FACE.D` | 1002 | container of 10 | portraits, 120×208 8bpp |
| `FACE2.D` | 1003 | container of 10 | portraits, 120×208 8bpp |
| `RC.D` | 1005 | one block | 256×256 4bpp, CLUT 16×10 — "Ranks charactor" |
| `WM.D` | 1006 | container of 6 | world map, 5 distinct images |
| `BF.D` | 1007 | one block | 256×256 4bpp — the battle font |

The error strings in the executable name three of them directly:
`Item Graphic read error.`, `Face file read error.`,
`Ranks charactor file read error.`, `Battle font Graphic read error.`,
`World map Graphic read error.`.

### `MC.D`, the font and menu pack

106,604 bytes on disc, one method-3 block, 256,576 bytes out, which is itself
a container of fifteen TIMs:

```
 [ 0]  256x256 4bpp  VRAM (320,  0)   CLUT 16x4 at (960,496)
 [ 1]  256x128 4bpp  VRAM (384,  0)   CLUT 16x4 at (960,500)
 [ 2]  256x128 4bpp  VRAM (384,128)   CLUT 16x4 at (992,500)
 [ 3]  256x128 4bpp  VRAM (448,  0)   CLUT 16x4 at (976,496)
 [ 4]  256x128 4bpp  VRAM (448,128)   CLUT 16x4 at (1008,496)
 [ 5]  256x128 4bpp  VRAM (640,  0)   CLUT 16x4 at (976,500)
 [ 6]  256x128 4bpp  VRAM (640,128)   CLUT 16x4 at (1008,500)
 [ 7]  256x128 4bpp  VRAM (704,  0)   CLUT 16x4 at (992,496)
 [ 8]  256x 96 4bpp  VRAM (704,128)   CLUT 16x4 at (976,504)
 [ 9]  256x 96 4bpp  VRAM (960,400)   CLUT 16x4 at (960,504)
 [10]  256x256 4bpp  VRAM (896,256)   CLUT 16x16 at (944,496)
 [11]  128x 16 4bpp  VRAM (960,128)   CLUT 16x1 at (1008,138)
 [12]  256x112 4bpp  VRAM (960,144)   CLUT 16x8 at (1008,128)
 [13]  128x128 8bpp  VRAM (960,  0)   CLUT 256x1 at (256,511)
 [14]  128x128 8bpp  VRAM (896,  0)   CLUT 256x1 at (256,509)
```

Members 0–9 are 344,064 pixels of 4bpp glyph sheet — the game's Japanese
font. Member 10 lands at `(896,256)` with a 16×16 CLUT, which is exactly where
`BF.D` puts its own 256×256 image with the same CLUT geometry: the battle font
**replaces** the menu one in the same VRAM slot rather than living beside it.
Members 13 and 14 use the 256-colour palettes at `(256,509)` and `(256,511)`,
the same slots `FACE.D` uses.

### `I.D`, and sharing by pointer

458 slots, 336 distinct 32×32 4bpp icons, all destined for `(976,200)` with a
16-colour CLUT at `(1008,246)`. Where two items share an icon the offset table
simply repeats an earlier offset, so the table is not monotonic — the only
place on the disc where that happens. See [05](05-containers-and-index.md).

## Graphics inside a map

A map extent's first three members are graphics
([05](05-containers-and-index.md)). For map `1000`:

* member 0 → 16 TIMs, 192×32 4bpp and smaller, every one of them sharing a
  64-entry CLUT at `(320,468)` — the map's tile strips;
* member 1 → three 8bpp images whose 256-colour CLUTs go to `(0,480)`,
  `(0,496)` and `(256,480)`, plus two standalone CLTs at `(0,488)` and
  `(0,504)` — the character sheets and their palettes;
* member 2 → three more 4bpp TIMs at `(512,256)`, `(576,256)` and `(576,400)`,
  the first two with 13-row CLUTs at `(256,496)` and `(272,496)` — the
  background tile pages.

`E.DAT`'s 38 extents are the same idea at larger scale: each is a container of
two to twenty-one TIMs and CLTs, 8bpp 256-colour still images — the event
cut-scene backdrops.

## Reading it yourself

```sh
python tools/tod_codec.py iso/PIC/MC.D -o mc.bin
python tools/tim.py       mc.bin                       # will not parse: it is a container
python tools/tod_arc.py   mc.bin --extract mc/
python tools/tim.py       mc/0000.bin
python tools/vram_map.py  iso/SLPS_011.00 iso/DAT iso/PIC --csv rects.csv
```
