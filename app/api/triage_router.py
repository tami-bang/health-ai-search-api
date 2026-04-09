# app/api/triage_router.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록

from fastapi import APIRouter  # 라우터 등록

from app.schemas import TriageRequest  # triage 요청 스키마
from app.schemas import TriageResponse  # triage 응답 스키마
from app.services.language_utils import detect_query_language  # 입력 언어 감지
from app.services.translator import translate_ko_to_en  # 한국어 -> 영어 번역
from app.services.triage_service import evaluate_triage_level  # triage 평가 서비스


logger = logging.getLogger(__name__)  # triage 라우터 로그 기록

router = APIRouter(tags=["triage"])  # triage 전용 라우터 분리


def _build_internal_query(
    query: str,
    detected_language: str,
) -> str:
    if detected_language == "ko":
        translated_query = translate_ko_to_en(query)
        return translated_query.strip() if translated_query and translated_query.strip() else query

    return query


def _build_normalized_query(internal_query: str) -> str:
    # 확장 포인트:
    # triage 전용 normalize 규칙이 생기면 여기서만 교체
    return (internal_query or "").strip().lower()


@router.post(
    "/triage",
    response_model=TriageResponse,
    summary="Triage",
)
def triage(payload: TriageRequest) -> TriageResponse:
    query = payload.query.strip()
    detected_language = detect_query_language(query)
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
        matched_patterns=triage_result.matched_patterns,
    )