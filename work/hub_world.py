"""A busier world: ambushes behind barricades, and siege clutter on boss arenas.

Ambush: a regular enemy on the way gets two more of its kind beside it (copies of its own MSB part: same
model, AI and NpcParam) and a barricade of barrel, boxes and a crate. Up to AMBUSHES per map, far apart,
away from bonfires, champions and the Hellkite bridge.
Arena: props around the spot where a boss stands (9-16 m out), on flat floor at the boss's height.
Spots come from the map's navmesh (hub_camps.load_nav); every new part stands on the collision of the part
it was placed by. Props are m10 / Sen's / DLC objects with their textures packed (texbank), so they show anywhere.
"""
import math, struct, zlib
from msb import Msb, Part, build_part, model_names, insert_model, recount_instances
from hub_npc import insert_part_by_type
import hub_camps, hub_decor, hub_champions, hub_elites, hub_bosses

AMBUSHES = 3
BARRICADE = ['o1150', 'o1133', 'o5980']              # barrel, three boxes, wooden crate
ARENA = ['o1150', 'o5980', 'o1133', 'o1150', 'o5550']  # barrels, crate, boxes, clay pot
EXTRA_PACK = ['o1133']                                # m10 object used outside m10: textures packed too
MAPS = ['m10_00_00_00', 'm10_01_00_00', 'm11_00_00_00', 'm12_00_00_00', 'm12_00_00_01', 'm12_01_00_00',
        'm13_00_00_00', 'm13_01_00_00', 'm13_02_00_00', 'm14_00_00_00', 'm14_01_00_00', 'm15_00_00_00',
        'm15_01_00_00', 'm16_00_00_00', 'm17_00_00_00', 'm18_00_00_00']
TRAVEL = []                                          # set by build.py
ADDED = {}                                           # map -> [(kind, model, pos)]


def _base(mapname):
    return mapname[:-2] + '00' if mapname.endswith('_01') else mapname


def _flat_spots(tris, center, y0, rmin, rmax, others, count, seed, clear=1.8, flat=0.25):
    out = []
    for step in range(48):
        ang = math.radians((seed * 53 + step * 41) % 360)
        r = rmin + (rmax - rmin) * ((step * 7 + seed) % 10) / 9
        x, z = center[0] + r * math.sin(ang), center[2] + r * math.cos(ang)
        y = hub_camps.floor_y(tris, x, z, y0)
        if y is None or abs(y - y0) > 0.2:
            continue
        ring = [hub_camps.floor_y(tris, x + 0.8 * math.cos(b), z + 0.8 * math.sin(b), y) for b in (0, 1.57, 3.14, 4.71)]
        if any(v is None or abs(v - y) > flat for v in ring):
            continue
        if any(math.dist((x, y, z), o) < clear for o in others + out):
            continue
        out.append((x, y0, z))      # the anchor's height (enemy / boss stand on the floor; the navmesh only roughly)
        if len(out) == count:
            break
    return out


def _add_prop(m, model, pos, yaw, coll_name, template, sources):
    smap, pname = hub_decor.SOURCE[model]
    src = Msb(sources[smap])
    sp = next(Part(p) for p in src.parts.entries if Part(p).name == pname)
    if model not in model_names(m):
        me = src.models.entries[sp.model_index]
        insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
    entity = bytearray(template.e[template.entity_off:template.type_off])
    struct.pack_into('<i', entity, 0, -1)
    k = sum(1 for e in m.parts.entries if Part(e).name.startswith(model + '_96'))
    new = build_part(template.e, f'{model}_96{k:02d}', '', entity, bytes(sp.e[sp.type_off:]))
    struct.pack_into('<i', new, 0x04, 1)              # an object (the header came from a character part:
                                                      # its draw groups belong to this spot)
    struct.pack_into('<i', new, 0x0C, model_names(m).index(model))
    struct.pack_into('<3f', new, 0x14, *pos)
    struct.pack_into('<3f', new, 0x20, 0.0, yaw, 0.0)
    insert_part_by_type(m, new, 1)
    names = [Part(e).name for e in m.parts.entries]
    struct.pack_into('<i', new, Part(new).type_off + 4, names.index(coll_name))


def _add_enemy(m, center_e, pos, yaw, n):
    from hub_npcs import _insert_enemy
    c = Part(center_e)
    names = [Part(e).name for e in m.parts.entries]
    coll_name = names[struct.unpack_from('<i', center_e, c.type_off + 28)[0]]
    model = model_names(m)[c.model_index]
    entity = bytearray(c.e[c.entity_off:c.type_off])
    struct.pack_into('<i', entity, 0, -1)
    t = list(struct.unpack_from('<16i', c.e, c.type_off))
    t[10:16] = [-1] * 6                               # no patrol route: they hold the barricade
    new = build_part(c.e, f'{model}_95{n:02d}', '', entity, struct.pack('<16i', *t) + bytes(c.e[c.type_off + 64:]))
    struct.pack_into('<i', new, 0x0C, c.model_index)
    struct.pack_into('<3f', new, 0x14, *pos)
    struct.pack_into('<3f', new, 0x20, 0.0, yaw, 0.0)
    _insert_enemy(m, new, coll_name)


def patch_msb(data, mapname, game, sources):
    m = Msb(data)
    base = _base(mapname)
    tris = hub_camps.load_nav(game, mapname, m)
    if not tris:
        return data, 0
    added = []
    fires = [Part(e).pos for e in m.parts.entries if Part(e).entity_id in {ent for mp, _, ent in TRAVEL if mp == base}]
    own = [Part(e).pos for e in m.parts.entries if '_98' in Part(e).name or '_70' in Part(e).name or '_71' in Part(e).name]
    others = lambda: [Part(e).pos for e in m.parts.entries if Part(e).type in (1, 2)]

    # --- ambushes
    cands = []
    for e in m.parts.entries:
        p = Part(e)
        if p.type != 2 or p.entity_id > 0:
            continue
        npc, talk = struct.unpack_from('<2i', e, p.type_off + 12)
        if talk or not hub_elites.eligible(npc) or hub_champions._avoid(base, p.pos):
            continue
        if any(math.dist(p.pos, f) < 25 for f in fires) or any(math.dist(p.pos, o) < 30 for o in own):
            continue
        cands.append((zlib.crc32(f'ambush/{base}/{p.name}'.encode()), p.name))
    centers = []
    for _, name in sorted(cands):
        if len(centers) == AMBUSHES:
            break
        e = next(e for e in m.parts.entries if Part(e).name == name)
        if any(math.dist(Part(e).pos, Part(c).pos) < 40 for c in centers):
            continue
        centers.append(e)
    n = 0
    for c in centers:
        cp = Part(c)
        seed = zlib.crc32(f'{base}/{cp.name}'.encode()) % 360
        guards = _flat_spots(tris, cp.pos, cp.pos[1], 2.5, 4.5, others(), 2, seed)
        if len(guards) < 2:
            continue
        name = cp.name
        for pos in guards:
            yaw = cp.rot[1]
            _add_enemy(m, next(e for e in m.parts.entries if Part(e).name == name), pos, yaw, n)
            added.append(('enemy', name[:5], tuple(round(v, 1) for v in pos)))
            n += 1
        ce = next(e for e in m.parts.entries if Part(e).name == name)
        cpp = Part(ce)
        names = [Part(e).name for e in m.parts.entries]
        coll = names[struct.unpack_from('<i', ce, cpp.type_off + 28)[0]]
        for pos, model in zip(_flat_spots(tris, cpp.pos, cpp.pos[1], 1.6, 3.2, others(), 3, seed + 90, clear=1.4),
                              BARRICADE):
            yaw = math.degrees(math.atan2(cpp.pos[0] - pos[0], cpp.pos[2] - pos[2]))
            _add_prop(m, model, pos, yaw, coll, cpp, sources)
            added.append(('prop', model, tuple(round(v, 1) for v in pos)))

    # --- boss arenas
    for bmap, _, boss, _ in hub_bosses.BOSSES:
        if bmap != base:
            continue
        be = next((e for e in m.parts.entries if Part(e).entity_id == boss), None)
        if be is None:
            continue
        bp = Part(be)
        names = [Part(e).name for e in m.parts.entries]
        ci = struct.unpack_from('<i', be, bp.type_off + 28)[0]
        if ci < 0:
            continue
        coll = names[ci]
        seed = boss % 360
        for pos, model in zip(_flat_spots(tris, bp.pos, bp.pos[1], 9, 16, others(), len(ARENA), seed, clear=2.5), ARENA):
            yaw = math.degrees(math.atan2(bp.pos[0] - pos[0], bp.pos[2] - pos[2]))
            _add_prop(m, model, pos, yaw, coll, bp, sources)
            added.append(('arena', model, tuple(round(v, 1) for v in pos)))

    recount_instances(m)
    ADDED[mapname] = added
    return m.build(), len(added)
