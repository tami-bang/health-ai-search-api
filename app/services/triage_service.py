from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from dataclasses import dataclass  # 용도: 경량 결과 구조 정의
from typing import Any  # 용도: 타입 힌트 보조

from app.core.triage_rules import TRIAGE_DEFAULT_LANGUAGE  # 용도: 기본 메시지 언어
from app.core.triage_rules import TRIAGE_LEVEL_GREEN  # 용도: green 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_RED  # 용도: red 레벨 상수
from app.core.triage_rules import TRIAGE_LEVEL_YELLOW  # 용도: yellow 레벨 상수
from app.core.triage_rules import TRIAGE_MESSAGE_MAP_BY_LANGUAGE  # 용도: 언어별 triage 문구
from app.core.triage_rules import TRIAGE_RULE_GROUPS  # 용도: 점수 기반 triage 룰 그룹
from app.core.triage_rules import TRIAGE_SCORE_THRESHOLDS  # 용도: triage 점수 임계값
from app.core.triage_rules import TRIAGE_SUPPORTED_LANGUAGES  # 용도: 지원 언어 목록

PERSISTENT_BLEEDING_PATTERNS: dict[str, tuple[str, ...]] = {
    "ko": (
        "코피",
        "비출혈",
        "출혈",
        "피가 안 멈춰",
        "피가 멈추지",
        "코피가 안 멈춰",
        "코피가 멈추지",
        "삼십분째",
        "30분째",
        "계속",
        "지속",
    ),
    "en": (
        "nosebleed",
        "nose bleed",
        "epistaxis",
        "bleeding",
        "won't stop bleeding",
        "bleeding for 30 minutes",
        "for 30 minutes",
        "persistent bleeding",
    ),
}

PERSISTENT_BLEEDING_GROUP_NAME = "persistent_bleeding"
PERSISTENT_BLEEDING_SCORE = 3


@dataclass(frozen=True)
class MatchedRule:
    group_name: str
    pattern: str
    score: int
    source_language: str


@dataclass(frozen=True)
class TriageEvaluationResult:
    detected_language: str
    triage_level: str
    triage_message: str
    triage_score: int
    matched_patterns: list[str]


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


def _resolve_supported_language(detected_language: str) -> str:
    language = (detected_language or "").strip().lower()
    if language in TRIAGE_SUPPORTED_LANGUAGES:
        return language
    return TRIAGE_DEFAULT_LANGUAGE


def _get_rule_groups_by_language(
    detected_language: str,
) -> dict[str, list[dict[str, Any]]]:
    supported_language = _resolve_supported_language(detected_language)
    return TRIAGE_RULE_GROUPS.get(supported_language, {})


def _collect_matched_rules(
    combined_text: str,
    rule_groups: dict[str, list[dict[str, Any]]],
    source_language: str,
) -> list[MatchedRule]:
    matched_rules: list[MatchedRule] = []

    for group_name, rules in rule_groups.items():
        for rule in rules:
            pattern = str(rule.get("pattern", "")).strip().lower()
            score = int(rule.get("score", 0))

            if not pattern:
                continue

            if pattern in combined_text:
                matched_rules.append(
                    MatchedRule(
                        group_name=group_name,
                        pattern=pattern,
                        score=score,
                        source_language=source_language,
                    )
                )

    return matched_rules


def _build_persistent_bleeding_rule(
    combined_text: str,
    source_language: str,
) -> list[MatchedRule]:
    patterns = PERSISTENT_BLEEDING_PATTERNS.get(source_language, ())
    matched_patterns = [
        pattern
        for pattern in patterns
        if pattern and pattern in combined_text
    ]

    if not matched_patterns:
        return []

    return [
        MatchedRule(
            group_name=PERSISTENT_BLEEDING_GROUP_NAME,
            pattern=matched_patterns[0],
            score=PERSISTENT_BLEEDING_SCORE,
            source_language=source_language,
        )
    ]


def _deduplicate_matched_rules(
    matched_rules: list[MatchedRule],
) -> list[MatchedRule]:
    unique_rules: list[MatchedRule] = []
    seen_rule_keys: set[tuple[str, str, str]] = set()

    for rule in matched_rules:
        rule_key = (rule.group_name, rule.pattern, rule.source_language)
        if rule_key in seen_rule_keys:
            continue

        seen_rule_keys.add(rule_key)
        unique_rules.append(rule)

    return unique_rules


def _calculate_total_score(matched_rules: list[MatchedRule]) -> int:
    group_best_scores: dict[str, int] = {}

    for rule in matched_rules:
        previous_score = group_best_scores.get(rule.group_name, 0)
        if rule.score > previous_score:
            group_best_scores[rule.group_name] = rule.score

    return sum(group_best_scores.values())


def _resolve_triage_level(total_score: int) -> str:
    red_threshold = int(TRIAGE_SCORE_THRESHOLDS[TRIAGE_LEVEL_RED])
    yellow_threshold = int(TRIAGE_SCORE_THRESHOLDS[TRIAGE_LEVEL_YELLOW])

    if total_score >= red_threshold:
        return TRIAGE_LEVEL_RED

    if total_score >= yellow_threshold:
        return TRIAGE_LEVEL_YELLOW

    return TRIAGE_LEVEL_GREEN


def _build_localized_triage_message(
    triage_level: str,
    detected_language: str,
) -> str:
    supported_language = _resolve_supported_language(detected_language)
    language_message_map = TRIAGE_MESSAGE_MAP_BY_LANGUAGE.get(
        supported_language,
        TRIAGE_MESSAGE_MAP_BY_LANGUAGE[TRIAGE_DEFAULT_LANGUAGE],
    )
    return language_message_map[triage_level]


def _extract_display_patterns(
    matched_rules: list[MatchedRule],
    detected_language: str,
) -> list[str]:
    supported_language = _resolve_supported_language(detected_language)
    preferred_patterns: list[str] = []
    fallback_patterns: list[str] = []
    seen_patterns: set[str] = set()

    for rule in matched_rules:
        if rule.pattern not in seen_patterns:
            seen_patterns.add(rule.pattern)
            fallback_patterns.append(rule.pattern)

            if rule.source_language == supported_language:
                preferred_patterns.append(rule.pattern)

    return preferred_patterns if preferred_patterns else fallback_patterns


def evaluate_triage_level(
    query: str,
    internal_query: str,
    normalized_query: str,
    detected_language: str,
) -> TriageEvaluationResult:
    combined_text = _build_triage_input_text(
        query=query,
        internal_query=internal_query,
        normalized_query=normalized_query,
    )

    language_code = _resolve_supported_language(detected_language)
    language_rule_groups = _get_rule_groups_by_language(language_code)
    english_rule_groups = TRIAGE_RULE_GROUPS.get("en", {})

    language_matched_rules = _collect_matched_rules(
        combined_text=combined_text,
        rule_groups=language_rule_groups,
        source_language=language_code,
    )
    english_matched_rules = _collect_matched_rules(
        combined_text=combined_text,
        rule_groups=english_rule_groups,
        source_language="en",
    )

    supplemental_language_rules = _build_persistent_bleeding_rule(
        combined_text=combined_text,
        source_language=language_code,
    )
    supplemental_english_rules = _build_persistent_bleeding_rule(
        combined_text=combined_text,
        source_language="en",
    )

    matched_rules = _deduplicate_matched_rules(
        language_matched_rules
        + english_matched_rules
        + supplemental_language_rules
        + supplemental_english_rules
    )
    triage_score = _calculate_total_score(matched_rules)
    triage_level = _resolve_triage_level(triage_score)
    triage_message = _build_localized_triage_message(
        triage_level=triage_level,
        detected_language=language_code,
    )
    matched_patterns = _extract_display_patterns(
        matched_rules=matched_rules,
        detected_language=language_code,
    )

    return TriageEvaluationResult(
        detected_language=language_code,
        triage_level=triage_level,
        triage_message=triage_message,
        triage_score=triage_score,
        matched_patterns=matched_patterns,
    )