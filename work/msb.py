"""DS1/DSR MSB (MSB1) reader-writer: sections of raw entries; entry-internal offsets are relative."""
import struct

PART_TYPES = {0: 'MapPiece', 1: 'Object', 2: 'Enemy', 4: 'Player', 5: 'Collision', 8: 'Navmesh',
              9: 'DummyObject', 10: 'DummyEnemy', 11: 'ConnectCollision'}


def cstr(b, o):
    return b[o:b.index(b'\0', o)].decode('shift_jis', 'replace')


class Section:
    def __init__(self, d, off):
        self.version, noff, cnt = struct.unpack_from('<3i', d, off)
        offs = struct.unpack_from(f'<{cnt}i', d, off + 12)
        self.name_bytes = d[noff:offs[0]] if cnt > 1 else d[noff:noff + 32]
        self.name = cstr(d, noff)
        self.entries = [bytearray(d[offs[i]:offs[i + 1] if offs[i + 1] else len(d)]) for i in range(cnt - 1)]
        self.next = offs[-1]

    def build(self, start, last):
        n = len(self.entries)
        head = 12 + (n + 1) * 4
        name_off = start + head
        pos = name_off + len(self.name_bytes)
        offs = []
        for e in self.entries:
            offs.append(pos)
            pos += len(e)
        nxt = 0 if last else pos
        out = bytearray(struct.pack('<3i', self.version, name_off, n + 1))
        out += struct.pack(f'<{n + 1}i', *offs, nxt)
        out += self.name_bytes
        for e in self.entries:
            out += e
        return out


class Msb:
    def __init__(self, d):
        self.sections = []
        off = 0
        while True:
            s = Section(d, off)
            self.sections.append(s)
            if s.next == 0:
                break
            off = s.next
        self.models, self.events, self.points, self.parts = self.sections

    def build(self):
        out = bytearray()
        for i, s in enumerate(self.sections):
            out += s.build(len(out), i == len(self.sections) - 1)
        return bytes(out)


class Part:
    """View over a part entry (bytearray)."""
    def __init__(self, e):
        self.e = e

    def i(self, o): return struct.unpack_from('<i', self.e, o)[0]
    def seti(self, o, v): struct.pack_into('<i', self.e, o, v)
    @property
    def name(self): return cstr(self.e, self.i(0))
    @property
    def type(self): return self.i(4)
    @property
    def type_index(self): return self.i(8)
    @property
    def model_index(self): return self.i(0xC)
    @property
    def pos(self): return struct.unpack_from('<3f', self.e, 0x14)
    @property
    def rot(self): return struct.unpack_from('<3f', self.e, 0x20)
    @property
    def entity_off(self): return self.i(0x58)
    @property
    def type_off(self): return self.i(0x5C)
    @property
    def entity_id(self): return self.i(self.entity_off)
    def enemy(self):
        o = self.type_off
        think, npc, talk = struct.unpack_from('<3i', self.e, o)
        unk_f = struct.unpack_from('<f', self.e, o + 12)[0]
        chara_init, coll = struct.unpack_from('<2i', self.e, o + 16)
        moves = struct.unpack_from('<8h', self.e, o + 24)
        tail = struct.unpack_from('<4i', self.e, o + 40) if o + 56 <= len(self.e) else None
        return dict(think=think, npc=npc, talk=talk, unk_f=unk_f, chara_init=chara_init,
                    coll=coll, moves=moves, tail=tail)


def build_part(header, name, sib, entity, typedata):
    """New part entry: header (0x64 bytes: offsets get rewritten), strings, entity data, type data."""
    e = bytearray(header[:0x64])
    nb = name.encode('shift_jis') + b'\0'
    sb = sib.encode('shift_jis') + b'\0'
    struct.pack_into('<i', e, 0x00, 0x64)
    struct.pack_into('<i', e, 0x10, 0x64 + len(nb))
    e += nb + sb
    e += bytes(-len(e) % 4)
    ent_off = len(e)
    e += entity
    type_off = len(e)
    e += typedata
    struct.pack_into('<ii', e, 0x58, ent_off, type_off)
    return e


def model_names(m):
    return [cstr(e, struct.unpack_from('<i', e, 0)[0]) for e in m.models.entries]


def insert_model(m, entry, mtype):
    """Insert a model at the end of its type group; shift part model indices behind it."""
    types = [struct.unpack_from('<i', e, 4)[0] for e in m.models.entries]
    ins = max(i for i, t in enumerate(types) if t == mtype) + 1
    e = bytearray(entry)
    struct.pack_into('<i', e, 8, sum(1 for t in types if t == mtype))  # type index
    struct.pack_into('<i', e, 0x10, 0)                                  # instance count, fixed later
    for pe in m.parts.entries:
        mi = struct.unpack_from('<i', pe, 0x0C)[0]
        if mi >= ins:
            struct.pack_into('<i', pe, 0x0C, mi + 1)
    m.models.entries.insert(ins, e)
    return ins


def recount_instances(m):
    from collections import Counter
    use = Counter(struct.unpack_from('<i', pe, 0x0C)[0] for pe in m.parts.entries)
    for i, e in enumerate(m.models.entries):
        struct.pack_into('<i', e, 0x10, use.get(i, 0))
