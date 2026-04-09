# app/services/symptom_normalizer.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from functools import lru_cache  # prototype embedding 캐시

import numpy as np  # 임베딩 유사도 계산

from app.core.symptom_rules import ENGLISH_HEAD_TRAUMA_PATTERNS  # 영어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_HEAD_TRAUMA_PATTERNS  # 한국어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_RULES  # 한국어 일반 증상 룰
from app.core.symptom_rules import NORMALIZER_ML_CONFIDENCE_THRESHOLD  # ML 정규화 임계값
from app.core.symptom_rules import NORMALIZER_SEMANTIC_THRESHOLD  # semantic 정규화 임계값
from app.core.symptom_rules import SYMPTOM_RULES  # canonical symptom 룰 테이블
from app.services.ai_ranker import get_embedding_model  # 공용 임베딩 모델 재사용
from app.services.model_loader import predict_with_confidence  # 학습 모델 예측 사용

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_symptom_prototype_embeddings() -> tuple[list[str], np.ndarray]:
    """
    정규화용 prototype embedding 생성
    - 룰 테이블을 임베딩으로도 재사용하도록 분리
    - 룰과 semantic 기준이 같은 데이터를 보게 하려는 목적
    """
    texts: list[str] = []
    labels: list[str] = []

    for canonical, variants in SYMPTOM_RULES.items():
        texts.append(canonical)
        labels.append(canonical)

        for variant in variants:
            texts.append(variant)
            labels.append(canonical)

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return labels, embeddings


def warmup_normalizer() -> None:
    _ = get_symptom_prototype_embeddings()


def _match_korean_head_trauma_rule(original_query: str) -> tuple[str, str, float] | None:
    for keyword, canonical in KOREAN_HEAD_TRAUMA_PATTERNS.items():
        if keyword in original_query:
            return canonical, "rule_ko_head_trauma", 1.0
    return None


def _match_korean_symptom_rule(original_query: str) -> tuple[str, str, float] | None:
    for keyword, canonical in KOREAN_RULES.items():
        if keyword in original_query:
            return canonical, "rule_ko", 1.0
    return None


def _match_english_head_trauma_rule(internal_query: str) -> tuple[str, str, float] | None:
    for keyword, canonical in ENGLISH_HEAD_TRAUMA_PATTERNS.items():
        if keyword in internal_query:
            return canonical, "rule_en_head_trauma", 1.0
    return None


def _match_english_symptom_rule(internal_query: str) -> tuple[str, str, float] | None:
    for canonical, variants in SYMPTOM_RULES.items():
        if canonical in internal_query:
            return canonical, "rule_en_canonical", 1.0

        for variant in variants:
            if variant in internal_query:
                return canonical, "rule_en_variant", 1.0

    return None


def _match_ml_rule(internal_query: str) -> tuple[str, str, float] | None:
    cleaned_query = (internal_query or "").strip().lower()
    if not cleaned_query:
        return None

    predicted_label, confidence = predict_with_confidence(cleaned_query)
    if not predicted_label:
        return None

    if confidence < NORMALIZER_ML_CONFIDENCE_THRESHOLD:
        return None

    return predicted_label, "ml_classifier", round(confidence, 4)


def _match_semantic_rule(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float] | None:
    try:
        labels, prototype_embeddings = get_symptom_prototype_embeddings()
        model = get_embedding_model()

        query_embedding = model.encode(
            [internal_query or original_query.lower()],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        scores = np.dot(prototype_embeddings, query_embedding)
        best_index = int(np.argmax(scores))
        best_label = labels[best_index]
        best_score = float(scores[best_index])

        if best_score >= NORMALIZER_SEMANTIC_THRESHOLD:
            return best_label, "semantic", round(best_score, 4)

    except Exception as error:
        logger.warning("[NORMALIZER] semantic normalize skipped: %s", error)

    return None


def _build_fallback_result(original_query: str, internal_query: str) -> tuple[str, str, float]:
    tokens = (internal_query or original_query.lower()).split()
    if tokens:
        return " ".join(tokens[:2]), "fallback_tokens", 0.0

    return internal_query or original_query.lower(), "fallback_raw", 0.0


def normalize_symptom_query(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float]:
    """
    하이브리드 정규화
    1) 원문 기준 외상성 머리 충격 룰
    2) 원문 기준 한국어 일반 증상 룰
    3) 번역문 기준 영어 외상성 머리 충격 룰
    4) 번역문 기준 영어 일반 증상 룰
    5) ML classifier 기반 정규화
    6) semantic 정규화
    7) fallback
    """
    original = (original_query or "").strip()
    internal = (internal_query or "").strip().lower()

    if not original and not internal:
        return "", "empty_input", 0.0

    rule_result = _match_korean_head_trauma_rule(original)
    if rule_result:
        return rule_result

    rule_result = _match_korean_symptom_rule(original)
    if rule_result:
        return rule_result

    rule_result = _match_english_head_trauma_rule(internal)
    if rule_result:
        return rule_result

    rule_result = _match_english_symptom_rule(internal)
    if rule_result:
        return rule_result

    ml_result = _match_ml_rule(internal)
    if ml_result:
        return ml_result

    semantic_result = _match_semantic_rule(original, internal)
    if semantic_result:
        return semantic_result

    return _build_fallback_result(original, internal)