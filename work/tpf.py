"""DSR TPF (PC, DDS textures) reader/writer."""
import struct


class Tpf:
    def __init__(self, d):
        assert d[:4] == b'TPF\0'
        self.head = bytes(d[:0x10])
        cnt = struct.unpack_from('<i', d, 8)[0]
        self.enc = d[0xE]  # 1 = utf-16 names
        self.tex = []
        for i in range(cnt):
            off, sz, fmt, typ, mips, fl, noff, unk = struct.unpack_from('<iiBBBBii', d, 0x10 + i * 20)
            if self.enc == 1:
                e = noff
                while d[e:e + 2] != b'\0\0':
                    e += 2
                name = d[noff:e].decode('utf-16-le')
            else:
                name = d[noff:d.index(b'\0', noff)].decode('shift_jis')
            self.tex.append({'name': name, 'fmt': fmt, 'typ': typ, 'mips': mips, 'fl': fl, 'unk': unk,
                             'data': bytes(d[off:off + sz])})

    @classmethod
    def parse_raw(cls, d):
        t = cls(d)
        cnt = len(t.tex)
        offs = [struct.unpack_from('<i', d, 0x10 + i * 20)[0] for i in range(cnt)]
        t.names_blob = bytes(d[0x10 + cnt * 20:min(offs)])
        t.name_offs = [struct.unpack_from('<i', d, 0x10 + i * 20 + 12)[0] for i in range(cnt)]
        return t

    def build(self):
        cnt = len(self.tex)
        data_start = 0x10 + cnt * 20 + len(self.names_blob)
        out = bytearray(self.head)
        struct.pack_into('<i', out, 4, sum(len(x['data']) for x in self.tex))
        pos = data_start
        for x, noff in zip(self.tex, self.name_offs):
            out += struct.pack('<iiBBBBii', pos, len(x['data']), x['fmt'], x['typ'], x['mips'], x['fl'], noff, x['unk'])
            pos += len(x['data'])
        out += self.names_blob
        for x in self.tex:
            out += x['data']
        return bytes(out)
