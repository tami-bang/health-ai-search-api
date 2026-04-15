from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import hashlib  # 용도: 문서 기준 안정적인 결과 ID 생성
from typing import Any  # 용도: 결과 아이템 타입 힌트 보조

from app.core.symptom_rules import DEFAULT_NOTICE  # 용도: 공통 안내 문구


DEFAULT_RESULT_CATEGORY = "general"


def _generate_stable_id(item: dict[str, Any]) -> str:
    """
    유지보수 포인트:
    - 같은 문서는 항상 같은 ID를 유지해야 프론트 key/상세조회/캐싱에 유리하다.
    - url + title 조합 기반 hash로 안정적인 식별자를 만든다.
    """
    base = f"{item.get('url', '')}-{item.get('title', '')}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def _to_float(value: Any, default: float = 0.0) -> float:
    """
    유지보수 포인트:
    - 점수 필드는 None / 문자열 / 숫자가 섞일 수 있으므로 안전 변환을 분리한다.
    - 확장 시 다른 점수 필드도 동일 함수로 재사용 가능하다.
    """
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_category(item: dict[str, Any]) -> str:
    """
    유지보수 포인트:
    - category는 프론트 호환용 alias다.
    - 기존 document_type이 없을 때만 기본값을 사용한다.
    """
    document_type = item.get("document_type")
    if document_type:
        return str(document_type)

    return DEFAULT_RESULT_CATEGORY


def _build_display_fields(item: dict[str, Any]) -> dict[str, Any]:
    """
    유지보수 포인트:
    - 프론트가 바로 쓰는 표시용 필드를 분리했다.
    - 프론트 구조가 바뀌면 이 함수만 우선 수정하면 된다.
    """
    return {
        "id": _generate_stable_id(item),
        "title": item.get("title", ""),
        "snippet": item.get("summary", ""),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "category": _normalize_category(item),
        "relevance_score": round(_to_float(item.get("hybrid_score"), 0.0), 4),
    }


def _build_analysis_fields(item: dict[str, Any]) -> dict[str, Any]:
    """
    유지보수 포인트:
    - 검색 품질 검증, 관리자 화면, 디버깅용 상세 필드를 유지한다.
    - 백엔드 고도화 정보를 잃지 않기 위해 display 필드와 분리했다.
    """
    semantic_score = item.get("semantic_score")
    keyword_boost = item.get("keyword_boost")
    hybrid_score = item.get("hybrid_score")

    return {
        "summary": item.get("summary"),
        "document_type": item.get("document_type"),
        "semantic_score": round(_to_float(semantic_score), 4) if semantic_score is not None else None,
        "keyword_boost": round(_to_float(keyword_boost), 4) if keyword_boost is not None else None,
        "hybrid_score": round(_to_float(hybrid_score), 4) if hybrid_score is not None else None,
        "reranked_by": item.get("reranked_by"),
    }


def _to_result_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    핵심 전략:
    - 프론트 호환 필드와 기존 고도화 필드를 함께 내려준다.
    - 프론트는 snippet/category/relevance_score를 사용하면 되고,
      백엔드는 summary/hybrid_score 등 원본 분석 필드를 계속 활용할 수 있다.
    """
    result_item = {}
    result_item.update(_build_display_fields(item))
    result_item.update(_build_analysis_fields(item))
    return result_item


def _build_meta(
    detected_language: str,
    internal_query: str,
    normalized_query: str,
    normalize_method: str,
    normalize_score: float,
    predicted_label: str | None,
    model_confidence: float,
    model_backend: str | None,
    model_version: str | None,
    search_query: str,
    is_error: bool,
    error_code: str | None,
    timings: dict[str, float],
) -> dict[str, Any]:
    return {
        "detected_language": detected_language,
        "internal_query": internal_query,
        "normalized_query": normalized_query,
        "normalize_method": normalize_method,
        "normalize_score": normalize_score,
        "predicted_label": predicted_label,
        "model_confidence": model_confidence,
        "model_backend": model_backend,
        "model_version": model_version,
        "search_query": search_query,
        "is_error": is_error,
        "error_code": error_code,
        "timings": timings,
    }


def _build_guidance(
    triage_level: str,
    triage_message: str,
    triage_score: int,
    matched_patterns: list[str],
    question_suggestions: list[str],
) -> dict[str, Any]:
    return {
        "notice": DEFAULT_NOTICE,
        "triage_level": triage_level,
        "triage_message": triage_message,
        "triage_score": triage_score,
        "matched_patterns": matched_patterns,
        "question_suggestions": question_suggestions,
    }


def _build_results_bundle(
    items: list[dict[str, Any]],
    ai_summary: str | None,
    ai_summary_model: str | None,
    summary_included: bool,
    summary_debug: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    유지보수 포인트:
    - results/top_result/related_topics 조립을 분리해 응답 구성을 명확히 했다.
    - related_topics 규칙이 바뀌면 이 함수에서만 수정하면 된다.
    """
    results = [_to_result_item(item) for item in items]
    top_result = results[0] if results else None

    return {
        "top_result": top_result,
        "results": results,
        "related_topics": results[:3],
        "ai_summary": ai_summary,
        "ai_summary_model": ai_summary_model,
        "summary_included": summary_included,
        "summary_debug": summary_debug,
    }


def build_search_response_v2(
    query: str,
    items: list[dict[str, Any]],
    detected_language: str,
    internal_query: str,
    normalized_query: str,
    normalize_method: str,
    normalize_score: float,
    predicted_label: str | None,
    model_confidence: float,
    model_backend: str | None,
    model_version: str | None,
    search_query: str,
    triage_level: str,
    triage_message: str,
    triage_score: int,
    matched_patterns: list[str],
    question_suggestions: list[str],
    ai_summary: str | None,
    ai_summary_model: str | None,
    timings: dict[str, float],
    summary_included: bool,
    summary_debug: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "query": query,
        "meta": _build_meta(
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
            is_error=False,
            error_code=None,
            timings=timings,
        ),
        "guidance": _build_guidance(
            triage_level=triage_level,
            triage_message=triage_message,
            triage_score=triage_score,
            matched_patterns=matched_patterns,
            question_suggestions=question_suggestions,
        ),
        "results_bundle": _build_results_bundle(
            items=items,
            ai_summary=ai_summary,
            ai_summary_model=ai_summary_model,
            summary_included=summary_included,
            summary_debug=summary_debug,
        ),
    }


def build_error_response_v2(
    query: str,
    detected_language: str,
    internal_query: str,
    normalized_query: str,
    normalize_method: str,
    normalize_score: float,
    predicted_label: str | None,
    model_confidence: float,
    model_backend: str | None,
    model_version: str | None,
    search_query: str,
    triage_level: str,
    triage_message: str,
    triage_score: int,
    matched_patterns: list[str],
    question_suggestions: list[str],
    message: str,
    error_code: str,
    timings: dict[str, float],
    summary_included: bool,
    summary_debug: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "query": query,
        "meta": _build_meta(
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
            is_error=True,
            error_code=error_code,
            timings=timings,
        ),
        "guidance": _build_guidance(
            triage_level=triage_level,
            triage_message=triage_message,
            triage_score=triage_score,
            matched_patterns=matched_patterns,
            question_suggestions=question_suggestions,
        ),
        "results_bundle": {
            "top_result": None,
            "results": [],
            "related_topics": [],
            "ai_summary": None,
            "ai_summary_model": None,
            "summary_included": summary_included,
            "summary_debug": summary_debug,
        },
        "message": message,
    }