# language_utils.py
import re  # 입력 문자열 언어 판별용 정규식


def detect_query_language(text: str) -> str:
    if not text:
        return "en"

    if re.search(r"[가-힣]", text):
        return "ko"

    return "en"