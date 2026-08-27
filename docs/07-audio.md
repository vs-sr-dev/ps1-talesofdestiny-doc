# 07 — Audio

**Status: verified** for the bank pairing, the sequence inventory and the XA
coding parameters; **consistent** for what each XA range is. Output in
[`reports/audio-vab.txt`](../reports/audio-vab.txt),
[`reports/xa-survey.txt`](../reports/xa-survey.txt) and
[`reports/exe-text.txt`](../reports/exe-text.txt).

Audio on this disc comes in three shapes, and the game uses all three at once:

* **sequenced music** — 94 Sony SEQ files in `S.DAT`, played from SPU samples;
* **streamed audio** — 194 MB of XA ADPCM in `S.XA` and `T.XA`;
* **the vocal theme** — Red Book CD-DA on track 2, played by the drive.

## The banks live in the executable

The PlayStation's sequencer needs a VAB: a header describing programs, tones
and waveform offsets, plus a body of raw SPU ADPCM. On this disc the bodies
are files and **every header is compiled into `SLPS_011.00`**.

### The main bank

At `0x80174B30`, uncompressed, 48,160 bytes:

| Field | Value |
|---|---|
| Tag | `pBAV` (Sony's `VABp` id as it appears in file order) |
| Version | 6 |
| Declared total size | 486,272 |
| Programs / tones / waveforms | 89 / 108 / 72 |
| Header length implied by 32 + 2048 + 89·16·32 + 512 | **48,160** |
| 486,272 − 48,160 | **438,112** |

`DAT/TALE.VB` is 438,112 bytes. The header's own size field, minus its own
computed length, equals the body file **to the byte**. And the boot sequence
([03](03-executable.md)) confirms the wiring: `main()` loads file id 1100
(`TALE.VB`) into `0x80010000` and then calls `0x800F7554` with `0x80174B30` as
the header pointer, before it does anything else.

### The battle banks

At `0x80180944` there is a seventeen-member container whose every member is a
**packed** VAB header — the only packed blocks anywhere in the executable.

```
 [ 0] 5152 bytes   5 programs   total 14,080  ->  body 8,928
 [ 1] 5152         5            total 15,536  ->  body 10,384
 ...
 [ 9] 5152         5            total 13,200  ->  body 8,048
 [10] 4640         4            total 12,128  ->  body 7,488
 ...
 [16] 4640         4            total 13,360  ->  body 8,720
```

`DAT/BVB.D` is a container of seventeen members whose sizes are
8,928 / 10,384 / 13,616 / 12,288 / 13,424 / 11,424 / 9,520 / 12,240 / 16,208 /
8,048 / 7,488 / 9,984 / 9,856 / 11,088 / 12,016 / 14,096 / 8,720 — **all
seventeen match, in order, exactly**. Sixteen "battle VB" bodies plus one,
each with a header the codec has to unpack before the SPU can be fed.

Each header's length is also exactly `32 + 2048 + programs·16·32 + 512`, the
textbook VAB layout, which is what makes the pairing a verification of the
decoder as well: a wrong dictionary would not produce seventeen headers whose
arithmetic closes.

Two details worth keeping. The main bank declares **version 6** and the
battle banks **version 32** — different tools, or the same tool at different
times. And the main bank, at 48 KB, was left uncompressed while the sixteen
smaller ones were packed down from 84 KB to 11 KB. Whoever added the battle
banks was paying attention to the executable's size in a way whoever added
the first one was not.

## The sequences

`DAT/S.DAT` is 94 extents and every one of them is a stock Sony SEQ:

| | |
|---|---|
| Tag | `pQES` on all 94 |
| Version | 1 on all 94 |
| Resolution | 48 ticks per quarter note on all 94 |
| Extent sizes | 2,048 – 36,864 bytes, 1,120,256 total |

Extents 0, 1 and 2 are the same size with the same header — the format has no
deduplication, so near-identical variants of a cue are simply stored again.

One further SEQ is embedded in the executable at `0x80183684`, just past the
packed VAB container.

## The sound test

The executable carries a 174-entry table of `char *` at `0x8018CFC8` — the
names shown in the game's Sound Test, in English, written by the sound team.

Entries 1–92 are music; 93–173 are sound effects. In full in
[`reports/exe-text.txt`](../reports/exe-text.txt). A sample:

```
  1  Preview edition          49  Lion  -Irony of fate-
  8  A Caged life             52  Rebel against destiny
 17  Victory!                 55  Tales of Destiny
 28  Wonder boy -Who are you?-   72  Memory "Yume de aruyouni"
 43  Will you dance with me?  91  Naval Forces
 92  Fin
```

and, for the effects, an entire vocabulary of Japanese onomatopoeia
transliterated into romaji:

```
 96  Swing1:Zashu            116  CrushGlass:kacha-n
105  Bomb3:Dogagagagaaaan!   150  Frog:Geroge-ro
110  Ice:Pikiiin             152  Oul:Ho-uHo-u
112  Majinken:Jyuba!         166  Money:Chariin
```

`Majinken` is 魔神剣, Stahn's signature technique — the same word the font
tables spell out in kanji ([09](09-text.md)). Several entries are marked by
their authors and are discussed in [10](10-leftovers.md).

94 sequences against 92 named music slots is close but not equal; the mapping
between the two is not established here.

## The XA streams

`XA/S.XA` and `XA/T.XA` are 194,002,944 bytes between them — 43% of the whole
disc. Every Form 2 sector in both reports the same coding byte, `0x01`:

**stereo, 37.8 kHz, 4-bit** — XA-ADPCM level B stereo.

> **Corrected.** This document previously read that byte as *mono 18.9 kHz*,
> from a decoder that had the coding byte's three two-bit fields in the reverse
> order. The disc settles it without reference to any specification. Four of
> the five audio-bearing movies carry an exact ratio between their audio
> sectors and their running time, and only one reading of the byte fits:
>
> | | sectors → seconds at 2× | audio sectors as stereo 37.8 kHz | as mono 18.9 kHz |
> |---|---:|---:|---:|
> | `OP.STR` | 122.61 s | **122.61 s** | 490.45 s |
> | `EVB.STR` | 61.49 s | **61.49 s** | 245.97 s |
> | `EVC.STR` | 39.20 s | **39.20 s** | 156.80 s |
> | `EVA.STR` | 49.79 s | **48.75 s** | 194.99 s |
>
> A stereo 37.8 kHz sector holds 2,016 samples per side, 53.33 ms; a mono
> 18.9 kHz sector holds 4,032 samples, 213.33 ms, which would give every movie
> four times as much audio as it is long. The corrected field order is
> `bits 0-1` channels, `bits 2-3` sample rate, `bits 4-5` bits per sample,
> which is what ECMA-130 specifies. `tools/str_probe.py` now decodes it that
> way and says so in its docstring.

### `T.XA`: eight channels, exactly matched to double speed

70,760 sectors, all tagged `RT | FORM2 | AUDIO`, with **file 1, channels 0
through 7** cycling one sector at a time:

```
149069  ch 0     149073  ch 4
149070  ch 1     149074  ch 5
149071  ch 2     149075  ch 6
149072  ch 3     149076  ch 7
149077  ch 0     ...
```

A level-B stereo stream consumes **18.75 sectors per second**: 2,016 samples
per side per sector at 37.8 kHz is 53.33 ms of sound. The PlayStation drive at
double speed delivers **150 sectors per second**, and an eight-way interleave
gives any one channel exactly 150 / 8 = **18.75**.

The match is exact, and it is the whole design: eight simultaneous voice
streams is precisely what a double-speed drive can carry at this coding, with
nothing left over. The interleave depth and the coding byte were chosen
together.

*Tales of Eternia*, three years later, spends the same budget the other way —
**sixteen** channels of **mono** 37.8 kHz, 9.375 sectors per second each,
which also comes to exactly 150. Twice the simultaneous voices, no stereo.
See [11](11-tales-lineage.md) and
[ps1-talesofeternia-doc](https://github.com/vs-sr-dev/ps1-talesofeternia-doc).

`SLPS_011.00` indexes the file with a table of 258 `(first sector, last
sector)` pairs at `0x80192FF4`, consumed by the player at `0x8014F0B8`:

```
8014F0B8  lui   v0, 0x8019
8014F0BC  addiu v0, v0, 12276        ; 0x80192FF4
8014F0C0  sll   v1, a3, 3            ; clip index * 8
8014F0C8  lw    a2, 0(v1)            ; first sector
8014F0CC  lw    a3, 4(v1)            ; last sector
8014F0D0  jal   0x8014EF04
```

The ranges run from sector 10 to sector 70,697 — inside `T.XA`'s 70,760 — and
they overlap heavily: 258 distinct ranges whose lengths sum to 508,969
sectors, 7.2× the file. That is what an eight-channel interleave looks like
from the index side: one disc range carries eight different clips, and
different entries take different sub-ranges of the same span. Per channel a
range is typically 120–720 sectors, or 7–45 seconds.

### `S.XA`: an eight-slot grid, three-eighths used

23,968 sectors on the same eight-way grid, but only channels 0, 1 and 2 are
ever tagged as audio:

| | Sectors |
|---|---|
| channel 0, submode `0x64` | 2,881 |
| channel 1, submode `0x64` | 2,995 |
| channel 2, submode `0x64` | 2,406 |
| channel 0, submode `0x00` | 15,682 |

The pattern on disc is `ch0, ch1, ch2, then five sectors with no submode bits
set at all`, repeating 11,282 times. Those five are the unused slots of the
interleave. They are not blank — about 72% of each one is non-zero — but
nothing marks them as audio, real-time or data, so the drive's XA filter drops
them.

What is actually in them is a leftover, and it names the machine that made the
disc. See [10](10-leftovers.md).

Sixty-five per cent of a 49 MB file is empty interleave slots: 32 MB of disc
spent to keep three streams on an eight-slot grid that only `T.XA` needs. The
simplest explanation is that both files were produced by the same tool with
the same interleave setting, and nobody reduced it for the smaller one.

## `V.DAT` — 1,349 more waveforms

`DAT/V.DAT` is 22,157,312 bytes divided into 1,349 extents by the table at
`0x80193804`. Its extents are neither containers nor packed blocks, and its
contents are high-entropy: 6.22 bits per byte.

They are SPU ADPCM. [`tools/vag_probe.py`](../tools/vag_probe.py) runs the
ADPCM predictor over a buffer and measures how rough the resulting waveform
is — the mean absolute second difference divided by the mean absolute sample.
Real audio is locally smooth; anything else decodes to something
indistinguishable from noise.

| Buffer | Roughness |
|---|---|
| `V.DAT`, 19 extents sampled across the file | **0.121 – 0.717**, mean 0.377 |
| `TALE.VB` — a known VAG body | 0.719 |
| `BVB.D` member 0 — a known VAG body | 0.954 |
| `M.DAT` — control, not audio | 1.271 |
| `SLPS_011.00` — control | 1.800 |
| uniform random bytes — control | 1.236 |

Every `V.DAT` extent lands inside the band the two known sample bodies
occupy, and every control lands where random bytes do. The block flags agree:
each extent carries exactly one `flag = 1` (loop start) and one `flag = 7`
(loop end) among otherwise-zero flag bytes, which is a single waveform.

The loader at `0x8014F990` bounds-checks its index against the literal `1349`,
reads file id 1500 — `\DAT\V.DAT;1` — and is called once, from the sound
module at `0x800F74F8`, with the index computed as `id − 100`.

So `V.DAT` is a library of 1,349 individual SPU waveforms, 8–40 KB each,
loaded one at a time by number. Which sound each one is remains
[open](99-open-questions.md).

Full report: [`reports/vdat-probe.txt`](../reports/vdat-probe.txt).

## Track 2

18,192 sectors of CD-DA, about 4 minutes 2 seconds. It is addressed by the ISO
volume through the `DUMMY3M.DA` pad file ([02](02-disc.md)) and by the drive
as an ordinary audio track. It is the only audio on the disc the PlayStation
does not have to decode.

## Reading it yourself

```sh
python tools/exe_tables.py iso/SLPS_011.00 --vab
python tools/exe_tables.py iso/SLPS_011.00 --xa
python tools/exe_tables.py iso/SLPS_011.00 --soundtest
python tools/tod_arc.py    iso/DAT/BVB.D
python tools/str_probe.py  "$TOD" --xa 149069 70760
python tools/sector_map.py "$TOD" --channels
```
