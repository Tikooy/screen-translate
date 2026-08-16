from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import region, translate, wordpick, ws
from .routers import settings as settings_router
from .services.ocr import OCRService
from .services.provider import build_provider
from .services.wordpick import WordPickManager

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ocr = OCRService(lang=settings.ocr_lang, device=settings.ocr_device)
    app.state.provider = build_provider(settings)
    app.state.wordpick = WordPickManager()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="在线翻译小工具", lifespan=lifespan)
    # 仅允许本机来源：桌面窗口加载 8765，Vite 开发服务器在 5173。
    # 不用 "*"，避免任意网页跨域读取本机 /api/wordpick/result（最近选中的文本）。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://{settings.host}:{settings.port}",
            f"http://localhost:{settings.port}",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(translate.router)
    app.include_router(wordpick.router)
    app.include_router(ws.router)
    app.include_router(region.router)
    app.include_router(settings_router.router)

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "provider": type(app.state.provider).__name__,
            "word_pick_hotkey": settings.word_pick_hotkey,
        }

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app
