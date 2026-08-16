from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/region/result")
async def region_result(request: Request):
    """区域翻译的最新状态/结果，供透明悬浮框前端轮询。"""
    manager = getattr(request.app.state, "region", None)
    if manager is None:
        return {"running": False, "status": "idle", "source": "", "translated": "", "note": "", "error": "", "seq": 0}
    return manager.latest()
