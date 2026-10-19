/* FirelinkHub runtime DLL (loaded by Mod Engine 2 via external_dlls).
 *
 * Amber herbs: when the amount of an amber herb in the inventory goes down (the herb was eaten),
 * every attuned spell gets back a share of its maximum uses.
 *
 * Estus: bonfires fill the flask as usual (by kindling), then the charges are cut down to
 * ESTUS_BASE + Estus Flames (kindled Estus Shards) in the inventory, at most ESTUS_MAX.
 *
 * Memory layout (DSR, found with a read-only scanner):
 *   GameDataMan   = *(rip-relative pointer found by CHR_CLASS_BASE pattern, same as DSR Gadget)
 *   PlayerGameData = *(GameDataMan + 0x10)
 *   inventory: records inside PlayerGameData, goods record = { 0x40000000?, id, quantity, ... }
 *   MagicData  = *(PlayerGameData + 0x418); slots at +0x18: 12 x { int spell id (-1 empty), int uses*3 }
 * All memory access goes through ReadProcessMemory/WriteProcessMemory on our own process, so a
 * bad pointer (main menu, loading screen) can never crash the game.
 */
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "generated.h"   /* from build.py: SPELL_MAX {spell id, max uses}, HERBS {goods id, percent} */

#define USES_UNIT 3      /* the game stores uses x3 */
#define SLOT_COUNT 12
#define PGD_SCAN 0x10000

#define HERB_COUNT (sizeof(HERBS) / sizeof(HERBS[0]))

static HANDLE g_proc;
static char g_log[MAX_PATH];

static void log_line(const char *fmt, ...) {
    FILE *f = fopen(g_log, "a");
    if (!f) return;
    SYSTEMTIME t; GetLocalTime(&t);
    fprintf(f, "%02d:%02d:%02d ", t.wHour, t.wMinute, t.wSecond);
    va_list a; va_start(a, fmt); vfprintf(f, fmt, a); va_end(a);
    fputc('\n', f);
    fclose(f);
}

static int rd(ULONG_PTR addr, void *out, SIZE_T n) {
    SIZE_T got = 0;
    return addr && ReadProcessMemory(g_proc, (LPCVOID)addr, out, n, &got) && got == n;
}
static ULONG_PTR rdp(ULONG_PTR addr) { ULONG_PTR v = 0; return rd(addr, &v, sizeof v) ? v : 0; }
static int wr(ULONG_PTR addr, const void *in, SIZE_T n) {
    SIZE_T put = 0;
    return WriteProcessMemory(g_proc, (LPVOID)addr, in, n, &put) && put == n;
}

/* "48 8B 05 ? ? ? ? 48 85 C0 ? ? F3 0F 58 80 AC 00 00 00" */
static const int GDM_PATTERN[] = {0x48,0x8B,0x05,-1,-1,-1,-1,0x48,0x85,0xC0,-1,-1,0xF3,0x0F,0x58,0x80,0xAC,0x00,0x00,0x00};

static ULONG_PTR find_game_data_man_ptr(void) {
    unsigned char *base = (unsigned char *)GetModuleHandleA(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    SIZE_T size = nt->OptionalHeader.SizeOfImage, n = sizeof(GDM_PATTERN) / sizeof(GDM_PATTERN[0]);
    for (SIZE_T i = 0; i + n < size; i++) {
        SIZE_T k = 0;
        for (; k < n; k++) if (GDM_PATTERN[k] >= 0 && base[i + k] != GDM_PATTERN[k]) break;
        if (k == n) {
            int disp = *(int *)(base + i + 3);
            return (ULONG_PTR)(base + i + 7 + disp);
        }
    }
    return 0;
}

static int max_uses(int spell) {
    for (size_t i = 0; i < sizeof(SPELL_MAX) / sizeof(SPELL_MAX[0]); i++)
        if (SPELL_MAX[i][0] == spell) return SPELL_MAX[i][1];
    return 0;
}

/* quantity of a goods item in the inventory (0 if absent / unreadable) */
static int herb_quantity(const unsigned char *pgd, int goods_id) {
    for (int o = 4; o + 8 <= PGD_SCAN; o += 4) {
        int cat, id, qty;
        memcpy(&cat, pgd + o - 4, 4); memcpy(&id, pgd + o, 4); memcpy(&qty, pgd + o + 4, 4);
        if (id == goods_id && cat == 0x40000000 && qty > 0 && qty < 1000) return qty;
    }
    return 0;
}

/* cut the charges of the Estus Flask record (goods 201, 203, ... 215: quantity = charges) */
static void cap_estus(ULONG_PTR pgd, const unsigned char *buf) {
    int cap = ESTUS_BASE + herb_quantity(buf, ESTUS_KINDLED);   /* Estus Flames: kindled shards */
    if (cap > ESTUS_MAX) cap = ESTUS_MAX;
    for (int o = 4; o + 8 <= PGD_SCAN; o += 4) {
        int cat, id, qty;
        memcpy(&cat, buf + o - 4, 4); memcpy(&id, buf + o, 4); memcpy(&qty, buf + o + 4, 4);
        if (cat != 0x40000000 || qty <= cap || qty > 99) continue;
        for (size_t i = 0; i < sizeof(ESTUS_CHARGED) / sizeof(ESTUS_CHARGED[0]); i++) {
            if (id != ESTUS_CHARGED[i]) continue;
            wr(pgd + o + 4, &cap, 4);
            log_line("estus %d: %d -> %d charges", id, qty, cap);
        }
    }
}

static void restore_spells(ULONG_PTR pgd, int percent) {
    ULONG_PTR magic = rdp(pgd + 0x418);
    int slots[SLOT_COUNT][2];
    if (!magic || !rd(magic + 0x18, slots, sizeof slots)) { log_line("restore: no magic data"); return; }
    for (int s = 0; s < SLOT_COUNT; s++) {
        int id = slots[s][0], stored = slots[s][1];
        if (id <= 0) continue;
        int mx = max_uses(id);
        if (mx <= 0) continue;
        int add = (mx * percent + 50) / 100;          /* whole casts, rounded */
        if (add < 1) add = 1;
        int now = stored + add * USES_UNIT, cap = mx * USES_UNIT;
        if (now > cap) now = cap;
        if (now != stored) {
            wr(magic + 0x18 + s * 8 + 4, &now, 4);
            log_line("  spell %d: %d -> %d uses (max %d)", id, stored / USES_UNIT, now / USES_UNIT, mx);
        }
    }
}

/* Rebirth Stone: back to the class's starting stats, refund the souls spent on levels.
 * PlayerGameData: stats are ints 8 bytes apart (DSR Gadget offsets), class is a byte. */
static const int STAT_OFF[8] = {0x40, 0x48, 0x50, 0x58, 0x60, 0x88, 0x68, 0x70};  /* vit att end str dex res int fth */
#define PGD_SOUL_LEVEL 0x90
#define PGD_SOULS 0x94
#define PGD_CLASS 0xCE
#define SOULS_CAP 999999999

/* souls to reach soul level `lv` from lv - 1 (DS1 formula; levels 2-11 from the game's table) */
static long long level_cost(int lv) {
    static const int low[] = {0, 0, 673, 690, 707, 724, 741, 758, 775, 793, 811, 829};
    if (lv < 2) return 0;
    if (lv < 12) return low[lv];
    double x = lv;
    return (long long)(0.02 * x * x * x + 3.06 * x * x + 105.6 * x - 895 + 0.5);
}

static void respec(ULONG_PTR pgd) {
    unsigned char cls = 0xFF;
    int sl = 0, souls = 0, stats[8];
    if (!rd(pgd + PGD_CLASS, &cls, 1) || cls >= CLASS_COUNT) { log_line("respec: unknown class %d", cls); return; }
    if (!rd(pgd + PGD_SOUL_LEVEL, &sl, 4) || !rd(pgd + PGD_SOULS, &souls, 4)) { log_line("respec: no data"); return; }
    for (int i = 0; i < 8; i++) rd(pgd + STAT_OFF[i], &stats[i], 4);
    const int *base = CLASS_BASE[cls];   /* soul level, then the 8 stats in STAT_OFF order */
    long long refund = 0;
    for (int lv = base[0] + 1; lv <= sl; lv++) refund += level_cost(lv);
    long long total = souls + refund;
    if (total > SOULS_CAP) total = SOULS_CAP;
    int new_souls = (int)total;
    log_line("respec: class %d, SL %d -> %d, stats %d/%d/%d/%d/%d/%d/%d/%d, souls %d + %lld",
             cls, sl, base[0], stats[0], stats[1], stats[2], stats[3], stats[4], stats[5], stats[6], stats[7],
             souls, refund);
    for (int i = 0; i < 8; i++) wr(pgd + STAT_OFF[i], &base[i + 1], 4);
    wr(pgd + PGD_SOUL_LEVEL, &base[0], 4);
    wr(pgd + PGD_SOULS, &new_souls, 4);
}

static DWORD WINAPI worker(LPVOID unused) {
    (void)unused;
    Sleep(5000);
    ULONG_PTR gdm_ptr = find_game_data_man_ptr();
    log_line("FirelinkHub DLL started, GameDataMan pointer at %p", (void *)gdm_ptr);
    if (!gdm_ptr) return 0;
    static unsigned char pgd_buf[PGD_SCAN];
    ULONG_PTR last_pgd = 0;
    int last_qty[HERB_COUNT], last_stone = 0;
    for (;;) {
        Sleep(100);
        ULONG_PTR gdm = rdp(gdm_ptr);
        ULONG_PTR pgd = gdm ? rdp(gdm + 0x10) : 0;
        if (!pgd || !rd(pgd, pgd_buf, PGD_SCAN)) { last_pgd = 0; continue; }
        if (pgd != last_pgd) {                      /* new character / save loaded: take a baseline */
            for (size_t i = 0; i < HERB_COUNT; i++) last_qty[i] = herb_quantity(pgd_buf, HERBS[i].goods_id);
            last_stone = herb_quantity(pgd_buf, RESPEC_GOODS);
            last_pgd = pgd;
            continue;
        }
        cap_estus(pgd, pgd_buf);
        int stone = herb_quantity(pgd_buf, RESPEC_GOODS);   /* a key item: it only leaves when given away */
        if (stone < last_stone) respec(pgd);
        last_stone = stone;
        for (size_t i = 0; i < HERB_COUNT; i++) {
            int q = herb_quantity(pgd_buf, HERBS[i].goods_id);
            if (q < last_qty[i]) {
                for (int used = last_qty[i] - q; used > 0; used--) {
                    log_line("amber herb %d used: +%d%%", HERBS[i].goods_id, HERBS[i].percent);
                    restore_spells(pgd, HERBS[i].percent);
                }
            }
            last_qty[i] = q;
        }
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) {
    (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        g_proc = GetCurrentProcess();
        GetModuleFileNameA(h, g_log, MAX_PATH);
        char *s = strrchr(g_log, '\\');
        if (s) strcpy(s + 1, "firelinkhub.log");
        CreateThread(0, 0, worker, 0, 0, 0);
    }
    return TRUE;
}
