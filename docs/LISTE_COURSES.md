# Liste d'achats LEO-S (robot complet, 2 jambes)

Quantités tirées de la CAO (`docs/cad`), câblage dans `docs/schema_electrique.html`. Sans rechange, sauf quand c'est
presque gratuit. ✅ = déjà possédé · 🛒 = dans un panier · 📦 = commandé · ➕ = à commander.

**Règle d'achat** : depuis le 1ᵉʳ juillet 2026, chaque colis venant de Chine paie **3 € de droits par catégorie
douanière**. On n'achète en Chine que ce qui y est nettement moins cher (servos, tubes carbone, stack de vol) ;
tout le petit matériel vient d'Amazon.

## Vagues 1 et 2 : monter les jambes, puis tenir debout et s'équilibrer

### 📦 Servos et adaptateur

| Qté | Article | Où |
|---|---|---|
| 7 | **STS3215 C018** (12 V, 30 kg·cm, 1:345), boutique Feetech | Alibaba |
| 1 | 8ᵉ servo STS3215 C018 | ailleurs |
| 1 | Waveshare Bus Servo Adapter (A) | ailleurs |

Reçus, ID 1 à 8 donnés et testés au banc (`servos/`).

### 🛒 AliExpress (tubes seuls, 24,4 € import compris)

| Qté | Article | Rôle |
|---|---|---|
| 2 × 500 mm | Tube carbone **Ø12 × 10** | cuisses 2 × 130 mm (tube 1) ; vague 4 : traverse des propulseurs 360 mm (tube 2) |
| 2 × 500 mm (+ 1 lot conseillé) | Tube carbone **Ø10 × 8** | tibias 4 × 135 mm ; vague 4 : 2 bras de propulseurs × 224 mm. Juste 1000 mm pour 988 de besoin : un 2ᵉ lot (6,39 €) donne de la marge et des rechanges |
| 2 × 500 mm | Tube carbone **Ø5 × 3** | bielles : 2 × B1 (~130 mm) + 2 × B2 (~135 mm), 2 rechanges |

### ➕ Amazon : mécanique et capteurs (vague 1)

| Qté | Article | Rôle |
|---|---|---|
| 1 lot de 4 | Ressorts de traction inox 304 **GUNGY fil 1,4 × Ø12 × 60 mm** (47,7 N max, 32,4 mm d'allongement max) | genoux. Le Dyneema est réglé pour que le ressort commence à tirer vers **25–40° de flexion** : l'accroupi profond (genou à 110°) reste possible, l'énergie stockée (~2,6 J pour 4 ressorts) est rendue au saut |
| 10 | Roulements **625ZZ** (5 × 16 × 5) | genoux et chevilles (8 utilisés) |
| 3 lots de 2 | **FSR402B** QUARKZMAN 20 g – 6 kg (~24,9 €) | 3 capteurs de force par pied (talon + 2 pointes) |
| 2 | **ADS1015** (ou ADS1115, plus lent) | 1 par pied, 4 entrées dont 3 utilisées (adresses 0x48 / 0x49 par la broche ADDR), alimenté en 3,3 V par le Pico |
| 1 lot | Assortiment de résistances (1 k, 2,2 k, 4,7 k, 10 kΩ) | pont diviseur de chaque FSR (sans elles, l'ADS ne lit rien). **1 kΩ conseillé** (voir plus bas), à confirmer au banc |
| 1 | **Raspberry Pi Pico 2** (sans W) | équilibre, capteurs, arrêt d'urgence |

### ➕ Amazon : alimentation embarquée (vague 2)

| Qté | Article | Rôle |
|---|---|---|
| 1 | **Régulateur 5 V 5 A** : Pololu D36V50F5 ou Hobbywing UBEC 5A | alimente le Pi 5 depuis la 3S (le LM2596 ✅ ne tient que ~2–3 A : il servira au cou et au LiDAR) |
| 1 + lot | Porte-fusible lame **ATO** en ligne 14 AWG + fusibles **20 A** | protection juste après la batterie |
| 1 | Boucle XT60 à débrancher, ou interrupteur anti-étincelle XT60 40 A | coupure générale des servos |
| 3 paires | Prises **XT60** | batterie, interrupteur, distribution |
| 1 m + 1 m | Câble silicone **14 AWG** rouge + noir | 3S → départs des jambes |
| 1 lot | Bornes **Wago 221** | distribution du 12 V vers les 2 jambes et le régulateur |
| 2 × 1 m | Câble souple 4 fils fin (26 AWG) | I²C des pieds : ADS1015 → Pico, le long de chaque jambe |
| 1 + 1 | Résistances **100 kΩ + 33 kΩ** (ou prises dans un lot) | tension de la 3S sur GP26 du Pico ; le courant vient de la télémétrie des servos, pas besoin d'INA226 |

**Capteurs de pied** : FSR402B en haut du pont (côté 3,3 V), résistance fixe vers la masse, point milieu sur l'entrée de
l'ADS1015 (gain ±4,096 V). Avec 10 kΩ la tension sature dès ~1 kg par capteur ; avec **1 kΩ** elle s'étale sur 0,1–3 kg,
la plage utile d'un robot de 2,4 kg. L'ADS1015 (3300 mesures/s) relit les 3 capteurs d'un pied à ~700 Hz.

**Axes du genou et de la cheville** : vis CHC M5 (genou M5 × 40 + écrou normal + frein-filet, cheville M5 × 55 + écrou),
partie lisse côté tête de préférence.

**Bielles** : tube carbone Ø5 × 3 + un embout imprimé collé à l'époxy à chaque bout, pivot sur vis M3 directement dans
l'œil imprimé. Entraxes **B1 = 161,9 mm**, **B2 = 166,9 mm** (axe à axe). Charge max ~135 N, flambage du tube
≈ 700–1200 N : large marge. Option plus tard : roulements 623ZZ (3 × 10 × 4) ou 683ZZ (3 × 7 × 3) dans les embouts.

## Vague 3 : il tient debout → il voit et il a une tête

| Qté | Article | Rôle | Ordre de prix |
|---|---|---|---|
| 1 | **LiDAR LDROBOT LD19** (câble fourni) | carte locale 360°, sur le dessus de la tête, UART du Pi | 70–100 € |
| 2 | **ToF VL53L8CX** (carte SATEL ST ou équivalente), ou **VL53L1X** pour démarrer | sol et obstacles bas, 0,30–2 m, sur les supports du bassin (pièce 17), I²C du Pico + LPn sur GP10/11 | 25–35 € pièce (VL53L1X : 8–15 €) |
| 1 | **Raspberry Pi Camera Module 3 Wide** | tête sociale, YOLO sur le Hailo | 35–45 € |
| 1 | Nappe caméra **Pi 5** (22 → 15 broches), 200–300 mm | la caméra du kit a la nappe 15 broches | 3–6 € |
| 1 | Écran couleur **1,9″ ST7789 IPS 170 × 320** SPI | seule lumière du robot, derrière la visière en PETG blanc translucide ✅ ; fente et couleur selon l'état (ambre repos, blanc écoute, rouge STOP) | 6–12 € |
| 1 | **Waveshare e-Paper 2,13″** | plaque façon matricule militaire sur le plastron | 15–20 € |
| 2 | **MG90S** (pignons métal) | cou (lacet + tangage), 5 V par le LM2596 ✅ | 3–5 € pièce |

Tout se trouve sur Amazon ; si un vendeur AliExpress a **tout le lot** dans un seul colis, ça peut valoir le coup
malgré les 3 € par catégorie.

## Vague 4 : il marche → propulsion

| Qté | Article | Remarque |
|---|---|---|
| 1 | Stack **F405 (ou F722) + ESC 4-en-1 BLHeli_S 45–60 A**, 30,5 × 30,5 | entrée **3–6S** (la 4S passe), capteur de courant, DShot. Le F722 n'apporte rien d'utile ici, le F405 suffit. Le Pico peut aussi piloter l'ESC directement en DShot (GP6–9) |
| 2 jeux | Hélices 5″ | |
| 1 | Interrupteur de coupure 4S (boucle XT60) | |

## Déjà possédé

✅ MPU6050 (centrale inertielle ; BNO085 plus tard si besoin) · ✅ LM2596 (5 V du cou et du LiDAR) · ✅ inserts M3 · ✅ visserie · ✅ Dyneema Ø2,4 (câbles des ressorts)
· ✅ câbles servo et connecteurs (bricolés) · ✅ PETG (dont blanc translucide pour la visière) + TPU · ✅ colles (cyanoacrylate souple + primaire, époxy, frein-filet)
· ✅ panne à inserts, pince à sertir, clé de 8 · ✅ Raspberry Pi 5 + AI HAT+ · ✅ LiPo 3S 2200 ×2 (servos) · ✅ LiPo 4S 1400 (propulseurs)
· ✅ moteurs 2206 (vérifier qu'il y en a 4) · ✅ radio FlySky + FS-iA6B (arrêt d'urgence, en iBUS vers le Pico)
· ✅ chargeur LiPo · ✅ imprimante Bambu P1S · ✅ PicoBoard
