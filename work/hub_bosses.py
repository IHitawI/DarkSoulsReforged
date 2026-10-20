"""Bosses' second phases: one event per boss, configured per boss in PHASES. No shared template.

A boss without an entry in PHASES is left exactly as in the game (no event at all). For a configured boss,
when its HP falls to `threshold` (once per fight; the event restarts with the map, so a new attempt starts
in phase 1 again):
  heal_to      HP fraction to heal back to (None: no heal). Host only (a client applying it too would heal
               twice in co-op). The game has no "set HP" for a character, only "+N% of max HP", so the heal
               is the gap from the threshold, then up to 4 corrections of +5% while below heal_to - 2.5%.
  name         (ru, en) new name on the boss bar, only for a real transformation (None: keep the name).
  sfx          (sfx id, dummy poly) a one-shot effect on the boss (None: nothing).
  anim         an animation of the boss's own to play (transformation, roar...) (None: nothing).
  invincible   seconds of invincibility at the transition (0: none).
  marker       always: a stat-less SpEffect (MARKER_BASE + k) the boss's AI script tests with
               ai:HasSpecialEffectId(TARGET_SELF, id) to switch behaviour (hub_bossai.py).
The universal template (heal to 60-70%, Wrath of the Gods burst, 2.5 s invincibility, "<boss> - second
phase" bar, +15% damage / stamina drain / lifesteal auras) is gone (author's decision, 2026-10-20).
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins

EVENT_BASE = 11027600           # event per boss k (the same numbers as before)
MARKER_BASE = 92700             # SpEffect per boss k: "in phase 2", no stats
HEAL_GAP, HEAL_STEP = 92740, 92739   # SpEffect per boss k: heal the gap (92740 + k); +5% correction step
NAME_BASE = 9850                # NpcName for a renamed boss k
CLIENT = 1                      # multiplayer state "client" (as the game's own ending events use it)

BOSSES = [  # map, defeat flag, boss entity, key
    ('m10_00_00_00', 11000001, 1000800, 'gaping_dragon'),
    ('m10_01_00_00', 11010901, 1010700, 'taurus'),
    ('m10_01_00_00', 11010902, 1010750, 'capra'),
    ('m11_00_00_00', 11100000, 1100160, 'priscilla'),
    ('m12_00_00_00', 11200001, 1200800, 'sif'),
    ('m12_00_00_00', 11200900, 1200801, 'butterfly'),
    ('m12_01_00_00', 11210000, 1210800, 'artorias'),
    ('m12_01_00_00', 11210001, 1210820, 'manus'),
    ('m12_01_00_00', 11210002, 1210840, 'kalameet'),
    ('m12_01_00_00', 11210005, 1210401, 'sanctuary_guardian'),
    ('m13_00_00_00', 11300001, 1300800, 'pinwheel'),
    ('m13_01_00_00', 11310001, 1310800, 'nito'),
    ('m14_00_00_00', 11400001, 1400800, 'quelaag'),
    ('m14_01_00_00', 11410900, 1410600, 'ceaseless'),
    ('m14_01_00_00', 11410901, 1410700, 'firesage'),
    ('m14_01_00_00', 11410410, 1410400, 'centipede'),
    ('m15_00_00_00', 11500001, 1500800, 'iron_golem'),
    ('m17_00_00_00', 11700001, 1700800, 'seath'),
    ('m18_00_00_00', 11800001, 1800800, 'gwyn'),
    ('m18_01_00_00', 11810900, 1810810, 'stray_demon'),
]
KEY = {key: k for k, (_, _, _, key) in enumerate(BOSSES)}

DEFAULT = dict(threshold=0.5, heal_to=None, name=None, sfx=None, anim=None, invincible=0.0)
PHASES = {  # key: overrides of DEFAULT. Only bosses whose new behaviour is ready. Heal / name: author approves.
    'taurus': dict(),           # behaviour only: jumps more (hub_bossai.py); no heal, name, effect, pause
}
MAPS = sorted({BOSSES[KEY[key]][0] for key in PHASES})
NAMES = {}                      # k -> (ru, en): the vanilla boss names (debug menu, docs)
TEXT = {}                       # item.msgbnd: ('npcname', id) -> {'ru', 'en'} for renamed bosses
BARS = {}                       # boss entity -> (bar slot, vanilla name id), from the vanilla map events


def phase(key):
    return {**DEFAULT, **PHASES[key]}


def marker(key):
    return MARKER_BASE + KEY[key]


def _bars(game):
    import struct
    from souls import dcx_read
    for mp in sorted({m for m, *_ in BOSSES}):
        for e in Emevd(dcx_read(f'{game}/event/{mp}.emevd.dcx')[1]).events:
            for b, i, a in e['ins']:
                if (b, i) == (2003, 11) and a[0] == 1:
                    BARS.setdefault(struct.unpack_from('<i', a, 4)[0], (a[8], struct.unpack_from('<h', a, 10)[0]))


def _names():
    from souls import dcx_read, Bnd3, Fmg
    out = {}
    for lang, key in (('RUSSIAN', 'ru'), ('ENGLISH', 'en')):
        _, d = dcx_read(f'orig/msg/{lang}/item.msgbnd.dcx')
        out[key] = Fmg(next(f[3] for f in Bnd3(d).files if f[1] == 18)).entries
    return out


def _self_effect(sid, src, name):
    """A SpEffect on the boss itself (targets as an NpcParam passive)."""
    sp, sl, _ = P['SpEffectParam']
    e = sp.add(sid, sp[src], name)
    for f in [f for f in sl.slots if f.startswith('effectTarget')]:
        sl.set(e, f, sl.get(sp[71100], f))
    sl.set(e, 'stateInfo', 0)
    return e, sl


def apply(game):
    _bars(game)
    names = _names()
    for k, (_, _, boss, _) in enumerate(BOSSES):
        NAMES[k] = (names['ru'][BARS[boss][1]], names['en'][BARS[boss][1]])
    for key in PHASES:
        k, cfg = KEY[key], phase(key)
        e, sl = _self_effect(marker(key), 71100, f'[Boss phase 2] {key} marker'.encode())
        sl.set(e, 'effectEndurance', -1)                       # for the rest of the fight, nothing else
        if cfg['heal_to'] is not None:
            assert cfg['heal_to'] > cfg['threshold']
            e, sl = _self_effect(HEAL_GAP + k, 1980, f'[Boss phase 2] {key} heal'.encode())
            sl.set(e, 'changeHpRate', -round((cfg['heal_to'] - cfg['threshold']) * 100, 1))   # negative = heal
        if cfg['name']:
            ru, en = cfg['name']
            TEXT[('npcname', NAME_BASE + k)] = {'ru': ru, 'en': en}
    if any(phase(key)['heal_to'] is not None for key in PHASES):
        e, sl = _self_effect(HEAL_STEP, 1980, b'[Boss phase 2] heal +5%')
        sl.set(e, 'changeHpRate', -5.0)


def phase_event(edf, key, flag, boss):
    k, cfg = KEY[key], phase(key)
    ins = [_ins(edf, 1003, 2, 0, 1, 0, flag),                   # boss already dead: end
           _ins(edf, 4, 2, 0, boss, 5, cfg['threshold'])]       # wait for HP <= threshold
    if cfg['invincible']:
        ins.append(_ins(edf, 2004, 15, boss, 1))
    if cfg['heal_to'] is not None:                              # host only: a client would heal twice
        heal = [_ins(edf, 2004, 8, boss, HEAL_GAP + k)]
        for g in (1, 2, 3, 4):                                  # corrections while still below the goal
            heal += [_ins(edf, 1001, 1, 1),                     # (the SpEffect lands next frame)
                     _ins(edf, 4, 2, g, boss, 4, cfg['heal_to'] - 0.025),
                     _ins(edf, 1000, 1, 1, 1, g),
                     _ins(edf, 2004, 8, boss, HEAL_STEP)]
        ins += [_ins(edf, 1003, 5, len(heal), CLIENT)] + heal
    if cfg['name']:
        slot, _ = BARS[boss]
        ins.append(_ins(edf, 2003, 11, 1, boss, slot, NAME_BASE + k))
    if cfg['sfx']:
        sfx, dummy = cfg['sfx']
        ins.append(_ins(edf, 2006, 3, 2, boss, dummy, sfx))
    if cfg['anim'] is not None:
        ins.append(_ins(edf, 2003, 18, boss, cfg['anim'], 0, 0, 0))
    ins.append(_ins(edf, 2004, 8, boss, marker(key)))           # the AI switches on this
    if cfg['invincible']:
        ins += [_ins(edf, 1001, 0, float(cfg['invincible'])), _ins(edf, 2004, 15, boss, 0)]
    ins.append(_ins(edf, 3, 0, 0, 1, 0, flag))                  # then idle until the boss is dead: once
    return {'id': EVENT_BASE + k, 'rest': 0, 'params': [], 'ins': ins}


def patch_map(data, edf, mapname):
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    for key in PHASES:
        m, flag, boss, _ = BOSSES[KEY[key]]
        if m != mapname:
            continue
        k = KEY[key]
        assert all(e['id'] != EVENT_BASE + k for e in ev.events)
        ev.events.append(phase_event(edf, key, flag, boss))
        e0['ins'].insert(0, _ins(edf, 2000, 0, 0, EVENT_BASE + k, 0))   # first: event 0 may wait further down
    return build_emevd(ev)
