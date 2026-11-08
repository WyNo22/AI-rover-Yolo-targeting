# ibus.py – lecture du récepteur FlySky FS-iA6B en iBUS (115 200 bauds, une trame de 32 octets toutes les ~7 ms).
# Trame : 0x20 0x40, 14 voies sur 2 octets (1000–2000), somme de contrôle = 0xFFFF − somme des 30 premiers octets.
import time


class IBus:
    def __init__(self, uart):
        self.u = uart
        self.buf = b""
        self.voies = [1500] * 14
        self.t_trame = None
        self.trames = 0
        self.erreurs = 0

    def lire(self):
        """Non bloquant : traite ce qui est arrivé. Renvoie True si une trame valide est arrivée."""
        n = self.u.any()
        if n:
            self.buf += self.u.read(n)
        nouvelle = False
        while len(self.buf) >= 32:
            if self.buf[0] != 0x20 or self.buf[1] != 0x40:
                self.buf = self.buf[1:]
                continue
            f = self.buf[:32]
            if 0xFFFF - sum(f[:30]) != (f[30] | (f[31] << 8)):
                self.erreurs += 1
                self.buf = self.buf[1:]
                continue
            self.voies = [(f[2 + 2 * k] | (f[3 + 2 * k] << 8)) & 0x0FFF for k in range(14)]
            self.buf = self.buf[32:]
            self.t_trame = time.ticks_ms()
            self.trames += 1
            nouvelle = True
        if len(self.buf) > 256:
            self.buf = self.buf[-64:]
        return nouvelle

    def voie(self, n):
        """Voie numérotée comme sur l'émetteur (1 à 14)."""
        return self.voies[n - 1]

    def age_ms(self):
        """Temps depuis la dernière trame valide, None si aucune trame reçue."""
        if self.t_trame is None:
            return None
        return time.ticks_diff(time.ticks_ms(), self.t_trame)
