from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import logging  # 용도: 실행 로그 기록
import re  # 용도: 패턴 ID 생성용 문자열 정리

from fastapi import APIRouter  # 용도: 라우터 등록

from app.schemas import TriageGuidanceMeta  # 용도: triage 가이드 메타 응답 스키마
from app.schemas import TriageMatchedRule  # 용도: triage 상세 룰 응답 스키마
from app.schemas import TriagePattern  # 용도: triage 패턴 응답 스키마
from app.schemas import TriageRequest  # 용도: triage 요청 스키마
from app.schemas import TriageResponse  # 용도: triage 응답 스키마
from app.schemas import TriageRiskFactor  # 용도: triage 위험 요소 응답 스키마
from app.schemas import TriageScoreBreakdown  # 용도: triage 점수 분해 응답 스키마
from app.services.language_utils import detect_query_language  # 용도: 입력 언어 감지
from app.services.translator import translate_ko_to_en  # 용도: 한국어 -> 영어 번역
from app.services.triage_service import evaluate_triage_level  # 용도: triage 평가 서비스

logger = logging.getLogger(__name__)  # 용도: triage 라우터 로그 기록
router = APIRouter(tags=["triage"])  # 용도: triage 전용 라우터 분리

KOREAN_TRAILING_PARTICLE_PATTERN = re.compile(  # 용도: 조사 차이 패턴 통합
    r"(이|가|은|는|을|를|에|에서|와|과|도|만|의|로|으로|께서|한테|에게)$"
)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _build_query_from_payload(payload: TriageRequest) -> str:
    """
    기존 query 기반 요청 유지
    프론트 symptoms 기반 요청 확장 지원
    """
    cleaned_query = _normalize_whitespace(payload.query or "")
    if cleaned_query:
        return cleaned_query

    cleaned_symptoms = [
        _normalize_whitespace(symptom)
        for symptom in payload.symptoms
        if _normalize_whitespace(symptom)
    ]
    if cleaned_symptoms:
        return " ".join(cleaned_symptoms)

    return ""


def _build_internal_query(
    query: str,
    detected_language: str,
) -> str:
    if detected_language == "ko":
        translated_query = translate_ko_to_en(query)
        return translated_query.strip() if translated_query and translated_query.strip() else query

    return query


def _build_normalized_query(internal_query: str) -> str:
    return (internal_query or "").strip().lower()


def _normalize_pattern_display_name(pattern_name: str) -> str:
    cleaned_pattern_name = _normalize_whitespace(pattern_name)
    if not cleaned_pattern_name:
        return ""

    collapsed_pattern_name = KOREAN_TRAILING_PARTICLE_PATTERN.sub("", cleaned_pattern_name)
    collapsed_pattern_name = _normalize_whitespace(collapsed_pattern_name)

    return collapsed_pattern_name or cleaned_pattern_name


def _build_pattern_slug(pattern_name: str) -> str:
    cleaned_pattern_name = _normalize_pattern_display_name(pattern_name)
    if not cleaned_pattern_name:
        return "pattern"

    slug_source = cleaned_pattern_name.lower()
    slug = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", slug_source).strip("-")

    return slug or "pattern"


def _build_pattern_id(pattern_name: str, index: int) -> str:
    pattern_slug = _build_pattern_slug(pattern_name)
    return f"triage-{pattern_slug}-{index + 1}"


def _build_pattern_description(pattern_name: str) -> str:
    return f"Matched triage signal: {pattern_name}"


def _build_pattern_confidence(triage_score: int) -> float:
    if triage_score <= 0:
        return 0.5

    return min(1.0, round(0.5 + (triage_score * 0.1), 2))


def _deduplicate_pattern_names(matched_patterns: list[str]) -> list[str]:
    unique_patterns: list[str] = []
    seen_pattern_keys: set[str] = set()

    for pattern_name in matched_patterns:
        normalized_pattern_name = _normalize_pattern_display_name(pattern_name)
        if not normalized_pattern_name:
            continue

        pattern_key = normalized_pattern_name.lower()
        if pattern_key in seen_pattern_keys:
            continue

        seen_pattern_keys.add(pattern_key)
        unique_patterns.append(normalized_pattern_name)

    return unique_patterns


def _build_pattern_items(
    matched_patterns: list[str],
    triage_score: int,
) -> list[TriagePattern]:
    confidence = _build_pattern_confidence(triage_score)
    deduplicated_patterns = _deduplicate_pattern_names(matched_patterns)
    pattern_items: list[TriagePattern] = []

    for index, pattern_name in enumerate(deduplicated_patterns):
        pattern_items.append(
            TriagePattern(
                pattern_id=_build_pattern_id(pattern_name, index),
                pattern_name=pattern_name,
                confidence=confidence,
                description=_build_pattern_description(pattern_name),
            )
        )

    return pattern_items


def _build_recommendations(
    triage_level: str,
    detected_language: str,
) -> list[str]:
    is_korean = detected_language == "ko"

    recommendation_map = {
        "red": (
            [
                "즉시 응급실 또는 119에 연락하세요.",
                "혼자 이동하지 말고 주변 사람의 도움을 받으세요.",
            ]
            if is_korean
            else [
                "Seek emergency care immediately or call emergency services.",
                "Do not travel alone; ask someone nearby for help.",
            ]
        ),
        "yellow": (
            [
                "가능하면 오늘 안에 의료진 상담을 받으세요.",
                "증상이 악화되면 즉시 응급 진료를 고려하세요.",
            ]
            if is_korean
            else [
                "Try to speak with a medical provider within today.",
                "If symptoms worsen, seek urgent care immediately.",
            ]
        ),
        "green": (
            [
                "우선 경과를 관찰하세요.",
                "증상이 지속되거나 심해지면 진료를 예약하세요.",
            ]
            if is_korean
            else [
                "Monitor your symptoms for now.",
                "Schedule a medical visit if symptoms continue or worsen.",
            ]
        ),
    }

    return recommendation_map.get(triage_level, [])


def _build_follow_up_questions(
    detected_language: str,
) -> list[str]:
    if detected_language == "ko":
        return [
            "언제부터 증상이 시작되었나요?",
            "증상이 점점 심해지고 있나요?",
            "동반되는 다른 증상이 있나요?",
        ]

    return [
        "When did the symptoms start?",
        "Are the symptoms getting worse?",
        "Are there any other symptoms happening at the same time?",
    ]


def _build_disclaimer(
    detected_language: str,
) -> str:
    if detected_language == "ko":
        return "이 triage 결과는 일반 안내용이며 의학적 진단이나 치료를 대신하지 않습니다."

    return "This triage result is general guidance only and does not replace medical diagnosis or treatment."


def _build_matched_rule_details(
    matched_rule_details: list[dict],
) -> list[TriageMatchedRule]:
    details: list[TriageMatchedRule] = []

    for rule_detail in matched_rule_details:
        details.append(
            TriageMatchedRule(
                group_name=str(rule_detail.get("group_name", "")),
                pattern=str(rule_detail.get("pattern", "")),
                score=int(rule_detail.get("score", 0)),
                source_language=str(rule_detail.get("source_language", "")) or None,
            )
        )

    return details


def _build_risk_factors(
    risk_factors: list[dict],
) -> list[TriageRiskFactor]:
    items: list[TriageRiskFactor] = []

    for risk_factor in risk_factors:
        label = _normalize_pattern_display_name(str(risk_factor.get("label", "")))
        if not label:
            continue

        factor_id = str(risk_factor.get("factor_id", "")).strip()
        if not factor_id:
            factor_id = f"risk-{_build_pattern_slug(label)}"

        items.append(
            TriageRiskFactor(
                factor_id=factor_id,
                label=label,
                score=int(risk_factor.get("score", 0)),
                category=str(risk_factor.get("category", "other")),
            )
        )

    deduplicated_items: list[TriageRiskFactor] = []
    seen_factor_keys: set[tuple[str, str]] = set()

    for item in items:
        factor_key = (item.label.lower(), item.category)
        if factor_key in seen_factor_keys:
            continue

        seen_factor_keys.add(factor_key)
        deduplicated_items.append(item)

    return deduplicated_items


def _build_score_breakdown(
    score_breakdown: dict,
) -> TriageScoreBreakdown:
    return TriageScoreBreakdown(
        base_score=int(score_breakdown.get("base_score", 0)),
        adjustment_score=int(score_breakdown.get("adjustment_score", 0)),
        total_score=int(score_breakdown.get("total_score", 0)),
    )


def _build_guidance_meta(
    guidance_meta: dict,
) -> TriageGuidanceMeta:
    return TriageGuidanceMeta(
        emergency=bool(guidance_meta.get("emergency", False)),
        urgent=bool(guidance_meta.get("urgent", False)),
        display_level=str(guidance_meta.get("display_level", "")) or None,
    )


@router.post(
    "/triage",
    response_model=TriageResponse,
    summary="Triage",
)
def triage(payload: TriageRequest) -> TriageResponse:
    query = _build_query_from_payload(payload)
    detected_language = detect_query_language(query) if query else "en"

    if not query:
        return TriageResponse(
            query="",
            detected_language=detected_language,
            triage_level="green",
            triage_message="No symptoms provided." if detected_language != "ko" else "증상이 입력되지 않았습니다.",
            triage_score=0,
            matched_patterns=[],
            recommendations=_build_recommendations("green", detected_language),
            follow_up_questions=_build_follow_up_questions(detected_language),
            disclaimer=_build_disclaimer(detected_language),
            matched_rule_names=[],
            matched_rule_details=[],
            risk_factors=[],
            score_breakdown=TriageScoreBreakdown(
                base_score=0,
                adjustment_score=0,
                total_score=0,
            ),
            guidance_meta=TriageGuidanceMeta(
                emergency=False,
                urgent=False,
                display_level="green",
            ),
            duration=payload.duration,
            severity=payload.severity,
            age=payload.age,
            additional_info=payload.additional_info,
            debug={"empty_query": True},
        )

    internal_query = _build_internal_query(
        query=query,
        detected_language=detected_language,
    )
    normalized_query = _build_normalized_query(internal_query)

    triage_result = evaluate_triage_level(
        query=query,
        internal_query=internal_query,
        normalized_query=normalized_query,
        detected_language=detected_language,
    )

    logger.info(
        "[TRIAGE] query=%s detected_language=%s triage_level=%s triage_score=%s matched_patterns=%s",
        query,
        triage_result.detected_language,
        triage_result.triage_level,
        triage_result.triage_score,
        triage_result.matched_patterns,
    )

    return TriageResponse(
        query=query,
        detected_language=triage_result.detected_language,
        triage_level=triage_result.triage_level,
        triage_message=triage_result.triage_message,
        triage_score=triage_result.triage_score,
        matched_patterns=_build_pattern_items(
            matched_patterns=triage_result.matched_patterns,
            triage_score=triage_result.triage_score,
        ),
        recommendations=_build_recommendations(
            triage_level=triage_result.triage_level,
            detected_language=triage_result.detected_language,
        ),
        follow_up_questions=_build_follow_up_questions(
            detected_language=triage_result.detected_language,
        ),
        disclaimer=_build_disclaimer(
            detected_language=triage_result.detected_language,
        ),
        matched_rule_names=triage_result.matched_rule_names,
        matched_rule_details=_build_matched_rule_details(
            triage_result.matched_rule_details,
        ),
        risk_factors=_build_risk_factors(
            triage_result.risk_factors,
        ),
        score_breakdown=_build_score_breakdown(
            triage_result.score_breakdown,
        ),
        guidance_meta=_build_guidance_meta(
            triage_result.guidance_meta,
        ),
        duration=payload.duration,
        severity=payload.severity,
        age=payload.age,
        additional_info=payload.additional_info,
        debug=triage_result.debug,
    )