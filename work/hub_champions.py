"""Champions: one-off named mini-bosses, one per area, in the spirit of the Black Knights.

A champion is a tough enemy brought from another area (a Silver Knight in Darkroot, a Darkwraith in the
Catacombs, ...), recoloured for its trait (hub_elite_tex.py), with an elite trait, more HP, a boss health
bar with its name when you come close, and a fixed reward. Once killed it never comes back.

It takes the place of a regular enemy 15-60 m from a bonfire of its area on the same level (that spot is
known to be walkable): the part keeps its position, collision and patrol, and gets the champion's model,
AI, NpcParam and an entity id. The template part comes from the map where the enemy lives in vanilla.
Area scaling (SpEffect 70xx) is taken from the replaced enemy, so a Silver Knight in Darkroot hits like
a Darkroot enemy, not like one from Anor Londo.

Event per champion (in its map, id EVENT_BASE + k, its flag = "killed"):
  killed: disable it and end.  Else wait until the player is within 15 m -> health bar on;
  wait until it dies or the player is 45 m away -> bar off; alive: start over; dead: reward, end.
"""
import math, struct
from load import *
from msb import Msb, Part, model_names, insert_model, recount_instances, build_part
from emevd import Emevd, build as build_emevd
from hub_npc import _ins
import hub_elites, hub_elite_tex

EVENT_BASE = 11027540           # 11027500..530 were used by the first version: stale flags in old saves
                                # 16 slots each: events 540.., debug warps 560.., reward flags 580..
LOT_FLAG_BASE = 11027580
WARP_EVENT_BASE = 11027560      # debug: warp the player to this map's champion
# entries 16+ (NG+ ones): another block, the first one is full and its flags already live in old saves
def event_id(k):
    return EVENT_BASE + k if k < 16 else 11027300 + k


def warp_id(k):
    return WARP_EVENT_BASE + k if k < 16 else 11027340 + k


def lot_flag(k):
    return LOT_FLAG_BASE + k if k < 16 else 11027380 + k


WARP_REQUEST = 11027599         # flag set by the debug menu
NAME_BASE = 9800                # NpcName (item.msgbnd 18 / 119)
NPC_BASE = 9_500_000
HP_RATE = 2.0
SOUL_RATE = 5
NEAR, FAR = 15.0, 45.0
PLAYER = 10000

CHAMPIONS = [  # target map, template (map, npc), trait, ru, en, reward [(goods, count)]
    ('m10_01_00_00', ('m10_01_00_00', 256000), 'rage', 'Капитан Балдера', 'Balder Captain',
     [(1010, 3), (600, 3)]),
    ('m10_00_00_00', ('m15_00_00_00', 269000), 'vampire', 'Змей-отступник', 'Renegade Man-Serpent',
     [(501, 1), (1010, 2)]),
    ('m12_00_00_00', ('m15_01_00_00', 241000), 'stone', 'Заблудший серебряный рыцарь', 'Lost Silver Knight',
     [(1030, 2)]),
    ('m14_00_00_00', ('m14_00_00_00', 281000), 'plague', 'Чумной громила', 'Plague Brute',
     [(1020, 3), (602, 1)]),
    ('m15_00_00_00', ('m10_01_00_00', 279000), 'rage', 'Чёрный рыцарь-страж', 'Black Knight Warden',
     [(1030, 3)]),
    ('m13_00_00_00', ('m16_00_00_00', 239000), 'abyss', 'Гонец Бездны', 'Herald of the Abyss',
     [(1130, 2)]),
    ('m17_00_00_00', ('m15_01_00_00', 240000), 'regen', 'Безумный хранитель', 'Mad Guardian',
     [(1070, 1)]),
    ('m14_01_00_00', ('m13_00_00_00', 279020), 'stone', 'Пепельный рыцарь', 'Ashen Knight',
     [(1120, 1)]),
    # dark spirits: NPC invaders brought to new places (trait None: their own stats, the red phantom look)
    ('m10_01_00_00', ('m12_00_00_00', 6802), None, 'Тёмный дух: странствующий рыцарь', 'Dark Spirit Wandering Knight',
     [(500, 1), (1010, 2)]),
    ('m10_00_00_00', ('m12_00_00_00', 6801), None, 'Тёмный дух: мародёр', 'Dark Spirit Marauder',
     [(500, 1), (403, 1)]),
    ('m12_00_00_00', ('m10_00_00_00', 6560), None, 'Тёмный дух: Кирк, рыцарь шипов', 'Dark Spirit Kirk, Knight of Thorns',
     [(501, 1)]),
    ('m15_00_00_00', ('m14_00_00_00', 6531), None, 'Тёмный дух: Людоедка Милдред', 'Dark Spirit Maneater Mildred',
     [(501, 1), (404, 1)]),
    ('m13_00_00_00', ('m11_00_00_00', 6570), None, 'Тёмный дух: Ксантский король Иеремия', 'Dark Spirit Xanthous King Jeremiah',
     [(501, 1), (1030, 1)]),
    ('m15_01_00_00', ('m15_00_00_00', 6600), None, 'Тёмный дух: принц Рикард', 'Dark Spirit Prince Ricard',
     [(501, 1), (1030, 2)]),
    ('m17_00_00_00', ('m14_01_00_00', 6620), None, 'Тёмный дух: Дочь Хаоса', 'Dark Spirit Daughter of Chaos',
     [(501, 2)]),
    ('m14_01_00_00', ('m17_00_00_00', 6610), None, 'Тёмный дух: Кристальный рыцарь', 'Dark Spirit Crystal Knight',
     [(501, 2), (1130, 1)]),
    # NG+ only (the 7th field): more dark spirits and champions once the game has been finished
    ('m10_01_00_00', ('m10_01_00_00', 6580), None, 'Тёмный дух: Хавел Скала', 'Dark Spirit Havel the Rock',
     [(501, 2), (1070, 1)], True),
    ('m12_01_00_00', ('m12_00_00_00', 6806), None, 'Тёмный дух: вор из Сада', 'Dark Spirit Garden Thief',
     [(501, 1), (1030, 1)], True),
    ('m12_00_00_00', ('m12_00_00_00', 6804), None, 'Тёмный дух: колдун-отшельник', 'Dark Spirit Hermit Sorcerer',
     [(501, 1), (1030, 1)], True),
    ('m14_00_00_00', ('m12_00_00_00', 6805), None, 'Тёмный дух: падший клирик', 'Dark Spirit Fallen Cleric',
     [(501, 1), (1030, 1)], True),
    ('m15_00_00_00', ('m15_01_00_00', 6640), None, 'Тёмный дух: рыцарь Тёмной Луны', 'Dark Spirit Darkmoon Knight',
     [(501, 2), (1070, 1)], True),
    ('m15_01_00_00', ('m15_01_00_00', 6650), None, 'Тёмный дух: клинок Тёмной Луны', 'Dark Spirit Darkmoon Blade',
     [(501, 2), (1070, 1)], True),
    ('m13_01_00_00', ('m13_01_00_00', 6551), None, 'Тёмный дух: паладин Лирой', 'Dark Spirit Paladin Leeroy',
     [(501, 2), (1130, 1)], True),
    ('m17_00_00_00', ('m10_01_00_00', 279001), 'rage', 'Чёрный рыцарь-мститель', 'Black Knight Avenger',
     [(1130, 2)], True),
    ('m14_00_00_00', ('m16_00_00_00', 239000), 'abyss', 'Посланник Бездны', 'Envoy of the Abyss',
     [(1130, 2)], True),
    ('m12_01_00_00', ('m13_00_00_00', 279020), 'stone', 'Страж Сада', 'Warden of the Garden',
     [(1070, 1)], True),
    ('m11_00_00_00', ('m15_01_00_00', 241000), 'vampire', 'Падший серебряный рыцарь', 'Fallen Silver Knight',
     [(1070, 1), (1130, 1)], True),
]
# enemy remix: a few themed guests from other areas, plain enemies (no bar, no event): map, template, count
REMIX = [
    ('m10_00_00_00', ('m14_00_00_00', 206000), 3),   # Infested Ghouls crawl up into the Depths' sewers
    ('m12_00_00_00', ('m12_01_00_00', 413000), 2),   # Scarecrows from Oolacile wander into Darkroot Garden
    ('m14_00_00_00', ('m10_00_00_00', 327000), 2),   # Basilisks in the Blighttown swamp
    ('m13_00_00_00', ('m17_00_00_00', 237003), 1),   # a Channeler buffing the Catacombs' skeletons
    ('m15_00_00_00', ('m10_01_00_00', 252000), 2),   # Undead Assassins among the traps of Sen's Fortress
    ('m17_00_00_00', ('m15_01_00_00', 241000), 2),   # Silver Knights guard the Duke's Archives
    ('m10_01_00_00', ('m10_01_00_00', 256000), 2),   # Balder Knights come down into the Burg streets
    ('m10_01_00_00', ('m10_01_00_00', 252000), 2),   # more Undead Assassins in the Burg alleys
    ('m15_01_00_00', ('m16_00_00_00', 239000), 2),   # Darkwraiths have crept into Anor Londo
    ('m11_00_00_00', ('m11_00_00_00', 231000), 1),   # one more Crow Demon in the Painted World
    ('m13_01_00_00', ('m13_01_00_00', 295000), 1),   # a Skeleton Beast in the Tomb's dark
    ('m14_01_00_00', ('m14_01_00_00', 224001), 1),   # a Capra Demon among the Demon Ruins' demons
    ('m17_00_00_00', ('m17_00_00_00', 271000), 1),   # a Crystal Golem off its post in the Archives
    ('m12_01_00_00', ('m12_00_00_00', 233000), 2),   # Demonic Foliage spreads to Darkroot Basin
    # DLC enemies (Oolacile, Royal Wood) out in the base game
    ('m14_00_00_00', ('m12_01_00_00', 415000), 2),   # Bloatheads wade through the Blighttown swamp
    ('m13_01_00_00', ('m12_01_00_00', 416000), 2),   # Bloathead Sorcerers in the Tomb's dark
    ('m12_00_00_00', ('m12_01_00_00', 412000), 1),   # a Royal Wood Stone Guardian among Darkroot's stone knights
    ('m16_00_00_00', ('m12_01_00_00', 417100), 2),   # Humanity Phantoms drift up from the Abyss in New Londo
    ('m14_01_00_00', ('m12_01_00_00', 418000), 1),   # a Chained Prisoner in the Demon Ruins
]
REMIX_NPC_BASE = 9_600_000
REMIX_APART = 20.0
ALIAS = {'m12_00_00_01': 'm12_00_00_00'}   # Darkroot's second MSB (the DLC version) gets the same changes
MAPS = sorted({c[0] for c in CHAMPIONS} | {r[0] for r in REMIX} | {'m10_01_00_00', 'm10_00_00_00', 'm12_00_00_00',
              'm15_00_00_00', 'm15_01_00_00', 'm17_00_00_00'})   # + squads
MSB_MAPS = MAPS + sorted(ALIAS)
TEXT = {}                       # item.msgbnd: ('npcname', id) -> {'ru', 'en'}
OWN = set()                     # part names taken by champions / dark spirits
SPOTS = {}                      # k -> dict(part=name, entity, npc, new_name, ...)
LOTS = {}


def _enemy(e):
    p = Part(e)
    think, npc, talk = struct.unpack_from('<3i', e, p.type_off + 8)
    return p, think, npc, talk


def _bonfires(m, mapname):
    ents = {ent for mp, _, ent in TRAVEL if mp == mapname}
    return [Part(e).pos for e in m.parts.entries if Part(e).entity_id in ents]


TRAVEL = []                     # set by build.py: hub_travel.bonfires(...)


MAP_OF = {}
# placed as a NEW enemy on the navmesh near a bonfire instead of replacing one: en name -> (bonfire entity,
# min m, max m, NpcParam whose area scaling it takes). The Parish bonfire has no regular enemy within 57 m.
# Undead Parish: the bonfire room is tiny, so the church nave below it (navmesh search, flat 3 m around).
PLACE = {'Balder Captain': dict(pos=(10.0, 28.0, 81.0), yaw=0.0, coll='h1020B1', scale=255041)}   # the Parish church nave


def _spot(m, mapname, taken, near=None):
    MAP_OF[id(m)] = mapname
    if near:
        ent, lo, hi = near
        fires = [Part(e).pos for e in m.parts.entries if Part(e).entity_id == ent]
        best = _closest(m, fires, taken, hi, 6, lo)
        if best:
            return best[1], best[2]
    fires = _bonfires(m, mapname)
    for far, dy in ((60, 4), (120, 8), (250, 15), (400, 40)):     # widen only if nothing is close
        best = _closest(m, fires, taken, far, dy)
        if best:
            return best[1], best[2]
    return None, None


# places where a champion would be killed before the player gets there: (map, (x0, y0, z0), (x1, y1, z1))
AVOID = [('m10_01_00_00', (-10.0, 3.0, -80.0), (35.0, 22.0, 45.0)),   # Undead Burg: the Hellkite's bridge
        ]   # + boxes around the restored bonfires (hub_bonfires.avoid_boxes(), added by build.py)


ARENA_MODELS = ('c2300',)       # Titanite Demons: their arenas stay theirs (a Balder Knight walked into one)
ARENA_R, ARENA_DY = 25.0, 12.0


def arena_boxes(game, maps):
    """Boxes (AVOID) around the vanilla Titanite Demons of these maps."""
    import os
    out = []
    for mp in maps:
        path = f'{game}/map/MapStudio/{mp}.msb'
        if not os.path.exists(path):
            continue
        for e in Msb(open(path, 'rb').read()).parts.entries:
            p = Part(e)
            if p.type == 2 and p.name.startswith(ARENA_MODELS):
                x, y, z = p.pos
                out.append((mp,
                            (x - ARENA_R, y - ARENA_DY, z - ARENA_R), (x + ARENA_R, y + ARENA_DY, z + ARENA_R)))
    return out


def _avoid(mapname, pos):
    return any(mp == mapname and all(lo[i] <= pos[i] <= hi[i] for i in range(3)) for mp, lo, hi in AVOID)


APART = 35.0                    # champions / dark spirits of one map stand at least this far apart


def _closest(m, fires, taken, far, dy, near=15):
    best = None
    busy = [Part(e).pos for e in m.parts.entries if Part(e).name in taken and Part(e).name in OWN]
    for e in m.parts.entries:
        p = Part(e)
        if p.type != 2 or p.entity_id > 0 or p.name in taken:
            continue
        if any(math.dist(p.pos, b) < APART for b in busy):
            continue
        if _avoid(MAP_OF.get(id(m)), p.pos):
            continue
        _, think, npc, talk = _enemy(e)
        if talk or not hub_elites.eligible(npc):
            continue
        for f in fires:
            d = math.dist((p.pos[0], p.pos[2]), (f[0], f[2]))
            if near <= d <= far and abs(p.pos[1] - f[1]) < dy:
                score = abs(d - 30) if near == 15 else d     # a preferred bonfire: as close as allowed
                if best is None or score < best[0]:
                    best = (score, p.name, npc)
    return best


def _area_scaling(row, nl):
    return [s for s in range(8) if 7000 <= nl.get(row, f'spEffectID{s}') < 7100]


def apply(game, out_dir='out/h/chr'):
    np_, nl, _ = P['NpcParam']
    lp, ll, _ = P['ItemLotParam']
    passives = hub_elites._PASSIVES
    wanted = set()
    def place(k, entry):
        mp, (src_map, tnpc), trait, ru, en, reward, *rest = entry
        ng = bool(rest and rest[0])
        m = Msb(open(f'{game}/map/MapStudio/{mp}.msb', 'rb').read())
        taken = {name for name, _, _ in hub_elites.CHOSEN.get(mp, [])}
        taken |= {sp['part'] for sp in SPOTS.values() if sp['map'] == mp}
        insert = None
        if en in PLACE:
            pl = PLACE[en]
            insert, local_npc = (pl['pos'], pl['yaw'], pl['coll']), pl['scale']
            part = f'new:{en}'
        else:
            part, local_npc = _spot(m, mp, taken)
            if part is None:
                print('champion: no spot for', en, 'in', mp)
                return
        OWN.add(part)
        src = Msb(open(f'{game}/map/MapStudio/{src_map}.msb', 'rb').read())
        tmpl = next(Part(e) for e in src.parts.entries if Part(e).type == 2 and _enemy(e)[2] == tnpc)
        model = model_names(src)[tmpl.model_index]
        area, block = int(mp[1:3]), int(mp[4:6])
        entity = area * 100000 + block * 10000 + 9800 + k
        nid = NPC_BASE + k
        r = np_.add(nid, np_[tnpc], f'[Champion] {en}'.encode())
        nl.set(r, 'disableRespawn', 0)       # one-off through its own event flag, not the engine's
        nl.set(r, 'teamType', 0)             # hostile (the summonable copies of some NPCs are allies)
        if trait is None:                    # dark spirit: the black phantom look is the point here
            nl.set(r, 'drawType', 2)
            nl.set(r, 'getSoul', max(nl.get(r, 'getSoul'), 1000))
        else:
            nl.set(r, 'hp', round(nl.get(r, 'hp') * HP_RATE))
            nl.set(r, 'getSoul', nl.get(r, 'getSoul') * SOUL_RATE)
            nl.set(r, 'drawType', 0)
        for s in range(1, 7):
            nl.set(r, f'itemLotId_{s}', -1)
        scale = [nl.get(np_[local_npc], f'spEffectID{s}') for s in _area_scaling(np_[local_npc], nl)]
        for s in _area_scaling(r, nl):
            nl.set(r, f'spEffectID{s}', scale[0] if scale else 0)
        if trait:
            ti = hub_elites.TRAITS.index(trait)
            free = [s for s in range(8) if nl.get(r, f'spEffectID{s}') <= 0]
            for s, sid in zip(free, passives[ti]):
                nl.set(r, f'spEffectID{s}', sid)
            wanted.add((int(model[1:5]), nl.get(r, 'normalChangeTexChrId'), trait))
        lot = next(i for i in range(2800, 3000) if all(j not in lp for j in (i - 1, i, i + 1)))
        lr = lp.add(lot, lp[2510], f'[Champion] {en}'.encode())
        for s in range(1, 9):
            ll.set(lr, f'lotItemId0{s}', 0); ll.set(lr, f'lotItemCategory0{s}', 0)
            ll.set(lr, f'lotItemNum0{s}', 0); ll.set(lr, f'lotItemBasePoint0{s}', 0)
        import hub_covenants                 # covenant offerings, so covenants rank up offline
        reward = reward + (hub_covenants.DARK_SPIRIT_REWARD if trait is None else hub_covenants.CHAMPION_REWARD)
        for s, (gid, n) in enumerate(reward, 1):
            ll.set(lr, f'lotItemId0{s}', gid); ll.set(lr, f'lotItemCategory0{s}', 0x40000000)
            ll.set(lr, f'lotItemNum0{s}', n); ll.set(lr, f'lotItemBasePoint0{s}', 100)
        ll.set(lr, 'getItemFlagId', lot_flag(k))
        TEXT[('npcname', NAME_BASE + k)] = {'ru': ru, 'en': en}
        think = struct.unpack_from('<i', tmpl.e, tmpl.type_off + 8)[0]
        tp, tl, _ = P['NpcThinkParam']
        SPOTS[k] = dict(map=mp, kind='champion', tag=f'98{k:02d}', insert=insert,
                        part=part, entity=entity, npc=nid, model=model, src_map=src_map, tmpl=tmpl.name,
                        goal=tl.get(tp[think], 'battleGoalID'),
                        trait=trait, lot=lot, name=NAME_BASE + k, ng=ng)

    ng_ones = [k for k, c in enumerate(CHAMPIONS) if len(c) > 6 and c[6]]
    for k, entry in enumerate(CHAMPIONS):
        if k not in ng_ones:
            place(k, entry)
    _remix(game)
    _squads(game)
    for k in ng_ones:                  # NG+ extras last: they take what the first playthrough leaves
        place(k, CHAMPIONS[k])
    looks = {}                        # recoloured textures don't show in game (hub_elite_tex.py): not built
    for k, s in SPOTS.items():
        if s['kind'] != 'champion':
            continue
        tex = looks.get((int(s['model'][1:5]), s['trait']))
        if tex:
            nl.set(np_[s['npc']], 'normalChangeTexChrId', tex)


def patch_msb(data, mapname, sources):
    """sources: map name -> raw MSB (same folder kind), for the template parts."""
    m = Msb(data)
    done = 0
    base_map = ALIAS.get(mapname, mapname)
    for k, s in SPOTS.items():
        if s['map'] != base_map:
            continue
        src = Msb(sources[s['src_map']])
        tmpl = next(Part(e) for e in src.parts.entries if Part(e).name == s['tmpl'])
        if s.get('insert'):
            _insert_new(m, src, tmpl, s)
            done += 1
            continue
        e = next((e for e in m.parts.entries if Part(e).name == s['part']), None)
        if e is None:
            continue
        p = Part(e)
        assert s['entity'] < 0 or all(Part(x).entity_id != s['entity'] for x in m.parts.entries)
        if s['model'] not in model_names(m):
            me = src.models.entries[tmpl.model_index]
            insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
        struct.pack_into('<i', e, 0x0C, model_names(m).index(s['model']))
        think = struct.unpack_from('<i', tmpl.e, tmpl.type_off + 8)[0]
        chara_init = s.get('chara') or struct.unpack_from('<i', tmpl.e, tmpl.type_off + 24)[0]
        struct.pack_into('<2i', e, p.type_off + 8, think, s['npc'])
        struct.pack_into('<i', e, p.type_off + 24, chara_init)
        if s['entity'] > 0:
            struct.pack_into('<i', e, p.entity_off, s['entity'])
        # the name follows the model (same length): cXXXX_98kk (champions), cXXXX_97kk (remix)
        new_name = f"{s['model']}_{s['tag']}"
        assert len(new_name) == len(p.name)
        noff = p.i(0)
        e[noff:noff + len(new_name)] = new_name.encode()
        done += 1
    recount_instances(m)
    return m.build(), done


def patch_emevd(data, edf, mapname):
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    for k, s in SPOTS.items():
        if s['map'] != mapname or s['kind'] != 'champion':
            continue
        ent, name = s['entity'], s['name']
        ins = [
            _ins(edf, 1003, 1, 3, 0, 0, event_id(k)),     # not killed yet (own flag off): skip the next 3
            _ins(edf, 2004, 5, ent, 0),
            _ins(edf, 2004, 4, ent, 0),
            _ins(edf, 1000, 4, 0),
            _ins(edf, 3, 3, 0, 1, PLAYER, ent, NEAR),   # player close
            _ins(edf, 2003, 11, 1, ent, 0, name),       # boss bar with the name
            _ins(edf, 4, 0, -1, ent, 1),                # dead ...
            _ins(edf, 3, 3, -1, 0, PLAYER, ent, FAR),   # ... or the player ran away
            _ins(edf, 0, 0, 0, 1, -1),
            _ins(edf, 2003, 11, 0, ent, 0, name),
            _ins(edf, 4, 0, 1, ent, 1),
            _ins(edf, 1000, 1, 1, 1, 1),                # dead: skip the restart
            _ins(edf, 1000, 4, 1),
            _ins(edf, 2003, 36, s['lot']),             # 36: the co-op partner gets it too
            _ins(edf, 1001, 0, 3.0),                    # let the death animation play ...
            _ins(edf, 2004, 4, ent, 0),                 # ... then make sure: dead (an NPC invader got up again)
            _ins(edf, 2004, 5, ent, 0),                 # and gone
            _ins(edf, 1000, 4, 0),
        ]
        eid = event_id(k)
        if s.get('ng'):                             # NG+ only: in the first playthrough gone
            ins = [_ins(edf, 3, 17, 1, 4, 1),       # group 1: cleared the game at least once
                   _ins(edf, 1000, 1, 2, 1, 1),     # NG+: skip the two lines below
                   _ins(edf, 2004, 5, ent, 0),
                   _ins(edf, 1000, 4, 0)] + ins
        assert all(e['id'] != eid for e in ev.events)
        ev.events.append({'id': eid, 'rest': 0, 'params': [], 'ins': ins})
        e0['ins'].insert(0, _ins(edf, 2000, 0, 0, eid, 0))
        warp = [_ins(edf, 3, 0, 0, 1, 0, WARP_REQUEST),
                _ins(edf, 2003, 2, WARP_REQUEST, 0),
                _ins(edf, 2004, 3, PLAYER, 2, ent, -1),     # to the character
                _ins(edf, 1000, 4, 1)]
        ev.events.append({'id': warp_id(k), 'rest': 0, 'params': [], 'ins': warp})
        e0['ins'].insert(0, _ins(edf, 2000, 0, 0, warp_id(k), 0))
    return build_emevd(ev)


def patch_scripts(game, out_dir):
    """Copy each brought-in enemy's battle AI script (and its registry entries) into its new map's luabnd:
    a Silver Knight's script only exists in Anor Londo's archive."""
    import os, luabnd
    from souls import dcx_read, dcx_write, Bnd3
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for mp in MAPS:
        h, d = dcx_read(f'{game}/script/{mp}.luabnd.dcx')
        dst = Bnd3(d)
        added = []
        for k, s in SPOTS.items():
            if s['map'] != mp:
                continue
            _, sd = dcx_read(f"{game}/script/{s['src_map']}.luabnd.dcx")
            if luabnd.copy_goal(dst, Bnd3(sd), s['goal']):
                added.append(s['goal'])
        if added:
            dcx_write(f'{out_dir}/{mp}.luabnd.dcx', h, dst.build())
            written.append((mp, added))
    return written


def _remix(game):
    """Plain guests from other areas in place of some regular enemies, spread out, area scaling of the place."""
    import zlib
    np_, nl, _ = P['NpcParam']
    tp, tl, _ = P['NpcThinkParam']
    nid = REMIX_NPC_BASE
    for i, (mp, (src_map, tnpc), count) in enumerate(REMIX):
        m = Msb(open(f'{game}/map/MapStudio/{mp}.msb', 'rb').read())
        src = Msb(open(f'{game}/map/MapStudio/{src_map}.msb', 'rb').read())
        tmpl = next(Part(e) for e in src.parts.entries if Part(e).type == 2 and _enemy(e)[2] == tnpc)
        model = model_names(src)[tmpl.model_index]
        think = struct.unpack_from('<i', tmpl.e, tmpl.type_off + 8)[0]
        own = {sp['part'] for sp in SPOTS.values() if sp['map'] == mp}
        taken = {n for n, _, _ in hub_elites.CHOSEN.get(mp, [])} | own
        busy = [Part(e).pos for e in m.parts.entries if Part(e).name in own]
        cands = []
        for e in m.parts.entries:
            p = Part(e)
            if p.type != 2 or p.entity_id > 0 or p.name in taken:
                continue
            _, _, npc, talk = _enemy(e)
            if talk or not hub_elites.eligible(npc):
                continue
            cands.append((zlib.crc32(f'remix/{mp}/{p.name}'.encode()), p.name, npc, p.pos))
        picked = []
        for _, name, npc, pos in sorted(cands):
            if len(picked) == count:
                break
            if any(math.dist(pos, b) < REMIX_APART for b in busy):
                continue
            if _avoid(mp, pos):
                continue
            picked.append((name, npc))
            busy.append(pos)
        if not picked:                     # no free spot (Catacombs: skeletons are event-driven)
            print('remix: no spot for', model, 'in', mp)
            continue
        row = np_.add(nid, np_[tnpc], f'[Remix] {model} in {mp}'.encode())
        scale = [nl.get(np_[picked[0][1]], f'spEffectID{s}') for s in _area_scaling(np_[picked[0][1]], nl)]
        for s in _area_scaling(row, nl):
            nl.set(row, f'spEffectID{s}', scale[0] if scale else 0)
        for j, (name, _) in enumerate(picked):
            OWN.add(name)
            SPOTS[('r', i, j)] = dict(map=mp, kind='remix', tag=f'{7000 + i * 10 + j}', part=name, entity=-1,
                                      npc=nid, model=model, src_map=src_map, tmpl=tmpl.name, trait=None,
                                      goal=tl.get(tp[think], 'battleGoalID'))
        nid += 1


def _navmesh_spot(game, m, mapname, place):
    """A flat walkable spot lo..hi m from the bonfire, at its height, 3 m clear of other parts."""
    import hub_camps
    ent, lo, hi, _ = place
    fire_e = next(e for e in m.parts.entries if Part(e).entity_id == ent)
    fire = Part(fire_e)
    coll = struct.unpack_from('<i', fire_e, fire.type_off + 4)[0]
    tris = hub_camps.load_nav(game, mapname, m)
    others = [Part(e).pos for e in m.parts.entries if Part(e).type in (1, 2)]
    for r in [lo + i * 0.5 for i in range(int((hi - lo) * 2) + 1)]:
        for a in range(0, 360, 15):
            x, z = fire.pos[0] + r * math.sin(math.radians(a)), fire.pos[2] + r * math.cos(math.radians(a))
            y = hub_camps.floor_y(tris, x, z, fire.pos[1])
            if y is None or abs(y - fire.pos[1]) > 0.5:
                continue
            ring = [hub_camps.floor_y(tris, x + 1.5 * math.cos(b), z + 1.5 * math.sin(b), y) for b in (0, 1.57, 3.14, 4.71)]
            if any(v is None or abs(v - y) > 0.4 for v in ring):
                continue
            if any(math.dist((x, y, z), o) < 3.0 for o in others):
                continue
            yaw = math.degrees(math.atan2(fire.pos[0] - x, fire.pos[2] - z)) - 180    # faces the bonfire
            return (x, y, z), yaw, Part(m.parts.entries[coll]).name
    raise AssertionError(('no navmesh spot', mapname, ent))


def _insert_new(m, src, tmpl, s):
    from hub_npcs import _insert_enemy
    (x, y, z), yaw, coll_name = s['insert']
    if s['model'] not in model_names(m):
        me = src.models.entries[tmpl.model_index]
        insert_model(m, me, struct.unpack_from('<i', me, 4)[0])
    entity = bytearray(tmpl.e[tmpl.entity_off:tmpl.type_off])
    struct.pack_into('<i', entity, 0, s['entity'])
    t = list(struct.unpack_from('<16i', tmpl.e, tmpl.type_off))
    t[3], t[4] = s['npc'], 0                      # NpcParam, no talk
    t[10:16] = [-1] * 6                           # no patrol: those region indices belong to the source map
    new = build_part(tmpl.e, f"{s['model']}_{s['tag']}", '', entity,
                     struct.pack('<16i', *t) + bytes(tmpl.e[tmpl.type_off + 64:]))
    struct.pack_into('<i', new, 0x0C, model_names(m).index(s['model']))
    struct.pack_into('<3f', new, 0x14, x, y, z)
    struct.pack_into('<3f', new, 0x20, 0.0, yaw, 0.0)
    _insert_enemy(m, new, coll_name)


# ---------- squads: human NPC enemies in gear of their own (the c0000 model wears whatever CharaInitParam says)
# AI from the Forest Hunters (Darkroot): 6801 bandit, 6802 knight, 6803 archer, 6804 sorcerer, 6805 cleric, 6806 thief.
# Their stats are SL 75-80, so each squad gets a tier: 1 early, 2 mid, 3 late.
TIERS = {1: dict(soulLv=20, baseVit=12, baseWil=10, baseEnd=14, baseStr=14, baseDex=14, baseMag=10, baseFai=10,
                 baseDurability=11, up=0, souls=150),
         2: dict(soulLv=45, baseVit=18, baseWil=12, baseEnd=20, baseStr=20, baseDex=20, baseMag=14, baseFai=14,
                 baseDurability=16, up=5, souls=400),
         3: dict(up=10, souls=1000)}                       # tier 3: the Forest Hunters' own stats
ARMOR = {'knight': (390000, 391000, 392000, 393000), 'brigand': (50000, 51000, 52000, 53000),
         'leather': (-1, 211000, 212000, 213000), 'black_iron': (70000, 71000, 72000, 73000),
         'elite': (350000, 351000, 352000, 353000), 'sorcerer': (220000, 221000, 222000, 223000),
         'crystal': (130000, 131000, 132000, 133000)}
SQUADS = [  # map, AI template npc (map), tier, armor, right weapon, left weapon, members, note
    ('m10_01_00_00', 6802, 1, 'knight', 201000, 1450000, 2, 'Burg watch: knights with longsword and heater shield'),
    ('m10_00_00_00', 6801, 1, 'brigand', 701000, 1402000, 2, 'Depths marauders: brigands with battle axes'),
    ('m12_00_00_00', 6803, 2, 'leather', 1201000, 1402000, 2, 'Darkroot hunters: longbows'),
    ('m15_00_00_00', 6802, 2, 'black_iron', 350000, 1474000, 2, "Sen's sellswords in Black Iron with Zweihanders"),
    ('m15_01_00_00', 6802, 3, 'elite', 204000, 1452000, 2, 'Anor Londo elite guard: Balder side swords, tower kites'),
    ('m15_01_00_00', 6804, 3, 'sorcerer', 1300000, 1402000, 1, 'Anor Londo: a sorcerer behind the guard'),
    ('m17_00_00_00', 6804, 3, 'crystal', 1300000, 1402000, 2, "Duke's Archives: crystal-clad sorcerers"),
]
SQUAD_CHARA, SQUAD_NPC = 9200, 9_700_000
SQUAD_SOURCE = 'm12_00_00_00'                             # where the Forest Hunter parts are


def _squads(game):
    import zlib
    np_, nl, _ = P['NpcParam']
    cp, cl, _ = P['CharaInitParam']
    tp, tl, _ = P['NpcThinkParam']
    src = Msb(open(f'{game}/map/MapStudio/{SQUAD_SOURCE}.msb', 'rb').read())
    for i, (mp, tnpc, tier, armor, right, left, count, note) in enumerate(SQUADS):
        tmpl = next(Part(e) for e in src.parts.entries if Part(e).type == 2 and _enemy(e)[2] == tnpc)
        think = struct.unpack_from('<i', tmpl.e, tmpl.type_off + 8)[0]
        t = TIERS[tier]
        cid = SQUAD_CHARA + i
        c = cp.add(cid, cp[tnpc], f'[Squad] {note}'.encode())
        for k, v in t.items():
            if k in cl.slots:
                cl.set(c, k, v)
        up = t['up']
        for slot, item in zip(('equip_Helm', 'equip_Armer', 'equip_Gaunt', 'equip_Leg'), ARMOR[armor]):
            cl.set(c, slot, item + up if item > 0 else -1)
        cl.set(c, 'equip_Wep_Right', right + (up if right < 1300000 else 0))   # catalysts don't upgrade that way
        cl.set(c, 'equip_Wep_Left', left + up)
        nid = SQUAD_NPC + i
        r = np_.add(nid, np_[tnpc], f'[Squad] {note}'.encode())
        nl.set(r, 'teamType', 0)
        nl.set(r, 'disableRespawn', 0)
        nl.set(r, 'getSoul', t['souls'])
        for s in range(1, 7):
            nl.set(r, f'itemLotId_{s}', -1)
        m = Msb(open(f'{game}/map/MapStudio/{mp}.msb', 'rb').read())
        own = {sp['part'] for sp in SPOTS.values() if sp['map'] == mp}
        taken = {n for n, _, _ in hub_elites.CHOSEN.get(mp, [])} | own
        busy = [Part(e).pos for e in m.parts.entries if Part(e).name in own]
        free = []
        for e in m.parts.entries:
            p = Part(e)
            if p.type != 2 or p.entity_id > 0 or p.name in taken or _avoid(mp, p.pos):
                continue
            _, _, npc, talk = _enemy(e)
            if talk or not hub_elites.eligible(npc) or any(math.dist(p.pos, b) < REMIX_APART for b in busy):
                continue
            free.append(p)
        free.sort(key=lambda p: zlib.crc32(f'squad/{mp}/{p.name}'.encode()))
        group = None
        for c0 in free:                                      # a center with enough regular enemies close by
            near = sorted((q for q in free if q is not c0 and math.dist(q.pos, c0.pos) < 10
                           and abs(q.pos[1] - c0.pos[1]) < 2), key=lambda q: math.dist(q.pos, c0.pos))
            if len(near) >= count - 1:
                group = [c0] + near[:count - 1]
                break
        if not group:
            print('squad: no spot for', note)
            continue
        for j, p in enumerate(group):
            OWN.add(p.name)
            SPOTS[('s', i, j)] = dict(map=mp, kind='squad', tag=f'{8000 + i * 10 + j}', part=p.name, entity=-1,
                                      npc=nid, chara=cid, model='c0000', src_map=SQUAD_SOURCE, tmpl=tmpl.name,
                                      trait=None, goal=tl.get(tp[think], 'battleGoalID'))
