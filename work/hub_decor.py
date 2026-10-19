"""Firelink grows with the hub: decor groups that appear when a quest is done.

Each group sits around one NPC spot and is shown only while all its flags are on
(an NPC moved in, Yulia found, ...). Objects from other areas (Duke's Archives books, DLC candles,
Sen's crates) get their textures packed into their own objbnd (texbank.py), because Firelink only
loads the m10 area textures.
"""
import math
import struct
from load import *
from msb import Msb, Part, build_part, model_names, insert_model, recount_instances
from hub_npc import _ins, insert_part_by_type, PROP_TEMPLATE
import hub_npc, hub_npcs, hub_yulia, place

# where vanilla uses each model (map, part) - its type data is copied
SOURCE = {
    'o1150': ('m10_00_00_00', 'o1150_01'),   # barrel
    'o1133': ('m10_00_00_00', 'o1133_01'),   # three boxes
    'o1146': ('m10_01_00_00', 'o1146_01'),   # jute bags with odds and ends
    'o1145': ('m10_00_00_00', 'o1145_05'),   # flat jute bag
    'o1140': ('m10_01_00_00', 'o1140_01'),   # basket
    'o2253': ('m12_01_00_00', 'o2253'),      # candles with bags (DLC)
    'o2403': ('m12_01_00_00', 'o2403_01'),   # standing lantern (DLC)
    'o7670': ('m17_00_00_00', 'o7670_01'),   # small bookcase with books (Duke's Archives)
    'o7640': ('m17_00_00_00', 'o7640_11'),   # low shelf
    'o7630': ('m17_00_00_00', 'o7630_01'),   # chair
    'o7650': ('m17_00_00_00', 'o7650_01'),   # small pot
    'o5980': ('m15_01_00_00', 'o5980_0000'), # wooden crate
    'o5550': ('m15_00_00_00', 'o5550_0000'), # clay pot
}
FOREIGN = ['o2253', 'o2403', 'o7670', 'o7640', 'o7630', 'o7650', 'o5980', 'o5550']   # need packed textures
TEXTURE_AREAS = ('m12', 'm15', 'm17')

N = hub_npcs.NPCS
SPOT = {   # anchor: position, Gadget angle (facing), collision
    'merchant': (hub_npc.POS, hub_npc.FACE_DEG, hub_npc.COLLISION),
    'andre': (N['andre']['pos'], N['andre']['angle'], N['andre']['coll']),
    'female': (N['female']['pos'], N['female']['angle'], N['female']['coll']),
    'sen': (N['sen']['pos'], N['sen']['angle'], N['sen']['coll']),
    'domhnall': (hub_npcs.DOMHNALL['pos'], hub_npcs.DOMHNALL['angle'], hub_npcs.DOMHNALL['coll']),
}
# props: (model, sideways m (+ = NPC's right), forward m (+ = in front of him), extra yaw deg)
GROUPS = [
    ('Yulia found: candles by the merchant', 'merchant', [hub_yulia.FOUND_FLAG],
     [('o2253', 1.7, 0.5, 0), ('o2403', -3.0, 0.2, 0)]),
    ('Andre moved in: his workshop', 'andre', [N['andre']['moved']],
     [('o1150', 1.4, -0.6, 0), ('o1133', -1.6, -0.6, 0), ('o1146', 2.2, 0.2, 30)]),
    ('female merchant moved in', 'female', [N['female']['moved']],
     [('o1140', 0.9, -0.3, 0), ('o1145', -0.9, -0.3, 0), ('o7650', 1.0, 0.6, 0)]),
    ("Sen's merchant moved in", 'sen', [N['sen']['moved']],
     [('o5980', 0.9, -0.4, 0), ('o5550', -0.9, -0.3, 0), ('o2403', 0.9, 0.8, 0)]),
    ('all three moved in: a reading corner by Domhnall', 'domhnall',
     [N['andre']['moved'], N['female']['moved'], N['sen']['moved']],
     [('o7670', -1.8, -0.5, 0), ('o7640', 1.6, -0.6, 0), ('o7630', 2.6, 0.2, 180), ('o2253', -0.9, -0.7, 0)]),
]
FIRST_ENTITY = 1020400
FIRST_EVENT = 11025920


def _layout():
    """[(group index, model, entity, pos, rotY, collision)]"""
    out, ent = [], FIRST_ENTITY
    for gi, (_, spot, _, props) in enumerate(GROUPS):
        pos, face, coll = SPOT[spot]
        f = math.radians(face)
        fwd = (math.sin(f), math.cos(f))
        side = (fwd[1], -fwd[0])
        for model, s, fo, yaw in props:
            x = pos[0] + s * side[0] + fo * fwd[0]
            z = pos[2] + s * side[1] + fo * fwd[1]
            out.append((gi, model, ent, (x, z), face - 180.0 + yaw, coll))
            ent += 1
    return out


def patch_firelink_msb(data, game, sub):
    m = Msb(data)
    nav = place.load_nav(game, y_range=(-62.5, -50))
    tmpl = next(Part(e) for e in m.parts.entries if Part(e).name == PROP_TEMPLATE)
    srcs = {}
    for k, (gi, model, ent, (x, z), rot_y, coll) in enumerate(_layout()):
        mp, pname = SOURCE[model]
        if mp not in srcs:
            srcs[mp] = Msb(open(f'{game}/map/{sub}/{mp}.msb', 'rb').read())
        src = srcs[mp]
        sp = next(Part(e) for e in src.parts.entries if Part(e).name == pname)
        if model not in model_names(m):
            me = src.models.entries[sp.model_index]
            insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
        anchor_y = SPOT[GROUPS[gi][1]][0][1]
        floor = place.floor_y(nav, x, z)
        y = floor if floor is not None and abs(floor - anchor_y) < 0.6 else anchor_y
        entity = bytearray(tmpl.e[tmpl.entity_off:tmpl.type_off])
        struct.pack_into('<i', entity, 0, ent)
        typedata = bytearray(sp.e[sp.type_off:])
        new = build_part(tmpl.e, f'{model}_9{100 + k:03d}', '', entity, bytes(typedata))
        struct.pack_into('<i', new, 0x0C, model_names(m).index(model))
        struct.pack_into('<3f', new, 0x14, x, y, z)
        struct.pack_into('<3f', new, 0x20, 0.0, rot_y, 0.0)
        insert_part_by_type(m, new, 1)
        # the vanilla collision index belongs to the source map: point it at the floor under the spot
        names = [Part(e).name for e in m.parts.entries]
        struct.pack_into('<i', new, Part(new).type_off + 4, names.index(coll))
    recount_instances(m)
    return m.build()


def _event(edf, gi):
    flags = GROUPS[gi][2]
    ents = [ent for g, _, ent, *_ in _layout() if g == gi]
    on = [_ins(edf, 2005, 3, e, 1) for e in ents]
    on_wait = [_ins(edf, 3, 0, -1, 0, 0, f) for f in flags] + [_ins(edf, 0, 0, 0, 1, -1)]   # any flag off
    off = [_ins(edf, 2005, 3, e, 0) for e in ents]
    off_wait = [_ins(edf, 3, 0, 0, 1, 0, f) for f in flags]                                 # all flags on
    ins = [_ins(edf, 2005, 13, e, 1) for e in ents]     # decor can't be smashed
    n = len(flags)
    for k, f in enumerate(flags):    # any flag off -> jump to the "off" block
        ins.append(_ins(edf, 1003, 1, (n - 1 - k) + len(on) + len(on_wait) + 1, 0, 0, f))
    ins += on + on_wait + [_ins(edf, 1000, 4, 1)]
    ins += off + off_wait + [_ins(edf, 1000, 4, 1)]
    return {'id': FIRST_EVENT + gi, 'rest': 0, 'ins': ins, 'params': []}


def patch_emevd(ev, edf):
    """ev: an Emevd of m10_02 (modified in place)."""
    e0 = next(e for e in ev.events if e['id'] == 0)
    for gi in range(len(GROUPS)):
        e = _event(edf, gi)
        assert all(x['id'] != e['id'] for x in ev.events)
        ev.events.append(e)
        e0['ins'].append(_ins(edf, 2000, 0, 0, e['id'], 0))
