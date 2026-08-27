"""Where the game puts things in video memory.

The disc stores no texture atlas and no placement metadata: every bitmap is a
TIM, and a TIM carries its own destination in the PlayStation's 1024x512
16-bit frame buffer.  So the whole VRAM budget of the game can be recovered by
decoding every block on the disc, reading the coordinates out of every TIM and
counting how often each 64x16 cell is written.

    python tools/vram_map.py EXE DATDIR PICDIR [--csv OUT]

Prints a coarse occupancy map — one character per 64x16 cell, shaded by how
many 16-bit words all the disc's images together write there — plus the list
of distinct rectangles sorted by how many images claim them.

The map is a union over the whole disc, not a snapshot: only one map, one
battle or one menu is resident at a time.
"""

import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tim
import tod_arc
import tod_codec
import tod_index
from dismips import Exe

CW, CH = 64, 16                      # cell size of the printed map
COLS, ROWS = 1024 // CW, 512 // CH


def collect(buf, out, depth=0):
    p = tod_arc.parse(buf, 0, len(buf))
    if p is None:
        info, _ = tim.parse(buf, 0)
        if info:
            note(info, out)
        return
    for i, s, e in tod_arc.members(buf, 0, len(buf)):
        if e <= s:
            continue
        k = tod_arc.kind(buf, s, e)
        if k.startswith('block'):
            try:
                d = tod_codec.unpack(buf, s)
            except Exception:
                continue
            if depth < 3:
                collect(d, out, depth + 1)
        elif k.startswith('container') and depth < 3:
            collect(buf[s:e], out, depth + 1)
        else:
            info, _ = tim.parse(buf, s)
            if info:
                note(info, out)


def note(info, out):
    for slot in ('pixels', 'clut'):
        b = info.get(slot)
        if b:
            out[(b['x'], b['y'], b['w'], b['h'], slot)] += 1


def main(argv):
    exe = Exe(argv[0])
    datdir, picdir = argv[1], argv[2]
    rects = Counter()

    for fn in sorted(os.listdir(picdir)):
        collect(open(os.path.join(picdir, fn), 'rb').read(), rects)

    for name in ('E.DAT', 'M.DAT', 'B.DAT', 'V.DAT'):
        path = os.path.join(datdir, name)
        if not os.path.exists(path):
            continue
        fh = open(path, 'rb')
        for off, sz in tod_index.extents(exe, name):
            fh.seek(off)
            collect(fh.read(sz), rects)
        fh.close()
        print('%s done, %d distinct rectangles so far' % (name, len(rects)),
              file=sys.stderr)

    grid = [[0] * COLS for _ in range(ROWS)]
    for (x, y, w, h, slot), n in rects.items():
        px = w * 1          # w is already in 16-bit units, which is what VRAM counts
        for yy in range(y, min(512, y + h)):
            for xx in range(x, min(1024, x + px)):
                grid[yy // CH][xx // CW] += n

    print('VRAM occupancy, one cell = %dx%d pixels of the 1024x512 frame buffer.'
          % (CW, CH))
    print('Shade is the log of how many 16-bit words every image on the disc')
    print('together writes into that cell; blank means no image ever does.')
    print('    ' + ''.join('%-4d' % (c * CW) for c in range(0, COLS, 4)))
    ramp = ' .:-=+*#%@'
    for r in range(ROWS):
        row = ''
        for c in range(COLS):
            v = grid[r][c]
            row += ' ' if v == 0 else ramp[min(9, 1 + int(v ** 0.25))]
        print('%3d %s' % (r * CH, row))
    print()
    print('%d distinct rectangles, %d image writes'
          % (len(rects), sum(rects.values())))
    print('%-28s %8s  %s' % ('rectangle', 'writes', 'kind'))
    for (x, y, w, h, slot), n in rects.most_common(40):
        print('(%4d,%3d) %3d x %3d words %8d  %s' % (x, y, w, h, n, slot))

    if '--csv' in argv:
        with open(argv[argv.index('--csv') + 1], 'w') as fh:
            fh.write('x,y,w_words,h,slot,writes\n')
            for (x, y, w, h, slot), n in sorted(rects.items()):
                fh.write('%d,%d,%d,%d,%s,%d\n' % (x, y, w, h, slot, n))


if __name__ == '__main__':
    main(sys.argv[1:])
