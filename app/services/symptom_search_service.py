# app/services/symptom_search_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 서비스 로그 기록
import time  # 처리 시간 측정
from typing import Any  # 타입 힌트 보조

from app.core.error_codes import INTERNAL_SERVER_ERROR  # 공통 서버 에러 코드
from app.core.error_codes import NO_RESULTS  # 검색 결과 없음 에러 코드
from app.core.exceptions import AppException  # 앱 공통 예외
from app.core.settings import DEFAULT_INCLUDE_SUMMARY  # 기본 요약 포함 여부
from app.core.settings import ENABLE_STARTUP_WARMUP  # 시작 시 워밍업 여부
from app.core.settings import ENABLE_TRIAGE  # 응급도 기능 사용 여부
from app.core.settings import HF_GENERATION_MODEL_NAME  # 생성 모델명 기록
from app.core.settings import SUMMARY_MODEL_PRELOAD  # 생성 모델 preload 여부
from app.core.symptom_rules import AI_FALLBACK_MIN_CONFIDENCE  # AI fallback 기준
from app.core.symptom_rules import AI_FALLBACK_MIN_TOKEN_COUNT  # AI 예측 최소 토큰 수
from app.services.ai_ranker import rerank_results  # 검색 결과 재랭킹
from app.services.health_status_service import record_search_metrics  # 운영 메트릭 기록
from app.services.hf_generation_service import get_generation_components  # 생성 모델 워밍업
from app.services.internal_vector_store import build_internal_vector_index  # 내부 벡터 인덱스 구축
from app.services.language_utils import detect_query_language  # 입력 언어 감지
from app.services.model_loader import load_model_artifacts  # 아티팩트 기반 모델 로드
from app.services.model_loader import predict_with_confidence  # AI 라벨 예측
from app.services.question_suggester import build_question_suggestions  # 추천 질문 생성
from app.services.response_enricher import generate_ai_summary  # AI 요약 생성
from app.services.response_formatter_v2 import build_error_response_v2  # 에러 응답 생성
from app.services.response_formatter_v2 import build_search_response_v2  # 성공 응답 생성
from app.services.response_localizer import localize_response  # 응답 현지화
from app.services.retriever import retrieve_health_topics  # 통합 검색
from app.services.symptom_normalizer import normalize_symptom_query  # 증상 정규화
from app.services.symptom_normalizer import warmup_normalizer  # 정규화 캐시 준비
from app.services.translator import translate_text  # 질의 번역
from app.services.triage_service import evaluate_triage_level  # 응급도 분기
from app.validators.search_request_validator import validate_search_query  # 입력 검증

logger = logging.getLogger(__name__)


def startup_search_dependencies() -> None:
    # 학습 대신 로드만 수행하고, 없으면 degraded 상태로 두어 검색 API는 계속 살린다.
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


def _build_internal_query(query: str, input_language: str) -> str:
    if input_language != "ko":
        return query

    translated = translate_text(
        query,
        target_lang="en",
        source_lang="auto",
    )
    return translated.strip() if translated and translated.strip() else query


def _should_predict_label(internal_query: str) -> bool:
    token_count = len((internal_query or "").split())
    return token_count >= AI_FALLBACK_MIN_TOKEN_COUNT


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
    title = (top_item.get("title") or "").lower()
    summary = (top_item.get("summary") or "").lower()
    combined = f"{title} {summary}".strip()

    if not combined:
        return True

    if normalized_query and normalized_query.lower() not in combined:
        return True

    return False


def _evaluate_triage(
    query: str,
    internal_query: str,
    normalized_query: str,
    input_language: str,
) -> tuple[str, str]:
    if not ENABLE_TRIAGE:
        return (
            "green",
            "This information may help with general understanding, but symptoms should still be monitored carefully.",
        )

    return evaluate_triage_level(
        query=query,
        internal_query=internal_query,
        normalized_query=normalized_query,
        detected_language=input_language,
    )


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


def search_symptom(
    query: str,
    include_summary: bool | None = None,
) -> dict[str, Any]:
    request_started_at = time.perf_counter()
    timings = _build_default_timings()

    summary_requested = DEFAULT_INCLUDE_SUMMARY if include_summary is None else include_summary

    detected_language = "en"
    internal_query = ""
    normalized_query = ""
    normalize_method = ""
    normalize_score = 0.0
    predicted_label: str | None = None
    model_confidence = 0.0
    search_query = ""
    triage_level = "green"
    triage_message = "This information may help with general understanding, but symptoms should still be monitored carefully."
    question_suggestions: list[str] = []

    try:
        stage_started_at = time.perf_counter()
        validated_query = validate_search_query(query)
        timings["validation_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        detected_language = detect_query_language(validated_query)
        internal_query = _build_internal_query(validated_query, detected_language)
        timings["translation_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        normalized_query, normalize_method, normalize_score = normalize_symptom_query(
            original_query=validated_query,
            internal_query=internal_query,
        )
        search_query = normalized_query
        timings["normalization_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        triage_level, triage_message = _evaluate_triage(
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

        stage_started_at = time.perf_counter()
        items = retrieve_health_topics(search_query)
        timings["retrieval_ms"] = _elapsed_ms(stage_started_at)

        stage_started_at = time.perf_counter()
        if _should_predict_label(internal_query):
            predicted_label, model_confidence = predict_with_confidence(internal_query)
        timings["prediction_ms"] = _elapsed_ms(stage_started_at)

        if _should_use_ai_fallback(
            items=items,
            normalized_query=normalized_query,
            predicted_label=predicted_label,
            model_confidence=model_confidence,
        ):
            search_query = predicted_label or search_query
            stage_started_at = time.perf_counter()
            items = retrieve_health_topics(search_query)
            timings["retrieval_ms"] = round(
                timings["retrieval_ms"] + _elapsed_ms(stage_started_at),
                2,
            )

        stage_started_at = time.perf_counter()
        ranked_items = rerank_results(
            query=internal_query or validated_query,
            items=items,
            keyword_hint=normalized_query,
        )
        timings["rerank_ms"] = _elapsed_ms(stage_started_at)

        ai_summary: str | None = None
        ai_summary_model: str | None = None

        if summary_requested and ranked_items:
            stage_started_at = time.perf_counter()
            ai_summary = generate_ai_summary(
                query=validated_query,
                detected_language=detected_language,
                ranked_items=ranked_items,
            )
            timings["summary_ms"] = _elapsed_ms(stage_started_at)

            if ai_summary:
                ai_summary_model = HF_GENERATION_MODEL_NAME

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
                search_query=search_query,
                triage_level=triage_level,
                triage_message=triage_message,
                question_suggestions=question_suggestions,
                message="No relevant health information was found for this query.",
                error_code=NO_RESULTS,
                timings=timings,
                summary_included=bool(ai_summary),
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
            search_query=search_query,
            triage_level=triage_level,
            triage_message=triage_message,
            question_suggestions=question_suggestions,
            ai_summary=ai_summary,
            ai_summary_model=ai_summary_model,
            timings=timings,
            summary_included=bool(ai_summary),
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
            search_query=search_query,
            triage_level=triage_level,
            triage_message=triage_message,
            question_suggestions=question_suggestions,
            message=error.message,
            error_code=error.error_code,
            timings=timings,
            summary_included=False,
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
            search_query=search_query,
            triage_level=triage_level,
            triage_message=triage_message,
            question_suggestions=question_suggestions,
            message="Internal server error.",
            error_code=INTERNAL_SERVER_ERROR,
            timings=timings,
            summary_included=False,
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