import asyncio
import base64

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from utils.screenshot import capture_screen_png

router = APIRouter()


class OcrRequest(BaseModel):
    image: str  # base64 编码的图片


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "ZH"
    source_lang: str | None = None


@router.post("/api/screenshot")
async def screenshot():
    """抓取全屏并返回 base64 PNG，供前端框选（开发/浏览器模式使用）。"""
    data = capture_screen_png()
    return {"image": base64.b64encode(data).decode()}


@router.post("/api/ocr")
async def ocr(req: OcrRequest, request: Request):
    if not req.image:
        raise HTTPException(400, "缺少图片数据")
    try:
        raw = base64.b64decode(req.image)
    except Exception as exc:
        raise HTTPException(400, "图片数据格式错误（需为 base64）") from exc
    try:
        text = await asyncio.to_thread(request.app.state.ocr.recognize, raw)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"OCR 识别失败：{exc}") from exc
    return {"text": text}


@router.post("/api/translate")
async def translate(req: TranslateRequest, request: Request):
    provider = request.app.state.provider
    if not provider.available():
        raise HTTPException(503, "未配置翻译引擎 API Key，请填写 .env 中的 DEEPL_API_KEY")
    try:
        text = await asyncio.to_thread(provider.translate, req.text, req.target_lang, req.source_lang)
    except Exception as exc:
        raise HTTPException(502, f"翻译失败：{exc}") from exc
    return {"translated": text}
