# Liste d'achats LEO-S (robot complet, 2 jambes)

Sans pièces de rechange, sauf quand elles coûtent presque rien. Quantités tirées de la CAO Rév. I (`docs/cad`),
câblage dans `docs/schema_electrique.html`. Prix relevés sur les annonces (à revérifier, ils changent souvent).
✅ = déjà possédé.

## Ordre de commande

| Vague | Pour faire quoi | À commander |
|---|---|---|
| **1. Maintenant** | monter les 2 jambes et les faire bouger au banc | 8 STS3215 C018 + câbles 300 mm · adaptateur de bus (Waveshare chez Eckstein ou FE-URT2) · 625ZZ · rotules M3 · tubes carbone · ressorts · tige filetée M3 · câble acier · inserts · visserie · Molex 5264 · PETG + TPU · fusible, XT60, câble 14 AWG, alarme LiPo · colles, panne à inserts, pince à sertir |
| **2. Quand une jambe bouge** | tenir debout et s'équilibrer | Pico 2 · BNO085 · 2 ADS1115 · 8 FSR 402 · INA226 · UBEC 5,1 V 5 A (Pi embarqué) |
| **3. Quand il tient debout** | tête, perception, interaction | caméra Pi Module 3 + nappe · VL53L5CX · écran e-ink 2,13″ · 2 MG90S · BEC 5 V 3 A |
| **4. Quand il marche** | sauts et vol assistés | ESC 4-en-1 (ou stack) · 2 jeux d'hélices 5″ · interrupteur de coupure 4S |

Astuce : les composants Alibaba de la vague 2 et 3 sont légers et bon marché ; si tu passes de toute façon une
commande Alibaba en vague 1, tu peux les ajouter pour ne payer le port qu'une fois.

## A. Commande Feetech sur Alibaba (boutique officielle « Shenzhen Feite Model »)

Une seule commande, envoi express vers Munich ; prévoir la TVA d'import (19 %).

| Qté | Article | Remarque |
|---|---|---|
| 8 | **STS3215 C018** (12 V, 30 kg·cm, 1:345) | choisir C018 dans les variantes ; pas C066 (« virtuel ») ni les 7,4 V |
| 2 | **FE-URT2-C001** (adaptateur USB ↔ bus) | ≈ 7 $ ; 1 robot + 1 établi. Inutile si tu prends la carte Waveshare chez Eckstein |
| 4 | Câbles servo 3 broches **300 mm** | à demander au vendeur ; les câbles fournis avec les servos font le reste |

## B. Autres achats Alibaba (quantité minimum acceptable)

| Qté | Article | Prix relevé | Remarque |
|---|---|---|---|
| 10 | Roulements **625ZZ** (5 × 16 × 5) | ≈ 0,83 $ (NMB, min. 10) | 8 utilisés |
| 8 | Rotules **M3 à œil, filetage femelle, pas à droite** | ≈ 0,21–0,26 $ (min. 100) | le lot de 100 coûte ≈ 25 $ ; sinon AliExpress par 10 |
| 1 kit | **Inserts M3 à chaud** (kit 220 pcs M2–M6) | quelques $ | 16 inserts M3 utilisés ; trou Ø4,0 |
| 1 | **ESC 4-en-1 45–50 A**, 4S, DShot, 30,5 × 30,5 | ≈ 15–25 $ | piloté par le Pico ; un stack F405 + ESC (≈ 24 $, HAKRC) convient aussi, le FC reste en réserve |
| 1 | **VL53L5CX** (ToF 8 × 8) | ≈ 10–11 $ | |
| 2 | **ADS1115** (module) | < 2 $ | 1 par pied |
| 8 | **FSR 402** | ≈ 1 $ | 4 par pied, version queue courte |
| 2 | **MG90S** | ≈ 2 $ | cou |
| 1 lot | Boîtiers **Molex 5264, 3 broches, pas 2,50 mm** + contacts 5263 | quelques $ | attention : pas 2,50, pas 2,54 |

## C. En Allemagne / Europe (plus rapide, ou minimum Alibaba trop gros)

| Qté | Article | Où | Pourquoi pas Alibaba |
|---|---|---|---|
| 1 ou 2 | **Waveshare Bus Servo Adapter (A)** | Eckstein | remplace les FE-URT-2, livré en 2 jours |
| 0,5 m | Tube carbone **Ø12 × 10** | boutique carbone / AliExpress | Alibaba : minimum 50 m |
| 1 m | Tube carbone **Ø10 × 8** | idem | coupes 4 × 135 mm |
| 1 m | Tube carbone **Ø5 × 3** | idem | bielles 2 × 130 + 2 × 135 mm |
| 4 | **Ressorts de traction** fil Ø1,4, Ø ext. 10–11, L0 ≈ 58 mm, ≈ 1,75 N/mm, F max ≥ 65 N | fabricant de ressorts sur catalogue (ex. federnshop.com) | Alibaba : sur mesure, minimum élevé |
| 1 m | Tige filetée M3 (goujons de bielle, 8 × 20 mm) | quincaillerie | |
| 1 m | Câble acier gainé Ø1 | quincaillerie | ressorts → came du genou |
| 1 | **Raspberry Pi Pico 2** | Eckstein / Berrybase | |
| 1 | **BNO085** (module type Adafruit) | Eckstein / Amazon | les annonces Alibaba sont incohérentes (prix par lot) |
| 1 | **INA226** (module) | Eckstein / Amazon | |
| 1 | **Écran e-ink 2,13″ Waveshare** (SPI) | Eckstein | |
| 1 | **Caméra Pi Module 3** + nappe Pi 5 (22 → 15 broches) | Eckstein / Berrybase | |
| 1 | **UBEC 5,1 V 5 A** | magasin de modélisme | alimente le Pi |
| 1 | **BEC 5 V 3 A** | magasin de modélisme | servos du cou |
| 2 jeux | **Hélices 5″** (2 CW + 2 CCW par jeu) | magasin de modélisme | 1 jeu de rechange, ça casse et ça ne coûte rien |
| 1 | Porte-fusible lame + fusible 20 A, interrupteur ou XT60 anti-étincelle, prises XT60, câble silicone 14 et 22 AWG, alarme LiPo | magasin de modélisme | |
| 1 kg + 0,5 kg | **PETG** + **TPU 95A** | Bambu / Amazon | |

### Visserie (robot complet)

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
| 10 + 24 | Écrous M3 Nylstop + rondelles M3 | |
| 2 + 2 | M5 × 40 et M5 × 55, tige lisse | genoux, chevilles |
| 4 + 8 | Écrous M5 Nylstop + rondelles M5 | |

Le plus simple : un coffret M3 inox 6–30 mm + un coffret M2, et les M3 × 40 / × 45 et M5 à part.

### Consommables et outils

Colle cyanoacrylate souple + primaire (semelles), époxy 24 h (bielles), frein-filet moyen, panne pour inserts,
pince à sertir pour contacts Molex 5263, clé plate 8 mm, scie à métaux lame fine.

## Déjà possédé

✅ Raspberry Pi 5 + AI HAT+ · ✅ LiPo 3S 2200 (servos) · ✅ LiPo 4S 1400 (propulseurs) · ✅ 4 moteurs 2206 (à vérifier)
· ✅ radio FlySky + FS-iA6B · ✅ chargeur LiPo (à vérifier) · ✅ imprimante Bambu P1S · ✅ PicoBoard (banc de poussée)
