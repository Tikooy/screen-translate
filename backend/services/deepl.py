from .provider import TranslationProvider


class DeepLProvider(TranslationProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._translator = None
        if api_key:
            import deepl

            self._translator = deepl.Translator(api_key)

    def available(self) -> bool:
        return self._translator is not None

    def translate(self, text: str, target_lang: str = "ZH", source_lang: str | None = None) -> str:
        if not self._translator:
            raise RuntimeError("未配置 DeepL API Key")
        kwargs = {"target_lang": target_lang}
        if source_lang:
            kwargs["source_lang"] = source_lang
        result = self._translator.translate_text(text, **kwargs)
        return result.text
