"""
android_usb_serial.py – USB serial via raw USBDEVFS ioctl (Android/Termux)
Supporte CH340G (clones) et CDC-ACM (ATmega16U2 / Arduino UNO R3).
Zero dépendance externe.  Utilise libc.ioctl directement.

Usage :
  termux-usb -r -e "python3 tracker_rover.py" /dev/bus/usb/001/004
"""
import ctypes, ctypes.util, os, struct, time, errno

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so", use_errno=True)
_ioctl = _libc.ioctl
_ioctl.restype = ctypes.c_int

# ── Structures USBDEVFS ────────────────────────────────────────────────────
class _Ctrl(ctypes.Structure):
    _fields_ = [("bmRT",ctypes.c_uint8),("bReq",ctypes.c_uint8),
                ("wVal",ctypes.c_uint16),("wIdx",ctypes.c_uint16),
                ("wLen",ctypes.c_uint16),("tout",ctypes.c_uint32),
                ("data",ctypes.c_void_p)]

class _Bulk(ctypes.Structure):
    _fields_ = [("ep",ctypes.c_uint),("len",ctypes.c_uint),
                ("tout",ctypes.c_uint),("data",ctypes.c_void_p)]

# ── ioctl numbers ──────────────────────────────────────────────────────────
_PTR = ctypes.sizeof(ctypes.c_void_p)

def _iowr(t,n,sz): return (3<<30)|(sz<<16)|(ord(t)<<8)|n
def _ior(t,n,sz):  return (2<<30)|(sz<<16)|(ord(t)<<8)|n

CTRL  = _iowr("U", 0, ctypes.sizeof(_Ctrl))   # 24 on 64b, 16 on 32b
BULK  = _iowr("U", 2, ctypes.sizeof(_Bulk))
CLAIM = _ior("U", 15, 4)
_T = 3000

def _check(ret, msg="ioctl"):
    if ret < 0:
        e = ctypes.get_errno()
        raise OSError(e, f"{msg}: {os.strerror(e)}")
    return ret

def ctrl(fd,rt,rq,v,i,d):
    n=len(d); buf=(ctypes.c_uint8*max(n,1))(*d[:n])
    t=_Ctrl(); t.bmRT=rt; t.bReq=rq; t.wVal=v&0xFFFF; t.wIdx=i&0xFFFF
    t.wLen=n; t.tout=_T; t.data=ctypes.cast(buf,ctypes.c_void_p)
    return _check(_ioctl(fd, CTRL, ctypes.byref(t)), "ctrl")

def claim(fd,iface):
    v=ctypes.c_uint(iface)
    return _check(_ioctl(fd, CLAIM, ctypes.byref(v)), f"claim({iface})")

def bw(fd,ep,d):
    buf=(ctypes.c_uint8*len(d))(*d); t=_Bulk()
    t.ep=ep&0xFF; t.len=len(d); t.tout=_T
    t.data=ctypes.cast(buf,ctypes.c_void_p)
    return _check(_ioctl(fd, BULK, ctypes.byref(t)), "bulk_write")

def br(fd,ep,sz):
    buf=(ctypes.c_uint8*sz)(); t=_Bulk()
    t.ep=(ep|0x80)&0xFF; t.len=sz; t.tout=_T
    t.data=ctypes.cast(buf,ctypes.c_void_p)
    try:
        n=_check(_ioctl(fd, BULK, ctypes.byref(t)), "bulk_read")
        return bytes(buf[:n])
    except OSError:
        return b""

def get_vid(fd):
    buf=(ctypes.c_uint8*18)(); t=_Ctrl()
    t.bmRT=0x80; t.bReq=0x06; t.wVal=0x0100; t.wIdx=0; t.wLen=18
    t.tout=_T; t.data=ctypes.cast(buf,ctypes.c_void_p)
    r = _ioctl(fd, CTRL, ctypes.byref(t))
    if r < 0:
        print(f"[USB] GET_DESCRIPTOR err={ctypes.get_errno()} ({os.strerror(ctypes.get_errno())})")
        return 0
    vid = buf[8]|(buf[9]<<8)
    pid = buf[10]|(buf[11]<<8)
    print(f"[USB] VID={vid:04X} PID={pid:04X}")
    return vid

def _init_ch340(fd,baud):
    claim(fd,0)
    ctrl(fd,0xC0,0x5F,0,0,[0,0])
    ctrl(fd,0x40,0xA1,0,0,[])
    f=1532620800//baud; d=3
    while f>0xFFF0 and d: f>>=3; d-=1
    f=0x10000-f; a=(f&0xFF00)|d; b=f&0xFF
    ctrl(fd,0x40,0x9A,0x1312,a,[])
    ctrl(fd,0x40,0x9A,0x0F2C,b,[])
    ctrl(fd,0x40,0x9A,0x2518,0x00C3,[])
    ctrl(fd,0x40,0xA4,0xFC,0,[])

def _init_cdc(fd,baud):
    claim(fd,0); claim(fd,1)
    lc=list(struct.pack('<IBBB',baud,0,0,8))
    ctrl(fd,0x21,0x20,0,0,lc)
    ctrl(fd,0x21,0x22,0x0003,0,[])

class UsbSerial:
    def __init__(self, fd, baud=115200):
        self.fd=fd; self._buf=b""
        print(f"[USB] fd={fd} ptr_sz={_PTR} ctrl_ioctl=0x{CTRL:08X} claim_ioctl=0x{CLAIM:08X}")
        vid=get_vid(fd)
        if vid==0x1A86:
            print("[USB] CH340"); _init_ch340(fd,baud)
            self._ei=0x82; self._eo=0x02
        else:
            print("[USB] CDC-ACM"); _init_cdc(fd,baud)
            self._ei=0x83; self._eo=0x04
        self.port=f"usb:{fd}"
        time.sleep(0.3)
        print(f"[USB] Prêt @ {baud} baud")

    def write(self,data):
        if isinstance(data,str): data=data.encode()
        bw(self.fd,self._eo,list(data))

    def readline(self):
        while b'\n' not in self._buf:
            c=br(self.fd,self._ei,64)
            if c: self._buf+=c
            else: break
        if b'\n' in self._buf:
            l,self._buf=self._buf.split(b'\n',1); return l+b'\n'
        r=self._buf; self._buf=b""; return r

    def close(self): pass
