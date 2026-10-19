"""Travel between ALL bonfires, not only the 21 of the vanilla warp list (that list is in the exe).

Bonfire menu (every bonfire dialog): "Travel" -> zone -> bonfire. The entry appears with the
Lordvessel (flag 710, same as vanilla "Warp"); a bonfire is listed once it is lit (its own flag).
Choosing one sets a request flag; an event in common.emevd (runs on every map) clears it and
moves the player to that map, onto the bonfire's respawn point (= bonfire entity + 1000, as the
vanilla events use it).
Bonfire list: every "register bonfire" (2009[3]) in the vanilla map events.
"""
import os
import struct
from souls import dcx_read
from emevd import Emevd, decode_args, build as build_emevd

LORDVESSEL = 710
EVENT_BASE = 11027800        # one event per bonfire
REQUEST_BASE = 11027200      # request flag per bonfire, 11027200..298 (was 11027850..: with the 11 restored
                             # bonfires it ran into the Yulia quest flags 11027903/904 - her quest warped you)
UNLOCK_REQUEST = 11027299    # debug "unlock all bonfires": set here, the flags themselves are set by UNLOCK_EVENT
UNLOCK_EVENT = 11027899      # after the bonfire menu has closed (setting them from the menu locked it up)
FLAG_SPACE = 99              # bonfires that fit: events 11027800.., requests 11027200..
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
    L = [f'{i20}elif GetTalkListEntryResult() == {MENU_SLOT}:', f'{i24}# FirelinkHub: travel to any lit bonfire',
         f'{i24}while True:', f'{i24}    ClearTalkListData()', f'{i24}    ShowShopMessage(TalkOptionsType.Old, False, False)']
    zones = list(ZONES)
    for z, mp in enumerate(zones, 1):
        L += [f'{i24}    AddTalkListData({z}, {zone_id[mp]}, -1)']
    L += [f'{i24}    AddTalkListData(99, {back_id}, -1)',
          f'{i24}    if {leave}:', f"{i24}        Goto('L1')",
          f'{i24}    elif GetTalkListEntryResult() == 0 or GetTalkListEntryResult() == 99:', f'{i24}        break']
    for z, mp in enumerate(zones, 1):
        L += [f'{i24}    elif GetTalkListEntryResult() == {z}:', f'{i24}        while True:',
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
                  f'{i24}                ForceEndTalk(0)', f'{i24}                ClearTalkProgressData()',
                  f'{i24}                CloseShopMessage()', f"{i24}                Goto('L12')"]
    anchor_branch = f'\n{i20}elif GetTalkListEntryResult() == 1:\n'   # line start: nested menus have deeper ones
    assert src.count(anchor_branch) == 1
    return src.replace(anchor_branch, '\n' + '\n'.join(L) + anchor_branch)


def patch_common(data, edf, bfs):
    """common.emevd: one waiting event per bonfire; started before event 0 bails out in multiplayer."""
    def ins(bank, iid, *vals):
        from emevd import encode_args
        _, args = edf.instr[(bank, iid)]
        return (bank, iid, encode_args(vals, [t for _, t in args]))
    assert len(bfs) <= FLAG_SPACE, len(bfs)
    ev = Emevd(data)
    e0 = next(e for e in ev.events if e['id'] == 0)
    starts = []
    for k, (mp, _, ent) in enumerate(bfs):
        area, block = int(mp[1:3]), int(mp[4:6])
        req = REQUEST_BASE + k
        ev.events.append({'id': EVENT_BASE + k, 'rest': 0, 'params': [], 'ins': [
            ins(3, 0, 0, 1, 0, req),                    # wait for the request
            ins(2003, 2, req, 0),
            ins(2003, 14, area, block, ent + 1000),     # to that map, onto the bonfire's spawn point
            ins(1000, 4, 1)]})                         # and wait again
        starts.append(ins(2000, 0, 0, EVENT_BASE + k, 0))
    ev.events.append({'id': UNLOCK_EVENT, 'rest': 0, 'params': [], 'ins': [
        ins(3, 0, 0, 1, 0, UNLOCK_REQUEST),
        ins(1001, 0, 1.0)]                                              # the bonfire menu is closed by now
        + [ins(2003, 2, fl, 1) for _, fl, _ in bfs] + [ins(2003, 2, LORDVESSEL, 1)]
        + [ins(2003, 2, UNLOCK_REQUEST, 0), ins(1000, 4, 1)]})
    starts.append(ins(2000, 0, 0, UNLOCK_EVENT, 0))
    e0['ins'][0:0] = starts
    return build_emevd(ev)
