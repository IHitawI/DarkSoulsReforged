"""Weapons nobody uses, given a reason to.

EquipParamWeapon has one row per weapon and infusion (base id + 100 * infusion); +1..+15 are computed
from it (ReinforceParamWeapon), so a change to the row reaches every level. `dmg` multiplies all base damage
of every infusion, `scale` the attribute scaling, `crit` is throwAtkRate (bonus on ripostes / backstabs).
"""
from load import *

INFUSIONS = range(0, 1000, 100)
WEAPONS = {  # base id: changes, why
    1600000: dict(dmg=1.3, scale=1.25),                  # Whip: reach weapon that finally hurts
    1601000: dict(dmg=1.3, scale=1.25),                  # Notched Whip
    901000: dict(dmg=1.3),                               # Caestus: fast fists worth the risk
    902000: dict(dmg=1.25),                              # Claw
    903000: dict(dmg=1.35, weight=5.0),                  # Dragon Bone Fist: lighter, heavier hits
    903100: dict(dmg=1.35, weight=5.0),
    200000: dict(dmg=1.1),                               # Shortsword: a starting sword that lasts a bit longer
    203000: dict(dmg=1.6, crit=60),                      # Broken Straight Sword: a riposte knife
    212000: dict(dmg=1.5, crit=150),                     # Straight Sword Hilt: the backstab joke made real
    206000: dict(dmg=1.15, faith=40.0),                  # Sunlight Straight Sword: praise the sun - faith scaling
    600000: dict(dmg=1.35, crit=45),                     # Mail Breaker: crits like a dagger
    804000: dict(dmg=1.25),                              # Pickaxe
    850000: dict(dmg=1.2),                               # Great Club
    855000: dict(dmg=1.25, weight=9.0),                  # Large Club
    856000: dict(dmg=1.1, weight=22.0),                  # Smough's Hammer: still huge, now carriable
    1050000: dict(dmg=1.15, weight=8.0),                 # Pike
    1150000: dict(dmg=1.25),                             # Great Scythe
    1307000: dict(magic_scale=125.0),                    # Demon's Catalyst: spell power closer to the others
    309000: dict(dmg=1.1, magic_scale=155.0),            # Moonlight Greatsword: rewards high Intelligence
}
DAMAGE = ('attackBasePhysics', 'attackBaseMagic', 'attackBaseFire', 'attackBaseThunder')
SCALING = ('correctStrength', 'correctAgility', 'correctMagic', 'correctFaith')
CHANGED = []


def apply():
    wp, wl, _ = P['EquipParamWeapon']
    for base, ch in WEAPONS.items():
        unique = base % 1000 != 0          # boss weapons / variants: one row only
        for inf in ([0] if unique else INFUSIONS):
            wid = base + inf
            if wid not in wp:
                continue
            r = wp[wid]
            for f in DAMAGE:
                wl.set(r, f, round(wl.get(r, f) * ch.get('dmg', 1.0)))
            if 'scale' in ch:
                for f in SCALING:
                    wl.set(r, f, round(wl.get(r, f) * ch['scale'], 1))
            if 'weight' in ch:
                wl.set(r, 'weight', ch['weight'])
            if 'crit' in ch:
                wl.set(r, 'throwAtkRate', ch['crit'])
            if 'faith' in ch and inf == 0:
                wl.set(r, 'correctFaith', ch['faith'])
            if 'magic_scale' in ch and inf == 0:
                wl.set(r, 'correctMagic', ch['magic_scale'])
            CHANGED.append(wid)
