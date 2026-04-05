"""
cv2 shim for Termux/Android — PIL + numpy backend, zero compilation.
Install: mkdir -p $PREFIX/lib/python3.13/site-packages/cv2
         cp __init__.py $PREFIX/lib/python3.13/site-packages/cv2/__init__.py
"""
import numpy as np
from PIL import Image
import io, time

__version__ = "4.9.0"

# ── Color conversion codes ───────────────────────────────────────────────────
COLOR_BGR2RGB = 4
COLOR_RGB2BGR = 4
COLOR_BGR2GRAY = 6
COLOR_RGB2GRAY = 7
COLOR_GRAY2BGR = 8
COLOR_GRAY2RGB = 8
COLOR_BGR2HSV = 40
COLOR_HSV2BGR = 54
COLOR_BGR2Lab = 44
COLOR_Lab2BGR = 56
COLOR_BGR2YCrCb = 36
COLOR_YCrCb2BGR = 38
COLOR_BGR2HLS = 52
COLOR_HLS2BGR = 60
COLOR_BGRA2GRAY = 10
COLOR_RGBA2GRAY = 11
COLOR_BGR2BGRA = 0
COLOR_BGRA2BGR = 1
COLOR_RGBA2BGR = 2
COLOR_BGR2RGBA = 2

# ── Read flags ────────────────────────────────────────────────────────────────
IMREAD_COLOR = 1
IMREAD_GRAYSCALE = 0
IMREAD_UNCHANGED = -1

# ── Interpolation ────────────────────────────────────────────────────────────
INTER_NEAREST = 0
INTER_LINEAR = 1
INTER_CUBIC = 2
INTER_AREA = 3
INTER_LANCZOS4 = 4

# ── Font ─────────────────────────────────────────────────────────────────────
FONT_HERSHEY_SIMPLEX = 0
FONT_HERSHEY_PLAIN = 1
FONT_HERSHEY_DUPLEX = 2
FONT_HERSHEY_COMPLEX = 3
FONT_HERSHEY_TRIPLEX = 4
FONT_HERSHEY_COMPLEX_SMALL = 5
FONT_HERSHEY_SCRIPT_SIMPLEX = 6
FONT_HERSHEY_SCRIPT_COMPLEX = 7
FONT_ITALIC = 16

# ── Line types ───────────────────────────────────────────────────────────────
LINE_4 = 4
LINE_8 = 8
LINE_AA = 16
FILLED = -1

# ── Marker types ─────────────────────────────────────────────────────────────
MARKER_CROSS = 0
MARKER_TILTED_CROSS = 1
MARKER_STAR = 2
MARKER_DIAMOND = 3
MARKER_SQUARE = 4
MARKER_TRIANGLE_UP = 5
MARKER_TRIANGLE_DOWN = 6

# ── Rotation ─────────────────────────────────────────────────────────────────
ROTATE_90_CLOCKWISE = 0
ROTATE_180 = 1
ROTATE_90_COUNTERCLOCKWISE = 2

# ── Threshold ────────────────────────────────────────────────────────────────
THRESH_BINARY = 0
THRESH_BINARY_INV = 1
THRESH_OTSU = 8

# ── Border ───────────────────────────────────────────────────────────────────
BORDER_CONSTANT = 0
BORDER_REPLICATE = 1
BORDER_REFLECT = 2

# ── VideoCapture props ───────────────────────────────────────────────────────
CAP_PROP_POS_MSEC = 0
CAP_PROP_POS_FRAMES = 1
CAP_PROP_POS_AVI_RATIO = 2
CAP_PROP_FRAME_WIDTH = 3
CAP_PROP_FRAME_HEIGHT = 4
CAP_PROP_FPS = 5
CAP_PROP_FOURCC = 6
CAP_PROP_FRAME_COUNT = 7
CAP_PROP_FORMAT = 8
CAP_PROP_MODE = 9
CAP_PROP_BRIGHTNESS = 10
CAP_PROP_CONTRAST = 11
CAP_PROP_SATURATION = 12
CAP_PROP_AUTO_EXPOSURE = 21
CAP_PROP_BUFFERSIZE = 38

# ── Capture backends ─────────────────────────────────────────────────────────
CAP_ANY = 0
CAP_V4L = 200
CAP_V4L2 = 200
CAP_DSHOW = 700
CAP_MSMF = 1400
CAP_GSTREAMER = 1800
CAP_FFMPEG = 1900

# ── Window flags ─────────────────────────────────────────────────────────────
WINDOW_NORMAL = 0
WINDOW_AUTOSIZE = 1
WINDOW_OPENGL = 4096
WINDOW_FULLSCREEN = 1
WINDOW_FREERATIO = 256
WINDOW_KEEPRATIO = 0
WND_PROP_FULLSCREEN = 0
WND_PROP_AUTOSIZE = 1

# ── Mouse events ─────────────────────────────────────────────────────────────
EVENT_MOUSEMOVE = 0
EVENT_LBUTTONDOWN = 1
EVENT_RBUTTONDOWN = 2
EVENT_MBUTTONDOWN = 3
EVENT_LBUTTONUP = 4
EVENT_RBUTTONUP = 5
EVENT_MBUTTONUP = 6
EVENT_LBUTTONDBLCLK = 7
EVENT_FLAG_LBUTTON = 1
EVENT_FLAG_RBUTTON = 2
EVENT_FLAG_CTRLKEY = 8
EVENT_FLAG_SHIFTKEY = 16

# ── Internal helpers ─────────────────────────────────────────────────────────
_INTER_PIL = {
    INTER_NEAREST: Image.NEAREST,
    INTER_LINEAR:  Image.BILINEAR,
    INTER_CUBIC:   Image.BICUBIC,
    INTER_AREA:    Image.BILINEAR,
    INTER_LANCZOS4: Image.LANCZOS,
}

def _to_bgr(pil_img):
    return np.array(pil_img.convert("RGB"))[:, :, ::-1].copy()

def _from_bgr(arr):
    if arr.ndim == 2:
        return Image.fromarray(arr)
    return Image.fromarray(arr[:, :, ::-1])

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ── Image I/O ────────────────────────────────────────────────────────────────
def imread(filename, flags=IMREAD_COLOR):
    try:
        img = Image.open(filename)
        if flags == IMREAD_GRAYSCALE:
            return np.array(img.convert("L"))
        return _to_bgr(img)
    except Exception:
        return None

def imwrite(filename, img, params=None):
    try:
        _from_bgr(img).save(filename)
        return True
    except Exception:
        return False

def imdecode(buf, flags=IMREAD_COLOR):
    try:
        data = buf.tobytes() if isinstance(buf, np.ndarray) else buf
        img = Image.open(io.BytesIO(data))
        if flags == IMREAD_GRAYSCALE:
            return np.array(img.convert("L"))
        return _to_bgr(img)
    except Exception:
        return None

def imencode(ext, img, params=None):
    try:
        bio = io.BytesIO()
        fmt = ext.lstrip(".").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        _from_bgr(img).save(bio, format=fmt)
        return True, np.frombuffer(bio.getvalue(), dtype=np.uint8)
    except Exception:
        return False, None

# ── Color conversion ─────────────────────────────────────────────────────────
def cvtColor(src, code):
    if code in (COLOR_BGR2RGB, COLOR_RGB2BGR):
        return src[:, :, ::-1].copy() if src.ndim == 3 else src.copy()
    if code == COLOR_BGR2GRAY:
        if src.ndim == 2:
            return src.copy()
        return np.dot(src[..., :3].astype(np.float32),
                      [0.114, 0.587, 0.299]).astype(np.uint8)
    if code == COLOR_RGB2GRAY:
        if src.ndim == 2:
            return src.copy()
        return np.dot(src[..., :3].astype(np.float32),
                      [0.299, 0.587, 0.114]).astype(np.uint8)
    if code in (COLOR_GRAY2BGR, COLOR_GRAY2RGB):
        if src.ndim == 3:
            return src.copy()
        return np.stack([src] * 3, axis=-1)
    if code in (COLOR_BGRA2BGR, COLOR_RGBA2BGR):
        return src[:, :, :3].copy()
    if code == COLOR_BGR2BGRA:
        alpha = np.full(src.shape[:2] + (1,), 255, dtype=np.uint8)
        return np.concatenate([src, alpha], axis=-1)
    if code == COLOR_BGRA2GRAY:
        return cvtColor(src[:, :, :3], COLOR_BGR2GRAY)
    # HSV
    if code == COLOR_BGR2HSV:
        rgb = src[:, :, ::-1]
        return np.array(Image.fromarray(rgb).convert("HSV"))
    return src.copy()

# ── Resize ───────────────────────────────────────────────────────────────────
def resize(src, dsize=None, dst=None, fx=0, fy=0, interpolation=INTER_LINEAR):
    if dsize is not None and dsize != (0, 0):
        w, h = int(dsize[0]), int(dsize[1])
    elif fx > 0 and fy > 0:
        h, w = int(src.shape[0] * fy), int(src.shape[1] * fx)
    else:
        return src.copy()
    resample = _INTER_PIL.get(interpolation, Image.BILINEAR)
    pil = _from_bgr(src).resize((w, h), resample)
    if src.ndim == 2:
        return np.array(pil)
    return _to_bgr(pil) if src.ndim == 3 and src.shape[2] == 3 else np.array(pil)

# ── Geometric ────────────────────────────────────────────────────────────────
def flip(src, flipCode):
    if flipCode == 0:
        return np.flipud(src).copy()
    if flipCode > 0:
        return np.fliplr(src).copy()
    return np.flipud(np.fliplr(src)).copy()

def rotate(src, rotateCode):
    if rotateCode == ROTATE_90_CLOCKWISE:
        return np.rot90(src, -1).copy()
    if rotateCode == ROTATE_180:
        return np.rot90(src, 2).copy()
    if rotateCode == ROTATE_90_COUNTERCLOCKWISE:
        return np.rot90(src, 1).copy()
    return src.copy()

def warpAffine(src, M, dsize, dst=None, flags=INTER_LINEAR,
               borderMode=BORDER_CONSTANT, borderValue=0):
    from PIL import Image as _Img
    pil = _from_bgr(src)
    w, h = dsize
    a, b, c, d, e, f = M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2]
    pil = pil.transform((w, h), _Img.AFFINE, (a, b, c, d, e, f),
                         resample=Image.BILINEAR)
    if src.ndim == 2:
        return np.array(pil)
    return _to_bgr(pil)

def getRotationMatrix2D(center, angle, scale):
    import math
    cx, cy = center
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad) * scale, math.sin(rad) * scale
    return np.array([
        [cos_a, sin_a, (1 - cos_a) * cx - sin_a * cy],
        [-sin_a, cos_a, sin_a * cx + (1 - cos_a) * cy],
    ], dtype=np.float64)

# ── Drawing ──────────────────────────────────────────────────────────────────
def _parse_color(c):
    if isinstance(c, (list, tuple)):
        return tuple(int(x) for x in c[:3])
    return (int(c), int(c), int(c))

def rectangle(img, pt1, pt2=None, color=(0, 255, 0), thickness=1,
              lineType=LINE_8, shift=0):
    if pt2 is None and isinstance(pt1, np.ndarray):
        return img
    x1, y1 = int(pt1[0]), int(pt1[1])
    x2, y2 = int(pt2[0]), int(pt2[1])
    h, w = img.shape[:2]
    x1, y1 = _clamp(x1, 0, w-1), _clamp(y1, 0, h-1)
    x2, y2 = _clamp(x2, 0, w-1), _clamp(y2, 0, h-1)
    c = _parse_color(color)
    if thickness < 0 or thickness == FILLED:
        img[y1:y2, x1:x2] = c
    else:
        t = max(2, thickness)
        img[max(y1,0):min(y1+t,h), max(x1,0):min(x2,w)] = c
        img[max(y2-t,0):min(y2,h), max(x1,0):min(x2,w)] = c
        img[max(y1,0):min(y2,h), max(x1,0):min(x1+t,w)] = c
        img[max(y1,0):min(y2,h), max(x2-t,0):min(x2,w)] = c
    return img

def putText(img, text, org, fontFace=0, fontScale=1, color=(255, 255, 255),
            thickness=1, lineType=LINE_8, bottomLeftOrigin=False):
    try:
        from PIL import ImageDraw, ImageFont
        x, y = int(org[0]), int(org[1])
        # BGR color → RGB for PIL
        c = _parse_color(color)
        rgb_color = (c[2], c[1], c[0]) if len(c) >= 3 else c
        # Convert BGR numpy array to RGB PIL image
        pil = Image.fromarray(img[:, :, ::-1] if img.ndim == 3 else img)
        draw = ImageDraw.Draw(pil)
        font_size = max(10, int(fontScale * 18))
        try:
            font = ImageFont.truetype("/system/fonts/DroidSans.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()
        draw.text((x, y - font_size), str(text), fill=rgb_color, font=font)
        # Convert back to BGR numpy
        result = np.array(pil)
        if img.ndim == 3:
            result = result[:, :, ::-1]
        np.copyto(img, result)
    except Exception:
        pass
    return img

def circle(img, center, radius, color, thickness=1, lineType=LINE_8, shift=0):
    try:
        cx, cy = int(center[0]), int(center[1])
        r = int(radius)
        c = _parse_color(color)
        h, w = img.shape[:2]
        yy, xx = np.ogrid[:h, :w]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2
        if thickness < 0 or thickness == FILLED:
            img[mask <= r * r] = c
        else:
            outer = r * r
            inner = max(0, r - max(1, thickness)) ** 2
            img[(mask <= outer) & (mask >= inner)] = c
    except Exception:
        pass
    return img

def line(img, pt1, pt2, color, thickness=1, lineType=LINE_8, shift=0):
    # Bresenham-style would be complex; simplified version
    try:
        c = _parse_color(color)
        x1, y1 = int(pt1[0]), int(pt1[1])
        x2, y2 = int(pt2[0]), int(pt2[1])
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for i in range(steps + 1):
            t_val = i / steps
            x = int(x1 + (x2 - x1) * t_val)
            y = int(y1 + (y2 - y1) * t_val)
            h, w = img.shape[:2]
            if 0 <= y < h and 0 <= x < w:
                img[y, x] = c
    except Exception:
        pass
    return img

def arrowedLine(img, pt1, pt2, color, thickness=1, line_type=LINE_8,
                shift=0, tipLength=0.1):
    return line(img, pt1, pt2, color, thickness)

def fillPoly(img, pts, color, lineType=LINE_8, shift=0, offset=None):
    return img

def polylines(img, pts, isClosed, color, thickness=1, lineType=LINE_8, shift=0):
    return img

def drawMarker(img, position, color, markerType=0, markerSize=20,
               thickness=1, line_type=LINE_8):
    """Draw a cross marker at the given position."""
    try:
        cx, cy = int(position[0]), int(position[1])
        s = markerSize // 2
        line(img, (cx - s, cy), (cx + s, cy), color, thickness)
        line(img, (cx, cy - s), (cx, cy + s), color, thickness)
    except Exception:
        pass
    return img

def getTextSize(text, fontFace, fontScale, thickness):
    w = int(len(text) * 8 * fontScale)
    h = int(14 * fontScale)
    baseline = int(4 * fontScale)
    return (w, h), baseline

# ── Threshold / morph ────────────────────────────────────────────────────────
def threshold(src, thresh, maxval, type_):
    if type_ & THRESH_OTSU:
        thresh = 128
    if (type_ & 0x7) == THRESH_BINARY:
        out = np.where(src > thresh, maxval, 0).astype(np.uint8)
    else:
        out = np.where(src > thresh, 0, maxval).astype(np.uint8)
    return float(thresh), out

def GaussianBlur(src, ksize, sigmaX, sigmaY=0, borderType=BORDER_CONSTANT):
    # Approximate with PIL
    try:
        from PIL import ImageFilter
        pil = _from_bgr(src)
        r = max(ksize[0], ksize[1]) // 2
        if r > 0:
            pil = pil.filter(ImageFilter.GaussianBlur(radius=r))
        if src.ndim == 2:
            return np.array(pil)
        return _to_bgr(pil)
    except Exception:
        return src.copy()

def blur(src, ksize):
    return GaussianBlur(src, ksize, 0)

def medianBlur(src, ksize):
    try:
        from PIL import ImageFilter
        pil = _from_bgr(src)
        pil = pil.filter(ImageFilter.MedianFilter(size=ksize))
        if src.ndim == 2:
            return np.array(pil)
        return _to_bgr(pil)
    except Exception:
        return src.copy()

def bilateralFilter(src, d, sigmaColor, sigmaSpace, borderType=BORDER_CONSTANT):
    return src.copy()

def Canny(image, threshold1, threshold2, apertureSize=3, L2gradient=False):
    gray = image if image.ndim == 2 else cvtColor(image, COLOR_BGR2GRAY)
    return np.zeros_like(gray)

def dilate(src, kernel, iterations=1, **kw):
    return src.copy()

def erode(src, kernel, iterations=1, **kw):
    return src.copy()

def morphologyEx(src, op, kernel, **kw):
    return src.copy()

def getStructuringElement(shape, ksize, anchor=None):
    return np.ones(ksize, dtype=np.uint8)

# ── Contours ─────────────────────────────────────────────────────────────────
RETR_EXTERNAL = 0
RETR_LIST = 1
RETR_TREE = 3
CHAIN_APPROX_SIMPLE = 2
CHAIN_APPROX_NONE = 1

def findContours(image, mode=RETR_EXTERNAL, method=CHAIN_APPROX_SIMPLE, offset=None):
    return [], None

def drawContours(image, contours, contourIdx, color, thickness=1, **kw):
    return image

def contourArea(contour):
    return 0.0

def arcLength(curve, closed):
    return 0.0

def boundingRect(contour):
    return (0, 0, 0, 0)

def minAreaRect(points):
    return ((0, 0), (0, 0), 0)

def approxPolyDP(curve, epsilon, closed):
    return curve

# ── GUI no-ops (headless Android) ────────────────────────────────────────────
def namedWindow(name, flags=WINDOW_AUTOSIZE):
    pass

def imshow(name, img):
    pass

def waitKey(delay=0):
    if delay > 0:
        time.sleep(delay / 1000.0)
    return -1

def destroyAllWindows():
    pass

def destroyWindow(name):
    pass

def setMouseCallback(windowName, onMouse, param=None):
    pass

def setWindowProperty(winname, prop_id, prop_value):
    pass

def getWindowProperty(winname, prop_id):
    return 0.0

def moveWindow(winname, x, y):
    pass

def resizeWindow(winname, width, height):
    pass

def getWindowImageRect(winname):
    return (0, 0, 0, 0)

# ── VideoCapture ─────────────────────────────────────────────────────────────
class VideoCapture:
    def __init__(self, source=None, apiPreference=CAP_ANY):
        self._opened = False
        self._props = {CAP_PROP_FRAME_WIDTH: 640.0,
                       CAP_PROP_FRAME_HEIGHT: 480.0,
                       CAP_PROP_FPS: 30.0}
        if source is not None:
            self.open(source, apiPreference)

    def open(self, source, apiPreference=CAP_ANY):
        self._opened = False
        return False

    def isOpened(self):
        return self._opened

    def read(self):
        return False, None

    def grab(self):
        return False

    def retrieve(self, flag=0):
        return False, None

    def release(self):
        self._opened = False

    def set(self, prop, value):
        self._props[prop] = float(value)
        return True

    def get(self, prop):
        return self._props.get(prop, 0.0)

# ── VideoWriter ──────────────────────────────────────────────────────────────
def VideoWriter_fourcc(*args):
    return 0

class VideoWriter:
    def __init__(self, filename=None, fourcc=0, fps=0, frameSize=None,
                 isColor=True):
        self._opened = filename is not None

    def isOpened(self):
        return self._opened

    def write(self, frame):
        pass

    def release(self):
        self._opened = False

# ── Misc ─────────────────────────────────────────────────────────────────────
def getVersionString():
    return __version__

def getBuildInformation():
    return "cv2 shim (PIL+numpy) for Termux"

def getNumThreads():
    return 1

def setNumThreads(n):
    pass

def getTickCount():
    return int(time.time() * 1e6)

def getTickFrequency():
    return 1e6

def copyMakeBorder(src, top, bottom, left, right, borderType,
                   value=None):
    if value is None:
        value = 0
    if isinstance(value, (list, tuple)):
        value = value[:src.shape[2]] if src.ndim == 3 else value[0]
    return np.pad(src,
                  ((top, bottom), (left, right)) if src.ndim == 2
                  else ((top, bottom), (left, right), (0, 0)),
                  mode='constant', constant_values=0)

def LUT(src, lut):
    return lut[src]

def addWeighted(src1, alpha, src2, beta, gamma):
    return np.clip(src1.astype(np.float32) * alpha +
                   src2.astype(np.float32) * beta + gamma,
                   0, 255).astype(np.uint8)

def convertScaleAbs(src, alpha=1, beta=0):
    return np.clip(np.abs(src.astype(np.float32) * alpha + beta),
                   0, 255).astype(np.uint8)

def normalize(src, dst=None, alpha=0, beta=255, norm_type=None, dtype=-1, mask=None):
    mn, mx = src.min(), src.max()
    if mx == mn:
        return np.full_like(src, alpha, dtype=np.uint8)
    out = ((src - mn) / (mx - mn) * (beta - alpha) + alpha)
    return out.astype(np.uint8)

def split(m):
    return [m[:, :, i] for i in range(m.shape[2])]

def merge(mv):
    return np.stack(mv, axis=-1)

def minMaxLoc(src, mask=None):
    mn = float(src.min())
    mx = float(src.max())
    mn_idx = np.unravel_index(src.argmin(), src.shape)
    mx_idx = np.unravel_index(src.argmax(), src.shape)
    return mn, mx, (int(mn_idx[1]), int(mn_idx[0])), (int(mx_idx[1]), int(mx_idx[0]))

# ── Needed by some ultralytics checks ────────────────────────────────────────
IMWRITE_JPEG_QUALITY = 1
IMWRITE_PNG_COMPRESSION = 16

# DNN placeholder (not used — YOLO uses PyTorch)
class dnn:
    @staticmethod
    def blobFromImage(*a, **kw):
        return np.zeros((1, 3, 1, 1), dtype=np.float32)
    @staticmethod
    def readNetFromONNX(*a, **kw):
        return None

print("[cv2 shim] PIL+numpy backend loaded (Termux)")
