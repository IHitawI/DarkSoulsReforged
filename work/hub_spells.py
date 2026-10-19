"""New spells ported by mechanics from DS2/DS3/Elden Ring, built from DS1 parts.

DS1 can't get new cast animations or new visual effects, so every spell reuses a vanilla cast
(Magic param refType: the animation, per school) and vanilla effects, with its own buffs, bullets
and damage. Support miracles reach the caster and nearby allies the AllyHeal way: an area bullet
that gives the caster the buff and every friendly player inside it a copy.
Scrolls are sold by the vanilla teachers (Petrus, Griggs, Laurentius).
"""
from load import *
import hub_casts

ALLY_RADIUS = 3.0
BUFF_CAST, RAISE_CAST, GROUND_CAST = 3, 4, 10   # Magic refType: vanilla cast animations
SOLD_FLAG = 11027930   # 11027930..11027990
# icon cells: Icon21 placeholders C7-C9 and unused sprites of other atlases (icons.FREE_SLOTS / EXTRA_SLOTS)
ICON = {'golden_vow': 2165, 'perseverance': 2166, 'blessed_rain': 2167, 'lightning_stake': 3032,
        'lightning_storm': 1268, 'farron_hail': 2033, 'black_serpent': 2044,   # 2168+ have no DRB sprite
        'lightning_spark': 4012, 'lesser_vow': 112}
SPARK, LESSER_VOW = 5540, 5640           # Cleric starters
CLERIC = 3008                            # CharaInitParam row of the Cleric (classes 3000-3009)

TEXT = {}   # item.msgbnd: (kind, id) -> {'ru', 'en'}; kinds: name/info/caption (scroll), mname/minfo/mcaption (spell)
SHOP_ROWS = []   # (row id, goods id, price)


def _text(sid, prefix, name, info, caption):
    ru_pre, en_pre = prefix
    TEXT[('name', sid)] = {'ru': f'{ru_pre}: {name[0]}', 'en': f'{en_pre}: {name[1]}'}
    TEXT[('mname', sid)] = {'ru': name[0], 'en': name[1]}
    TEXT[('minfo', sid)] = {'ru': info[0], 'en': info[1]}
    TEXT[('caption', sid)] = {'ru': caption[0], 'en': caption[1]}
    TEXT[('mcaption', sid)] = {'ru': caption[0], 'en': caption[1]}


MIRACLE = ('Чудо', 'Miracle')
SORCERY = ('Волшебство', 'Sorcery')
PYROMANCY = ('Пиромантия', 'Pyromancy')
SCROLL_INFO = {MIRACLE: ('Свиток для изучения чуда', 'Spell scroll for attuning miracle'),
               SORCERY: ('Свиток для изучения колдовства', 'Spell scroll for attuning sorcery'),
               PYROMANCY: ('Свиток для изучения пиромантии', 'Spell scroll for attuning pyromancy')}


def apply():
    mp, ml, _ = P['Magic']
    gp, gl, _ = P['EquipParamGoods']
    sp, sl, _ = P['SpEffectParam']
    bp, bl, _ = P['Bullet']
    ap, al, _ = P['AtkParam_Pc']
    ally_flags = {k: sl.get(sp[1430], k) for k in sl.slots if k.startswith('effectTarget')}   # Soothing Sunlight heal
    # body visuals: SpEffect stateInfo is a row of SpEffectVfxParam (29 = Magic Barrier bubble, 50 = regen glow)
    vp, vl, _ = P['SpEffectVfxParam']
    VFX_VOW, VFX_PERSEVERANCE = 250, 251
    v = vp.add(VFX_VOW, vp[48], b'[FirelinkHub] Golden Vow')                # Red Tearstone aura
    vl.set(v, 'midstSfxId', 24003)
    v = vp.add(VFX_PERSEVERANCE, vp[155], b'[FirelinkHub] Perseverance')    # "SA enhancement": poise aura
    vl.set(v, 'midstSfxId', 24023)

    def spell(sid, template, key, *, faith=0, intel=0, uses, slots=1, ref=None, ref_type=None, sort):
        m = mp.add(sid, mp[template], key.encode())
        g = gp.add(sid, gp[template], key.encode())
        gl.set(g, 'magicId', sid)          # the scroll teaches this spell (the template's points at its own)
        for k in range(16):                # castable in any covenant (Soothing Sunlight's row is Sunlight-only)
            ml.set(m, f'vowType{k}', 1)
        for row, lay in ((m, ml), (g, gl)):
            lay.set(row, 'iconId', ICON[key])
            lay.set(row, 'sortId', sort)
        ml.set(m, 'requirementFaith', faith)
        ml.set(m, 'requirementIntellect', intel)
        ml.set(m, 'maxQuantity', uses)
        ml.set(m, 'slotLength', slots)
        if ref is not None:
            ml.set(m, 'refCategory', 1)      # a bullet
            ml.set(m, 'refId', ref)
        if ref_type is not None:
            ml.set(m, 'refType', ref_type)   # cast animation
        return m

    def buff(sid, template, label, keep_state=False, **fields):
        """Own buff + ally copy (sid + 5). stateInfo is cleared (Magic Barrier's bubble) unless keep_state:
        regeneration (Replenishment, stateInfo 50) needs it."""
        own = sp.add(sid, sp[template], f'[Spell] {label}'.encode())
        for k in ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate', 'neutralDamageCutRate',
                  'magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate'):
            sl.set(own, k, 1.0)
        if not keep_state:
            sl.set(own, 'stateInfo', 0)      # no Magic Barrier bubble
        for k, v in fields.items():
            sl.set(own, k, v)
        ally = sp.add(sid + 5, own, f'[Spell] {label} - Ally'.encode())
        for k, v in ally_flags.items():
            sl.set(ally, k, v)
        return sid, sid + 5

    def area(bid, label, own, ally, radius=ALLY_RADIUS, spread=0.5):
        """Area bullets for every talisman level (Soothing Sunlight has levels 0-4)."""
        for lvl in range(5):
            b = bp.add(bid + lvl, bp[3100 + lvl], f'{label} - Area {lvl}'.encode())
            bl.set(b, 'spEffectIDForShooter', own)
            bl.set(b, 'spEffectId0', ally)
            bl.set(b, 'hitRadiusMax', radius)
            bl.set(b, 'spreadTime', spread)
        return bid

    def atk(aid, template, label, **fields):
        a = ap.add(aid, ap[template], label.encode())
        for k, v in fields.items():
            al.set(a, k, v)
        return aid

    # ---------- Golden Vow (Elden Ring): +15% damage, -10% damage taken, 60 s, caster and allies
    own, ally = buff(92500, 1160, 'Golden Vow', keep_state=True, stateInfo=VFX_VOW, effectEndurance=60.0, iconId=sl.get(sp[1070], 'iconId'),
                     physicsAttackPowerRate=1.15, magicAttackPowerRate=1.15, fireAttackPowerRate=1.15,
                     thunderAttackPowerRate=1.15,
                     **{k: 0.9 for k in ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate',
                                         'neutralDamageCutRate', 'magicDamageCutRate', 'fireDamageCutRate',
                                         'thunderDamageCutRate')})
    spell(5620, 5600, 'golden_vow', faith=25, uses=2, ref=area(3700, 'Golden Vow', own, ally), ref_type=BUFF_CAST,
          sort=3218)
    _text(5620, MIRACLE, ('Золотой обет', 'Golden Vow'),
          ('Усиливает атаку и защиту себя и союзников рядом.', 'Raise attack and defense of self and nearby allies'),
          ('Древнее чудо рыцарей, давших золотой обет.\nТе, кто стоит рядом, разделяют его силу.\n\n'
           'На 60 сек. заклинатель и союзники рядом\nнаносят на 15% больше урона\nи получают на 10% меньше.',
           'An ancient miracle of knights who swore\na golden vow. Those who stand close\nshare in its strength.\n\n'
           'For 60 seconds the caster and nearby allies\ndeal 15% more damage\nand take 10% less.'))
    SHOP_ROWS.append((4011, 5620, 20000))

    # ---------- Perseverance (DS2): +50 poise, 30 s, caster and allies
    own, ally = buff(92510, 1160, 'Perseverance', keep_state=True, stateInfo=VFX_PERSEVERANCE, effectEndurance=30.0, iconId=sl.get(sp[1130], 'iconId'),
                     changeSuperArmorPoint=120,       # Havel's set level: most hits don't stagger
                     **{k: 0.7 for k in ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate',
                                         'neutralDamageCutRate')})   # -30% physical damage
    spell(5630, 5600, 'perseverance', faith=14, uses=4, ref=area(3710, 'Perseverance', own, ally), sort=3219)
    _text(5630, MIRACLE, ('Стойкость', 'Perseverance'),
          ('Стойкость и защита от физического урона.', 'Poise and physical damage reduction'),
          ('Чудо странствующих монахов, что шли\nсквозь бурю, не сгибаясь.\n\n'
           'На 30 сек. заклинатель и союзники рядом\nполучают +120 к стойкости и на 30% меньше\nфизического урона: их почти не сбить с ног.',
           'A miracle of wandering monks who walked\nthrough the storm without bending.\n\n'
           'For 30 seconds the caster and nearby allies\ngain 120 poise and take 30% less physical\ndamage: they are hard to stagger.'))
    SHOP_ROWS.append((4012, 5630, 6000))

    # ---------- Blessed Rain: slow regeneration for everyone in a wide circle
    own, ally = buff(92520, 570, 'Blessed Rain', keep_state=True, effectEndurance=40.0, changeHpPoint=-8)
    spell(5060, 5030, 'blessed_rain', faith=20, uses=2, slots=1,
          ref=area(3720, 'Blessed Rain', own, ally, radius=8.0, spread=1.0), ref_type=RAISE_CAST, sort=3207)
    _text(5060, MIRACLE, ('Благодатный дождь', 'Blessed Rain'),
          ('Медленно лечит всех союзников в широком круге.', 'Slowly heal all allies in a wide area'),
          ('Молитва о дожде, что смывает раны.\nЛечит слабее «Исцеления», зато всех вокруг.\n\n'
           'На 40 сек. заклинатель и союзники\nв радиусе 8 м восстанавливают по 8 HP\nв секунду.',
           'A prayer for rain that washes wounds away.\nWeaker than Heal, but it reaches everyone.\n\n'
           'For 40 seconds the caster and allies\nwithin 8 m regain 8 HP per second.'))
    SHOP_ROWS.append((4013, 5060, 12000))


    # ---------- Lightning Stake (DS3): Gravelord Sword Dance cast (talisman into the ground),
    # a lightning burst right there, then a shockwave. The bullet starts at the talisman: at your feet.
    GRAVELORD = 16                                   # Magic refType: Gravelord Sword Dance cast
    stake_atk = atk(16500, 16100, 'Lightning Stake', atkThun=330, knockbackDist=1.5)
    wave_atk = atk(16540, 19010, 'Lightning Stake - Shockwave', atkMag=0, atkThun=110, knockbackDist=2.5)
    for lvl in range(5):
        b = bp.add(3730 + lvl, bp[10000 + lvl], f'Lightning Stake {lvl}'.encode())   # Force: area, no flight
        bl.set(b, 'atkId_Bullet', stake_atk)
        bl.set(b, 'sfxId_Bullet', 20236)            # Sunlight Spear impact: big golden burst
        bl.set(b, 'sfxId_Hit', 20230)               # Lightning Spear hit
        bl.set(b, 'hitRadius', 2.2)
        bl.set(b, 'attachEffectType', 0)
        bl.set(b, 'atkAttribute', bl.get(bp[9000], 'atkAttribute'))
        bl.set(b, 'spAttribute', bl.get(bp[9000], 'spAttribute'))
        bl.set(b, 'HitBulletID', 3790 + lvl)        # then a Wrath of the Gods shockwave
        w = bp.add(3790 + lvl, bp[10100 + lvl], f'Lightning Stake - Shockwave {lvl}'.encode())
        bl.set(w, 'atkId_Bullet', wave_atk)
        bl.set(w, 'hitRadius', 3.0)
    m = spell(5330, 5100, 'lightning_stake', faith=22, uses=10, ref=3730, ref_type=GRAVELORD, sort=3308)
    _text(5330, MIRACLE, ('Кол молнии', 'Lightning Stake'),
          ('Вонзает молнию в землю у ног заклинателя.', 'Drive lightning into the ground at your feet'),
          ('Чудо воинов солнца древнего бога войны.\nЗаклинатель вонзает талисман в землю,\n'
           'и молния бьёт в это место, поражая\nвсех, кто стоит рядом.',
           'A miracle of the warriors of the old god\nof war. The caster drives the talisman\n'
           'into the ground and lightning strikes there,\nhitting all who stand close.'))
    SHOP_ROWS.append((4014, 5330, 15000))

    # ---------- Lightning Storm: Firestorm's own mechanics with lightning. Firestorm is a ground-slam cast
    # (refType 10) whose animation releases its short emitter (bullet 8000: life 1 s, 2 pillars at random
    # spots around the caster) several times; the strikes copy the pillar (8010) with lightning damage and
    # bursts. (A single long-lived emitter from a raise cast - the first version - hardly ever struck.)
    storm_atk = atk(16510, 16100, 'Lightning Storm', atkThun=220)
    for lvl in range(5):
        b = bp.add(3750 + lvl, bp[8000], f'Lightning Storm {lvl}'.encode())
        bl.set(b, 'HitBulletID', 3760 + lvl)
        h = bp.add(3760 + lvl, bp[8010], f'Lightning Storm - Strike {lvl}'.encode())
        bl.set(h, 'atkId_Bullet', storm_atk)
        bl.set(h, 'sfxId_Bullet', 20236)            # Sunlight Spear impact: big golden burst
        bl.set(h, 'sfxId_Hit', 20230)
        bl.set(h, 'hitRadius', 1.5)
        bl.set(h, 'hitRadiusMax', 1.5)
        bl.set(h, 'spAttribute', bl.get(bp[9000], 'spAttribute'))
    m = spell(5530, 5030, 'lightning_storm', faith=40, uses=4, slots=2, ref=3750, ref_type=GROUND_CAST,
              sort=3309)
    _text(5530, MIRACLE, ('Буря молний', 'Lightning Storm'),
          ('Молнии бьют в землю вокруг заклинателя.', 'Lightning strikes the ground around the caster'),
          ('Самое грозное чудо воинов солнца.\nЗаклинатель бьёт талисманом оземь,\nи вокруг него одна за другой\nбьют молнии.\n\n'
           'Требует много веры и два слота.',
           'The most fearsome miracle of the warriors\nof sunlight. The caster strikes the ground\nwith the talisman and lightning falls\naround them, bolt after bolt.\n\n'
           'Demands great faith and two slots.'))
    SHOP_ROWS.append((4015, 5530, 40000))

    # ---------- Farron Hail (DS3): a fan of small homing soul arrows
    hail_atk = atk(16520, 10000, 'Farron Hail', atkMag=48)
    b = bp.add(3770, bp[3000], b'Farron Hail')
    bl.set(b, 'atkId_Bullet', hail_atk)
    bl.set(b, 'numShoot', 7)
    bl.set(b, 'shootAngleInterval', 6)
    bl.set(b, 'shootAngle', -18)                    # centred fan, like Dark Bead
    bl.set(b, 'homingAngle', 25)
    bl.set(b, 'dist', 16.0)
    spell(3080, 3000, 'farron_hail', intel=18, uses=10, ref=3770, sort=3009)
    _text(3080, SORCERY, ('Град Фаррона', 'Farron Hail'),
          ('Выпускает веер небольших самонаводящихся стрел.', 'Fire a spread of small homing soul arrows'),
          ('Колдовство дозорных из далёкой страны.\nВеер маленьких стрел души, каждая\n'
           'слабее «Стрелы души», но вместе они\nбьют больно, особенно вблизи.',
           'A sorcery of watchers from a distant land.\nA fan of small soul arrows, each weaker\n'
           'than Soul Arrow, that hit hard together,\nespecially up close.'))
    SHOP_ROWS.append((2022, 3080, 12000))

    # ---------- Black Serpent: the caster touches the ground (Firestorm cast) and five fire serpents
    # crawl out, seek enemies like soulmasses, pass through them and set everyone they touch on fire
    vfx_burn = 252
    v = vp.add(vfx_burn, vp[200], b'[FirelinkHub] Black Serpent burn')   # Power Within's flame aura
    burn = sp.add(92530, sp[1200], b'[Spell] Black Serpent - Burn')    # Poison Mist: damage over time
    sl.set(burn, 'changeHpPoint', 14)
    sl.set(burn, 'motionInterval', 0.5)
    sl.set(burn, 'effectEndurance', 5.0)            # 140 damage over 5 s per touch
    sl.set(burn, 'stateInfo', vfx_burn)
    serpent_atk = atk(16530, 21000, 'Black Serpent', atkFire=110, atkPhys=40, knockbackDist=0.3)
    b = bp.add(3780, bp[3000], b'Black Serpent')      # Soul Arrow: homing flight
    bl.set(b, 'atkId_Bullet', serpent_atk)
    bl.set(b, 'sfxId_Bullet', 20186)                 # Fire Orb: a flame ball you can follow
    bl.set(b, 'sfxId_Hit', 20286)                    # Fire Orb burst
    bl.set(b, 'numShoot', 5)
    bl.set(b, 'shootAngleInterval', 6)
    bl.set(b, 'shootAngle', -12)                    # centred: -12 -6 0 6 12 (as Dark Bead does it)
    bl.set(b, 'shootAngleXZ', 0)
    for k, v_ in (('initVellocity', 5.0), ('minVellocity', 5.0), ('maxVellocity', 6.5), ('accelTime', 0.0)):
        bl.set(b, k, v_)
    bl.set(b, 'life', 3.5)
    bl.set(b, 'dist', 20.0)
    bl.set(b, 'homingAngle', 20)                     # gentle curve: the fan bows out, then closes in
    bl.set(b, 'homingBeginDist', 0.5)
    bl.set(b, 'hormingStopRange', 0.0)
    bl.set(b, 'autoSearchNPCThinkID', 10000)        # find targets by itself (as Homing Soulmass)
    bl.set(b, 'hitRadius', 0.6)
    bl.set(b, 'isPenetrate', 1)                      # through one enemy, on to the next
    bl.set(b, 'isPenetrateMap', 1)                   # born at the hand on the ground: don't die in the floor
    bl.set(b, 'dmgHitRecordLifeTime', 1.0)
    bl.set(b, 'spEffectId0', 92530)               # the burn above
    for k in ('atkAttribute', 'spAttribute', 'Material_AttackMaterial'):
        bl.set(b, k, bl.get(bp[11200], k))         # fire, like Fire Surge
    spell(4070, 4030, 'black_serpent', uses=6, ref=3780, ref_type=GROUND_CAST, sort=3120)
    _text(4070, PYROMANCY, ('Чёрный змей', 'Black Serpent'),
          ('Пять огненных змей ищут врагов и поджигают их.', 'Five fire serpents hunt foes and set them ablaze'),
          ('Запретная пиромантия изгнанников.\nЗаклинатель касается земли, и из неё\n'
           'выползают пять огненных змей. Они сами ищут\nврагов, проходят сквозь них и поджигают\nкаждого, кого коснутся.',
           'A forbidden pyromancy of exiles.\nThe caster touches the ground and five\n'
           'fire serpents crawl out. They seek foes,\npass through them and set ablaze\nall they touch.'))
    SHOP_ROWS.append((3005, 4070, 15000))

    # ---------- Cleric starters (a weak attack and a weak support next to Heal)
    # Lightning Spark: a Lightning Spear with ~48% of its damage, 8 casts like Fireball; its faith scaling is
    # 80 instead of 110, so it falls behind the Spear later on (a starter, not an endgame spell)
    spark = bp.add(3800, bp[9000], b'Lightning Spark')
    bl.set(spark, 'atkId_Bullet', atk(16550, 16000, 'Lightning Spark', atkThun=130, atkThunCorrection=80,
                                      atkSuperArmor=15))
    spell(SPARK, 5500, 'lightning_spark', faith=12, uses=8, ref=3800, sort=3300)
    _text(SPARK, MIRACLE, ('Искра молнии', 'Lightning Spark'),
          ('Бросает небольшую искру молнии.', 'Hurl a small spark of lightning'),
          ('Первое боевое чудо, которому учат\nклириков Торолунда перед паломничеством.\n\n'
           'Слабее копья молнии и с ростом веры\nотстаёт от него, зато доступно сразу.',
           'The first war miracle taught to the\nclerics of Thorolund before their pilgrimage.\n\n'
           'Weaker than a Lightning Spear and falls\nbehind it as faith grows, but ready at once.'))
    SHOP_ROWS.append((4016, SPARK, 2000))
    # Lesser Vow: a Golden Vow cut down: +7% damage, -5% damage taken, 30 s, caster and allies
    own, ally = buff(92550, 1160, 'Lesser Vow', keep_state=True, stateInfo=VFX_VOW, effectEndurance=30.0,
                     iconId=sl.get(sp[1070], 'iconId'),
                     physicsAttackPowerRate=1.07, magicAttackPowerRate=1.07, fireAttackPowerRate=1.07,
                     thunderAttackPowerRate=1.07,
                     **{k: 0.95 for k in ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate',
                                          'neutralDamageCutRate', 'magicDamageCutRate', 'fireDamageCutRate',
                                          'thunderDamageCutRate')})
    spell(LESSER_VOW, 5600, 'lesser_vow', faith=12, uses=2, ref=area(3810, 'Lesser Vow', own, ally),
          ref_type=BUFF_CAST, sort=3217)
    _text(LESSER_VOW, MIRACLE, ('Малый обет', 'Lesser Vow'),
          ('Немного усиливает себя и союзников рядом.', 'Slightly strengthen self and nearby allies'),
          ('Короткая молитва, которой клирики\nТоролунда благословляют спутников в пути.\n\n'
           'На 30 сек. заклинатель и союзники рядом\nнаносят на 7% больше урона\nи получают на 5% меньше.',
           'A short prayer the clerics of Thorolund\nuse to bless their companions on the road.\n\n'
           'For 30 seconds the caster and nearby allies\ndeal 7% more damage and take 5% less.'))
    SHOP_ROWS.append((4017, LESSER_VOW, 3000))

    for sid in (5620, 5630, 5060, 5330, 5530, SPARK, LESSER_VOW):
        TEXT[('info', sid)] = {'ru': SCROLL_INFO[MIRACLE][0], 'en': SCROLL_INFO[MIRACLE][1]}
    TEXT[('info', 3080)] = {'ru': SCROLL_INFO[SORCERY][0], 'en': SCROLL_INFO[SORCERY][1]}
    TEXT[('info', 4070)] = {'ru': SCROLL_INFO[PYROMANCY][0], 'en': SCROLL_INFO[PYROMANCY][1]}

    shp, shl, _ = P['ShopLineupParam']
    # the bonfire attunement menu is a "shop" of rows 10000-10099 (OpenMagicEquip): one row per spell,
    # shown while the player has what its material set asks for (the spell's own scroll, x1)
    mtp, mtl, _ = P['EquipMtrlSetParam']
    # vanilla leaves holes in that block; fill them first so the list doesn't grow past the end
    # (the last row, 10083, was not shown)
    menu_rows = (10006, 10007, 10032, 10033, 10067, 10077, 10078, 10079, 10080)
    for row_id, sid in zip(menu_rows, (4070, 3080, 5620, 5630, 5060, 5330, 5530, SPARK, LESSER_VOW)):
        r = shp.add(row_id, shp[10000], b'')
        shl.set(r, 'equipId', sid)
        shl.set(r, 'mtrlId', sid)
        mt = mtp.add(sid, mtp[3000], b'')
        mtl.set(mt, 'materialId01', sid)
    for k, (rid, gid, price) in enumerate(SHOP_ROWS):
        assert rid not in shp, rid
        r = shp.add(rid, shp[4000], b'')            # Petrus: Heal scroll (a goods row, one copy)
        shl.set(r, 'equipId', gid)
        shl.set(r, 'value', price)
        shl.set(r, 'eventFlag', SOLD_FLAG + 10 * k)   # each scroll its own "bought" flag (vanilla steps by 10)


def cleric_start():
    """The Cleric starts with Heal, Lightning Spark and Lesser Vow, and the 3 attunement slots to use them:
    Attunement 11 -> 14, paid for by Vitality, Endurance and Resistance -1 each (same soul level, the same
    stat budget as every class: stats - SL = 82). Strength stays 12: his Mace needs 12."""
    cp, cl, _ = P['CharaInitParam']
    r = cp[CLERIC]
    assert cl.get(r, 'equip_Spell_01') == 5000 and cl.get(r, 'baseWil') == 11
    cl.set(r, 'baseWil', 14)
    for k in ('baseVit', 'baseEnd', 'baseDurability'):
        cl.set(r, k, cl.get(r, k) - 1)
    cl.set(r, 'equip_Spell_02', SPARK)
    cl.set(r, 'equip_Spell_03', LESSER_VOW)
    for slot, sid in ((2, SPARK), (3, LESSER_VOW)):          # their scrolls, so the attunement menu lists them
        assert cl.get(r, f'item_{slot:02d}') == -1
        cl.set(r, f'item_{slot:02d}', sid)
        cl.set(r, f'itemNum_{slot:02d}', 1)
