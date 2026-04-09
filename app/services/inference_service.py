# app/services/inference_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # 공용 타입 힌트

from app.services.model_loader import predict_result  # 통합 분류 예측 호출


def classify_symptom_text(text: str) -> dict[str, Any]:
    """
    서비스 레이어에서 모델 로더를 직접 노출하지 않으려고 한 번 감싼다.
    나중에 threshold, A/B, shadow inference를 여기서 확장하면 된다.
    """
    return predict_result(text)