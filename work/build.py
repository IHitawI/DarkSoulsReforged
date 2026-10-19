"""Builds the FirelinkHub mod: GameParam, item/menu texts for every language, maps, events, dialogs."""
import sys, os, subprocess, shutil; sys.path.insert(0, ".")
from load import *
import allyheal, hub_items, useful, hub_npc, hub_npc_esd, hub_debug, hub_yulia, hub_npcs, hub_decor, hub_respec, hub_spells, hub_talks, hub_rolls
import talkpatch, texbank

DEBUG = '--release' not in sys.argv   # the [Reforged debug] bonfire menu (hub_debug.py); --release leaves it out
from emevd import Edf, Emevd, build as build_emevd

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS REMASTERED'
ESDTOOL = os.path.abspath(os.path.join('..', 'tools_dl', 'esdtool', 'esdtool-v0.5.1', 'esdtool.exe'))

import hub_fixes, hub_estus
MODULES = (allyheal, hub_items, useful, hub_fixes)
for mod in MODULES:
    mod.apply()
hub_npc.apply()
hub_yulia.apply()
hub_npcs.apply()
hub_respec.apply()
hub_spells.apply()
hub_spells.cleric_start()
hub_talks.apply()
hub_rolls.apply()
hub_estus.apply()
import hub_weapons
hub_weapons.apply()
import hub_covenants
hub_covenants.apply()
import hub_ai
print('AI think rows changed:', hub_ai.apply())
import hub_elites, hub_elite_tex
hub_elites.apply(GAME)
import hub_bosses
hub_bosses.apply(GAME)
import hub_travel
from emevd import Edf as _Edf
import hub_bonfires
hub_bonfires.prepare(GAME)
hub_champions_avoid = hub_bonfires.avoid_boxes()
TRAVEL = hub_travel.bonfires(GAME, _Edf(dcx_read(f'{GAME}/event/common.emedf.dcx')[1])) + hub_bonfires.travel_entries()
import hub_champions
hub_champions.AVOID += hub_champions_avoid
hub_champions.AVOID += hub_champions.arena_boxes(GAME, [f'm{a}_{b:02d}_00_00' for a in range(10, 19) for b in range(3)])
hub_champions.TRAVEL = TRAVEL
import hub_camps
hub_camps.TRAVEL = TRAVEL
import hub_world
hub_world.TRAVEL = TRAVEL
hub_champions.apply(GAME)
import hub_quests
hub_quests.texts()
if DEBUG:
    hub_debug.setup(TRAVEL)
    hub_debug.apply()
TRAVEL_TEXT = {('event', k): {'ru': ru, 'en': en, 'copy': None}
               for k, (ru, en) in hub_travel.texts(TRAVEL)[0].items()}

for pname in ('Magic', 'SpEffectParam', 'Bullet', 'EquipParamGoods', 'ShopLineupParam', 'TalkParam', 'ItemLotParam', 'AtkParam_Pc', 'EquipMtrlSetParam', 'SpEffectVfxParam', 'NpcParam', 'EquipParamWeapon', 'CharaInitParam', 'NpcThinkParam'):
    p, _, f = P[pname]
    f[3] = p.build()
os.makedirs('out/h', exist_ok=True)
for _d in ('MapStudio', 'MapStudioNew', 'event', 'script', 'chr', 'obj', 'menu'):   # no stale files from older builds
    shutil.rmtree(f'out/h/{_d}', ignore_errors=True)
dcx_write('out/h/GameParam.parambnd.dcx', H, G.build())

FMG_IDS = {'name': (10, 111), 'info': (20, 110), 'caption': (24, 100),
           'mname': (14, 118), 'minfo': (28,), 'mcaption': (29, 105),   # m*: the spell itself
           'rname': (13, 113), 'rinfo': (23, 112), 'rcaption': (27, 109),   # r*: rings
           'npcname': (18, 119)}                                            # boss bar names
for lang in sorted(os.listdir('orig/msg')):
    key = 'ru' if lang == 'RUSSIAN' else 'en'
    h, d = dcx_read(f'orig/msg/{lang}/item.msgbnd.dcx')
    bnd = Bnd3(d)
    for f in bnd.files:
        kind = next((k for k, ids in FMG_IDS.items() if f[1] in ids), None)
        if kind is None:
            continue
        m = Fmg(f[3])
        for mod in MODULES + (hub_respec, hub_spells, hub_rolls, hub_estus, hub_champions, hub_bosses):
            for (k, gid), t in getattr(mod, 'ITEM_TEXT' if mod is hub_respec else 'TEXT', {}).items():
                # new items get text in every language; rewritten vanilla texts only in RU/EN,
                # other languages keep their own translation
                if k == kind and (not m.entries.get(gid) or lang in ('RUSSIAN', 'ENGLISH')):
                    m.entries[gid] = t[key]
            for (k, gid), t in getattr(mod, 'APPEND', {}).items():
                if k == kind and m.entries.get(gid):
                    base = m.entries[gid].rstrip()
                    if kind == 'info' and not base.endswith(('.', '!', '。')):
                        base += '.'
                    m.entries[gid] = base + t[key]
        f[3] = m.build()
    dcx_write(f'out/h/msg_{lang}.dcx', h, bnd.build())

# --- menu texts: NPC lines (Conversation) and talk menu entries (Event_text)
MENU_IDS = {'talk': (1, 104), 'event': (30, 101)}
for lang in sorted(os.listdir('orig/msg')):
    key = 'ru' if lang == 'RUSSIAN' else 'en'
    h, d = dcx_read(f'orig/msg/{lang}/menu.msgbnd.dcx')
    bnd = Bnd3(d)
    for f in bnd.files:
        kind = next((k for k, ids in MENU_IDS.items() if f[1] in ids), None)
        if kind is None:
            continue
        m = Fmg(f[3])
        for (k, mid), t in list(hub_npc.TEXT.items()) + list(hub_yulia.TEXT.items()) + list(hub_npcs.TEXT.items()) + list(hub_respec.TEXT.items()) + list(hub_talks.TEXT.items()) + list(hub_estus.MENU_TEXT.items()) + list(hub_quests.MENU_TEXT.items()) + list(TRAVEL_TEXT.items()) + (list(hub_debug.TEXT.items()) if DEBUG else []):
            if k == kind:
                assert not m.entries.get(mid), (lang, mid)
                m.entries[mid] = m.entries[t['copy']] if t['copy'] else t[key]
        f[3] = m.build()
    dcx_write(f'out/h/menu_{lang}.dcx', h, bnd.build())

# --- maps (both copies the game ships), events
import place, icons, spell_icons
nav = place.load_nav(GAME)
for sub in ('MapStudio', 'MapStudioNew'):
    burg_msb = open(f'{GAME}/map/{sub}/m10_01_00_00.msb', 'rb').read()
    hub_npc.BURG_TYPE_DATA = hub_npc.burg_type_data(burg_msb)
    os.makedirs(f'out/h/{sub}', exist_ok=True)
    src = open(f'{GAME}/map/{sub}/m10_02_00_00.msb', 'rb').read()
    fl = hub_npc.patch_firelink_msb(src, burg_msb, nav)
    sources = {mp: open(f'{GAME}/map/{sub}/{mp}.msb', 'rb').read() for mp in ('m10_01_00_00', 'm15_00_00_00', 'm15_01_00_00')}
    fl = hub_npcs.patch_firelink_msb(fl, sources)
    fl = hub_decor.patch_firelink_msb(fl, GAME, sub)
    open(f'out/h/{sub}/m10_02_00_00.msb', 'wb').write(hub_respec.patch_msb(fl))
    vanilla = lambda mp: open(f'{GAME}/map/{sub}/{mp}.msb', 'rb').read()
    for mp in sorted(set(hub_elites.MAPS) | set(hub_champions.MSB_MAPS) | set(hub_camps.MAPS) | set(hub_world.MAPS)):   # elites, champions, remix, camps
        out, n = hub_elites.patch_msb(vanilla(mp), mp)
        out, c = hub_bonfires.patch_msb(out, mp)
        n += c
        if mp in hub_champions.MSB_MAPS:
            sources = {c[1][0]: vanilla(c[1][0]) for c in hub_champions.CHAMPIONS + hub_champions.REMIX}
            out, c = hub_champions.patch_msb(out, mp, sources)
            n += c
        if mp in hub_camps.MAPS:
            out, c = hub_camps.patch_msb(out, mp, GAME, {s: vanilla(s) for s, _ in hub_camps.SOURCE.values()})
            n += c
        if mp in hub_world.MAPS:
            out, c = hub_world.patch_msb(out, mp, GAME, {s: vanilla(s) for s, _ in hub_decor.SOURCE.values()})
            n += c
        if n:
            open(f'out/h/{sub}/{mp}.msb', 'wb').write(out)

# --- decor from other areas: pack the textures they need into their own objbnd
os.makedirs('out/h/obj', exist_ok=True)
_, tmpl_obj = dcx_read(f'{GAME}/obj/o0200.objbnd.dcx')
tpf_head = Bnd3(tmpl_obj).files[0][3][:16]
banks = [texbank.area_textures(GAME, a) for a in hub_decor.TEXTURE_AREAS + ('m10',)]
for oid in hub_decor.FOREIGN + hub_camps.EXTRA + hub_world.EXTRA_PACK:
    missing = texbank.pack_object(GAME, oid, banks, f'out/h/obj/{oid}.objbnd.dcx', tpf_head)
    assert not missing, (oid, missing)

# --- player animations: own cast animations (hub_casts.py) and rolls one tier up (hub_rolls.py)
import hub_casts
os.makedirs('out/h/chr', exist_ok=True)
# own cast slots (hub_casts) are not built: animations appended to a00.tae lose their events
h, d = dcx_read(f'{GAME}/chr/c0000.anibnd.dcx')
bnd = Bnd3(d)
tae_file = next(f for f in bnd.files if f[2].decode('shift_jis').endswith('a00.tae'))
tae_file[3] = hub_rolls.remap(tae_file[3])
dcx_write('out/h/chr/c0000.anibnd.dcx', h, bnd.build())
print('AI scripts copied:', hub_champions.patch_scripts(GAME, 'out/h/script'))
# the Giant Blacksmith's battle AI for his Firelink copy (if he is attacked there)
import luabnd
_h, _d = dcx_read(f'{GAME}/script/m10_02_00_00.luabnd.dcx')
_fl = Bnd3(_d)
if luabnd.copy_goal(_fl, Bnd3(dcx_read(f'{GAME}/script/m15_01_00_00.luabnd.dcx')[1]), hub_npcs.GIANT_GOAL):
    dcx_write('out/h/script/m10_02_00_00.luabnd.dcx', _h, _fl.build())
hub_rolls.swap_motions(f'{GAME}/chr/{hub_rolls.MOTIONS}', f'out/h/chr/{hub_rolls.MOTIONS}')

# hub_throws.py (allies hit an enemy during your riposte / backstab) is off: removing the victims' flag 67 did not
# let a co-op partner hurt them (the engine protects a throw victim on its own) and it broke the death moment -
# an enemy killed by a backstab stood up first and only then died.

# --- item icons (DS2 lifegems) into the Icon21 atlas
os.makedirs('out/h/menu', exist_ok=True)
ICON_SRC = os.path.join('..', 'tools_dl', 'ds2icons')
ALL_ICONS = {2159: f'{ICON_SRC}/Lifegem.png', 2160: f'{ICON_SRC}/Radiant_Lifegem.png',
             2161: f'{ICON_SRC}/Old_Radiant_Lifegem.png',
             2162: 'icons/herbs/amber.png', 2163: 'icons/herbs/lush.png', 2164: 'icons/herbs/ancient.png',
             hub_respec.ICON: f'{ICON_SRC}/Soul_Vessel.png', hub_estus.ICON: 'icons/estus_shard.png',
             **{hub_spells.ICON[k]: p for k, p in spell_icons.build(GAME).items()}}
icons.patch_atlas(f'{GAME}/menu/menu_3.tpf.dcx', 'out/h/menu/menu_3.tpf.dcx',
                  {i: p for i, p in ALL_ICONS.items() if i in icons.FREE_SLOTS})
# vanilla DSR leaves the Escape Death icon (3042, atlas Icon30) empty: draw it (escape_death_icon.py)
import escape_death_icon
icons.patch_texture_cell(f'{GAME}/menu/menu_0.tpf.dcx', 'out/h/menu/menu_0.tpf.dcx', 'Icon30',
                         escape_death_icon.build(), (986, 554, 1146, 734))
# icons past the 9 Icon21 placeholders: other unused sprites in other atlases (icons.EXTRA_SLOTS)
icons.patch_extra(GAME, 'out/h/menu', {i: p for i, p in ALL_ICONS.items() if i in icons.EXTRA_SLOTS})
_, edf_raw = dcx_read(f'{GAME}/event/common.emedf.dcx')
edf = Edf(edf_raw)
os.makedirs('out/h/event', exist_ok=True)
h, d = dcx_read(f'{GAME}/event/common.emevd.dcx')
dcx_write('out/h/event/common.emevd.dcx', h, hub_estus.patch_common(hub_travel.patch_common(d, edf, TRAVEL), edf))
BOSS_MAPS = ['m10_00_00_00', 'm10_01_00_00', 'm11_00_00_00', 'm12_00_00_00', 'm12_01_00_00', 'm13_00_00_00', 'm13_01_00_00',
             'm14_00_00_00', 'm14_01_00_00', 'm15_00_00_00', 'm15_01_00_00', 'm16_00_00_00', 'm17_00_00_00', 'm18_00_00_00',
             'm18_01_00_00']
MAP_EVENTS = {**{m: None for m in hub_estus.MAPS + hub_bosses.MAPS + hub_champions.MAPS + BOSS_MAPS}, 'm10_02_00_00': 'firelink', 'm10_01_00_00': 'burg'}
for m, which in MAP_EVENTS.items():
    h, d = dcx_read(f'{GAME}/event/{m}.emevd.dcx')
    if which:
        d = hub_npc.patch_emevd(d, edf, which)
    if which == 'burg':
        d = hub_yulia.patch_capra_event(d, edf)
        d = hub_fixes.patch_burg(d, edf)
    d = hub_npcs.patch_emevd(d, edf, m)
    if m in hub_estus.MAPS:
        d = hub_estus.patch_map(d, edf, m)
    if m in hub_bosses.MAPS:
        d = hub_bosses.patch_map(d, edf, m)
    if m in hub_champions.MAPS:
        d = hub_champions.patch_emevd(d, edf, m)
    d = hub_bonfires.patch_emevd(d, edf, m)
    if m in BOSS_MAPS:
        d, _n = hub_covenants.patch_map(d, edf, m)
        medals = globals().setdefault('MEDALS', {}); medals[m] = _n
    if m == 'm10_02_00_00':
        ev = Emevd(d)
        hub_decor.patch_emevd(ev, edf)
        d = build_emevd(ev)
    dcx_write(f'out/h/event/{m}.emevd.dcx', h, d)


# --- dialogs: decompile vanilla merchant ESD, patch, compile with ESDLang, repack with vanilla IDs
work = os.path.abspath('out/esdwork')
shutil.rmtree(work, ignore_errors=True)
os.makedirs(f'{work}/py'); os.makedirs(f'{work}/src'); os.makedirs(f'{work}/bnd')
def esdtool(*args):
    r = subprocess.run([ESDTOOL, '-ds1r', '-basedir', GAME, *args], cwd=os.path.dirname(ESDTOOL),
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, errors='replace')
    if r.returncode != 0 or 'ERROR' in r.stdout:
        sys.exit(r.stdout[-3000:] + r.stderr[-2000:])
esdtool('-i', f'{GAME}/script/talk/m10_01_00_00.talkesdbnd.dcx', '-f', 't101623', 't101619', '-writepy', f'{work}/py/%e.py')
esdtool('-i', f'{GAME}/script/talk/m15_00_00_00.talkesdbnd.dcx', '-f', 't150625', '-writepy', f'{work}/py/%e.py')
esdtool('-i', f'{GAME}/script/talk/m15_01_00_00.talkesdbnd.dcx', '-f', 't151621', '-writepy', f'{work}/py/%e.py')
esdtool('-i', f'{GAME}/script/talk/m10_02_00_00.talkesdbnd.dcx', '-f', 't102624', 't102626', 't102627', '-writepy', f'{work}/py/%e.py')
def esd_src(name):
    return open(f'{work}/py/{name}.py', encoding='utf-8').read()
def esd_out(name, text):
    open(f'{work}/src/{name}.py', 'w', encoding='utf-8').write(text)
    return f'{work}/src/{name}.py'
src = esd_src('t101623')
sources = [esd_out('t101623', hub_yulia.patch_esd(hub_npc_esd.burg(src))),
           esd_out('t102690', hub_yulia.patch_esd(hub_npc_esd.firelink(src))),
           esd_out('t101619', hub_npcs.andre_burg(esd_src('t101619'))),
           esd_out('t102692', hub_talks.greeting(hub_npcs.firelink_copy(esd_src('t101619'), 101619, 102692), 'andre')),
           esd_out('t102691', hub_talks.greeting(hub_npcs.firelink_copy(esd_src('t150625'), 150625, 102691), 'sen')),
           esd_out('t102627', hub_quests.crestfallen(hub_talks.pendant(esd_src('t102627')))),
           esd_out('t151621', hub_npcs.giant_anor_londo(esd_src('t151621'))),
           esd_out('t102695', hub_npcs.firelink_copy(esd_src('t151621'), 151621, 102695)),
           esd_out('t102693', hub_respec.anastacia_esd()),
           esd_out('t102694', hub_talks.greeting(hub_npcs.firelink_copy(esd_src('t102624'), 102624, 102694), 'female'))]
esdtool('-i', f'{GAME}/script/talk/m10_02_00_00.talkesdbnd.dcx', '-f', 't100200', '-writepy', f'{work}/py/%e.py')
bon = hub_travel.patch_bonfire(open(f'{work}/py/t100200.py', encoding='utf-8').read(), TRAVEL)
bon = hub_estus.patch_bonfire(bon)
if DEBUG:
    bon = hub_debug.patch_bonfire(bon)
sources.append(esd_out('t100200', bon))
esdtool('-i', *sources, '-extra', 't102690=m10_02_00_00', 't102691=m10_02_00_00', 't102692=m10_02_00_00', 't102693=m10_02_00_00', 't102694=m10_02_00_00', 't102695=m10_02_00_00', '-writebnd', f'{work}/bnd')
shutil.rmtree('out/h/talk', ignore_errors=True)   # stale debug copies must not survive a release build
os.makedirs('out/h/talk', exist_ok=True)
for m in ('m10_01_00_00', 'm10_02_00_00', 'm15_01_00_00'):
    print(m, talkpatch.patch(f'{GAME}/script/talk/{m}.talkesdbnd.dcx', f'{work}/bnd/{m}.talkesdbnd.dcx',
                             f'out/h/talk/{m}.talkesdbnd.dcx'))
if True:
    # every bonfire in the game runs the same dialog: copy the patched one into every map
    import hashlib
    _, fl_bnd = dcx_read('out/h/talk/m10_02_00_00.talkesdbnd.dcx')
    patched = next(f[3] for f in Bnd3(fl_bnd).files if f[2].decode('shift_jis').endswith('t100200.esd'))
    _, van = dcx_read(f'{GAME}/script/talk/m10_02_00_00.talkesdbnd.dcx')
    vanilla = next(f[3] for f in Bnd3(van).files if f[2].decode('shift_jis').endswith('t100200.esd'))
    count = 0
    for name in sorted(os.listdir(f'{GAME}/script/talk')):
        out = f'out/h/talk/{name}'
        h, d = dcx_read(out if os.path.exists(out) else f'{GAME}/script/talk/{name}')
        bnd = Bnd3(d)
        hits = [f for f in bnd.files if f[3] == vanilla]
        for f in hits:
            f[3] = patched
        if hits:
            dcx_write(out, h, bnd.build())
            count += len(hits)
    print('bonfire dialog patched in', count + 1, 'places')

# --- runtime DLL (amber herbs): generated tables + Zig/clang build
mp, ml, _ = P['Magic']
spells = sorted((r[0], ml.get(r[1], 'maxQuantity')) for r in mp.rows if r[0] < 10000 and ml.get(r[1], 'maxQuantity') > 0)
NL = chr(10)
with open('dll/generated.h', 'w') as f:
    f.write('/* generated by build.py */' + NL)
    f.write('typedef struct { int goods_id; int percent; } Herb;' + NL)
    f.write('static const Herb HERBS[] = {' + ', '.join(f'{{{g}, {p}}}' for g, p, *_ in hub_items.HERBS) + '};' + NL)
    f.write('static const int SPELL_MAX[][2] = {' + ', '.join(f'{{{s}, {q}}}' for s, q in spells) + '};' + NL)
    cp, cl, _ = P['CharaInitParam']
    keys = ('soulLv', 'baseVit', 'baseWil', 'baseEnd', 'baseStr', 'baseDex', 'baseDurability', 'baseMag', 'baseFai')
    classes = [[cl.get(cp[3000 + c], k) for k in keys] for c in range(10)]   # PGD class byte 0..9 = rows 3000..3009
    f.write(f'#define RESPEC_GOODS {hub_respec.GOODS_ID}' + NL + '#define CLASS_COUNT 10' + NL)
    f.write(f'#define ESTUS_SHARD {hub_estus.SHARD}' + NL + f'#define ESTUS_KINDLED {hub_estus.KINDLED}' + NL + f'#define ESTUS_BASE {hub_estus.BASE}' + NL + f'#define ESTUS_MAX {hub_estus.MAX}' + NL)
    f.write('static const int ESTUS_CHARGED[] = {' + ', '.join(map(str, hub_estus.ESTUS_CHARGED)) + '};' + NL)
    f.write('static const int CLASS_BASE[CLASS_COUNT][9] = {' + ', '.join('{' + ', '.join(map(str, c)) + '}' for c in classes) + '};' + NL)
    # travel: request flag k -> the DLL warps to bonfire k's spawn point (bonfire entity + 1000)
    f.write(f'#define WARP_REQUEST_BASE {hub_travel.REQUEST_BASE}' + NL)
    f.write('static const int WARP_TARGETS[] = {' + ', '.join(str(ent + 1000) for _, _, ent in TRAVEL) + '};' + NL)
ZIG = os.path.abspath(os.path.join('..', 'tools_dl', 'zig', 'zig-x86_64-windows-0.16.0', 'zig.exe'))
r = subprocess.run([ZIG, 'cc', '-target', 'x86_64-windows-gnu', '-shared', '-O2', '-Wall',
                    '-o', os.path.abspath('out/h/firelinkhub.dll'), 'firelinkhub.c'],
                   cwd='dll', capture_output=True, text=True)
if r.returncode != 0:
    sys.exit('DLL build failed:' + NL + r.stdout + r.stderr)
if r.stderr.strip():
    print(r.stderr)
print('built', 'DEBUG' if DEBUG else 'release', sorted(os.listdir('out/h')))
