# Étude technique — calculateur embarqué pour le rover YOLO

*Recherche effectuée le 18/10/2026. Les prix viennent de résultats de recherche (Geizhals, BerryBase, Reichelt, buyzero, Kleinanzeigen, Sixfab EU) : les pages marchandes elles-mêmes n'ont pas pu être ouvertes depuis l'environnement de recherche. Les annonces eBay/Kleinanzeigen citées dans le contexte n'ont donc **pas** pu être vérifiées. Tous les prix sont à reconfirmer au moment de l'achat.*

---

## 0. Conclusion en une ligne

**Raspberry Pi 5 2 Go + AI HAT+ (Hailo-8L 13 TOPS ou Hailo-8 26 TOPS selon le prix), une seule carte, l'Arduino Nano conservé, le flux MJPEG de la caméra relayé sans ré-encodage et les détections superposées dans le navigateur.** Le Jetson Orin Nano serait le meilleur choix technique, mais la crise de la RAM de 2026 l'a sorti du budget (300 à 360 € d'occasion, 349 à 590 € neuf).

---

## 1. Les cinq métriques à ne pas confondre

| Métrique | Ce qu'elle mesure | Ordre de grandeur visé | Ce qui la limite |
|---|---|---|---|
| **FPS du réseau seul** | Débit du NPU/GPU sur des tenseurs déjà prêts (souvent en batch 8) | 60 à 400 | Le seul accélérateur. **C'est le chiffre des fiches techniques.** |
| **FPS du pipeline de détection** | Images caméra réellement décodées, inférées, post-traitées, suivies | **30 = le maximum de la caméra** | Caméra, décodage JPEG, CPU Python, NMS |
| **FPS du flux vidéo transmis** | Images affichées chez l'opérateur | 30 (1080p) | Wi-Fi, encodage. **Doit être indépendant de YOLO.** |
| **Fréquence des commandes Arduino** | Consignes envoyées aux servos et moteurs | 50 Hz | Inutile d'aller plus vite : un servo standard ne lit sa consigne PWM qu'à 50 Hz |
| **Latence de bout en bout** | Mouvement réel → commande servo | < 120 ms avec la DJI | Surtout la **latence interne de la caméra** |

**Point clé :** le pipeline ne peut pas détecter plus d'images que la caméra n'en produit. Si la DJI Osmo Action 4 en mode webcam fournit du 1080p30, ce qui est probable mais non confirmé (aucune source ne documente son mode UVC), alors **30 FPS de détection est le plafond**. Viser 40 FPS suppose une caméra à 60 FPS. Un NPU capable de 200 FPS n'apporte alors rien de plus en débit : il ne fait que réduire la latence par image.

### Budget de latence réaliste (Pi 5 + Hailo, caméra USB MJPEG 1080p30)

| Étape | Estimation |
|---|---|
| Latence interne de la caméra (capteur, ISP, encodage MJPEG, USB) | **50 à 150 ms (inconnue, à mesurer)** |
| Attente de l'image suivante (moyenne à 30 FPS) | ~17 ms |
| Décodage JPEG en résolution réduite (voir §5) | ~3 à 6 ms |
| Letterbox et conversion en 640×640 | ~2 ms |
| Inférence Hailo-8L / Hailo-8 (batch 1) | ~16 ms / ~7 ms |
| Post-traitement (NMS sur la puce), tracker, PID | ~2 ms |
| Envoi série (≈10 octets à 115200 bauds) | ~1 ms |
| Prise en compte par le servo (période PWM de 50 Hz) | 0 à 20 ms |
| **Total, sans compter la caméra** | **≈ 40 à 60 ms** |

Conclusion : une fois le pipeline corrigé, **c'est la caméra, et non l'accélérateur, qui domine la latence**. Passer du Hailo-8L au Hailo-8 ne fait gagner qu'environ 9 ms sur un total d'environ 100 à 200 ms.

---

## 2. Comparatif des plateformes

> Les benchmarks ne sont **pas directement comparables** : batch 1 ou 8, INT8 ou FP16, avec ou sans pré- et post-traitement. Les chiffres qui figurent dans la même colonne viennent de méthodes différentes ; la colonne « Fiabilité » le signale.

| # | Plateforme | YOLOv8n 640, réseau seul | Pipeline caméra réel (estimation) | Puissance | Prix total livré en Allemagne | Portage du modèle | Fiabilité des chiffres |
|---|---|---|---|---|---|---|---|
| 1 | **Pi 5 + Hailo-8L (13 TOPS)** | **61,9 FPS mesurés sur Pi 5, batch 1** ([forum Hailo](https://community.hailo.ai/t/yolov8n-real-performance-didnt-expected-from-hailo-model-zoo-documentation/18904)) ; 182 FPS batch 1 dans le Model Zoo (débit brut de la puce) | **30 FPS** (plafonné par la caméra) | Pi 5 ~5 à 8 W + HAT ~1,5 à 2 W | **≈ 165 à 175 €** (2 Go, neuf) | Facile : `.hef` précompilé (COCO) | Moyenne à bonne |
| 2 | **Pi 5 + Hailo-8 (26 TOPS)** | **~144 FPS en C++ sans pré/post** ([forum Hailo](https://community.hailo.ai/t/the-performance-on-the-raspberry-pi-5-with-the-hailo-8-chip-seems-not-good-as-he-official-results/17473)) | 30 FPS, latence d'inférence ≈ 7 ms ; permet YOLOv8s à 30 FPS | HAT 2,5 W typ., 8,65 W max ([Waveshare](https://www.waveshare.com/hailo-8-acce-a.htm)) | **≈ 215 €** neuf ; **≈ 175 à 185 €** via l'annonce eBay si elle est à ≤160 € | Facile (idem) | Moyenne |
| 3 | **Orange Pi 5 (RK3588S, NPU 6 TOPS)** | ~60 FPS INT8 sur 1 cœur NPU ([rknn_model_zoo](https://github.com/airockchip/rknn_model_zoo)) ; 80 à 96 FPS sur 3 cœurs (non confirmé) | 25 à 30 FPS ; post-traitement DFL en Python ≈ 30 à 40 ms ([forum Radxa](https://forum.radxa.com/t/use-yolov8-in-rk3588-npu/15838?page=7)), il faut du C++ | ~6 à 10 W | **≈ 200 à 215 €** neuf (4 Go, Amazon.de) ; ~160 € d'occasion | Moyen à difficile (RKNN, post-traitement) | Faible à moyenne |
| 4a | **Jetson Orin Nano Super 8 Go** | 79 FPS en FP32 et 142 FPS en FP16, mesurés (TensorRT, Orin Nano non Super, [forum NVIDIA](https://forums.developer.nvidia.com/t/benchmarck-int8-similar-to-fp32-on-yolov8-from-ultralytics/276023)) | 30 FPS, décodage JPEG matériel | 7 à 25 W | **≈ 300 à 360 € d'occasion**, 349 à 590 € neuf ([Geizhals](https://geizhals.de/nvidia-jetson-orin-nano-super-developer-kit-a3524658.html)) | Très facile (`yolo export format=engine`) | Bonne |
| 4b | Jetson Nano (2019) | ~19 FPS ([Qengineering](https://github.com/Qengineering/YoloV8-TensorRT-Jetson_Nano)) | < 15 FPS | 5 à 10 W | 60 à 100 € d'occasion | Pénible (JetPack 4, Ubuntu 18.04, Python 3.6) | Bonne |
| 4c | Jetson Xavier NX | ~60 FPS pour YOLOv5n (pas de chiffre YOLOv8n trouvé) | ~30 FPS | 10 à 20 W | prix d'occasion non trouvé | Correct, mais **JetPack 5 en fin de vie au T3 2026** ([NVIDIA](https://forums.developer.nvidia.com/t/jetson-nano-and-jetson-xavier-announcements/232522)) | Faible |
| 5 | **Pi 5 + Sixfab AI HAT+ DEEPX DX-M1M (25 TOPS)** | Le constructeur annonce **30 à 35 FPS pour YOLOv8n 640 sur Pi 5** ([Sixfab](https://eu.sixfab.com/products/ai-hat-plus-raspberry-pi-5)) ; [Sixfab](https://sixfab.com/blog/raspberry-pi-5-ai-hat-benchmark-deepx-vs-hailo/) le dit 156 % plus rapide que le Hailo-8 sur YOLOv8l | ~30 FPS | ~3 W annoncés | **≈ 185 à 190 €** (HAT 90 € + Pi 5 2 Go) | Moyen à difficile (DX-COM / DX-RT, petite communauté) | Faible (chiffres du vendeur uniquement) |
| 6 | Mini-PC Intel N100 (OpenVINO, iGPU) | 4 à 7 FPS sur CPU ; YOLOv10n ~12 FPS en FP16 sur iGPU, 18 à 19 FPS en INT8 ([LattePanda](https://lattepanda.com/blog-323181.html)) | 10 à 18 FPS | 10 à 25 W | 100 à 150 € d'occasion | Facile | Moyenne |
| 7 | **Calcul sur l'IdeaPad (Wi-Fi)** | Dépend du GPU (**modèle inconnu**) ; une RTX d'entrée de gamme dépasse 200 FPS | 30 FPS, avec **+20 à 60 ms de Wi-Fi et de la gigue** | 0 W côté rover | **0 €** | Aucun | — |

### Lecture critique

- **Hailo-8L contre Hailo-8.** Avec une caméra à 30 FPS, **les deux tiennent 30 FPS de détection**. Le Hailo-8 apporte environ 9 ms de latence en moins et la marge pour passer à **YOLOv8s** (meilleure détection des cibles petites ou lointaines) en restant à 30 FPS. C'est utile, mais cela ne double pas les performances du rover. Il vaut le surcoût d'environ 45 € en neuf, ou s'il est obtenu au prix du 8L (annonce d'occasion).
- **AI HAT+ 2 (Hailo-10H, 40 TOPS, 208 €)** : il cible surtout les LLM et sort du budget. Je l'écarte.
- **RK3588** : sur le papier, c'est intéressant (8 cœurs CPU, **décodage MJPEG matériel**). Mais en 2026, l'Orange Pi 5 4 Go coûte autant qu'un Pi 5 avec Hailo-8L, son NPU est plus lent et sa chaîne logicielle demande plus de travail. Il ne l'emporte que s'il est trouvé d'occasion à moins de 120 € environ.
- **Jetson Orin Nano Super** : c'est la meilleure plateforme pour ce projet (CUDA, TensorRT en une commande, NVJPG matériel, OpenCV et GStreamer matures). Mais **le moins cher repéré coûte 305 € d'occasion**, hors budget même dans le palier à 250 €. À surveiller si un kit passe sous 250 €.
- **DEEPX** : c'est la seule alternative crédible à Hailo sur Pi 5 (25 TOPS pour 90 €). Mais les seuls chiffres disponibles viennent du vendeur, et le kit de développement et la communauté sont jeunes. Cela représente un risque logiciel réel pour un gain nul sur ton cas, puisque la caméra est plafonnée à 30 FPS.
- **N100** : il est éliminé, à 10 à 18 FPS sans accélérateur.
- **Jetson Nano 2019 / Xavier NX** : éliminés (plateforme trop ancienne, fin de vie de JetPack).

---

## 3. Faut-il plusieurs cartes ?

**Non.** Voici le partage des tâches recommandé :

| Unité | Tâches |
|---|---|
| **NPU Hailo** | Inférence YOLO (NMS inclus dans le `.hef`) |
| **CPU du Pi 5 (4 cœurs A76)** | Capture USB, relais MJPEG brut, décodage JPEG à résolution réduite, letterbox, tracker (ByteTrack/Kalman), PID, serveur web/WebSocket, liaison série |
| **Arduino Nano (conservé)** | PWM servos et moteurs, lecture du récepteur RC FS-iA6B, **watchdog** (arrêt si plus de consigne depuis 200 ms), **priorité au mode manuel RC** |
| **Écran opérateur** | Navigateur sur **le Galaxy A50 réutilisé** ou sur le PC : aucune interface graphique ne tourne sur le Pi |

Une deuxième carte (une pour la vidéo, une pour le NPU) ne supprime aucun goulot d'étranglement. Le relais MJPEG ne coûte presque rien en CPU, et le NPU décharge déjà le CPU de l'inférence. Elle ajouterait des coûts, du poids, de la consommation et un lien réseau interne.

---

## 4. Liste d'achats

> Prix relevés dans les résultats de recherche du 18/10/2026. **Les prix de la RAM ont augmenté trois fois en 2026** ([heise](https://www.heise.de/en/news/Up-to-150-Raspi-prices-rise-again-11243959.html), [PCGH](https://www.pcgameshardware.de/Raspberry-Pi-Hardware-257637/News/raspberry-pi-4-5-2-gb-ram-preiserhoehung-1555550/)) : vérifier avant l'achat.

### Configuration A — « sous 150 € » (approchée au plus près)
| Article | Prix |
|---|---|
| Raspberry Pi 5 **2 Go** (officiel 77,50 $, ≈ 77 à 85 € en Allemagne) | ~80 € |
| AI HAT+ 13 TOPS (Hailo-8L) — [buyzero.de](https://buyzero.de/collections/hailo) « ab 69,75 € », ou BerryBase sur eBay 78,90 € + 4,95 € de port | ~70 à 84 € |
| Raspberry Pi Active Cooler | ~6 € |
| microSD A2 32 Go (ou réutilisation d'une carte existante) | ~8 € |
| **Total** | **≈ 165 €** neuf ; **≈ 150 €** en réutilisant une microSD et avec le prix buyzero |

Sous 150 € strictement, il faut passer par l'occasion (lot Pi 5 + AI HAT 13 TOPS sur Kleinanzeigen à 130 à 140 €). Les gains et limites sont détaillés au §6.

### Configuration B — « sous 200 € » ⭐ recommandée
| Article | Prix |
|---|---|
| **Option B1 (occasion)** : lot eBay Pi 5 + AI HAT+ **26 TOPS**, *si ≤ 165 € livré et vérifié (voir §7)* | ~160 à 165 € |
| **Option B2 (neuf)** : Pi 5 2 Go (~80 €) + AI HAT+ 26 TOPS ([BerryBase 121,90 €](https://www.berrybase.de/en/raspberry-pi-ai-hat-26-tops-hailo-8-accelerator), [Reichelt ~122,50 €](https://www.reichelt.com/de/en/shop/product/raspberry_pi_shield_-_ai_ai_26_tops_raspberry_pi_5-390448)) | ~202 € + port |
| Active Cooler + microSD | ~14 € |
| **Total** | **B1 ≈ 175 à 180 € / B2 ≈ 215 à 220 €** |

En neuf strict sous 200 €, **la configuration A (Hailo-8L) reste le bon choix** : elle donne les mêmes 30 FPS de détection.

### Configuration C — « ~250 € »
Pi 5 **4 Go** (~135 €) + AI HAT+ 26 TOPS (~122 €) + refroidissement et stockage (~14 €) ≈ **270 €**.
**Je ne la recommande pas** : les 2 Go supplémentaires ne servent pas à un pipeline sans interface graphique, puisque la compilation Hailo se fait sur PC x86 et non sur le Pi. Seule exception où le palier 250 à 300 € vaut le coup : **un Jetson Orin Nano Super d'occasion trouvé sous ~260 €**. Il simplifie fortement le logiciel (TensorRT en une commande, YOLOv8s ou v11s en FP16 sans contrainte de compilation, décodage JPEG matériel), mais consomme 2 à 3 fois plus d'énergie.

### Accessoires d'alimentation (hors budget calcul, mais indispensables)
| Article | Rôle | Prix indicatif |
|---|---|---|
| Convertisseur abaisseur **5,1 V / 5 A** à large plage d'entrée (ex. Pololu D24V50F5, ou un UBEC 5 V 5 A de qualité) | Alimentation du Pi 5 depuis la 2S | 15 à 30 € |
| BEC 6 V / ≥ 5 A dédié | Servos de la tourelle | ~10 € |
| Condensateur de 1000 à 2200 µF en entrée de chaque branche, fusible | Absorber les pointes de courant | ~5 € |

---

## 5. Architecture logicielle recommandée

```
DJI (UVC MJPEG 1080p30)
  │  thread capture : lit les trames JPEG brutes, sans décodage
  ├──► Relais HTTP multipart : le MJPEG d'origine est retransmis tel quel → 1080p30 intact, ~0 % CPU
  └──► Emplacement « dernière trame » (taille 1, écrasée à chaque nouvelle image)
          │  thread inférence (prend toujours la plus récente, jette les autres)
          ▼
        cv2.imdecode(buf, cv2.IMREAD_REDUCED_COLOR_2)   ← décodage à 960×540, 3 à 4× plus rapide
        letterbox 640×640 → Hailo (.hef YOLOv8n, NMS sur la puce)
          ▼
        tracker (ByteTrack + Kalman) → prédiction de la position à t + latence mesurée
          ▼
        thread contrôle à 50 Hz : PID(err_x, err_y) → série → Arduino
        thread web : boîtes en JSON via WebSocket → <canvas> superposé à la vidéo dans le navigateur
```

Règles :
1. **Ne jamais ré-encoder la vidéo pour dessiner les boîtes.** L'overlay est dessiné côté navigateur, qui gère aussi le clic de verrouillage de cible.
2. **Une seule image en attente au maximum.** Pas de `Queue` non bornée : l'inférence se fait toujours sur l'image la plus récente.
3. **Horodater chaque trame** (heure de capture, de début et de fin d'inférence, d'envoi de la commande) et afficher ces latences dans l'interface. Cela permet de comparer les plateformes sur le vrai pipeline.
4. **Une boucle de contrôle à fréquence fixe (50 Hz)**, découplée des détections. Entre deux détections, le Kalman extrapole la position.
5. **Modèle : YOLOv8n, 640×640, `.hef` précompilé du Hailo Model Zoo.** Avec le Hailo-8, essayer YOLOv8s. Une entrée rectangulaire 640×384 (adaptée au 16:9) réduirait encore le calcul, mais elle impose de recompiler le modèle avec le Dataflow Compiler sur PC x86 : c'est pour plus tard. Le dépôt mentionne aussi `yolo26n.onnx` : son support par Hailo n'est pas garanti, **rester sur YOLOv8n/YOLO11n**.
6. **Pi 5 : pas d'encodeur H.264 matériel.** C'est une raison de plus de relayer le MJPEG de la caméra plutôt que de ré-encoder. Un flux MJPEG 1080p30 fait environ 20 à 40 Mbit/s, ce qui demande du Wi-Fi 5 GHz à courte portée. Si le Wi-Fi sature, il faut ré-encoder en 720p, mais seulement à ce moment-là.

### Coût du portage selon l'accélérateur

| Cible | Travail | Estimation |
|---|---|---|
| Hailo, classes COCO (`person`…) | Télécharger le `.hef` YOLOv8n, utiliser l'API Python HailoRT `InferVStreams` à la place d'ONNX Runtime | **1 à 3 jours** |
| Hailo, modèle personnalisé | Dataflow Compiler sur Ubuntu x86 avec images de calibration | +1 à 3 jours |
| RKNN | rknn-toolkit2 sur x86, toolkit-lite2 sur la carte, post-traitement DFL en C++ ou NumPy vectorisé | 3 à 6 jours |
| DEEPX | DX-COM et DX-RT, documentation limitée | 3 à 7 jours, incertain |
| Jetson | `yolo export format=engine half=True` | **< 1 jour** |

---

## 6. Décision

| Palier | Choix | Ce que tu gagnes par rapport au Galaxy A50 |
|---|---|---|
| **Sous 150 €** | Pi 5 2 Go + AI HAT+ 13 TOPS (neuf à ~150 à 165 €, ou lot d'occasion) | Passage d'environ 12 FPS à 320×240 à **30 FPS à 640** (le plafond de la caméra) ; latence de calcul d'environ 40 à 60 ms au lieu de plus de 100 ms ; vidéo 1080p30 intacte ; environ 8 à 10 W |
| **Sous 200 €** ⭐ | **Le lot eBay Pi 5 + AI HAT+ 26 TOPS s'il est vérifié et à ≤ 165 € ; sinon la configuration à 150 €** | Comme ci-dessus, plus environ 9 ms de latence en moins et YOLOv8s possible à 30 FPS |
| **~250 €** | Ne pas dépenser plus pour un Pi 4 Go. **Seule exception : un Jetson Orin Nano Super d'occasion sous ~260 €** | Logiciel beaucoup plus simple et grande marge de calcul ; en contrepartie, 2 à 3 fois plus de consommation et une autonomie réduite |
| **Occasion à surveiller** | Orin Nano Super 8 Go sous 260 € sur Kleinanzeigen (les annonces actuelles vont de 305 à 360 € VB, une à Munich à 349 € VB, une à Weilheim à 305 €) | — |
| **Mon choix pour ton rover** | **Pi 5 2 Go + Hailo-8** (lot d'occasion si vérifié, sinon Hailo-8L neuf), pipeline du §5, Arduino conservé, A50 réutilisé comme écran | 30 FPS stables, vidéo 1080p native, portage en quelques jours, autonomie d'environ 3 h de calcul sur la 2S 5200 |

---

## 7. Vérifications avant d'acheter l'annonce eBay ou Kleinanzeigen

1. Une photo nette du HAT : la puce doit porter **« HAILO-8 »** (26 TOPS) et non « HAILO-8L ».
2. Une photo de la puce RAM du Pi (ou la sortie de `free -h`) pour connaître la capacité.
3. Demander la sortie de `hailortcli fw-control identify` (ligne `Device Architecture: HAILO8`) et de `hailortcli benchmark` sur le `.hef` yolov8n.
4. L'entretoise, le connecteur nappe PCIe et le dissipateur doivent être fournis.
5. Acheter via eBay avec **protection acheteur** (« nicht wie beschrieben ») ; sur Kleinanzeigen, n'utiliser que le paiement sécurisé.
6. Prix plafond raisonnable : **≤ 165 € livré pour 2 Go + 26 TOPS**, et ≤ 185 € pour 4 Go + 26 TOPS.

---

## 8. Alimentation

- **Batterie : 2S 5200 mAh** (≈ 38 Wh). Avec un calculateur à environ 10 W, compter environ **3 h de calcul seul**, moins avec les moteurs.
- **Branche calculateur** : convertisseur abaisseur 5,1 V / 5 A **dédié**, câblé directement aux bornes de la batterie (en étoile). Avec 2S (6,0 à 8,4 V), le convertisseur garde assez de marge de tension.
  - Ajouter `usb_max_current_enable=1` dans `/boot/firmware/config.txt`. Sinon, avec une alimentation non officielle, le Pi 5 limite les ports USB à 600 mA, alors que la DJI peut tirer plus.
- **Branche servos** : BEC 6 V dédié avec un condensateur de 1000 µF ou plus. Ne jamais alimenter les servos depuis le 5 V du Pi.
- **Branche moteurs** : depuis la batterie, via le driver. Avec l'Adafruit Motor Shield v2 (TB6612, 1,2 A par canal, 13,5 V max), la 2S convient et la 4S est exclue.
- **Masses communes**, câbles moteurs séparés du câble de la caméra, condensateurs de 100 nF sur les moteurs TT.

---

## 9. Informations encore nécessaires

1. **Le GPU exact de l'IdeaPad** (`nvidia-smi` ou Gestionnaire des tâches → Performances). Il sert de référence gratuite.
2. **Les formats UVC réellement exposés par la DJI** : `v4l2-ctl -d /dev/video0 --list-formats-ext` sous Linux, ou `ffmpeg -list_options true -f dshow -i video="..."` sous Windows. La présence ou non d'un 1080p60 change l'objectif de FPS.
3. **La latence propre de la caméra** : filmer un chronomètre à l'écran et comparer avec l'image reçue.
4. **Les moteurs et le driver réellement utilisés** : le README parle d'un Arduino Uno avec Motor Shield v2 et de moteurs TT, le contexte d'un Arduino Nano. Cela décide du choix entre 2S et 3S.

---

## Sources
- Hailo-8L sur Pi 5 : 61,9 FPS mesurés contre 182 FPS dans le Model Zoo — https://community.hailo.ai/t/yolov8n-real-performance-didnt-expected-from-hailo-model-zoo-documentation/18904
- Hailo-8 sur Pi 5 : 144 FPS en C++ sans pré/post — https://community.hailo.ai/t/the-performance-on-the-raspberry-pi-5-with-the-hailo-8-chip-seems-not-good-as-he-official-results/17473
- Compilation Hailo-8 contre Hailo-8L — https://community.hailo.ai/t/model-inference-on-hailo-8-vs-hailo-8l/2880
- DEEPX contre Hailo (Sixfab) — https://sixfab.com/blog/raspberry-pi-5-ai-hat-benchmark-deepx-vs-hailo/ ; https://eu.sixfab.com/products/ai-hat-plus-raspberry-pi-5
- RKNN Model Zoo — https://github.com/airockchip/rknn_model_zoo ; forum Radxa — https://forum.radxa.com/t/use-yolov8-in-rk3588-npu/15838?page=7
- Orin Nano, YOLOv8n TensorRT — https://forums.developer.nvidia.com/t/benchmarck-int8-similar-to-fp32-on-yolov8-from-ultralytics/276023 ; https://github.com/Qengineering/YoloV8-TensorRT-Jetson_Nano
- Fin de vie de JetPack 5 — https://forums.developer.nvidia.com/t/jetson-nano-and-jetson-xavier-announcements/232522
- N100 / OpenVINO — https://lattepanda.com/blog-323173.html ; https://lattepanda.com/blog-323181.html
- Prix des Jetson — https://geizhals.de/nvidia-jetson-orin-nano-super-developer-kit-a3524658.html ; https://de.rs-online.com/web/p/entwicklungstools-prozessor/2647384 ; https://www.kleinanzeigen.de/s-jetson-orin/k0
- Prix AI HAT+ 26 TOPS — https://www.berrybase.de/en/raspberry-pi-ai-hat-26-tops-hailo-8-accelerator ; https://www.reichelt.com/de/en/shop/product/raspberry_pi_shield_-_ai_ai_26_tops_raspberry_pi_5-390448
- Prix AI HAT+ 13 TOPS — https://buyzero.de/collections/hailo ; https://www.ebay.de/shop/ai-hat
- Hausse des prix des Raspberry Pi en 2026 — https://www.heise.de/en/news/Up-to-150-Raspi-prices-rise-again-11243959.html ; https://www.pcgameshardware.de/Raspberry-Pi-Hardware-257637/News/raspberry-pi-4-5-2-gb-ram-preiserhoehung-1555550/
- Prix de l'Orange Pi 5 — https://www.amazon.de/-/en/orange-pi-5/s?k=orange+pi+5 ; https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-alternatives-2026-orange-pi-5-rock-5b-odroid-n2-compared
- Consommation du Hailo-8 — https://www.waveshare.com/hailo-8-acce-a.htm
