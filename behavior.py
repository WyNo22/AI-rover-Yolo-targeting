"""
behavior.py – Couche « comportement » : transforme les gestes reconnus en états et en réactions.

La vision dit ce qu'elle voit (gestures.py), le comportement décide quoi faire.
Aujourd'hui la seule sortie est la tourelle (protocole "ex ey bh") : les réactions sont donc des
petites animations de la tête. Sur LEO-S, les mêmes événements piloteront la marche (voir PROJET.md).

États (affichés dans la vidéo, sur /etat, et plus tard sur l'écran e-ink) :
  SUIVI    suit le propriétaire (la cible verrouillée), ou attend qu'il y en ait un
  ECOUTE   propriétaire reconnu (main levée), accepte un ordre pendant ECOUTE_S secondes
  ARRET    STOP reçu : ne bouge plus, jusqu'à une main levée ou le bouton « Reprendre »
  REPOS    bras croisés : lâche la cible, ne suit plus personne jusqu'à une main levée

Règles : STOP et COUCOU marchent pour tout le monde ; ECOUTE désigne le propriétaire ;
les ordres (POINTE, VIENS, SAUTE, REPOS) ne sont acceptés que du propriétaire en état ECOUTE.
"""
import threading
import time
from collections import deque

ECOUTE_S = 3.0        # fenêtre pour donner un ordre après la main levée
ANIM_E = 140          # amplitude des animations (repère d'erreur 640x480)

# Animations de la tourelle : suites de (erreur pan, erreur tilt, durée en s)
NOD = [(0, -ANIM_E, 0.15), (0, ANIM_E, 0.15), (0, -ANIM_E, 0.15), (0, ANIM_E, 0.15)]    # oui
SHAKE = [(-ANIM_E, 0, 0.15), (ANIM_E, 0, 0.3), (-ANIM_E, 0, 0.15)]                       # non
WIGGLE = [(-ANIM_E, 0, 0.12), (ANIM_E, 0, 0.24), (-ANIM_E, 0, 0.24), (ANIM_E, 0, 0.12)]  # salut
HOP = [(0, -2 * ANIM_E, 0.25), (0, 2 * ANIM_E, 0.25), (0, 0, 0.2)]                         # « saute »

TEXTES = {
    "SUIVI": "Je te suis",
    "ATTENTE": "Je cherche quelqu'un",
    "ECOUTE": "Je t'écoute",
    "ARRET": "STOP",
    "REPOS": "Repos",
}


class Behavior:
    def __init__(self, state, on_change=None):
        self.state = state                 # TargetState de tracker_v2 (cible = propriétaire)
        self.lock = threading.Lock()
        self.mode = "SUIVI"
        self.ecoute_until = 0.0
        self.anim, self.anim_t0, self.action = [], 0.0, ""
        self.log = deque(maxlen=6)         # derniers événements (affichés dans la vidéo)
        self.on_change = on_change         # rappel (texte d'état) : écran e-ink plus tard
        self._last_etat = None

    # ── état lisible ──────────────────────────────────────────────────────────
    def etat(self, now=None):
        now = now or time.monotonic()
        with self.lock:
            mode = self.mode
            if mode == "ECOUTE" and now > self.ecoute_until:
                mode = self.mode = "SUIVI"
            if mode == "SUIVI" and self.state.target_id is None:
                mode = "ATTENTE"
            return {"etat": mode, "texte": TEXTES[mode], "action": self.action if self.anim else "",
                    "proprio": self.state.target_id,
                    "ecoute_restant": round(max(0.0, self.ecoute_until - now), 1) if mode == "ECOUTE" else 0,
                    "evenements": list(self.log)}

    def _note(self, txt):
        self.log.append({"t": round(time.time(), 1), "msg": txt})
        print(f"[GESTE] {txt}")

    def _play(self, anim, action):
        self.anim, self.anim_t0, self.action = list(anim), time.monotonic(), action

    # ── événements ────────────────────────────────────────────────────────────
    def on_events(self, events):
        if not events:
            return
        now = time.monotonic()
        with self.lock:
            if self.mode == "ECOUTE" and now > self.ecoute_until:
                self.mode = "SUIVI"
            for name, tid, info in events:
                owner = tid == self.state.target_id
                if name == "STOP":
                    self.mode = "ARRET"
                    self.anim = []
                    self._note(f"STOP par #{tid}")
                elif name == "ECOUTE":
                    self.state.lock_on(tid)
                    self.state.paused = False
                    self.mode, self.ecoute_until = "ECOUTE", now + ECOUTE_S
                    self._play(NOD, "oui")
                    self._note(f"#{tid} : je t'écoute")
                elif name == "COUCOU":
                    if self.mode != "ARRET":
                        self._play(WIGGLE, "salut")
                    self._note(f"Coucou de #{tid}")
                elif self.mode == "ARRET":
                    continue
                elif not (owner and self.mode == "ECOUTE"):
                    self._note(f"{name} de #{tid} ignoré (lever la main d'abord)")
                elif name == "POINTE":
                    vx, vy = info
                    self._play([(int(vx * 2 * ANIM_E), int(vy * ANIM_E), 0.8), (0, 0, 2.0),
                                (int(-vx * 2 * ANIM_E), int(-vy * ANIM_E), 0.8)], "regarde")
                    self.mode = "SUIVI"
                    self._note(f"Je regarde à {'gauche' if vx < 0 else 'droite'}")
                elif name == "VIENS":
                    self.state.drive = True
                    self._play(NOD, "j'arrive")
                    self.mode = "SUIVI"
                    self._note("Je viens (rover : avance vers toi)")
                elif name == "SAUTE":
                    self._play(HOP, "saute")
                    self.mode = "SUIVI"
                    self._note("Saut ! (bipède : seulement si l'obstacle le permet)")
                elif name == "REPOS":
                    self.state.release()
                    self.state.paused = True
                    self.state.drive = False
                    self.mode = "REPOS"
                    self._note("Repos")
        self._changed()

    def resume(self):
        """Bouton « Reprendre » : sort de ARRET / REPOS."""
        with self.lock:
            self.mode = "SUIVI"
            self.state.paused = False
            self._note("Reprise")
        self._changed()

    def _changed(self):
        e = self.etat()
        key = (e["etat"], e["proprio"])
        if key != self._last_etat:
            self._last_etat = key
            print(f"[ETAT] {e['etat']} – {e['texte']}" + (f" (#{e['proprio']})" if e["proprio"] else ""))
            if self.on_change:
                self.on_change(e)

    # ── sortie tourelle ───────────────────────────────────────────────────────
    def override(self, now):
        """Consigne imposée à la tourelle, ou None pour le suivi normal de la cible."""
        with self.lock:
            if self.anim:
                t = now - self.anim_t0
                for ex, ey, d in self.anim:
                    if t < d:
                        return ex, ey, 0
                    t -= d
                self.anim = []
            if self.mode in ("ARRET", "REPOS"):
                return 0, 0, 0
            return None
