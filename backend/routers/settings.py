from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..config import settings, update_env_file
from ..services.provider import build_provider

router = APIRouter()


class SettingsUpdate(BaseModel):
    translate_provider: str | None = None
    deepl_api_key: str | None = None
    google_api_key: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    word_pick_hotkey: str | None = None
    word_pick_lang: str | None = None
    region_poll_interval: float | None = None
    exit_on_close: bool | None = None


@router.get("/api/settings")
async def get_settings():
    return {
        "translate_provider": settings.translate_provider,
        "deepl_api_key": settings.deepl_api_key,
        "google_api_key": settings.google_api_key,
        "openai_api_key": settings.openai_api_key,
        "openai_base_url": settings.openai_base_url,
        "openai_model": settings.openai_model,
        "word_pick_hotkey": settings.word_pick_hotkey,
        "word_pick_lang": settings.word_pick_lang,
        "region_poll_interval": settings.region_poll_interval,
        "exit_on_close": settings.exit_on_close,
    }


@router.put("/api/settings")
async def put_settings(req: SettingsUpdate, request: Request):
    updates: dict[str, str] = {}
    provider_changed = False

    if req.word_pick_hotkey is not None:
        hotkey = req.word_pick_hotkey.strip()
        if hotkey:
            # 先验证热键格式是否合法，再应用
            try:
                import keyboard

                keyboard.add_hotkey(hotkey, lambda: None)
                keyboard.remove_hotkey(hotkey)
            except Exception as exc:
                return {"ok": False, "error": f"热键格式无效：{exc}"}

    if req.translate_provider is not None:
        p = req.translate_provider.strip().lower()
        if p not in ("deepl", "google", "openai"):
            return {"ok": False, "error": "不支持的翻译引擎"}
        updates["TRANSLATE_PROVIDER"] = p
        if p != settings.translate_provider:
            settings.translate_provider = p
            provider_changed = True

    for field, env_key in [
        ("deepl_api_key", "DEEPL_API_KEY"),
        ("google_api_key", "GOOGLE_API_KEY"),
        ("openai_api_key", "OPENAI_API_KEY"),
    ]:
        value = getattr(req, field)
        if value is not None:
            v = value.strip()
            updates[env_key] = v
            if v != getattr(settings, field):
                setattr(settings, field, v)
                provider_changed = True

    if req.openai_base_url is not None:
        url = req.openai_base_url.strip() or "https://api.openai.com/v1"
        updates["OPENAI_BASE_URL"] = url
        if url != settings.openai_base_url:
            settings.openai_base_url = url
            provider_changed = True

    if req.openai_model is not None:
        model = req.openai_model.strip()
        updates["OPENAI_MODEL"] = model
        if model != settings.openai_model:
            settings.openai_model = model
            provider_changed = True

    if req.word_pick_hotkey is not None:
        hotkey = req.word_pick_hotkey.strip()
        updates["WORD_PICK_HOTKEY"] = hotkey
        settings.word_pick_hotkey = hotkey

    if req.word_pick_lang is not None:
        lang = req.word_pick_lang.strip().upper() or "ZH"
        updates["WORD_PICK_LANG"] = lang
        settings.word_pick_lang = lang

    if req.region_poll_interval is not None:
        interval = max(0.5, min(60.0, float(req.region_poll_interval)))
        updates["REGION_POLL_INTERVAL"] = str(interval)
        settings.region_poll_interval = interval

    if req.exit_on_close is not None:
        updates["EXIT_ON_CLOSE"] = "true" if req.exit_on_close else "false"
        settings.exit_on_close = req.exit_on_close

    if updates:
        update_env_file(updates)

    if provider_changed:
        request.app.state.provider = build_provider(settings)

    if req.word_pick_hotkey is not None or req.word_pick_lang is not None:
        from .. import runtime

        if runtime.hotkey_service is not None:
            runtime.hotkey_service.reconfigure(settings.word_pick_hotkey, settings.word_pick_lang)

    return {"ok": True}


@router.post("/api/settings/test")
async def test_settings(req: SettingsUpdate):
    """用当前表单填写的引擎配置构建 provider，做一次小翻译验证连接是否可用。"""
    from types import SimpleNamespace

    tmp = SimpleNamespace(
        translate_provider=(req.translate_provider or settings.translate_provider),
        deepl_api_key=(req.deepl_api_key if req.deepl_api_key is not None else settings.deepl_api_key),
        google_api_key=(req.google_api_key if req.google_api_key is not None else settings.google_api_key),
        openai_api_key=(req.openai_api_key if req.openai_api_key is not None else settings.openai_api_key),
        openai_base_url=(req.openai_base_url if req.openai_base_url is not None else settings.openai_base_url),
        openai_model=(req.openai_model if req.openai_model is not None else settings.openai_model),
    )
    provider = build_provider(tmp)
    if not provider.available():
        return {"ok": False, "error": "未填写所选引擎的 API Key"}
    try:
        sample = provider.translate("Hello, world!", "ZH", "EN")
        return {"ok": True, "sample": sample}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/api/settings/hotkey-pause")
async def hotkey_pause():
    """设置面板打开时暂停全局热键，避免录制热键时按下旧组合键误触发取词。"""
    from .. import runtime

    if runtime.hotkey_service is not None:
        runtime.hotkey_service.stop()
    return {"ok": True}


@router.post("/api/settings/hotkey-resume")
async def hotkey_resume():
    from .. import runtime

    if runtime.hotkey_service is not None:
        runtime.hotkey_service.start()
    return {"ok": True}
