"""Covenants you can rank up offline.

Most covenant offerings come from other players: Sunlight Medals from co-op boss kills, Souvenirs of Reprisal
from killing invaders, Eyes of Death and Dragon Scales from PvP. Offline there are a handful in the world and
6% drops. Here they come from what the offline game has instead:
  Sunlight Medal       - one for every boss, to the co-op partner too (2003[36], after "boss defeated");
  Souvenir of Reprisal - 2 from every dark spirit (hub_champions: the NPC invaders the Blades hunt);
  Dragon Scale         - 2 from every champion (hub_champions);
  drop chances         - Eye of Death from Basilisks and Souvenir from the Crow Demons 6% -> 20%,
                         Sunlight Medal from Chaos Bugs 3% -> 15%.
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins

SUNLIGHT_MEDAL, SOUVENIR, EYE_OF_DEATH, DRAGON_SCALE = 375, 374, 109, 1110
MEDAL_LOT = 2900
DROPS = {  # lot: (goods, new base points out of the lot's total)
    32700000: (EYE_OF_DEATH, 20),      # Basilisk - The Depths
    32700100: (EYE_OF_DEATH, 20),      # Basilisk - Great Hollow
    23100000: (SOUVENIR, 20),          # Crow Demon - Painted World
    34800000: (SUNLIGHT_MEDAL, 150),   # Chaos Bug - Demon Ruins (out of 1000)
}
DARK_SPIRIT_REWARD = [(SOUVENIR, 2)]
CHAMPION_REWARD = [(DRAGON_SCALE, 2)]


def apply():
    lp, ll, _ = P['ItemLotParam']
    assert all(i not in lp for i in (MEDAL_LOT - 1, MEDAL_LOT, MEDAL_LOT + 1))
    r = lp.add(MEDAL_LOT, lp[2510], b'[FirelinkHub] Sunlight Medal for a boss')
    for s in range(1, 9):
        ll.set(r, f'lotItemId0{s}', 0); ll.set(r, f'lotItemCategory0{s}', 0)
        ll.set(r, f'lotItemNum0{s}', 0); ll.set(r, f'lotItemBasePoint0{s}', 0)
    ll.set(r, 'lotItemId01', SUNLIGHT_MEDAL); ll.set(r, 'lotItemCategory01', 0x40000000)
    ll.set(r, 'lotItemNum01', 1); ll.set(r, 'lotItemBasePoint01', 100)
    ll.set(r, 'getItemFlagId', -1)               # every boss gives one: the boss event runs once anyway
    for lot, (gid, points) in DROPS.items():
        row = lp[lot]
        slots = {ll.get(row, f'lotItemId0{s}'): s for s in range(1, 9) if ll.get(row, f'lotItemBasePoint0{s}')}
        item, nothing = slots[gid], slots[0]
        old = ll.get(row, f'lotItemBasePoint0{item}')
        ll.set(row, f'lotItemBasePoint0{item}', points)
        ll.set(row, f'lotItemBasePoint0{nothing}', ll.get(row, f'lotItemBasePoint0{nothing}') - (points - old))


def patch_map(data, edf, mapname):
    """A Sunlight Medal after every "boss defeated" (2003[12]) of the map."""
    ev = Emevd(data)
    n = 0
    for e in ev.events:
        at = [k for k, (b, i, _) in enumerate(e['ins']) if (b, i) == (2003, 12)]
        if at:
            e['ins'].insert(at[-1] + 1, _ins(edf, 2003, 36, MEDAL_LOT))
            n += 1
    return build_emevd(ev), n
