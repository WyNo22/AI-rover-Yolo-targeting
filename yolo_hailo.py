"""
yolo_hailo.py – YOLO sur l'accélérateur Hailo (Raspberry Pi 5 + AI HAT+).
Utilise les modèles .hef compilés avec NMS intégré (ceux de /usr/share/hailo-models,
installés par `sudo apt install hailo-all`) : la puce renvoie directement les boîtes.

Même interface que yolo_onnx.YOLODetector : detect(img_bgr, classes) → [(x1, y1, x2, y2, conf, cls)]
"""
import glob
import os

import cv2
import numpy as np

HAILO_MODEL_DIR = "/usr/share/hailo-models"


def find_hef(name):
    """Chemin tel quel, puis à côté du script, puis dans /usr/share/hailo-models."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (name, os.path.join(here, name), os.path.join(HAILO_MODEL_DIR, name)):
        if os.path.exists(p):
            return p
    return None


def default_hef():
    """Meilleur modèle de détection installé. Les .hef « _h8 » visent le Hailo-8 (26 TOPS),
    les « _h8l » le Hailo-8L (13 TOPS) : on prend _h8 en priorité, _h8l sinon."""
    hefs = [os.path.basename(h) for h in glob.glob(os.path.join(HAILO_MODEL_DIR, "*.hef"))]
    hefs = [h for h in hefs if "pose" not in h and "seg" not in h]
    for arch in ("_h8.", "_h8_", "_h8l"):
        for pref in ("yolov8s", "yolov8m", "yolov11s", "yolov6n", "yolov8n", "yolov5"):
            for h in sorted(hefs):
                if h.startswith(pref) and arch in h:
                    return os.path.join(HAILO_MODEL_DIR, h)
    return None


class HailoDetector:
    def __init__(self, hef_path, conf=0.4):
        from hailo_platform import (HEF, VDevice, ConfigureParams, HailoStreamInterface,
                                    InputVStreamParams, OutputVStreamParams, InferVStreams, FormatType)
        self.conf = conf
        self.hef = HEF(hef_path)
        self.device = VDevice()
        cfg = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        self.ng = self.device.configure(self.hef, cfg)[0]
        in_params = InputVStreamParams.make(self.ng, format_type=FormatType.UINT8)
        out_params = OutputVStreamParams.make(self.ng, format_type=FormatType.FLOAT32)
        self.in_info = self.hef.get_input_vstream_infos()[0]
        outs = self.hef.get_output_vstream_infos()
        order = str(getattr(getattr(outs[0], "format", None), "order", "nms")).lower()
        if len(outs) != 1 or "nms" not in order:
            raise SystemExit(f"[HAILO] {os.path.basename(hef_path)} n'a pas de NMS intégré : "
                             "prendre un modèle de détection yolov8*/yolov6*/yolov5* de /usr/share/hailo-models")
        self.out_name = outs[0].name
        self.in_h, self.in_w = self.in_info.shape[0], self.in_info.shape[1]
        # Le réseau reste activé et les flux ouverts : aucun coût de mise en route par image.
        self._activation = self.ng.activate(self.ng.create_params())
        self._activation.__enter__()
        self._pipe = InferVStreams(self.ng, in_params, out_params)
        self._pipe.__enter__()
        print(f"[YOLO] {os.path.basename(hef_path)} sur Hailo ({self.in_w}x{self.in_h})")

    def detect(self, img, classes=None):
        h, w = img.shape[:2]
        # Letterbox : on garde les proportions, bandes grises comme à l'entraînement.
        s = min(self.in_w / w, self.in_h / h)
        nw, nh = int(round(w * s)), int(round(h * s))
        px, py = (self.in_w - nw) // 2, (self.in_h - nh) // 2
        canvas = np.full((self.in_h, self.in_w, 3), 114, np.uint8)
        canvas[py:py + nh, px:px + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

        res = self._pipe.infer({self.in_info.name: rgb[None]})[self.out_name][0]
        # Sortie NMS : une liste par classe, chaque ligne = [y1, x1, y2, x2, score] normalisés.
        out = []
        for cls, boxes in enumerate(res):
            if classes is not None and cls not in classes:
                continue
            for y1, x1, y2, x2, score in np.asarray(boxes).reshape(-1, 5):
                if score < self.conf:
                    continue
                out.append((float(x1 * self.in_w - px) / s, float(y1 * self.in_h - py) / s,
                            float(x2 * self.in_w - px) / s, float(y2 * self.in_h - py) / s,
                            float(score), cls))
        return out

    def close(self):
        self._pipe.__exit__(None, None, None)
        self._activation.__exit__(None, None, None)
        self.device.release()
