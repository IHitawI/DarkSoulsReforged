import ctypes, os, time, sys
os.add_dll_directory(os.path.dirname(os.path.abspath('probe.dll')))
h = ctypes.WinDLL(os.path.abspath('probe.dll'))
time.sleep(0.5)
print(open('probe.log').read().strip())
