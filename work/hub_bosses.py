"""Second boss phase: at half HP the boss stops for a moment in a Wrath of the Gods burst and comes back changed.

The burst (2.5 s of invincibility) is the telegraph; the boss heals back to 60-70% (HEAL_TO: early bosses 60,
late ones 70), the bar is renamed "<boss> - second phase", and it keeps an aura for the rest of the fight:
  rage    - +15% damage: the beasts and demons.
  abyss   - every hit drains 40 stamina and stops its regen for 2 s: Sif, Artorias, Manus, Seath.
  vampire - every hit heals it by 3% of its HP: Priscilla, Pinwheel, Nito.
The fight is ~1.1-1.2x vanilla: the old full heal (+25% damage taken) on top of Seamless Co-op's boss HP per player
made co-op bosses ~6x vanilla.
Bosses with a second phase of their own are left alone (Gargoyles, O&S, Four Kings, Bed of Chaos),
as is the tutorial Asylum Demon.
The event runs in the boss's map, restarts with the map (so a retry gets phase 1 again) and ends when the
boss is dead (its defeat flag = its vanilla boss event id).
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins
import hub_elites

PHASE_SP = {'rage': 92700, 'abyss': 92710, 'vampire': 92720}
VAMPIRE_HEAL = 92721
EVENT_BASE = 11027600
BURST_SFX = 20176               # Wrath of the Gods shockwave
INVINCIBLE = 2.5
PLAYER = 10000
BOSSES = [  # map, defeat flag, boss entity, phase
    ('m10_00_00_00', 11000001, 1000800, 'rage'),      # Gaping Dragon
    ('m10_01_00_00', 11010901, 1010700, 'rage'),      # Taurus Demon
    ('m10_01_00_00', 11010902, 1010750, 'rage'),      # Capra Demon
    ('m11_00_00_00', 11100000, 1100160, 'vampire'),   # Crossbreed Priscilla
    ('m12_00_00_00', 11200001, 1200800, 'abyss'),     # Great Grey Wolf Sif
    ('m12_00_00_00', 11200900, 1200801, 'rage'),      # Moonlight Butterfly
    ('m12_01_00_00', 11210000, 1210800, 'abyss'),     # Knight Artorias
    ('m12_01_00_00', 11210001, 1210820, 'abyss'),     # Manus
    ('m12_01_00_00', 11210002, 1210840, 'rage'),      # Black Dragon Kalameet
    ('m12_01_00_00', 11210005, 1210401, 'rage'),      # Sanctuary Guardian
    ('m13_00_00_00', 11300001, 1300800, 'vampire'),   # Pinwheel
    ('m13_01_00_00', 11310001, 1310800, 'vampire'),   # Gravelord Nito
    ('m14_00_00_00', 11400001, 1400800, 'rage'),      # Chaos Witch Quelaag
    ('m14_01_00_00', 11410900, 1410600, 'rage'),      # Ceaseless Discharge
    ('m14_01_00_00', 11410901, 1410700, 'rage'),      # Demon Firesage
    ('m14_01_00_00', 11410410, 1410400, 'rage'),      # Centipede Demon
    ('m15_00_00_00', 11500001, 1500800, 'rage'),      # Iron Golem
    ('m17_00_00_00', 11700001, 1700800, 'abyss'),     # Seath the Scaleless
    ('m18_00_00_00', 11800001, 1800800, 'rage'),      # Gwyn, Lord of Cinder
    ('m18_01_00_00', 11810900, 1810810, 'rage'),      # Stray Demon
]
MAPS = sorted({m for m, *_ in BOSSES})


HEAL_BASE = 92730              # SpEffect 92730+k: heal boss k from 50% to HEAL_TO
HEAL_TO = {1210800: 70, 1210820: 70, 1210840: 70, 1700800: 70, 1800800: 70, 1310800: 70,   # late
           1200800: 65, 1100160: 65, 1400800: 65, 1500800: 65, 1410700: 65, 1410400: 65,   # mid
           1410600: 65, 1210401: 65, 1810810: 65}                    # everyone else (early bosses): 60
PHASE_NAME_BASE = 9850         # NpcName: "<boss> - second phase", shown on the bar in phase 2
BARS = {}                      # boss entity -> (bar slot, vanilla name id), from the vanilla map events
TEXT = {}                      # item.msgbnd: ('npcname', id) -> {'ru', 'en'}


def _bars(game):
    import os, struct
    from souls import dcx_read
    for mp in MAPS:
        for e in Emevd(dcx_read(f'{game}/event/{mp}.emevd.dcx')[1]).events:
            for b, i, a in e['ins']:
                if (b, i) == (2003, 11) and a[0] == 1:
                    BARS.setdefault(struct.unpack_from('<i', a, 4)[0], (a[8], struct.unpack_from('<h', a, 10)[0]))


def _names():
    from souls import dcx_read, Bnd3, Fmg
    out = {}
    for lang, key in (('RUSSIAN', 'ru'), ('ENGLISH', 'en')):
        _, d = dcx_read(f'orig/msg/{lang}/item.msgbnd.dcx')
        fmg = Fmg(next(f[3] for f in Bnd3(d).files if f[1] == 18))
        out[key] = fmg.entries
    return out


def apply(game):
    """Needs hub_elites.apply() first (abyss drain, rage aura)."""
    sp, sl, _ = P['SpEffectParam']
    _bars(game)
    names = _names()
    for k, (_, _, boss, _) in enumerate(BOSSES):
        _, nid = BARS[boss]
        TEXT[('npcname', PHASE_NAME_BASE + k)] = {'ru': f"{names['ru'][nid]} — вторая фаза",
                                                  'en': f"{names['en'][nid]} - Second Phase"}
    for k, (_, _, boss, _) in enumerate(BOSSES):
        e = sp.add(HEAL_BASE + k, sp[1980], b'[Boss phase 2] heal')      # applies once, at the start
        sl.set(e, 'changeHpRate', -float(HEAL_TO.get(boss, 60) - 50))     # % of max HP, negative = heal
        sl.set(e, 'stateInfo', 0)
        for f in [k for k in sl.slots if k.startswith('effectTarget')]:
            sl.set(e, f, sl.get(sp[71100], f))                           # self / AI, like NpcParam passives
    attacker = {k: sl.get(sp[2241], k) for k in sl.slots if k.startswith('effectTarget')}
    heal = sp.add(VAMPIRE_HEAL, sp[1980], b'[Boss phase 2] vampire heal')
    sl.set(heal, 'changeHpRate', -3.0)
    sl.set(heal, 'stateInfo', 0)
    for f, val in attacker.items():
        sl.set(heal, f, val)
    abyss_drain = hub_elites.SP_BASE + 10 * hub_elites.TRAITS.index('abyss') + 1
    for phase, sid in PHASE_SP.items():
        e = sp.add(sid, sp[71100], f'[Boss phase 2] {phase}'.encode())
        sl.set(e, 'effectEndurance', -1)
        rate = 1.15 if phase == 'rage' else 1.0          # abyss / vampire: their trait is the threat
        for f in ('physicsAttackPowerRate', 'magicAttackPowerRate', 'fireAttackPowerRate', 'thunderAttackPowerRate'):
            sl.set(e, f, rate)
        sl.set(e, 'stateInfo', {'rage': hub_elites.VFX_RAGE, 'abyss': 205, 'vampire': 48}[phase])
        if phase == 'abyss':
            sl.set(e, 'atkOccurrenceSpEffectId', abyss_drain)
        if phase == 'vampire':
            sl.set(e, 'atkOccurrenceSpEffectId', VAMPIRE_HEAL)


def phase_event(edf, k, flag, boss, phase):
    slot, _ = BARS[boss]
    return {'id': EVENT_BASE + k, 'rest': 0, 'params': [], 'ins': [
        _ins(edf, 1003, 2, 0, 1, 0, flag),             # boss already dead: end
        _ins(edf, 4, 2, 0, boss, 5, 0.5),              # wait for HP <= 50%
        _ins(edf, 2004, 15, boss, 1),                  # invincible during the burst
        _ins(edf, 2006, 3, 2, boss, -1, BURST_SFX),
        _ins(edf, 2006, 3, 2, PLAYER, 220, BURST_SFX),  # on the player too: bosses lack the dummies, players don't
        _ins(edf, 2004, 8, boss, HEAL_BASE + k),       # back to HEAL_TO ...
        _ins(edf, 2003, 11, 1, boss, slot, PHASE_NAME_BASE + k),   # ... named "<boss> - second phase"
        _ins(edf, 2004, 8, boss, PHASE_SP[phase]),
        _ins(edf, 1001, 0, INVINCIBLE),
        _ins(edf, 2004, 15, boss, 0),
        _ins(edf, 3, 0, 0, 1, 0, flag),                # then idle until the boss is dead
    ]}


def patch_map(data, edf, mapname):
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    for k, (m, flag, boss, phase) in enumerate(BOSSES):
        if m != mapname:
            continue
        assert all(e['id'] != EVENT_BASE + k for e in ev.events)
        ev.events.append(phase_event(edf, k, flag, boss, phase))
        e0['ins'].insert(0, _ins(edf, 2000, 0, 0, EVENT_BASE + k, 0))   # first: event 0 may wait further down
    return build_emevd(ev)
