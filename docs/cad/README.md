# CAO LEO-S (Rév. I)

Pièces imprimées d'une jambe, générées par `jambe_cad.py` (CadQuery). Les cotes viennent du plan `docs/jambe_leo_s.html`.

| Fichier | Pièce | Qté (robot) |
|---|---|---|
| `01_plaque_bassin` | plaque de bassin (les deux hanches) | 1 |
| `02_berceau_S1` | berceau fixe du servo de roulis | 2 (miroir pour la gauche) |
| `03_etrier_roulis_berceau_S2` | étrier de roulis + berceau de S2 | 2 (miroir) |
| `04_chape_cuisse_berceau_S3` | chape en U de cuisse + berceau de S3 + ancrage des ressorts | 2 (miroir) |
| `05_languette_genou` | bas de cuisse, tube Ø12 | 2 |
| `06_raccord_tibia_berceau_S4` | joues-cames du genou + levier B1 en cadre fermé (pont, arc, colonne) + berceau de S4 + 2 tubes Ø10 | 2 (miroir) |
| `07_tibia_bas` | languette de cheville, 2 tubes Ø10 | 2 |
| `08_pied` | pied 100 × 65, dessous plein (collage), poches par le dessus, joues en A + levier de talon intégré | 2 (miroir) |
| `09_bras_servo_22` | bras de 22 mm (S3, S4) | 4 |
| `10_entretoise_S3_11_8` / `11_entretoise_S4_3_8` | entretoises palonnier → bras de 6 mm (S3 / S4), alésées pour la vis centrale du palonnier | 2 / 2 |
| `16_semelle_TPU` | semelle TPU 95A, 4 mm, 4 poches FSR 402, rainures, **collée** sous le pied | 2 (miroir) |

- `step/` : une pièce par fichier, les tubes à couper (`12` à `15`), et trois assemblages :
  - **`assemblage_robot_complet.step`** : les deux jambes + bassin + **buste estimé** (batteries, Pi, contrôleur de vol,
    bras et propulseurs, protections, tête) — généré par `robot_cad.py`, avec `bilan_masse.md` ;
  - `assemblage_jambe.step` : une jambe tendue avec tous ses composants ;
  - **`assemblage_deux_jambes.step`** : plaque de bassin + les deux jambes (gauche et droite symétriques), tous composants :
    servos (**modèle réel `STS3215_c.step`**, inséré par instance), **câble du bus**, pièces imprimées, tubes carbone, bielles avec rotules, bras, entretoises, roulements 625ZZ,
    vis épaulées M5, ressorts de genou, semelles, **toute la visserie** (vis de palonnier, vis de boîtier M2, rotules,
    colliers, goupilles des tubes, axe des ressorts, tendeurs, vis du berceau de S1).
- `stl/` : mêmes pièces, prêtes à trancher.
- Repère : x avant, y extérieur, z haut, origine sur l'axe de tangage de hanche. **Jambe gauche : symétrie par rapport au plan xz** (dans Fusion : Miroir).
- Tubes carbone : cuisse Ø12 × 10 coupé à **130 mm**, tibia 2 × Ø10 × 8 coupés à **135 mm**, bielles Ø4 × 2
  coupées à **130 mm** (B1, entraxe 162) et **135 mm** (B2, entraxe 167).
- Les rotules se montent à côté du bras ou du levier (rondelle) : bielles à 40 mm (B1) et 32 mm (B2) de l'axe de jambe.

Contrôles faits : aucune collision entre tous les composants jambe tendue (servo réel et câble compris), ni sur les
débattements (roulis −20/+30°, hanche −30/+90°, genou 0–110°, cheville ±40°, bielles), ni pour les tronçons de câble
portés par chaque pièce pendant ces mouvements.

**À faire avant d'imprimer :**
1. Servo : modèle `STS3215_c.step` (palonniers Ø19,2, 4 trous en croix sur Ø14). Vérifier le filetage des trous du
   palonnier (M3 ou M2,5 : `HORN_HOLE`).
2. Les pièces entraînées se vissent sur les deux palonniers via un bossage Ø19,2 jusqu'au plan d'appui à 21,5 mm
   (bossage de 2,3 mm côté palonnier en saillie, 3,45 mm côté connecteurs, où le palonnier affleure).
3. Imprimer un test d'emmanchement (Ø16,15 pour les 625ZZ, Ø12,2 / Ø10,2 pour les tubes) et ajuster `JEU`, `BRG_D`, `T12`, `T10`.

Régénérer : `pip install cadquery` puis `python jambe_cad.py`.

## Rév. I — servo réel et câblage du bus

- **Servo = `STS3215_c.step`** (fourni) : un seul composant (boîtier, palonniers, connecteurs Molex, visserie interne),
  inséré par instance dans les assemblages (1 seul exemplaire du modèle par fichier STEP). Ce qu'il a changé :
  - boîtier asymétrique : plots à −17,9 côté connecteurs, étiquette à +17,3 → enveloppe ±18 (poches ±18,2) ;
  - palonniers : en saillie à 19,2 côté opposé aux connecteurs, presque affleurants à 18,05 côté connecteurs →
    bossages asymétriques ; entretoises S3 / S4 = 11,8 / 3,8 mm pour garder le plan des bielles ;
  - vis centrale d'origine du palonnier conservée (tête jusqu'à 21,55) → lamage Ø8,4 dans les bossages et les plaques,
    entretoises alésées Ø6,6 ; plus de vis centrale à nous.
- **Orientation** : connecteurs de S2, S3, S4 vers l'intérieur de la jambe, S1 vers l'arrière. Jambe droite : servo
  retourné autour de son axe long (pas de servo « miroir »), connecteurs toujours vers l'intérieur.
- **Bus en guirlande** bassin → S1 → S2 → S3 → S4 (câble Ø2,6 modélisé, `cablage_bus`, un seul corps par jambe) :
  - plaque de bassin : lumière au-dessus de chaque S1 ; berceau de S1 : fenêtre des connecteurs ouverte sur toute la hauteur ;
  - roulis : le câble S1 → S2 passe derrière S1 à 13 mm de l'axe de roulis, puis par une lumière du plancher de l'étrier ;
  - hanche : boucle S2 → S3 le long des faces des servos (le gousset arrière intérieur de la chape est supprimé pour elle) ;
  - berceaux de S3 et S4 : fenêtre devant les connecteurs (on branche les fiches, les fils sortent à plat) ;
  - cuisse et tibia : **passe-câbles imprimés dans la chape, la languette du genou et le raccord du tibia** ;
  - **genou : pion coaxial Ø5 sur le raccord**, le câble s'y enroule → longueur quasi constante (±4 mm sur 110°)
    au lieu d'une boucle de 24 mm. La vis M5 du genou se monte donc tête côté extérieur, écrou côté intérieur.
- Visserie de palonnier : **M3×12** (S1 et S2), **M3×22** (bras de S3), **M3×14** (bras de S4) — pointes arrêtées au dos du palonnier.

## Rév. H — corrections

- **Pied refait** : les 4 bossages de vis de semelle flottaient dans les évidements (corps séparés dans le STEP) et le
  levier de talon ne tenait que par une arête. Maintenant : plaque 6 mm avec dessous plein (surface de collage) et
  poches par le dessus (peau 2,5 mm), joues en A tangentes au moyeu de cheville, levier de talon collé sur toute la face
  extérieure de la joue, lamage pour l'écrou M5. +11 g par pied.
- **Semelle TPU collée** (plus de vis) : colle souple pour TPU/PETG (cyanoacrylate souple + primaire, ou colle néoprène),
  FSR posés dans leurs poches avant collage, queues des FSR par les encoches latérales.
- **Levier B1 du genou** : l'ancienne lame de 6 mm en biais remplacée par un arc de 8 mm autour de l'axe (la vis M5
  et la clé passent) + une colonne Ø13 qui ramène le moyeu sur la joue → cadre fermé joue / pont / arc / colonne.
- Berceaux de S3 et S4 : arêtes extérieures arrondies (r 3).
- Vérifié : chaque pièce = 1 seul corps, aucune collision statique, ni sur les débattements (roulis, hanche, genou
  0–110°, cheville ±40° avec bielles et bras).

## Rév. G — ce qui a changé

Efforts de référence : réception d'un saut sur une jambe ≈ 54 N, servo au blocage 2,9 N·m → **134 N dans une bielle**.

| Pièce | Modification | Pourquoi |
|---|---|---|
| Bras de servo | 4 → **6 mm**, racine plus large, insert M3 au bout | 14 → 9 MPa au blocage |
| Raccord tibia | pont du levier B1 **14 × 12** + gousset décalé de l'écrou M5 ; bloc plein → **nervures** ; goupille M3 à travers les 2 tubes | 20 → 8 MPa entre couches ; −matière inutile |
| Étrier de roulis | plancher 6 mm, **goussets** plaques ↔ plancher, joues du berceau S2 5,5 mm, allègement réduit | il porte tout le moment de la jambe en roulis |
| Berceau S1 | **fond** sous S1 (hors zone balayée par l'étrier), bloc plus grand et évidé | les joues seules étaient souples |
| Chape de cuisse | **goussets** bras ↔ traverse, collier remonté | coin le plus chargé |
| Tibia bas | évidé entre les tubes, goupille M3 traversante | moins de matière, tubes bloqués |
| Pied | **goussets** avant/arrière des joues, traverse, bossages d'inserts | la joue ne tenait que par son pied |
| Semelle TPU | **nouvelle** | adhérence, amorti, capteurs de force |
| Entretoises | 12,4 (S3) et 4,4 (S4) | bras plus épais, plans des bielles inchangés |

Contrôles : aucune collision entre tous les composants (visserie comprise) jambe tendue, ni sur les débattements.

**Masse (bilan_masse.md) : ≈ 2,38 kg, centre de gravité à ≈ 467 mm du sol.** Pistes pour revenir vers 2,1 kg :
protections d'hélices en anneau fin ou en jonc carbone (−90 g), semelle TPU 3 mm à 50 % (−30 g), raccords du tibia
et étrier allégés après essais (−30 g).
