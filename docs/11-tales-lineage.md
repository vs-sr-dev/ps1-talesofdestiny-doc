# 11 — The Tales lineage

**Status: verified** for the format comparison; **open** for anything about
shared source code, which nothing here can establish.

> The codec itself is documented title-agnostically, with a reference decoder
> that handles both dialects, at
> **[tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc)**.
> That repository is the single copy of the specification; this document
> records what the comparison means *for this disc* and does not restate the
> format.

*Tales of Phantasia* shipped on the Super Famicom in December 1995.
*Tales of Destiny* shipped on the PlayStation in December 1997, two years
later, on different hardware, with a different CPU, a different display
pipeline and a different sound chip. Almost nothing survives such a move.

The compressor did.

## What matches

| | *Phantasia*, SNES 1995 | *Destiny*, PS1 1997 |
|---|---|---|
| Block header | `u8 method, u32 packed, u32 unpacked` | **identical** |
| Method: LZSS | `$81` | `1` |
| Method: LZSS + run escape | `$83` | `3` |
| Window | 4,096 bytes | 4,096 bytes |
| Control bits | LSB first, `1` = literal | **identical** |
| Match length | 3-18 | 3-18 |
| Short run | `n + 3`, **4-18**, two-byte token | **identical** |
| Long run | `b0 + 19`, **19-274**, three-byte token | **identical** |
| Driven by | packed size only | packed size only |

The two constants are the tell. On the Super Famicom, `+3` and `+19` fall out
of `MVN`, the block-move instruction that transfers `A + 1` bytes and is used
to propagate a fill byte from `X` to `X+1` — so the register always holds two
less than the count. The MIPS decoder at `0x80150D4C` has no `MVN`, writes its
fill with an ordinary store loop, and has no reason at all to be off by two.
It is off by two anyway.

A compressor written from scratch for MIPS in 1997 does not choose 19 as the
base of its long run length. It chooses 19 because the packer that produced
the data was the same packer.

## What this build changed

Two things, and one of them is real work.

**The nibble order is swapped.** *Phantasia* puts the length code in the high
nibble of the second token byte and the reference's top bits in the low
nibble; this build does the opposite. It costs nothing either way.

**The dictionary is new.** *Phantasia* has none — it addresses the output
buffer directly, because on a Super Famicom the destination is a 32 KiB WRAM
buffer that `MVN` can reach. This build keeps a real 4,096-byte ring on the
stack, because its destination may be anywhere in 2 MB, and **preloads 3,840
bytes of it** with synthetic `(i, 0x00)` and `(i, 0xFF)` pairs before reading
a single token ([04](04-block-codec.md)). That is a standing guess that the
data will be 4bpp tile rows and `0xFF`-padded tables, installed so the packer
can back-reference them for free. There is nothing like it in 1995.

**And the stored path was broken in transit.** *Phantasia* uses it on three
blocks and it works. This build inherits it, wires the source pointer to the
block header instead of the payload, and never notices — because its packer
had stopped emitting stored blocks ([10](10-leftovers.md)). The dead code is
the clearest evidence of direction: 1995 to 1997, not the other way.

## The boundary

The 2003 Game Boy Advance rebuild of *Phantasia* does **not** use this format.
It uses the platform's stock BIOS `LZ77UnComp` and `RLUnComp` throughout. Same
title, eight years later, and the codec did not travel with it.

So the format follows the team, not the series — which is why the shared
repository is scoped to the codec rather than to *Tales* as a whole.

## The same structural instinct, twice

Beyond the codec, the two games make the same architectural choice about where
asset addressing lives, and this one is not a shared tool — it is a shared
habit.

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
different programs; only the *format* is the same, and a format can travel as
a specification, a packing tool, or one programmer's memory. The most
economical reading is that the packer — the tool on the PC side that produced
the blocks — was carried forward and the decoder rewritten to match it, which
is the usual way a compression format outlives its hardware. The nibble swap
fits that reading: it is the sort of thing that changes when code is rewritten
from a description rather than ported line by line.

*Phantasia*'s Super Famicom engine is credited to Yoshiharu Gotanda, who left
Wolf Team with Masaki Norimoto and Hiroya Hatsushiba to found tri-Ace
immediately after it shipped. *Destiny* came out of what remained of the same
studio two years later. Whatever else changed in between, the compressor did
not.
