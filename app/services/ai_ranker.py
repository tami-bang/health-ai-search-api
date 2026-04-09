# ai_ranker.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

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

def compute_keyword_boost(
    item: dict[str, Any],
    keyword_hint: str | None = None,
) -> tuple[float, dict[str, float]]:
    title = (item.get("title") or "").strip().lower()
    summary = (item.get("summary") or "").strip().lower()
    hint = (keyword_hint or "").strip().lower()

    if not hint:
        return 0.0, {
            "title_exact": 0.0,
            "title_contains": 0.0,
            "summary_contains": 0.0,
            "retrieval_priority_boost": 0.0,
        }

    title_exact = 0.0
    title_contains = 0.0
    summary_contains = 0.0
    retrieval_priority_boost = float(item.get("retrieval_priority_boost", 0.0) or 0.0)

    if title == hint:
        title_exact = 0.45
    elif hint in title:
        title_contains = 0.25

    if hint in summary:
        summary_contains = 0.10

    total_boost = title_exact + title_contains + summary_contains + retrieval_priority_boost
    return total_boost, {
        "title_exact": title_exact,
        "title_contains": title_contains,
        "summary_contains": summary_contains,
        "retrieval_priority_boost": retrieval_priority_boost,
    }

def rerank_results(
    query: str,
    items: list[dict[str, Any]],
    keyword_hint: str | None = None,
) -> list[dict[str, Any]]:
    if not items:
        return []

    valid_items: list[dict[str, Any]] = []
    texts: list[str] = []

    for item in items:
        text = build_search_text(item)
        if text:
            valid_items.append(item)
            texts.append(text)

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
        model = get_embedding_model()

        embeddings = model.encode(
            [query] + texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        query_embedding = embeddings[0]
        item_embeddings = embeddings[1:]
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