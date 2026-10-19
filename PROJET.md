# PROJET — Rover IA YOLO et bipède propulsé LEO-S

*Synthèse au 19/10/2026. Les chiffres marqués « estimation » ne sont pas mesurés ; ils sont à confirmer sur banc.*

---

## 1. Objectif

Deux machines qui partagent le même « cerveau » de vision :

1. **Rover IA (existant, remis en service)** : un châssis 4WD avec une tourelle pan/tilt. Il détecte et suit une personne avec YOLO et envoie un retour vidéo en direct dans un navigateur.
2. **Bipède LEO-S (en conception)** : un LEONARDO simplifié d'environ 70 cm qui **marche seul et stable sans propulseurs**. Quatre propulseurs aux épaules se déclenchent pour **rattraper une perte d'équilibre** et pour **sauter** par-dessus un muret de 30 cm. Il est piloté par la vision (gestes, missions).

Fil conducteur : la vision et l'interaction (YOLO, estimation de pose, gestes) développées sur le rover sont réutilisées telles quelles sur le bipède.

---

## 2. Architecture IA / vision

### Pipeline (`tracker_v2.py`)

```
Caméra MJPEG ──► relais du MJPEG brut vers le navigateur (sans ré-encodage → qualité intacte)
            └──► « dernière image » (taille 1) ──► décodage à demi-résolution ──► YOLO ──► tracker
                                                                                      └──► boucle de contrôle à fréquence fixe ──► Arduino
Navigateur : vidéo + boîtes dessinées dans un <canvas>, clic pour choisir la cible, métriques de latence
```

- **Modèle :** YOLOv8n (`.pt` via Ultralytics, ou `.onnx`). Prochaine étape : `yolov8n-pose` pour les gestes, qui **remplace** le modèle de détection au lieu de s'y ajouter (≈ +5 % de calcul).
- **Règle de conception :** la vision n'est **jamais** dans la boucle d'équilibre. Elle décide (cible, direction, saut) à environ 30 Hz ; la stabilité est gérée par un microcontrôleur à 200 Hz et plus.
- **Mesuré sur le PC (IdeaPad, inférence sur CPU) :** caméra 30,4 FPS, YOLO 12,7 FPS, inférence 55,6 ms. Le GPU n'est pas encore utilisé : il faut installer la version CUDA de PyTorch (modèle de carte graphique encore à confirmer).

### Calculateur embarqué retenu

- **Raspberry Pi 5 4 Go + AI HAT+ 26 TOPS (Hailo-8)**, acheté d'occasion pour **161 € + 6,19 € de port**.
- Justification (étude complète dans `docs/ETUDE_CALCULATEUR_EMBARQUE.md`) :
  - avec une caméra à 30 FPS, la caméra limite le débit avant l'accélérateur ;
  - un Hailo-8 mesuré sur Pi 5 donne environ 144 FPS pour YOLOv8n, hors pré- et post-traitement ;
  - un Jetson Orin Nano sortait du budget (≥ 300 € d'occasion).
- **À vérifier à réception :** carte Pi 5, `free -h` ≈ 4 Go, `hailortcli fw-control identify` → `HAILO8`.

---

## 3. Rover (existant)

| Élément | Détail |
|---|---|
| Châssis | 4WD, 4 moteurs TT, Adafruit Motor Shield v2.3 |
| Contrôleur | Arduino Uno |
| Tourelle | servo **PAN** rotation continue (MG996R modifié), **D9** ; servo **TILT** 180°, **D10** |
| Radio | FlySky FS-iA6B (CH1 → D2, CH2 → D3, CH3 → D6, CH4 → D7, CH5 mode → D8) |
| Caméra | DJI Osmo Action 4 en webcam USB (MJPEG) |
| Alimentation | LiPo 2S → VIN Arduino + servos ; 4 × AA → moteurs (Vs du shield) ; masse commune |
| Protocole série | `err_x err_y bbox_h\n` à 115200 bauds, erreurs exprimées dans un repère 640 × 480 |

**Programmes Arduino :**
- `turret_click.ino` : tourelle seule ;
- `turret_rover.ino` : tourelle + moteurs + radio ;
- `pan_test.ino` : test du servo pan seul.

**Côté PC :**
- `yolo_test.py` / `lancer_yolo_test.bat` : test de YOLO avec la caméra ;
- `tracker_v2.py` / `lancer_tourelle.bat` : suivi de cible avec la tourelle, interface sur http://localhost:8082.

**État :** la chaîne complète tourne de nouveau (caméra → YOLO → navigateur → tourelle).

**Décisions et points d'attention :**
- Les consignes sont envoyées à **15 Hz** : le tilt avance d'un pas par message, donc 30 Hz doublerait sa vitesse.
- Le script attend 2 s à l'ouverture du port série, car l'Arduino redémarre.
- Une LiPo 2S chargée (8,4 V) dépasse la tension max d'un MG996R (7,2 V) : un BEC 6 V est recommandé.
- Une panne passée venait de la LiPo, pas du code.

---

## 4. Bipède LEO-S

Schéma détaillé, chaîne cinématique et séquence de saut : `docs/leo_s.html`, aussi publié sous forme de page.

### Principes retenus

- **Inspiration :** LEONARDO (Caltech, 2021) : 3 articulations motorisées par jambe, 4 hélices inclinées aux épaules, environ 0,7 m.
- **Différence clé :** LEO-S **marche sans propulseurs** grâce à une **cheville motorisée**. Les propulseurs ne servent qu'au rattrapage d'équilibre (au-delà d'environ 8° d'inclinaison, ou quand le centre de pression sort du pied) et aux sauts.
- **Propulseurs au ralenti** (5 à 10 % des gaz) pendant la marche, parce que les moteurs mettent 100 à 200 ms à démarrer.
- **Ressort de genou à engagement retardé :** il reste libre entre 0 et 40° pour ne pas gêner la marche, et ne se charge qu'entre 40 et 110° pour l'accroupi et le saut.

### Articulations (par jambe)

| Liaison | Statut | Débattement | Servo V1 |
|---|---|---|---|
| Hanche roulis | obligatoire | −20° / +30° | STS3215 12 V |
| Hanche tangage | obligatoire | −30° / +90° | STS3215 12 V (STS3250 si besoin) |
| Genou (+ ressort) | obligatoire | 0° / 130° | STS3215 12 V (STS3250 si besoin) |
| Cheville tangage | obligatoire | ±45° | STS3215 12 V |
| Hanche lacet | facultatif | ±30° | place réservée dans le bassin |
| Cheville roulis | facultatif | ±20° | V2 |

→ **8 servos** au total, plus 2 micro-servos pour la tête.

### Géométrie

Hauteur ≈ 710 mm · hanche à 370 mm · cuisse 170 mm · tibia 170 mm · cheville à 50 mm du sol · pied 85 mm · écart entre les hanches 120 mm · propulseurs à 340 mm d'entraxe gauche/droite et 200 mm avant/arrière, inclinés de 15° vers l'extérieur.

### Électronique et calcul

| Rôle | Choix |
|---|---|
| Vision, décisions, Wi-Fi | Pi 5 4 Go + Hailo-8 (possédé) |
| Temps réel : marche, équilibre, séquence de saut | Raspberry Pi **Pico 2 (RP2350)** |
| Bus servos | half-duplex 1 Mbit/s (adaptateur Waveshare ou 74HC126) |
| Centrale inertielle | BNO085 |
| Capteurs de pied | 4 capteurs de force (FSR) par pied + 2 × ADS1115 |
| Propulseurs | contrôleur de vol FPV F405 (Betaflight, mode angle) + ESC 4-en-1 45 A ; le Pico envoie ses consignes en **CRSF** et lit l'attitude en **MSP** |
| Arrêt d'urgence | FS-iA6B (possédée) en iBUS vers le Pico, prioritaire sur tout |
| Distance | VL53L1X vers l'avant (V2 : un second vers le bas) |
| Mesure batteries | 2 × INA226 |

**Boucles :**

| Boucle | Fréquence | Rôle |
|---|---|---|
| Contrôleur de vol | plusieurs kHz | assiette du buste |
| Pico | 200 Hz | marche, équilibre, séquence de saut |
| Pi 5 | 30 Hz | vision et décisions |

Si le Pi plante, le Pico garde le robot debout.

### Énergie

- **LiPo 4S 1400 mAh 140C** (possédée) → ESC → propulseurs uniquement.
- **LiPo 3S 2200 mAh** (possédée) → servos 12 V en direct (plage servo 4–14 V) + régulateur 5,1 V / 5 A pour le Pi et le Pico.
- Deux batteries séparées pour qu'un saut ne fasse jamais redémarrer l'électronique. Masses communes, interrupteur d'armement sur la 4S.

### Propulseurs

- **Choix V1 :** 4 moteurs FPV **2207 + hélices 5″ dans des carénages imprimés de 140 mm**. Un fabricant annonce ≈ 1,4 kg par moteur en 4S pour 37 A ; il en faut ≈ 690 g, donc environ le double de marge.
- **Option V2 :** EDF de 64 mm (600 à 800 g en 4S selon les fiches, pour 26 à 43 A) si le look « jet » compte. Moins bon rendement, plus lourd.

---

## 5. Chiffres de dimensionnement (estimations)

| Grandeur | Valeur |
|---|---|
| Masse totale visée | ≈ 2,1 kg (bilan détaillé ≈ 1 945 g + marge) |
| Poussée pour sauter (poussée/poids = 1,3) | 2,75 kg au total → ≈ 690 g par propulseur |
| Couple de basculement à 5° (hanche) | ≈ 0,6 N·m |
| Couple de rattrapage (±400 g de poussée à 17 cm) | ≈ 1,3 N·m |
| Couple genou, appui sur les 2 jambes, flexion 30 / 60 / 90 / 120° | 4 / 7,6 / 10,8 / 13,3 kg·cm |
| Couple genou, appui sur 1 jambe, flexion 30 / 60° | 8 / 15 kg·cm |
| STS3215 12 V | 30 kg·cm en blocage, 10 kg·cm nominal, 0,222 s / 60° |
| Énergie de saut (décollage à 1 m/s) | ≈ 1,05 J → ≈ 0,6 J par genou |
| Ressort de genou | k ≈ 0,8 N·m/rad entre 40 et 110°, ≈ 10 kg·cm d'aide à 110° |
| Ressort de traction sur came de 15 mm | ≈ 3,5 N/mm, course ≥ 20 mm, force max ≥ 70 N |
| Consommation d'un saut (1 à 2 s) | ≈ 70 mAh sur la 4S |
| Profil de poussée pendant un saut | accroupi 0,4 → impulsion 1,3 → vol ≈ 1,05 → descente 0,85 → 0 (en fraction du poids) |

---

## 6. Composants

### Déjà possédés

- Raspberry Pi 5 4 Go + AI HAT+ 26 TOPS (Hailo-8)
- PC Lenovo IdeaPad Gaming (8 Go, carte graphique à confirmer)
- DJI Osmo Action 4
- Arduino Uno + Adafruit Motor Shield v2.3, servos MG996R, châssis 4WD
- Radio FlySky + récepteur FS-iA6B
- LiPo 2S 5200, 3S 2200, 4S 1300, 4S 1400 140C
- Imprimante Bambu Lab P1S
- Carte HyPrSpace PicoBoard V4.1 + PicoShield-ADC (RP2040 probable) → banc de poussée
- Galaxy A50 (utilisable comme écran de l'interface web)
- Matériel FPV (moteurs ou contrôleur de vol possiblement réutilisables)

### À acheter (prévisionnel, ordres de grandeur)

| Étape | Contenu | Estimation |
|---|---|---|
| 1. Jambe de test | 6 STS3215 12 V (lot AliExpress), adaptateur bus, PETG, roulements/visserie/ressorts, IMU, 4 FSR | ≈ 255 – 275 € |
| 2. V1 sans propulseurs | +2 STS3215, 4 FSR, tubes carbone, Pico 2 + INA226 + ToF, régulateur et câblage, tête (caméra + 2 micro-servos) | ≈ 185 – 205 € |
| 3. Propulsion | 4 moteurs 2207, hélices 5″, ESC 4-en-1 45 A, contrôleur de vol F405, capteur de force + HX711 | ≈ 150 – 210 € (≈ 20 – 80 € avec les pièces FPV) |
| **Total avec 15 % de marge** | | **≈ 530 – 790 €** |
| Option | 4 × STS3250 (50 kg·cm) sur hanches tangage et genoux | + ≈ 190 € |

**Prix servos :**
- STS3215 12 V (C018) : ≈ 28 € en Europe (OpenELAB), ≈ 13–17 $ à l'unité sur AliExpress.
- Sur AliExpress, vérifier la référence **C018 / 30 kg·cm** : certaines annonces sont trompeuses (16,5 kg·cm).

---

## 7. Prochaines étapes

**Rover / vision :**
1. Installer PyTorch avec CUDA sur le PC (12,7 → 30 FPS attendus).
2. Ajouter l'estimation de pose et la reconnaissance de gestes : pointer, lever la main, stop.
3. À réception du Pi 5 + Hailo : vérifications, puis portage du pipeline (modèle `.hef`).

**Bipède LEO-S :**
1. **CAO + simulation** (gratuit) : jambe dans SolidWorks → URDF → MuJoCo, pour valider longueurs et couples.
2. **Jambe de test** : 4 STS3215 sur un rail vertical avec une masse au-dessus. Tester 2, 3,5 et 5 N/mm de ressort avec une came interchangeable, mesurer le couple réel et l'accroupi/détente.
3. **Banc de poussée** (carte HyPrSpace + capteur de force) : poussée, courant et chauffe des propulseurs.
4. Deuxième jambe + bassin → premiers pas sous longe.
5. Torse volant attaché : contrôleur de vol en mode angle, pont CRSF depuis le Pico, kill radio.
6. Marche avec rattrapage par les propulseurs → sauts (sur place, 10 cm, puis muret de 30 cm).
7. Vision et missions sur le Pi 5 + Hailo.

**Ressources pour apprendre :**
- James Bruton (YouTube) ;
- Open Duck Mini (GitHub et YouTube) ;
- Disney BDX ;
- mots-clés « ZMP walking » et « linear inverted pendulum » ;
- vidéos Caltech LEONARDO et Salto-1P (Berkeley).

---

## 8. Fichiers du dépôt liés

| Fichier | Contenu |
|---|---|
| `docs/ETUDE_CALCULATEUR_EMBARQUE.md` | étude comparative du calculateur embarqué |
| `docs/leo_s.html` | avant-projet LEO-S (schémas, cinématique, saut, dimensionnement) |
| `tracker_v2.py`, `yolo_test.py`, `lancer_*.bat` | pipeline vision et lanceurs Windows |
| `turret_click/`, `turret_rover/`, `pan_test/`, `turret_test/` | programmes Arduino |
