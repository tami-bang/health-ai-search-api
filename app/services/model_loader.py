# app/services/model_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from pathlib import Path  # 파일 경로 처리
from typing import Any  # 타입 힌트 보조

import joblib  # sklearn 아티팩트 로드

from app.core.settings import SYMPTOM_MODEL_ARTIFACT_PATH  # 분류기 아티팩트 경로
from app.core.settings import SYMPTOM_VECTORIZER_ARTIFACT_PATH  # 벡터라이저 아티팩트 경로


logger = logging.getLogger(__name__)

_vectorizer: Any | None = None
_model: Any | None = None
_load_attempted = False


def load_model_artifacts(force_reload: bool = False) -> bool:
    global _vectorizer, _model, _load_attempted

    if _load_attempted and not force_reload:
        return is_model_ready()

    vectorizer_path = Path(SYMPTOM_VECTORIZER_ARTIFACT_PATH)
    model_path = Path(SYMPTOM_MODEL_ARTIFACT_PATH)

    _load_attempted = True
    _vectorizer = None
    _model = None

    if not vectorizer_path.exists() or not model_path.exists():
        logger.warning(
            "[MODEL] artifacts not found: vectorizer=%s model=%s",
            vectorizer_path,
            model_path,
        )
        return False

    try:
        _vectorizer = joblib.load(vectorizer_path)
        _model = joblib.load(model_path)
        logger.info("[MODEL] artifacts loaded successfully")
        return True
    except Exception as error:
        logger.exception("[MODEL] artifact load failed: %s", error)
        _vectorizer = None
        _model = None
        return False


def is_model_ready() -> bool:
    return _vectorizer is not None and _model is not None


def get_model_status() -> dict[str, Any]:
    return {
        "is_ready": is_model_ready(),
        "load_attempted": _load_attempted,
        "vectorizer_path": SYMPTOM_VECTORIZER_ARTIFACT_PATH,
        "model_path": SYMPTOM_MODEL_ARTIFACT_PATH,
    }


def predict(text: str) -> str:
    cleaned_text = str(text).strip() if text is not None else ""
    if not cleaned_text:
        return ""

    if not is_model_ready():
        load_model_artifacts()

    if not is_model_ready():
        return ""

    transformed = _vectorizer.transform([cleaned_text])
    prediction = _model.predict(transformed)[0]
    return str(prediction)


def predict_with_confidence(text: str) -> tuple[str | None, float]:
    cleaned_text = str(text).strip() if text is not None else ""
    if not cleaned_text:
        return None, 0.0

    if not is_model_ready():
        load_model_artifacts()

    if not is_model_ready():
        return None, 0.0

    transformed = _vectorizer.transform([cleaned_text])

    try:
        probabilities = _model.predict_proba(transformed)[0]
        best_index = int(probabilities.argmax())
        best_label = str(_model.classes_[best_index])
        best_score = float(probabilities[best_index])
        return best_label, round(best_score, 4)
    except Exception:
        predicted = _model.predict(transformed)[0]
        return str(predicted), 0.0