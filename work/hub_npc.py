"""Firelink hub, NPC #1: the Undead Merchant (male) moves from Undead Burg to Firelink Shrine.

After the first Bell of Awakening a "Move to Firelink Shrine" option appears in his menu (ESD).
Agreeing sets MOVED_FLAG; on the next load Undead Burg disables him and Firelink enables a copy
of him sitting by the bonfire, with his own Firelink dialog (t102690).
"""
import math
import struct
from load import *
from msb import Msb, Part, cstr, build_part, model_names, insert_model, recount_instances
import place
from emevd import Emevd, Edf, build as build_emevd, encode_args
from hub_npc_esd import MOVED_FLAG, MOVE_OPTION_TEXT, MOVE_TALK, GREET_TALK

BURG_ENTITY = 6230          # Undead Merchant (male) in m10_01
BURG_TALK = 101623
DEAD_FLAG = 1402            # merchant killed
NEW_ENTITY = 1020300        # his copy in Firelink
NEW_TALK = 102690
NEW_NAME = 'c2510_0010'
TEMPLATE_PART = 'c2750_0000'   # an NPC part of Firelink: draw groups / lighting for characters
COLLISION = 'h0000B2_0000'     # upper floor around the bonfire (navmesh n0000B2)
POS = (-48.748, -59.832, 49.965)  # picked in game with DSR Gadget (upper level, by the stone ledge)
FACE_DEG = 337.0               # DSR Gadget "Angle": the direction he looks (towards the bonfire)
SIT_ANIM = 9000
# his shop props from Undead Burg (part names there): (part, entity id, sideways m, forward m)
# offsets are in his own frame: +side = his right... as seen by a player facing him it's his left
PROPS = [
    ('o1129', 1020301, 0.0, 0.95),     # wares laid out in front of him
    ('o1156', 1020302, 0.9, 0.2),      # pickled barrel beside him
    ('o1134', 1020303, -0.95, 0.2),    # box with accessories on the other side
    ('o1133_07', 1020304, -2.2, 0.3),  # three boxes a bit further out
]
PROP_TEMPLATE = 'o0200_0000'   # object right at the Firelink bonfire: lighting ids for objects

TEXT = {}   # (fmg kind, id) -> {'ru', 'en'}; kinds: 'talk' (Conversation), 'event' (Event_text)
LAUGH = 33001104  # his "Nee hee hee"

# DS1 shows a subtitle only as long as its voice clip plays, so every line reuses one of his own
# recordings with a close meaning. (voice id, ru, en); ru=None -> reuse that vanilla line's text
# in every language.
MOVE_LINES = [
    (33000000, None, None),                                   # "Well, now..."
    (33000001, 'Раз ты прозвонил колокол, ты понимаешь, что к чему, верно?',
               'You rang that bell, so you have your wits about you, hmm?'),
    (33000003, 'У костра покупателей побольше будет. Жди меня там!',
               'More customers by the bonfire. Wait for me there!'),
    (LAUGH, None, None),
]
GREET_LINES = [
    (33000120, None, None),   # "Oh, there you are."
    (33001500, None, None),   # "It's actually quite nice here, you know?"
    (33001502, None, None),   # "I've got Yulia... And nobody pelts me with stones anymore."
    (LAUGH, None, None),
]


def apply():
    """GameParam part: TalkParam rows for the new lines; texts for menu.msgbnd."""
    tp, tl, _ = P['TalkParam']
    for base, lines in ((MOVE_TALK, MOVE_LINES), (GREET_TALK, GREET_LINES)):
        assert base + len(lines) not in tp  # a gap ends the sequence
        for k, (voice, ru, en) in enumerate(lines):
            row = tp.add(base + k, tp[voice], f'[FirelinkHub] Undead Merchant {base + k}'.encode())
            tl.set(row, 'msgId', base + k)
            tl.set(row, 'voiceId', tl.get(tp[voice], 'voiceId'))
            TEXT[('talk', base + k)] = {'ru': ru, 'en': en, 'copy': voice if ru is None else None}
    TEXT[('event', MOVE_OPTION_TEXT)] = {'ru': 'Перебраться в Храм Огня', 'en': 'Move to Firelink Shrine', 'copy': None}


# ---------------- map ----------------
def patch_firelink_msb(data, burg_data, nav):
    m = Msb(data)
    names = [cstr(e, struct.unpack_from('<i', e, 0)[0]) for e in m.parts.entries]
    models = [cstr(e, struct.unpack_from('<i', e, 0)[0]) for e in m.models.entries]
    assert NEW_NAME not in names
    tmpl = bytearray(m.parts.entries[names.index(TEMPLATE_PART)])
    p = Part(tmpl)
    assert p.type == 2 and len(p.name) == len(NEW_NAME)
    tmpl[p.i(0):p.i(0) + len(NEW_NAME)] = NEW_NAME.encode()
    model_idx = models.index('c2510')
    p.seti(0x0C, model_idx)
    p.seti(0x08, sum(1 for e in m.parts.entries if Part(e).type == 2))  # next enemy type index
    rot_y = FACE_DEG - 180.0    # MSB rotY: the character faces rotY + 180
    pos = POS
    struct.pack_into('<3f', tmpl, 0x14, *pos)
    struct.pack_into('<3f', tmpl, 0x20, 0.0, rot_y, 0.0)
    p.seti(p.entity_off, NEW_ENTITY)
    # behaviour from the Burg merchant: think / npc param, talk, collision, idle animation
    t = list(BURG_TYPE_DATA)
    t[4] = NEW_TALK
    t[7] = names.index(COLLISION)
    t[14] = SIT_ANIM
    # parts must stay grouped by type: insert right after the last Enemy and shift every
    # reference to the parts that move down by one (Players, Collisions, Navmeshes, Dummies, ...)
    ins = max(i for i, e in enumerate(m.parts.entries) if Part(e).type == 2) + 1
    for kind, entry, off in part_refs(m):
        v = struct.unpack_from('<i', entry, off)[0]
        if v >= ins:
            struct.pack_into('<i', entry, off, v + 1)
    if t[7] >= ins:
        t[7] += 1
    struct.pack_into('<16i', tmpl, p.type_off, *t)
    m.parts.entries.insert(ins, tmpl)
    add_props(m, Msb(burg_data), nav, pos, rot_y)
    recount_instances(m)
    return m.build()


def insert_part_by_type(m, entry, ptype):
    """Insert a part at the end of its type group, shifting all references to later parts."""
    ins = max(i for i, e in enumerate(m.parts.entries) if Part(e).type == ptype) + 1
    for kind, ref_entry, off in part_refs(m):
        v = struct.unpack_from('<i', ref_entry, off)[0]
        if v >= ins:
            struct.pack_into('<i', ref_entry, off, v + 1)
    struct.pack_into('<i', entry, 0x08, sum(1 for e in m.parts.entries if Part(e).type == ptype))
    m.parts.entries.insert(ins, entry)


def add_props(m, burg, nav, pos, rot_y):
    """Copy the merchant's shop props from Undead Burg around his new Firelink spot."""
    bparts = {Part(e).name: Part(e) for e in burg.parts.entries}
    bmodels = model_names(burg)
    merchant = next(Part(e) for e in burg.parts.entries if Part(e).type == 2 and Part(e).entity_id == BURG_ENTITY)
    tmpl = next(Part(e) for e in m.parts.entries if Part(e).name == PROP_TEMPLATE)
    entity = bytearray(tmpl.e[tmpl.entity_off:tmpl.type_off])
    struct.pack_into('<i', entity, 0, -1)
    dyaw = rot_y - merchant.rot[1]
    face = math.radians(FACE_DEG)
    fwd = (math.sin(face), math.cos(face))
    side = (fwd[1], -fwd[0])
    for k, (pname, ent, s_off, f_off) in enumerate(PROPS):
        bp = bparts[pname]
        mname = bmodels[bp.model_index]
        if mname not in model_names(m):
            src = burg.models.entries[bp.model_index]
            insert_model(m, src, struct.unpack_from('<i', src, 4)[0])
        x = pos[0] + s_off * side[0] + f_off * fwd[0]
        z = pos[2] + s_off * side[1] + f_off * fwd[1]
        floor = place.floor_y(nav, x, z)
        y = (floor if floor is not None else pos[1]) + (bp.pos[1] - merchant.pos[1])
        struct.pack_into('<i', entity, 0, ent)
        new = build_part(tmpl.e, f'{mname}_9{k:03d}', '', entity, bytes(bp.e[bp.type_off:]))
        struct.pack_into('<i', new, 0x0C, model_names(m).index(mname))
        struct.pack_into('<3f', new, 0x14, x, y, z)
        struct.pack_into('<3f', new, 0x20, bp.rot[0], bp.rot[1] + dyaw, bp.rot[2])
        insert_part_by_type(m, new, 1)
        # the copied collision index belongs to the Burg: point it at the floor he stands on
        names = [Part(e).name for e in m.parts.entries]
        struct.pack_into('<i', new, Part(new).type_off + 4, names.index(COLLISION))


def part_refs(m):
    """Every field that holds an index into the full parts list: (label, entry, byte offset).

    Found by checking vanilla DS1 maps: Object/DummyObject collision (type data int 1),
    Enemy/DummyEnemy collision (type data int 7), event base part index, Treasure part (type int 1),
    ObjAct part (type int 1). SpawnPoint/Navmesh events point at regions, ConnectCollision is
    collision-relative - neither moves.
    """
    refs = []
    for e in m.parts.entries:
        p = Part(e)
        if p.type in (1, 9):
            refs.append(('obj.collision', e, p.type_off + 4))
        elif p.type in (2, 10):
            refs.append(('enemy.collision', e, p.type_off + 28))
    for e in m.events.entries:
        _, _, typ, _, base_off, type_off = struct.unpack_from('<6i', e, 0)
        refs.append(('event.part', e, base_off))
        if typ in (4, 7):   # Treasure, ObjAct
            refs.append(('event.typepart', e, type_off + 4))
    return refs


def burg_type_data(data):
    m = Msb(data)
    for e in m.parts.entries:
        p = Part(e)
        if p.type == 2 and p.entity_id == BURG_ENTITY:
            t = struct.unpack_from('<16i', e, p.type_off)
            assert t[4] == BURG_TALK
            return t
    raise KeyError(BURG_ENTITY)


BURG_TYPE_DATA = None


# ---------------- events ----------------
def _ins(edf, bank, iid, *vals):
    _, args = edf.instr[(bank, iid)]
    return (bank, iid, encode_args(vals, [t for _, t in args]))


FIRELINK_EVENT = 11025900   # keeps merchant + props in sync with MOVED_FLAG (also live, for the debug menu)
BURG_EVENT = 11015960


def firelink_event(edf):
    props = [ent for _, ent, _, _ in PROPS]
    off = [_ins(edf, 2004, 5, NEW_ENTITY, 0)] + [_ins(edf, 2005, 3, e, 0) for e in props]
    on = ([_ins(edf, 1003, 1, 1, 1, 0, DEAD_FLAG), _ins(edf, 2004, 5, NEW_ENTITY, 1)]   # dead: stay hidden
          + [_ins(edf, 2005, 3, e, 1) for e in props])
    ins = [_ins(edf, 2005, 13, e, 1) for e in props]                  # props can't be smashed
    ins += [_ins(edf, 1003, 1, len(off) + 2, 1, 0, MOVED_FLAG)]       # moved -> jump to "on"
    ins += off + [_ins(edf, 3, 0, 0, 1, 0, MOVED_FLAG), _ins(edf, 1000, 4, 1)]   # wait moved, restart
    ins += on + [_ins(edf, 3, 0, 0, 0, 0, MOVED_FLAG), _ins(edf, 1000, 4, 1)]    # wait back, restart
    return {'id': FIRELINK_EVENT, 'rest': 0, 'ins': ins, 'params': []}


def burg_event(edf):
    ins = [_ins(edf, 1003, 1, 2, 1, 0, MOVED_FLAG),                    # moved -> jump to "gone"
           _ins(edf, 3, 0, 0, 1, 0, MOVED_FLAG), _ins(edf, 1000, 4, 1),  # wait moved, restart
           _ins(edf, 2004, 5, BURG_ENTITY, 0),                           # gone from the Burg
           _ins(edf, 3, 0, 0, 0, 0, MOVED_FLAG),                         # wait until sent back
           _ins(edf, 1003, 1, 1, 1, 0, DEAD_FLAG),
           _ins(edf, 2004, 5, BURG_ENTITY, 1),
           _ins(edf, 1000, 4, 1)]
    return {'id': BURG_EVENT, 'rest': 0, 'ins': ins, 'params': []}


def patch_emevd(data, edf, which):
    ev = Emevd(data)
    new = firelink_event(edf) if which == 'firelink' else burg_event(edf)
    assert all(e['id'] != new['id'] for e in ev.events)
    ev.events.append(new)
    e0 = next(e for e in ev.events if e['id'] == 0)
    e0['ins'].append(_ins(edf, 2000, 0, 0, new['id'], 0))   # start it with the map
    return build_emevd(ev)
