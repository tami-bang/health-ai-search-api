# app/services/model_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import json  # 메타데이터/라벨 매핑 로드
import logging  # 실행 로그 기록
from pathlib import Path  # 파일 경로 처리
from typing import Any  # 타입 힌트 보조

import joblib  # sklearn 아티팩트 로드

from app.core.settings import HF_CLASSIFIER_ARTIFACT_DIR  # HF 분류기 경로
from app.core.settings import HF_CLASSIFIER_MAX_LENGTH  # HF 토큰 길이 제한
from app.core.settings import HF_CLASSIFIER_METADATA_PATH  # HF 메타데이터 경로
from app.core.settings import PREFERRED_CLASSIFIER_BACKEND  # 선호 백엔드
from app.core.settings import SYMPTOM_MODEL_ARTIFACT_PATH  # sklearn 분류기 경로
from app.core.settings import SYMPTOM_VECTORIZER_ARTIFACT_PATH  # sklearn 벡터라이저 경로

logger = logging.getLogger(__name__)

_sklearn_vectorizer: Any | None = None
_sklearn_model: Any | None = None
_sklearn_load_attempted = False

_hf_tokenizer: Any | None = None
_hf_model: Any | None = None
_hf_torch: Any | None = None
_hf_label_decoder: dict[int, str] = {}
_hf_load_attempted = False


def _safe_read_json(json_path: Path) -> dict[str, Any]:
    if not json_path.exists():
        return {}

    try:
        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception as error:
        logger.warning("[MODEL] failed to read json=%s error=%s", json_path, error)
        return {}


def _resolve_hf_device() -> str:
    try:
        import torch  # GPU 가능 여부 확인

        if torch.cuda.is_available():
            return "cuda"
    except Exception as error:
        logger.warning("[MODEL] torch device check failed: %s", error)

    return "cpu"


def load_sklearn_model_artifacts(force_reload: bool = False) -> bool:
    global _sklearn_vectorizer, _sklearn_model, _sklearn_load_attempted

    if _sklearn_load_attempted and not force_reload:
        return is_sklearn_model_ready()

    vectorizer_path = Path(SYMPTOM_VECTORIZER_ARTIFACT_PATH)
    model_path = Path(SYMPTOM_MODEL_ARTIFACT_PATH)

    _sklearn_load_attempted = True
    _sklearn_vectorizer = None
    _sklearn_model = None

    if not vectorizer_path.exists() or not model_path.exists():
        logger.warning(
            "[MODEL] sklearn artifacts not found: vectorizer=%s model=%s",
            vectorizer_path,
            model_path,
        )
        return False

    try:
        _sklearn_vectorizer = joblib.load(vectorizer_path)
        _sklearn_model = joblib.load(model_path)
        logger.info("[MODEL] sklearn artifacts loaded successfully")
        return True
    except Exception as error:
        logger.exception("[MODEL] sklearn artifact load failed: %s", error)
        _sklearn_vectorizer = None
        _sklearn_model = None
        return False


def load_hf_model_artifacts(force_reload: bool = False) -> bool:
    global _hf_tokenizer, _hf_model, _hf_torch, _hf_label_decoder, _hf_load_attempted

    if _hf_load_attempted and not force_reload:
        return is_hf_model_ready()

    artifact_dir = Path(HF_CLASSIFIER_ARTIFACT_DIR)
    _hf_load_attempted = True
    _hf_tokenizer = None
    _hf_model = None
    _hf_torch = None
    _hf_label_decoder = {}

    if not artifact_dir.exists():
        logger.warning("[MODEL] hf artifact dir not found: %s", artifact_dir)
        return False

    try:
        import torch  # 텐서 추론
        from transformers import AutoModelForSequenceClassification  # HF 분류 모델 로드
        from transformers import AutoTokenizer  # HF 토크나이저 로드

        tokenizer = AutoTokenizer.from_pretrained(str(artifact_dir))
        model = AutoModelForSequenceClassification.from_pretrained(str(artifact_dir))

        device_name = _resolve_hf_device()
        model = model.to(device_name)
        model.eval()

        config_id2label = getattr(model.config, "id2label", {}) or {}
        label_decoder: dict[int, str] = {}

        for raw_key, raw_value in config_id2label.items():
            try:
                label_decoder[int(raw_key)] = str(raw_value)
            except Exception:
                continue

        _hf_tokenizer = tokenizer
        _hf_model = model
        _hf_torch = torch
        _hf_label_decoder = label_decoder

        logger.info("[MODEL] hf artifacts loaded successfully device=%s", device_name)
        return True

    except Exception as error:
        logger.exception("[MODEL] hf artifact load failed: %s", error)
        _hf_tokenizer = None
        _hf_model = None
        _hf_torch = None
        _hf_label_decoder = {}
        return False


def load_model_artifacts(force_reload: bool = False) -> bool:
    """
    서비스 시작 시에는 둘 다 로드 시도하고,
    추론 시에는 preferred backend 기준으로 선택한다.
    """
    hf_loaded = load_hf_model_artifacts(force_reload=force_reload)
    sklearn_loaded = load_sklearn_model_artifacts(force_reload=force_reload)
    return hf_loaded or sklearn_loaded


def is_sklearn_model_ready() -> bool:
    return _sklearn_vectorizer is not None and _sklearn_model is not None


def is_hf_model_ready() -> bool:
    return _hf_tokenizer is not None and _hf_model is not None and _hf_torch is not None


def is_model_ready() -> bool:
    return is_hf_model_ready() or is_sklearn_model_ready()


def _predict_with_sklearn(text: str) -> tuple[str | None, float, str]:
    cleaned_text = str(text).strip() if text is not None else ""
    if not cleaned_text:
        return None, 0.0, "sklearn"

    if not is_sklearn_model_ready():
        load_sklearn_model_artifacts()

    if not is_sklearn_model_ready():
        return None, 0.0, "sklearn"

    transformed = _sklearn_vectorizer.transform([cleaned_text])

    try:
        probabilities = _sklearn_model.predict_proba(transformed)[0]
        best_index = int(probabilities.argmax())
        best_label = str(_sklearn_model.classes_[best_index])
        best_score = float(probabilities[best_index])
        return best_label, round(best_score, 4), "sklearn"
    except Exception:
        predicted = _sklearn_model.predict(transformed)[0]
        return str(predicted), 0.0, "sklearn"


def _predict_with_hf(text: str) -> tuple[str | None, float, str]:
    cleaned_text = str(text).strip() if text is not None else ""
    if not cleaned_text:
        return None, 0.0, "hf"

    if not is_hf_model_ready():
        load_hf_model_artifacts()

    if not is_hf_model_ready():
        return None, 0.0, "hf"

    device_name = next(_hf_model.parameters()).device
    encoded_inputs = _hf_tokenizer(
        cleaned_text,
        truncation=True,
        max_length=HF_CLASSIFIER_MAX_LENGTH,
        return_tensors="pt",
    )
    encoded_inputs = {
        key: value.to(device_name)
        for key, value in encoded_inputs.items()
    }

    with _hf_torch.no_grad():
        outputs = _hf_model(**encoded_inputs)
        probabilities = _hf_torch.softmax(outputs.logits, dim=-1)[0]
        best_index = int(probabilities.argmax().item())
        best_score = float(probabilities[best_index].item())

    best_label = _hf_label_decoder.get(best_index)
    if not best_label:
        best_label = str(best_index)

    return best_label, round(best_score, 4), "hf"


def predict(text: str) -> str:
    predicted_label, _confidence = predict_with_confidence(text)
    return predicted_label or ""


def predict_with_confidence(text: str) -> tuple[str | None, float]:
    preferred_backend = PREFERRED_CLASSIFIER_BACKEND

    if preferred_backend == "hf":
        predicted_label, confidence, _backend = _predict_with_hf(text)
        if predicted_label:
            return predicted_label, confidence

        predicted_label, confidence, _backend = _predict_with_sklearn(text)
        return predicted_label, confidence

    predicted_label, confidence, _backend = _predict_with_sklearn(text)
    if predicted_label:
        return predicted_label, confidence

    predicted_label, confidence, _backend = _predict_with_hf(text)
    return predicted_label, confidence


def get_model_status() -> dict[str, Any]:
    hf_metadata = _safe_read_json(Path(HF_CLASSIFIER_METADATA_PATH))

    active_backend = "none"
    if PREFERRED_CLASSIFIER_BACKEND == "hf" and is_hf_model_ready():
        active_backend = "hf"
    elif PREFERRED_CLASSIFIER_BACKEND == "sklearn" and is_sklearn_model_ready():
        active_backend = "sklearn"
    elif is_hf_model_ready():
        active_backend = "hf"
    elif is_sklearn_model_ready():
        active_backend = "sklearn"

    return {
        "is_ready": is_model_ready(),
        "active_backend": active_backend,
        "preferred_backend": PREFERRED_CLASSIFIER_BACKEND,
        "sklearn": {
            "is_ready": is_sklearn_model_ready(),
            "load_attempted": _sklearn_load_attempted,
            "vectorizer_path": SYMPTOM_VECTORIZER_ARTIFACT_PATH,
            "model_path": SYMPTOM_MODEL_ARTIFACT_PATH,
        },
        "hf": {
            "is_ready": is_hf_model_ready(),
            "load_attempted": _hf_load_attempted,
            "artifact_dir": HF_CLASSIFIER_ARTIFACT_DIR,
            "metadata_path": HF_CLASSIFIER_METADATA_PATH,
            "metadata": hf_metadata,
        },
    }