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
| 8 (ou 10) | Rotules **M3 à œil, filetage femelle** (type SI3T/K, PHS3) | 2 par bielle ; à défaut igus igubal KBRM-03 en Allemagne |
| 2 | **MG90S** | servos du cou (vague 3, mais quasi gratuit ici) |

## 3. Reste à acheter en Europe — vague 1 (monter les jambes)

| Qté | Article | Remarque |
|---|---|---|
| 0,5 m | Tube carbone **Ø12 × 10** | cuisses, 2 × 130 mm |
| 1 m | Tube carbone **Ø10 × 8** | tibias, 4 × 135 mm |
| 1 m | Tube carbone **Ø5 × 3** | bielles : 2 × 130 mm (B1) + 2 × 135 mm (B2) |
| 4 | **Ressorts de traction** fil Ø1,4, Ø ext. 10–11, L0 ≈ 58 mm, ≈ 1,75 N/mm, F max ≥ 65 N | genoux ; fabricant de ressorts sur catalogue |
| 1 m | Câble acier gainé Ø1 | ressort → came du genou |
| 8 | Résistances 10 kΩ | pont diviseur des RFP602 (valeur à ajuster au banc) |
| 1 | Fusible lame 20 A + porte-fusible, prises XT60, câble silicone 14 AWG, alarme LiPo | banc 12 V |

**Bielles** (B1 genou, B2 cheville, 2 par jambe) : tube carbone Ø5 × 3 + à chaque bout un goujon M3 × 20
(tige filetée) collé à l'époxy sur 10 mm + contre-écrou M3 + rotule M3 femelle vissée dessus. Entraxes à régler :
**B1 = 161,9 mm**, **B2 = 166,9 mm** (centre de rotule à centre de rotule).

## Visserie à sortir de ta boîte (déjà possédée)

| Qté | Vis | Où |
|---|---|---|
| 32 | M2 × 12 | boîtiers des servos |
| 36 | M3 × 12 | palonniers S1/S2 + berceaux S1 |
| 8 | M3 × 14 | bras de S4 |
| 8 | M3 × 16 | rotules |
| 8 | M3 × 22 (à défaut × 20) | bras de S3 |
| 4 | M3 × 8 | tendeurs des ressorts |
| 4 | M3 × 25 | colliers |
| 4 | M3 × 40 | goupilles des tibias |
| 2 | M3 × 45 | axes des ressorts |
| 4 | M3 × 12 | supports des ToF bas |
| 10 + 24 | Écrous M3 Nylstop + rondelles M3 | |
| 2 + 2 | M5 × 40 et M5 × 55, tige lisse | genoux, chevilles |
| 4 + 8 | Écrous M5 Nylstop + rondelles M5 | |

## 4. Plus tard

| Vague | Quand | À acheter |
|---|---|---|
| **2** | une jambe bouge | Pico 2 · BNO085 · INA226 · UBEC 5,1 V 5 A |
| **3** | il tient debout | LiDAR LD19 · caméra Pi Module 3 Wide + nappe Pi 5 · écran e-ink 2,13″ · BEC 5 V 3 A |
| **4** | il marche | ESC 4-en-1 45 A (ou stack F405 + ESC) · 2 jeux d'hélices 5″ · interrupteur de coupure 4S |

## Déjà possédé

✅ inserts M3 · ✅ visserie complète (voir le tableau) · ✅ tige filetée M3 · ✅ câbles servo et connecteurs (bricolés)
· ✅ PETG + TPU · ✅ colles (cyanoacrylate souple + primaire, époxy, frein-filet) · ✅ panne à inserts, pince à sertir, clé de 8
· ✅ Raspberry Pi 5 + AI HAT+ · ✅ LiPo 3S 2200 (servos) · ✅ LiPo 4S 1400 (propulseurs) · ✅ moteurs 2206 (vérifier qu'il y en a 4)
· ✅ radio FlySky + FS-iA6B · ✅ chargeur LiPo (à vérifier) · ✅ imprimante Bambu P1S · ✅ PicoBoard (banc de poussée)
