from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """翻译引擎抽象：DeepL / Google Cloud Translation / OpenAI 兼容接口。"""

    @abstractmethod
    def available(self) -> bool:
        """引擎是否已正确配置（如 API Key 是否就绪）。"""

    @abstractmethod
    def translate(self, text: str, target_lang: str = "ZH", source_lang: str | None = None) -> str:
        """翻译单段文本，返回译文。"""

    def provider_name(self) -> str:
        return type(self).__name__


class MissingKeyProvider(TranslationProvider):
    """所选引擎未配置时兜底：调用即抛出带指引的错误，避免静默失败。"""

    def __init__(self, message: str | None = None):
        self._message = message or "未配置所选翻译引擎的 API Key"

    def available(self) -> bool:
        return False

    def translate(self, text: str, target_lang: str = "ZH", source_lang: str | None = None) -> str:
        raise RuntimeError(self._message)


def build_provider(settings) -> TranslationProvider:
    provider_type = (settings.translate_provider or "deepl").lower()

    if provider_type == "google":
        if settings.google_api_key:
            from .google import GoogleProvider

            return GoogleProvider(settings.google_api_key)
        return MissingKeyProvider("未配置 Google Cloud Translation API Key，请在设置或 .env 中填写 GOOGLE_API_KEY")

    if provider_type == "openai":
        if settings.openai_api_key:
            from .openai_compat import OpenAICompatProvider

            return OpenAICompatProvider(
                settings.openai_api_key, settings.openai_base_url, settings.openai_model
            )
        return MissingKeyProvider("未配置 OpenAI 兼容接口 API Key，请在设置或 .env 中填写 OPENAI_API_KEY")

    # 默认 DeepL
    if settings.deepl_api_key:
        from .deepl import DeepLProvider

        return DeepLProvider(settings.deepl_api_key)
    return MissingKeyProvider("未配置 DeepL API Key，请在设置或 .env 中填写 DEEPL_API_KEY")
