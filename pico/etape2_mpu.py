# Étape 2 – centrale MPU6050 : détection, calibration du gyroscope, inclinaison en direct.
# Branchement : VCC → 3V3 (broche 36), GND, SDA → GP4 (broche 6), SCL → GP5 (broche 7), AD0 → GND.
import time

import brochage as B
from mpu6050 import MPU6050, Inclinaison, QUI_SUIS_JE


def main(tours=None):
    i2c = B.i2c()
    if B.MPU not in i2c.scan():
        print("✗ Pas de MPU6050 en 0x%02X. Vérifie VCC, GND, SDA/SCL (pas inversés ?) et AD0 à la masse." % B.MPU)
        return None
    imu = MPU6050(i2c, B.MPU)
    print("Puce : 0x%02X (%s)" % (imu.qui, QUI_SUIS_JE.get(imu.qui, "inconnue, mais on essaie")))

    print("Calibration : pose la carte à plat et ne la touche plus pendant 2 s…")
    time.sleep_ms(1000)
    biais, g = imu.calibrer_gyro()
    print("  biais du gyroscope : (%.2f, %.2f, %.2f) °/s" % biais)
    print("  → copie dans brochage.py : GYRO_BIAIS = (%.2f, %.2f, %.2f)" % biais)
    if abs(g - 1.0) > 0.08:
        print("  ⚠ accélération mesurée %.2f g au lieu de 1,00 g : carte bougée pendant la mesure, ou puce douteuse" % g)
    else:
        print("  ✓ accélération au repos %.2f g" % g)

    filtre = Inclinaison()
    print("\nIncline la carte : roulis = autour de X, tangage = autour de Y. Ctrl+C pour arrêter.")
    n = 0
    while tours is None or n < tours:
        acc, gyro, temp = imu.lire()
        r, t = filtre.maj(acc, gyro)
        if n % 10 == 0:
            print("roulis %+6.1f°  tangage %+6.1f°  | gyro %+7.1f %+7.1f %+7.1f °/s | %.1f °C   "
                  % (r, t, gyro[0], gyro[1], gyro[2], temp), end="\r")
        n += 1
        time.sleep_ms(5)                        # ~200 lectures par seconde
    print()
    return biais


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêté.")
