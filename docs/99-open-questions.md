# 99 — Open questions

Everything here is observed but not explained. Nothing in the other documents
is softened to hide a gap; the gaps are collected in this one.

## 1. What is inside a decoded map

**What is known.** Every one of the 1,315 map extents is a container of three
or four members. The first two or three decode to TIMs; the last decodes to a
container of nine to twelve sub-members, and among those sub-members is the
map's entire Shift-JIS script ([09](09-text.md)).

For map extent 1 (`id 1000`) the last member's twelve sub-members are:

```
 [ 0]      52 -  36,732   36,680   a table of {u32, u16, u16} triples, then data
 [ 1]  36,732 -  36,736        4
 [ 2]  36,736 -  36,752       16
 [ 3]  36,752 -  36,760        8
 [ 4]  36,760 -  41,472    4,712
 [ 5]  41,472 -  41,480        8
 [ 6]  41,480 -  41,632      152
 [ 7]  41,632 -  82,004   40,372
 [ 8]  82,004 -  89,692    7,688
 [ 9]  89,692 - 286,308  196,616
 [10] 286,308 - 288,620    2,312
 [11] 288,620 - 289,140      520
```

**What is not.** Which sub-member is geometry, which is collision, which is
the event script's bytecode, which holds entity placement. Sub-member 0 opens
with a run of `{u32 address, u16, u16}` triples that looks like an event or
label table, and sub-member 9's 196,616 bytes (`0x30008`) is suspiciously
close to a round `0x30000` plus a header.

**How to attack it.** The sub-member count is stable at nine to twelve across
all 1,315 maps; comparing the same index across many maps of very different
sizes should separate the fixed-size tables from the variable ones. The script
strings give an anchor: whatever references them is the message table, and
whatever references *that* is the event interpreter.

## 2. How a Shift-JIS code becomes a glyph

**What is known.** The text is Shift-JIS ([09](09-text.md)). A 39-entry table
at `0x801807FC` folds full-width punctuation onto single-byte JIS X 0201
codes. `PIC/MC.D` holds ten 4bpp glyph sheets totalling 344,064 pixels, and
`TKM.BIN` carries its own 119-glyph inventory for the same purpose at smaller
scale.

**What is not.** No table has been found that maps the two-byte Shift-JIS
kanji range onto a position in those ten sheets. `TKM.BIN` does it with an
explicit inventory plus a pointer array; `MC.D` has neither.

**How to attack it.** Find the text renderer — it will be the function that
reads a byte, tests it against `0x81`, and computes a `RECT` — and follow what
it indexes. The `0x800A0000` string block gives an easy breakpoint target.

## 3. What each of the 1,349 `V.DAT` entries is

**What is known.** `V.DAT` is SPU ADPCM. Decoding a sample of its extents with
[`tools/vag_probe.py`](../tools/vag_probe.py) gives waveform roughness of
0.12–0.72, against 0.72 for the known VAG body `TALE.VB`, 0.95 for a `BVB.D`
body, and 1.24–1.80 for controls that are not audio (see
[`reports/vdat-probe.txt`](../reports/vdat-probe.txt)). Its loader at
`0x8014F990` is bounds-checked against the literal 1349, reads file id 1500,
and is called from the sound module at `0x800F74F8` with the index computed as
`id − 100`. Each extent carries exactly one loop-start (`flag 1`) and one
loop-end (`flag 7`) marker, so each holds a single waveform of 8–40 KB.

**What is not.** What the 1,349 waveforms *are*. There are 1,315 maps, which
is close but not equal; whether the correspondence is per-map, per-scene or
per-effect is not established, and no VAB header has been found that indexes
them.

## 4. What `DEBUG.TXT` unlocks

**What is known.** `0x801502F4` searches for `\DEBUG.TXT;1` and writes 8 or 4
to `0x80174AD0` accordingly ([10](10-leftovers.md)).

**What is not.** What reads it. A naive `lui`/`addiu` cross-reference returns
116 sites, which is too many to be real — the address is almost certainly the
base of a structure and most hits are neighbouring fields.

**How to attack it.** Disassemble the whole `0x800F0000`–`0x80110000` band
with proper register liveness and separate the accesses that are exactly
`0x80174AD0` from those that are `0x80174AD0 + n`.

## 5. The 258 XA ranges, one by one

**What is known.** The table at `0x80192FF4` holds 258 `(first, last)` sector
pairs into `T.XA`, consumed at `0x8014F0B8` ([07](07-audio.md)).

**What is not.** What index corresponds to what scene, and how the channel
number is chosen. The player function takes the range and a location built
from four stack bytes; where the channel comes from is not traced.

## 6. The second frame buffer

**What is known.** Boot sets both `SetDefDrawEnv` and `SetDefDispEnv` to
`(0, 0, 320, 240)`. No TIM on the disc writes into `(0,0)`–`(255,255)`, and
exactly one writes into `(256,0)`–`(319,255)`. There is a second empty region
at `(640,256)`–`(1023,479)` ([06](06-graphics.md)).

**What is not.** Where the back buffer lives, and whether the layout changes
between field, battle and movie playback. The code at `0x800F18E0` sets up a
second pair of environments under a `height == 480` test that this build does
not appear to take.

## 7. `B.DAT`'s variant-B containers

**What is known.** All 339 `B.DAT` extents use the countless container variant
([05](05-containers-and-index.md)), and no other archive does. Its extent
table also sits apart from the other four in the executable.

**What is not.** Why. The obvious guess is that battle data came through a
different tool chain, which would also explain the isolated table, but nothing
here confirms it.

## 8. Where the 16,768 submode-`0x00` sectors' data comes from

**What is known.** 15,682 of them are `S.XA`'s unused interleave slots. Their
user data is not zero ([07](07-audio.md)).

**What is not.** What is in them. If it is a copy of the previous sector, the
mastering tool padded by repetition; if it is stale buffer content, it may
contain material from elsewhere in the build. Either would be worth knowing.

## 9. `PICTURE.BIN` and the eighth `PIC` file

`KAISEN.BIN` references `sim:PICTURE.BIN`, and the file registry skips id 1004
([10](10-leftovers.md)). Neither file exists on the disc, and nothing else
names them. There is nothing more to measure here; they are recorded so that
anyone who finds a prototype disc knows what to look for.

## 10. `namco 1` … `namco 11`

Eleven consecutive entries in the sound test are named only by number
([07](07-audio.md)). Whether they are unfinished cues, licensed material
awaiting clearance, or arrangements of Namco's older themes is not something
the disc says.
