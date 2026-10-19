"""Area texture archives (map/mXX/*.tpfbhd + .tpfbdt) and object models that carry their own textures.

Firelink only loads the m10 area textures, so an object from another area (Duke's Archives
bookshelves, DLC candles) would be drawn untextured there. pack_object() copies the textures the
model needs into its own objbnd (as oXXXX.tpf, the way vanilla objects with own textures do it).
"""
import os
import re
import struct
import zlib
from souls import Bnd3, dcx_read, dcx_write
from tpf import Tpf


def _undcx(b):
    if b[:4] == b'DCX\0':
        assert b[0x28:0x2C] == b'DFLT'
        return zlib.decompress(b[0x4C:])
    return b


def area_textures(game, area):
    """name (lower case) -> texture dict (Tpf format) for every texture of map/<area>/*.tpfbhd."""
    bank = {}
    folder = f'{game}/map/{area}'
    for f in sorted(os.listdir(folder)):
        if not f.endswith('.tpfbhd'):
            continue
        bhd = open(f'{folder}/{f}', 'rb').read()
        bdt = open(f'{folder}/{f[:-3]}bdt', 'rb').read()
        assert bhd[:4] == b'BHF3' and bhd[0xC] in (0x54, 0x74)   # both: 0x18-byte entries
        for i in range(struct.unpack_from('<i', bhd, 0x10)[0]):
            _, size, off, _, _, _ = struct.unpack_from('<IiiiiI', bhd, 0x20 + i * 0x18)
            for t in Tpf(_undcx(bdt[off:off + size])).tex:
                bank.setdefault(t['name'].lower(), t)
    return bank


def wanted_textures(flver):
    names = set()
    for m in re.finditer(rb'((?:[\x20-\x7e]\x00){3,80})\x00\x00', flver):
        s = m.group(1).decode('utf-16le').replace('\\', '/').split('/')[-1]
        if s.lower().endswith(('.tga', '.dds')):
            names.add(s[:-4].lower())
    return names


def build_tpf(head, textures):
    """A new TPF with these textures (name encoding taken from `head`, data 16-aligned)."""
    cnt = len(textures)
    utf16 = head[0xE] == 1
    names = bytearray()
    noffs = []
    base = 0x10 + cnt * 20
    for t in textures:
        noffs.append(base + len(names))
        names += t['name'].encode('utf-16-le') + b'\0\0' if utf16 else t['name'].encode('shift_jis') + b'\0'
    pos = (base + len(names) + 0xF) & ~0xF
    offs = []
    for t in textures:
        offs.append(pos)
        pos = (pos + len(t['data']) + 0xF) & ~0xF
    out = bytearray(head)
    struct.pack_into('<i', out, 4, sum(len(t['data']) for t in textures))
    struct.pack_into('<i', out, 8, cnt)
    for t, o, n in zip(textures, offs, noffs):
        out += struct.pack('<iiBBBBii', o, len(t['data']), t['fmt'], t['typ'], t['mips'], t['fl'], n, t['unk'])
    out += names
    for t, o in zip(textures, offs):
        out += bytes(o - len(out)) + t['data']
    return bytes(out)


def pack_object(game, oid, banks, out_path, tpf_head):
    """Write obj/<oid>.objbnd.dcx with the textures it needs from `banks` (list of area banks).
    Returns the texture names that could not be found anywhere."""
    h, d = dcx_read(f'{game}/obj/{oid}.objbnd.dcx')
    bnd = Bnd3(d)
    assert not any(f[1] == 100 for f in bnd.files), f'{oid} already has its own textures'
    want = set()
    for f in bnd.files:
        if f[2].decode('shift_jis').lower().endswith('.flver'):
            want |= wanted_textures(f[3])
    found, missing = [], []
    for n in sorted(want):
        t = next((b[n] for b in banks if n in b), None)
        (found if t else missing).append(t or n)
    flver = next(f for f in bnd.files if f[2].decode('shift_jis').lower().endswith('.flver'))
    path = flver[2].decode('shift_jis').rsplit('\\', 1)[0] + '\\' + oid + '.tpf'
    bnd.files.insert(0, [flver[0], 100, path.encode('shift_jis'), build_tpf(tpf_head, found)])
    dcx_write(out_path, h, bnd.build())
    return missing
