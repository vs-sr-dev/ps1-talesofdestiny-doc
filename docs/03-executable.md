# 03 — The executable

**Status: verified** for the header, the load map and the boot chain;
**consistent** for the module bands, which are inferred from an
instruction-plausibility scan rather than from symbols. Disassembly in
[`reports/exe-map.txt`](../reports/exe-map.txt), strings in
[`reports/exe-strings.txt`](../reports/exe-strings.txt).

## Header

`SLPS_011.00` is 1,155,072 bytes: a 2,048-byte PS-EXE header and 1,153,024
bytes of image.

| Field | Value |
|---|---|
| Magic | `PS-X EXE` |
| Entry (`pc0`) | `0x80151010` |
| `gp0` | `0x00000000` (set by the boot code instead) |
| Text address | `0x800A0000` |
| Text size | `0x00119800` = 1,153,024 |
| Data / bss / stack in header | all zero |
| Region string | `Sony Computer Entertainment Inc. for Japan area` |

`SYSTEM.CNF` asks for four TCBs, sixteen events and a stack at `0x801FFF00`:

```
BOOT = cdrom:SLPS_011.00;1
TCB = 4
EVENT = 16
STACK = 801FFF00
```

## The memory map

The image occupies `0x800A0000` – `0x801B9800`. That placement is the single
most consequential decision in the build, because of what it leaves *below*.

```
0x80000000 - 0x8000FFFF   kernel
0x80010000 - 0x8009FFFF   576 KiB free — the working arena
                          · a whole map's data is read here (see 05)
                          · KAISEN.BIN, the naval mini-game overlay, links here
                          · TKM.BIN, the janken mini-game, links here
                          · TALE.VB is staged here before the SPU transfer
0x800A0000 - 0x800ABFFF   read-only strings: error text, path templates,
                          the sound-test names, the SE names
0x800AC000 - 0x8016FFFF   code — 100% decodable MIPS across the whole band
0x80170000 - 0x801B97FF   data: the VAB header, the font tables, the map id
                          array, the file registry, the five extent tables
0x801B9800 - 0x801C8DB7   (image ends; small data begins)
0x801C8DB8                gp
0x801C96C8 - 0x801D0E4F   zeroed at boot by the entry stub: 29,576 bytes of bss
0x801D0E50 - 0x801FFFFF   heap and stack
0x80200000                sp, as the entry stub sets it
```

The 576 KiB hole under the executable is the game's only large working buffer,
and three different subsystems take turns in it. A map extent is read into it
whole and then decoded in place; a mini-game overlay is loaded over the top of
it; the SPU sample body passes through it. Nothing else on the PlayStation
side of this disc allocates on that scale.

The instruction-density scan that establishes the code band is stark: from
`0x800B0000` to `0x8016FFFF` every single 32-bit word decodes as a valid
MIPS-I or GTE instruction, 100.0% across forty-eight consecutive 16 KiB
windows. Outside that band the figure never exceeds 92%.

## The entry stub

`0x80151010` is a stock PSY-Q `crt0`:

```
80151010  lui   v0, 0x801C          ; v0 = 0x801C96C8
80151018  lui   v1, 0x801D          ; v1 = 0x801D0E50
80151020  sw    zero, 0(v0)         ; clear bss, word at a time
8015102C  bne   at, zero, 0x80151020
80151034  addiu v0, zero, 4         ; index into the stack table below
80151048  lui   a0, 0x8015          ; a0 = 0x801510BC
80151054  lw    v0, 0(a0)           ; = 0x00200000
8015105C  or    sp, v0, t0          ; sp = 0x80200000
80151090  lui   gp, 0x801C
80151094  addiu gp, gp, -29256      ; gp = 0x801C8DB8
8015109C  jal   0x801510CC          ; the BIOS thunk block
801510B0  jal   0x800F32F4          ; main()
801510B8  break 0x1
801510BC  .word 0x00200000 x4       ; the stack table
```

Two details are worth keeping.

The stack does **not** come from `SYSTEM.CNF`. The stub indexes a four-entry
table at `0x801510BC` with the constant 4 and takes `0x00200000 | 0x80000000`
= `0x80200000`, one byte above the top of a retail 2 MB console. All four
entries hold the same value; on a development board with 8 MB the natural
thing for such a table to hold would be a larger top, so this reads like a
per-machine table that was flattened for the retail build. That reading is a
guess; the four identical words are a fact.

The block at `0x801510CC` is the standard libapi BIOS thunk sled — pairs of
`addiu t2, zero, 0xA0 / jr t2 / addiu t1, zero, N` for BIOS calls `A0:39`
(`InitHeap`), `A0:70` (`_bu_init`), `B0:08`, `B0:09`, `B0:0B`, `B0:0C`.

`main()` is at `0x800F32F4`.

## What the runtime is

Three RCS keyword strings survived the link and date the SDK precisely:

```
0x800ACE3C  $Id: sys.c,v 1.135 1997/09/02 13:37:26 noda Exp $
0x800AD404  $Id: bios.c,v 1.86  1997/03/28 07:42:42 makoto Exp $
0x800AD6DC  $Id: intr.c,v 1.76  1997/02/12 12:45:05 makoto Exp $
```

The most recent is 2 September 1997, three months before the disc was
mastered. Around them are the usual PSY-Q artefacts: `MDEC_in_sync` /
`MDEC_out_sync` from libpress, the `CdlNop`…`CdlReadS` command-name table and
`CD timeout: ` / `DiskError: ` from libcd, `GPU timeout:que=%d,stat=%08x,…`
and the primitive names `F3L G3L FT3L GT3L … GT4` from libgpu, and
`Library Programs (c) 1993-1997 Sony Computer Entertainment Inc.` at
`0x801B71F0`. A `PS-X Control TAP Driver  Ver 3.0` string at `0x801B8D84`
accounts for the multitap support the pad-type strings advertise
(`<Multi Tap>`, `<Analog Controler>`, `<neGcon>`, `<Mouse>`).

## Boot order

The first thing `main()` does, before it touches the GPU:

```
800F2B7C  jal 0x801502F4          ; probe for \DEBUG.TXT;1, then bind the file registry
800F2B88  jal 0x800F34B8(1024, 512)   ; VRAM
800F2B9C  jal 0x800F18E0(320, 240)    ; display mode
800F2BB4  jal 0x8014F840(1100, 0x80010000)  ; load file id 1100 = TALE.VB
800F2BD8  jal 0x800F7554(0, 0x80174B30, 0x80010000)  ; hand it the VAB header
```

So the display is **320×240**, and the very first asset the game reads is the
main SPU sample bank, staged through the bottom of the working arena and
married to a VAB header that lives inside the executable at `0x80174B30`. See
[07](07-audio.md).

The `\DEBUG.TXT;1` probe is described in [10](10-leftovers.md).

## The module bands

Landmarks, in address order. These are the anchors the rest of this
documentation refers to.

| Address | What |
|---|---|
| `0x800A178C` – `0x800A4FC0` | error strings, sound names, path templates |
| `0x800F32F4` | `main()` |
| `0x800FC54C` | the map/scenario decode call, and `Decode error.(Scenario & Map)` |
| `0x80107E80` | the map loader, and `Map No.%d(0x%04x) not found.` |
| `0x8014EE08` | the CD read primitive |
| `0x8014F0B8` | the XA clip player — indexes the range table |
| `0x8014FAC4` | the map fetch: extent table → sector → `CdlReadN` |
| `0x80150BB0` | codec method 1 |
| `0x80150D4C` | codec method 3 |
| `0x80150F58` | the codec dispatcher |
| `0x801502F4` | the `DEBUG.TXT` probe and file-registry binder |
| `0x8015160C` | codec method 0 (stored) — never reached |
| `0x80151010` | entry |
| `0x80174B30` | the main VAB header, uncompressed, 48,160 bytes |
| `0x801807FC` | Shift-JIS → internal code map, 39 entries |
| `0x8018089C` | technique-name kanji inventory, 74 glyphs |
| `0x80180944` | 17 packed VAB headers |
| `0x80183684` | a SEQ, embedded |
| `0x80186C74` | 1,315 map IDs |
| `0x8018CFC8` | 174 sound-test names |
| `0x80192E44` | the file registry |
| `0x80192FF4` | 258 XA clip ranges |
| `0x80193804` | the five extent tables, back to back to `0x80198F74` |
| `0x8019923C` | the `B.DAT` extent table |

## Reading it yourself

```sh
python tools/dismips.py iso/SLPS_011.00 --header
python tools/dismips.py iso/SLPS_011.00 0x80151010 48       # the entry stub
python tools/dismips.py iso/SLPS_011.00 0x800F2B60 46       # boot order
python tools/dismips.py iso/SLPS_011.00 --strings
python tools/dismips.py iso/SLPS_011.00 --find-jal 0x80150F58
```
