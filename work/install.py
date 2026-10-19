"""Copies the build (out/h) into the Mod Engine 2 mod folder, in the game's own layout."""
import os, shutil

MOD = r'C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS REMASTERED\ModEngine2\FirelinkHub'
OUT = 'out/h'


LOCKED = []


def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copyfile(src, dst)
    except PermissionError:          # the game is running and holds it (the DLL)
        LOCKED.append(dst)
        return 0
    return 1


n = put(f'{OUT}/GameParam.parambnd.dcx', f'{MOD}/param/GameParam/GameParam.parambnd.dcx')
n += put(f'{OUT}/firelinkhub.dll', f'{MOD}/firelinkhub.dll')
for name in os.listdir(OUT):
    for kind, file in (('msg_', 'item'), ('menu_', 'menu')):
        if name.startswith(kind) and name.endswith('.dcx'):
            n += put(f'{OUT}/{name}', f'{MOD}/msg/{name[len(kind):-4]}/{file}.msgbnd.dcx')
for sub, dst in (('event', 'event'), ('chr', 'chr'), ('obj', 'obj'), ('menu', 'menu'), ('talk', 'script/talk'), ('script', 'script'),
                 ('MapStudio', 'map/MapStudio'), ('MapStudioNew', 'map/MapStudioNew')):
    for name in os.listdir(f'{OUT}/{sub}'):
        n += put(f'{OUT}/{sub}/{name}', f'{MOD}/{dst}/{name}')
    # mirror: a file this build no longer makes must not stay in the mod (old maps pointing at removed params)
    built = set(os.listdir(f'{OUT}/{sub}'))
    for name in os.listdir(f'{MOD}/{dst}'):
        path = f'{MOD}/{dst}/{name}'
        if os.path.isfile(path) and name not in built and not name.endswith('.bak'):
            os.remove(path)
            print('removed stale', f'{dst}/{name}')
print('installed', n, 'files')
if LOCKED:
    print('LOCKED (close the game and run again):', *LOCKED, sep=chr(10) + '  ')
