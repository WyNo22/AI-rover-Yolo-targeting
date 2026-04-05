"""
arduino_bridge.py
Bridge TCP ↔ Arduino série – tourne sur PC
Le téléphone (tracker_rover.py) se connecte en TCP et envoie les commandes.
Le bridge les relaie vers l'Arduino et renvoie les réponses série.

Usage :
    python arduino_bridge.py            # auto-détection COM + port TCP 5001
    python arduino_bridge.py COM10 5001
"""

import sys
import socket
import threading
import serial
import serial.tools.list_ports
import time

# ── Config ──────────────────────────────────────────────────────────────────
SERIAL_PORT  = None    # None = auto-détection Arduino
SERIAL_BAUD  = 115200
TCP_HOST     = "0.0.0.0"
TCP_PORT     = 5001
# ─────────────────────────────────────────────────────────────────────────────


def find_arduino_port():
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(k in desc for k in ("arduino", "ch340", "cp210", "usb serial", "ftdi")):
            return p.device
    return None


def serial_reader(ser, conn):
    """Lit les réponses Arduino et les envoie au client TCP."""
    try:
        while True:
            line = ser.readline()
            if line:
                conn.sendall(line)
    except Exception:
        pass


def handle_client(conn, addr, ser):
    print(f"[BRIDGE] Client connecté : {addr}")
    t = threading.Thread(target=serial_reader, args=(ser, conn), daemon=True)
    t.start()
    try:
        buf = b""
        while True:
            data = conn.recv(256)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                ser.write(line + b"\n")
    except Exception as e:
        print(f"[BRIDGE] Client déconnecté : {e}")
    finally:
        conn.close()
        print(f"[BRIDGE] Client {addr} fermé")


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else SERIAL_PORT
    tcp_port = int(sys.argv[2]) if len(sys.argv) > 2 else TCP_PORT

    if port is None:
        port = find_arduino_port()
    if port is None:
        print("[BRIDGE] Arduino non trouvé – spécifie le port en argument")
        sys.exit(1)

    print(f"[BRIDGE] Ouverture {port} @ {SERIAL_BAUD} baud")
    ser = serial.Serial(port, SERIAL_BAUD, timeout=0.1)
    time.sleep(2)   # reset Arduino

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((TCP_HOST, tcp_port))
    srv.listen(1)
    print(f"[BRIDGE] En écoute sur TCP :{tcp_port} – en attente du téléphone…")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr, ser), daemon=True)
        t.start()


if __name__ == "__main__":
    main()
