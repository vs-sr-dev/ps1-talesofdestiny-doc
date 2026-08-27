"""The Tales of Destiny container, in its two variants.

Variant A — counted:

    u32  count
    u32  offset[count]          offset[0] == 4 + 4*count

Variant B — self-sizing:

    u32  offset[n]              offset[0] == 4*n

Both are the same idea: a table of byte offsets from the head of the
container.  A container never records a member's length and never records a
member's type — a member's extent is inferred from the next offset, and its
type from its own first bytes.  Variant A spends four bytes on an explicit
count; variant B derives the count from its own first entry, which is also
the offset of member 0.  Variant B is what the battle archive B.DAT uses
throughout; everything else on the disc uses variant A.

The table is a list of pointers and is not required to be sorted.  PIC/I.D,
the 458-slot item icon table, points several slots at the same bytes to share
an icon between items, so its offsets go backwards in places.

Members are usually packed blocks (tod_codec), sometimes nested containers,
sometimes raw bytes.  Empty members (offset[i] == offset[i+1]) are common and
are how the format expresses a hole in an otherwise dense index.

Usage:
    python tools/tod_arc.py FILE [--at OFFSET --size N]
    python tools/tod_arc.py FILE --recurse
    python tools/tod_arc.py FILE --extract DIR
    python tools/tod_arc.py FILE --member N
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tod_codec

MAX_MEMBERS = 0x10000


def _valid(offs, size, head):
    """The table is a list of pointers, not necessarily a sorted one.

    Most containers on the disc are written in increasing order, so a member
    ends where the next one starts.  A few — PIC/I.D, the item icons — reuse
    an earlier member by pointing several slots at the same bytes, and the
    table then goes backwards.  Accept that, and let members() work out each
    member's end from the next larger offset in the table.
    """
    if offs[0] != head or head > size:
        return False
    for o in offs:
        if o < head or o > size:
            return False
    return True


def parse(buf, base=0, size=None):
    """(variant, offsets) for the container at base, or None.

    variant is 'A' or 'B'.
    """
    if size is None:
        size = len(buf) - base
    if size < 8 or base + 8 > len(buf):
        return None
    first = struct.unpack_from('<I', buf, base)[0]

    if 1 <= first <= MAX_MEMBERS and 4 + 4 * first <= min(size, len(buf) - base):
        offs = list(struct.unpack_from('<%dI' % first, buf, base + 4))
        if _valid(offs, size, 4 + 4 * first):
            return 'A', offs

    if first % 4 == 0 and 4 <= first <= 4 * MAX_MEMBERS and first <= min(size, len(buf) - base):
        n = first // 4
        offs = list(struct.unpack_from('<%dI' % n, buf, base))
        if _valid(offs, size, 4 * n):
            return 'B', offs

    return None


def members(buf, base=0, size=None):
    """Yield (index, start, end) absolute in buf."""
    if size is None:
        size = len(buf) - base
    p = parse(buf, base, size)
    if p is None:
        return
    _, offs = p
    ordered = sorted(set(offs)) + [size]
    for i, o in enumerate(offs):
        end = ordered[ordered.index(o) + 1]
        yield i, base + o, base + end


def kind(buf, start, end):
    if end <= start:
        return 'empty'
    if end - start >= 9:
        m, p, u = tod_codec.header(buf, start)
        if m in (0, 1, 3) and 0 < u < (1 << 24) and 9 <= 9 + p <= end - start <= 9 + p + 3:
            slack = end - start - 9 - p
            return 'block m%d %d->%d%s' % (m, p, u, ' +%d' % slack if slack else '')
    c = parse(buf, start, end - start)
    if c is not None:
        return 'container%s %d' % (c[0], len(c[1]))
    return 'raw'


def walk(buf, base, size, depth, path, out):
    for i, s, e in members(buf, base, size):
        k = kind(buf, s, e)
        out.append(('%s%d' % (path, i), s, e - s, k, depth))
        if k.startswith('container') and depth < 4:
            walk(buf, s, e - s, depth + 1, '%s%d.' % (path, i), out)


def main(argv):
    path = argv[0]
    buf = open(path, 'rb').read()
    base = int(argv[argv.index('--at') + 1], 0) if '--at' in argv else 0
    size = int(argv[argv.index('--size') + 1], 0) if '--size' in argv else len(buf) - base

    if '--member' in argv:
        n = int(argv[argv.index('--member') + 1], 0)
        for i, s, e in members(buf, base, size):
            if i == n:
                sys.stdout.buffer.write(buf[s:e])
                return
        sys.exit('no member %d' % n)

    if '--extract' in argv:
        d = argv[argv.index('--extract') + 1]
        os.makedirs(d, exist_ok=True)
        n = 0
        for i, s, e in members(buf, base, size):
            if e <= s:
                continue
            k = kind(buf, s, e)
            if k.startswith('block'):
                data, ext = tod_codec.unpack(buf, s), 'bin'
            else:
                data, ext = buf[s:e], 'raw'
            open(os.path.join(d, '%04d.%s' % (i, ext)), 'wb').write(data)
            n += 1
        print('%d members written to %s' % (n, d))
        return

    rows = []
    if '--recurse' in argv:
        walk(buf, base, size, 0, '', rows)
    else:
        for i, s, e in members(buf, base, size):
            rows.append((str(i), s, e - s, kind(buf, s, e), 0))
    if not rows:
        print('%s: not a container (%s)'
              % (os.path.basename(path), kind(buf, base, base + size)))
        return
    p = parse(buf, base, size)
    print('variant %s, %d members' % (p[0], len(p[1])))
    print('%-12s %10s %10s  %s' % ('member', 'offset', 'size', 'contents'))
    for name, s, sz, k, depth in rows:
        print('%-12s %10d %10d  %s%s' % (name, s, sz, '  ' * depth, k))
    print('%d entries' % len(rows))


if __name__ == '__main__':
    main(sys.argv[1:])
