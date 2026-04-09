# trainer/hf_train_symptom_classifier.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import json  # 메타데이터 저장
import logging  # 실행 로그 기록
from datetime import datetime  # 저장 시각 기록
from pathlib import Path  # 파일 경로 처리
from typing import Any  # 타입 힌트 보조

import numpy as np  # metric 계산 보조
from sklearn.metrics import accuracy_score  # 정확도 계산
from sklearn.metrics import f1_score  # F1 점수 계산

from app.core.logging_config import configure_logging  # 공통 로그 초기화
from app.core.settings import ARTIFACTS_DIR  # 아티팩트 루트 경로
from app.core.settings import HF_CLASSIFIER_ARTIFACT_DIR  # HF 분류기 저장 경로
from app.core.settings import HF_CLASSIFIER_BASE_MODEL_NAME  # 학습 시작 base model
from app.core.settings import HF_CLASSIFIER_BATCH_SIZE  # 배치 크기
from app.core.settings import HF_CLASSIFIER_LEARNING_RATE  # 러닝레이트
from app.core.settings import HF_CLASSIFIER_MAX_LENGTH  # 토큰 길이 제한
from app.core.settings import HF_CLASSIFIER_METADATA_PATH  # HF 메타데이터 저장 경로
from app.core.settings import HF_CLASSIFIER_MODEL_VERSION  # HF 모델 버전
from app.core.settings import HF_CLASSIFIER_NUM_EPOCHS  # 학습 epoch 수
from app.core.settings import TRAINING_DATASET_NAME  # 데이터셋 이름
from app.core.settings import TRAINING_DATASET_VERSION  # 데이터셋 버전
from app.core.settings import TRAINING_RANDOM_STATE  # 랜덤 시드
from app.trainer.dataset_loader import build_dataset_fingerprint  # 데이터 fingerprint 생성
from app.trainer.hf_dataset_builder import build_hf_dataset  # HF dataset 구성

configure_logging()
logger = logging.getLogger(__name__)


def _ensure_artifact_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    Path(HF_CLASSIFIER_ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)


def _tokenize_dataset(dataset, tokenizer):
    def tokenize_batch(batch: dict[str, list[str]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=HF_CLASSIFIER_MAX_LENGTH,
        )

    return dataset.map(tokenize_batch, batched=True)


def _build_compute_metrics():
    def compute_metrics(eval_prediction) -> dict[str, float]:
        logits, labels = eval_prediction
        predictions = np.argmax(logits, axis=-1)

        accuracy = float(accuracy_score(labels, predictions))
        macro_f1 = float(f1_score(labels, predictions, average="macro", zero_division=0))
        weighted_f1 = float(f1_score(labels, predictions, average="weighted", zero_division=0))

        return {
            "accuracy": round(accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
        }

    return compute_metrics


def _save_metadata(
    metrics: dict[str, Any],
    id_to_label: dict[int, str],
    dataset_fingerprint: str,
    train_size: int,
    eval_size: int,
) -> str:
    metadata = {
        "model_version": HF_CLASSIFIER_MODEL_VERSION,
        "base_model_name": HF_CLASSIFIER_BASE_MODEL_NAME,
        "dataset_name": TRAINING_DATASET_NAME,
        "dataset_version": TRAINING_DATASET_VERSION,
        "dataset_fingerprint": dataset_fingerprint,
        "artifact_dir": HF_CLASSIFIER_ARTIFACT_DIR,
        "train_size": train_size,
        "eval_size": eval_size,
        "label_count": len(id_to_label),
        "labels": [id_to_label[index] for index in sorted(id_to_label.keys())],
        "metrics": metrics,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    metadata_path = Path(HF_CLASSIFIER_METADATA_PATH)
    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    return str(metadata_path)


def main() -> None:
    import torch  # GPU 사용 확인
    from transformers import AutoModelForSequenceClassification  # HF 분류 모델 로드
    from transformers import AutoTokenizer  # HF 토크나이저 로드
    from transformers import DataCollatorWithPadding  # 배치 패딩 처리
    from transformers import Trainer  # 학습 실행
    from transformers import TrainingArguments  # 학습 파라미터 정의

    _ensure_artifact_dir()

    dataset, label_to_id, id_to_label, source_rows = build_hf_dataset()
    dataset_fingerprint = build_dataset_fingerprint(source_rows)

    split_dataset = dataset.train_test_split(
        test_size=0.2,
        seed=TRAINING_RANDOM_STATE,
    )
    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]

    tokenizer = AutoTokenizer.from_pretrained(HF_CLASSIFIER_BASE_MODEL_NAME)
    tokenized_train_dataset = _tokenize_dataset(train_dataset, tokenizer)
    tokenized_eval_dataset = _tokenize_dataset(eval_dataset, tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        HF_CLASSIFIER_BASE_MODEL_NAME,
        num_labels=len(label_to_id),
        id2label=id_to_label,
        label2id=label_to_id,
    )

    training_args = TrainingArguments(
        output_dir=HF_CLASSIFIER_ARTIFACT_DIR,
        num_train_epochs=HF_CLASSIFIER_NUM_EPOCHS,
        per_device_train_batch_size=HF_CLASSIFIER_BATCH_SIZE,
        per_device_eval_batch_size=HF_CLASSIFIER_BATCH_SIZE,
        learning_rate=HF_CLASSIFIER_LEARNING_RATE,
        seed=TRAINING_RANDOM_STATE,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_eval_dataset,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=_build_compute_metrics(),
    )

    logger.info(
        "[HF-TRAIN] start base_model=%s device=%s train_size=%s eval_size=%s",
        HF_CLASSIFIER_BASE_MODEL_NAME,
        "cuda" if torch.cuda.is_available() else "cpu",
        len(train_dataset),
        len(eval_dataset),
    )

    trainer.train()
    evaluation_metrics = trainer.evaluate()

    trainer.save_model(HF_CLASSIFIER_ARTIFACT_DIR)
    tokenizer.save_pretrained(HF_CLASSIFIER_ARTIFACT_DIR)

    metadata_path = _save_metadata(
        metrics=evaluation_metrics,
        id_to_label=id_to_label,
        dataset_fingerprint=dataset_fingerprint,
        train_size=len(train_dataset),
        eval_size=len(eval_dataset),
    )

    logger.info(
        "[HF-TRAIN] finished model_version=%s metadata=%s",
        HF_CLASSIFIER_MODEL_VERSION,
        metadata_path,
    )


if __name__ == "__main__":
    main()