"""Détails : interface du STS3215 (relevée sur le modèle 3D SO-ARM100) et hanche (S1, étrier de roulis, S2)."""
import math
from leg import P, f, line, circle, text, dim

def rect(x, y, w, h, cls, rx=0, extra=""):
    return f'<rect class="{cls}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" {extra}/>'

# ── J · Interface du servo : face arbre (L × W) et vue de côté ────────────────
L, W, H = 45.2, 24.7, 35.0
SH = 10.2                          # arbre → bout du boîtier
o = []
x0, y0 = 10, 22                    # coin haut gauche de la face arbre (arbre à droite)
o.append(rect(x0, y0, L, W, "servo", 2))
sx, sy = x0 + L - SH, y0 + W / 2
o.append(circle(P(sx, sy), 2.95, "horn")); o.append(circle(P(sx, sy), 1.0, "pin"))
for dx in (-4.95, 4.95):
    for dy in (-4.95, 4.95):
        o.append(circle(P(sx + dx, sy + dy), 1.25, "hole"))
for hx in (x0 + 2.4, x0 + 2.4 + 24.5):
    for hy in (sy - 10.25, sy + 10.25):
        o.append(circle(P(hx, hy), 0.75, "pin"))
# cotes
o.append(dim(P(x0, y0 + W), P(x0 + L, y0 + W), 9, "45,2", side=1))
o.append(dim(P(x0 + L - SH, y0), P(x0 + L, y0), 6, "10,2"))
o.append(dim(P(x0 + 2.4, y0), P(x0 + 2.4 + 24.5, y0), 6, "24,5"))
o.append(dim(P(x0, y0 + W), P(x0 + 2.4, y0 + W), 4, "2,4", side=1))
o.append(dim(P(x0 + L, y0), P(x0 + L, y0 + W), -6, "24,7", side=-1))
o.append(dim(P(x0, sy - 10.25), P(x0, sy + 10.25), 5, "20,5", side=1))
o.append(dim(P(sx - 4.95, y0 + W), P(sx + 4.95, y0 + W), 4, "9,9", side=1))
o.append(text(P(x0, y0 + W + 19), "FACE ARBRE", "cap"))
# vue de côté : épaisseur 35, saillie de l'arbre et du moyeu arrière
bx = 98
o.append(rect(bx, y0, H, W, "servo", 2))
o.append(rect(bx + H, sy - 2.95, 2.7, 5.9, "horn"))
o.append(rect(bx - 0.8, sy - 3, 0.8, 6, "horn"))
o.append(line(P(bx - 6, sy), P(bx + H + 8, sy), "axis"))
o.append(dim(P(bx, y0 + W), P(bx + H, y0 + W), 9, "35", side=1))
o.append(text(P(bx + H + 4, sy - 3), "arbre 25 dents", "small"))
o.append(text(P(bx + H + 4, sy + 6), "Ø 5,9, saillie 2,7", "small"))
o.append(text(P(bx - 24, sy - 3), "moyeu arrière", "small"))
o.append(text(P(bx - 24, sy + 6), "Ø 6 + trou M3", "small"))
o.append(text(P(bx, y0 + W + 19), "VUE DE CÔTÉ", "cap"))
servo_svg = "\n".join(o)
SERVO_VB = "-2 4 178 66"

# ── I · Hanche, vue de côté (x avant, y bas, 0 = axe de tangage) ──────────────
c = []
AX1 = -63.5                                   # axe de roulis S1
c.append(rect(-48, -84, 96, 8, "plate", 1.5))                       # plaque de bassin
c.append(rect(-17.5, AX1 - 12.35, 35, 24.7, "servo", 2))            # S1, axe vers l'avant
c.append(rect(17.5, AX1 - 2.95, 4, 5.9, "horn"))
c.append(rect(-18.3, AX1 - 3, 0.8, 6, "horn"))
c.append(rect(-26, -76, 9, 14, "fit"))                              # berceau S1 (joue arrière, côté bout)
c.append(rect(17, -76, 2, 6, "fit"))
c.append(rect(21.5, AX1 - 11, 5, 52, "fitE"))                      # étrier : plaque avant sur palonnier S1
c.append(rect(-23.3, AX1 - 11, 5, 52, "fitE"))                      # plaque arrière sur moyeu arrière S1
c.append(rect(-38, -22.5, 64.5, 5, "fitE"))                         # plancher de l'étrier
c.append(rect(-36, -17.5, 16, 30, "fitE"))                          # joue du berceau de S2 (côté bout)
c.append(rect(-35, -12.35, 45.2, 24.7, "servo", 2))                 # S2, arbre en 0 (10,2 du bout avant)
c.append(circle(P(0, 0), 6, "horn")); c.append(circle(P(0, 0), 1.6, "pin"))
c.append(circle(P(0, AX1), 1.4, "pin"))
for hx in (-32.6,):
    for hy in (-10.25, 10.25):
        c.append(circle(P(hx, hy), 0.9, "pin"))
c.append(line(P(-45, AX1), P(40, AX1), "axis")); c.append(line(P(-45, 0), P(40, 0), "axis"))
c.append(line(P(0, -10), P(0, 30), "axis"))
# chape de cuisse (bras sur palonnier) qui descend
c.append(f'<path class="fit" d="M-10,-8 L10,-8 L12,22 L-12,22 Z" style="fill-opacity:.6"/>')
c.append(dim(P(30, AX1), P(30, 0), 0, "63,5", side=1))
c.append(line(P(22, 0), P(33, 0), "ext")); c.append(line(P(27, AX1), P(33, AX1), "ext"))
c.append(dim(P(-17.5, -88), P(17.5, -88), 0, "S1 : 35", side=-1))
c.append(text(P(-92, 38), "HANCHE · VUE DE CÔTÉ", "cap"))
labels = [(-80, P(-40, -80), "plaque de bassin"), (-68, P(-22, -70), "berceau S1"), (-56, P(-10, -60), "S1 (roulis)"),
          (-40, P(-20, -40), "étrier"), (-26, P(-36, -20), "plancher"), (-12, P(-30, -5), "berceau S2"),
          (4, P(-25, 5), "S2 (tangage)"), (20, P(-8, 16), "chape de cuisse")]
for y, t_, t in labels:
    c.append(line(P(-92 + len(t) * 1.75 + 1, y - 1), t_, "lead"))
    c.append(text(P(-92, y), t, "small"))
hip_side_svg = "\n".join(c)
HIP_SIDE_VB = "-94 -96 136 140"

# ── I · Hanche, vue de face (une jambe, extérieur vers +x) ────────────────────
d = []
d.append(rect(-50, -84, 100, 8, "plate", 1.5))
d.append(rect(-10.2, AX1 - 12.35, 45.2, 24.7, "servo", 2))          # S1 : arbre en 0, 10,2 du bout intérieur
d.append(circle(P(0, AX1), 6, "horn")); d.append(circle(P(0, AX1), 1.4, "pin"))
d.append(rect(13, -76, 22, 26, "fitT", 2))                          # berceau S1 côté bout (extérieur)
for hy in (AX1 - 10.25, AX1 + 10.25):
    d.append(circle(P(35 - 2.4, hy), 0.9, "pin"))
# étrier vu de face : moyeu r 11 autour de l'axe S1, col, plancher
d.append(f'<path class="fitE" d="M-11,{f(AX1)} A11,11 0 0 1 11,{f(AX1)} L11,-30 L30,-22.5 L30,-17.5 L-30,-17.5 L-30,-22.5 L-11,-30 Z" style="fill-opacity:.55"/>')
d.append(rect(-17.5, -12.35, 35, 24.7, "servo", 2))                 # S2 (épaisseur 35 latérale)
d.append(rect(17.5, -2.95, 2.7, 5.9, "horn")); d.append(rect(-18.3, -3, 0.8, 6, "horn"))
d.append(rect(20.2, -10, 5, 36, "fit")); d.append(rect(-24, -10, 5, 36, "fit"))   # chape en U de cuisse
d.append(rect(-24, 22, 49.2, 6, "fit"))
d.append(line(P(-35, AX1), P(45, AX1), "axis")); d.append(line(P(-35, 0), P(45, 0), "axis"))
d.append(line(P(0, -100), P(0, 40), "axis"))
d.append(dim(P(-10.2, -92), P(0, -92), 0, "10,2", side=-1))
d.append(dim(P(0, -92), P(34.2, -92), 0, "35", side=-1))
d.append(dim(P(-24, 34), P(25.2, 34), 0, "49 (chape en U)", side=1))
# arc de roulis
r = 90
pts = [P(r * math.sin(math.radians(a)), AX1 + r * math.cos(math.radians(a))) for a in (-20, 30)]
d.append(f'<path class="arc" d="M{f(pts[0][0])},{f(pts[0][1])} A{r},{r} 0 0 0 {f(pts[1][0])},{f(pts[1][1])}"/>')
d.append(text(P(26, 18), "roulis", "arct")); d.append(text(P(26, 23), "−20° / +30°", "arct"))
d.append(text(P(-38, 44), "HANCHE · VUE DE FACE (jambe droite)", "cap"))
hip_front_svg = "\n".join(d)
HIP_FRONT_VB = "-42 -100 100 150"
