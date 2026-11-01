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
   | 1 | jambe G · S1 roulis de hanche |
   | 2 | jambe G · S2 tangage de hanche |
   | 3 | jambe G · S3 genou |
   | 4 | jambe G · S4 cheville |
   | 5 | jambe D · S1 roulis de hanche |
   | 6 | jambe D · S2 tangage de hanche |
   | 7 | jambe D · S3 genou |
   | 8 | jambe D · S4 cheville |

3. **Vérifier la chaîne complète** : branche les 8 servos en guirlande, puis
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
