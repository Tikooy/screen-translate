import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..services.streaming import split_sentences

router = APIRouter()


class WordPickRequest(BaseModel):
    text: str
    target_lang: str = "ZH"
    cursor_x: int = 0
    cursor_y: int = 0


@router.post("/api/wordpick")
async def wordpick(req: WordPickRequest, request: Request):
    """取词翻译：逐句流式翻译并把结果写入 WordPickManager，供气泡窗口轮询。"""
    manager = request.app.state.wordpick
    if not req.text.strip():
        manager.submit("", "未检测到选中文字，请先框选文本后重试", req.cursor_x, req.cursor_y, hint=True)
        return {"ok": True, "hint": True}
    provider = request.app.state.provider
    if not provider.available():
        manager.submit(req.text, "未配置翻译引擎 API Key，请在右上角设置中填写", req.cursor_x, req.cursor_y, hint=True)
        return {"ok": True, "hint": True}

    manager.begin_stream(req.text, req.cursor_x, req.cursor_y)

    async def _stream():
        try:
            for sentence in split_sentences(req.text):
                chunk = await asyncio.to_thread(provider.translate, sentence, req.target_lang, None)
                manager.append_stream(chunk)
            manager.finish_stream()
        except Exception as exc:
            manager.fail_stream(str(exc))

    # 持有任务引用，避免被垃圾回收中断
    request.app.state.wordpick_task = asyncio.create_task(_stream())
    return {"ok": True}


@router.get("/api/wordpick/result")
async def wordpick_result(request: Request):
    return request.app.state.wordpick.latest() or {}
