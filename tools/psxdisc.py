"""Raw PlayStation CD-ROM (MODE2/2352) sector access.

A PS1 data track is a sequence of 2352-byte raw sectors:

    0x000  12  sync           00 FF*10 00
    0x00C   3  address        MM SS FF, BCD, MSF from 00:02:00
    0x00F   1  mode           always 0x02 on PS1 discs
    0x010   8  subheader      file, channel, submode, coding  (twice)
    0x018      user data      2048 bytes (Form 1) or 2324 bytes (Form 2)
    ...        EDC/ECC        288 bytes (Form 1) or 4 bytes EDC (Form 2)

Form is selected by bit 5 of the submode byte at 0x012.  Form 1 carries the
file system and program data; Form 2 carries XA-ADPCM audio and streamed
video, which the drive delivers without the ECC layer.

No game data is bundled with this file; it operates on an image you supply.
"""

import struct

RAW = 2352
HDR = 24            # sync + address + mode + subheader
FORM1 = 2048
FORM2 = 2324

SM_EOR   = 0x01     # end of record
SM_VIDEO = 0x02
SM_AUDIO = 0x04
SM_DATA  = 0x08
SM_TRIG  = 0x10
SM_FORM2 = 0x20
SM_RT    = 0x40     # real-time
SM_EOF   = 0x80


def bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


class Disc:
    """A MODE2/2352 data track opened for random sector access."""

    def __init__(self, path):
        self.path = path
        self.fh = open(path, 'rb')
        self.fh.seek(0, 2)
        self.size = self.fh.tell()
        self.sectors = self.size // RAW
        if self.size % RAW:
            raise ValueError(f'{path}: {self.size} is not a multiple of {RAW}')

    def raw(self, lba):
        if not 0 <= lba < self.sectors:
            raise IndexError(f'lba {lba} outside 0..{self.sectors - 1}')
        self.fh.seek(lba * RAW)
        return self.fh.read(RAW)

    def subheader(self, lba):
        s = self.raw(lba)
        return s[0x10:0x18]

    def submode(self, lba):
        return self.raw(lba)[0x12]

    def msf(self, lba):
        s = self.raw(lba)
        return bcd(s[0x0C]), bcd(s[0x0D]), bcd(s[0x0E])

    def form(self, lba):
        return 2 if (self.raw(lba)[0x12] & SM_FORM2) else 1

    def data(self, lba):
        """User data of one sector, Form-aware."""
        s = self.raw(lba)
        n = FORM2 if (s[0x12] & SM_FORM2) else FORM1
        return s[HDR:HDR + n]

    def read(self, lba, nbytes):
        """nbytes of Form 1 user data starting at the head of sector lba."""
        out = bytearray()
        while len(out) < nbytes:
            out += self.raw(lba)[HDR:HDR + FORM1]
            lba += 1
        return bytes(out[:nbytes])

    def close(self):
        self.fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def submode_str(sm):
    names = [(SM_EOF, 'EOF'), (SM_RT, 'RT'), (SM_FORM2, 'FORM2'),
             (SM_TRIG, 'TRIG'), (SM_DATA, 'DATA'), (SM_AUDIO, 'AUDIO'),
             (SM_VIDEO, 'VIDEO'), (SM_EOR, 'EOR')]
    on = [n for bit, n in names if sm & bit]
    return '|'.join(on) if on else '-'
