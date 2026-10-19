#include <windows.h>
#include <string.h>

static DWORD WINAPI worker(LPVOID p) {
    char path[MAX_PATH];
    GetModuleFileNameA((HMODULE)p, path, MAX_PATH);
    char *s = strrchr(path, '\\');
    if (s) strcpy(s + 1, "probe.log");
    HANDLE f = CreateFileA(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, 0, 0);
    DWORD w;
    const char *msg = "probe loaded\r\n";
    WriteFile(f, msg, (DWORD)strlen(msg), &w, 0);
    CloseHandle(f);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) {
    (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        CreateThread(0, 0, worker, h, 0, 0);
    }
    return TRUE;
}
