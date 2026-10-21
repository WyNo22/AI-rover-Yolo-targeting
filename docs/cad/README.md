# CAO jambe LEO-S (Rév. F)

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
| `10_entretoise_11_5` / `11_entretoise_3_5` | entretoises palonnier → bras (S3 / S4) | 2 / 2 |

- `step/` : une pièce par fichier + `assemblage_jambe.step` (jambe droite tendue, avec maquettes des servos et des tubes).
- `stl/` : mêmes pièces, prêtes à trancher.
- Repère : x avant, y extérieur, z haut, origine sur l'axe de tangage de hanche. **Jambe gauche : symétrie par rapport au plan xz** (dans Fusion : Miroir).
- Tubes carbone : cuisse Ø12 × 10 coupé à **130 mm**, tibia 2 × Ø10 × 8 coupés à **135 mm**.

Contrôles faits : aucune collision entre pièces et servos jambe tendue, ni sur les débattements
(roulis −20/+30°, hanche −30/+90°, genou 0–110°).

**À faire avant d'imprimer :**
1. Mesurer le STS3215 (`SL, SW, SH, S_END, S_HOLE_*` en tête du script) : cotes relevées sur un modèle 3D.
2. Relever le motif de trous de ton palonnier (`HORN_PCD, HORN_N, HORN_HOLE`) : **valeurs provisoires**.
3. Imprimer un test d'emmanchement (Ø16,15 pour les 625ZZ, Ø12,2 / Ø10,2 pour les tubes) et ajuster `JEU`, `BRG_D`, `T12`, `T10`.

Régénérer : `pip install cadquery` puis `python jambe_cad.py`.
