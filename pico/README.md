# Pico 2 de LEO-S : scripts de mise en route (MicroPython)

Un script par étape, à lancer dans l'ordre, chacun branché et validé avant de passer au suivant.
Brochage : `docs/schema_electrique.html` (rév. J). Toutes les broches et calibrations sont dans `lib/brochage.py`.

| Fichier | Rôle |
|---|---|
| `lib/brochage.py` | broches, adresses I²C, réglages et calibrations (le seul fichier à modifier) |
| `lib/sts.py` | protocole des servos STS3215 (même protocole que `servos/sts_banc.py`) |
| `lib/mpu6050.py` | centrale inertielle + filtre d'inclinaison |
| `lib/ads1x15.py` | ADS1015 / ADS1115 + calcul de la résistance des FSR |
| `lib/ibus.py` | récepteur FlySky en iBUS |
| `lib/batterie.py` | tension de la 3S |
| `etape1_pico.py` … `etape7_radio.py` | un test par étape |
| `test_sim.py` | teste tout sur PC sans matériel (`python test_sim.py`) |

## Installer (une fois)

1. **Thonny** (thonny.org) sur le PC. Récupère les nouveaux fichiers du dépôt : `git pull` dans ton dossier du projet.
2. **MicroPython sur le Pico 2** : maintiens le bouton BOOTSEL, branche l'USB, relâche.
   Dans Thonny : *Outils → Options → Interpréteur → MicroPython (Raspberry Pi Pico)* → *Installer ou mettre à jour
   MicroPython* → variante **Raspberry Pi • Pico 2** → Installer.
3. **Copier la bibliothèque** sur le Pico : *Affichage → Fichiers*. Côté Pico (en bas), clic droit → *Nouveau dossier*
   → `lib`. Côté PC (en haut), va dans `pico/lib`, sélectionne les 6 fichiers → clic droit → *Téléverser vers /lib*.
   En ligne de commande, c'est aussi possible : `pip install mpremote` puis, dans le dossier `pico` : `mpremote cp -r lib :`.
4. **Lancer une étape** : ouvre le fichier `etapeN_….py` dans Thonny, **F5**. Il tourne sur le Pico (pas besoin de le
   copier). Bouton **Stop** ou Ctrl+C pour arrêter.

Après une calibration, modifie `lib/brochage.py` sur le PC **et** téléverse-le à nouveau dans `/lib`.

## Broches du Pico 2 utilisées

| Broche (n°) | Fonction | Va vers |
|---|---|---|
| GP4 (6) · GP5 (7) | I²C0 SDA · SCL | MPU6050, ADS1015 ×2 (et plus tard les ToF) |
| GP20 (26) · GP21 (27) | UART1 TX · RX | adaptateur bus servo, cavalier sur **A** |
| GP1 (2) | UART0 RX | récepteur FS-iA6B, prise iBUS |
| GP26 (31) · AGND (33) | ADC0 | pont de la batterie 3S |
| 3V3 OUT (36) | 3,3 V | MPU6050, ADS1015, haut des FSR |
| VBUS (40) | 5 V de l'USB | récepteur radio |
| GND (38, 3, 8…) | masse | tout, y compris la masse de l'adaptateur servo |

## Les étapes

**1 – Pico seul** · `etape1_pico.py` : la LED clignote 3 fois et le scan I²C s'affiche (vide si rien n'est branché).

**2 – MPU6050** · VCC → 3V3, GND, SDA → GP4, SCL → GP5, AD0 → GND.
`etape2_mpu.py` : la carte posée à plat 2 s, il donne le biais du gyroscope (à copier dans `GYRO_BIAIS`) puis
l'inclinaison en direct. Vérifie que roulis et tangage suivent quand tu penches la carte et reviennent à ~0° à plat.

**3 – FSR au multimètre (sans script)** · plus de 1 MΩ au repos, quelques kΩ au doigt, quelques centaines d'Ω très appuyé.
Pas de soudure longue sur les pattes : connecteur Dupont femelle + colle chaude, ou moins de 2 s à ~300 °C.

**4 – FSR + ADS1015** · ADS : VDD → 3V3, GND, SCL → GP5, SDA → GP4, ADDR → GND (pied G, 0x48) ou → 3V3 (pied D, 0x49).
Chaque FSR : une patte au 3V3, l'autre sur A0 (talon), A1 (pointe int.) ou A2 (pointe ext.) **et** sur la résistance
du pont vers la masse.
- `etape4_pieds.py` avec `MODE = "direct"` : les 3 capteurs de chaque pied en continu, appuie au doigt.
- Puis `MODE = "pesee"` : pose des masses connues (0,1 / 0,5 / 1 / 2 kg) sur une pièce de monnaie centrée sur le FSR ;
  le script conseille la résistance du pont. Mets-la dans `R_FSR`, et dans `R_PONT` du script si tu la changes.

**5 – Bus servo depuis le Pico** · cavalier de l'adaptateur sur **A**, 12 V sur son bornier.
Avant de brancher le Pico, au multimètre entre la masse et chaque broche TX/RX de l'adaptateur (rien d'autre branché) :
la broche à **~3,3 V** est la sortie de l'adaptateur → **GP21** ; l'autre → **GP20**. Si elle lit **~5 V**, ne la
branche pas directement : pont 1 kΩ (côté adaptateur) + 2 kΩ (vers la masse) sur la ligne de GP21. Relie aussi les GND.
`etape5_servos.py` : scan, état des 8 servos, durée d'un cycle de la future boucle, puis (si tu réponds « o ») chaque
servo bouge de ±9° l'un après l'autre et se relâche. Pour revenir au banc PC (`servos/sts_banc.py`), cavalier sur B.

**6 – Batterie** · 100 kΩ entre le + de la 3S et GP26, 33 kΩ entre GP26 et AGND (33), 100 nF en parallèle sur la 33 k.
**Jamais sur la 4S.** `etape6_batterie.py` affiche la tension (et celle lue par un servo pour comparer), puis te
demande la valeur du multimètre et donne `CAL_BATTERIE`.

**7 – Radio et arrêt d'urgence** · récepteur : prise iBUS → GP1, + → VBUS, − → GND. Sur l'émetteur, règle le
**failsafe de CH5 sur la position ARRÊT**. `etape7_radio.py` affiche les voies, et :
- CH5 sur ARMÉ → les servos se raidissent sur leur position actuelle (aucun mouvement), LED allumée ;
- CH5 sur ARRÊT → couple coupé sur les 8 servos, LED éteinte ;
- émetteur éteint → couple coupé en moins de 0,1 s.
Si l'interrupteur marche à l'envers, change `ARRET_SI_HAUT` dans `brochage.py`.
**Cette étape doit marcher avant de monter les jambes.**
