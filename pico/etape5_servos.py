# Étape 5 – bus servo piloté par le Pico : adaptateur Waveshare, cavalier sur A.
# Pico GP20 (TX) → entrée de l'adaptateur · sortie de l'adaptateur → GP21 (RX) · GND ↔ GND · 12 V sur le bornier.
# Avant de brancher : la sortie de l'adaptateur est la broche qui lit ~3,3 V au multimètre (au repos).
# Si elle lit ~5 V : pont 1 kΩ + 2 kΩ sur la ligne qui va vers GP21.
import time

import brochage as B
from sts import Bus, ErreurBus, POSITION

TEST_MOUVEMENT = True                          # demande avant de faire bouger chaque servo de ±100 pas (±9°)


def info(bus, sid):
    e = bus.etat(sid)
    print("  ID %d %-14s pos %4d (%+6.1f°)  %4.1f V  %2d °C  charge %+5.1f %%  %4d mA"
          % (sid, B.ARTICULATIONS.get(sid, ""), e["position"], (e["position"] - 2048) * 360 / 4096,
             e["tension"], e["temp"], e["charge"], e["courant"]))
    return e


def vitesse_boucle(bus, ids, n=50):
    """Lit les positions de tous les servos puis renvoie une consigne groupée : c'est le cycle de la future boucle."""
    pos = {}
    t0 = time.ticks_us()
    for _ in range(n):
        for i in ids:
            pos[i] = bus.position(i)
        bus.sync_positions(pos)                # consigne = position actuelle : rien ne bouge
    dt = time.ticks_diff(time.ticks_us(), t0) / n
    return 1000000 / dt, dt / 1000


def mouvement(bus, sid):
    p0 = bus.position(sid)
    for cible in (p0 + 100, p0 - 100, p0):
        bus.aller(sid, cible, vitesse=300)
        ok = bus.attendre(sid, cible)
        print("    → %4d : %s %d" % (cible, "arrivé à" if ok else "⚠ pas arrivé, à", bus.position(sid)))
    bus.couple(sid, False)


def main(saisie=input):
    bus = Bus(B.uart_servos())
    trouves = bus.scanner(range(0, 21))
    if not trouves:
        print("✗ Aucun servo ne répond. Dans l'ordre :")
        print("  1. 12 V branché sur le bornier de l'adaptateur ?")
        print("  2. cavalier sur A (pas B) ?")
        print("  3. GND du Pico relié au GND de l'adaptateur ?")
        print("  4. TX/RX inversés ? (GP20 = TX du Pico, GP21 = RX)")
        return None
    uniques = sorted(set(trouves))
    doublons = sorted(set(i for i in trouves if trouves.count(i) > 1))
    print("✓ %d servo(s) répondent : %s" % (len(uniques), uniques))
    if doublons:
        print("⚠ plusieurs servos sur l'ID %s : à corriger au banc (sts_banc.py, cavalier sur B)" % doublons)
    manquants = [i for i in B.IDS if i not in uniques]
    if manquants:
        print("⚠ manquants : %s (câble de la chaîne ? servo débranché ?)" % manquants)

    for i in uniques:
        try:
            info(bus, i)
        except ErreurBus as e:
            print("  ✗ %s" % e)

    ids = [i for i in B.IDS if i in uniques]
    if ids:
        hz, ms = vitesse_boucle(bus, ids)
        print("\nCycle « lire %d positions + consigne groupée » : %.2f ms → %.0f Hz max" % (len(ids), ms, hz))

    if TEST_MOUVEMENT and ids and saisie("\nFaire bouger chaque servo de ±9°, l'un après l'autre ? (o/n) ").strip().lower() == "o":
        for i in ids:
            print("  ID %d %s" % (i, B.ARTICULATIONS.get(i, "")))
            mouvement(bus, i)
        print("✓ Mouvements finis, couple libéré.")
    return uniques


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêté.")
