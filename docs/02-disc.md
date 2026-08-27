# 02 — The disc

**Status: verified.** Every sector of the data track was read and classified
by [`tools/sector_map.py`](../tools/sector_map.py); the volume was parsed by
[`tools/iso9660.py`](../tools/iso9660.py). Output in
[`reports/sector-map.txt`](../reports/sector-map.txt),
[`reports/disc-layout.txt`](../reports/disc-layout.txt) and
[`reports/iso-volume.txt`](../reports/iso-volume.txt).

## Sector format

The data track is MODE2/2352: raw sectors with no ECC stripping.

```
0x000  12  sync             00 FF FF FF FF FF FF FF FF FF FF 00
0x00C   3  address          MM SS FF in BCD, counting from 00:02:00
0x00F   1  mode             0x02 throughout
0x010   8  subheader        file, channel, submode, coding — written twice
0x018      user data        2048 bytes (Form 1) or 2324 bytes (Form 2)
           EDC / ECC        288 bytes (Form 1) or a 4-byte EDC (Form 2)
```

Form is bit 5 of the submode byte. Form 1 carries the file system, the
executable and all packed content; Form 2 carries XA ADPCM and the audio half
of the movies.

## The system area

Sectors 0–15 sit below the volume descriptors and are not part of the file
system. On this disc:

| Sector | Contents |
|---|---|
| 0–3 | ASCII `'0'` filler, 2,323 of 2,324 bytes non-zero |
| 4 | `          Licensed  by          Sony Computer Entertainment Inc.` followed by more `'0'` |
| 5–11 | the PlayStation boot logo, as binary |
| 12–15 | Form 2, entirely zero |

This is the stock licence block a PlayStation mastering tool writes; the four
trailing Form 2 sectors are the standard shape of it. Nothing here is
game-specific.

## Submode census

All 220,544 sectors:

| Submode | Meaning | Sectors | Share |
|---|---|---|---|
| `0x64` | RT \| FORM2 \| AUDIO | 84,203 | 38.2% |
| `0x08` | DATA | 83,890 | 38.0% |
| `0x48` | RT \| DATA | 34,951 | 15.8% |
| `0x00` | none set | 16,768 | 7.6% |
| `0x42` | RT \| VIDEO | 679 | 0.3% |
| `0x89` | EOF \| DATA \| EOR | 31 | — |
| `0xE4` | EOF \| RT \| FORM2 \| AUDIO | 14 | — |
| `0x20` | FORM2 | 4 | — |
| `0x80` | EOF | 2 | — |
| `0x09`, `0xC8` | — | 2 | — |

Form 1: 136,323 sectors. Form 2: 84,221 (38.2%).

The 16,768 sectors with *no* submode bits set are not padding. All but 1,086
of them are the unused slots of `S.XA`'s interleave — see
[07](07-audio.md) — and their user data is not zero.

## Per-file sector modes, and the seams they show

The interesting column is the one that shows which sectors a file is made of.
Abridged from [`reports/disc-layout.txt`](../reports/disc-layout.txt):

| File | LBA | Sectors | Submodes |
|---|---|---|---|
| `EVA.STR` | 82,318 | 7,468 | `48` RT\|DATA ×6534, `64` audio ×914, `00` ×19 |
| `EVB.STR` | 89,786 | 9,224 | `48` ×7866, `64` ×1152, `00` ×205 |
| `EVC.STR` | 99,010 | 5,880 | `48` ×4503, `64` ×734, `00` ×642 |
| `LOGO.STR` | 104,890 | 776 | **`42` RT\|VIDEO ×679**, `64` ×71, `00` ×25 |
| `NAMCO.STR` | 105,666 | 850 | **`08` DATA ×849** — no real-time flag, no audio at all |
| `OP.STR` | 106,516 | 18,392 | `48` ×16048, `64` ×2298, `00` ×45 |
| `S.XA` | 125,101 | 23,968 | `00` ×15682, `64` ×8282 |
| `T.XA` | 149,069 | 70,760 | `64` ×70752 |

Three different conventions for six movies, in one directory:

* `NAMCO.STR` is mastered as **ordinary Form 1 data**, submode `0x08`, with no
  real-time bit and no XA audio sectors interleaved into it. The ISO record
  agrees: its XA attribute word is `0D55` (plain Mode 2) where every other
  `.STR` on the disc is `2555` (Form 2).
* `LOGO.STR` tags its video sectors `RT | VIDEO` (`0x42`).
* The four event movies tag theirs `RT | DATA` (`0x48`).

Since all six are decoded by the same MDEC path, the tagging makes no
difference at run time; it is a fingerprint of *when and by whom* each file was
made. [08](08-movies.md) shows the same three-way split in the bitstream
version numbers, and the two splits agree.

## Packing

Files are laid down back to back. Between the end of one and the start of the
next there is never more than the single sector holding a directory record.
The only slack on the whole track is:

* 154 all-zero sectors (0.07%), of which 150 are the pre-gap before track 2;
* the tail of the last sector of each file, which is what the container
  format's final member absorbs (see [05](05-containers-and-index.md)).

Every one of the five bulk archives is covered by its extent table to the last
byte, with no unreferenced regions at all — see the table in
[05](05-containers-and-index.md). Whatever else this disc is, it is not
padded.

## `DUMMY3M.DA` — the pad file that names the music

The root directory has one entry that cannot be read:

```
DUMMY3M.DA;1    LBA 220694    36,952,064 bytes    attr=4555 [INTERLEAVED]
```

The data track ends at LBA 220,543. The extent begins 151 sectors past that
and runs for 18,043 more. Three numbers explain it:

* 220,544 + 150 = **220,694** — the data track plus the standard two-second
  pre-gap is exactly where the CD-DA audio track begins;
* 220,694 + 18,043 = **238,737** — exactly the volume size the PVD declares;
* the ISO attribute word is `4555`, whose bit 14 is the CD-XA *interleaved*
  flag.

So the pad file is not a hole and not an accident of the dump. It is a
directory entry laid deliberately over the Red Book audio track, so that the
ISO volume covers the physical disc end to end. The name is the giveaway:
`DUMMY` plus a size tag, the sort of thing a mastering script generates.

Any tool that walks the ISO and trusts the extent will read past the end of
the data track; `tools/iso9660.py --extract` clamps and reports the file as
truncated rather than failing.

## Reading it yourself

```sh
python tools/iso9660.py    "$TOD" --pvd
python tools/iso9660.py    "$TOD"
python tools/sector_map.py "$TOD" --files
python tools/sector_map.py "$TOD" --runs --channels
python tools/leftovers.py  "$TOD" iso/ --filler
```
