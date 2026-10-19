"""Minimal DSR (DS1R) DCX / BND3 / PARAM / PARAMDEF reader-writer."""
import struct, zlib, re

# ---------- DCX (DFLT) ----------
def dcx_read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'DCX\0' and b[0x28:0x2C] == b'DFLT'
    return b[:0x4C], zlib.decompress(b[0x4C:])

def dcx_write(path, header, data):
    comp = zlib.compress(data, 9)
    h = bytearray(header)
    struct.pack_into('>II', h, 0x1C, len(data), len(comp))
    open(path, 'wb').write(bytes(h) + comp)

# ---------- BND3 (format 0x74, little endian) ----------
class Bnd3:
    def __init__(self, data):
        assert data[:4] == b'BND3'
        self.version = data[4:12]
        self.fmt = data[0xC]
        assert self.fmt in (0x74, 0x70), hex(self.fmt)   # 0x70: entries without the uncompressed size
        self.entry = 0x18 if self.fmt == 0x74 else 0x14
        n = struct.unpack_from('<i', data, 0x10)[0]
        self.files = []  # [flags, id, name(bytes), data]
        for i in range(n):
            flags, csize, off, fid, noff = struct.unpack_from('<Iiiii', data, 0x20 + i * self.entry)
            name = data[noff:data.index(b'\0', noff)]
            self.files.append([flags, fid, name, data[off:off + csize]])

    def get(self, suffix):
        for f in self.files:
            if f[2].decode('shift_jis').replace('\\', '/').endswith(suffix):
                return f
        raise KeyError(suffix)

    def build(self):
        n = len(self.files)
        hdr_end = 0x20 + n * self.entry
        names = bytearray()
        noffs = []
        for f in self.files:
            noffs.append(hdr_end + len(names))
            names += f[2] + b'\0'
        headers_end = hdr_end + len(names)
        out = bytearray(b'BND3' + self.version + bytes([self.fmt, 0, 0, 0]))
        out += struct.pack('<iiii', n, headers_end, 0, 0)
        pos = (headers_end + 0xF) & ~0xF
        offs = []
        for f in self.files:
            offs.append(pos)
            pos = (pos + len(f[3]) + 0xF) & ~0xF
        for f, no, do in zip(self.files, noffs, offs):
            out += struct.pack('<Iiiii', f[0], len(f[3]), do, f[1], no)
            if self.entry == 0x18:
                out += struct.pack('<I', len(f[3]))
        out += names
        for f, do in zip(self.files, offs):
            out += b'\0' * (do - len(out))
            out += f[3]
        return bytes(out)

# ---------- PARAMDEF (DS1, 0xB0 fields) ----------
TYPES = {'s8': 'b', 'u8': 'B', 's16': 'h', 'u16': 'H', 's32': 'i', 'u32': 'I', 'f32': 'f'}

class Field:
    def __init__(self, disp, itype, iname, nbytes):
        self.disp, self.itype, self.nbytes = disp, itype, nbytes
        m = re.match(r'^([^\[:]+?)\s*(?:\[(\d+)\])?\s*(?::\s*(\d+))?$', iname.strip())
        self.name = m.group(1)
        self.arr = int(m.group(2)) if m.group(2) else None
        self.bits = int(m.group(3)) if m.group(3) else None

def paramdef_parse(data):
    size, hsize, ver, nfields, fsize = struct.unpack_from('<iHhhh', data, 0)
    ptype = data[0xC:0x2C].split(b'\0')[0].decode().strip()
    assert fsize == 0xB0, fsize
    fields = []
    for i in range(nfields):
        o = hsize + i * fsize
        disp = data[o:o + 0x40].split(b'\0')[0].decode('shift_jis', 'replace')
        nbytes = struct.unpack_from('<i', data, o + 0x64)[0]
        itype = data[o + 0x40:o + 0x48].split(b'\0')[0].decode().strip()
        iname = data[o + 0x8C:o + 0xAC].split(b'\0')[0].decode('shift_jis', 'replace').strip()
        fields.append(Field(disp, itype, iname, nbytes))
    return ptype, fields

class Layout:
    """Computes byte/bit offsets for each named field."""
    def __init__(self, fields):
        self.fields = fields
        self.slots = {}  # name -> (kind, offset, fmt/bitinfo)
        off = 0
        bit_unit = None  # (type, offset, size_bits, used_bits)
        for f in fields:
            t = f.itype
            if f.bits is not None and t in TYPES:
                usize = struct.calcsize(TYPES[t]) * 8
                if bit_unit is None or bit_unit[0] != t or bit_unit[3] + f.bits > bit_unit[2]:
                    bit_unit = [t, off, usize, 0]
                    off += usize // 8
                self.slots[f.name] = ('bit', bit_unit[1], (TYPES[t], bit_unit[3], f.bits))
                bit_unit[3] += f.bits
                continue
            if f.bits is not None and t == 'dummy8':
                # padding bits share unit with previous bitfield
                if bit_unit is None or bit_unit[3] + f.bits > bit_unit[2]:
                    bit_unit = ['u8', off, 8, 0]
                    off += 1
                bit_unit[3] += f.bits
                continue
            bit_unit = None
            if t in TYPES:
                self.slots[f.name] = ('num', off, '<' + TYPES[t])
            off += f.nbytes
        self.size = off

    def get(self, row, name):
        kind, off, info = self.slots[name]
        if kind == 'num':
            return struct.unpack_from(info, row, off)[0]
        fmt, shift, nb = info
        v = struct.unpack_from('<' + fmt.upper(), row, off)[0]
        return (v >> shift) & ((1 << nb) - 1)

    def set(self, row, name, value):
        kind, off, info = self.slots[name]
        if kind == 'num':
            struct.pack_into(info, row, off, value)
            return
        fmt, shift, nb = info
        ufmt = '<' + fmt.upper()
        v = struct.unpack_from(ufmt, row, off)[0]
        mask = ((1 << nb) - 1) << shift
        v = (v & ~mask) | ((int(value) << shift) & mask)
        struct.pack_into(ufmt, row, off, v)

    def dump(self, row):
        return {n: self.get(row, n) for n in self.slots}

# ---------- PARAM (DS1) ----------
class Param:
    def __init__(self, data):
        self.raw_header = bytearray(data[:0x30])
        strings_off, data_start, unk6, dver, count = struct.unpack_from('<IHHHH', data, 0)
        self.ptype = data[0xC:0x2C].split(bytes(1))[0].decode()
        entries = [struct.unpack_from('<iii', data, 0x30 + i * 12) for i in range(count)]
        self.gap = bytes(data[0x30 + count * 12:data_start])
        end = max((data.index(bytes(1), e[2]) + 1 for e in entries if e[2]), default=len(data))
        self.tail = bytes(data[end:])
        offs = sorted(e[1] for e in entries) + [strings_off]
        self.rowsize = (offs[-1] - offs[0]) // count if count else 0
        self.rows = []  # [id, bytearray, name bytes], file order
        for rid, doff, noff in entries:
            name = data[noff:data.index(bytes(1), noff)] if noff else b''
            self.rows.append([rid, bytearray(data[doff:doff + self.rowsize]), name])

    def __getitem__(self, rid):
        for r in self.rows:
            if r[0] == rid:
                return r[1]
        raise KeyError(rid)

    def __contains__(self, rid):
        return any(r[0] == rid for r in self.rows)

    def name(self, rid):
        for r in self.rows:
            if r[0] == rid:
                return r[2].decode('shift_jis', 'replace')

    def add(self, rid, row, name=b''):
        assert rid not in self, rid
        assert len(row) == self.rowsize
        # keep ids ascending: the game looks rows up by binary search (spells appended at the end
        # were missing from the attunement menu)
        at = next((i for i, r in enumerate(self.rows) if r[0] > rid), len(self.rows))
        self.rows.insert(at, [rid, bytearray(row), name])
        return self.rows[at][1]

    def build(self):
        n = len(self.rows)
        data_start = 0x30 + n * 12 + len(self.gap)
        strings_off = data_start + n * self.rowsize
        names = bytearray()
        seen = {}
        entries = bytearray()
        body = bytearray()
        for i, (rid, row, name) in enumerate(self.rows):
            assert len(row) == self.rowsize
            if name not in seen:
                seen[name] = strings_off + len(names)
                names += name + bytes(1)
            entries += struct.pack('<iii', rid, data_start + i * self.rowsize, seen[name])
            body += row
        h = bytearray(self.raw_header)
        struct.pack_into('<IH', h, 0, strings_off, data_start)
        struct.pack_into('<H', h, 0xA, n)
        return bytes(h + entries + self.gap + body + names + self.tail)

# ---------- FMG (DS1, version 1, UTF-16LE) ----------
class Fmg:
    def __init__(self, data):
        self.head = bytes(data[:0xC])
        assert data[2] == 1, 'only FMG v1'
        groups, nstr, soff = struct.unpack_from('<iii', data, 0xC)
        self.entries = {}  # id -> str or None, in id order
        for g in range(groups):
            first_idx, first_id, last_id = struct.unpack_from('<iii', data, 0x1C + g * 12)
            for k, eid in enumerate(range(first_id, last_id + 1)):
                off = struct.unpack_from('<i', data, soff + (first_idx + k) * 4)[0]
                if off == 0:
                    self.entries[eid] = None
                else:
                    end = off
                    while data[end:end + 2] != b'\0\0':
                        end += 2
                    self.entries[eid] = data[off:end].decode('utf-16-le')

    def build(self):
        ids = sorted(self.entries)
        groups = []
        for eid in ids:
            if groups and groups[-1][2] == eid - 1:
                groups[-1][2] = eid
            else:
                groups.append([None, eid, eid])
        idx = 0
        for g in groups:
            g[0] = idx
            idx += g[2] - g[1] + 1
        soff = 0x1C + len(groups) * 12
        text_start = soff + len(ids) * 4
        offs, text = [], bytearray()
        for eid in ids:
            s = self.entries[eid]
            if s is None:
                offs.append(0)
            else:
                offs.append(text_start + len(text))
                text += s.encode('utf-16-le') + b'\0\0'
        out = bytearray(self.head)
        out += struct.pack('<iiiii', len(groups), len(ids), soff, 0, 0)[:0x10]
        out = out[:0x1C]
        for g in groups:
            out += struct.pack('<iii', *g)
        for o in offs:
            out += struct.pack('<i', o)
        out += text
        out += bytes(-len(out) % 4)
        struct.pack_into('<i', out, 4, len(out))
        return bytes(out)
