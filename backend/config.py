from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8765

    # 翻译引擎：deepl | google | openai（OpenAI 兼容接口，可接 ChatGPT/DeepSeek 等）
    translate_provider: str = "deepl"
    deepl_api_key: str = ""
    google_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    ocr_lang: str = "ch"
    ocr_device: str = "cpu"  # cpu 或 gpu（gpu 需安装 GPU 版 PaddlePaddle）

    # 取词翻译的全局热键（keyboard 库的按键写法，如 ctrl+alt+t）
    word_pick_hotkey: str = "ctrl+alt+t"
    # 取词（热键）翻译的目标语言
    word_pick_lang: str = "ZH"
    # 区域翻译的变化检测轮询间隔（秒），开始后每隔该秒数重新截图+OCR 一次
    region_poll_interval: float = 2.0
    # 点击主窗口 × 是否直接退出（不最小化到托盘）
    exit_on_close: bool = False


def update_env_file(updates: dict[str, str]) -> None:
    """把若干环境变量写回 .env（保留注释与未改动项），值统一转字符串。"""
    lines = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    normalized = {k.upper(): str(v) for k, v in updates.items()}
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=", 1)[0].strip().upper()
            if key in normalized:
                out.append(f"{key}={normalized[key]}")
                seen.add(key)
            else:
                out.append(line)
        else:
            out.append(line)
    for key, value in normalized.items():
        if key not in seen:
            out.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


settings = Settings()
