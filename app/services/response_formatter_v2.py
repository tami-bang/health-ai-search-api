# app/services/response_formatter_v2.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from typing import Any  # 용도: dict 타입 힌트 보조

from app.core.symptom_rules import DEFAULT_NOTICE  # 용도: 공통 안내 문구


def _to_result_item(item: dict[str, Any]) -> dict[str, Any]:
    data = {
        "title": item.get("title", ""),
        "summary": item.get("summary", ""),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "document_type": item.get("document_type", ""),
    }

    if item.get("semantic_score") is not None:
        data["semantic_score"] = round(float(item["semantic_score"]), 4)

    if item.get("keyword_boost") is not None:
        data["keyword_boost"] = round(float(item["keyword_boost"]), 4)

    if item.get("hybrid_score") is not None:
        data["hybrid_score"] = round(float(item["hybrid_score"]), 4)

    if item.get("reranked_by"):
        data["reranked_by"] = item["reranked_by"]

    return data


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
    results = [_to_result_item(item) for item in items]
    top_result = results[0] if results else None

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
        "results_bundle": {
            "top_result": top_result,
            "results": results,
            "related_topics": results[:3],
            "ai_summary": ai_summary,
            "ai_summary_model": ai_summary_model,
            "summary_included": summary_included,
            "summary_debug": summary_debug,
        },
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