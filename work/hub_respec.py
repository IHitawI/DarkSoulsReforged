"""Rebirth Stone: give it to Anastacia, the Fire Keeper in Firelink, to start your build over.

Stats go back to your class's starting values and every soul spent on levels comes back.
Her new dialog (t102693) takes the stone; FirelinkHub's DLL sees it leave the inventory and rewrites
the stats in memory (the same trick as the amber herbs).
"""
from load import *

GOODS_ID = 607
TEMPLATE = 384          # Peculiar Doll: a key item - can't be dropped, sold or stored
ICON = 2008             # atlas cell C14: DS2 Soul Vessel (the DS2 respec item)
PRICE = 20000
SHOP_ROW = 1137         # Undead Merchant (male)
GIVE_TEXT = 15009030    # Event_text: "Give the Rebirth Stone to the Fire Keeper?"
DONE_TEXT = 15009031    # Event_text: result message
ANASTACIA_TALK = 102693   # new dialog file in m10_02

TEXT = {}               # menu.msgbnd: (kind, id) -> {'ru', 'en', 'copy'}
ITEM_TEXT = {}          # item.msgbnd: (kind, id) -> {'ru', 'en'}


def apply():
    gp, gl, _ = P['EquipParamGoods']
    g = gp.add(GOODS_ID, gp[TEMPLATE], b'Rebirth Stone')
    gl.set(g, 'iconId', ICON)
    gl.set(g, 'sortId', 4052)
    shp, shl, _ = P['ShopLineupParam']
    r = shp.add(SHOP_ROW, shp[1102], b'')   # unlimited goods row (Throwing Knife)
    shl.set(r, 'equipType', 3)
    shl.set(r, 'equipId', GOODS_ID)
    shl.set(r, 'value', PRICE)
    shl.set(r, 'sellQuantity', -1)
    shl.set(r, 'eventFlag', -1)
    ITEM_TEXT[('name', GOODS_ID)] = {'ru': 'Камень перерождения', 'en': 'Rebirth Stone'}
    ITEM_TEXT[('info', GOODS_ID)] = {'ru': 'Отдайте Хранительнице Огня, чтобы начать путь заново.',
                                     'en': 'Give to the Fire Keeper to begin your path anew.'}
    ITEM_TEXT[('caption', GOODS_ID)] = {
        'ru': 'Тёплый камень, в котором дремлет искра\nпервого пламени. Хранительница Огня\n'
              'в Храме Огня знает, что с ним делать.\n\n'
              'Отдайте его Хранительнице: характеристики\nвернутся к начальным для вашего класса,\n'
              'а все души, потраченные на уровни,\nвернутся к вам.',
        'en': 'A warm stone in which a spark of the first\nflame lies dormant. The Fire Keeper of\n'
              'Firelink Shrine knows what to do with it.\n\n'
              'Give it to her: your attributes return to\nthe starting values of your class, and every\n'
              'soul spent on levels is returned to you.'}
    TEXT[('event', GIVE_TEXT)] = {'ru': 'Отдать Хранительнице камень перерождения?',
                                  'en': 'Give the Rebirth Stone to the Fire Keeper?', 'copy': None}
    TEXT[('event', DONE_TEXT)] = {'ru': 'Тело вернулось к прежнему облику.\nДуши, потраченные на уровни, возвращены.',
                                  'en': 'Your body has returned to its former self.\nThe souls spent on levels are returned.',
                                  'copy': None}


ANASTACIA_ENTITY = 6060     # c2750_0000 in Firelink; vanilla gives her no dialog at all (talk id 0)
ANASTACIA_PART = 'c2750_0000'


def patch_msb(data):
    """Give Anastacia the new dialog."""
    import struct
    from msb import Msb, Part
    m = Msb(data)
    e = next(e for e in m.parts.entries if Part(e).name == ANASTACIA_PART)
    p = Part(e)
    assert p.entity_id == ANASTACIA_ENTITY and struct.unpack_from('<i', e, p.type_off + 16)[0] == 0
    struct.pack_into('<i', e, p.type_off + 16, ANASTACIA_TALK)
    return m.build()


def _give_block(goods, give_text, after, away, ind):
    """The give dialog for one item: Yes -> take it, run `after`, show DONE_TEXT."""
    i = ' ' * ind
    lines = [
        f'OpenGenericDialog(DialogBoxType.CenterBottom2, {give_text}, DialogResult.Leave, DialogBoxStyle.Unk, 2)',
        f'if CheckSelfDeath() or IsAttackedBySomeone() or ({away}):',
        f'    ForceCloseGenericDialog()',
        f"    Goto('L1')",
        f'elif ((GetGenericDialogButtonResult() == DialogResult.Cancel and not IsGenericDialogOpen()) or',
        f'      (GetGenericDialogButtonResult() == DialogResult.Right and not IsGenericDialogOpen())):',
        f"    Goto('L1')",
        f'elif GetGenericDialogButtonResult() == DialogResult.Left and not IsGenericDialogOpen():',
        f'    PlayerEquipmentQuantityChange(ItemType.Goods, {goods}, -1)',
    ] + [f'    {a}' for a in after] + [
        f'    OpenGenericDialog(DialogBoxType.CenterMiddleDimScreen1, {after_text(goods)}, DialogResult.Left,',
        f'                      DialogBoxStyle.OrnateNoOptions, 2)',
        f'    if not IsGenericDialogOpen() or ({away}):',
        f'        ForceCloseGenericDialog()',
        f"        Goto('L1')",
    ]
    return chr(10).join(i + l for l in lines)


def after_text(goods):
    import hub_estus
    return DONE_TEXT if goods == GOODS_ID else hub_estus.DONE_TEXT


def anastacia_esd():
    """t102693: with the Rebirth Stone or an Estus Shard in the inventory a "Talk" prompt appears;
    talking offers to give it (the stone first). A shard becomes an Estus Flame (hub_estus.py)."""
    import hub_estus
    near = 'GetRelativeAngleBetweenPlayerAndSelf() <= 90 and GetDistanceToPlayer() <= 6'   # she sits behind bars, ~4.7 m away
    away = ('IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled() or IsClientPlayer()'
            ' or GetRelativeAngleBetweenPlayerAndSelf() > 120 or GetDistanceToPlayer() > 8')
    has_stone = f'DoesPlayerHaveItem(ItemType.Goods, {GOODS_ID})'
    has_shard = f'DoesPlayerHaveItem(ItemType.Goods, {hub_estus.SHARD})'
    has_any = f'({has_stone} or {has_shard})'
    stone = _give_block(GOODS_ID, GIVE_TEXT, [], away, 16)
    shard = _give_block(hub_estus.SHARD, hub_estus.GIVE_TEXT,
                        [f'PlayerEquipmentQuantityChange(ItemType.Goods, {hub_estus.KINDLED}, 1)'], away, 16)
    return f'''# -*- coding: utf-8 -*-
def t{ANASTACIA_TALK}_1():
    """State 0"""
    while True:
        """State 1"""
        if (IsPlayerTalkingToMe() == 1 and {near} and GetOneLineHelpStatus()
              and {has_any} and not CheckSelfDeath()):
            """State 2"""
            DisplayOneLineHelp(-1)
            if {has_stone}:
                """State 10"""
{stone}
            else:
                """State 20"""
{shard}
        elif (not GetOneLineHelpStatus() and HasDisableTalkPeriodElapsed() and not IsTalkingToSomeoneElse() and
              not CheckSelfDeath() and not IsCharacterDisabled() and not IsClientPlayer() and {near}
              and {has_any}):
            """State 6"""
            # action:10010200:"Talk"
            DisplayOneLineHelp(10010200)
            continue
        elif (GetOneLineHelpStatus() and (IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled()
              or IsClientPlayer() or GetRelativeAngleBetweenPlayerAndSelf() > 90 or GetDistanceToPlayer() > 6
              or not {has_any})):
            """State 7"""
            DisplayOneLineHelp(-1)
            continue
        """State 8"""
        Label('L1')
        ClearTalkProgressData()
        """State 9"""
        ForceEndTalk(0)
'''
