"""Exhaustive check of the container and codec model against the whole disc.

Walks every extent of every archive, every container inside it and every
packed block inside that, decodes each block and compares the length produced
against the length the block's own header declares.  Prints a census and a
list of every disagreement.

    python tools/verify.py EXE DATDIR [PICDIR] [--quick]

DATDIR is a directory holding B.DAT, E.DAT, M.DAT, S.DAT, V.DAT as extracted
from the disc image by tools/iso9660.py --extract.
"""

import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tod_arc
import tod_codec
import tod_index
from dismips import Exe

PAD = 2048          # the final member of an extent absorbs sector padding


def classify(buf, start, end, final):
    """'block'|'container'|'raw'.

    `final` is true only for the last member of a top-level extent, which is
    the one member allowed to carry the archive's sector padding.
    """
    if end <= start:
        return 'empty', None
    if end - start >= 9:
        m, p, u = tod_codec.header(buf, start)
        slack = end - start - 9 - p
        room = PAD if final else 3
        if m in (0, 1, 3) and p > 0 and 0 < u < (1 << 24) and 0 <= slack <= room:
            return 'block', (m, p, u)
    c = tod_arc.parse(buf, start, end - start)
    if c is not None:
        return 'container', c
    return 'raw', None


class Stats:
    def __init__(self):
        self.blocks = 0
        self.containers = 0
        self.raw = 0
        self.empty = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.methods = {}
        self.bad = []
        self.depth = 0


def scan(buf, base, size, st, where, depth=0, decode=True):
    c = tod_arc.parse(buf, base, size)
    if c is None:
        return
    st.containers += 1
    st.depth = max(st.depth, depth)
    _, offs = c
    n = len(offs)
    for i, s, e in tod_arc.members(buf, base, size):
        final = (i == n - 1 and depth == 0)
        k, info = classify(buf, s, e, final)
        tag = '%s[%d]' % (where, i)
        if k == 'empty':
            st.empty += 1
        elif k == 'block':
            m, p, u = info
            st.blocks += 1
            st.methods[m] = st.methods.get(m, 0) + 1
            st.bytes_in += p + 9
            st.bytes_out += u
            if decode:
                out = tod_codec.unpack(buf, s)
                if len(out) != u:
                    st.bad.append('%s: declared %d, produced %d' % (tag, u, len(out)))
                else:
                    scan(out, 0, len(out), st, tag + '/', depth + 1, decode)
        elif k == 'container':
            scan(buf, s, e, st, tag + '.', depth + 1, decode)
        else:
            st.raw += 1


def control(exe, datdir):
    """Negative control for the method-1 dictionary.

    Block lengths cannot distinguish a right dictionary from a wrong one: a
    back-reference copies the same number of bytes either way.  What can is
    whether the bytes that come out are still a TIM or a container.  Decode
    every method-1 block on the disc four times — with the model, and with
    each of the three nearby wrong guesses — and count.
    """
    import tim
    trials = [('preloaded ring, cursor 4078  (the model)', False, 4078),
              ('preloaded ring, cursor 4079', False, 4079),
              ('zeroed ring, cursor 4078', True, 4078),
              ('zeroed ring, cursor 4079', True, 4079)]
    real = tod_codec.preload_ring
    for label, zero, start in trials:
        tod_codec.preload_ring = (lambda m: bytearray(4096)) if zero else real
        tod_codec.START[1] = start
        kinds = {}
        for name in ('M.DAT', 'E.DAT', 'B.DAT'):
            path = os.path.join(datdir, name)
            if not os.path.exists(path):
                continue
            fh = open(path, 'rb')
            for off, sz in tod_index.extents(exe, name):
                fh.seek(off)
                d = fh.read(sz)
                for i, a, b in tod_arc.members(d, 0, sz):
                    if not tod_arc.kind(d, a, b).startswith('block m1'):
                        continue
                    out = tod_codec.unpack(d, a)
                    info, _ = tim.parse(out, 0)
                    c = tod_arc.parse(out, 0, len(out))
                    t = 'TIM' if info else ('container' if c else 'unrecognised')
                    kinds[t] = kinds.get(t, 0) + 1
            fh.close()
        ok = kinds.get('TIM', 0) + kinds.get('container', 0)
        print('%-42s %3d of %d method-1 blocks decode to a structure  %s'
              % (label, ok, sum(kinds.values()), kinds))
    tod_codec.preload_ring = real
    tod_codec.START[1] = 4078


def main(argv):
    exe = Exe(argv[0])
    datdir = argv[1]
    if '--control' in argv:
        control(exe, datdir)
        return
    picdir = argv[2] if len(argv) > 2 and not argv[2].startswith('-') else None
    decode = '--quick' not in argv
    st = Stats()
    t0 = time.time()

    for name, va, cnt, total in tod_index.TABLES:
        path = os.path.join(datdir, name)
        if not os.path.exists(path):
            print('%s missing, skipped' % name)
            continue
        fh = open(path, 'rb')
        ex = tod_index.extents(exe, name)
        before = st.blocks
        for i, (off, sz) in enumerate(ex):
            fh.seek(off)
            d = fh.read(sz)
            scan(d, 0, len(d), st, '%s/%d' % (name, i), 0, decode)
        fh.close()
        print('%-8s %5d extents   %7d blocks   %6.1fs'
              % (name, len(ex), st.blocks - before, time.time() - t0))

    if picdir:
        for fn in sorted(os.listdir(picdir)):
            d = open(os.path.join(picdir, fn), 'rb').read()
            if tod_arc.parse(d, 0, len(d)):
                scan(d, 0, len(d), st, 'PIC/' + fn, 0, decode)
            elif d[0] in (0, 1, 3):
                st.blocks += 1
                m, p, u = tod_codec.header(d)
                st.methods[m] = st.methods.get(m, 0) + 1
                st.bytes_in += p + 9
                st.bytes_out += u
                if decode and len(tod_codec.unpack(d)) != u:
                    st.bad.append('PIC/%s: length mismatch' % fn)
        print('PIC      %5d files' % len(os.listdir(picdir)))

    print()
    print('containers      %d (max nesting depth %d)' % (st.containers, st.depth))
    print('packed blocks   %d  %s'
          % (st.blocks, ', '.join('method %d: %d' % kv for kv in sorted(st.methods.items()))))
    print('empty members   %d' % st.empty)
    print('raw members     %d' % st.raw)
    print('packed bytes    %s' % format(st.bytes_in, ','))
    print('unpacked bytes  %s  (ratio %.2fx)'
          % (format(st.bytes_out, ','), st.bytes_out / max(1, st.bytes_in)))
    print('mismatches      %d' % len(st.bad))
    for b in st.bad[:40]:
        print('   ' + b)
    print('elapsed         %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main(sys.argv[1:])
