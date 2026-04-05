from ultralytics import YOLO
import cv2
import subprocess
import serial
import serial.tools.list_ports
import time

# ── Paramètres tourelle ───────────────────────────────────────────────────────
SERIAL_PORT     = None       # None = auto-détection, sinon ex. "COM3"
SERIAL_BAUD     = 115200
TILT_CENTER     = 90         # angle de repos tilt
TILT_MIN        = 10
TILT_MAX        = 170
PAN_SPEED_MAX   = 80         # vitesse pan max (tracking)
DEAD_ZONE_PX    = 40         # pixels d'erreur tolérés avant correction
CMD_RATE_HZ     = 15         # fréquence d'envoi des commandes série
FACE_Y_RATIO        = 0.15   # position cible dans le bbox (0=top, 0.5=centre, 1=bas)
SEARCH_PAN_SPD      = 30     # vitesse balayage mode recherche
SEARCH_DELAY_S      = 2.0    # secondes sans detection avant mode recherche
TILT_DEAD_ZONE_PX   = 30     # dead zone tilt (pixels)
SMOOTH_ALPHA        = 0.35   # EMA sur position cible (0=figee, 1=aucun lissage)
# ─────────────────────────────────────────────────────────────────────────────


def get_windows_camera_names():
    """Retourne la liste des noms de cameras detectees par Windows via PowerShell."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice -Class Camera -Status OK | Select-Object -ExpandProperty FriendlyName"],
            capture_output=True, text=True, timeout=8
        )
        names = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        return names
    except Exception:
        return []


def scan_available_cameras(max_index=8):
    """Scanne les indices OpenCV et retourne ceux disponibles."""
    available = []
    print("Scan des cameras disponibles", end="", flush=True)
    for i in range(max_index):
        print(".", end="", flush=True)
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            available.append(i)
            cap.release()
    print()
    return available


def select_camera_index():
    """Detecte automatiquement la DJI Action 4 ou demande a l'utilisateur de choisir."""
    print("\n=== Detection de la camera ===")
    print("NOTE DJI Action 4 : branchez en USB, puis sur la camera :")
    print("  Menu > Connexion > Mode USB > Webcam (UVC)\n")

    device_names = get_windows_camera_names()
    available_indices = scan_available_cameras()

    if not available_indices:
        print("Aucune camera trouvee. Verifiez la connexion USB et le mode Webcam de la DJI.")
        return None

    print(f"Cameras trouvees (indices OpenCV) : {available_indices}")
    if device_names:
        print("Peripheriques camera Windows :")
        for i, name in enumerate(device_names):
            print(f"  [{i}] {name}")

    # Tentative de detection automatique DJI
    if device_names:
        for i, name in enumerate(device_names):
            if any(kw in name.lower() for kw in ["dji", "action 4", "action4"]):
                cam_idx = available_indices[i] if i < len(available_indices) else available_indices[0]
                print(f"\nDJI Action 4 detectee automatiquement -> index {cam_idx} : {name}")
                return cam_idx

    # Une seule camera disponible
    if len(available_indices) == 1:
        name = device_names[0] if device_names else "Camera inconnue"
        print(f"\nUne seule camera disponible -> index {available_indices[0]} : {name}")
        return available_indices[0]

    # Plusieurs cameras : choix manuel
    print("\nPlusieurs cameras disponibles. Entrez l'index a utiliser :")
    for i, idx in enumerate(available_indices):
        name = device_names[i] if i < len(device_names) else f"Camera index {idx}"
        print(f"  {idx} -> {name}")
    try:
        choice = int(input("Index choisi : "))
        if choice in available_indices:
            return choice
    except (ValueError, EOFError):
        pass
    print(f"Choix invalide, utilisation de l'index {available_indices[0]}.")
    return available_indices[0]


def find_arduino_port():
    """Detecte automatiquement le port serie de l'Arduino UNO."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "uno" in desc or "ftdi" in desc:
            return p.device
    # Fallback : premier port COM disponible
    if ports:
        return ports[0].device
    return None


def connect_arduino(port=None):
    """Ouvre la connexion serie vers l'Arduino. Retourne l'objet Serial ou None."""
    if port is None:
        port = find_arduino_port()
    if port is None:
        print("Arduino non detecte. La tourelle sera desactivee (mode camera seule).")
        return None
    try:
        ser = serial.Serial(port, SERIAL_BAUD, timeout=1)
        time.sleep(2)  # laisse l'Arduino booter apres ouverture du port
        print(f"Arduino connecte sur {port} ({SERIAL_BAUD} baud)")
        return ser
    except serial.SerialException as e:
        print(f"Impossible d'ouvrir {port} : {e}")
        print("La tourelle sera desactivee (mode camera seule).")
        return None


def send_turret_command(ser, pan_speed, tilt_angle):
    """Envoie une commande P<speed>T<angle> a l'Arduino."""
    if ser is None:
        return
    cmd = f"P{int(pan_speed)}T{int(tilt_angle)}\n"
    try:
        ser.write(cmd.encode())
    except serial.SerialException:
        pass


def face_center(box):
    """Retourne le centre estimé du visage a partir d'un bbox personne."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2.0
    cy = y1 + (y2 - y1) * FACE_Y_RATIO
    return cx, cy


def compute_turret_commands(frame_w, frame_h, cx, cy, current_tilt):
    """
    Calcule pan_speed et tilt_angle en fonction de l'erreur de centrage.
    cx, cy : position cible en pixels (centre visage)
    Retourne (pan_speed, new_tilt_angle)
    """
    ex = cx - frame_w / 2.0   # + = cible a droite
    ey = cy - frame_h / 2.0   # + = cible en bas

    # Pan : proportionnel a ex, avec dead zone
    if abs(ex) < DEAD_ZONE_PX:
        pan_speed = 0
    else:
        pan_speed = int((ex / (frame_w / 2.0)) * PAN_SPEED_MAX)
        pan_speed = max(-PAN_SPEED_MAX, min(PAN_SPEED_MAX, pan_speed))

    # Tilt : proportionnel a ey, avec dead zone
    tilt_step = 0
    if abs(ey) >= TILT_DEAD_ZONE_PX:
        # Plus on est loin du centre, plus la correction est grande (max 8 deg/frame)
        tilt_step = int((ey / (frame_h / 2.0)) * 8)
        tilt_step = max(-8, min(8, tilt_step))
    new_tilt = int(max(TILT_MIN, min(TILT_MAX, current_tilt - tilt_step)))

    return pan_speed, new_tilt


def read_arduino(ser):
    """Lit les messages Arduino. Retourne True si PAN_LIMIT recu."""
    if ser is None:
        return False
    hit_limit = False
    try:
        while ser.in_waiting:
            msg = ser.readline().decode(errors='ignore').strip()
            if msg == "PAN_LIMIT":
                hit_limit = True
    except serial.SerialException:
        pass
    return hit_limit


# ── Initialisation ────────────────────────────────────────────────────────────
model = YOLO("yolo26n.pt")

# Connexion Arduino (optionnelle)
arduino = connect_arduino(SERIAL_PORT)

# Selection camera
cam_index = select_camera_index()
if cam_index is None:
    if arduino:
        arduino.close()
    exit(1)

cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not cap.isOpened():
    print(f"Erreur : impossible d'ouvrir la camera (index {cam_index}).")
    if arduino:
        arduino.close()
    exit(1)

frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"\nCamera ouverte (index {cam_index}) -> {frame_w}x{frame_h}")
print("Appuyez sur 'q' pour quitter.")

WIN_NAME = "YOLO26 - Tourelle DJI Action 4 - q pour quitter"
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WIN_NAME, 1280, 720)

current_tilt     = TILT_CENTER
cmd_interval     = 1.0 / CMD_RATE_HZ
last_cmd_time    = 0.0
last_person_time = time.time()
search_dir       = 1          # +1 = droite, -1 = gauche
mode             = "TRACKING"
pan_speed        = 0
smooth_cx        = frame_w / 2.0
smooth_cy        = frame_h / 2.0

# ── Boucle principale ─────────────────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        print("Erreur : impossible de lire le flux camera.")
        break

    # Inference YOLO
    results = model(frame, verbose=False)

    # Filtrage : garder uniquement les detections "person"
    best_box  = None
    best_conf = 0.0
    boxes = results[0].boxes
    if boxes is not None:
        for box in boxes:
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = results[0].names[cls_id]
            if label == "person" and conf > best_conf:
                best_conf = conf
                best_box  = box.xyxy[0].tolist()

    # Lecture Arduino (pour inverser direction si PAN_LIMIT)
    if read_arduino(arduino):
        search_dir *= -1
        if arduino:
            arduino.write(b'R\n')  # reset angle estime

    now = time.time()

    # Etat : TRACKING ou SEARCHING
    if best_box is not None:
        last_person_time = now
        mode = "TRACKING"
    elif now - last_person_time > SEARCH_DELAY_S:
        mode = "SEARCHING"
    else:
        mode = "LOST"   # vient de perdre la cible, on attend

    # Calcul et envoi commande
    if now - last_cmd_time >= cmd_interval:
        if mode == "TRACKING":
            fcx, fcy = face_center(best_box)
            # EMA smoothing pour reduire le jitter YOLO
            smooth_cx = SMOOTH_ALPHA * fcx + (1 - SMOOTH_ALPHA) * smooth_cx
            smooth_cy = SMOOTH_ALPHA * fcy + (1 - SMOOTH_ALPHA) * smooth_cy
            pan_speed, current_tilt = compute_turret_commands(
                frame_w, frame_h, smooth_cx, smooth_cy, current_tilt
            )
        elif mode == "SEARCHING":
            pan_speed = SEARCH_PAN_SPD * search_dir
        else:  # LOST
            pan_speed = 0
        send_turret_command(arduino, pan_speed, current_tilt)
        last_cmd_time = now

    # Affichage
    annotated_frame = results[0].plot()
    if best_box is not None:
        x1, y1, x2, y2 = [int(v) for v in best_box]
        fcx, fcy = face_center(best_box)
        cv2.circle(annotated_frame, (int(fcx), int(fcy)), 8, (0, 255, 0), -1)
        cv2.line(annotated_frame, (frame_w // 2, frame_h // 2),
                 (int(fcx), int(fcy)), (0, 255, 0), 2)
        cv2.putText(annotated_frame, f"VISAGE conf={best_conf:.2f}",
                    (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Croix de centrage
    cv2.drawMarker(annotated_frame, (frame_w // 2, frame_h // 2),
                   (0, 0, 255), cv2.MARKER_CROSS, 30, 2)

    # HUD
    mode_color = (0, 255, 0) if mode == "TRACKING" else (0, 165, 255) if mode == "SEARCHING" else (0, 200, 255)
    cv2.putText(annotated_frame, f"MODE: {mode}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, mode_color, 2)
    cv2.putText(annotated_frame, f"Pan={pan_speed:+4d}  Tilt={current_tilt:3d}", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    arduino_status = f"Arduino: {arduino.port}" if arduino else "Arduino: DESACTIVE"
    cv2.putText(annotated_frame, arduino_status, (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    cv2.imshow(WIN_NAME, annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ── Nettoyage ─────────────────────────────────────────────────────────────────
send_turret_command(arduino, 0, TILT_CENTER)  # retour position repos
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
