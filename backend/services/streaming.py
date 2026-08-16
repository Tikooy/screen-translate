import re

# 按句末标点/换行切分，模拟"逐句流出"的伪流式效果。
# 英文句点需后跟空格 + 大写/数字/CJK 才切分，避免误拆缩写（Mr.、e.g.）。
_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\n])\s*|(?<=\.)\s+(?=[A-Z0-9\u4e00-\u9fff])")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def iter_translate(provider, text: str, target_lang: str = "ZH", source_lang: str | None = None):
    """逐句翻译并逐句产出译文块，供 WebSocket 逐条推送。"""
    for sentence in split_sentences(text):
        yield provider.translate(sentence, target_lang, source_lang)
