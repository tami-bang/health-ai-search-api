from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import hashlib  # 용도: 문서 기준 안정적인 결과 ID 생성
from typing import Any  # 용도: 결과 아이템 타입 힌트 보조

from app.core.symptom_rules import DEFAULT_NOTICE  # 용도: 공통 안내 문구

DEFAULT_RESULT_CATEGORY = "general"


def _generate_stable_id(item: dict[str, Any]) -> str:
    """
    같은 문서는 항상 같은 ID를 유지하도록 url + title 기반 안정 ID 생성
    """
    base = f"{item.get('url', '')}-{item.get('title', '')}"
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def _to_float(value: Any, default: float = 0.0) -> float:
    """
    점수 필드 안전 변환
    """
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_category(item: dict[str, Any]) -> str:
    """
    프론트 호환용 category alias
    """
    document_type = item.get("document_type")
    if document_type:
        return str(document_type)

    return DEFAULT_RESULT_CATEGORY


def _build_display_fields(item: dict[str, Any]) -> dict[str, Any]:
    """
    프론트 표시용 필드 생성
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
    디버깅/분석용 상세 필드 유지
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
        "retrieval_priority_boost": round(_to_float(item.get("retrieval_priority_boost"), 0.0), 4),
        "reranked_by": item.get("reranked_by"),
    }


def _to_result_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    프론트 호환 필드 + 분석 필드 결합
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