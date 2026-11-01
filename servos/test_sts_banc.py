"""Tests de sts_banc.py sans matériel : un faux bus série avec des STS3215 simulés (protocole Feetech STS).

  python test_sts_banc.py
"""
import builtins
import io
import sys
import contextlib

import sts_banc as S


class FauxServo:
    def __init__(self, sid, position=1500):
        self.m = bytearray(128)
        self.m[3:5] = (777).to_bytes(2, "little")        # modèle STS3215
        self.m[S.ID_] = sid
        self.m[S.ANGLE_MAX:S.ANGLE_MAX + 2] = (4095).to_bytes(2, "little")
        self.m[S.COUPLE_MAX:S.COUPLE_MAX + 2] = (1000).to_bytes(2, "little")
        self.m[S.VERROU] = 1
        self.brut = position
        self.m[S.TENSION] = 121
        self.m[S.TEMPERATURE] = 28
        self.maj()

    @property
    def sid(self):
        return self.m[S.ID_]

    def decalage(self):
        v = self.m[S.DECALAGE] | (self.m[S.DECALAGE + 1] << 8)
        return S.signe(v, 11)

    def maj(self):
        pos = (self.brut - self.decalage()) % 4096
        self.m[S.POSITION:S.POSITION + 2] = pos.to_bytes(2, "little")

    def ecrire(self, adr, data):
        eeprom = adr < 40
        if eeprom and self.m[S.VERROU] == 1:
            return 0x08                                  # écriture refusée (EEPROM verrouillée)
        self.m[adr:adr + len(data)] = bytes(data)
        if self.m[S.COUPLE_ON] and adr <= S.CONSIGNE + 1 and adr + len(data) > S.CONSIGNE:
            cible = self.m[S.CONSIGNE] | (self.m[S.CONSIGNE + 1] << 8)
            self.brut = (cible + self.decalage()) % 4096    # mouvement instantané
        if adr == S.COUPLE_ON and self.m[S.COUPLE_ON]:
            cible = self.m[S.CONSIGNE] | (self.m[S.CONSIGNE + 1] << 8)
            self.brut = (cible + self.decalage()) % 4096
        self.maj()
        return 0


class FauxSerie:
    def __init__(self, servos, timeout=0.02):
        self.servos, self.timeout, self.sortie = servos, timeout, bytearray()

    @property
    def in_waiting(self):
        return len(self.sortie)

    def reset_input_buffer(self):
        self.sortie.clear()

    def read(self, n):
        out, self.sortie[:] = bytes(self.sortie[:n]), self.sortie[n:]
        return out

    def close(self):
        pass

    def write(self, b):
        assert b[:2] == b"\xff\xff"
        sid, lg, instr, params = b[2], b[3], b[4], b[5:5 + b[3] - 2]
        assert (~sum(b[2:-1])) & 0xFF == b[-1], "somme de contrôle de la trame envoyée"
        for s in list(self.servos):
            if s.sid != sid and sid != S.DIFFUSION:
                continue
            err, data = 0, b""
            if instr == S.READ:
                a, n = params
                data = bytes(s.m[a:a + n])
            elif instr == S.WRITE:
                err = s.ecrire(params[0], params[1:])
            if sid != S.DIFFUSION:
                corps = [s.sid, len(data) + 2, err, *data]       # répond avec son ID actuel
                self.sortie += bytes([0xFF, 0xFF, *corps, (~sum(corps)) & 0xFF])


def lancer(servos, *args, entrees=()):
    S.serial.Serial = lambda port, baud, timeout: FauxSerie(servos, timeout)
    reps = iter(entrees)
    builtins.input = lambda msg="": next(reps)
    sys.argv = ["sts_banc.py", "--port", "FAUX", *args]
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        try:
            S.main()
        except SystemExit as e:
            print(f"[sortie] {e}")
    return f.getvalue()


def test():
    neuf = [FauxServo(1)]
    out = lancer(neuf, "scan", "--max", "10")
    assert "1 servo(s) : [1]" in out and "modèle 777" in out, out

    out = lancer(neuf, "id", "1", "3")
    assert "✓ ID 1 → 3" in out and neuf[0].sid == 3 and neuf[0].m[S.VERROU] == 1, out

    out = lancer(neuf, "move", "3", "2500")
    assert "position 2500" in out, out

    out = lancer(neuf, "zero", "3")
    assert "position lue maintenant 2048" in out and neuf[0].decalage() == 2500 - 2048, out
    out = lancer(neuf, "info", "3")
    assert "décalage centre +452" in out, out

    out = lancer(neuf, "zero-reset", "3")
    assert neuf[0].decalage() == 0, out

    out = lancer(neuf, "test", "3")
    assert "✓ test fini" in out and "couple libéré" in out, out

    # attribution guidée : 8 servos neufs (tous en ID 1), branchés un par un
    bus = []
    reponses = []
    poste = [FauxServo(1, 900 + 100 * k) for k in range(8)]
    class Bus(list):
        pass
    branche = Bus()
    def suivant(msg=""):
        branche.clear()
        branche.append(poste[len(reponses)])
        reponses.append(1)
        return ""
    S.serial.Serial = lambda port, baud, timeout: FauxSerie(branche, timeout)
    builtins.input = suivant
    sys.argv = ["sts_banc.py", "--port", "FAUX", "installer"]
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        S.main()
    out = f.getvalue()
    assert [s.sid for s in poste] == list(range(1, 9)), [s.sid for s in poste]
    assert all(s.m[S.POSITION] | (s.m[S.POSITION + 1] << 8) == 2048 for s in poste)
    assert "Les 8 servos ont leur ID" in out

    tous = poste
    out = lancer(tous, "scan", "--max", "20")
    assert "8 servo(s) : [1, 2, 3, 4, 5, 6, 7, 8]" in out, out

    # deux servos neufs en même temps : l'attribution doit refuser et redemander
    doublon = [FauxServo(1), FauxServo(1)]
    tours = iter(["", ""])
    def entree(msg=""):
        try:
            return next(tours)
        except StopIteration:
            raise KeyboardInterrupt
    S.serial.Serial = lambda port, baud, timeout: FauxSerie(doublon, timeout)
    builtins.input = entree
    sys.argv = ["sts_banc.py", "--port", "FAUX", "installer"]
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        S.main()
    assert "il en faut exactement un" in f.getvalue() and all(s.sid == 1 for s in doublon)
    print("tous les tests passent")


if __name__ == "__main__":
    test()
