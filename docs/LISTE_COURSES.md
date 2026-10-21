# Liste d'achats LEO-S (robot complet, 2 jambes)

Quantités tirées de la CAO (`docs/cad`), câblage dans `docs/schema_electrique.html`. Sans rechange, sauf quand c'est
presque gratuit. ✅ = déjà possédé · 🛒 = dans le panier Alibaba · 📦 = commandé ailleurs.

## 1. Déjà commandé

### 🛒 Panier Alibaba (livraison groupée prévue 30 oct. – 17 nov.)

| Qté | Article | Vendeur | Prix |
|---|---|---|---|
| 7 | **STS3215 C018** (12 V, 30 kg·cm, 1:345) | Shenzhen Feite Model (Feetech) | 13,23 € |
| 8 | **RFP602 5 kg** (capteurs de force des pieds, 4 par pied) | Shenzhen Yonglisheng | 1,64 € |
| 3 | Module de conversion pour capteur à membrane | Shenzhen Yonglisheng | 1,08 € |
| 2 | **VL53L1X** (ToF 1 zone, 4 m) | Shenzhen Caiyusheng | 2,95 € |
| 20 | Roulements **625ZZ** (8 utilisés) | Dongguan Changhua Bearing | 0,20 € |

Sous-total 135,03 € HT port compris ; prévoir la **TVA d'import (19 %, ≈ 26 €)** à la livraison.

### 📦 Ailleurs

| Qté | Article |
|---|---|
| 1 | 8ᵉ servo STS3215 C018 |
| 1 | Adaptateur bus servo (USB ↔ bus TTL) |

## 2. À ajouter au panier Alibaba (même livraison, peu cher)

| Qté | Article | Pourquoi |
|---|---|---|
| 2 | **ADS1115** (module) | indispensable pour lire les 8 RFP602 : le Pico n'a que 3 entrées analogiques |
| 2 | **MG90S** | servos du cou (vague 3, mais quasi gratuit ici) |

## 3. AliExpress — vague 1 (monter les jambes)

| Qté | Article | Remarque |
|---|---|---|
| 0,5 m | Tube carbone **Ø12 × 10** | cuisses, 2 × 130 mm |
| 1 m | Tube carbone **Ø10 × 8** | tibias, 4 × 135 mm |
| 1 m | Tube carbone **Ø5 × 3** | bielles : 2 × 130 mm (B1) + 2 × 135 mm (B2) |
| 4 | **Ressorts de traction 65Mn, fil 1,4 × Ø10 × 60 mm** (magasin Jindong) | genoux, ≈ 1,8–1,9 N/mm ; crochets ouverts à refermer à la pince |
| 8 | Résistances 10 kΩ (ou 5 modules de conversion de plus) | un RFP602 n'est qu'une résistance qui varie : sans résistance fixe en série, l'ADS1115 ne lit rien |
| 8 | Roulements **683ZZ** (3 × 7 × 3), optionnel | dans les embouts de bielle imprimés : pivot sans jeu ; à prendre chez le vendeur des 625ZZ |

**Bielles** (B1 genou, B2 cheville, 2 par jambe) : tube carbone Ø5 × 3 + un embout imprimé collé à l'époxy à chaque
bout, pivot sur vis M3. Entraxes : **B1 = 161,9 mm**, **B2 = 166,9 mm** (axe à axe).

## 4. Plus tard

| Vague | Quand | À acheter |
|---|---|---|
| **2** | une jambe bouge | Pico 2 · INA226 · UBEC 5,1 V 5 A · fusible 20 A + porte-fusible, prises XT60, câble 14 AWG (alimentation embarquée) |
| **3** | il tient debout | LiDAR LD19 · caméra Pi Module 3 Wide + nappe Pi 5 · écran e-ink 2,13″ · BEC 5 V 3 A |
| **4** | il marche | ESC 4-en-1 45 A (ou stack F405 + ESC) · 2 jeux d'hélices 5″ · interrupteur de coupure 4S |

## Déjà possédé

✅ MPU6050 (centrale inertielle pour démarrer ; BNO085 plus tard si besoin) · ✅ inserts M3 · ✅ visserie · ✅ Dyneema Ø2,4 (câbles des ressorts) · ✅ câbles servo et connecteurs (bricolés)
· ✅ PETG + TPU · ✅ colles (cyanoacrylate souple + primaire, époxy, frein-filet) · ✅ panne à inserts, pince à sertir, clé de 8
· ✅ Raspberry Pi 5 + AI HAT+ · ✅ LiPo 3S 2200 (servos) · ✅ LiPo 4S 1400 (propulseurs) · ✅ moteurs 2206 (vérifier qu'il y en a 4)
· ✅ radio FlySky + FS-iA6B · ✅ chargeur LiPo (à vérifier) · ✅ imprimante Bambu P1S · ✅ PicoBoard
