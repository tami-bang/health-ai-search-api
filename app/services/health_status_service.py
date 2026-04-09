# health_status_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from app.core.settings import APP_ENV  # 현재 실행 환경
from app.core.settings import APP_NAME  # 앱 이름
from app.services.internal_vector_store import is_vector_index_ready  # 벡터 인덱스 준비 상태 확인
from app.services.model_loader import is_model_ready  # 모델 준비 상태 확인

def build_live_status() -> dict:
    return {
        "app_name": APP_NAME,
        "environment": APP_ENV,
        "status": "ok",
    }

def build_ready_status() -> dict:
    model_ready = is_model_ready()
    vector_index_ready = is_vector_index_ready()

    overall_status = "ready" if model_ready and vector_index_ready else "not_ready"

    return {
        "status": overall_status,
        "dependencies": {
            "symptom_model": model_ready,
            "internal_vector_index": vector_index_ready,
        },
    }