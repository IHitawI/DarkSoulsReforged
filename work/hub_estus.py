"""Estus: 3 flasks at the start, one more per kindled Estus Shard, at most 10 (DS3-style shards).

A shard does nothing in the bag: it is kindled at any bonfire ("Kindle an Estus Shard" in the bonfire menu)
or given to Anastacia, the Fire Keeper. Each one becomes one "Estus Flame" (a key item that counts them).
Bonfires keep filling the flask as in vanilla; FirelinkHub's DLL cuts the charges down to
3 + Estus Flames (max 10) whenever there are more. Healing beyond the flasks comes from miracles and lifegems.
Shards drop from seven bosses on the main path (an item lot awarded right after "boss defeated").
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins

SHARD = 608
ICON = 2018                    # Icon20 sprite 2018 (unused vanilla art): DS3 Estus Shard
KINDLED = 609                  # Estus Flame: one per kindled shard, the DLL counts these
HAS_SHARD = 11027598           # on while a shard is in the bag (shows the bonfire menu entry)
HAS_SHARD_EVENT = 11027596
KINDLE_SLOT = 15               # bonfire menu slot (14 = Travel, 13 = debug)
KINDLE_TEXT, GIVE_TEXT, DONE_TEXT = 15009300, 15009301, 15009302   # Event_text
BASE, MAX = 3, 10
ESTUS_CHARGED = list(range(201, 216, 2))   # Estus Flask +0..+7 with charges (quantity = charges)
FLAG_BASE = 11027700           # "shard k taken"
# boss event (map, event id) -> item lot
BOSSES = [
    ('m10_01_00_00', 11010901, 2603),   # Taurus Demon
    ('m10_01_00_00', 11010001, 2605),   # Bell Gargoyles
    ('m14_00_00_00', 11400001, 2607),   # Chaos Witch Quelaag
    ('m15_00_00_00', 11500001, 2613),   # Iron Golem
    ('m15_01_00_00', 11510001, 2615),   # Ornstein and Smough
    ('m12_00_00_00', 11200001, 2617),   # Great Grey Wolf Sif
    ('m13_01_00_00', 11310001, 2623),   # Gravelord Nito
]
MAPS = sorted({m for m, _, _ in BOSSES})
NL = chr(10)

TEXT = {}                      # item.msgbnd: (kind, id) -> {'ru', 'en'}
MENU_TEXT = {}                 # menu.msgbnd: ('event', id) -> {'ru', 'en', 'copy'}


def apply():
    gp, gl, _ = P['EquipParamGoods']
    g = gp.add(SHARD, gp[384], b'Estus Shard')          # a key item: can't be dropped or sold
    gl.set(g, 'iconId', ICON)
    gl.set(g, 'sortId', 4053)
    gl.set(g, 'maxNum', MAX - BASE)
    f = gp.add(KINDLED, gp[384], b'Estus Flame')
    gl.set(f, 'iconId', gl.get(gp[201], 'iconId'))       # the Estus Flask's own icon
    gl.set(f, 'sortId', 4054)
    gl.set(f, 'maxNum', MAX - BASE)
    lp, ll, _ = P['ItemLotParam']
    for k, (_, _, lot) in enumerate(BOSSES):
        assert lot not in lp and lot - 1 not in lp and lot + 1 not in lp, lot
        r = lp.add(lot, lp[2510], f'[FirelinkHub] Estus Shard {k + 1}'.encode())
        ll.set(r, 'lotItemId01', SHARD)
        ll.set(r, 'lotItemCategory01', 0x40000000)     # goods
        ll.set(r, 'getItemFlagId', FLAG_BASE + k)
    TEXT[('name', SHARD)] = {'ru': 'Осколок эстуса', 'en': 'Estus Shard'}
    TEXT[('info', SHARD)] = {'ru': 'Возожгите у костра или отдайте Хранительнице.',
                             'en': 'Kindle at a bonfire or give to the Fire Keeper.'}
    TEXT[('caption', SHARD)] = {
        'ru': NL.join(['Осколок фляги с эстусом, ещё тёплый.', 'Находят его там, где пал сильный враг.', '',
                       'Возожгите его у костра или отдайте', 'Хранительнице Огня: у костра будет',
                       'наполняться на одну флягу больше', f'(сначала {BASE}, всего не больше {MAX}).']),
        'en': NL.join(['A shard of an Estus Flask, still warm.', 'Found where a mighty foe has fallen.', '',
                       'Kindle it at a bonfire or give it to the', 'Fire Keeper: bonfires will fill one more',
                       f'charge (at first {BASE}, up to {MAX} in all).'])}
    TEXT[('name', KINDLED)] = {'ru': 'Пламя эстуса', 'en': 'Estus Flame'}
    TEXT[('info', KINDLED)] = {'ru': 'Возожжённые осколки: каждый — ещё одна фляга.',
                               'en': 'Kindled shards: each one is one more charge.'}
    TEXT[('caption', KINDLED)] = {
        'ru': NL.join(['Пламя возожжённых осколков эстуса.', '',
                       f'У костра наполняются {BASE} фляги и ещё', f'по одной за каждое пламя, всего не больше {MAX}.']),
        'en': NL.join(['The flame of kindled Estus Shards.', '',
                       f'A bonfire fills {BASE} charges and one more', f'for every flame, up to {MAX} in all.'])}
    MENU_TEXT[('event', KINDLE_TEXT)] = {'ru': 'Возжечь осколок эстуса', 'en': 'Kindle an Estus Shard', 'copy': None}
    MENU_TEXT[('event', GIVE_TEXT)] = {'ru': 'Отдать Хранительнице осколок эстуса?',
                                       'en': 'Give the Estus Shard to the Fire Keeper?', 'copy': None}
    MENU_TEXT[('event', DONE_TEXT)] = {'ru': 'Пламя эстуса разгорается.' + NL + 'У костра наполнится ещё одна фляга.',
                                       'en': 'The Estus flame grows.' + NL + 'Bonfires fill one more charge.', 'copy': None}


def patch_map(data, edf, mapname):
    """Award the shard lot right after the boss's "boss defeated" (last one in the event)."""
    ev = Emevd(data)
    for m, eid, lot in BOSSES:
        if m != mapname:
            continue
        e = next(e for e in ev.events if e['id'] == eid)
        at = max(k for k, (b, i, _) in enumerate(e['ins']) if (b, i) == (2003, 12)) + 1
        e['ins'].insert(at, _ins(edf, 2003, 36, lot))   # 36: also to the co-op partner
    return build_emevd(ev)


def patch_bonfire(src):
    """Bonfire dialog: "Kindle an Estus Shard" while one is in the bag (flag HAS_SHARD)."""
    i20, i24 = ' ' * 20, ' ' * 24
    anchor_add = f'{i20}AddTalkListData(11, 15000270, 11810000)' + NL
    assert src.count(anchor_add) == 1
    src = src.replace(anchor_add, anchor_add + f'{i20}# action:{KINDLE_TEXT}:"Kindle an Estus Shard"' + NL
                      + f'{i20}AddTalkListData({KINDLE_SLOT}, {KINDLE_TEXT}, {HAS_SHARD})' + NL)
    branch = [f'{i20}elif GetTalkListEntryResult() == {KINDLE_SLOT}:', f'{i24}# FirelinkHub: kindle an Estus Shard',
              f'{i24}PlayerEquipmentQuantityChange(ItemType.Goods, {SHARD}, -1)',
              f'{i24}PlayerEquipmentQuantityChange(ItemType.Goods, {KINDLED}, 1)',
              f'{i24}SetEventFlag({HAS_SHARD}, FlagState.Off)']
    anchor_branch = NL + f'{i20}elif GetTalkListEntryResult() == 1:' + NL
    assert src.count(anchor_branch) == 1
    return src.replace(anchor_branch, NL + NL.join(branch) + anchor_branch)


def patch_common(data, edf):
    """common.emevd: HAS_SHARD follows "a shard is in the bag" (the bonfire menu reads it)."""
    ev = Emevd(data)
    ev.events.append({'id': HAS_SHARD_EVENT, 'rest': 0, 'params': [], 'ins': [
        _ins(edf, 2003, 2, HAS_SHARD, 0),
        _ins(edf, 3, 4, 0, 3, SHARD, 1),          # goods in the bag
        _ins(edf, 2003, 2, HAS_SHARD, 1),
        _ins(edf, 3, 4, 0, 3, SHARD, 0),
        _ins(edf, 1000, 4, 1)]})
    next(e for e in ev.events if e['id'] == 0)['ins'].insert(0, _ins(edf, 2000, 0, 0, HAS_SHARD_EVENT, 0))
    return build_emevd(ev)
