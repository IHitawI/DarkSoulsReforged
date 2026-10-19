"""Elite enemies: about one regular enemy in twelve is an elite with a trait that changes how you fight it.

An elite is a copy of its NpcParam row: recoloured textures (hub_elite_tex.py), one passive
trait effect with an aura, 3x souls and a chance of a lifegem. MSB parts pick their copy by id.
Only parts no event refers to (entity id -1) are chosen, so ambushes and scripted enemies stay as
they are. The choice is fixed per part name (crc32), so it is the same every time and in both map copies.

Traits (they change the answer, not only the numbers):
  vampire - every hit it lands heals it by 8% of its HP: don't trade hits, punish and back off.
  stone   - physical damage -50%, it doesn't stagger, magic / fire / lightning +50%: switch weapons.
  abyss   - every hit drains 40 stamina and stops stamina regen for 2 s: guarding and rolling cost more.
  regen   - heals 2% of its HP every second: burst it down, don't poke.
  plague  - every hit builds up a lot of poison: kill it fast or carry a moss clump.
  rage    - below half HP it deals +50% damage, with the Power Within aura: the telegraph is the aura.
"""
import struct, zlib
from load import *
from msb import Msb, Part, model_names
import hub_elite_tex

ENABLED = False                 # off: the recoloured looks never showed in game, and without a look an elite
                                # is just a confusing enemy. Champions (hub_champions.py) carry the idea instead.
SP_BASE = 92600                 # trait k: passive SP_BASE + 10k, on-hit effect SP_BASE + 10k + 1
VFX_BARRIER, VFX_RAGE = 254, 255   # new SpEffectVfxParam rows at dummy 220 (enemies have it; 200 is player-only)
LOT = None                      # set by apply(): one drop table for every elite
SOUL_RATE = 3
HP_RATE = 1.3
CHANCE = 12                     # one part in CHANCE
PER_MAP = 8
MAPS = ['m10_00_00_00', 'm10_01_00_00', 'm11_00_00_00', 'm12_00_00_00', 'm12_00_00_01', 'm12_01_00_00',
        'm13_00_00_00', 'm13_01_00_00', 'm13_02_00_00', 'm14_00_00_00', 'm14_01_00_00', 'm15_00_00_00',
        'm15_01_00_00', 'm16_00_00_00', 'm17_00_00_00']   # not Firelink, the Asylum or the Kiln
TRAITS = ['vampire', 'stone', 'abyss', 'regen', 'plague', 'rage']
ELITES = {}                     # (base npc id, trait index) -> elite npc id
CHOSEN = {}                     # map -> [(part name, base npc, trait)]
_PASSIVES = {}                  # trait index -> passive SpEffect ids (also used by hub_champions)
LOOKS = {}                      # (model, trait) -> texture character id
MODEL = {}                      # base npc id -> chr model id (from the MSB parts)


def elite_id(base, k):
    return 10_000_000 + base * 10 + k


def _copy(sp, template, sid, name):
    return sp.add(sid, sp[template], name.encode())


def _traits():
    sp, sl, _ = P['SpEffectParam']
    vp, vl, _ = P['SpEffectVfxParam']
    v = vp.add(VFX_BARRIER, vp[29], b'[FirelinkHub] Elite stone')
    vl.set(v, 'midstDmyId', 220)
    v = vp.add(VFX_RAGE, vp[200], b'[FirelinkHub] Elite rage')
    vl.set(v, 'midstDmyId', 220)
    attacker = {k: sl.get(sp[2241], k) for k in sl.slots if k.startswith('effectTarget')}   # on the attacker
    out = []
    for k, trait in enumerate(TRAITS):
        sid = SP_BASE + 10 * k
        e = _copy(sp, 71100, sid, f'[Elite] {trait}')
        sl.set(e, 'effectEndurance', -1)
        sl.set(e, 'maxHpRate', HP_RATE)
        if trait == 'vampire':
            sl.set(e, 'stateInfo', 48)                   # Red Tearstone glow
            h = _copy(sp, 1980, sid + 1, '[Elite] vampire heal')
            sl.set(h, 'changeHpRate', -8.0)
            sl.set(h, 'stateInfo', 0)
            for f, val in attacker.items():
                sl.set(h, f, val)
            sl.set(e, 'atkOccurrenceSpEffectId', sid + 1)
        elif trait == 'stone':
            sl.set(e, 'stateInfo', VFX_BARRIER)
            for f in ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate', 'neutralDamageCutRate'):
                sl.set(e, f, 0.5)
            for f in ('magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate'):
                sl.set(e, f, 1.5)
            sl.set(e, 'changeSuperArmorPoint', 999)
        elif trait == 'abyss':
            sl.set(e, 'stateInfo', 205)                  # Artorias' abyss aura
            h = _copy(sp, 71100, sid + 1, '[Elite] abyss drain')
            sl.set(h, 'effectEndurance', 2.0)
            sl.set(h, 'changeStaminaPoint', 40)
            sl.set(h, 'staminaRecoverChangeSpeed', -200)
            sl.set(e, 'atkOccurrenceSpEffectId', sid + 1)
        elif trait == 'regen':
            sl.set(e, 'stateInfo', 50)                   # regen glow
            sl.set(e, 'motionInterval', 1.0)
            sl.set(e, 'changeHpRate', -2.0)
        elif trait == 'plague':
            sl.set(e, 'stateInfo', 2)                    # poison bubbles
            h = _copy(sp, 4021, sid + 1, '[Elite] plague hit')
            sl.set(h, 'effectEndurance', 0.5)
            sl.set(h, 'changeHpPoint', 0)
            sl.set(h, 'poizonAttackPower', 45)
            sl.set(h, 'stateInfo', 0)
            sl.set(e, 'atkOccurrenceSpEffectId', sid + 1)
        elif trait == 'rage':
            r = _copy(sp, 71100, sid + 1, '[Elite] rage below half HP')
            sl.set(r, 'effectEndurance', -1)
            sl.set(r, 'conditionHp', 50.0)
            for f in ('physicsAttackPowerRate', 'magicAttackPowerRate', 'fireAttackPowerRate', 'thunderAttackPowerRate'):
                sl.set(r, f, 1.5)
            sl.set(r, 'stateInfo', VFX_RAGE)
            out.append((k, [sid, sid + 1]))
            continue
        out.append((k, [sid]))
    return dict(out)


def _lot():
    lp, ll, _ = P['ItemLotParam']
    lot = next(i for i in range(2750, 2900) if all(j not in lp for j in (i - 1, i, i + 1)))
    r = lp.add(lot, lp[25401000], b'[FirelinkHub] Elite drop')
    for k in range(1, 9):
        ll.set(r, f'lotItemId0{k}', 0)
        ll.set(r, f'lotItemCategory0{k}', -1 if k == 1 else 0)
        ll.set(r, f'lotItemBasePoint0{k}', 0)
        ll.set(r, f'lotItemNum0{k}', 0)
    for k, (gid, points) in enumerate([(None, 55), (600, 35), (601, 10)], 1):   # nothing, Lifegem, Radiant
        ll.set(r, f'lotItemBasePoint0{k}', points)
        if gid:
            ll.set(r, f'lotItemId0{k}', gid)
            ll.set(r, f'lotItemCategory0{k}', 0x40000000)
            ll.set(r, f'lotItemNum0{k}', 1)
    ll.set(r, 'getItemFlagId', -1)
    return lot


def eligible(npc):
    np_, nl, _ = P['NpcParam']
    if npc not in np_:
        return False
    r = np_[npc]
    return (30 <= nl.get(r, 'hp') <= 700 and nl.get(r, 'getSoul') > 0 and nl.get(r, 'drawType') == 0
            and nl.get(r, 'teamType') == 0 and not nl.get(r, 'isGhost'))


def _enemies(m):
    for e in m.parts.entries:
        p = Part(e)
        if p.type != 2 or p.entity_id > 0:
            continue
        npc, talk = struct.unpack_from('<2i', e, p.type_off + 12)
        if talk == 0 and eligible(npc):
            yield e, p, npc


def choose(mapname, data):
    picks = []
    m = Msb(data)
    models = model_names(m)
    for e, p, npc in _enemies(m):
        MODEL[npc] = int(models[p.model_index][1:5])
        h = zlib.crc32(f'{mapname}/{p.name}'.encode())
        if h % CHANCE == 0:
            picks.append((h, p.name, npc, (h // CHANCE) % len(TRAITS)))
    return [(name, npc, k) for _, name, npc, k in sorted(picks)[:PER_MAP]]


def apply(game, out_dir='out/h/chr'):
    """game: game folder (the MSBs decide which NpcParam copies are needed)."""
    global LOT
    np_, nl, _ = P['NpcParam']
    passives = _traits()
    _PASSIVES.update(passives)
    LOT = _lot()
    if not ENABLED:                   # the trait effects stay: champions use them
        return
    for mp in MAPS:
        CHOSEN[mp] = choose(mp, open(f'{game}/map/MapStudio/{mp}.msb', 'rb').read())
        for _, base, k in CHOSEN[mp]:
            if (base, k) in ELITES:
                continue
            nid = elite_id(base, k)
            r = np_.add(nid, np_[base], f'[Elite {TRAITS[k]}]'.encode())
            nl.set(r, 'getSoul', nl.get(r, 'getSoul') * SOUL_RATE)
            free = [s for s in range(8) if nl.get(r, f'spEffectID{s}') <= 0]
            assert len(free) >= len(passives[k]), (base, free)
            for s, sid in zip(free, passives[k]):
                nl.set(r, f'spEffectID{s}', sid)
            lots = [s for s in range(2, 7) if nl.get(r, f'itemLotId_{s}') <= 0]
            nl.set(r, f'itemLotId_{lots[0]}', LOT)
            ELITES[(base, k)] = nid
    # looks: a recoloured texture character per (model, trait)
    wanted = {(MODEL[b], nl.get(np_[b], 'normalChangeTexChrId'), TRAITS[k]) for b, k in ELITES}
    looks = hub_elite_tex.build(game, wanted, out_dir)
    LOOKS.update(looks)
    for (b, k), nid in ELITES.items():
        tex = looks.get((MODEL[b], TRAITS[k]))
        if tex:
            nl.set(np_[nid], 'normalChangeTexChrId', tex)
        else:                                       # no colour textures found: black phantom tint
            nl.set(np_[nid], 'drawType', 2)


def patch_msb(data, mapname):
    m = Msb(data)
    want = {name: (base, k) for name, base, k in CHOSEN.get(mapname, [])}
    done = 0
    for e, p, npc in list(_enemies(m)):
        if p.name in want and want[p.name][0] == npc:
            struct.pack_into('<i', e, p.type_off + 12, ELITES[want[p.name]])
            done += 1
    return m.build(), done
