"""
Génère le PowerPoint de présentation du projet Robot Tracking Autonome.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = RGBColor(0x0D, 0x0D, 0x1A)   # fond sombre
ACCENT   = RGBColor(0x00, 0xC8, 0xFF)   # bleu cyan
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
GRAY     = RGBColor(0xAA, 0xAA, 0xAA)
GREEN    = RGBColor(0x00, 0xE5, 0x96)
ORANGE   = RGBColor(0xFF, 0x8C, 0x00)
DARK_BOX = RGBColor(0x1A, 0x1A, 0x2E)

W = Inches(13.33)   # 16:9 large
H = Inches(7.5)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK = prs.slide_layouts[6]   # layout vierge


def add_slide():
    return prs.slides.add_slide(BLANK)


def bg(slide, color=BG):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def box(slide, x, y, w, h, color=DARK_BOX, radius=False):
    from pptx.util import Emu
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.color.rgb = ACCENT
    shape.line.width = Pt(0.8)
    return shape


def txt(slide, text, x, y, w, h, size=18, bold=False, color=WHITE,
        align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txb


def accent_line(slide, x, y, w):
    from pptx.util import Pt as PPt
    line = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(0.04))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()


def arrow_box(slide, items, x, y, box_w=1.8, box_h=0.65, gap=0.18):
    """Dessine des boîtes reliées par des flèches horizontalement."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    for i, (label, color) in enumerate(items):
        bx = x + i * (box_w + gap)
        b = box(slide, bx, y, box_w, box_h, color=color)
        b.line.color.rgb = ACCENT
        txt(slide, label, bx, y + 0.06, box_w, box_h - 0.1,
            size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        if i < len(items) - 1:
            ax = bx + box_w + 0.01
            arrow = slide.shapes.add_shape(
                1, Inches(ax), Inches(y + box_h / 2 - 0.03),
                Inches(gap - 0.02), Inches(0.06)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 1 – Titre
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
accent_line(s, 0.6, 1.8, 12.1)
accent_line(s, 0.6, 5.5, 12.1)

txt(s, "ROBOT TRACKING AUTONOME", 0.6, 0.5, 12, 1.0,
    size=42, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
txt(s, "Tourelle Pan-Tilt IA sur Base Roulante 4WD",
    0.6, 1.4, 12, 0.7, size=24, bold=False, color=WHITE, align=PP_ALIGN.CENTER)

# Tags
for i, (tag, col) in enumerate([
    ("YOLOv8n", GREEN), ("ByteTrack", ACCENT), ("Arduino Uno", ORANGE),
    ("Adafruit Shield v2", GREEN), ("DJI Osmo Action 4", ACCENT)
]):
    bx = 1.1 + i * 2.22
    b = box(s, bx, 2.15, 2.0, 0.5, color=DARK_BOX)
    b.line.color.rgb = col
    txt(s, tag, bx, 2.2, 2.0, 0.45, size=13, bold=True, color=col,
        align=PP_ALIGN.CENTER)

txt(s, "Détection & suivi de personnes en temps réel\n"
       "Tourelle orientable + base mobile autonome",
    1.5, 3.0, 10, 1.2, size=20, color=GRAY, align=PP_ALIGN.CENTER)

txt(s, "Projet personnel – 2025/2026", 0.6, 6.8, 12, 0.5,
    size=13, color=GRAY, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 2 – Vue d'ensemble
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Vue d'ensemble du système", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

desc = [
    ("🎯  Objectif",
     "Un robot autonome capable de détecter une personne, de la suivre\n"
     "avec une tourelle orientable, et de s'approcher d'elle en roulant."),
    ("🧠  Cerveau",
     "Un PC (ou smartphone Android) fait tourner YOLO + ByteTrack,\n"
     "calcule où pointer, envoie les ordres à l'Arduino via USB série."),
    ("⚙️  Corps",
     "L'Arduino Uno + Adafruit Motor Shield v2 pilote 2 servos\n"
     "(pan/tilt) et 4 moteurs DC via les ports M1–M4."),
    ("📷  Œil",
     "DJI Osmo Action 4 branchée en mode webcam USB (protocole UVC).\n"
     "Reconnue comme caméra standard, aucun driver spécial."),
]
for i, (titre, body) in enumerate(desc):
    row = i // 2
    col = i % 2
    bx, by = 0.4 + col * 6.5, 1.15 + row * 2.7
    b = box(s, bx, by, 6.1, 2.4)
    txt(s, titre, bx + 0.15, by + 0.12, 5.8, 0.55,
        size=16, bold=True, color=ACCENT)
    txt(s, body, bx + 0.15, by + 0.65, 5.8, 1.6,
        size=13, color=WHITE)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 3 – Pipeline technique
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Pipeline technique", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

# Flux principal
pipeline = [
    ("Caméra\nDJI UVC",    DARK_BOX),
    ("YOLOv8n\n(detect)",  RGBColor(0x1A, 0x2E, 0x1A)),
    ("ByteTrack\n(track)",  RGBColor(0x1A, 0x1A, 0x2E)),
    ("Calcul\nerreur px",   RGBColor(0x2E, 0x1A, 0x1A)),
    ("Serial USB\n115200",  RGBColor(0x1A, 0x2A, 0x2A)),
    ("Arduino\nUno",        RGBColor(0x2E, 0x20, 0x00)),
]
arrow_box(s, pipeline, x=0.35, y=1.2, box_w=1.95, gap=0.2)

# Sorties Arduino
txt(s, "Arduino", 5.8, 2.4, 2.0, 0.4, size=14, bold=True,
    color=ORANGE, align=PP_ALIGN.CENTER)
outputs = [
    ("Servo PAN\n(pin 9)\nGauche / Droite", 0.5, GREEN),
    ("Servo TILT\n(pin 10)\nHaut / Bas",    3.8, ACCENT),
    ("Moteurs DC\nM1–M4\nAvant / Recul / Virage", 7.1, ORANGE),
]
for label, bx, col in outputs:
    b = box(s, bx, 3.2, 2.9, 1.6, color=DARK_BOX)
    b.line.color.rgb = col
    txt(s, label, bx + 0.1, 3.3, 2.7, 1.4,
        size=13, bold=False, color=col, align=PP_ALIGN.CENTER)

# Protocole série
bp = box(s, 0.35, 5.25, 12.3, 1.0, color=RGBColor(0x0A, 0x0A, 0x18))
bp.line.color.rgb = GRAY
txt(s, "Protocole série :   \"error_x  error_y  bbox_h\\n\"   |   "
       "error_x/y = décalage pixel cible vs centre image   |   "
       "bbox_h = hauteur bbox (taille → distance estimée)",
    0.5, 5.35, 12.3, 0.8, size=12, color=GRAY, align=PP_ALIGN.CENTER)

txt(s, "bbox_h < 280 → AVANCER   |   280–420 → STOP   |   > 420 → RECULER   "
       "|   error_x → virage différentiel",
    0.5, 5.95, 12.3, 0.6, size=12, color=ACCENT, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 4 – Architecture hardware
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Architecture hardware", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

hw = [
    ("Arduino Uno",          "Microcontrôleur 16 MHz / 32 KB flash\nPilote servos (PWM D9/D10)\nReçoit commandes via USB-Serial", ORANGE),
    ("Adafruit Motor\nShield v2.3", "Contrôleur I2C (PCA9685 + TB6612)\n4 ports DC : M1 avant-G, M2 avant-D\nM3 arrière-D, M4 arrière-G", ACCENT),
    ("Servos PAN/TILT",      "PAN : rotation continue (D9)\nTILT : servo 180° standard (D10)\nMécanisme pan-tilt imprimé 3D", GREEN),
    ("Moteurs TT",           "4× moteurs jaunes 3–6V\nBase roulante 4WD\nVitesse pilotée 0–255 PWM", GREEN),
    ("Alimentation",         "LiPo 2S 7.4V → Arduino VIN + servos\nPiles AA ×4 série (6V) → Vs shield\n2 sources indépendantes", ORANGE),
    ("DJI Osmo Action 4",    "Webcam USB UVC standard\nAucun driver requis\n1080p / 4K – branché hub OTG", ACCENT),
]
for i, (titre, body, col) in enumerate(hw):
    row = i // 3
    col_ = i % 3
    bx = 0.35 + col_ * 4.33
    by = 1.15 + row * 2.75
    b = box(s, bx, by, 4.1, 2.45)
    b.line.color.rgb = col
    b2 = box(s, bx, by, 4.1, 0.5, color=col)
    b2.line.color.rgb = col
    txt(s, titre, bx + 0.1, by + 0.05, 3.9, 0.45,
        size=14, bold=True, color=BG, align=PP_ALIGN.CENTER)
    txt(s, body, bx + 0.1, by + 0.6, 3.9, 1.75,
        size=12, color=WHITE)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 5 – Évolution du projet (4 phases)
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Évolution du projet – 4 phases", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

phases = [
    ("Phase 1", "Tourelle\nManuelle",
     "Contrôle clavier\nC++ Arduino pur\nPas de vision", GRAY),
    ("Phase 2", "YOLO\nAuto",
     "YOLOv8 + suivi auto\n1er sujet détecté\nPas de sélection", GREEN),
    ("Phase 3", "Clic\nCible ✅",
     "ByteTrack + sélection\npar clic souris\nTracking robuste", ACCENT),
    ("Phase 4", "Robot\nRoulant 🚀",
     "Base 4WD autonome\nbbox_h → distance\nTéléphone Android", ORANGE),
]
for i, (ph, titre, body, col) in enumerate(phases):
    bx = 0.4 + i * 3.15
    b = box(s, bx, 1.15, 2.9, 5.5)
    b.line.color.rgb = col
    ph_box = box(s, bx, 1.15, 2.9, 0.55, color=col)
    ph_box.line.color.rgb = col
    txt(s, ph, bx + 0.1, 1.18, 2.7, 0.5,
        size=15, bold=True, color=BG, align=PP_ALIGN.CENTER)
    txt(s, titre, bx + 0.1, 1.85, 2.7, 1.0,
        size=20, bold=True, color=col, align=PP_ALIGN.CENTER)
    txt(s, body, bx + 0.15, 2.95, 2.6, 1.8,
        size=13, color=WHITE, align=PP_ALIGN.CENTER)
    if i < 3:
        arrow = box(s, bx + 2.9, 3.2, 0.25, 0.35, color=DARK_BOX)
        arrow.line.fill.background()
        txt(s, "→", bx + 2.9, 3.15, 0.28, 0.45,
            size=22, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 6 – Intégration mobile (téléphone)
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Intégration mobile – Option D (Hub OTG)", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

# Schéma connexion
schema_items = [
    ("Oppo A74\nAndroid", RGBColor(0x1A, 0x2E, 0x1A)),
    ("Hub Oliveria\nOTG ✅", DARK_BOX),
    ("DJI Osmo\nAction 4\n(UVC)", RGBColor(0x2E, 0x1A, 0x1A)),
]
arrow_box(s, schema_items, x=0.5, y=1.2, box_w=2.8, gap=0.3)

b = box(s, 6.5, 1.2, 0.3, 0.65, color=DARK_BOX)
b.line.fill.background()
txt(s, "↓", 6.5, 1.15, 0.4, 0.7, size=22, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

b2 = box(s, 6.1, 1.85, 2.8, 0.65, color=RGBColor(0x2E, 0x20, 0x00))
b2.line.color.rgb = ORANGE
txt(s, "Arduino Uno\n(USB série)", 6.1, 1.9, 2.8, 0.6,
    size=14, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)

# Points clés
points = [
    ("Zero ESP32 requis", "Un seul hub USB-C → remplace tout câblage sans-fil", GREEN),
    ("Même code Python", "IS_WINDOWS détecte l'OS → backends caméra/série adaptés", ACCENT),
    ("YOLO sur ARM", "ultralytics utilise NCNN automatiquement → ~5-10 FPS", ORANGE),
    ("Plug & Play", "DJI reconnue comme webcam V4L2, Arduino sur /dev/ttyUSB0", GREEN),
]
for i, (titre, body, col) in enumerate(points):
    row = i // 2
    c = i % 2
    bx = 0.4 + c * 6.5
    by = 3.2 + row * 1.8
    b = box(s, bx, by, 6.1, 1.55)
    b.line.color.rgb = col
    txt(s, f"✓  {titre}", bx + 0.15, by + 0.1, 5.8, 0.5,
        size=15, bold=True, color=col)
    txt(s, body, bx + 0.15, by + 0.6, 5.8, 0.8,
        size=12, color=GRAY)


# ═══════════════════════════════════════════════════════════════════════════════
# Slide 7 – Résultats & Next Steps
# ═══════════════════════════════════════════════════════════════════════════════
s = add_slide(); bg(s)
txt(s, "Résultats & Next Steps", 0.5, 0.25, 12, 0.7,
    size=30, bold=True, color=ACCENT)
accent_line(s, 0.5, 0.95, 12.3)

done = [
    "Détection temps réel YOLOv8n + ByteTrack",
    "Sélection de cible par clic, suivi robuste multi-personnes",
    "Tourelle pan-tilt précise (EMA lissage, watchdog sécurité)",
    "Base roulante 4WD câblée et validée (motor_test.ino ✅)",
    "Architecture multi-OS (Windows PC ↔ Android Termux)",
    "Hub OTG validé : DJI + Arduino simultanément ✅",
]
b_done = box(s, 0.4, 1.1, 7.2, 5.5)
b_done.line.color.rgb = GREEN
txt(s, "✅  Accompli", 0.55, 1.15, 7.0, 0.5,
    size=16, bold=True, color=GREEN)
for i, item in enumerate(done):
    txt(s, f"•  {item}", 0.55, 1.75 + i * 0.78, 6.9, 0.65,
        size=13, color=WHITE)

next_steps = [
    "Test tracker_rover.py sur PC avec DJI live",
    "Calibrer APPROACH/RETREAT_TARGET",
    "Finir setup Termux (pip install ultralytics)",
    "Test intégration complète sans PC",
    "Optimiser FPS YOLO mobile (NCNN / int8)",
]
b_next = box(s, 7.9, 1.1, 5.0, 5.5)
b_next.line.color.rgb = ORANGE
txt(s, "🚀  Next Steps", 8.05, 1.15, 4.8, 0.5,
    size=16, bold=True, color=ORANGE)
for i, item in enumerate(next_steps):
    txt(s, f"→  {item}", 8.05, 1.75 + i * 0.95, 4.7, 0.8,
        size=13, color=WHITE)


# ── Sauvegarde ────────────────────────────────────────────────────────────────
out = "Robot_Tracking_Autonome.pptx"
prs.save(out)
print(f"✅  Fichier généré : {out}")
