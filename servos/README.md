# Banc des servos STS3215 (LEO-S)

Outil : `sts_banc.py` (Python 3 + `pyserial`). Il fonctionne sur le PC (Windows) ou sur le Raspberry Pi.

- Windows : `pip install pyserial`
- Pi : déjà installé (`python3-serial`)

`test_sts_banc.py` teste l'outil sans matériel, sur un bus simulé : `python test_sts_banc.py`.

## Branchement

```
3S (11,1–12,6 V) ──► bornier à vis vert (+ / −) de l'adaptateur Waveshare
                     cavalier sur B (mode USB)
PC ou Pi ──USB-C──► adaptateur ──câble 3 broches──► servo
```

- **Cavalier en position B** pour l'USB (la position A sert à piloter depuis une carte en série).
- **Alimentation 12 V** : ta LiPo 3S sur le bornier vert, ou une alimentation 12 V ≥ 3 A sur le jack 5,5 × 2,1.
  **Jamais la 4S** (16,8 V détruit les STS3215).
- Le port apparaît en **COMx** sous Windows, **/dev/ttyACM0** sur le Pi. `python sts_banc.py ports` le montre.

## Procédure

1. **Vérifier la liaison** avec un seul servo neuf branché :
   ```
   python sts_banc.py scan
   ```
   On doit voir `1 servo(s) : [1]`, modèle 777, tension ≈ 11–12,6 V.

2. **Donner les ID**, guidé, un servo à la fois. Les servos neufs sont tous en ID 1.
   ```
   python sts_banc.py installer
   ```
   Pour chaque ID de 1 à 8 : branche **un seul** servo, Entrée, puis colle une étiquette avec son numéro.
   Le script le renumérote, le met au centre et affiche ses mesures. S'il voit plusieurs servos à la fois, il refuse et redemande.

   | ID | Articulation |
   |---|---|
   | 1 | jambe D · S1 roulis de hanche |
   | 2 | jambe D · S2 tangage de hanche |
   | 3 | jambe D · S3 genou |
   | 4 | jambe D · S4 cheville |
   | 5 | jambe G · S1 roulis de hanche |
   | 6 | jambe G · S2 tangage de hanche |
   | 7 | jambe G · S3 genou |
   | 8 | jambe G · S4 cheville |

3. **Vérifier la chaîne complète** : prise DVG droite → 1 → 2 → 3 → 4 (jambe droite), prise DVG gauche → 5 → 6 → 7 → 8
   (jambe gauche), puis
   ```
   python sts_banc.py scan
   python sts_banc.py info 1 2 3 4 5 6 7 8
   ```

4. **Tester chaque servo** (aller-retour de ±35°, puis couple libéré) :
   ```
   python sts_banc.py test 1
   ```
   Valeurs attendues à vide : charge < 10 %, courant de quelques centaines de mA en mouvement, température proche
   de l'ambiante. Un servo qui force, grince ou chauffe sans charge est à mettre de côté.

5. **Avant le montage**, tout mettre au centre (2048) :
   ```
   python sts_banc.py centre 1 2 3 4 5 6 7 8
   ```
   Monte les pièces sur les palonniers dans la position neutre de la CAO (jambe tendue, pied à plat).

6. **Après le montage**, régler le zéro exact de chaque articulation. Tiens la jambe dans la position de référence
   (tendue, pied à plat), puis :
   ```
   python sts_banc.py zero 3
   ```
   La position actuelle devient le centre (2048), enregistré dans le servo. `zero-reset 3` annule.

## Autres commandes

| Commande | Effet |
|---|---|
| `suivi 1 2 3 4` | tableau en direct : position, tension, température, charge, courant |
| `move 3 2500` | va à une position (0–4095 ; 2048 = centre ; 4096 pas = 360°) |
| `couple 3 off` / `on` | libère ou bloque le servo (couple libre pour le tourner à la main) |
| `id 1 5` | change un ID à la main (un seul servo branché) |

## Jambe complète : `jambe_banc.py`

Une fois la jambe montée et les zéros faits (`sts_banc.py zero`, jambe tendue et pied à plat), tout se fait avec ce
script. Il faut aussi `matplotlib` pour l'animation : `pip install matplotlib`.

Jambe fixée par le haut au bord d'une table, pied dans le vide (sauf l'étape 6). `--jambe G` pour la jambe gauche
(ID 5–8). Les réglages sont enregistrés dans `jambe_D.json` / `jambe_G.json`.

| # | Commande | Ce que tu fais | C'est bon si |
|---|---|---|---|
| 0 | `python jambe_banc.py marche --sim` | rien : la marche des deux jambes s'anime sur le PC | tu vois ce que la vraie jambe va faire |
| 1 | `python jambe_banc.py butees` | couple coupé, tu amènes chaque articulation à ses deux limites à la main | limites enregistrées ; la jambe s'arrêtera ensuite à 5° de chaque butée |
| 2 | `python jambe_banc.py sens` | chaque articulation bouge un peu ; tu réponds o/n | chaque articulation part dans le sens annoncé (sinon le sens est inversé automatiquement) |
| 3 | `python jambe_banc.py cycle` | chaque articulation fait toute sa course, aller-retour | charge < 20 %, rien ne frotte ni n'accroche |
| 4 | `python jambe_banc.py pied 40 30` | le pied va 40 mm devant et 30 mm plus haut que la position debout | il y va, et **reste à plat** |
| 5 | `python jambe_banc.py marche` | la vraie jambe fait 6 pas dans le vide | mouvement fluide, charge et température affichées raisonnables |
| 6 | `python jambe_banc.py charge` | pied posé sur une balance (~1,2 kg d'appui), 5 min de flexions | < 60 % de charge et < 50 °C ; mesures dans `charge_D_….csv` |

`python jambe_banc.py repos` coupe le couple. Ctrl+C à tout moment coupe aussi le couple.
Rythmes : `marche --rythme lent|moyen|max` (moyen par défaut), en vrai comme en simulation (`--sim`).
`rythmes` enchaîne les trois sur la vraie jambe, avec Entrée entre chaque (« s » pour s'arrêter).

| Rythme | Un pas toutes les | Pas | Vitesse du robot | Articulation la plus rapide |
|---|---|---|---|---|
| lent | 2,0 s | 40 mm | ≈ 0,12 km/h | genou 73°/s |
| moyen | 1,2 s | 50 mm | ≈ 0,25 km/h | genou 152°/s |
| max | 0,92 s (calculée) | 60 mm | ≈ 0,39 km/h | genou 200°/s (limite fixée à ~75 % du servo) |

Les options `--periode --pas --levee --roulis --cycles` remplacent celles du rythme.

**Endurance** : `python jambe_banc.py endurance` (5 min au rythme moyen ; `--minutes 10 --rythme max` pour varier).
La jambe marche dans le vide ; le script enregistre consigne et position mesurée, charge, courant, température et
tension 5 fois par seconde dans `endurance_D_….csv`, affiche un bilan par minute et la dérive entre la première et
la dernière minute (une charge qui monte = frottement ou pièce qui se déforme, un écart qui grandit = jeu qui
apparaît), et trace `endurance_D_….png`. Il s'arrête seul à 60 °C ou sous 10,5 V.
`python test_jambe_banc.py` teste le script sans matériel.
