"""Rolls shifted one weight tier up, and the Dark Wood Grain Ring reworked.

Rolls (player a00.tae, 4 directions each):  700-703 light, 710-713 medium, 720-723 fat,
735-738 the ring's flip. New tiers: light load -> the flip, medium -> vanilla light roll,
heavy -> vanilla medium roll (the fat roll is gone). The motion files are swapped inside
c0000_a00_lo.anibnd, and each roll animation gets the lighter roll's events (invincibility, sounds).

Dark Wood Grain Ring: no longer changes rolls (its stateInfo 115 did). Instead every hit starts
or extends a combo: four stacked effects, each added by the previous one on the next hit within
3 s - +5% / +5% / +5% / +10% damage, the last with a red aura.
"""
import struct
from load import *
from souls import Bnd3, dcx_read, dcx_write
from tae import Tae
import tae_patch as tp

REMAP = {700: 735, 710: 700, 720: 710}   # first id of each 4-direction block: new <- old
RING = 128
COMBO_SP = 92540                          # 92540..92543
COMBO_STEPS = [1.05, 1.05, 1.05, 1.10]
COMBO_SECONDS = 3.0
VFX_COMBO_MAX = 253

TEXT = {}   # item.msgbnd: (kind, id) -> {'ru', 'en'}; kinds rname / rinfo / rcaption (rings)


MOTIONS = 'c0000_a00_lo.anibnd.dcx'        # holds a00_0700.hkx ... a00_0738.hkx (file id = animation id)


def remap(data):
    """a00.tae bytes -> bytes (same size): the roll animations' bodies are permuted, so each roll gets
    the events (invincibility, sounds, cancel windows) of the roll whose motion it now plays
    (swap_motions). A permutation: two entries on one body made the game quit on start, and
    bodies appended at the end of the file had their events ignored (no sounds)."""
    t = Tae(data)
    out = bytearray(data)
    count, list_off = struct.unpack_from('<ii', out, 0x54)
    index = {struct.unpack_from('<i', out, list_off + i * 8)[0]: i for i in range(count)}
    cycle = dict(REMAP)
    cycle[735] = 720              # the fat roll's body goes to the ring's old flip slot: nothing shared
    for new, old in cycle.items():
        for k in range(4):
            struct.pack_into('<i', out, list_off + index[new + k] * 8 + 4, t.body[old + k])
    return bytes(out)


def swap_motions(src_path, out_path):
    """The motion files of the roll animations: a00_0700.hkx gets the flip's motion, and so on."""
    h, d = dcx_read(src_path)
    bnd = Bnd3(d)
    by_id = {f[1]: f for f in bnd.files}
    vanilla = {f[1]: f[3] for f in bnd.files}
    for new, old in REMAP.items():
        for k in range(4):
            by_id[new + k][3] = vanilla[old + k]
    dcx_write(out_path, h, bnd.build())


def apply():
    sp, sl, _ = P['SpEffectParam']
    vp, vl, _ = P['SpEffectVfxParam']
    acp, acl, _ = P['EquipParamAccessory']
    v = vp.add(VFX_COMBO_MAX, vp[48], b'[FirelinkHub] Combo max')     # Red Tearstone aura
    vl.set(v, 'midstSfxId', 24003)
    attacker = {k: sl.get(sp[2241], k) for k in sl.slots if k.startswith('effectTarget')}   # on the attacker
    for k, rate in enumerate(COMBO_STEPS):
        e = sp.add(COMBO_SP + k, sp[2241], f'[Ring] Dark Wood Grain - combo {k + 1}'.encode())
        sl.set(e, 'changeHpPoint', 0)
        sl.set(e, 'effectEndurance', COMBO_SECONDS)
        sl.set(e, 'spCategory', 0)                     # the steps stack instead of replacing each other
        for f in ('physicsAttackPowerRate', 'magicAttackPowerRate', 'fireAttackPowerRate', 'thunderAttackPowerRate'):
            sl.set(e, f, rate)
        for f, val in attacker.items():
            sl.set(e, f, val)
        sl.set(e, 'atkOccurrenceSpEffectId', COMBO_SP + min(k + 1, len(COMBO_STEPS) - 1))   # next hit: next step
        sl.set(e, 'stateInfo', VFX_COMBO_MAX if k == len(COMBO_STEPS) - 1 else 0)
    ring_sp = sp[acl.get(acp[RING], 'refId')]
    sl.set(ring_sp, 'stateInfo', 0)                  # 115 = flip rolls: gone
    sl.set(ring_sp, 'atkOccurrenceSpEffectId', COMBO_SP)
    TEXT[('rinfo', RING)] = {'ru': 'Серия попаданий усиливает урон.', 'en': 'A series of hits raises damage.'}
    TEXT[('rcaption', RING)] = {
        'ru': '\nОсобое кольцо, сделанное на Востоке.\nЗолотое, с имитацией деревянной поверхности.\n\n'
              'Носящий его входит в ритм боя: каждое\nпопадание в течение 3 секунд после\nпредыдущего '
              'усиливает урон (+5%, +10%,\n+15%, затем +25%). Пауза обрывает серию.',
        'en': '\nA special ring made in the East.\nGold, with an imitation wood grain finish.\n\n'
              'Its wearer falls into the rhythm of battle:\nevery hit within 3 seconds of the last one\n'
              'raises damage (+5%, +10%, +15%, then +25%).\nA pause breaks the series.'}
