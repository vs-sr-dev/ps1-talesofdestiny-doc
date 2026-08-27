"""Find the Japanese script in the map archive, and the development labels in it.

Each map extent's last member decodes to a container of nine to twelve
sub-members; the ones that are not TIMs hold the map's own data, and among
that is its dialogue, stored as plain Shift-JIS.  This walks every map, pulls
the strings out, and reports either a census or the entries that look like
labels the team left for itself — anything containing full-width Latin
letters, which Japanese prose does not use.

    python tools/script_scan.py EXE DATDIR [--labels] [--map N] [--census]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tim
import tod_arc
import tod_codec
import tod_index
from dismips import Exe

FW_UPPER = range(0x8260, 0x827A)      # Ａ-Ｚ
FW_LOWER = range(0x8281, 0x829B)      # ａ-ｚ
FW_DIGIT = range(0x824F, 0x8259)      # ０-９


def runs(b, minlen=3):
    out = []
    i = 0
    n = len(b)
    while i < n - 1:
        j = i
        k = 0
        while j < n - 1:
            hi, lo = b[j], b[j + 1]
            if (0x81 <= hi <= 0x9F or 0xE0 <= hi <= 0xEA) and 0x40 <= lo <= 0xFC and lo != 0x7F:
                j += 2
                k += 1
            else:
                break
        if k >= minlen:
            try:
                out.append((i, b[i:j].decode('shift_jis')))
            except UnicodeDecodeError:
                pass
            i = j
        else:
            i += 1
    return out


def has_fullwidth_latin(raw):
    for i in range(0, len(raw) - 1, 2):
        c = (raw[i] << 8) | raw[i + 1]
        if c in FW_UPPER or c in FW_LOWER:
            return True
    return False


def map_strings(d, sz):
    """Strings in the non-image members of one map extent."""
    ms = list(tod_arc.members(d, 0, sz))
    if not ms:
        return []
    # The last member of an extent carries the archive's sector padding, so
    # it will not pass the strict block test; check the header directly.
    last = ms[-1]
    m, p, u = tod_codec.header(d, last[1])
    if m not in (1, 3) or not (0 < u < (1 << 24)) or last[1] + 9 + p > len(d):
        return []
    out = tod_codec.unpack(d, last[1])
    res = []
    for j, a, b in tod_arc.members(out, 0, len(out)):
        info, _ = tim.parse(out, a)
        if info:
            continue
        for off, s in runs(out[a:b]):
            res.append((j, off, s))
    return res


def main(argv):
    exe = Exe(argv[0])
    datdir = argv[1]
    ids = tod_index.map_ids(exe)
    ex = tod_index.extents(exe, 'M.DAT')
    fh = open(os.path.join(datdir, 'M.DAT'), 'rb')

    if '--map' in argv:
        n = int(argv[argv.index('--map') + 1], 0)
        off, sz = ex[n]
        fh.seek(off)
        for j, o, s in map_strings(fh.read(sz), sz):
            print('  sub %2d +%6d  %s' % (j, o, s))
        return

    labels = '--labels' in argv
    total = 0
    withtext = 0
    seen = set()
    for i, (off, sz) in enumerate(ex):
        fh.seek(off)
        ss = map_strings(fh.read(sz), sz)
        if ss:
            withtext += 1
        total += len(ss)
        if labels:
            for j, o, s in ss:
                raw = s.encode('shift_jis', 'ignore')
                if has_fullwidth_latin(raw) and s not in seen:
                    seen.add(s)
                    print('map %4d  id %04X  sub %2d  %s' % (i, ids[i], j, s))
        if i % 200 == 0:
            print('... %d/%d' % (i, len(ex)), file=sys.stderr)
    print('%d maps, %d with text, %d strings' % (len(ex), withtext, total),
          file=sys.stderr)
    if not labels:
        print('%d maps, %d with text, %d strings' % (len(ex), withtext, total))


if __name__ == '__main__':
    main(sys.argv[1:])
