from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import re  # 용도: 기간/강도/위험 표현 패턴 매칭
from dataclasses import dataclass  # 용도: 경량 결과 구조 정의
from dataclasses import field  # 용도: dataclass 기본값 컬렉션 정의
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

CONTEXT_SEVERITY_GROUP_NAME = "context_severity"
CONTEXT_DURATION_GROUP_NAME = "context_duration"
CONTEXT_WORSENING_GROUP_NAME = "context_worsening"
CONTEXT_VULNERABLE_GROUP_NAME = "context_vulnerable"
CONTEXT_MULTI_SYMPTOM_GROUP_NAME = "context_multi_symptom"

CONTEXT_GROUP_NAMES: set[str] = {
    CONTEXT_SEVERITY_GROUP_NAME,
    CONTEXT_DURATION_GROUP_NAME,
    CONTEXT_WORSENING_GROUP_NAME,
    CONTEXT_VULNERABLE_GROUP_NAME,
    CONTEXT_MULTI_SYMPTOM_GROUP_NAME,
}

CONTEXT_RULE_PATTERNS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "ko": {
        CONTEXT_SEVERITY_GROUP_NAME: [
            {"pattern": r"매우\s*심", "score": 2},
            {"pattern": r"너무\s*아파", "score": 2},
            {"pattern": r"극심", "score": 2},
            {"pattern": r"심한\s*(통증|두통|복통|기침|호흡곤란)", "score": 2},
            {"pattern": r"\b(9|10)점\b", "score": 2},
            {"pattern": r"중간\s*이상", "score": 1},
            {"pattern": r"심해요", "score": 1},
            {"pattern": r"심합니다", "score": 1},
            {"pattern": r"아픈\s*편", "score": 1},
        ],
        CONTEXT_DURATION_GROUP_NAME: [
            {"pattern": r"\b\d+\s*주", "score": 2},
            {"pattern": r"\b\d+\s*개월", "score": 2},
            {"pattern": r"며칠째", "score": 1},
            {"pattern": r"\b\d+\s*일째", "score": 1},
            {"pattern": r"\b\d+\s*일", "score": 1},
            {"pattern": r"하루\s*넘", "score": 1},
            {"pattern": r"계속", "score": 1},
            {"pattern": r"지속", "score": 1},
        ],
        CONTEXT_WORSENING_GROUP_NAME: [
            {"pattern": r"점점\s*심", "score": 2},
            {"pattern": r"악화", "score": 2},
            {"pattern": r"더\s*심해", "score": 2},
            {"pattern": r"점점\s*나빠", "score": 2},
            {"pattern": r"반복", "score": 1},
            {"pattern": r"자꾸", "score": 1},
        ],
        CONTEXT_VULNERABLE_GROUP_NAME: [
            {"pattern": r"임신", "score": 1},
            {"pattern": r"임산부", "score": 1},
            {"pattern": r"신생아", "score": 1},
            {"pattern": r"영아", "score": 1},
            {"pattern": r"아기", "score": 1},
            {"pattern": r"노인", "score": 1},
            {"pattern": r"고령", "score": 1},
            {"pattern": r"면역저하", "score": 1},
        ],
    },
    "en": {
        CONTEXT_SEVERITY_GROUP_NAME: [
            {"pattern": r"\bsevere\b", "score": 2},
            {"pattern": r"\bvery severe\b", "score": 2},
            {"pattern": r"\bextreme\b", "score": 2},
            {"pattern": r"\bunbearable\b", "score": 2},
            {"pattern": r"\b(9|10)\/10\b", "score": 2},
            {"pattern": r"\bmoderate to severe\b", "score": 1},
            {"pattern": r"\bbad pain\b", "score": 1},
            {"pattern": r"\bworse pain\b", "score": 1},
        ],
        CONTEXT_DURATION_GROUP_NAME: [
            {"pattern": r"\b\d+\s*weeks?\b", "score": 2},
            {"pattern": r"\b\d+\s*months?\b", "score": 2},
            {"pattern": r"\b\d+\s*days?\b", "score": 1},
            {"pattern": r"\bsince yesterday\b", "score": 1},
            {"pattern": r"\bongoing\b", "score": 1},
            {"pattern": r"\bpersistent\b", "score": 1},
            {"pattern": r"\bfor hours\b", "score": 1},
        ],
        CONTEXT_WORSENING_GROUP_NAME: [
            {"pattern": r"\bworsening\b", "score": 2},
            {"pattern": r"\bgetting worse\b", "score": 2},
            {"pattern": r"\bprogressively worse\b", "score": 2},
            {"pattern": r"\brecurrent\b", "score": 1},
            {"pattern": r"\bkeeps happening\b", "score": 1},
        ],
        CONTEXT_VULNERABLE_GROUP_NAME: [
            {"pattern": r"\bpregnan", "score": 1},
            {"pattern": r"\binfant\b", "score": 1},
            {"pattern": r"\bbaby\b", "score": 1},
            {"pattern": r"\bnewborn\b", "score": 1},
            {"pattern": r"\belderly\b", "score": 1},
            {"pattern": r"\bold adult\b", "score": 1},
            {"pattern": r"\bimmunocompromised\b", "score": 1},
        ],
    },
}

SYMPTOM_DELIMITER_PATTERNS: tuple[str, ...] = (
    ",",
    "，",
    "/",
    "|",
    " and ",
    " 그리고 ",
    " 및 ",
)

MULTI_SYMPTOM_MIN_COUNT = 2
MULTI_SYMPTOM_SCORE = 1


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
    matched_rule_names: list[str] = field(default_factory=list)
    matched_rule_details: list[dict[str, Any]] = field(default_factory=list)
    risk_factors: list[dict[str, Any]] = field(default_factory=list)
    score_breakdown: dict[str, int] = field(default_factory=dict)
    guidance_meta: dict[str, Any] = field(default_factory=dict)
    debug: dict[str, Any] = field(default_factory=dict)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _build_triage_input_text(
    query: str,
    internal_query: str,
    normalized_query: str,
) -> str:
    combined_text = " ".join([
        (query or "").strip(),
        (internal_query or "").strip(),
        (normalized_query or "").strip(),
    ])
    return _normalize_whitespace(combined_text).lower()


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


def _collect_regex_context_rules(
    combined_text: str,
    context_rule_groups: dict[str, list[dict[str, Any]]],
    source_language: str,
) -> list[MatchedRule]:
    matched_rules: list[MatchedRule] = []

    for group_name, rules in context_rule_groups.items():
        for rule in rules:
            pattern = str(rule.get("pattern", "")).strip().lower()
            score = int(rule.get("score", 0))

            if not pattern:
                continue

            if re.search(pattern, combined_text, flags=re.IGNORECASE):
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


def _count_detected_symptom_units(combined_text: str) -> int:
    normalized_text = f" {combined_text.strip()} "
    symptom_count = 1 if normalized_text.strip() else 0

    for delimiter in SYMPTOM_DELIMITER_PATTERNS:
        symptom_count += normalized_text.count(delimiter)

    return symptom_count


def _build_multi_symptom_rule(
    combined_text: str,
    source_language: str,
) -> list[MatchedRule]:
    symptom_count = _count_detected_symptom_units(combined_text)

    if symptom_count < MULTI_SYMPTOM_MIN_COUNT:
        return []

    return [
        MatchedRule(
            group_name=CONTEXT_MULTI_SYMPTOM_GROUP_NAME,
            pattern="multi_symptom",
            score=MULTI_SYMPTOM_SCORE,
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


def _calculate_group_best_scores(matched_rules: list[MatchedRule]) -> dict[str, int]:
    group_best_scores: dict[str, int] = {}

    for rule in matched_rules:
        previous_score = group_best_scores.get(rule.group_name, 0)
        if rule.score > previous_score:
            group_best_scores[rule.group_name] = rule.score

    return group_best_scores


def _calculate_total_score(matched_rules: list[MatchedRule]) -> int:
    return sum(_calculate_group_best_scores(matched_rules).values())


def _calculate_score_breakdown(matched_rules: list[MatchedRule]) -> dict[str, int]:
    group_best_scores = _calculate_group_best_scores(matched_rules)
    base_score = 0
    adjustment_score = 0

    for group_name, score in group_best_scores.items():
        if group_name in CONTEXT_GROUP_NAMES:
            adjustment_score += score
        else:
            base_score += score

    return {
        "base_score": base_score,
        "adjustment_score": adjustment_score,
        "total_score": base_score + adjustment_score,
    }


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
        display_pattern = rule.pattern

        if rule.pattern == "multi_symptom":
            display_pattern = "multiple symptoms" if supported_language == "en" else "복합 증상"

        if display_pattern not in seen_patterns:
            seen_patterns.add(display_pattern)
            fallback_patterns.append(display_pattern)

            if rule.source_language == supported_language:
                preferred_patterns.append(display_pattern)

    return preferred_patterns if preferred_patterns else fallback_patterns


def _collect_language_context_rules(
    combined_text: str,
    language_code: str,
) -> list[MatchedRule]:
    context_rule_groups = CONTEXT_RULE_PATTERNS.get(language_code, {})
    return _collect_regex_context_rules(
        combined_text=combined_text,
        context_rule_groups=context_rule_groups,
        source_language=language_code,
    )


def _collect_english_context_rules(
    combined_text: str,
) -> list[MatchedRule]:
    english_context_rule_groups = CONTEXT_RULE_PATTERNS.get("en", {})
    return _collect_regex_context_rules(
        combined_text=combined_text,
        context_rule_groups=english_context_rule_groups,
        source_language="en",
    )


def _build_matched_rule_names(matched_rules: list[MatchedRule]) -> list[str]:
    matched_rule_names: list[str] = []
    seen_group_names: set[str] = set()

    for rule in matched_rules:
        if rule.group_name in seen_group_names:
            continue

        seen_group_names.add(rule.group_name)
        matched_rule_names.append(rule.group_name)

    return matched_rule_names


def _build_matched_rule_details(matched_rules: list[MatchedRule]) -> list[dict[str, Any]]:
    return [
        {
            "group_name": rule.group_name,
            "pattern": rule.pattern,
            "score": rule.score,
            "source_language": rule.source_language,
        }
        for rule in matched_rules
    ]


def _resolve_risk_category(group_name: str) -> str:
    if group_name in {"respiratory_red_flags", "neuro_red_flags", "cardio_red_flags", "bleeding_red_flags"}:
        return "symptom"

    if group_name in {"trauma_red_flags", "dehydration_warning", "gastro_warning", "fever_warning", "eye_warning", "ent_warning"}:
        return "symptom"

    if group_name == CONTEXT_SEVERITY_GROUP_NAME:
        return "severity"

    if group_name == CONTEXT_DURATION_GROUP_NAME:
        return "duration"

    if group_name == CONTEXT_VULNERABLE_GROUP_NAME:
        return "age"

    return "context"


def _build_risk_factors(
    matched_rules: list[MatchedRule],
    detected_language: str,
) -> list[dict[str, Any]]:
    supported_language = _resolve_supported_language(detected_language)
    risk_factors: list[dict[str, Any]] = []

    for index, rule in enumerate(matched_rules):
        label = rule.pattern
        if label == "multi_symptom":
            label = "multiple symptoms" if supported_language == "en" else "복합 증상"

        risk_factors.append(
            {
                "factor_id": f"risk-factor-{index + 1}",
                "label": label,
                "score": rule.score,
                "category": _resolve_risk_category(rule.group_name),
            }
        )

    return risk_factors


def _build_guidance_meta(triage_level: str) -> dict[str, Any]:
    return {
        "emergency": triage_level == TRIAGE_LEVEL_RED,
        "urgent": triage_level == TRIAGE_LEVEL_YELLOW,
        "display_level": triage_level,
    }


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

    language_context_rules = _collect_language_context_rules(
        combined_text=combined_text,
        language_code=language_code,
    )
    english_context_rules = _collect_english_context_rules(
        combined_text=combined_text,
    )

    supplemental_language_rules = _build_persistent_bleeding_rule(
        combined_text=combined_text,
        source_language=language_code,
    )
    supplemental_english_rules = _build_persistent_bleeding_rule(
        combined_text=combined_text,
        source_language="en",
    )

    multi_symptom_language_rule = _build_multi_symptom_rule(
        combined_text=combined_text,
        source_language=language_code,
    )

    matched_rules = _deduplicate_matched_rules(
        language_matched_rules
        + english_matched_rules
        + language_context_rules
        + english_context_rules
        + supplemental_language_rules
        + supplemental_english_rules
        + multi_symptom_language_rule
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
    matched_rule_names = _build_matched_rule_names(matched_rules)
    matched_rule_details = _build_matched_rule_details(matched_rules)
    risk_factors = _build_risk_factors(
        matched_rules=matched_rules,
        detected_language=language_code,
    )
    score_breakdown = _calculate_score_breakdown(matched_rules)
    guidance_meta = _build_guidance_meta(triage_level)

    return TriageEvaluationResult(
        detected_language=language_code,
        triage_level=triage_level,
        triage_message=triage_message,
        triage_score=triage_score,
        matched_patterns=matched_patterns,
        matched_rule_names=matched_rule_names,
        matched_rule_details=matched_rule_details,
        risk_factors=risk_factors,
        score_breakdown=score_breakdown,
        guidance_meta=guidance_meta,
        debug={
            "combined_text": combined_text,
            "matched_rule_count": len(matched_rules),
        },
    )