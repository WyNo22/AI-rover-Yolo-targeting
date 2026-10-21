# Liste de courses LEO-S

Quantités tirées de la CAO Rév. I (`docs/cad`). ✅ = déjà possédé (voir PROJET.md §6), à vérifier avant de racheter.

## 1. Première jambe (de quoi la monter et la faire bouger au banc)

### Servos et bus
| Qté | Article | Remarque |
|---|---|---|
| 4 + 1 | Servo **Feetech STS3215-C049** (12 V, 1/191) | +1 de rechange ; vérifier la référence exacte sur l'annonce |
| 2 | **FE-URT-2** (adaptateur USB ↔ bus TTL Feetech) | 1 sur le robot, 1 pour l'établi (IDs, tests) |
| 2 | Câbles servo 3 broches Molex 5264, **300 mm** | bassin → S1 et S3 → S4 ; les câbles livrés avec les servos font S1 → S2 et S2 → S3 |
| 1 lot | Boîtiers Molex 5264 3 broches + contacts à sertir | pour faire les rallonges et l'injection d'alimentation |

### Mécanique
| Qté | Article | Remarque |
|---|---|---|
| 1 | Tube carbone **Ø12 × 10**, ≥ 130 mm | cuisse, coupé à **130 mm** (acheter 500 mm = les 2 jambes) |
| 2 | Tube carbone **Ø10 × 8**, ≥ 135 mm | tibia, coupés à **135 mm** (acheter 1 m = les 2 jambes + chute) |
| 2 | Tube carbone **Ø5 × 3** (ou Ø4 × 2) | bielles, coupées à **130 mm** (B1) et **135 mm** (B2) ; acheter 1 m |
| 4 | Rotules à œil **M3** (filetage femelle) | 2 par bielle |
| 4 | Goujons M3 × 20 (ou tige filetée M3 à couper) | collés à l'époxy dans les tubes de bielle Ø5 × 3 |
| 4 | Roulements **625ZZ** (5 × 16 × 5) | genou et cheville ; lot de 10 pour les 2 jambes |
| 2 | **Ressorts de traction** : fil Ø1,4, Ø ext. 10–11, L0 ≈ 58 mm, ≈ 1,75 N/mm, course ≥ 35 mm, F max ≥ 65 N | genou ; prendre 4 + 2 de rechange pour les 2 jambes |
| 1 m | Câble acier gainé Ø1 (ou Dyneema 1 mm) | ressort → came du genou |

### Visserie (par jambe)
| Qté | Article | Où |
|---|---|---|
| 16 | **M2 × 12** | vis de boîtier des servos (4 par servo) |
| 18 | **M3 × 12** | palonniers S1 et S2 (16) + berceau de S1 (2) |
| 4 | **M3 × 14** | bras de S4 |
| 4 | **M3 × 16** | rotules |
| 4 | **M3 × 22** (à défaut × 20) | bras de S3 |
| 2 | M3 × 8 | tendeurs des ressorts |
| 2 | M3 × 25 | colliers cuisse et languette |
| 2 | M3 × 40 | goupilles des tubes de tibia |
| 1 | M3 × 45 | axe d'ancrage des ressorts |
| 5 | Écrous M3 Nylstop | colliers, goupilles, axe |
| 12 | Rondelles M3 | rotules, divers |
| 1 | **M5 × 40**, tige lisse (partiellement filetée) | axe du genou (tête côté extérieur) |
| 1 | **M5 × 55** (ou × 60), tige lisse | axe de la cheville |
| 2 + 4 | Écrous M5 Nylstop + rondelles M5 | |
| 8 | **Inserts M3 à chaud** (trou Ø4,0, L 4–5) | lot de 100 pour tout le robot |

Plus simple : un **coffret M3 inox 6–30 mm** + un **coffret M2** + les M3 × 40 / × 45 et les M5 à part.

### Impression
| Qté | Article | Remarque |
|---|---|---|
| 1 kg | **PETG** | pièces 02 à 11 des 2 jambes + plaque de bassin ≈ 600 g supports compris |
| 0,5 kg | **TPU 95A** | semelles (≈ 25 g pièce) |

### Pour la faire tourner au banc
| Qté | Article | Remarque |
|---|---|---|
| ✅ | LiPo **3S** 2200 | alimentation 12 V des servos (**jamais la 4S** : 16,8 V) |
| 1 | Fusible lame 20 A + porte-fusible, câble silicone 14 AWG rouge/noir, prises XT60 | |
| 1 | Alarme de tension LiPo | |

## 2. Deuxième jambe

Racheter la même chose que §1 **sauf** : le 2ᵉ FE-URT-2, les tubes (déjà en longueur pour 2 jambes),
les lots (roulements, inserts, coffrets de vis, boîtiers Molex), le filament.

| Qté | Article |
|---|---|
| 4 | Servos STS3215-C049 (+ éventuellement 1 2ᵉ rechange) |
| 2 | Câbles servo 300 mm |
| 4 | Rotules M3 + 4 goujons M3 × 20 |
| 2 | Ressorts de traction (si pas pris en lot) |
| 1 jeu | Visserie spécifique : M2 × 12 ×16, M3 × 22 ×4, M3 × 40 ×2, M3 × 45 ×1, M5 × 40 + M5 × 55 + 2 Nylstop M5 |

Total robot : **8 servos (+1 ou 2)**, 8 roulements 625ZZ, 8 rotules, 4 ressorts (+2), 32 M2 × 12, 36 M3 × 12.

## 3. Électronique et puissance du robot

| Qté | Article | Remarque |
|---|---|---|
| ✅ | Raspberry Pi 5 4 Go + AI HAT+ 26 TOPS | cerveau, vision |
| 1 | **Raspberry Pi Pico 2** (RP2350) | boucle d'équilibre, capteurs (la PicoBoard ✅ peut dépanner) |
| 1 | **UBEC / abaisseur 5,1 V 5 A** | alimente le Pi depuis la 3S |
| 1 | Interrupteur de puissance (ou anti-étincelle XT60) | coupure générale servos |
| 1 | Carte ou bornier de distribution (12 V vers les 2 jambes) | le courant des servos ne passe pas par l'URT-2 |
| 1 lot | Câble silicone 14 AWG et 22 AWG, gaine thermo, gaine tressée, colliers | |
| ✅ | Radio FlySky + récepteur FS-iA6B | arrêt d'urgence, MANUEL / AUTO |
| ✅ | Chargeur équilibreur LiPo | à vérifier |

## 4. Capteurs

| Qté | Article | Remarque |
|---|---|---|
| 1 | **Centrale inertielle BNO085** (ou ICM-42688-P) | équilibre ; sur le Pico en I²C |
| 8 | **FSR 402** | 4 par pied, dans les poches de la semelle TPU |
| 2 | **ADS1115** (CAN 4 voies) + 8 résistances 10 kΩ | 1 par pied, lecture des FSR |
| 1 | **Caméra ToF VL53L5CX** (8 × 8 zones) | obstacles, distance avant un saut |
| 1 | **INA226** | tension et courant batterie |
| ✅ | DJI Osmo Action 4 | caméra de développement (trop lourde pour le robot final) |

## 5. Tête et interaction

| Qté | Article | Remarque |
|---|---|---|
| 1 | **Caméra Raspberry Pi Module 3** + nappe Pi 5 (22 → 15 broches) | caméra embarquée, remplace la DJI |
| 2 | Micro-servos 9 g (MG90S) | cou : panoramique et inclinaison |
| 1 | **Écran e-ink 2,13″** (Waveshare, SPI) | affiche l'état du robot |

## 6. Propulsion (vol / saut)

| Qté | Article | Remarque |
|---|---|---|
| ✅ | 4 moteurs **2206 2400 KV** | vérifier que tu en as 4 ; sinon compléter avec les 2205 |
| 1 | Contrôleur de vol **F405** + **ESC 4-en-1 45 A** (stack 30 × 30) | |
| 8 + 8 | Hélices **5″** (4 CW + 4 CCW) + rechanges | |
| ✅ | LiPo **4S** 1400 | propulseurs uniquement |
| 1 | Capteur de force 5 kg + HX711 | banc de poussée (avec la PicoBoard ✅) |

## 7. Consommables et outillage

| Qté | Article |
|---|---|
| 1 | Colle **cyanoacrylate souple + primaire** (ou néoprène) — semelle TPU sur PETG |
| 1 | Époxy 24 h — goujons dans les tubes de bielle |
| 1 | Frein-filet moyen (Loctite 243) — vis de palonnier |
| 1 | Panne pour inserts à chaud (fer à souder) |
| 1 | Pince à sertir Molex / JST (contacts 5264) |
| 1 | Clés Allen 1,5 / 2 / 2,5 / 4 mm, clé plate 8 mm (Nylstop M5) |
| 1 | Scie à métaux lame fine + ruban adhésif (coupe du carbone, sous masque) |
