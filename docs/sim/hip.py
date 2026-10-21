"""Détails : interface du STS3215 (plan Feetech) et hanche (S1, étrier de roulis, S2)."""
import math
from leg import P, f, line, circle, text, dim

def rect(x, y, w, h, cls, rx=0, extra=""):
    return f'<rect class="{cls}" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" {extra}/>'

# ── J · Interface du servo (plan Feetech) : face palonnier et vue de côté ─────
L, W, H = 45.22, 24.72, 35.0
SH_ = 10.11                        # arbre → bout du boîtier
o = []
x0, y0 = 10, 22
o.append(rect(x0, y0, L, W, "servo", 2))
sx, sy = x0 + L - SH_, y0 + W / 2
o.append(circle(P(sx, sy), 9.6, "horn")); o.append(circle(P(sx, sy), 1.65, "pin"))
for dx, dy in ((7, 0), (-7, 0), (0, 7), (0, -7)):
    o.append(circle(P(sx + dx, sy + dy), 1.4, "hole"))
for hx in (x0 + L - 18.41, x0 + L - 18.41 - 24.45):
    for hy in (sy - 10.25, sy + 10.25):
        o.append(circle(P(hx, hy), 0.9, "pin"))
o.append(dim(P(x0 + L - SH_, y0 + W), P(x0 + L, y0 + W), 5, "10,11", side=1))
o.append(dim(P(x0 + L - 18.41, y0 + W), P(x0 + L, y0 + W), 11, "18,41", side=1))
o.append(dim(P(x0 + L - 18.41 - 24.45, y0 + W), P(x0 + L - 18.41, y0 + W), 11, "24,45", side=1))
o.append(dim(P(x0, y0 + W), P(x0 + L, y0 + W), 17, "45,22", side=1))
o.append(dim(P(x0 + L, y0), P(x0 + L, y0 + W), -6, "24,72", side=-1))
o.append(dim(P(x0, sy - 10.25), P(x0, sy + 10.25), 5, "20,5", side=1))
o.append(text(P(sx, y0 - 3), "palonnier Ø19,2 · 4 trous en croix sur Ø14", "small", "middle"))
o.append(text(P(x0, y0 + W + 27), "FACE PALONNIER (les deux faces sont identiques)", "cap"))
bx = 98
o.append(rect(bx + 3, y0, 29, W, "servo", 2))
o.append(rect(bx, y0 + 8, 35, W - 8, "servo", 1))
o.append(rect(bx + 3 + 29, sy - 9.6, 4.125, 19.2, "horn")); o.append(rect(bx + 3 - 4.125, sy - 9.6, 4.125, 19.2, "horn"))
o.append(line(P(bx - 8, sy), P(bx + 43, sy), "axis"))
o.append(dim(P(bx - 1.125, y0 - 2), P(bx + 36.125, y0 - 2), 2, "37,25 palonniers compris"))
o.append(dim(P(bx, y0 + W), P(bx + 35, y0 + W), 9, "35 boîtier", side=1))
o.append(text(P(bx, y0 + W + 27), "VUE DE CÔTÉ", "cap"))
servo_svg = "\n".join(o)
SERVO_VB = "-2 10 178 70"

# ── I · Hanche, vue de côté (x avant, y bas, 0 = axe de tangage) ──────────────
c = []
AX1 = -63.5                                   # axe de roulis S1
c.append(rect(-48, -84, 96, 8, "plate", 1.5))                       # plaque de bassin
c.append(rect(-17.5, AX1 - 12.35, 35, 24.7, "servo", 2))            # S1, axe vers l'avant
c.append(rect(17.5, AX1 - 9.6, 1.1, 19.2, "horn")); c.append(rect(18.6, AX1 - 9.6, 2.9, 19.2, "fitE"))
c.append(rect(-18.6, AX1 - 9.6, 1.1, 19.2, "horn"))
c.append(rect(-26, -76, 9, 14, "fit"))                              # berceau S1 (joue arrière, côté bout)
c.append(rect(17, -76, 2, 6, "fit"))
c.append(rect(21.5, AX1 - 11, 5, 52, "fitE"))                      # étrier : plaque avant sur palonnier S1
c.append(rect(-26.5, AX1 - 11, 5, 52, "fitE"))                      # plaque arrière sur le palonnier arrière de S1
c.append(rect(-38, -22.5, 64.5, 5, "fitE"))                         # plancher de l'étrier
c.append(rect(-36, -17.5, 16, 30, "fitE"))                          # joue du berceau de S2 (côté bout)
c.append(rect(-35.11, -12.36, 45.22, 24.72, "servo", 2))             # S2, arbre en 0 (10,11 du bout avant)
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
d.append(rect(-10.11, AX1 - 12.36, 45.22, 24.72, "servo", 2))       # S1 : arbre en 0, 10,11 du bout intérieur
d.append(circle(P(0, AX1), 6, "horn")); d.append(circle(P(0, AX1), 1.4, "pin"))
d.append(rect(13, -76, 22, 26, "fitT", 2))                          # berceau S1 côté bout (extérieur)
for hy in (AX1 - 10.25, AX1 + 10.25):
    d.append(circle(P(35 - 2.4, hy), 0.9, "pin"))
# étrier vu de face : moyeu r 11 autour de l'axe S1, col, plancher
d.append(f'<path class="fitE" d="M-11,{f(AX1)} A11,11 0 0 1 11,{f(AX1)} L11,-30 L30,-22.5 L30,-17.5 L-30,-17.5 L-30,-22.5 L-11,-30 Z" style="fill-opacity:.55"/>')
d.append(rect(-17.5, -12.35, 35, 24.7, "servo", 2))                 # S2 (épaisseur 35 latérale)
d.append(rect(14.5, -9.6, 4.1, 19.2, "horn")); d.append(rect(-18.6, -9.6, 4.1, 19.2, "horn"))
d.append(rect(18.6, -10, 7.9, 36, "fit")); d.append(rect(-26.5, -10, 7.9, 36, "fit"))   # chape en U sur les deux palonniers
d.append(rect(-26.5, 22, 53, 6, "fit"))
d.append(line(P(-35, AX1), P(45, AX1), "axis")); d.append(line(P(-35, 0), P(45, 0), "axis"))
d.append(line(P(0, -100), P(0, 40), "axis"))
d.append(dim(P(-10.11, -92), P(0, -92), 0, "10,11", side=-1))
d.append(dim(P(0, -92), P(34.2, -92), 0, "35", side=-1))
d.append(dim(P(-26.5, 34), P(26.5, 34), 0, "53 (chape en U)", side=1))
# arc de roulis
r = 90
pts = [P(r * math.sin(math.radians(a)), AX1 + r * math.cos(math.radians(a))) for a in (-20, 30)]
d.append(f'<path class="arc" d="M{f(pts[0][0])},{f(pts[0][1])} A{r},{r} 0 0 0 {f(pts[1][0])},{f(pts[1][1])}"/>')
d.append(text(P(26, 18), "roulis", "arct")); d.append(text(P(26, 23), "−20° / +30°", "arct"))
d.append(text(P(-38, 44), "HANCHE · VUE DE FACE (jambe droite)", "cap"))
hip_front_svg = "\n".join(d)
HIP_FRONT_VB = "-42 -100 100 150"
