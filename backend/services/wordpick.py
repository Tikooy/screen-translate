import threading
import time
import uuid


class WordPickManager:
    """保存最近一次取词翻译结果，供气泡窗口轮询。支持逐句流式写入。线程安全。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._latest = None

    def begin_stream(self, source: str, cursor_x: int, cursor_y: int) -> dict:
        """开始一次流式翻译：先占位（translated 为空、done=False），后续 append_stream 逐句写入。"""
        result = {
            "id": str(uuid.uuid4()),
            "source": source,
            "translated": "",
            "hint": False,
            "cursor_x": cursor_x,
            "cursor_y": cursor_y,
            "created_at": time.time(),
            "done": False,
            "error": "",
        }
        with self._lock:
            self._latest = result
        return result

    def append_stream(self, chunk: str) -> None:
        with self._lock:
            if self._latest is not None and not self._latest.get("done"):
                self._latest["translated"] += chunk

    def finish_stream(self) -> None:
        with self._lock:
            if self._latest is not None:
                self._latest["done"] = True

    def fail_stream(self, message: str) -> None:
        with self._lock:
            if self._latest is not None and not self._latest.get("done"):
                self._latest["translated"] = f"翻译失败：{message}"
                self._latest["done"] = True
                self._latest["error"] = message

    def submit(self, source: str, translated: str, cursor_x: int, cursor_y: int, hint: bool = False) -> dict:
        """非流式写入（空文本/未配置等提示场景），done=True 表示已是最终结果。"""
        result = {
            "id": str(uuid.uuid4()),
            "source": source,
            "translated": translated,
            "hint": hint,
            "cursor_x": cursor_x,
            "cursor_y": cursor_y,
            "created_at": time.time(),
            "done": True,
            "error": "",
        }
        with self._lock:
            self._latest = result
        return result

    def latest(self) -> dict | None:
        with self._lock:
            return self._latest

    def clear(self) -> None:
        """清空当前结果，供重建取词框前调用，避免新窗口读到上一次的旧译文。"""
        with self._lock:
            self._latest = None
