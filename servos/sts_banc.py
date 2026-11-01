"""
sts_banc.py – Banc des servos Feetech STS3215 de LEO-S (adaptateur Waveshare Bus Servo Adapter (A), USB).

Protocole Feetech STS implémenté ici (seule dépendance : pyserial), pour voir exactement ce qui part sur le bus.

  python sts_banc.py ports                 liste les ports série
  python sts_banc.py scan                  cherche les servos (ID 0 à 253)
  python sts_banc.py installer             attribution guidée des ID 1 à 8, un servo neuf à la fois
  python sts_banc.py id 1 5                change l'ID 1 en 5 (un seul servo branché)
  python sts_banc.py info 1 2 3            position, tension, température, charge, courant, réglages
  python sts_banc.py suivi 1 2 3 4         tableau en direct (Ctrl+C pour quitter)
  python sts_banc.py centre 1 2            va doucement au centre (2048) et tient la position
  python sts_banc.py move 3 2500           va à une position (0–4095)
  python sts_banc.py test 3                petit aller-retour ±400 pas, mesure charge et courant
  python sts_banc.py couple 3 off          libère (off) ou bloque (on) le servo
  python sts_banc.py zero 3                fait de la position actuelle le nouveau centre (2048), en EEPROM
  python sts_banc.py zero-reset 3          remet le décalage du centre à 0

Options : --port COM5 ou /dev/ttyACM0 (sinon détection auto), --baud 1000000 (défaut des STS3215).
"""
import argparse
import sys
import time

import serial
from serial.tools import list_ports

# ── Table mémoire STS3215 (petit-boutiste) ────────────────────────────────────
MODELE, ID_, BAUD = 3, 5, 6
ANGLE_MIN, ANGLE_MAX = 9, 11
TEMP_MAX, V_MAX, V_MIN, COUPLE_MAX = 13, 14, 15, 16
DECALAGE, MODE = 31, 33
COUPLE_ON, ACCEL, CONSIGNE, VITESSE_CONS = 40, 41, 42, 46
VERROU = 55
POSITION, VITESSE, CHARGE, TENSION, TEMPERATURE, EN_MOUVEMENT, COURANT = 56, 58, 60, 62, 63, 66, 69

PING, READ, WRITE = 0x01, 0x02, 0x03
DIFFUSION = 0xFE
CENTRE = 2048

ARTICULATIONS = {
    1: "jambe D · S1 roulis de hanche", 2: "jambe D · S2 tangage de hanche",
    3: "jambe D · S3 genou", 4: "jambe D · S4 cheville",
    5: "jambe G · S1 roulis de hanche", 6: "jambe G · S2 tangage de hanche",
    7: "jambe G · S3 genou", 8: "jambe G · S4 cheville",
}


class ErreurBus(Exception):
    pass


def signe(v, bit):
    """Valeurs Feetech en signe + amplitude : le bit `bit` porte le signe."""
    return -(v & ((1 << bit) - 1)) if v & (1 << bit) else v


def vers_signe(v, bit):
    return (abs(v) | (1 << bit)) if v < 0 else v


class Bus:
    def __init__(self, port, baud=1_000_000, timeout=0.02):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        self.ser.reset_input_buffer()
        self.surplus = False          # des octets en trop après une réponse = plusieurs servos sur le même ID

    def close(self):
        self.ser.close()

    # ── trames ────────────────────────────────────────────────────────────────
    @staticmethod
    def trame(sid, instr, params=()):
        corps = [sid, len(params) + 2, instr, *params]
        return bytes([0xFF, 0xFF, *corps, (~sum(corps)) & 0xFF])

    def _lire_reponse(self, sid, delai=0.06):
        t0 = time.monotonic()
        buf = b""
        while time.monotonic() - t0 < delai:
            buf += self.ser.read(max(1, self.ser.in_waiting))
            i = buf.find(b"\xff\xff")
            if i < 0 or len(buf) < i + 4:
                continue
            rid, lg = buf[i + 2], buf[i + 3]
            if len(buf) < i + 4 + lg:
                continue
            paquet = buf[i + 2:i + 4 + lg]
            if (~sum(paquet[:-1])) & 0xFF != paquet[-1]:
                raise ErreurBus(f"ID {sid} : somme de contrôle fausse")
            if rid != sid:
                buf = buf[i + 2:]
                continue
            time.sleep(0.003)
            self.surplus = len(buf) > i + 4 + lg or self.ser.in_waiting > 0
            err = paquet[2]
            if err & 0x20:
                print(f"  ⚠ ID {sid} : surcharge signalée par le servo", file=sys.stderr)
            if err & 0x04:
                print(f"  ⚠ ID {sid} : surchauffe signalée par le servo", file=sys.stderr)
            if err & 0x01:
                print(f"  ⚠ ID {sid} : tension hors plage signalée par le servo", file=sys.stderr)
            return paquet[3:-1]
        return None

    def echange(self, sid, instr, params=(), reponse=True, delai=0.06):
        self.ser.reset_input_buffer()
        self.ser.write(self.trame(sid, instr, params))
        if sid == DIFFUSION or not reponse:
            return None
        return self._lire_reponse(sid, delai)

    # ── opérations ────────────────────────────────────────────────────────────
    def ping(self, sid):
        return self.echange(sid, PING, delai=0.015) is not None

    def changer_id(self, ancien, nouveau):
        """Le servo répond déjà avec son nouvel ID : on n'attend pas de réponse de l'ancien."""
        self.eeprom(ancien, True)
        self.echange(ancien, WRITE, (ID_, nouveau), reponse=False)
        time.sleep(0.05)
        self.ser.reset_input_buffer()
        self.eeprom(nouveau, False)
        return self.ping(nouveau)

    def lire(self, sid, adr, n):
        r = self.echange(sid, READ, (adr, n))
        if r is None or len(r) != n:
            raise ErreurBus(f"ID {sid} ne répond pas (lecture adresse {adr})")
        return r

    def lire8(self, sid, adr):
        return self.lire(sid, adr, 1)[0]

    def lire16(self, sid, adr):
        b = self.lire(sid, adr, 2)
        return b[0] | (b[1] << 8)

    def ecrire(self, sid, adr, octets):
        r = self.echange(sid, WRITE, (adr, *octets))
        if sid != DIFFUSION and r is None:
            raise ErreurBus(f"ID {sid} ne répond pas (écriture adresse {adr})")

    def ecrire8(self, sid, adr, v):
        self.ecrire(sid, adr, (v & 0xFF,))

    def ecrire16(self, sid, adr, v):
        self.ecrire(sid, adr, (v & 0xFF, (v >> 8) & 0xFF))

    def eeprom(self, sid, ouvert):
        self.ecrire8(sid, VERROU, 0 if ouvert else 1)

    def etat(self, sid):
        b = self.lire(sid, POSITION, 15)          # 56 à 70 en une lecture
        g = lambda a: b[a - POSITION] | (b[a - POSITION + 1] << 8)
        return {
            "position": g(POSITION),
            "vitesse": signe(g(VITESSE), 15),
            "charge_%": signe(g(CHARGE), 10) / 10,
            "tension_V": b[TENSION - POSITION] / 10,
            "temp_C": b[TEMPERATURE - POSITION],
            "bouge": bool(b[EN_MOUVEMENT - POSITION]),
            "courant_mA": round(signe(g(COURANT), 15) * 6.5),
        }

    def aller(self, sid, pos, vitesse=600, accel=20):
        pos = max(0, min(4095, int(pos)))
        self.ecrire8(sid, ACCEL, accel)
        self.ecrire(sid, CONSIGNE, (pos & 0xFF, pos >> 8, 0, 0, vitesse & 0xFF, vitesse >> 8))
        self.ecrire8(sid, COUPLE_ON, 1)

    def attendre(self, sid, cible, tol=15, delai=None, vitesse=600):
        """Attend que le servo arrive ; le délai par défaut dépend de la distance à parcourir."""
        if delai is None:
            delai = abs(self.lire16(sid, POSITION) - cible) / max(vitesse, 1) + 1.5
        t0 = time.monotonic()
        while time.monotonic() - t0 < delai:
            if abs(self.lire16(sid, POSITION) - cible) <= tol:
                return True
            time.sleep(0.05)
        return False


# ── outils ────────────────────────────────────────────────────────────────────
def trouver_port():
    ports = list(list_ports.comports())
    pref = [p for p in ports if (p.vid == 0x1A86) or "ACM" in p.device or "CH34" in (p.description or "")]
    choix = pref or [p for p in ports if "USB" in (p.description or "") or "USB" in p.device or "ACM" in p.device]
    if not choix:
        sys.exit("Aucun port série trouvé : adaptateur branché en USB, cavalier sur B ? (python sts_banc.py ports)")
    return choix[0].device


def scanner(bus, ids):
    """Liste des ID qui répondent ; un ID partagé par plusieurs servos (collision) y figure deux fois."""
    trouves = []
    for i in ids:
        try:
            if bus.ping(i):
                trouves += [i, i] if bus.surplus else [i]
        except ErreurBus:
            trouves += [i, i]                 # réponses superposées : au moins deux servos sur cet ID
    return trouves


def verifier_tension(bus, sid):
    v = bus.lire8(sid, TENSION) / 10
    if v < 10.5:
        print(f"  ⚠ tension {v:.1f} V : batterie 3S faible ou alimentation insuffisante (C018 = 12 V)")
    elif v > 12.8:
        print(f"  ⚠ tension {v:.1f} V : trop haute pour un STS3215 12 V (jamais la 4S !)")
    return v


def afficher_info(bus, sid):
    m = bus.lire16(sid, MODELE)
    e = bus.etat(sid)
    dec = signe(bus.lire16(sid, DECALAGE), 11)
    amin, amax = bus.lire16(sid, ANGLE_MIN), bus.lire16(sid, ANGLE_MAX)
    cmax = bus.lire16(sid, COUPLE_MAX)
    print(f"ID {sid:3d}  {ARTICULATIONS.get(sid, '')}")
    print(f"   modèle {m} · mode {bus.lire8(sid, MODE)} · couple {'ON' if bus.lire8(sid, COUPLE_ON) else 'off'}"
          f" · couple max {cmax / 10:.0f} % · butées {amin}–{amax} · décalage centre {dec:+d}")
    print(f"   position {e['position']:4d} ({(e['position'] - CENTRE) * 360 / 4096:+6.1f}°) · tension {e['tension_V']:.1f} V"
          f" · {e['temp_C']} °C · charge {e['charge_%']:+.1f} % · courant {e['courant_mA']} mA")


def cmd_installer(bus):
    print("Attribution des ID, un servo neuf à la fois (les neufs sont tous en ID 1).")
    print("Branche UN SEUL servo sur l'adaptateur, puis Entrée. Colle une étiquette avec son numéro dès qu'il est fait.\n")
    for nid, nom in ARTICULATIONS.items():
        while True:
            input(f"→ Servo pour l'ID {nid} ({nom}) : branche-le SEUL et appuie sur Entrée…")
            presents = scanner(bus, range(0, 21))
            if len(presents) == 1:
                break
            print(f"  ✗ {len(presents)} servo(s) répondent {presents} : il en faut exactement un. Recommence.")
        old = presents[0]
        if old != nid and not bus.changer_id(old, nid):
            sys.exit(f"  ✗ le servo ne répond plus en ID {nid} : relance « scan »")
        verifier_tension(bus, nid)
        bus.aller(nid, CENTRE, vitesse=800)
        au_centre = bus.attendre(nid, CENTRE, vitesse=800)
        afficher_info(bus, nid)
        bus.ecrire8(nid, COUPLE_ON, 0)
        etat = "servo au centre" if au_centre else "⚠ centre non atteint (refaire « centre » plus tard)"
        print(f"  ✓ ID {nid} fait, {etat}. Étiquette « {nid} », débranche-le.\n")
    print("Les 8 servos ont leur ID. Rebranche-les en chaîne et lance « scan » pour vérifier.")


def main():
    ap = argparse.ArgumentParser(description="Banc des servos STS3215 (LEO-S)")
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=1_000_000)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("ports")
    s = sp.add_parser("scan"); s.add_argument("--max", type=int, default=253)
    sp.add_parser("installer")
    s = sp.add_parser("id"); s.add_argument("ancien", type=int); s.add_argument("nouveau", type=int)
    for nom in ("info", "suivi", "centre"):
        s = sp.add_parser(nom); s.add_argument("ids", type=int, nargs="+")
    s = sp.add_parser("move"); s.add_argument("id", type=int); s.add_argument("pos", type=int); s.add_argument("--vitesse", type=int, default=600)
    s = sp.add_parser("test"); s.add_argument("id", type=int); s.add_argument("--amplitude", type=int, default=400)
    s = sp.add_parser("couple"); s.add_argument("id", type=int); s.add_argument("etat", choices=["on", "off"])
    for nom in ("zero", "zero-reset"):
        s = sp.add_parser(nom); s.add_argument("id", type=int)
    a = ap.parse_args()

    if a.cmd == "ports":
        for p in list_ports.comports():
            print(f"{p.device:16s} {p.description}  (VID {p.vid:04X})" if p.vid else f"{p.device:16s} {p.description}")
        return

    port = a.port or trouver_port()
    bus = Bus(port, a.baud)
    print(f"Port {port} à {a.baud} bauds")
    try:
        if a.cmd == "scan":
            t = scanner(bus, range(0, a.max + 1))
            doublons = sorted({i for i in t if t.count(i) > 1})
            uniques = sorted(set(t))
            print(f"{len(t)} servo(s) : {uniques}" if t else "Aucun servo. Alimentation 12 V branchée ? Cavalier sur B ? Câble dans le bon sens ?")
            if doublons:
                print(f"⚠ plusieurs servos partagent l'ID {doublons} : branche-les un par un et utilise « installer » ou « id »")
            for i in uniques:
                if i not in doublons:
                    afficher_info(bus, i)
        elif a.cmd == "installer":
            cmd_installer(bus)
        elif a.cmd == "id":
            if not bus.ping(a.ancien):
                sys.exit(f"Pas de servo en ID {a.ancien}")
            if bus.ping(a.nouveau):
                sys.exit(f"L'ID {a.nouveau} est déjà pris sur le bus")
            print(f"✓ ID {a.ancien} → {a.nouveau}" if bus.changer_id(a.ancien, a.nouveau) else "✗ le servo ne répond pas au nouvel ID")
        elif a.cmd == "info":
            for i in a.ids:
                afficher_info(bus, i)
        elif a.cmd == "suivi":
            print("Ctrl+C pour quitter")
            while True:
                lignes = []
                for i in a.ids:
                    try:
                        e = bus.etat(i)
                        lignes.append(f"ID {i}: {e['position']:4d} {e['tension_V']:4.1f}V {e['temp_C']:2d}°C {e['charge_%']:+6.1f}% {e['courant_mA']:5d}mA")
                    except ErreurBus:
                        lignes.append(f"ID {i}: ---")
                print(" | ".join(lignes), end="\r", flush=True)
                time.sleep(0.2)
        elif a.cmd == "centre":
            for i in a.ids:
                verifier_tension(bus, i)
                bus.aller(i, CENTRE, vitesse=800)
            for i in a.ids:
                ok = bus.attendre(i, CENTRE, vitesse=800)
                print(f"ID {i} au centre ({bus.lire16(i, POSITION)})" if ok else f"ID {i} : ⚠ centre non atteint ({bus.lire16(i, POSITION)})")
            print("Couple maintenu : les servos tiennent le centre. « couple <ID> off » pour les libérer.")
        elif a.cmd == "move":
            bus.aller(a.id, a.pos, vitesse=a.vitesse)
            bus.attendre(a.id, a.pos, vitesse=a.vitesse)
            afficher_info(bus, a.id)
        elif a.cmd == "test":
            verifier_tension(bus, a.id)
            p0 = bus.lire16(a.id, POSITION)
            pics = []
            for cible in (p0 + a.amplitude, p0 - a.amplitude, p0):
                bus.aller(a.id, cible, vitesse=800)
                t0 = time.monotonic()
                while time.monotonic() - t0 < 1.5:
                    e = bus.etat(a.id)
                    pics.append((abs(e["charge_%"]), abs(e["courant_mA"])))
                    if not e["bouge"] and abs(e["position"] - cible) < 15:
                        break
                    time.sleep(0.02)
                print(f"  → {cible:4d} : arrivé à {bus.lire16(a.id, POSITION)}")
            bus.ecrire8(a.id, COUPLE_ON, 0)
            print(f"✓ test fini · charge max {max(p[0] for p in pics):.1f} % · courant max {max(p[1] for p in pics)} mA"
                  f" · {bus.lire8(a.id, TEMPERATURE)} °C · couple libéré")
        elif a.cmd == "couple":
            bus.ecrire8(a.id, COUPLE_ON, 1 if a.etat == "on" else 0)
            print(f"ID {a.id} : couple {a.etat}")
        elif a.cmd == "zero":
            bus.ecrire8(a.id, COUPLE_ON, 0)
            bus.eeprom(a.id, True)
            bus.ecrire16(a.id, DECALAGE, 0)
            time.sleep(0.05)
            brut = bus.lire16(a.id, POSITION)
            dec = brut - CENTRE
            bus.ecrire16(a.id, DECALAGE, vers_signe(dec, 11))
            bus.eeprom(a.id, False)
            time.sleep(0.05)
            print(f"✓ ID {a.id} : décalage {dec:+d} pas · position lue maintenant {bus.lire16(a.id, POSITION)} (cible {CENTRE})")
        elif a.cmd == "zero-reset":
            bus.eeprom(a.id, True)
            bus.ecrire16(a.id, DECALAGE, 0)
            bus.eeprom(a.id, False)
            print(f"✓ ID {a.id} : décalage remis à 0")
    except ErreurBus as e:
        sys.exit(f"✗ {e}")
    except KeyboardInterrupt:
        print()
    finally:
        bus.close()


if __name__ == "__main__":
    main()
