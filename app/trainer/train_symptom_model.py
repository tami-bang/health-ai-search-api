# trainer/train_symptom_model.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록

from app.core.logging_config import configure_logging  # 공통 로그 초기화
from app.core.settings import SYMPTOM_MODEL_VERSION  # 모델 버전 정보
from app.core.settings import TRAINING_DATASET_NAME  # 데이터셋 이름
from app.core.settings import TRAINING_DATASET_VERSION  # 데이터셋 버전 정보
from app.trainer.artifact_writer import save_model_artifacts  # 학습 결과 저장
from app.trainer.artifact_writer import save_training_metadata  # 메타데이터 저장
from app.trainer.dataset_loader import build_dataset_fingerprint  # 데이터 fingerprint 생성
from app.trainer.dataset_loader import build_training_texts_and_labels  # 학습 데이터 준비
from app.trainer.dataset_loader import load_training_rows  # 원본 처리행 조회
from app.trainer.model_pipeline import evaluate_model  # 검증 성능 평가
from app.trainer.model_pipeline import split_training_data  # 학습/검증 데이터 분리
from app.trainer.model_pipeline import train_vectorizer_and_model  # 벡터라이저/분류기 학습

configure_logging()
logger = logging.getLogger(__name__)


def _validate_training_inputs(
    texts: list[str],
    labels: list[str],
) -> None:
    if not texts or not labels:
        raise RuntimeError("학습 데이터가 비어 있습니다.")

    if len(texts) != len(labels):
        raise RuntimeError("학습 텍스트와 라벨 개수가 맞지 않습니다.")


def _build_training_metadata(
    train_texts: list[str],
    valid_texts: list[str],
    labels: list[str],
    evaluation_summary: dict,
    artifact_paths: dict[str, str],
    dataset_fingerprint: str,
) -> dict:
    unique_labels = sorted({str(label) for label in labels})

    return {
        "model_version": SYMPTOM_MODEL_VERSION,
        "dataset_name": TRAINING_DATASET_NAME,
        "dataset_version": TRAINING_DATASET_VERSION,
        "dataset_fingerprint": dataset_fingerprint,
        "train_size": len(train_texts),
        "validation_size": len(valid_texts),
        "total_size": len(labels),
        "unique_label_count": len(unique_labels),
        "unique_labels_preview": unique_labels[:30],
        "evaluation": evaluation_summary,
        "artifacts": artifact_paths,
    }


def main() -> None:
    logger.info("[TRAIN] start symptom artifact generation")

    processed_rows = load_training_rows()
    dataset_fingerprint = build_dataset_fingerprint(processed_rows)

    texts, labels = build_training_texts_and_labels()
    _validate_training_inputs(texts, labels)

    train_texts, valid_texts, train_labels, valid_labels = split_training_data(
        texts=texts,
        labels=labels,
    )

    vectorizer, classifier = train_vectorizer_and_model(
        train_texts=train_texts,
        train_labels=train_labels,
    )

    evaluation_summary = evaluate_model(
        vectorizer=vectorizer,
        classifier=classifier,
        valid_texts=valid_texts,
        valid_labels=valid_labels,
    )

    artifact_paths = save_model_artifacts(
        vectorizer=vectorizer,
        classifier=classifier,
    )

    metadata = _build_training_metadata(
        train_texts=train_texts,
        valid_texts=valid_texts,
        labels=labels,
        evaluation_summary=evaluation_summary,
        artifact_paths=artifact_paths,
        dataset_fingerprint=dataset_fingerprint,
    )
    metadata_path = save_training_metadata(metadata)

    logger.info("[TRAIN] finished model_version=%s metadata=%s", SYMPTOM_MODEL_VERSION, metadata_path)


if __name__ == "__main__":
    main()