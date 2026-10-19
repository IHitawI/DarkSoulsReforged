"""Firelink hub, mini-quest "Yulia": the Undead Merchant (male) is sure every katana is his Yulia.

Capra Demon also drops the Iaito; the Blighttown corpse that held the Iaito now holds an Uchigatana.
After Capra is dead the merchant gets a "Show a katana" option (Burg and Firelink dialogs):
each katana gets its own scene ("not Yulia"), and once both were shown he finds her himself.
The player keeps both katanas.
"""
from load import *
from emevd import Emevd, build as build_emevd
from hub_npc import _ins, LAUGH

IAITO, UCHIGATANA = 502000, 500000
CAPRA = 1010750
CAPRA_EVENT = 11010902          # boss event in m10_01; also "Capra defeated" flag
CAPRA_LOT = 2515                # new lot: Iaito (2516 is free, so no lot chaining)
CAPRA_LOT_FLAG = 11027902
IAITO_CORPSE_LOT = 1400340      # Blighttown corpse, vanilla Iaito -> Uchigatana

IAITO_FLAG = 11027903           # Iaito shown
UCHI_FLAG = 11027904            # Uchigatana shown
FOUND_FLAG = 11027905           # he found Yulia himself
OPTION_TEXT = 15009001
IAITO_TALK, UCHI_TALK, NOTHING_TALK, FOUND_TALK, AFTER_TALK = 33009520, 33009530, 33009540, 33009550, 33009560

TEXT = {}   # same format as hub_npc.TEXT

# (voice id, ru, en); ru=None -> keep that vanilla line's text in every language
SCENES = {
    IAITO_TALK: [
        (33000500, 'Это ещё что такое?', 'What have we here?'),
        (33000900, 'Катана? Хороша, ничего не скажешь...', 'A katana? Lovely, I grant you...'),
        (33001000, 'Но это не Юлия. Даже не надейся.', "But that's not Yulia. Don't you even hope."),
        (LAUGH, None, None),
    ],
    UCHI_TALK: [
        (33000220, None, None),                                          # "Tsk!"
        (33000241, 'Опять не то. И это не Юлия.', "Wrong again. That's not Yulia either."),
        (33000902, None, None),   # "You'd never leave my side, now would you, Yulia?"
        (LAUGH, None, None),
    ],
    NOTHING_TALK: [
        (33001300, 'Э? И что ты мне показываешь?', 'Eh? What are you showing me?'),
        (33001301, 'Принеси катану, тогда и поговорим.', 'Bring me a katana, then we talk.'),
    ],
    FOUND_TALK: [
        (33000801, None, None),   # "Little Yulia..."
        (33000702, None, None),   # "Yulia! Yulia!"
        (33000900, 'А, вот же она! Всё это время была при мне!', 'Ah, here she is! She was with me all along!'),
        (33000901, None, None),   # "Her name is Yulia. She's plumb in love with me."
        (LAUGH, None, None),
    ],
    AFTER_TALK: [   # after he found her
        (33001001, None, None),   # "I'm all that she needs."
        (33001003, None, None),   # "Be kind, Yulia, be kind!"
        (LAUGH, None, None),
    ],
}
KATANA_IDS = {}   # base id -> every upgrade / infusion id (filled in apply)


def apply():
    tp, tl, _ = P['TalkParam']
    for base, lines in SCENES.items():
        assert base + len(lines) not in tp  # a gap ends the sequence
        for k, (voice, ru, en) in enumerate(lines):
            row = tp.add(base + k, tp[voice], f'[FirelinkHub] Yulia {base + k}'.encode())
            tl.set(row, 'msgId', base + k)
            tl.set(row, 'voiceId', tl.get(tp[voice], 'voiceId'))
            TEXT[('talk', base + k)] = {'ru': ru, 'en': en, 'copy': voice if ru is None else None}
    TEXT[('event', OPTION_TEXT)] = {'ru': 'Показать катану', 'en': 'Show a katana', 'copy': None}

    lp, ll, _ = P['ItemLotParam']
    assert CAPRA_LOT not in lp
    r = lp.add(CAPRA_LOT, lp[2510], b'[Capra Demon] Iaito (FirelinkHub)')
    ll.set(r, 'lotItemId01', IAITO)
    ll.set(r, 'lotItemCategory01', 0)          # weapon
    ll.set(r, 'getItemFlagId', CAPRA_LOT_FLAG)
    assert ll.get(lp[IAITO_CORPSE_LOT], 'lotItemId01') == IAITO
    ll.set(lp[IAITO_CORPSE_LOT], 'lotItemId01', UCHIGATANA)

    wp = P['EquipParamWeapon'][0]
    for base in (IAITO, UCHIGATANA):
        KATANA_IDS[base] = sorted(i for i, *_ in wp.rows if base <= i < base + 1000)


def patch_capra_event(data, edf):
    """m10_01: award the Iaito lot right after Capra's defeat."""
    ev = Emevd(data)
    e = next(e for e in ev.events if e['id'] == CAPRA_EVENT)
    assert not e['params']
    at = next(k for k, (b, i, _) in enumerate(e['ins']) if (b, i) == (2003, 12)) + 1   # after "boss defeated"
    e['ins'].insert(at, _ins(edf, 2003, 36, CAPRA_LOT))   # 36: also to the co-op partner
    return build_emevd(ev)


# ---------------- dialog (ESDLang text) ----------------
def _has(base):
    return '(' + ' or '.join(f'DoesPlayerHaveItem(ItemType.Weapon, {i})' for i in KATANA_IDS[base]) + ')'


def _scene(ind, talk, flag):
    done = f'{ind}        SetEventFlag({flag}, FlagState.On)\n' if flag else ''
    return (f'{ind}    TalkToPlayer({talk}, -1, -1)\n'
            f'{ind}    if IsAttackedBySomeone() or CheckSelfDeath():\n'
            f'{ind}        Goto(\'L0\')\n'
            f'{ind}    elif HasTalkEnded():\n'
            f'{done}'
            f'{ind}        continue\n'
            f'{ind}    elif (IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled() or IsClientPlayer()\n'
            f'{ind}          or GetRelativeAngleBetweenPlayerAndSelf() > 120 or GetDistanceToPlayer() > 5):\n'
            f'{ind}        Goto(\'L2\')\n')


def patch_esd(src):
    """Adds the "Show a katana" entry (slot 5, available once Capra is dead) to the merchant menu."""
    from hub_npc_esd import replace_once
    ind = ' ' * 24
    src = replace_once(src, f'{ind}AddTalkListData(4, 15000005, -1)\n',
                       f'{ind}# action:{OPTION_TEXT}:"Show a katana"\n'
                       f'{ind}AddTalkListData(5, {OPTION_TEXT}, {CAPRA_EVENT})\n'
                       f'{ind}AddTalkListData(4, 15000005, -1)\n')
    i2 = ind + '    '
    branch = (f'{ind}elif GetTalkListEntryResult() == 5:\n'
              f'{ind}    # FirelinkHub: Yulia quest\n'
              f'{i2}if {_has(IAITO)} and not GetEventFlag({IAITO_FLAG}):\n' + _scene(i2, IAITO_TALK, IAITO_FLAG) +
              f'{i2}elif {_has(UCHIGATANA)} and not GetEventFlag({UCHI_FLAG}):\n' + _scene(i2, UCHI_TALK, UCHI_FLAG) +
              f'{i2}elif GetEventFlag({IAITO_FLAG}) and GetEventFlag({UCHI_FLAG}) and not GetEventFlag({FOUND_FLAG}):\n'
              + _scene(i2, FOUND_TALK, FOUND_FLAG) +
              f'{i2}elif GetEventFlag({FOUND_FLAG}):\n' + _scene(i2, AFTER_TALK, None) +
              f'{i2}else:\n' + _scene(i2, NOTHING_TALK, None))
    return replace_once(src, f'{ind}elif GetTalkListEntryResult() == 4:\n',
                        branch + f'{ind}elif GetTalkListEntryResult() == 4:\n')
