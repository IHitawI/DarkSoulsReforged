"""Firelink hub, more residents: Andre, the female Undead Merchant, Sen's Crestfallen Merchant, Domhnall.

Same scheme as the male Undead Merchant (hub_npc.py): a copy of the NPC sits in Firelink, a MOVED
flag switches between the old place and the new one.
  Andre          - "Move to Firelink Shrine" in his menu once the Large Ember was given to him.
  female merchant - moves by herself once Capra Demon is dead.
  Crestfallen Merchant (Sen's) - moves by himself once the Iron Golem is dead.
  Domhnall       - his vanilla Firelink spot is just moved up to the bonfire.
  Giant Blacksmith (Anor Londo) - "Move to Firelink Shrine" in his menu once Ornstein and Smough are dead;
                   he works next to Andre (a flat open spot found on the Firelink navmesh, not with Gadget).
Positions were picked in game with DSR Gadget.
"""
import math
import struct
from load import *
from msb import Msb, Part, build_part, model_names, insert_model, recount_instances
from emevd import Emevd, build as build_emevd
from hub_npc import _ins, part_refs, insert_part_by_type, TEMPLATE_PART, PROP_TEMPLATE
from hub_npc_esd import MOVE_OPTION_TEXT, LEAVE_CHECK, replace_once
import hub_npc

# key: dict(src map, src entity, new entity, part name, talk ids, pos, Gadget angle, collision, moved flag,
#           boss flag that sets it, NPC state flags (first, last, dead, hostile), props from the source map)
NPCS = {
    'andre': dict(src='m10_01_00_00', ent=6190, new=1020310, name='c2640_0010', talk=101619, new_talk=102692,
                  pos=(-36.160, -56.508, 69.125), angle=199, coll='h0003B2_0000', moved=11027910, boss=None,
                  state=(1320, 1339, 1322, 1321),
                  props=[('o1252', 1020311), ('o1251', 1020312)]),   # anvil and his tools
    'female': dict(src='m10_02_00_00', ent=6240, new=1020320, name='c2510_0011', talk=102624, new_talk=102694,   # own copy: two characters can't share one talk id in a map
                   pos=(-25.240, -55.237, 63.123), angle=0, coll='h0011B2_0000', moved=11027911, boss=11010902,
                   state=(1410, 1413, 1412, 1411), props=[]),
    'sen': dict(src='m15_00_00_00', ent=6250, new=1020330, name='c0000_0090', talk=150625, new_talk=102691,
                pos=(-25.679, -54.585, 71.165), angle=324, coll='h0011B2_0000', moved=11027912, boss=11,
                state=(1420, 1429, 1422, 1421), props=[]),
    'giant': dict(src='m15_01_00_00', ent=6210, new=1020340, name='c2860_0010', talk=151621, new_talk=102695,
                  pos=(-33.0, -56.47, 63.5), angle=247, coll='h0003B2_0000', moved=11027920, boss=None,
                  state=(1360, 1363, 1362, 1361), props=[]),
}
GIANT_GATE = 11510001          # Ornstein and Smough defeated
GIANT_MOVE_TALK = 31000400     # his own "Mng, hmng?"
GIANT_GOAL = 286001            # battle AI, only in Anor Londo's luabnd
DOMHNALL = dict(ent=6261,   # c0000_0003, dialog t102626 ("Aye, siwmae"); NpcParam names are shifted
                pos=(-42.640, -59.102, 51.179), angle=350, coll='h0000B2_0000')
# the male merchant's copy gets the same hostility / death handling
MERCHANT_STATE = (hub_npc.NEW_ENTITY, (1400, 1409, 1402, 1401))
HOSTILE_EVENT, DEATH_EVENT = 11020510, 11020530   # vanilla Firelink NPC events, (entity, flags) as args
COPY_DEATH_EVENT = 11025940                         # 11025940.. one per NPC copy in Firelink

ANDRE_MOVE_TALK = 33009600
ANDRE_LINES = [
    (29000800, 'Хочешь, чтобы я перебрался в Храм Огня?', 'You want me down at Firelink Shrine?'),
    (29001401, 'С таким угольком мне не терпится взяться за дело у костра.',
               'With an ember like that, I can hardly wait to get to work by the bonfire.'),
    (29000308, None, None),   # "Hah hah hah!"
]
LARGE_EMBER_GIVEN = 350

TEXT = {}


def apply():
    tp, tl, _ = P['TalkParam']
    assert ANDRE_MOVE_TALK + len(ANDRE_LINES) not in tp
    for k, (voice, ru, en) in enumerate(ANDRE_LINES):
        row = tp.add(ANDRE_MOVE_TALK + k, tp[voice], f'[FirelinkHub] Andre {ANDRE_MOVE_TALK + k}'.encode())
        tl.set(row, 'msgId', ANDRE_MOVE_TALK + k)
        tl.set(row, 'voiceId', tl.get(tp[voice], 'voiceId'))
        TEXT[('talk', ANDRE_MOVE_TALK + k)] = {'ru': ru, 'en': en, 'copy': voice if ru is None else None}


# ---------------- map ----------------
def _names(m):
    return [Part(e).name for e in m.parts.entries]


def _find(m, ent):
    return next(Part(e) for e in m.parts.entries if Part(e).type == 2 and Part(e).entity_id == ent)


def _insert_enemy(m, entry, coll_name):
    """Insert an Enemy part after the last one; its collision index is set after the shift."""
    p = Part(entry)
    ins = max(i for i, e in enumerate(m.parts.entries) if Part(e).type == 2) + 1
    for _, ref_entry, off in part_refs(m):
        v = struct.unpack_from('<i', ref_entry, off)[0]
        if v >= ins:
            struct.pack_into('<i', ref_entry, off, v + 1)
    struct.pack_into('<i', entry, 0x08, sum(1 for e in m.parts.entries if Part(e).type == 2))
    m.parts.entries.insert(ins, entry)
    struct.pack_into('<i', entry, p.type_off + 28, _names(m).index(coll_name))


def _place(entry, pos, angle):
    struct.pack_into('<3f', entry, 0x14, *pos)
    struct.pack_into('<3f', entry, 0x20, 0.0, angle - 180.0, 0.0)   # MSB rotY: the character faces rotY + 180


def patch_firelink_msb(data, sources):
    """sources: map name -> raw MSB of the maps the NPCs come from."""
    m = Msb(data)
    tmpl = next(Part(e) for e in m.parts.entries if Part(e).name == TEMPLATE_PART)
    for key, n in NPCS.items():
        src = Msb(sources[n['src']]) if n['src'] != 'm10_02_00_00' else m
        sp = _find(src, n['ent'])
        mname = model_names(src)[sp.model_index]
        if mname not in model_names(m):
            me = src.models.entries[sp.model_index]
            insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
        assert n['name'] not in _names(m) and len(n['name']) == len(tmpl.name)
        entity = bytearray(tmpl.e[tmpl.entity_off:tmpl.type_off])
        struct.pack_into('<i', entity, 0, n['new'])
        t = list(struct.unpack_from('<16i', sp.e, sp.type_off))
        t[4] = n['new_talk']
        new = build_part(tmpl.e, n['name'], '', entity, struct.pack('<16i', *t) + bytes(sp.e[sp.type_off + 64:]))
        struct.pack_into('<i', new, 0x0C, model_names(m).index(mname))
        _place(new, n['pos'], n['angle'])
        _insert_enemy(m, new, n['coll'])
        if n['props']:
            _add_props(m, src, sp, n)
    # Domhnall: same part, new spot
    d = next(e for e in m.parts.entries if Part(e).type == 2 and Part(e).entity_id == DOMHNALL['ent'])
    _place(d, DOMHNALL['pos'], DOMHNALL['angle'])
    struct.pack_into('<i', d, Part(d).type_off + 28, _names(m).index(DOMHNALL['coll']))
    recount_instances(m)
    return m.build()


def _add_props(m, src, npc, n):
    """Copy the props around the NPC, keeping their offsets in his own frame."""
    tmpl = next(Part(e) for e in m.parts.entries if Part(e).name == PROP_TEMPLATE)
    entity = bytearray(tmpl.e[tmpl.entity_off:tmpl.type_off])
    sparts = {Part(e).name: Part(e) for e in src.parts.entries}
    smodels = model_names(src)
    rot_y = n['angle'] - 180.0
    dyaw = rot_y - npc.rot[1]
    a = math.radians(dyaw)
    for k, (pname, ent) in enumerate(n['props']):
        bp = sparts[pname]
        mname = smodels[bp.model_index]
        if mname not in model_names(m):
            me = src.models.entries[bp.model_index]
            insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
        dx, dz = bp.pos[0] - npc.pos[0], bp.pos[2] - npc.pos[2]
        # DS1 yaw turns +x towards -z: rotate the offset by the same yaw change
        x = n['pos'][0] + dx * math.cos(a) + dz * math.sin(a)
        z = n['pos'][2] - dx * math.sin(a) + dz * math.cos(a)
        y = n['pos'][1] + (bp.pos[1] - npc.pos[1])
        struct.pack_into('<i', entity, 0, ent)
        new = build_part(tmpl.e, f'{mname}_9{k:03d}', '', entity, bytes(bp.e[bp.type_off:]))
        struct.pack_into('<i', new, 0x0C, model_names(m).index(mname))
        struct.pack_into('<3f', new, 0x14, x, y, z)
        struct.pack_into('<3f', new, 0x20, bp.rot[0], bp.rot[1] + dyaw, bp.rot[2])
        insert_part_by_type(m, new, 1)
        names = [Part(e).name for e in m.parts.entries]   # floor under the new spot, not the source map's
        struct.pack_into('<i', new, Part(new).type_off + 4, names.index(n['coll']))


# ---------------- events ----------------
FIRELINK_EVENTS = {'andre': 11025910, 'female': 11025911, 'sen': 11025912, 'giant': 11025913}
SOURCE_EVENTS = {'andre': 11015961, 'sen': 11505960, 'giant': 11515960}


def _boss_prefix(edf, n):
    if n['boss'] is None:
        return []
    return [_ins(edf, 1003, 1, 1, 0, 0, n['boss']),            # boss dead -> he has moved
            _ins(edf, 2003, 2, n['moved'], 1)]


def _firelink_event(edf, key):
    n = NPCS[key]
    dead, props = n['state'][2], [e for _, e in n['props']]
    same_map = n['src'] == 'm10_02_00_00'
    off = [_ins(edf, 2004, 5, n['new'], 0)] + [_ins(edf, 2005, 3, e, 0) for e in props]
    if same_map:   # back at the old place
        off += [_ins(edf, 1003, 1, 1, 1, 0, dead), _ins(edf, 2004, 5, n['ent'], 1)]
    on = [_ins(edf, 2004, 5, n['ent'], 0)] if same_map else []
    on += [_ins(edf, 1003, 1, 1, 1, 0, dead), _ins(edf, 2004, 5, n['new'], 1)]
    on += [_ins(edf, 2005, 3, e, 1) for e in props]
    ins = _boss_prefix(edf, n) + [_ins(edf, 2005, 13, e, 1) for e in props]
    ins += [_ins(edf, 1003, 1, len(off) + 2, 1, 0, n['moved'])]
    ins += off + [_ins(edf, 3, 0, 0, 1, 0, n['moved']), _ins(edf, 1000, 4, 1)]
    ins += on + [_ins(edf, 3, 0, 0, 0, 0, n['moved']), _ins(edf, 1000, 4, 1)]
    return {'id': FIRELINK_EVENTS[key], 'rest': 0, 'ins': ins, 'params': []}


def _source_event(edf, key):
    n = NPCS[key]
    ins = _boss_prefix(edf, n) + [
        _ins(edf, 1003, 1, 2, 1, 0, n['moved']),
        _ins(edf, 3, 0, 0, 1, 0, n['moved']), _ins(edf, 1000, 4, 1),
        _ins(edf, 2004, 5, n['ent'], 0),
        _ins(edf, 3, 0, 0, 0, 0, n['moved']),
        _ins(edf, 1003, 1, 1, 1, 0, n['state'][2]),
        _ins(edf, 2004, 5, n['ent'], 1),
        _ins(edf, 1000, 4, 1)]
    return {'id': SOURCE_EVENTS[key], 'rest': 0, 'ins': ins, 'params': []}


def _start(edf, ev, event):
    assert all(e['id'] != event['id'] for e in ev.events)
    ev.events.append(event)
    next(e for e in ev.events if e['id'] == 0)['ins'].append(_ins(edf, 2000, 0, 0, event['id'], 0))


def patch_emevd(data, edf, mapname):
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    if mapname == 'm10_02_00_00':
        for key in FIRELINK_EVENTS:
            _start(edf, ev, _firelink_event(edf, key))
        # The copies' death: an own small event. Not the vanilla Firelink NPC events 11020510/11020530 in free
        # slots: 11020530 starts with "this slot's flag on -> turn the NPC into a treasure corpse", and the flags
        # of slots 20+ belong to other things - the merchant's copy lay there as a corpse with his Uchigatana.
        copies = [(NPCS[k]['new'], NPCS[k]['state']) for k in NPCS if NPCS[k]['new'] != NPCS[k]['ent']]
        for k, (ent, (first, last, dead, hostile)) in enumerate(copies + [MERCHANT_STATE]):
            _start(edf, ev, {'id': COPY_DEATH_EVENT + k, 'rest': 0, 'params': [], 'ins': [
                _ins(edf, 1003, 2, 0, 1, 0, dead),     # already dead: nothing to do
                _ins(edf, 4, 0, 0, ent, 1),            # wait for the copy's death
                _ins(edf, 2003, 2, dead, 1)]})
    for key, eid in SOURCE_EVENTS.items():
        if NPCS[key]['src'] == mapname:
            _start(edf, ev, _source_event(edf, key))
    return build_emevd(ev)


# ---------------- dialogs ----------------
def andre_burg(src):
    """t101619: 'Move to Firelink Shrine' once the Large Ember was given to him."""
    ind = ' ' * 24
    src = replace_once(src, f'{ind}AddTalkListData(7, 15000005, -1)\n',
                       f'{ind}# action:{MOVE_OPTION_TEXT}:"Move to Firelink Shrine"\n'
                       f'{ind}AddTalkListData(9, {MOVE_OPTION_TEXT}, {LARGE_EMBER_GIVEN})\n'
                       f'{ind}AddTalkListData(7, 15000005, -1)\n')
    branch = (f'{ind}elif GetTalkListEntryResult() == 9:\n'
              f'{ind}    # FirelinkHub: agrees to move\n'
              f'{ind}    TalkToPlayer({ANDRE_MOVE_TALK}, -1, -1)\n'
              f'{ind}    if IsAttackedBySomeone() or CheckSelfDeath():\n'
              f'{ind}        Goto(\'L1\')\n'
              f'{ind}    elif HasTalkEnded():\n'
              f'{ind}        SetEventFlag({NPCS["andre"]["moved"]}, FlagState.On)\n'
              f'{ind}        ForceEndTalk(0)\n'
              f'{ind}        Continue(\'mainloop\')\n'
              f'{ind}    elif {LEAVE_CHECK.format(ind=ind)}:\n'
              f'{ind}        Goto(\'L7\')\n')
    return replace_once(src, f'{ind}elif GetTalkListEntryResult() == 7:\n',
                        branch + f'{ind}elif GetTalkListEntryResult() == 7:\n')


def giant_anor_londo(src):
    """t151621: 'Move to Firelink Shrine' once Ornstein and Smough are dead."""
    ind = ' ' * 24
    nl = NL
    src = replace_once(src, f'{ind}AddTalkListData(6, 15000005, -1){nl}',
                       f'{ind}# action:{MOVE_OPTION_TEXT}:"Move to Firelink Shrine"{nl}'
                       f'{ind}AddTalkListData(9, {MOVE_OPTION_TEXT}, {GIANT_GATE}){nl}'
                       f'{ind}AddTalkListData(6, 15000005, -1){nl}')
    branch = (f'{ind}elif GetTalkListEntryResult() == 9:{nl}'
              f'{ind}    # FirelinkHub: agrees to move{nl}'
              f'{ind}    TalkToPlayer({GIANT_MOVE_TALK}, -1, -1){nl}'
              f'{ind}    if IsAttackedBySomeone() or CheckSelfDeath():{nl}'
              f'{ind}        Goto("L1"){nl}'
              f'{ind}    elif HasTalkEnded():{nl}'
              f'{ind}        SetEventFlag({NPCS["giant"]["moved"]}, FlagState.On){nl}'
              f'{ind}        ForceEndTalk(0){nl}'
              f'{ind}        Continue("mainloop"){nl}'
              f'{ind}    elif {LEAVE_CHECK.format(ind=ind)}:{nl}'
              f'{ind}        Goto("L7"){nl}')
    return replace_once(src, f'{ind}elif GetTalkListEntryResult() == 6:{nl}',
                        branch + f'{ind}elif GetTalkListEntryResult() == 6:{nl}')


NL = chr(10)


def firelink_copy(src, old, new):
    return src.replace(f't{old}', f't{new}')
