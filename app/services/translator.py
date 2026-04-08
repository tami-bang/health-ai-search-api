# translator.py
from deep_translator import GoogleTranslator  # Google 번역기 기반 텍스트 번역


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    if text is None:
        return ""

    cleaned = str(text).strip()
    if not cleaned:
        return cleaned

    try:
        translated = GoogleTranslator(
            source=source_lang,
            target=target_lang,
        ).translate(cleaned)

        return translated.strip() if translated else cleaned
    except Exception:
        return cleaned


def translate_ko_to_en(text: str) -> str:
    return translate_text(text, target_lang="en", source_lang="auto")


def translate_en_to_ko(text: str) -> str:
    return translate_text(text, target_lang="ko", source_lang="auto")