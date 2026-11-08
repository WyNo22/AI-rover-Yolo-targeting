# ads1x15.py – convertisseur ADS1015 (12 bits, 3300 mesures/s) ou ADS1115 (16 bits, 860 mesures/s) en I²C.
# Mesure à la demande sur une entrée A0–A3 par rapport à la masse.
import time

GAINS = {6.144: 0, 4.096: 1, 2.048: 2, 1.024: 3, 0.512: 4, 0.256: 5}


class ADS1x15:
    def __init__(self, i2c, adr=0x48, modele=1015, pleine_echelle=4.096):
        self.i2c, self.adr, self.modele = i2c, adr, modele
        self.fs = pleine_echelle
        self.gain = GAINS[pleine_echelle]
        self.debit = 0b110 if modele == 1015 else 0b111      # 3300 ou 860 mesures/s
        self.pas = pleine_echelle / (2048 if modele == 1015 else 32768)

    def brut(self, entree):
        cfg = (0x8000 | ((4 + entree) << 12) | (self.gain << 9) | 0x0100 | (self.debit << 5) | 0x0003)
        self.i2c.writeto_mem(self.adr, 0x01, bytes([cfg >> 8, cfg & 0xFF]))
        t0 = time.ticks_us()
        while time.ticks_diff(time.ticks_us(), t0) < 5000:
            if self.i2c.readfrom_mem(self.adr, 0x01, 2)[0] & 0x80:    # conversion finie
                break
            time.sleep_us(100)
        d = self.i2c.readfrom_mem(self.adr, 0x00, 2)
        v = (d[0] << 8) | d[1]
        if v & 0x8000:
            v -= 65536
        return v >> 4 if self.modele == 1015 else v

    def tension(self, entree):
        return max(0.0, self.brut(entree) * self.pas)


def r_fsr(v, r_pont, v_haut=3.3):
    """Résistance du FSR (Ω) : FSR entre 3V3 et l'entrée, r_pont entre l'entrée et la masse. None = pas d'appui."""
    if v <= 0.002:
        return None
    return r_pont * (v_haut - v) / v
