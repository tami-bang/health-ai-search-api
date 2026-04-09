# trainer/evaluator.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from typing import Any  # 타입 힌트 보조

from sklearn.metrics import accuracy_score  # 정확도 계산
from sklearn.metrics import classification_report  # 분류 성능 리포트
from sklearn.metrics import f1_score  # F1 점수 계산


def build_evaluation_summary(
    valid_labels: list[str],
    predicted_labels: list[str],
    class_labels: list[str],
) -> dict[str, Any]:
    accuracy = float(accuracy_score(valid_labels, predicted_labels))
    macro_f1 = float(f1_score(valid_labels, predicted_labels, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(valid_labels, predicted_labels, average="weighted", zero_division=0))

    report = classification_report(
        valid_labels,
        predicted_labels,
        output_dict=True,
        zero_division=0,
    )

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "sample_count": len(valid_labels),
        "label_count": len(class_labels),
        "classes": [str(item) for item in class_labels],
        "macro_avg": report.get("macro avg", {}),
        "weighted_avg": report.get("weighted avg", {}),
    }