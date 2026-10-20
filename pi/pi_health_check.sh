#!/usr/bin/env bash
# pi_health_check.sh
# Bilan de santé d'un Raspberry Pi 5 + AI HAT+ (Hailo) reçu d'occasion.
# Vérifie : modèle, RAM, OS, alimentation/throttling, température, lien PCIe,
# identité exacte de la puce Hailo (HAILO8 = 26 TOPS, HAILO8L = 13 TOPS),
# puis benchmark réel du NPU sur les modèles .hef installés, et un court test de charge CPU.
#
# Usage :  bash pi_health_check.sh            (rapport complet dans ~/pi_health_report.txt)
#          bash pi_health_check.sh --quick    (sans benchmark ni test de charge)

QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1
REPORT="$HOME/pi_health_report.txt"
PASS=0; WARN=0; FAIL=0

exec > >(tee "$REPORT") 2>&1

ok()   { echo "  [OK]    $*"; PASS=$((PASS+1)); }
warn() { echo "  [WARN]  $*"; WARN=$((WARN+1)); }
bad()  { echo "  [FAIL]  $*"; FAIL=$((FAIL+1)); }
info() { echo "          $*"; }
title(){ echo; echo "== $* =="; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "Bilan Pi 5 + AI HAT+ — $(date '+%Y-%m-%d %H:%M')"

# ── 1. Carte ──────────────────────────────────────────────────────────────────
title "1. Carte"
MODEL=$( { tr -d '\0' < /proc/device-tree/model; } 2>/dev/null )
info "Modèle : ${MODEL:-inconnu}"
case "$MODEL" in
  *"Raspberry Pi 5"*) ok "C'est bien un Raspberry Pi 5" ;;
  *"Raspberry Pi 4"*) bad "C'est un Pi 4, pas un Pi 5 : non conforme à l'annonce" ;;
  *)                  bad "Modèle inattendu" ;;
esac
REV=$(awk '/^Revision/ {print $3}' /proc/cpuinfo)
info "Révision : ${REV:-?}   Série : $(awk '/^Serial/ {print $3}' /proc/cpuinfo)"

MEM_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
MEM_GB=$(awk -v k="$MEM_KB" 'BEGIN{printf "%.1f", k/1024/1024}')
info "RAM vue par l'OS : ${MEM_GB} Go"
if   [ "$MEM_KB" -gt 3500000 ] && [ "$MEM_KB" -lt 4300000 ]; then ok "4 Go, conforme"
elif [ "$MEM_KB" -ge 4300000 ]; then ok "Plus de 4 Go (${MEM_GB} Go)"
else bad "Moins de 4 Go : non conforme à l'annonce (4 Go)"; fi

# ── 2. Système ────────────────────────────────────────────────────────────────
title "2. Système"
info "OS : $(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-?}")"
info "Noyau : $(uname -r)   Archi : $(uname -m)"
[ "$(uname -m)" = "aarch64" ] && ok "OS 64 bits" || warn "OS non 64 bits : installer Raspberry Pi OS 64 bits (Bookworm ou plus récent)"
ROOT_DEV=$(findmnt -n -o SOURCE /)
info "Disque système : $ROOT_DEV   libre : $(df -h / | awk 'NR==2{print $4}')"

# ── 3. Alimentation et température ───────────────────────────────────────────
title "3. Alimentation et température"
if have vcgencmd; then
  T=$(vcgencmd measure_temp | grep -o '[0-9.]*')
  info "Température au repos : ${T} °C"
  awk -v t="$T" 'BEGIN{exit !(t<60)}' && ok "Température correcte au repos" || warn "Chaud au repos (${T} °C) : ventilateur absent ou mal monté ?"
  THR=$(vcgencmd get_throttled | cut -d= -f2)
  info "get_throttled = $THR"
  if [ "$THR" = "0x0" ]; then ok "Aucune sous-tension ni bridage depuis le démarrage"
  else
    V=$((THR))
    (( V & 0x1 ))     && bad "Sous-tension EN COURS : alimentation insuffisante (5 V / 5 A recommandé)"
    (( V & 0x10000 )) && warn "Sous-tension détectée depuis le démarrage"
    (( V & 0x4 ))     && warn "Bridage (throttling) en cours"
    (( V & 0x40000 )) && warn "Bridage survenu depuis le démarrage"
    (( V & 0x8 ))     && warn "Limite thermique atteinte"
  fi
  info "Tension cœur : $(vcgencmd measure_volts core | cut -d= -f2)"
  if vcgencmd pmic_read_adc EXT5V_V >/dev/null 2>&1; then
    info "Entrée 5 V mesurée : $(vcgencmd pmic_read_adc EXT5V_V | awk -F= '{print $2}')"
  fi
else
  warn "vcgencmd absent : impossible de lire température et alimentation"
fi
FAN=$(cat /sys/class/thermal/cooling_device*/type 2>/dev/null | grep -c pwm-fan)
[ "$FAN" -gt 0 ] && ok "Ventilateur (Active Cooler) détecté" || warn "Aucun ventilateur détecté : indispensable sous charge NPU + CPU"

# ── 4. PCIe et AI HAT+ ───────────────────────────────────────────────────────
title "4. Lien PCIe et AI HAT+"
if have lspci; then
  HL=$(lspci -nn | grep -i hailo)
  if [ -n "$HL" ]; then
    ok "Accélérateur Hailo vu sur le bus PCIe"
    info "$HL"
    SLOT=$(echo "$HL" | awk '{print $1}')
    LNK=$(sudo lspci -vv -s "$SLOT" 2>/dev/null | grep -m1 'LnkSta:')
    info "Lien : ${LNK:-illisible (relancer avec sudo)}"
    case "$LNK" in
      *"8GT/s"*) ok "PCIe Gen 3 actif (débit maximal)" ;;
      *"5GT/s"*) warn "PCIe Gen 2 seulement : ajouter 'dtparam=pciex1_gen=3' dans /boot/firmware/config.txt puis redémarrer (jusqu'à ~2x de FPS en plus)" ;;
    esac
  else
    bad "Aucun périphérique Hailo sur le PCIe : nappe mal enfichée, HAT défectueux ou PCIe désactivé"
  fi
else
  warn "lspci absent (sudo apt install pciutils)"
fi

# ── 5. Identité de la puce Hailo ─────────────────────────────────────────────
title "5. Identité de la puce Hailo"
if have hailortcli; then
  ID=$(hailortcli fw-control identify 2>&1)
  echo "$ID" | sed 's/^/          /'
  ARCH=$(echo "$ID" | grep -i 'Device Architecture' | awk -F: '{gsub(/ /,"",$2); print $2}')
  case "$ARCH" in
    HAILO8)  ok "HAILO8 : c'est bien la version 26 TOPS" ;;
    HAILO8L) bad "HAILO8L : c'est la version 13 TOPS, non conforme à l'annonce (26 TOPS)" ;;
    "")      bad "Puce non identifiée : pilote non chargé ? (sudo apt install hailo-all puis redémarrer)" ;;
    *)       warn "Architecture inattendue : $ARCH" ;;
  esac
  DRV=$(lsmod | grep -c hailo_pci)
  [ "$DRV" -gt 0 ] && ok "Pilote hailo_pci chargé" || warn "Pilote hailo_pci non chargé"
  info "HailoRT : $(hailortcli --version 2>/dev/null | head -1)"
else
  bad "hailortcli absent : sudo apt update && sudo apt install hailo-all, puis redémarrer"
  ARCH=""
fi

# ── 6. Benchmark NPU ─────────────────────────────────────────────────────────
if [ "$QUICK" -eq 0 ] && have hailortcli && [ -n "$ARCH" ]; then
  title "6. Benchmark du NPU (débit brut de la puce)"
  SUFFIX=$( [ "$ARCH" = "HAILO8L" ] && echo h8l || echo h8 )
  mapfile -t HEFS < <(find /usr/share/hailo-models "$HOME" -maxdepth 3 -name "*.hef" 2>/dev/null \
                      | grep -iE "yolov8|yolov6|yolov5|yolox" | grep -iE "_${SUFFIX}(_|\.)" | head -3)
  [ ${#HEFS[@]} -eq 0 ] && mapfile -t HEFS < <(find /usr/share/hailo-models "$HOME" -maxdepth 3 -name "*.hef" 2>/dev/null | head -3)
  if [ ${#HEFS[@]} -eq 0 ]; then
    warn "Aucun modèle .hef trouvé (installés par 'hailo-all' dans /usr/share/hailo-models)"
  else
    for H in "${HEFS[@]}"; do
      info "Modèle : $H"
      OUT=$(timeout 120 hailortcli benchmark --time-to-run 15 "$H" 2>&1)
      echo "$OUT" | grep -iE "fps|latency|power" | sed 's/^/          /'
      if echo "$OUT" | grep -qi "fps"; then ok "Benchmark terminé sans erreur"; else bad "Benchmark en échec : $(echo "$OUT" | tail -2 | tr '\n' ' ')"; fi
      [ -n "$(command -v vcgencmd)" ] && info "Température après benchmark : $(vcgencmd measure_temp | cut -d= -f2)"
    done
    info "Repère : sur Pi 5 en Gen 3, un HAILO8 donne nettement plus de FPS qu'un HAILO8L sur le même modèle."
  fi
fi

# ── 7. Test de charge CPU (60 s) ─────────────────────────────────────────────
if [ "$QUICK" -eq 0 ]; then
  title "7. Test de charge CPU, 60 s sur 4 cœurs"
  if have vcgencmd; then
    for i in 1 2 3 4; do ( end=$((SECONDS+60)); while [ $SECONDS -lt $end ]; do :; done ) & done
    MAXT=0
    for s in $(seq 1 12); do
      sleep 5
      T=$(vcgencmd measure_temp | grep -o '[0-9.]*')
      MAXT=$(awk -v a="$MAXT" -v b="$T" 'BEGIN{print (b>a)?b:a}')
    done
    wait
    info "Température maximale sous charge : ${MAXT} °C"
    awk -v t="$MAXT" 'BEGIN{exit !(t<80)}' && ok "Refroidissement suffisant (< 80 °C)" || warn "Plus de 80 °C : le Pi va brider sous charge, vérifier ventilateur et pâte thermique"
    THR=$(vcgencmd get_throttled | cut -d= -f2)
    [ "$THR" = "0x0" ] && ok "Pas de sous-tension ni bridage pendant la charge" || warn "get_throttled = $THR après la charge : alimentation ou refroidissement limites"
  fi
fi

# ── Bilan ────────────────────────────────────────────────────────────────────
title "Bilan"
echo "  OK : $PASS    Avertissements : $WARN    Échecs : $FAIL"
if [ "$FAIL" -eq 0 ]; then echo "  → Matériel conforme et fonctionnel."
else echo "  → Problème détecté : voir les lignes [FAIL]. En cas de non-conformité, ouvrir une réclamation eBay avec ce rapport."; fi
echo "  Rapport enregistré dans : $REPORT"
