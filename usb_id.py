import ctypes, ctypes.util, sys
L = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so", use_errno=True)

class C(ctypes.Structure):
    _fields_ = [
        ("a", ctypes.c_uint8), ("b", ctypes.c_uint8),
        ("c", ctypes.c_uint16), ("d", ctypes.c_uint16),
        ("e", ctypes.c_uint16), ("f", ctypes.c_uint32),
        ("g", ctypes.c_void_p),
    ]

CTRL = (3 << 30) | (ctypes.sizeof(C) << 16) | (ord("U") << 8) | 0
fd = int(sys.argv[-1])
buf = (ctypes.c_uint8 * 18)()
t = C()
t.a = 0x80; t.b = 6; t.c = 0x0100; t.d = 0; t.e = 18
t.f = 3000; t.g = ctypes.cast(buf, ctypes.c_void_p)
r = L.ioctl(fd, CTRL, ctypes.byref(t))
if r < 0:
    print("ERREUR lecture descripteur")
else:
    vid = buf[8] | (buf[9] << 8)
    pid = buf[10] | (buf[11] << 8)
    if vid == 0x2341:
        print(f"ARDUINO  VID={vid:04X} PID={pid:04X}")
    else:
        print(f"AUTRE    VID={vid:04X} PID={pid:04X}")
