"""Sector-level census of a PlayStation data track.

Reports the system area (the 16 sectors before the volume descriptors, which
on a licensed disc carry Sony's boot logo and licence string), then walks the
track counting Form 1 versus Form 2 sectors, submode flags and XA
file/channel numbers, and prints a run-length map of what is where.

    python tools/sector_map.py TRACK.bin [--runs] [--channels]
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psxdisc import Disc, RAW, HDR, submode_str, SM_FORM2, SM_AUDIO, SM_VIDEO, SM_RT


def main(argv):
    d = Disc(argv[0])
    print('track      %s' % os.path.basename(argv[0]))
    print('raw size   %s bytes, %d sectors' % (format(d.size, ','), d.sectors))

    if '--files' in argv:
        from iso9660 import Volume
        v = Volume(d)
        files = sorted((e for e in v.files() if not e.is_dir), key=lambda e: e.lba)
        print('\n-- per file, in disc order --')
        print('%-14s %8s %8s %12s  %s'
              % ('file', 'lba', 'sectors', 'bytes', 'submodes'))
        prev = 16
        for e in files:
            n = min(e.sectors, d.sectors - e.lba)
            if n <= 0:
                print('%-14s %8d %8s %12s  extent lies beyond the end of the track'
                      % (e.base, e.lba, '-', format(e.size, ',')))
                continue
            if e.lba > prev:
                print('%-14s %8d %8d %12s  (directory records / gap)'
                      % ('--', prev, e.lba - prev, ''))
            c = Counter(d.raw(l)[0x12] for l in range(e.lba, e.lba + n))
            prev = max(prev, e.lba + n)
            print('%-14s %8d %8d %12s  %s'
                  % (e.base, e.lba, n, format(e.size, ','),
                     ', '.join('%02X %s x%d' % (k, submode_str(k), val)
                               for k, val in c.most_common(4))))
        print('%-14s %8d %8d %12s  (post-gap before the audio track)'
              % ('--', prev, d.sectors - prev, ''))
        return

    print('\n-- system area (LBA 0-15) --')
    for lba in range(16):
        s = d.raw(lba)
        body = s[HDR:HDR + 2324]
        txt = bytes(c if 32 <= c < 127 else 0x2E for c in body[:64]).decode('latin1')
        nz = sum(1 for c in body if c)
        print('  %2d  mode %d  sub %s  %5d non-zero  %s'
              % (lba, s[0x0F], submode_str(s[0x12]), nz, txt.rstrip('.') or '(empty)'))

    print('\n-- submode census --')
    sub = Counter()
    chan = Counter()
    form2 = 0
    runs = []
    prev = None
    start = 0
    step = 1
    for lba in range(0, d.sectors, step):
        s = d.raw(lba)
        sm = s[0x12]
        sub[sm] += 1
        if sm & SM_FORM2:
            form2 += 1
            chan[(s[0x10], s[0x11], sm & (SM_AUDIO | SM_VIDEO | SM_RT))] += 1
        key = 'FORM2' if sm & SM_FORM2 else 'FORM1'
        if key != prev:
            if prev is not None:
                runs.append((start, lba - start, prev))
            prev, start = key, lba
    runs.append((start, d.sectors - start, prev))
    for sm, n in sub.most_common():
        print('  submode %02X  %-24s %8d sectors  (%.1f%%)'
              % (sm, submode_str(sm), n, 100.0 * n / d.sectors))
    print('  Form 1 %d, Form 2 %d (%.1f%% of the track)'
          % (d.sectors - form2, form2, 100.0 * form2 / d.sectors))

    if '--channels' in argv:
        print('\n-- XA file/channel pairs on Form 2 sectors --')
        for (f, c, kind), n in sorted(chan.items()):
            print('  file %3d channel %3d  %-16s %8d sectors  %6.1f s of stereo XA'
                  % (f, c, submode_str(kind), n, n / 150.0))

    if '--runs' in argv:
        print('\n-- Form 1 / Form 2 runs --')
        for a, n, k in runs:
            if n < 16:
                continue
            print('  %8d .. %8d  %8d  %s' % (a, a + n - 1, n, k))


if __name__ == '__main__':
    main(sys.argv[1:])
