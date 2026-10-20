"""Debug menu at every bonfire: "[Reforged debug]" - test any part of the mod in a minute.

Built by default; `python build.py --release` leaves it out. Every bonfire uses the same dialog file, so
the patched one is copied into every map (build.py). The menu is built in setup() from the mod's own
lists - fast travel bonfires (hub_travel + hub_bonfires), bosses (hub_bosses), champions, NPCs, quests -
so whatever is added to those lists shows up here too. An entry is (slot, ru, en, action): action is a
list of ESD lines, a submenu (list of entries) or None (back). `ru` may be an existing Event_text id
(the fast travel names), then `en` is ignored.

Why "unlock all bonfires" did not work before: it lit an old list of 44 bonfires (none of the restored
ones), the fast travel entry also needs the Lordvessel flag (710), and the old warp used the vanilla
warp menu (21 bonfires). Now: all lit flags + 710, and the warp goes through fast travel's own request
flags (common.emevd), which do not care whether the bonfire is lit. Setting all the lit flags from the open
bonfire menu locked the player at the bonfire, so the menu only sets hub_travel.UNLOCK_REQUEST, closes, and
an event in common.emevd sets the flags a second later.
"""
from hub_npc_esd import BELL1_FLAG, MOVED_FLAG, GREETED_FLAG
from hub_npcs import NPCS, LARGE_EMBER_GIVEN, GIANT_GATE
import hub_yulia, hub_respec, hub_estus, hub_champions, hub_travel, hub_bosses, hub_quests, hub_weapons, hub_items
from load import P

MENU_TEXT = 15009500   # Event_text ids 15009500.. (debug only)
DONE_TEXT = 15009699   # "Done" after an action
BELL2_FLAG = 11400200  # second Bell of Awakening (Blighttown)
LORDVESSEL = hub_travel.LORDVESSEL
GOD_SP, ONE_SHOT_SP = 92900, 92901
BUFF_SECONDS = 1800

SPELL_KIT = {  # spells changed by AllyHeal and the mod's own
    5000: 1, 5010: 1, 5020: 1, 5040: 1, 5600: 1, 5610: 1, 5200: 1,
    4310: 1, 3610: 1, 3600: 1, 3410: 1, 3510: 1, 3540: 1, 3500: 1, 3530: 1,
    5620: 1, 5630: 1, 5060: 1, 5330: 1, 5530: 1, 3080: 1, 4070: 1, 5540: 1, 5640: 1,
}
CATALYSTS = {1360000: 1, 1330000: 1, 1300000: 1}  # Talisman, Pyromancy Flame, Sorcerer's Catalyst
CONSUMABLES = {600: 10, 601: 5, 602: 3, 604: 5, 605: 3, 606: 2, 381: 5, 382: 5, 383: 5, 296: 5, 293: 5, 380: 10}
MATERIALS = {1000: 30, 1010: 30, 1020: 30, 1030: 30, 1040: 10, 1050: 10, 1060: 10, 1070: 5, 1080: 5, 1090: 5,
             1100: 5, 1110: 10, 1120: 10, 1130: 20}
EMBERS = {i: 1 for i in (800, 801, 802, 806, 807, 808, 809, 810, 812, 813)}
TOOLS = {2600: 1, 2601: 1, 2602: 1, 2607: 1, 2608: 1}   # smithboxes, repairbox, Rite of Kindling, Bottomless Box
KEYS = {i: 1 for i in list(range(2001, 2023)) + [2100, 2510]}   # every key, the Master Key, the Lordvessel
COVENANT = {109: 30, 374: 30, 375: 30, 1110: 30}   # Eye of Death, Souvenir of Reprisal, Sunlight Medal, Dragon Scale
RINGS = {128: 1, 100: 1, 143: 1}                  # Dark Wood Grain (the combo ring), Havel's, Favor and Protection
# ChangePlayerStat sets the number only: HP, stamina and attunement slots stay as they were (a Cleric with
# Attunement 99 showed 1 slot and 594 HP) until something recomputes them - a level up at the bonfire.
# ChangePlayerStat sets the number only: HP, stamina and attunement slots stay as they were (a Cleric with
# Attunement 99 still had 1 slot and 594 HP) until a level up at the bonfire recomputes them.
STAT_NAMES = ('Vitality', 'Attunement', 'Endurance', 'Strength', 'Dexterity', 'Intelligence', 'Faith')   # no Resistance in DSR's ESD
YULIA_FLAGS = [hub_yulia.IAITO_FLAG, hub_yulia.UCHI_FLAG, hub_yulia.FOUND_FLAG]
EXTRA_BOSSES = [(11010001, 'Горгульи колокола', 'Bell Gargoyles'), (GIANT_GATE, 'Орнштейн и Смоуг', 'Ornstein and Smough')]

MENU = []
TEXT = {}
TEXT_IDS = {}


def flags(ids, on):
    return [f'SetEventFlag({i}, FlagState.{"On" if on else "Off"})' for i in ids]


def give(kind, items):
    return [f'PlayerEquipmentQuantityChange(ItemType.{kind}, {i}, {n})' for i, n in items.items()]


def stats(value):
    return [f'ChangePlayerStat(PlayerStat.{s}, ChangeType.Set, {value})' for s in STAT_NAMES]


def _leave_talk():
    return hub_travel.STAND_UP


def _warp_menu(travel):
    """Zone -> bonfire, every bonfire (lit or not): fast travel's request flag, its event in common.emevd warps."""
    _, zone_id, bonfire_id, _ = hub_travel.texts(travel)
    zones = []
    for z, mp in enumerate(hub_travel.ZONES, 1):
        mine = [k for k, (m, _, _) in enumerate(travel) if m == mp]
        if not mine:
            continue
        sub = [(s, bonfire_id[k], None, flags([hub_travel.REQUEST_BASE + k], True) + _leave_talk())
               for s, k in enumerate(mine, 1)]
        zones.append((z, zone_id[mp], None, sub + [(99, 'Назад', 'Back', None)]))
    return zones + [(99, 'Назад', 'Back', None)]


def _boss_menus():
    names = []
    for k, (_, flag, _, _) in enumerate(hub_bosses.BOSSES):
        names.append((flag, *hub_bosses.NAMES[k]))
    names += EXTRA_BOSSES
    half = (len(names) + 1) // 2
    out = []
    for part in (names[:half], names[half:]):
        out.append([(s, ru, en, flags([flag], True)) for s, (flag, ru, en) in enumerate(part, 1)]
                   + [(99, 'Назад', 'Back', None)])
    return out


def setup(travel):
    """Builds MENU and its texts from the mod's lists. build.py calls it after TRAVEL is known."""
    bosses1, bosses2 = _boss_menus()
    champs = range(len(hub_champions.CHAMPIONS))
    MENU[:] = [
        (1, 'Костры и перемещение', 'Bonfires and travel', [
            (1, 'Открыть все костры (и «Путешествие»)', 'Unlock all bonfires (and Travel)',
             flags([hub_travel.UNLOCK_REQUEST], True) + _leave_talk()),
            (2, 'Телепорт к любому костру', 'Warp to any bonfire', _warp_menu(travel)),
            (3, 'Телепорт к чемпиону этой зоны', 'Warp to the champion here',
             flags([hub_champions.WARP_REQUEST], True) + _leave_talk()),
            (4, 'Сохранить игру', 'Save the game', ['RequestSave(0)']),
            (99, 'Назад', 'Back', None),
        ]),
        (2, 'Персонаж', 'Character', [
            (1, '+100 000 душ', '+100,000 souls', ['ChangePlayerStat(PlayerStat.SoulsCollected, ChangeType.Add, 100000)']),
            (2, '+1 000 000 душ', '+1,000,000 souls', ['ChangePlayerStat(PlayerStat.SoulsCollected, ChangeType.Add, 1000000)']),
            (3, 'Характеристики 40 — потом подними уровень', 'Stats 40 - then level up once', stats(40)),
            (4, 'Характеристики 99 — потом подними уровень', 'Stats 99 - then level up once', stats(99)),
            (5, 'Магия: Настр. 40, Инт. 40, Вера 50 — потом подними уровень', 'Magic: Att 40, Int 40, Fth 50 - then level up',
             [f'ChangePlayerStat(PlayerStat.{s}, ChangeType.Set, {v})' for s, v in
              (('Attunement', 40), ('Intelligence', 40), ('Faith', 50))]),
            (6, 'Режим бога: урон по тебе ×0.05 (30 мин)', 'God mode: damage taken x0.05 (30 min)',
             [f'GiveSpEffectToPlayer({GOD_SP})']),
            (7, 'Убивать с удара: урон ×20 (30 мин)', 'One-shot: damage x20 (30 min)', [f'GiveSpEffectToPlayer({ONE_SHOT_SP})']),
            (8, '+10 человечности', '+10 Humanity', give('Goods', {500: 10})),
            (99, 'Назад', 'Back', None),
        ]),
        (3, 'Предметы', 'Items', [
            (1, 'Заклинания и катализаторы', 'Spells and catalysts', give('Goods', SPELL_KIT) + give('Weapon', CATALYSTS)),
            (2, 'Камни жизни, травы, монеты (до лимита)', 'Lifegems, herbs, coins (to the cap)', give('Goods', CONSUMABLES)),
            (3, 'Титанит и чешуя', 'Titanite and scales', give('Goods', MATERIALS)),
            (4, 'Все угольки', 'All embers', give('Goods', EMBERS)),
            (5, 'Кузница, ремонт, шкатулка, Обряд возжжения', 'Smithboxes, repairbox, box, Rite of Kindling',
             give('Goods', TOOLS)),
            (6, 'Все ключи и Сосуд Повелителя', 'All keys and the Lordvessel', give('Goods', KEYS)),
            (7, 'Дары ковенантов ×30', 'Covenant offerings x30', give('Goods', COVENANT)),
            (8, 'Перебалансированное оружие', 'Rebalanced weapons', give('Weapon', {w: 1 for w in hub_weapons.WEAPONS})),
            (10, 'Кольца: Тёмное Древесное Зерно, Хавел, Покровительство', 'Rings: Dark Wood Grain, Havel, Favor',
             give('Accessory', RINGS)),
            (11, 'Иайто и Утигатана', 'Iaito and Uchigatana', give('Weapon', {hub_yulia.IAITO: 1, hub_yulia.UCHIGATANA: 1})),
            (12, 'Камень перерождения', 'Rebirth Stone', give('Goods', {hub_respec.GOODS_ID: 1})),
            (13, 'Подвеска', 'Pendant', give('Goods', {376: 1})),
            (99, 'Назад', 'Back', None),
        ]),
        (4, 'Эстус', 'Estus', [
            (1, 'Осколок эстуса', 'Estus Shard', give('Goods', {hub_estus.SHARD: 1})),
            (2, '+1 Пламя эстуса (+1 фляга сразу)', '+1 Estus Flame (+1 charge now)', give('Goods', {hub_estus.KINDLED: 1})),
            (3, 'Пламя эстуса: сбросить (3 фляги)', 'Estus Flames: reset (3 charges)',
             give('Goods', {hub_estus.KINDLED: -1}) * (hub_estus.MAX - hub_estus.BASE)),
            (99, 'Назад', 'Back', None),
        ]),
        (5, 'Боссы: отметить побеждённым', 'Bosses: mark as defeated', [
            (1, 'Боссы, часть 1', 'Bosses, part 1', bosses1),
            (2, 'Боссы, часть 2', 'Bosses, part 2', bosses2),
            (99, 'Назад', 'Back', None),
        ]),
        (6, 'Чемпионы и поручения', 'Champions and bounties', [
            (1, 'Телепорт к чемпиону этой зоны', 'Warp to the champion here',
             flags([hub_champions.WARP_REQUEST], True) + _leave_talk()),
            (2, 'Вернуть всех чемпионов', 'Bring all champions back', flags([hub_champions.event_id(k) for k in champs], False)),
            (3, 'Отметить всех чемпионов убитыми', 'Mark all champions killed', flags([hub_champions.event_id(k) for k in champs], True)),
            (4, 'Поручения: сбросить', 'Bounties: reset', flags([hub_quests.REWARD_FLAG + i for i in range(len(hub_quests.BOUNTIES))], False)),
            (5, 'Советы воина: сбросить', "Warrior's advice: reset",
             flags([hub_quests.TIP_FLAG + i for i in range(len(hub_quests.TIPS))] + [hub_quests.PASS_FLAG, hub_quests.USED_FLAG], False)),
            (99, 'Назад', 'Back', None),
        ]),
        (7, 'NPC и сюжет', 'NPCs and story', [
            (1, 'Первый колокол прозвонён', 'First bell rung', flags([BELL1_FLAG], True)),
            (2, 'Второй колокол прозвонён', 'Second bell rung', flags([BELL2_FLAG], True)),
            (3, 'Торговец нежити: в Храм', 'Undead Merchant: move to Firelink', flags([MOVED_FLAG], True)),
            (4, 'Торговец нежити: обратно в Город', 'Undead Merchant: back to the Burg', flags([MOVED_FLAG, GREETED_FLAG], False)),
            (5, 'Андре, торговцы, Гигант: в Храм', 'Andre, merchants, Giant: move to Firelink',
             flags([n['moved'] for n in NPCS.values()], True)),
            (6, 'Андре, торговцы, Гигант: обратно', 'Andre, merchants, Giant: send back',
             flags([n['moved'] for n in NPCS.values()], False)),
            (7, 'Андре: уголёк отдан', 'Andre: Large Ember given', flags([LARGE_EMBER_GIVEN], True)),
            (8, 'Квест Юлии: завершить', 'Yulia quest: complete', flags(YULIA_FLAGS, True)),
            (10, 'Квест Юлии: сбросить', 'Yulia quest: reset', flags(YULIA_FLAGS, False)),
            (11, 'Домнал: в Храм', 'Domhnall: to Firelink', flags([1430], False) + flags([1431], True)),
            (12, 'Сбросить приветствия и Подвеску', 'Reset greetings and Pendant',
             flags([11027913, 11027914, 11027915, 11027916], False)),
            (99, 'Назад', 'Back', None),
        ]),
        (99, 'Назад', 'Back', None),
    ]
    _texts()


def _texts():
    """Text ids in menu order: {id(entry list): [ids]}; reused ids (int `ru`) get no new text."""
    TEXT.clear()
    TEXT_IDS.clear()
    TEXT[('event', MENU_TEXT)] = {'ru': '[Отладка Reforged]', 'en': '[Reforged debug]', 'copy': None}
    TEXT[('event', DONE_TEXT)] = {'ru': 'Готово.', 'en': 'Done.', 'copy': None}
    nxt = MENU_TEXT + 1
    seen = {}
    def walk(menu):
        nonlocal nxt
        TEXT_IDS[id(menu)] = []
        for slot, ru, en, act in menu:
            if isinstance(ru, int):
                TEXT_IDS[id(menu)].append(ru)
            else:
                if (ru, en) not in seen:
                    seen[(ru, en)] = nxt
                    TEXT[('event', nxt)] = {'ru': ru, 'en': en, 'copy': None}
                    nxt += 1
                TEXT_IDS[id(menu)].append(seen[(ru, en)])
            if isinstance(act, list) and act and isinstance(act[0], tuple):
                walk(act)
    walk(MENU)
    assert nxt < DONE_TEXT, nxt


def apply():
    """Debug-only SpEffects: god mode and one-shot (on the player, BUFF_SECONDS)."""
    sp, sl, _ = P['SpEffectParam']
    for sid, name, fields, val in (
            (GOD_SP, b'[Debug] god mode', ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate',
                                           'neutralDamageCutRate', 'magicDamageCutRate', 'fireDamageCutRate',
                                           'thunderDamageCutRate'), 0.05),
            (ONE_SHOT_SP, b'[Debug] one-shot', ('physicsAttackPowerRate', 'magicAttackPowerRate',
                                                'fireAttackPowerRate', 'thunderAttackPowerRate'), 20.0)):
        e = sp.add(sid, sp[3040], name)
        sl.set(e, 'staminaRecoverChangeSpeed', 0)
        sl.set(e, 'stateInfo', 0)
        sl.set(e, 'iconId', 0)
        sl.set(e, 'spCategory', 0)       # both at once: not one category replacing the other
        sl.set(e, 'effectEndurance', float(BUFF_SECONDS))
        for f in fields:
            sl.set(e, f, val)


def _menu(menu, ind, leave):
    """ESD lines for one (sub)menu loop at indentation `ind`."""
    # the menu we came from is still open: close it first, or the new list is drawn over the old one
    out = [f'{ind}CloseShopMessage()',
           f'{ind}while True:', f'{ind}    ClearTalkListData()', f'{ind}    ShowShopMessage(TalkOptionsType.Old, False, False)']
    for (slot, ru, en, act), tid in zip(menu, TEXT_IDS[id(menu)]):
        out += [f'{ind}    # action:{tid}', f'{ind}    AddTalkListData({slot}, {tid}, -1)']
    back = [s for s, _, _, a in menu if a is None]
    out += [f'{ind}    if {leave}:', f'{ind}        Goto(\'L1\')',
            f'{ind}    elif ' + ' or '.join(f'GetTalkListEntryResult() == {s}' for s in [0] + back) + ':',
            f'{ind}        break']
    for slot, ru, en, act in menu:
        if act is None:
            continue
        out.append(f'{ind}    elif GetTalkListEntryResult() == {slot}:')
        i2 = ind + '        '
        if act and isinstance(act[0], tuple):
            out += _menu(act, i2, leave)
        else:
            out += [f'{i2}{l}' for l in act]
            if not act[-1].startswith('Goto'):     # every action says it worked; the menu comes back after
                out += [f'{i2}OpenGenericDialog(DialogBoxType.CenterBottom1, {DONE_TEXT}, DialogResult.Left, '
                        f'DialogBoxStyle.OrnateNoOptions, 2)',
                        f'{i2}if not IsGenericDialogOpen():', f'{i2}    pass']
    return out


def patch_bonfire(src):
    """Adds slot 13 '[Reforged debug]' to the bonfire menu and its submenus."""
    assert MENU, 'hub_debug.setup() first'
    i20, i24 = ' ' * 20, ' ' * 24
    anchor_add = f'{i20}AddTalkListData(11, 15000270, 11810000)\n'
    assert src.count(anchor_add) == 1
    src = src.replace(anchor_add, anchor_add + f'{i20}# action:{MENU_TEXT}:"[Reforged debug]"\n'
                                                f'{i20}AddTalkListData(13, {MENU_TEXT}, -1)\n')
    anchor_branch = f'\n{i20}elif GetTalkListEntryResult() == 1:\n'   # line start: nested menus have deeper ones
    assert src.count(anchor_branch) == 1
    leave = '(CompareBonfireState(0) or IsPlayerDead() or HasPlayerBeenAttacked() or IsTalkingToSomeoneElse() or GetDistanceToPlayer() > 8)'
    lines = [f'{i20}elif GetTalkListEntryResult() == 13:', f'{i24}# Reforged debug menu']
    lines += _menu(MENU, i24, leave)
    return src.replace(anchor_branch, '\n' + '\n'.join(lines) + anchor_branch)
