# sts.py – protocole Feetech STS (STS3215) sur une UART du Pico, via l'adaptateur Waveshare (cavalier sur A).
# Même protocole et mêmes noms que servos/sts_banc.py (version PC).
import time

MODELE, ID_, DECALAGE, MODE = 3, 5, 31, 33
COUPLE_ON, ACCEL, CONSIGNE, VERROU = 40, 41, 42, 55
POSITION, VITESSE, CHARGE, TENSION, TEMPERATURE, EN_MOUVEMENT, COURANT = 56, 58, 60, 62, 63, 66, 69
PING, READ, WRITE, SYNC_WRITE = 0x01, 0x02, 0x03, 0x83
DIFFUSION = 0xFE
CENTRE = 2048


class ErreurBus(Exception):
    pass


def signe(v, bit):
    """Valeurs Feetech en signe + amplitude : le bit `bit` porte le signe."""
    return -(v & ((1 << bit) - 1)) if v & (1 << bit) else v


class Bus:
    def __init__(self, uart, delai_ms=6):
        self.u = uart
        self.delai_ms = delai_ms
        self.dernier_err = 0
        self.surplus = False

    @staticmethod
    def trame(sid, instr, params=()):
        corps = bytes([sid, len(params) + 2, instr]) + bytes(params)
        return b"\xff\xff" + corps + bytes([(~sum(corps)) & 0xFF])

    def _vider(self):
        while self.u.any():
            self.u.read()

    def _envoyer(self, f):
        self._vider()
        self.u.write(f)
        if hasattr(self.u, "flush"):
            self.u.flush()                     # attend la fin de l'émission

    def _reponse(self, sid, envoye, delai_ms):
        t0 = time.ticks_ms()
        buf = b""
        while time.ticks_diff(time.ticks_ms(), t0) < delai_ms:
            n = self.u.any()
            if not n:
                continue
            buf += self.u.read(n)
            if envoye is not None:             # certains montages renvoient la trame émise : on l'ignore
                if len(buf) < len(envoye) and envoye[:len(buf)] == buf:
                    continue
                if buf[:len(envoye)] == envoye:
                    buf = buf[len(envoye):]
                envoye = None
            while True:
                i = buf.find(b"\xff\xff")
                if i < 0 or len(buf) < i + 4:
                    break
                lg = buf[i + 3]
                if len(buf) < i + 4 + lg:
                    break
                p = buf[i + 2:i + 4 + lg]
                if (~sum(p[:-1])) & 0xFF != p[-1]:
                    raise ErreurBus("ID %d : somme de contrôle fausse" % sid)
                if p[0] == sid:
                    self.dernier_err = p[2]
                    self.surplus = len(buf) > i + 4 + lg       # octets en trop : deux servos sur le même ID ?
                    return p[3:-1]
                buf = buf[i + 2:]
        return None

    def echange(self, sid, instr, params=(), reponse=True, delai_ms=None):
        f = self.trame(sid, instr, params)
        self._envoyer(f)
        if sid == DIFFUSION or not reponse:
            return None
        return self._reponse(sid, f, delai_ms or self.delai_ms)

    # ── opérations ────────────────────────────────────────────────────────────
    def ping(self, sid):
        return self.echange(sid, PING, delai_ms=4) is not None

    def lire(self, sid, adr, n):
        r = self.echange(sid, READ, (adr, n))
        if r is None or len(r) != n:
            raise ErreurBus("ID %d ne répond pas (lecture adresse %d)" % (sid, adr))
        return r

    def lire8(self, sid, adr):
        return self.lire(sid, adr, 1)[0]

    def lire16(self, sid, adr):
        b = self.lire(sid, adr, 2)
        return b[0] | (b[1] << 8)

    def ecrire(self, sid, adr, octets):
        r = self.echange(sid, WRITE, (adr,) + tuple(octets))
        if sid != DIFFUSION and r is None:
            raise ErreurBus("ID %d ne répond pas (écriture adresse %d)" % (sid, adr))

    def ecrire8(self, sid, adr, v):
        self.ecrire(sid, adr, (v & 0xFF,))

    def position(self, sid):
        return self.lire16(sid, POSITION)

    def etat(self, sid):
        b = self.lire(sid, POSITION, 15)       # adresses 56 à 70 en une lecture

        def g(a):
            return b[a - POSITION] | (b[a - POSITION + 1] << 8)

        return {
            "position": g(POSITION),
            "vitesse": signe(g(VITESSE), 15),
            "charge": signe(g(CHARGE), 10) / 10,
            "tension": b[TENSION - POSITION] / 10,
            "temp": b[TEMPERATURE - POSITION],
            "bouge": bool(b[EN_MOUVEMENT - POSITION]),
            "courant": int(signe(g(COURANT), 15) * 6.5),
        }

    def couple(self, sid, actif):
        self.ecrire8(sid, COUPLE_ON, 1 if actif else 0)

    def couple_tous_off(self):
        """Diffusion à tous les servos, sans réponse : c'est la commande de l'arrêt d'urgence."""
        self.echange(DIFFUSION, WRITE, (COUPLE_ON, 0))

    def aller(self, sid, pos, vitesse=600, accel=20):
        pos = max(0, min(4095, int(pos)))
        self.ecrire8(sid, ACCEL, accel)
        self.ecrire(sid, CONSIGNE, (pos & 0xFF, pos >> 8, 0, 0, vitesse & 0xFF, vitesse >> 8))
        self.couple(sid, True)

    def attendre(self, sid, cible, tol=15, delai_ms=3000):
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < delai_ms:
            if abs(self.position(sid) - cible) <= tol:
                return True
            time.sleep_ms(20)
        return False

    def sync_positions(self, consignes, vitesse=0):
        """Une seule trame pour tous les servos : {id: position}. vitesse 0 = maximale."""
        params = [CONSIGNE, 6]
        for sid, pos in consignes.items():
            pos = max(0, min(4095, int(pos)))
            params += [sid, pos & 0xFF, pos >> 8, 0, 0, vitesse & 0xFF, vitesse >> 8]
        self.echange(DIFFUSION, SYNC_WRITE, params)

    def scanner(self, ids):
        trouves = []
        for i in ids:
            try:
                if self.ping(i):
                    time.sleep_ms(1)
                    double = self.surplus or self.u.any()
                    trouves += [i, i] if double else [i]
            except ErreurBus:
                trouves += [i, i]              # réponses superposées : au moins deux servos sur cet ID
        return trouves
