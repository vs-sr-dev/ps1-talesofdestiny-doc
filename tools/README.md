# Tools

Dependency-free Python 3. Nothing here bundles game data; everything takes a
path to an image you supply. Tested on CPython 3.11+.

Set up once:

```sh
export TOD="/path/to/Tales of Destiny (Japan) (Track 1).bin"
python tools/iso9660.py "$TOD" --extract iso/
```

Everything below assumes `iso/` holds the extracted file system.

## Layers

The tools stack in the order the disc does. Each one is usable on its own and
importable as a module.

```
psxdisc.py      raw MODE2/2352 sectors, subheaders, Form 1 / Form 2
  iso9660.py    volume descriptors, the directory tree, extraction
  sector_map.py the sector-mode census and the per-file breakdown
  str_probe.py  .STR frame headers and XA coding parameters

dismips.py      R3000A / MIPS-I + GTE disassembler, PS-EXE header
  exe_tables.py the tables compiled into SLPS_011.00
  tod_index.py  the five extent tables and the map id array

tod_codec.py    the block codec — methods 0, 1 and 3
  tod_arc.py    the container, both variants
    verify.py   decode every block on the disc and check it
    tim.py      Sony TIM / CLT
      vram_map.py   where every image on the disc lands in VRAM
    script_scan.py  the Shift-JIS script in the map archive

sjis_strings.py Shift-JIS and half-width strings out of any file
vag_probe.py    is this buffer SPU ADPCM?  decode it and find out
leftovers.py    the archaeology, collected
```

## One-liners

```sh
# what is on the disc
python tools/iso9660.py     "$TOD" --pvd
python tools/iso9660.py     "$TOD"
python tools/sector_map.py  "$TOD" --files
python tools/sector_map.py  "$TOD" --runs --channels

# the executable
python tools/dismips.py     iso/SLPS_011.00 --header
python tools/dismips.py     iso/SLPS_011.00 0x80150D4C 84
python tools/dismips.py     iso/SLPS_011.00 --find-jal 0x80150F58
python tools/dismips.py     iso/SLPS_011.00 --strings
python tools/exe_tables.py  iso/SLPS_011.00
python tools/exe_tables.py  iso/SLPS_011.00 --vab --xa
python tools/tod_index.py   iso/SLPS_011.00 --table M.DAT

# the codec
python tools/tod_codec.py   iso/PIC/MC.D -o mc.bin
python tools/tod_arc.py     mc.bin
python tools/tod_arc.py     iso/DAT/E.DAT --recurse
python tools/tod_arc.py     iso/DAT/E.DAT --extract edat/
python tools/verify.py      iso/SLPS_011.00 iso/DAT iso/PIC
python tools/verify.py      iso/SLPS_011.00 iso/DAT --control

# assets
python tools/tim.py         edat/0000.bin
python tools/vram_map.py    iso/SLPS_011.00 iso/DAT iso/PIC --csv rects.csv
python tools/str_probe.py   "$TOD" --str 106516 18392
python tools/str_probe.py   "$TOD" --xa  149069 70760
python tools/vag_probe.py   iso/DAT/V.DAT --len 16384 --pcm out.raw

# text
python tools/sjis_strings.py iso/DAT/TKM.BIN --min 3 --offsets
python tools/script_scan.py  iso/SLPS_011.00 iso/DAT --map 900
python tools/script_scan.py  iso/SLPS_011.00 iso/DAT --labels

# archaeology
python tools/leftovers.py    "$TOD" iso/ --filler
```

## Notes

* `verify.py` decodes the whole disc and takes about a minute on a modern CPU.
  `--quick` skips the decode and only walks the structure.
* `script_scan.py --labels` decodes all 1,315 map extents and takes a few
  minutes.
* Output that contains Japanese needs a UTF-8 capable terminal. On Windows,
  `set PYTHONIOENCODING=utf-8` first, or redirect to a file.
* `vram_map.py` writes a coarse ASCII map; the CSV it can emit is the
  authoritative form.
* `leftovers.py --xa-filler` sweeps the unused slots of the XA interleave and
  takes about a minute.

## Two corrections, made while documenting Tales of Eternia

Both change numbers that earlier versions of this repository published.

* **`iso9660.py`** decoded the CD-XA directory attribute bits one position
  low, so Form-1 files read as `MODE2`, interleaved files as `FORM2`, and
  `DUMMY3M.DA` as `INTERLEAVED`. ECMA-168 puts Mode 2 Form 1 at bit 11, Form 2
  at 12, interleaved at 13, CD-DA at 14 and directory at 15. With the fix
  `DUMMY3M.DA` reads `4555[CDDA]`, which is what it always was.

* **`str_probe.py`** decoded the CD-XA coding byte's three two-bit fields in
  the reverse order, so `0x01` read as "mono 18.9 kHz" instead of "stereo
  37.8 kHz". The disc settles it on its own: four of the five audio-bearing
  movies match stereo 37.8 kHz to two decimal places against their own running
  time, and mono 18.9 kHz is four times out on every one of them. The voice on
  this disc is **stereo 37.8 kHz**, and the eight-channel interleave turns out
  to fill a double-speed drive exactly. See
  [docs/07-audio.md](../docs/07-audio.md).
