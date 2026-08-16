import io
import threading

import numpy as np
from PIL import Image


class OCRService:
    """PP-OCRv6（PaddleOCR 3.x）封装：懒加载模型，串行推理避免 Paddle 线程问题。"""

    def __init__(self, lang: str = "ch", device: str = "cpu"):
        self._lang = lang
        self._device = device
        self._engine = None
        self._lock = threading.Lock()

    def _ensure_engine(self):
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    from paddleocr import PaddleOCR

                    # 首次调用会在后台下载模型，耗时取决于网络。
                    # enable_mkldnn=False：PaddlePaddle 3.3 的 oneDNN 后端有 PIR 转换 bug，CPU 推理需禁用。
                    self._engine = PaddleOCR(lang=self._lang, device=self._device, enable_mkldnn=False)
        return self._engine

    def recognize(self, image_bytes: bytes) -> str:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img)
        engine = self._ensure_engine()
        with self._lock:
            result = engine.predict(arr)
        return self._extract_text(result)

    @staticmethod
    def _extract_text(result) -> str:
        texts: list[str] = []
        for page in result:
            rec_texts = None
            if hasattr(page, "rec_texts"):
                rec_texts = page.rec_texts
            elif isinstance(page, dict):
                rec_texts = page.get("rec_texts")
            if rec_texts:
                texts.extend(t for t in rec_texts if t)
        return "\n".join(texts)
