"""
tracker_v2.py
Pipeline découplé : la vidéo ne dépend plus de YOLO, YOLO ne prend jamais d'image en retard.

    Caméra (MJPEG)
      ├─► relais HTTP du MJPEG brut (pas de ré-encodage → qualité caméra intacte)
      └─► "dernière image" (taille 1, les anciennes sont écrasées)
              └─► thread inférence : décodage réduit → YOLO → tracker → cible
                      └─► thread contrôle à fréquence fixe → Arduino (protocole inchangé)
    Navigateur : vidéo + boîtes dessinées dans un <canvas> (Server-Sent Events) + métriques.

Protocole série identique à tracker_rover.py : "err_x err_y bbox_h\\n".
Les erreurs sont exprimées dans un repère 640x480 quelle que soit la résolution
caméra, donc les PID déjà réglés dans turret_rover.ino restent valables.

Exemples :
  python tracker_v2.py --source test --model demo            # sans caméra ni modèle
  python tracker_v2.py --source 0 --model yolo26n.onnx       # Linux : /dev/video0 via ffmpeg
  python tracker_v2.py --source "dshow:OsmoAction4" --size 1920x1080   # Windows + ffmpeg
  python tracker_v2.py --source 0 --backend opencv           # sans ffmpeg
  python tracker_v2.py --list-devices                        # noms DirectShow (Windows)
Puis ouvrir http://<ip>:8082
"""

import argparse
import json
import math
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import cv2
import numpy as np

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

from yolo_onnx import SimpleTracker

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"

# ── Paramètres ────────────────────────────────────────────────────────────────
ERR_REF_W, ERR_REF_H = 640, 480   # repère des erreurs envoyées à l'Arduino (PID réglés dessus)
SERVO_DEADZONE   = 8              # px (repère 640x480) : en dessous, pas de correction
SERIAL_BAUD      = 115200
CLICK_MARGIN     = 0.03           # tolérance du clic, en fraction de l'image
LOST_TOLERANCE_S = 1.0            # secondes sans détection avant de lâcher la cible
TARGET_Y_RATIO   = 0.12           # point visé : 12 % depuis le haut de la boîte (tête)
FILTER_ALPHA     = 0.6            # filtre alpha-bêta : poids de la mesure sur la position
FILTER_BETA      = 0.15           #                     poids de la mesure sur la vitesse
MAX_PREDICT_S    = 0.25           # extrapolation maximale de la position cible


# ── Utilitaires ───────────────────────────────────────────────────────────────
class Frame:
    __slots__ = ("seq", "t_cap", "jpeg", "bgr", "w", "h")

    def __init__(self, seq, t_cap, jpeg=None, bgr=None, w=0, h=0):
        self.seq, self.t_cap, self.jpeg, self.bgr, self.w, self.h = seq, t_cap, jpeg, bgr, w, h


class LatestSlot:
    """Boîte aux lettres de taille 1 : put() écrase, get_newer() attend une image plus récente."""

    def __init__(self):
        self._cond = threading.Condition()
        self._item = None
        self._seq = 0

    def put(self, item):
        with self._cond:
            self._seq += 1
            item.seq = self._seq
            self._item = item
            self._cond.notify_all()

    def get_newer(self, last_seq, timeout=1.0):
        with self._cond:
            self._cond.wait_for(lambda: self._seq > last_seq, timeout)
            if self._seq > last_seq:
                return self._item
            return None


class RateMeter:
    """Fréquence lissée (Hz) à partir des instants d'événements."""

    def __init__(self, alpha=0.1):
        self.alpha, self.hz, self._t = alpha, 0.0, None

    def tick(self, t=None):
        t = time.monotonic() if t is None else t
        if self._t is not None and t > self._t:
            inst = 1.0 / (t - self._t)
            self.hz = inst if self.hz == 0 else self.alpha * inst + (1 - self.alpha) * self.hz
        self._t = t


class Ema:
    def __init__(self, alpha=0.1):
        self.alpha, self.v = alpha, None

    def add(self, x):
        self.v = x if self.v is None else self.alpha * x + (1 - self.alpha) * self.v
        return self.v


def jpeg_size(jpeg):
    """Lit largeur/hauteur dans l'en-tête SOF d'un JPEG sans le décoder."""
    i = 2
    n = len(jpeg)
    while i + 9 < n:
        if jpeg[i] != 0xFF:
            i += 1
            continue
        marker = jpeg[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            return (jpeg[i + 7] << 8) | jpeg[i + 8], (jpeg[i + 5] << 8) | jpeg[i + 6]
        seg_len = (jpeg[i + 2] << 8) | jpeg[i + 3]
        i += 2 + seg_len
    return 0, 0


# ── Sources caméra ────────────────────────────────────────────────────────────
class FfmpegMjpegSource:
    """ffmpeg recopie le MJPEG de la caméra sans le décoder (-c:v copy).
    On récupère les JPEG bruts : relayés tels quels au navigateur, décodés à la demande pour YOLO."""

    def __init__(self, source, size, fps, slot, stop):
        self.slot, self.stop = slot, stop
        self.rate = RateMeter()
        self.cmd = self._build_cmd(source, size, fps)
        threading.Thread(target=self._run, daemon=True, name="capture").start()

    @staticmethod
    def _build_cmd(source, size, fps):
        w, h = size
        base = ["ffmpeg", "-hide_banner", "-loglevel", "error",
                "-fflags", "nobuffer", "-flags", "low_delay"]
        src = str(source)
        if src == "test":
            inp = ["-re", "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate={fps}",
                   "-c:v", "mjpeg", "-q:v", "5"]
        elif src.startswith("dshow:"):
            inp = ["-f", "dshow", "-rtbufsize", "64M", "-vcodec", "mjpeg",
                   "-video_size", f"{w}x{h}", "-framerate", str(fps),
                   "-i", f"video={src[6:]}", "-c:v", "copy"]
        elif src.startswith("http"):
            inp = ["-f", "mjpeg", "-i", src, "-c:v", "copy"]
        else:
            dev = f"/dev/video{src}" if src.isdigit() else src
            inp = ["-f", "v4l2", "-input_format", "mjpeg",
                   "-video_size", f"{w}x{h}", "-framerate", str(fps),
                   "-i", dev, "-c:v", "copy"]
        return base + inp + ["-an", "-f", "mjpeg", "pipe:1"]

    def _run(self):
        while not self.stop.is_set():
            print("[CAM] " + " ".join(self.cmd))
            proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, bufsize=0)
            buf = bytearray()
            size = (0, 0)
            try:
                while not self.stop.is_set():
                    chunk = proc.stdout.read(65536)
                    if not chunk:
                        break
                    buf += chunk
                    while True:
                        a = buf.find(b"\xff\xd8")
                        if a < 0:
                            buf.clear()
                            break
                        b = buf.find(b"\xff\xd9", a + 2)
                        if b < 0:
                            if a:
                                del buf[:a]
                            break
                        jpeg = bytes(buf[a:b + 2])
                        del buf[:b + 2]
                        t = time.monotonic()
                        if size == (0, 0):
                            size = jpeg_size(jpeg)
                            print(f"[CAM] Flux MJPEG reçu : {size[0]}x{size[1]}")
                        self.rate.tick(t)
                        self.slot.put(Frame(0, t, jpeg=jpeg, w=size[0], h=size[1]))
            finally:
                proc.kill()
                proc.wait()
            if not self.stop.is_set():
                print("[CAM] ffmpeg s'est arrêté, nouvelle tentative dans 1 s")
                time.sleep(1.0)


class OpenCVSource:
    """Repli sans ffmpeg : OpenCV décode chaque image. Le flux web est alors ré-encodé (qualité réglable)."""

    def __init__(self, source, size, fps, slot, stop):
        self.slot, self.stop = slot, stop
        self.rate = RateMeter()
        src = int(source) if str(source).isdigit() else source
        if IS_WINDOWS and isinstance(src, int):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(src, cv2.CAP_MSMF)
        else:
            self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise SystemExit(f"[CAM] Impossible d'ouvrir la caméra {source!r}")
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"[CAM] OpenCV : {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
              f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
        threading.Thread(target=self._run, daemon=True, name="capture").start()

    def _run(self):
        while not self.stop.is_set():
            ok, img = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            t = time.monotonic()
            self.rate.tick(t)
            self.slot.put(Frame(0, t, bgr=img, w=img.shape[1], h=img.shape[0]))
        self.cap.release()


# ── Détecteurs ────────────────────────────────────────────────────────────────
class DemoDetector:
    """Fausse personne qui se déplace : permet de tester tout le pipeline sans modèle."""

    def detect(self, img, classes=None):
        h, w = img.shape[:2]
        t = time.monotonic()
        cx = w * (0.5 + 0.3 * math.sin(t * 0.8))
        cy = h * (0.55 + 0.1 * math.sin(t * 1.3))
        bw, bh = w * 0.12, h * 0.45
        return [(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2, 0.9, 0)]


class NullDetector:
    def detect(self, img, classes=None):
        return []


class UltralyticsDetector:
    def __init__(self, path, conf, imgsz):
        from ultralytics import YOLO
        self.model, self.conf, self.imgsz = YOLO(path), conf, imgsz

    def detect(self, img, classes=None):
        r = self.model.predict(img, imgsz=self.imgsz, conf=self.conf,
                               classes=classes, verbose=False)[0]
        out = []
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            out.append((x1, y1, x2, y2, float(b.conf[0]), int(b.cls[0])))
        return out


def make_detector(model, conf, imgsz):
    if model == "demo":
        return DemoDetector()
    if model == "none":
        return NullDetector()
    path = model if os.path.isabs(model) else os.path.join(_SCRIPT_DIR, model)
    if not os.path.exists(path):
        raise SystemExit(f"[YOLO] Modèle introuvable : {path}")
    if path.endswith(".pt"):
        return UltralyticsDetector(path, conf, imgsz)
    from yolo_onnx import YOLODetector
    return YOLODetector(path, conf=conf, imgsz=imgsz)


# ── État partagé : pistes, cible, filtre ──────────────────────────────────────
class TargetState:
    """Pistes courantes (coordonnées normalisées 0..1), cible verrouillée et filtre alpha-bêta."""

    def __init__(self, auto_lock):
        self.lock = threading.Condition()
        self.version = 0
        self.tracks = []          # [(id, x1, y1, x2, y2, conf)] normalisés
        self.target_id = None
        self.auto_lock = auto_lock
        self.drive = False
        self.t_seen = 0.0         # dernier instant (capture) où la cible a été vue
        self.pos = None           # [x, y] normalisé, filtré
        self.vel = [0.0, 0.0]
        self.box_h = 0.0
        self.t_meas = 0.0

    def _reset_target(self):
        self.target_id, self.pos, self.vel, self.box_h = None, None, [0.0, 0.0], 0.0

    def update(self, tracks, t_cap):
        with self.lock:
            self.tracks = tracks
            if self.target_id is None and self.auto_lock and tracks:
                best = min(tracks, key=lambda d: abs((d[1] + d[3]) / 2 - 0.5) + abs((d[2] + d[4]) / 2 - 0.5))
                self.target_id = best[0]
                print(f"[AUTO] Cible ID {self.target_id}")
            tgt = next((d for d in tracks if d[0] == self.target_id), None)
            if tgt is not None:
                _, x1, y1, x2, y2, _ = tgt
                z = [(x1 + x2) / 2, y1 + (y2 - y1) * TARGET_Y_RATIO]
                if self.pos is None:
                    self.pos, self.vel = z, [0.0, 0.0]
                else:
                    dt = max(t_cap - self.t_meas, 1e-3)
                    for i in range(2):
                        pred = self.pos[i] + self.vel[i] * dt
                        r = z[i] - pred
                        self.pos[i] = pred + FILTER_ALPHA * r
                        self.vel[i] += FILTER_BETA * r / dt
                self.box_h = y2 - y1
                self.t_meas = self.t_seen = t_cap
            elif self.target_id is not None and t_cap - self.t_seen > LOST_TOLERANCE_S:
                print(f"[LOST] ID {self.target_id} perdue")
                self._reset_target()
            self.version += 1
            self.lock.notify_all()

    def estimate(self, t_now, predict):
        """Position cible extrapolée à t_now (compense la latence capture → commande)."""
        with self.lock:
            if self.pos is None or t_now - self.t_seen > 0.3:
                return None
            h = min(max(t_now - self.t_meas, 0.0), MAX_PREDICT_S) if predict else 0.0
            return (self.pos[0] + self.vel[0] * h, self.pos[1] + self.vel[1] * h, self.box_h)

    def click(self, nx, ny):
        with self.lock:
            for d in self.tracks:
                if d[1] - CLICK_MARGIN <= nx <= d[3] + CLICK_MARGIN and \
                   d[2] - CLICK_MARGIN <= ny <= d[4] + CLICK_MARGIN:
                    self._reset_target()
                    self.target_id = d[0]
                    self.t_seen = time.monotonic()
                    print(f"[LOCK] Cible ID {self.target_id}")
                    return
            print("[CLICK] Aucune détection à cet endroit")

    def key(self, k):
        with self.lock:
            if k == "r":
                self._reset_target()
                print("[RESET] Cible effacée")
            elif k == "d":
                self.drive = not self.drive
                print(f"[DRIVE] {'ON' if self.drive else 'OFF'}")
            elif k == "a":
                self.auto_lock = not self.auto_lock
                print(f"[AUTO] {'ON' if self.auto_lock else 'OFF'}")


# ── Thread inférence ──────────────────────────────────────────────────────────
class InferenceWorker:
    def __init__(self, slot, detector, state, stop, reduce, classes):
        self.slot, self.detector, self.state, self.stop = slot, detector, state, stop
        self.reduce, self.classes = reduce, classes
        self.tracker = SimpleTracker(iou_thresh=0.3, max_lost=30)
        self.rate = RateMeter()
        self.decode_ms, self.infer_ms, self.age_ms = Ema(), Ema(), Ema()
        self.dropped = 0
        threading.Thread(target=self._run, daemon=True, name="inference").start()

    def _run(self):
        last = 0
        while not self.stop.is_set():
            fr = self.slot.get_newer(last, 1.0)
            if fr is None:
                continue
            if last:
                self.dropped += fr.seq - last - 1
            last = fr.seq
            t0 = time.monotonic()
            if fr.jpeg is not None:
                # Décodage directement à 1/2 ou 1/4 de la taille (DCT réduite) : bien plus rapide,
                # et YOLO travaille de toute façon en 640.
                flag = cv2.IMREAD_COLOR
                if self.reduce and fr.w >= 2560:
                    flag = cv2.IMREAD_REDUCED_COLOR_4
                elif self.reduce and fr.w >= 1280:
                    flag = cv2.IMREAD_REDUCED_COLOR_2
                img = cv2.imdecode(np.frombuffer(fr.jpeg, np.uint8), flag)
                if img is None:
                    continue
            else:
                img = fr.bgr
            t1 = time.monotonic()
            dets = self.detector.detect(img, classes=self.classes)
            tracks = self.tracker.update(dets)
            t2 = time.monotonic()
            h, w = img.shape[:2]
            norm = [(int(tid), x1 / w, y1 / h, x2 / w, y2 / h, float(c))
                    for tid, x1, y1, x2, y2, c in tracks]
            self.state.update(norm, fr.t_cap)
            self.decode_ms.add((t1 - t0) * 1000)
            self.infer_ms.add((t2 - t1) * 1000)
            self.age_ms.add((t2 - fr.t_cap) * 1000)
            self.rate.tick(t2)


# ── Arduino ───────────────────────────────────────────────────────────────────
def open_serial(port):
    if port == "none" or serial is None:
        print("[SERIAL] Désactivé" + (" (pyserial absent)" if serial is None else ""))
        return None
    if port is None:
        cands = [p.device for p in serial.tools.list_ports.comports()
                 if any(k in (p.description or "").lower() for k in ("arduino", "ch340", "ftdi", "acm", "usb serial"))]
        if not cands:
            print("[SERIAL] Aucun Arduino détecté – mode vision seule")
            return None
        port = cands[0]
    try:
        ser = serial.Serial(port, SERIAL_BAUD, timeout=0, write_timeout=0.05)
        time.sleep(0.5)
        print(f"[SERIAL] Arduino : {port}")
        return ser
    except (serial.SerialException, OSError) as e:
        print(f"[SERIAL] Erreur {port} : {e} – mode vision seule")
        return None


class ControlLoop:
    """Envoie la consigne à fréquence fixe, indépendamment du rythme de YOLO."""

    def __init__(self, ser, state, stop, rate_hz, predict, cam_latency):
        self.ser, self.state, self.stop = ser, state, stop
        self.period, self.predict, self.cam_latency = 1.0 / rate_hz, predict, cam_latency
        self.last_cmd = (0, 0, 0)
        threading.Thread(target=self._run, daemon=True, name="control").start()

    def _run(self):
        t_next = time.monotonic()
        while not self.stop.is_set():
            est = self.state.estimate(time.monotonic() + self.cam_latency, self.predict)
            if est is None:
                ex = ey = bh = 0
            else:
                x, y, box_h = est
                ex = (x - 0.5) * ERR_REF_W
                ey = (y - 0.5) * ERR_REF_H
                ex = 0 if abs(ex) < SERVO_DEADZONE else int(ex)
                ey = 0 if abs(ey) < SERVO_DEADZONE else int(ey)
                bh = int(box_h * ERR_REF_H) if self.state.drive else 0
            self.last_cmd = (ex, ey, bh)
            if self.ser is not None:
                try:
                    self.ser.write(f"{ex} {ey} {bh}\n".encode())
                except (serial.SerialException, OSError):
                    pass
            t_next += self.period
            time.sleep(max(0.0, t_next - time.monotonic()))
        if self.ser is not None:
            try:
                self.ser.write(b"0 0 0\n")
                self.ser.close()
            except (serial.SerialException, OSError):
                pass


# ── Serveur web ───────────────────────────────────────────────────────────────
_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tracker Rover v2</title>
<style>
body{background:#111;color:#eee;font-family:system-ui,sans-serif;margin:0;text-align:center}
#wrap{position:relative;display:inline-block;max-width:100%}
#v{display:block;max-width:100%;max-height:80vh}
#o{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair}
#hud{font:13px monospace;margin:6px;white-space:pre-wrap}
button{margin:4px;padding:10px 16px;font-size:1em;border:0;border-radius:8px;color:#fff;background:#444;cursor:pointer}
button.on{background:#2a2}
</style></head><body>
<div id="wrap"><img id="v" src="/stream"><canvas id="o"></canvas></div>
<div id="hud">connexion…</div>
<button id="bd" onclick="key('d')">Drive</button>
<button id="ba" onclick="key('a')">Auto</button>
<button onclick="key('r')">Reset cible</button>
<button onclick="key('q')">Quitter</button>
<script>
const v=document.getElementById('v'),o=document.getElementById('o'),c=o.getContext('2d');
let st=null;
function post(p,b){fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});}
function key(k){post('/key',{key:k});}
document.addEventListener('keydown',e=>{if('rdaq'.includes(e.key))key(e.key);});
o.addEventListener('click',e=>{const r=o.getBoundingClientRect();
  post('/click',{x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height});});
function draw(){
  const d=window.devicePixelRatio||1,W=o.clientWidth,H=o.clientHeight;
  if(o.width!==W*d||o.height!==H*d){o.width=W*d;o.height=H*d;}
  c.setTransform(d,0,0,d,0,0);c.clearRect(0,0,W,H);
  c.strokeStyle='#f33';c.lineWidth=2;c.beginPath();
  c.moveTo(W/2-12,H/2);c.lineTo(W/2+12,H/2);c.moveTo(W/2,H/2-12);c.lineTo(W/2,H/2+12);c.stroke();
  if(!st)return;
  c.font='13px monospace';
  for(const [id,x1,y1,x2,y2,cf] of st.tracks){
    const t=id===st.target;c.strokeStyle=c.fillStyle=t?'#0f0':'#fa0';c.lineWidth=t?3:2;
    c.strokeRect(x1*W,y1*H,(x2-x1)*W,(y2-y1)*H);c.fillText('ID '+id+' '+cf.toFixed(2),x1*W+3,y1*H-4);
  }
  if(st.aim){c.fillStyle='#0f0';c.beginPath();c.arc(st.aim[0]*W,st.aim[1]*H,6,0,7);c.fill();}
}
const es=new EventSource('/events');
es.onmessage=e=>{st=JSON.parse(e.data);const m=st.m;
  document.getElementById('bd').className=st.drive?'on':'';
  document.getElementById('ba').className=st.auto?'on':'';
  document.getElementById('hud').textContent=
   `${st.target!==null?'CIBLE ID '+st.target:'IDLE'} | cmd ${st.cmd.join(' ')} | ${m.size}\\n`+
   `caméra ${m.cam_fps} fps | YOLO ${m.det_fps} fps (décodage ${m.dec_ms} ms, inférence ${m.inf_ms} ms) | `+
   `âge à la décision ${m.age_ms} ms | images sautées ${m.dropped}`;
  draw();};
es.onerror=()=>{document.getElementById('hud').textContent='connexion perdue…';};
window.addEventListener('resize',draw);
</script></body></html>"""


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/":
                body = _HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/stream":
                self._stream()
            elif self.path == "/events":
                self._events()
            else:
                self.send_error(404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                data = {}
            if self.path == "/click":
                app.state.click(float(data.get("x", -1)), float(data.get("y", -1)))
            elif self.path == "/key":
                k = str(data.get("key", ""))
                if k == "q":
                    app.stop.set()
                else:
                    app.state.key(k)
            self.send_response(204)
            self.end_headers()

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            app.clients += 1
            last = 0
            try:
                while not app.stop.is_set():
                    fr = app.slot.get_newer(last, 1.0)
                    if fr is None:
                        continue
                    last = fr.seq
                    jpeg = app.jpeg_for(fr)
                    # Un client lent saute naturellement des images : on reprend toujours la plus récente.
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
                    app.stream_rate.tick()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                app.clients -= 1

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            ver = -1
            try:
                while not app.stop.is_set():
                    with app.state.lock:
                        app.state.lock.wait_for(lambda: app.state.version != ver, 0.5)
                        ver = app.state.version
                    self.wfile.write(b"data: " + json.dumps(app.snapshot()).encode() + b"\n\n")
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

    return Handler


class App:
    def __init__(self, args):
        self.stop = threading.Event()
        self.slot = LatestSlot()
        self.state = TargetState(auto_lock=args.auto)
        self.clients = 0
        self.stream_rate = RateMeter()
        self._jpeg_cache = (0, b"")
        self._jpeg_lock = threading.Lock()
        self.jpeg_quality = args.stream_quality

        w, h = (int(v) for v in args.size.lower().split("x"))
        backend = args.backend
        if backend == "auto":
            usable = shutil.which("ffmpeg") and not (IS_WINDOWS and str(args.source).isdigit())
            backend = "ffmpeg" if usable else "opencv"
        src_cls = FfmpegMjpegSource if backend == "ffmpeg" else OpenCVSource
        print(f"[CAM] Backend : {backend}")

        detector = make_detector(args.model, args.conf, args.imgsz)
        classes = None if args.classes == "all" else [int(c) for c in args.classes.split(",")]
        self.source = src_cls(args.source, (w, h), args.fps, self.slot, self.stop)
        self.infer = InferenceWorker(self.slot, detector, self.state, self.stop,
                                     reduce=not args.no_reduce, classes=classes)
        self.control = ControlLoop(open_serial(args.serial), self.state, self.stop,
                                   args.cmd_rate, not args.no_predict, args.cam_latency / 1000)
        srv = _Server(("0.0.0.0", args.port), make_handler(self))
        threading.Thread(target=srv.serve_forever, daemon=True, name="http").start()
        self.server = srv
        print(f"[WEB] http://{local_ip()}:{args.port}  (ou http://localhost:{args.port})")

    def jpeg_for(self, fr):
        if fr.jpeg is not None:
            return fr.jpeg
        with self._jpeg_lock:
            if self._jpeg_cache[0] != fr.seq:
                ok, enc = cv2.imencode(".jpg", fr.bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                self._jpeg_cache = (fr.seq, enc.tobytes() if ok else b"")
            return self._jpeg_cache[1]

    def metrics(self):
        fr = self.slot.get_newer(-1, 0)
        r = lambda x: None if x is None else round(x, 1)
        return {
            "size": f"{fr.w}x{fr.h}" if fr else "-",
            "cam_fps": r(self.source.rate.hz), "det_fps": r(self.infer.rate.hz),
            "dec_ms": r(self.infer.decode_ms.v), "inf_ms": r(self.infer.infer_ms.v),
            "age_ms": r(self.infer.age_ms.v), "dropped": self.infer.dropped,
            "stream_fps": r(self.stream_rate.hz), "clients": self.clients,
        }

    def snapshot(self):
        s = self.state
        est = s.estimate(time.monotonic(), predict=False)
        with s.lock:
            return {"tracks": [[t[0]] + [round(v, 4) for v in t[1:]] for t in s.tracks],
                    "target": s.target_id, "drive": s.drive, "auto": s.auto_lock,
                    "aim": [round(est[0], 4), round(est[1], 4)] if est else None,
                    "cmd": list(self.control.last_cmd), "m": self.metrics()}

    def run(self):
        t_log = time.monotonic()
        try:
            while not self.stop.wait(0.5):
                if time.monotonic() - t_log >= 5:
                    t_log = time.monotonic()
                    m = self.metrics()
                    print(f"[PERF] {m['size']} caméra {m['cam_fps']} fps | YOLO {m['det_fps']} fps "
                          f"(déc {m['dec_ms']} ms, inf {m['inf_ms']} ms) "
                          f"| âge {m['age_ms']} ms | sautées {m['dropped']} | clients {m['clients']}")
        except KeyboardInterrupt:
            self.stop.set()
        time.sleep(0.3)
        self.server.shutdown()
        print("Arrêt propre.")


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "localhost"


def default_model():
    for name in ("yolo26n.onnx", "yolov8n.onnx", "yolo11n.onnx"):
        if os.path.exists(os.path.join(_SCRIPT_DIR, name)):
            return name
    return "yolov8n.onnx"


def main():
    p = argparse.ArgumentParser(description="Tracker rover v2 – pipeline YOLO découplé")
    p.add_argument("--source", default="0",
                   help="index caméra, /dev/videoN, dshow:<nom> (Windows), URL MJPEG, ou 'test'")
    p.add_argument("--backend", choices=("auto", "ffmpeg", "opencv"), default="auto")
    p.add_argument("--size", default="1920x1080", help="résolution demandée à la caméra")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--model", default=default_model(), help=".onnx, .pt, 'demo' ou 'none'")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--classes", default="0", help="classes COCO, ex. '0' (personne) ou 'all'")
    p.add_argument("--no-reduce", action="store_true", help="décoder en pleine résolution pour YOLO")
    p.add_argument("--serial", default=None, help="port Arduino (auto par défaut), 'none' pour désactiver")
    p.add_argument("--cmd-rate", type=float, default=30, help="fréquence d'envoi des consignes (Hz)")
    p.add_argument("--no-predict", action="store_true", help="désactive l'extrapolation de la cible")
    p.add_argument("--cam-latency", type=float, default=0, help="latence caméra estimée (ms) à compenser")
    p.add_argument("--auto", action="store_true", help="verrouille automatiquement la cible la plus centrale")
    p.add_argument("--port", type=int, default=8082)
    p.add_argument("--stream-quality", type=int, default=80, help="qualité JPEG du flux (backend opencv)")
    p.add_argument("--list-devices", action="store_true", help="liste les caméras DirectShow via ffmpeg")
    args = p.parse_args()

    if args.list_devices:
        subprocess.run(["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"])
        return
    App(args).run()


if __name__ == "__main__":
    main()
