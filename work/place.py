"""Placement helpers: Firelink navmesh floor height and the merchant's shop layout."""
import struct, math
from souls import dcx_read, Bnd3

def load_nav(G, y_range=(-62.5, -57.5)):
    h, d = dcx_read(G + '/map/m10_02_00_00/m10_02_00_00.nvmbnd.dcx')
    tris = []
    for f in Bnd3(d).files:
        x = f[3]
        nv, vo, nt, to = struct.unpack_from('<4i', x, 4)
        vs = [struct.unpack_from('<3f', x, vo + i * 12) for i in range(nv)]
        for i in range(nt):
            a, b, c = struct.unpack_from('<3i', x, to + i * 28)
            t = (vs[a], vs[b], vs[c])
            if y_range[0] < sum(v[1] for v in t) / 3 < y_range[1]:
                tris.append(t)
    return tris

def floor_y(tris, x, z):
    """Height of the navmesh under (x, z), or None if outside."""
    for a, b, c in tris:
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-4:
            return l1 * a[1] + l2 * b[1] + l3 * c[1]
    return None

def rotate(dx, dz, deg):
    a = math.atan2(dx, dz) + math.radians(deg)
    r = math.hypot(dx, dz)
    return r * math.sin(a), r * math.cos(a)

def facing_rot(x, z, tx, tz):
    """rotY that makes a character at (x, z) face (tx, tz) (DS1: facing angle = rotY + 180)."""
    return (math.degrees(math.atan2(tx - x, tz - z)) - 180 + 540) % 360 - 180
