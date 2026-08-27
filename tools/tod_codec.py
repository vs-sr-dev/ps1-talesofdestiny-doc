"""The Tales of Destiny block codec.

Every packed block on the disc carries a nine-byte header:

    +0  u8   method      0 = stored, 1 = LZSS, 3 = LZSS + run escape
    +1  u32  packed      bytes of stream that follow the header
    +5  u32  unpacked    bytes the stream expands to

and is decoded by one dispatcher in the main executable at 0x80150F58, which
hands the stream to 0x8015160C (method 0), 0x80150BB0 (method 1) or
0x80150D4C (method 3).  All three share a 4096-byte ring dictionary that the
decoder builds from scratch on every call and that starts already populated —
see `preload_ring`.

Method 1 and method 3 build the same preloaded ring and use the same token
grammar.  They differ in two things: method 3 spends the all-ones length code
on a run escape, and so starts its cursor one byte lower; and method 0, the
stored path, is wired to the wrong source pointer and is never used.  See
docs/04-block-codec.md.
"""

import struct
import sys

RING = 4096

# The write cursor starts at RING minus the longest match the variant can
# encode: 18 bytes for method 1, 17 for method 3, which spends the all-ones
# length code on its run escape.  Classic LZSS r = N - F.
START = {0: RING - 18, 1: RING - 18, 3: RING - 17}


def preload_ring(method):
    """The dictionary as the decoder leaves it before reading the first token.

    Both compressed methods fill the low 3840 bytes with the same synthetic
    alternating table, so that runs of (value, 0x00) and (value, 0xFF) — which
    is what 4bpp tile data and padded tables look like — match immediately,
    without the encoder having to spend literals seeding them.  The remaining
    bytes below the cursor are cleared; the bytes at and above it are left as
    they were on the stack.
    """
    r = bytearray(RING)
    p = 0
    for i in range(256):                 # 0x0000-0x07FF : i,0,i,0,i,0,i,0
        r[p:p + 8] = bytes((i, 0, i, 0, i, 0, i, 0))
        p += 8
    for i in range(256):                 # 0x0800-0x0EFF : i,255,i,255,i,255,i
        r[p:p + 7] = bytes((i, 255, i, 255, i, 255, i))
        p += 7
    # 0x0F00 up to the cursor was explicitly zeroed by the loop at the head of
    # each routine; the cursor and everything above it is whatever the stack
    # happened to hold.  No block on the disc reads from there.
    return r


def unpack_stream(src, method, limit=None):
    """Decode one raw token stream (no header).  Returns bytes."""
    ring = preload_ring(method)
    pos = START.get(method, RING - 18)
    out = bytearray()
    i = 0
    n = len(src)
    flags = 0
    while i < n:
        flags >>= 1
        if not (flags & 0x0100):
            flags = src[i] | 0xFF00
            i += 1
            if i > n:
                break
        if flags & 1:                                   # literal
            c = src[i]; i += 1
            ring[pos] = c; pos = (pos + 1) & 0xFFF
            out.append(c)
            continue
        if i + 1 >= n:
            break
        lo = src[i]; hi = src[i + 1]; i += 2
        off = lo | ((hi & 0xF0) << 4)
        ln = (hi & 0x0F) + 2
        if ln < 17:                                     # back-reference
            for k in range(ln + 1):
                c = ring[(off + k) & 0xFFF]
                ring[pos] = c; pos = (pos + 1) & 0xFFF
                out.append(c)
        elif method == 3:                               # run escape
            if off < 256:
                c = src[i]; i += 1
                count = off + 19
            else:
                c = off & 0xFF
                count = (off >> 8) + 3
            for _ in range(count):
                ring[pos] = c; pos = (pos + 1) & 0xFFF
            out += bytes((c,)) * count
        else:                                           # method 1: plain match
            for k in range(ln + 1):
                c = ring[(off + k) & 0xFFF]
                ring[pos] = c; pos = (pos + 1) & 0xFFF
                out.append(c)
        if limit is not None and len(out) >= limit:
            break
    return bytes(out)


def header(buf, o=0):
    """(method, packed, unpacked) of the block at offset o."""
    method = buf[o]
    packed, unpacked = struct.unpack_from('<II', buf, o + 1)
    return method, packed, unpacked


def is_block(buf, o=0):
    if o + 9 > len(buf):
        return False
    m, p, u = header(buf, o)
    return m in (0, 1, 3) and 0 < p <= len(buf) - o - 9 + 1 and 0 < u < (1 << 24)


def unpack(buf, o=0, faithful=False):
    """Decode the packed block at offset o, header included.

    `faithful` reproduces what the game's method-0 path actually does — copy
    `packed` bytes from the *header*, not from the payload.  No block on the
    disc takes that path, so the default is the sane reading.
    """
    method, packed, unpacked = header(buf, o)
    if method == 0:
        if faithful:
            return buf[o:o + packed]
        return buf[o + 9:o + 9 + unpacked]
    body = buf[o + 9:o + 9 + packed]
    out = unpack_stream(body, method, unpacked)
    return out[:unpacked]


def main(argv):
    path = argv[0]
    buf = open(path, 'rb').read()
    off = int(argv[1], 0) if len(argv) > 1 and not argv[1].startswith('-') else 0
    m, p, u = header(buf, off)
    out = unpack(buf, off)
    sys.stderr.write('method %d  packed %d  unpacked %d  got %d  %s\n'
                     % (m, p, u, len(out), 'OK' if len(out) == u else 'SHORT'))
    if '-o' in argv:
        open(argv[argv.index('-o') + 1], 'wb').write(out)
    else:
        sys.stdout.buffer.write(out)


if __name__ == '__main__':
    main(sys.argv[1:])
