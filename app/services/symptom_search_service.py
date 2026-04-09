# app/services/symptom_search_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import logging  # 용도: 서비스 로그 기록
import re  # 용도: summary 후처리용 정규식 처리
import time  # 용도: 처리 시간 측정
from dataclasses import dataclass  # 용도: triage 결과 내부 표준화
from typing import Any  # 용도: 타입 힌트 보조

from app.core.error_codes import INTERNAL_SERVER_ERROR  # 용도: 공통 서버 에러 코드
from app.core.error_codes import NO_RESULTS  # 용도: 검색 결과 없음 에러 코드
from app.core.exceptions import AppException  # 용도: 앱 공통 예외
from app.core.settings import DEFAULT_INCLUDE_SUMMARY  # 용도: 기본 요약 포함 여부
from app.core.settings import ENABLE_STARTUP_WARMUP  # 용도: 시작 시 워밍업 여부
from app.core.settings import ENABLE_TRIAGE  # 용도: 응급도 기능 사용 여부
from app.core.settings import HF_GENERATION_MODEL_NAME  # 용도: 생성 모델명 기록
from app.core.settings import RERANK_CANDIDATE_LIMIT  # 용도: rerank 후보 상한
from app.core.settings import SUMMARY_MODEL_PRELOAD  # 용도: 생성 모델 preload 여부
from app.core.symptom_rules import AI_FALLBACK_MIN_CONFIDENCE  # 용도: AI fallback 기준
from app.core.symptom_rules import AI_FALLBACK_MIN_TOKEN_COUNT  # 용도: AI 예측 최소 토큰 수
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 용도: 복합 증상 구분자
from app.core.symptom_rules import PREDICTED_LABEL_DISPLAY_MIN_CONFIDENCE  # 용도: predicted_label 노출 기준
from app.services.ai_ranker import rerank_results  # 용도: 검색 결과 재랭킹
from app.services.health_status_service import record_search_metrics  # 용도: 운영 메트릭 기록
from app.services.hf_generation_service import get_generation_components  # 용도: 생성 모델 워밍업
from app.services.inference_service import classify_symptom_text  # 용도: 통합 추론 서비스
from app.services.internal_vector_store import build_internal_vector_index  # 용도: 내부 벡터 인덱스 구축
from app.services.language_utils import detect_query_language  # 용도: 입력 언어 감지
from app.services.model_loader import load_model_artifacts  # 용도: 아티팩트 기반 모델 로드
from app.services.question_suggester import build_question_suggestions  # 용도: 추천 질문 생성
from app.services.response_enricher import build_extractive_summary  # 용도: fallback summary 생성
from app.services.response_enricher import build_summary_debug  # 용도: summary debug 정보 생성
from app.services.response_enricher import evaluate_summary_quality  # 용도: summary 품질 검증
from app.services.response_enricher import generate_ai_summary  # 용도: AI 요약 생성
from app.services.response_formatter_v2 import build_error_response_v2  # 용도: 에러 응답 생성
from app.services.response_formatter_v2 import build_search_response_v2  # 용도: 성공 응답 생성
from app.services.response_localizer import localize_response  # 용도: 응답 현지화
from app.services.retriever import retrieve_health_topics  # 용도: 통합 검색
from app.services.symptom_normalizer import normalize_symptom_query  # 용도: 증상 정규화
from app.services.symptom_normalizer import warmup_normalizer  # 용도: 정규화 캐시 준비
from app.services.translator import translate_text  # 용도: 질의 번역
from app.services.triage_service import evaluate_triage_level  # 용도: 응급도 분기
from app.validators.search_request_validator import validate_search_query  # 용도: 입력 검증

logger = logging.getLogger(__name__)

DEFAULT_TRIAGE_LEVEL = "green"
DEFAULT_TRIAGE_MESSAGE = (
    "This information may help with general understanding, but symptoms should still be monitored carefully."
)

SUMMARY_FALLBACK_MODEL_NAME = "extractive-fallback-v2"
SUMMARY_MIN_TEXT_LENGTH = 12


@dataclass(slots=True)
class SearchTriageResult:
    triage_level: str
    triage_message: str
    triage_score: int
    matched_patterns: list[str]


def startup_search_dependencies() -> None:
    model_loaded = load_model_artifacts()
    logger.info("[APP] startup: symptom model loaded=%s", model_loaded)

    warmup_normalizer()
    logger.info("[APP] startup: symptom normalizer ready")

    build_internal_vector_index()
    logger.info("[APP] startup: internal vector index ready")

    if ENABLE_STARTUP_WARMUP and SUMMARY_MODEL_PRELOAD:
        try:
            get_generation_components()
            logger.info("[APP] startup: generation model preloaded")
        except Exception as error:
            logger.warning("[APP] startup: generation warmup skipped: %s", error)


def _parse_normalized_symptoms(normalized_query: str) -> list[str]:
    cleaned_query = (normalized_query or "").strip()
    if not cleaned_query:
        return []

    if NORMALIZED_QUERY_SEPARATOR not in cleaned_query:
        return [cleaned_query.lower()]

    return [
        symptom.strip().lower()
        for symptom in cleaned_query.split(NORMALIZED_QUERY_SEPARATOR)
        if symptom and symptom.strip()
    ]


def _limit_rerank_candidates(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    retrieval 단계에서 이미 1차 우선순위가 적용되어 있으므로
    semantic rerank는 상위 후보만 다시 정렬해도 품질 손실이 작다.
    """
    if len(items) <= RERANK_CANDIDATE_LIMIT:
        return items

    return items[:RERANK_CANDIDATE_LIMIT]


def _build_internal_query(
    query: str,
    input_language: str,
    normalized_query: str,
    normalize_method: str,
) -> str:
    if input_language != "ko":
        return query

    if normalized_query and normalize_method not in {"fallback_tokens", "fallback_raw"}:
        return " ".join(_parse_normalized_symptoms(normalized_query)).strip()

    translated = translate_text(
        query,
        target_lang="en",
        source_lang="auto",
    )
    return translated.strip() if translated and translated.strip() else query


def _should_predict_label(internal_query: str) -> bool:
    token_count = len((internal_query or "").split())
    return token_count >= AI_FALLBACK_MIN_TOKEN_COUNT


def _should_expose_predicted_label(
    predicted_label: str | None,
    model_confidence: float,
) -> bool:
    if not predicted_label:
        return False

    return model_confidence >= PREDICTED_LABEL_DISPLAY_MIN_CONFIDENCE


def _top_item_matches_normalized_query(
    item: dict[str, Any],
    normalized_query: str,
) -> bool:
    symptoms = _parse_normalized_symptoms(normalized_query)
    if not symptoms:
        return False

    title = str(item.get("title") or "").lower()
    summary = str(item.get("summary") or "").lower()
    combined = f"{title} {summary}".strip()

    if not combined:
        return False

    return any(symptom in combined for symptom in symptoms)


def _should_use_ai_fallback(
    items: list[dict[str, Any]],
    normalized_query: str,
    predicted_label: str | None,
    model_confidence: float,
) -> bool:
    if not predicted_label:
        return False

    if model_confidence < AI_FALLBACK_MIN_CONFIDENCE:
        return False

    if not items:
        return True

    top_item = items[0]
    if _top_item_matches_normalized_query(top_item, normalized_query):
        return False

    return True


def _build_default_triage_result() -> SearchTriageResult:
    return SearchTriageResult(
        triage_level=DEFAULT_TRIAGE_LEVEL,
        triage_message=DEFAULT_TRIAGE_MESSAGE,
        triage_score=0,
        matched_patterns=[],
    )


def _coerce_triage_result(raw_result: Any) -> SearchTriageResult:
    if raw_result is None:
        return _build_default_triage_result()

    if isinstance(raw_result, tuple):
        triage_level = str(raw_result[0]) if len(raw_result) > 0 else DEFAULT_TRIAGE_LEVEL
        triage_message = str(raw_result[1]) if len(raw_result) > 1 else DEFAULT_TRIAGE_MESSAGE
        return SearchTriageResult(
            triage_level=triage_level,
            triage_message=triage_message,
            triage_score=0,
            matched_patterns=[],
        )

    triage_level = str(
        getattr(raw_result, "triage_level", DEFAULT_TRIAGE_LEVEL)
        or DEFAULT_TRIAGE_LEVEL
    )
    triage_message = str(
        getattr(raw_result, "triage_message", DEFAULT_TRIAGE_MESSAGE)
        or DEFAULT_TRIAGE_MESSAGE
    )

    raw_triage_score = getattr(raw_result, "triage_score", 0)
    triage_score = int(raw_triage_score or 0)

    raw_matched_patterns = getattr(raw_result, "matched_patterns", []) or []
    matched_patterns = [
        str(pattern).strip()
        for pattern in raw_matched_patterns
        if str(pattern).strip()
    ]

    return SearchTriageResult(
        triage_level=triage_level,
        triage_message=triage_message,
        triage_score=triage_score,
        matched_patterns=matched_patterns,
    )


def _evaluate_triage(
    query: str,
    internal_query: str,
    normalized_query: str,
    input_language: str,
) -> SearchTriageResult:
    if not ENABLE_TRIAGE:
        return _build_default_triage_result()

    raw_result = evaluate_triage_level(
        query=query,
        internal_query=internal_query,
        normalized_query=normalized_query,
        detected_language=input_language,
    )
    return _coerce_triage_result(raw_result)


def _build_default_timings() -> dict[str, float]:
    return {
        "validation_ms": 0.0,
        "translation_ms": 0.0,
        "normalization_ms": 0.0,
        "triage_ms": 0.0,
        "retrieval_ms": 0.0,
        "prediction_ms": 0.0,
        "rerank_ms": 0.0,
        "summary_ms": 0.0,
        "total_ms": 0.0,
    }


def _elapsed_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 2)


def _resolve_summary_requested(
    include_summary: bool | None,
    force_summary: bool,
) -> bool:
    if force_summary:
        return True

    if include_summary is None:
        return DEFAULT_INCLUDE_SUMMARY

    return include_summary


def _normalize_summary_text(summary_text: str | None) -> str | None:
    if not summary_text:
        return None

    collapsed_text = re.sub(r"\s+", " ", str(summary_text)).strip()
    if len(collapsed_text) < SUMMARY_MIN_TEXT_LENGTH:
        return None

    return collapsed_text


def _build_summary_debug_result(
    detected_language: str,
    normalized_query: str,
    ranked_items: list[dict[str, Any]],
    ai_summary: str | None,
    ai_summary_model: str | None,
    quality_result: dict[str, Any] | None,
    summary_status: str,
) -> dict[str, Any]:
    return build_summary_debug(
        detected_language=detected_language,
        normalized_query=normalized_query,
        ranked_items=ranked_items,
        ai_summary=ai_summary,
        ai_summary_model=ai_summary_model,
        quality_result=quality_result,
        summary_status=summary_status,
    )


def _generate_summary_with_fallback(
    query: str,
    detected_language: str,
    normalized_query: str,
    ranked_items: list[dict[str, Any]],
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    generated_summary: str | None = None
    quality_result: dict[str, Any] | None = None

    try:
        generated_summary = generate_ai_summary(
            query=query,
            detected_language=detected_language,
            ranked_items=ranked_items,
            normalized_query=normalized_query,
        )
        normalized_generated_summary = _normalize_summary_text(generated_summary)

        if normalized_generated_summary:
            quality_result = evaluate_summary_quality(
                summary_text=normalized_generated_summary,
                normalized_query=normalized_query,
                ranked_items=ranked_items,
            )

            if quality_result.get("is_valid"):
                debug_result = _build_summary_debug_result(
                    detected_language=detected_language,
                    normalized_query=normalized_query,
                    ranked_items=ranked_items,
                    ai_summary=normalized_generated_summary,
                    ai_summary_model=HF_GENERATION_MODEL_NAME,
                    quality_result=quality_result,
                    summary_status="llm_accepted",
                )
                return normalized_generated_summary, HF_GENERATION_MODEL_NAME, debug_result

            logger.warning(
                "[SEARCH] summary rejected query=%s reason=%s",
                query,
                quality_result.get("reason"),
            )
        else:
            logger.warning(
                "[SEARCH] summary generation returned empty text query=%s",
                query,
            )

    except Exception as error:
        logger.warning(
            "[SEARCH] summary generation failed query=%s error=%s",
            query,
            error,
        )

    fallback_summary = build_extractive_summary(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )
    normalized_fallback_summary = _normalize_summary_text(fallback_summary)
    if normalized_fallback_summary:
        fallback_quality_result = evaluate_summary_quality(
            summary_text=normalized_fallback_summary,
            normalized_query=normalized_query,
            ranked_items=ranked_items,
        )
        debug_result = _build_summary_debug_result(
            detected_language=detected_language,
            normalized_query=normalized_query,
            ranked_items=ranked_items,
            ai_summary=normalized_fallback_summary,
            ai_summary_model=SUMMARY_FALLBACK_MODEL_NAME,
            quality_result=fallback_quality_result,
            summary_status="fallback_used",
        )
        return normalized_fallback_summary, SUMMARY_FALLBACK_MODEL_NAME, debug_result

    debug_result = _build_summary_debug_result(
        detected_language=detected_language,
        normalized_query=normalized_query,
        ranked_items=ranked_items,
        ai_summary=generated_summary,
        ai_summary_model=None,
        quality_result=quality_result,
        summary_status="summary_unavailable",
    )
    return None, None, debug_result


def search_symptom(
    query: str,
    include_summary: bool | None = None,
    force_summary: bool = False,
) -> dict[str, Any]:
    request_started_at = time.perf_counter()
    timings = _build_default_timings()

    summary_requested = _resolve_summary_requested(
        include_summary=include_summary,
        force_summary=force_summary,
    )

    detected_language = "en"
    internal_query = ""
    normalized_query = ""
    normalize_method = ""
    normalize_score = 0.0
    prediction_candidate_label: str | None = None
    predicted_label: str | None = None
    model_confidence = 0.0
    model_backend: str | None = None
    model_version: str | None = None
    search_query = ""
    triage_result = _build_default_triage_result()
    question_suggestions: list[str] = []

    try:
        stage_started_at = time.perf_counter()
        validated_query = validate_search_query(query)
        timings["validation_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        detected_language = detect_query_language(validated_query)
        timings["translation_ms"] = 0.0

        stage_started_at = time.perf_counter()
        normalization_input = validated_query if detected_language != "ko" else ""
        normalized_query, normalize_method, normalize_score = normalize_symptom_query(
            original_query=validated_query,
            internal_query=normalization_input,
        )
        search_query = normalized_query
        timings["normalization_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        internal_query = _build_internal_query(
            query=validated_query,
            input_language=detected_language,
            normalized_query=normalized_query,
            normalize_method=normalize_method,
        )
        timings["translation_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        triage_result = _evaluate_triage(
            query=validated_query,
            internal_query=internal_query,
            normalized_query=normalized_query,
            input_language=detected_language,
        )
        question_suggestions = build_question_suggestions(
            normalized_query=normalized_query,
            detected_language=detected_language,
        )
        timings["triage_ms"] = _elapsed_ms(stage_started_at)

        logger.info(
            "[SEARCH] normalized query=%s method=%s score=%s",
            normalized_query,
            normalize_method,
            normalize_score,
        )
        logger.info(
            "[SEARCH] triage integrated query=%s level=%s score=%s matched_patterns=%s",
            validated_query,
            triage_result.triage_level,
            triage_result.triage_score,
            triage_result.matched_patterns,
        )

        stage_started_at = time.perf_counter()
        items = retrieve_health_topics(search_query)
        timings["retrieval_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        if _should_predict_label(internal_query):
            prediction_result = classify_symptom_text(internal_query)
            prediction_candidate_label = prediction_result.get("label")
            model_confidence = float(prediction_result.get("confidence", 0.0) or 0.0)
            model_backend = prediction_result.get("backend")
            model_version = prediction_result.get("model_version")

            if _should_expose_predicted_label(
                predicted_label=prediction_candidate_label,
                model_confidence=model_confidence,
            ):
                predicted_label = prediction_candidate_label

        timings["prediction_ms"] = _elapsed_ms(stage_started_at)

        if _should_use_ai_fallback(
            items=items,
            normalized_query=normalized_query,
            predicted_label=prediction_candidate_label,
            model_confidence=model_confidence,
        ):
            search_query = prediction_candidate_label or search_query

            stage_started_at = time.perf_counter()
            items = retrieve_health_topics(search_query)
            timings["retrieval_ms"] = round(
                timings["retrieval_ms"] + _elapsed_ms(stage_started_at),
                2,
            )

        stage_started_at = time.perf_counter()
        rerank_candidates = _limit_rerank_candidates(items)

        ranked_items = rerank_results(
            query=internal_query or validated_query,
            items=rerank_candidates,
            keyword_hint=normalized_query,
        )
        timings["rerank_ms"] = _elapsed_ms(stage_started_at)

        logger.info(
            "[SEARCH] rerank candidates query=%s original=%s limited=%s",
            validated_query,
            len(items),
            len(rerank_candidates),
        )

        ai_summary: str | None = None
        ai_summary_model: str | None = None
        summary_debug: dict[str, Any] | None = None

        logger.info(
            "[SEARCH] summary requested query=%s requested=%s force_summary=%s ranked_items=%s",
            validated_query,
            summary_requested,
            force_summary,
            len(ranked_items),
        )

        if summary_requested and ranked_items:
            stage_started_at = time.perf_counter()
            ai_summary, ai_summary_model, summary_debug = _generate_summary_with_fallback(
                query=validated_query,
                detected_language=detected_language,
                normalized_query=normalized_query,
                ranked_items=ranked_items,
            )
            timings["summary_ms"] = _elapsed_ms(stage_started_at)

            logger.info(
                "[SEARCH] summary result query=%s generated=%s model=%s status=%s",
                validated_query,
                bool(ai_summary),
                ai_summary_model,
                summary_debug.get("summary_status") if isinstance(summary_debug, dict) else None,
            )

        if summary_requested and not summary_debug:
            summary_debug = _build_summary_debug_result(
                detected_language=detected_language,
                normalized_query=normalized_query,
                ranked_items=ranked_items,
                ai_summary=None,
                ai_summary_model=None,
                quality_result=None,
                summary_status="requested_but_not_built",
            )

        timings["total_ms"] = _elapsed_ms(request_started_at)

        if not ranked_items:
            error_response = build_error_response_v2(
                query=validated_query,
                detected_language=detected_language,
                internal_query=internal_query,
                normalized_query=normalized_query,
                normalize_method=normalize_method,
                normalize_score=normalize_score,
                predicted_label=predicted_label,
                model_confidence=model_confidence,
                model_backend=model_backend,
                model_version=model_version,
                search_query=search_query,
                triage_level=triage_result.triage_level,
                triage_message=triage_result.triage_message,
                triage_score=triage_result.triage_score,
                matched_patterns=triage_result.matched_patterns,
                question_suggestions=question_suggestions,
                message="No relevant health information was found for this query.",
                error_code=NO_RESULTS,
                timings=timings,
                summary_included=bool(ai_summary),
                summary_debug=summary_debug,
            )
            localized_error_response = localize_response(
                error_response,
                target_lang=detected_language,
            )
            record_search_metrics(
                total_latency_ms=timings["total_ms"],
                is_success=False,
                summary_included=bool(ai_summary),
            )
            return localized_error_response

        success_response = build_search_response_v2(
            query=validated_query,
            items=ranked_items,
            detected_language=detected_language,
            internal_query=internal_query,
            normalized_query=normalized_query,
            normalize_method=normalize_method,
            normalize_score=normalize_score,
            predicted_label=predicted_label,
            model_confidence=model_confidence,
            model_backend=model_backend,
            model_version=model_version,
            search_query=search_query,
            triage_level=triage_result.triage_level,
            triage_message=triage_result.triage_message,
            triage_score=triage_result.triage_score,
            matched_patterns=triage_result.matched_patterns,
            question_suggestions=question_suggestions,
            ai_summary=ai_summary,
            ai_summary_model=ai_summary_model,
            timings=timings,
            summary_included=bool(ai_summary),
            summary_debug=summary_debug,
        )
        localized_success_response = localize_response(
            success_response,
            target_lang=detected_language,
        )
        record_search_metrics(
            total_latency_ms=timings["total_ms"],
            is_success=True,
            summary_included=bool(ai_summary),
        )
        return localized_success_response

    except AppException as error:
        timings["total_ms"] = _elapsed_ms(request_started_at)

        error_response = build_error_response_v2(
            query=query,
            detected_language=detected_language,
            internal_query=internal_query,
            normalized_query=normalized_query,
            normalize_method=normalize_method,
            normalize_score=normalize_score,
            predicted_label=predicted_label,
            model_confidence=model_confidence,
            model_backend=model_backend,
            model_version=model_version,
            search_query=search_query,
            triage_level=triage_result.triage_level,
            triage_message=triage_result.triage_message,
            triage_score=triage_result.triage_score,
            matched_patterns=triage_result.matched_patterns,
            question_suggestions=question_suggestions,
            message=error.message,
            error_code=error.error_code,
            timings=timings,
            summary_included=False,
            summary_debug=None,
        )
        localized_error_response = localize_response(
            error_response,
            target_lang=detected_language,
        )
        record_search_metrics(
            total_latency_ms=timings["total_ms"],
            is_success=False,
            summary_included=False,
        )
        return localized_error_response

    except Exception as error:
        logger.exception("[SEARCH] unexpected error: %s", error)
        timings["total_ms"] = _elapsed_ms(request_started_at)

        error_response = build_error_response_v2(
            query=query,
            detected_language=detected_language,
            internal_query=internal_query,
            normalized_query=normalized_query,
            normalize_method=normalize_method,
            normalize_score=normalize_score,
            predicted_label=predicted_label,
            model_confidence=model_confidence,
            model_backend=model_backend,
            model_version=model_version,
            search_query=search_query,
            triage_level=triage_result.triage_level,
            triage_message=triage_result.triage_message,
            triage_score=triage_result.triage_score,
            matched_patterns=triage_result.matched_patterns,
            question_suggestions=question_suggestions,
            message="Internal server error.",
            error_code=INTERNAL_SERVER_ERROR,
            timings=timings,
            summary_included=False,
            summary_debug=None,
        )
        localized_error_response = localize_response(
            error_response,
            target_lang=detected_language,
        )
        record_search_metrics(
            total_latency_ms=timings["total_ms"],
            is_success=False,
            summary_included=False,
        )
        return localized_error_response