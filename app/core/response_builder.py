# response_builder.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from app.core.symptom_rules import DEFAULT_NOTICE  # 공통 안내문 상수


def build_success_response(data: dict) -> dict:
    data["is_error"] = False
    data["error_code"] = None

    if "notice" not in data:
        data["notice"] = DEFAULT_NOTICE

    return data


def build_error_response(
    query: str,
    message: str,
    error_code: str,
) -> dict:
    return {
        "query": query,
        "top_result": None,
        "results": [],
        "related_topics": [],
        "message": message,
        "error_code": error_code,
        "is_error": True,
        "notice": DEFAULT_NOTICE,
        "ai_summary": None,
        "ai_summary_model": None,
    }