"""Fixes for the most cursed bits of DS1.

Capra Demon: the narrow arena with two fast dogs is a lottery right at the door. One of the two
dogs (entity 1010501) is switched off on map load; the boss event only waits for Capra's death.
Blighttown: toxin from the blowdart snipers (registIllness) and poison from the swamp and the
mosquitoes (poizonAttackPower) build up half as fast.
Soul items: the name says how many souls the item gives.
Enemies turn 35% faster while attacking: faster rolls must be timed, not spammed.
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins

CAPRA_DOG = 1010501
CAPRA_EVENT = 11015970
HALVE = {5231: 'registIllness',        # blowdart toxin
         4021: 'poizonAttackPower',    # swamp
         5027: 'poizonAttackPower',    # mosquito
         5028: 'poizonAttackPower'}    # mosquito, full
SOUL_ITEMS = list(range(400, 410)) + list(range(700, 712))
TURN_RATE = 1.35

TEXT = {}
APPEND = {}


def apply():
    sp, sl, _ = P['SpEffectParam']
    gp, gl, _ = P['EquipParamGoods']
    np_, nl, _ = P['NpcParam']
    for nid, *_ in np_.rows:
        v = nl.get(np_[nid], 'turnVellocity')
        if 0 < v < 9999:                      # 0 = can't turn, 9999 = instant: leave those
            nl.set(np_[nid], 'turnVellocity', v * TURN_RATE)
    for sid, field in HALVE.items():
        sl.set(sp[sid], field, max(1, round(sl.get(sp[sid], field) / 2)))
    for gid in SOUL_ITEMS:
        if gid not in gp or gl.get(gp[gid], 'refCategory') != 2:
            continue
        souls = sl.get(sp[gl.get(gp[gid], 'refId')], 'soul')
        if souls > 0:
            APPEND[('name', gid)] = {'ru': f' ({souls:,} душ)'.replace(',', ' '), 'en': f' ({souls:,} souls)'}


def patch_burg(data, edf):
    ev = Emevd(data)
    assert all(e['id'] != CAPRA_EVENT for e in ev.events)
    ev.events.append({'id': CAPRA_EVENT, 'rest': 0, 'params': [],
                      'ins': [_ins(edf, 2004, 5, CAPRA_DOG, 0)]})     # one dog instead of two
    next(e for e in ev.events if e['id'] == 0)['ins'].insert(0, _ins(edf, 2000, 0, 0, CAPRA_EVENT, 0))
    return build_emevd(ev)
