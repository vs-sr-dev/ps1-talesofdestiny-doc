# 05 — Containers, and the file system that lives in the executable

**Status: verified.** The five extent tables cover their archives to the byte,
with no unreferenced regions; the container model walks 5,983 containers and
classifies 44,512 raw members without a single failure to parse. Output in
[`reports/exe-index.txt`](../reports/exe-index.txt) and
[`reports/verify.txt`](../reports/verify.txt).

## There is no directory on the disc

ISO 9660 lists 29 files. Five of them are the game:

| File | Bytes | What is inside |
|---|---|---|
| `DAT/M.DAT` | 137,869,312 | 1,315 maps |
| `DAT/V.DAT` | 22,157,312 | 1,349 SPU waveforms ([07](07-audio.md)) |
| `DAT/B.DAT` | 4,466,688 | 339 battle sets |
| `DAT/E.DAT` | 2,152,448 | 38 event picture sets |
| `DAT/S.DAT` | 1,120,256 | 94 music sequences |

Nothing inside any of those files says where one entry ends and the next
begins. There is no header, no magic, no table of contents, no length field —
the first byte of `M.DAT` is the first byte of map 0.

What divides them is five arrays compiled into `SLPS_011.00`, sitting back to
back in one 22 KiB region of the data segment. Each entry is eight bytes:

```
u32  byte offset into the archive     always a multiple of 2048
u32  byte length
```

| Table | Address | Entries | Archive | Coverage |
|---|---|---|---|---|
| — | `0x80193804` | 1,349 | `V.DAT` | 100.00% |
| — | `0x8019622C` | 1,315 | `M.DAT` | 100.00% |
| — | `0x80198B44` | 38 | `E.DAT` | 100.00% |
| — | `0x80198C74` | 94 | `S.DAT` | 100.00% |
| — | `0x8019923C` | 339 | `B.DAT` | 100.00% |

Every one of those archives is referenced end to end. Not one byte of the
167 MB they hold is unreachable, and not one byte is padding beyond what a
sector boundary demands.

Delete `SLPS_011.00` and 131 MB of `M.DAT` becomes an undifferentiated blob.
That is the same trick the Super Famicom *Tales of Phantasia* plays with
literal `bank:offset` immediates at its call sites — the asset directory is
part of the program, not part of the data ([11](11-tales-lineage.md)).

## How a map is fetched

`0x8014FAC4`, thirty-one instructions:

```
8014FAF0  addiu v0, v0, 25132       ; v0 = 0x8019622C, the M.DAT table
8014FAF4  sll   v1, a2, 3           ; index * 8
8014FAF8  addu  s0, v1, v0
...
8014FB0C  addiu v0, zero, 1700      ; look up file id 1700 in the registry
8014FB30  lw    a0, 0(s0)           ; the byte offset
8014FB38  srl   a0, a0, 11          ; -> sector
8014FB40  addu  a0, v0, a0          ; + the archive's own LBA
8014FB3C  jal   0x8015C648          ; sector -> MM:SS:FF
8014FB68  lw    a3, 4(s0)           ; the length
8014FB9C  jal   0x8014EE08          ; read it
```

Offset, shifted right by 11 to become a sector, plus the archive's start LBA,
converted to MSF, one `CdlReadN` for the whole extent. The offsets are all
multiples of 2048 precisely so that this shift is legal. The destination is
`0x80010000` — the bottom of the 576 KiB arena described in
[03](03-executable.md) — and a whole map arrives in one read.

## The map IDs

The extents are numbered, not named, and the numbering is indirect. A parallel
array of 1,315 `u16` map IDs at `0x80186C74`, terminated by `0xFFFF`, is
searched **linearly** by the loader at `0x80107E80`; the index at which the ID
is found is the extent number. When it is not found:

```
Map No.%d(0x%04x) not found.
```

All 1,315 IDs are distinct. They group by high byte, which behaves like an
area code:

| Area | Maps | | Area | Maps | | Area | Maps |
|---|---|---|---|---|---|---|---|
| `00` | 2 | | `06` | 90 | | `0C` | 202 |
| `01` | 7 | | `07` | 41 | | `0D` | 73 |
| `02` | 159 | | `08` | 37 | | `0E` | 82 |
| `03` | 156 | | `09` | 27 | | `0F` | 5 |
| `04` | 198 | | `0A` | 107 | | `10` | 9 |
| `05` | 115 | | `0B` | 5 | | | |

Extent 0 (`id 0002`) is 8,192 bytes at offset 0 and extent 1,314 (`id 0001`)
is 81,920 bytes at the very end; the low IDs bracket the archive.

**134 of the 1,315 entries share 39 extents.** Where two scene IDs need the
same room, the table simply points both at the same bytes; the sizes sum to
104.1% of the file. That is the only deduplication mechanism the format has,
and it works because nothing but the table knows where an extent starts.

## The container

Inside an extent, content is divided by a second structure — a bare table of
byte offsets, in two variants.

**Variant A**, counted:

```
u32  count
u32  offset[count]            offset[0] == 4 + 4*count
```

**Variant B**, self-sizing:

```
u32  offset[n]                offset[0] == 4*n
```

Variant B has no count field at all: its first entry is simultaneously the
offset of member 0 and, divided by four, the number of entries. Variant A
spends four extra bytes to say the same thing. Everything on the disc uses
variant A except `B.DAT`, whose 339 extents are all variant B.

A container records **no lengths and no types**. A member runs to the next
offset in the table; what it *is* has to be worked out from its own first
bytes, which is possible because every member is one of three self-describing
things: a packed block (nine-byte header), a nested container (the
`offset[0]` identity above), or a TIM (`0x00000010` and a self-consistent
block chain).

Two consequences of that austerity:

* **The last member absorbs the padding.** An extent's length is rounded up to
  a sector, and nothing records where the real data stops, so the final
  member of the top-level container is always a little longer than its
  content. In `M.DAT` extent 1 that slack is 743 bytes.
* **The table need not be sorted.** `PIC/I.D`, the item icon table, has 458
  slots but only 336 distinct offsets: where two items share an icon, two
  slots point at the same bytes and the table runs backwards. A member's end
  is then the next *larger* offset in the table, not the next entry.

Empty members — `offset[i] == offset[i+1]` — are how the format expresses a
hole in an otherwise dense index.

## What a map extent looks like

`M.DAT` extent 1, map ID `1000`, 251,904 bytes at LBA 4:

```
container A, 4 members
  [0] +20      74,996   block m3   74,986 ->  192,004   -> container A, 16 TIMs
  [1] +75,016  92,028   block m3   92,017 ->  199,328   -> container A, 5 TIMs/CLTs
  [2] +167,044 13,876   block m3   13,865 ->   56,272   -> container A, 3 TIMs
  [3] +180,920 70,984   block m3   70,232 ->  289,140   -> container A, 12 members
```

Three of the four are graphics; the fourth is the map itself. Its twelve
sub-members hold the map's data structures — geometry, collision, event
logic, entity tables — and, in 1,311 of the 1,315 maps, **the map's entire
Shift-JIS dialogue** ([09](09-text.md)). Identifying the rest is
[open](99-open-questions.md). What is settled is the shape: **three levels of
container, two of compression, and a 251 KB extent that becomes 736 KB in
RAM.**

Every one of the 1,315 map extents parses as a container with three or four
members; every one of the 38 `E.DAT` extents parses as a container with two
to twenty-one.

## Where the table region sits

```
0x80192E44   file registry, 26 entries of 16 bytes, -1 terminated
0x80192FF4   258 XA clip ranges
0x80193804   V.DAT   1349 x 8
0x8019622C   M.DAT   1315 x 8
0x80198B44   E.DAT     38 x 8
0x80198C74   S.DAT     94 x 8
0x80198F64   two stray one-entry tables
0x8019923C   B.DAT    339 x 8
```

The four in the middle are literally contiguous — `0x80193804` +
1349×8 = `0x8019622C`, and so on — so they were emitted by one generator in
one pass. `B.DAT`'s table sits apart, past a small region of `u16` pair data,
which fits with `B.DAT` also being the one archive that uses the other
container variant.

## The file registry

The 26-entry table at `0x80192E44` is how an id becomes a path. Each record is
`{u32 id, char *name, u32, u32}`; the last two words are zero on disc and are
filled at run time with what `CdSearchFile` returns.

The loader at `0x80150324` turns the id into a filename:

```
1000 <= id < 1100   ->  sprintf("\PIC\%s.D;1", name)
1100 <= id < 1300   ->  sprintf("\DAT\%s;1",   name)
otherwise           ->  the name is used as-is
```

| id | name | | id | name |
|---|---|---|---|---|
| 0 | `\DAT\B.DAT;1` | | 1250 | `INI.D` |
| 1000 | `MC` | | 1251 | `DBG.D` |
| 1001 | `I` | | 1300 | `\DAT\E.DAT;1` |
| 1002 | `FACE` | | 1400 | `\DAT\S.DAT;1` |
| 1003 | `FACE2` | | 1500 | `\DAT\V.DAT;1` |
| 1005 | `RC` | | 1600 | `\XA\T.XA;1` |
| 1006 | `WM` | | 1650 | `\XA\S.XA;1` |
| 1007 | `BF` | | 1700 | `\DAT\M.DAT;1` |
| 1100 | `TALE.VB` | | 1800–1805 | the six `.STR` movies |
| 1101 | `BVB.D` | | | |
| 1200 | `KAISEN.BIN` | | | |
| 1201 | `TKM.BIN` | | | |

Every file on the disc is here except `SYSTEM.CNF`, the executable itself and
the `DUMMY3M.DA` pad. **Id 1004 is missing** — an eighth `PIC` slot that was
dropped; see [10](10-leftovers.md).

## Reading it yourself

```sh
python tools/tod_index.py  iso/SLPS_011.00                # coverage of all five
python tools/tod_index.py  iso/SLPS_011.00 --table M.DAT   # every extent, with its map id
python tools/exe_tables.py iso/SLPS_011.00 --registry
python tools/tod_arc.py    iso/PIC/I.D                     # a table that goes backwards
python tools/tod_arc.py    iso/DAT/E.DAT --recurse
```
