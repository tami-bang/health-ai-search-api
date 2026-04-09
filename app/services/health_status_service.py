# app/services/health_status_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # 타입 힌트 보조

from app.core.settings import APP_ENV  # 현재 실행 환경
from app.core.settings import APP_NAME  # 앱 이름
from app.core.settings import ENABLE_AI_SUMMARY  # 요약 기능 기본 설정
from app.services.internal_vector_store import is_vector_index_ready  # 벡터 인덱스 준비 상태 확인
from app.services.medlineplus_client import get_medlineplus_cache_stats  # 외부 검색 캐시 통계 조회
from app.services.model_loader import get_model_status  # 모델 상태 조회


_SEARCH_METRICS = {
    "request_count": 0,
    "success_count": 0,
    "error_count": 0,
    "summary_request_count": 0,
    "total_latency_ms": 0.0,
}


def record_search_metrics(
    total_latency_ms: float,
    is_success: bool,
    summary_included: bool,
) -> None:
    _SEARCH_METRICS["request_count"] += 1
    _SEARCH_METRICS["total_latency_ms"] += max(total_latency_ms, 0.0)

    if is_success:
        _SEARCH_METRICS["success_count"] += 1
    else:
        _SEARCH_METRICS["error_count"] += 1

    if summary_included:
        _SEARCH_METRICS["summary_request_count"] += 1


def build_live_status() -> dict[str, Any]:
    return {
        "app_name": APP_NAME,
        "environment": APP_ENV,
        "status": "ok",
    }


def build_ready_status() -> dict[str, Any]:
    model_status = get_model_status()
    vector_index_ready = is_vector_index_ready()

    dependencies = {
        "symptom_model": model_status["is_ready"],
        "internal_vector_index": vector_index_ready,
    }

    overall_status = "ready" if all(dependencies.values()) else "degraded"

    return {
        "status": overall_status,
        "dependencies": dependencies,
        "model_status": model_status,
    }


def build_metrics_status() -> dict[str, Any]:
    request_count = int(_SEARCH_METRICS["request_count"])
    average_latency_ms = (
        round(_SEARCH_METRICS["total_latency_ms"] / request_count, 2)
        if request_count > 0
        else 0.0
    )

    return {
        "search_metrics": {
            "request_count": request_count,
            "success_count": int(_SEARCH_METRICS["success_count"]),
            "error_count": int(_SEARCH_METRICS["error_count"]),
            "summary_request_count": int(_SEARCH_METRICS["summary_request_count"]),
            "average_latency_ms": average_latency_ms,
        },
        "feature_flags": {
            "enable_ai_summary_default": ENABLE_AI_SUMMARY,
        },
        "external_cache": get_medlineplus_cache_stats(),
    }