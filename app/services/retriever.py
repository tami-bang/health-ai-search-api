# retriever.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # dict 타입 힌트 보조

from app.services.internal_vector_store import search_internal_knowledge  # 내부 벡터 검색
from app.services.medlineplus_client import search_medlineplus  # 외부 실시간 검색


ERROR_TITLES = {"request error", "parse error"}


def retrieve_health_topics(query: str) -> list[dict[str, Any]]:
    """
    검색 오케스트레이션 레이어
    - 내부 지식: vector search
    - 외부 지식: MedlinePlus live search
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    internal_items = search_internal_knowledge(cleaned_query)
    external_items = search_medlineplus(cleaned_query)

    return internal_items + external_items


def is_retrieval_error(items: list[dict[str, Any]]) -> bool:
    if not items:
        return False

    first_title = (items[0].get("title") or "").strip().lower()
    first_type = (items[0].get("document_type") or "").strip().lower()

    return first_title in ERROR_TITLES or first_type == "external_error"