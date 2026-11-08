# Étape 6 – tension de la 3S sur GP26 : pont 100 kΩ (+ 3S → GP26) et 33 kΩ (GP26 → AGND, broche 33),
# condensateur 100 nF en parallèle sur la 33 k. JAMAIS la 4S sur ce pont (4,2 V sur l'entrée : elle grille).
import time

import brochage as B
from batterie import Batterie
from sts import Bus, ErreurBus


def main(tours=20, saisie=input):
    bat = Batterie(B.ADC_BATTERIE, B.PONT_BATTERIE, B.CAL_BATTERIE)
    bus = Bus(B.uart_servos())
    servo = None
    for i in B.IDS:                             # premier servo qui répond, pour comparer sa tension
        if bus.ping(i):
            servo = i
            break

    for _ in range(tours):
        v = bat.tension()
        ligne = "batterie %.2f V (%.2f V par élément)" % (v, v / 3)
        if servo is not None:
            try:
                ligne += " · lue par le servo %d : %.1f V" % (servo, bus.etat(servo)["tension"])
            except ErreurBus:
                pass
        if v < B.V_CRITIQUE:
            ligne += "  ✗ CRITIQUE : recharge"
        elif v < B.V_BASSE:
            ligne += "  ⚠ basse"
        print(ligne + "    ", end="\r")
        time.sleep_ms(250)
    print()

    m = saisie("Tension mesurée au multimètre aux bornes de la batterie (Entrée pour passer) : ").strip().replace(",", ".")
    if m:
        brute = bat.tension(n=256, calibree=False)
        cal = float(m) / brute
        print("→ mets dans brochage.py : CAL_BATTERIE = %.4f" % cal)
        if abs(cal - 1) > 0.08:
            print("⚠ écart de plus de 8 % : vérifie les valeurs des résistances du pont et la masse AGND.")
        return cal
    return None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêté.")
