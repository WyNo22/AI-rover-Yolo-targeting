import json, math, sys
import stabilite_lipm as sim
feet_opts = [("85×55 (actuel)", (0.025, 0.060, 0.0275, 0.0275)),
             ("100×65", (0.035, 0.065, 0.0325, 0.0325)),
             ("110×70, décalé 5 ext.", (0.040, 0.070, 0.030, 0.040))]
gaits = [(0.10, 0.35, 0.10), (0.13, 0.32, 0.08), (0.16, 0.30, 0.06)]
rows = []
for fname, fo in feet_opts:
    heel, toe = fo[0], fo[1]
    center = (toe - heel) / 2
    for st, ts, td in gaits:
        for comp, frac in (("sans", 1.0), ("avec", 0.3)):
            # ZMP visé au centre du pied
            orig = sim.walk
            def w2(step, t_ss, t_ds, **kw):
                kw["zmp_fwd"] = center
                return orig(step, t_ss, t_ds, **kw)
            sim.walk = w2
            r, _ = sim.analyse(st, ts, td, fo)
            sim.walk = orig
            # recalcule les marges avant/arrière avec la fraction de perturbation résiduelle
            d = r["jambe_air_mm"]
            r["marge_av_mm"] = round(r["marge_av_mm"] + d * (1 - frac), 1)
            r["marge_ar_mm"] = round(r["marge_ar_mm"] + d * (1 - frac), 1)
            w = math.sqrt(9.81 / 0.5)
            r["poussee_av_ms"] = round(max(r["marge_av_mm"], 0) / 1000 * w, 2)
            r["poussee_ar_ms"] = round(max(r["marge_ar_mm"], 0) / 1000 * w, 2)
            r["pied"], r["jambe_comp"] = fname, comp
            rows.append(r)
for r in rows:
    print(f'{r["pied"]:24s} v={r["vitesse_ms"]:.2f} jambe {r["jambe_comp"]:4s} | av {r["marge_av_mm"]:6.1f} ar {r["marge_ar_mm"]:6.1f} lat {r["marge_lat_mm"]:5.1f} mm | poussée av {r["poussee_av_ms"]} ar {r["poussee_ar_ms"]} lat {r["poussee_lat_ms"]} m/s | balanc {r["balancement_mm"]}')
json.dump(rows, open(__import__("os").path.join(__import__("os").path.dirname(__file__), "res_pieds.json"), "w"), ensure_ascii=False)
