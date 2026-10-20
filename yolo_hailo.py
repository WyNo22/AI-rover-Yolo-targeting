"""
yolo_hailo.py – YOLO sur l'accélérateur Hailo (Raspberry Pi 5 + AI HAT+).

  HailoDetector      modèles de détection avec NMS intégré (yolov8s_h8.hef…) : la puce renvoie les boîtes
  HailoPoseDetector  modèles de pose (yolov8s_pose_h8.hef…) : boîtes + 17 points du corps,
                     décodage (DFL, points, NMS) fait ici sur le processeur

Même interface que yolo_onnx.YOLODetector :
  detect(img_bgr, classes) → [(x1, y1, x2, y2, conf, cls)]               détection
                           → [(x1, y1, x2, y2, conf, 0, kpts[17, 3])]     pose (x, y en pixels, visibilité 0..1)

Diagnostic : python3 yolo_hailo.py --info /usr/share/hailo-models/yolov8s_pose_h8.hef
"""
import glob
import os
import sys

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


def default_hef(pose=False):
    """Meilleur modèle installé. Les .hef « _h8 » visent le Hailo-8 (26 TOPS),
    les « _h8l » le Hailo-8L (13 TOPS) : on prend _h8 en priorité, _h8l sinon."""
    hefs = [os.path.basename(h) for h in glob.glob(os.path.join(HAILO_MODEL_DIR, "*.hef"))]
    if pose:
        hefs, prefs = [h for h in hefs if "pose" in h], ("yolov8s_pose", "yolov8m_pose", "yolov8n_pose")
    else:
        hefs = [h for h in hefs if "pose" not in h and "seg" not in h]
        prefs = ("yolov8s", "yolov8m", "yolov11s", "yolov6n", "yolov8n", "yolov5")
    for arch in ("_h8.", "_h8_", "_h8l"):
        for pref in prefs:
            for h in sorted(hefs):
                if h.startswith(pref) and arch in h:
                    return os.path.join(HAILO_MODEL_DIR, h)
    return None


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class _HailoNet:
    """Réseau chargé une fois, activé en permanence ; letterbox à l'entrée."""

    def __init__(self, hef_path):
        from hailo_platform import (HEF, VDevice, ConfigureParams, HailoStreamInterface,
                                    InputVStreamParams, OutputVStreamParams, InferVStreams, FormatType)
        self.name = os.path.basename(hef_path)
        self.hef = HEF(hef_path)
        self.device = VDevice()
        cfg = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
        self.ng = self.device.configure(self.hef, cfg)[0]
        in_params = InputVStreamParams.make(self.ng, format_type=FormatType.UINT8)
        out_params = OutputVStreamParams.make(self.ng, format_type=FormatType.FLOAT32)
        self.in_info = self.hef.get_input_vstream_infos()[0]
        self.out_infos = self.hef.get_output_vstream_infos()
        self.in_h, self.in_w = self.in_info.shape[0], self.in_info.shape[1]
        # Le réseau reste activé et les flux ouverts : aucun coût de mise en route par image.
        self._activation = self.ng.activate(self.ng.create_params())
        self._activation.__enter__()
        self._pipe = InferVStreams(self.ng, in_params, out_params)
        self._pipe.__enter__()

    def _infer(self, img):
        h, w = img.shape[:2]
        # Letterbox : on garde les proportions, bandes grises comme à l'entraînement.
        s = min(self.in_w / w, self.in_h / h)
        nw, nh = int(round(w * s)), int(round(h * s))
        px, py = (self.in_w - nw) // 2, (self.in_h - nh) // 2
        canvas = np.full((self.in_h, self.in_w, 3), 114, np.uint8)
        canvas[py:py + nh, px:px + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        return self._pipe.infer({self.in_info.name: rgb[None]}), s, px, py

    def close(self):
        self._pipe.__exit__(None, None, None)
        self._activation.__exit__(None, None, None)
        self.device.release()


class HailoDetector(_HailoNet):
    def __init__(self, hef_path, conf=0.4):
        super().__init__(hef_path)
        self.conf = conf
        order = str(getattr(getattr(self.out_infos[0], "format", None), "order", "nms")).lower()
        if len(self.out_infos) != 1 or "nms" not in order:
            raise SystemExit(f"[HAILO] {self.name} n'a pas de NMS intégré : "
                             "prendre un modèle de détection yolov8*/yolov6*/yolov5* de /usr/share/hailo-models")
        self.out_name = self.out_infos[0].name
        print(f"[YOLO] {self.name} sur Hailo ({self.in_w}x{self.in_h})")

    def detect(self, img, classes=None):
        res, s, px, py = self._infer(img)
        res = res[self.out_name][0]
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


class HailoPoseDetector(_HailoNet):
    """YOLOv8-pose : par échelle (stride 8, 16, 32) trois sorties, reconnues à leur nombre de canaux :
    64 = boîte (4 côtés × 16 cases DFL), 1 = score personne, 51 = 17 points × (x, y, visibilité)."""

    def __init__(self, hef_path, conf=0.4, iou=0.5):
        super().__init__(hef_path)
        self.conf, self.iou = conf, iou
        chans = sorted({o.shape[-1] for o in self.out_infos})
        if not {1, 51, 64} <= set(chans):
            raise SystemExit(f"[HAILO] {self.name} : sorties inattendues {chans} (attendu 64/1/51). "
                             f"Lancer : python3 yolo_hailo.py --info {hef_path}")
        self._bins = np.arange(16, dtype=np.float32)
        print(f"[YOLO] {self.name} (pose, 17 points) sur Hailo ({self.in_w}x{self.in_h})")

    def detect(self, img, classes=None):
        res, s, px, py = self._infer(img)
        scales = {}
        for name, a in res.items():
            a = np.asarray(a)[0]
            scales.setdefault(a.shape[0], {})[a.shape[-1]] = a
        boxes, scores, kpts = [], [], []
        for gh, g in scales.items():
            gw = g[1].shape[1]
            stride = self.in_h / gh
            sc = g[1].reshape(-1)
            if sc.min() < 0 or sc.max() > 1:      # logits si la sigmoïde n'est pas dans le modèle
                sc = _sigmoid(sc)
            keep = np.nonzero(sc >= self.conf)[0]
            if keep.size == 0:
                continue
            gy, gx = np.divmod(keep, gw)
            # Boîte : distribution sur 16 cases par côté (DFL) → distance gauche/haut/droite/bas
            d = g[64].reshape(-1, 4, 16)[keep]
            e = np.exp(d - d.max(-1, keepdims=True))
            d = (e / e.sum(-1, keepdims=True) * self._bins).sum(-1) * stride
            cx, cy = (gx + 0.5) * stride, (gy + 0.5) * stride
            boxes.append(np.stack([cx - d[:, 0], cy - d[:, 1], cx + d[:, 2], cy + d[:, 3]], 1))
            scores.append(sc[keep])
            k = g[51].reshape(-1, 17, 3)[keep].astype(np.float32)
            k[..., 0] = (k[..., 0] * 2 + gx[:, None]) * stride
            k[..., 1] = (k[..., 1] * 2 + gy[:, None]) * stride
            v = k[..., 2]
            k[..., 2] = _sigmoid(v) if (v.min() < 0 or v.max() > 1) else v
            kpts.append(k)
        if not boxes:
            return []
        boxes, scores, kpts = np.concatenate(boxes), np.concatenate(scores), np.concatenate(kpts)
        xywh = np.column_stack([boxes[:, :2], boxes[:, 2:] - boxes[:, :2]]).tolist()
        idx = cv2.dnn.NMSBoxes(xywh, scores.tolist(), self.conf, self.iou)
        out = []
        for i in np.array(idx).reshape(-1):
            b = (boxes[i] - [px, py, px, py]) / s
            k = kpts[i].copy()
            k[:, 0] = (k[:, 0] - px) / s
            k[:, 1] = (k[:, 1] - py) / s
            out.append((float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(scores[i]), 0, k))
        return out


def make_hailo_detector(path, conf):
    if "pose" in os.path.basename(path).lower():
        return HailoPoseDetector(path, conf=conf)
    return HailoDetector(path, conf=conf)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--info":
        from hailo_platform import HEF
        hef = HEF(find_hef(sys.argv[2]) or sys.argv[2])
        for i in hef.get_input_vstream_infos():
            print("entrée ", i.name, i.shape)
        for o in hef.get_output_vstream_infos():
            print("sortie ", o.name, o.shape, getattr(getattr(o, "format", None), "order", ""))
    else:
        print("Modèles installés :")
        for h in sorted(glob.glob(os.path.join(HAILO_MODEL_DIR, "*.hef"))):
            print("  ", os.path.basename(h))
        print("Détection par défaut :", default_hef())
        print("Pose par défaut      :", default_hef(pose=True))
