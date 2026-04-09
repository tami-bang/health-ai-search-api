# trainer/model_pipeline.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록

from sklearn.feature_extraction.text import TfidfVectorizer  # 텍스트 벡터화
from sklearn.linear_model import LogisticRegression  # 텍스트 분류 모델
from sklearn.model_selection import train_test_split  # 학습/검증 분리

from app.core.settings import TRAINING_RANDOM_STATE  # 학습 고정 seed
from app.trainer.evaluator import build_evaluation_summary  # 평가 결과 생성

logger = logging.getLogger(__name__)

TEST_SIZE = 0.2
MAX_FEATURES = 20000
NGRAM_RANGE = (1, 2)
MAX_ITER = 1000


def build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        ngram_range=NGRAM_RANGE,
        min_df=1,
        max_features=MAX_FEATURES,
    )


def build_classifier() -> LogisticRegression:
    return LogisticRegression(
        max_iter=MAX_ITER,
        random_state=TRAINING_RANDOM_STATE,
    )


def split_training_data(
    texts: list[str],
    labels: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    return train_test_split(
        texts,
        labels,
        test_size=TEST_SIZE,
        random_state=TRAINING_RANDOM_STATE,
        stratify=labels,
    )


def train_vectorizer_and_model(
    train_texts: list[str],
    train_labels: list[str],
) -> tuple[TfidfVectorizer, LogisticRegression]:
    vectorizer = build_vectorizer()
    classifier = build_classifier()

    train_matrix = vectorizer.fit_transform(train_texts)
    classifier.fit(train_matrix, train_labels)

    logger.info("[TRAIN] vectorizer/model training complete")
    return vectorizer, classifier


def evaluate_model(
    vectorizer: TfidfVectorizer,
    classifier: LogisticRegression,
    valid_texts: list[str],
    valid_labels: list[str],
) -> dict:
    valid_matrix = vectorizer.transform(valid_texts)
    predicted_labels = classifier.predict(valid_matrix)

    summary = build_evaluation_summary(
        valid_labels=valid_labels,
        predicted_labels=[str(item) for item in predicted_labels],
        class_labels=[str(item) for item in classifier.classes_],
    )

    logger.info(
        "[TRAIN] evaluation accuracy=%.4f macro_f1=%.4f weighted_f1=%.4f",
        summary["accuracy"],
        summary["macro_f1"],
        summary["weighted_f1"],
    )
    return summary