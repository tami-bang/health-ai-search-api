# app/services/model_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import json  # 메타데이터 JSON 로드
import logging  # 실행 로그 기록
from pathlib import Path  # 파일 경로 처리
from typing import Any  # 공용 타입 힌트

import joblib  # sklearn 아티팩트 로드

from app.core.settings import ENABLE_GPU  # GPU 사용 가능 여부 설정
from app.core.settings import HF_CLASSIFIER_ARTIFACT_DIR  # HF 분류기 저장 경로
from app.core.settings import HF_CLASSIFIER_MAX_LENGTH  # HF 입력 토큰 길이 제한
from app.core.settings import HF_CLASSIFIER_METADATA_PATH  # HF 메타데이터 경로
from app.core.settings import HF_CLASSIFIER_MODEL_VERSION  # HF 기본 모델 버전
from app.core.settings import PREFERRED_CLASSIFIER_BACKEND  # 선호 분류 백엔드
from app.core.settings import SYMPTOM_MODEL_ARTIFACT_PATH  # sklearn 모델 경로
from app.core.settings import SYMPTOM_MODEL_VERSION  # sklearn 모델 버전
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

        if not isinstance(data, dict):
            return {}

        return data

    except Exception as error:
        logger.warning("[MODEL] failed to read json path=%s error=%s", json_path, error)
        return {}


def _get_hf_metadata() -> dict[str, Any]:
    return _safe_read_json(Path(HF_CLASSIFIER_METADATA_PATH))


def _resolve_hf_device() -> str:
    if not ENABLE_GPU:
        return "cpu"

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

    _sklearn_load_attempted = True
    _sklearn_vectorizer = None
    _sklearn_model = None

    vectorizer_path = Path(SYMPTOM_VECTORIZER_ARTIFACT_PATH)
    model_path = Path(SYMPTOM_MODEL_ARTIFACT_PATH)

    if not vectorizer_path.exists() or not model_path.exists():
        logger.warning(
            "[MODEL] sklearn artifacts not found vectorizer=%s model=%s",
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

    _hf_load_attempted = True
    _hf_tokenizer = None
    _hf_model = None
    _hf_torch = None
    _hf_label_decoder = {}

    artifact_dir = Path(HF_CLASSIFIER_ARTIFACT_DIR)
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

        label_decoder: dict[int, str] = {}
        raw_id2label = getattr(model.config, "id2label", {}) or {}

        for raw_key, raw_value in raw_id2label.items():
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
    hf_loaded = load_hf_model_artifacts(force_reload=force_reload)
    sklearn_loaded = load_sklearn_model_artifacts(force_reload=force_reload)
    return hf_loaded or sklearn_loaded


def is_sklearn_model_ready() -> bool:
    return _sklearn_vectorizer is not None and _sklearn_model is not None


def is_hf_model_ready() -> bool:
    return _hf_tokenizer is not None and _hf_model is not None and _hf_torch is not None


def is_model_ready() -> bool:
    return is_hf_model_ready() or is_sklearn_model_ready()


def _build_prediction_result(
    label: str | None,
    confidence: float,
    backend: str,
    model_version: str,
    is_ready: bool,
) -> dict[str, Any]:
    return {
        "label": label,
        "confidence": round(float(confidence or 0.0), 4),
        "backend": backend,
        "model_version": model_version,
        "is_ready": is_ready,
    }


def _predict_with_sklearn(text: str) -> dict[str, Any]:
    cleaned_text = str(text or "").strip()
    if not cleaned_text:
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="sklearn",
            model_version=SYMPTOM_MODEL_VERSION,
            is_ready=is_sklearn_model_ready(),
        )

    if not is_sklearn_model_ready():
        load_sklearn_model_artifacts()

    if not is_sklearn_model_ready():
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="sklearn",
            model_version=SYMPTOM_MODEL_VERSION,
            is_ready=False,
        )

    try:
        transformed = _sklearn_vectorizer.transform([cleaned_text])

        if hasattr(_sklearn_model, "predict_proba"):
            probabilities = _sklearn_model.predict_proba(transformed)[0]
            best_index = int(probabilities.argmax())
            best_label = str(_sklearn_model.classes_[best_index])
            best_score = float(probabilities[best_index])

            return _build_prediction_result(
                label=best_label,
                confidence=best_score,
                backend="sklearn",
                model_version=SYMPTOM_MODEL_VERSION,
                is_ready=True,
            )

        predicted = _sklearn_model.predict(transformed)[0]
        return _build_prediction_result(
            label=str(predicted),
            confidence=0.0,
            backend="sklearn",
            model_version=SYMPTOM_MODEL_VERSION,
            is_ready=True,
        )

    except Exception as error:
        logger.warning("[MODEL] sklearn prediction failed: %s", error)
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="sklearn",
            model_version=SYMPTOM_MODEL_VERSION,
            is_ready=True,
        )


def _predict_with_hf(text: str) -> dict[str, Any]:
    cleaned_text = str(text or "").strip()
    hf_metadata = _get_hf_metadata()
    hf_model_version = str(hf_metadata.get("model_version") or HF_CLASSIFIER_MODEL_VERSION)

    if not cleaned_text:
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="hf",
            model_version=hf_model_version,
            is_ready=is_hf_model_ready(),
        )

    if not is_hf_model_ready():
        load_hf_model_artifacts()

    if not is_hf_model_ready():
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="hf",
            model_version=hf_model_version,
            is_ready=False,
        )

    try:
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

        return _build_prediction_result(
            label=best_label,
            confidence=best_score,
            backend="hf",
            model_version=hf_model_version,
            is_ready=True,
        )

    except Exception as error:
        logger.warning("[MODEL] hf prediction failed: %s", error)
        return _build_prediction_result(
            label=None,
            confidence=0.0,
            backend="hf",
            model_version=hf_model_version,
            is_ready=True,
        )


def predict_result(text: str) -> dict[str, Any]:
    preferred_backend = str(PREFERRED_CLASSIFIER_BACKEND or "").strip().lower()

    backend_order = ["hf", "sklearn"] if preferred_backend == "hf" else ["sklearn", "hf"]

    for backend_name in backend_order:
        if backend_name == "hf":
            result = _predict_with_hf(text)
        else:
            result = _predict_with_sklearn(text)

        if result.get("label"):
            return result

    fallback_backend = backend_order[0]
    if fallback_backend == "hf":
        return _predict_with_hf(text)
    return _predict_with_sklearn(text)


def predict(text: str) -> str:
    result = predict_result(text)
    return str(result.get("label") or "")


def predict_with_confidence(text: str) -> tuple[str | None, float]:
    result = predict_result(text)
    return result.get("label"), float(result.get("confidence", 0.0) or 0.0)


def get_model_status() -> dict[str, Any]:
    hf_metadata = _get_hf_metadata()

    active_backend = "none"
    active_model_version = ""

    if PREFERRED_CLASSIFIER_BACKEND == "hf" and is_hf_model_ready():
        active_backend = "hf"
        active_model_version = str(hf_metadata.get("model_version") or HF_CLASSIFIER_MODEL_VERSION)
    elif PREFERRED_CLASSIFIER_BACKEND == "sklearn" and is_sklearn_model_ready():
        active_backend = "sklearn"
        active_model_version = SYMPTOM_MODEL_VERSION
    elif is_hf_model_ready():
        active_backend = "hf"
        active_model_version = str(hf_metadata.get("model_version") or HF_CLASSIFIER_MODEL_VERSION)
    elif is_sklearn_model_ready():
        active_backend = "sklearn"
        active_model_version = SYMPTOM_MODEL_VERSION

    return {
        "is_ready": is_model_ready(),
        "active_backend": active_backend,
        "active_model_version": active_model_version,
        "preferred_backend": PREFERRED_CLASSIFIER_BACKEND,
        "sklearn": {
            "is_ready": is_sklearn_model_ready(),
            "load_attempted": _sklearn_load_attempted,
            "vectorizer_path": SYMPTOM_VECTORIZER_ARTIFACT_PATH,
            "model_path": SYMPTOM_MODEL_ARTIFACT_PATH,
            "model_version": SYMPTOM_MODEL_VERSION,
        },
        "hf": {
            "is_ready": is_hf_model_ready(),
            "load_attempted": _hf_load_attempted,
            "artifact_dir": HF_CLASSIFIER_ARTIFACT_DIR,
            "metadata_path": HF_CLASSIFIER_METADATA_PATH,
            "metadata": hf_metadata,
            "model_version": str(hf_metadata.get("model_version") or HF_CLASSIFIER_MODEL_VERSION),
        },
    }