"""Cut bonfires brought back.

The MSBs still hold bonfires that were cut: the bonfire object o0200_xxxx, its dialog character c1000_xxxx
(the common bonfire dialog) and the spawn point event (bonfire entity + 1000) - but both parts are
placeholders the game does not load (DummyObject, DummyEnemy), and nothing registers them (event 2009[3]).
Here the parts are moved into the real Object / Enemy groups (every part index reference shifted), each
bonfire gets a registration with a free lit flag, and the regular enemies close to its spawn point are
removed so a respawn is not a death trap.
  - on the way to a boss: registered from the start;
  - in a boss arena (the "...1950" ones, a DS3-style bonfire after the fight): registered once the boss is dead.
"""
import math, os, struct
from msb import Msb, Part, model_names
from emevd import Emevd, build as build_emevd
from hub_npc import _ins

TYPE_REAL = {9: 1, 10: 2}       # DummyObject -> Object, DummyEnemy -> Enemy
CLEAR_RADIUS, CLEAR_DY = 12.0, 5.0
NEW = [  # map, bonfire object entity, boss defeat flag it waits for (None: lit from the start), note
    dict(map='m10_01_00_00', obj=1011965, after=None, note='Undead Burg, between the Hellkite bridge and the Taurus tower'),
    dict(map='m10_01_00_00', obj=1011960, after=None, note='Lower Undead Burg, before the Capra Demon'),
    dict(map='m10_01_00_00', obj=1011966, after=None, note='Undead Parish, under the bell tower (Bell Gargoyles)'),
    dict(map='m16_00_00_00', obj=1601960, after=None, note='New Londo Ruins'),
    dict(map='m10_00_00_00', obj=1001950, after=11000001, note='Gaping Dragon arena'),
    dict(map='m10_01_00_00', obj=1011950, after=11010001, note='Bell Gargoyles roof'),
    dict(map='m11_00_00_00', obj=1101950, after=11100000, note='Crossbreed Priscilla arena'),
    dict(map='m12_00_00_00', obj=1201950, after=11200001, note="Sif's arena"),
    dict(map='m13_00_00_00', obj=1301950, after=11300001, note='Pinwheel arena'),
    dict(map='m14_00_00_00', obj=1401950, after=11400001, note="Quelaag's arena"),
    dict(map='m15_00_00_00', obj=1501950, after=11500001, note='Iron Golem, the roof'),
]
ALIAS = {'m12_00_00_01': 'm12_00_00_00'}
PLAN = {}                       # obj -> dict(flag, event, clear=[part names], spawn=(x, y, z))


def _used_numbers(game, mapname):
    used = set()
    _, d = __import__('souls').dcx_read(f'{game}/event/{mapname}.emevd.dcx')
    for e in Emevd(d).events:
        used.add(e['id'])
        for _, _, a in e['ins']:
            used.update(struct.unpack_from(f'<{len(a) // 4}i', a[:len(a) // 4 * 4]))
    return used


def prepare(game):
    """Flags, events and enemies to clear for every bonfire (from the vanilla files)."""
    import hub_elites
    taken = {}
    for b in NEW:
        mp = b['map']
        used = _used_numbers(game, mp) | taken.setdefault(mp, set())
        a, k = int(mp[1:3]), int(mp[4:6])
        base = 11000000 + (a - 10) * 100000 + k * 10000          # m10_01 -> 11010000, m15_01 -> 11510000
        flag = next(f for f in (base + x for x in range(920, 1000, 8)) if all(f + i not in used for i in range(8)))
        event = next(e for e in range(base + 5992, base + 6000) if e not in used)
        taken[mp] |= set(range(flag, flag + 8)) | {event}
        m = Msb(open(f'{game}/map/MapStudio/{mp}.msb', 'rb').read())
        spawn = None
        for e in m.events.entries:
            h = struct.unpack_from('<6i', e, 0)
            if h[2] == 8 and struct.unpack_from('<i', e, h[4] + 8)[0] == b['obj'] + 1000:
                pe = m.points.entries[struct.unpack_from('<i', e, h[5])[0]]
                spawn = struct.unpack_from('<3f', pe, 0x10)
        assert spawn, b
        clear = []
        for e in m.parts.entries:
            p = Part(e)
            if p.type != 2 or p.entity_id > 0:
                continue
            npc, talk = struct.unpack_from('<2i', e, p.type_off + 12)
            if talk or not hub_elites.eligible(npc):
                continue
            if math.dist((p.pos[0], p.pos[2]), (spawn[0], spawn[2])) < CLEAR_RADIUS and abs(p.pos[1] - spawn[1]) < CLEAR_DY:
                clear.append(p.name)
        nth = sum(1 for x in NEW[:NEW.index(b)] if x['map'] == mp)          # entities 9900 + 10 * nth + i
        PLAN[b['obj']] = dict(flag=flag, event=event, clear=clear[:10], spawn=spawn,
                              clear_base=a * 100000 + k * 10000 + 9900 + 10 * nth)


def travel_entries():
    """Rows for hub_travel / hub_camps: (map, lit flag, bonfire entity)."""
    return [(b['map'], PLAN[b['obj']]['flag'], b['obj']) for b in NEW]


def avoid_boxes():
    """Boxes (hub_champions.AVOID) around every restored bonfire: no ambush or champion right there."""
    out = []
    for b in NEW:
        x, y, z = PLAN[b['obj']]['spawn']
        out.append((b['map'], (x - 20, y - 10, z - 20), (x + 20, y + 10, z + 20)))
    return out


def _make_real(m, entry):
    """Move a Dummy part into its real type group (end of the group), keeping every reference right."""
    from hub_npc import part_refs
    p = Part(entry)
    old_type, new_type = p.type, TYPE_REAL[p.type]
    old = m.parts.entries.index(entry)
    refs = part_refs(m)
    vals = [struct.unpack_from('<i', e, off)[0] for _, e, off in refs]
    for e in m.parts.entries:
        q = Part(e)
        if q.type == old_type and q.type_index > p.type_index:
            struct.pack_into('<i', e, 0x08, q.type_index - 1)
    m.parts.entries.pop(old)
    vals = [v - 1 if v > old else (None if v == old else v) for v in vals]
    ins = max(i for i, e in enumerate(m.parts.entries) if Part(e).type == new_type) + 1
    vals = [ins if v is None else (v + 1 if v >= ins else v) for v in vals]
    for (_, e, off), v in zip(refs, vals):
        struct.pack_into('<i', e, off, v)
    struct.pack_into('<i', entry, 0x04, new_type)
    struct.pack_into('<i', entry, 0x08, sum(1 for e in m.parts.entries if Part(e).type == new_type))
    m.parts.entries.insert(ins, entry)


def patch_msb(data, mapname):
    """Make the bonfires' parts real; give the enemies to remove entity ids (the event disables them)."""
    m = Msb(data)
    base = ALIAS.get(mapname, mapname)
    done = 0
    for b in NEW:
        if b['map'] != base:
            continue
        plan = PLAN[b['obj']]
        for ent in (b['obj'], b['obj'] - 1000):
            e = next((e for e in m.parts.entries if Part(e).entity_id == ent), None)
            if e is not None and Part(e).type in TYPE_REAL:
                _make_real(m, e)
                done += 1
        for k, name in enumerate(plan['clear']):
            e = next((e for e in m.parts.entries if Part(e).name == name), None)
            if e is None or Part(e).entity_id > 0:
                continue
            struct.pack_into('<i', e, Part(e).entity_off, plan['clear_base'] + k)
            done += 1
    return m.build(), done


def patch_emevd(data, edf, mapname):
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    for b in NEW:
        if b['map'] != mapname:
            continue
        plan = PLAN[b['obj']]
        ins = [_ins(edf, 2004, 5, plan['clear_base'] + k, 0) for k in range(len(plan['clear']))]
        if b['after']:
            ins.append(_ins(edf, 3, 0, 0, 1, 0, b['after']))      # the boss is dead
        ins.append(_ins(edf, 2009, 3, plan['flag'], b['obj'], 2.0, 180.0, 0))
        assert all(e['id'] != plan['event'] for e in ev.events)
        ev.events.append({'id': plan['event'], 'rest': 0, 'params': [], 'ins': ins})
        e0['ins'].insert(0, _ins(edf, 2000, 0, 0, plan['event'], 0))
    return build_emevd(ev)
