"""Travel between ALL bonfires, not only the 21 of the vanilla warp list (that list is in the exe).

Bonfire menu (every bonfire dialog): "Travel" -> zone -> bonfire. The entry appears with the
Lordvessel (flag 710, same as vanilla "Warp"); a bonfire is listed once it is lit (its own flag).
Choosing one sets a request flag and the player stands up; the DLL (dll/firelinkhub.c, travel()) sees
the flag, clears it and calls the game's own bonfire warp to that bonfire's spawn point (bonfire entity
+ 1000). A map event warp (2003[14]) was used first: across maps it lost the spawn point and dropped
the player out of the world.
Bonfire list: every "register bonfire" (2009[3]) in the vanilla map events.
"""
import os
import struct
from souls import dcx_read
from emevd import Emevd, decode_args, build as build_emevd

LORDVESSEL = 710
EVENT_BASE = 11027800        # 11027800..898: events of the first (map event) warp, no longer built
REQUEST_BASE = 11028200      # request flag per bonfire, 11028200..298. Was 11027850.. (ran into the Yulia quest
                             # flags 11027903/904), then 11027200.. (the game's shop sold-out flags: Griggs' Fall
                             # Control is 11027200 - buying it would have warped you). 11028xxx: the game uses none.
UNLOCK_REQUEST = 11028299    # debug "unlock all bonfires": set here, the flags themselves are set by UNLOCK_EVENT
UNLOCK_EVENT = 11027899      # after the bonfire menu has closed (setting them from the menu locked it up)
# Leaving the bonfire before an event warp: close the menu AND stand up, like "Leave" does. L12 is the exit
# after the vanilla warp menu, where the engine moves the player itself; used for an event warp it left the
# player sitting with no menu - stuck at the bonfire.
STAND_UP = ['ForceEndTalk(0)', 'ClearTalkProgressData()', 'CloseShopMessage()', 'EndBonfireKindleAnimLoop()', "Goto('L1')"]
FLAG_SPACE = 99              # bonfires that fit: requests 11028200..298
TEXT_BASE = 15009200         # Event_text ids: menu entry, zones, bonfires
MENU_SLOT = 14

ZONES = {   # map -> (ru, en); the order is the menu order
    'm10_02_00_00': ('Храм Огня', 'Firelink Shrine'),
    'm18_01_00_00': ('Северное Прибежище Нежити', 'Northern Undead Asylum'),
    'm10_01_00_00': ('Город и Уезд Нежити', 'Undead Burg and Parish'),
    'm10_00_00_00': ('Глубины', 'Depths'),
    'm14_00_00_00': ('Чумной Город', 'Blighttown'),
    'm15_00_00_00': ('Крепость Сена', "Sen's Fortress"),
    'm15_01_00_00': ('Анор-Лондо', 'Anor Londo'),
    'm11_00_00_00': ('Нарисованный Мир Ариамис', 'Painted World of Ariamis'),
    'm12_00_00_00': ('Сад Тёмных Корней', 'Darkroot Garden'),
    'm12_01_00_00': ('Озеро Тёмных Корней и Олачиль', 'Darkroot Basin and Oolacile'),
    'm13_00_00_00': ('Катакомбы', 'The Catacombs'),
    'm13_01_00_00': ('Склеп Великанов', 'Tomb of the Giants'),
    'm13_02_00_00': ('Полость и Озеро Золы', 'The Great Hollow and Ash Lake'),
    'm14_01_00_00': ('Руины Демонов и Изалит', 'Demon Ruins and Lost Izalith'),
    'm16_00_00_00': ('Руины Нового Лондо', 'New Londo Ruins'),
    'm17_00_00_00': ('Архивы Герцога', "The Duke's Archives"),
    'm18_00_00_00': ('Горнило Первого Пламени', 'Kiln of the First Flame'),
}


def bonfires(game, edf):
    """[(map, lit flag, bonfire entity)] in ZONES order, one per bonfire."""
    _, args = edf.instr[(2009, 3)]
    found = {}
    for f in sorted(os.listdir(f'{game}/event')):
        mp = f.split('.')[0]
        if mp not in ZONES or not f.endswith('.emevd.dcx'):
            continue
        _, d = dcx_read(f'{game}/event/{f}')
        for ev in Emevd(d).events:
            for b, i, blob in ev['ins']:
                if (b, i) == (2009, 3):
                    flag, ent = decode_args(blob, [t for _, t in args])[:2]
                    found.setdefault((mp, flag), ent)
    out = []
    for mp in ZONES:
        out += sorted((m, fl, ent) for (m, fl), ent in found.items() if m == mp)
    return out


def texts(bfs):
    """Event_text entries: {id: (ru, en)} and the ids used by the menu."""
    t = {TEXT_BASE: ('Путешествие', 'Travel')}
    zone_id, bonfire_id = {}, []
    nxt = TEXT_BASE + 1
    for mp, (ru, en) in ZONES.items():
        zone_id[mp] = nxt
        t[nxt] = (ru, en)
        nxt += 1
    count = {}
    for mp, _, _ in bfs:
        n = sum(1 for m, _, _ in bfs if m == mp)
        count[mp] = count.get(mp, 0) + 1
        ru, en = ZONES[mp]
        t[nxt] = (ru, en) if n == 1 else (f'{ru} — костёр {count[mp]}', f'{en} - bonfire {count[mp]}')
        bonfire_id.append(nxt)
        nxt += 1
    t[nxt] = ('Назад', 'Back')
    return t, zone_id, bonfire_id, nxt


def patch_bonfire(src, bfs):
    """Bonfire dialog (t100200 text): adds the Travel entry and its zone / bonfire submenus."""
    _, zone_id, bonfire_id, back_id = texts(bfs)
    i20, i24 = ' ' * 20, ' ' * 24
    anchor_add = f'{i20}AddTalkListData(11, 15000270, 11810000)\n'
    assert src.count(anchor_add) == 1
    src = src.replace(anchor_add, anchor_add + f'{i20}# action:{TEXT_BASE}:"Travel"\n'
                                                f'{i20}AddTalkListData({MENU_SLOT}, {TEXT_BASE}, {LORDVESSEL})\n')
    leave = ('(CompareBonfireState(0) or IsPlayerDead() or HasPlayerBeenAttacked() or IsTalkingToSomeoneElse() '
             'or GetDistanceToPlayer() > 8)')
    # every submenu closes the list it came from first, or the new one is drawn over the old one
    L = [f'{i20}elif GetTalkListEntryResult() == {MENU_SLOT}:', f'{i24}# FirelinkHub: travel to any lit bonfire',
         f'{i24}CloseShopMessage()', f'{i24}while True:', f'{i24}    ClearTalkListData()', f'{i24}    ShowShopMessage(TalkOptionsType.Old, False, False)']
    zones = list(ZONES)
    for z, mp in enumerate(zones, 1):
        L += [f'{i24}    AddTalkListData({z}, {zone_id[mp]}, -1)']
    L += [f'{i24}    AddTalkListData(99, {back_id}, -1)',
          f'{i24}    if {leave}:', f"{i24}        Goto('L1')",
          f'{i24}    elif GetTalkListEntryResult() == 0 or GetTalkListEntryResult() == 99:', f'{i24}        break']
    for z, mp in enumerate(zones, 1):
        L += [f'{i24}    elif GetTalkListEntryResult() == {z}:', f'{i24}        CloseShopMessage()', f'{i24}        while True:',
              f'{i24}            ClearTalkListData()', f'{i24}            ShowShopMessage(TalkOptionsType.Old, False, False)']
        mine = [(k, fl) for k, (m, fl, _) in enumerate(bfs) if m == mp]
        for slot, (k, fl) in enumerate(mine, 1):
            L += [f'{i24}            AddTalkListData({slot}, {bonfire_id[k]}, {fl})']
        L += [f'{i24}            AddTalkListData(99, {back_id}, -1)',
              f'{i24}            if {leave}:', f"{i24}                Goto('L1')",
              f'{i24}            elif GetTalkListEntryResult() == 0 or GetTalkListEntryResult() == 99:',
              f'{i24}                break']
        for slot, (k, fl) in enumerate(mine, 1):
            L += [f'{i24}            elif GetTalkListEntryResult() == {slot}:',
                  f'{i24}                SetEventFlag({REQUEST_BASE + k}, FlagState.On)',
                  *[f'{i24}                {l}' for l in STAND_UP]]
    anchor_branch = f'\n{i20}elif GetTalkListEntryResult() == 1:\n'   # line start: nested menus have deeper ones
    assert src.count(anchor_branch) == 1
    return src.replace(anchor_branch, '\n' + '\n'.join(L) + anchor_branch)


def patch_common(data, edf, bfs):
    """common.emevd: the debug "unlock all bonfires" event; started before event 0 bails out in multiplayer."""
    def ins(bank, iid, *vals):
        from emevd import encode_args
        _, args = edf.instr[(bank, iid)]
        return (bank, iid, encode_args(vals, [t for _, t in args]))
    assert len(bfs) <= FLAG_SPACE, len(bfs)
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    starts = []
    ev.events.append({'id': UNLOCK_EVENT, 'rest': 0, 'params': [], 'ins': [
        ins(3, 0, 0, 1, 0, UNLOCK_REQUEST),
        ins(1001, 0, 1.0)]                                              # the bonfire menu is closed by now
        + [ins(2003, 2, fl, 1) for _, fl, _ in bfs] + [ins(2003, 2, LORDVESSEL, 1)]
        + [ins(2003, 2, UNLOCK_REQUEST, 0), ins(1000, 4, 1)]})
    starts.append(ins(2000, 0, 0, UNLOCK_EVENT, 0))
    e0['ins'][0:0] = starts
    return build_emevd(ev)
