# LEO-S : brief de design visuel (à donner à une IA d'images)

## Images à joindre

1. **Photos de LEONARDO (Caltech)**, l'inspiration principale, à télécharger soi-même :
   - page du projet : https://aerospacerobotics.caltech.edu/leonardo
   - article et couverture *Science Robotics*, oct. 2021 (LEONARDO en équilibre sur une jambe) : https://authors.library.caltech.edu/records/a3y6x-12v73
   - photos skate : https://community.element14.com/technologies/industrial-automation-space/b/blog/posts/caltech-s-bipedal-robot-can-ride-a-skateboard
2. **Une ou deux photos du casque de RoboCop (1987)** : pour la visière en bandeau et l'attitude.
3. `docs/cad/apercu_robot_complet.png` et `docs/cad/apercu_navigation.png` : la CAO réelle (mécanique, proportions).
4. `docs/look/planche_style.png` : **seulement pour les proportions** (face / profil). Ses couleurs et ses visages ne sont plus d'actualité.

## Direction artistique retenue

- **Ambiance :** LEONARDO × RoboCop. Sérieux, un peu menaçant, mécanique, militaire. Pas de rondeurs, pas de look jouet.
- **Couleurs :** noir mat + carbone pour toute la mécanique ; **sable militaire** pour quelques plaques d'armure ;
  **PETG blanc translucide dépoli** pour la visière uniquement.
- **Formes :** mécanique nue comme LEONARDO, avec seulement quelques plaques facettées à arêtes vives
  (casque, plastron, protections de cuisse).
- **Une seule lumière : la visière.** Fente lumineuse diffusée (on ne voit ni écran ni LED), dont la forme et la
  couleur changent : ambre au repos, blanc en écoute, rouge en colère ou STOP.
- **Plastron :** une plaque e-ink façon matricule militaire (« LEO-S », état, batterie), noir sur gris, non lumineuse.

## Prompt principal (anglais)

```
Product concept render of "LEO-S", a small bipedal robot with thrusters, about 80 cm tall. Design language: Caltech's
LEONARDO robot crossed with RoboCop. Serious, slightly menacing, military, mechanical. Not cute, not a toy.

Body layout, no arms:
- Two slim legs with exposed mechanics, like LEONARDO. Each leg has 4 joints: hip roll, hip pitch, knee, ankle. The
  knee and ankle are driven by thin black carbon push rods from compact black servos mounted high (one behind the
  thigh near the hip, one at the top of the shin), so the lower legs are light and slender.
- Thigh: a single black carbon fiber tube between angular black joint housings, covered on the front by a faceted
  military-sand armor plate. Shin: two parallel thin black carbon tubes. Knee: round cam joint with visible bearings
  and two small steel extension springs on the front of the thigh. Flat angular feet (10 x 6.5 cm) with a thin black
  rubber sole.
- Compact torso (12 x 9 x 15 cm) above a flat black pelvis plate, protected by a faceted, chamfered military-sand
  chest plate with sharp edges. On the chest plate, a small e-paper tag (2 inch) shows "LEO-S" and a status line in
  black on grey, like a military ID plate. It does not glow.
- At shoulder height, a black carbon fiber H-frame carries four 5-inch propellers in thin black ducts (two each side,
  front and back), tilted 15 degrees outward. Span about 48 cm.
- Head: a compact angular helmet in matte black and military sand on a short neck, with a narrow horizontal visor
  band across the front, RoboCop style. The visor is frosted white translucent plastic, lit from behind: a thin
  glowing amber slit, soft and diffused, the only light source on the whole robot. A tiny dark camera lens under the
  visor. A short round black LiDAR puck (4 cm) on top of the helmet.

Materials: matte black 3D-printed parts with a fine layer texture, black twill carbon fiber, black servos with small
brushed aluminum horns, matte military-sand armor plates, frosted translucent white visor, visible hex screws,
precise engineering details. No other lights, no LEDs anywhere else.

Shot: three-quarter front view, full body, standing still, head slightly lowered, looking at the camera. Moody studio
lighting on a dark grey seamless background, hard rim light, soft shadows, 85 mm lens, high detail, photorealistic
industrial design render.
```

### Mises en scène (remplacer le paragraphe « Shot »)

- `jumping over a 30 cm concrete step in a city street at night, thrusters spinning with motion blur, legs tucked, visor glowing amber, dynamic action shot`
- `descending outdoor stairs while hovering on its thrusters, feet just touching the next step, wet street at dusk, visor glowing amber`
- `riding a skateboard on an empty concrete plaza, balancing with its thrusters, low angle shot`
- `standing guard in a dark garage, visor glowing red, menacing low angle shot`
- `close-up of the helmet: frosted visor with a narrow amber glowing slit, LiDAR puck on top, shallow depth of field`

### États de la visière (pour des gros plans)

| État | Texte à mettre dans le prompt |
|---|---|
| neutre | `a thin, dim amber glowing slit` |
| écoute | `the slit opens wider and glows soft white` |
| suivi | `a short amber glowing segment shifted toward one side, tracking` |
| recherche | `an amber light bar sweeping left to right, scanner style` |
| concentré | `a very thin, bright amber slit with its ends angled down toward the center, intense look` |
| colère / STOP | `a red glowing V-shaped slit` |
| fatigué | `a dim amber slit drooping, flickering` |

### Prompt négatif

```
cute, toy, cartoon, rounded bubbly shapes, big eyes, human face, humanoid arms, glossy plastic, chrome, white plastic
body, LEDs or glowing lines on the body, RGB gaming lights, bulky armor, thick legs, wheels, extra limbs, text,
watermark
```
