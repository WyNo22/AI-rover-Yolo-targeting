"""
tracker_click.py
Pipeline complet : YOLO + ByteTrack + sélection cible par clic + Serial Arduino

Touches :
  Clic gauche  : sélectionner / changer de cible
  r            : reset cible
  q            : quitter
"""

from ultralytics import YOLO
import cv2
import serial
import serial.tools.list_ports
import subprocess
import time

# ── Paramètres utilisateur ────────────────────────────────────────────────────
SERIAL_PORT     = None      # None = auto-détection  |  sinon ex. "COM3"
SERIAL_BAUD     = 115200
CAM_INDEX       = None      # None = auto-détection  |  sinon ex. 0
CAM_W           = 1280
CAM_H           = 720
MODEL_PATH      = "yolo26n.pt"
CONF_THRESHOLD  = 0.4
CMD_RATE_HZ     = 15        # fréquence max d'envoi série
SMOOTH_ALPHA    = 0.35      # EMA position cible : 0 = figé, 1 = aucun lissage
LOST_TOLERANCE  = 30        # frames sans détection avant reset cible
CLICK_MARGIN    = 20        # pixels de tolérance autour des bboxes pour le clic
# ─────────────────────────────────────────────────────────────────────────────


# ── Scan caméra ───────────────────────────────────────────────────────────────
def get_windows_camera_names():
    """Retourne les noms des caméras Windows via PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice -Class Camera -Status OK | Select-Object -ExpandProperty FriendlyName"],
            capture_output=True, text=True, timeout=8
        )
        return [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
    except Exception:
        return []


def scan_cameras(max_idx=6):
    available = []
    print("Scan des caméras", end="", flush=True)
    for i in range(max_idx):
        print(".", end="", flush=True)
        for backend in (cv2.CAP_MSMF, cv2.CAP_DSHOW):
            cap = cv2.VideoCapture(i, backend)
            if cap.isOpened():
                cap.release()
                available.append(i)
                break
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

    # Plusieurs caméras : chercher la DJI automatiquement
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

    # Fallback : premier index disponible
    # Pour forcer un index précis : CAM_INDEX = <index> en haut du fichier
    print(f"→ index {cams[0]} sélectionné par défaut  (forcer avec CAM_INDEX=<n>)")
    return cams[0]


# ── Arduino ───────────────────────────────────────────────────────────────────
def find_arduino_port():
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if any(kw in desc for kw in ["arduino", "ch340", "uno", "ftdi"]):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None


def connect_arduino(port=None):
    if port is None:
        port = find_arduino_port()
    if port is None:
        print("Arduino non détecté – mode caméra seule.")
        return None
    try:
        # dsrdtr=False : empêche le reset Arduino via DTR (évite le twitch servo au démarrage)
        ser = serial.Serial(port, SERIAL_BAUD, timeout=1, dsrdtr=False, rtscts=False)
        time.sleep(0.5)
        print(f"Arduino connecté : {port} ({SERIAL_BAUD} baud)")
        return ser
    except serial.SerialException as e:
        print(f"Erreur port {port} : {e}  – mode caméra seule.")
        return None


def send_errors(ser, ex, ey):
    """Envoie 'error_x error_y\n' à l'Arduino."""
    if ser is None:
        return
    try:
        ser.write(f"{int(ex)} {int(ey)}\n".encode())
    except serial.SerialException:
        pass


# ── Callback souris ───────────────────────────────────────────────────────────
_click = [-1, -1]


def _mouse_cb(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"[MOUSE] clic gauche ({x},{y})", flush=True)
        _click[0], _click[1] = x, y


# ── Initialisation ────────────────────────────────────────────────────────────
print("\n=== Tracker Click – YOLO + ByteTrack ===")
model   = YOLO(MODEL_PATH)
arduino = connect_arduino(SERIAL_PORT)

cam_index = get_camera_index(CAM_INDEX)
if cam_index is None:
    if arduino:
        arduino.close()
    raise SystemExit(1)

# MSMF = Media Foundation, meilleur support UVC/DJI sur Windows
cap = cv2.VideoCapture(cam_index, cv2.CAP_MSMF)
if not cap.isOpened():
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if not cap.isOpened():
    print(f"Impossible d'ouvrir la caméra (index {cam_index}).")
    if arduino:
        arduino.close()
    raise SystemExit(1)

# Chauffe caméra : les premières frames sont souvent noires au démarrage
print("Initialisation caméra", end="", flush=True)
for _ in range(10):
    cap.read()
    print(".", end="", flush=True)
print()

print(f"Caméra prête (index {cam_index}) : {frame_w}x{frame_h}")
print("Clic gauche = cibler | r = reset | q = quitter\n")

WIN = "Tracker | clic=cibler | r=reset | q=quitter"
cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WIN, min(frame_w, 1280), min(frame_h, 720))
cv2.setMouseCallback(WIN, _mouse_cb)

# ── Variables d'état ──────────────────────────────────────────────────────────
target_id   = None   # ID de la cible sélectionnée
lost_frames = 0      # compteur frames sans cible
smooth_cx   = None   # position lissée X (EMA)
smooth_cy   = None   # position lissée Y (EMA)
error_x     = 0
error_y     = 0

cmd_interval  = 1.0 / CMD_RATE_HZ
last_cmd_time = 0.0
fps_avg       = 0.0
t_prev        = time.time()

# ── Boucle principale ─────────────────────────────────────────────────────────
while True:
    t_frame = time.time()

    ret, frame = cap.read()
    if not ret:
        print("Erreur lecture caméra.")
        break

    # ── Tracking ByteTrack, filtre classe 0 = person ─────────────────────────
    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=CONF_THRESHOLD,
        verbose=False,
        imgsz=640,
        show=False
    )

    # ── Extraction boxes + IDs ────────────────────────────────────────────────
    # Format : (tid, x1, y1, x2, y2, conf)
    detections = []
    r_boxes = results[0].boxes
    if r_boxes is not None and r_boxes.id is not None:
        for b in r_boxes:
            tid  = int(b.id[0])
            x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
            conf = float(b.conf[0])
            detections.append((tid, x1, y1, x2, y2, conf))

    # ── Gestion clic souris ───────────────────────────────────────────────────
    if _click[0] >= 0:
        cx_click, cy_click = _click[0], _click[1]
        _click[0] = _click[1] = -1
        # Convertir coordonnées fenêtre → frame (compense le redimensionnement)
        try:
            _, _, disp_w, disp_h = cv2.getWindowImageRect(WIN)
            if disp_w > 0 and disp_h > 0 and (disp_w != frame_w or disp_h != frame_h):
                cx_click = int(cx_click * frame_w / disp_w)
                cy_click = int(cy_click * frame_h / disp_h)
        except Exception:
            pass
        matched = False
        print(f"[CLICK] coords=({cx_click},{cy_click})  {len(detections)} personne(s) détectée(s)")
        for tid, x1, y1, x2, y2, conf in detections:
            if (x1 - CLICK_MARGIN) <= cx_click <= (x2 + CLICK_MARGIN) and \
               (y1 - CLICK_MARGIN) <= cy_click <= (y2 + CLICK_MARGIN):
                target_id   = tid
                lost_frames = 0
                smooth_cx   = None
                smooth_cy   = None
                matched     = True
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
        lost_frames = 0
        bx = (target_box[0] + target_box[2]) / 2.0
        # Cibler le visage : ~12% depuis le haut de la bbox (pas le centre du corps)
        by = target_box[1] + (target_box[3] - target_box[1]) * 0.12
        if smooth_cx is None:
            smooth_cx, smooth_cy = bx, by
        else:
            smooth_cx = SMOOTH_ALPHA * bx + (1 - SMOOTH_ALPHA) * smooth_cx
            smooth_cy = SMOOTH_ALPHA * by + (1 - SMOOTH_ALPHA) * smooth_cy
    elif target_id is not None:
        lost_frames += 1
        if lost_frames > LOST_TOLERANCE:
            print(f"[LOST] ID {target_id} perdue ({LOST_TOLERANCE} frames). Reset.")
            target_id   = None
            lost_frames = 0
            smooth_cx   = None
            smooth_cy   = None

    # ── Calcul erreurs pixel ──────────────────────────────────────────────────
    cx_frame = frame_w / 2.0
    cy_frame = frame_h / 2.0

    if target_box is not None and smooth_cx is not None:
        error_x = smooth_cx - cx_frame
        error_y = smooth_cy - cy_frame
    else:
        error_x = 0
        error_y = 0

    # ── Envoi série (rate-limited) ────────────────────────────────────────────
    if now - last_cmd_time >= cmd_interval:
        send_errors(arduino, error_x, error_y)
        last_cmd_time = now

    # ── Dessin ────────────────────────────────────────────────────────────────
    display = frame.copy()

    for tid, x1, y1, x2, y2, conf in detections:
        is_target = (tid == target_id)
        color     = (0, 255, 0)     if is_target else (160, 160, 160)
        thick     = 3               if is_target else 1
        cv2.rectangle(display, (x1, y1), (x2, y2), color, thick)
        cv2.putText(display, f"ID:{tid}",
                    (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Ligne + point cible + erreurs affichées
    if target_box is not None and smooth_cx is not None:
        tcx = int(smooth_cx)
        tcy = int(smooth_cy)
        cv2.circle(display, (tcx, tcy), 8, (0, 255, 0), -1)
        cv2.line(display,
                 (int(cx_frame), int(cy_frame)),
                 (tcx, tcy),
                 (0, 255, 0), 2)
        cv2.putText(display,
                    f"err_x={int(error_x):+d}  err_y={int(error_y):+d}",
                    (target_box[0], target_box[3] + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # Croix de centrage (rouge)
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
        mode_txt   = "IDLE  –  Cliquez sur une personne"
        mode_color = (180, 180, 180)

    cv2.putText(display, mode_txt,
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.85, mode_color, 2)
    cv2.putText(display, f"FPS: {fps_avg:.1f}",
                (frame_w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)
    ard_txt = f"Arduino: {arduino.port}" if arduino else "Arduino: OFF"
    cv2.putText(display, ard_txt,
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

    cv2.imshow(WIN, display)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        target_id   = None
        lost_frames = 0
        smooth_cx   = None
        smooth_cy   = None
        print("[RESET] Cible effacée.")

# ── Nettoyage ─────────────────────────────────────────────────────────────────
send_errors(arduino, 0, 0)
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("Arrêt propre.")
