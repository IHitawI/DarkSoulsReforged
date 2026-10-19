"""Useless items made useful: Lloyd's Talisman, Dung Pie, Rubbish."""
from load import *

TEXT = {}    # (kind, goods id) -> {'ru', 'en'}: replaces the text
APPEND = {}  # (kind, goods id) -> {'ru', 'en'}: appended to the existing text

VULN_RATE = 1.2     # Lloyd's Talisman: enemies in the area take 20% more damage
VULN_SECONDS = 15
RUBBISH_LURE = 2.5  # seconds enemies are distracted (Alluring Skull = 5)

DAMAGE_CUTS = ('slashDamageCutRate', 'blowDamageCutRate', 'thrustDamageCutRate', 'neutralDamageCutRate',
               'magicDamageCutRate', 'fireDamageCutRate', 'thunderDamageCutRate')
ENEMY_ONLY = {'effectTargetSelf': 0, 'effectTargetFriend': 0, 'effectTargetEnemy': 1,
              'effectTargetPlayer': 1, 'effectTargetAI': 1, 'effectTargetLive': 1, 'effectTargetGhost': 1}


def apply():
    gp, gl, _ = P['EquipParamGoods']
    sp, sl, _ = P['SpEffectParam']
    bp, bl, _ = P['Bullet']

    # --- Lloyd's Talisman: its Estus-blocking area also makes enemies take more damage
    vuln = sp.add(92300, sp[3150], b"[Item] Lloyd's Talisman - Vulnerability")
    for k in DAMAGE_CUTS:
        sl.set(vuln, k, VULN_RATE)
    sl.set(vuln, 'effectEndurance', float(VULN_SECONDS))
    sl.set(vuln, 'stateInfo', 0)       # 127 = Estus block, keep that only on the original effect
    sl.set(vuln, 'spCategory', 0)
    for k, v in ENEMY_ONLY.items():
        sl.set(vuln, k, v)
    area = bp[161]
    assert bl.get(area, 'spEffectId2') in (0, -1)
    bl.set(area, 'spEffectId2', 92300)
    APPEND[('info', 296)] = {'ru': f' Враги в области получают +{round((VULN_RATE - 1) * 100)}% урона.',
                             'en': f' Enemies in the area take {round((VULN_RATE - 1) * 100)}% more damage.'}
    APPEND[('caption', 296)] = {
        'ru': f'\n\nВраги в области действия {VULN_SECONDS} секунд\nполучают на {round((VULN_RATE - 1) * 100)}% больше урона.',
        'en': f'\n\nEnemies within the area take {round((VULN_RATE - 1) * 100)}% more\ndamage for {VULN_SECONDS} seconds.'}

    # --- Dung Pie: no longer poisons the thrower
    bl.set(bp[150], 'spEffectIDForShooter', 0)  # 0 = none, as in vanilla bullets
    TEXT[('info', 293)] = {'ru': 'Отравляет врага токсином.', 'en': 'Turns enemy toxic'}
    TEXT[('caption', 293)] = {
        'ru': 'Отвратительная, вонючая масса.\nБросьте во врага и отравите его токсинами.\n\n'
              'Терпеть вонь практически невозможно,\nно если отравить врага токсинами, он будет\n'
              'получать серьезный урон какое-то время.',
        'en': 'Atrocious fecal waste material.\nThrow at enemy to build up toxins.\n\n'
              "Although the stench makes it difficult to\ncarry on one's person, turning an enemy toxic\n"
              'inflicts high damage over a period of time.'}

    # --- Rubbish: thrown to briefly distract enemies, a weaker Alluring Skull
    lure = sp.add(92310, sp[3130], b'[Item] Rubbish - Lure')
    sl.set(lure, 'effectEndurance', RUBBISH_LURE)
    hit = bp.add(3551, bp[121], b'[Item] Rubbish - HitBullet')
    bl.set(hit, 'life', RUBBISH_LURE)
    bl.set(hit, 'spEffectId0', 92310)
    throw = bp.add(3550, bp[120], b'[Item] Rubbish')
    bl.set(throw, 'HitBulletID', 3551)
    g = gp[380]
    gl.set(g, 'refCategory', 1)
    gl.set(g, 'refId', 3550)
    gl.set(g, 'goodsUseAnim', gl.get(gp[294], 'goodsUseAnim'))  # same throw as Alluring Skull
    gl.set(g, 'sfxVariationId', gl.get(gp[294], 'sfxVariationId'))
    for k in ('enable_live', 'enable_gray', 'enable_white', 'enable_black', 'enable_multi', 'enable_pvp',
              'isEquip'):  # isEquip: can go into the quick-item slot; without it the item can't be used
        gl.set(g, k, 1)
    TEXT[('info', 380)] = {'ru': 'Можно бросить, чтобы ненадолго отвлечь врагов.',
                           'en': 'Throw to briefly distract enemies'}
    APPEND[('caption', 380)] = {'ru': '\n\nЕсли его бросить, враги ненадолго\nотвлекутся на шум.',
                                'en': '\n\nThrow it and enemies will be briefly\ndistracted by the noise.'}
