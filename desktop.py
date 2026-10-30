"""Windows client-area capture and guarded mouse input."""
import ctypes
from ctypes import wintypes
import os
import threading
import time
from PIL import ImageGrab
from core import StopRun
from vision import normalize

def dpi_awareness():
    if os.name == 'nt':
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()

class Desktop:
    def __init__(self, stop=None):
        if os.name != 'nt':
            raise RuntimeError('此脚本仅支持Windows')
        self.stop = stop if stop is not None else threading.Event()
        self.u = ctypes.windll.user32
        self.u.GetForegroundWindow.restype = wintypes.HWND
        self.u.mouse_event.argtypes = [wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]
        self.u.mouse_event.restype = None
        for name in ('GetWindowTextW', 'GetWindowTextLengthW', 'GetClientRect',
                     'ClientToScreen', 'IsWindow', 'IsIconic'):
            fn = getattr(self.u, name)
            if name == 'GetWindowTextW':
                fn.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            elif name == 'GetClientRect':
                fn.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            elif name == 'ClientToScreen':
                fn.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
            else:
                fn.argtypes = [wintypes.HWND]
        self.u.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.u.GetAsyncKeyState.restype = ctypes.c_short
        self.hwnd = self.u.GetForegroundWindow()
        length = self.u.GetWindowTextLengthW(self.hwnd)
        name = ctypes.create_unicode_buffer(length+1)
        self.u.GetWindowTextW(self.hwnd, name, length+1)
        if name.value.strip().lower() not in ('炉石传说', 'hearthstone'):
            raise StopRun('请在倒计时结束前切回炉石传说收藏界面')
        self.rect = self.geometry()
        # Reject unsupported aspect ratio before any mouse input.
        w, h = self.rect[2]-self.rect[0], self.rect[3]-self.rect[1]
        normalize(__import__('PIL.Image', fromlist=['Image']).new('RGB', (w, h)))

    def geometry(self):
        rect = wintypes.RECT()
        origin = wintypes.POINT(0, 0)
        if not self.u.GetClientRect(self.hwnd, ctypes.byref(rect)):
            raise StopRun('无法获取游戏窗口')
        if not self.u.ClientToScreen(self.hwnd, ctypes.byref(origin)):
            raise StopRun('无法定位游戏窗口')
        return (origin.x, origin.y, origin.x + rect.right, origin.y + rect.bottom)

    def check(self):
        if self.u.GetAsyncKeyState(0x77) & 0x8001:
            self.stop.set()
        if self.stop.is_set():
            raise StopRun('已停止（F8或停止按钮）')
        if (not self.u.IsWindow(self.hwnd) or self.u.IsIconic(self.hwnd)
                or self.u.GetForegroundWindow() != self.hwnd):
            raise StopRun('游戏失去焦点，已停止；重新扫描后再执行')
        if self.geometry() != self.rect:
            raise StopRun('游戏窗口移动或尺寸改变，已停止')

    def sleep(self, seconds):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            self.check()
            time.sleep(min(.05, max(0, deadline-time.monotonic())))

    def capture(self):
        self.check()
        image = ImageGrab.grab(bbox=self.rect, all_screens=True)
        self.check()
        return normalize(image)

    def click(self, x, y, right=False):
        self.check()
        l, t, r, b = self.rect
        self.u.SetCursorPos(l + round(x*(r-l)/2048), t + round(y*(b-t)/1152))
        self.sleep(.12)
        self.check()
        down, up = (0x0008, 0x0010) if right else (0x0002, 0x0004)
        self.u.mouse_event(down, 0, 0, 0, 0)
        try:
            self.sleep(.08)
        finally:
            self.u.mouse_event(up, 0, 0, 0, 0)


    def scroll(self, amount):
        if amount not in (-120, 120):
            raise ValueError('每次只能翻一页')
        self.check()
        l,t,r,b=self.rect
        self.u.SetCursorPos(l+round(950*(r-l)/2048),t+round(550*(b-t)/1152))
        self.sleep(.1)
        self.check()
        # The game on this PC advances for positive native wheel data.
        self.u.mouse_event(0x0800,0,0,(-amount) & 0xffffffff,0)
        self.sleep(.75)
