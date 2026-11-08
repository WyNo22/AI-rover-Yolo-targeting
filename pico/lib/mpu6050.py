# mpu6050.py – centrale inertielle MPU6050 (GY-521) en I²C.
# Accéléromètre ±8 g, gyroscope ±500 °/s, filtre interne 44 Hz, échantillonnage 1 kHz.
import math
import struct
import time

QUI_SUIS_JE = {0x68: "MPU6050", 0x70: "MPU6500 (clone)", 0x71: "MPU9250", 0x72: "clone MPU6050",
               0x98: "clone MPU6050"}


class MPU6050:
    def __init__(self, i2c, adr=0x68, biais=(0.0, 0.0, 0.0)):
        self.i2c, self.adr = i2c, adr
        self.qui = i2c.readfrom_mem(adr, 0x75, 1)[0]
        self._w(0x6B, 0x80)                    # réinitialisation
        time.sleep_ms(100)
        self._w(0x6B, 0x01)                    # réveil, horloge sur le gyroscope X
        self._w(0x19, 0x00)                    # 1 kHz
        self._w(0x1A, 0x03)                    # filtre passe-bas 44 Hz
        self._w(0x1B, 0x08)                    # gyroscope ±500 °/s → 65,5 pas par °/s
        self._w(0x1C, 0x10)                    # accéléromètre ±8 g → 4096 pas par g
        self.biais = list(biais)

    def _w(self, reg, v):
        self.i2c.writeto_mem(self.adr, reg, bytes([v]))

    def brut(self):
        return struct.unpack(">7h", self.i2c.readfrom_mem(self.adr, 0x3B, 14))

    def lire(self):
        """((ax, ay, az) en g, (gx, gy, gz) en °/s corrigés du biais, température en °C)."""
        ax, ay, az, t, gx, gy, gz = self.brut()
        b = self.biais
        return ((ax / 4096, ay / 4096, az / 4096),
                (gx / 65.5 - b[0], gy / 65.5 - b[1], gz / 65.5 - b[2]),
                t / 340 + 36.53)

    def calibrer_gyro(self, n=500):
        """La carte doit rester immobile. Renvoie (biais, norme moyenne de l'accélération en g)."""
        s = [0.0, 0.0, 0.0]
        norme = 0.0
        for _ in range(n):
            ax, ay, az, t, gx, gy, gz = self.brut()
            s[0] += gx / 65.5
            s[1] += gy / 65.5
            s[2] += gz / 65.5
            norme += math.sqrt(ax * ax + ay * ay + az * az) / 4096
            time.sleep_ms(2)
        self.biais = [v / n for v in s]
        return tuple(self.biais), norme / n


class Inclinaison:
    """Filtre complémentaire : roulis et tangage en degrés (le gyroscope suit, l'accéléromètre corrige la dérive)."""

    def __init__(self, alpha=0.98):
        self.alpha = alpha
        self.roulis = self.tangage = None
        self.t = None

    def maj(self, acc, gyro):
        ax, ay, az = acc
        r_acc = math.atan2(ay, az) * 57.29578
        t_acc = math.atan2(-ax, math.sqrt(ay * ay + az * az)) * 57.29578
        maintenant = time.ticks_us()
        if self.t is None:
            self.roulis, self.tangage = r_acc, t_acc
        else:
            dt = time.ticks_diff(maintenant, self.t) / 1000000
            a = self.alpha
            self.roulis = a * (self.roulis + gyro[0] * dt) + (1 - a) * r_acc
            self.tangage = a * (self.tangage + gyro[1] * dt) + (1 - a) * t_acc
        self.t = maintenant
        return self.roulis, self.tangage
