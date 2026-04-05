# Tracker Click – YOLO + ByteTrack + Tourelle Arduino

Système complet de tracking avec sélection de cible par clic souris.

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `tracker_click.py` | Script Python principal |
| `turret_click/turret_click.ino` | Sketch Arduino (nouveau protocole) |
| `webcam_yolo26.py` | Ancien script (suivi auto, sans sélection) – conservé |
| `turret_control/turret_control.ino` | Ancien sketch Arduino – conservé |

---

## Pipeline

```
Caméra → YOLOv8 → ByteTrack → Clic souris
                                    ↓
                         ID cible sélectionné
                                    ↓
                         error_x / error_y (pixels)
                                    ↓
                    Serial USB → Arduino → Servos Pan + Tilt
```

---

## Câblage Arduino

### Servos

```
Servo PAN  (signal) ──→ Pin 9   (Arduino UNO/Nano)
Servo TILT (signal) ──→ Pin 10  (Arduino UNO/Nano)
Servo VCC           ──→ 5V externe ou LiPo 2S (NE PAS alimenter depuis Arduino 5V)
Servo GND           ──→ GND Arduino (masse commune OBLIGATOIRE)
```

> **Attention** : alimenter les servos depuis une source externe (LiPo 2S / alimentation 5-6V).
> Brancher uniquement la masse commune avec l'Arduino.

### Type de servo PAN

Ouvrir `turret_click.ino` et modifier la ligne :

```cpp
#define PAN_STANDARD_180  0   // 0 = rotation continue (MG996R modifié)
                              // 1 = servo 180° standard (SG90, MG995, etc.)
```

---

## Installation Python

```bash
pip install ultralytics>=8.3 opencv-python pyserial>=3.5
```

ByteTrack est inclus dans Ultralytics — aucun package supplémentaire nécessaire.

---

## Lancement

### 1. Flasher l'Arduino

Ouvrir `turret_click/turret_click.ino` dans l'Arduino IDE et flasher sur la carte.

Vérifier dans le Serial Monitor (115200 baud) que `READY` s'affiche au démarrage.

### 2. Lancer Python

```bash
python tracker_click.py
```

La caméra et l'Arduino sont détectés automatiquement.

Pour forcer un port ou un index précis, modifier en haut du fichier :

```python
SERIAL_PORT = "COM3"   # forcer port Arduino
CAM_INDEX   = 0        # forcer index caméra
```

---

## Utilisation

| Action | Effet |
|---|---|
| **Clic gauche** sur une personne | Verrouille cette cible (ID ByteTrack) |
| **`r`** | Reset – arrêt du suivi |
| **`q`** | Quitter |

### HUD affiché

- `IDLE` – aucune cible sélectionnée
- `LOCKED ID:X` – cible verrouillée sur l'ID X
- `LOST (N/30)` – cible temporairement perdue, attente
- `err_x` / `err_y` – erreurs pixel envoyées à l'Arduino
- FPS en temps réel
- Statut Arduino (port ou OFF)

---

## Protocole série

### Python → Arduino

```
"<error_x> <error_y>\n"
```

Exemple : `"45 -30\n"`

- `error_x` : décalage horizontal en pixels (+ = cible à droite du centre)
- `error_y` : décalage vertical en pixels   (+ = cible en bas du centre)
- Envoyé à **15 Hz** (configurable via `CMD_RATE_HZ`)

### Commande reset

```
"R\n"
```

Remet les servos en position de repos (PAN stop, TILT 90°).

---

## Paramètres à ajuster

### Python (`tracker_click.py`)

| Paramètre | Défaut | Description |
|---|---|---|
| `CONF_THRESHOLD` | `0.4` | Confiance YOLO minimale |
| `SMOOTH_ALPHA` | `0.35` | Lissage EMA (0=figé, 1=brut) |
| `LOST_TOLERANCE` | `30` | Frames avant reset cible perdue |
| `CMD_RATE_HZ` | `15` | Fréquence envoi série |

### Arduino (`turret_click.ino`)

| Paramètre | Défaut | Description |
|---|---|---|
| `PAN_KP` | `0.15` | Gain pan continu (pixels → vitesse%) |
| `PAN180_KP` | `0.05` | Gain pan 180° (pixels → degrés) |
| `TILT_KP` | `0.06` | Gain tilt (pixels → degrés) |
| `PAN_DEAD_PX` | `30` | Dead zone horizontale (pixels) |
| `TILT_DEAD_PX` | `25` | Dead zone verticale (pixels) |
| `WATCHDOG_MS` | `600` | Timeout watchdog (ms) |

---

## Calibration des gains

Si la tourelle **oscille** → diminuer les gains (`KP`).  
Si la tourelle **réagit trop lentement** → augmenter les gains.  
Si la tourelle **tremble au repos** → augmenter les dead zones (`DEAD_PX`).

---

## Fonctionnement interne

1. **YOLO** détecte toutes les personnes dans la frame
2. **ByteTrack** assigne un ID stable à chaque personne frame après frame
3. Au **clic souris**, l'ID de la boîte cliquée est mémorisé
4. Seule la boîte de cet ID est suivie ; les autres sont affichées en gris
5. La position cible est **lissée (EMA)** pour réduire le jitter YOLO
6. Les erreurs pixel `(error_x, error_y)` sont calculées par rapport au **centre de l'image**
7. Ces erreurs sont envoyées à l'Arduino via USB (Serial 115200 baud)
8. L'Arduino applique un **correcteur proportionnel** pour orienter les servos
9. Si la cible disparaît plus de **30 frames**, le tracking se reset
