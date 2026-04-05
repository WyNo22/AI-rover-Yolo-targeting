"""
uvc_camera.py – Capture UVC via libuvc sur Android/Termux
Utilise uvc_wrap() pour ouvrir une caméra USB via le fd de termux-usb.
Fournit une interface compatible OpenCV (read() retourne un numpy array).

Usage :
  termux-usb -r -e "python3 tracker_rover.py" /dev/bus/usb/001/XXX
"""
import ctypes, ctypes.util, os, sys, time, threading
import numpy as np

_LIBUVC_PATH = os.path.join(os.path.expanduser("~"), "libuvc", "build", "libuvc.so")

# ── UVC frame formats ─────────────────────────────────────────────────────
UVC_FRAME_FORMAT_YUYV = 4
UVC_FRAME_FORMAT_MJPEG = 6

# ── Structures libuvc ──────────────────────────────────────────────────────
class _uvc_stream_ctrl(ctypes.Structure):
    _fields_ = [("raw", ctypes.c_uint8 * 128)]

class _uvc_frame(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("data_bytes", ctypes.c_size_t),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("frame_format", ctypes.c_int),
        ("step", ctypes.c_size_t),
        ("sequence", ctypes.c_uint32),
    ]

_FRAME_CB_TYPE = ctypes.CFUNCTYPE(None, ctypes.POINTER(_uvc_frame), ctypes.c_void_p)


class UvcCamera:
    """Interface caméra UVC via libuvc, compatible OpenCV."""

    def __init__(self, fd, width=640, height=480, fps=30):
        self._lib = ctypes.CDLL(_LIBUVC_PATH)
        self._setup_api()

        self._lock = threading.Lock()
        self._frame = None
        self._running = False

        # Android fix: libusb_init_context with option 2 (NO_DEVICE_DISCOVERY)
        # libusb_init(NULL) fails on Android (-1), but init_context(opt=2) works.
        class _LibusbInitOpt(ctypes.Structure):
            _fields_ = [("option", ctypes.c_uint32),
                        ("_pad",   ctypes.c_uint32),
                        ("value",  ctypes.c_uint64)]

        self._usb_ctx = None
        try:
            _libusb = ctypes.CDLL("libusb-1.0.so")
            _libusb.libusb_init_context.argtypes = [
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.c_void_p,
                ctypes.c_int]
            _libusb.libusb_init_context.restype = ctypes.c_int

            opts = (_LibusbInitOpt * 1)()
            opts[0].option = 2   # NO_DEVICE_DISCOVERY (confirmed working)
            opts[0].value  = 0
            usb_ctx = ctypes.c_void_p()
            r_usb = _libusb.libusb_init_context(ctypes.byref(usb_ctx), opts, 1)
            if r_usb == 0:
                self._usb_ctx = usb_ctx
                print("[UVC] libusb context OK (NO_DEVICE_DISCOVERY)")
            else:
                print(f"[UVC] libusb_init_context failed: {r_usb}")
        except Exception as e:
            print(f"[UVC] libusb init error: {e}")

        # Init UVC context (pass our libusb ctx to bypass /dev/bus/usb scan)
        self._ctx = ctypes.c_void_p()
        r = self._lib.uvc_init(ctypes.byref(self._ctx), self._usb_ctx)
        if r != 0:
            raise RuntimeError(f"uvc_init failed: {r}")

        # Wrap fd
        self._devh = ctypes.c_void_p()
        r = self._lib.uvc_wrap(fd, self._ctx, ctypes.byref(self._devh))
        if r != 0:
            self._lib.uvc_exit(self._ctx)
            raise RuntimeError(f"uvc_wrap failed: {r} (DJI en mode Webcam ?)")

        # Negotiate stream format
        self._ctrl = _uvc_stream_ctrl()
        fmt_ok = False
        for fmt, name in [(UVC_FRAME_FORMAT_MJPEG, "MJPEG"),
                          (UVC_FRAME_FORMAT_YUYV, "YUYV")]:
            r = self._lib.uvc_get_stream_ctrl_format_size(
                self._devh, ctypes.byref(self._ctrl), fmt, width, height, fps)
            if r == 0:
                self._fmt = fmt
                self._fmt_name = name
                fmt_ok = True
                print(f"[UVC] {name} {width}x{height}@{fps} OK")
                break
            print(f"[UVC] {name} {width}x{height}@{fps} : non supporté")

        if not fmt_ok:
            self._lib.uvc_close(self._devh)
            self._lib.uvc_exit(self._ctx)
            raise RuntimeError("Aucun format UVC supporté par la caméra")

        self._width = width
        self._height = height

        # Keep callback reference alive
        self._cb = _FRAME_CB_TYPE(self._frame_callback)

        # Start streaming
        r = self._lib.uvc_start_streaming(
            self._devh, ctypes.byref(self._ctrl), self._cb, None, 0)
        if r != 0:
            self._lib.uvc_close(self._devh)
            self._lib.uvc_exit(self._ctx)
            raise RuntimeError(f"uvc_start_streaming failed: {r}")

        self._running = True
        print(f"[UVC] Streaming démarré ({self._fmt_name})")

    def _setup_api(self):
        lib = self._lib
        lib.uvc_init.restype = ctypes.c_int
        lib.uvc_init.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
        lib.uvc_wrap.restype = ctypes.c_int
        lib.uvc_wrap.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                 ctypes.POINTER(ctypes.c_void_p)]
        lib.uvc_get_stream_ctrl_format_size.restype = ctypes.c_int
        lib.uvc_get_stream_ctrl_format_size.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.uvc_start_streaming.restype = ctypes.c_int
        lib.uvc_start_streaming.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, _FRAME_CB_TYPE,
            ctypes.c_void_p, ctypes.c_uint8]
        lib.uvc_stop_streaming.restype = None
        lib.uvc_stop_streaming.argtypes = [ctypes.c_void_p]
        lib.uvc_close.restype = None
        lib.uvc_close.argtypes = [ctypes.c_void_p]
        lib.uvc_exit.restype = None
        lib.uvc_exit.argtypes = [ctypes.c_void_p]

    def _frame_callback(self, frame_ptr, user_ptr):
        """Callback appelé par libuvc pour chaque frame."""
        try:
            f = frame_ptr.contents
            if f.data_bytes == 0 or f.data is None:
                return
            raw = (ctypes.c_uint8 * f.data_bytes).from_address(f.data)
            data = bytes(raw)

            if self._fmt == UVC_FRAME_FORMAT_MJPEG:
                import cv2
                arr = np.frombuffer(data, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            elif self._fmt == UVC_FRAME_FORMAT_YUYV:
                import cv2
                arr = np.frombuffer(data, dtype=np.uint8).reshape(
                    (f.height, f.width, 2))
                img = cv2.cvtColor(arr, cv2.COLOR_YUV2BGR_YUYV)
            else:
                return

            if img is not None:
                with self._lock:
                    self._frame = img
        except Exception:
            pass

    def read(self):
        """Retourne (ret, frame) compatible OpenCV."""
        with self._lock:
            if self._frame is not None:
                return True, self._frame.copy()
        return False, None

    def isOpened(self):
        return self._running

    def release(self):
        if self._running:
            self._running = False
            try:
                self._lib.uvc_stop_streaming(self._devh)
            except Exception:
                pass
            self._lib.uvc_close(self._devh)
            self._lib.uvc_exit(self._ctx)
            print("[UVC] Caméra fermée")

    def get(self, prop):
        """Compatibilité cv2.VideoCapture.get()"""
        import cv2
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return self._width
        elif prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return self._height
        return 0
