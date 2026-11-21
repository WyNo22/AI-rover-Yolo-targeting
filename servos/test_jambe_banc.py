"""Tests de jambe_banc.py sans matériel : cinématique, butées, commandes sur un bus simulé, animation.

  python test_jambe_banc.py
"""
import builtins
import contextlib
import io
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")

import jambe_banc as JB
import sts_banc as S
from test_sts_banc import FauxServo, FauxSerie


class FauxSerieSync(FauxSerie):
    """Ajoute SYNC WRITE (0x83) au faux bus de test_sts_banc."""
    def write(self, b):
        if b[4] == 0x83:
            p = b[5:5 + b[3] - 2]
            adr, lg = p[0], p[1]
            for k in range(2, len(p), lg + 1):
                for s in self.servos:
                    if s.sid == p[k]:
                        s.ecrire(adr, p[k + 1:k + 1 + lg])
            return
        super().write(b)


def lancer(servos, *args, entrees=()):
    S.serial.Serial = lambda port, baud, timeout: FauxSerieSync(servos, timeout)
    reps = iter(entrees)
    builtins.input = lambda msg="": next(reps)
    sys.argv = ["jambe_banc.py", "--port", "FAUX", *args]
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        try:
            JB.main()
        except SystemExit as e:
            print(f"[sortie] {e}")
    return f.getvalue()


def test():
    # cinématique : aller-retour, pied à plat, jambe tendue
    for (x, z) in ((0, 380), (40, 360), (-30, 390), (25, 330)):
        q = JB.cinematique_inverse(x, z)
        p = JB.cinematique_directe(q)
        assert abs(p["cheville"][0] - x) < 0.01 and abs(p["cheville"][1] + z) < 0.01, (x, z, p)
        assert abs(p["talon"][1] - p["pointe"][1]) < 0.01, "pied pas à plat"
    q = JB.cinematique_inverse(0, 400)
    assert abs(q["genou"]) < 3 and abs(q["hanche"]) < 1.5
    # trajectoire : appui au sol, vol au-dessus, boucle fermée
    assert JB.trajectoire_pied(0.3)[1] == 0 and JB.trajectoire_pied(0.8)[1] > 20
    assert abs(JB.trajectoire_pied(0.0)[0] - JB.trajectoire_pied(0.9999)[0]) < 0.1
    # butées : bornage et conversion degrés ↔ pas
    r = JB.charger("TEST")
    r["butees_relevees"] = True
    assert JB.vers_pas(r, "genou", 200) == JB.vers_pas(r, "genou", 105)
    assert abs(JB.vers_deg(r, "hanche", JB.vers_pas(r, "hanche", 30)) - 30) < 0.1

    jambe = [FauxServo(i, 2048) for i in (1, 2, 3, 4)]
    # butées relevées à la main : on « bouge » le servo entre deux Entrée
    limites = iter([2048 - 200, 2048 + 900, 2048 - 300, 2048 + 1000, 2048, 2048 + 1250, 2048 - 450, 2048 + 450])
    def bouge(msg=""):
        sid = 1 + ["roulis", "hanche", "genou", "cheville"].index(msg.split()[1])
        jambe[sid - 1].brut = next(limites)
        jambe[sid - 1].maj()
        return ""
    S.serial.Serial = lambda port, baud, timeout: FauxSerieSync(jambe, timeout)
    builtins.input = bouge
    fichier = JB.fichier_reglages("D")
    if os.path.exists(fichier):
        os.remove(fichier)
    sys.argv = ["jambe_banc.py", "--port", "FAUX", "butees"]
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        JB.main()
    out = f.getvalue()
    assert "Butées enregistrées" in out, out
    r = JB.charger("D")
    assert r["butees"]["genou"] == [0.0, 109.9] or abs(r["butees"]["genou"][1] - 109.9) < 0.2, r["butees"]

    out = lancer(jambe, "sens", entrees=["o", "o", "n", "o"])
    assert "sens de genou inversé" in out and JB.charger("D")["sens"]["genou"] == -1, out
    lo, hi = JB.charger("D")["butees"]["genou"]
    assert lo < -100 and abs(hi) < 0.2, (lo, hi)            # butées retournées avec le sens
    out = lancer(jambe, "pied", "40", "30")
    assert "angles" in out and "✓" in out, out
    qv = JB.cinematique_inverse(40, JB.H_DEBOUT - 30)
    assert abs(jambe[2].m[S.POSITION] | (jambe[2].m[S.POSITION + 1] << 8)) == JB.vers_pas(JB.charger("D"), "genou", qv["genou"])
    out = lancer(jambe, "marche", "--cycles", "1", "--periode", "0.4")
    assert "Marche finie" in out and "charge max" in out, out
    out = lancer(jambe, "marche", "--rythme", "max", "--cycles", "1")
    assert "Rythme max" in out and "genou 200°/s" in out and "Marche finie" in out, out
    out = lancer(jambe, "rythmes", "--cycles", "1", entrees=["", "", "s"])
    assert "Rythme lent" in out and "Rythme moyen" in out and out.count("Marche finie") == 2, out
    out = lancer(jambe, "cycle")
    assert "Cycle fini" in out, out
    out = lancer(jambe, "charge", "--minutes", "0.02", entrees=[""])
    assert "Test réussi" in out, out
    for n in os.listdir(os.path.dirname(os.path.abspath(JB.__file__))):
        if n.startswith("charge_D_") and n.endswith(".csv"):
            os.remove(os.path.join(os.path.dirname(os.path.abspath(JB.__file__)), n))
    out = lancer(jambe, "repos")
    assert "Couple coupé" in out and all(s.m[S.COUPLE_ON] == 0 for s in jambe)
    out = lancer([FauxServo(1)], "repos")
    assert "absent" in out, out
    os.remove(fichier)

    # animation : quelques images sans fenêtre
    import argparse
    A = JB.regler_rythme(argparse.Namespace(rythme="max", cycles=1, periode=None, pas=None, levee=None, roulis=None))
    assert max(JB.vitesses_pic(A.periode, A.pas, A.levee, A.roulis).values()) <= JB.VITESSE_MAX + 1
    assert JB.simuler(A, images=range(0, 30, 3))
    print("tous les tests passent")


if __name__ == "__main__":
    test()
