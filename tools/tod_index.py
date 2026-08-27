"""The extent tables, which live in the game executable rather than on the disc.

Five of the six bulk archives on the disc carry no directory of their own.
The directory is compiled into SLPS_011.00 as a run of eight-byte records

    u32  byte offset into the archive     (always a multiple of 2048)
    u32  byte length

sitting back to back in one 22 KiB region of the data segment.  The loader at
0x8014FAC4 indexes the table with the asset number, shifts the offset right by
11 to turn it into a sector, adds the archive's start LBA and issues one
CdlReadN.  Nothing on the disc says how M.DAT is divided; delete the
executable and 131 MB of the disc becomes unaddressable.

    table         entries  archive     bytes covered
    0x80193804      1349   V.DAT        22,157,312
    0x8019622C      1315   M.DAT       137,869,312
    0x80198B44        38   E.DAT         2,152,448
    0x80198C74        94   S.DAT         1,120,256
    0x8019923C       339   B.DAT         4,466,688

A sixth table at 0x80192FF4 holds 258 sector *ranges* rather than
offset/length pairs; see docs/06-audio.md.

Map extents are additionally named: a parallel array of 1315 u16 map IDs at
0x80186C74, terminated by 0xFFFF, is searched linearly by the map loader at
0x80107E80, which prints "Map No.%d(0x%04x) not found." when the ID is absent.

Usage:
    python tools/tod_index.py EXE                       # all tables
    python tools/tod_index.py EXE --table M.DAT         # one table
    python tools/tod_index.py EXE --extract M.DAT DIR --dat DIR_WITH_ARCHIVES
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dismips import Exe

TABLES = [
    ('V.DAT', 0x80193804, 1349, 22157312),
    ('M.DAT', 0x8019622C, 1315, 137869312),
    ('E.DAT', 0x80198B44, 38, 2152448),
    ('S.DAT', 0x80198C74, 94, 1120256),
    ('B.DAT', 0x8019923C, 339, 4466688),
]

MAP_IDS = 0x80186C74
XA_RANGES = 0x80192FF4


def read(exe, va, n):
    o = va - exe.taddr
    return exe.text[o:o + n]


def extents(exe, name):
    for nm, va, cnt, _ in TABLES:
        if nm == name:
            r = struct.unpack_from('<%dI' % (2 * cnt), read(exe, va, cnt * 8))
            return [(r[2 * i], r[2 * i + 1]) for i in range(cnt)]
    raise KeyError(name)


def map_ids(exe):
    out = []
    b = read(exe, MAP_IDS, 4096)
    for i in range(0, len(b), 2):
        v = struct.unpack_from('<H', b, i)[0]
        if v == 0xFFFF:
            break
        out.append(v)
    return out


def xa_ranges(exe, n=258):
    r = struct.unpack_from('<%dI' % (2 * n), read(exe, XA_RANGES, n * 8))
    return [(r[2 * i], r[2 * i + 1]) for i in range(n)]


def coverage(ex, total):
    iv = sorted((o, o + s) for o, s in ex)
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    cov = sum(b - a for a, b in merged)
    holes = []
    prev = 0
    for a, b in merged:
        if a > prev:
            holes.append((prev, a - prev))
        prev = b
    if prev < total:
        holes.append((prev, total - prev))
    return cov, holes


def main(argv):
    exe = Exe(argv[0])
    if '--extract' in argv:
        i = argv.index('--extract')
        name, outdir = argv[i + 1], argv[i + 2]
        datdir = argv[argv.index('--dat') + 1]
        os.makedirs(outdir, exist_ok=True)
        fh = open(os.path.join(datdir, name), 'rb')
        for n, (o, s) in enumerate(extents(exe, name)):
            fh.seek(o)
            open(os.path.join(outdir, '%04d.bin' % n), 'wb').write(fh.read(s))
        print('%d extents written' % len(extents(exe, name)))
        return

    want = argv[argv.index('--table') + 1] if '--table' in argv else None
    ids = map_ids(exe)
    for name, va, cnt, total in TABLES:
        if want and name != want:
            continue
        ex = extents(exe, name)
        cov, holes = coverage(ex, total)
        print('%s  table 0x%08X  %d entries' % (name, va, cnt))
        print('  archive %s bytes, %d referenced (%.2f%%), %d unreferenced region(s)'
              % (format(total, ','), cov, 100.0 * cov / total, len(holes)))
        dup = {}
        for o, s in ex:
            dup[(o, s)] = dup.get((o, s), 0) + 1
        shared = sum(v for v in dup.values() if v > 1)
        if shared:
            print('  %d entries share %d extents'
                  % (shared, len([1 for v in dup.values() if v > 1])))
        if want:
            for i, (o, s) in enumerate(ex):
                tag = '  id %04X' % ids[i] if name == 'M.DAT' and i < len(ids) else ''
                print('  [%4d] offset %10d  sector %8d  size %8d%s'
                      % (i, o, o >> 11, s, tag))
        print()
    if not want:
        print('map id array 0x%08X: %d ids, %d distinct'
              % (MAP_IDS, len(ids), len(set(ids))))
        groups = {}
        for v in ids:
            groups[v >> 8] = groups.get(v >> 8, 0) + 1
        print('  by high byte: %s'
              % ', '.join('%02X:%d' % kv for kv in sorted(groups.items())))


if __name__ == '__main__':
    main(sys.argv[1:])
