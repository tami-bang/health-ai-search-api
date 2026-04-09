# trainer/dataset_loader.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from typing import Any  # 타입 힌트 보조

from datasets import load_dataset  # Hugging Face 데이터셋 로드


logger = logging.getLogger(__name__)

DATASET_NAME = "gretelai/symptom_to_diagnosis"
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
    dataset = load_dataset(DATASET_NAME)
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

    logger.info("[TRAIN] loaded rows: %s", len(rows))
    return rows


def build_training_texts_and_labels() -> tuple[list[str], list[str]]:
    rows = load_training_rows()

    texts = [row["input_text"] for row in rows]
    labels = [row["label_text"] for row in rows]

    return texts, labels