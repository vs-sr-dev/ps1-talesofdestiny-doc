"""Decide whether a buffer is SPU ADPCM, by decoding it.

The PlayStation's SPU eats 16-byte blocks: a shift/filter byte, a flag byte,
and fourteen bytes of 4-bit residual.  That structure is loose enough that
almost anything parses, so a structural check proves nothing.  Decoding does:
run the ADPCM predictor and measure how rough the waveform is.

    roughness = mean |x[i+2] - 2*x[i+1] + x[i]|  /  mean |x[i]|

Real audio is locally smooth and lands well under 1.  Bytes that are not
ADPCM decode to something indistinguishable from noise and land near 1.3,
which is where uniformly random input lands.

    python tools/vag_probe.py FILE [--at OFFSET] [--len N] [--pcm OUT.raw]
"""

import os
import struct
import sys

FILTERS = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]
BLOCK = 16


def decode(d):
    """4-bit SPU ADPCM to a list of 16-bit samples."""
    out = []
    s1 = s2 = 0.0
    for o in range(0, len(d) - BLOCK + 1, BLOCK):
        shift = d[o] & 0x0F
        filt = (d[o] >> 4) & 0x0F
        if filt > 4:
            filt = 0
        f0, f1 = FILTERS[filt]
        f0 /= 64.0
        f1 /= 64.0
        for k in range(14):
            b = d[o + 2 + k]
            for nib in (b & 0x0F, b >> 4):
                v = nib - 16 if nib > 7 else nib
                s = (v << 12) >> shift if shift <= 12 else 0
                s = float(s) + s1 * f0 + s2 * f1
                s = max(-32768.0, min(32767.0, s))
                out.append(s)
                s2, s1 = s1, s
    return out


def roughness(x):
    if len(x) < 3:
        return float('inf')
    d2 = sum(abs(x[i + 2] - 2 * x[i + 1] + x[i]) for i in range(len(x) - 2)) / (len(x) - 2)
    a = sum(abs(v) for v in x) / len(x) + 1e-9
    return d2 / a


def flags(d):
    from collections import Counter
    return Counter(d[o + 1] for o in range(0, len(d) - BLOCK + 1, BLOCK))


def main(argv):
    path = argv[0]
    off = int(argv[argv.index('--at') + 1], 0) if '--at' in argv else 0
    n = int(argv[argv.index('--len') + 1], 0) if '--len' in argv else 16384
    with open(path, 'rb') as fh:
        fh.seek(off)
        d = fh.read(n)
    x = decode(d)
    f = flags(d)
    print('%s +%d, %d bytes, %d blocks' % (os.path.basename(path), off, len(d), len(d) // BLOCK))
    print('  roughness  %.3f   (real ADPCM < 1; noise ~1.3)' % roughness(x))
    print('  peak       %.0f' % max(abs(v) for v in x))
    print('  flag bytes %s' % dict(f.most_common(6)))
    if '--pcm' in argv:
        out = argv[argv.index('--pcm') + 1]
        with open(out, 'wb') as fh:
            for v in x:
                fh.write(struct.pack('<h', int(v)))
        print('  wrote %s (%d samples, mono, play at 44100 or 22050)' % (out, len(x)))


if __name__ == '__main__':
    main(sys.argv[1:])
