# 01 — Overview: one disc, two tracks

*Tales of Destiny* shipped in Japan on 23 December 1997 as a single
PlayStation disc, SLPS-01100. The volume was mastered three weeks earlier —
every directory record on it is stamped `1997-12-02 01:03:00 GMT+0`, to the
second.

This repository documents the structure of that disc: how the file system is
laid out, how the 488 MB of content inside 29 files is addressed, what
compresses it, and which of the formats Namco wrote and which they took from
Sony's libraries.

## Reference image

Everything in these documents was measured against this dump. No other build
was consulted, and nothing from it is redistributed here.

| | |
|---|---|
| Cue sheet | `Tales of Destiny (Japan).cue`, MD5 `3d93f3866fb795def4422b1c5714ae3e` |
| Track 1 | `Tales of Destiny (Japan) (Track 1).bin` — MODE2/2352 |
| Size | 518,719,488 bytes = 220,544 raw sectors |
| MD5 | `816721cd3224c98f89306b06c06c846c` |
| SHA-1 | `eb1c41fcb44e5fbc85da7d92f1e2889b69f299f5` |
| Track 2 | `Tales of Destiny (Japan) (Track 2).bin` — CD-DA |
| Size | 42,789,936 bytes = 18,192 sectors ≈ 4 min 02 s |
| MD5 | `26d92549b65c142e1f9dfcf9cb50d188` |
| SHA-1 | `3db2ed0464ac53c6f1da35bdcc0c08694d91788a` |

Track 2 is the game's vocal theme, played from the Red Book track rather than
streamed — the only asset on the disc in a format the game does not have to
decode. Everything else is in track 1.

## Volume identity

From the Primary Volume Descriptor at LBA 16, printed by
[`tools/iso9660.py --pvd`](../tools/iso9660.py) and committed as
[`reports/iso-volume.txt`](../reports/iso-volume.txt):

| Field | Value |
|---|---|
| System identifier | `PLAYSTATION` |
| Volume identifier | `TALESOFDESTINY` |
| Publisher | `NAMCO LIMITED` |
| Data preparer | `NAMCO LIMITED` |
| Application | `PLAYSTATION` |
| Created | `1997120201030000` |
| Volume size | 238,737 blocks |
| XA signature | `CD-XA001` at offset 0x400 of the PVD |
| Boot file | `cdrom:SLPS_011.00;1` (from `SYSTEM.CNF`) |

The volume claims 238,737 blocks but the data track holds only 220,544. The
missing 18,193 are the CD-DA track, and the volume covers them with a pad
file — see [02](02-disc.md).

## The 29 files

```
DAT/    B.DAT        4,466,688   battle data           339 extents
        BVB.D          189,400   battle sample bodies   17 members
        DBG.D              705   a debug new-game state
        E.DAT        2,152,448   event still images     38 extents
        INI.D              797   the new-game state
        KAISEN.BIN      73,160   the naval mini-game, a MIPS overlay
        M.DAT      137,869,312   maps, and the script 1315 extents
        S.DAT        1,120,256   music                  94 sequences
        TALE.VB        438,112   the main sample body
        TKM.BIN         63,420   the janken mini-game
        V.DAT       22,157,312   SPU ADPCM waveforms   1349 extents
MOVIE/  EVA.STR     15,294,464   746 frames
        EVB.STR     18,890,752   898 frames
        EVC.STR     12,042,240   514 frames
        LOGO.STR     1,589,248   155 frames, 320x240
        NAMCO.STR    1,740,800   170 frames, 256x240, no audio
        OP.STR      37,666,816   1832 frames
PIC/    BF.D            13,676   battle font
        FACE.D          57,792   portraits, 10
        FACE2.D         65,596   portraits, 10
        I.D            109,904   item icons, 458 slots
        MC.D           106,604   the main font and menu graphics
        RC.D            11,882   rank characters
        WM.D            18,356   world map
XA/     S.XA        49,086,464   3 of 8 interleave slots used
        T.XA       144,916,480   8 channels, 258 indexed clips
        SLPS_011.00  1,155,072   the executable
        SYSTEM.CNF          67
        DUMMY3M.DA  36,952,064   declared past the end of the data track
```

Sixteen of those are real content files; the remaining thirteen are the
executable, the boot script, the pad file and ten small support files. Nothing
in the ISO says what is inside `M.DAT`, `V.DAT`, `B.DAT`, `S.DAT` or `E.DAT` —
that knowledge is compiled into `SLPS_011.00`.

## What the disc is made of, by sector

Measured by [`tools/sector_map.py`](../tools/sector_map.py), committed as
[`reports/disc-layout.txt`](../reports/disc-layout.txt) and
[`reports/sector-map.txt`](../reports/sector-map.txt).

```
        0 -     15   system area: '0' filler, the Sony licence string at 4,
                     the boot logo at 5-11, four empty Form 2 sectors at 12-15
       16 -     23   volume descriptors, path tables, root directory
       24 -  82,316  DAT/ : B.DAT, BVB.D, E.DAT, KAISEN.BIN, M.DAT, S.DAT,
                     TALE.VB, TKM.BIN, V.DAT — 82,293 sectors of Form 1
   82,317 - 124,907  MOVIE/ : six .STR files, mostly Form 2
  124,908 - 125,099  PIC/ : seven .D files
  125,100 - 219,828  XA/ : S.XA then T.XA — 94,728 sectors, all Form 2
  219,829 - 220,392  SLPS_011.00
  220,393            SYSTEM.CNF
  220,394 - 220,543  150 all-zero sectors, the pre-gap before track 2
```

Two things about that layout are worth noticing straight away.

**The executable is at the far end of the disc.** Almost every PlayStation
disc puts its boot executable near LBA 24, right after the file system, so the
drive can load it without a long seek. Here it sits at LBA 219,829, 99.7% of
the way out, past 194 MB of XA audio. Whatever the reason — probably that the
outer edge reads fastest on a CAV drive, or simply that the mastering script
appended it — the boot seek is the longest one the disc can ask for.

**Streamed audio is 43% of the disc.** `S.XA` and `T.XA` together are
194,002,944 bytes across 94,728 sectors. Of the whole data track, 84,221
sectors (38.2%) are Form 2, the mode that carries XA ADPCM and MDEC video
without an ECC layer.

## Content, decompressed

Running the codec over everything the index reaches
([`reports/verify.txt`](../reports/verify.txt)):

| | |
|---|---|
| Containers walked | 5,983 |
| Packed blocks | 6,638 |
| Packed bytes | 148,665,346 |
| Unpacked bytes | 464,839,924 |
| Ratio | 3.13× |
| Length disagreements | 0 |

Add the 194 MB of XA and the 87 MB of MDEC video, neither of which is packed,
and the disc's 488 MB of files expand to roughly 745 MB of runtime data.

Inside that expansion is the whole game script: **538,900 Shift-JIS strings**
spread across 1,311 of the 1,315 map extents ([09](09-text.md)).

## Where to go next

* The disc itself: sector modes, the mastering seams, the pad file — [02](02-disc.md)
* The executable and the memory map — [03](03-executable.md)
* The codec, fully specified and reimplemented — [04](04-block-codec.md)
* Containers, and the file system that lives in the executable — [05](05-containers-and-index.md)
* Graphics, and a measured map of VRAM — [06](06-graphics.md)
* Audio: sequences, banks, and the XA interleave — [07](07-audio.md)
* The six movies and their three encoders — [08](08-movies.md)
* Text, the font, and how Japanese is stored — [09](09-text.md)
* Leftovers and small archaeology — [10](10-leftovers.md)
* What this build inherited from *Tales of Phantasia* — [11](11-tales-lineage.md)
* What is still unknown — [99](99-open-questions.md)
