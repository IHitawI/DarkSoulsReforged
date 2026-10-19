"""AI script archives (script/<map>.luabnd.dcx): compiled Lua 5.0 scripts plus two registries.

  <map>.luainfo - "LUAI", version 1, count, 0; then per goal {goal id, name offset, interrupt name offset
                  (0 = none), flags u32}; then the names (offsets from the file start).
  <map>.luagnl  - u32 offsets of the global names the scripts define, a 0, then the names.
A battle script copied into another map's archive has to be registered in both, or its goal is unknown there.
"""
import struct
from souls import Bnd3


def _cs(d, o):
    return d[o:d.index(b'\0', o)]


def read_info(d):
    magic, ver, cnt, _ = struct.unpack_from('<4sIII', d, 0)
    assert magic == b'LUAI' and ver == 1
    out = []
    for i in range(cnt):
        gid, n1, n2, fl = struct.unpack_from('<iiiI', d, 16 + i * 16)
        out.append((gid, _cs(d, n1), _cs(d, n2) if n2 else None, fl))
    return out


def build_info(entries, size_like=None):
    head = struct.pack('<4sIII', b'LUAI', 1, len(entries), 0)
    pool = bytearray()
    base = 16 + 16 * len(entries)
    table = bytearray()
    for gid, name, iname, fl in entries:
        n1 = base + len(pool); pool += name + b'\0'
        n2 = 0
        if iname is not None:
            n2 = base + len(pool); pool += iname + b'\0'
        table += struct.pack('<iiiI', gid, n1, n2, fl)
    out = head + table + pool
    return bytes(out + bytes(-len(out) % 16))


def read_gnl(d):
    names, o = [], 0
    while True:
        v = struct.unpack_from('<I', d, o)[0]
        o += 4
        if v == 0:
            return names
        names.append(_cs(d, v))


def build_gnl(names):
    base = 4 * (len(names) + 1)
    offs, pool = [], bytearray()
    for n in names:
        offs.append(base + len(pool))
        pool += n + b'\0'
    out = struct.pack(f'<{len(names) + 1}I', *offs, 0) + pool
    return bytes(out + bytes(-len(out) % 16))


def _files(bnd, ext):
    return next(f for f in bnd.files if f[2].endswith(ext))


def script_name(goal):
    return f'{goal:06d}_battle.lua'.encode()


def copy_goal(dst, src, goal):
    """dst, src: Bnd3 of luabnds. Adds goal's battle script with its registry entries; False if already there."""
    name = script_name(goal)
    if any(f[2].endswith(name) for f in dst.files):
        return False
    sf = next(f for f in src.files if f[2].endswith(name))
    s_info, s_gnl = read_info(_files(src, b'.luainfo')[3]), read_gnl(_files(src, b'.luagnl')[3])
    d_info_f, d_gnl_f = _files(dst, b'.luainfo'), _files(dst, b'.luagnl')
    d_info, d_gnl = read_info(d_info_f[3]), read_gnl(d_gnl_f[3])
    d_info += [e for e in s_info if e[0] == goal]
    have = set(d_gnl)
    d_gnl += [n for n in s_gnl if n not in have and n in sf[3]]     # the globals this script defines
    d_info_f[3], d_gnl_f[3] = build_info(d_info), build_gnl(d_gnl)
    scripts = [f for f in dst.files if f[2].endswith(b'.lua')]
    new_id = max(f[1] for f in scripts) + 1
    assert all(f[1] != new_id for f in dst.files)
    path = scripts[0][2].rsplit(b'\\', 1)[0] + b'\\' + name
    at = dst.files.index(scripts[-1]) + 1
    dst.files.insert(at, [sf[0], new_id, path, sf[3]])
    return True
