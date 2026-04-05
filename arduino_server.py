"""
arduino_server.py – Pont USB→TCP pour Arduino sur Android/Termux
Lance avec : termux-usb -e "python3 ~/arduino_server.py" /dev/bus/usb/001/XXX

Écoute sur TCP 127.0.0.1:9999 et relaie les données vers/depuis l'Arduino.
tracker_rover.py se connecte via ARDUINO_TCP="127.0.0.1:9999".
"""
import sys, os, socket, threading, time

sys.path.insert(0, os.path.expanduser("~"))
from android_usb_serial import UsbSerial

TCP_HOST = "127.0.0.1"
TCP_PORT = 9999

def main():
    fd = int(sys.argv[-1])
    print(f"[ARD-SRV] Arduino fd={fd}")
    ser = UsbSerial(fd, 115200)
    print(f"[ARD-SRV] Arduino prêt")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((TCP_HOST, TCP_PORT))
    srv.listen(1)
    print(f"[ARD-SRV] TCP en écoute sur {TCP_HOST}:{TCP_PORT}")

    while True:
        conn, addr = srv.accept()
        print(f"[ARD-SRV] Client connecté: {addr}")
        conn.settimeout(0.1)

        # Thread: Arduino → TCP
        def ard_to_tcp():
            while True:
                try:
                    line = ser.readline()
                    if line:
                        conn.sendall(line)
                except (OSError, BrokenPipeError):
                    break

        t = threading.Thread(target=ard_to_tcp, daemon=True)
        t.start()

        # Main: TCP → Arduino
        buf = b""
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                ser.write(data)
            except socket.timeout:
                continue
            except (OSError, BrokenPipeError):
                break

        print(f"[ARD-SRV] Client déconnecté")
        conn.close()

if __name__ == "__main__":
    main()
