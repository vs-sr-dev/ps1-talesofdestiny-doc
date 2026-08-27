"""R3000A / MIPS-I disassembler, with the PlayStation GTE (COP2) opcodes.

Enough of the ISA to read a PS1 executable: all MIPS-I integer and branch
opcodes, COP0, the GTE register moves and the 15 GTE operations.  Branch and
jump targets are resolved to absolute addresses so the output can be followed
without arithmetic.

Usage:
    python tools/dismips.py EXE                       # whole .text
    python tools/dismips.py EXE 0x80151010 200        # 200 instructions at va
    python tools/dismips.py EXE --find-jal 0x800A1234 # call sites
    python tools/dismips.py EXE --strings             # printable strings
"""

import struct
import sys

REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3',
       't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
       't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

SPECIAL = {
    0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x04: 'sllv', 0x06: 'srlv',
    0x07: 'srav', 0x08: 'jr', 0x09: 'jalr', 0x0C: 'syscall', 0x0D: 'break',
    0x10: 'mfhi', 0x11: 'mthi', 0x12: 'mflo', 0x13: 'mtlo',
    0x18: 'mult', 0x19: 'multu', 0x1A: 'div', 0x1B: 'divu',
    0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu',
    0x24: 'and', 0x25: 'or', 0x26: 'xor', 0x27: 'nor',
    0x2A: 'slt', 0x2B: 'sltu',
}

OPC = {
    0x02: 'j', 0x03: 'jal', 0x04: 'beq', 0x05: 'bne', 0x06: 'blez', 0x07: 'bgtz',
    0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi',
    0x0D: 'ori', 0x0E: 'xori', 0x0F: 'lui',
    0x20: 'lb', 0x21: 'lh', 0x22: 'lwl', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
    0x26: 'lwr', 0x28: 'sb', 0x29: 'sh', 0x2A: 'swl', 0x2B: 'sw', 0x2E: 'swr',
    0x32: 'lwc2', 0x3A: 'swc2',
}

REGIMM = {0x00: 'bltz', 0x01: 'bgez', 0x10: 'bltzal', 0x11: 'bgezal'}

GTE_OP = {
    0x01: 'rtps', 0x06: 'nclip', 0x0C: 'op', 0x10: 'dpcs', 0x11: 'intpl',
    0x12: 'mvmva', 0x13: 'ncds', 0x14: 'cdp', 0x16: 'ncdt', 0x1B: 'nccs',
    0x1C: 'cc', 0x1E: 'ncs', 0x20: 'nct', 0x28: 'sqr', 0x29: 'dcpl',
    0x2A: 'dpct', 0x2D: 'avsz3', 0x2E: 'avsz4', 0x30: 'rtpt', 0x3D: 'gpf',
    0x3E: 'gpl', 0x3F: 'ncct',
}

COP0R = {0: 'Index', 2: 'EntryLo', 4: 'Context', 8: 'BadVAddr', 10: 'EntryHi',
         12: 'SR', 13: 'Cause', 14: 'EPC', 15: 'PRId'}


def s16(x):
    return x - 0x10000 if x & 0x8000 else x


def disasm(w, pc):
    """Return (text, target_or_None) for one word at virtual address pc."""
    op = w >> 26
    rs, rt, rd = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
    sa, fn = (w >> 6) & 31, w & 63
    imm = w & 0xFFFF
    si = s16(imm)
    R = REG

    if w == 0:
        return 'nop', None
    if op == 0:
        m = SPECIAL.get(fn)
        if m is None:
            return '.word 0x%08X' % w, None
        if m in ('sll', 'srl', 'sra'):
            return '%-7s %s, %s, %d' % (m, R[rd], R[rt], sa), None
        if m in ('sllv', 'srlv', 'srav'):
            return '%-7s %s, %s, %s' % (m, R[rd], R[rt], R[rs]), None
        if m == 'jr':
            return '%-7s %s' % (m, R[rs]), None
        if m == 'jalr':
            return '%-7s %s, %s' % (m, R[rd], R[rs]), None
        if m in ('syscall', 'break'):
            return '%-7s 0x%X' % (m, (w >> 6) & 0xFFFFF), None
        if m in ('mfhi', 'mflo'):
            return '%-7s %s' % (m, R[rd]), None
        if m in ('mthi', 'mtlo'):
            return '%-7s %s' % (m, R[rs]), None
        if m in ('mult', 'multu', 'div', 'divu'):
            return '%-7s %s, %s' % (m, R[rs], R[rt]), None
        return '%-7s %s, %s, %s' % (m, R[rd], R[rs], R[rt]), None

    if op == 1:
        m = REGIMM.get(rt, 'regimm?')
        tgt = pc + 4 + si * 4
        return '%-7s %s, 0x%08X' % (m, R[rs], tgt), tgt

    if op in (2, 3):
        tgt = (pc & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
        return '%-7s 0x%08X' % (OPC[op], tgt), tgt

    if op in (4, 5):
        tgt = pc + 4 + si * 4
        if op == 4 and rt == 0 and rs == 0:
            return '%-7s 0x%08X' % ('b', tgt), tgt
        return '%-7s %s, %s, 0x%08X' % (OPC[op], R[rs], R[rt], tgt), tgt

    if op in (6, 7):
        tgt = pc + 4 + si * 4
        return '%-7s %s, 0x%08X' % (OPC[op], R[rs], tgt), tgt

    if op == 0x0F:
        return '%-7s %s, 0x%04X' % ('lui', R[rt], imm), None

    if op in (0x08, 0x09, 0x0A, 0x0B):
        return '%-7s %s, %s, %d' % (OPC[op], R[rt], R[rs], si), None
    if op in (0x0C, 0x0D, 0x0E):
        return '%-7s %s, %s, 0x%04X' % (OPC[op], R[rt], R[rs], imm), None

    if op in OPC and 0x20 <= op <= 0x2E:
        return '%-7s %s, %d(%s)' % (OPC[op], R[rt], si, R[rs]), None

    if op == 0x10:                                   # COP0
        if rs == 0:
            return '%-7s %s, %s' % ('mfc0', R[rt], COP0R.get(rd, 'c0r%d' % rd)), None
        if rs == 4:
            return '%-7s %s, %s' % ('mtc0', R[rt], COP0R.get(rd, 'c0r%d' % rd)), None
        if w & 0x02000000:
            return '%-7s' % 'rfe', None
        return 'cop0    0x%07X' % (w & 0x1FFFFFF), None

    if op == 0x12:                                   # COP2 / GTE
        if rs == 0:
            return '%-7s %s, r%d' % ('mfc2', R[rt], rd), None
        if rs == 2:
            return '%-7s %s, r%d' % ('cfc2', R[rt], rd), None
        if rs == 4:
            return '%-7s %s, r%d' % ('mtc2', R[rt], rd), None
        if rs == 6:
            return '%-7s %s, r%d' % ('ctc2', R[rt], rd), None
        if w & 0x02000000:
            m = GTE_OP.get(w & 0x3F, 'gte?')
            sf = (w >> 19) & 1
            return '%-7s (sf=%d, 0x%07X)' % (m, sf, w & 0x1FFFFFF), None
        return 'cop2    0x%07X' % (w & 0x1FFFFFF), None

    if op in (0x32, 0x3A):
        return '%-7s r%d, %d(%s)' % (OPC[op], rt, si, R[rs]), None

    return '.word 0x%08X' % w, None


class Exe:
    def __init__(self, path):
        b = open(path, 'rb').read()
        if b[:8] != b'PS-X EXE':
            raise ValueError('not a PS-X EXE')
        self.raw = b
        (self.pc0, self.gp0, self.taddr, self.tsize, self.daddr, self.dsize,
         self.baddr, self.bsize, self.bss, self.bsssz, self.sp,
         self.spsz) = struct.unpack_from('<12I', b, 0x10)
        self.region = b[0x4C:0x7B].split(b'\0')[0].decode('latin1')
        self.text = b[0x800:0x800 + self.tsize]

    def word(self, va):
        o = va - self.taddr
        return struct.unpack_from('<I', self.text, o)[0]

    def contains(self, va):
        return self.taddr <= va < self.taddr + self.tsize


def main(argv):
    exe = Exe(argv[0])
    rest = argv[1:]

    if '--header' in rest:
        print('entry pc0    0x%08X' % exe.pc0)
        print('gp0          0x%08X' % exe.gp0)
        print('text va      0x%08X .. 0x%08X (%s bytes)'
              % (exe.taddr, exe.taddr + exe.tsize, format(exe.tsize, ',')))
        print('data va      0x%08X (%d)' % (exe.daddr, exe.dsize))
        print('bss va       0x%08X (%d)' % (exe.bss, exe.bsssz))
        print('sp           0x%08X (%d)' % (exe.sp, exe.spsz))
        print('region       %r' % exe.region)
        return

    if '--find-jal' in rest:
        tgt = int(rest[rest.index('--find-jal') + 1], 0)
        enc = (0x03 << 26) | ((tgt >> 2) & 0x03FFFFFF)
        n = 0
        for o in range(0, len(exe.text), 4):
            if struct.unpack_from('<I', exe.text, o)[0] == enc:
                print('0x%08X' % (exe.taddr + o))
                n += 1
        print('%d call sites' % n)
        return

    if '--strings' in rest:
        mn = 4
        cur = bytearray()
        start = 0
        for i, c in enumerate(exe.text):
            if 0x20 <= c < 0x7F:
                if not cur:
                    start = i
                cur.append(c)
            else:
                if c == 0 and len(cur) >= mn:
                    print('0x%08X  %s' % (exe.taddr + start, cur.decode('latin1')))
                cur = bytearray()
        return

    if rest:
        va = int(rest[0], 0)
        n = int(rest[1], 0) if len(rest) > 1 else 64
    else:
        va, n = exe.taddr, exe.tsize // 4

    for i in range(n):
        a = va + i * 4
        if not exe.contains(a):
            break
        w = exe.word(a)
        t, _ = disasm(w, a)
        print('%08X  %08X  %s' % (a, w, t))


if __name__ == '__main__':
    main(sys.argv[1:])
