# retriever.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # dict 타입 힌트 보조

from app.core.settings import ENABLE_EXTERNAL_SEARCH  # 외부 검색 사용 여부
from app.core.settings import ENABLE_INTERNAL_SEARCH  # 내부 검색 사용 여부
from app.core.symptom_rules import SYMPTOM_PRIORITY_KEYWORDS  # 증상별 우선 키워드
from app.core.symptom_rules import SYMPTOM_SEARCH_EXPANSIONS  # 증상별 검색 확장어
from app.services.internal_vector_store import search_internal_knowledge  # 내부 벡터 검색
from app.services.medlineplus_client import search_medlineplus  # 외부 실시간 검색

ERROR_TITLES = {"request error", "parse error"}

def _build_search_queries(query: str) -> list[str]:
    cleaned_query = (query or "").strip().lower()
    if not cleaned_query:
        return []

    expanded_queries = [cleaned_query]
    mapped_queries = SYMPTOM_SEARCH_EXPANSIONS.get(cleaned_query, [])

    for item in mapped_queries:
        normalized_item = str(item).strip().lower()
        if normalized_item and normalized_item not in expanded_queries:
            expanded_queries.append(normalized_item)

    return expanded_queries

def _deduplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for item in items:
        title = str(item.get("title", "")).strip().lower()
        url = str(item.get("url", "")).strip().lower()
        dedupe_key = (title, url)

        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        deduplicated_items.append(item)

    return deduplicated_items

def _compute_priority_boost(item: dict[str, Any], normalized_query: str) -> float:
    title = str(item.get("title", "")).strip().lower()
    summary = str(item.get("summary", "")).strip().lower()
    keywords = SYMPTOM_PRIORITY_KEYWORDS.get(normalized_query, [])

    if not keywords:
        return 0.0

    boost_score = 0.0

    for keyword in keywords:
        cleaned_keyword = keyword.strip().lower()
        if not cleaned_keyword:
            continue

        if cleaned_keyword == title:
            boost_score += 0.45
        elif cleaned_keyword in title:
            boost_score += 0.20

        if cleaned_keyword in summary:
            boost_score += 0.08

    return round(boost_score, 4)

def _apply_retrieval_priority(items: list[dict[str, Any]], normalized_query: str) -> list[dict[str, Any]]:
    prioritized_items: list[dict[str, Any]] = []

    for item in items:
        new_item = dict(item)
        retrieval_boost = _compute_priority_boost(new_item, normalized_query)
        new_item["retrieval_priority_boost"] = retrieval_boost
        prioritized_items.append(new_item)

    prioritized_items.sort(
        key=lambda item: item.get("retrieval_priority_boost", 0.0),
        reverse=True,
    )
    return prioritized_items

def retrieve_health_topics(query: str) -> list[dict[str, Any]]:
    """
    검색 오케스트레이션 레이어
    - 내부 지식: vector search
    - 외부 지식: MedlinePlus live search
    - 증상별 query expansion 적용
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    search_queries = _build_search_queries(cleaned_query)
    merged_items: list[dict[str, Any]] = []

    if ENABLE_INTERNAL_SEARCH:
        for search_query in search_queries:
            merged_items.extend(search_internal_knowledge(search_query))

    if ENABLE_EXTERNAL_SEARCH:
        for search_query in search_queries:
            merged_items.extend(search_medlineplus(search_query))

    deduplicated_items = _deduplicate_items(merged_items)
    prioritized_items = _apply_retrieval_priority(deduplicated_items, cleaned_query.lower())
    return prioritized_items

def is_retrieval_error(items: list[dict[str, Any]]) -> bool:
    if not items:
        return False

    first_title = (items[0].get("title") or "").strip().lower()
    first_type = (items[0].get("document_type") or "").strip().lower()

    return first_title in ERROR_TITLES or first_type == "external_error"