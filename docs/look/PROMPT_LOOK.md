# LEO-S : brief de design visuel (à donner à une IA d'images)

## Images à joindre

1. `docs/look/planche_style.png` : silhouettes aux vraies proportions (face / profil), deux variantes de couleurs, palette.
2. `docs/look/visages_eink.png` : les 8 expressions de l'écran e-ink du visage.
3. `docs/cad/apercu_robot_complet.png` et `docs/cad/apercu_navigation.png` : la CAO réelle du robot.
4. **Photos de LEONARDO (Caltech)**, l'inspiration principale, à télécharger soi-même :
   - page du projet : https://aerospacerobotics.caltech.edu/leonardo
   - article et couverture *Science Robotics*, oct. 2021 (LEONARDO en équilibre sur une jambe) : https://authors.library.caltech.edu/records/a3y6x-12v73
   - photos skate : https://community.element14.com/technologies/industrial-automation-space/b/blog/posts/caltech-s-bipedal-robot-can-ride-a-skateboard

## Direction artistique (résumé)

- **Inspiration principale : LEONARDO** (Caltech). Bipède noir et technique, jambes fines en carbone, mécanique visible,
  propulseurs sur les épaules. Il doit avoir l'air **sérieux et impressionnant**, pas d'un jouet.
- **Touche de caractère** : un petit **visage e-ink** (deux yeux expressifs sur papier gris chaud) qui le rend attachant.
- **Couleurs** : **noir mat + carbone** dominants, **sable / beige** sur les coques (torse, haut des cuisses, cerclage
  des carénages d'hélices, chants des semelles), **une seule touche ambre** (liseré d'état). Le gris chaud du papier
  e-ink répond au sable.
- **Références de style** : produits noir et beige façon Braun / Dieter Rams et Teenage Engineering (sobre, précis),
  drones FPV en carbone mat, Disney BDX pour l'expressivité.

## Prompt principal (anglais)

```
Product concept render of "LEO-S", a small bipedal robot with thrusters, about 80 cm tall, inspired by Caltech's
LEONARDO robot. Serious, technical, impressive, not a toy.

Body layout, no arms:
- Two slim legs, each with 4 joints: hip roll, hip pitch, knee, ankle. The knee and ankle are driven remotely by thin
  carbon push rods from compact black servos mounted high (one behind the thigh near the hip, one at the top of the
  shin), so the lower legs are light and slender.
- Thigh: a single black carbon fiber tube (12 mm) between printed joint housings. Shin: two parallel thin carbon tubes
  (10 mm). The knee is a round cam joint with exposed bearings and two small extension springs on the front of the
  thigh. Flat rectangular feet (10 x 6.5 cm) with a thin rubber sole.
- Compact boxy torso (12 x 9 x 15 cm) above a flat pelvis plate, with rounded-corner shell panels.
- At shoulder height, a carbon fiber H-frame carries four 5-inch propellers in thin circular ducts (two each side,
  front and back), tilted 15 degrees outward. Span about 48 cm.
- Small rounded head on a short neck (pan/tilt). The front of the head is an e-paper face showing two simple rounded
  black eyes on warm grey paper. A tiny camera lens sits above the face. A short round LiDAR puck (4 cm) on top of
  the head.

Materials and colors: matte black 3D-printed parts with a fine layer texture, black twill carbon fiber, black
serial-bus servos with small brushed aluminum horns, sand / beige matte shell panels on the torso, upper thighs and
duct rims, warm grey e-paper face, a single thin amber status line on the chest. Visible screws and precise
engineering details.

Shot: three-quarter front view, full body, standing in a neutral pose, studio lighting on a seamless light warm-grey
background, soft shadows, 85 mm lens, high detail, photorealistic industrial design render.
```

### Variantes (remplacer le paragraphe « Materials and colors »)

- **A, noir intégral** : `all matte black and carbon fiber, graphite grey torso shell, no beige, only the warm grey
  e-paper face and a thin amber status line break the black.`
- **B, noir + sable** (préférée) : le texte ci-dessus.
- **C, sable dominant** : `sand / beige printed structural parts, with black carbon tubes, black servos and black
  ducts as contrast.`

### Mises en scène (remplacer le paragraphe « Shot »)

- `jumping over a 30 cm concrete step in a city street at dusk, thrusters spinning with motion blur, legs tucked, dynamic action shot`
- `descending outdoor stairs while hovering on its thrusters, feet just touching the next step, urban setting, golden hour`
- `riding a skateboard on a smooth plaza, balancing with its thrusters, low angle shot`
- `kicking a small soccer ball on artificial turf, one leg extended, e-paper face showing happy eyes`
- `close-up of the head: e-paper face with focused eyes, LiDAR puck on top, shallow depth of field`

### Prompt négatif

```
humanoid arms, human face, cartoon, toy, glossy plastic, chrome, LEDs everywhere, RGB lighting, bulky armor,
thick legs, wheels, extra limbs, text, watermark
```

## Expressions de l'écran e-ink (visages_eink.png)

| Expression | Quand |
|---|---|
| neutre | au repos |
| écoute | main levée vue, attend un ordre |
| content | ordre compris, salut (coucou) |
| suivi | suit le propriétaire (yeux tournés vers lui) |
| concentré | se prépare à sauter |
| surpris | obstacle imprévu, poussée, chute évitée |
| fatigué | batterie faible |
| STOP | arrêt d'urgence |
