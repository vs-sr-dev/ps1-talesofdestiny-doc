"""ISO 9660 volume and directory walker for PlayStation discs.

Reads the Primary Volume Descriptor at LBA 16, then the directory tree.  PS1
discs use plain ISO 9660 Level 1 (8.3 names, ";1" version suffix) with the
Sony CD-XA signature block at offset 0x400 of the PVD and a fourteen-byte XA
extension appended to every directory record.

Usage:
    python tools/iso9660.py IMAGE.bin            # tree listing
    python tools/iso9660.py IMAGE.bin --pvd      # volume descriptors
    python tools/iso9660.py IMAGE.bin --extract OUTDIR
"""

import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from psxdisc import Disc


def both16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def both32(b, o):
    return struct.unpack_from('<I', b, o)[0]


class Entry:
    __slots__ = ('name', 'lba', 'size', 'flags', 'date', 'xa', 'path',
                 'unit', 'gap', 'parent')

    def __init__(self, rec):
        self.lba = both32(rec, 2)
        self.size = both32(rec, 10)
        self.date = tuple(rec[18:25])
        self.flags = rec[25]
        self.unit = rec[26]
        self.gap = rec[27]
        nlen = rec[32]
        raw = rec[33:33 + nlen]
        if nlen == 1 and raw in (b'\x00', b'\x01'):
            self.name = '.' if raw == b'\x00' else '..'
        else:
            self.name = raw.decode('shift_jis', 'replace')
        tail = 33 + nlen + ((nlen + 1) % 2)
        self.xa = rec[tail:tail + 14] if len(rec) >= tail + 14 else b''
        self.path = self.name
        self.parent = ''

    @property
    def is_dir(self):
        return bool(self.flags & 0x02)

    @property
    def base(self):
        return self.name.split(';')[0]

    @property
    def sectors(self):
        return (self.size + 2047) // 2048

    def date_str(self):
        y, m, d, H, M, S, tz = self.date
        off = tz - 256 if tz > 127 else tz
        return '%04d-%02d-%02d %02d:%02d:%02d GMT%+d' % (
            1900 + y, m, d, H, M, S, off // 4)

    def xa_str(self):
        if len(self.xa) < 8 or self.xa[6:8] != b'XA':
            return ''
        own_g, own_u, attr = struct.unpack_from('>HHH', self.xa, 0)
        bits = []
        for bit, n in ((0x0800, 'MODE2'), (0x1000, 'FORM1'), (0x2000, 'FORM2'),
                       (0x4000, 'INTERLEAVED'), (0x8000, 'CDDA')):
            if attr & bit:
                bits.append(n)
        return 'attr=%04X[%s] owner=%d:%d' % (attr, ','.join(bits), own_g, own_u)


def read_dir(disc, lba, size, parent=''):
    data = disc.read(lba, size)
    out = []
    off = 0
    while off < len(data):
        ln = data[off]
        if ln == 0:
            off = (off // 2048 + 1) * 2048
            continue
        e = Entry(data[off:off + ln])
        e.parent = parent
        e.path = (parent + '/' + e.name) if parent else e.name
        if e.name not in ('.', '..'):
            out.append(e)
        off += ln
    return out


def walk(disc, lba, size, parent=''):
    for e in read_dir(disc, lba, size, parent):
        yield e
        if e.is_dir:
            for sub in walk(disc, e.lba, e.size, e.path):
                yield sub


class Volume:
    def __init__(self, disc):
        self.disc = disc
        self.descriptors = []
        lba = 16
        while lba <= 32:
            b = disc.read(lba, 2048)
            self.descriptors.append((lba, b))
            if b[0] == 0xFF:
                break
            lba += 1
        self.pvd = next(b for _, b in self.descriptors if b[0] == 1)
        p = self.pvd
        self.system_id = p[8:40].decode('latin1').rstrip()
        self.volume_id = p[40:72].decode('latin1').rstrip()
        self.volume_blocks = both32(p, 80)
        self.block_size = both16(p, 128)
        self.path_table_size = both32(p, 132)
        self.path_table_l = struct.unpack_from('<I', p, 140)[0]
        self.path_table_m = struct.unpack_from('>I', p, 148)[0]
        self.root = Entry(p[156:156 + 34])
        self.root.path = ''
        self.volume_set = p[190:318].decode('latin1').rstrip()
        self.publisher = p[318:446].decode('latin1').rstrip()
        self.preparer = p[446:574].decode('latin1').rstrip()
        self.application = p[574:702].decode('latin1').rstrip()
        self.copyright_file = p[702:739].decode('latin1').rstrip('\0 ')
        self.abstract_file = p[739:776].decode('latin1').rstrip('\0 ')
        self.biblio_file = p[776:813].decode('latin1').rstrip('\0 ')
        self.created = p[813:830]
        self.modified = p[830:847]
        self.expires = p[847:864]
        self.effective = p[864:881]
        self.xa_sig = p[1024:1024 + 8]

    def files(self):
        return list(walk(self.disc, self.root.lba, self.root.size))

    def find(self, path):
        want = path.strip('/').upper()
        for e in self.files():
            if e.path.upper() == want or e.path.upper().split(';')[0] == want:
                return e
        return None

    def read_file(self, e):
        return self.disc.read(e.lba, e.size)


def main(argv):
    img = argv[0]
    disc = Disc(img)
    v = Volume(disc)
    if '--pvd' in argv:
        print('image           %s' % os.path.basename(img))
        print('raw sectors     %d' % disc.sectors)
        print('descriptors     %s' % [(l, b[0], b[1:6].decode('latin1'))
                                      for l, b in v.descriptors])
        print('system id       %r' % v.system_id)
        print('volume id       %r' % v.volume_id)
        print('volume blocks   %d (%s bytes of Form-1 data)'
              % (v.volume_blocks, format(v.volume_blocks * 2048, ',')))
        print('block size      %d' % v.block_size)
        print('path table      %d bytes, L at LBA %d, M at LBA %d'
              % (v.path_table_size, v.path_table_l, v.path_table_m))
        print('volume set      %r' % v.volume_set)
        print('publisher       %r' % v.publisher)
        print('preparer        %r' % v.preparer)
        print('application     %r' % v.application)
        print('copyright file  %r' % v.copyright_file)
        print('abstract file   %r' % v.abstract_file)
        print('created         %r' % v.created.decode('latin1'))
        print('modified        %r' % v.modified.decode('latin1'))
        print('expires         %r' % v.expires.decode('latin1'))
        print('effective       %r' % v.effective.decode('latin1'))
        print('XA signature    %r' % v.xa_sig)
        print('root            LBA %d size %d' % (v.root.lba, v.root.size))
        return
    if '--extract' in argv:
        out = argv[argv.index('--extract') + 1]
        for e in v.files():
            dst = os.path.join(out, e.path.replace(';1', ''))
            if e.is_dir:
                os.makedirs(dst, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            avail = max(0, (disc.sectors - e.lba)) * 2048
            n = min(e.size, avail)
            with open(dst, 'wb') as fh:
                fh.write(disc.read(e.lba, n) if n else b'')
            note = '' if n == e.size else '   (TRUNCATED: extent runs past the end of the track)'
            print('%s  %s%s' % (e.path, format(n, ','), note))
        return
    tot = 0
    n = 0
    for e in v.files():
        if e.is_dir:
            print('DIR  %7d  %12s  %s  %s' % (e.lba, '', e.date_str(), e.path))
        else:
            tot += e.size
            n += 1
            print('     %7d  %12s  %s  %s   %s'
                  % (e.lba, format(e.size, ','), e.date_str(), e.path, e.xa_str()))
    print('\n%d files, %s bytes' % (n, format(tot, ',')))


if __name__ == '__main__':
    main(sys.argv[1:])
