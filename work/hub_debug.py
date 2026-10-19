"""Debug build only: a "[FirelinkHub debug]" entry in the bonfire menu for testing the mod quickly.

Every bonfire in the game uses the same dialog file, so the patched one is copied into every map
(build.py). The menu has submenus; each entry is (slot, ru, en, action) where action is a list of
ESD lines or a nested menu (list of entries).
"""
from hub_npc_esd import BELL1_FLAG, MOVED_FLAG, GREETED_FLAG
from hub_npcs import NPCS, LARGE_EMBER_GIVEN
import hub_yulia, hub_respec, hub_estus, hub_champions

MENU_TEXT = 15009100   # Event_text ids 15009100.. (debug only)

GOODS = {  # goods id: count
    # spells changed by AllyHeal
    5000: 1, 5010: 1, 5020: 1, 5040: 1, 5600: 1, 5610: 1, 5200: 1,
    4310: 1, 3610: 1, 3600: 1, 3410: 1, 3510: 1, 3540: 1, 3500: 1, 3530: 1,
    # FirelinkHub items
    600: 10, 601: 10, 602: 5, 604: 5, 605: 5, 606: 5, 381: 5, 382: 5, 383: 5, 296: 5, 293: 5, 380: 10,
    # FirelinkHub spells (hub_spells.py)
    5620: 1, 5630: 1, 5060: 1, 5330: 1, 5530: 1, 3080: 1, 4070: 1,
}
WEAPONS = {1360000: 1, 1330000: 1, 1300000: 1}  # Talisman, Pyromancy Flame, Sorcerer's Catalyst
STATS = [('Attunement', 40), ('Intelligence', 40), ('Faith', 50)]
YULIA_FLAGS = [hub_yulia.IAITO_FLAG, hub_yulia.UCHI_FLAG, hub_yulia.FOUND_FLAG]


def bonfire_flags():
    with open('hub/bonfire_flags.txt') as f:
        return [int(x) for x in f.read().split() if not x.startswith('199')]  # skip the m99 test map


def flags(ids, on):
    return [f'SetEventFlag({i}, FlagState.{"On" if on else "Off"})' for i in ids]


def give(kind, items):
    return [f'PlayerEquipmentQuantityChange(ItemType.{kind}, {i}, {n})' for i, n in items.items()]


WARP = None   # placeholder: the warp entry needs the bonfire's labels, see _action()

MENU = [
    (1, 'Персонаж и предметы', 'Character and items', [
        (1, 'Набор тестера (заклинания, катализаторы, предметы)', 'Tester kit (spells, catalysts, items)',
         give('Goods', GOODS) + give('Weapon', WEAPONS)),
        (2, '+100 000 душ', '+100,000 souls', ['ChangePlayerStat(PlayerStat.SoulsCollected, ChangeType.Add, 100000)']),
        (3, 'Статы для магии (Настр. 40, Инт. 40, Вера 50)', 'Magic stats (Att 40, Int 40, Fth 50)',
         [f'ChangePlayerStat(PlayerStat.{s}, ChangeType.Set, {v})' for s, v in STATS]),
        (4, 'Камень перерождения', 'Rebirth Stone', give('Goods', {hub_respec.GOODS_ID: 1})),
        (5, 'Иайто и Утигатана', 'Iaito and Uchigatana',
         give('Weapon', {hub_yulia.IAITO: 1, hub_yulia.UCHIGATANA: 1})),
        (6, 'Большой уголёк', 'Large Ember', give('Goods', {800: 1})),
        (7, '+10 человечности', '+10 Humanity', give('Goods', {500: 10})),
        (8, 'Подвеска', 'Pendant', give('Goods', {376: 1})),
        (10, 'Осколок эстуса (+1 фляга)', 'Estus Shard (+1 charge)', give('Goods', {hub_estus.SHARD: 1})),
        (9, 'Назад', 'Back', None),
    ]),
    (2, 'NPC и квесты', 'NPCs and quests', [
        (1, 'Прозвонить первый колокол', 'Ring the first bell', flags([BELL1_FLAG], True)),
        (2, 'Торговец нежити: в Храм', 'Undead Merchant: move to Firelink', flags([MOVED_FLAG], True)),
        (3, 'Торговец нежити: обратно в Город', 'Undead Merchant: back to the Burg',
         flags([MOVED_FLAG, GREETED_FLAG], False)),
        (4, 'Андре и торговцы: в Храм', 'Andre and merchants: move to Firelink',
         flags([n['moved'] for n in NPCS.values()], True)),
        (5, 'Андре и торговцы: обратно', 'Andre and merchants: send back',
         flags([n['moved'] for n in NPCS.values()], False)),
        (6, 'Андре: уголёк отдан', 'Andre: Large Ember given', flags([LARGE_EMBER_GIVEN], True)),
        (7, 'Квест Юлии: завершить', 'Yulia quest: complete', flags(YULIA_FLAGS, True)),
        (8, 'Квест Юлии: сбросить', 'Yulia quest: reset', flags(YULIA_FLAGS, False)),
        (10, 'Домнал: в Храм', 'Domhnall: to Firelink', flags([1430], False) + flags([1431], True)),
        (11, 'Сбросить приветствия и Подвеску', 'Reset greetings and Pendant',
         flags([11027913, 11027914, 11027915, 11027916], False)),
        (9, 'Назад', 'Back', None),
    ]),
    (3, 'Открыть все костры', 'Unlock all bonfires', flags(bonfire_flags(), True)),
    (5, 'Чемпионы', 'Champions', [
        (1, 'Телепорт к чемпиону этой зоны', 'Warp to the champion here', flags([hub_champions.WARP_REQUEST], True)),
        (2, 'Вернуть всех чемпионов', 'Bring all champions back', flags([hub_champions.event_id(k) for k in range(len(hub_champions.CHAMPIONS))], False)),
        (9, 'Назад', 'Back', None),
    ]),
    (4, 'Телепорт к любому костру', 'Warp to any bonfire', 'warp'),
    (9, 'Назад', 'Back', None),
]

TEXT = {}


def _texts():
    """Assigns text ids in menu order: {id(entry list): [ids]}."""
    ids, nxt = {}, MENU_TEXT + 1
    def walk(menu):
        nonlocal nxt
        ids[id(menu)] = []
        for slot, ru, en, act in menu:
            ids[id(menu)].append(nxt)
            TEXT[('event', nxt)] = {'ru': ru, 'en': en, 'copy': None}
            nxt += 1
            if isinstance(act, list) and act and isinstance(act[0], tuple):
                walk(act)
    walk(MENU)
    return ids


TEXT[('event', MENU_TEXT)] = {'ru': '[Отладка FirelinkHub]', 'en': '[FirelinkHub debug]', 'copy': None}
TEXT_IDS = _texts()


def _menu(menu, ind, leave):
    """ESD lines for one (sub)menu loop at indentation `ind`."""
    out = [f'{ind}while True:', f'{ind}    ClearTalkListData()', f'{ind}    ShowShopMessage(TalkOptionsType.Old, False, False)']
    for (slot, ru, en, act), tid in zip(menu, TEXT_IDS[id(menu)]):
        out += [f'{ind}    # action:{tid}:"{en}"', f'{ind}    AddTalkListData({slot}, {tid}, -1)']
    back = [s for s, _, _, a in menu if a is None]
    out += [f'{ind}    if {leave}:', f'{ind}        Goto(\'L1\')',
            f'{ind}    elif ' + ' or '.join(f'GetTalkListEntryResult() == {s}' for s in [0] + back) + ':',
            f'{ind}        break']
    for slot, ru, en, act in menu:
        if act is None:
            continue
        out.append(f'{ind}    elif GetTalkListEntryResult() == {slot}:')
        i2 = ind + '        '
        if act == 'warp':
            out += [f'{i2}{l}' for l in flags(bonfire_flags(), True)]
            out += [f'{i2}StartWarpMenuInit()',
                    f'{i2}if WasWarpMenuDestinationSelected():',
                    f'{i2}    ForceEndTalk(0)',
                    f'{i2}    ClearTalkProgressData()',
                    f'{i2}    CloseShopMessage()',
                    f'{i2}    Goto(\'L12\')',
                    f'{i2}elif not IsMenuOpen(MenuType.Warp):',
                    f'{i2}    pass']
        elif act and isinstance(act[0], tuple):
            out += _menu(act, i2, leave)
        else:
            out += [f'{i2}{l}' for l in act]
    return out


def patch_bonfire(src):
    """Adds slot 13 '[Debug]' to the bonfire menu and its submenus."""
    i20, i24 = ' ' * 20, ' ' * 24
    anchor_add = f'{i20}AddTalkListData(11, 15000270, 11810000)\n'
    assert src.count(anchor_add) == 1
    src = src.replace(anchor_add, anchor_add + f'{i20}# action:{MENU_TEXT}:"[FirelinkHub debug]"\n'
                                                f'{i20}AddTalkListData(13, {MENU_TEXT}, -1)\n')
    anchor_branch = f'\n{i20}elif GetTalkListEntryResult() == 1:\n'   # line start: nested menus have deeper ones
    assert src.count(anchor_branch) == 1
    leave = '(CompareBonfireState(0) or IsPlayerDead() or HasPlayerBeenAttacked() or IsTalkingToSomeoneElse() or GetDistanceToPlayer() > 8)'
    lines = [f'{i20}elif GetTalkListEntryResult() == 13:', f'{i24}# FirelinkHub debug menu']
    lines += _menu(MENU, i24, leave)
    return src.replace(anchor_branch, '\n' + '\n'.join(lines) + anchor_branch)
