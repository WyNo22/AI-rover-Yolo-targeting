# Étape 4 – FSR402B + ADS1015 : lecture des appuis, puis choix de la résistance du pont par des pesées.
# Chaque FSR : une patte au 3V3, l'autre sur A0/A1/A2 de l'ADS1015 ET sur la résistance R_FSR vers la masse.
# ADS1015 : VDD → 3V3, GND, ADDR → GND. Chaque pied a son bus : pied G SDA → GP14 (broche 19), SCL → GP15 (broche 20) ;
#           pied D SDA → GP16 (broche 21), SCL → GP17 (broche 22).
#
# MODE = "direct" : valeurs en continu (appuie au doigt).
# MODE = "pesee"  : pose des masses connues (0,1 / 0,5 / 1 / 2 kg sur une pièce de monnaie centrée sur le FSR),
#                   le script mesure la résistance du FSR et conseille la meilleure résistance de pont.
import math
import time

import brochage as B
from ads1x15 import ADS1x15, r_fsr

MODE = "direct"
MODELE = 1015                                   # 1115 si tu as des ADS1115
R_PONT = B.R_FSR                                # la résistance réellement soudée pendant ce test (Ω)
E12 = (1000, 1200, 1500, 1800, 2200, 2700, 3300, 3900, 4700, 5600, 6800, 8200, 10000)


def trouver_pieds():
    pieds = {}
    for cote, adr in B.PIEDS.items():
        bus = B.bus_i2c(cote)
        if adr in bus.scan():
            pieds[cote] = ADS1x15(bus, adr, MODELE)
    return pieds


def texte_r(r):
    return "   ∞   " if r is None else ("%6.1fk" % (r / 1000) if r < 1000000 else "  >1M ")


def direct(pieds, tours=None):
    print("Appuie sur chaque capteur. Ctrl+C pour arrêter.")
    n = 0
    while tours is None or n < tours:
        morceaux = []
        for cote, ads in pieds.items():
            for e, nom in B.FSR.items():
                v = ads.tension(e)
                morceaux.append("%s %s %.2fV %s" % (cote, nom, v, texte_r(r_fsr(v, R_PONT, B.V_FSR))))
        print(" | ".join(morceaux), end="\r")
        n += 1
        time.sleep_ms(100)
    print()


def moyenne(ads, e, n=100):
    s = 0.0
    for _ in range(n):
        s += ads.tension(e)
    return s / n


def pesee(pieds, saisie=input):
    cote = list(pieds)[0]
    ads = pieds[cote]
    e = int(saisie("Pied %s : quelle entrée tester (0 talon, 1 pointe int., 2 pointe ext.) ? " % cote) or 0)
    mesures = []
    print("Pour chaque masse : pose-la, attends 2 s, puis Entrée. Entrée sans masse tapée = fin.")
    while True:
        m = saisie("Masse posée en kg (ex. 0.5) : ").strip().replace(",", ".")
        if not m:
            break
        v = moyenne(ads, e)
        r = r_fsr(v, R_PONT, B.V_FSR)
        mesures.append((float(m), v, r))
        print("  %.2f kg → %.3f V, FSR %s" % (float(m), v, texte_r(r)))
    valides = [x for x in mesures if x[2] is not None and x[0] > 0]
    if len(valides) < 2:
        print("Il faut au moins deux masses non nulles pour conseiller une résistance.")
        return None
    r_haut = max(x[2] for x in valides)          # masse la plus légère
    r_bas = min(x[2] for x in valides)           # masse la plus lourde
    r_opt = math.sqrt(r_haut * r_bas)            # pont le plus sensible sur toute la plage mesurée
    conseil = min(E12, key=lambda x: abs(math.log(x / r_opt)))
    print("\nFSR de %s (léger) à %s (lourd) → résistance idéale %.0f Ω → prends %d Ω."
          % (texte_r(r_haut).strip(), texte_r(r_bas).strip(), r_opt, conseil))
    print("Mets cette valeur dans brochage.py : R_FSR = %d" % conseil)
    return conseil


def main(tours=None, saisie=input):
    pieds = trouver_pieds()
    if not pieds:
        print("✗ Aucun ADS1015 trouvé. Vérifie VDD, GND, ADDR à GND, et SDA/SCL : GP14/GP15 (pied G), GP16/GP17 (pied D).")
        return None
    print("ADS trouvés : " + ", ".join("pied %s" % c for c in pieds))
    print("Pont : %d Ω (R_PONT en haut du fichier)" % R_PONT)
    if MODE == "pesee":
        return pesee(pieds, saisie)
    direct(pieds, tours)
    return pieds


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêté.")
