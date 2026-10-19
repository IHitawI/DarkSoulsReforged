"""Ally heal mod: heals and support buffs also affect nearby allies (never enemies)."""
import sys, os; sys.path.insert(0, ".")
from load import *

ALLY_RATE = 0.75     # allies get 75% of the caster's heal
RADIUS_MAX = 3.0     # metres (Soothing Sunlight = 4.0)
SPREAD_TIME = 0.5    # seconds for the area to grow to full size

mp, ml, mf = P['Magic']
sp, sl, sf = P['SpEffectParam']
bp, bl, bf = P['Bullet']

TEMPLATE_BULLET = 3100  # Soothing Sunlight
# target flags copied from Soothing Sunlight's heal: everyone friendly, no enemies
# (Self must stay on: hits on a remote player are resolved on that player's side)
ALLY_FLAGS = {k: sl.get(sp[1430], k) for k in sl.slots if k.startswith('effectTarget')}

# magic id -> (new ally SpEffect base, new bullet base, label, levels, heal scaling)
# levels: miracles have hidden Level 1-4 variants (base id + 1..4)
SPELLS = {
    # heals: allies get ALLY_RATE of the heal
    5000: (1440, 3400, 'Heal', 5, True),
    5020: (1450, 3410, 'Great Heal Excerpt', 5, True),
    5010: (1460, 3420, 'Great Heal', 5, True),
    5040: (1470, 3430, 'Replenishment', 5, True),
    # defensive buffs: full effect on allies
    5600: (92000, 3440, 'Magic Barrier', 5, False),
    5610: (92010, 3450, 'Great Magic Barrier', 5, False),
    5200: (92020, 3460, 'Escape Death', 5, False),
    4310: (92030, 3470, 'Flash Sweat', 1, False),
    3610: (92040, 3480, 'Remedy', 1, False),
    3600: (92050, 3490, 'Resist Curse', 1, False),
    # stealth / utility
    3410: (92060, 3500, 'Hidden Body', 1, False),
    3510: (92070, 3510, 'Hush', 1, False),
    3540: (92080, 3520, 'Fall Control', 1, False),
    3500: (92090, 3530, 'Cast Light', 1, False),  # experimental: its cast animation never spawns a bullet in vanilla
    3530: (92100, 3540, 'Repair', 1, False),
}

for magic_id, (ally_sp, bullet, label, levels, is_heal) in SPELLS.items():
    m = mp[magic_id]
    if ml.get(m, 'refCategory') == 2:
        self_sp = ml.get(m, 'refId')                     # effect applied straight to the caster
    else:
        self_sp = bl.get(bp[ml.get(m, 'refId')], 'spEffectIDForShooter')  # self-only bullet (Remedy)
    for lvl in range(levels):
        tag = '' if lvl == 0 else f' - Level {lvl}'
        own = self_sp + lvl if self_sp + lvl in sp else self_sp
        src = sp[own]
        row = sp.add(ally_sp + lvl, src, f'[Spell] {label} - Ally{tag}'.encode('shift_jis'))
        if is_heal:
            sl.set(row, 'changeHpPoint', int(round(sl.get(src, 'changeHpPoint') * ALLY_RATE)))
        for k, v in ALLY_FLAGS.items():
            sl.set(row, k, v)
        # area bullet: own effect to the caster, ally copy to every friendly player hit
        b = bp.add(bullet + lvl, bp[TEMPLATE_BULLET + lvl], f'{label} - Ally{tag}'.encode('shift_jis'))
        bl.set(b, 'spEffectIDForShooter', own)
        bl.set(b, 'spEffectId0', ally_sp + lvl)
        bl.set(b, 'hitRadiusMax', RADIUS_MAX)
        bl.set(b, 'spreadTime', SPREAD_TIME)
    # spell now spawns the bullet instead of applying the effect directly (cast animation unchanged)
    ml.set(m, 'refCategory', 1)
    ml.set(m, 'refId', bullet)

# Remedy cures in a chain of bullets (base 1300, then bleed 1301, poison 1302, toxic 1303).
# Caster keeps the original chain via HitBulletID; allies get all four cures from the area bullet.
REMEDY_BULLET, REMEDY_ALLY = SPELLS[3610][1], SPELLS[3610][0]
b = bp[REMEDY_BULLET]
bl.set(b, 'HitBulletID', 2910)
for i in range(1, 4):
    row = sp.add(REMEDY_ALLY + i, sp[1300 + i], f'[Spell] {sp.name(1300 + i)[8:]} - Ally'.encode('shift_jis'))
    for k, v in ALLY_FLAGS.items():
        sl.set(row, k, v)
    bl.set(b, f'spEffectId{i}', REMEDY_ALLY + i)

for p, f in ((mp, mf), (sp, sf), (bp, bf)):
    f[3] = p.build()

out = 'out'
os.makedirs(out, exist_ok=True)
dcx_write(f'{out}/GameParam.parambnd.dcx', H, G.build())
print('written', f'{out}/GameParam.parambnd.dcx')
