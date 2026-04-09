# trainer/preprocessor.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import re  # 텍스트 정규화
from collections import OrderedDict  # 중복 제거 순서 유지


def normalize_training_text(text: str) -> str:
    cleaned = str(text or "").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def normalize_training_label(label: str) -> str:
    return str(label or "").strip().lower()


def filter_valid_training_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    valid_rows: list[dict[str, str]] = []

    for row in rows:
        input_text = normalize_training_text(row.get("input_text", ""))
        label_text = normalize_training_label(row.get("label_text", ""))

        if not input_text or not label_text:
            continue

        valid_rows.append({
            "input_text": input_text,
            "label_text": label_text,
        })

    return valid_rows


def deduplicate_training_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduplicated: OrderedDict[tuple[str, str], dict[str, str]] = OrderedDict()

    for row in rows:
        input_text = normalize_training_text(row.get("input_text", ""))
        label_text = normalize_training_label(row.get("label_text", ""))

        if not input_text or not label_text:
            continue

        dedupe_key = (input_text, label_text)
        if dedupe_key not in deduplicated:
            deduplicated[dedupe_key] = {
                "input_text": input_text,
                "label_text": label_text,
            }

    return list(deduplicated.values())


def preprocess_training_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered_rows = filter_valid_training_rows(rows)
    deduplicated_rows = deduplicate_training_rows(filtered_rows)
    return deduplicated_rows