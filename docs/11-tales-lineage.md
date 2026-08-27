# 11 — The Tales lineage

**Status: verified** for the format comparison, which is a byte-level match of
two independently reverse-engineered specifications; **open** for anything
about shared source code, which nothing here can establish.

*Tales of Phantasia* shipped on the Super Famicom in December 1995.
*Tales of Destiny* shipped on the PlayStation in December 1997, two years
later, on different hardware, with a different CPU, a different display
pipeline and a different sound chip. Almost nothing survives such a move.

One thing did.

## The block header is the same nine bytes

| | *Phantasia*, SNES (1995) | *Destiny*, PS1 (1997) |
|---|---|---|
| `+0` | u8 type | u8 method |
| `+1` | u32 packed size | u32 packed size |
| `+5` | u32 unpacked size | u32 unpacked size |
| `+9` | payload | payload |
| type: plain LZSS | `$81` | `1` |
| type: LZSS + run escape | `$83` | `3` |
| type: stored | anything else | `0` |
| driven by | packed size only | packed size only |
| `+5` used on the compressed path | no | no |

Same layout, same field widths, same offsets, and the method numbers agree in
their low bits — `$81` and `1`, `$83` and `3`. The Super Famicom values carry
bit 7 set; the PlayStation values do not.

## The token grammar is the same

| | *Phantasia* | *Destiny* |
|---|---|---|
| Window | 4,096 bytes | 4,096 bytes |
| Control bits | LSB first | LSB first |
| Bit `1` | literal | literal |
| Bit `0` | two-byte back-reference | two-byte back-reference |
| Match length | 3–18 | 3–18 (method 1), 3–17 (method 3) |
| Offset | 12 bits, **distance backwards** | 12 bits, **absolute ring index** |
| Length field | high nibble of `b1` | low nibble of `b1` |

The two differences are exactly what a port to a byte-addressable machine with
a 4 KiB scratch buffer would produce. The 65816 version copies backwards
inside the destination buffer, because on a Super Famicom the destination is a
32 KiB WRAM buffer and the `MVN` block-move instruction can address it
directly. The MIPS version keeps a real ring dictionary on the stack, which is
what you do when the destination might be anywhere in a 2 MB address space.
The nibble swap is free either way.

## The run escape is the same arithmetic

This is the part that settles it. Both formats reserve the all-ones length
code and spend it on two run forms:

| | *Phantasia* `$83` | *Destiny* method 3 |
|---|---|---|
| Escape condition | `b1 >= $F0` | `b1 & 0x0F == 0x0F` |
| Short form | `b1 = $Fn, n != 0` → emit `b0`, **n + 3** times | high nibble `n != 0` → emit `b0`, **n + 3** times |
| Short range | **4 – 18** | **4 – 18** |
| Long form | `b1 = $F0` → read `b2`, emit it **b0 + 19** times | high nibble `0` → read `b2`, emit it **b0 + 19** times |
| Long range | **19 – 274** | **19 – 274** |
| Token sizes | 2 bytes / 3 bytes | 2 bytes / 3 bytes |

`+3` and `+19`. Both constants, in both roles, in both ranges, on both
machines. On the Super Famicom those numbers are an artefact of the `MVN`
instruction, which moves `A + 1` bytes and is used to propagate a fill byte
from `X` to `X+1` — so the register always holds two less than the count. The
PlayStation code has no `MVN` and no reason to be off by two, and it is off by
two anyway.

A compressor written from scratch for MIPS in 1997 would not choose 19 as the
base of its long run length. It chose 19 because the packer that produced the
data was the same packer, and the decoder was written to match it.

## What is different

| | *Phantasia*, SNES | *Destiny*, PS1 |
|---|---|---|
| Ring dictionary | none — reads the output buffer | 4,096 bytes, rebuilt per call |
| Dictionary preload | n/a | **3,840 bytes of synthetic `(i,0)` / `(i,255)` pairs** |
| Cursor start | n/a | `4096 − F`, i.e. 4078 or 4079 |
| Decoder size | 457 bytes of 65816, four near-identical loops | 1,164 bytes of MIPS in three routines plus a dispatcher |
| Stored path | reads `+5`, copies from `+9`, used on 3 blocks | wired wrong, used on 0 blocks |
| Blocks in the game | 1,089 found by scan | 6,638 found by index |
| Exact-length decodes | 53 of 74; 21 overshoot by one byte | **6,638 of 6,638** |

The preloaded dictionary is the genuine addition. It is a 3,840-byte guess
about what the data will look like — alternating `(value, 0x00)` and
`(value, 0xFF)` pairs, which is what 4bpp tile rows and padded 16-bit tables
look like — installed before the first token is read so the packer can
back-reference them for free. There is nothing like it in the 1995 decoder.

The stored path is the counter-example that proves the direction of travel.
*Phantasia* uses it on three blocks and it works. *Destiny* inherits it,
mis-wires it, and never notices, because its packer stopped emitting stored
blocks.

## The same structural instinct, twice

Beyond the codec, the two games make the same architectural choice about where
asset addressing lives.

*Phantasia*, on a cartridge with no file system, puts literal `bank:offset`
immediates at 99 call sites and backs them with four sparse three-byte
directories covering 147 of its 1,089 blocks. The ROM is a flat address space
held together by constants in code.

*Destiny*, on a disc with a perfectly good ISO 9660 file system available,
uses it for **29 files** and then puts the real directory — 3,135 eight-byte
extent records across five tables — inside the executable
([05](05-containers-and-index.md)). `M.DAT` is 131 MB with no internal
structure of any kind; every one of its 1,315 divisions exists only as an
array at `0x8019622C`.

Two years and two platforms apart, both teams reached for the same answer: the
asset directory is part of the program, not part of the data.

## What this does not show

Nothing here demonstrates shared source code. The 65816 and MIPS decoders are
different programs; only the *format* is the same, and a format can travel as a
specification, a packing tool, or one programmer's memory. The most economical
reading is that the packer — the tool on the PC side that produced the blocks
— was carried forward and the decoder rewritten to match it, which is the
usual way a compression format outlives its hardware.

*Phantasia*'s Super Famicom engine is credited to Yoshiharu Gotanda, who left
Wolf Team with Masaki Norimoto and Hiroya Hatsushiba to found tri-Ace
immediately after it shipped. *Destiny* came out of what remained of the same
studio two years later. Whatever else changed in between, the compressor did
not.

## Sources

The *Phantasia* side of this comparison is documented in the companion
repository for the Super Famicom and Game Boy Advance builds, and its numbers
are quoted here rather than re-derived. The *Destiny* side is
[04](04-block-codec.md) and [`reports/verify.txt`](../reports/verify.txt).
