# ai_ranker.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from functools import lru_cache  # text embedding 캐시
from typing import Any  # dict/list 타입 힌트 보조

import numpy as np  # 벡터 유사도 계산
from sentence_transformers import SentenceTransformer  # 문장 임베딩 모델 로드

_MODEL: SentenceTransformer | None = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def get_embedding_model() -> SentenceTransformer:
    """
    임베딩 모델 lazy load
    - 여러 서비스에서 재사용하므로 1회만 로드
    """
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(_MODEL_NAME)
    return _MODEL


def build_search_text(item: dict[str, Any]) -> str:
    title = (item.get("title") or "").strip()
    summary = (item.get("summary") or "").strip()

    if title and summary:
        return f"{title}. {summary}"
    return title or summary


@lru_cache(maxsize=2048)
def _encode_single_text(text: str) -> np.ndarray:
    """
    유지보수 포인트:
    - rerank 병목의 대부분은 item text 재임베딩이다.
    - 검색 결과 문서는 반복 조회가 많아서 text 단위 캐시가 효과적이다.
    """
    model = get_embedding_model()
    return model.encode(
        [text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]


def _encode_query_text(text: str) -> np.ndarray:
    """
    query는 반복성이 상대적으로 낮아서 별도 캐시 없이 처리한다.
    """
    model = get_embedding_model()
    return model.encode(
        [text],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]


def _parse_keyword_hints(keyword_hint: str | None) -> list[str]:
    cleaned_hint = (keyword_hint or "").strip().lower()
    if not cleaned_hint:
        return []

    if "|" not in cleaned_hint:
        return [cleaned_hint]

    return [
        token.strip()
        for token in cleaned_hint.split("|")
        if token and token.strip()
    ]


def compute_keyword_boost(
    item: dict[str, Any],
    keyword_hint: str | None = None,
) -> tuple[float, dict[str, float]]:
    title = (item.get("title") or "").strip().lower()
    summary = (item.get("summary") or "").strip().lower()
    hints = _parse_keyword_hints(keyword_hint)

    if not hints:
        return 0.0, {
            "title_exact": 0.0,
            "title_contains": 0.0,
            "summary_contains": 0.0,
            "multi_hint_coverage": 0.0,
            "retrieval_priority_boost": 0.0,
        }

    title_exact = 0.0
    title_contains = 0.0
    summary_contains = 0.0
    multi_hint_coverage = 0.0
    retrieval_priority_boost = float(item.get("retrieval_priority_boost", 0.0) or 0.0)

    matched_hint_count = 0

    for hint in hints:
        matched_this_hint = False

        if title == hint:
            title_exact += 0.45
            matched_this_hint = True
        elif hint in title:
            title_contains += 0.25
            matched_this_hint = True

        if hint in summary:
            summary_contains += 0.10
            matched_this_hint = True

        if matched_this_hint:
            matched_hint_count += 1

    # 복합 증상일 때 여러 hint를 동시에 커버하는 문서에 추가 가점
    if len(hints) >= 2 and matched_hint_count >= 2:
        multi_hint_coverage = 0.18

    total_boost = (
        title_exact
        + title_contains
        + summary_contains
        + multi_hint_coverage
        + retrieval_priority_boost
    )

    return total_boost, {
        "title_exact": round(title_exact, 4),
        "title_contains": round(title_contains, 4),
        "summary_contains": round(summary_contains, 4),
        "multi_hint_coverage": round(multi_hint_coverage, 4),
        "retrieval_priority_boost": round(retrieval_priority_boost, 4),
    }


def _prepare_valid_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    valid_items: list[dict[str, Any]] = []
    texts: list[str] = []

    for item in items:
        text = build_search_text(item)
        if not text:
            continue

        valid_items.append(item)
        texts.append(text)

    return valid_items, texts


def rerank_results(
    query: str,
    items: list[dict[str, Any]],
    keyword_hint: str | None = None,
) -> list[dict[str, Any]]:
    if not items:
        return []

    valid_items, texts = _prepare_valid_items(items)
    if not valid_items:
        return items

    if len(valid_items) == 1:
        single = dict(valid_items[0])

        keyword_boost, _ = compute_keyword_boost(
            single,
            keyword_hint=keyword_hint,
        )

        single["semantic_score"] = 1.0
        single["keyword_boost"] = round(keyword_boost, 4)
        single["hybrid_score"] = round(1.0 + keyword_boost, 4)
        single["reranked_by"] = f"{_MODEL_NAME}+keyword_boost"
        return [single]

    try:
        query_embedding = _encode_query_text(query)
        item_embeddings = np.vstack([
            _encode_single_text(text)
            for text in texts
        ])

        semantic_scores = np.dot(item_embeddings, query_embedding)

        ranked_items: list[dict[str, Any]] = []
        for item, semantic_score in zip(valid_items, semantic_scores):
            new_item = dict(item)

            keyword_boost, _ = compute_keyword_boost(
                new_item,
                keyword_hint=keyword_hint,
            )

            hybrid_score = float(semantic_score) + float(keyword_boost)

            new_item["semantic_score"] = round(float(semantic_score), 4)
            new_item["keyword_boost"] = round(float(keyword_boost), 4)
            new_item["hybrid_score"] = round(hybrid_score, 4)
            new_item["reranked_by"] = f"{_MODEL_NAME}+keyword_boost"

            ranked_items.append(new_item)

        ranked_items.sort(
            key=lambda item: item.get("hybrid_score", 0.0),
            reverse=True,
        )
        return ranked_items

    except Exception:
        fallback_items: list[dict[str, Any]] = []
        for item in valid_items:
            new_item = dict(item)

            keyword_boost, _ = compute_keyword_boost(
                new_item,
                keyword_hint=keyword_hint,
            )

            new_item["semantic_score"] = None
            new_item["keyword_boost"] = round(keyword_boost, 4)
            new_item["hybrid_score"] = round(keyword_boost, 4)
            new_item["reranked_by"] = "fallback_keyword_boost"

            fallback_items.append(new_item)

        fallback_items.sort(
            key=lambda item: item.get("hybrid_score", 0.0),
            reverse=True,
        )
        return fallback_items