"""Vue de dessus : empreintes, trajectoire du ZMP et du centre de gravité (marche à 0,33 m/s, pied 100×65)."""
import math, numpy as np
import stabilite_lipm as sim
HEEL, TOE, HW = 0.035, 0.065, 0.0325
center = (TOE - HEEL) / 2
feet, sup, ref, out, dt = sim.walk(0.13, 0.32, 0.08, nsteps=6, zmp_fwd=center)
comx, zx = out[0]; comy, zy = out[1]
S = 1000                     # mm
def P(x, y): return x * S, -y * S
def f(v): return f"{v:.1f}"
o = []
xmax = max(fx for fx, fy in feet) + TOE + 0.03
# grille légère tous les 100 mm
for gx in range(0, int(xmax * 10) + 1):
    X = gx * 100
    o.append(f'<line class="grid" x1="{X}" y1="-95" x2="{X}" y2="95"/>')
    o.append(f'<text class="tick" x="{X}" y="112" text-anchor="middle">{X}</text>')
o.append('<text class="tick" x="-60" y="112">x (mm)</text>')
for i, (fx, fy) in enumerate(feet):
    x0, y0 = P(fx - HEEL, fy + HW)
    w, h = (HEEL + TOE) * S, 2 * HW * S
    side = "gauche" if fy > 0 else "droit"
    o.append(f'<rect class="foot" x="{f(x0)}" y="{f(y0)}" width="{f(w)}" height="{f(h)}" rx="6">'
             f'<title>Pied {side}, pose n° {i} : x = {round(fx*1000)} mm</title></rect>')
    cx, cy = P(fx, fy)
    o.append(f'<circle class="ankle" cx="{f(cx)}" cy="{f(cy)}" r="2.5"/>')
def path(xs, ys, cls):
    pts = " ".join(f"{f(x*S)},{f(-y*S)}" for x, y in zip(xs[::4], ys[::4]))
    return f'<polyline class="{cls}" points="{pts}"/>'
o.append(path(zx, zy, "zmp")); o.append(path(comx, comy, "com"))
# libellés directs
k = int(len(comx) * 0.45)
o.append(f'<text class="lab-com" x="{f(comx[k]*S + 8)}" y="{f(-comy[k]*S - 6)}">centre de gravité</text>')
k2 = int(len(zx) * 0.55)
o.append(f'<text class="lab-zmp" x="{f(zx[k2]*S + 6)}" y="{f(-zy[k2]*S + 16)}">point d\'appui (ZMP)</text>')
o.append(f'<line class="axis" x1="-70" y1="0" x2="{f(xmax*S)}" y2="0"/>')
top_svg = "\n".join(o)
VB = f"-70 -100 {round(xmax*S)+90} 225"
if __name__ == "__main__":
    print(VB, len(top_svg))
