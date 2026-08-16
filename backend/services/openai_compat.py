from .provider import TranslationProvider

_LANG_NAMES = {
    "ZH": "Chinese",
    "EN": "English",
    "JA": "Japanese",
    "KO": "Korean",
    "FR": "French",
    "DE": "German",
    "ES": "Spanish",
    "PT": "Portuguese",
    "IT": "Italian",
    "RU": "Russian",
    "NL": "Dutch",
    "PL": "Polish",
    "SV": "Swedish",
    "DA": "Danish",
    "FI": "Finnish",
    "NB": "Norwegian",
    "CS": "Czech",
    "SK": "Slovak",
    "EL": "Greek",
    "HU": "Hungarian",
    "RO": "Romanian",
    "BG": "Bulgarian",
    "LT": "Lithuanian",
    "LV": "Latvian",
    "ET": "Estonian",
    "SL": "Slovenian",
    "HR": "Croatian",
    "UK": "Ukrainian",
    "TR": "Turkish",
    "ID": "Indonesian",
    "AR": "Arabic",
    "VI": "Vietnamese",
    "TH": "Thai",
}


class OpenAICompatProvider(TranslationProvider):
    """OpenAI 兼容 /chat/completions 接口：可接 OpenAI、DeepSeek、Qwen、Moonshot 等。"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self._api_key = api_key
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._model = model

    def available(self) -> bool:
        return bool(self._api_key) and bool(self._model)

    def translate(self, text: str, target_lang: str = "ZH", source_lang: str | None = None) -> str:
        import json
        import urllib.request

        if not self._api_key:
            raise RuntimeError("未配置 OpenAI 兼容接口 API Key")
        target_name = _LANG_NAMES.get(target_lang.upper(), target_lang)
        source_name = _LANG_NAMES.get(source_lang.upper(), source_lang) if source_lang else "auto-detect"
        prompt = (
            f"Translate the following text from {source_name} to {target_name}. "
            f"Output only the translation, no explanations.\n\n{text}"
        )
        body = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self._api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"AI 翻译请求失败：{exc}") from exc
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            raise RuntimeError(f"AI 翻译返回异常：{data}") from None
