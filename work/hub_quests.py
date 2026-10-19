"""Hub quests and advice: the Crestfallen Warrior by the Firelink bonfire (t102627) gets a menu.

Talking to him opens it:
  Talk     - his own story lines (the vanilla dialog answers the next press, once; then the menu is back);
  Advice   - one tip about the mod per ask, in turn (estus, champions, phases, respec, travel, ...);
  Bounties - he names one champion (hub_champions) at a time, in story order; once it is dead (its event flag =
             "killed") asking again pays the reward and names the next one.
Domhnall shows up too late in the story for this, so it is the warrior, who sits there from the start.
"""
import hub_champions

NL = chr(10)
TEXT_BASE = 15009400          # Event_text: bounties (menu entry, task / paid per bounty, "no more")
ADVICE_BASE = 15009440        # Event_text: menu entry, the tips, "that's all"
REWARD_FLAG = 11027100        # 11027100.. "bounty k paid"
TIP_FLAG = 11027120           # 11027120.. "tip k told"
PASS_FLAG = 11027119          # "Talk" chosen: let his own dialog answer the next press
USED_FLAG = 11027118          # ... and that press came: once the talk is over, PASS goes off
ZONES_RU = {'m10_01_00_00': 'Уезд нежити, в нефе церкви', 'm10_00_00_00': 'Глубины',
            'm14_00_00_00': 'Чумной город', 'm12_00_00_00': 'Сад Тёмных корней',
            'm15_00_00_00': 'Крепость Сена', 'm13_00_00_00': 'Катакомбы',
            'm14_01_00_00': 'Руины демонов', 'm17_00_00_00': 'Архивы Герцога'}
ZONES_EN = {'m10_01_00_00': 'the Undead Parish church', 'm10_00_00_00': 'the Depths', 'm14_00_00_00': 'Blighttown',
            'm12_00_00_00': 'Darkroot Garden', 'm15_00_00_00': "Sen's Fortress", 'm13_00_00_00': 'the Catacombs',
            'm14_01_00_00': 'the Demon Ruins', 'm17_00_00_00': "the Duke's Archives"}
BOUNTIES = [  # champion index (hub_champions.CHAMPIONS), reward [(goods, count)]
    (0, [(600, 3), (1010, 2)]),
    (1, [(601, 2), (1010, 3)]),
    (3, [(1030, 2), (500, 2)]),
    (2, [(1020, 2), (601, 3)]),
    (4, [(1030, 3), (501, 1)]),
    (5, [(1130, 2), (602, 1)]),
    (7, [(1120, 1), (1070, 1)]),
    (6, [(1070, 2), (1130, 3)]),
]
TIPS = [
    ('У костра наполняются всего три фляги. Осколки эстуса' + NL + 'с сильных боссов возжигай у костра или отдай' + NL +
     'Хранительнице — будет на одну флягу больше.',
     'A bonfire fills only three charges. Kindle the Estus' + NL + 'Shards of mighty bosses at a bonfire, or give them' + NL +
     'to the Fire Keeper: one more charge each.'),
    ('По землям бродят чемпионы — сильные враги из чужих' + NL + 'краёв. Увидишь полосу с именем — готовься.' + NL +
     'За них хорошо платят: спроси меня о поручениях.',
     'Champions roam these lands, strong foes from far away.' + NL + 'See a bar with a name, get ready. They pay well for' + NL +
     'them: ask me about bounties.'),
    ('Тёмные духи подстерегают путников. С них падают' + NL + 'сувениры возмездия — Клинкам Тёмной Луны такие нужны.',
     'Dark spirits lie in wait for travellers. They drop' + NL + 'Souvenirs of Reprisal - the Darkmoon Blades want those.'),
    ('Боссы тут так просто не сдаются: на половине сил' + NL + 'вспыхивают и встают снова. Зато во второй раз' + NL +
     'их легче ранить.',
     "Bosses here don't give up easily: at half strength" + NL + 'they flare up and rise again. But the second time' + NL +
     'they are easier to wound.'),
    ('Разонравился свой путь? Найди Камень перерождения' + NL + 'и отдай Хранительнице. Она вернёт тебя к началу,' + NL +
     'а души за уровни - тебе.',
     'Tired of your path? Find a Rebirth Stone and give it' + NL + 'to the Fire Keeper. She returns you to your start,' + NL +
     'and the souls you spent - to you.'),
    ('Добудешь Сосуд Повелителя — у любого костра сможешь' + NL + 'переноситься к любому зажжённому костру.',
     'Get the Lordvessel and from any bonfire you can travel' + NL + 'to any bonfire you have lit.'),
    ('Торговцы и кузнецы, которых встретишь в пути,' + NL + 'со временем перебираются сюда. Храм оживёт.',
     'Merchants and smiths you meet on the road move' + NL + 'here in time. The Shrine will come alive.'),
    ('Торговка нежити продаёт янтарные травы:' + NL + 'они возвращают заряды чудесам и колдовству.',
     'The Undead merchant sells amber herbs: they give' + NL + 'your miracles and sorceries their casts back.'),
    ('Ковенантам нужны дары. Медаль Солнца дают за' + NL + 'каждого босса, чешую дракона - за чемпионов,' + NL +
     'глаза смерти чаще носят василиски.',
     'Covenants want offerings. Every boss gives a Sunlight' + NL + 'Medal, champions give Dragon Scales, Basilisks' + NL +
     'carry Eyes of Death more often.'),
    ('Говорят, в логове иного чудовища после победы' + NL + 'загорается костёр. А по пути бывают забытые костры.',
     'They say a bonfire kindles in some lairs once the beast' + NL + 'is dead. And there are forgotten bonfires on the way.'),
    ('Бочки да ящики посреди дороги — к засаде.' + NL + 'Там редко бывает один враг.',
     'Barrels and crates across the road mean an ambush.' + NL + 'There is rarely just one foe.'),
]
MENU_TEXT = {}


def texts():
    MENU_TEXT[('event', TEXT_BASE)] = {'ru': 'Поручения', 'en': 'Bounties', 'copy': None}
    for i, (k, _) in enumerate(BOUNTIES):
        mp, _, _, ru, en = hub_champions.CHAMPIONS[k][:5]
        MENU_TEXT[('event', TEXT_BASE + 1 + 2 * i)] = {
            'ru': f'Поручение: «{ru}».' + NL + f'Его видели: {ZONES_RU[mp]}.' + NL + 'Убей — и возвращайся за платой.',
            'en': f'Bounty: {en}.' + NL + f'Last seen in {ZONES_EN[mp]}.' + NL + 'Kill it, then come back for your pay.',
            'copy': None}
        MENU_TEXT[('event', TEXT_BASE + 2 + 2 * i)] = {
            'ru': f'«{ru}» мёртв. Вот твоя плата.', 'en': f'{en} is dead. Here is your pay.', 'copy': None}
    MENU_TEXT[('event', TEXT_BASE + 1 + 2 * len(BOUNTIES))] = {
        'ru': 'Поручений больше нет. Ты славно поработал.', 'en': 'No more bounties. Fine work.', 'copy': None}
    MENU_TEXT[('event', ADVICE_BASE)] = {'ru': 'Совет', 'en': 'Advice', 'copy': None}
    for i, (ru, en) in enumerate(TIPS):
        MENU_TEXT[('event', ADVICE_BASE + 1 + i)] = {'ru': ru, 'en': en, 'copy': None}
    MENU_TEXT[('event', ADVICE_BASE + 1 + len(TIPS))] = {
        'ru': 'Вот и всё, что я знаю. Спросишь ещё — начну сначала.',
        'en': "That's all I know. Ask again and I'll start over.", 'copy': None}


def _dialog(ind, text):
    return [f'{ind}OpenGenericDialog(DialogBoxType.CenterMiddleDimScreen1, {text}, DialogResult.Left,',
            f'{ind}                  DialogBoxStyle.OrnateNoOptions, 2)',
            f'{ind}if not IsGenericDialogOpen():',
            f'{ind}    continue']


def _bounties(ind):
    i2 = ind + '    '
    L, kw = [], 'if'
    for i, (k, reward) in enumerate(BOUNTIES):
        paid, killed = REWARD_FLAG + i, hub_champions.event_id(k)
        L.append(f'{ind}{kw} not GetEventFlag({paid}) and GetEventFlag({killed}):')
        kw = 'elif'
        L += [f'{i2}PlayerEquipmentQuantityChange(ItemType.Goods, {g}, {n})' for g, n in reward]
        L.append(f'{i2}SetEventFlag({paid}, FlagState.On)')
        L += _dialog(i2, TEXT_BASE + 2 + 2 * i)
        L.append(f'{ind}elif not GetEventFlag({paid}):')
        L += _dialog(i2, TEXT_BASE + 1 + 2 * i)
    L.append(f'{ind}else:')
    L += _dialog(i2, TEXT_BASE + 1 + 2 * len(BOUNTIES))
    return L


def _advice(ind):
    i2 = ind + '    '
    L, kw = [], 'if'
    for i in range(len(TIPS)):
        L.append(f'{ind}{kw} not GetEventFlag({TIP_FLAG + i}):')
        kw = 'elif'
        L.append(f'{i2}SetEventFlag({TIP_FLAG + i}, FlagState.On)')
        L += _dialog(i2, ADVICE_BASE + 1 + i)
    L.append(f'{ind}else:')
    L += [f'{i2}SetEventFlag({TIP_FLAG + i}, FlagState.Off)' for i in range(len(TIPS))]
    L += _dialog(i2, ADVICE_BASE + 1 + len(TIPS))
    return L


def crestfallen(src):
    """t102627: the menu branch, inserted before his vanilla talk (after the Pendant one)."""
    import hub_talks
    i8, i12, i16, i20 = ' ' * 8, ' ' * 12, ' ' * 16, ' ' * 20
    near = 'GetRelativeAngleBetweenPlayerAndSelf() <= 45 and GetDistanceToPlayer() <= 2'
    alive = f'not GetEventFlag({hub_talks.CRESTFALLEN_HOSTILE}) and not GetEventFlag({hub_talks.CRESTFALLEN_DEAD})'
    # "Talk" lets one press through to his own dialog: PASS on -> the press (talking) marks USED -> his
    # dialog -> the talk is over (not talking, USED) -> both off, the menu answers again. Walking away resets
    # too. (PASS alone reset only at 4 m, and he sits by the bonfire: his line kept repeating.)
    L = [f'{i8}elif GetEventFlag({PASS_FLAG}) and (GetDistanceToPlayer() > 4 or',
         f'{i8}      (GetEventFlag({USED_FLAG}) and IsPlayerTalkingToMe() == 0)):',
         f'{i12}# FirelinkHub: his own dialog is over: the menu answers again',
         f'{i12}SetEventFlag({PASS_FLAG}, FlagState.Off)',
         f'{i12}SetEventFlag({USED_FLAG}, FlagState.Off)',
         f'{i12}continue',
         f'{i8}elif GetEventFlag({PASS_FLAG}) and not GetEventFlag({USED_FLAG}) and IsPlayerTalkingToMe() == 1:',
         f'{i12}SetEventFlag({USED_FLAG}, FlagState.On)',
         f'{i12}continue',
         f'{i8}elif (IsPlayerTalkingToMe() == 1 and {near} and GetOneLineHelpStatus()',
         f'{i8}      and not GetEventFlag({PASS_FLAG}) and {alive}):',
         f'{i12}# FirelinkHub: the warrior\'s menu - talk, advice, bounties',
         f'{i12}DisplayOneLineHelp(-1)',
         f'{i12}while True:',
         f'{i16}ClearTalkListData()',
         f'{i16}# action:15000000:"Talk"',
         f'{i16}AddTalkListData(1, 15000000, -1)',
         f'{i16}# action:{ADVICE_BASE}:"Advice"',
         f'{i16}AddTalkListData(2, {ADVICE_BASE}, -1)',
         f'{i16}# action:{TEXT_BASE}:"Bounties"',
         f'{i16}AddTalkListData(3, {TEXT_BASE}, -1)',
         f'{i16}# action:15000005:"Leave"',
         f'{i16}AddTalkListData(4, 15000005, -1)',
         f'{i16}ShowShopMessage(TalkOptionsType.Old, False, False)',
         f'{i16}if IsAttackedBySomeone() or CheckSelfDeath() or {hub_talks.LEAVE}:',
         f'{i20}ForceEndTalk(0)',
         f'{i20}ClearTalkProgressData()',
         f'{i20}CloseShopMessage()',
         f'{i20}break',
         f'{i16}elif GetTalkListEntryResult() == 0 or GetTalkListEntryResult() == 4:',
         f'{i20}ForceEndTalk(0)',
         f'{i20}CloseShopMessage()',
         f'{i20}break',
         f'{i16}elif GetTalkListEntryResult() == 1:',
         f'{i20}SetEventFlag({PASS_FLAG}, FlagState.On)',
         f'{i20}ForceEndTalk(0)',
         f'{i20}CloseShopMessage()',
         f'{i20}break',
         f'{i16}elif GetTalkListEntryResult() == 2:']
    L += _advice(i20)
    L.append(f'{i16}elif GetTalkListEntryResult() == 3:')
    L += _bounties(i20)
    L.append(f'{i12}continue')
    return hub_talks._insert(src, NL.join(L) + NL)
