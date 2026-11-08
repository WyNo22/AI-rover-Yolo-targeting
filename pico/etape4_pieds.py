# Étape 4 – FSR402B + ADS1015 : lecture des appuis, puis choix de la résistance du pont par des pesées.
# Chaque FSR : une patte au 3V3, l'autre sur A0/A1/A2 de l'ADS1015 ET sur la résistance R_FSR vers la masse.
# ADS1015 : VDD → 3V3, GND, SCL → GP5, SDA → GP4, ADDR → GND (pied G, 0x48) ou → 3V3 (pied D, 0x49).
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


def trouver_pieds(i2c):
    presents = i2c.scan()
    pieds = {}
    for cote, adr in B.PIEDS.items():
        if adr in presents:
            pieds[cote] = ADS1x15(i2c, adr, MODELE)
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
    pieds = trouver_pieds(B.i2c())
    if not pieds:
        print("✗ Aucun ADS1015 en 0x48 ni 0x49. Vérifie VDD, GND, SDA/SCL et la broche ADDR.")
        return None
    print("ADS trouvés : " + ", ".join("pied %s (0x%02X)" % (c, a.adr) for c, a in pieds.items()))
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
