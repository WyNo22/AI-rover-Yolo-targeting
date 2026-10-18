"""
yolo_test.py
Test simple : caméra (DJI / GoPro en mode webcam / webcam) → YOLO → fenêtre vidéo annotée.
Aucune commande série, aucun servo.

  pip install ultralytics opencv-python        # modèle yolov8n.pt téléchargé automatiquement, GPU si dispo
  python yolo_test.py                          # première caméra trouvée
  python yolo_test.py --source 1 --size 1920x1080
  python yolo_test.py --model yolo26n.onnx     # sans PyTorch (onnxruntime)

Touches : q / Échap = quitter   s = capture d'écran   c = classes : personnes ↔ toutes
"""

import argparse
import os
import platform
import threading
import time

import cv2

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"

COCO = ("person bicycle car motorcycle airplane bus train truck boat traffic-light fire-hydrant "
        "stop-sign parking-meter bench bird cat dog horse sheep cow elephant bear zebra giraffe "
        "backpack umbrella handbag tie suitcase frisbee skis snowboard sports-ball kite baseball-bat "
        "baseball-glove skateboard surfboard tennis-racket bottle wine-glass cup fork knife spoon bowl "
        "banana apple sandwich orange broccoli carrot hot-dog pizza donut cake chair couch potted-plant "
        "bed dining-table toilet tv laptop mouse remote keyboard cell-phone microwave oven toaster sink "
        "refrigerator book clock vase scissors teddy-bear hair-drier toothbrush").split()


class Camera:
    """Lit la caméra dans un thread et ne garde que la dernière image (pas de retard accumulé)."""

    def __init__(self, source, size, fps):
        src = int(source) if str(source).isdigit() else source
        if IS_WINDOWS and isinstance(src, int):
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(src, cv2.CAP_MSMF)
        else:
            self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise SystemExit(f"Impossible d'ouvrir la caméra {source!r} (essaie --source 1, 2…)")
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._cond = threading.Condition()
        self._frame, self._seq = None, 0
        self.fps, self._t = 0.0, None
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            ok, img = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            t = time.monotonic()
            if self._t is not None:
                self.fps = 0.9 * self.fps + 0.1 / max(t - self._t, 1e-6)
            self._t = t
            with self._cond:
                self._frame, self._seq = img, self._seq + 1
                self._cond.notify_all()

    def latest(self, last_seq, timeout=2.0):
        with self._cond:
            self._cond.wait_for(lambda: self._seq > last_seq, timeout)
            return self._seq, self._frame

    def release(self):
        self.running = False
        time.sleep(0.05)
        self.cap.release()


class Detector:
    """Ultralytics (.pt, GPU si disponible) ou ONNX Runtime (.onnx, CPU)."""

    def __init__(self, model, imgsz, conf, device):
        self.imgsz, self.conf = imgsz, conf
        if model.endswith(".pt"):
            from ultralytics import YOLO
            import torch
            self.kind = "ultralytics"
            self.device = device or ("0" if torch.cuda.is_available() else "cpu")
            self.model = YOLO(model)          # yolov8n.pt est téléchargé s'il n'existe pas
            self.names = self.model.names
            label = torch.cuda.get_device_name(0) if self.device != "cpu" else "CPU"
        else:
            from yolo_onnx import YOLODetector
            path = model if os.path.isabs(model) else os.path.join(_SCRIPT_DIR, model)
            if not os.path.exists(path):
                raise SystemExit(f"Modèle introuvable : {path}")
            self.kind = "onnx"
            self.model = YOLODetector(path, conf=conf, imgsz=imgsz)
            self.names = dict(enumerate(COCO))
            label = "CPU (onnxruntime)"
        self.backend = f"{self.kind} – {label}"

    def detect(self, img, classes):
        if self.kind == "ultralytics":
            r = self.model.predict(img, imgsz=self.imgsz, conf=self.conf, classes=classes,
                                   device=self.device, verbose=False)[0]
            return [(*b.xyxy[0].tolist(), float(b.conf[0]), int(b.cls[0])) for b in r.boxes]
        return self.model.detect(img, classes=classes)


def draw(img, dets, names, hud):
    s = max(img.shape[1] / 1280, 1.0)          # traits lisibles même en 1080p / 4K
    for x1, y1, x2, y2, conf, cls in dets:
        color = (0, 255, 0) if cls == 0 else (255, 160, 0)
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(img, p1, p2, color, int(2 * s))
        label = f"{names.get(int(cls), cls)} {conf:.2f}"
        cv2.putText(img, label, (p1[0], max(p1[1] - int(6 * s), 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6 * s, color, int(2 * s))
    for i, line in enumerate(hud):
        y = int((28 + 28 * i) * s)
        cv2.putText(img, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * s, (0, 0, 0), int(5 * s))
        cv2.putText(img, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * s, (0, 255, 255), int(2 * s))


def default_model():
    try:
        import ultralytics  # noqa: F401
        return "yolov8n.pt"
    except ImportError:
        for name in ("yolo26n.onnx", "yolov8n.onnx", "yolo11n.onnx"):
            if os.path.exists(os.path.join(_SCRIPT_DIR, name)):
                return name
        return "yolov8n.onnx"


def main():
    p = argparse.ArgumentParser(description="Test YOLO sur caméra avec retour vidéo")
    p.add_argument("--source", default="0", help="index caméra (0, 1…), chemin vidéo ou URL")
    p.add_argument("--size", default="1920x1080")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--model", default=default_model(), help="yolov8n.pt, yolo11n.pt, *.onnx…")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--device", default=None, help="ultralytics : 0 (GPU) ou cpu")
    p.add_argument("--all", action="store_true", help="toutes les classes COCO (sinon : personnes)")
    args = p.parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))
    det = Detector(args.model, args.imgsz, args.conf, args.device)
    cam = Camera(args.source, (w, h), args.fps)
    print(f"Caméra {cam.w}x{cam.h} | modèle {args.model} | {det.backend}")

    win = "YOLO test  |  q = quitter  s = capture  c = classes"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, min(cam.w, 1280), min(cam.h, 720))

    all_classes, last, yolo_fps, inf_ms, t_prev = args.all, 0, 0.0, 0.0, None
    try:
        while True:
            seq, frame = cam.latest(last)
            if frame is None or seq == last:
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
                continue
            last = seq
            t0 = time.monotonic()
            dets = det.detect(frame, None if all_classes else [0])
            t1 = time.monotonic()
            inf_ms = 0.9 * inf_ms + 0.1 * (t1 - t0) * 1000 if inf_ms else (t1 - t0) * 1000
            if t_prev is not None:
                yolo_fps = 0.9 * yolo_fps + 0.1 / max(t1 - t_prev, 1e-6)
            t_prev = t1

            img = frame.copy()
            draw(img, dets, det.names, [
                f"camera {cam.fps:4.1f} fps  {cam.w}x{cam.h}",
                f"YOLO {yolo_fps:4.1f} fps  inference {inf_ms:5.1f} ms",
                f"{det.backend}  |  {'toutes classes' if all_classes else 'personnes'}  |  {len(dets)} det.",
            ])
            cv2.imshow(win, img)
            k = cv2.waitKey(1) & 0xFF
            if k in (ord("q"), 27):
                break
            if k == ord("s"):
                name = time.strftime("yolo_%Y%m%d_%H%M%S.jpg")
                cv2.imwrite(os.path.join(_SCRIPT_DIR, name), img)
                print(f"Capture : {name}")
            if k == ord("c"):
                all_classes = not all_classes
            if cv2.getWindowProperty(win, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        print(f"[PERF] caméra {cam.fps:.1f} fps | YOLO {yolo_fps:.1f} fps | inférence {inf_ms:.1f} ms | {det.backend}")
        cam.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
