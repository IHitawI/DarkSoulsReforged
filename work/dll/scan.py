"""Read-only memory scanner for DARK SOULS REMASTERED (research for the spell-restore DLL).

    python scan.py spells        # find attuned spells (id, uses) in PlayerGameData
    python scan.py effect 92210  # find an active SpEffect id near the player character
Nothing is ever written to the game.
"""
import ctypes as C
import ctypes.wintypes as W
import struct
import sys

k32 = C.WinDLL('kernel32', use_last_error=True)
PROCESS_VM_READ, PROCESS_QUERY_INFORMATION = 0x10, 0x400
TH32CS_SNAPPROCESS, TH32CS_SNAPMODULE = 0x2, 0x8


class PROCESSENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('cntUsage', W.DWORD), ('th32ProcessID', W.DWORD),
                ('th32DefaultHeapID', C.c_void_p), ('th32ModuleID', W.DWORD), ('cntThreads', W.DWORD),
                ('th32ParentProcessID', W.DWORD), ('pcPriClassBase', C.c_long), ('dwFlags', W.DWORD),
                ('szExeFile', W.WCHAR * 260)]


class MODULEENTRY32W(C.Structure):
    _fields_ = [('dwSize', W.DWORD), ('th32ModuleID', W.DWORD), ('th32ProcessID', W.DWORD),
                ('GlblcntUsage', W.DWORD), ('ProccntUsage', W.DWORD), ('modBaseAddr', C.c_void_p),
                ('modBaseSize', W.DWORD), ('hModule', C.c_void_p), ('szModule', W.WCHAR * 256),
                ('szExePath', W.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = W.HANDLE
k32.OpenProcess.restype = W.HANDLE
k32.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]


def find_game():
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    e = PROCESSENTRY32W(); e.dwSize = C.sizeof(e)
    ok = k32.Process32FirstW(snap, C.byref(e))
    while ok:
        if e.szExeFile.lower() == 'darksoulsremastered.exe':
            pid = e.th32ProcessID
            break
        ok = k32.Process32NextW(snap, C.byref(e))
    else:
        sys.exit('DarkSoulsRemastered.exe is not running')
    k32.CloseHandle(snap)
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    m = MODULEENTRY32W(); m.dwSize = C.sizeof(m)
    k32.Module32FirstW(snap, C.byref(m))
    base, size = m.modBaseAddr, m.modBaseSize
    k32.CloseHandle(snap)
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        sys.exit(f'OpenProcess failed: {C.get_last_error()} (try running as administrator)')
    return h, base, size


def read(h, addr, n):
    buf = C.create_string_buffer(n); got = C.c_size_t()
    if not k32.ReadProcessMemory(h, C.c_void_p(addr), buf, n, C.byref(got)):
        return None
    return buf.raw[:got.value]


def ptr(h, addr):
    b = read(h, addr, 8)
    return struct.unpack('<Q', b)[0] if b else 0


def aob(image, pattern):
    pat = [None if t == '?' else int(t, 16) for t in pattern.split()]
    first = next(i for i, b in enumerate(pat) if b is not None)
    start = 0
    while True:
        i = image.find(bytes([pat[first]]), start)
        if i < 0:
            return -1
        s = i - first
        if s >= 0 and all(b is None or image[s + k] == b for k, b in enumerate(pat)):
            return s
        start = i + 1


def rip_target(image, base, at):
    """Address referenced by a 'mov rax, [rip+disp32]' (7-byte) instruction at offset `at`."""
    disp = struct.unpack_from('<i', image, at + 3)[0]
    return base + at + 7 + disp


CHR_CLASS_BASE = '48 8B 05 ? ? ? ? 48 85 C0 ? ? F3 0F 58 80 AC 00 00 00'   # GameDataMan (DSR Gadget)
WORLD_CHR_BASE = '48 8B 05 ? ? ? ? 48 8B 48 68 48 85 C9 0F 84 ? ? ? ? 48 39 5E 10 0F 84 ? ? ? ? 48'


def main():
    h, base, size = find_game()
    image = read(h, base, size)
    print(f'module base {base:#x} size {size:#x}')
    if sys.argv[1] == 'spells':
        at = aob(image, CHR_CLASS_BASE)
        gdm = ptr(h, rip_target(image, base, at))
        pgd = ptr(h, gdm + 0x10)
        stats = read(h, pgd + 0x40, 0x58)
        print(f'GameDataMan {gdm:#x}  PlayerGameData {pgd:#x}')
        print('  Vit/Att/End/Str/Dex/Int/Fth:', [struct.unpack_from('<i', stats, o)[0] for o in range(0, 0x38, 8)])
        blob = read(h, pgd, 0x2000) or b''
        spell_ids = set(range(3000, 6000))
        for off in range(0, len(blob) - 8, 4):
            sid, cnt = struct.unpack_from('<ii', blob, off)
            if sid in spell_ids and sid % 10 == 0 and 0 <= cnt <= 100:
                print(f'  PlayerGameData+{off:#06x}: spell {sid} uses {cnt}  | next ints',
                      struct.unpack_from('<6i', blob, off + 8) if off + 32 <= len(blob) else '')
    elif sys.argv[1] == 'effect':
        target = int(sys.argv[2])
        at = aob(image, WORLD_CHR_BASE)
        wcb = ptr(h, rip_target(image, base, at))
        chr_ = ptr(h, wcb + 0x68)
        print(f'WorldChrBase {wcb:#x}  player chr {chr_:#x}')
        blob = read(h, chr_, 0x1000) or b''
        for off in range(0, len(blob) - 4, 4):
            if struct.unpack_from('<i', blob, off)[0] == target:
                print(f'  chr+{off:#05x} holds {target} directly')
        # one level of pointers out of the chr struct
        for off in range(0, len(blob) - 8, 8):
            p = struct.unpack_from('<Q', blob, off)[0]
            if not (0x10000 < p < 0x7fffffffffff):
                continue
            sub = read(h, p, 0x400)
            if not sub:
                continue
            for o2 in range(0, len(sub) - 4, 4):
                if struct.unpack_from('<i', sub, o2)[0] == target:
                    print(f'  [chr+{off:#05x}] -> {p:#x} +{o2:#05x} holds {target} | around:',
                          struct.unpack_from('<8i', sub, max(0, o2 - 8)))


if __name__ == '__main__':
    main()
