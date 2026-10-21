"""
jambe_cad.py — CAO paramétrique des pièces imprimées d'une jambe LEO-S (Rév. I : servo réel STS3215_c.step, câblage du bus intégré, visserie, buste estimé), en CadQuery.

  python jambe_cad.py            → STEP + STL de chaque pièce dans ./step et ./stl, assemblage dans ./step/assemblage_jambe.step

Repère d'une jambe (jambe droite, tendue) : x vers l'avant, y vers l'extérieur, z vers le haut,
origine sur l'axe de tangage de hanche (S2). La jambe gauche = symétrie par rapport au plan xz.
Toutes les cotes sont en mm et viennent du plan docs/jambe_leo_s.html.
À VÉRIFIER avant impression : cotes du STS3215 (relevées sur un modèle 3D), motif de trous du palonnier.
"""
import math
import os
import cadquery as cq

# ── Paramètres ────────────────────────────────────────────────────────────────
SEG = 200.0                 # cuisse = tibia (entraxes)
SL, SW, SH = 45.22, 24.72, 36.0  # STS3215 : longueur, largeur, enveloppe en épaisseur (plots -17,9 / étiquette +17,3 sur STS3215_c.step)
S_END = 10.11               # arbre → bout du boîtier
S_HOLE_X, S_HOLE_Y = 2.36, 10.25  # vis de boîtier : 2,36 du bout opposé à l'arbre (18,41 + 24,45 côté arbre), ±10,25
HORN_T = 4.0                # plan d'appui des pièces sur palonnier : MP = 21,5 de l'axe du servo
JEU = 0.2                   # jeu d'impression par côté
BRG_D, BRG_W = 16.15, 5.0   # logement 625ZZ
M5, M3, M2, INS = 5.2, 3.3, 2.3, 4.0   # passages et insert M3
T12, T10, SOCK = 12.2, 10.2, 20.0      # emmanchements tubes
B1_Y, B2_Y = 35.0, 27.0     # plans des bielles (vers l'extérieur)
ARM = 22.0                  # bras / leviers
ARM_T = 6.0                 # épaisseur des bras de servo (4 → 6 : 9 MPa au blocage)
OFF = 25.0                  # S3 et S4 en arrière de l'axe des tubes
S1_Z = 63.5                 # axe de roulis au-dessus de l'axe de tangage
FOOT = (35.0, 65.0, 65.0)   # talon, pointe, largeur
KZ, AZ, GZ = -SEG, -2 * SEG, -2 * SEG - 50.0
TOP1, CLV, TOP2 = 75.0, 35.0, 70.0   # raccord haut de cuisse, languettes (axe → bout), raccord haut de tibia
# palonnier : motif de trous à mesurer sur ton palonnier aluminium (valeurs provisoires)
HORN_PCD, HORN_N, HORN_HOLE = 14.0, 4, 3.3   # palonnier alu Ø19,2 : 4 trous en croix sur Ø14 (filetage à vérifier : M3 ou M2,5)
HORN_A0 = 0.0                # trous en croix (0°, 90°, 180°, 270°)
HORN_D = 19.2                # palonniers alu des DEUX côtés (double sortie), mesurés sur STS3215_c.step :
HORN_FACE_O = 19.2           #   côté opposé aux connecteurs : palonnier en saillie, face à 19,2 de l'axe
HORN_FACE_C = 18.05          #   côté connecteurs : palonnier presque affleurant, face à 18,05
HORN_BACK = 14.7             #   dos des deux palonniers (fond des taraudages)
LAMAGE_R, LAMAGE_Y = 4.2, 22.3   # lamage pour les têtes des vis centrales des palonniers (r 2,8 → 21,55 / r 3,75 → 20,89)
CONN_X, CONN_Z, CONN_FACE = 14.0, 4.98, 17.6   # 2 connecteurs Molex Spox 3 br. encastrés : à 14 de l'arbre, ±4,98 en travers,
                                               # fils sortant de la face côté connecteurs (-y du servo) à 17,6 de l'axe
MP = 35.0 / 2 + 4.0          # plan d'appui = 21,5 ; un bossage Ø19,2 comble l'écart avec le palonnier
SERVO_STEP = "STS3215_c.step"   # modèle 3D du servo (fourni), à côté de ce script
CABLE_R = 1.3                # câble servo 3 fils (bus) modélisé Ø2,6

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

def fenetre_connecteurs(cx, zc):
    """Fenêtre dans la paroi -y d'un berceau vertical (S3, S4) devant les 2 connecteurs : on branche les fiches
    et les fils sortent à plat ; la paroi reste fermée sous la fenêtre."""
    return box(cx - 11.5, cx + 11.5, -SH / 2 - 6, -SH / 2 + 0.5, zc - CONN_X - 6, zc - CONN_X + 5).edges("|Y").fillet(2)

def passe_cable(x, y, z0, z1, xs, ys):
    """Passe-câble imprimé dans la pièce : bloc arrondi, percé plus tard d'un trou Ø3,8 d'axe z en (x, y)."""
    return box(xs[0], xs[1], ys[0], ys[1], z0, z1).edges("|Z").fillet(1.5)

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
        y0, y1 = sorted((yl + s_ * 9.5, yl + s_ * 18.5))
        p = p.cut(box(-22.5, -15.5, y0, y1, z0 - 1, z0 + 7).edges("|Z").fillet(2.5))       # passage du câble du bus
        for (hx, hy) in TOF_VIS:                                                       # vis des supports de ToF bas
            p = p.cut(cyl_z(hx, s_ * hy, M3 / 2, z0 - 1, z0 + 7))
    return p

# ── 17. Support d'un ToF bas (VL53L8CX) sous l'avant du bassin ────────────────
# Navigation : 2 ToF multizones fixés au corps regardent le sol et les obstacles bas devant les pieds,
# indépendamment de la tête. Repère robot, côté gauche (y > 0) ; le droit est son symétrique (plan xz).
TOF_P0 = (52.0, 30.0)        # centre de la face du capteur (x, y), à mi-hauteur du support
TOF_PITCH, TOF_YAW = 37.0, 20.0   # plongée sous l'horizontale, ouverture vers l'extérieur (champ 45° × 45°)
TOF_PCB = (19.0, 27.0)       # logement de la carte (largeur, hauteur) : à ajuster sur la carte reçue
TOF_VIS = ((42.0, 26.0), (42.0, 34.0))

def place_tof(w):
    """Repère local du capteur (x = axe de visée, face en x = 0) → repère robot."""
    zb = S1_Z + SW / 2 + 0.15
    return (w.rotate((0, 0, 0), (0, 1, 0), TOF_PITCH).rotate((0, 0, 0), (0, 0, 1), TOF_YAW)
            .translate((TOF_P0[0], TOF_P0[1], zb - 11)))

def support_tof():
    zb = S1_Z + SW / 2 + 0.15                                   # dessous de la plaque de bassin
    s_ = box(36, 58, 20, 40, zb - 22, zb).edges("|Z").fillet(2)
    s_ = s_.cut(place_tof(box(0, 100, -60, 60, -60, 60)))       # face avant inclinée et tournée
    w, h = TOF_PCB
    s_ = s_.cut(place_tof(box(-2.2, 1, -w / 2, w / 2, -h / 2, h / 2)))      # logement de la carte
    s_ = s_.cut(place_tof(box(-2.2, 1, -3, 3, h / 2 - 1, h / 2 + 12)))      # sortie des fils vers le haut
    for (hx, hy) in TOF_VIS:
        s_ = s_.cut(cyl_z(hx, hy, INS / 2, zb - 8, zb + 0.1))              # inserts M3
    return cq.Workplane().add(max(s_.solids().vals(), key=lambda v: v.Volume()))   # sans l'éclat laissé en haut par la sortie des fils

# ── 2. Berceau de S1 (fixe) ───────────────────────────────────────────────────
def berceau_s1():
    """Joues entre S1 et les plaques de l'étrier, fond sous S1 hors de la zone balayée par l'étrier, bloc de vissage."""
    y_far = SL - S_END
    z0, z1 = S1_Z - SW / 2, S1_Z + SW / 2
    top = z1 + 0.15
    xa, xb = SH / 2 + JEU, MP - 0.2
    joue_av = box(xa, xb, 13, y_far + 1, z0 - 4, top)
    joue_ar = box(-xb, -xa, 13, y_far + 1, z0 - 4, top)
    fond = box(-xb, xb, 24, y_far + 1, z0 - 4, z0 - JEU)                 # fond sous S1 (y ≥ 24 : hors du balayage de l'étrier)
    bloc = box(-xb, xb, y_far + JEU, y_far + 12, z0 - 4, top)
    b = joue_av.union(joue_ar).union(fond).union(bloc)
    for dz in (-S_HOLE_Y, S_HOLE_Y):
        b = b.cut(cyl_x(y_far - S_HOLE_X, S1_Z + dz, M2 / 2, -30, 30))
    for x in (-12, 12):                                       # inserts M3 sous la plaque
        b = b.cut(cyl_z(x, 40, INS / 2, top - 6, top + 1))
    b = b.cut(box(-12, 12, y_far + 3, y_far + 9, z0 - 5, top - 8))      # allègement du bloc
    return b.cut(box(-22, -17, 9.5, 19, z0 - 6, top + 1))               # fenêtre des connecteurs + passage du câble vers le bassin

# ── 3. Étrier de roulis + berceau de S2 ───────────────────────────────────────
def etrier_roulis():
    def plaque(x0, x1, trou):
        prof = (cq.Workplane("YZ").moveTo(-11, S1_Z).threePointArc((0, S1_Z + 11), (11, S1_Z))
                .lineTo(11, 30).lineTo(30, 23.5).lineTo(30, 17.5).lineTo(-30, 17.5).lineTo(-30, 23.5)
                .lineTo(-11, 30).close().extrude(x1 - x0).translate((x0, 0, 0)))
        return prof.cut(cyl_x(0, S1_Z, trou / 2, x0 - 1, x1 + 1))
    av = plaque(MP, MP + 6, M3).union(cyl_x(0, S1_Z, HORN_D / 2, HORN_FACE_O, MP))      # S1 : connecteurs vers l'arrière
    ar = plaque(-MP - 6, -MP, M3).union(cyl_x(0, S1_Z, HORN_D / 2, -MP, -HORN_FACE_C))
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        hy, hz = HORN_PCD / 2 * math.cos(a), S1_Z + HORN_PCD / 2 * math.sin(a)
        av = av.cut(cyl_x(hy, hz, HORN_HOLE / 2, 0, 40))
        ar = ar.cut(cyl_x(hy, hz, HORN_HOLE / 2, -40, 0))
    av, ar = av.cut(cyl_x(0, S1_Z, LAMAGE_R, 17, LAMAGE_Y)), ar.cut(cyl_x(0, S1_Z, LAMAGE_R, -LAMAGE_Y, -17))
    plancher = box(-38, MP + 6, -30, 30, 17.5, 23.5)
    # goussets plaques ↔ plancher (dans le plan du col, ±11), pour reprendre le moment de la jambe en roulis
    gous = None
    for (x0, x1) in ((MP - 5, MP), (-MP, -MP + 5)):
        for ys in (-1, 1):
            g = (cq.Workplane("YZ").polyline([(ys * 11, 23.5), (ys * 11, 34), (ys * 24, 23.5)]).close()
                 .extrude(x1 - x0).translate((x0, 0, 0)))
            gous = g if gous is None else gous.union(g)
    # berceau de S2 : joues 5,5 mm, fond, nervure sous le plancher
    x_far = -(SL - S_END)
    joues = (box(x_far - 4, -18, SH / 2 + JEU, SH / 2 + 5.5, -SW / 2 - 2, 17.5)
             .union(box(x_far - 4, -18, -SH / 2 - 5.5, -SH / 2 - JEU, -SW / 2 - 2, 17.5))
             .union(box(x_far - 4, x_far - JEU, -SH / 2 - 5.5, SH / 2 + 5.5, -SW / 2 - 2, 17.5)))
    e = av.union(ar).union(plancher).union(gous).union(joues)
    for dz in (-S_HOLE_Y, S_HOLE_Y):
        e = e.cut(cyl_y(x_far + S_HOLE_X, dz, M2 / 2, -30, 30))
    e = e.cut(box(-12, 10, -8, 8, 16, 25).edges("|Z").fillet(3))       # allègement réduit (le plancher porte S2)
    e = e.cut(box(-17.5, -10.5, -21, -12.5, 16, 25).edges("|Z").fillet(2.5))   # passage du câble S1 → S2
    s3 = box(-OFF - SW / 2 - 1, -OFF + SW / 2 + 1, -SH / 2 - 1, SH / 2 + 1, -40 - (SL - S_END), -40 + S_END + 1)
    ch = chape_cuisse()
    for a in (-15, -20, -25, -30, -35):
        e = e.cut(s3.rotate((0, 0, 0), (0, 1, 0), -a)).cut(ch.rotate((0, 0, 0), (0, 1, 0), -a))
    return e

# ── 4. Chape de cuisse + raccord haut + berceau de S3 + patte d'ancrage des ressorts
def chape_cuisse():
    bras_ext = box(-12, 12, MP, MP + 5, -31, 0).union(cyl_y(0, 0, 12, MP, MP + 5))
    bras_int = box(-12, 12, -MP - 5, -MP, -31, 0).union(cyl_y(0, 0, 12, -MP - 5, -MP))
    bossages = cyl_y(0, 0, HORN_D / 2, HORN_FACE_O, MP).union(cyl_y(0, 0, HORN_D / 2, -MP, -HORN_FACE_C))   # S2 : connecteurs vers -y
    traverse = box(-12, 12, -MP - 5, MP + 5, -37, -31)
    gous = None
    for ys in (1, -1):                                         # goussets bras ↔ traverse (le coin le plus chargé)
        y0, y1 = (MP - 6, MP) if ys > 0 else (-MP, -MP + 6)
        g = cq.Workplane("XZ").polyline([(12, -31), (12, -25), (6, -31)]).close().extrude(-(y1 - y0)).translate((0, y0, 0))
        if ys > 0:                                             # côté intérieur : pas de gousset arrière, la boucle du câble S2 → S3 y passe
            g = g.union(cq.Workplane("XZ").polyline([(-12, -31), (-12, -25), (-6, -31)]).close().extrude(-(y1 - y0)).translate((0, y0, 0)))
        gous = g if gous is None else gous.union(g)
    corps = box(-12, 9, -12, 12, -TOP1, -31)                   # autour du tube Ø12
    # berceau de S3 : arbre en (x=-OFF, z=-40), boîtier vertical vers le bas
    s3z = -40.0
    zf = s3z - (SL - S_END)                                    # bout opposé à l'arbre
    cad = box(-OFF - SW / 2 - 3.5, -OFF + SW / 2 + 3.5, -SH / 2 - 3.5, SH / 2 + 3.5, zf - 3, s3z - 12).edges("|Z").fillet(3)
    pont = box(-OFF, -6, -12, 12, -TOP1, -50)
    patte = box(6, 18, -20, 20, -TOP1, -TOP1 + 6)               # ancrage des ressorts (axe M3 d'axe y)
    guide = passe_cable(-30, -24, -76, -68, (-33.5, -26.5), (-27.5, -20.6))   # câble S3 → S4 le long du berceau
    c = bras_ext.union(bras_int).union(bossages).union(traverse).union(gous).union(corps).union(cad).union(pont).union(patte).union(guide)
    c = c.cut(servo_pocket_vertical(-OFF, s3z))
    c = c.cut(cyl_y(-OFF, s3z, HORN_D / 2 + 1, -MP - 1, -HORN_FACE_C + 4))   # dégagement du palonnier intérieur de S3
    c = c.cut(cyl_y(0, 0, LAMAGE_R, 17, LAMAGE_Y)).cut(cyl_y(0, 0, LAMAGE_R, -LAMAGE_Y, -17))   # têtes des vis centrales de S2
    c = c.cut(fenetre_connecteurs(-OFF, s3z))
    c = c.cut(cyl_z(-30, -24, 1.9, -80, -60))                    # trou du passe-câble
    import math
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        c = c.cut(cyl_y(HORN_PCD / 2 * math.cos(a), HORN_PCD / 2 * math.sin(a), HORN_HOLE / 2, -40, 40))
    c = c.cut(cyl_z(0, 0, T12 / 2, -TOP1 - 0.1, -TOP1 + SOCK))  # emmanchement du tube
    c = c.cut(box(-0.75, 0.75, -15, 15, -79, -66) if False else box(4, 14, -0.75, 0.75, -TOP1 - 1, -TOP1 + 16))  # fente
    c = c.cut(cyl_x(9, -70, M3 / 2, -2, 14).rotate((0, 0, 0), (0, 0, 1), 90).translate((0, 0, 0)) if False else cyl_y(9.5, -TOP1 + 12, M3 / 2, -14, 14))
    c = c.cut(servo_corner_holes_y(-OFF, zf, +1, -30, 30))
    c = c.cut(cyl_y(12, -TOP1 + 3, M3 / 2, -25, 25))           # axe d'ancrage
    return c

# ── 5. Languette du genou (bas de cuisse) ─────────────────────────────────────
def languette_genou():
    l = box(-10, 10, -10, 10, KZ, KZ + CLV).union(cyl_y(0, KZ, 10, -10, 10))
    l = l.union(passe_cable(-2, -27, KZ + 28, KZ + 34, (-6, 2), (-30, -9.5)))   # câble qui passe le genou au ras de l'axe
    l = l.cut(cyl_z(-2, -27, 1.9, KZ + 20, KZ + 40))
    l = l.cut(cyl_z(0, 0, T12 / 2, KZ + CLV - SOCK, KZ + CLV + 1)).cut(cyl_y(0, KZ, M5 / 2, -20, 20))
    l = l.cut(box(-0.75, 0.75, -11, 11, KZ + CLV - 14, KZ + CLV + 1)).cut(cyl_x(0, KZ + CLV - 6, M3 / 2, -12, 12))
    return l

# ── 6. Raccord haut de tibia : joues + came + levier du genou + berceau de S4 + 2 emmanchements
def raccord_tibia():
    joues = cyl_y(0, KZ, 20, 10.5, 18).union(cyl_y(0, KZ, 20, -18, -10.5))           # came r 20
    corps = box(-8.5, 8.5, -18, 18, KZ - TOP2, KZ - 12)
    b0 = math.radians(55)
    lx, lz = -ARM * math.cos(b0), KZ - ARM * math.sin(b0)
    pont = box(-7, 7, 16, B1_Y + 2, KZ + 7, KZ + 19)          # 14 × 12 (8 MPa au blocage), au-dessus de l'écrou M5
    gous = (cq.Workplane("XZ").polyline([(7, KZ + 7), (15, KZ + 7), (15, KZ - 3)]).close().extrude(-(B1_Y - 4 - 18)).translate((0, 18, 0)))
    # levier : arc de 8 mm autour de l'axe (laisse passer la vis M5 et la clé), du pont jusqu'au moyeu,
    # plus une colonne qui ramène le moyeu sur la joue : cadre fermé joue / pont / arc / colonne
    def pol(r, a):
        return (r * math.cos(math.radians(a)), KZ + r * math.sin(math.radians(a)))
    a0, a1 = 70.0, 180.0 + 55.0
    plaque = (cq.Workplane("XZ").moveTo(*pol(10, a0)).lineTo(*pol(21, a0)).threePointArc(pol(21, (a0 + a1) / 2), pol(21, a1))
              .lineTo(*pol(10, a1)).threePointArc(pol(10, (a0 + a1) / 2), pol(10, a0)).close()
              .extrude(-8).translate((0, B1_Y - 6, 0)))
    moyeu = cyl_y(lx, lz, 6.5, 15.5, B1_Y + 2)                     # colonne jusqu'à la joue (hors gorge du câble)
    s4z = KZ - 35.0
    zf = s4z - (SL - S_END)
    cad = box(-OFF - SW / 2 - 3.5, -OFF + SW / 2 + 3.5, -SH / 2 - 3.5, SH / 2 + 3.5, zf - 3, s4z - 12).edges("|Z").fillet(3)
    nerv = box(-OFF + SW / 2, -8, -3, 3, zf - 3, KZ - 50).union(box(-OFF + SW / 2, -8, -18, 18, zf - 3, zf + 2))   # nervures au lieu du bloc plein
    guide = passe_cable(-6, -27, KZ - 24, KZ - 16, (-10, -2), (-30, -17.5))
    # pion coaxial au genou : le câble s'enroule dessus (longueur quasi constante), joue extérieure + bras vers le passe-câble
    guide = (guide.union(cyl_y(0, KZ, 2.5, -28.5, -23.2)).union(cyl_y(0, KZ, 6, -30, -28.5))
             .union(box(-4, 2, -30, -28.5, KZ - 20, KZ)))
    r = joues.union(corps).union(pont).union(gous).union(plaque).union(moyeu).union(cad).union(nerv).union(guide)
    r = r.cut(servo_pocket_vertical(-OFF, s4z))
    r = r.cut(servo_corner_holes_y(-OFF, zf, +1, -30, 30))
    r = r.cut(box(-21, 21, -10.6, 10.6, KZ - 21, KZ + 21))
    for ys in (1, -1):
        r = r.cut(cyl_y(0, KZ, BRG_D / 2, 10.5 if ys > 0 else -10.5 - BRG_W, (10.5 + BRG_W) if ys > 0 else -10.5))
    r = r.cut(cyl_y(0, KZ, M5 / 2, -25, 25))
    r = r.cut(cyl_y(lx, lz, INS / 2, 24, B1_Y + 2.5))
    for (g0, g1) in ((13.5, 15.0), (-15.0, -13.5)):
        r = r.cut(cyl_y(0, KZ, 21, g0, g1).cut(cyl_y(0, KZ, 18.5, g0 - 1, g1 + 1)))
    for yc in (14.25, -14.25):
        r = r.cut(cyl_x(yc, KZ - 12, 1.0, 8, 22)).cut(cyl_y(15, KZ - 12, INS / 2, yc - 4, yc + 4))
    for ty in (-10, 10):
        r = r.cut(cyl_z(0, ty, T10 / 2, KZ - TOP2 - 0.1, KZ - TOP2 + SOCK))
    r = r.cut(cyl_y(0, KZ - TOP2 + 8, M3 / 2, -25, 25))                # goupille M3 à travers les deux tubes
    r = r.cut(box(-4, 4, -3, 3, KZ - TOP2 + 22, KZ - 22))              # allègement entre les tubes
    r = r.cut(cyl_y(-OFF, s4z, HORN_D / 2 + 1, -MP - 1, -HORN_FACE_C + 4))
    r = r.cut(fenetre_connecteurs(-OFF, s4z))
    return r.cut(cyl_z(-6, -27, 1.9, KZ - 30, KZ - 10))

# ── 7. Bas de tibia (languette de cheville) ───────────────────────────────────
def tibia_bas():
    t = box(-8, 8, -18.5, 18.5, AZ, AZ + CLV).union(cyl_y(0, AZ, 10, -18.5, 18.5))
    for ty in (-10, 10):
        t = t.cut(cyl_z(0, ty, T10 / 2, AZ + CLV - SOCK, AZ + CLV + 1))
    t = t.cut(cyl_y(0, AZ + CLV - 8, M3 / 2, -25, 25))                   # goupille M3 à travers les deux tubes
    t = t.cut(box(-9, 9, -3.5, 3.5, AZ + 13, AZ + CLV - 12))              # allègement entre les tubes (sous la goupille)
    return t.cut(cyl_y(0, AZ, M5 / 2, -25, 25))

# ── 8. Pied : semelle nervurée (dessous plein pour le collage), joues en A, levier de talon intégré
def profil_tangent(c, r, p_g, p_d, z_bas):
    """Contour XZ : base [p_g, p_d] à z_bas, flancs tangents au cercle (c, r) qui coiffe le haut."""
    def tangente(p, cote):
        dx, dz = p[0] - c[0], p[1] - c[1]
        d = math.hypot(dx, dz)
        a = math.atan2(dz, dx) + cote * math.acos(r / d)
        return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
    tg, td = tangente(p_g, -1), tangente(p_d, +1)
    return (cq.Workplane("XZ").moveTo(p_g[0], z_bas).lineTo(p_d[0], z_bas).lineTo(*td)
            .threePointArc((c[0], c[1] + r), tg).close())

def pied():
    talon, pointe, larg = FOOT
    z0, peau, z1 = GZ + 4, GZ + 6.5, GZ + 10                             # plaque 6 mm, peau 2,5 mm sous les poches
    p = box(-talon, pointe, -larg / 2, larg / 2, z0, z1).edges("|Z").fillet(10)
    for (x0, x1) in ((-31, -14), (14, 36), (40, 61)):                  # poches par le dessus : le dessous reste plein
        for (y0, y1) in ((3, larg / 2 - 4), (-larg / 2 + 4, -3)):
            p = p.cut(box(x0, x1, y0, y1, peau, z1 + 1).edges("|Z").fillet(3))
    for (y0, y1) in ((19, 25), (-25, -19)):                             # joues en A, tangentes au moyeu r 12
        j = profil_tangent((0, AZ), 12, (-28, peau), (28, peau), peau).extrude(-(y1 - y0)).translate((0, y0, 0))
        j = j.cut(cyl_y(0, GZ + 24, 7, y0 - 1, y1 + 1))                 # allègement
        p = p.union(j)
    p = p.union(box(-12, 12, -25, 25, peau, GZ + 14).edges("|Y").fillet(3))   # traverse sous la cheville
    # levier de talon collé à toute la face extérieure de la joue (+y), œil r 6,5 en (-ARM, AZ)
    lev = (cq.Workplane("XZ").moveTo(0, AZ + 12).lineTo(-ARM, AZ + 6.5).threePointArc((-ARM - 6.5, AZ), (-ARM, AZ - 6.5))
           .lineTo(0, AZ - 12).threePointArc((12, AZ), (0, AZ + 12)).close().extrude(-(B2_Y + 2 - 24)).translate((0, 24, 0)))   # 1 mm noyé dans la joue
    p = p.union(lev)
    p = p.cut(cyl_y(0, AZ, 6.5, 25, B2_Y + 3))                           # lamage de l'écrou M5 dans le levier
    p = p.cut(cyl_y(0, AZ, BRG_D / 2, 19, 19 + BRG_W)).cut(cyl_y(0, AZ, BRG_D / 2, -19 - BRG_W, -19))
    p = p.cut(cyl_y(0, AZ, M5 / 2, -30, 30))
    return p.cut(cyl_y(-ARM, AZ, INS / 2, 18, B2_Y + 3))

FSR = ((-24, 0), (8, 0), (52, 17), (52, -17))           # 4 capteurs de force FSR 402 (Ø18 actif)

def semelle_tpu():
    """Semelle TPU 95A, 4 mm, collée sous le pied : poches pour 4 FSR sur le dessus, rainures sous la semelle."""
    talon, pointe, larg = FOOT
    s_ = box(-talon, pointe, -larg / 2, larg / 2, GZ, GZ + 4).edges("|Z").fillet(8)
    s_ = s_.edges(">Z or <Z").chamfer(0.6)
    for (fx, fy) in FSR:
        s_ = s_.cut(cyl_z(fx, fy, 9.6, GZ + 3.2, GZ + 4.1))                 # poche FSR, 0,8 mm
        s_ = s_.cut(box(fx - 1, fx + 1, fy, larg / 2 + 1, GZ + 3.2, GZ + 4.1) if fy >= 0 else box(fx - 1, fx + 1, -larg / 2 - 1, fy, GZ + 3.2, GZ + 4.1))  # passage de la queue
    for i in range(-4, 13):                                              # rainures 1 mm sous la semelle
        x = i * 7.5
        if -talon + 4 < x < pointe - 4:
            s_ = s_.cut(box(x - 1, x + 1, -larg / 2 + 5, larg / 2 - 5, GZ - 0.1, GZ + 1))
    return s_

# ── 9. Bras de servo 22 mm et entretoises ─────────────────────────────────────
def bras_servo():
    t = ARM_T
    b = (cq.Workplane("XZ").circle(10).extrude(-t)
         .union(cq.Workplane("XZ").polyline([(0, 7), (ARM, 5), (ARM, -5), (0, -7)]).close().extrude(-t))
         .union(cq.Workplane("XZ").center(ARM, 0).circle(5.5).extrude(-t)))
    b = b.cut(cq.Workplane("XZ").circle(M3 / 2).extrude(-t - 1)).cut(cq.Workplane("XZ").center(ARM, 0).circle(INS / 2).extrude(-t - 1))
    for i in range(HORN_N):
        a = 2 * math.pi * i / HORN_N + HORN_A0
        b = b.cut(cq.Workplane("XZ").center(HORN_PCD / 2 * math.cos(a), HORN_PCD / 2 * math.sin(a)).circle(HORN_HOLE / 2).extrude(-t - 1))
    return b


def entretoise(h):
    e = cq.Workplane("XZ").circle(10).extrude(-h).cut(cq.Workplane("XZ").circle(3.3).extrude(-h - 1))   # tête de la vis centrale
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
ENT_S3, ENT_S4 = MP + 11.5 + 4 - ARM_T - HORN_FACE_O, MP + 3.5 + 4 - ARM_T - HORN_FACE_O   # 11,8 et 3,8 (bras de 6 mm, face extérieure inchangée)   # plan des rotules : contre la face extérieure du bras/levier + rondelle

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

def place_entretoise(h, centre, y_face, cible=None):
    e = entretoise(h)
    e = e.translate((0, y_face - e.val().BoundingBox().ymin, 0))
    if cible is not None:
        e = e.rotate((0, 0, 0), (0, 1, 0), math.degrees(math.atan2(-(cible[1] - centre[1]), cible[0] - centre[0])))
    return e.translate((centre[0], 0, centre[1]))

# ── Visserie (simplifiée : tige + tête, écrous hexagonaux) ────────────────────
def vis(axis, p, sens, L, d):
    """Vis d'axe x/y/z : tête posée en p (face d'appui), tige de longueur L dans le sens +1/-1 de l'axe."""
    hd, hh = 1.8 * d, 0.6 * d
    a0, a1 = sorted((0, sens * L)); h0, h1 = sorted((0, -sens * hh))
    if axis == "x":
        return cyl_x(p[1], p[2], d / 2, p[0] + a0, p[0] + a1).union(cyl_x(p[1], p[2], hd / 2, p[0] + h0, p[0] + h1))
    if axis == "y":
        return cyl_y(p[0], p[2], d / 2, p[1] + a0, p[1] + a1).union(cyl_y(p[0], p[2], hd / 2, p[1] + h0, p[1] + h1))
    return cyl_z(p[0], p[1], d / 2, p[2] + a0, p[2] + a1).union(cyl_z(p[0], p[1], hd / 2, p[2] + h0, p[2] + h1))

def ecrou(axis, p, sens, d):
    """Écrou hexagonal posé en p (face d'appui), épaisseur 0,8 d dans le sens donné."""
    e = cq.Workplane("XY").polygon(6, 2 * d).extrude(0.8 * d * sens)
    if axis == "y":
        e = e.rotate((0, 0, 0), (1, 0, 0), -90)
    elif axis == "x":
        e = e.rotate((0, 0, 0), (0, 1, 0), 90)
    return e.translate(p)

LONGUEURS_VIS = (6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 30)

def long_vis(face):
    """Plus longue vis M3 standard dont la pointe s'arrête au dos du palonnier (+0,3) depuis une face à |face| de l'axe."""
    return max(l for l in LONGUEURS_VIS if l <= face - HORN_BACK + 0.3)

def croix(cx, cz, phi=0.0):
    return [(cx + HORN_PCD / 2 * math.cos(phi + k * math.pi / 2), cz + HORN_PCD / 2 * math.sin(phi + k * math.pi / 2)) for k in range(4)]

def visserie_jambe(pins):
    """Toute la visserie d'une jambe droite, en place : {nom: forme}."""
    pin_s3, pin_genou, pin_s4, pin_talon = pins
    v = {}
    def add(nom, f):
        v[nom] = f if nom not in v else v[nom].union(f)
    y_far = SL - S_END
    # palonniers de S1 (étrier, avant et arrière) et de S2 (chape, extérieur et intérieur) : 4 vis M3 par palonnier
    # (la vis centrale d'origine du palonnier reste en place, logée dans le lamage)
    for (yy, zz) in croix(0, S1_Z):
        add("vis_palonnier_S1", vis("x", (MP + 6, yy, zz), -1, long_vis(MP + 6), 3).union(vis("x", (-MP - 6, yy, zz), 1, long_vis(MP + 6), 3)))
    for (xx, zz) in croix(0, 0):
        add("vis_palonnier_S2", vis("y", (xx, MP + 5, zz), -1, long_vis(MP + 5), 3).union(vis("y", (xx, -MP - 5, zz), 1, long_vis(MP + 5), 3)))
    # bras de S3 / S4 : 4 vis à travers bras + entretoise jusque dans le palonnier, suivant l'orientation du bras
    for nom, c_, pin, yb in (("S3", (-OFF, -40), pin_s3, B1_Y + 2), ("S4", (-OFF, KZ - 35), pin_s4, B2_Y + 2)):
        phi = math.atan2(pin[1] - c_[1], pin[0] - c_[0])
        for (xx, zz) in croix(c_[0], c_[1], phi):
            add(f"vis_bras_{nom}", vis("y", (xx, yb, zz), -1, long_vis(yb), 3))
    # vis de boîtier M2 (2 par face, au bout opposé à l'arbre) : S1 sur x, S2/S3/S4 sur y
    for dz in (-S_HOLE_Y, S_HOLE_Y):
        for sx in (1, -1):
            add("vis_boitier_S1", vis("x", (sx * (MP - 0.2), y_far - S_HOLE_X, S1_Z + dz), -sx, 12, 2))
            add("vis_boitier_S2", vis("y", (-(SL - S_END) + S_HOLE_X, sx * (SH / 2 + 5.5), dz), -sx, 12, 2))
    for nom, zc in (("S3", -40.0), ("S4", KZ - 35.0)):
        zf = zc - (SL - S_END) + S_HOLE_X
        for dx in (-S_HOLE_Y, S_HOLE_Y):
            for sy in (1, -1):
                add(f"vis_boitier_{nom}", vis("y", (-OFF + dx, sy * (SH / 2 + 3.5), zf), -sy, 12, 2))
    # vis épaulées M5 : écrous
    add("ecrou_M5", ecrou("y", (0, -18.2, KZ), -1, 5).union(ecrou("y", (0, 25.2, AZ), 1, 5)))   # genou : écrou côté intérieur
    # rotules : vis M3 à travers l'œil dans le bras / le levier
    for nom, pin, y_ext in (("B1", pin_s3, B1_ROD + 3), ("B1", pin_genou, B1_ROD + 3), ("B2", pin_s4, B2_ROD + 3), ("B2", pin_talon, B2_ROD + 3)):
        add(f"vis_rotules_{nom}", vis("y", (pin[0], y_ext, pin[1]), -1, 16, 3))
    # colliers et goupilles des tubes
    add("vis_tubes", vis("y", (9.5, 12, -TOP1 + 12), -1, 25, 3).union(ecrou("y", (9.5, -12, -TOP1 + 12), -1, 3)))
    add("vis_tubes", vis("x", (10, 0, KZ + CLV - 6), -1, 25, 3).union(ecrou("x", (-10, 0, KZ + CLV - 6), -1, 3)))
    add("vis_tubes", vis("y", (0, 18, KZ - TOP2 + 8), -1, 40, 3).union(ecrou("y", (0, -18, KZ - TOP2 + 8), -1, 3)))
    add("vis_tubes", vis("y", (0, 18.5, AZ + CLV - 8), -1, 40, 3).union(ecrou("y", (0, -18.5, AZ + CLV - 8), -1, 3)))
    # ressorts : axe d'ancrage M3 × 45 + tendeurs de câble
    add("vis_ressorts", vis("y", (12, 20, -TOP1 + 3), -1, 45, 3).union(ecrou("y", (12, -20, -TOP1 + 3), -1, 3)))
    for yc in (14.25, -14.25):
        sy = 1 if yc > 0 else -1
        add("vis_ressorts", vis("y", (15, sy * 18, KZ - 12), -sy, 7, 3))
    # berceau de S1 sous la plaque de bassin
    ztop = S1_Z + SW / 2 + 0.15 + 6
    for x in (-12, 12):
        add("vis_berceau_S1", vis("z", (x, 40, ztop), -1, 12, 3))
    return v

# ── Maquettes (non imprimées) pour l'assemblage ───────────────────────────────
_SERVO = []

def servo_sts3215():
    """STS3215 (STS3215_c.step : boîtier, palonniers, connecteurs, visserie interne) en un seul composant.
    Repère du fichier : arbre selon y à l'origine, boîtier vers +x, connecteurs sur la face -y."""
    if not _SERVO:
        w = cq.importers.importStep(os.path.join(os.path.dirname(os.path.abspath(__file__)), SERVO_STEP))
        _SERVO.append(cq.Compound.makeCompound(w.solids().vals()))
    return _SERVO[0]

# Orientation de chaque servo dans le repère de jambe : colonnes = images des axes x, y, z du fichier servo.
#   S1 : boîtier vers l'extérieur (+y), arbre selon x, connecteurs vers l'arrière
#   S2 : boîtier vers l'arrière ; S3, S4 : boîtier vers le bas ; connecteurs vers l'intérieur (-y)
SERVOS = {
    "S1": (((0, 1, 0), (1, 0, 0), (0, 0, -1)), (0, 0, S1_Z)),
    "S2": (((-1, 0, 0), (0, 1, 0), (0, 0, -1)), (0, 0, 0)),
    "S3": (((0, 0, -1), (0, 1, 0), (1, 0, 0)), (-OFF, 0, -40)),
    "S4": (((0, 0, -1), (0, 1, 0), (1, 0, 0)), (-OFF, 0, KZ - 35)),
}

def loc_servo(nom, cote=None):
    """Position du servo : repère de jambe (cote=None), jambe gauche (+45) ou droite (symétrique, -45).
    Pour la jambe droite le servo n'est pas « miroir » : on le retourne autour de son axe long (z du fichier),
    ce que permet sa symétrie, et ses connecteurs restent vers l'intérieur."""
    from OCP.gp import gp_Trsf
    cols, t = SERVOS[nom]
    R = [[cols[j][i] for j in range(3)] for i in range(3)]
    t = list(t)
    if cote == "D":
        R = [[R[i][j] * (-1 if i == 1 else 1) * (-1 if j == 2 else 1) for j in range(3)] for i in range(3)]
        t = [t[0], -t[1] - 45, t[2]]
    elif cote == "G":
        t = [t[0], t[1] + 45, t[2]]
    tr = gp_Trsf()
    tr.SetValues(R[0][0], R[0][1], R[0][2], t[0], R[1][0], R[1][1], R[1][2], t[1], R[2][0], R[2][1], R[2][2], t[2])
    return cq.Location(tr)

def servo(nom):
    return cq.Workplane().add(servo_sts3215().moved(loc_servo(nom)))

def point_servo(nom, p):
    """Point du repère du fichier servo → repère de jambe."""
    cols, t = SERVOS[nom]
    return tuple(t[i] + sum(cols[j][i] * p[j] for j in range(3)) for i in range(3))

# ── Câblage du bus (un seul corps par jambe) ──────────────────────────────────
def chemins_cables():
    """Bus en guirlande bassin → S1 → S2 → S3 → S4, fils sortant à plat des connecteurs puis guidés par les pièces.
    Chaque articulation est traversée au plus près de son axe (longueur quasi constante, pas de boucle géante)."""
    f = -(CONN_FACE + CABLE_R)
    c = {n: [point_servo(n, (CONN_X, f, CONN_Z)), point_servo(n, (CONN_X, f, -CONN_Z))] for n in SERVOS}
    s1h, s1b = sorted(c["S1"], key=lambda q: -q[2])
    s2h, s2b = sorted(c["S2"], key=lambda q: -q[2])
    s3a, s3b = sorted(c["S3"], key=lambda q: -q[0])          # S3 : avant (vers S2) / arrière (vers S4)
    s4a = max(c["S4"], key=lambda q: q[0])
    return {
        "bassin_S1": [s1h, (s1h[0], s1h[1], 76), (s1h[0], s1h[1], 92)],
        "S1_S2": [s1b, (-19.5, 9, s1b[2] - 6), (-19.5, 4, 51), (-19.5, -6, 52), (-19.5, -12, 50), (-15.5, -15, 40),
                  (-14, -16, 30), (-14, -16, 21), (-14, -19, 15), s2h],
        "S2_S3": [s2b, (-14.5, -19.2, -28), (-13.8, -19.2, -38), (-13.5, -19.2, -45), (s3a[0], s3a[1], -50), s3a],
        "S3_S4": [s3b, (s3b[0], -24, -58), (s3b[0], -24, -84), (-6, -27, -112), (-2, -27, KZ + 42), (-2, -27, KZ + 20),
                  (-3.8, -26.6, KZ + 3), (-3.8, -26.6, KZ - 3), (-6, -27, KZ - 12), (-6, -27, KZ - 28), (-14, -26, KZ - 38), (s4a[0], -22, KZ - 45), s4a],
    }

def cablage_jambe():
    corps = None
    for pts in chemins_cables().values():
        for a_, b_ in zip(pts, pts[1:]):
            v = cq.Vector(b_) - cq.Vector(a_)
            seg = cq.Solid.makeCylinder(CABLE_R, v.Length, cq.Vector(a_), v.normalized())
            corps = seg if corps is None else corps.fuse(seg)
        for q in pts[1:-1]:
            corps = corps.fuse(cq.Solid.makeSphere(CABLE_R, cq.Vector(q), angleDegrees1=-90, angleDegrees2=90))
    return cq.Workplane().add(corps.clean())

def composants_jambe():
    """Tous les composants d'une jambe droite (repère de jambe), hors plaque de bassin : {nom: (forme, couleur)}."""
    pla, srv, carb = cq.Color(0.85, 0.88, 0.86), cq.Color(0.2, 0.37, 0.55), cq.Color(0.15, 0.15, 0.15)
    acier, orange, vert = cq.Color(0.62, 0.62, 0.65), cq.Color(0.72, 0.42, 0.06), cq.Color(0.17, 0.53, 0.34)
    c = {}
    for n, fn in PIECES.items():
        if n[:2] in ("01", "09", "10", "11", "17"):
            continue
        c[n[3:]] = (fn(), pla)
    for n in SERVOS:
        c[n] = (servo(n), srv)
    c["cablage_bus"] = (cablage_jambe(), cq.Color(0.1, 0.1, 0.1))
    c["tube_cuisse"] = (tube(12, 10, L_CUISSE).translate((0, 0, -TOP1 + SOCK)), carb)
    for ty in (-10, 10):
        c[f"tube_tibia_{'int' if ty < 0 else 'ext'}"] = (tube(10, 8, L_TIBIA).translate((0, ty, KZ - TOP2 + SOCK)), carb)
    b0 = math.radians(55)
    pin_s3 = (-OFF - ARM * math.cos(b0), -40 - ARM * math.sin(b0))
    pin_genou = (-ARM * math.cos(b0), KZ - ARM * math.sin(b0))
    pin_s4, pin_talon = (-OFF - ARM, KZ - 35), (-ARM, AZ)
    c["bielle_B1"] = (bielle(pin_s3, pin_genou, B1_ROD)[0], orange)
    c["bielle_B2"] = (bielle(pin_s4, pin_talon, B2_ROD)[0], orange)
    c["entretoise_S3"] = (place_entretoise(ENT_S3, (-OFF, -40), HORN_FACE_O, pin_s3), pla)
    c["bras_S3"] = (place_bras((-OFF, -40), pin_s3, HORN_FACE_O + ENT_S3), pla)
    c["entretoise_S4"] = (place_entretoise(ENT_S4, (-OFF, KZ - 35), HORN_FACE_O, pin_s4), pla)
    c["bras_S4"] = (place_bras((-OFF, KZ - 35), pin_s4, HORN_FACE_O + ENT_S4), pla)
    for n, (y, z) in {"625_genou_ext": (13.0, KZ), "625_genou_int": (-13.0, KZ),
                      "625_cheville_ext": (21.5, AZ), "625_cheville_int": (-21.5, AZ)}.items():
        c[n] = (roulement_625().translate((0, y, z)), acier)
    c["vis_M5_genou"] = (vis_epaulee_m5(40).mirror("XZ").translate((0, 0, KZ)), acier)   # tête côté extérieur
    c["vis_M5_cheville"] = (vis_epaulee_m5(56).translate((0, 0, AZ)), acier)
    for ys in (14.5, -14.5):
        c[f"ressort_{'ext' if ys > 0 else 'int'}"] = (ressort().translate((12, ys, -TOP1 - 1)), vert)
    tpu = cq.Color(0.33, 0.42, 0.38)
    c["semelle_TPU"] = (c.pop("semelle_TPU")[0], tpu)
    for n, f in visserie_jambe((pin_s3, pin_genou, pin_s4, pin_talon)).items():
        c[n] = (f, cq.Color(0.45, 0.45, 0.48))
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
    "10_entretoise_S3_11_8": lambda: entretoise(ENT_S3),
    "11_entretoise_S4_3_8": lambda: entretoise(ENT_S4),
    "16_semelle_TPU": semelle_tpu,
    "17_support_ToF_bas": support_tof,
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
        if n in SERVOS:
            asm.add(servo_sts3215(), name=n, loc=loc_servo(n), color=col)
        else:
            asm.add(sh, name=n, color=col)
    asm.save(os.path.join(here, "step", "assemblage_jambe.step"))
    # deux jambes : y robot vers la gauche ; jambe gauche = repère de jambe décalé de +45,
    # jambe droite = symétrie par rapport au plan xz puis décalage de -45
    asm2 = cq.Assembly(name="LEO-S_jambes")
    asm2.add(built["01_plaque_bassin"], name="plaque_bassin", color=pla)
    for n, (sh, col) in comp.items():
        if n in SERVOS:
            asm2.add(servo_sts3215(), name="G_" + n, loc=loc_servo(n, "G"), color=col)
            asm2.add(servo_sts3215(), name="D_" + n, loc=loc_servo(n, "D"), color=col)
            continue
        asm2.add(sh.translate((0, 45, 0)), name="G_" + n, color=col)
        asm2.add(sh.mirror("XZ").translate((0, -45, 0)), name="D_" + n, color=col)
    asm2.save(os.path.join(here, "step", "assemblage_deux_jambes.step"))
    print("Assemblages : step/assemblage_jambe.step, step/assemblage_deux_jambes.step")
