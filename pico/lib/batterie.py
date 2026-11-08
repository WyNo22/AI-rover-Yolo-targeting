# batterie.py – tension de la LiPo 3S par le pont 100 k / 33 k sur GP26 (12,6 V → 3,13 V sur l'entrée).
from machine import ADC


class Batterie:
    def __init__(self, broche=26, pont=(100000, 33000), cal=1.0, vref=3.3):
        self.adc = ADC(broche)
        self.facteur = vref / 65535 * (pont[0] + pont[1]) / pont[1]
        self.cal = cal

    def tension(self, n=32, calibree=True):
        s = 0
        for _ in range(n):
            s += self.adc.read_u16()
        v = s / n * self.facteur
        return v * self.cal if calibree else v
