"""Firelink talk extras: greetings of the NPCs that moved in, and the Pendant for the Crestfallen Warrior.

Greetings: the first talk in Firelink plays a short voiced scene, then the usual dialog goes on.
Pendant: the starting gift that does nothing in vanilla. Give it to the Crestfallen Warrior and he
hands you a Rebirth Stone (hub_respec.py) - a free respec at the Fire Keeper.
Branches are inserted before the first "player talks to me" branch of each dialog.
"""
from load import *
import hub_respec

TEXT = {}   # menu.msgbnd: (kind, id) -> {'ru', 'en', 'copy'}

LEAVE = ('(IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled() or IsClientPlayer() or '
         'GetRelativeAngleBetweenPlayerAndSelf() > 120 or GetDistanceToPlayer() > 5)')
TALK_START = '        elif (IsPlayerTalkingToMe() == 1'

# key: (talk id of the Firelink dialog, greeted flag, first TalkParam id, lines (voice, ru, en))
GREETINGS = {
    'andre': (102692, 11027913, 33009610, [
        (29000100, None, None),                                   # "Well, hello again."
        (29000801, 'А у костра-то работается куда веселее.', 'Working by the bonfire is far more cheerful.'),
        (29000102, None, None),                                   # "Need anything forged?"
        (29000308, None, None)]),                                 # "Hah hah hah!"
    'female': (102694, 11027914, 33009620, [
        (34000140, None, None),                                   # "Oh, hello, dearie."
        (34000141, 'Перебралась поближе к костру, дорогуша.', 'I moved closer to the bonfire, dearie.'),
        (34000145, None, None)]),                                 # "Vee hee hee!"
    'sen': (102691, 11027915, 33009630, [
        (35000201, None, None),                                   # "Hm...Oh, yes, it's you."
        (35000102, 'Здесь хоть брёвна на голову не падают...', 'At least no logs fall on your head here...'),
        (35000223, None, None)]),                                 # "Anything you want? ...at a price!"
}

PENDANT = 376
PENDANT_FLAG = 11027916
PENDANT_TALK = 33009640
PENDANT_TEXT = 15009032          # Event_text: "Give the Pendant?"
CRESTFALLEN_TALK = 102627
CRESTFALLEN_HOSTILE, CRESTFALLEN_DEAD = 1461, 1462
PENDANT_LINES = [
    (37002900, 'Хе-хе, подвеска? Небось с самой родины...', 'Heh, a pendant? From home, I suppose...'),
    (37002901, 'Знаешь, за такое и я кое-что дам.', "You know, for that I'll give you something too."),
    (37000003, 'Отнеси этот камень Хранительнице. Начнёшь путь заново.',
               'Take this stone to the Fire Keeper. Start your path anew.'),
    (37000009, None, None),                                       # "Hah hah hah hah..."
]


def _lines(base, lines, label):
    tp, tl, _ = P['TalkParam']
    assert base + len(lines) not in tp       # a gap ends the sequence
    for k, (voice, ru, en) in enumerate(lines):
        row = tp.add(base + k, tp[voice], f'[FirelinkHub] {label} {base + k}'.encode())
        tl.set(row, 'msgId', base + k)
        tl.set(row, 'voiceId', tl.get(tp[voice], 'voiceId'))
        TEXT[('talk', base + k)] = {'ru': ru, 'en': en, 'copy': voice if ru is None else None}


def apply():
    for key, (_, _, base, lines) in GREETINGS.items():
        _lines(base, lines, f'greeting {key}')
    _lines(PENDANT_TALK, PENDANT_LINES, 'Pendant')
    TEXT[('event', PENDANT_TEXT)] = {'ru': 'Отдать подвеску?', 'en': 'Give the Pendant?', 'copy': None}


def _insert(src, branch):
    i = src.index(TALK_START)
    return src[:i] + branch + src[i:]


def greeting(src, key):
    _, flag, base, _ = GREETINGS[key]
    i8, i12 = ' ' * 8, ' ' * 12
    branch = (
        f'{i8}elif (IsPlayerTalkingToMe() == 1 and GetRelativeAngleBetweenPlayerAndSelf() <= 45 and '
        f'GetDistanceToPlayer() <= 3\n{i8}      and GetOneLineHelpStatus() and not GetEventFlag({flag})):\n'
        f'{i12}# FirelinkHub: first greeting in Firelink\n'
        f'{i12}DisplayOneLineHelp(-1)\n'
        f'{i12}TalkToPlayer({base}, -1, -1)\n'
        f'{i12}if IsAttackedBySomeone() or CheckSelfDeath():\n'
        f'{i12}    pass\n'
        f'{i12}elif HasTalkEnded():\n'
        f'{i12}    SetEventFlag({flag}, FlagState.On)\n'
        f'{i12}    continue\n'
        f'{i12}elif {LEAVE}:\n'
        f'{i12}    pass\n')
    return _insert(src, branch)


def pendant(src):
    """t102627 (Crestfallen Warrior): with the Pendant, a talk offers to give it to him."""
    i8, i12, i16, i20 = ' ' * 8, ' ' * 12, ' ' * 16, ' ' * 20
    stone = hub_respec.GOODS_ID
    branch = (
        f'{i8}elif (IsPlayerTalkingToMe() == 1 and GetRelativeAngleBetweenPlayerAndSelf() <= 45 and '
        f'GetDistanceToPlayer() <= 3\n{i8}      and GetOneLineHelpStatus() and DoesPlayerHaveItem(ItemType.Goods, {PENDANT})\n'
        f'{i8}      and not DoesPlayerHaveItem(ItemType.Goods, {stone}) and not GetEventFlag({PENDANT_FLAG})\n'
        f'{i8}      and not GetEventFlag({CRESTFALLEN_HOSTILE}) and not GetEventFlag({CRESTFALLEN_DEAD})):\n'
        f'{i12}# FirelinkHub: the Pendant for a Rebirth Stone\n'
        f'{i12}DisplayOneLineHelp(-1)\n'
        f'{i12}OpenGenericDialog(DialogBoxType.CenterBottom2, {PENDANT_TEXT}, DialogResult.Leave, DialogBoxStyle.Unk, 2)\n'
        f'{i12}if CheckSelfDeath() or IsAttackedBySomeone() or {LEAVE}:\n'
        f'{i16}ForceCloseGenericDialog()\n'
        f'{i12}elif ((GetGenericDialogButtonResult() == DialogResult.Cancel and not IsGenericDialogOpen()) or\n'
        f'{i12}      (GetGenericDialogButtonResult() == DialogResult.Right and not IsGenericDialogOpen())):\n'
        f'{i16}pass\n'
        f'{i12}elif GetGenericDialogButtonResult() == DialogResult.Left and not IsGenericDialogOpen():\n'
        f'{i16}PlayerEquipmentQuantityChange(ItemType.Goods, {PENDANT}, -1)\n'
        f'{i16}PlayerEquipmentQuantityChange(ItemType.Goods, {stone}, 1)   # the swap happens at once\n'
        f'{i16}SetEventFlag({PENDANT_FLAG}, FlagState.On)\n'
        f'{i16}TalkToPlayer({PENDANT_TALK}, -1, -1)\n'
        f'{i16}if IsAttackedBySomeone() or CheckSelfDeath():\n'
        f'{i20}pass\n'
        f'{i16}elif HasTalkEnded():\n'
        f'{i20}OpenItemAcquisitionMenu(ItemType.Goods, {stone}, 1)\n'
        f'{i20}continue\n'
        f'{i16}elif {LEAVE}:\n'
        f'{i20}pass\n')
    return _insert(src, branch)
