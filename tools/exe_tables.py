"""Dump the tables the game keeps inside SLPS_011.00.

Tales of Destiny puts almost all of its metadata in the executable rather than
on the disc: the file registry, the extent tables for the five bulk archives,
the map ID array, the XA clip ranges, the font's character inventories and the
sound-test name list are all compiled-in arrays.  This tool prints them.

    python tools/exe_tables.py EXE [--registry] [--fonts] [--soundtest]
                                   [--xa] [--vab] [--blocks]

With no selector it prints everything.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tod_arc
import tod_codec
import tod_index
from dismips import Exe

REGISTRY = 0x80192E44        # {u32 id, char *name, u32 lba, u32 flags} x N, -1 terminated
SOUND_NAMES = 0x8018CFC8     # 174 char* — the sound test list
PUNCT_MAP = 0x801807FC       # 39 x {u16 Shift-JIS, u16 internal code}
TECH_KANJI = 0x8018089C      # Shift-JIS codes of the technique-name font
VAB_ARCHIVE = 0x80180944     # container of 17 packed VAB headers


def cstr(exe, va):
    if not exe.contains(va):
        return '<0x%08X>' % va
    o = va - exe.taddr
    return exe.text[o:exe.text.find(b'\0', o)].decode('latin1')


def rd(exe, va, n):
    o = va - exe.taddr
    return exe.text[o:o + n]


def registry(exe):
    print('== file registry, 0x%08X ==' % REGISTRY)
    print('   the loader turns an id into a path: 1000-1099 become \\PIC\\%s.D;1,')
    print('   1100-1299 become \\DAT\\%s;1, everything else is used literally.')
    print('   %-6s %-22s %s' % ('id', 'name', 'record'))
    i = 0
    while True:
        w = struct.unpack_from('<4I', rd(exe, REGISTRY + i * 16, 16))
        if w[0] == 0xFFFFFFFF:
            print('   -1     (end)')
            break
        print('   %-6d %-22s 0x%08X 0x%08X 0x%08X'
              % (w[0], cstr(exe, w[1]), w[1], w[2], w[3]))
        i += 1
        if i > 64:
            break
    print()


def fonts(exe):
    print('== Shift-JIS to internal code map, 0x%08X ==' % PUNCT_MAP)
    print('   39 entries.  Full-width punctuation folds onto the single-byte')
    print('   JIS X 0201 codes the text engine actually stores.')
    b = rd(exe, PUNCT_MAP, 39 * 4)
    row = []
    for i in range(39):
        sj, code = struct.unpack_from('<HH', b, i * 4)
        ch = bytes((sj >> 8, sj & 0xFF)).decode('shift_jis', 'replace')
        row.append('%04X %s -> %02X' % (sj, ch, code))
        if len(row) == 4:
            print('   ' + '   '.join(row))
            row = []
    if row:
        print('   ' + '   '.join(row))
    print()

    print('== technique-name kanji inventory, 0x%08X ==' % TECH_KANJI)
    o = TECH_KANJI - exe.taddr
    t = exe.text
    codes = bytearray()
    while o + 2 <= len(t):
        hi, lo = t[o], t[o + 1]
        if not ((0x81 <= hi <= 0x9F or 0xE0 <= hi <= 0xEA)
                and 0x40 <= lo <= 0xFC and lo != 0x7F):
            break
        codes += bytes((hi, lo))
        o += 2
    s = codes.decode('shift_jis')
    print('   %d glyphs, ending at 0x%08X' % (len(s), exe.taddr + o))
    for i in range(0, len(s), 40):
        print('   ' + s[i:i + 40])
    print()


def soundtest(exe):
    print('== sound test name list, 0x%08X ==' % SOUND_NAMES)
    ptrs = struct.unpack_from('<174I', rd(exe, SOUND_NAMES, 174 * 4))
    for i, p in enumerate(ptrs):
        print('   %3d  %s' % (i, cstr(exe, p)))
    print()


def xa(exe):
    print('== XA clip ranges, 0x%08X ==' % tod_index.XA_RANGES)
    print('   258 (first sector, last sector) pairs into \\XA\\T.XA;1, which is')
    print('   an eight-channel interleave; one entry is one scene\'s dialogue.')
    r = tod_index.xa_ranges(exe, 258)
    for i, (a, b) in enumerate(r):
        print('   %3d  %6d .. %6d   %5d sectors   %6d per channel'
              % (i, a, b, b - a, (b - a) // 8))
    print()


def vab(exe):
    print('== packed VAB headers, 0x%08X ==' % VAB_ARCHIVE)
    t = exe.text
    o = VAB_ARCHIVE - exe.taddr
    c = tod_arc.parse(t, o, len(t) - o)
    print('   container %s, %d members' % (c[0], len(c[1])))
    last = o + c[1][-1]
    end = last + 9 + struct.unpack_from('<I', t, last + 1)[0]
    for i, s, e in tod_arc.members(t, o, end - o):
        d = tod_codec.unpack(t, s)
        form = d[:4].decode('latin1')
        ver, vid, fsize = struct.unpack_from('<III', d, 4)
        ps, ts, vs = struct.unpack_from('<HHH', d, 18)
        want = 32 + 2048 + ps * 16 * 32 + 512
        print('   [%2d] +%-6d %s ver %d id %d  header %d bytes (%s)  '
              'total %s  %d programs, %d tones, %d waveforms  -> BVB.D body %s'
              % (i, s - o, form, ver, vid, len(d),
                 'as laid out' if want == len(d) else 'expected %d' % want,
                 format(fsize, ','), ps, ts, vs, format(fsize - len(d), ',')))
    print()


def blocks(exe):
    print('== packed blocks embedded in the executable ==')
    t = exe.text
    n = 0
    for o in range(0, len(t) - 9, 4):
        if t[o] not in (1, 3):
            continue
        p, u = struct.unpack_from('<II', t, o + 1)
        if not (16 <= p < len(t) - o - 9 and 64 <= u < 0x400000 and u > p):
            continue
        try:
            out = tod_codec.unpack(t, o)
        except Exception:
            continue
        if len(out) != u:
            continue
        head = ' '.join('%02X' % x for x in out[:8])
        print('   0x%08X  method %d  %7d -> %7d   %s' % (exe.taddr + o, t[o], p, u, head))
        n += 1
    print('   %d candidates (a brute-force scan; the seventeen at 0x8018098C'
          % n)
    print('   onwards are the real ones, the rest are code that happens to')
    print('   decode to a self-consistent length)')
    print()


def main(argv):
    exe = Exe(argv[0])
    sel = [a for a in argv[1:] if a.startswith('--')]
    all_ = not sel
    if all_ or '--registry' in sel:
        registry(exe)
    if all_ or '--extents' in sel:
        tod_index.main([argv[0]])
        print()
    if all_ or '--fonts' in sel:
        fonts(exe)
    if all_ or '--soundtest' in sel:
        soundtest(exe)
    if all_ or '--xa' in sel:
        xa(exe)
    if all_ or '--vab' in sel:
        vab(exe)
    if '--blocks' in sel:
        blocks(exe)


if __name__ == '__main__':
    main(sys.argv[1:])
