"""ESD edits for the Undead Merchant (male) relocation. Works on ESDLang .py text."""
import re

MOVED_FLAG = 11027900      # merchant agreed to move to Firelink
GREETED_FLAG = 11027901    # first greeting in Firelink done
BELL1_FLAG = 11010700      # first Bell of Awakening rung (Undead Parish)
MOVE_OPTION_TEXT = 15009000  # Event_text: menu entry
MOVE_TALK = 33009500       # TalkParam: lines 33009500.. (Burg, agreeing to move)
GREET_TALK = 33009510      # TalkParam: lines 33009510.. (Firelink, first greeting)

LEAVE_CHECK = ('(IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled() or IsClientPlayer()\n'
               '{ind}      or GetRelativeAngleBetweenPlayerAndSelf() > 120 or GetDistanceToPlayer() > 5)')


def replace_once(src, old, new):
    assert src.count(old) == 1, f'expected exactly one match for: {old[:60]!r} (found {src.count(old)})'
    return src.replace(old, new)


def burg(src):
    """t101623 in Undead Burg: add the 'move to Firelink' option after the first bell."""
    ind = ' ' * 24
    src = replace_once(src,
        f'{ind}AddTalkListData(4, 15000005, -1)\n',
        # vanilla way: the 3rd argument is the event flag that makes the entry available
        # (an if-branch here splits the menu state and the entry can't be selected)
        f'{ind}# action:{MOVE_OPTION_TEXT}:"Move to Firelink Shrine"\n'
        f'{ind}AddTalkListData(2, {MOVE_OPTION_TEXT}, {BELL1_FLAG})\n'
        f'{ind}AddTalkListData(4, 15000005, -1)\n')
    branch = (
        f'{ind}elif GetTalkListEntryResult() == 2:\n'
        f'{ind}    # FirelinkHub: agrees to move\n'
        f'{ind}    TalkToPlayer({MOVE_TALK}, -1, -1)\n'
        f'{ind}    if IsAttackedBySomeone() or CheckSelfDeath():\n'
        f'{ind}        Goto(\'L0\')\n'
        f'{ind}    elif HasTalkEnded():\n'
        f'{ind}        SetEventFlag({MOVED_FLAG}, FlagState.On)\n'
        f'{ind}        ForceEndTalk(0)\n'
        f'{ind}        Continue(\'mainloop\')\n'
        f'{ind}    elif {LEAVE_CHECK.format(ind=ind)}:\n'
        f'{ind}        Goto(\'L2\')\n')
    src = replace_once(src, f'{ind}elif GetTalkListEntryResult() == 4:\n', branch + f'{ind}elif GetTalkListEntryResult() == 4:\n')
    return src


def firelink(src):
    """t102690 in Firelink: the same merchant, plus a one-time greeting at the new place."""
    src = src.replace('t101623', 't102690')
    ind = ' ' * 8
    anchor = (f'{ind}elif (not GetEventFlag(11016100) and IsPlayerTalkingToMe() == 1 and GetRelativeAngleBetweenPlayerAndSelf()\n'
              f'{ind}      <= 45 and GetDistanceToPlayer() <= 2 and GetOneLineHelpStatus() and GetEventFlag(11400200)')
    greet = (
        f'{ind}elif (not GetEventFlag({GREETED_FLAG}) and IsPlayerTalkingToMe() == 1 and GetRelativeAngleBetweenPlayerAndSelf()\n'
        f'{ind}      <= 45 and GetDistanceToPlayer() <= 2 and GetOneLineHelpStatus()):\n'
        f'{ind}    # FirelinkHub: first greeting in Firelink\n'
        f'{ind}    TalkToPlayer({GREET_TALK}, -1, -1)\n'
        f'{ind}    DisplayOneLineHelp(-1)\n'
        f'{ind}    if IsAttackedBySomeone() or CheckSelfDeath():\n'
        f'{ind}        Goto(\'L0\')\n'
        f'{ind}    elif HasTalkEnded():\n'
        f'{ind}        SetEventFlag({GREETED_FLAG}, FlagState.On)\n'
        f'{ind}        SetEventFlag(71010070, FlagState.On)\n'
        f'{ind}        SetEventFlag(11016100, FlagState.On)\n'
        f'{ind}        Goto(\'L6\')\n'
        f'{ind}    elif (IsTalkingToSomeoneElse() or CheckSelfDeath() or IsCharacterDisabled() or IsClientPlayer() or\n'
        f'{ind}          GetRelativeAngleBetweenPlayerAndSelf() > 120 or GetDistanceToPlayer() > 5):\n'
        f'{ind}        Goto(\'L2\')\n')
    assert src.count(anchor) == 1
    return src.replace(anchor, greet + anchor)
