import ctypes
import io

import mss
from PIL import Image


def system_dpi_scale() -> float:
    """系统 DPI 缩放系数（物理像素 / 逻辑像素）。

    pywebview 在 Windows 上以 SetProcessDPIAware 启动（系统级 DPI 感知），
    其 Window.x/y/width/height 均为逻辑像素；mss 截图使用的是物理像素。
    因此抓取窗口区域前需按此系数换算。
    """
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


def capture_screen_png() -> bytes:
    """抓取全屏（多显示器合并）并返回 PNG 字节。"""
    with mss.mss() as sct:
        monitor = sct.monitors[0]  # monitors[0] 为所有屏幕合并区域
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def capture_rect_png(left: int, top: int, width: int, height: int) -> bytes:
    """抓取虚拟屏幕上指定区域（物理像素坐标）并返回 PNG 字节。

    left/top 可为负（如框位于主显示器左侧的副屏），与 mss 虚拟屏幕坐标系一致。
    """
    width = max(1, int(width))
    height = max(1, int(height))
    with mss.mss() as sct:
        shot = sct.grab({"left": int(left), "top": int(top), "width": width, "height": height})
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
