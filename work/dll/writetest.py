"""One-off: give Wrath of the Gods back one cast (stored +3) to confirm the slot layout."""
import sys, struct, ctypes as C
sys.path.insert(0, '.')
import scan
from scan import *
h, base, size = find_game()
image = read(h, base, size)
gdm = ptr(h, rip_target(image, base, aob(image, CHR_CLASS_BASE)))
pgd = ptr(h, gdm + 0x10)
magic = ptr(h, pgd + 0x418)
slots = [struct.unpack_from('<ii', read(h, magic + 0x18 + i * 8, 8)) for i in range(12)]
print('slots before:', slots)
i = next(k for k, (sid, _) in enumerate(slots) if sid == 5310)
sid, stored = slots[i]
new = min(stored + 3, 9)
hw = scan.k32.OpenProcess(0x0008 | 0x0020 | 0x0010 | 0x0400, False, scan.k32.GetProcessId(h))
buf = C.c_int(new); put = C.c_size_t()
k = C.WinDLL('kernel32')
k.WriteProcessMemory.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
ok = k.WriteProcessMemory(hw, C.c_void_p(magic + 0x18 + i * 8 + 4), C.byref(buf), 4, C.byref(put))
print('write', bool(ok), 'Wrath stored', stored, '->', new)
print('slots after:', [struct.unpack_from('<ii', read(h, magic + 0x18 + j * 8, 8)) for j in range(12)][:5])
