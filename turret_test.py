"""
turret_test.py
Controle temps reel de la tourelle : maintenir la touche = mouvement, relacher = stop.

  Fleche gauche  : pan gauche  (maintenir)
  Fleche droite  : pan droite  (maintenir)
  Fleche haut    : tilt haut   (maintenir)
  Fleche bas     : tilt bas    (maintenir)
  ESPACE         : stop pan + tilt centre
  r              : reset angle pan
  q / ESC        : quitter
"""

import serial
import serial.tools.list_ports
import time
import sys
import threading
import keyboard

SERIAL_PORT     = None   # None = auto-detection, sinon "COM3"
SERIAL_BAUD     = 115200
TILT_CENTER     = 90
TILT_MIN        = 10
TILT_MAX        = 170
PAN_SPEED       = 60     # vitesse pan (0-100)
TILT_DEG_PER_S  = 60.0   # vitesse tilt en degres/seconde quand maintenu
LOOP_HZ         = 30     # frequence de la boucle


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(kw in desc for kw in ["arduino", "ch340", "uno", "ftdi"]):
            return p.device
    if ports:
        return ports[0].device
    return None


def connect(port=None):
    if port is None:
        port = find_arduino_port()
    if port is None:
        print("Aucun port COM trouve. Verifiez la connexion USB de l'Arduino.")
        sys.exit(1)
    print(f"Connexion sur {port} ({SERIAL_BAUD} baud)...")
    ser = serial.Serial(port, SERIAL_BAUD, timeout=1)
    time.sleep(2)
    print(f"Arduino pret ({port})\n")
    return ser


def send(ser, pan_speed, tilt_angle):
    cmd = f"P{int(pan_speed)}T{int(tilt_angle)}\n"
    try:
        ser.write(cmd.encode())
    except serial.SerialException:
        pass


def read_arduino(ser):
    try:
        while ser.in_waiting:
            msg = ser.readline().decode(errors='ignore').strip()
            if msg == "PAN_LIMIT":
                print("  [!] LIMITE PAN atteinte  ->  appuyez sur R pour reset")
            elif msg == "PAN_RESET":
                print("  [OK] Angle pan remis a zero")
    except serial.SerialException:
        pass


def main():
    ser = connect(SERIAL_PORT)
    current_tilt = float(TILT_CENTER)
    dt           = 1.0 / LOOP_HZ

    send(ser, 0, TILT_CENTER)

    print("┌─────────────────────────────────────────┐")
    print("│    TOURELLE  -  CONTROLE TEMPS REEL     │")
    print("├─────────────────────────────────────────┤")
    print("│  Maintenir ←/→  : pan gauche / droite   │")
    print("│  Maintenir ↑/↓  : tilt haut / bas       │")
    print("│  ESPACE         : stop + centre          │")
    print("│  R              : reset angle pan        │")
    print("│  Q              : quitter                │")
    print("└─────────────────────────────────────────┘")
    print()

    # Hook evenementiel pour quitter (evite les faux positifs de is_pressed au demarrage)
    quit_event = threading.Event()
    def _on_q(e):
        if e.name == 'q':
            quit_event.set()

    time.sleep(0.4)  # laisse le terminal vider ses events
    keyboard.on_press(_on_q)
    print("Go ! (Q pour quitter)\n")

    try:
        while not quit_event.is_set():

            # Reset pan
            if keyboard.is_pressed('r'):
                ser.write(b'R\n')
                time.sleep(0.3)  # eviter repetition

            # Calcul pan
            if keyboard.is_pressed('left'):
                pan = -PAN_SPEED
            elif keyboard.is_pressed('right'):
                pan = PAN_SPEED
            else:
                pan = 0

            # Calcul tilt (incremental continu)
            if keyboard.is_pressed('up'):
                current_tilt = min(TILT_MAX, current_tilt + TILT_DEG_PER_S * dt)
            elif keyboard.is_pressed('down'):
                current_tilt = max(TILT_MIN, current_tilt - TILT_DEG_PER_S * dt)

            # Espace : stop + centre
            if keyboard.is_pressed('space'):
                pan = 0
                current_tilt = float(TILT_CENTER)

            tilt_int = int(round(current_tilt))

            # Envoi permanent a 30Hz pour eviter le watchdog Arduino
            send(ser, pan, tilt_int)

            read_arduino(ser)
            time.sleep(dt)

    except KeyboardInterrupt:
        pass

    keyboard.unhook_all()
    print("\nArret : retour position repos...")
    send(ser, 0, TILT_CENTER)
    time.sleep(0.5)
    ser.close()
    print("Ferme.")


if __name__ == "__main__":
    main()
