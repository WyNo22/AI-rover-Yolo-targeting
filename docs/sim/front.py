"""Vue de face cotée des deux jambes, jambes tendues (x = latéral, y = vers le bas, 0 = axe de hanche)."""
import leg
from leg import P, f, line, circle, text, dim

SEG = leg.SEG
KY, AY, GY = SEG, 2 * SEG, 2 * SEG + 50           # genou, cheville, sol
HIP = 45                                          # demi-entraxe des hanches
B1X, B2X = 35, 27                                 # plans des bielles (depuis l'axe de jambe, vers l'extérieur)
o = []

def R(cx, sgn, x0, x1, y0, y1, cls, rx=0, extra=""):
    a, b = cx + sgn * x0, cx + sgn * x1
    xa, xb = min(a, b), max(a, b)
    return f'<rect class="{cls}" x="{f(xa)}" y="{f(y0)}" width="{f(xb-xa)}" height="{f(y1-y0)}" rx="{rx}" {extra}/>'

o.append(f'<line class="ground" x1="-125" y1="{GY}" x2="125" y2="{GY}"/>')
o.append(f'<rect class="hatch" x="-125" y="{GY}" width="250" height="6"/>')
o.append(line(P(0, -105), P(0, GY + 4), "axis"))
o.append('<rect class="plate" x="-85" y="-84" width="170" height="8" rx="1.5"/>')
for sgn in (-1, 1):
    cx = sgn * HIP
    X = lambda d: cx + sgn * d
    # — derrière : B2, S4 —
    o.append(line(P(X(B2X), KY + 35), P(X(B2X), AY), "stud"))
    o.append(R(cx, sgn, B2X - 2, B2X + 2, KY + 35 + 16, AY - 16, "rod"))
    o.append(R(cx, sgn, 21.5, B2X + 2, KY + 33, KY + 37, "arm2"))           # entretoise + bras de S4
    o.append(R(cx, sgn, -17.5, 17.5, KY + 24, KY + 69, "servo2", 2))
    o.append(R(cx, sgn, 17.5, 21.5, KY + 29, KY + 41, "horn"))
    # — tibia : 2 tubes Ø10 —
    for tx in (-10, 10):
        o.append(R(cx, sgn, tx - 5, tx + 5, KY + 50, KY + 70, "tube-in"))
        o.append(R(cx, sgn, tx - 5, tx + 5, KY + 70, AY - 25, "tube"))
        o.append(R(cx, sgn, tx - 5, tx + 5, AY - 25, AY - 5, "tube-in"))
    o.append(R(cx, sgn, -20, 20, KY - 10, KY + 70, "fitT", 3))                # raccord haut de tibia (transparent)
    o.append(R(cx, sgn, -17, 17, AY - 45, AY + 8, "fitT", 3))                 # bas de tibia (languette)
    # — pied, chape de cheville —
    for c0, c1 in ((-25, -19), (19, 25)):
        o.append(R(cx, sgn, c0, c1, AY - 8, GY - 8, "fit"))
        o.append(R(cx, sgn, c0 + 1, c1 - 1, AY - 8, AY + 8, "bearing"))
    o.append(R(cx, sgn, 25, B2X + 2, AY - 5, AY + 5, "arm2"))                 # levier de talon
    o.append(R(cx, sgn, -29, 29, AY - 1.6, AY + 1.6, "bolt"))
    o.append(R(cx, sgn, -32.5, 32.5, GY - 8, GY - 4, "plate", 1))
    o.append(R(cx, sgn, -32.5, 32.5, GY - 4, GY, "tpu", 1.5))
    for y in (KY + 35, AY):
        o.append(circle(P(X(B2X), y), 3.2, "rodend"))
    # — cuisse : S3 derrière le tube —
    o.append(R(cx, sgn, -17.5, 17.5, 29, 74, "servo", 2))
    o.append(R(cx, sgn, 17.5, 21.5, 34, 46, "horn"))
    o.append(R(cx, sgn, 21.5, B1X + 2, 38, 42, "arm2"))
    o.append(R(cx, sgn, -6, 6, 55, 75, "tube-in"))
    o.append(R(cx, sgn, -6, 6, 75, KY - 25, "tube"))
    o.append(R(cx, sgn, -6, 6, KY - 25, KY - 5, "tube-in"))
    o.append(R(cx, sgn, -20, 20, 25, 78, "fitT", 3))                          # raccord haut de cuisse (transparent)
    o.append(R(cx, sgn, -10, 10, KY - 25, KY + 8, "fit", 3))                  # languette du genou
    # genou : joues du tibia, roulements, vis, levier vers B1
    for c0, c1 in ((-18, -11), (11, 18)):
        o.append(R(cx, sgn, c0, c1, KY - 10, KY + 30, "fit"))
        o.append(R(cx, sgn, c0 + 1, c1 - 1, KY - 8, KY + 8, "bearing"))
    o.append(R(cx, sgn, 18, B1X + 2, KY + 10, KY + 22, "arm2"))               # levier du genou (côté extérieur)
    o.append(R(cx, sgn, -24, 24, KY - 1.6, KY + 1.6, "bolt"))
    # B1
    o.append(line(P(X(B1X), 58), P(X(B1X), KY + 18), "stud"))
    o.append(R(cx, sgn, B1X - 2, B1X + 2, 58 + 16, KY + 18 - 16, "rod"))
    for y in (58, KY + 18):
        o.append(circle(P(X(B1X), y), 3.2, "rodend"))
    # hanche : chape de cuisse en U autour de S2, S2, étrier de roulis, S1
    o.append(R(cx, sgn, -17.5, 17.5, -12.35, 12.35, "servo", 2))
    o.append(R(cx, sgn, 17.5, 21.5, -10, 10, "horn"))
    o.append(R(cx, sgn, 21.5, 26, -12, 25, "fit"))
    o.append(R(cx, sgn, -26, -21.5, -12, 25, "fit"))
    o.append(R(cx, sgn, -26, 26, 17, 25, "fit"))
    o.append(R(cx, sgn, -25.5, -22, -8, 8, "bearing"))
    o.append(R(cx, sgn, -32, -17.5, -1.6, 1.6, "bolt"))
    o.append(R(cx, sgn, -32, -27, -60, 10, "fitT"))                          # paroi intérieure de l'étrier
    o.append(R(cx, sgn, -32, 30, -64, -14, "fitT", 2))                       # plaque de l'étrier sur S1
    o.append(R(cx, sgn, -11, 34, -76, -51.3, "servo", 2))                    # S1, arbre vers l'avant
    o.append(circle(P(cx, -63.5), 6, "horn")); o.append(circle(P(cx, -63.5), 1.6, "pin"))
    for y in (0, KY, AY):
        o.append(line(P(cx - 34, y), P(cx + 34, y), "axis"))
    o.append(line(P(cx, -70), P(cx, GY + 4), "axis"))

# ── cotes (jambe de droite sur le dessin : extérieur vers +x) ──
o.append(dim(P(-HIP, -96), P(HIP, -96), 0, "90 entre axes de hanche", side=-1))
o.append(line(P(-HIP, -88), P(-HIP, -99), "ext")); o.append(line(P(HIP, -88), P(HIP, -99), "ext"))
o.append(dim(P(HIP, 120), P(HIP + B1X, 120), 0, str(B1X), side=-1))
o.append(dim(P(HIP - 17.5, 92), P(HIP + 17.5, 92), 0, "35", side=-1))
o.append(line(P(HIP - 17.5, 75), P(HIP - 17.5, 95), "ext")); o.append(line(P(HIP + 17.5, 75), P(HIP + 17.5, 95), "ext"))
o.append(dim(P(HIP - 10, KY + 95), P(HIP + 10, KY + 95), 0, "20", side=-1))
o.append(dim(P(HIP, KY + 125), P(HIP + B2X, KY + 125), 0, str(B2X), side=-1))
o.append(dim(P(-HIP - 32.5, GY + 14), P(-HIP + 32.5, GY + 14), 0, "65", side=-1))
o.append(dim(P(-HIP + 32.5, GY + 14), P(HIP - 32.5, GY + 14), 0, "25", side=-1))
o.append(dim(P(HIP - 32.5, GY + 14), P(HIP + 32.5, GY + 14), 0, "65", side=-1))
for x in (-HIP - 32.5, -HIP + 32.5, HIP - 32.5, HIP + 32.5):
    o.append(line(P(x, GY + 2), P(x, GY + 17), "ext"))
o.append(dim(P(-HIP - B1X, GY + 32), P(HIP + B1X, GY + 32), 0, f"{2 * (HIP + B1X)} hors tout aux bielles", side=-1))
for x in (-HIP - B1X, HIP + B1X):
    o.append(line(P(x, KY + 22), P(x, GY + 35), "ext"))
VX = 118
for (y0, y1, t) in ((-63.5, 0, "63,5"), (0, KY, str(SEG)), (KY, AY, str(SEG)), (AY, GY, "50")):
    o.append(dim(P(VX, y0), P(VX, y1), 0, t, side=1))
for y in (-63.5, 0, KY, AY):
    o.append(line(P(HIP + 36, y), P(VX + 3, y), "ext"))
o.append(dim(P(VX + 16, 0), P(VX + 16, GY), 0, f"{GY} hanche–sol", side=1))
o.append(line(P(VX + 3, GY), P(VX + 19, GY), "ext"))
# libellés en colonne à gauche, avec trait de rappel (jambe de gauche du dessin)
LX = -134
lab = [(-63, P(-62, -63), "S1 roulis"), (-30, P(-30, -40), "étrier de roulis"), (0, P(-45, 0), "S2"),
       (40, P(-45, 52), "S3 (derrière)"), (100, P(-45, 110), "Ø12"), (150, P(-80, 150), "B1"),
       (KY - 12, P(-30.5, KY - 4), "625ZZ"), (KY + 45, P(-45, KY + 50), "S4 (derrière)"),
       (KY + 100, P(-55, KY + 100), "2 × Ø10"), (KY + 140, P(-72, KY + 140), "B2"),
       (AY + 22, P(-60, GY - 6), "pied")]
for y, t_, t in lab:
    o.append(line(P(LX + len(t) * 2.7 + 3, y - 1.8), t_, "lead"))
    o.append(text(P(LX, y), t, "small"))
o.append(text(P(-134, GY + 50), "VUE DE FACE · jambes tendues · pièces imprimées en transparence", "cap"))
front_svg = "\n".join(o)
