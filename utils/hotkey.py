"""取词翻译的全局热键服务。

按下热键 → 模拟 Ctrl+C 复制选中文本 → 读取剪贴板 → 恢复原剪贴板 →
把文本 + 鼠标坐标 POST 给本地后端，气泡窗口随后轮询展示译文。
"""
import ctypes
import json
import threading
import time
import urllib.request
from typing import Callable

import keyboard
import pyperclip

from backend.config import settings


def _cursor_pos() -> tuple[int, int]:
    class _POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _cursor_pos_logical() -> tuple[int, int]:
    """光标物理像素坐标转逻辑像素（pywebview 窗口定位用），高 DPI 缩放时避免气泡偏移。

    优先按光标所在显示器的 DPI 换算（与 pywebview 内部 GetDpiForWindow 一致），
    退化到系统 DPI，再退化到 1.0（无缩放）。
    """
    x, y = _cursor_pos()
    scale = 1.0
    try:
        from ctypes import wintypes

        hmonitor = ctypes.windll.user32.MonitorFromPoint(wintypes.POINT(x, y), 2)  # MONITOR_DEFAULTTONEAREST
        dpi_x, dpi_y = wintypes.UINT(), wintypes.UINT()
        if ctypes.windll.shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
            scale = dpi_x.value / 96.0
        else:
            scale = ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        scale = 1.0
    return round(x / scale), round(y / scale)


class HotkeyService:
    def __init__(
        self,
        hotkey: str | None = None,
        target_lang: str | None = None,
        on_pick: Callable[[], None] | None = None,
    ):
        """on_pick 在每次取词前调用，供主程序首次按热键时创建取词框窗口。"""
        self._hotkey = hotkey or settings.word_pick_hotkey
        self._target_lang = target_lang or settings.word_pick_lang
        self._url = f"http://{settings.host}:{settings.port}/api/wordpick"
        self._on_pick = on_pick
        self._registered_hotkey: str | None = None

    def _register_hotkey(self, hotkey: str) -> None:
        keyboard.add_hotkey(hotkey, self.trigger_now)
        self._registered_hotkey = hotkey
        print(f"[取词] 全局热键已注册：{hotkey}")

    def _unregister_hotkey(self) -> None:
        if self._registered_hotkey:
            try:
                keyboard.remove_hotkey(self._registered_hotkey)
            finally:
                self._registered_hotkey = None

    def start(self):
        if self._registered_hotkey:
            return
        try:
            self._register_hotkey(self._hotkey)
        except Exception as e:
            print(f"[取词] 热键注册失败：{e}")

    def stop(self):
        self._unregister_hotkey()

    def reconfigure(self, hotkey: str, target_lang: str):
        """运行中修改热键与取词目标语言：注销旧热键并注册新热键。"""
        self._unregister_hotkey()
        self._hotkey = hotkey
        self._target_lang = target_lang
        try:
            self._register_hotkey(hotkey)
        except Exception as e:
            print(f"[取词] 热键注册失败：{e}")

    def trigger_now(self):
        """复制当前选中文本并提交翻译（供热键与托盘菜单共用）。"""
        threading.Thread(target=self.pick_and_submit, daemon=True).start()

    def pick_and_submit(self):
        """同步执行：取光标位置、复制选中文本、确保取词框就绪、提交翻译。

        先复制再建取词框，避免首次建窗（hidden=True 的 Show→Hide 会触发
        on_shown 聚焦）干扰复制所需的焦点状态。热键与托盘菜单共用。
        """
        x, y = _cursor_pos_logical()
        selected = self._copy_selection()
        if self._on_pick:
            self._on_pick()
        self._submit(selected, x, y)

    def _hotkey_modifiers(self) -> list[str]:
        """解析热键字符串中的修饰键，如 ctrl+alt+t -> ['ctrl', 'alt']。"""
        mods = {"ctrl", "alt", "shift", "win", "cmd", "windows"}
        return [p.strip().lower() for p in self._hotkey.split("+") if p.strip().lower() in mods]

    def _wait_hotkey_released(self):
        """热键触发时修饰键仍被按住，此刻注入 ctrl+c 会被系统识别成 Ctrl+Alt+C，
        目标程序往往不认，复制失败。等修饰键松开后再注入干净的控制组合。"""
        deadline = time.monotonic() + 5.0
        mods = self._hotkey_modifiers()
        while time.monotonic() < deadline:
            if not any(keyboard.is_pressed(m) for m in mods):
                return
            time.sleep(0.02)

    def _copy_selection(self) -> str:
        """模拟 Ctrl+C 复制选中文本，结束后恢复原剪贴板。返回新复制到的文本。"""
        try:
            original = pyperclip.paste()
        except Exception:
            original = ""
        try:
            self._wait_hotkey_released()
            keyboard.send("ctrl+c")
            time.sleep(0.2)  # 等待目标程序把内容写入剪贴板（慢应用需略长）
            selected = pyperclip.paste()
        except Exception:
            selected = ""
        finally:
            try:
                if original:
                    pyperclip.copy(original)
            except Exception:
                pass
        # 剪贴板内容未变化说明没有可复制的选中文本
        if selected == original:
            return ""
        return selected.strip()

    def _submit(self, text: str, x: int, y: int):
        payload = json.dumps(
            {"text": text, "target_lang": self._target_lang, "cursor_x": x, "cursor_y": y}
        ).encode("utf-8")
        req = urllib.request.Request(
            self._url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except Exception:
            pass  # 本地后端未启动时静默丢弃，避免热键回调抛异常
