# symptom_search_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 서비스 로그 기록

from fastapi import HTTPException  # API 예외 응답 처리

from app.core.settings import HF_GENERATION_MODEL_NAME  # 생성 모델명 기록
from app.core.symptom_rules import AI_FALLBACK_MIN_CONFIDENCE  # AI fallback 기준
from app.core.symptom_rules import AI_FALLBACK_MIN_TOKEN_COUNT  # AI 예측 최소 토큰 수
from app.services.ai_ranker import rerank_results  # 검색 결과 재랭킹
from app.services.internal_vector_store import build_internal_vector_index  # 내부 벡터 인덱스 구축
from app.services.language_utils import detect_query_language  # 입력 언어 감지
from app.services.model_loader import predict_with_confidence  # AI 라벨 예측
from app.services.model_loader import train_model  # 학습 모델 초기화
from app.services.question_suggester import build_question_suggestions  # 추천 질문 생성
from app.services.response_enricher import generate_ai_summary  # AI 요약 생성
from app.services.response_formatter_v2 import build_error_response_v2  # 에러 응답 생성
from app.services.response_formatter_v2 import build_search_response_v2  # 성공 응답 생성
from app.services.response_localizer import localize_response  # 응답 현지화
from app.services.retriever import is_retrieval_error  # 검색 오류 판별
from app.services.retriever import retrieve_health_topics  # 통합 검색
from app.services.symptom_normalizer import normalize_symptom_query  # 증상 정규화
from app.services.symptom_normalizer import warmup_normalizer  # 정규화 캐시 준비
from app.services.translator import translate_text  # 질의 번역
from app.services.triage_service import evaluate_triage_level  # 응급도 분기

logger = logging.getLogger(__name__)


def startup_search_dependencies() -> None:
    logger.info("[APP] startup: training symptom model...")
    train_model()
    logger.info("[APP] startup: symptom model ready")

    warmup_normalizer()
    logger.info("[APP] startup: symptom normalizer ready")

    build_internal_vector_index()
    logger.info("[APP] startup: internal vector index ready")


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
    items: list[dict],
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

    if is_retrieval_error(items):
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


def search_symptom(query: str) -> dict:
    try:
        input_language = detect_query_language(query)
        internal_query = _build_internal_query(query, input_language)

        normalized_query, normalize_method, normalize_score = normalize_symptom_query(
            original_query=query,
            internal_query=internal_query,
        )
        search_query = normalized_query

        triage_level, triage_message = evaluate_triage_level(
            query=query,
            internal_query=internal_query,
            normalized_query=normalized_query,
            detected_language=input_language,
        )

        question_suggestions = build_question_suggestions(
            normalized_query=normalized_query,
            detected_language=input_language,
        )

        items = retrieve_health_topics(search_query)

        predicted_label: str | None = None
        model_confidence = 0.0

        if _should_predict_label(internal_query):
            try:
                predicted_label, model_confidence = predict_with_confidence(internal_query)
            except Exception as model_error:
                logger.warning("[SEARCH] predict skipped: %s", model_error)

        if _should_use_ai_fallback(
            items=items,
            normalized_query=normalized_query,
            predicted_label=predicted_label,
            model_confidence=model_confidence,
        ):
            fallback_query = predicted_label or ""
            fallback_items = retrieve_health_topics(fallback_query)

            if fallback_items and not is_retrieval_error(fallback_items):
                items = fallback_items
                search_query = fallback_query

        if not items or is_retrieval_error(items):
            error_response = build_error_response_v2(
                query=query,
                detected_language=input_language,
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
                message="검색 결과가 없습니다.",
                error_code="NO_RESULTS",
            )
            return localize_response(error_response, target_lang=input_language)

        ranked_items = rerank_results(
            query=internal_query,
            items=items,
            keyword_hint=normalized_query,
        )

        ai_summary = generate_ai_summary(
            query=query,
            detected_language=input_language,
            ranked_items=ranked_items,
        )

        response_data = build_search_response_v2(
            query=query,
            items=ranked_items,
            detected_language=input_language,
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
            ai_summary_model=HF_GENERATION_MODEL_NAME if ai_summary else None,
        )

        return localize_response(response_data, target_lang=input_language)

    except Exception as error:
        logger.exception("[SEARCH] error: %s", error)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(error)}")