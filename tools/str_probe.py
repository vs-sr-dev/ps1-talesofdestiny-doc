"""Reader for the streamed data on the disc: MDEC video (.STR) and XA audio.

An .STR video sector carries a 32-byte stream header in front of its 2016
bytes of payload:

    +0   u16  0x0160          Sony's stream marker
    +2   u16  0x8001          chunk type: MDEC video
    +4   u16  chunk index within the frame
    +6   u16  chunks in the frame
    +8   u32  frame number
    +12  u32  bytes of bitstream in the frame
    +16  u16  width
    +18  u16  height
    +20  u16  bitstream length in 32-bit units
    +22  u16  0x3800          the frame's own MDEC bitstream header,
    +24  u16  quantisation    repeated verbatim in every chunk of the frame
    +26  u16  bitstream version (1, 2 or 3 on this disc)

An XA audio sector's parameters live in the CD-XA subheader's fourth byte:

    bit 0-1  sample rate   0 = 37.8 kHz, 1 = 18.9 kHz
    bit 2-3  bits/sample   0 = 4 bit, 1 = 8 bit
    bit 4-5  channels      0 = mono, 1 = stereo
    bit 6    emphasis

Usage:
    python tools/str_probe.py TRACK.bin --str LBA COUNT
    python tools/str_probe.py TRACK.bin --xa  LBA COUNT
"""

import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psxdisc import Disc, HDR, submode_str, SM_FORM2

RATE = {0: '37.8 kHz', 1: '18.9 kHz'}
BITS = {0: '4 bit', 1: '8 bit'}
CHAN = {0: 'mono', 1: 'stereo'}


def coding(b):
    return '%s %s %s%s' % (CHAN.get((b >> 4) & 3, '?'), RATE.get(b & 3, '?'),
                           BITS.get((b >> 2) & 3, '?'),
                           ', emphasis' if b & 0x40 else '')


def do_str(d, lba, n):
    frames = {}
    dims = Counter()
    bad = 0
    audio = 0
    for l in range(lba, min(lba + n, d.sectors)):
        s = d.raw(l)
        if s[0x12] & SM_FORM2 and (s[0x12] & 0x04):
            audio += 1
            continue
        h = s[HDR:HDR + 32]
        marker, typ = struct.unpack_from('<HH', h, 0)
        if marker != 0x0160:
            bad += 1
            continue
        idx, cnt = struct.unpack_from('<HH', h, 4)
        frame, nbytes = struct.unpack_from('<II', h, 8)
        w, hgt = struct.unpack_from('<HH', h, 16)
        bs = struct.unpack_from('<HHHH', h, 20)
        dims[(w, hgt, typ, bs[1], bs[3])] += 1
        f = frames.setdefault(frame, [0, cnt, nbytes])
        f[0] += 1
    print('  video sectors  %d in %d frames' % (sum(f[0] for f in frames.values()), len(frames)))
    print('  audio sectors  %d' % audio)
    print('  other          %d' % bad)
    for k, c in dims.most_common():
        print('  %dx%d  chunk type 0x%04X  bs magic 0x%04X  bs version %d   on %d sectors'
              % (k[0], k[1], k[2], k[3], k[4], c))
    if frames:
        ks = sorted(frames)
        short = [k for k in ks if frames[k][0] != frames[k][1]]
        print('  frame numbers  %d .. %d, %d distinct, %d incomplete'
              % (ks[0], ks[-1], len(ks), len(short)))
        sizes = [frames[k][2] for k in ks]
        print('  bitstream      %d .. %d bytes, mean %d'
              % (min(sizes), max(sizes), sum(sizes) // len(sizes)))


def do_xa(d, lba, n):
    codes = Counter()
    chans = Counter()
    for l in range(lba, min(lba + n, d.sectors)):
        s = d.raw(l)
        codes[(s[0x13], s[0x12])] += 1
        chans[(s[0x10], s[0x11])] += 1
    for (c, sm), v in sorted(codes.items()):
        print('  coding %02X  submode %02X %-22s %8d sectors   %s'
              % (c, sm, submode_str(sm), v, coding(c)))
    print('  %d distinct file/channel pairs' % len(chans))


def main(argv):
    d = Disc(argv[0])
    if '--str' in argv:
        i = argv.index('--str')
        do_str(d, int(argv[i + 1], 0), int(argv[i + 2], 0))
    if '--xa' in argv:
        i = argv.index('--xa')
        do_xa(d, int(argv[i + 1], 0), int(argv[i + 2], 0))


if __name__ == '__main__':
    main(sys.argv[1:])
