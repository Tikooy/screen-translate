"""区域翻译：把透明悬浮框覆盖的屏幕区域持续截图 → OCR → 变化检测 → 翻译。

设计目标：在后台线程里循环"截图 → OCR → 比对"；只有识别文字发生变化
（且不是目标语言）才调用翻译引擎，避免内容不变或已是目标语言时重复翻译、
浪费 API 额度。翻译结果写入本对象，供区域框前端轮询展示。
"""
import re
import threading
import time

from utils.screenshot import capture_rect_png, system_dpi_scale

# 目标语言对应的"特征字符"Unicode 区间与判定阈值（命中字符占字母数的比例）。
# 拉丁系语言（EN/FR/DE 等）共用拉丁字母，无法仅靠脚本区分语种，故单独走
# "拉丁字母占比"分支。这里是最佳努力的本地启发式，用于省额度，非精确语种识别。
_SCRIPT_RANGES: dict[str, tuple[list[tuple[int, int]], float]] = {
    "ZH": ([(0x3400, 0x4DBF), (0x4E00, 0x9FFF)], 0.5),  # CJK 统一表意文字
    "JA": ([(0x3040, 0x309F), (0x30A0, 0x30FF)], 0.05),  # 平假名/片假名（日语独有）
    "KO": ([(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)], 0.3),  # 谚文
    "RU": ([(0x0400, 0x04FF)], 0.5),  # 西里尔
    "UK": ([(0x0400, 0x04FF)], 0.5),
    "BG": ([(0x0400, 0x04FF)], 0.5),
    "EL": ([(0x0370, 0x03FF), (0x1F00, 0x1FFF)], 0.5),  # 希腊
    "AR": ([(0x0600, 0x06FF)], 0.5),  # 阿拉伯
    "TH": ([(0x0E00, 0x0E7F)], 0.5),  # 泰文
}

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """归一化用于变化比对：压缩空白、去首尾空格。"""
    return _WS_RE.sub(" ", text or "").strip()


def _looks_like_target(text: str, target_lang: str) -> bool:
    """本地启发式判断文字是否"已是目标语言"，用于跳过翻译以省额度。"""
    if not text:
        return False
    lang = (target_lang or "").upper()
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False

    entry = _SCRIPT_RANGES.get(lang)
    if entry:
        ranges, threshold = entry
        hit = sum(1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ranges))
        return hit / len(letters) >= threshold

    # 拉丁系目标语言：绝大多数字母落在拉丁区（含变音字母）即视为已是目标语言
    latin = sum(1 for c in letters if ord(c) < 0x0370)
    return latin / len(letters) >= 0.8


class RegionManager:
    """区域翻译循环管理器。线程安全；由 run.py 注入窗口引用，前端经桥调用 start/stop。"""

    def __init__(self, app):
        self._app = app
        self._window = None
        self._lock = threading.RLock()  # 可重入：start() 持锁时会调用 _update()
        self._stop_event = threading.Event()
        self._thread = None
        self._running = False
        self._seq = 0
        self._result: dict = {
            "running": False,
            "status": "idle",
            "source": "",
            "translated": "",
            "note": "",
            "error": "",
            "seq": 0,
        }

    def attach_window(self, window) -> None:
        self._window = window

    # ---- 对外控制（前端桥调用）----
    def start(self) -> dict:
        from backend.config import settings

        with self._lock:
            if self._running:
                return {"ok": True, "running": True}
            provider = getattr(self._app.state, "provider", None)
            if provider is None or not provider.available():
                self._update(status="error", note="未配置翻译引擎 API Key，请在右上角设置中填写")
                return {"ok": False, "error": "未配置翻译引擎 API Key"}
            self._target_lang = (settings.word_pick_lang or "ZH").upper()
            self._interval = float(settings.region_poll_interval or 2.0)
            self._last_norm = None
            self._running = True
            self._stop_event.clear()
            self._update(status="capturing", note="正在识别区域文字…")

        self._thread = threading.Thread(target=self._loop, daemon=True, name="region-translate")
        self._thread.start()
        return {"ok": True, "running": True}

    def stop(self) -> dict:
        with self._lock:
            self._running = False
        self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)
        self._update(status="idle", source="", translated="", note="", error="")
        return {"ok": True, "running": False}

    def latest(self) -> dict:
        with self._lock:
            return dict(self._result)

    # ---- 内部循环 ----
    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as exc:  # 单轮异常不中断整个循环
                self._update(status="error", error=str(exc), note="")
            self._stop_event.wait(self._interval)

    def _tick(self) -> None:
        window = self._window
        if window is None:
            self._update(status="error", error="区域窗口未就绪", note="")
            return

        left, top, width, height = self._window_rect(window)
        png = self._capture(window, left, top, width, height)
        if png is None:
            return

        ocr = getattr(self._app.state, "ocr", None)
        if ocr is None:
            self._update(status="error", error="OCR 服务未就绪", note="")
            return

        text = (ocr.recognize(png) or "").strip()
        norm = _normalize(text)

        if not norm:
            # 区域内无文字
            self._update(status="empty", source="", translated="", note="区域内未识别到文字", error="")
            return

        if norm == self._last_norm:
            # 内容未变化：保留上一次译文，不重复翻译
            with self._lock:
                self._seq += 1
                self._result.update(
                    {
                        "status": "unchanged",
                        "note": "内容未变化，未重复翻译",
                        "seq": self._seq,
                    }
                )
            return

        self._last_norm = norm

        if _looks_like_target(text, self._target_lang):
            # 已是目标语言：不翻译
            self._update(status="already_target", source=text, translated="", note="检测到区域内已是目标语言，已跳过翻译")
            return

        # 新内容：翻译
        self._update(status="translating", source=text, translated="", note="正在翻译…")
        provider = getattr(self._app.state, "provider", None)
        if provider is None or not provider.available():
            self._update(status="error", source=text, note="未配置翻译引擎 API Key", error="未配置翻译引擎 API Key")
            return
        try:
            translated = provider.translate(text, self._target_lang, None)
        except Exception as exc:
            self._update(status="error", source=text, note="", error=str(exc))
            return
        self._update(status="done", source=text, translated=translated, note="")

    def _window_rect(self, window) -> tuple[int, int, int, int]:
        """窗口逻辑像素矩形 → 物理像素（mss 用）。"""
        scale = system_dpi_scale()
        left = round(window.x * scale)
        top = round(window.y * scale)
        width = max(1, round(window.width * scale))
        height = max(1, round(window.height * scale))
        return left, top, width, height

    def _capture(self, window, left: int, top: int, width: int, height: int) -> bytes | None:
        """隐藏悬浮框后抓取区域，抓完恢复，避免把框本身截进图里。"""
        try:
            window.hide()
            time.sleep(0.15)  # 等隐藏真正生效
            return capture_rect_png(left, top, width, height)
        except Exception as exc:
            self._update(status="error", error=f"区域截图失败：{exc}", note="")
            return None
        finally:
            try:
                window.show()
            except Exception:
                pass

    def _update(self, status: str, source: str = "", translated: str = "", note: str = "", error: str = "") -> None:
        with self._lock:
            self._seq += 1
            self._result.update(
                {
                    "running": self._running,
                    "status": status,
                    "source": source,
                    "translated": translated,
                    "note": note,
                    "error": error,
                    "seq": self._seq,
                }
            )
