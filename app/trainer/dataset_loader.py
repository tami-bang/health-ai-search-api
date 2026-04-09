# trainer/dataset_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import hashlib  # 데이터 fingerprint 생성
import json  # fingerprint용 직렬화
import logging  # 실행 로그 기록
from typing import Any  # 타입 힌트 보조

from datasets import load_dataset  # Hugging Face 데이터셋 로드

from app.core.settings import TRAINING_DATASET_NAME  # 학습 데이터셋 이름
from app.trainer.preprocessor import preprocess_training_rows  # 학습 전처리 적용

logger = logging.getLogger(__name__)

TRAIN_SPLIT_NAME = "train"
INPUT_COLUMN_NAME = "input_text"
LABEL_COLUMN_NAME = "output_text"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_valid_row(input_text: str, label_text: str) -> bool:
    return bool(input_text and label_text)


def load_training_rows() -> list[dict[str, str]]:
    dataset = load_dataset(TRAINING_DATASET_NAME)
    train_split = dataset[TRAIN_SPLIT_NAME]

    rows: list[dict[str, str]] = []

    for row in train_split:
        input_text = _normalize_text(row.get(INPUT_COLUMN_NAME))
        label_text = _normalize_text(row.get(LABEL_COLUMN_NAME))

        if not _is_valid_row(input_text, label_text):
            continue

        rows.append({
            "input_text": input_text,
            "label_text": label_text,
        })

    processed_rows = preprocess_training_rows(rows)
    logger.info("[TRAIN] loaded raw rows=%s processed rows=%s", len(rows), len(processed_rows))
    return processed_rows


def build_training_texts_and_labels() -> tuple[list[str], list[str]]:
    rows = load_training_rows()

    texts = [row["input_text"] for row in rows]
    labels = [row["label_text"] for row in rows]

    return texts, labels


def build_dataset_fingerprint(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()