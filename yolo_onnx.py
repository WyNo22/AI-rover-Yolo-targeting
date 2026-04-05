"""
yolo_onnx.py – Lightweight YOLO inference + simple IoU tracker.
Replaces ultralytics + PyTorch on Android/Termux.
Requires: onnxruntime (or ncnn), numpy, cv2 shim.
"""
import numpy as np
import cv2
import time


# ── YOLO ONNX Detector ──────────────────────────────────────────────────────
class YOLODetector:
    """Run YOLOv8/v11 ONNX model without ultralytics or PyTorch."""

    def __init__(self, model_path, conf=0.4, iou_thresh=0.45, imgsz=640):
        import onnxruntime as ort
        self.session = ort.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.imgsz = imgsz
        self.conf = conf
        self.iou_thresh = iou_thresh

        # Detect output format
        out = self.session.get_outputs()[0]
        # End-to-end (NMS built-in): [1, 300, 6] → x1,y1,x2,y2,conf,cls
        # Raw format: [1, 4+num_classes, num_boxes]
        if len(out.shape) == 3 and out.shape[2] == 6:
            self.end2end = True
            self.num_classes = -1
        elif len(out.shape) == 3 and out.shape[1] > out.shape[2]:
            self.end2end = False
            self.num_classes = out.shape[1] - 4
        elif len(out.shape) == 3:
            self.end2end = False
            self.num_classes = out.shape[2] - 4 if out.shape[2] > 6 else -1
        else:
            self.end2end = False
            self.num_classes = 80
        fmt = 'end2end (NMS built-in)' if self.end2end else f'raw ({self.num_classes} classes)'
        print(f"[YOLO-ONNX] Loaded {model_path}  format={fmt}  input={self.imgsz}x{self.imgsz}")

    def detect(self, frame, classes=None):
        """
        Run detection on a BGR frame.
        Returns list of (x1, y1, x2, y2, conf, class_id).
        """
        h0, w0 = frame.shape[:2]
        blob, ratio, pad_w, pad_h = self._preprocess(frame)
        outputs = self.session.run(None, {self.input_name: blob})
        preds = outputs[0]  # [1, 300, 6] or [1, 4+C, N]

        if self.end2end:
            return self._postprocess_e2e(preds[0], ratio, pad_w, pad_h, w0, h0, classes)

        # Raw format
        if preds.shape[1] > preds.shape[2]:
            preds = preds[0].T  # [N, 4+C]
        else:
            preds = preds[0]
        return self._postprocess_raw(preds, ratio, pad_w, pad_h, w0, h0, classes)

    def _preprocess(self, frame):
        """Letterbox resize + normalize → NCHW float32 blob."""
        h0, w0 = frame.shape[:2]
        sz = self.imgsz
        ratio = min(sz / h0, sz / w0)
        new_w, new_h = int(w0 * ratio), int(h0 * ratio)
        pad_w, pad_h = (sz - new_w) / 2, (sz - new_h) / 2

        resized = cv2.resize(frame, (new_w, new_h))

        # Create padded image
        top, bottom = int(round(pad_h - 0.1)), int(round(pad_h + 0.1))
        left, right = int(round(pad_w - 0.1)), int(round(pad_w + 0.1))

        if resized.ndim == 2:
            padded = np.full((sz, sz), 114, dtype=np.uint8)
            padded[top:top+new_h, left:left+new_w] = resized
        else:
            padded = np.full((sz, sz, 3), 114, dtype=np.uint8)
            padded[top:top+new_h, left:left+new_w] = resized

        # BGR→RGB, HWC→CHW, normalize
        img = padded[:, :, ::-1] if padded.ndim == 3 else padded
        img = img.transpose(2, 0, 1) if img.ndim == 3 else img[np.newaxis]
        img = img.astype(np.float32) / 255.0
        blob = img[np.newaxis]  # [1, 3, H, W]
        return blob, ratio, pad_w, pad_h

    def _postprocess_e2e(self, preds, ratio, pad_w, pad_h, w0, h0, classes):
        """Post-process end-to-end output [300, 6] → x1,y1,x2,y2,conf,cls."""
        if len(preds) == 0:
            return []

        x1, y1, x2, y2 = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
        confs = preds[:, 4]
        class_ids = preds[:, 5].astype(int)

        # Confidence filter
        mask = confs > self.conf
        if classes is not None:
            mask = mask & np.isin(class_ids, classes)

        x1, y1, x2, y2 = x1[mask], y1[mask], x2[mask], y2[mask]
        confs, class_ids = confs[mask], class_ids[mask]

        if len(confs) == 0:
            return []

        # Scale from letterbox to original
        x1 = np.clip((x1 - pad_w) / ratio, 0, w0).astype(int)
        y1 = np.clip((y1 - pad_h) / ratio, 0, h0).astype(int)
        x2 = np.clip((x2 - pad_w) / ratio, 0, w0).astype(int)
        y2 = np.clip((y2 - pad_h) / ratio, 0, h0).astype(int)

        results = []
        for i in range(len(confs)):
            results.append((int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]),
                            float(confs[i]), int(class_ids[i])))
        return results

    def _postprocess_raw(self, preds, ratio, pad_w, pad_h, w0, h0, classes):
        """Post-process raw output [N, 4+C] with NMS."""
        cx, cy, bw, bh = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
        scores_all = preds[:, 4:]
        class_ids = scores_all.argmax(axis=1)
        confs = scores_all[np.arange(len(scores_all)), class_ids]

        mask = confs > self.conf
        if classes is not None:
            mask = mask & np.isin(class_ids, classes)

        cx, cy, bw, bh = cx[mask], cy[mask], bw[mask], bh[mask]
        confs, class_ids = confs[mask], class_ids[mask]

        if len(confs) == 0:
            return []

        x1 = np.clip((cx - bw/2 - pad_w) / ratio, 0, w0).astype(int)
        y1 = np.clip((cy - bh/2 - pad_h) / ratio, 0, h0).astype(int)
        x2 = np.clip((cx + bw/2 - pad_w) / ratio, 0, w0).astype(int)
        y2 = np.clip((cy + bh/2 - pad_h) / ratio, 0, h0).astype(int)

        indices = self._nms(x1, y1, x2, y2, confs, self.iou_thresh)
        results = []
        for i in indices:
            results.append((int(x1[i]), int(y1[i]), int(x2[i]), int(y2[i]),
                            float(confs[i]), int(class_ids[i])))
        return results

    @staticmethod
    def _nms(x1, y1, x2, y2, scores, thresh):
        """Simple NMS."""
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = np.where(iou <= thresh)[0]
            order = order[inds + 1]
        return keep


# ── Simple IoU Tracker (replaces BotsSort) ───────────────────────────────────
class SimpleTracker:
    """Lightweight IoU-based tracker with stable IDs."""

    def __init__(self, iou_thresh=0.3, max_lost=30):
        self._next_id = 1
        self._tracks = {}   # id → {"box": (x1,y1,x2,y2), "lost": int, "conf": float}
        self.iou_thresh = iou_thresh
        self.max_lost = max_lost

    def update(self, detections):
        """
        Update tracks with new detections.
        detections: list of (x1, y1, x2, y2, conf, class_id)
        Returns: list of (track_id, x1, y1, x2, y2, conf)
        """
        if not detections:
            # Age all tracks
            lost_ids = []
            for tid in self._tracks:
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self.max_lost:
                    lost_ids.append(tid)
            for tid in lost_ids:
                del self._tracks[tid]
            return []

        det_boxes = np.array([(d[0], d[1], d[2], d[3]) for d in detections])
        det_confs = [d[4] for d in detections]

        track_ids = list(self._tracks.keys())
        matched_det = set()
        matched_trk = set()
        results = []

        if track_ids:
            trk_boxes = np.array([self._tracks[t]["box"] for t in track_ids])
            iou_matrix = self._iou_batch(trk_boxes, det_boxes)

            # Greedy matching
            while True:
                if iou_matrix.size == 0:
                    break
                max_iou = iou_matrix.max()
                if max_iou < self.iou_thresh:
                    break
                ti, di = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
                tid = track_ids[ti]
                self._tracks[tid]["box"] = tuple(det_boxes[di])
                self._tracks[tid]["lost"] = 0
                self._tracks[tid]["conf"] = det_confs[di]
                matched_det.add(di)
                matched_trk.add(ti)
                iou_matrix[ti, :] = -1
                iou_matrix[:, di] = -1

        # Collect matched tracks
        for ti, tid in enumerate(track_ids):
            if ti in matched_trk:
                b = self._tracks[tid]["box"]
                results.append((tid, b[0], b[1], b[2], b[3],
                                self._tracks[tid]["conf"]))

        # Create new tracks for unmatched detections
        for di in range(len(detections)):
            if di not in matched_det:
                tid = self._next_id
                self._next_id += 1
                box = tuple(det_boxes[di])
                self._tracks[tid] = {"box": box, "lost": 0,
                                     "conf": det_confs[di]}
                results.append((tid, box[0], box[1], box[2], box[3],
                                det_confs[di]))

        # Age unmatched tracks
        lost_ids = []
        for ti, tid in enumerate(track_ids):
            if ti not in matched_trk:
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self.max_lost:
                    lost_ids.append(tid)
        for tid in lost_ids:
            del self._tracks[tid]

        return results

    @staticmethod
    def _iou_batch(boxes_a, boxes_b):
        """Compute IoU matrix [len(a), len(b)]."""
        x1 = np.maximum(boxes_a[:, 0:1], boxes_b[:, 0:1].T)
        y1 = np.maximum(boxes_a[:, 1:2], boxes_b[:, 1:2].T)
        x2 = np.minimum(boxes_a[:, 2:3], boxes_b[:, 2:3].T)
        y2 = np.minimum(boxes_a[:, 3:4], boxes_b[:, 3:4].T)
        inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area_a = (boxes_a[:, 2] - boxes_a[:, 0]) * (boxes_a[:, 3] - boxes_a[:, 1])
        area_b = (boxes_b[:, 2] - boxes_b[:, 0]) * (boxes_b[:, 3] - boxes_b[:, 1])
        union = area_a[:, None] + area_b[None, :] - inter + 1e-6
        return inter / unio