"""
gestures.py – Reconnaissance de gestes à partir des 17 points du corps (format COCO, modèles *-pose).

Gestes (voir PROJET.md) :
  STOP    les deux bras levés, immobiles          0,3 s   n'importe qui
  ECOUTE  une main levée, immobile                1 s     « c'est moi, écoute »
  POINTE  bras tendu sur le côté                  1 s     direction donnée par épaule → poignet
  REPOS   bras croisés en X sur la poitrine       1 s
  COUCOU  main levée qui oscille                  3 allers-retours
  VIENS   avant-bras qui se replie vers soi       2 cycles
  SAUTE   on mime le saut : genoux pliés puis redressés en moins de 2,5 s

Les gestes statiques doivent être tenus (barre de progression dans l'interface) ;
les gestes dynamiques se déclenchent à la fin du mouvement.
"""
import math
import time
from collections import deque

import numpy as np

# Indices COCO
NOSE, LSH, RSH, LEL, REL, LWR, RWR, LHIP, RHIP, LKNEE, RKNEE, LANK, RANK = 0, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
SKELETON = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4)]

KP_MIN = 0.4                    # visibilité minimale d'un point
HOLD_S = {"STOP": 0.3, "ECOUTE": 1.0, "POINTE": 1.0, "REPOS": 1.0}
DROPOUT_S = 0.25                # un geste tenu survit à une image ratée
COOLDOWN_S = 2.0                # délai avant de redéclencher un geste dynamique
FORGET_S = 2.0                  # oubli d'une personne disparue


def _angle(a, b, c):
    """Angle en b (degrés) entre b→a et b→c."""
    u, v = a - b, c - b
    n = np.linalg.norm(u) * np.linalg.norm(v)
    return math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v) / n)))) if n > 1e-9 else 180.0


class _Track:
    def __init__(self):
        self.label, self.since, self.last_label_t, self.fired = None, 0.0, 0.0, False
        self.seen = 0.0
        self.wave = {LWR: deque(), RWR: deque()}       # (t, x poignet − x coude) / échelle
        self.beck = {LWR: deque(), RWR: deque()}       # (t, état coude : 0 ouvert, 1 fermé)
        self.squat_down = None                          # instant où les genoux se sont pliés
        self.cool = {}
        self.point = None


class GestureRecognizer:
    def __init__(self):
        self.tracks = {}
        self.current = {}       # id → (geste, progression 0..1) pour l'affichage
        self.pointing = {}      # id → (vx, vy) vecteur unitaire dans l'image (x corrigé de l'aspect)

    def update(self, t, persons, aspect):
        """persons : {id: kpts (17, 3) normalisés 0..1}. aspect = largeur / hauteur de l'image.
        Retourne les gestes déclenchés : [(nom, id, info)]."""
        events, current, pointing = [], {}, {}
        for tid, kp in persons.items():
            tr = self.tracks.setdefault(tid, _Track())
            tr.seen = t
            P = kp[:, :2] * [aspect, 1.0]          # mêmes unités en x et y
            vis = kp[:, 2] >= KP_MIN
            geo = self._geometry(P, vis)
            if geo is None:
                continue
            for ev in self._dynamic(t, tr, P, vis, geo):
                events.append((ev, tid, None))
            label, info = self._static(P, vis, geo, waving=self._waving(t, tr))
            if label is not None:
                tr.last_label_t, tr.point = t, info
            elif tr.label is not None and t - tr.last_label_t < DROPOUT_S:
                label, info = tr.label, tr.point          # image ratée : le geste tenu survit
            if label != tr.label:
                tr.label, tr.since, tr.fired = label, t, False
            if label is not None:
                prog = min(1.0, (t - tr.since) / HOLD_S[label])
                current[tid] = (label, prog)
                if label == "POINTE" and info is not None:
                    pointing[tid] = info
                if prog >= 1.0 and not tr.fired:
                    tr.fired = True
                    events.append((label, tid, info))
        for tid in [k for k, tr in self.tracks.items() if t - tr.seen > FORGET_S]:
            del self.tracks[tid]
        self.current, self.pointing = current, pointing
        return events

    # ── géométrie commune ─────────────────────────────────────────────────────
    @staticmethod
    def _geometry(P, vis):
        if not (vis[LSH] and vis[RSH]):
            return None
        sh = (P[LSH] + P[RSH]) / 2
        if vis[LHIP] and vis[RHIP]:
            hip = (P[LHIP] + P[RHIP]) / 2
            S = float(np.linalg.norm(hip - sh))            # longueur du torse
        else:
            S = float(np.linalg.norm(P[LSH] - P[RSH])) * 1.6
            hip = sh + [0.0, S]
        if S < 1e-3:
            return None
        head_y = P[NOSE][1] if vis[NOSE] else sh[1] - 0.45 * S
        return {"sh": sh, "hip": hip, "S": S, "head_y": head_y}

    # ── gestes statiques ──────────────────────────────────────────────────────
    @staticmethod
    def _static(P, vis, g, waving):
        S, head_y, sh, hip = g["S"], g["head_y"], g["sh"], g["hip"]

        def up(w):
            return vis[w] and P[w][1] < head_y - 0.05 * S

        # STOP : deux mains au-dessus de la tête, coudes au-dessus des épaules
        if up(LWR) and up(RWR) and \
                (not vis[LEL] or P[LEL][1] < P[LSH][1]) and (not vis[REL] or P[REL][1] < P[RSH][1]):
            return "STOP", None
        # REPOS : poignets croisés (chacun du côté opposé de l'axe du corps), à hauteur de poitrine
        if vis[LWR] and vis[RWR]:
            chest = all(sh[1] < P[w][1] < hip[1] + 0.1 * S for w in (LWR, RWR))
            crossed = (P[LWR][0] - sh[0]) * (P[LSH][0] - sh[0]) < 0 and \
                      (P[RWR][0] - sh[0]) * (P[RSH][0] - sh[0]) < 0
            if chest and crossed:
                return "REPOS", None
        # ECOUTE : une seule main levée, immobile (sinon c'est un coucou)
        if up(LWR) != up(RWR) and not waving:
            other = RWR if up(LWR) else LWR
            if not vis[other] or P[other][1] > sh[1]:
                return "ECOUTE", None
        # POINTE : bras tendu, écarté du corps, ni levé ni pendant
        for s_, e_, w_ in ((LSH, LEL, LWR), (RSH, REL, RWR)):
            if not (vis[s_] and vis[e_] and vis[w_]):
                continue
            v = P[w_] - P[s_]
            reach = float(np.linalg.norm(v))
            if _angle(P[s_], P[e_], P[w_]) > 150 and reach > 0.9 * S and abs(v[0]) > 0.6 * S \
                    and head_y < P[w_][1] < hip[1] + 0.2 * S:
                return "POINTE", (float(v[0] / reach), float(v[1] / reach))
        return None, None

    # ── gestes dynamiques ─────────────────────────────────────────────────────
    @staticmethod
    def _reversals(series, hyst):
        """Nombre de changements de sens d'une série (x), avec hystérésis."""
        n, d, ext = 0, 0, None
        for _, x in series:
            if ext is None:
                ext = x
            elif d == 0:
                if abs(x - ext) > hyst:
                    d, ext = (1 if x > ext else -1), x
            elif d * (x - ext) > 0:
                ext = x                              # on continue dans le même sens
            elif abs(x - ext) > hyst:
                n, d, ext = n + 1, -d, x             # demi-tour
        return n

    def _waving(self, t, tr):
        return any(self._reversals([p for p in q if t - p[0] < 1.0], 0.12) >= 1 for q in tr.wave.values())

    def _dynamic(self, t, tr, P, vis, g):
        S, head_y, hip = g["S"], g["head_y"], g["hip"]
        out = []

        def ready(name):
            return t - tr.cool.get(name, -1e9) > COOLDOWN_S

        for s_, e_, w_ in ((LSH, LEL, LWR), (RSH, REL, RWR)):
            if not (vis[s_] and vis[e_] and vis[w_]):
                continue
            # COUCOU : main bien au-dessus de l'épaule, le poignet oscille autour du coude
            q = tr.wave[w_]
            raised = P[w_][1] < P[s_][1] - 0.35 * S
            if raised:
                q.append((t, float(P[w_][0] - P[e_][0]) / S))
            while q and t - q[0][0] > 1.5:
                q.popleft()
            if raised and ready("COUCOU") and self._reversals(q, 0.12) >= 3:
                out.append("COUCOU")
                tr.cool["COUCOU"] = t
            # VIENS : main devant soi (entre tête et hanches), le coude s'ouvre et se ferme
            b = tr.beck[w_]
            if head_y < P[w_][1] < hip[1]:
                a = _angle(P[s_], P[e_], P[w_])
                state = 0 if a > 130 else 1 if a < 85 else None
                if state is not None and (not b or b[-1][1] != state):
                    b.append((t, state))
            while b and t - b[0][0] > 2.5:
                b.popleft()
            if ready("VIENS") and len(b) >= 4:
                out.append("VIENS")
                tr.cool["VIENS"] = t
                b.clear()
        # SAUTE : genoux pliés (< 125°) puis redressés (> 155°) en moins de 2,5 s
        knees = [_angle(P[h], P[k], P[a]) for h, k, a in ((LHIP, LKNEE, LANK), (RHIP, RKNEE, RANK))
                 if vis[h] and vis[k] and vis[a]]
        if knees:
            ang = min(knees)
            if ang < 125 and tr.squat_down is None:
                tr.squat_down = t
            elif ang > 155 and tr.squat_down is not None:
                if t - tr.squat_down < 2.5 and ready("SAUTE"):
                    out.append("SAUTE")
                    tr.cool["SAUTE"] = t
                tr.squat_down = None
        return out


# ── Personne synthétique pour tester sans caméra (--model demo-pose) ─────────
class DemoPoseDetector:
    """Une personne qui enchaîne les gestes en boucle : permet de tester gestes, comportement et
    affichage sans modèle ni caméra."""

    # Chaque ordre est précédé d'une main levée (ECOUTE), comme dans la vraie vie.
    SCRIPT = [("—", 1.5), ("ECOUTE", 1.4), ("POINTE", 2.0), ("—", 3.0), ("COUCOU", 2.5), ("—", 1.0),
              ("ECOUTE", 1.4), ("VIENS", 2.5), ("—", 1.0), ("ECOUTE", 1.4), ("—", 0.3), ("SAUTE", 2.0),
              ("—", 1.0), ("ECOUTE", 1.4), ("REPOS", 1.8), ("—", 2.0), ("ECOUTE", 1.5), ("—", 1.0),
              ("STOP", 1.5), ("—", 2.0), ("ECOUTE", 1.5), ("—", 1.0)]

    def __init__(self):
        self.t0 = time.monotonic()
        self.period = sum(d for _, d in self.SCRIPT)

    def _phase(self):
        t = (time.monotonic() - self.t0) % self.period
        for name, d in self.SCRIPT:
            if t < d:
                return name, t
            t -= d
        return "—", 0.0

    @staticmethod
    def _arm(sh, sg, a1, a2):
        """Bras : a1 = angle de l'épaule depuis la verticale basse, a2 = flexion du coude (degrés)."""
        r1, r12 = math.radians(a1), math.radians(a1 + a2)
        el = sh + 0.6 * np.array([sg * math.sin(r1), math.cos(r1)])
        return el, el + 0.55 * np.array([sg * math.sin(r12), math.cos(r12)])

    def detect(self, img, classes=None):
        h, w = img.shape[:2]
        name, t = self._phase()
        S = h * 0.2
        cx = w * (0.5 + 0.15 * math.sin((time.monotonic() - self.t0) * 0.3))
        drop = 0.0
        if name == "SAUTE" and 0.5 < t < 1.2:
            drop = 0.4
        o = np.array([cx, h * 0.3 + drop * S])          # milieu des épaules
        L, R = +1, -1                                    # gauche de la personne = droite de l'image
        pts = {NOSE: (0, -0.45), 1: (0.08, -0.52), 2: (-0.08, -0.52), 3: (0.18, -0.48), 4: (-0.18, -0.48),
               LSH: (0.4, 0), RSH: (-0.4, 0), LHIP: (0.25, 1.0), RHIP: (-0.25, 1.0)}
        k = {i: o + np.array(v) * S for i, v in pts.items()}
        arms = {L: (8, 8), R: (8, 8)}
        if name == "ECOUTE":
            arms[L] = (170, 0)
        elif name == "POINTE":
            arms[R] = (95, 0)
        elif name == "STOP":
            arms = {L: (165, 0), R: (165, 0)}
        elif name == "REPOS":
            arms = {L: (0, -120), R: (0, -120)}
        elif name == "COUCOU":
            arms[R] = (150, 35 * math.sin(t * 2 * math.pi * 2))
        elif name == "VIENS":
            arms[R] = (60, 55 - 55 * math.cos(t * 2 * math.pi * 1.2))
        for sg, (sh_i, el_i, wr_i) in ((L, (LSH, LEL, LWR)), (R, (RSH, REL, RWR))):
            el, wr = self._arm(np.zeros(2), sg, *arms[sg])
            k[el_i], k[wr_i] = k[sh_i] + el * S, k[sh_i] + wr * S
        knee_dx = 0.25 if drop else 0.0
        floor = h * 0.3 + 2.1 * S
        for sg, (kn, an, hp) in ((L, (LKNEE, LANK, LHIP)), (R, (RKNEE, RANK, RHIP))):
            k[an] = np.array([cx + sg * 0.28 * S, floor])
            k[kn] = np.array([cx + sg * (0.27 + knee_dx) * S, floor - 0.55 * S])
        kp = np.array([[*k[i], 0.9] for i in range(17)], np.float32)
        x1, y1 = kp[:, :2].min(0) - 0.15 * S
        x2, y2 = kp[:, :2].max(0) + 0.15 * S
        return [(float(x1), float(y1), float(x2), float(y2), 0.9, 0, kp)]
