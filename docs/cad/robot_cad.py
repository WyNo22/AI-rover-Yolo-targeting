"""
robot_cad.py — Robot LEO-S complet : deux jambes (jambe_cad.py) + buste ESTIMÉ (volumes réservés, pas encore conçu),
bilan de masse calculé sur les volumes de la CAO et position du centre de gravité.

  python robot_cad.py   → step/assemblage_robot_complet.step + bilan_masse.md

Repère robot : x avant, y gauche, z haut, origine sur l'axe de tangage des hanches ; sol à z = −450.
"""
import math
import os
import cadquery as cq
import jambe_cad as J
from jambe_cad import box, cyl_x, cyl_y, cyl_z

Z0 = J.S1_Z + J.SW / 2 + 0.15 + 6          # dessus de la plaque de bassin
Z_EP = 228.0                               # axe des bras de propulseurs (épaules)
PROP = 127.0                               # hélices 5"

def buste():
    """Volumes du buste, estimés. Retourne {nom: (forme, couleur, masse_g ou None si calculée sur le volume, matière)}."""
    petg, carb, bat, elec = cq.Color(0.85, 0.88, 0.86), cq.Color(0.15, 0.15, 0.15), cq.Color(0.85, 0.65, 0.1), cq.Color(0.1, 0.45, 0.25)
    b = {}
    cadre = None
    for ys in (1, -1):
        pl = box(-45, 45, ys * 56 - 2, ys * 56 + 2, Z0, Z_EP).cut(box(-33, 33, ys * 56 - 3, ys * 56 + 3, Z0 + 14, Z_EP - 14).edges("|Y").fillet(8))
        cadre = pl if cadre is None else cadre.union(pl)
    cadre = cadre.union(box(-50, 50, -60, 60, Z_EP + 4, Z_EP + 8).cut(box(-30, 30, -40, 40, Z_EP + 3, Z_EP + 9)))
    cadre = cadre.union(box(-45, 45, -58, 58, 146, 149).cut(box(-30, 30, -40, 40, 145, 150)))   # étagère
    b["cadre_buste"] = (cadre, petg, None, "petg")
    b["LiPo_3S_2200"] = (box(-17.5, 17.5, -52.5, 52.5, Z0 + 4, Z0 + 28), bat, 185, "")
    b["LiPo_4S_1400"] = (box(-17, 17, -37.5, 37.5, Z0 + 32, Z0 + 62), bat, 175, "")
    b["Pi5_AI_HAT_ventilo"] = (box(-42.5, 42.5, -28, 28, 152, 187), elec, 90, "")
    b["FC_F405_ESC_4en1_RX"] = (box(-18, 18, -18, 18, 192, 208), elec, 36, "")
    b["Pico2_regulateur_capteurs"] = (box(20, 44, -25, 25, 192, 202), elec, 80, "")
    b["ecran_eink"] = (box(45, 46.5, -32, 32, 165, 195), elec, 15, "")
    b["cablage"] = (box(-40, -30, -45, 45, Z0 + 4, Z_EP - 10), cq.Color(0.6, 0.1, 0.1), 70, "")
    bras = cyl_y(0, Z_EP, 6, -180, 180)
    for ys in (1, -1):
        bras = bras.union(cyl_x(ys * 170, Z_EP, 5, -112, 112))
    b["bras_propulseurs_carbone"] = (bras.cut(cyl_y(0, Z_EP, 5, -181, 181)), carb, None, "carbone")
    mot = garde = helice = None
    for xs in (1, -1):
        for ys in (1, -1):
            c = (xs * 100, ys * 170, Z_EP + 6)
            m = cyl_z(0, 0, 14, 0, 30)
            h = cyl_z(0, 0, PROP / 2, 36, 38)
            g = cyl_z(0, 0, 71, 26, 48).cut(cyl_z(0, 0, 68, 25, 49))
            pose = lambda w: w.rotate((0, 0, 0), (1, 0, 0), -ys * 15).translate(c)   # inclinés de 15° vers l'extérieur
            mot = pose(m) if mot is None else mot.union(pose(m))
            helice = pose(h) if helice is None else helice.union(pose(h))
            garde = pose(g) if garde is None else garde.union(pose(g))
    b["moteurs_2206"] = (mot, cq.Color(0.3, 0.3, 0.35), 4 * 32, "")
    b["helices_5po"] = (helice, cq.Color(0.2, 0.5, 0.9), 4 * 4.5, "")
    b["protections_helices"] = (garde, petg, None, "petg_plein")
    b["cou_servo_pan"] = (box(-6, 6, -11.5, 11.5, Z_EP + 8, Z_EP + 35), cq.Color(0.2, 0.37, 0.55), 9, "")
    tete = box(-30, 30, -30, 30, Z_EP + 38, Z_EP + 80).edges("|Z").fillet(10).faces(">Z").shell(-1.6)
    b["tete_coque"] = (tete, petg, None, "petg_plein")
    b["tete_servo_tilt"] = (box(-10, 10, -6, 6, Z_EP + 40, Z_EP + 63), cq.Color(0.2, 0.37, 0.55), 9, "")
    b["camera_Pi_cam3"] = (box(30, 40, -12.5, 12.5, Z_EP + 55, Z_EP + 74), elec, 4, "")
    b["camera_ToF"] = (box(30, 42, -19, 19, Z_EP + 41, Z_EP + 53), elec, 10, "")
    return b

DENS = {"petg": 1.27 * 0.6, "petg_plein": 1.27 * 0.9, "tpu": 1.21 * 0.9, "carbone": 1.6, "acier": 7.85}

def masse_jambe(comp):
    """Masse de chaque composant d'une jambe (g) à partir du volume CAO, ou masse catalogue."""
    out = {}
    for n, (sh, c) in comp.items():
        v = sh.val().Volume() / 1000.0
        if n in ("S1", "S2", "S3", "S4"):
            m = 55.0
        elif n.startswith("625_"):
            m = 4.6
        elif n.startswith("ressort"):
            m = 11.0
        elif n.startswith("bielle_"):
            m = 2 * 2.0 + v * 0  # rotules ≈ 2 g chacune ; tube compté ci-dessous
            m += (math.pi / 4 * (J.ROD_D ** 2 - J.ROD_DI ** 2) * 135 / 1000) * DENS["carbone"]
        elif n.startswith("tube_"):
            m = v * DENS["carbone"]
        elif n.startswith(("vis_", "ecrou_")):
            m = v * DENS["acier"]
        elif n == "semelle_TPU":
            m = v * DENS["tpu"]
        else:
            m = v * DENS["petg"]
        out[n] = (m, sh.val().Center())
    return out

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    comp, pins = J.composants_jambe()
    mj = masse_jambe(comp)
    plaque = J.plaque_bassin()
    b = buste()
    asm = cq.Assembly(name="LEO-S_robot_complet")
    asm.add(plaque, name="plaque_bassin", color=cq.Color(0.85, 0.88, 0.86))
    lignes, M, mz, mx = [], 0.0, 0.0, 0.0
    def compte(cat, nom, m, cz, cx=0.0):
        global M, mz, mx
        lignes.append((cat, nom, m)); M += m; mz += m * cz; mx += m * cx
    compte("bassin", "plaque de bassin", plaque.val().Volume() / 1000 * DENS["petg"], plaque.val().Center().z)
    for n, (sh, col) in comp.items():
        asm.add(sh.translate((0, 45, 0)), name="G_" + n, color=col)
        asm.add(sh.mirror("XZ").translate((0, -45, 0)), name="D_" + n, color=col)
        m, c = mj[n]
        compte("jambes (×2)", n, 2 * m, c.z, c.x)
    for n, (sh, col, m, mat) in b.items():
        asm.add(sh, name=n, color=col)
        if m is None:
            m = sh.val().Volume() / 1000 * DENS[mat]
        c = sh.val().Center()
        compte("buste (estimé)", n, m, c.z, c.x)
    asm.save(os.path.join(here, "step", "assemblage_robot_complet.step"))
    zg, xg = mz / M, mx / M
    cats = {}
    for cat, nom, m in lignes:
        cats[cat] = cats.get(cat, 0) + m
    with open(os.path.join(here, "bilan_masse.md"), "w") as f:
        f.write("# Bilan de masse LEO-S (calculé sur la CAO)\n\n")
        f.write("Pièces imprimées : PETG à 60 % de densité effective (4 parois, gyroïde 40 %). Buste : volumes réservés, masses catalogue.\n\n")
        f.write("| Ensemble | Masse |\n|---|---|\n")
        for cat, m in cats.items():
            f.write(f"| {cat} | {m:.0f} g |\n")
        f.write(f"| **Total** | **{M:.0f} g** |\n\n")
        f.write(f"Centre de gravité : **{zg + 450:.0f} mm au-dessus du sol** ({zg:+.0f} mm par rapport à l'axe de hanche), {xg:+.1f} mm en x.\n\n")
        f.write("| Ensemble | Composant | Masse |\n|---|---|---|\n")
        for cat, nom, m in sorted(lignes, key=lambda t: -t[2]):
            f.write(f"| {cat} | {nom} | {m:.1f} g |\n")
    print(f"Total {M:.0f} g ; CdG à {zg + 450:.0f} mm du sol ; {cats}")
    print("step/assemblage_robot_complet.step + bilan_masse.md")
