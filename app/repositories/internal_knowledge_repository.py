# internal_knowledge_repository.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import json  # JSON 파일 로드
from pathlib import Path  # 파일 경로 처리
from typing import Any  # dict 타입 힌트 보조

from app.core.settings import INTERNAL_KNOWLEDGE_JSON_PATH  # 내부 지식 파일 경로

def load_internal_health_documents() -> list[dict[str, Any]]:
    json_path = Path(INTERNAL_KNOWLEDGE_JSON_PATH)

    if not json_path.exists():
        return []

    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    valid_documents: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        document = {
            "document_id": str(item.get("document_id", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "source": str(item.get("source", "InternalKnowledge")).strip(),
            "url": str(item.get("url", "")).strip(),
            "content": str(item.get("content", "")).strip(),
        }

        if document["document_id"] and document["title"] and document["content"]:
            valid_documents.append(document)

    return valid_documents