"""Sony TIM / CLT reader.

Every bitmap on this disc is a stock Sony TIM.  The game keeps no texture
format of its own: a packed block is decoded straight into a buffer and the
result is handed to the GPU as-is, so a TIM's VRAM coordinates are the
addressing.

    u32  id       0x10 = TIM, 0x11 = CLT (a palette on its own)
    u32  flags    bits 0-2 pixel mode (0 = 4bpp, 1 = 8bpp, 2 = 16bpp,
                  3 = 24bpp, 4 = mixed), bit 3 = a CLUT block follows
    block:
        u32  bytes in this block, header included
        u16  VRAM x, u16 VRAM y
        u16  width in 16-bit units, u16 height
        ...  pixels

Usage:
    python tools/tim.py FILE [--png OUT.png] [--all]
"""

import os
import struct
import sys

MODE = {0: '4bpp', 1: '8bpp', 2: '16bpp', 3: '24bpp', 4: 'mixed'}


def parse(buf, off=0):
    """(info dict, end offset) for the TIM at off, or (None, off)."""
    if off + 8 > len(buf):
        return None, off
    ident, flags = struct.unpack_from('<II', buf, off)
    if ident not in (0x10, 0x11) or flags & ~0x0F:
        return None, off
    o = off + 8
    info = {'id': ident, 'flags': flags, 'mode': MODE.get(flags & 7, '?'),
            'clut': None, 'pixels': None, 'start': off}
    for slot in ('clut', 'pixels'):
        if slot == 'clut' and not (flags & 8) and ident == 0x10:
            continue
        if o + 12 > len(buf):
            return None, off
        n, x, y, w, h = struct.unpack_from('<IHHHH', buf, o)
        if n < 12 or o + n > len(buf) or n != 12 + w * h * 2:
            return None, off
        info[slot] = {'bytes': n, 'x': x, 'y': y, 'w': w, 'h': h, 'off': o + 12}
        o += n
        if ident == 0x11:
            break
    info['end'] = o
    return info, o


def describe(info):
    if info['id'] == 0x11:
        c = info['clut'] or info['pixels']
        return 'CLT   %3d colours at VRAM (%d,%d)' % (c['w'], c['x'], c['y'])
    p = info['pixels']
    px = {'4bpp': 4, '8bpp': 2, '16bpp': 1, '24bpp': 2 / 3.0}.get(info['mode'], 1)
    s = 'TIM   %-6s %4dx%-4d px  at VRAM (%d,%d) %dx%d words' % (
        info['mode'], int(p['w'] * px), p['h'], p['x'], p['y'], p['w'], p['h'])
    if info['clut']:
        c = info['clut']
        s += '   CLUT %dx%d at (%d,%d)' % (c['w'], c['h'], c['x'], c['y'])
    return s


def walk(buf):
    """Yield every TIM/CLT found back to back from offset 0."""
    o = 0
    while o < len(buf):
        info, nxt = parse(buf, o)
        if info is None:
            break
        yield info
        o = nxt


def main(argv):
    buf = open(argv[0], 'rb').read()
    n = 0
    for info in walk(buf):
        print('+%08X  %s' % (info['start'], describe(info)))
        n += 1
    if not n:
        print('no TIM at offset 0')
    else:
        print('%d image(s), %d of %d bytes consumed'
              % (n, info['end'], len(buf)))


if __name__ == '__main__':
    main(sys.argv[1:])
