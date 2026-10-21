import math
import numpy as np

def P(x, y): return np.array([float(x), float(y)])
def f(v): return f"{v:.2f}".rstrip("0").rstrip(".")
def pt(p): return f"{f(p[0])},{f(p[1])}"

# ── Géométrie (mm, x = avant, y = bas), genou fléchi de 25° ──────────────────
T = math.radians(12.5)
u1 = P(math.sin(T), math.cos(T))          # cuisse, hanche → genou
u2 = P(-math.sin(T), math.cos(T))         # tibia, genou → cheville
nb1 = P(-math.cos(T), math.sin(T))        # perpendiculaire à la cuisse, vers l'arrière
SEG = 200                                  # cuisse = tibia (hanche à 450 mm jambe tendue)
H = P(0, 0); K = H + SEG * u1; A = K + SEG * u2
GROUND = A[1] + 50
S3 = H + 40 * u1 + 25 * nb1                # S3 centré derrière le tube de cuisse
a = math.radians(30)                       # bras du parallélogramme à 25° de flexion
arm = math.cos(a) * nb1 + math.sin(a) * u1
P1 = S3 + 22 * arm; P2 = K + 22 * arm
nb2 = P(-math.cos(T), -math.sin(T))       # perpendiculaire au tibia, vers l'arrière
S4 = K + 35 * u2 + 25 * nb2                # S4 derrière les deux tubes, centré
P3 = S4 + P(-22, 0); P4 = A + P(-22, 0)
RE = 16                                    # centre rotule → bout du tube
B1 = np.linalg.norm(P2 - P1); B2 = np.linalg.norm(P4 - P3)
TOP1, CLV, INS = 75, 35, 20                # raccord haut de cuisse, chape genou (axe → bout), emmanchement
TOP2, CLV2 = 70, 35
thigh_vis = SEG - TOP1 - CLV; thigh_cut = thigh_vis + 2 * INS
shank_vis = SEG - TOP2 - CLV2; shank_cut = shank_vis + 2 * INS
B1_cut = round(B1) - 2 * RE; B2_cut = round(B2) - 2 * RE
DIMS = dict(thigh_vis=thigh_vis, thigh_cut=thigh_cut, shank_vis=shank_vis, shank_cut=shank_cut,
            B1=round(B1), B2=round(B2), B1_cut=B1_cut, B2_cut=B2_cut, hip_h=round(GROUND))

def band(p, q, w, cls, extra=""):
    d = (q - p) / np.linalg.norm(q - p); n = P(-d[1], d[0]) * w / 2
    pts = [p + n, q + n, q - n, p - n]
    return f'<polygon class="{cls}" points="{" ".join(pt(x) for x in pts)}" {extra}/>'

def rect_on(c, d, along0, along1, w, cls):
    d = d / np.linalg.norm(d)
    return band(c + along0 * d, c + along1 * d, w, cls)

def circle(c, r, cls): return f'<circle class="{cls}" cx="{f(c[0])}" cy="{f(c[1])}" r="{f(r)}"/>'
def line(p, q, cls): return f'<line class="{cls}" x1="{f(p[0])}" y1="{f(p[1])}" x2="{f(q[0])}" y2="{f(q[1])}"/>'
def text(p, s, cls="lbl", anchor="start", rot=None):
    r = f' transform="rotate({f(rot)} {f(p[0])} {f(p[1])})"' if rot is not None else ""
    return f'<text class="{cls}" x="{f(p[0])}" y="{f(p[1])}" text-anchor="{anchor}"{r}>{s}</text>'

def dim(p, q, off, label, side=1):
    d = (q - p) / np.linalg.norm(q - p); n = P(-d[1], d[0]) * side
    a, b = p + n * off, q + n * off
    out = [line(p + n * 2, a + n * 3, "ext"), line(q + n * 2, b + n * 3, "ext"),
           f'<line class="dim" x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" '
           f'marker-start="url(#ar)" marker-end="url(#ar)"/>']
    ang = math.degrees(math.atan2(d[1], d[0]))
    if ang > 90: ang -= 180
    if ang <= -90: ang += 180
    up = P(math.sin(math.radians(ang)), -math.cos(math.radians(ang)))   # haut des lettres
    m = (a + b) / 2 + up * 2.8
    out.append(text(m, label, "dimt", "middle", ang))
    return "\n".join(out)

def balloon(c, target, n):
    return (line(c, target, "lead") + circle(c, 6.2, "bal") +
            text(c + P(0, 2.4), str(n), "baln", "middle"))

def spring(p, q, turns=9, amp=3.2):
    d = (q - p); L = np.linalg.norm(d); d = d / L; n = P(-d[1], d[0])
    pts = [p]
    for i in range(1, 2 * turns):
        pts.append(p + d * (L * i / (2 * turns)) + n * (amp if i % 2 else -amp))
    pts.append(q)
    return f'<polyline class="spr" points="{" ".join(pt(x) for x in pts)}"/>'

# ── Vue de côté ───────────────────────────────────────────────────────────────
s = []
# sol
s.append(f'<line class="ground" x1="-110" y1="{f(GROUND)}" x2="150" y2="{f(GROUND)}"/>')
s.append(f'<rect class="hatch" x="-110" y="{f(GROUND)}" width="260" height="6"/>')
# bassin + S1 (roulis, axe vers l'avant)
s.append('<rect class="plate" x="-48" y="-84" width="96" height="8" rx="1.5"/>')
s.append('<rect class="servo" x="-24" y="-76" width="35" height="25" rx="2"/>')
s.append(line(P(11, -63.5), P(26, -63.5), "axis"))
s.append('<rect class="yoke" x="11" y="-70" width="5" height="14"/>')
# étrier de roulis
s.append('<path class="yoke" d="M16,-68 H24 V16 H-42 V-30 H-36 V10 H18 V-60 H16 Z"/>')
# S2 (tangage hanche), arbre en H
s.append('<rect class="servo" x="-34" y="-12.35" width="45.2" height="24.7" rx="2"/>')
s.append(circle(H, 6, "horn")); s.append(circle(H, 1.6, "pin"))
# raccord haut de cuisse (porte S3) + chape genou
s.append(rect_on(H + 12 * nb1, u1, -6, TOP1, 54, "fit"))   # raccord haut de cuisse, enveloppe S3
s.append(rect_on(K, u1, -CLV, 9, 24, "fit"))
# tube cuisse (+ emmanchements en pointillés)
s.append(rect_on(H, u1, TOP1 - INS, TOP1, 12, "tube-in"))
s.append(rect_on(H, u1, TOP1, SEG - CLV, 12, "tube"))
s.append(rect_on(H, u1, SEG - CLV, SEG - CLV + INS, 12, "tube-in"))
# S3 sur la cuisse (côté extérieur)
s.append(rect_on(S3, u1, -11, 34.2, 24.7, "servo"))
s.append(circle(S3, 6, "horn")); s.append(circle(S3, 1.6, "pin"))
# tibia : raccord haut (levier genou + S4), tube, chape cheville
s.append(rect_on(K + 12 * nb2, u2, -9, TOP2, 52, "fit"))   # raccord haut de tibia, enveloppe S4
# tibia : 2 tubes Ø10 côte à côte (vus superposés de côté)
s.append(rect_on(K, u2, TOP2 - INS, TOP2, 10, "tube-in"))
s.append(rect_on(K, u2, TOP2, SEG - CLV2, 10, "tube"))
s.append(rect_on(K, u2, SEG - CLV2, SEG - CLV2 + INS, 10, "tube-in"))
s.append(text(K + 140 * u2 + P(9, 0), "2 × Ø10", "small"))
s.append(rect_on(A, u2, -CLV2, 8, 22, "fit"))
s.append(rect_on(S4, u2, -11, 34.2, 24.7, "servo2"))
s.append(circle(S4, 6, "horn")); s.append(circle(S4, 1.6, "pin"))
# came du ressort (rayon 20 sur le genou)
s.append(circle(K, 20, "cam"))
s.append(circle(K, 8, "bearing")); s.append(circle(K, 2.5, "pin"))
# ressort de genou le long de l'arrière de la cuisse + câble
# 2 ressorts côte à côte (vus superposés), ancrés sur l'avant du raccord haut de cuisse,
# câble Dyneema jusqu'au profil de came des joues du tibia (rayon 20 devant l'axe du genou)
sa = H + 76 * u1 - 15 * nb1; sb = H + 134 * u1 - 15 * nb1
s.append(rect_on(H + 72 * u1 - 15 * nb1, u1, -3, 3, 9, "fit"))          # patte d'ancrage
s.append(circle(sa, 1.8, "pin")); s.append(spring(sa, sb, turns=12, amp=4.5))
cable_end = K - 20 * nb1
s.append(line(sb, cable_end, "cable"))
s.append(circle(cable_end + 6 * u1, 1.6, "pin"))                       # serre-câble / tendeur M3
s.append(text(sa + P(16, -2), "ancrage M3", "small"))
s.append(text(cable_end + P(6, 14), "tendeur M3", "small"))
# leviers et bielles
s.append(line(S3, P1, "arm")); s.append(line(K, P2, "arm"))
s.append(line(S4, P3, "arm"));
s.append(line(P1, P2, "stud")); s.append(line(P3, P4, "stud"))     # goujons M3 jusqu'aux rotules
s.append(rect_on(P1, P2 - P1, RE, B1 - RE, 4, "rod"))
s.append(rect_on(P3, P4 - P3, RE, B2 - RE, 4, "rod"))
for p_, tag, off in ((P1, "a", P(-9, -5)), (P2, "b", P(-10, 8)), (P3, "c", P(-9, -6)), (P4, "d", P(-9, 9))):
    s.append(circle(p_, 3.2, "rodend")); s.append(circle(p_, 1.1, "pin"))
    s.append(circle(p_ + off, 4.2, "tag")); s.append(text(p_ + off + P(0, 1.9), tag, "tagt", "middle"))
# pied : chapes, levier talon, semelle
foot_top = GROUND - 8
s.append(f'<polygon class="fit" points="-12,{f(foot_top)} 12,{f(foot_top)} 9,{f(A[1]-4)} -9,{f(A[1]-4)}"/>')
s.append(line(A, P4, "arm"))
s.append(f'<rect class="plate" x="-35" y="{f(foot_top)}" width="100" height="4" rx="1"/>')
for x0, w0 in ((-30, 16), (18, 18), (40, 18)):     # évidements du pied
    s.append(f'<rect x="{x0}" y="{f(foot_top + 0.9)}" width="{w0}" height="2.2" rx="1" style="fill:var(--sheet)"/>')
s.append(f'<rect class="tpu" x="-35" y="{f(foot_top+4)}" width="100" height="4" rx="1.5"/>')
s.append(circle(A, 7, "bearing")); s.append(circle(A, 2.5, "pin"))
s.append(circle(H, 6, "horn")); s.append(circle(H, 1.6, "pin"))
# débattements des articulations
def arc_deg(c, r, a0, a1, label, lp):
    """Arc de débattement : angles depuis la verticale basse, positifs vers l'avant (+x)."""
    pa = c + r * P(math.sin(math.radians(a0)), math.cos(math.radians(a0)))
    pb = c + r * P(math.sin(math.radians(a1)), math.cos(math.radians(a1)))
    big = 1 if abs(a1 - a0) > 180 else 0
    sweep = 0 if a1 > a0 else 1
    s.append(f'<path class="arc" d="M{pt(pa)} A{r},{r} 0 {big} {sweep} {pt(pb)}" marker-start="url(#arw)" marker-end="url(#arw)"/>')
    s.append(text(lp, label, "arct"))
th = math.degrees(T)
arc_deg(H, 62, -30, 90, "hanche −30° / +90°", H + P(48, -8))
arc_deg(K, 46, th, th - 110, "genou 0–110°", P(-112, 222))
arc_deg(A, 34, 90 - 45, 90 + 45, "cheville ±45°", A + P(24, -26))
s.append(text(K + P(14, -40), "flexion dessinée : 25°", "small"))
# axes (repères)
for c in (H, K, A):
    s.append(line(c + P(-10, 0), c + P(10, 0), "axis")); s.append(line(c + P(0, -10), c + P(0, 10), "axis"))

# cotes
s.append(dim(H, K, 34, str(SEG), side=-1))
s.append(dim(K, A, 34, str(SEG), side=-1))
s.append(dim(H, H + 40 * u1, 22, "40", side=-1))
s.append(text(S3 + P(-50, 12), "S3 : 25 derrière l'axe", "small", "middle"))
s.append(dim(K, K + 35 * u2, 24, "35", side=-1))
s.append(text(S4 + P(-58, 14), "S4 : 25 derrière l'axe", "small", "middle"))
s.append(dim(P(-95, 0), P(-95, GROUND), 0, f"{round(GROUND)} (genou à 25°)"))
s.append(line(P(-40, 0), P(-98, 0), "ext"))
s.append(dim(P(78, A[1]), P(78, GROUND), 0, "50", side=-1))
s.append(line(A + P(10, 0), P(81, A[1]), "ext"))
s.append(dim(P(-35, GROUND + 14), P(0, GROUND + 14), 0, "35", side=-1))
s.append(dim(P(0, GROUND + 14), P(65, GROUND + 14), 0, "65", side=-1))
s.append(line(P(-35, GROUND + 8), P(-35, GROUND + 17), "ext")); s.append(line(P(65, GROUND + 8), P(65, GROUND + 17), "ext"))
s.append(line(P(0, A[1] + 10), P(0, GROUND + 17), "ext"))
# libellés bielles
mid1 = (P1 + P2) / 2; mid2 = (P3 + P4) / 2
ang1 = math.degrees(math.atan2((P2 - P1)[1], (P2 - P1)[0])); ang2 = math.degrees(math.atan2((P4 - P3)[1], (P4 - P3)[0]))
s.append(text(mid1 + nb1 * 8, f"B1 entraxe {round(B1)}", "dimt", "middle", ang1 - 180 if ang1 > 90 else ang1))
s.append(text(mid2 + P(-8, 0), f"B2 entraxe {round(B2)}", "dimt", "middle", ang2 - 180 if ang2 > 90 else ang2))
s.append(text(S3 + arm * 11 + P(-12, -3), "r 22", "small"))
s.append(text(K + arm * 11 + P(4, 10), "r 22", "small"))
s.append(text(P3 + P(-2, -4), "r 22", "small", "middle"))
s.append(text(P4 + P(0, -5), "r 22", "small", "middle"))
s.append(text(K + P(23, -16), "came r 20", "small"))
# repères
def side(t_, x, dy=0):
    return P(x, t_[1] + dy), t_
bal = [(P(-80, -100), P(-30, -80), 1), (P(-80, -68), P(-15, -63), 2), (P(-80, -30), P(-30, -4), 3),
       (P(110, -10), H + 52 * u1 + P(12, 0), 4)]
for n, (x, t_, dy) in enumerate([(120, H + 135 * u1 + P(5, 0), 0), (120, K + P(14, 6), 0),
                                  (-80, P1 + (P2 - P1) * 0.5, 0), (120, sa + (sb - sa) * 0.5, -25),
                                  (120, S4 + P(10, 8), 0), (120, K + 150 * u2 + P(5, 0), 0),
                                  (-80, P3 + (P4 - P3) * 0.5, 0), (120, A + P(8, 4), 0),
                                  (-80, P(-20, GROUND - 2), -10)], start=5):
    c_, tt = side(t_, x, dy)
    bal.append((c_, tt, n))
for c, t_, n in bal:
    s.append(balloon(c, t_, n))
s.append(text(P(-110, GROUND + 30), "VUE DE CÔTÉ · cotes en mm · genou fléchi de 25°", "cap"))
side_svg = "\n".join(s)

# ── Vue de face (bassin + haut des jambes) ────────────────────────────────────
v = []
v.append('<rect class="plate" x="-60" y="-84" width="120" height="8" rx="1.5"/>')
for sx in (-1, 1):
    hx = 45 * sx
    v.append(f'<rect class="servo" x="{f(hx-12.35)}" y="-76" width="24.7" height="35" rx="2"/>')
    v.append(circle(P(hx, -59), 5, "horn"))
    v.append(f'<path class="yoke" d="M{f(hx-16)},-50 H{f(hx+16)} V16 H{f(hx+11)} V-45 H{f(hx-11)} V16 H{f(hx-16)} Z"/>')
    v.append(f'<rect class="servo" x="{f(hx-11)}" y="-12.35" width="22" height="24.7" rx="2"/>')
    v.append(f'<rect class="fit" x="{f(hx-9)}" y="10" width="18" height="40"/>')
    v.append(f'<rect class="tube" x="{f(hx-6)}" y="50" width="12" height="40"/>')
    v.append(line(P(hx, -70), P(hx, 100), "axis"))
v.append(dim(P(-45, 100), P(45, 100), 8, "90 entre axes de hanche", side=1))
v.append(text(P(-60, -100), "VUE DE FACE · bassin", "cap"))
v.append(text(P(-60, 128), "S1 roulis : axe vers l'avant, au centre de chaque étrier", "small"))
front_svg = "\n".join(v)

if __name__ == "__main__":
    print(DIMS)
