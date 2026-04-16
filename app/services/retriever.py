from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import logging  # 용도: 실행 로그 기록
import re  # 용도: 문자열 정규화 처리
from concurrent.futures import ThreadPoolExecutor  # 용도: 병렬 검색 실행
from concurrent.futures import as_completed  # 용도: 병렬 완료 순회
from typing import Any  # 용도: dict 타입 힌트 보조
from typing import Callable  # 용도: 검색 함수 타입 힌트

from app.core.settings import ENABLE_EXTERNAL_SEARCH  # 용도: 외부 검색 사용 여부
from app.core.settings import ENABLE_INTERNAL_SEARCH  # 용도: 내부 검색 사용 여부
from app.core.settings import RETRIEVAL_MAX_WORKERS  # 용도: 병렬 검색 worker 수
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 용도: 복합 증상 구분자
from app.core.symptom_rules import SYMPTOM_PRIORITY_KEYWORDS  # 용도: 증상별 우선 키워드
from app.core.symptom_rules import SYMPTOM_SEARCH_EXPANSIONS  # 용도: 증상별 검색 확장어
from app.services.internal_vector_store import search_internal_knowledge  # 용도: 내부 벡터 검색
from app.services.medlineplus_client import search_medlineplus  # 용도: 외부 실시간 검색

logger = logging.getLogger(__name__)

MIN_BACKOFF_TOKEN_LENGTH = 3  # 용도: fallback 토큰 최소 길이
MAX_PREFIX_FALLBACK_LENGTH = 3  # 용도: 최후 fallback prefix 길이
BACKOFF_STOPWORDS: set[str] = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "have",
    "been",
    "my",
    "your",
    "is",
    "are",
    "eye",
    "eyes",
    "nose",
}  # 용도: 과도하게 일반적인 fallback 토큰 제외


def _normalize_text(text: str) -> str:
    """
    검색용 문자열 정규화
    - 소문자 통일
    - 연속 공백 제거
    """
    cleaned_text = str(text or "").strip().lower()
    if not cleaned_text:
        return ""

    return re.sub(r"\s+", " ", cleaned_text)


def _append_unique_query(
    expanded_queries: list[str],
    candidate_query: str,
) -> None:
    """
    중복 없이 검색 후보 추가
    """
    normalized_candidate = _normalize_text(candidate_query)
    if not normalized_candidate:
        return

    if normalized_candidate in expanded_queries:
        return

    expanded_queries.append(normalized_candidate)


def _parse_symptom_keys(query: str) -> list[str]:
    """
    복합 증상 문자열을 증상 키 목록으로 분해
    """
    cleaned_query = _normalize_text(query)
    if not cleaned_query:
        return []

    if NORMALIZED_QUERY_SEPARATOR not in cleaned_query:
        return [cleaned_query]

    return [
        _normalize_text(symptom)
        for symptom in cleaned_query.split(NORMALIZED_QUERY_SEPARATOR)
        if _normalize_text(symptom)
    ]


def _build_backoff_queries(symptom_key: str) -> list[str]:
    """
    긴 증상 구문을 토큰 단위로 분해해 안전한 backoff 후보 생성
    """
    tokens = [
        _normalize_text(token)
        for token in str(symptom_key).split()
        if _normalize_text(token)
    ]

    if len(tokens) <= 1:
        return []

    backoff_queries: list[str] = []
    for token in tokens:
        if len(token) < MIN_BACKOFF_TOKEN_LENGTH:
            continue
        if token in BACKOFF_STOPWORDS:
            continue
        backoff_queries.append(token)

    return backoff_queries


def _build_prefix_fallback_queries(search_queries: list[str]) -> list[str]:
    """
    최후 fallback용 prefix query 생성
    """
    prefix_queries: list[str] = []

    for query in search_queries:
        normalized_query = _normalize_text(query)
        if len(normalized_query) < MAX_PREFIX_FALLBACK_LENGTH:
            continue

        prefix_query = normalized_query[:MAX_PREFIX_FALLBACK_LENGTH]
        _append_unique_query(prefix_queries, prefix_query)

    return prefix_queries


def _build_search_queries(
    query: str,
    original_query: str | None = None,
    translated_query: str | None = None,
) -> list[str]:
    """
    검색 후보 생성
    우선순위:
    1. normalized query
    2. original query
    3. translated query
    4. 복합 증상 결합형
    5. 증상별 확장어
    6. 토큰 backoff
    """
    expanded_queries: list[str] = []

    normalized_query_text = _normalize_text(query)
    original_query_text = _normalize_text(original_query or "")
    translated_query_text = _normalize_text(translated_query or "")

    if normalized_query_text:
        _append_unique_query(expanded_queries, normalized_query_text)

    if original_query_text:
        _append_unique_query(expanded_queries, original_query_text)

    if translated_query_text:
        _append_unique_query(expanded_queries, translated_query_text)

    symptom_keys = _parse_symptom_keys(normalized_query_text)
    if not symptom_keys:
        symptom_keys = _parse_symptom_keys(original_query_text)

    if len(symptom_keys) > 1:
        _append_unique_query(expanded_queries, " ".join(symptom_keys))

    for symptom_key in symptom_keys:
        _append_unique_query(expanded_queries, symptom_key)

        mapped_queries = SYMPTOM_SEARCH_EXPANSIONS.get(symptom_key, [])
        for mapped_query in mapped_queries:
            _append_unique_query(expanded_queries, mapped_query)

        for backoff_query in _build_backoff_queries(symptom_key):
            _append_unique_query(expanded_queries, backoff_query)

    return expanded_queries


def _deduplicate_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    title + url 기준 dedupe
    """
    deduplicated_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for item in items:
        title = _normalize_text(item.get("title", ""))
        url = _normalize_text(item.get("url", ""))
        dedupe_key = (title, url)

        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        deduplicated_items.append(item)

    return deduplicated_items


def _build_priority_keywords(normalized_query: str) -> list[str]:
    """
    증상 우선 키워드 병합
    """
    symptom_keys = _parse_symptom_keys(normalized_query)
    merged_keywords: list[str] = []
    seen_keywords: set[str] = set()

    for symptom_key in symptom_keys:
        for keyword in SYMPTOM_PRIORITY_KEYWORDS.get(symptom_key, []):
            cleaned_keyword = _normalize_text(keyword)
            if not cleaned_keyword:
                continue
            if cleaned_keyword in seen_keywords:
                continue

            seen_keywords.add(cleaned_keyword)
            merged_keywords.append(cleaned_keyword)

    return merged_keywords


def _compute_priority_boost(item: dict[str, Any], normalized_query: str) -> float:
    """
    retrieval 단계 우선 키워드 기반 boost 계산
    """
    title = _normalize_text(item.get("title", ""))
    summary = _normalize_text(item.get("summary", ""))
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
    """
    retrieval priority boost 반영 정렬
    """
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
    """
    내부/외부 검색 task 생성
    """
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
    """
    단일 검색 task 실행
    """
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
    """
    검색 task 병렬 실행
    """
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


def _run_search_round(search_queries: list[str]) -> list[dict[str, Any]]:
    """
    하나의 검색 라운드 실행
    """
    if not search_queries:
        return []

    tasks = _build_search_tasks(search_queries)
    if not tasks:
        return []

    return _run_parallel_searches(tasks)


def retrieve_health_topics(
    query: str,
    original_query: str | None = None,
    translated_query: str | None = None,
) -> list[dict[str, Any]]:
    """
    검색 오케스트레이션 레이어

    처리 흐름:
    1. normalized/original/translated 기반 multi query 생성
    2. 내부/외부 검색 병렬 실행
    3. 결과 없으면 prefix fallback 재시도
    4. dedupe
    5. retrieval priority boost 적용
    """
    cleaned_query = _normalize_text(query)
    cleaned_original_query = _normalize_text(original_query or "")
    cleaned_translated_query = _normalize_text(translated_query or "")

    if not cleaned_query and not cleaned_original_query and not cleaned_translated_query:
        return []

    primary_queries = _build_search_queries(
        query=cleaned_query,
        original_query=cleaned_original_query,
        translated_query=cleaned_translated_query,
    )

    if not primary_queries:
        fallback_seed = cleaned_query or cleaned_original_query or cleaned_translated_query
        primary_queries = [fallback_seed]

    logger.info("[RETRIEVER] primary_queries=%s", primary_queries)

    merged_items = _run_search_round(primary_queries)

    if not merged_items:
        fallback_queries = _build_prefix_fallback_queries(primary_queries)
        logger.info("[RETRIEVER] fallback_queries=%s", fallback_queries)

        if fallback_queries:
            merged_items = _run_search_round(fallback_queries)

    deduplicated_items = _deduplicate_items(merged_items)

    priority_base_query = cleaned_query or cleaned_original_query or cleaned_translated_query
    prioritized_items = _apply_retrieval_priority(
        deduplicated_items,
        priority_base_query,
    )

    logger.info(
        "[RETRIEVER] done query=%s original=%s translated=%s total=%s deduped=%s",
        cleaned_query,
        cleaned_original_query,
        cleaned_translated_query,
        len(merged_items),
        len(prioritized_items),
    )

    return prioritized_items