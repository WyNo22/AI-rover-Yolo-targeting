# Étape 1 – Pico 2 seul : firmware, LED, scan du bus I²C (GP4 = SDA, GP5 = SCL).
import sys
import time

import machine
from machine import Pin

import brochage as B


def main():
    print("MicroPython", sys.version, "·", sys.implementation._machine if hasattr(sys.implementation, "_machine") else "")
    print("Fréquence du processeur : %d MHz" % (machine.freq() // 1000000))

    led = Pin("LED", Pin.OUT)
    for _ in range(6):
        led.toggle()
        time.sleep_ms(150)
    led.off()
    print("✓ La LED verte a clignoté 3 fois.")

    trouve = {}
    for nom, (ctrl, sda, scl) in B.BUS_I2C.items():
        adresses = B.bus_i2c(nom).scan()
        trouve[nom] = adresses
        titre = {"imu": "centrale", "G": "pied G", "D": "pied D"}.get(nom, nom)
        print("Bus %-8s (SDA GP%d, SCL GP%d) : %s" % (titre, sda, scl, "vide" if not adresses else ""))
        for a in adresses:
            print("    0x%02X  %s" % (a, B.NOMS_I2C.get(a, "inconnu")))
    return trouve


if __name__ == "__main__":
    main()
