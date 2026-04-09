# app/services/retriever.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from concurrent.futures import ThreadPoolExecutor  # 병렬 검색 실행
from concurrent.futures import as_completed  # 병렬 완료 순회
from typing import Any  # dict 타입 힌트 보조
from typing import Callable  # 검색 함수 타입 힌트

from app.core.settings import ENABLE_EXTERNAL_SEARCH  # 외부 검색 사용 여부
from app.core.settings import ENABLE_INTERNAL_SEARCH  # 내부 검색 사용 여부
from app.core.settings import RETRIEVAL_MAX_WORKERS  # 병렬 검색 worker 수
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 복합 증상 구분자
from app.core.symptom_rules import SYMPTOM_PRIORITY_KEYWORDS  # 증상별 우선 키워드
from app.core.symptom_rules import SYMPTOM_SEARCH_EXPANSIONS  # 증상별 검색 확장어
from app.services.internal_vector_store import search_internal_knowledge  # 내부 벡터 검색
from app.services.medlineplus_client import search_medlineplus  # 외부 실시간 검색

logger = logging.getLogger(__name__)


def _parse_symptom_keys(query: str) -> list[str]:
    cleaned_query = (query or "").strip().lower()
    if not cleaned_query:
        return []

    if NORMALIZED_QUERY_SEPARATOR not in cleaned_query:
        return [cleaned_query]

    return [
        symptom.strip().lower()
        for symptom in cleaned_query.split(NORMALIZED_QUERY_SEPARATOR)
        if symptom and symptom.strip()
    ]


def _append_unique_query(
    expanded_queries: list[str],
    candidate_query: str,
) -> None:
    normalized_candidate = str(candidate_query).strip().lower()
    if not normalized_candidate:
        return

    if normalized_candidate in expanded_queries:
        return

    expanded_queries.append(normalized_candidate)


def _build_search_queries(query: str) -> list[str]:
    symptom_keys = _parse_symptom_keys(query)
    if not symptom_keys:
        return []

    expanded_queries: list[str] = []

    # 복합 증상 전체 표현도 먼저 넣어 복합 질환 문서를 잡는다.
    if len(symptom_keys) > 1:
        _append_unique_query(expanded_queries, " ".join(symptom_keys))

    for symptom_key in symptom_keys:
        _append_unique_query(expanded_queries, symptom_key)

        mapped_queries = SYMPTOM_SEARCH_EXPANSIONS.get(symptom_key, [])
        for item in mapped_queries:
            _append_unique_query(expanded_queries, item)

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


def _build_priority_keywords(normalized_query: str) -> list[str]:
    symptom_keys = _parse_symptom_keys(normalized_query)
    merged_keywords: list[str] = []
    seen_keywords: set[str] = set()

    for symptom_key in symptom_keys:
        for keyword in SYMPTOM_PRIORITY_KEYWORDS.get(symptom_key, []):
            cleaned_keyword = str(keyword).strip().lower()
            if not cleaned_keyword or cleaned_keyword in seen_keywords:
                continue

            seen_keywords.add(cleaned_keyword)
            merged_keywords.append(cleaned_keyword)

    return merged_keywords


def _compute_priority_boost(item: dict[str, Any], normalized_query: str) -> float:
    title = str(item.get("title", "")).strip().lower()
    summary = str(item.get("summary", "")).strip().lower()
    keywords = _build_priority_keywords(normalized_query)

    if not keywords:
        return 0.0

    boost_score = 0.0

    for keyword in keywords:
        if keyword == title:
            boost_score += 0.45
        elif keyword in title:
            boost_score += 0.20

        if keyword in summary:
            boost_score += 0.08

    return round(boost_score, 4)


def _apply_retrieval_priority(
    items: list[dict[str, Any]],
    normalized_query: str,
) -> list[dict[str, Any]]:
    prioritized_items: list[dict[str, Any]] = []

    for item in items:
        new_item = dict(item)
        retrieval_boost = _compute_priority_boost(new_item, normalized_query)
        new_item["retrieval_priority_boost"] = retrieval_boost
        prioritized_items.append(new_item)

    prioritized_items.sort(
        key=lambda item: (
            item.get("retrieval_priority_boost", 0.0),
            item.get("hybrid_score", 0.0),
            item.get("semantic_score", 0.0),
        ),
        reverse=True,
    )
    return prioritized_items


def _build_search_tasks(
    search_queries: list[str],
) -> list[tuple[str, str, Callable[[str], list[dict[str, Any]]]]]:
    tasks: list[tuple[str, str, Callable[[str], list[dict[str, Any]]]]] = []

    if ENABLE_INTERNAL_SEARCH:
        for search_query in search_queries:
            tasks.append(("internal", search_query, search_internal_knowledge))

    if ENABLE_EXTERNAL_SEARCH:
        for search_query in search_queries:
            tasks.append(("external", search_query, search_medlineplus))

    return tasks


def _execute_search_task(
    source_name: str,
    search_query: str,
    search_function: Callable[[str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    try:
        results = search_function(search_query)
        logger.info(
            "[RETRIEVER] source=%s query=%s count=%s",
            source_name,
            search_query,
            len(results),
        )
        return results

    except Exception as error:
        logger.warning(
            "[RETRIEVER] source=%s query=%s failed error=%s",
            source_name,
            search_query,
            error,
        )
        return []


def _run_parallel_searches(
    tasks: list[tuple[str, str, Callable[[str], list[dict[str, Any]]]]],
) -> list[dict[str, Any]]:
    if not tasks:
        return []

    if len(tasks) == 1:
        source_name, search_query, search_function = tasks[0]
        return _execute_search_task(
            source_name=source_name,
            search_query=search_query,
            search_function=search_function,
        )

    merged_items: list[dict[str, Any]] = []
    max_workers = min(RETRIEVAL_MAX_WORKERS, len(tasks))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                _execute_search_task,
                source_name,
                search_query,
                search_function,
            ): (source_name, search_query)
            for source_name, search_query, search_function in tasks
        }

        for future in as_completed(future_map):
            try:
                merged_items.extend(future.result())
            except Exception as error:
                source_name, search_query = future_map[future]
                logger.warning(
                    "[RETRIEVER] future failed source=%s query=%s error=%s",
                    source_name,
                    search_query,
                    error,
                )

    return merged_items


def retrieve_health_topics(query: str) -> list[dict[str, Any]]:
    """
    검색 오케스트레이션 레이어
    - 내부 지식: vector search
    - 외부 지식: MedlinePlus live search
    - 복합 증상 query expansion 적용
    - 내부/외부 검색을 병렬 처리해 전체 latency 편차를 줄인다
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    search_queries = _build_search_queries(cleaned_query)
    tasks = _build_search_tasks(search_queries)
    merged_items = _run_parallel_searches(tasks)

    deduplicated_items = _deduplicate_items(merged_items)
    prioritized_items = _apply_retrieval_priority(
        deduplicated_items,
        cleaned_query.lower(),
    )
    return prioritized_items