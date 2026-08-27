# 04 — The block codec

**Status: verified.** A reimplementation in
[`tools/tod_codec.py`](../tools/tod_codec.py) reproduces the declared output
length for **6,638 of 6,638** packed blocks on the disc, with no exceptions
and no tolerance. The dictionary model, which lengths alone cannot test, is
supported by a negative control at the end of this document.

Original: three routines plus a dispatcher, `0x80150BB0` – `0x80151004` and
`0x8015160C`, in `SLPS_011.00`. Full listing in
[`reports/exe-map.txt`](../reports/exe-map.txt).

> This document covers **this build's** implementation: its addresses, its
> dispatcher, its dictionary and its verification. The format itself — which
> this game shares with the 1995 Super Famicom *Tales of Phantasia* — is
> documented once, with a decoder for both dialects, at
> [tales-blockcodec-doc](https://github.com/vs-sr-dev/tales-blockcodec-doc).
> See [11](11-tales-lineage.md) for what the two have in common.

## Block header

Every packed block on the disc starts with the same nine bytes.

| Offset | Size | Field |
|---|---|---|
| `+0` | u8 | method: `0` stored, `1` LZSS, `3` LZSS + run escape |
| `+1` | u32 | packed size — the number of stream bytes that follow the header |
| `+5` | u32 | unpacked size |
| `+9` | — | stream begins |

The dispatcher at `0x80150F58` reads the packed size a byte at a time — the
header is not guaranteed to be aligned, because a container can place a member
at any offset — and branches on `+0`:

```
80150F68  lbu v0, 2(a3)         ; packed size, assembled from four
80150F6C  lbu a0, 1(a3)         ; unaligned byte loads
80150F70  lbu v1, 3(a3)
80150F84  lbu v0, 4(a3)
80150F88  lbu v1, 0(a3)         ; the method
80150F90  bne v1, zero, 0x80150FA8
80150F98  jal 0x8015160C        ; method 0
80150FAC  bne v1, v0(=1), ...
80150FC4  jal 0x80150BB0        ; method 1, with a3 = sp+16, the ring
80150FD4  bne v1, v0(=3), ...   ; anything else returns -1
80150FEC  jal 0x80150D4C        ; method 3
```

The stack frame is 4,144 bytes: 4,096 of ring dictionary at `sp+16`, the
return address at `sp+4136`. The ring is rebuilt from scratch on every call.

Both compressed methods are driven **only** by the packed size; the loop
condition is `source < source + packed`. The unpacked size at `+5` is never
read by either. It is metadata written by the packer — and on this disc it is
correct every time, which is why it can be used to check the decoder.

## The ring dictionary

Classic LZSS with a 4,096-byte ring, but the ring does not start empty. Both
`0x80150BB0` and `0x80150D4C` open with the same three loops:

```
  ring[0 .. r-1]     = 0                       ; r is the start cursor
  for i in 0..255:  ring[8i    .. 8i+7]    = i, 0,   i, 0,   i, 0,   i, 0
  for i in 0..255:  ring[2048+7i .. +6]    = i, 255, i, 255, i, 255, i
```

which fills `0x0000`–`0x07FF` with `(i, 0x00)` pairs and `0x0800`–`0x0EFF`
with `(i, 0xFF)` pairs, 3,840 bytes in all. `0x0F00` up to the cursor is
zeroed; the cursor and everything above it is left holding whatever was on the
stack.

The point of the preload is what the game compresses. A 4bpp tile row where
one nibble is a colour and the other is zero looks exactly like `(i, 0x00)`; a
16-bit table of small values padded with `0xFF` looks exactly like
`(i, 0xFF)`. Those two patterns are in the dictionary before the first token
is read, so the packer can emit a back-reference for them instead of spending
literals. It is 3,840 bytes of guess about what the data will look like, and
the disc says the guess was right often enough to keep.

The write cursor starts at `RING - F`, where `F` is the longest match the
variant can encode:

| Method | Cleared | Cursor start | Undefined bytes |
|---|---|---|---|
| 1 | `0` – `4077` | **4078** | 4078 – 4095 (18) |
| 3 | `0` – `4078` | **4079** | 4079 – 4095 (17) |

That difference is not arbitrary: method 1's longest match is 18 bytes and
method 3's is 17, because method 3 spends the all-ones length code on its
run escape. `r = N − F` is the textbook LZSS initialisation, and both
routines follow it.

## The token stream

Byte-aligned, identical for methods 1 and 3.

A control byte is fetched whenever the shift register runs dry, and its bits
are consumed **least-significant first**. The register is 16 bits wide and is
refilled as `flags = byte | 0xFF00`, so the eight `1` bits in the high half
act as a counter: after eight shifts bit 8 goes clear and the next byte is
fetched.

```
80150E24  srl  v0, t5, 1
80150E2C  andi v0, v0, 0x0100      ; still have bits?
80150E38  lbu  v0, 0(a1)
80150E40  ori  t5, v0, 0xFF00      ; refill
```

| Control bit | Meaning |
|---|---|
| `1` | copy one literal byte |
| `0` | a two-byte token follows |

The token is:

```
b0 = offset & 0xFF
b1 = ((offset >> 8) << 4) | (length - 3)

offset = b0 | ((b1 & 0xF0) << 4)      12 bits, an absolute index into the ring
length = (b1 & 0x0F) + 3              3..18 (method 1), 3..17 (method 3)
```

Note that the offset is an **absolute ring index**, not a distance backwards
from the cursor. Bytes are copied one at a time from `ring[(offset + k) & 0xFFF]`
to the output *and* back into `ring[cursor]`, so a match may legitimately
overlap the cursor and read bytes it has just written — the usual LZSS
self-referential run.

## The run escape (method 3)

Method 3 reserves the length code `0x0F`, which in method 1 would mean a
match of 18 bytes.

```
b1 & 0x0F == 0x0F  and  b1 & 0xF0 != 0   ->  emit b0 (b1>>4) + 3 times   2-byte token,   4..18 bytes
b1 & 0x0F == 0x0F  and  b1 & 0xF0 == 0   ->  emit b2, b0 + 19 times      3-byte token,  19..274 bytes
```

The two forms are contiguous with no redundant encoding: short runs cover
4–18, long runs 19–274. The escape writes into the ring as well as the output,
so a run remains addressable by later matches.

```
80150EEC  andi t0, t1, 0xFFFF      ; the offset field
80150EF0  sltiu v0, t0, 256        ; high nibble zero?
80150EF8  addiu t1, t3, 18         ; long form: count-1 = offset + 18
80150EFC  lbu  v1, 0(a1)           ;            the byte comes from the stream
80150F08  andi v1, t3, 0x00FF      ; short form: the byte is the offset's low half
80150F0C  srl  v0, t0, 8
80150F10  addiu t1, v0, 2          ;            count-1 = high nibble + 2
```

The `+3` and `+19` are not tuning constants chosen for this game. They are the
same two constants, in the same two roles, as in the Super Famicom
*Tales of Phantasia* codec — see [11](11-tales-lineage.md).

## Method 0 — the stored path that never runs

`0x8015160C` is a plain byte copy: `copy(a0, a1, a2)`. The dispatcher reaches
it with `a0` = destination, `a2` = the **packed** size, and `a1` still holding
the pointer it was given — which points at the block *header*, not at the
stream at `+9`. So the stored path, as wired, would emit the nine header bytes
followed by `packed − 9` bytes of payload.

It is never exercised. Across all 6,638 blocks the disc contains, the method
byte is `1` on 157 of them and `3` on 6,481; **no block on this disc has
method 0**. The path exists because the format it inherited had one
([11](11-tales-lineage.md)), and the wiring was never tested because the
packer never emits it.

`tools/tod_codec.py` copies from `+9` by default and will reproduce the game's
actual behaviour with `unpack(..., faithful=True)`.

## Verification

[`tools/verify.py`](../tools/verify.py) walks every extent of every archive,
every container inside it and every block inside that, decodes the block and
compares the length produced against the length the block's own header
declares. Output: [`reports/verify.txt`](../reports/verify.txt).

| | |
|---|---|
| Containers walked | 5,983, nested at most two deep |
| Packed blocks | 6,638 — method 1: 157, method 3: 6,481, method 0: 0 |
| Raw members | 44,512 |
| Packed bytes | 148,665,346 |
| Unpacked bytes | 464,839,924 |
| Ratio | 3.13× |
| **Length disagreements** | **0** |

Never short, never long, no tolerance needed anywhere. That is a stronger
result than the Super Famicom codec gives on its own cartridge, where 21 of 74
blocks overshoot the declared size by one byte.

### The negative control

Block lengths cannot tell a right dictionary from a wrong one: a
back-reference copies the same number of bytes either way, so a decoder with
a garbage ring still hits the declared size. What *can* tell them apart is
whether the bytes that come out are still a TIM or a container.

Decoding all 147 method-1 blocks in `M.DAT`, `E.DAT` and `B.DAT` four times —
once with the model, once with each nearby wrong guess
(`tools/verify.py --control`):

| Dictionary | Cursor | Blocks that decode to a TIM or a container |
|---|---|---|
| **preloaded** | **4078** | **25** (15 TIM, 10 container) |
| preloaded | 4079 | 11 (11 TIM, 0 container) |
| zeroed | 4078 | 18 (8 TIM, 10 container) |
| zeroed | 4079 | 4 (4 TIM, 0 container) |

The model is strictly better than every perturbation of it, on both axes
independently. Method 3, which dominates the corpus, is checked far more
strongly than this: 6,481 of its blocks decode into structures — containers,
TIMs, VAB headers whose declared body size matches a file on the disc to the
byte ([07](07-audio.md)) — that a wrong dictionary could not produce.

## Trying it

```sh
python tools/tod_codec.py iso/PIC/MC.D -o mc.bin          # one block
python tools/tod_arc.py   iso/DAT/E.DAT --recurse         # a whole archive
python tools/verify.py    iso/SLPS_011.00 iso/DAT iso/PIC
python tools/verify.py    iso/SLPS_011.00 iso/DAT --control
python tools/dismips.py   iso/SLPS_011.00 0x80150D4C 84   # method 3 in full
```
