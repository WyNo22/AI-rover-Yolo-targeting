# Liste d'achats LEO-S (robot complet, 2 jambes)

Quantités tirées de la CAO (`docs/cad`), câblage dans `docs/schema_electrique.html`. Sans rechange, sauf quand c'est
presque gratuit. ✅ = déjà possédé · 🛒 = dans un panier · 📦 = commandé ailleurs · ➕ = à ajouter.

## Vagues 1 et 2 : monter les jambes, puis tenir debout et s'équilibrer

### 🛒 Alibaba (servos seuls)

| Qté | Article | Prix |
|---|---|---|
| 7 | **STS3215 C018** (12 V, 30 kg·cm, 1:345), boutique Feetech | 13,23 € + port + TVA d'import |

### 📦 Ailleurs

| Qté | Article |
|---|---|
| 1 | 8ᵉ servo STS3215 C018 |
| 1 | Adaptateur bus servo (USB ↔ bus TTL) |

### 🛒 Panier AliExpress

| Qté | Article | Rôle |
|---|---|---|
| 2 × 500 mm | Tube carbone **Ø12 × 10** | cuisses, 2 × 130 mm |
| 2 × 500 mm | Tube carbone **Ø10 × 8** | tibias, 4 × 135 mm |
| 2 × 500 mm | Tube carbone **Ø5 × 3** | bielles : 2 × 130 mm (B1) + 2 × 135 mm (B2) |
| 4 | Ressorts de traction 65Mn **fil 1,4 × Ø10 × 60 mm** | genoux ; crochets ouverts à refermer à la pince |
| 10 | Roulements **625ZZ** | genoux et chevilles (8 utilisés) |
| 6 | **RFP602 5 kg** | 3 capteurs de force par pied (talon + 2 pointes) |
| 2 | **ADS1015** | 1 par pied, lit ses 3 capteurs (adresses 0x48 / 0x49) |
| 100 | Résistances 10 kΩ | pont diviseur de chaque capteur |
| 1 | **Pico 2** (sans W) | équilibre, capteurs (vague 2) |
| 1 | Stack F405 + ESC 4-en-1 | vague 4 : prendre la variante **6S 55A** (pas 8S 70A), ou le retirer pour l'instant |

### ➕ À ajouter pour la vague 2 (alimentation embarquée et mesure)

| Qté | Article | Rôle |
|---|---|---|
| 1 | **INA226, version 36 V / 20 A** (shunt **R002**, 2 mΩ) | tension et courant de la 3S ; la version courante à shunt R100 ne mesure que 0,8 A |
| 1 | **Régulateur 5 V 5 A** réglable (UBEC ou module abaisseur type XL4015), réglé à **5,1 V** | alimente le Pi 5 depuis la 3S |
| 1 | Porte-fusible lame en ligne 14 AWG + fusibles **20 A** | protection juste après la batterie |
| 1 | Interrupteur ≥ 20 A 12 V (ou boucle XT60 à débrancher) | coupure générale des servos |
| 3 paires | Prises **XT60** | batterie, interrupteur, distribution |
| 1 m + 1 m | Câble silicone **14 AWG** rouge + noir | 3S → départs des jambes |
| 1 lot | Bornes **Wago 221** | distribution du 12 V vers les 2 jambes et le régulateur |
| 2 × 1 m | Câble souple 4 fils fin (26 AWG) | I²C des pieds : ADS1015 → Pico, le long de chaque jambe |

**Bielles** : tube carbone Ø5 × 3 + un embout imprimé collé à l'époxy à chaque bout, pivot sur vis M3.
Entraxes **B1 = 161,9 mm**, **B2 = 166,9 mm** (axe à axe). Option : 8 roulements 683ZZ (3 × 7 × 3) dans les embouts.

## Plus tard

| Vague | Quand | À acheter |
|---|---|---|
| **3** | il tient debout | LiDAR LD19 · 2 ToF bas (VL53L8CX, ou VL53L1X pour démarrer) · caméra Pi Module 3 Wide + nappe Pi 5 · écran e-ink 2,13″ · 2 MG90S · BEC 5 V 3 A |
| **4** | il marche | stack F405 + ESC (si pas pris) · 2 jeux d'hélices 5″ · interrupteur de coupure 4S |

## Déjà possédé

✅ MPU6050 (centrale inertielle ; BNO085 plus tard si besoin) · ✅ inserts M3 · ✅ visserie · ✅ Dyneema Ø2,4 (câbles des ressorts)
· ✅ câbles servo et connecteurs (bricolés) · ✅ PETG + TPU · ✅ colles (cyanoacrylate souple + primaire, époxy, frein-filet)
· ✅ panne à inserts, pince à sertir, clé de 8 · ✅ Raspberry Pi 5 + AI HAT+ · ✅ LiPo 3S 2200 (servos) · ✅ LiPo 4S 1400 (propulseurs)
· ✅ moteurs 2206 (vérifier qu'il y en a 4) · ✅ radio FlySky + FS-iA6B (arrêt d'urgence, en iBUS vers le Pico)
· ✅ chargeur LiPo (à vérifier) · ✅ imprimante Bambu P1S · ✅ PicoBoard
