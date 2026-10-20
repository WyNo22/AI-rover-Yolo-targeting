#!/usr/bin/env bash
# lancer_tourelle_pi.sh
# Tourelle sur Raspberry Pi 5 + AI HAT+ : DJI en USB → YOLO sur Hailo → Arduino en USB.
# Interface sur le téléphone : http://<ip-du-pi>:8082
#
# Usage :  bash pi/lancer_tourelle_pi.sh                    (tout en automatique)
#          bash pi/lancer_tourelle_pi.sh --size 1920x1080   (options passées à tracker_v2.py)
#          CAM=/dev/video8 bash pi/lancer_tourelle_pi.sh    (forcer la caméra)

cd "$(dirname "$0")/.." || exit 1

# Dépendances : paquets système, pour rester sur le Python où hailo_platform est installé.
missing=()
command -v ffmpeg    >/dev/null || missing+=(ffmpeg)
command -v v4l2-ctl  >/dev/null || missing+=(v4l-utils)
python3 -c "import cv2"    2>/dev/null || missing+=(python3-opencv)
python3 -c "import serial" 2>/dev/null || missing+=(python3-serial)
if [ ${#missing[@]} -gt 0 ]; then
  echo "Installation : ${missing[*]}"
  sudo apt-get update -qq && sudo apt-get install -y "${missing[@]}" || exit 1
fi
python3 -c "import hailo_platform" 2>/dev/null \
  || { echo "hailo_platform absent : sudo apt install hailo-all, puis redémarrer"; exit 1; }

# Caméra USB : premier /dev/videoN d'un périphérique USB qui sait sortir du MJPEG.
# (sur Pi 5, les /dev/video0..7 sont souvent ceux du processeur d'image interne, pas la DJI)
if [ -z "$CAM" ]; then
  for d in $(v4l2-ctl --list-devices 2>/dev/null | awk '/usb/{f=1;next} /^[^ \t]/{f=0} f && /\/dev\/video/{print $1}'); do
    if v4l2-ctl -d "$d" --list-formats 2>/dev/null | grep -q MJPG; then CAM=$d; break; fi
  done
fi
if [ -z "$CAM" ]; then
  echo "Aucune caméra USB MJPEG trouvée. DJI en mode webcam branchée ? Liste :"
  v4l2-ctl --list-devices
  exit 1
fi
echo "Caméra : $CAM"
v4l2-ctl -d "$CAM" --list-formats-ext 2>/dev/null | grep -A1 MJPG | head -4

IP=$(hostname -I | awk '{print $1}')
echo
echo "Interface : http://$IP:8082   (clic sur une personne = cible, Ctrl+C pour arrêter)"
echo
exec python3 tracker_v2.py --source "$CAM" --size 1280x720 "$@"
