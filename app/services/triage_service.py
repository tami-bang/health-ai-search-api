# app/services/triage_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # 타입 힌트 보조

from app.core.triage_rules import TRIAGE_LEVEL_GREEN  # green 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_RED  # red 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_YELLOW  # yellow 레벨 상수
from app.core.triage_rules import TRIAGE_MESSAGE_MAP  # 레벨별 안내 문구
from app.core.triage_rules import TRIAGE_RULE_GROUPS  # 점수 기반 triage 룰 그룹
from app.core.triage_rules import TRIAGE_SCORE_THRESHOLDS  # triage 점수 임계값


def _build_triage_input_text(
    query: str,
    internal_query: str,
    normalized_query: str,
) -> str:
    return " ".join([
        (query or "").strip(),
        (internal_query or "").strip(),
        (normalized_query or "").strip(),
    ]).strip().lower()


def _get_language_rule_groups(detected_language: str) -> dict[str, list[dict[str, Any]]]:
    if detected_language == "ko":
        return TRIAGE_RULE_GROUPS.get("ko", {})
    return TRIAGE_RULE_GROUPS.get("en", {})


def _collect_matched_rules(
    combined_text: str,
    rule_groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    matched_rules: list[dict[str, Any]] = []

    for group_name, rules in rule_groups.items():
        for rule in rules:
            pattern = str(rule.get("pattern", "")).strip().lower()
            score = int(rule.get("score", 0))

            if not pattern:
                continue

            if pattern in combined_text:
                matched_rules.append({
                    "group_name": group_name,
                    "pattern": pattern,
                    "score": score,
                })

    return matched_rules


def _calculate_total_score(matched_rules: list[dict[str, Any]]) -> int:
    return sum(int(rule.get("score", 0)) for rule in matched_rules)


def _resolve_triage_level(total_score: int) -> str:
    red_threshold = int(TRIAGE_SCORE_THRESHOLDS[TRIAGE_LEVEL_RED])
    yellow_threshold = int(TRIAGE_SCORE_THRESHOLDS[TRIAGE_LEVEL_YELLOW])

    if total_score >= red_threshold:
        return TRIAGE_LEVEL_RED

    if total_score >= yellow_threshold:
        return TRIAGE_LEVEL_YELLOW

    return TRIAGE_LEVEL_GREEN


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

    language_rule_groups = _get_language_rule_groups(detected_language)
    english_rule_groups = TRIAGE_RULE_GROUPS.get("en", {})

    # 확장 포인트:
    # - 한국어 질의도 내부 번역문이 함께 들어오므로 영어 그룹을 함께 적용하면 coverage가 좋아진다.
    merged_rule_groups = {
        **english_rule_groups,
        **language_rule_groups,
    }

    matched_rules = _collect_matched_rules(
        combined_text=combined_text,
        rule_groups=merged_rule_groups,
    )
    total_score = _calculate_total_score(matched_rules)
    triage_level = _resolve_triage_level(total_score)

    return triage_level, TRIAGE_MESSAGE_MAP[triage_level]