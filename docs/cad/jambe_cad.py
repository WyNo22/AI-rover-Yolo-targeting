"""
jambe_cad.py — CAO paramétrique des pièces imprimées d'une jambe LEO-S (Rév. F), en CadQuery.

  python jambe_cad.py            → STEP + STL de chaque pièce dans ./step et ./stl, assemblage dans ./step/assemblage_jambe.step

Repère d'une jambe (jambe droite, tendue) : x vers l'avant, y vers l'extérieur, z vers le haut,
origine sur l'axe de tangage de hanche (S2). La jambe gauche = symétrie par rapport au plan xz.
Toutes les cotes sont en mm et viennent du plan docs/jambe_leo_s.html.
À VÉRIFIER avant impression : cotes du STS3215 (relevées sur un modèle 3D), motif de trous du palonnier.
"""
import os
import cadquery as cq

# ── Paramètres ────────────────────────────────────────────────────────────────
SEG = 200.0                 # cuisse = tibia (entraxes)
SL, SW, SH = 45.22, 24.72, 35.0  # STS3215 (plan Feetech) : longueur, largeur, épaisseur du boîtier
S_END = 10.11               # arbre → bout du boîtier
S_HOLE_X, S_HOLE_Y = 2.36, 10.25  # vis de boîtier : 2,36 du bout opposé à l'arbre (18,41 + 24,45 côté arbre), ±10,25
HORN_T = 4.0                # plan d'appui des pièces sur palonnier : SH/2 + HORN_T = 21,5 de l'axe du servo
JEU = 0.2                   # jeu d'impression par côté
BRG_D, BRG_W = 16.15, 5.0   # logement 625ZZ
M5, M3, M2, INS = 5.2, 3.3, 2.3, 4.0   # passages et insert M3
T12, T10, SOCK = 12.2, 10.2, 20.0      # emmanchements tubes
B1_Y, B2_Y = 35.0, 27.0     # plans des bielles (vers l'extérieur)
ARM = 22.0                  # bras / leviers
OFF = 25.0                  # S3 et S4 en arrière de l'axe des tubes
S1_Z = 63.5                 # axe de roulis au-dessus de l'axe de tangage
FOOT = (35.0, 65.0, 65.0)   # talon, pointe, largeur
KZ, AZ, GZ = -SEG, -2 * SEG, -2 * SEG - 50.0
TOP1, CLV, TOP2 = 75.0, 35.0, 70.0   # raccord haut de cuisse, languettes (axe → bout), raccord haut de tibia
# palonnier : motif de trous à mesurer sur ton palonnier aluminium (valeurs provisoires)
HORN_PCD, HORN_N, HORN_HOLE = 14.0, 4, 3.3   # palonnier alu Ø19,2 : 4 trous en croix sur Ø14 (filetage à vérifier : M3 ou M2,5)
HORN_A0 = 0.0                # trous en croix (0°, 90°, 180°, 270°)
HORN_D, HORN_FACE = 19.2, 37.25 / 2   # palonniers des DEUX côtés (double sortie), faces extérieures à ±18,625
MP = 35.0 / 2 + 4.0          # plan d'appui = 21,5 ; un bossage Ø19,2 comble l'écart avec le palonnier

def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))

def cyl_y(x, z, r, y0, y1):
    """Cylindre d'axe y (axes des articulations de tangage)."""
    return cq.Workplane("XZ").center(x, z).circle(r).extrude(-(y1 - y0)).translate((0, y0, 0))

def cyl_z(x, y, r, z0, z1):
    return cq.Workplane("XY").center(x, y).circle(r).extrude(z1 - z0).translate((0, 0, z0))

def cyl_x(y, z, r, x0, x1):
    return cq.Workplane("YZ").center(y, z).circle(r).extrude(x1 - x0).translate((x0, 0, 0))

def servo_pocket_vertical(cx, zc, top_shaft=True):
    """Poche d'un servo dont l'arbre est d'axe y, boîtier vertical (S3, S4) : arbre en (cx, zc)."""
    z_top = zc + S_END if top_shaft else zc - S_END
    z_bot = z_top - SL if top_shaft else z_top + SL
    return box(cx - SW / 2 - JEU, cx + SW / 2 + JEU, -SH / 2 - JEU, SH / 2 + JEU, min(z_top, z_bot) - JEU, max(z_top, z_bot) + JEU)

def servo_corner_holes_y(cx, z_far, sign_far, y0, y1):
    """Trous de coin (vis M2 traversantes, d'axe y) au bout opposé à l'arbre."""
    zc = z_far + sign_far * S_HOLE_X
    h = None
    for dx in (-S_HOLE_Y, S_HOLE_Y):
        c = cyl_y(cx + dx, zc, M2 / 2, y0, y1)
        h = c if h is None else h.union(c)
    return h

# ── 1. Plaque de bassin (les deux hanches, axes à ±45 du plan médian) ──────────
def plaque_bassin():
    z0 = S1_Z + SW / 2 + 0.15
    p = box(-48, 48, -95, 95, z0, z0 + 6).edges("|Z").fillet(6)
    p = p.cut(box(-34, 34, -28, 28, z0 - 1, z0 + 7).edges("|Z").fillet(6))            # allègement central
    for yl in (45, -45):
        s_ = 1 if yl > 0 else -1
        p = p.cut(box(-34, 34, yl - s_ * 8 - 8, yl - s_ * 8 + 8, z0 - 1, z0 + 7).edges("|Z").fillet(4))  # au-dessus de S1
        for x in (-12, 12):                                                            # vis M3 vers le bloc du berceau
            p = p.cut(cyl_z(x, yl + s_ * 40, M3 / 2, z0 - 1, z0 + 7))
    return p

# ── 2. Berceau de S1 (fixe) ───────────────────────────────────────────────────
def berceau_s1():
    """Joues fines entre S1 et les plaques de l'étrier (x), bloc de vissage au-delà du bout extérieur (y 36–44)."""
    y_far = SL - S_END
    z0, z1 = S1_Z - SW / 2, S1_Z + SW / 2
    top = z1 + 0.15
    joue_av = box(SH / 2 + JEU, SH / 2 + HORN_T - 0.3, 13, y_far + 1, z0 - 1, top)
    joue_ar = box(-SH / 2 - HORN_T + 0.3, -SH / 2 - JEU, 13, y_far + 1, z0 - 1, top)
    bloc = box(-SH / 2 - HORN_T + 0.3, SH / 2 + HORN_T - 0.3, y_far + JEU, y_far + 10, z0 - 1, top)
    b = joue_av.union(joue_ar).union(bloc)
    for dz in (-S_HOLE_Y, S_HOLE_Y):
        b = b.cut(cyl_x(y_far - S_HOLE_X, S1_Z + dz, M2 / 2, -30, 30))
    for x in (-12, 12):                                       # inserts M3 sous la plaque
        b = b.cut(cyl_z(x, 40, INS / 2, top - 6, top + 1))
    return b

# ── 3. Étrier de roulis + berceau de S2 ───────────────────────────────────────
def etrier_roulis():
    def plaque(x0, x1, trou):
        prof = (cq.Workplane("YZ").moveTo(-11, S1_Z).threePointArc((0, S1_Z + 11), (11, S1_Z))
                .lineTo(11, 30).lineTo(30, 22.5).lineTo(30, 17.5).lineTo(-30, 17.5).lineTo(-30, 22.5)
                .lineTo(-11, 30).close().extrude(x1 - x0).translate((x0, 0, 0)))
        return prof.cut(cyl_x(0, S1_Z, trou / 2, x0 - 1, x1 + 1))
    av = plaque(SH / 2 + HORN_T, SH / 2 + HORN_T + 5, M3)           # sur le palonnier avant de S1
    av = av.union(cyl_x(0, S1_Z, HORN_D / 2, HORN_FACE, MP)).cut(cyl_x(0, S1_Z, M3 / 2, 0, 40))
    for i in range(HORN_N):                                            # motif provisoire du palonnier
        import math
        a = 2 * math.pi * i / HORN_N + HORN_A0
        av = av.cut(cyl_x(HORN_PCD / 2 * math.cos(a), S1_Z + HORN_PCD / 2 * math.sin(a), HORN_HOLE / 2, 0, 40))
    ar = plaque(-MP - 5, -MP, M3)                                       # sur le palonnier arrière de S1
    ar = ar.union(cyl_x(0, S1_Z, HORN_D / 2, -MP, -HORN_FACE)).cut(cyl_x(0, S1_Z, M3 / 2, -40, 0))
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        ar = ar.cut(cyl_x(HORN_PCD / 2 * math.cos(a), S1_Z + HORN_PCD / 2 * math.sin(a), HORN_HOLE / 2, -40, 0))
    plancher = box(-38, SH / 2 + HORN_T + 5, -30, 30, 17.5, 22.5)
    plancher = plancher.union(box(-SH / 2 - HORN_T - 5, -SH / 2 - HORN_T, -30, 30, 17.5, 22.5))
    # berceau de S2 : S2 arbre d'axe y en (0,0), boîtier x de -SL+S_END à S_END, z ±SW/2, y ±SH/2
    x_far = -(SL - S_END)
    joues = (box(x_far - 3, -18, SH / 2 + JEU, SH / 2 + 3.5, -SW / 2 - 1, 17.5)
             .union(box(x_far - 3, -18, -SH / 2 - 3.5, -SH / 2 - JEU, -SW / 2 - 1, 17.5))
             .union(box(x_far - 3, x_far - JEU, -SH / 2 - 3.5, SH / 2 + 3.5, -SW / 2 - 1, 17.5)))
    e = av.union(ar).union(plancher).union(joues)
    for dz in (-S_HOLE_Y, S_HOLE_Y):
        e = e.cut(cyl_y(x_far + S_HOLE_X, dz, M2 / 2, -30, 30))
    e = e.cut(box(-30, 10, -14, 14, 16, 24).edges("|Z").fillet(3))   # allègement du plancher
    # dégagement : volume balayé par S3 et la chape quand la hanche s'étend jusqu'à −35° (jeu 1 mm)
    s3 = box(-OFF - SW / 2 - 1, -OFF + SW / 2 + 1, -SH / 2 - 1, SH / 2 + 1, -40 - (SL - S_END), -40 + S_END + 1)
    ch = chape_cuisse()
    for a in (-15, -20, -25, -30, -35):
        e = e.cut(s3.rotate((0, 0, 0), (0, 1, 0), -a)).cut(ch.rotate((0, 0, 0), (0, 1, 0), -a))
    return e

# ── 4. Chape de cuisse + raccord haut + berceau de S3 + patte d'ancrage des ressorts
def chape_cuisse():
    bras_ext = box(-12, 12, SH / 2 + HORN_T, SH / 2 + HORN_T + 5, -31, 0).union(cyl_y(0, 0, 12, SH / 2 + HORN_T, SH / 2 + HORN_T + 5))
    bras_int = box(-12, 12, -MP - 5, -MP, -31, 0).union(cyl_y(0, 0, 12, -MP - 5, -MP))
    bossages = cyl_y(0, 0, HORN_D / 2, HORN_FACE, MP).union(cyl_y(0, 0, HORN_D / 2, -MP, -HORN_FACE))
    traverse = box(-12, 12, -MP - 5, MP + 5, -37, -31)
    corps = box(-12, 9, -12, 12, -TOP1, -31)                   # autour du tube Ø12
    # berceau de S3 : arbre en (x=-OFF, z=-40), boîtier vertical vers le bas
    s3z = -40.0
    zf = s3z - (SL - S_END)                                    # bout opposé à l'arbre
    cad = box(-OFF - SW / 2 - 3.5, -OFF + SW / 2 + 3.5, -SH / 2 - 3.5, SH / 2 + 3.5, zf - 3, s3z - 12)
    pont = box(-OFF, -6, -12, 12, -TOP1, -50)
    patte = box(6, 18, -20, 20, -TOP1, -TOP1 + 6)               # ancrage des ressorts (axe M3 d'axe y)
    c = bras_ext.union(bras_int).union(bossages).union(traverse).union(corps).union(cad).union(pont).union(patte)
    c = c.cut(servo_pocket_vertical(-OFF, s3z))
    c = c.cut(cyl_y(-OFF, s3z, HORN_D / 2 + 1, -MP - 1, -HORN_FACE + 4))   # dégagement du palonnier intérieur de S3
    c = c.cut(cyl_y(0, 0, M3 / 2, -40, 40))
    import math
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        c = c.cut(cyl_y(HORN_PCD / 2 * math.cos(a), HORN_PCD / 2 * math.sin(a), HORN_HOLE / 2, -40, 40))
    c = c.cut(cyl_z(0, 0, T12 / 2, -TOP1 - 0.1, -TOP1 + SOCK))  # emmanchement du tube
    c = c.cut(box(-0.75, 0.75, -15, 15, -79, -66) if False else box(4, 14, -0.75, 0.75, -TOP1 - 1, -TOP1 + 16))  # fente
    c = c.cut(cyl_x(9, -70, M3 / 2, -2, 14).rotate((0, 0, 0), (0, 0, 1), 90).translate((0, 0, 0)) if False else cyl_y(9.5, -TOP1 + 6, M3 / 2, -14, 14))
    c = c.cut(servo_corner_holes_y(-OFF, zf, +1, -30, 30))
    c = c.cut(cyl_y(12, -TOP1 + 3, M3 / 2, -25, 25))           # axe d'ancrage
    return c

# ── 5. Languette du genou (bas de cuisse) ─────────────────────────────────────
def languette_genou():
    l = box(-10, 10, -10, 10, KZ, KZ + CLV).union(cyl_y(0, KZ, 10, -10, 10))
    l = l.cut(cyl_z(0, 0, T12 / 2, KZ + CLV - SOCK, KZ + CLV + 1)).cut(cyl_y(0, KZ, M5 / 2, -20, 20))
    l = l.cut(box(-0.75, 0.75, -11, 11, KZ + CLV - 14, KZ + CLV + 1)).cut(cyl_x(0, KZ + CLV - 6, M3 / 2, -12, 12))
    return l

# ── 6. Raccord haut de tibia : joues + came + levier du genou + berceau de S4 + 2 emmanchements
def raccord_tibia():
    joues = cyl_y(0, KZ, 20, 10.5, 18).union(cyl_y(0, KZ, 20, -18, -10.5))           # came r 20
    corps = box(-8.5, 8.5, -18, 18, KZ - TOP2, KZ - 12)
    # levier du genou (B1) : pont au-dessus de la zone de S4, plaque dans le plan de B1
    import math
    b0 = math.radians(55)                                    # jambe tendue : bras à 55° vers le bas/arrière
    lx, lz = -ARM * math.cos(b0), KZ - ARM * math.sin(b0)
    pont = box(-6, 6, 18, B1_Y + 2, KZ + 7, KZ + 15)         # au-dessus de l'écrou de la vis M5
    plaque = (cq.Workplane("XZ").polyline([(-6, KZ + 7), (6, KZ + 7), (lx + 5, lz - 3), (lx - 5, lz + 3)]).close()
              .extrude(-6).translate((0, B1_Y - 4, 0)))
    moyeu = cyl_y(lx, lz, 5, B1_Y - 4, B1_Y + 2)
    s4z = KZ - 35.0
    zf = s4z - (SL - S_END)
    cad = box(-OFF - SW / 2 - 3.5, -OFF + SW / 2 + 3.5, -SH / 2 - 3.5, SH / 2 + 3.5, zf - 3, s4z - 12)
    pont4 = box(-OFF, -15, -20, 20, zf - 3, KZ - 50)
    r = joues.union(corps).union(pont).union(plaque).union(moyeu).union(cad).union(pont4)
    r = r.cut(servo_pocket_vertical(-OFF, s4z))
    r = r.cut(servo_corner_holes_y(-OFF, zf, +1, -30, 30))
    r = r.cut(box(-21, 21, -10.6, 10.6, KZ - 21, KZ + 21))   # place de la languette entre les joues
    for ys in (1, -1):                                        # logements 625ZZ côté intérieur des joues
        r = r.cut(cyl_y(0, KZ, BRG_D / 2, ys * 10.5 if ys > 0 else -10.5 - BRG_W, (10.5 + BRG_W) if ys > 0 else -10.5))
    r = r.cut(cyl_y(0, KZ, M5 / 2, -25, 25))
    r = r.cut(cyl_y(lx, lz, INS / 2, B1_Y - 4.5, B1_Y + 2.5))  # insert M3 du levier
    for (g0, g1) in ((13.5, 15.0), (-15.0, -13.5)):            # gorge du câble Dyneema sur la came (r 20 → 18,5)
        r = r.cut(cyl_y(0, KZ, 21, g0, g1).cut(cyl_y(0, KZ, 18.5, g0 - 1, g1 + 1)))
    for yc in (14.25, -14.25):                                 # trou du câble + insert du tendeur M3
        r = r.cut(cyl_x(yc, KZ - 12, 1.0, 8, 22)).cut(cyl_y(15, KZ - 12, INS / 2, yc - 3.5, yc + 3.5))
    for ty in (-10, 10):                                       # emmanchements des 2 tubes Ø10
        r = r.cut(cyl_z(0, ty, T10 / 2, KZ - TOP2 - 0.1, KZ - TOP2 + SOCK))
    r = r.cut(cyl_y(-OFF, s4z, HORN_D / 2 + 1, -MP - 1, -HORN_FACE + 4))   # dégagement du palonnier intérieur de S4
    return r

# ── 7. Bas de tibia (languette de cheville) ───────────────────────────────────
def tibia_bas():
    t = box(-9, 9, -18.5, 18.5, AZ, AZ + CLV).union(cyl_y(0, AZ, 10, -18.5, 18.5))
    for ty in (-10, 10):
        t = t.cut(cyl_z(0, ty, T10 / 2, AZ + CLV - SOCK, AZ + CLV + 1))
    return t.cut(cyl_y(0, AZ, M5 / 2, -25, 25))

# ── 8. Pied évidé + joues de cheville + levier de talon ───────────────────────
def pied():
    talon, pointe, larg = FOOT
    sole = box(-talon, pointe, -larg / 2, larg / 2, GZ + 4, GZ + 8).edges("|Z").fillet(8)
    for (x0, x1) in ((-28, -12), (12, 30), (36, 56)):
        sole = sole.cut(box(x0, x1, -larg / 2 + 6, larg / 2 - 6, GZ + 3, GZ + 9).edges("|Z").fillet(3))
    joues = None
    for (y0, y1) in ((19, 25), (-25, -19)):
        j = box(-12, 12, y0, y1, GZ + 4, AZ).union(cyl_y(0, AZ, 12, y0, y1))
        joues = j if joues is None else joues.union(j)
    levier = box(-ARM - 5, -8, 25, B2_Y + 2, AZ - 5, AZ + 5).union(cyl_y(-ARM, AZ, 5, 25, B2_Y + 2))
    p = sole.union(joues).union(levier)
    p = p.cut(cyl_y(0, AZ, M5 / 2, -30, 30))
    p = p.cut(cyl_y(0, AZ, BRG_D / 2, 19, 19 + BRG_W)).cut(cyl_y(0, AZ, BRG_D / 2, -19 - BRG_W, -19))
    return p.cut(cyl_y(-ARM, AZ, INS / 2, 24, B2_Y + 3))

# ── 9. Bras de servo 22 mm et entretoises ─────────────────────────────────────
def bras_servo():
    import math
    b = (cq.Workplane("XZ").circle(10).extrude(-4)
         .union(cq.Workplane("XZ").polyline([(0, 6), (ARM, 4), (ARM, -4), (0, -6)]).close().extrude(-4))
         .union(cq.Workplane("XZ").center(ARM, 0).circle(5).extrude(-4)))
    b = b.cut(cq.Workplane("XZ").circle(M3 / 2).extrude(-5)).cut(cq.Workplane("XZ").center(ARM, 0).circle(M3 / 2).extrude(-5))
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        b = b.cut(cq.Workplane("XZ").center(HORN_PCD / 2 * math.cos(a), HORN_PCD / 2 * math.sin(a)).circle(HORN_HOLE / 2).extrude(-5))
    return b

def entretoise(h):
    import math
    e = cq.Workplane("XZ").circle(10).extrude(-h).cut(cq.Workplane("XZ").circle(M3 / 2).extrude(-h - 1))
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        e = e.cut(cq.Workplane("XZ").center(HORN_PCD / 2 * math.cos(a), HORN_PCD / 2 * math.sin(a)).circle(HORN_HOLE / 2).extrude(-h - 1))
    return e

# ── Tubes carbone (à couper) et pièces du commerce simplifiées ────────────────
import math
L_CUISSE = SEG - TOP1 - CLV + 2 * SOCK      # 130
L_TIBIA = SEG - TOP2 - CLV + 2 * SOCK       # 135
RE = 16.0                                   # centre de rotule → bout du tube de bielle
ROD_D, ROD_DI = 4.0, 2.0                    # tube de bielle (Ø5 × 3 conseillé si disponible)
B1_ROD, B2_ROD = B1_Y + 2 + 3, B2_Y + 2 + 3
ENT_S3, ENT_S4 = MP + 11.5 - HORN_FACE, MP + 3.5 - HORN_FACE   # 14,4 et 6,4   # plan des rotules : contre la face extérieure du bras/levier + rondelle

def tube(d_ext, d_int, L):
    return cyl_z(0, 0, d_ext / 2, -L, 0).cut(cyl_z(0, 0, d_int / 2, -L - 1, 1))

def roulement_625():
    return cyl_y(0, 0, 8, -2.5, 2.5).cut(cyl_y(0, 0, 2.5, -3, 3))

def vis_epaulee_m5(L):
    return cyl_y(0, 0, 2.5, -L / 2, L / 2).union(cyl_y(0, 0, 4, -L / 2 - 3, -L / 2))

def rotule_m3():
    """Rotule à œil M3 simplifiée : œil Ø9 × 5 (axe y) + corps vers +x."""
    return cyl_y(0, 0, 4.5, -2.5, 2.5).cut(cyl_y(0, 0, 1.5, -3, 3)).union(cyl_x(0, 0, 2.5, 3.5, RE - 1))

def bielle(p_a, p_b, y):
    dx, dz = p_b[0] - p_a[0], p_b[1] - p_a[1]
    L = math.hypot(dx, dz)
    ang = math.degrees(math.atan2(-dz, dx))
    t = cyl_x(0, 0, ROD_D / 2, RE, L - RE).cut(cyl_x(0, 0, ROD_DI / 2, RE - 1, L - RE + 1))
    b = t.union(rotule_m3()).union(rotule_m3().rotate((0, 0, 0), (0, 0, 1), 180).translate((L, 0, 0)))
    return b.rotate((0, 0, 0), (0, 1, 0), ang).translate((p_a[0], y, p_a[1])), L

def ressort(L=58.0, d=10.5):
    return cyl_z(0, 0, d / 2, -L, 0).cut(cyl_z(0, 0, d / 2 - 1.4, -L - 1, 1))

def place_bras(centre, cible, y_face):
    ang = math.degrees(math.atan2(-(cible[1] - centre[1]), cible[0] - centre[0]))
    b = bras_servo()
    b = b.translate((0, y_face - b.val().BoundingBox().ymin, 0))
    return b.rotate((0, 0, 0), (0, 1, 0), ang).translate((centre[0], 0, centre[1]))

def place_entretoise(h, centre, y_face):
    e = entretoise(h)
    return e.translate((centre[0], y_face - e.val().BoundingBox().ymin, centre[1]))

# ── Maquettes (non imprimées) pour l'assemblage ───────────────────────────────
def servo_maquette(axis, center, shaft_end_dir, body_dir):
    """Boîtier STS3215 simplifié. axis : 'x' ou 'y' (axe de l'arbre)."""
    cx, cy, cz = center
    if axis == "y":
        h = cyl_y(cx, cz, HORN_D / 2, cy + 14.5, cy + HORN_FACE).union(cyl_y(cx, cz, HORN_D / 2, cy - HORN_FACE, cy - 14.5))
        if body_dir == "-x":
            return box(cx - (SL - S_END), cx + S_END, cy - SH / 2, cy + SH / 2, cz - SW / 2, cz + SW / 2).union(h)
        return box(cx - SW / 2, cx + SW / 2, cy - SH / 2, cy + SH / 2, cz - (SL - S_END), cz + S_END).union(h)
    h = cyl_x(cy, cz, HORN_D / 2, cx + 14.5, cx + HORN_FACE).union(cyl_x(cy, cz, HORN_D / 2, cx - HORN_FACE, cx - 14.5))
    return box(cx - SH / 2, cx + SH / 2, cy - S_END, cy + SL - S_END, cz - SW / 2, cz + SW / 2).union(h)

def composants_jambe():
    """Tous les composants d'une jambe droite (repère de jambe), hors plaque de bassin : {nom: (forme, couleur)}."""
    pla, srv, carb = cq.Color(0.85, 0.88, 0.86), cq.Color(0.2, 0.37, 0.55), cq.Color(0.15, 0.15, 0.15)
    acier, orange, vert = cq.Color(0.62, 0.62, 0.65), cq.Color(0.72, 0.42, 0.06), cq.Color(0.17, 0.53, 0.34)
    c = {}
    for n, fn in PIECES.items():
        if n[:2] in ("01", "09", "10", "11"):
            continue
        c[n[3:]] = (fn(), pla)
    c["S1"] = (servo_maquette("x", (0, 0, S1_Z), None, None), srv)
    c["S2"] = (servo_maquette("y", (0, 0, 0), None, "-x"), srv)
    c["S3"] = (servo_maquette("y", (-OFF, 0, -40), None, "-z"), srv)
    c["S4"] = (servo_maquette("y", (-OFF, 0, KZ - 35), None, "-z"), srv)
    c["tube_cuisse"] = (tube(12, 10, L_CUISSE).translate((0, 0, -TOP1 + SOCK)), carb)
    for ty in (-10, 10):
        c[f"tube_tibia_{'int' if ty < 0 else 'ext'}"] = (tube(10, 8, L_TIBIA).translate((0, ty, KZ - TOP2 + SOCK)), carb)
    b0 = math.radians(55)
    pin_s3 = (-OFF - ARM * math.cos(b0), -40 - ARM * math.sin(b0))
    pin_genou = (-ARM * math.cos(b0), KZ - ARM * math.sin(b0))
    pin_s4, pin_talon = (-OFF - ARM, KZ - 35), (-ARM, AZ)
    c["bielle_B1"] = (bielle(pin_s3, pin_genou, B1_ROD)[0], orange)
    c["bielle_B2"] = (bielle(pin_s4, pin_talon, B2_ROD)[0], orange)
    c["entretoise_S3"] = (place_entretoise(ENT_S3, (-OFF, -40), HORN_FACE), pla)
    c["bras_S3"] = (place_bras((-OFF, -40), pin_s3, HORN_FACE + ENT_S3), pla)
    c["entretoise_S4"] = (place_entretoise(ENT_S4, (-OFF, KZ - 35), HORN_FACE), pla)
    c["bras_S4"] = (place_bras((-OFF, KZ - 35), pin_s4, HORN_FACE + ENT_S4), pla)
    for n, (y, z) in {"625_genou_ext": (13.0, KZ), "625_genou_int": (-13.0, KZ),
                      "625_cheville_ext": (21.5, AZ), "625_cheville_int": (-21.5, AZ)}.items():
        c[n] = (roulement_625().translate((0, y, z)), acier)
    c["vis_M5_genou"] = (vis_epaulee_m5(40).translate((0, 0, KZ)), acier)
    c["vis_M5_cheville"] = (vis_epaulee_m5(56).translate((0, 0, AZ)), acier)
    for ys in (14.5, -14.5):
        c[f"ressort_{'ext' if ys > 0 else 'int'}"] = (ressort().translate((12, ys, -TOP1 - 1)), vert)
    return c, (pin_s3, pin_genou, pin_s4, pin_talon)

PIECES = {
    "01_plaque_bassin": plaque_bassin,
    "02_berceau_S1": berceau_s1,
    "03_etrier_roulis_berceau_S2": etrier_roulis,
    "04_chape_cuisse_berceau_S3": chape_cuisse,
    "05_languette_genou": languette_genou,
    "06_raccord_tibia_berceau_S4": raccord_tibia,
    "07_tibia_bas": tibia_bas,
    "08_pied": pied,
    "09_bras_servo_22": bras_servo,
    "10_entretoise_S3_14_4": lambda: entretoise(ENT_S3),
    "11_entretoise_S4_6_4": lambda: entretoise(ENT_S4),
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "step"), exist_ok=True)
    os.makedirs(os.path.join(here, "stl"), exist_ok=True)
    built = {}
    for name, fn in PIECES.items():
        shape = fn()
        built[name] = shape
        cq.exporters.export(shape, os.path.join(here, "step", name + ".step"))
        cq.exporters.export(shape, os.path.join(here, "stl", name + ".stl"), tolerance=0.05, angularTolerance=0.1)
        bb = shape.val().BoundingBox()
        print(f"{name:32s} {bb.xlen:6.1f} × {bb.ylen:6.1f} × {bb.zlen:6.1f} mm   volume {shape.val().Volume()/1000:6.1f} cm³")
    comp, pins = composants_jambe()
    L1 = math.hypot(pins[1][0] - pins[0][0], pins[1][1] - pins[0][1])
    L2 = math.hypot(pins[3][0] - pins[2][0], pins[3][1] - pins[2][1])
    a_couper = {f"12_tube_cuisse_12x10_L{L_CUISSE:.0f}": tube(12, 10, L_CUISSE),
                f"13_tube_tibia_10x8_L{L_TIBIA:.0f}_x2": tube(10, 8, L_TIBIA),
                f"14_tube_bielle_B1_{ROD_D:.0f}x{ROD_DI:.0f}_L{L1 - 2 * RE:.0f}": tube(ROD_D, ROD_DI, L1 - 2 * RE),
                f"15_tube_bielle_B2_{ROD_D:.0f}x{ROD_DI:.0f}_L{L2 - 2 * RE:.0f}": tube(ROD_D, ROD_DI, L2 - 2 * RE)}
    for name, shape in a_couper.items():
        cq.exporters.export(shape, os.path.join(here, "step", name + ".step"))
        print(f"{name:32s} (tube à couper)")
    print(f"Bielles : B1 entraxe {L1:.1f}, B2 entraxe {L2:.1f}")
    pla = cq.Color(0.85, 0.88, 0.86)
    asm = cq.Assembly(name="jambe_droite_tendue")
    asm.add(built["01_plaque_bassin"].translate((0, -45, 0)), name="plaque_bassin", color=pla)
    for n, (sh, col) in comp.items():
        asm.add(sh, name=n, color=col)
    asm.save(os.path.join(here, "step", "assemblage_jambe.step"))
    # deux jambes : y robot vers la gauche ; jambe gauche = repère de jambe décalé de +45,
    # jambe droite = symétrie par rapport au plan xz puis décalage de -45
    asm2 = cq.Assembly(name="LEO-S_jambes")
    asm2.add(built["01_plaque_bassin"], name="plaque_bassin", color=pla)
    for n, (sh, col) in comp.items():
        asm2.add(sh.translate((0, 45, 0)), name="G_" + n, color=col)
        asm2.add(sh.mirror("XZ").translate((0, -45, 0)), name="D_" + n, color=col)
    asm2.save(os.path.join(here, "step", "assemblage_deux_jambes.step"))
    print("Assemblages : step/assemblage_jambe.step, step/assemblage_deux_jambes.step")
