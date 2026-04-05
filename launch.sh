#!/data/data/com.termux/files/usr/bin/bash
# launch.sh – Auto-detect Arduino + USB Camera (DJI via Camera2)
# Usage : bash ~/launch.sh
# Pré-requis : app USB Camera lancée avec la DJI sélectionnée + serveur IP activé

set -e

# Cleanup anciens processus
pkill -f arduino_server.py 2>/dev/null || true
pkill -f tracker_rover.py 2>/dev/null || true
sleep 1

echo "=== Scan des périphériques USB (Arduino) ==="

# Récupère la liste JSON des devices
DEVS=$(termux-usb -l 2>/dev/null | tr -d '[]" \n' | tr ',' '\n')

if [ -z "$DEVS" ]; then
    echo "Aucun périphérique USB détecté. Vérifier le hub OTG."
    exit 1
fi

ARDUINO_DEV=""

for dev in $DEVS; do
    echo -n "  $dev → "
    RESULT=$(termux-usb -r -e "python3 /data/data/com.termux/files/home/usb_id.py" "$dev" 2>/dev/null || echo "ERREUR")

    if echo "$RESULT" | grep -q "ARDUINO"; then
        echo "ARDUINO"
        ARDUINO_DEV="$dev"
    elif echo "$RESULT" | grep -q "05E3"; then
        echo "HUB (ignoré)"
    else
        echo "(ignoré) $RESULT"
    fi
done

echo ""

if [ -z "$ARDUINO_DEV" ]; then
    echo "ERREUR : Arduino non trouvé !"
    exit 1
fi
echo "Arduino : $ARDUINO_DEV"

# Vérif USB Camera (DJI via Camera2)
echo ""
echo "=== Vérification USB Camera (DJI) ==="
if curl -s --max-time 2 -u admin:admin http://127.0.0.1:8081/ -o /dev/null; then
    echo "USB Camera OK ✓ (port 8081)"
else
    echo "ERREUR : USB Camera non détectée sur :8081"
    echo "→ Lancer l'app USB Camera avec la DJI sélectionnée + serveur IP activé"
    exit 1
fi

echo ""
echo "=== Lancement Arduino Bridge (TCP 127.0.0.1:9999) ==="
termux-usb -e "python3 /data/data/com.termux/files/home/arduino_server.py" "$ARDUINO_DEV" &
ARD_PID=$!
sleep 3

echo "=== Lancement Tracker Rover (USB Camera + YOLO) ==="
python3 /data/data/com.termux/files/home/tracker_rover.py

# Cleanup
kill $ARD_PID 2>/dev/null
echo "Terminé."
