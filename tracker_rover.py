"""
tracker_rover.py
Phase 4 : YOLO + BotsSort + sélection cible + tourelle + navigation base roulante

Extension de tracker_click.py :
  - Envoi bbox_h en plus de error_x / error_y → Arduino contrôle aussi les moteurs
  - Affichage HUD : état drive (FORWARD / STOP / REVERSE) + bbox_h
  - Constante DRIVE_ENABLED pour désactiver la navigation sans modifier l'Arduino

Touches :
  Clic gauche  : sélectionner / changer de cible
  r            : reset cible
  d            : toggle drive (activer/désactiver les moteurs)
  q            : quitter
"""

import platform
if platform.system() == "Windows":
    try:
        from ultralytics import YOLO
        _USE_ULTRALYTICS = True
    except ImportError:
        _USE_ULTRALYTICS = False
        from yolo_onnx import YOLODetector, SimpleTracker
else:
    _USE_ULTRALYTICS = False
    from yolo_onnx import YOLODetector, SimpleTracker
import cv2
import numpy as np
try:
    import serial
except ImportError:
    serial = None
try:
    import serial.tools.list_ports
except (ImportError, Exception):
    pass
import subprocess
import time
import threading
import json
import os
import sys
try:
    import requests as _requests
except ImportError:
    _requests = None
from http.server import BaseHTTPRequestHandler, HTTPServer

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

IS_WINDOWS = platform.system() == "Windows"

# ── Paramètres utilisateur ────────────────────────────────────────────────────
SERIAL_PORT     = None      # None = auto-détection  |  sinon ex. "COM3"
SERIAL_BAUD     = 115200
ARDUINO_TCP     = None      # None = USB série  |  Android bridge ex. "127.0.0.1:9999"
CAM_INDEX       = None   # None=auto Windows | Android: "http://127.0.0.1:8081" (USB Camera)
CAM_AUTH        = ("admin", "admin")  # HTTP basic auth pour USB Camera (None = pas d'auth)
_DJI_UVC_FD     = None      # Rempli automatiquement sur Android (termux-usb fd)
CAM_W           = 640
CAM_H           = 480
YOLO_SKIP       = 3         # Android: YOLO toutes les N frames (1=chaque frame)
MODEL_PATH      = os.path.join(_SCRIPT_DIR, "yolo26n.pt" if _USE_ULTRALYTICS else "yolo26n.onnx")
CONF_THRESHOLD  = 0.4
CMD_RATE_HZ     = 15        # fréquence max d'envoi série
SMOOTH_ALPHA    = 0.35      # EMA position cible : 0 = figé, 1 = aucun lissage
LOST_TOLERANCE  = 30        # frames sans détection avant reset cible
CLICK_MARGIN    = 20        # pixels de tolérance autour des bboxes pour le clic

# ── Paramètres navigation ─────────────────────────────────────────────────────
DRIVE_ENABLED    = False    # Démarrage en mode tourelle seule – bouton écran ou touche 'd' pour activer
AUTO_LOCK        = False    # True = verrouille automatiquement la personne la plus proche du centre
SERVO_DEADZONE   = 8        # pixels : en dessous de ce seuil, pas de correction servo
APPROACH_TARGET  = 280      # bbox_h (px) → bonne distance → stop
RETREAT_TARGET   = 420      # bbox_h (px) → trop proche → reculer
STREAM_PORT      = 8082     # port HTTP stream MJPEG (Android/Linux) – 8081 réservé à USB Camera

# ── Détection automatique Android (termux-usb) ──────────────────────────────
if not IS_WINDOWS and len(sys.argv) > 1 and sys.argv[-1].isdigit():
    _DJI_UVC_FD = int(sys.argv[-1])
    if ARDUINO_TCP is None:
        ARDUINO_TCP = "127.0.0.1:9999"
    print(f"[ANDROID] DJI UVC fd={_DJI_UVC_FD}, Arduino TCP={ARDUINO_TCP}")
# Android sans UVC fd → IP Webcam bridge (DJI via Camera2 + app IP Webcam)
if not IS_WINDOWS and _DJI_UVC_FD is None:
    if CAM_INDEX is None:
        CAM_INDEX = "http://127.0.0.1:8081"
    if ARDUINO_TCP is None:
        ARDUINO_TCP = "127.0.0.1:9999"
    print(f"[ANDROID] IP Webcam mode: {CAM_INDEX}, Arduino TCP={ARDUINO_TCP}")
# ─────────────────────────────────────────────────────────────────────────────


# ── Stream MJPEG (Android sans display) ──────────────────────────────────────
_stream_lock    = threading.Lock()
_stream_jpg     = [b""]
_stream_cmd     = []   # ("click", x, y) | ("key", char)
_stream_clients = 0    # nombre de navigateurs connectés au flux

_HTML_TPL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tracker Rover</title>
<style>body{{background:#111;color:#fff;font-family:sans-serif;text-align:center;margin:0}}
img{{max-width:100%;cursor:crosshair;display:block;margin:auto}}
button{{margin:6px;padding:12px 20px;font-size:1em;border-radius:8px;border:none;cursor:pointer;color:#fff}}
#btnD{{background:#2a2}}#btnR{{background:#a42}}#btnA{{background:#48a}}#btnQ{{background:#444}}</style></head>
<body><h3 style="margin:8px">Tracker Rover</h3>
<img id="s" src="/stream" onclick="click_(event)">
<br><button id="btnD" onclick="key_('d')">Toggle Drive</button>
<button id="btnA" onclick="key_('a')">Auto ON/OFF</button>
<button id="btnR" onclick="key_('r')">Reset cible</button>
<button id="btnQ" onclick="key_('q')">Quitter</button>
<script>
var FW={fw},FH={fh};
function click_(e){{var r=e.target.getBoundingClientRect();
var x=Math.round((e.clientX-r.left)/r.width*FW);
var y=Math.round((e.clientY-r.top)/r.height*FH);
fetch('/click',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{x,y}})}});}}
function key_(k){{fetch('/key',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{key:k}})}});}}
</script></body></html>"""
_HTML = b""  # sera rempli avec les dimensions réelles dans _start_mjpeg()


class _MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_HTML)
        elif self.path == "/stream":
            global _stream_clients
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            _stream_clients += 1
            try:
                while True:
                    with _stream_lock:
                        jpg = _stream_jpg[0]
                    if jpg:
                        self.wfile.write(
                            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
                    time.sleep(0.04)
            except Exception:
                pass
            finally:
                _stream_clients -= 1
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        n    = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n).decode()) if n else {}
        if self.path == "/click":
            _stream_cmd.append(("click", int(data.get("x", -1)), int(data.get("y", -1))))
        elif self.path == "/key":
            _stream_cmd.append(("key", str(data.get("key", ""))))
        self.send_response(200); self.end_headers()

    def log_message(self, *a):
        pass


def _start_mjpeg():
    global _HTML
    from socketserver import ThreadingMixIn
    class _ThreadedHTTP(ThreadingMixIn, HTTPServer):
        daemon_threads = True
    _HTML = _HTML_TPL.format(fw=frame_w, fh=frame_h).encode()
    srv = _ThreadedHTTP(("0.0.0.0", STREAM_PORT), _MJPEGHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import socket
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    if not ip or ip.startswith("127."):
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "<ip_du_tel>"
    print(f"[STREAM] Ouvre http://{ip}:{STREAM_PORT} dans un navigateur WiFi")


# ── Scan caméra ───────────────────────────────────────────────────────────────
def get_windows_camera_names():
    """Retourne les noms des caméras Windows via PowerShell."""
    if not IS_WINDOWS:
        return []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice -Class Camera -Status OK | Select-Object -ExpandProperty FriendlyName"],
            capture_output=True, text=True, timeout=8
        )
        return [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    except Exception:
        return []


class _HTTPCapture:
    """Lit des frames HTTP (MJPEG ou snapshot) dans un thread.
    read() retourne toujours la dernière frame dispo — zéro buffering."""
    def __init__(self, base_url, auth=None):
        self._base  = base_url.rstrip('/')
        self._auth  = auth
        self._w, self._h = 640, 480
        self._lock   = threading.Lock()
        self._latest = None
        self._ok     = False
        self._stop   = False
        threading.Thread(target=self._run, daemon=True).start()
        # Attendre la première frame (max 10s)
        for _ in range(100):
            with self._lock:
                if self._latest is not None:
                    self._ok = True
                    break
            time.sleep(0.1)
        if not self._ok:
            print("[CAM] Aucune frame reçue après 10s !")

    def _auth_headers(self):
        if not self._auth:
            return {}
        import base64
        cred = base64.b64encode(f"{self._auth[0]}:{self._auth[1]}".encode()).decode()
        return {'Authorization': f'Basic {cred}'}

    def _run(self):
        """Thread principal : essaie snapshot puis MJPEG, reconnecte si besoin."""
        import urllib.request, urllib.error
        headers = self._auth_headers()
        # Essai snapshot d'abord
        for path in ['/shot.jpg', '/photo.jpg', '/capture']:
            url = self._base + path
            try:
                req = urllib.request.Request(url, headers=headers)
                r = urllib.request.urlopen(req, timeout=5)
                data = r.read()
                if len(data) > 500 and data[:2] == b'\xff\xd8':
                    print(f"[CAM] Snapshot mode: {url}")
                    self._snap_loop(url, headers)
                    return
            except Exception:
                pass
        # Mode MJPEG stream avec reconnexion automatique
        for path in ['', '/video', '/mjpeg', '/stream']:
            url = self._base + path
            try:
                req = urllib.request.Request(url, headers=headers)
                test = urllib.request.urlopen(req, timeout=5)
                test.close()
                print(f"[CAM] MJPEG stream mode (threaded): {url}")
                self._mjpeg_loop(url, headers)
                return
            except Exception:
                pass
        print("[CAM] Aucun endpoint trouvé !")

    def _snap_loop(self, url, headers):
        import urllib.request
        while not self._stop:
            try:
                req = urllib.request.Request(url, headers=headers)
                r = urllib.request.urlopen(req, timeout=3)
                data = r.read()
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    with self._lock:
                        self._latest = frame
                        self._h, self._w = frame.shape[:2]
            except Exception:
                time.sleep(0.05)

    def _mjpeg_loop(self, url, headers):
        import urllib.request
        while not self._stop:
            try:
                req = urllib.request.Request(url, headers=headers)
                stream = urllib.request.urlopen(req, timeout=10)
                buf = b''
                frames_decoded = 0
                while not self._stop:
                    chunk = stream.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    # Extraire tous les JPEGs du buffer, garder seulement le dernier
                    last_frame = None
                    while True:
                        a = buf.find(b'\xff\xd8')
                        if a < 0:
                            break
                        b = buf.find(b'\xff\xd9', a + 2)
                        if b < 0:
                            buf = buf[a:]   # garder depuis le début du JPEG
                            break
                        jpg = buf[a:b+2]
                        buf = buf[b+2:]
                        f = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                        if f is not None:
                            last_frame = f
                    if last_frame is not None:
                        with self._lock:
                            self._latest = last_frame
                            self._h, self._w = last_frame.shape[:2]
                        frames_decoded += 1
                    # Limite taille buf
                    if len(buf) > 500000:
                        buf = b''
                stream.close()
            except Exception as e:
                time.sleep(0.2)

    def isOpened(self):
        return self._ok

    def read(self):
        with self._lock:
            if self._latest is not None:
                return True, self._latest
        return False, None

    def get(self, prop):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:  return float(self._w)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT: return float(self._h)
        if prop == cv2.CAP_PROP_FPS:          return 10.0
        return 0.0

    def set(self, prop, value):
        pass

    def release(self):
        self._stop = True
        self._ok = False


def _open_cap(index):
    """Ouvre une caméra avec le bon backend selon l'OS.
    Sur Android/Linux : utilise le chemin /dev/videoN directement
    pour éviter l'échec de l'énumération V4L2 via sysfs.
    Pour les URL HTTP : utilise _HTTPCapture (bypass FFmpeg MJPEG)."""
    if isinstance(index, str) and index.startswith('http'):
        return _HTTPCapture(index, auth=CAM_AUTH)
    if IS_WINDOWS:
        cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
        if not cap.isOpened():
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    else:
        path = index if isinstance(index, str) else f"/dev/video{index}"
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    return cap


def scan_cameras(max_idx=8):
    available = []
    print("Scan des caméras", end="", flush=True)
    if IS_WINDOWS:
        indices = range(max_idx)
    else:
        # Sur Android : scan par chemin string – ne dépend pas de sysfs V4L2
        indices = [f"/dev/video{i}" for i in range(max_idx)]
    for i in indices:
        print(".", end="", flush=True)
        cap = _open_cap(i)
        if cap.isOpened():
            cap.release()
            available.append(i)
    print()
    return available


def get_camera_index(forced=None):
    if forced is not None:
        return forced
    cams = scan_cameras()
    if not cams:
        print("Aucune caméra trouvée.")
        return None
    if len(cams) == 1:
        print(f"Caméra détectée : index {cams[0]}")
        return cams[0]

    device_names = get_windows_camera_names()
    print(f"Caméras disponibles : {cams}")
    if device_names:
        print("Périphériques détectés par Windows :")
        for i, name in enumerate(device_names):
            print(f"  [{i}] {name}")
        for i, name in enumerate(device_names):
            if any(kw in name.lower() for kw in ["dji", "action 4", "action4", "osmo"]):
                idx = cams[i] if i < len(cams) else cams[-1]
                print(f"DJI détectée automatiquement → index {idx} : {name}")
                return idx

    print(f"→ index {cams[0]} sélectionné par défaut  (forcer avec CAM_INDEX=<n>)")
    return cams[0]


# ── Arduino ───────────────────────────────────────────────────────────────────
class TcpSerial:
    """Wrapper TCP compatible avec l'interface serial.Serial (write/close/port)."""
    def __init__(self, host, port_num):
        import socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5)
        self._sock.connect((host, port_num))
        self._sock.settimeout(None)
        self.port = f"tcp://{host}:{port_num}"
        self._f = self._sock.makefile('rb')

    def write(self, data):
        self._sock.sendall(data)

    def readline(self):
        return self._f.readline()

    def close(self):
        try: self._sock.close()
        except Exception: pass


def find_arduino_port():
    # Sur Linux/Android : essayer les ports USB série connus en priorité
    if not IS_WINDOWS:
        import os
        for candidate in ["/dev/ttyUSB0", "/dev/ttyACM0",
                          "/dev/ttyUSB1", "/dev/ttyACM1"]:
            if os.path.exists(candidate):
                return candidate
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(kw in desc for kw in ["arduino", "ch340", "uno", "ftdi", "acm"]):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def connect_arduino(port=None):
    if ARDUINO_TCP:
        host, tcp_port = ARDUINO_TCP.rsplit(":", 1)
        try:
            s = TcpSerial(host, int(tcp_port))
            print(f"Arduino connecté via TCP bridge : {ARDUINO_TCP}")
            return s
        except Exception as e:
            print(f"Erreur TCP bridge {ARDUINO_TCP} : {e}  – mode caméra seule.")
            return None
    if port is None:
        port = find_arduino_port()
    if port is None:
        print("Arduino non détecté – mode caméra seule.")
        return None
    try:
        ser = serial.Serial(port, SERIAL_BAUD, timeout=1, dsrdtr=False, rtscts=False)
        time.sleep(0.5)
        print(f"Arduino connecté : {port} ({SERIAL_BAUD} baud)")
        return ser
    except serial.SerialException as e:
        print(f"Erreur port {port} : {e}  – mode caméra seule.")
        return None


def send_command(ser, ex, ey, bbox_h=0):
    """Envoie 'error_x error_y bbox_h\n' à l'Arduino.
    Si bbox_h=0 ou DRIVE_ENABLED=False → moteurs stop côté Arduino."""
    if ser is None:
        return
    try:
        bh = int(bbox_h) if DRIVE_ENABLED else 0
        ser.write(f"{int(ex)} {int(ey)} {bh}\n".encode())
    except (serial.SerialException, OSError):
        pass


# ── Callback souris ───────────────────────────────────────────────────────────
_click      = [-1, -1]
_btn_click  = False   # True si le dernier clic était sur le bouton Mode Traque


def _mouse_cb(event, x, y, flags, param):
    global _btn_click
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"[MOUSE] clic gauche ({x},{y})", flush=True)
        _click[0], _click[1] = x, y
        _btn_click = False


# ── Initialisation ────────────────────────────────────────────────────────────
print("\n=== Tracker Rover – YOLO + BotsSort + Drive ===")
if _USE_ULTRALYTICS:
    model = YOLO(MODEL_PATH)
else:
    _onnx_path = os.path.join(_SCRIPT_DIR, "yolo26n.onnx")
    model = YOLODetector(_onnx_path, conf=CONF_THRESHOLD, imgsz=640)
    _tracker = SimpleTracker(iou_thresh=0.3, max_lost=LOST_TOLERANCE)
arduino = connect_arduino(SERIAL_PORT)

if _DJI_UVC_FD is not None:
    from uvc_camera import UvcCamera
    cap = UvcCamera(_DJI_UVC_FD, width=CAM_W, height=CAM_H, fps=30)
    frame_w, frame_h = CAM_W, CAM_H
    print(f"[ANDROID] DJI UVC ouvert : {frame_w}x{frame_h}")
else:
    cam_index = get_camera_index(CAM_INDEX)
    if cam_index is None:
        if arduino:
            arduino.close()
        raise SystemExit(1)
    cap = _open_cap(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if not cap.isOpened():
    print("Impossible d'ouvrir la caméra.")
    if arduino:
        arduino.close()
    raise SystemExit(1)

print("Initialisation caméra", end="", flush=True)
for _ in range(10):
    cap.read()
    print(".", end="", flush=True)
print()

if not IS_WINDOWS and frame_w > 400:
    frame_w, frame_h = 320, 240
print(f"Caméra prête (index {cam_index}) : {frame_w}x{frame_h}")
print("Clic gauche = cibler | bouton écran = mode traque | r = reset | q = quitter\n")

# ── Bouton Mode Traque (coordonnées en pixels frame) ──────────────────────────
BTN_W, BTN_H = 260, 52
BTN_X1 = frame_w // 2 - BTN_W // 2
BTN_Y1 = frame_h - BTN_H - 18
BTN_X2 = BTN_X1 + BTN_W
BTN_Y2 = BTN_Y1 + BTN_H

WIN = "Tracker Rover | clic=cibler | r=reset | d=drive | q=quitter"
if IS_WINDOWS:
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, min(frame_w, 1280), min(frame_h, 720))
    cv2.setMouseCallback(WIN, _mouse_cb)
else:
    _start_mjpeg()

# ── Variables d'état ──────────────────────────────────────────────────────────
target_id   = None
lost_frames = 0
smooth_cx   = None
smooth_cy   = None
error_x     = 0
error_y     = 0
current_bbox_h = 0

cmd_interval  = 1.0 / CMD_RATE_HZ
last_cmd_time = 0.0
fps_avg       = 0.0
t_prev        = time.time()

# ── Boucle principale ─────────────────────────────────────────────────────────
_yolo_counter = 0
_last_detections = []

while True:
    t_frame = time.time()

    ret, frame = cap.read()
    if not ret:
        print("Erreur lecture caméra.")
        break
    # Resize pour perf sur Android
    if not IS_WINDOWS:
        if frame.shape[1] > 400:
            frame = cv2.resize(frame, (320, 240))

    # ── Tracking (skip YOLO sur Android pour perf) ───────────────────────
    _yolo_counter += 1
    _run_yolo = IS_WINDOWS or (_yolo_counter % YOLO_SKIP == 0)

    if _run_yolo:
        detections = []
        if _USE_ULTRALYTICS:
            results = model.track(
                frame, persist=True, tracker="botsort.yaml",
                classes=[0], conf=CONF_THRESHOLD, verbose=False,
                imgsz=640, show=False)
            r_boxes = results[0].boxes
            if r_boxes is not None and r_boxes.id is not None:
                for b in r_boxes:
                    tid  = int(b.id[0])
                    x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                    conf = float(b.conf[0])
                    detections.append((tid, x1, y1, x2, y2, conf))
        else:
            raw_dets = model.detect(frame, classes=[0])
            tracked = _tracker.update(raw_dets)
            for tid, x1, y1, x2, y2, conf in tracked:
                detections.append((tid, int(x1), int(y1), int(x2), int(y2), conf))
        _last_detections = detections
    else:
        detections = _last_detections

    # ── Gestion clic souris ───────────────────────────────────────────────────
    if _click[0] >= 0:
        cx_click, cy_click = _click[0], _click[1]
        _click[0] = _click[1] = -1
        if IS_WINDOWS:
            try:
                _, _, disp_w, disp_h = cv2.getWindowImageRect(WIN)
                if disp_w > 0 and disp_h > 0 and (disp_w != frame_w or disp_h != frame_h):
                    cx_click = int(cx_click * frame_w / disp_w)
                    cy_click = int(cy_click * frame_h / disp_h)
            except Exception:
                pass

        if False:  # Bouton in-frame désactivé (HTML gère)
            pass
        else:
            matched = False
            print(f"[CLICK] coords=({cx_click},{cy_click})  {len(detections)} personne(s) détectée(s)")
            for tid, x1, y1, x2, y2, conf in detections:
                if (x1 - CLICK_MARGIN) <= cx_click <= (x2 + CLICK_MARGIN) and \
                   (y1 - CLICK_MARGIN) <= cy_click <= (y2 + CLICK_MARGIN):
                    target_id      = tid
                    lost_frames    = 0
                    smooth_cx      = None
                    smooth_cy      = None
                    current_bbox_h = 0
                    matched        = True
                    print(f"[LOCK] Cible sélectionnée : ID {target_id}")
                    break
            if not matched:
                print("[INFO] Aucune personne détectée à cet endroit.")

    # ── Recherche de la cible dans les détections ─────────────────────────────
    target_box = None
    for tid, x1, y1, x2, y2, conf in detections:
        if tid == target_id:
            target_box = (x1, y1, x2, y2)
            break

    now = time.time()

    # ── Mise à jour position lissée (EMA) ─────────────────────────────────────
    if target_box is not None:
        lost_frames    = 0
        current_bbox_h = target_box[3] - target_box[1]
        bx = (target_box[0] + target_box[2]) / 2.0
        by = target_box[1] + (target_box[3] - target_box[1]) * 0.12
        if smooth_cx is None:
            smooth_cx, smooth_cy = bx, by
        else:
            smooth_cx = SMOOTH_ALPHA * bx + (1 - SMOOTH_ALPHA) * smooth_cx
            smooth_cy = SMOOTH_ALPHA * by + (1 - SMOOTH_ALPHA) * smooth_cy
    elif target_id is not None:
        lost_frames += 1
        current_bbox_h = 0
        if lost_frames > LOST_TOLERANCE:
            print(f"[LOST] ID {target_id} perdue ({LOST_TOLERANCE} frames). Reset.")
            target_id      = None
            lost_frames    = 0
            smooth_cx      = None
            smooth_cy      = None
            current_bbox_h = 0

    # ── Mode auto-lock ─────────────────────────────────────────────────────────
    if AUTO_LOCK and target_id is None and detections:
        cx_frame = frame_w / 2.0
        cy_frame = frame_h / 2.0
        best = min(detections, key=lambda d: abs((d[1]+d[3])/2-cx_frame) + abs((d[2]+d[4])/2-cy_frame))
        target_id      = best[0]
        lost_frames    = 0
        smooth_cx      = None
        smooth_cy      = None
        current_bbox_h = 0
        print(f"[AUTO] Lock ID {target_id}")

    # ── Calcul erreurs pixel ──────────────────────────────────────────────────
    cx_frame = frame_w / 2.0
    cy_frame = frame_h / 2.0

    if target_box is not None and smooth_cx is not None:
        error_x = smooth_cx - cx_frame
        error_y = smooth_cy - cy_frame
    else:
        error_x = 0
        error_y = 0

    # ── Envoi série (rate-limited) — zone morte anti-jitter ──────────────────
    if now - last_cmd_time >= cmd_interval:
        ex_send = 0 if abs(error_x) < SERVO_DEADZONE else error_x
        ey_send = 0 if abs(error_y) < SERVO_DEADZONE else error_y
        send_command(arduino, ex_send, ey_send, current_bbox_h)
        last_cmd_time = now

    # ── Dessin ────────────────────────────────────────────────────────────────
    display = frame.copy()

    for tid, x1, y1, x2, y2, conf in detections:
        is_target = (tid == target_id)
        color     = (0, 255, 0)   if is_target else (255, 100, 0)
        thick     = 3             if is_target else 2
        cv2.rectangle(display, (x1, y1), (x2, y2), color, thick)
        if IS_WINDOWS:
            cv2.putText(display, f"ID:{tid}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    if target_box is not None and smooth_cx is not None:
        tcx = int(smooth_cx)
        tcy = int(smooth_cy)
        cv2.circle(display, (tcx, tcy), 8, (0, 255, 0), -1)
        cv2.line(display,
                 (int(cx_frame), int(cy_frame)),
                 (tcx, tcy),
                 (0, 255, 0), 2)
        if IS_WINDOWS:
            cv2.putText(display,
                        f"err_x={int(error_x):+d}  err_y={int(error_y):+d}  bbox_h={current_bbox_h}",
                        (target_box[0], target_box[3] + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    cv2.drawMarker(display,
                   (int(cx_frame), int(cy_frame)),
                   (0, 0, 255), cv2.MARKER_CROSS, 30, 2)

    # ── HUD ───────────────────────────────────────────────────────────────────
    dt      = max(t_frame - t_prev, 1e-6)
    fps_avg = 0.9 * fps_avg + 0.1 * (1.0 / dt)
    t_prev  = t_frame

    if target_id is not None:
        mode_txt   = f"LOCKED  ID:{target_id}"
        mode_color = (0, 255, 0)
    elif lost_frames > 0:
        mode_txt   = f"LOST  ({lost_frames}/{LOST_TOLERANCE})"
        mode_color = (0, 165, 255)
    else:
        mode_txt   = "IDLE"
        mode_color = (180, 180, 180)

    if IS_WINDOWS:
        cv2.putText(display, mode_txt,
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.85, mode_color, 2)
        cv2.putText(display, f"FPS: {fps_avg:.1f}",
                    (frame_w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
        ard_txt = f"Arduino: {arduino.port}" if arduino else "Arduino: OFF"
        cv2.putText(display, ard_txt,
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)
        if DRIVE_ENABLED and target_box is not None:
            if current_bbox_h < APPROACH_TARGET:
                drive_txt   = f"DRIVE: FORWARD  (bbox_h={current_bbox_h})"
                drive_color = (0, 200, 255)
            elif current_bbox_h > RETREAT_TARGET:
                drive_txt   = f"DRIVE: REVERSE  (bbox_h={current_bbox_h})"
                drive_color = (0, 80, 255)
            else:
                drive_txt   = f"DRIVE: HOLD  (bbox_h={current_bbox_h})"
                drive_color = (0, 255, 150)
        elif DRIVE_ENABLED:
            drive_txt   = "DRIVE: en attente de cible"
            drive_color = (0, 200, 100)
        else:
            drive_txt   = "TOURELLE seule"
            drive_color = (80, 80, 80)
        cv2.putText(display, drive_txt,
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.65, drive_color, 2)
    else:
        # Android: FPS dans le terminal toutes les 30 frames
        if _yolo_counter % 30 == 0:
            print(f"[PERF] FPS={fps_avg:.1f}  det={len(detections)}  target={target_id}", flush=True)

    # Bouton in-frame uniquement sur Windows (sur Android = HTML)
    if IS_WINDOWS:
        if DRIVE_ENABLED:
            btn_bg    = (0, 180, 0)
            btn_label = "  TRAQUE ON  –  clic pour desactiver"
        else:
            btn_bg    = (40, 40, 40)
            btn_label = "  TRAQUE OFF  –  clic pour activer"
        cv2.rectangle(display, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), btn_bg, -1)
        cv2.rectangle(display, (BTN_X1, BTN_Y1), (BTN_X2, BTN_Y2), (200, 200, 200), 2)
        cv2.putText(display, btn_label,
                    (BTN_X1 + 8, BTN_Y1 + 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    if IS_WINDOWS:
        cv2.imshow(WIN, display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            target_id = None; lost_frames = 0
            smooth_cx = None; smooth_cy = None; current_bbox_h = 0
            print("[RESET] Cible effacée.")
        elif key == ord('d'):
            DRIVE_ENABLED = not DRIVE_ENABLED
            print(f"[DRIVE] {'Activé' if DRIVE_ENABLED else 'Désactivé'} (touche d)")
    else:
        if _stream_clients > 0:
            ok, jpg = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 40])
            if ok:
                with _stream_lock:
                    _stream_jpg[0] = jpg.tobytes()
        _do_quit = False
        while _stream_cmd:
            cmd = _stream_cmd.pop(0)
            if cmd[0] == "click":
                _click[0], _click[1] = cmd[1], cmd[2]
            elif cmd[0] == "key":
                k = cmd[1]
                if k == 'q':
                    _do_quit = True
                elif k == 'r':
                    target_id = None; lost_frames = 0
                    smooth_cx = None; smooth_cy = None; current_bbox_h = 0
                    print("[RESET] Cible effacée.")
                elif k == 'd':
                    DRIVE_ENABLED = not DRIVE_ENABLED
                    print(f"[DRIVE] {'Activé' if DRIVE_ENABLED else 'Désactivé'} (web)")
                elif k == 'a':
                    AUTO_LOCK = not AUTO_LOCK
                    print(f"[AUTO] {'Activé' if AUTO_LOCK else 'Désactivé'} (web)")
        if _do_quit:
            break

# ── Nettoyage ─────────────────────────────────────────────────────────────────
send_command(arduino, 0, 0, 0)
cap.release()
if IS_WINDOWS:
    cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("Arrêt propre.")
