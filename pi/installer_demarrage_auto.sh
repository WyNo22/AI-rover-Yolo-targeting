#!/usr/bin/env bash
# installer_demarrage_auto.sh
# Lance la tourelle automatiquement à chaque démarrage du Pi (service systemd « tourelle »).
# Si la DJI n'est pas encore en mode webcam, le service réessaie toutes les 5 s :
# il suffit de la brancher quand on veut. Le bouton « Quitter » de la page web relance le programme.
#
# Usage :  bash pi/installer_demarrage_auto.sh             installe et démarre
#          bash pi/installer_demarrage_auto.sh --remove    désinstalle
#
# Ensuite :
#   journalctl -u tourelle -f              voir ce qui se passe (Ctrl+C pour quitter l'affichage)
#   sudo systemctl stop tourelle           arrêter (avant de lancer le script à la main : le Hailo
#                                          ne peut servir qu'à un programme à la fois)
#   sudo systemctl start tourelle          redémarrer
#   sudo systemctl disable tourelle        ne plus lancer au démarrage
#   nano pi/tourelle.conf                  options (ex. --auto), puis : sudo systemctl restart tourelle

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNIT=/etc/systemd/system/tourelle.service

if [ "${1:-}" = "--remove" ]; then
  sudo systemctl disable --now tourelle 2>/dev/null
  sudo rm -f "$UNIT" && sudo systemctl daemon-reload
  echo "Démarrage automatique supprimé."
  exit 0
fi

# Vérifie une fois que tout est installé (le service ne peut pas taper le mot de passe sudo)
bash "$REPO/pi/lancer_tourelle_pi.sh" --deps-only || exit 1

CONF="$REPO/pi/tourelle.conf"
[ -f "$CONF" ] || cat > "$CONF" <<'EOF'
# Options passées à tracker_v2.py par le service « tourelle ».
# Exemples : --auto   --size 640x480   --serial none   --conf 0.5
# Après modification : sudo systemctl restart tourelle
ARGS=""
EOF

sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=Tourelle YOLO (Hailo) – interface sur le port 8082
After=network.target
StartLimitIntervalSec=0

[Service]
User=$USER
WorkingDirectory=$REPO
EnvironmentFile=-$CONF
Environment=PYTHONUNBUFFERED=1
ExecStart=/bin/bash $REPO/pi/lancer_tourelle_pi.sh \$ARGS
Restart=always
RestartSec=5
# Ctrl+C plutôt que kill : arrêt propre, consigne 0 0 0 envoyée à l'Arduino
KillSignal=SIGINT
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tourelle
sleep 3
systemctl --no-pager --lines=0 status tourelle | head -3
echo
echo "Installé. Au prochain démarrage, la tourelle se lance seule : http://$(hostname -I | awk '{print $1}'):8082"
echo "Suivre les messages : journalctl -u tourelle -f"
