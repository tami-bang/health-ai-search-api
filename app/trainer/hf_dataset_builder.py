# trainer/hf_dataset_builder.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # 타입 힌트 보조

from datasets import Dataset  # HF Dataset 생성

from app.trainer.dataset_loader import load_training_rows  # 전처리된 학습 데이터 로드


def build_label_maps(rows: list[dict[str, str]]) -> tuple[dict[str, int], dict[int, str]]:
    unique_labels = sorted({str(row["label_text"]) for row in rows})
    label_to_id = {
        label: index
        for index, label in enumerate(unique_labels)
    }
    id_to_label = {
        index: label
        for label, index in label_to_id.items()
    }
    return label_to_id, id_to_label


def build_hf_dataset() -> tuple[Dataset, dict[str, int], dict[int, str], list[dict[str, str]]]:
    rows = load_training_rows()
    label_to_id, id_to_label = build_label_maps(rows)

    dataset_rows: list[dict[str, Any]] = []
    for row in rows:
        dataset_rows.append({
            "text": row["input_text"],
            "label": label_to_id[row["label_text"]],
        })

    dataset = Dataset.from_list(dataset_rows)
    return dataset, label_to_id, id_to_label, rows