# trainer/artifact_writer.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import json  # 메타데이터 JSON 저장
import logging  # 실행 로그 기록
from datetime import datetime  # 생성 시각 기록
from pathlib import Path  # 파일 경로 처리
from typing import Any  # 타입 힌트 보조

import joblib  # sklearn 아티팩트 저장

from app.core.settings import ARTIFACTS_DIR  # 아티팩트 디렉토리 경로
from app.core.settings import SYMPTOM_MODEL_ARTIFACT_PATH  # 분류기 저장 경로
from app.core.settings import SYMPTOM_MODEL_VERSION  # 모델 버전 정보
from app.core.settings import SYMPTOM_VECTORIZER_ARTIFACT_PATH  # 벡터라이저 저장 경로

logger = logging.getLogger(__name__)

SYMPTOM_METADATA_ARTIFACT_PATH = ARTIFACTS_DIR / "symptom_training_metadata.json"


def ensure_artifact_directory() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def save_model_artifacts(
    vectorizer: Any,
    classifier: Any,
) -> dict[str, str]:
    ensure_artifact_directory()

    vectorizer_path = Path(SYMPTOM_VECTORIZER_ARTIFACT_PATH)
    model_path = Path(SYMPTOM_MODEL_ARTIFACT_PATH)

    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(classifier, model_path)

    logger.info("[TRAIN] saved vectorizer: %s", vectorizer_path)
    logger.info("[TRAIN] saved classifier: %s", model_path)

    return {
        "vectorizer_path": str(vectorizer_path),
        "model_path": str(model_path),
    }


def save_training_metadata(metadata: dict[str, Any]) -> str:
    ensure_artifact_directory()

    payload = {
        **metadata,
        "model_version": SYMPTOM_MODEL_VERSION,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    with Path(SYMPTOM_METADATA_ARTIFACT_PATH).open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    logger.info("[TRAIN] saved metadata: %s", SYMPTOM_METADATA_ARTIFACT_PATH)
    return str(SYMPTOM_METADATA_ARTIFACT_PATH)