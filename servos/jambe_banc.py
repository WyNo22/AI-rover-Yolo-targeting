"""
jambe_banc.py – Mise au point d'une jambe complète de LEO-S au banc (PC, adaptateur Waveshare cavalier sur B),
et marche simulée sur le PC.

Jambe fixée par le haut au bord d'une table, pied dans le vide (sauf « charge »). Les zéros sont faits
(sts_banc.py zero : jambe tendue, pied à plat = 2048 sur chaque servo).

  python jambe_banc.py marche --sim         marche des deux jambes animée sur le PC (sans robot)
  python jambe_banc.py butees               relève les limites de chaque articulation à la main
  python jambe_banc.py sens                 vérifie le sens de chaque articulation (+10°)
  python jambe_banc.py cycle                plie et déplie chaque articulation sur toute sa course
  python jambe_banc.py pied 40 30           pied 40 mm devant, 30 mm plus haut que la position debout
  python jambe_banc.py marche               la vraie jambe joue son rôle dans la marche (pied dans le vide)
  python jambe_banc.py charge               pied posé : flexions 0→60° pendant 5 min, mesures dans un CSV
  python jambe_banc.py repos                couple coupé sur la jambe

Options : --jambe D (ID 1–4, défaut) ou G (ID 5–8), --port, --baud.
Réglages enregistrés dans jambe_D.json / jambe_G.json (butées, sens, rapports des bielles).
"""
import argparse
import csv
import json
import math
import os
import sys
import time

# ── Géométrie (CAO Rév. J, docs/cad/jambe_cad.py) ─────────────────────────────
CUISSE, TIBIA = 200.0, 200.0          # entraxes hanche → genou → cheville (mm)
H_ROULIS = 63.5                       # axe de roulis au-dessus de l'axe de tangage de hanche
H_PIED = 53.25                        # cheville → dessous de la semelle
TALON, POINTE = 35.0, 65.0            # longueur du pied derrière / devant la cheville
H_DEBOUT = 380.0                      # hanche → cheville en position debout (genou plié ~36°)
ECART_HANCHES = 90.0                  # distance entre les deux hanches

ARTIC = ("roulis", "hanche", "genou", "cheville")
IDS = {"D": (1, 2, 3, 4), "G": (5, 6, 7, 8)}
BUTEES_CAO = {"roulis": (-20, 30), "hanche": (-30, 90), "genou": (0, 110), "cheville": (-40, 40)}
MARGE = 5.0                           # degrés gardés avant chaque butée relevée
PAS_PAR_DEGRE = 4096 / 360
SENS_ATTENDU = {"roulis": "la jambe s'écarte vers l'extérieur",
                "hanche": "la jambe part vers l'avant",
                "genou": "le genou se plie (tibia vers l'arrière)",
                "cheville": "la pointe du pied monte"}


# ── Cinématique ────────────────────────────────────────────────────────────────
def cinematique_inverse(x, z, y=0.0):
    """Cheville en (x devant, z sous la hanche, y vers l'extérieur) → angles en degrés, pied à plat.
    Conventions : hanche + = jambe vers l'avant, genou + = flexion, cheville + = pointe vers le haut,
    roulis + = jambe vers l'extérieur."""
    d = min(math.hypot(x, z), CUISSE + TIBIA - 0.1)
    genou = math.pi - math.acos(max(-1.0, min(1.0, (CUISSE ** 2 + TIBIA ** 2 - d * d) / (2 * CUISSE * TIBIA))))
    alpha = math.atan2(x, z)                                    # direction hanche → cheville (z positif vers le bas)
    beta = math.acos(max(-1.0, min(1.0, (CUISSE ** 2 + d * d - TIBIA ** 2) / (2 * CUISSE * d))))
    hanche = alpha + beta
    cheville = genou - hanche                                   # garde le pied parallèle au sol
    roulis = math.atan2(y, z + H_ROULIS)
    return {"roulis": math.degrees(roulis), "hanche": math.degrees(hanche),
            "genou": math.degrees(genou), "cheville": math.degrees(cheville)}


def cinematique_directe(q):
    """Angles (degrés) → points du plan sagittal : hanche, genou, cheville, talon, pointe (x, z vers le haut)."""
    h, g, c = (math.radians(q[k]) for k in ("hanche", "genou", "cheville"))
    genou = (CUISSE * math.sin(h), -CUISSE * math.cos(h))
    t = h - g                                                   # orientation du tibia
    cheville = (genou[0] + TIBIA * math.sin(t), genou[1] - TIBIA * math.cos(t))
    p = t + c                                                   # inclinaison du pied (0 = à plat)
    sol = (cheville[0] + H_PIED * math.sin(p), cheville[1] - H_PIED * math.cos(p))
    talon = (sol[0] - TALON * math.cos(p), sol[1] - TALON * math.sin(p))
    pointe = (sol[0] + POINTE * math.cos(p), sol[1] + POINTE * math.sin(p))
    return {"hanche": (0.0, 0.0), "genou": genou, "cheville": cheville, "talon": talon, "pointe": pointe}


def trajectoire_pied(phase, pas=50.0, levee=25.0, appui=0.6):
    """Position de la cheville (x, dz) sur un cycle de marche : appui (le pied recule au sol), puis vol (il revient)."""
    phase %= 1.0
    if phase < appui:
        return pas / 2 - pas * phase / appui, 0.0
    s = (phase - appui) / (1 - appui)
    return -pas / 2 + pas * (1 - math.cos(math.pi * s)) / 2, levee * math.sin(math.pi * s)


def pose_marche(phase, pas=50.0, levee=25.0, roulis=4.0, cote="D"):
    """Angles d'une jambe à un instant du cycle ; la jambe gauche est décalée d'un demi-cycle."""
    if cote == "G":
        phase += 0.5
    x, dz = trajectoire_pied(phase, pas, levee)
    q = cinematique_inverse(x, H_DEBOUT - dz)
    q["roulis"] = roulis * math.sin(2 * math.pi * (phase % 1.0))   # bascule du bassin vers la jambe d'appui
    return q


# ── Réglages de la jambe ──────────────────────────────────────────────────────
def fichier_reglages(cote):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), f"jambe_{cote}.json")


def charger(cote):
    r = {"butees": {k: list(v) for k, v in BUTEES_CAO.items()}, "sens": {k: 1 for k in ARTIC},
         "rapport": {k: 1.0 for k in ARTIC}, "butees_relevees": False}
    try:
        with open(fichier_reglages(cote)) as f:
            r.update(json.load(f))
    except FileNotFoundError:
        pass
    return r


def sauver(cote, r):
    with open(fichier_reglages(cote), "w") as f:
        json.dump(r, f, indent=2)


def borne(r, artic, deg):
    lo, hi = r["butees"][artic]
    m = MARGE if r.get("butees_relevees") else 0.0
    return max(lo + m, min(hi - m, deg))


def vers_pas(r, artic, deg):
    deg = borne(r, artic, deg)
    return int(round(2048 + r["sens"][artic] * r["rapport"][artic] * deg * PAS_PAR_DEGRE))


def vers_deg(r, artic, pas):
    return (pas - 2048) / (r["sens"][artic] * r["rapport"][artic] * PAS_PAR_DEGRE)


# ── Pilotage ──────────────────────────────────────────────────────────────────
def envoyer(bus, S, r, ids, q):
    """Une trame SYNC WRITE pour les 4 servos (vitesse maximale : la trajectoire fait le lissage)."""
    params = [S.CONSIGNE, 6]
    for artic, sid in zip(ARTIC, ids):
        p = vers_pas(r, artic, q[artic])
        params += [sid, p & 0xFF, p >> 8, 0, 0, 0, 0]
    bus.echange(S.DIFFUSION, 0x83, params)


def aller_doucement(bus, S, r, ids, q, vitesse=400):
    for artic, sid in zip(ARTIC, ids):
        bus.aller(sid, vers_pas(r, artic, q[artic]), vitesse=vitesse)
    for artic, sid in zip(ARTIC, ids):
        bus.attendre(sid, vers_pas(r, artic, q[artic]), vitesse=vitesse)


def jouer(bus, S, r, ids, q_de_t, duree, hz=50):
    """Joue une trajectoire q(t) pendant `duree` secondes à `hz` consignes par seconde."""
    for sid in ids:
        bus.ecrire8(sid, S.ACCEL, 0)
        bus.ecrire8(sid, S.COUPLE_ON, 1)
    t0 = time.monotonic()
    pics = {sid: [0.0, 0, 0] for sid in ids}
    n = 0
    while True:
        t = time.monotonic() - t0
        if t >= duree:
            break
        envoyer(bus, S, r, ids, q_de_t(t))
        n += 1
        if n % 10 == 0:                                         # mesures 5 fois par seconde
            for sid in ids:
                try:
                    e = bus.etat(sid)
                    p = pics[sid]
                    p[0], p[1], p[2] = max(p[0], abs(e["charge_%"])), max(p[1], abs(e["courant_mA"])), max(p[2], e["temp_C"])
                except S.ErreurBus:
                    pass
        time.sleep(max(0.0, n / hz - (time.monotonic() - t0)))
    return pics


def afficher_pics(pics, ids, noms=ARTIC):
    for artic, sid in zip(noms, ids):
        c, i, t = pics[sid]
        alerte = "  ⚠ force beaucoup" if c > 60 else ("  ⚠ chaud" if t > 50 else "")
        print(f"  {artic:9s} (ID {sid}) : charge max {c:5.1f} %, courant max {i:5d} mA, {t} °C{alerte}")


def cmd_butees(bus, S, r, ids, cote, saisie=None):
    saisie = saisie or input
    print("Couple coupé : amène chaque articulation à la main jusqu'à sa limite, doucement.")
    for sid in ids:
        bus.ecrire8(sid, S.COUPLE_ON, 0)
    for artic, sid in zip(ARTIC, ids):
        mesures = []
        for bout in ("une limite", "l'autre limite"):
            saisie(f"→ {artic} : amène-le à {bout}, puis Entrée…")
            mesures.append(vers_deg(r, artic, bus.lire16(sid, S.POSITION)))
        lo, hi = sorted(mesures)
        r["butees"][artic] = [round(lo, 1), round(hi, 1)]
        print(f"  {artic} : {lo:+.1f}° → {hi:+.1f}°  (la jambe s'arrêtera à {MARGE:.0f}° de chaque butée)")
    r["butees_relevees"] = True
    sauver(cote, r)
    print(f"✓ Butées enregistrées dans {os.path.basename(fichier_reglages(cote))}")


def cmd_sens(bus, S, r, ids, cote, saisie=None):
    saisie = saisie or input
    aller_doucement(bus, S, r, ids, {k: 0.0 for k in ARTIC})
    for artic, sid in zip(ARTIC, ids):
        q = {k: 0.0 for k in ARTIC}
        q[artic] = 10.0 if artic != "genou" else 20.0
        aller_doucement(bus, S, r, ids, q, vitesse=300)
        rep = saisie(f"→ {artic} : est-ce que {SENS_ATTENDU[artic]} ? (o/n) ").strip().lower()
        if rep == "n":
            r["sens"][artic] *= -1
            lo, hi = r["butees"][artic]
            r["butees"][artic] = [-hi, -lo]                     # mêmes butées physiques, dans le nouveau sens
            print(f"  sens de {artic} inversé (butées : {-hi:+.1f}° → {-lo:+.1f}°)")
        aller_doucement(bus, S, r, ids, {k: 0.0 for k in ARTIC}, vitesse=300)
    sauver(cote, r)
    print("✓ Sens enregistrés.")


def cmd_cycle(bus, S, r, ids):
    if not r.get("butees_relevees"):
        print("⚠ butées pas encore relevées : je prends celles de la CAO (lance « butees » d'abord pour être tranquille)")
    for artic, sid in zip(ARTIC, ids):
        lo, hi = r["butees"][artic]
        a, b = lo + MARGE, hi - MARGE
        print(f"→ {artic} : {a:+.0f}° ↔ {b:+.0f}°")

        def q_de_t(t, a=a, b=b, artic=artic):
            q = {k: 0.0 for k in ARTIC}
            q[artic] = a + (b - a) * (1 - math.cos(2 * math.pi * t / 4.0)) / 2     # aller-retour en 4 s
            return q
        q0 = q_de_t(0)
        aller_doucement(bus, S, r, ids, q0)
        afficher_pics(jouer(bus, S, r, ids, q_de_t, 8.0), [sid], [artic])
    aller_doucement(bus, S, r, ids, {k: 0.0 for k in ARTIC})
    print("✓ Cycle fini. Normal : 30–50 % de charge (la jambe est soulevée, les ressorts tirent au genou) ;\n"
          "  à surveiller : un pic soudain, un claquement, ou plus de 50 °C.")


def cmd_pied(bus, S, r, ids, dx, dz, dy):
    q = cinematique_inverse(dx, H_DEBOUT - dz, dy)
    print("  angles : " + ", ".join(f"{k} {v:+.1f}°" for k, v in q.items()))
    aller_doucement(bus, S, r, ids, q)
    print("✓ Le pied doit être à la position demandée et rester parallèle à la table.")


def cmd_marche_reelle(bus, S, r, ids, cote, a):
    q_de_t = lambda t: pose_marche(t / a.periode, a.pas, a.levee, a.roulis, cote)
    print(f"Position de départ (lentement)… puis {a.cycles} pas de {a.periode:.1f} s. Ctrl+C pour arrêter.")
    aller_doucement(bus, S, r, ids, q_de_t(0.0))
    afficher_pics(jouer(bus, S, r, ids, q_de_t, a.cycles * a.periode), ids)
    aller_doucement(bus, S, r, ids, cinematique_inverse(0, H_DEBOUT))
    print("✓ Marche finie, jambe en position debout.")


def cmd_charge(bus, S, r, ids, cote, minutes, saisie=None):
    saisie = saisie or input
    saisie("Pose le pied sur la balance (environ 1,2 kg d'appui), puis Entrée…")
    nom = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"charge_{cote}_{time.strftime('%Y%m%d_%H%M%S')}.csv")
    q_de_t = lambda t: cinematique_inverse(0, 398 - 52 * (1 - math.cos(2 * math.pi * t / 3.0)) / 2)   # genou ≈ 5° → 60°, 3 s
    aller_doucement(bus, S, r, ids, q_de_t(0))
    for sid in ids:
        bus.ecrire8(sid, S.ACCEL, 0)
    t0 = time.monotonic()
    pire = {sid: [0.0, 0] for sid in ids}
    with open(nom, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s"] + [f"{a}_{m}" for a in ARTIC for m in ("pos", "charge_%", "courant_mA", "temp_C")])
        while time.monotonic() - t0 < minutes * 60:
            t = time.monotonic() - t0
            envoyer(bus, S, r, ids, q_de_t(t))
            ligne = [round(t, 2)]
            for sid in ids:
                try:
                    e = bus.etat(sid)
                    ligne += [e["position"], e["charge_%"], e["courant_mA"], e["temp_C"]]
                    pire[sid] = [max(pire[sid][0], abs(e["charge_%"])), max(pire[sid][1], e["temp_C"])]
                except S.ErreurBus:
                    ligne += ["", "", "", ""]
            w.writerow(ligne)
            if any(p[1] >= 60 for p in pire.values()):
                print("\n⚠ un servo atteint 60 °C : arrêt du test")
                break
            print(f"  {t:5.0f} s / {minutes * 60:.0f} s · pires : " +
                  " | ".join(f"{a} {pire[s][0]:.0f} % {pire[s][1]} °C" for a, s in zip(ARTIC, ids)), end="\r")
            time.sleep(0.1)
    print()
    for sid in ids:
        bus.ecrire8(sid, S.COUPLE_ON, 0)
    ok = all(p[0] < 60 and p[1] < 50 for p in pire.values())
    print(("✓ Test réussi" if ok else "⚠ À regarder") + f" (objectif : < 60 % de charge, < 50 °C). Mesures : {os.path.basename(nom)}")


# ── Simulation (sans robot) ───────────────────────────────────────────────────
def simuler(a, gif=None, images=None):
    """Marche des deux jambes animée : vue de côté (tapis roulant) et vue de face (bascule du bassin)."""
    import matplotlib
    if gif or images is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import animation
    r = {"butees": {k: list(v) for k, v in BUTEES_CAO.items()}, "butees_relevees": False}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 6), gridspec_kw={"width_ratios": [2, 1]})
    sol = -(H_DEBOUT + H_PIED)
    for ax, titre in ((ax1, "côté : marche sur tapis roulant"), (ax2, "face : bascule du bassin")):
        ax.set_aspect("equal"); ax.axhline(sol, color="0.6", lw=1); ax.set_title(titre, fontsize=10)
        ax.set_ylim(sol - 30, 110)
    ax1.set_xlim(-160, 180); ax2.set_xlim(-150, 150)
    traits = {c: ax1.plot([], [], "-o", lw=4, ms=5, color=col, label=f"jambe {c}")[0] for c, col in (("D", "tab:blue"), ("G", "tab:orange"))}
    face = {c: ax2.plot([], [], "-o", lw=4, ms=5, color=col)[0] for c, col in (("D", "tab:blue"), ("G", "tab:orange"))}
    bassin, = ax2.plot([], [], "-", lw=6, color="0.3")
    texte = ax1.text(-155, 75, "", fontsize=8, va="center")
    ax1.legend(loc="lower left", fontsize=8)
    nb = int(a.cycles * a.periode * 25)

    def image(i):
        t = i / 25
        phase = t / a.periode
        for c in ("D", "G"):
            q = pose_marche(phase, a.pas, a.levee, a.roulis, c)
            q = {k: borne(r, k, v) for k, v in q.items()}
            p = cinematique_directe(q)
            xs = [p[k][0] for k in ("hanche", "genou", "cheville", "talon", "pointe", "cheville")]
            zs = [p[k][1] for k in ("hanche", "genou", "cheville", "talon", "pointe", "cheville")]
            traits[c].set_data(xs, zs)
            s = 1 if c == "G" else -1                           # vue de face : la jambe G apparaît à droite de l'image
            hx = s * ECART_HANCHES / 2
            ro = math.radians(q["roulis"]) * s
            L = -p["cheville"][1] + H_ROULIS
            face[c].set_data([hx, hx + L * math.sin(ro)], [H_ROULIS, H_ROULIS - L * math.cos(ro)])
        qd = pose_marche(phase, a.pas, a.levee, a.roulis, "D")
        bassin.set_data([-ECART_HANCHES / 2 - 10, ECART_HANCHES / 2 + 10], [H_ROULIS, H_ROULIS])
        texte.set_text(f"t = {t:4.1f} s · pas {a.pas:.0f} mm · levée {a.levee:.0f} mm · période {a.periode:.1f} s\n"
                       f"jambe D : hanche {qd['hanche']:+5.1f}° genou {qd['genou']:5.1f}° cheville {qd['cheville']:+5.1f}°")
        return list(traits.values()) + list(face.values()) + [bassin, texte]

    if images is not None:                                     # pour les tests
        for i in images:
            image(i)
        plt.close(fig)
        return True
    anim = animation.FuncAnimation(fig, image, frames=nb, interval=40, blit=False)
    if gif:
        anim.save(gif, writer=animation.PillowWriter(fps=25))
        print(f"✓ Animation enregistrée : {gif}")
    else:
        plt.show()
    return True


# ── Programme ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Mise au point d'une jambe de LEO-S")
    ap.add_argument("--jambe", choices=["D", "G"], default="D")
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=1_000_000)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nom in ("butees", "sens", "cycle", "repos"):
        sp.add_parser(nom)
    s = sp.add_parser("pied"); s.add_argument("dx", type=float); s.add_argument("dz", type=float)
    s.add_argument("dy", type=float, nargs="?", default=0.0)
    s = sp.add_parser("marche")
    s.add_argument("--sim", action="store_true", help="animation sur le PC, sans robot")
    s.add_argument("--gif", help="avec --sim : enregistre l'animation dans ce fichier au lieu de l'afficher")
    s.add_argument("--cycles", type=int, default=6)
    s.add_argument("--periode", type=float, default=1.2, help="durée d'un pas complet (s)")
    s.add_argument("--pas", type=float, default=50.0, help="longueur du pas (mm)")
    s.add_argument("--levee", type=float, default=25.0, help="hauteur de levée du pied (mm)")
    s.add_argument("--roulis", type=float, default=4.0, help="bascule du bassin (degrés)")
    s = sp.add_parser("charge"); s.add_argument("--minutes", type=float, default=5.0)
    a = ap.parse_args()

    if a.cmd == "marche" and a.sim:
        simuler(a, a.gif)
        return

    import sts_banc as S
    port = a.port or S.trouver_port()
    bus = S.Bus(port, a.baud)
    ids = IDS[a.jambe]
    r = charger(a.jambe)
    print(f"Port {port} · jambe {a.jambe} (ID {ids[0]}–{ids[-1]})")
    try:
        manquants = [i for i in ids if not bus.ping(i)]
        if manquants:
            sys.exit(f"✗ servo(s) {manquants} absent(s) : alimentation, câble de la chaîne, cavalier sur B ?")
        if a.cmd == "butees":
            cmd_butees(bus, S, r, ids, a.jambe)
        elif a.cmd == "sens":
            cmd_sens(bus, S, r, ids, a.jambe)
        elif a.cmd == "cycle":
            cmd_cycle(bus, S, r, ids)
        elif a.cmd == "pied":
            cmd_pied(bus, S, r, ids, a.dx, a.dz, a.dy)
        elif a.cmd == "marche":
            cmd_marche_reelle(bus, S, r, ids, a.jambe, a)
        elif a.cmd == "charge":
            cmd_charge(bus, S, r, ids, a.jambe, a.minutes)
        elif a.cmd == "repos":
            for sid in ids:
                bus.ecrire8(sid, S.COUPLE_ON, 0)
            print("✓ Couple coupé, jambe libre.")
    except S.ErreurBus as e:
        sys.exit(f"✗ {e}")
    except KeyboardInterrupt:
        print("\nArrêt demandé : couple coupé.")
        for sid in ids:
            try:
                bus.ecrire8(sid, S.COUPLE_ON, 0)
            except S.ErreurBus:
                pass
    finally:
        bus.close()


if __name__ == "__main__":
    main()
