# 🤖 AI-Controlled Robot — YOLO Tracking with DJI Camera & Samsung Galaxy A50

Autonomous person-tracking rover powered by **YOLOv8 + ONNX Runtime**, a **DJI Osmo Action 4** camera, and an **Arduino-driven 4WD chassis with pan/tilt turret**. The phone (Samsung Galaxy A50) runs the AI pipeline headlessly via Termux, and streams an annotated MJPEG feed to a PC browser for remote monitoring and target selection.

---

## 🎥 Demo

```
Samsung Galaxy A50 (Termux)
    ├── DJI Osmo Action 4 (USB Camera app, MJPEG)
    ├── YOLO v8 nano (ONNX Runtime, 640×640)
    ├── Person tracking + target lock
    ├── Arduino serial commands (pan/tilt/drive)
    └── MJPEG stream → http://<phone_ip>:8082

PC Browser
    ├── Live annotated video feed
    ├── Click on a person → lock target
    └── Buttons: Drive ON/OFF, Auto mode, Reset, Quit
```

---

## 📋 Project Phases

This project evolved through **5 phases**, each building on the previous:

### Phase 1 — Webcam + YOLO + Auto-tracking Turret
> `webcam_yolo26.py` + `turret_control/turret_control.ino`

- PC webcam → YOLOv8 detection → auto-follow the closest person
- Arduino controls 2 servos (PAN + TILT) via USB serial
- Simple proportional controller, no target selection

### Phase 2 — Click-to-Target
> `tracker_click.py` + `turret_click/turret_click.ino`

- Added **ByteTrack** multi-object tracking with stable IDs
- **Click on a person** to lock their ID — only that person is tracked
- Smoothed position (EMA) to reduce YOLO jitter
- Dead zones and watchdog on Arduino side

### Phase 3 — 4WD Rover Base
> `tracker_rover.py` + `turret_rover/turret_rover.ino`

- Added **Adafruit Motor Shield v2.3** driving 4× TT motors
- Robot **approaches/retreats** based on bounding box height (distance proxy)
- Steering via differential speed (left/right motor bias)
- Toggle drive mode with `d` key

### Phase 4 — Android (Samsung Galaxy A50 + Termux)
> `tracker_rover.py` + `launch.sh` + `arduino_bridge.py` + `cv2_termux/`

- Moved the entire pipeline to a **Samsung Galaxy A50** running **Termux**
- DJI Osmo Action 4 connected via USB OTG → **USB Camera** app (MJPEG HTTP)
- Arduino connected via USB OTG → TCP bridge (`arduino_bridge.py`)
- Custom **OpenCV shim** (`cv2_termux/`) for Termux (PIL-based text rendering)
- YOLO runs on-device via **ONNX Runtime** (12 FPS @ 320×240 input)

### Phase 5 — Remote Control via Browser
> `tracker_rover.py` (MJPEG stream + HTML UI)

- Phone streams annotated MJPEG to `http://<ip>:8082`
- **Click on the PC browser** to select a target — commands sent to phone
- Buttons: Toggle Drive, Auto Lock, Reset, Quit
- **Stream-optional**: JPEG encoding skipped when no browser is connected
- **Auto-lock mode**: automatically tracks the nearest person to frame center
- **Servo dead zone**: eliminates micro-corrections when target is centered

---

## 🔧 Hardware

| Component | Role |
|---|---|
| Samsung Galaxy A50 | AI compute (Termux + ONNX Runtime) |
| DJI Osmo Action 4 | USB camera (UVC via USB Camera app) |
| Arduino Uno | Motor + servo controller |
| Adafruit Motor Shield v2.3 | Drives 4× TT motors |
| Servo PAN (pin 9) | Horizontal rotation (continuous) |
| Servo TILT (pin 10) | Vertical rotation (180°) |
| 4× TT yellow motors | M1/M2/M3/M4 on shield |
| USB OTG hub | Connects DJI + Arduino to phone |
| AA batteries (~5.5V) | Motor power (shield Vs terminal) |
| LiPo 2S (~7.4V) | Arduino VIN + servo power |

### Wiring Diagram

```
Samsung Galaxy A50 (USB-C)
         │
    USB OTG Hub
    ├── DJI Osmo Action 4 (USB-C → USB-A)
    └── Arduino Uno (USB-A → USB-B)

Motor Shield v2.3
    M1 → front-left motor
    M2 → front-right motor
    M3 → rear-right motor
    M4 → rear-left motor

Power
    AA 5.5V ──→ Vs screw terminal (motors)
    LiPo 7.4V ──→ Arduino VIN + servos
```

---

## 🚀 Quick Start

### 1. Arduino

1. Install **Adafruit Motor Shield V2 Library** (Arduino IDE → Library Manager)
2. Flash `turret_rover/turret_rover.ino` to Arduino Uno
3. Verify `READY` in Serial Monitor (115200 baud)

### 2. PC (Windows — webcam mode)

```bash
pip install ultralytics>=8.3 opencv-python pyserial>=3.5 onnxruntime
python tracker_rover.py
```

### 3. Android (Termux — full autonomous mode)

```bash
# Install Termux from F-Droid (not Play Store)
pkg update && pkg install python python-numpy
pip install onnxruntime pyserial

# Copy to phone: tracker_rover.py, yolo_onnx.py, cv2_termux/, launch.sh, etc.
# Download YOLO model: yolo26n.onnx (place in home directory)

# Install "USB Camera" app from Play Store
# Connect DJI + Arduino via OTG hub
bash ~/launch.sh
```

Then open `http://<phone_ip>:8082` on your PC browser.

### YOLO Model

The YOLO model (`yolo26n.onnx`) is not included in the repo due to size. You can export it from ultralytics:

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
model.export(format="onnx", imgsz=640)
```

Or use any YOLOv8 nano ONNX model with 640×640 input and person detection (class 0).

---

## 🎮 Controls

| Action | Effect |
|---|---|
| **Click** on a person (browser or window) | Lock target |
| **`r`** | Reset — clear target |
| **`d`** | Toggle drive (motors ON/OFF) |
| **`a`** | Toggle auto-lock mode |
| **`q`** | Quit |

---

## 📁 Project Structure

```
├── tracker_rover.py          # Main script (Phase 5 — full system)
├── tracker_click.py          # Phase 2 — click-to-target (PC only)
├── webcam_yolo26.py          # Phase 1 — auto-track (PC only)
├── yolo_onnx.py              # YOLO ONNX Runtime inference engine
├── cv2_termux/               # OpenCV shim for Termux (PIL backend)
│   └── __init__.py
├── arduino_bridge.py         # USB-serial → TCP bridge for Termux
├── android_usb_serial.py     # USB device scanner for Termux
├── launch.sh                 # One-command launcher for Android
├── usb_id.py                 # USB device identification utility
├── uvc_camera.py             # UVC camera wrapper (experimental)
├── test_dji.py               # DJI camera test script
├── requirements.txt          # Python dependencies
├── turret_rover/             # Arduino sketch — Phase 4+5 (rover)
│   └── turret_rover.ino
├── turret_click/             # Arduino sketch — Phase 2 (turret only)
│   └── turret_click.ino
├── turret_control/           # Arduino sketch — Phase 1 (basic turret)
│   └── turret_control.ino
├── turret_test/              # Arduino servo test sketch
│   └── turret_test.ino
├── motor_test/               # Arduino motor test sketch
│   └── motor_test.ino
└── rc_test/                  # Arduino RC test sketch
    └── rc_test.ino
```

---

## 🧪 Test rapide YOLO (`yolo_test.py`)

Caméra → YOLO → fenêtre vidéo annotée, sans Arduino ni servos.

```bash
pip install ultralytics opencv-python   # yolov8n.pt se télécharge tout seul, GPU utilisé si dispo
python yolo_test.py                     # caméra 0 ; sinon --source 1, 2…
```
Touches : `q` quitter, `s` capture, `c` personnes ↔ toutes les classes.

**Tourelle** : double-clic sur `lancer_tourelle.bat` (Arduino branché avec `turret_click.ino` pour la tourelle seule, ou `turret_rover.ino` pour tourelle + moteurs + RC, interrupteur RC sur AUTO) → l'interface s'ouvre sur http://localhost:8082, clic sur une personne pour la suivre.

---

## ⚡ Tracker v2 — pipeline découplé (`tracker_v2.py`)

Nouvelle version qui sépare la vidéo de la détection :

- **Vidéo** : le MJPEG de la caméra est relayé **tel quel** au navigateur (via ffmpeg `-c:v copy`) → 1080p30 sans ré-encodage, quelle que soit la vitesse de YOLO.
- **Détection** : un thread prend toujours **la dernière image** (jamais de file d'attente), la décode à demi-résolution et lance YOLO.
- **Contrôle** : consigne envoyée à fréquence fixe (15 Hz par défaut, comme l'ancien code) avec extrapolation de la position de la cible. Protocole série **inchangé** (`err_x err_y bbox_h`, repère 640×480) → `turret_rover.ino` n'a pas besoin d'être reflashé.
- **Interface** (`http://<ip>:8082`) : boîtes dessinées côté navigateur, clic pour verrouiller, Drive/Auto/Reset, et métriques (FPS caméra, FPS YOLO, temps de décodage et d'inférence, âge de l'image au moment de la décision).

```bash
pip install opencv-python onnxruntime pyserial numpy      # + ffmpeg dans le PATH (recommandé)
yolo export model=yolov8n.pt format=onnx                  # une fois, sur PC, pour obtenir le modèle

python tracker_v2.py --source test --model demo           # test sans caméra ni modèle
python tracker_v2.py --list-devices                       # Windows : noms des caméras
python tracker_v2.py --source "dshow:<nom DJI>" --size 1920x1080 --model yolov8n.onnx
python tracker_v2.py --source 0 --size 1920x1080          # Linux / Raspberry Pi : /dev/video0
python tracker_v2.py --source 0 --backend opencv          # sans ffmpeg (le flux est alors ré-encodé)
```

`python tracker_v2.py -h` liste toutes les options (`--cmd-rate`, `--cam-latency`, `--auto`, `--serial none`…).

---

## 🍓 Tourelle sur Raspberry Pi 5 + AI HAT+ (Hailo)

DJI (mode webcam) et Arduino branchés en USB sur le Pi, YOLO tourne sur le Hailo (`yolo_hailo.py`).

```bash
git clone -b claude/sleepy-fermi-a1a0sa https://github.com/WyNo22/AI-rover-Yolo-targeting.git
cd AI-rover-Yolo-targeting
bash pi/lancer_tourelle_pi.sh            # trouve la caméra USB, installe ce qui manque, lance
```

Puis ouvrir `http://<ip-du-pi>:8082` sur le téléphone. Le modèle est choisi automatiquement dans
`/usr/share/hailo-models` (`yolov8s_h8.hef` en priorité) ; pour en forcer un : `--model yolov8m_h8.hef`.
Options utiles : `--size 1920x1080`, `--auto`, `--serial none` (vision seule). `CAM=/dev/videoN` force la caméra.

**Gestes** : si un modèle de pose est installé (`yolov8s_pose_h8.hef`), il est choisi automatiquement.
Squelette, geste en cours et état du robot s'affichent dans la vidéo ; état sur `/etat`, perception complète sur
`/perception`. ✋ main levée 1 s = « écoute », puis 👉 regarde là · 🤏 viens · 🦘 saute · ❌ repos ;
🙌 = STOP ; 👋 = coucou. Test sans caméra : `python3 tracker_v2.py --source test --model demo-pose --serial none`.
Sur PC : `--model yolov8n-pose.pt`. Désactiver : `--no-gestes`. Modèles installés : `python3 yolo_hailo.py`.

**Démarrage automatique** (plus besoin de SSH) : `bash pi/installer_demarrage_auto.sh` une fois.
La tourelle se lance à chaque allumage et attend la DJI si elle n'est pas encore branchée.
Messages : `journalctl -u tourelle -f`. Arrêt : `sudo systemctl stop tourelle`. Options : `pi/tourelle.conf`.

## ⚙️ Serial Protocol (Python → Arduino)

```
"<error_x> <error_y> <bbox_h>\n"
```

| Field | Description |
|---|---|
| `error_x` | Horizontal pixel offset (+ = target right of center) |
| `error_y` | Vertical pixel offset (+ = target below center) |
| `bbox_h` | Target bounding box height (0 = no target → stop motors) |

**Navigation logic** (Arduino side):

| Condition | Action |
|---|---|
| `bbox_h == 0` | Motors stop |
| `bbox_h < 280` | Drive forward (target far) |
| `280 ≤ bbox_h ≤ 420` | Hold position |
| `bbox_h > 420` | Reverse (target too close) |

---

## 📊 Performance (Samsung Galaxy A50)

| Metric | Value |
|---|---|
| YOLO inference | ~80ms per frame (ONNX Runtime, 640×640) |
| Processing FPS | **12 FPS** (YOLO every 3rd frame) |
| Stream resolution | 320×240 |
| Stream quality | JPEG Q40 |
| Latency (phone → browser) | ~200ms |

---

## 📜 License

MIT License — use freely, credit appreciated.
