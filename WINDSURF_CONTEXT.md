# Contexte projet – Tracker Rover YOLO (à coller dans Windsurf)

Colle ce texte au début d'une conversation Windsurf pour que l'IA comprenne immédiatement le projet.

---

## Prompt à copier-coller dans Windsurf

```
Tu m'aides sur un projet de robot roulant autonome avec tourelle de tracking YOLO.

## Architecture

- **tracker_rover.py** : script Python principal. Capture webcam → YOLO détection (yolo26n.onnx, ONNX Runtime) → BotsSort tracking → envoie via USB série à l'Arduino les valeurs : error_x, error_y, bbox_h
- **turret_rover/turret_rover.ino** : sketch Arduino Uno + Adafruit Motor Shield v2.3. Reçoit les commandes série et pilote 2 servos (PAN pin9 rotation continue, TILT pin10 180°) + 4 moteurs TT sur M1/M2/M3/M4.
- **yolo26n.onnx** : modèle YOLO nano ONNX, entrée fixe 640×640, classe 0 = personne.

## Protocole série Python → Arduino (115200 baud)

"<error_x> <error_y> <bbox_h>\n"   ex: "45 -30 310\n"
"R\n"  →  reset (servos repos + stop moteurs)

- error_x > 0 = cible à droite du centre
- bbox_h = 0 → pas de cible → stop moteurs
- bbox_h < 280 → avancer | 280–420 → hold | > 420 → reculer

## Paramètres clés dans tracker_rover.py

- CAM_INDEX = None         # None = auto-détection Windows | "http://127.0.0.1:8080/video" = IP Webcam Android
- CAM_W / CAM_H = 640/480
- MODEL_PATH = absolu via os.path (relatif au script)
- CONF_THRESHOLD = 0.4
- DRIVE_ENABLED = False    # True = moteurs actifs
- STREAM_PORT = 8081       # stream MJPEG annoté (Android sans écran)
- imgsz = 640              # fixe (modèle ONNX 640×640 hardcodé)

## Classe _HTTPCapture

Sur Android, la caméra IP Webcam (port 8080) est lue via requests.get("/shot.jpg") frame par frame au lieu de cv2.VideoCapture (problème FFmpeg MJPEG sur ARM). Cette classe est un drop-in replacement de cv2.VideoCapture pour les URL http://.

## Matériel

- Arduino Uno + Adafruit Motor Shield v2.3
- Servo PAN pin 9 (rotation continue), TILT pin 10 (180°)
- 4× moteurs TT sur M1(AV-G) M2(AV-D) M3(AR-D) M4(AR-G)
- Alimentation : Piles AA 5.5V → Vs shield | LiPo 2S 7.4V → VIN Arduino + servos
- Caméra PC : webcam USB auto-détectée
- Caméra Android : DJI Osmo Action 4 (UVC) ou IP Webcam app

## Dépendances Python (requirements.txt)

ultralytics>=8.3, opencv-python, pyserial>=3.5, requests, lapx

## Contrôles

- Clic gauche sur une personne → verrouille la cible
- r = reset cible | d = toggle drive | q = quitter
- Sur Android : stream YOLO visible sur http://<ip_tel>:8081 depuis un navigateur

## État actuel

Le script tourne sur PC Windows (webcam auto, Arduino auto). 
Sur Android (proot-distro Ubuntu), il utilise IP Webcam comme source caméra via HTTP.
lapx et onnx doivent être installés avec --break-system-packages sur Ubuntu proot.
```
