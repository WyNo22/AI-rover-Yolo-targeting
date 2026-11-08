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

    adresses = B.i2c().scan()
    if not adresses:
        print("Bus I²C vide (normal si rien n'est encore branché sur GP4 / GP5).")
    for a in adresses:
        print("  0x%02X  %s" % (a, B.NOMS_I2C.get(a, "inconnu")))
    return adresses


if __name__ == "__main__":
    main()
