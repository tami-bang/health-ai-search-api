# internal_vector_store.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # dict 타입 힌트 보조

import numpy as np  # 벡터 유사도 계산

from app.core.settings import RAG_CHUNK_OVERLAP  # chunk overlap 설정
from app.core.settings import RAG_CHUNK_SIZE  # chunk size 설정
from app.core.settings import RAG_INTERNAL_TOP_K  # 내부 검색 top-k 설정
from app.core.settings import RAG_MIN_SCORE  # 내부 검색 최소 score
from app.repositories.internal_knowledge_repository import load_internal_health_documents  # 내부 지식 로드
from app.services.ai_ranker import get_embedding_model  # 공용 임베딩 모델 재사용
from app.services.chunker import chunk_text  # 문서 chunking

_VECTOR_ROWS: list[dict[str, Any]] = []
_VECTOR_MATRIX: np.ndarray | None = None

def _build_chunk_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    documents = load_internal_health_documents()

    for document in documents:
        document_id = (document.get("document_id") or "").strip()
        title = (document.get("title") or "").strip()
        source = (document.get("source") or "InternalKnowledge").strip()
        url = (document.get("url") or "").strip()
        content = (document.get("content") or "").strip()

        if not content:
            continue

        chunks = chunk_text(
            text=content,
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP,
        )

        for chunk_index, chunk in enumerate(chunks, start=1):
            rows.append({
                "document_id": document_id,
                "chunk_id": f"{document_id}-chunk-{chunk_index}",
                "title": title,
                "summary": chunk,
                "source": source,
                "url": url,
                "document_type": "internal",
                "chunk_index": chunk_index,
                "chunk_text": chunk,
            })

    return rows

def build_internal_vector_index() -> None:
    global _VECTOR_ROWS, _VECTOR_MATRIX

    rows = _build_chunk_rows()
    if not rows:
        _VECTOR_ROWS = []
        _VECTOR_MATRIX = None
        return

    model = get_embedding_model()
    texts = [row["chunk_text"] for row in rows]

    matrix = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    _VECTOR_ROWS = rows
    _VECTOR_MATRIX = matrix

def is_vector_index_ready() -> bool:
    return _VECTOR_MATRIX is not None and len(_VECTOR_ROWS) > 0

def search_internal_knowledge(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    if _VECTOR_MATRIX is None or not _VECTOR_ROWS:
        return []

    model = get_embedding_model()
    query_embedding = model.encode(
        [cleaned_query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    scores = np.dot(_VECTOR_MATRIX, query_embedding)

    ranked_indices = np.argsort(scores)[::-1]
    limit = top_k if top_k is not None else RAG_INTERNAL_TOP_K
    threshold = min_score if min_score is not None else RAG_MIN_SCORE

    results: list[dict[str, Any]] = []
    seen_document_ids: set[str] = set()

    for index in ranked_indices:
        score = float(scores[index])
        if score < threshold:
            continue

        row = dict(_VECTOR_ROWS[int(index)])
        document_id = str(row.get("document_id") or "")

        # 같은 문서 chunk가 연속으로 많이 뜨면 결과 다양성이 떨어져서 문서 단위로 먼저 dedupe
        if document_id in seen_document_ids:
            continue

        seen_document_ids.add(document_id)
        row["semantic_score"] = round(score, 4)
        row["hybrid_score"] = round(score, 4)
        row["reranked_by"] = "internal_vector_search"
        results.append(row)

        if len(results) >= limit:
            break

    return results