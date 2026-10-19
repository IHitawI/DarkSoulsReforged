"""Firelink hub, stage 1: lifegems, usable coins, Firelink shop and price tweaks."""
from load import *

# text ids: 'name' -> FMG 10/111, 'info' -> FMG 20/110, 'caption' -> FMG 24/100
TEXT = {}   # (kind, goods id) -> {'ru': str, 'en': str}
APPEND = {}  # (kind, goods id) -> {'ru': str, 'en': str}, appended to the existing text


def text(kind, gid, ru, en):
    TEXT[(kind, gid)] = {'ru': ru, 'en': en}


# The pricier the gem, the faster it heals: cheap slow top-up -> mid -> expensive near-burst.
LIFEGEMS = [
    # goods id, SpEffect id, hp per tick, tick (s), seconds, price, sell, icon, sort, ru, en, ru speed, en speed
    (600, 92200, 20, 1.0, 15, 300, 30, 2159, 37, 'Камень жизни', 'Lifegem', 'медленно', 'slowly'),
    (601, 92201, 30, 0.5, 8, 1200, 120, 2160, 38, 'Сияющий камень жизни', 'Radiant Lifegem', 'быстро', 'quickly'),
    (602, 92202, 100, 0.5, 4, 3500, 350, 2161, 39, 'Древний сияющий камень жизни', 'Old Radiant Lifegem',
     'почти мгновенно', 'almost instantly'),
]
PRICE = {g[0]: g[5] for g in LIFEGEMS}
LIFEGEM_LORE = {
    600: ('Камень, в котором теплится жизнь.\nЕго приносят в Лордран странники,\nне желающие полагаться на один Эстус.',
          'A stone in which life still glows.\nWanderers bring them to Lordran,\nunwilling to rely on Estus alone.'),
    601: ('Камень жизни, напитанный светом.\nСияет так ярко, что его можно принять\nза осколок солнца.',
          'A lifegem steeped in light.\nIt shines so brightly that it could be\nmistaken for a shard of the sun.'),
    602: ('Древний камень жизни. Говорят, такие\nкамни хранили ещё жрецы Торолунда,\nпока их пламя не угасло.',
          'An ancient lifegem. They say the clerics\nof Thorolund kept such stones\nlong before their flame waned.'),
}

# Amber herbs: restore a share of every attuned spell's uses. The item itself only applies a
# harmless marker; FirelinkHub's DLL sees the herb count drop and adds the uses in memory.
HERBS = [
    # goods id, percent, price, sell, sort, ru name, en name
    (604, 30, 1500, 150, 41, 'Янтарная трава', 'Amber Herb'),
    (605, 50, 3000, 300, 42, 'Сочная янтарная трава', 'Lush Amber Herb'),
    (606, 80, 6000, 600, 43, 'Древняя янтарная трава', 'Ancient Amber Herb'),
]
HERB_SP = 92230
HERB_ICONS = {604: 2162, 605: 2163, 606: 2164}   # DS2 Amber Herb, three tints (atlas cells C4-C6)

COINS = [
    # goods id, SpEffect id, soul multiplier, percent
    (381, 92210, 1.25, 25),
    (382, 92211, 1.50, 50),
    (383, 92212, 2.00, 100),
]
COIN_SECONDS = 120

# shop rows: (row id, goods id, price); row ranges belong to the merchant (Petrus 4000-4099 etc.)
SHOP_ROWS = [
    (4007, 600, PRICE[600]),  # Petrus (Firelink): Lifegem
    (4008, 240, 5000),   # Petrus: Divine Blessing, unlimited
    (4009, 230, 3000),   # Petrus: Elizabeth's Mushroom
    (4010, 500, 8000),   # Petrus: Humanity, unlimited
    (1135, 600, PRICE[600]),  # Undead Merchant (Male), Burg / Firelink: Lifegem
    (1136, 601, PRICE[601]),  # Undead Merchant (Male): Radiant Lifegem
    (1221, 604, 1500),        # Undead Merchant (Female), Lower Burg / Firelink: Amber Herb
    (1222, 605, 3000),        # Undead Merchant (Female): Lush Amber Herb
    (1223, 606, 6000),        # Undead Merchant (Female): Ancient Amber Herb
    (5330, 601, PRICE[601]),  # Crestfallen Merchant, Sen's Fortress / Firelink: Radiant Lifegem
    (5331, 602, PRICE[602]),  # Crestfallen Merchant: Old Radiant Lifegem
    (5332, 292, 150),         # Crestfallen Merchant: Firebomb
    (5333, 310, 500),         # Crestfallen Merchant: Charcoal Pine Resin
    (5334, 311, 1000),        # Crestfallen Merchant: Gold Pine Resin
    (5335, 313, 1000),        # Crestfallen Merchant: Rotten Pine Resin
]
PRICE_CHANGES = {1214: 3000}  # Undead Merchant (Female): Purging Stone 6000 -> 3000


def apply():
    gp, gl, _ = P['EquipParamGoods']
    sp, sl, _ = P['SpEffectParam']
    shp, shl, _ = P['ShopLineupParam']

    # --- lifegems: regeneration over time, not interrupted by damage (built on Elizabeth's Mushroom;
    #     the crush-in-hand animation 9 with a consumable use limit made them unusable)
    for gid, spid, tick_hp, tick, secs, _, sell, icon, sort, ru, en, ru_speed, en_speed in LIFEGEMS:
        e = sp.add(spid, sp[3041], f'[Item] {en}'.encode('shift_jis'))   # Elizabeth's Mushroom regen
        sl.set(e, 'changeHpPoint', -tick_hp)   # negative = heal, every `tick` seconds
        sl.set(e, 'effectEndurance', float(secs))
        sl.set(e, 'motionInterval', tick)
        sl.set(e, 'spCategory', 0)      # as Heal: no clash with miracle buffs (category 10001)
        sl.set(e, 'stateInfo', 52)      # own regen state ("weak regenerate" glow), not Replenishment's
        g = gp.add(gid, gp[230], en.encode('shift_jis'))   # Elizabeth's Mushroom: a working heal-over-time item
        gl.set(g, 'refId', spid)
        gl.set(g, 'iconId', icon)
        gl.set(g, 'sortId', sort)
        gl.set(g, 'sellValue', sell)
        gl.set(g, 'useLimitCategory', 0)   # the Mushroom's 2 blocks it while Magic Barrier & co. are active
        total = round(tick_hp * secs / tick)
        lore_ru, lore_en = LIFEGEM_LORE[gid]
        text('name', gid, ru, en)
        text('info', gid, f'Восстанавливает {total} HP ({ru_speed}).', f'Restores {total} HP ({en_speed}).')
        text('caption', gid,
             f'{lore_ru}\n\nВосстанавливает {total} HP за {secs} сек.\nНе прерывается при получении урона.',
             f'{lore_en}\n\nRestores {total} HP over {secs} seconds.\nNot interrupted by taking damage.')

    # --- amber herbs
    e = sp.add(HERB_SP, sp[3040], b'[Item] Amber Herb - marker')
    sl.set(e, 'staminaRecoverChangeSpeed', 0)
    sl.set(e, 'stateInfo', 0)
    sl.set(e, 'iconId', 0)
    sl.set(e, 'effectEndurance', 0.1)
    for gid, pct, _, sell, sort, ru, en in HERBS:
        g = gp.add(gid, gp[260], en.encode('shift_jis'))    # Green Blossom: an eaten herb
        gl.set(g, 'refId', HERB_SP)
        gl.set(g, 'iconId', HERB_ICONS[gid])
        gl.set(g, 'sortId', sort)
        gl.set(g, 'sellValue', sell)
        gl.set(g, 'isDrop', 0)       # the DLL counts herbs in the inventory: no dropping
        gl.set(g, 'isDeposit', 0)    # ...and no storing in the Bottomless Box
        gl.set(g, 'useLimitCategory', 0)   # Green Blossom's 2 blocks it during most miracle buffs
        text('name', gid, ru, en)
        text('info', gid, f'Восстанавливает {pct}% зарядов заклинаний.', f'Restores {pct}% of spell uses.')
        text('caption', gid,
             'Янтарная трава с терпким запахом.\nЖуют её те, кто полагается на чары,\nкогда до костра ещё далеко.\n\n'
             f'Восстанавливает каждому настроенному\nзаклинанию {pct}% зарядов (минимум 1).\n'
             'Траву нельзя выбросить или убрать в шкатулку.',
             'An amber herb with a sharp scent.\nChewed by those who rely on sorcery\nwhen the next bonfire is far away.\n\n'
             f'Restores {pct}% of the uses of every\nattuned spell (at least 1).\n'
             'Cannot be dropped or stored.')

    # --- coins: crush for more souls from kills
    for gid, spid, mult, pct in COINS:
        e = sp.add(spid, sp[3040], f'[Item] Coin soul bonus +{pct}%'.encode('shift_jis'))
        sl.set(e, 'staminaRecoverChangeSpeed', 0)
        sl.set(e, 'stateInfo', 0)
        sl.set(e, 'iconId', 5003)
        sl.set(e, 'soulRate', mult)
        sl.set(e, 'effectEndurance', float(COIN_SECONDS))
        g = gp[gid]
        gl.set(g, 'refCategory', 2)
        gl.set(g, 'refId', spid)
        gl.set(g, 'goodsUseAnim', 6)            # hold up, like Transient Curse
        gl.set(g, 'sfxVariationId', gl.get(gp[312], 'sfxVariationId'))
        for k in ('enable_live', 'enable_gray', 'enable_white', 'enable_black', 'enable_multi', 'enable_pvp',
                  'isEquip'):  # isEquip: can go into the quick-item slot; without it the item can't be used
            gl.set(g, k, 1)
        APPEND[('caption', gid)] = {
            'ru': f'\n\nИспользуйте, чтобы на {COIN_SECONDS // 60} минуты\nполучать на {pct}% больше душ за убийства.',
            'en': f'\n\nUse to gain {pct}% more souls\nfrom kills for {COIN_SECONDS // 60} minutes.'}
        APPEND[('info', gid)] = {'ru': f' Увеличивает души за убийства на {pct}%.',
                                 'en': f' Increases souls from kills by {pct}%.'}

    # --- shops
    template = shp[1102]  # unlimited goods row (Throwing Knife)
    for rid, gid, price in SHOP_ROWS:
        r = shp.add(rid, template, b'')
        shl.set(r, 'equipType', 3)
        shl.set(r, 'equipId', gid)
        shl.set(r, 'value', price)
        shl.set(r, 'sellQuantity', -1)
        shl.set(r, 'eventFlag', -1)
    for rid, price in PRICE_CHANGES.items():
        shl.set(shp[rid], 'value', price)
