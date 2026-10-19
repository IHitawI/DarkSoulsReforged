"""A lived-in world: small travellers' camps by the bonfires.

Every bonfire outside Firelink gets two or three props around it - candles with bags, a barrel, jute bags,
sometimes a lantern - as if someone had rested there before you. Spots are picked on the map's navmesh:
3.0-4.2 m from the bonfire (not at the fire itself), flat ground around the spot (no edge, no stairs) at the bonfire's height, and
away from every other part. Props stand on the bonfire's own collision. They are breakable as usual.
The props are m10 / DLC objects: their textures are packed into their objbnds (texbank), so they show
in every area.
"""
import math, struct, zlib
from souls import dcx_read, Bnd3
from msb import Msb, Part, build_part, model_names, insert_model, recount_instances
from hub_npc import insert_part_by_type
import hub_decor

PROPS = ['o2253', 'o1146', 'o1150', 'o1145', 'o2403']     # candles with bags, jute bags, barrel, flat bag, lantern
EXTRA = ['o1146', 'o1150', 'o1145']                         # added to hub_decor.FOREIGN for texture packing
SOURCE = dict(hub_decor.SOURCE)
MAPS = ['m10_00_00_00', 'm10_01_00_00', 'm11_00_00_00', 'm12_00_00_00', 'm12_00_00_01', 'm12_01_00_00',
        'm13_00_00_00', 'm13_01_00_00', 'm13_02_00_00', 'm14_00_00_00', 'm14_01_00_00', 'm15_00_00_00',
        'm15_01_00_00', 'm16_00_00_00', 'm17_00_00_00', 'm18_00_00_00']   # not the Asylum: it looked out of place there
TRAVEL = []                     # set by build.py: hub_travel.bonfires(...)
PLACED = {}                     # map -> [(model, pos)]


def load_nav(game, mapname, m):
    """Navmesh triangles in map space. Each .nvm is local to its navmesh part in the MSB (n0000B0A17.nvm ->
    part model n0000B0): moved by that part's position and turned by its Y rotation."""
    base = mapname[:-2] + '00' if mapname.endswith('_01') else mapname
    try:
        _, d = dcx_read(f'{game}/map/{base}/{base}.nvmbnd.dcx')
    except FileNotFoundError:
        return []
    names = model_names(m)
    place = {}
    for e in m.parts.entries:
        mn = names[Part(e).model_index]
        if mn.startswith('n') and mn not in place:
            place[mn] = (Part(e).pos, Part(e).rot[1])
    tris = []
    for f in Bnd3(d).files:
        stem = f[2].decode('shift_jis').replace(chr(92), '/').split('/')[-1][:7]
        if stem not in place:
            continue
        (ox, oy, oz), ry = place[stem]
        ca, sa = math.cos(math.radians(ry)), math.sin(math.radians(ry))
        x = f[3]
        nv, vo, nt, to = struct.unpack_from('<4i', x, 4)
        vs = []
        for i in range(nv):
            vx, vy, vz = struct.unpack_from('<3f', x, vo + i * 12)
            vs.append((ox + vx * ca + vz * sa, oy + vy, oz - vx * sa + vz * ca))
        for i in range(nt):
            a, b, cc = struct.unpack_from('<3i', x, to + i * 28)
            tris.append((vs[a], vs[b], vs[cc]))
    return tris


def floor_y(tris, x, z, near_y):
    best = None
    for a, b, c in tris:
        if min(a[0], b[0], c[0]) > x or max(a[0], b[0], c[0]) < x or min(a[2], b[2], c[2]) > z or max(a[2], b[2], c[2]) < z:
            continue
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-4:
            y = l1 * a[1] + l2 * b[1] + l3 * c[1]
            if best is None or abs(y - near_y) < abs(best - near_y):
                best = y
    return best


def _spots(tris, fire, others, count, seed):
    out = []
    for step in range(24):
        ang = math.radians((seed * 37 + step * 47) % 360)
        for r in (3.4, 4.2, 3.0):
            x, z = fire[0] + r * math.sin(ang), fire[2] + r * math.cos(ang)
            y = floor_y(tris, x, z, fire[1])
            if y is None or abs(y - fire[1]) > 0.2:
                continue
            ring = [floor_y(tris, x + 0.7 * math.cos(a), z + 0.7 * math.sin(a), y) for a in (0, 1.57, 3.14, 4.71)]
            if any(v is None or abs(v - y) > 0.25 for v in ring):
                continue
            if any(math.dist((x, y, z), o) < 1.6 for o in others + [p for p in out]):
                continue
            out.append((x, fire[1], z))     # the bonfire's height: it stands on the floor, the navmesh only roughly
            break
        if len(out) == count:
            break
    return out


def patch_msb(data, mapname, game, sources):
    """sources: map -> raw MSB of the same folder kind (for the props' type data)."""
    m = Msb(data)
    base = mapname[:-2] + '00' if mapname.endswith('_01') else mapname
    fires = [(mp, ent) for mp, _, ent in TRAVEL if mp == base]
    tris = load_nav(game, mapname, m)
    if not tris or not fires:
        return data, 0
    placed = []
    for mp, ent in fires:
        e = next((e for e in m.parts.entries if Part(e).type == 1 and Part(e).entity_id == ent), None)
        if e is None:
            continue
        fire = Part(e)
        coll = struct.unpack_from('<i', e, fire.type_off + 4)[0]
        if coll < 0:
            continue
        others = [Part(x).pos for x in m.parts.entries if Part(x).type in (1, 2) and math.dist(Part(x).pos, fire.pos) < 8]
        seed = zlib.crc32(f'{mapname}/{ent}'.encode())
        count = 2 + seed % 2
        models = [PROPS[(seed // 7 + i * 3) % len(PROPS)] for i in range(count)]
        if 'o2253' not in models:
            models[0] = 'o2253'                          # always the candles: the camp's landmark
        for (x, y, z), model in zip(_spots(tris, fire.pos, others, count, seed), models):
            smap, pname = SOURCE[model]
            src = Msb(sources[smap])
            sp = next(Part(p) for p in src.parts.entries if Part(p).name == pname)
            if model not in model_names(m):
                me = src.models.entries[sp.model_index]
                insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
            entity = bytearray(fire.e[fire.entity_off:fire.type_off])
            struct.pack_into('<i', entity, 0, -1)
            k = len(placed)
            new = build_part(fire.e, f'{model}_9{500 + k:03d}', '', entity, bytes(sp.e[sp.type_off:]))
            struct.pack_into('<i', new, 0x0C, model_names(m).index(model))
            struct.pack_into('<3f', new, 0x14, x, y, z)
            yaw = math.degrees(math.atan2(fire.pos[0] - x, fire.pos[2] - z)) - 180
            struct.pack_into('<3f', new, 0x20, 0.0, yaw, 0.0)
            coll_name = Part(m.parts.entries[coll]).name
            insert_part_by_type(m, new, 1)
            names = [Part(p).name for p in m.parts.entries]
            struct.pack_into('<i', new, Part(new).type_off + 4, names.index(coll_name))
            placed.append((model, (round(x, 1), round(y, 1), round(z, 1))))
    recount_instances(m)
    PLACED[mapname] = placed
    return m.build(), len(placed)
