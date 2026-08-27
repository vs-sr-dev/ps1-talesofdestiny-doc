"""Pull Shift-JIS and ASCII strings out of a binary.

The disc keeps its Japanese in two different shapes.  Menu and mini-game text
is plain NUL-terminated Shift-JIS (TKM.BIN, the save templates); dialogue in
the map archives is not, and is stored as indices into a font the game builds
itself.  This tool finds the former.

    python tools/sjis_strings.py FILE [--min N] [--ascii] [--offsets]
"""

import sys


def is_sjis_lead(c):
    return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF


def is_sjis_trail(c):
    return 0x40 <= c <= 0xFC and c != 0x7F


def is_half(c):
    return 0x20 <= c < 0x7F or 0xA1 <= c <= 0xDF


def strings(data, minlen=2):
    """Yield (offset, text) for NUL-terminated Shift-JIS runs."""
    i = 0
    n = len(data)
    while i < n:
        j = i
        glyphs = 0
        while j < n:
            c = data[j]
            if is_sjis_lead(c) and j + 1 < n and is_sjis_trail(data[j + 1]):
                j += 2
                glyphs += 1
            elif is_half(c):
                j += 1
                glyphs += 1
            else:
                break
        if glyphs >= minlen:
            try:
                yield i, data[i:j].decode('shift_jis')
            except UnicodeDecodeError:
                pass
            i = j
        else:
            i += 1


def main(argv):
    data = open(argv[0], 'rb').read()
    minlen = int(argv[argv.index('--min') + 1]) if '--min' in argv else 2
    show = '--offsets' in argv
    n = 0
    for off, s in strings(data, minlen):
        s = s.replace('\n', '\\n')
        print('%06X  %s' % (off, s) if show else s)
        n += 1
    print('-- %d strings' % n, file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
