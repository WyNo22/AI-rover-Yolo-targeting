"""Test de stabilité LEO-S : modèle du pendule inverse linéaire (LIPM) + commande prédictive de Kajita.
Repère : x avant, y gauche (m). Pieds à ±HIP de l'axe, ZMP visé au centre du pied pendant l'appui simple."""
import json, math, sys
import numpy as np

g = 9.81
def preview_gains(zc, dt, N, Qe=1.0, R=1e-6):
    A = np.array([[1, dt, dt*dt/2], [0, 1, dt], [0, 0, 1]])
    B = np.array([[dt**3/6], [dt*dt/2], [dt]])
    C = np.array([[1, 0, -zc/g]])
    # système augmenté (erreur intégrée)
    Ab = np.block([[np.eye(1), C @ A], [np.zeros((3, 1)), A]])
    Bb = np.vstack([C @ B, B]); Ib = np.vstack([np.eye(1), np.zeros((3, 1))])
    Q = np.zeros((4, 4)); Q[0, 0] = Qe
    P = Q.copy()
    for _ in range(5000):
        K = np.linalg.solve(R + Bb.T @ P @ Bb, Bb.T @ P @ Ab)
        Pn = Ab.T @ P @ Ab - Ab.T @ P @ Bb @ K + Q
        if np.max(np.abs(Pn - P)) < 1e-12: P = Pn; break
        P = Pn
    K = np.linalg.solve(R + Bb.T @ P @ Bb, Bb.T @ P @ Ab)
    Gi, Gx = K[0, 0], K[0, 1:]
    Ac = Ab - Bb @ K
    X = -Ac.T @ P @ Ib
    Gd = np.zeros(N); Gd[0] = -Gi
    for i in range(1, N):
        Gd[i] = (np.linalg.solve(R + Bb.T @ P @ Bb, Bb.T @ X)).item()
        X = Ac.T @ X
    return A, B, C, Gi, Gx, Gd

def walk(step, t_ss, t_ds, nsteps=8, zc=0.50, hip=0.045, zmp_fwd=0.010, dt=0.005, prev=1.6):
    """Réf. ZMP : centre du pied (zmp_fwd devant la cheville), transfert linéaire en double appui."""
    N = int(prev / dt)
    A, B, C, Gi, Gx, Gd = preview_gains(zc, dt, N)
    feet = [(0.0, -hip), (0.0, hip)]                       # départ pieds joints
    for k in range(1, nsteps + 1):
        feet.append((k * step, hip if k % 2 == 0 else -hip))
    feet.append((nsteps * step, hip if nsteps % 2 else -hip))  # pieds réunis à la fin
    seg = []                                               # (durée, zmp début, zmp fin, pied d'appui)
    t0 = (0.0, 0.0)
    seg.append((1.0, t0, t0, None))
    for i in range(2, len(feet)):
        sup = feet[i - 1]
        zs = (sup[0] + zmp_fwd, sup[1])
        prevz = seg[-1][2]
        seg.append((t_ds, prevz, zs, None))
        seg.append((t_ss, zs, zs, i - 1))
    endz = ((feet[-1][0] + feet[-2][0]) / 2 + zmp_fwd, 0.0)
    seg.append((t_ds, seg[-1][2], endz, None)); seg.append((1.5, endz, endz, None))
    ref, sup = [], []
    for d, a, b, s in seg:
        n = int(round(d / dt))
        for j in range(n):
            u = j / n
            ref.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)); sup.append(s)
    ref = np.array(ref); T = len(ref)
    refp = np.vstack([ref, np.repeat(ref[-1:], N, 0)])
    out = {}
    for ax in (0, 1):
        x = np.zeros((3, 1)); x[0, 0] = ref[0, ax]; e = 0.0
        com, zmp = [], []
        for k in range(T):
            p = (C @ x).item(); e += p - refp[k, ax]
            u = -Gi * e - (Gx @ x).item() - Gd[1:] @ refp[k + 1:k + N, ax] if False else \
                -Gi * e - (Gx @ x).item() - sum(Gd[i] * refp[k + i, ax] for i in range(1, N))
            x = A @ x + B * u
            com.append(x[0, 0]); zmp.append((C @ x).item())
        out[ax] = (np.array(com), np.array(zmp))
    return feet, sup, ref, out, dt

def analyse(step, t_ss, t_ds, foot, zc=0.50, hip=0.045, swing_err=True, ctrl_err=0.005):
    """foot = (talon, pointe, demi-largeur intérieure, demi-largeur extérieure) en m depuis la cheville."""
    heel, toe, win, wout = foot
    feet, sup, ref, out, dt = walk(step, t_ss, t_ds, zc=zc, hip=hip)
    w = math.sqrt(g / zc)
    comx, zx = out[0]; comy, zy = out[1]
    vx = np.gradient(comx, dt); vy = np.gradient(comy, dt)
    # perturbation ZMP due à la jambe en l'air (masse 0,30 kg, CoM ~0,25 m, profil min-jerk sur 2*step*0,5)
    leg_m, M = 0.30, 2.1
    a_pk = 5.77 * (step) / t_ss**2
    d_swing = leg_m * a_pk * 0.25 / (M * g) if swing_err else 0.0
    res = {"marge_av": 1e9, "marge_ar": 1e9, "marge_lat": 1e9, "cap_av": 1e9, "cap_ar": 1e9, "cap_lat": 1e9}
    for k, s in enumerate(sup):
        if s is None: continue
        fx, fy = feet[s]
        side = 1 if fy > 0 else -1
        rx, ry = zx[k] - fx, (zy[k] - fy) * side          # ry > 0 = vers l'extérieur
        res["marge_av"] = min(res["marge_av"], toe - rx - d_swing - ctrl_err)
        res["marge_ar"] = min(res["marge_ar"], rx + heel - d_swing - ctrl_err)
        res["marge_lat"] = min(res["marge_lat"], min(wout - ry, ry + win) - ctrl_err)
        # point de capture : CoM + v/ω doit rester dans le pied pour récupérer sans faire de pas
        cpx = comx[k] + vx[k] / w - fx; cpy = (comy[k] + vy[k] / w - fy) * side
    lat_sway = float(np.max(np.abs(comy)))
    v = step / (t_ss + t_ds)
    # vitesse de poussée encaissable par la cheville (sans pas) = marge × ω
    return {"pas_mm": round(step * 1000), "periode_s": t_ss + t_ds, "vitesse_ms": round(v, 2),
            "marge_av_mm": round(res["marge_av"] * 1000, 1), "marge_ar_mm": round(res["marge_ar"] * 1000, 1),
            "marge_lat_mm": round(res["marge_lat"] * 1000, 1),
            "poussee_av_ms": round(max(res["marge_av"], 0) * w, 2), "poussee_ar_ms": round(max(res["marge_ar"], 0) * w, 2),
            "poussee_lat_ms": round(max(res["marge_lat"], 0) * w, 2),
            "balancement_mm": round(lat_sway * 1000, 1), "jambe_air_mm": round(d_swing * 1000, 1)}, (feet, sup, ref, out, dt)

if __name__ == "__main__":
    feet_opts = {"actuel 85×55 (25/60)": (0.025, 0.060, 0.0275, 0.0275),
                 "95×65 (30/65)": (0.030, 0.065, 0.0325, 0.0325),
                 "100×70 (35/65), décalé ext.": (0.035, 0.065, 0.030, 0.040)}
    gaits = [(0.10, 0.35, 0.10), (0.13, 0.32, 0.08), (0.16, 0.30, 0.06)]
    rows = []
    for fname, fo in feet_opts.items():
        for st, ts, td in gaits:
            r, _ = analyse(st, ts, td, fo)
            r["pied"] = fname; rows.append(r)
            print(json.dumps(r, ensure_ascii=False))
    json.dump(rows, open(sys.argv[1] if len(sys.argv) > 1 else "res.json", "w"), ensure_ascii=False)
