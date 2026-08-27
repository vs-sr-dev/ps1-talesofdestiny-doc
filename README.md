# Tales of Destiny (PlayStation, Japan) — structural documentation

Reverse-engineering notes on **SLPS-01100**, the Japanese PlayStation release
of Namco / Wolf Team's *Tales of Destiny*, mastered 2 December 1997.

This repository is **documentation and analysis only**. It contains no disc
image, no extracted asset, no patch and no translation. The tools operate on
an image you supply yourself; every number quoted in the documents was
produced by running them, and their output is committed under
[`reports/`](reports/) so the claims can be checked without owning the disc.

There is **no porting, BYOA or modding intent**. The goal is a written record
of how this build is put together — and of what it inherited from the
Super Famicom game that came before it.

---

## TL;DR — what this disc actually is

| | |
|---|---|
| Disc | one MODE2/2352 data track of 220,544 sectors + one 4-minute CD-DA track |
| File system | plain ISO 9660 with the Sony CD-XA extension — **29 files**, four directories |
| Executable | `SLPS_011.00`, 1,155,072 bytes, loaded at **0x800A0000**, entry `0x80151010` |
| Codec | in-house LZSS, 4 KiB ring with a **preloaded synthetic dictionary**, methods `1` and `3` |
| Blocks | **6,638** packed blocks, 148.7 MB → 464.8 MB (3.13×), zero disagreements |
| Container | a bare table of byte offsets, in two variants; no lengths, no types |
| Directory | **there is none on the disc** — five extent tables compiled into the executable |
| Maps | 1,315 of them, in a 131 MB archive addressed only from a table at `0x8019622C` |
| Graphics | stock Sony **TIM**, with VRAM coordinates baked into every image |
| Music | stock Sony **SEQ** (94 of them) driven by VAB banks that live inside the executable |
| Voice | 194 MB of XA ADPCM, mono 18.9 kHz, on an **eight-channel interleave** |
| Script | **538,900 Shift-JIS strings** in 1,311 of the 1,315 map extents |
| Video | six `.STR` files, 4,315 MDEC frames, **three different bitstream versions** |
| Slack | 154 all-zero sectors in a 220,544-sector track — 0.07% |

Three structural facts carry most of the weight.

**The disc has no directory of its own.** ISO 9660 lists 29 files, and five of
them are undifferentiated multi-megabyte blobs. What divides `M.DAT` into
1,315 maps is a 10 KiB array of `(offset, length)` pairs compiled into
`SLPS_011.00` at `0x8019622C`. Delete the executable and 131 MB of the disc
becomes unaddressable. See [05](docs/05-containers-and-index.md).

**Everything else is Sony's.** TIM for images, SEQ and VAB for music, XA for
voice, STR/MDEC for video, PSY-Q for the runtime — dated by three RCS strings
left in the library code. The only format Namco wrote themselves is the
compressor. See [06](docs/06-graphics.md), [07](docs/07-audio.md),
[08](docs/08-movies.md).

**And that compressor is the Super Famicom one.** *Tales of Phantasia* (1995)
and *Tales of Destiny* (1997) share a nine-byte block header, the same method
numbering, the same 4 KiB window, and — to the constant — the same
run-length escape arithmetic. Two years, two CPU architectures, one packer.
See [11](docs/11-tales-lineage.md).

Start at [docs/01-overview.md](docs/01-overview.md).

---

## Documents

| Document | Contents |
|---|---|
| [01 — Overview](docs/01-overview.md) | The two tracks, hashes, the shape of the disc |
| [02 — The disc](docs/02-disc.md) | ISO 9660, sector modes, the mastering seams, `DUMMY3M.DA` |
| [03 — The executable](docs/03-executable.md) | PS-EXE, the memory map, PSY-Q, boot order, module bands |
| [04 — The block codec](docs/04-block-codec.md) | Full specification, the preloaded ring, verification |
| [05 — Containers and the index](docs/05-containers-and-index.md) | The offset table, and the file system that lives in the executable |
| [06 — Graphics](docs/06-graphics.md) | TIM everywhere, and a measured map of video memory |
| [07 — Audio](docs/07-audio.md) | 94 SEQ, 18 VAB headers inside the executable, the XA interleave |
| [08 — Movies](docs/08-movies.md) | Six STR files, three encoders, one that forgot its audio |
| [09 — Text and the font](docs/09-text.md) | JIS X 0201, per-file glyph inventories, the technique kanji |
| [10 — Leftovers](docs/10-leftovers.md) | `DEBUG.TXT`, a debug save, a profiler HUD, and a dead code path |
| [11 — The Tales lineage](docs/11-tales-lineage.md) | What 1997 kept from 1995, measured |
| [99 — Open questions](docs/99-open-questions.md) | What is still unknown, and how to attack it |

## Tools

Dependency-free Python 3 under [`tools/`](tools/). Nothing bundles game data.

```sh
export TOD="/path/to/Tales of Destiny (Japan) (Track 1).bin"

# the disc
python tools/iso9660.py    "$TOD" --pvd            # volume descriptors
python tools/iso9660.py    "$TOD"                  # the 29 files, with XA attributes
python tools/iso9660.py    "$TOD" --extract iso/   # unpack the file system
python tools/sector_map.py "$TOD" --files          # per-file sector-mode census
python tools/sector_map.py "$TOD" --runs --channels

# the executable
python tools/dismips.py    iso/SLPS_011.00 --header
python tools/dismips.py    iso/SLPS_011.00 0x80150D4C 84    # the decoder
python tools/dismips.py    iso/SLPS_011.00 --strings
python tools/exe_tables.py iso/SLPS_011.00           # every compiled-in table
python tools/tod_index.py  iso/SLPS_011.00 --table M.DAT

# the codec and the containers
python tools/tod_codec.py  iso/PIC/MC.D -o mc.bin
python tools/tod_arc.py    iso/DAT/E.DAT --recurse
python tools/verify.py     iso/SLPS_011.00 iso/DAT iso/PIC   # decode everything
python tools/verify.py     iso/SLPS_011.00 iso/DAT --control # the negative control

# assets
python tools/tim.py        mc.bin
python tools/vram_map.py   iso/SLPS_011.00 iso/DAT iso/PIC
python tools/str_probe.py  "$TOD" --str 106516 18392         # OP.STR
python tools/str_probe.py  "$TOD" --xa  149069 70760         # T.XA
python tools/sjis_strings.py iso/DAT/TKM.BIN --min 3
python tools/vag_probe.py    iso/DAT/V.DAT --at 0 --len 16384
python tools/script_scan.py  iso/SLPS_011.00 iso/DAT --map 900

# archaeology
python tools/leftovers.py    "$TOD" iso/ --filler
python tools/script_scan.py  iso/SLPS_011.00 iso/DAT --labels
```

## Confidence

Claims in these documents are labelled:

* **Verified** — a reimplementation reproduces the format over the whole
  relevant corpus, and the disagreements are enumerated.
* **Consistent** — the model explains every sample checked, but has not been
  exhaustively proven.
* **Open** — observed but not explained. Everything of this kind is collected
  in [99](docs/99-open-questions.md) rather than softened in place.

| Subject | Status | Coverage |
|---|---|---|
| ISO 9660 volume, file table, XA attributes | Verified | all 29 entries parsed and re-read |
| Sector modes and submodes | Verified | all 220,544 sectors of the data track |
| PS-EXE header and load map | Verified | header fields, entry chain disassembled |
| Block codec, methods 1 and 3 | Verified | 6,638 / 6,638 blocks, exact length, no exceptions |
| Method-1 dictionary | Verified | negative control: 25 structures vs 11 / 18 / 4 for wrong guesses |
| Method 0 (stored) | Consistent | disassembled; never used by any block on the disc |
| Container, both variants | Verified | 5,983 containers walked, 44,512 raw members classified |
| Extent tables in the executable | Verified | five tables cover their archives to the byte, 100% |
| TIM as the only image format | Verified | 443 distinct VRAM rectangles, all self-describing |
| VAB ↔ body pairing | Verified | 18 / 18 headers; `fsize − header` equals the body size exactly |
| SEQ inventory | Verified | 94 / 94 parse, `pQES` v1, 48 ticks per quarter |
| STR frame structure | Verified | 4,315 frames, none incomplete |
| XA coding parameters | Verified | read from the subheader of every Form-2 sector |
| Codec lineage to *Tales of Phantasia* | Verified | header, method numbering and escape constants compared |
| `V.DAT` is SPU ADPCM | Verified | 19 extents decoded; roughness inside the known-good band, controls outside it |
| The script's location and encoding | Verified | 1,315 extents walked, 538,900 strings recovered |
| What each `V.DAT` waveform is | **Open** | format settled, contents not |
| The map data structures inside a decoded map | **Open** | container shape known, contents not |
| Shift-JIS to glyph-sheet indexing | **Open** | the single-byte half is solved, the kanji half is not |

## Licence

Documentation: [CC BY 4.0](LICENSE-DOCS). Tools: [MIT](LICENSE).

*Tales of Destiny* is a trademark of BANDAI NAMCO Entertainment. This project
is unaffiliated with and unendorsed by Bandai Namco, Wolf Team or Sony
Interactive Entertainment.
