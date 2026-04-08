# triage_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from app.core.triage_rules import RED_FLAG_PATTERNS  # 응급 red 패턴
from app.core.triage_rules import TRIAGE_LEVEL_GREEN  # green 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_RED  # red 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_YELLOW  # yellow 레벨 상수
from app.core.triage_rules import TRIAGE_MESSAGE_MAP  # 레벨별 안내 문구
from app.core.triage_rules import YELLOW_FLAG_PATTERNS  # 주의 yellow 패턴


def _contains_any_pattern(text: str, patterns: list[str]) -> bool:
    lowered_text = (text or "").strip().lower()
    if not lowered_text:
        return False

    for pattern in patterns:
        if pattern.lower() in lowered_text:
            return True

    return False


def _build_triage_input_text(
    query: str,
    internal_query: str,
    normalized_query: str,
) -> str:
    return " ".join([
        (query or "").strip(),
        (internal_query or "").strip(),
        (normalized_query or "").strip(),
    ]).strip()


def evaluate_triage_level(
    query: str,
    internal_query: str,
    normalized_query: str,
    detected_language: str,
) -> tuple[str, str]:
    combined_text = _build_triage_input_text(
        query=query,
        internal_query=internal_query,
        normalized_query=normalized_query,
    )

    red_patterns = RED_FLAG_PATTERNS.get(detected_language, []) + RED_FLAG_PATTERNS.get("en", [])
    yellow_patterns = YELLOW_FLAG_PATTERNS.get(detected_language, []) + YELLOW_FLAG_PATTERNS.get("en", [])

    if _contains_any_pattern(combined_text, red_patterns):
        return TRIAGE_LEVEL_RED, TRIAGE_MESSAGE_MAP[TRIAGE_LEVEL_RED]

    if _contains_any_pattern(combined_text, yellow_patterns):
        return TRIAGE_LEVEL_YELLOW, TRIAGE_MESSAGE_MAP[TRIAGE_LEVEL_YELLOW]

    return TRIAGE_LEVEL_GREEN, TRIAGE_MESSAGE_MAP[TRIAGE_LEVEL_GREEN]