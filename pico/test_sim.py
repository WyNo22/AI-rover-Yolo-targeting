"""Tests des scripts du Pico sur PC, sans matériel : faux module `machine` (I²C, UART, ADC, Pin) et horloge virtuelle.

  python test_sim.py

Simule : MPU6050, 2 ADS1015 + FSR, 8 servos STS3215 (avec ou sans écho de trame), récepteur iBUS, pont de batterie.
"""
import builtins
import contextlib
import io
import math
import os
import struct
import sys
import time
import types

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(ICI, "lib"), ICI]

# ── horloge virtuelle : chaque lecture avance de 20 µs, les sleep avancent sans attendre ─────────
HORLOGE = [0.0]


def _us():
    HORLOGE[0] += 20
    return int(HORLOGE[0])


time.ticks_us = _us
time.ticks_ms = lambda: _us() // 1000
time.ticks_diff = lambda a, b: a - b
time.sleep_ms = lambda ms: HORLOGE.__setitem__(0, HORLOGE[0] + ms * 1000)
time.sleep_us = lambda us: HORLOGE.__setitem__(0, HORLOGE[0] + us)


# ── monde simulé ──────────────────────────────────────────────────────────────
class Monde:
    def __init__(self):
        self.i2c = {}
        self.servos = []
        self.echo = False
        self.radio_active = False
        self.ch5 = 1000
        self.radio_corrompue = 0
        self.v_batterie = 11.1


M = Monde()


class FauxMPU:
    def __init__(self):
        self.reg = bytearray(256)
        self.reg[0x75] = 0x68
        self.biais = (1.0, -0.5, 0.2)          # °/s
        self.inclinaison = 0.0                 # roulis en degrés

    def lire(self, reg, n):
        if reg == 0x3B:
            a = math.radians(self.inclinaison)
            v = (0, int(4096 * math.sin(a)), int(4096 * math.cos(a)), 1000,
                 int(self.biais[0] * 65.5), int(self.biais[1] * 65.5), int(self.biais[2] * 65.5))
            return struct.pack(">7h", *v)
        return bytes(self.reg[reg:reg + n])

    def ecrire(self, reg, data):
        self.reg[reg:reg + len(data)] = data


class FauxADS:
    def __init__(self):
        self.entree = 0
        self.v = [1.65, 0.5, 0.0, 0.0]

    def lire(self, reg, n):
        if reg == 0x01:
            return bytes([0x80 | 0x40, 0x83])
        code = max(0, min(2047, int(self.v[self.entree] / 0.002))) << 4
        return bytes([code >> 8, code & 0xFF])

    def ecrire(self, reg, data):
        if reg == 0x01:
            self.entree = ((data[0] >> 4) & 0x07) - 4


class FauxServo:
    def __init__(self, sid, position=1500):
        self.m = bytearray(128)
        self.m[3:5] = (777).to_bytes(2, "little")
        self.m[5] = sid
        self.m[62], self.m[63] = 120, 27
        self.m[42:44] = position.to_bytes(2, "little")
        self.pos(position)

    def pos(self, p=None):
        if p is not None:
            self.m[56:58] = (p % 4096).to_bytes(2, "little")
        return self.m[56] | (self.m[57] << 8)

    def ecrire(self, adr, data):
        self.m[adr:adr + len(data)] = bytes(data)
        if self.m[40] and (adr <= 42 < adr + len(data) or adr == 40):
            self.pos(self.m[42] | (self.m[43] << 8))


def repondre(sid, data=b""):
    corps = [sid, len(data) + 2, 0, *data]
    return bytes([0xFF, 0xFF, *corps, (~sum(corps)) & 0xFF])


class FausseUART:
    def __init__(self, uid, **kw):
        self.uid = uid
        self.rx = bytearray()
        self.t_radio = 0

    def any(self):
        if self.uid == 0 and M.radio_active and HORLOGE[0] - self.t_radio > 7000:
            self.t_radio = HORLOGE[0]
            voies = [1500, 1500, 1000, 1500, M.ch5, 1000] + [1500] * 8
            f = bytes([0x20, 0x40]) + b"".join(v.to_bytes(2, "little") for v in voies)
            f += (0xFFFF - sum(f)).to_bytes(2, "little")
            if M.radio_corrompue:
                M.radio_corrompue -= 1
                f = f[:10] + bytes([f[10] ^ 0xFF]) + f[11:]
            self.rx += f
        return len(self.rx)

    def read(self, n=None):
        n = len(self.rx) if n is None else n
        out, self.rx[:] = bytes(self.rx[:n]), self.rx[n:]
        return out

    def flush(self):
        pass

    def write(self, b):
        if self.uid != 1:
            return
        if M.echo:
            self.rx += b
        assert b[:2] == b"\xff\xff" and (~sum(b[2:-1])) & 0xFF == b[-1], "trame mal formée"
        sid, instr, params = b[2], b[4], b[5:-1]
        if instr == 0x83:                                  # SYNC WRITE
            adr, lg = params[0], params[1]
            for k in range(2, len(params), lg + 1):
                for s in M.servos:
                    if s.m[5] == params[k]:
                        s.ecrire(adr, params[k + 1:k + 1 + lg])
            return
        for s in M.servos:
            if s.m[5] != sid and sid != 0xFE:
                continue
            data = b""
            if instr == 0x02:
                data = bytes(s.m[params[0]:params[0] + params[1]])
            elif instr == 0x03:
                s.ecrire(params[0], params[1:])
            if sid != 0xFE:
                self.rx += repondre(s.m[5], data)


class FauxI2C:
    def __init__(self, *a, **kw):
        pass

    def scan(self):
        return sorted(M.i2c)

    def readfrom_mem(self, adr, reg, n):
        return M.i2c[adr].lire(reg, n)

    def writeto_mem(self, adr, reg, data):
        M.i2c[adr].ecrire(reg, data)


class FauxADC:
    def __init__(self, broche):
        pass

    def read_u16(self):
        return int(M.v_batterie * 33 / 133 / 3.3 * 65535)


class FauxPin:
    OUT, IN = 1, 0

    def __init__(self, *a, **kw):
        self.v = 0

    def value(self, v=None):
        if v is None:
            return self.v
        self.v = v

    def toggle(self):
        self.v ^= 1

    def on(self):
        self.v = 1

    def off(self):
        self.v = 0


machine = types.ModuleType("machine")
machine.Pin, machine.I2C, machine.UART, machine.ADC = FauxPin, FauxI2C, FausseUART, FauxADC
machine.freq = lambda: 150000000
sys.modules["machine"] = machine


def silencieux(f, *a, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        r = f(*a, **kw)
    return r, out.getvalue()


def test():
    import etape1_pico, etape2_mpu, etape4_pieds, etape5_servos, etape6_batterie, etape7_radio
    from ads1x15 import r_fsr
    from mpu6050 import Inclinaison
    from sts import Bus, signe
    import brochage as B

    mpu, g, d = FauxMPU(), FauxADS(), FauxADS()
    M.i2c = {0x68: mpu, 0x48: g, 0x49: d}

    # 1 – scan I²C
    adrs, out = silencieux(etape1_pico.main)
    assert adrs == [0x48, 0x49, 0x68] and "MPU6050" in out and "pied D" in out, out

    # 2 – MPU6050 : biais, puis inclinaison
    biais, out = silencieux(etape2_mpu.main, tours=30)
    assert all(abs(b - e) < 0.02 for b, e in zip(biais, mpu.biais)), biais
    assert "GYRO_BIAIS" in out and "✓ accélération au repos 1.00 g" in out, out
    f = Inclinaison()
    a = math.radians(20)
    r, t = f.maj((0, math.sin(a), math.cos(a)), (0, 0, 0))
    assert abs(r - 20) < 0.1 and abs(t) < 0.1, (r, t)

    # 4 – pieds : lecture directe, puis pesées et conseil de résistance
    _, out = silencieux(etape4_pieds.main, tours=2)
    assert "pied G (0x48)" in out and "pied D (0x49)" in out and "1.65V" in out, out
    assert abs(r_fsr(1.65, 1000) - 1000) < 1 and r_fsr(0.0, 1000) is None
    fsr = {"0.5": 2000, "2": 500}                         # FSR à 0,5 kg puis 2 kg

    def saisie(msg=""):
        if "entrée" in msg:
            return "0"
        m = reponses.pop(0)
        if m:
            g.v[0] = 3.3 * 1000 / (1000 + fsr[m])
        return m

    reponses = ["0.5", "2", ""]
    etape4_pieds.MODE = "pesee"
    conseil, out = silencieux(etape4_pieds.main, saisie=saisie)
    assert conseil == 1000 and "R_FSR = 1000" in out, out
    etape4_pieds.MODE = "direct"

    # 5 – servos : 8 servos, écho de trame ou non, boucle groupée, mouvements
    for echo in (False, True):
        M.echo = echo
        M.servos = [FauxServo(i, 1500 + 50 * i) for i in range(1, 9)]
        ids, out = silencieux(etape5_servos.main, saisie=lambda m="": "o")
        assert ids == list(range(1, 9)), (echo, out)
        assert "Cycle" in out and "Mouvements finis" in out, out
        assert all(s.pos() == 1500 + 50 * s.m[5] and s.m[40] == 0 for s in M.servos), "retour au départ, couple libéré"
    M.echo = False

    bus = Bus(FausseUART(1))
    bus.sync_positions({1: 2000, 2: 2100})
    assert M.servos[0].m[42] | (M.servos[0].m[43] << 8) == 2000

    M.servos = [FauxServo(3), FauxServo(3), FauxServo(5)]  # deux servos sur l'ID 3
    trouves = bus.scanner(range(0, 8))
    assert trouves.count(3) == 2 and trouves.count(5) == 1, trouves
    assert signe(0x0400 | 25, 10) == -25

    M.servos = []
    r, out = silencieux(etape5_servos.main, saisie=lambda m="": "n")
    assert r is None and "cavalier sur A" in out

    # 6 – batterie
    M.servos = [FauxServo(i) for i in range(1, 9)]
    cal, out = silencieux(etape6_batterie.main, tours=3, saisie=lambda m="": "11.3")
    assert abs(cal - 11.3 / 11.1) < 0.01 and "lue par le servo 1 : 12.0 V" in out, out
    M.v_batterie = 10.0
    _, out = silencieux(etape6_batterie.main, tours=1, saisie=lambda m="": "")
    assert "CRITIQUE" in out
    M.v_batterie = 11.1

    # 7 – radio et arrêt d'urgence
    M.radio_active, M.ch5, M.radio_corrompue = True, 1000, 2
    arrete, out = silencieux(etape7_radio.main, tours=400)
    assert arrete is False and "▶ ARMÉ" in out and "erreurs 2" in out, out
    M.servos[0].m[40] = 1                                    # un servo tenu…
    M.ch5 = 2000                                             # … interrupteur sur ARRÊT
    arrete, out = silencieux(etape7_radio.main, tours=300)
    assert arrete is True and all(s.m[40] == 0 for s in M.servos), out
    M.ch5, M.radio_active = 1000, False                      # émetteur éteint
    M.servos[0].m[40] = 1
    arrete, out = silencieux(etape7_radio.main, tours=300)
    assert arrete is True and all(s.m[40] == 0 for s in M.servos) and "dernière il y a — ms" in out, out

    print("tous les tests passent")


if __name__ == "__main__":
    test()
