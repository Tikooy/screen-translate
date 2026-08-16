from .provider import TranslationProvider


class GoogleProvider(TranslationProvider):
    """Google Cloud Translation v2（API Key 方式）。语言码用小写（Google 格式）。"""

    def __init__(self, api_key: str):
        self._api_key = api_key

    def available(self) -> bool:
        return bool(self._api_key)

    def translate(self, text: str, target_lang: str = "ZH", source_lang: str | None = None) -> str:
        import json
        import urllib.parse
        import urllib.request

        if not self._api_key:
            raise RuntimeError("未配置 Google Cloud Translation API Key")
        params = {"key": self._api_key, "q": text, "target": target_lang.lower()}
        if source_lang:
            params["source"] = source_lang.lower()
        url = "https://translation.googleapis.com/language/translate/v2?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Google 翻译请求失败：{exc}") from exc
        try:
            return data["data"]["translations"][0]["translatedText"]
        except Exception:
            raise RuntimeError(f"Google 翻译返回异常：{data}") from None
