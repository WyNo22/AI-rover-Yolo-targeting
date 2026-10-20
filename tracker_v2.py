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
  python3 tracker_v2.py --source 0 --model yolov8s_h8.hef    # Raspberry Pi 5 + AI HAT+ (Hailo)
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

from behavior import Behavior
from gestures import DemoPoseDetector, GestureRecognizer, KP_MIN
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
TORSO_M          = 0.50           # longueur épaules → hanches d'un adulte (estimation de distance)
PERSON_M         = 1.70           # taille d'une personne debout (repli si pas de squelette)


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
        import torch
        self.device = "0" if torch.cuda.is_available() else "cpu"
        self.model, self.conf, self.imgsz = YOLO(path), conf, imgsz
        gpu = torch.cuda.get_device_name(0) if self.device != "cpu" else "CPU (PyTorch sans CUDA)"
        print(f"[YOLO] {os.path.basename(path)} sur {gpu}")

    def detect(self, img, classes=None):
        r = self.model.predict(img, imgsz=self.imgsz, conf=self.conf, classes=classes,
                               device=self.device, verbose=False)[0]
        kps = r.keypoints.data.cpu().numpy() if r.keypoints is not None else None
        out = []
        for i, b in enumerate(r.boxes):
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            d = (x1, y1, x2, y2, float(b.conf[0]), int(b.cls[0]))
            out.append(d + (kps[i],) if kps is not None else d)
        return out


def make_detector(model, conf, imgsz):
    if model == "demo":
        return DemoDetector()
    if model == "demo-pose":
        return DemoPoseDetector()
    if model == "none":
        return NullDetector()
    if model.endswith(".hef"):
        from yolo_hailo import find_hef, make_hailo_detector
        path = find_hef(model)
        if path is None:
            raise SystemExit(f"[YOLO] Modèle Hailo introuvable : {model} (voir ls /usr/share/hailo-models)")
        return make_hailo_detector(path, conf)
    path = model if os.path.isabs(model) else os.path.join(_SCRIPT_DIR, model)
    if path.endswith(".pt"):
        # nom nu si absent : ultralytics télécharge alors le modèle officiel
        return UltralyticsDetector(path if os.path.exists(path) else model, conf, imgsz)
    if not os.path.exists(path):
        raise SystemExit(f"[YOLO] Modèle introuvable : {path}")
    from yolo_onnx import YOLODetector
    return YOLODetector(path, conf=conf, imgsz=imgsz)


# ── État partagé : pistes, cible, filtre ──────────────────────────────────────
class TargetState:
    """Pistes courantes (coordonnées normalisées 0..1), cible verrouillée et filtre alpha-bêta."""

    def __init__(self, auto_lock):
        self.lock = threading.Condition()
        self.version = 0
        self.tracks = []          # [(id, x1, y1, x2, y2, conf)] normalisés
        self.kpts = {}            # id → points du corps (17, 3) normalisés (modèles -pose)
        self.gest = ({}, {})      # (id → (geste, progression), id → direction pointée)
        self.t_cap = 0.0
        self.target_id = None
        self.auto_lock = auto_lock
        self.paused = False       # REPOS : pas de verrouillage automatique
        self.drive = False
        self.t_seen = 0.0         # dernier instant (capture) où la cible a été vue
        self.pos = None           # [x, y] normalisé, filtré
        self.vel = [0.0, 0.0]
        self.box_h = 0.0
        self.t_meas = 0.0

    def _reset_target(self):
        self.target_id, self.pos, self.vel, self.box_h = None, None, [0.0, 0.0], 0.0

    def lock_on(self, tid):
        with self.lock:
            if tid != self.target_id:
                self._reset_target()
                self.target_id = tid
                self.t_seen = time.monotonic()
                print(f"[LOCK] Cible ID {tid}")

    def release(self):
        with self.lock:
            self._reset_target()

    def update(self, tracks, t_cap, kpts=None, gest=({}, {})):
        with self.lock:
            self.tracks, self.kpts, self.gest, self.t_cap = tracks, kpts or {}, gest, t_cap
            if self.target_id is None and self.auto_lock and not self.paused and tracks:
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
    def __init__(self, slot, detector, state, stop, reduce, classes, gestures=None, behavior=None):
        self.slot, self.detector, self.state, self.stop = slot, detector, state, stop
        self.gestures, self.behavior = gestures, behavior
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
            tracks = self.tracker.update([d[:6] for d in dets])
            t2 = time.monotonic()
            h, w = img.shape[:2]
            norm = [(int(tid), x1 / w, y1 / h, x2 / w, y2 / h, float(c))
                    for tid, x1, y1, x2, y2, c in tracks]
            # Le tracker renvoie les boîtes détectées telles quelles : on y raccroche les squelettes
            by_box = {tuple(np.round(d[:4], 2)): d[6] for d in dets if len(d) > 6}
            kpts = {}
            for tid, x1, y1, x2, y2, _ in tracks:
                k = by_box.get(tuple(np.round((x1, y1, x2, y2), 2)))
                if k is not None:
                    k = np.array(k, np.float32)
                    k[:, 0] /= w
                    k[:, 1] /= h
                    kpts[int(tid)] = k
            events, gest = [], ({}, {})
            if self.gestures is not None:
                events = self.gestures.update(fr.t_cap, kpts, w / h)
                gest = (self.gestures.current, self.gestures.pointing)
            self.state.update(norm, fr.t_cap, kpts, gest)      # squelettes et gestes publiés ensemble
            if self.behavior is not None:
                self.behavior.on_events(events)
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
                 if any(k in (p.description or "").lower() for k in ("arduino", "ch340", "ftdi", "acm", "usb serial"))
                 or "ttyACM" in p.device or "ttyUSB" in p.device]
        if not cands:
            print("[SERIAL] Aucun Arduino détecté – mode vision seule")
            return None
        port = cands[0]
    try:
        ser = serial.Serial(port, SERIAL_BAUD, timeout=0.1, write_timeout=0.05)
        time.sleep(2.0)       # l'ouverture du port redémarre l'Arduino : attendre la fin du bootloader
        print(f"[SERIAL] Arduino : {port}")
        threading.Thread(target=_serial_reader, args=(ser,), daemon=True, name="serial-rx").start()
        return ser
    except (serial.SerialException, OSError) as e:
        print(f"[SERIAL] Erreur {port} : {e} – mode vision seule")
        return None


def _serial_reader(ser):
    """Vide le tampon de réception et affiche les messages utiles de l'Arduino (mode RC/AUTO, PID…)."""
    while True:
        try:
            line = ser.readline().decode(errors="replace").strip()
        except (serial.SerialException, OSError, TypeError):
            return
        if line and not line.startswith(("[RC]", "[MOT]")):
            print(f"[ARDUINO] {line}")


class ControlLoop:
    """Envoie la consigne à fréquence fixe, indépendamment du rythme de YOLO."""

    def __init__(self, ser, state, stop, rate_hz, predict, cam_latency, behavior=None):
        self.ser, self.state, self.stop, self.behavior = ser, state, stop, behavior
        self.period, self.predict, self.cam_latency = 1.0 / rate_hz, predict, cam_latency
        self.last_cmd = (0, 0, 0)
        threading.Thread(target=self._run, daemon=True, name="control").start()

    def _run(self):
        t_next = time.monotonic()
        while not self.stop.is_set():
            ov = self.behavior.override(time.monotonic()) if self.behavior else None
            est = None if ov else self.state.estimate(time.monotonic() + self.cam_latency, self.predict)
            if ov:
                ex, ey, bh = ov            # animation ou arrêt imposés par le comportement
            elif est is None:
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
#v{display:block;max-width:100%;max-height:80vh;min-width:320px;min-height:180px;background:#000}
#o{position:absolute;inset:0;width:100%;height:100%;cursor:crosshair}
#hud{font:13px monospace;margin:6px;white-space:pre-wrap}
button{margin:4px;padding:10px 16px;font-size:1em;border:0;border-radius:8px;color:#fff;background:#444;cursor:pointer}
button.on{background:#2a2}
#aide{font-size:13px;color:#aaa;margin:6px 10px 14px}
</style></head><body>
<div id="wrap"><img id="v" alt=""><canvas id="o"></canvas></div>
<div id="hud">connexion…</div>
<button id="bd" onclick="key('d')">Drive</button>
<button id="ba" onclick="key('a')">Auto</button>
<button onclick="key('r')">Reset cible</button>
<button onclick="key('p')">Reprendre</button>
<button onclick="key('q')">Quitter</button>
<div id="aide">✋ 1 main levée 1 s = « c'est moi, écoute » · puis dans les 3 s : 👉 bras tendu = regarde là ·
🤏 avant-bras qui se replie = viens · 🦘 plier les genoux et se redresser = saute · ❌ bras croisés = repos<br>
🙌 deux bras levés = STOP (tout le monde) · 👋 coucou (tout le monde)</div>
<script>
const v=document.getElementById('v'),o=document.getElementById('o'),c=o.getContext('2d');
const SK=[[5,7],[7,9],[6,8],[8,10],[5,6],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16],[0,1],[0,2],[1,3],[2,4]];
const COL={SUIVI:'#2a2',ATTENTE:'#666',ECOUTE:'#08f',ARRET:'#d22',REPOS:'#a6a'};
const GN={STOP:'🙌 STOP',ECOUTE:'✋ écoute',POINTE:'👉 pointe',REPOS:'❌ repos'};
let st=null;
function post(p,b){fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});}
function key(k){post('/key',{key:k});}
document.addEventListener('keydown',e=>{if('rdaqp'.includes(e.key))key(e.key);});
o.addEventListener('click',e=>{const r=o.getBoundingClientRect();
  post('/click',{x:(e.clientX-r.left)/r.width,y:(e.clientY-r.top)/r.height});});
function label(x,y,txt,col,W){c.font='bold 15px system-ui';const w=c.measureText(txt).width+10;
  x=Math.min(Math.max(x,0),W-w);c.fillStyle='rgba(0,0,0,.65)';c.fillRect(x,y-18,w,22);
  c.fillStyle=col;c.fillText(txt,x+5,y-2);}
function draw(){
  const d=window.devicePixelRatio||1,W=o.clientWidth,H=o.clientHeight;
  if(o.width!==W*d||o.height!==H*d){o.width=W*d;o.height=H*d;}
  c.setTransform(d,0,0,d,0,0);c.clearRect(0,0,W,H);
  c.strokeStyle='#f33';c.lineWidth=2;c.beginPath();
  c.moveTo(W/2-12,H/2);c.lineTo(W/2+12,H/2);c.moveTo(W/2,H/2-12);c.lineTo(W/2,H/2+12);c.stroke();
  if(!st)return;
  for(const [id,x1,y1,x2,y2,cf] of st.tracks){
    const t=id===st.target,col=t?'#0f0':'#fa0',k=st.kp[id];
    c.strokeStyle=col;c.lineWidth=t?3:1.5;c.setLineDash(k?[6,4]:[]);
    c.strokeRect(x1*W,y1*H,(x2-x1)*W,(y2-y1)*H);c.setLineDash([]);
    if(k){c.strokeStyle=t?'#0ff':'#fd6';c.lineWidth=3;c.beginPath();
      for(const [a,b] of SK){if(k[a*3+2]>=0.4&&k[b*3+2]>=0.4){
        c.moveTo(k[a*3]*W,k[a*3+1]*H);c.lineTo(k[b*3]*W,k[b*3+1]*H);}}
      c.stroke();c.fillStyle='#fff';
      for(let i=0;i<17;i++)if(k[i*3+2]>=0.4){c.beginPath();c.arc(k[i*3]*W,k[i*3+1]*H,3,0,7);c.fill();}
      const p=st.pt[id];
      if(p&&k[5*3+2]>=0.4){const sx=(k[15]+k[18])/2*W,sy=(k[16]+k[19])/2*H,L=H*0.35;
        c.strokeStyle='#ff0';c.lineWidth=4;c.beginPath();c.moveTo(sx,sy);
        c.lineTo(sx+p[0]*L,sy+p[1]*L);c.stroke();}}
    let txt=(t?'★ ':'')+'#'+id;const g=st.g[id];
    if(g)txt+='  '+(GN[g[0]]||g[0]);
    label(x1*W,y1*H,txt,col,W);
    if(g&&g[1]<1){c.fillStyle='#08f';c.fillRect(x1*W,y1*H+5,(x2-x1)*W*g[1],5);}
  }
  if(st.aim){c.fillStyle='#0f0';c.beginPath();c.arc(st.aim[0]*W,st.aim[1]*H,6,0,7);c.fill();}
  const b=st.beh;if(!b)return;
  let txt=b.etat+' – '+b.texte+(b.etat==='ECOUTE'?' ('+b.ecoute_restant+' s)':'')+(b.action?'  → '+b.action:'');
  c.font='bold 18px system-ui';const w=c.measureText(txt).width+16;
  c.fillStyle=COL[b.etat]||'#444';c.globalAlpha=.85;c.fillRect(8,8,w,30);c.globalAlpha=1;
  c.fillStyle='#fff';c.fillText(txt,16,29);
  let y=H-10;c.font='14px system-ui';
  for(const e of b.evenements.slice().reverse()){const age=b.now-e.t;if(age>6)continue;
    c.globalAlpha=Math.max(0,1-age/6);const w2=c.measureText(e.msg).width+10;
    c.fillStyle='rgba(0,0,0,.7)';c.fillRect(8,y-17,w2,22);c.fillStyle='#fff';c.fillText(e.msg,13,y);y-=26;}
  c.globalAlpha=1;
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
// Vidéo : la page demande la dernière image, l'affiche, puis redemande. Le débit s'adapte
// tout seul au Wi-Fi : pas de file d'images en retard, contrairement à un flux MJPEG poussé.
(async()=>{let seq=0,url=null;
  for(;;){try{const r=await fetch('/frame.jpg?after='+seq,{cache:'no-store'});
      if(r.status!==200){await new Promise(z=>setTimeout(z,200));continue;}
      seq=+r.headers.get('X-Seq')||0;const u=URL.createObjectURL(await r.blob());
      v.src=u;await v.decode().catch(()=>{});if(url)URL.revokeObjectURL(url);url=u;draw();
    }catch(e){await new Promise(z=>setTimeout(z,500));}}})();
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
                print(f"[WEB] Page ouverte par {self.client_address[0]}")
                body = _HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/frame.jpg"):
                self._frame()
            elif self.path == "/stream":
                self._stream()
            elif self.path == "/events":
                self._events()
            elif self.path in ("/perception", "/etat"):
                data = app.perception() if self.path == "/perception" else app.behavior.etat()
                body = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
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
                elif k == "p":
                    app.behavior.resume()
                else:
                    app.state.key(k)
            self.send_response(204)
            self.end_headers()

        def _frame(self):
            try:
                after = int(self.path.split("after=")[1]) if "after=" in self.path else 0
            except ValueError:
                after = 0
            fr = app.slot.get_newer(after, 1.0)
            if fr is None:
                self.send_response(204)
                self.end_headers()
                return
            jpeg = app.jpeg_for(fr)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Seq", str(fr.seq))
            self.end_headers()
            try:
                self.wfile.write(jpeg)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
            app.stream_rate.tick()
            app.last_pull = time.monotonic()

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
        self.last_pull = 0.0
        self.stream_rate = RateMeter()
        self._jpeg_cache = (0, b"")
        self._jpeg_lock = threading.Lock()
        self.jpeg_quality = args.stream_quality
        self.hfov = args.hfov
        self.behavior = Behavior(self.state)
        self.gestures = None if args.no_gestes else GestureRecognizer()

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
                                     reduce=not args.no_reduce, classes=classes,
                                     gestures=self.gestures, behavior=self.behavior)
        self.control = ControlLoop(open_serial(args.serial), self.state, self.stop,
                                   args.cmd_rate, not args.no_predict, args.cam_latency / 1000,
                                   behavior=self.behavior)
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
            "stream_fps": r(self.stream_rate.hz), "clients": self.clients + (time.monotonic() - self.last_pull < 2),
        }

    def snapshot(self):
        s = self.state
        est = s.estimate(time.monotonic(), predict=False)
        beh = self.behavior.etat()
        beh["now"] = time.time()
        with s.lock:
            cur, pts = s.gest
            return {"tracks": [[t[0]] + [round(v, 4) for v in t[1:]] for t in s.tracks],
                    "target": s.target_id, "drive": s.drive, "auto": s.auto_lock,
                    "aim": [round(est[0], 4), round(est[1], 4)] if est else None,
                    "kp": {i: np.round(k, 3).reshape(-1).tolist() for i, k in s.kpts.items()},
                    "g": {i: [n, round(p, 2)] for i, (n, p) in cur.items()},
                    "pt": {i: [round(v[0], 3), round(v[1], 3)] for i, v in pts.items()},
                    "beh": beh, "cmd": list(self.control.last_cmd), "m": self.metrics()}

    def perception(self):
        """Message de perception (contrat vision → comportement, voir PROJET.md).
        Directions en degrés depuis l'axe de la caméra (az > 0 à droite, el > 0 en haut) ;
        distances estimées d'après la taille du torse (ou de la boîte à défaut). À calibrer avec --hfov."""
        fr = self.slot.get_newer(-1, 0)
        aspect = fr.w / fr.h if fr and fr.h else 16 / 9
        tan_h = math.tan(math.radians(self.hfov) / 2)
        tan_v = tan_h / aspect
        s = self.state
        with s.lock:
            tracks, kpts, t_cap, target = list(s.tracks), dict(s.kpts), s.t_cap, s.target_id
            cur, pts = s.gest
        personnes = []
        for tid, x1, y1, x2, y2, conf in tracks:
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            dist, src = None, None
            k = kpts.get(tid)
            if k is not None and min(k[5, 2], k[6, 2], k[11, 2], k[12, 2]) >= KP_MIN:
                sh, hip = (k[5, :2] + k[6, :2]) / 2, (k[11, :2] + k[12, :2]) / 2
                cx, cy = (sh[0] + hip[0]) / 2, (sh[1] + hip[1]) / 2
                torso = math.hypot((hip[0] - sh[0]) * aspect, hip[1] - sh[1])
                dist, src = TORSO_M / (torso * 2 * tan_v), "torse"
            elif y2 - y1 > 0.05 and y1 > 0.01 and y2 < 0.99:      # boîte entière dans l'image
                dist, src = PERSON_M / ((y2 - y1) * 2 * tan_v), "boite"
            geste, pointe = cur.get(tid), pts.get(tid)
            personnes.append({
                "id": tid, "conf": round(conf, 2), "boite": [round(v, 3) for v in (x1, y1, x2, y2)],
                "az_deg": round(math.degrees(math.atan((cx - 0.5) * 2 * tan_h)), 1),
                "el_deg": round(math.degrees(math.atan((0.5 - cy) * 2 * tan_v)), 1),
                "dist_m": round(dist, 2) if dist else None, "dist_source": src,
                "proprio": tid == target,
                "geste": geste[0] if geste else None, "geste_prog": round(geste[1], 2) if geste else 0,
                "pointe": {"vx": round(pointe[0], 3), "vy": round(pointe[1], 3)} if pointe else None,
                "squelette": np.round(k, 3).tolist() if k is not None else None,
            })
        m = self.metrics()
        return {"t": round(t_cap, 3), "latence_ms": m["age_ms"], "fps": m["det_fps"],
                "hfov_deg": self.hfov, "comportement": self.behavior.etat(),
                "cible": next((p for p in personnes if p["proprio"]), None),
                "personnes": personnes,
                "obstacles": [], "sol": None}      # capteur de profondeur à venir

    def run(self):
        t_log = time.monotonic()
        try:
            while not self.stop.wait(0.5):
                self.behavior._changed()           # transitions sans geste (fin d'écoute, cible perdue…)
                if time.monotonic() - t_log >= 5:
                    t_log = time.monotonic()
                    m = self.metrics()
                    print(f"[PERF] {m['size']} caméra {m['cam_fps']} fps | YOLO {m['det_fps']} fps "
                          f"(déc {m['dec_ms']} ms, inf {m['inf_ms']} ms) "
                          f"| âge {m['age_ms']} ms | sautées {m['dropped']} | vidéo {m['stream_fps']} fps, clients {m['clients']}")
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
    try:
        import hailo_platform  # noqa: F401  (Raspberry Pi 5 + AI HAT+)
        from yolo_hailo import default_hef
        hef = default_hef(pose=True) or default_hef()
        if hef:
            return hef
    except ImportError:
        pass
    try:
        import ultralytics  # noqa: F401
        return "yolov8n.pt"
    except ImportError:
        pass
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
    p.add_argument("--model", default=default_model(), help=".hef (Hailo, *_pose_* = gestes), .pt (yolov8n-pose.pt = gestes), .onnx, "
                        "'demo', 'demo-pose' ou 'none'")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--classes", default="0", help="classes COCO, ex. '0' (personne) ou 'all'")
    p.add_argument("--no-reduce", action="store_true", help="décoder en pleine résolution pour YOLO")
    p.add_argument("--serial", default=None, help="port Arduino (auto par défaut), 'none' pour désactiver")
    p.add_argument("--cmd-rate", type=float, default=15,
                   help="fréquence d'envoi des consignes (Hz). Le tilt de turret_rover.ino avance d'un pas "
                        "par message : 15 Hz = réglage d'origine, plus haut = tilt plus nerveux")
    p.add_argument("--no-predict", action="store_true", help="désactive l'extrapolation de la cible")
    p.add_argument("--cam-latency", type=float, default=0, help="latence caméra estimée (ms) à compenser")
    p.add_argument("--auto", action="store_true", help="verrouille automatiquement la cible la plus centrale")
    p.add_argument("--hfov", type=float, default=90,
                   help="champ de vision horizontal de la caméra (degrés) pour les directions et distances")
    p.add_argument("--no-gestes", action="store_true", help="désactive la reconnaissance des gestes")
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
