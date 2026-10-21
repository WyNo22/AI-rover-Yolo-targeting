# CAO LEO-S (Rév. G)

Pièces imprimées d'une jambe, générées par `jambe_cad.py` (CadQuery). Les cotes viennent du plan `docs/jambe_leo_s.html`.

| Fichier | Pièce | Qté (robot) |
|---|---|---|
| `01_plaque_bassin` | plaque de bassin (les deux hanches) | 1 |
| `02_berceau_S1` | berceau fixe du servo de roulis | 2 (miroir pour la gauche) |
| `03_etrier_roulis_berceau_S2` | étrier de roulis + berceau de S2 | 2 (miroir) |
| `04_chape_cuisse_berceau_S3` | chape en U de cuisse + berceau de S3 + ancrage des ressorts | 2 (miroir) |
| `05_languette_genou` | bas de cuisse, tube Ø12 | 2 |
| `06_raccord_tibia_berceau_S4` | joues-cames du genou + levier B1 + berceau de S4 + 2 tubes Ø10 | 2 (miroir) |
| `07_tibia_bas` | languette de cheville, 2 tubes Ø10 | 2 |
| `08_pied` | pied 100 × 65 évidé + joues de cheville + levier de talon | 2 (miroir) |
| `09_bras_servo_22` | bras de 22 mm (S3, S4) | 4 |
| `10_entretoise_S3_12_4` / `11_entretoise_S4_4_4` | entretoises palonnier → bras de 6 mm (S3 / S4) | 2 / 2 |
| `16_semelle_TPU` | semelle TPU 95A, 4 mm, 4 poches FSR 402, rainures, 4 vis M3 fraisées | 2 (miroir) |

- `step/` : une pièce par fichier, les tubes à couper (`12` à `15`), et trois assemblages :
  - **`assemblage_robot_complet.step`** : les deux jambes + bassin + **buste estimé** (batteries, Pi, contrôleur de vol,
    bras et propulseurs, protections, tête) — généré par `robot_cad.py`, avec `bilan_masse.md` ;
  - `assemblage_jambe.step` : une jambe tendue avec tous ses composants ;
  - **`assemblage_deux_jambes.step`** : plaque de bassin + les deux jambes (gauche et droite symétriques), tous composants :
    servos (maquettes), pièces imprimées, tubes carbone, bielles avec rotules, bras, entretoises, roulements 625ZZ,
    vis épaulées M5, ressorts de genou, semelles, **toute la visserie** (vis de palonnier, vis de boîtier M2, rotules,
    colliers, goupilles des tubes, axe des ressorts, tendeurs, vis de semelle, vis du berceau de S1).
- `stl/` : mêmes pièces, prêtes à trancher.
- Repère : x avant, y extérieur, z haut, origine sur l'axe de tangage de hanche. **Jambe gauche : symétrie par rapport au plan xz** (dans Fusion : Miroir).
- Tubes carbone : cuisse Ø12 × 10 coupé à **130 mm**, tibia 2 × Ø10 × 8 coupés à **135 mm**, bielles Ø4 × 2
  coupées à **130 mm** (B1, entraxe 162) et **135 mm** (B2, entraxe 167).
- Les rotules se montent à côté du bras ou du levier (rondelle) : bielles à 40 mm (B1) et 32 mm (B2) de l'axe de jambe.

Contrôles faits : aucune collision entre tous les composants jambe tendue, ni sur les débattements
(roulis −20/+30°, hanche −30/+90°, genou 0–110°).

**À faire avant d'imprimer :**
1. Cotes du STS3215 reprises du plan Feetech (double sortie : palonnier Ø19,2, 4 trous en croix sur Ø14 de chaque côté,
   37,25 mm palonniers compris). Vérifier le filetage des trous du palonnier (M3 ou M2,5 : `HORN_HOLE`).
2. Les pièces entraînées se vissent sur les deux palonniers via un bossage Ø19,2 jusqu'au plan d'appui à 21,5 mm.
3. Imprimer un test d'emmanchement (Ø16,15 pour les 625ZZ, Ø12,2 / Ø10,2 pour les tubes) et ajuster `JEU`, `BRG_D`, `T12`, `T10`.

Régénérer : `pip install cadquery` puis `python jambe_cad.py`.

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
