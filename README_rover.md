# Tracker Rover – Phase 4 : Robot Roulant Autonome

Tourelle YOLO + base roulante 4WD autonome pilotée par la taille de la bbox cible.

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `tracker_rover.py` | Script Python principal (Phase 4) |
| `turret_rover/turret_rover.ino` | Sketch Arduino (tourelle + 4 moteurs) |
| `tracker_click.py` | Phase 3 – conservé |
| `turret_click/turret_click.ino` | Phase 3 – conservé |
| `webcam_yolo26.py` | Phase 2 – conservé |
| `turret_control/turret_control.ino` | Phase 1 – conservé |

---

## Matériel

- Arduino Uno + **Adafruit Motor Shield v2.3**
- 2× servos : PAN (pin 9, rotation continue) + TILT (pin 10, 180°)
- 4× moteurs TT jaunes (3–6 V) sur M1/M2/M3/M4
- DJI Osmo Action 4
- Oppo A74 + Hub USB Oliveria (OTG)

---

## Câblage moteurs

```
Motor Shield v2
  M1 → moteur avant-gauche
  M2 → moteur avant-droit
  M3 → moteur arrière-droit
  M4 → moteur arrière-gauche
```

> Si un moteur tourne dans le mauvais sens : inverser ses 2 fils sur le port Mx.

---

## Alimentation

```
Piles AA ~5.5 V ──→ bloc vis Vs du Motor Shield   (moteurs TT : 3–6 V ✅)
LiPo 2S ~7.4 V  ──→ barrel jack / VIN Arduino     (7–12 V ✅)
                └──→ Servos PAN + TILT             (comme avant ✅)
```

> ⚠️ Ne pas mettre 5.5 V sur VIN Arduino (régulateur instable < 7 V).

---

## Librairie Arduino à installer

`Adafruit Motor Shield V2 Library` → Arduino IDE → Library Manager → chercher "Adafruit Motor Shield V2"

---

## Pipeline

```
Caméra → YOLOv8 → ByteTrack → Clic souris
                                    ↓
                         ID cible sélectionné
                                    ↓
                    error_x / error_y / bbox_h
                                    ↓
              Serial USB → Arduino → Servos PAN+TILT
                                  └→ 4 moteurs TT (drive)
```

---

## Protocole série

### Python → Arduino

```
"<error_x> <error_y> <bbox_h>\n"
```

| Champ | Description |
|---|---|
| `error_x` | Décalage horizontal pixels (+ = droite) |
| `error_y` | Décalage vertical pixels (+ = bas) |
| `bbox_h` | Hauteur bbox cible pixels (0 = pas de cible → stop moteurs) |

Exemple : `"45 -30 310\n"`

### Commande reset

```
"R\n"  →  servos en position repos + moteurs stop
```

---

## Logique de navigation (Arduino)

| Condition | Action |
|---|---|
| `bbox_h == 0` | Moteurs stop |
| `bbox_h < 280` | Avancer (cible trop loin) |
| `280 ≤ bbox_h ≤ 420` | Stop (bonne distance) |
| `bbox_h > 420` | Reculer (trop proche) |
| `error_x > +40` | Virage droite (roues droites ralentissent) |
| `error_x < -40` | Virage gauche (roues gauches ralentissent) |

---

## Paramètres à calibrer

### Arduino (`turret_rover.ino`)

| Paramètre | Défaut | Description |
|---|---|---|
| `APPROACH_TARGET` | `280` | bbox_h → bonne distance (px) |
| `RETREAT_TARGET` | `420` | bbox_h → trop proche (px) |
| `DRIVE_BASE_SPEED` | `180` | Vitesse moteurs 0–255 |
| `DRIVE_DEAD_X` | `40` | Dead zone avant virage (px) |

### Python (`tracker_rover.py`)

| Paramètre | Défaut | Description |
|---|---|---|
| `APPROACH_TARGET` | `280` | Même valeur que Arduino (affichage HUD) |
| `RETREAT_TARGET` | `420` | Même valeur que Arduino (affichage HUD) |
| `DRIVE_ENABLED` | `True` | False = tourelle seule |
| `CONF_THRESHOLD` | `0.4` | Confiance YOLO minimale |

---

## Installation

### 1. Arduino IDE

1. Library Manager → installer **Adafruit Motor Shield V2 Library**
2. Ouvrir `turret_rover/turret_rover.ino`
3. Flasher sur l'Arduino Uno
4. Vérifier `READY` dans le Serial Monitor (115200 baud)

### 2. Python (PC)

```bash
pip install ultralytics>=8.3 opencv-python pyserial>=3.5
python tracker_rover.py
```

### 3. Téléphone Android (Termux)

```bash
# Installer Termux depuis F-Droid (pas le Play Store)
pkg update && pkg upgrade
pkg install python python-numpy
pip install ultralytics opencv-python pyserial

# Copier sur le téléphone :
#   yolo26n.pt
#   tracker_rover.py

# Brancher hub Oliveria → DJI (port USB-A) + Arduino (port USB-A)
# Accepter les permissions USB dans Android
python tracker_rover.py
```

> Sur Android/Termux, le port Arduino apparaît sous `/dev/ttyUSB0` ou `/dev/ttyACM0`.  
> ultralytics utilise automatiquement le backend NCNN sur ARM → ~5–10 FPS.

---

## Utilisation

| Action | Effet |
|---|---|
| **Clic gauche** sur une personne | Verrouille cette cible |
| **`r`** | Reset – arrêt du suivi + moteurs stop |
| **`d`** | Toggle drive (moteurs ON/OFF) |
| **`q`** | Quitter |

### HUD affiché

- `LOCKED ID:X` / `LOST` / `IDLE`
- `DRIVE: FORWARD / HOLD / REVERSE / OFF`
- `err_x`, `err_y`, `bbox_h` sur la bbox cible
- FPS + statut Arduino

---

## Connexion téléphone (Option D – Hub OTG)

```
Oppo A74 USB-C
      │
   Hub Oliveria (OTG ✅ validé)
      ├── USB-A → DJI Osmo Action 4  (câble USB-C→USB-A livré avec la DJI)
      └── USB-A → Arduino Uno        (câble USB-A→USB-B "câble imprimante")
```

La DJI est reconnue comme webcam UVC standard (index 0 ou 1 selon Android).  
Forcer si besoin : `CAM_INDEX = 0` en haut de `tracker_rover.py`.
