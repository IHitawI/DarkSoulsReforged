"""Boss AI changed for the second phase (GDD patch 2: unique boss phases).

A boss's battle script (Lua 5.0, 64-bit bytecode in script/<map>.luabnd) is decompiled with DSLuaDecompiler
(comes with Grimrukh's soulstruct), patched as text and compiled back with our own luac 5.0.3
(tools_dl/lua50/luac50.exe, built with zig: soulstruct's LuaC.exe is a debug build that needs Visual
Studio's ucrtbased.dll). The second phase is visible to the script: hub_bosses puts its phase SpEffect on
the boss, ai:HasSpecialEffectId(TARGET_SELF, id) tests it.

Checked on the Taurus Demon: same bytecode header as the game's; the instruction listings differ only by
decompiler artefacts (an empty `return` at function ends, `a <= b` compiled as the reverse comparison,
a few assignments to unused locals). The decompiler writes decimals with the system's comma
(Russian Windows: "2,9") - fixed before compiling, or "local x = 2,9" would quietly become 2.

Taurus Demon (225000): in phase 2 he jumps (attack 3004, 6.5-8.5 m) a lot more: from 7 m and further
85% of his decisions (vanilla 60-75%), at 3-7 m half the time he backs off to ~7 m and jumps, up close a
third of the time. His tower logic (jumping onto / off the tower) comes first, untouched.
"""
import os, re, subprocess, tempfile
from souls import dcx_read, dcx_write, Bnd3
import luabnd, hub_bosses

DECOMPILER = os.path.expanduser(r'~\.reforged\venv\Lib\site-packages\soulstruct\base\ai\lua\x64\DSLuaDecompiler.exe')
LUAC = os.path.abspath(os.path.join('..', 'tools_dl', 'lua50', 'luac50.exe'))
RAGE = hub_bosses.PHASE_SP['rage']


def decompile(bytecode):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'temp'), 'wb').write(bytecode)
        r = subprocess.run([DECOMPILER, 'temp'], cwd=d, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        src = open(os.path.join(d, 'temp.dec.lua'), encoding='shift_jis_2004').read()
    return re.sub(r'(\d),(\d)', r'\1.\2', src)        # "2,9" -> "2.9" (arguments are always ", ")


def compile_lua(src):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'in.lua'), 'w', encoding='shift_jis_2004').write(src)
        r = subprocess.run([LUAC, '-o', 'out.luac', 'in.lua'], cwd=d, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr + r.stdout
        return open(os.path.join(d, 'out.luac'), 'rb').read()


def _sub(src, old, new):
    assert src.count(old) == 1, old
    return src.replace(old, new)


def _append(src, code):
    """New functions go before the chunk's closing `return` (nothing may follow it in Lua)."""
    body = src.rstrip()
    assert body.endswith('return'), body[-40:]
    return body[:-len('return')] + code + '\nreturn\n'


def taurus(src):
    p = 'Hammer_m10_225000'
    src = _sub(src, f'    elseif fateAct <= Act01Per then\n        {p}_Act01(ai, goal)',
               f'    elseif ai:HasSpecialEffectId(TARGET_SELF, {RAGE}) and {p}_Phase2(ai, goal, targetDist) then\n'
               f'        -- Reforged: second phase, jumps (its own roll; false = the usual choice below)\n'
               f'    elseif fateAct <= Act01Per then\n        {p}_Act01(ai, goal)')
    return _append(src, f'''
-- Reforged: Taurus Demon, second phase
function {p}_Act12(ai, goal)
    goal:AddSubGoal(GOAL_COMMON_LeaveTarget, 2.5, TARGET_ENE_0, 7, TARGET_ENE_0, true, -1)
    goal:AddSubGoal(GOAL_COMMON_AttackTunableSpin, 10, 3004, TARGET_ENE_0, DIST_Middle, -1, 27, 10, 10)
    GetWellSpace_Odds = 100
end

function {p}_Phase2(ai, goal, targetDist)
    local roll = ai:GetRandam_Int(1, 100)
    if 7 <= targetDist then
        if roll <= 85 then
            {p}_Act04(ai, goal)
            return true
        end
    elseif 3 <= targetDist then
        if roll <= 50 then
            {p}_Act12(ai, goal)
            return true
        end
    elseif roll <= 35 then
        {p}_Act12(ai, goal)
        return true
    end
    return false
end
''')


PATCHES = {  # (map, battle goal id): text patch
    ('m10_01_00_00', 225000): taurus,
}


def apply(game, out_dir):
    """Patches the luabnds in out_dir (or the game's when the build has none yet). -> [(map, goal, bytes)]."""
    done = []
    for mp in sorted({m for m, _ in PATCHES}):
        path = f'{out_dir}/{mp}.luabnd.dcx'
        h, d = dcx_read(path if os.path.exists(path) else f'{game}/script/{mp}.luabnd.dcx')
        bnd = Bnd3(d)
        for (m, goal), patch in PATCHES.items():
            if m != mp:
                continue
            f = next(f for f in bnd.files if f[2].endswith(luabnd.script_name(goal)))
            src = patch(decompile(f[3]))
            os.makedirs('out/bossai', exist_ok=True)
            open(f'out/bossai/{goal:06d}_battle.lua', 'w', encoding='utf-8').write(src)   # for reading
            f[3] = compile_lua(src)
            gnl_f = luabnd._files(bnd, b'.luagnl')                    # register the new globals, like copy_goal
            names = luabnd.read_gnl(gnl_f[3])
            new = [n.encode() for n in re.findall(r'^function (\w+)\(', src, re.M) if n.encode() not in names]
            gnl_f[3] = luabnd.build_gnl(names + new)
            done.append((mp, goal, len(f[3]), [n.decode() for n in new]))
        dcx_write(path, h, bnd.build())
    return done
