"""Archaeology: things on the disc that were not meant to ship, or that stopped
being used before it did.

    python tools/leftovers.py TRACK.bin ISODIR
    python tools/leftovers.py TRACK.bin ISODIR --filler
    python tools/leftovers.py TRACK.bin ISODIR --xa-filler

ISODIR is the directory produced by tools/iso9660.py --extract.
"""

import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tod_codec
import tod_index
from dismips import Exe
from psxdisc import Disc, HDR
from iso9660 import Volume

CHARACTERS = 10          # party records in the save templates
CHAR_STRIDE = 0xAC


def rule(t):
    print()
    print('-- %s ' % t + '-' * max(0, 66 - len(t)))


def debug_txt(exe, vol):
    rule('the DEBUG.TXT switch')
    print('The startup path at 0x801502F4 asks the CD for \\DEBUG.TXT;1 before it')
    print('does anything else, and stores 8 into the word at 0x80174AD0 if the file')
    print('is there and 4 if it is not.  Nothing else on the disc mentions the name.')
    print('  \\DEBUG.TXT;1 present on this disc: %s'
          % ('yes' if vol.find('DEBUG.TXT;1') else 'no'))


def registry_gap(exe):
    rule('the hole in the PIC id space')
    ids = []
    i = 0
    while True:
        w = struct.unpack_from('<4I', exe.text, 0x80192E44 - exe.taddr + i * 16)
        if w[0] == 0xFFFFFFFF:
            break
        ids.append(w[0])
        i += 1
    pic = [x for x in ids if 1000 <= x < 1100]
    missing = [x for x in range(min(pic), max(pic) + 1) if x not in pic]
    print('PIC ids in the registry: %s' % ', '.join(str(x) for x in pic))
    print('missing: %s  (seven .D files ship; the eighth slot was dropped)'
          % (', '.join(str(x) for x in missing) or 'none'))


def saves(isodir):
    rule('DBG.D — a debug save next to the real one')
    a = tod_codec.unpack(open(os.path.join(isodir, 'DAT', 'DBG.D'), 'rb').read())
    b = tod_codec.unpack(open(os.path.join(isodir, 'DAT', 'INI.D'), 'rb').read())
    print('INI.D and DBG.D both decode to %d bytes and are byte-identical except'
          % len(a))
    runs = []
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    print('in %d places totalling %d bytes.' % (len(runs), sum(j - i for i, j in runs)))
    names = []
    for k in range(CHARACTERS):
        o = 0x0C + k * CHAR_STRIDE
        given = b[o:o + 12].split(b'\0')[0].decode('shift_jis', 'replace')
        family = b[o + 16:o + 28].split(b'\0')[0].decode('shift_jis', 'replace')
        hp_i = struct.unpack_from('<H', b, o + 0x20)[0]      # first of three
        hp_d = struct.unpack_from('<H', a, o + 0x20)[0]      # equal 16-bit fields
        names.append((given, family, hp_i, hp_d))
    print()
    print('  %-14s %-14s %8s %8s' % ('given', 'family', 'INI.D', 'DBG.D'))
    for g, f, hi, hd in names:
        print('  %-14s %-14s %8d %8d' % (g, f, hi, hd))
    print()
    print('  byte at +0x08:        INI.D %d, DBG.D %d' % (b[8], a[8]))
    roster_i = list(b[0x94:0xA4])
    roster_d = list(a[0x94:0xA4])
    print('  16 bytes at +0x94:    INI.D %s' % ' '.join('%02X' % x for x in roster_i))
    print('                        DBG.D %s' % ' '.join('%02X' % x for x in roster_d))
    print('  — empty in the shipping template, fully populated in the debug one.')


def kaisen(isodir):
    rule('KAISEN.BIN — the naval mini-game, with its profiler still in it')
    d = open(os.path.join(isodir, 'DAT', 'KAISEN.BIN'), 'rb').read()
    print('%s bytes, a MIPS overlay linked at 0x80010000 — the same arena the map'
          % format(len(d), ','))
    print('data uses. A 0x118-byte header of strings and pointers, then code.')
    cur = bytearray()
    st = 0
    out = []
    for k, c in enumerate(d[:0x120]):
        if 32 <= c < 127:
            if not cur:
                st = k
            cur.append(c)
        else:
            if c == 0 and len(cur) >= 3:
                out.append((st, cur.decode()))
            cur = bytearray()
    for o, s in out:
        print('  +%04X  %r' % (o, s))


def sound_notes(exe):
    rule('names the sound team left marked')
    ptrs = struct.unpack_from('<174I', exe.text, 0x8018CFC8 - exe.taddr)
    for i, p in enumerate(ptrs):
        o = p - exe.taddr
        s = exe.text[o:exe.text.find(b'\0', o)].decode('latin1')
        if s.startswith('*') or s.strip() in ('?', 'Fin') or s.startswith(' namco'):
            print('  %3d  %s' % (i, s))


def ring(exe):
    rule('seventeen bytes of the decoder dictionary are never initialised')
    print('The method-3 decoder at 0x80150D4C builds its 4096-byte ring on the')
    print('stack, clears indices 0..4078, fills 0..3839 with a synthetic table,')
    print('and starts writing at 4079.  Indices 4079..4095 are left holding')
    print('whatever the previous call left on the stack.  A block that referenced')
    print('them would decode differently on every call; over 6,638 blocks on this')
    print('disc, none does.')


def filler(track):
    rule('filler')
    d = Disc(track)
    v = Volume(d)
    zero = 0
    for lba in range(d.sectors):
        if not any(d.raw(lba)[HDR:HDR + 2324]):
            zero += 1
    print('all-zero sectors in the data track: %d of %d (%.2f%%)'
          % (zero, d.sectors, 100.0 * zero / d.sectors))
    e = v.find('DUMMY3M.DA;1')
    if e:
        print('DUMMY3M.DA is declared at LBA %d for %s bytes (%d sectors).'
              % (e.lba, format(e.size, ','), e.sectors))
        print('The data track ends at LBA %d, so the whole extent lies outside it:'
              % (d.sectors - 1))
        print('LBA %d is exactly where track 2, the CD-DA audio track, starts after'
              % e.lba)
        print('its 150-sector pre-gap, and %d + %d = %d is the volume size the PVD'
              % (e.lba, e.sectors, e.lba + e.sectors))
        print('declares.  The pad file names the music track.')


# (name, first lba, sectors), from the ISO directory
XA_FILES = [('S.XA', 125101, 23968), ('T.XA', 149069, 70760)]
WORDY = re.compile(rb'[\x20-\x7e]{5,}')


def xa_filler(track):
    """What is in the unused slots of the eight-channel XA interleave.

    S.XA puts three live channels on an eight-slot grid and leaves five slots
    per cycle with no submode bits set at all.  Those sectors were never
    cleared, and about 72% of each one is non-zero.  Almost all of it is
    unreadable, but one fragment is not.
    """
    rule('what is in the empty interleave slots')
    d = Disc(track)
    runs = Counter()
    total = 0
    for name, lba, n in XA_FILES:
        here = 0
        for l in range(lba, min(lba + n, d.sectors)):
            s = d.raw(l)
            if s[0x12] != 0:
                continue
            here += 1
            body = s[HDR:HDR + 2048]
            for m in WORDY.finditer(body):
                runs[m.group()] += 1
        total += here
        print('%-6s %6d of %6d sectors carry no submode bits (%.1f%%), %s bytes'
              % (name, here, n, 100.0 * here / n, format(here * 2048, ',')))
    print('%s filler sectors overall, %s bytes -- and they are not blank.'
          % (format(total, ','), format(total * 2048, ',')))

    def wordy(b):
        t = b.decode('latin1')
        good = sum(1 for c in t if c.isalpha() or c in ' ._-')
        return good / len(t) >= 0.8 and any(c in 'aeiouAEIOU' for c in t)

    keep = sorted(((k, v) for k, v in runs.items() if wordy(k)),
                  key=lambda kv: -kv[1])
    print()
    print('printable runs that read as text, out of %d distinct runs in all:'
          % len(runs))
    for k, v in keep[:12]:
        print('  %6d x  %r' % (v, k.decode('latin1')))
    if not keep:
        print('  (none)')
    print()
    print('"rogram Manager" is the tail of "Program Manager", the title of the')
    print('Windows shell window.  The machine that authored this XA stream was')
    print('running Windows, and the tool wrote its uncleared buffer into every')
    print('unused slot of the interleave.')


def main(argv):
    track, isodir = argv[0], argv[1]
    exe = Exe(os.path.join(isodir, 'SLPS_011.00'))
    d = Disc(track)
    vol = Volume(d)
    debug_txt(exe, vol)
    registry_gap(exe)
    saves(isodir)
    kaisen(isodir)
    sound_notes(exe)
    ring(exe)
    if '--filler' in argv:
        filler(track)
    if '--xa-filler' in argv:
        xa_filler(track)


if __name__ == '__main__':
    main(sys.argv[1:])
