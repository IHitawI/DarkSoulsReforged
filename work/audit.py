"""Checks the built mod (out/h) for the bugs that cost us playthroughs. Run after build.py:  python audit.py

1. Flags and event ids the mod allocates for itself must not be used by the game anywhere: its events, its
   dialogs (all of them, decompiled once into out/audit/esd), its params (shop sold-out flags, item lot flags...).
   (Found this way: travel requests on the Yulia quest flags, then on Griggs' shop flags.)
2. No two of the mod's own allocations share a number.
3. New map events: no id twice in one map, none equal to a vanilla event id.
4. Debug menu: every item / SpEffect it gives exists, every entry has a text, no slot twice in one menu.
5. Bonfire dialog: every submenu closes the list it came from (else the lists are drawn over each other).
Exit code 1 if anything is wrong.
"""
import os, re, sys, json, struct, subprocess, collections
sys.argv = [sys.argv[0]]
from souls import dcx_read, Bnd3, Param, Fmg
from emevd import Emevd, Edf, decode_args
import load
from load import P

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS REMASTERED'
ESDTOOL = os.path.abspath(os.path.join('..', 'tools_dl', 'esdtool', 'esdtool-v0.5.1', 'esdtool.exe'))
CACHE = 'out/audit'
problems = []
# module constants that name the game's own flags on purpose (read, or set like the game does): not ours to own
VANILLA_REFS = {'BELL1_FLAG', 'BELL2_FLAG', 'CAPRA_EVENT', 'GIANT_GATE', 'LORDVESSEL'}


def bad(*a):
    problems.append(a)
    print('  !!', *a)


def vanilla_numbers():
    """Every number the game itself uses as a flag / event id: {number: [where]}. Cached."""
    path = f'{CACHE}/vanilla_numbers.json'
    if os.path.exists(path):
        return {int(k): v for k, v in json.load(open(path)).items()}
    os.makedirs(f'{CACHE}/esd', exist_ok=True)
    for f in os.listdir(f'{GAME}/script/talk'):
        subprocess.run([ESDTOOL, '-ds1r', '-basedir', GAME, '-i', f'{GAME}/script/talk/{f}', '-writepy',
                        os.path.abspath(f'{CACHE}/esd/%e.py')], cwd=os.path.dirname(ESDTOOL),
                       stdin=subprocess.DEVNULL, capture_output=True)
    edf = Edf(dcx_read(f'{GAME}/event/common.emedf.dcx')[1])
    van = collections.defaultdict(set)
    for f in os.listdir(f'{GAME}/event'):
        if not f.endswith('.emevd.dcx'):
            continue
        for e in Emevd(dcx_read(f'{GAME}/event/{f}')[1]).events:
            van[e['id']].add(f'event id {f[:12]}')
            for b, i, a in e['ins']:
                try:
                    vals = decode_args(a, [t for _, t in edf.instr[(b, i)][1]])
                except Exception:
                    continue
                for x in vals:
                    if isinstance(x, int) and 1000 <= x <= 99999999:
                        van[x].add(f'emevd {f[:12]} {b}[{i}]')
    for f in os.listdir(f'{CACHE}/esd'):
        for x in re.findall(r'\b(\d{4,8})\b', open(f'{CACHE}/esd/{f}', encoding='utf-8').read()):
            van[int(x)].add(f'talk {f}')
    for pn, (p, L, _) in P.items():
        for rid, row, _ in p.rows:
            for k in (k for k in L.slots if 'flag' in k.lower()):
                try:
                    v = L.get(row, k)
                except Exception:
                    continue
                if isinstance(v, int) and v >= 1000:
                    van[v].add(f'param {pn}.{k} row {rid}')
    out = {k: sorted(v) for k, v in van.items()}
    json.dump(out, open(path, 'w'))
    return out


def own_numbers(travel):
    """Every flag / event id the mod allocates: {number: [what]}."""
    import hub_quests as Q, hub_travel, hub_champions as C, hub_estus, hub_bosses, hub_npcs, hub_npc_esd, hub_talks
    import hub_yulia, hub_spells, hub_bonfires
    own = collections.defaultdict(list)
    def add(name, ids):
        for i in ids:
            own[i].append(name)
    add('bounty paid', [Q.REWARD_FLAG + i for i in range(len(Q.BOUNTIES))])
    add('warrior pass/used', [Q.PASS_FLAG, Q.USED_FLAG])
    add('tip told', [Q.TIP_FLAG + i for i in range(len(Q.TIPS))])
    add('travel request', [hub_travel.REQUEST_BASE + k for k in range(len(travel))])
    add('travel unlock', [hub_travel.UNLOCK_REQUEST, hub_travel.UNLOCK_EVENT])
    n = len(C.CHAMPIONS)
    add('champion event', [C.event_id(k) for k in range(n)])
    add('champion warp event', [C.warp_id(k) for k in range(n)])
    add('champion lot flag', [C.lot_flag(k) for k in range(n)])
    add('champion warp request', [C.WARP_REQUEST])
    add('boss phase event', [hub_bosses.EVENT_BASE + k for k in range(len(hub_bosses.BOSSES))])
    for p in hub_bonfires.PLAN.values():
        add('restored bonfire flags', range(p['flag'], p['flag'] + 8))
        add('restored bonfire event', [p['event']])
    add('NPC copy death event', [hub_npcs.COPY_DEATH_EVENT + k for k in range(8)])
    add('NPC moved', [n_['moved'] for n_ in hub_npcs.NPCS.values()])
    add('estus shard taken', [hub_estus.FLAG_BASE + k for k in range(16)])
    for f in [f for f in os.listdir('.') if f.startswith('hub_') and f.endswith('.py')]:   # named constants
        for m in re.finditer(r'^([A-Z_0-9]+)\s*=\s*(1[0-9]{7})\b', open(f, encoding='utf-8').read(), re.M):
            if int(m.group(2)) not in own and m.group(1) not in VANILLA_REFS:
                add(f'{f}:{m.group(1)}', [int(m.group(2))])
    return own


def check_flags(travel):
    print('1-2. flags and event ids')
    van = vanilla_numbers()
    own = own_numbers(travel)
    for k in sorted(own):
        if k in van:
            bad('flag used by the game too', k, own[k], van[k][:3])
        if len(set(own[k])) > 1 and not all('restored bonfire' in x for x in own[k]):
            names = sorted(set(own[k]))
            if len({n.split(':')[0] for n in names}) > 1 and not any(n.startswith('hub_') for n in names):
                bad('two allocations share a number', k, names)
    print(f'   {len(own)} own numbers checked against {len(van)} of the game')


def check_events():
    print('3. new map events')
    van_ids = set()
    for f in os.listdir(f'{GAME}/event'):
        if f.endswith('.emevd.dcx'):
            van_ids |= {e['id'] for e in Emevd(dcx_read(f'{GAME}/event/{f}')[1]).events}
    for f in os.listdir('out/h/event'):
        ids = [e['id'] for e in Emevd(dcx_read(f'out/h/event/{f}')[1]).events]
        vanilla_here = {e['id'] for e in Emevd(dcx_read(f'{GAME}/event/{f}')[1]).events}
        for i, c in collections.Counter(ids).items():
            if c > 1:
                bad('event id twice', f, i)
        for i in set(ids) - vanilla_here:
            if i in van_ids:
                bad('new event has a vanilla event id', f, i)


def check_debug(travel):
    print('4. debug menu')
    import hub_debug, hub_bosses
    hub_bosses.apply(GAME) if not hub_bosses.TEXT else None
    hub_debug.setup(travel)
    _, gp = dcx_read('out/h/GameParam.parambnd.dcx')
    rows = {}
    for f in Bnd3(gp).files:
        rows[f[2].decode('shift_jis').split(chr(92))[-1].replace('.param', '')] = {r[0] for r in Param(f[3]).rows}
    kinds = {'Goods': 'EquipParamGoods', 'Weapon': 'EquipParamWeapon', 'Accessory': 'EquipParamAccessory'}
    _, mm = dcx_read('out/h/menu_RUSSIAN.dcx')
    ev = next(Fmg(f[3]).entries for f in Bnd3(mm).files if f[1] == 30)
    def walk(menu, path):
        slots = [s for s, *_ in menu]
        if len(slots) != len(set(slots)):
            bad('slot twice', path, slots)
        for (slot, ru, en, act), tid in zip(menu, hub_debug.TEXT_IDS[id(menu)]):
            if not ev.get(tid):
                bad('entry without text', path, slot, tid)
            if act is None:
                continue
            if act and isinstance(act[0], tuple):
                walk(act, path + [slot])
                continue
            for line in act:
                m = re.match(r'PlayerEquipmentQuantityChange\(ItemType\.(\w+), (-?\d+), (-?\d+)\)', line)
                if m and int(m.group(2)) not in rows[kinds[m.group(1)]]:
                    bad('debug gives a missing item', path, slot, line)
                m = re.match(r'GiveSpEffectToPlayer\((\d+)\)', line)
                if m and int(m.group(1)) not in rows['SpEffectParam']:
                    bad('debug gives a missing SpEffect', path, slot, line)
    walk(hub_debug.MENU, [])
    if not ev.get(hub_debug.DONE_TEXT):
        bad('no "Done" text')


def check_dialog():
    print('5. bonfire dialog: submenus close their parent list')
    # the mod's menu loops start with ClearTalkListData (the game's own start with ShowShopMessage)
    src = [l.strip() for l in open('out/esdwork/src/t100200.py', encoding='utf-8').read().splitlines()]
    for n, line in enumerate(src[:-1]):
        if line == 'while True:' and src[n + 1] == 'ClearTalkListData()':
            prev = next(l for l in reversed(src[:n]) if l and not l.startswith('#'))
            if prev != 'CloseShopMessage()':
                bad('submenu does not close its parent list', 'line', n + 1)


def _entities(paths):
    """{entity id: count} over the parts, regions and events of these MSBs."""
    from msb import Msb, Part
    out = collections.Counter()
    for path in paths:
        m = Msb(open(path, 'rb').read())
        for e in m.parts.entries:
            out[Part(e).entity_id] += 1
        for e in m.points.entries:
            eo = struct.unpack_from('<i', e, 0x34)[0]
            out[struct.unpack_from('<i', e, eo)[0]] += 1
        for e in m.events.entries:
            h = struct.unpack_from('<6i', e, 0)
            out[struct.unpack_from('<i', e, h[4] + 8)[0]] += 1
    return out


def check_entities():
    print('6. map entities: no new duplicates, every entity the mod\'s events use exists')
    edf = Edf(dcx_read(f'{GAME}/event/common.emedf.dcx')[1])
    for f in sorted(os.listdir('out/h/MapStudio')):
        a, b = _entities([f'{GAME}/map/MapStudio/{f}']), _entities([f'out/h/MapStudio/{f}'])
        for k, c in b.items():
            if k > 0 and c > 1 and c > a.get(k, 0):
                bad('entity id twice in a map', f, k)
    for f in sorted(os.listdir('out/h/event')):
        mp = f[:12]
        if not mp.startswith('m'):
            continue
        msbs = [f'out/h/MapStudio/{x}' for x in os.listdir('out/h/MapStudio') if x.startswith(mp[:6])] or \
               [f'{GAME}/map/MapStudio/{x}' for x in os.listdir(f'{GAME}/map/MapStudio') if x.startswith(mp[:6])]
        ents = _entities(msbs)
        vanilla = [ins for e in Emevd(dcx_read(f'{GAME}/event/{f}')[1]).events for ins in e['ins']]
        for e in Emevd(dcx_read(f'out/h/event/{f}')[1]).events:
            for ins in e['ins']:
                if ins in vanilla:
                    continue
                b, i, a = ins
                if (b, i) == (2000, 0):        # event start: its arguments
                    for v in struct.unpack_from(f'<{len(a) // 4}i', a)[3:]:
                        if 1000000 <= v <= 1899999 and v not in ents:
                            bad('event started with a missing entity', mp, e['id'], v)
                    continue
                name, args = edf.instr[(b, i)]
                try:
                    vals = decode_args(a, [t for _, t in args])
                except Exception:
                    continue
                for (an, _), v in zip(args, vals):
                    if 'エンティティ' in an and isinstance(v, int) and v > 0 and v != 10000 and not e['params'] \
                            and v not in ents:
                        bad('event uses a missing entity', mp, e['id'], (b, i), v)


if __name__ == '__main__':
    import hub_travel, hub_bonfires
    hub_bonfires.prepare(GAME)
    travel = hub_travel.bonfires(GAME, Edf(dcx_read(f'{GAME}/event/common.emedf.dcx')[1])) + hub_bonfires.travel_entries()
    check_flags(travel)
    check_events()
    check_debug(travel)
    check_dialog()
    check_entities()
    print('problems:', len(problems))
    sys.exit(1 if problems else 0)
