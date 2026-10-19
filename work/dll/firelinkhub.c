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
        int add = mx * percent / 100;                 /* whole casts, rounded down */
        if (add < 1 && mx >= 3) add = 1;              /* 1-2 cast spells: only what the share gives */
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

/* ---- travel: the game's own bonfire warp (what the vanilla warp menu and DSR Gadget use) ----
 * Travel / debug set request flag WARP_REQUEST_BASE + k and close the bonfire menu. Here: clear the flag,
 * write bonfire k's spawn point (bonfire entity + 1000) as the "last bonfire" and call the game's bonfire
 * warp with (GameDataMan, 1) - it loads the map and puts the player there, any map to any map.
 * (A map event warp, 2003[14], loses its spawn point across maps: the player fell out of the world.) */
static const int WARP_PATTERN[] = {0x48,0x89,0x5C,0x24,0x08,0x57,0x48,0x83,0xEC,0x20,0x48,0x8B,0xD9,0x8B,0xFA,0x48,
                                   0x8B,0x49,0x08,0x48,0x85,0xC9,0x0F,0x84,-1,-1,-1,-1,0xE8,-1,-1,-1,-1,0x48,0x8B,0x4B,0x08};
/* "48 8B 05 ? ? ? ? 66 0F 7F 80 [StableXYZ] 0F 28 02 ...": a static pointer, then the stable position's offset */
static const int CHR_WARP_PATTERN[] = {0x48,0x8B,0x05,-1,-1,-1,-1,0x66,0x0F,0x7F,0x80,-1,-1,-1,-1,0x0F,0x28,0x02,
                                       0x66,0x0F,0x7F,0x80,-1,-1,-1,-1,0xC6,0x80};
/* "48 8B 0D ? ? ? ? 99 33 C2 45 33 C0 2B C2 8D 50 F6": the event flag manager's static pointer */
static const int FLAGS_PATTERN[] = {0x48,0x8B,0x0D,-1,-1,-1,-1,0x99,0x33,0xC2,0x45,0x33,0xC0,0x2B,0xC2,0x8D,0x50,0xF6};
#define GADGET_STABLE_X 0xB90       /* DSR Gadget's offsets for the first game version; */
#define GADGET_LAST_BONFIRE 0xB24   /* newer versions moved both by the same amount */
#define WARP_COUNT (sizeof(WARP_TARGETS) / sizeof(WARP_TARGETS[0]))

typedef void (*BonfireWarpFn)(ULONG_PTR game_data_man, int unk);

static unsigned char *find_pattern(const int *pat, SIZE_T n) {
    unsigned char *base = (unsigned char *)GetModuleHandleA(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    SIZE_T size = nt->OptionalHeader.SizeOfImage;
    for (SIZE_T i = 0; i + n < size; i++) {
        SIZE_T k = 0;
        for (; k < n; k++) if (pat[k] >= 0 && base[i + k] != pat[k]) break;
        if (k == n) return base + i;
    }
    return 0;
}
static ULONG_PTR rip_target(unsigned char *at) { return (ULONG_PTR)(at + 7 + *(int *)(at + 3)); }

static ULONG_PTR g_flags_ptr, g_chr_warp_ptr;
static int g_last_bonfire_off;
static BonfireWarpFn g_bonfire_warp;

/* event flag -> byte offset + mask in the flag block (DSR Gadget's layout): 8 digits g aaa s nnn */
static int flag_offset(int id, unsigned *mask) {
    static const int areas[][2] = {{0,0},{100,1},{101,2},{102,3},{110,4},{120,5},{121,6},{130,7},{131,8},{132,9},
                                   {140,10},{141,11},{150,12},{151,13},{160,14},{170,15},{180,16},{181,17}};
    int group = id / 10000000, area = id / 10000 % 1000, section = id / 1000 % 10, number = id % 1000;
    int g;
    switch (group) { case 0: g = 0; break; case 1: g = 0x500; break; case 5: g = 0x5F00; break;
                     case 6: g = 0xB900; break; case 7: g = 0x11300; break; default: return -1; }
    for (size_t i = 0; i < sizeof areas / sizeof areas[0]; i++)
        if (areas[i][0] == area) {
            *mask = 0x80000000u >> (number % 32);
            return g + areas[i][1] * 0x500 + section * 128 + (number - number % 32) / 8;
        }
    return -1;
}
static ULONG_PTR flag_block(void) { ULONG_PTR p = rdp(g_flags_ptr); return p ? rdp(p) : 0; }
static int get_flag(int id) {
    unsigned mask, v;
    int off = flag_offset(id, &mask);
    ULONG_PTR b = flag_block();
    return off >= 0 && b && rd(b + off, &v, 4) && (v & mask) != 0;
}
static void clear_flag(int id) {
    unsigned mask, v;
    int off = flag_offset(id, &mask);
    ULONG_PTR b = flag_block();
    if (off >= 0 && b && rd(b + off, &v, 4)) { v &= ~mask; wr(b + off, &v, 4); }
}

static void init_warp(void) {
    unsigned char *f = find_pattern(FLAGS_PATTERN, sizeof FLAGS_PATTERN / sizeof FLAGS_PATTERN[0]);
    unsigned char *c = find_pattern(CHR_WARP_PATTERN, sizeof CHR_WARP_PATTERN / sizeof CHR_WARP_PATTERN[0]);
    g_bonfire_warp = (BonfireWarpFn)find_pattern(WARP_PATTERN, sizeof WARP_PATTERN / sizeof WARP_PATTERN[0]);
    if (f) g_flags_ptr = rip_target(f);
    if (c) {
        g_chr_warp_ptr = rip_target(c);
        g_last_bonfire_off = *(int *)(c + 11) - GADGET_STABLE_X + GADGET_LAST_BONFIRE;
    }
    log_line("travel: flags %p, chr warp %p (+0x%X), warp fn %p", (void *)g_flags_ptr, (void *)g_chr_warp_ptr,
             g_last_bonfire_off, (void *)g_bonfire_warp);
}

static void travel(ULONG_PTR gdm_ptr) {
    if (!g_flags_ptr || !g_chr_warp_ptr || !g_bonfire_warp) return;
    for (size_t k = 0; k < WARP_COUNT; k++) {
        if (!get_flag(WARP_REQUEST_BASE + (int)k)) continue;
        clear_flag(WARP_REQUEST_BASE + (int)k);
        ULONG_PTR chr = rdp(g_chr_warp_ptr), gdm = rdp(gdm_ptr);
        if (!chr || !gdm) { log_line("travel %d: not in game", (int)k); return; }
        int target = WARP_TARGETS[k];
        wr(chr + g_last_bonfire_off, &target, 4);
        log_line("travel %d: warp to spawn point %d", (int)k, target);
        Sleep(1500);                    /* let the player stand up from the bonfire first */
        g_bonfire_warp(gdm, 1);
        return;
    }
}

static DWORD WINAPI worker(LPVOID unused) {
    (void)unused;
    Sleep(5000);
    ULONG_PTR gdm_ptr = find_game_data_man_ptr();
    log_line("FirelinkHub DLL started, GameDataMan pointer at %p", (void *)gdm_ptr);
    if (!gdm_ptr) return 0;
    init_warp();
    int flags_logged = 0;
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
        if (!flags_logged) {            /* a check of the flag layout: Firelink lit = 1 on any character past the Asylum */
            log_line("flags: Firelink lit %d, Lordvessel %d, travel request 0 %d", get_flag(11020992), get_flag(710),
                     get_flag(WARP_REQUEST_BASE));
            flags_logged = 1;
        }
        travel(gdm_ptr);
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
