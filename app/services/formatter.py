# formatter.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # dict 타입 힌트 보조

from app.core.symptom_rules import DEFAULT_NOTICE  # 공통 안내문


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


def _to_related_topic(item: dict[str, Any]) -> dict[str, Any]:
    data = {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source": item.get("source", ""),
        "document_type": item.get("document_type", ""),
    }

    if item.get("semantic_score") is not None:
        data["semantic_score"] = round(float(item["semantic_score"]), 4)

    if item.get("hybrid_score") is not None:
        data["hybrid_score"] = round(float(item["hybrid_score"]), 4)

    return data


def format_response(query: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "query": query,
            "top_result": None,
            "results": [],
            "related_topics": [],
            "notice": DEFAULT_NOTICE,
        }

    return {
        "query": query,
        "top_result": _to_result_item(items[0]),
        "results": [_to_result_item(item) for item in items],
        "related_topics": [_to_related_topic(item) for item in items[:3]],
        "notice": DEFAULT_NOTICE,
    }