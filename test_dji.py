"""Test DJI UVC via libuvc sur Android/Termux"""
import ctypes, sys, os

fd = int(sys.argv[-1])
print(f"DJI fd={fd}")

LIBUVC = os.path.join(os.path.expanduser("~"), "libuvc", "build", "libuvc.so")
lib = ctypes.CDLL(LIBUVC)

ctx = ctypes.c_void_p()
devh = ctypes.c_void_p()

r = lib.uvc_init(ctypes.byref(ctx), None)
print(f"uvc_init: {r} ({'OK' if r==0 else 'FAIL'})")

r = lib.uvc_wrap(fd, ctx, ctypes.byref(devh))
print(f"uvc_wrap: {r} ({'OK' if r==0 else 'FAIL'})")

if r != 0:
    print("Camera UVC non accessible - verifier mode Webcam sur la DJI")
    lib.uvc_exit(ctx)
    sys.exit(1)

ctrl = (ctypes.c_uint8 * 128)()
found = False
for fmt, name in [(6, "MJPEG"), (4, "YUYV")]:
    for w, h in [(640, 480), (1280, 720), (1920, 1080), (320, 240)]:
        r = lib.uvc_get_stream_ctrl_format_size(devh, ctrl, fmt, w, h, 30)
        tag = "OK" if r == 0 else "fail"
        print(f"  {name} {w}x{h}@30: {tag}")
        if r == 0:
            found = True

if found:
    print("\nDJI UVC fonctionne ! Au moins un format supporte.")
else:
    print("\nAucun format trouve - la DJI est-elle en mode Webcam ?")

lib.uvc_close(devh)
lib.uvc_exit(ctx)
print("Test termine")
