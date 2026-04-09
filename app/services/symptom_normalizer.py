# app/services/symptom_normalizer.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from functools import lru_cache  # prototype embedding 캐시

import numpy as np  # 임베딩 유사도 계산

from app.core.symptom_rules import ENGLISH_HEAD_TRAUMA_PATTERNS  # 영어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_HEAD_TRAUMA_PATTERNS  # 한국어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_RULES  # 한국어 일반 증상 룰
from app.core.symptom_rules import MAX_NORMALIZED_SYMPTOMS  # 복합 증상 최대 개수
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 복합 증상 구분자
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


@lru_cache(maxsize=1)
def _get_english_variant_mapping() -> dict[str, str]:
    mapping: dict[str, str] = {}

    for canonical, variants in SYMPTOM_RULES.items():
        mapping[canonical] = canonical

        for variant in variants:
            cleaned_variant = str(variant).strip().lower()
            if cleaned_variant:
                mapping[cleaned_variant] = canonical

    return mapping


def warmup_normalizer() -> None:
    _ = get_symptom_prototype_embeddings()
    _ = _get_english_variant_mapping()


def _collect_matches_from_mapping(
    text: str,
    mapping: dict[str, str],
) -> list[tuple[int, str]]:
    cleaned_text = (text or "").strip().lower()
    if not cleaned_text:
        return []

    matches: list[tuple[int, str]] = []

    for keyword, canonical in mapping.items():
        keyword_index = cleaned_text.find(str(keyword).strip().lower())
        if keyword_index >= 0:
            matches.append((keyword_index, canonical))

    return matches


def _deduplicate_ordered_canonicals(
    matches: list[tuple[int, str]],
) -> list[str]:
    ordered_matches = sorted(matches, key=lambda item: item[0])
    unique_canonicals: list[str] = []
    seen_canonicals: set[str] = set()

    for _, canonical in ordered_matches:
        if canonical in seen_canonicals:
            continue

        seen_canonicals.add(canonical)
        unique_canonicals.append(canonical)

        if len(unique_canonicals) >= MAX_NORMALIZED_SYMPTOMS:
            break

    return unique_canonicals


def _join_canonical_symptoms(canonicals: list[str]) -> str:
    return NORMALIZED_QUERY_SEPARATOR.join(canonicals)


def _build_rule_result(
    canonicals: list[str],
    single_method: str,
    multi_method: str,
) -> tuple[str, str, float] | None:
    if not canonicals:
        return None

    if len(canonicals) == 1:
        return canonicals[0], single_method, 1.0

    return _join_canonical_symptoms(canonicals), multi_method, 1.0


def _match_korean_rules(original_query: str) -> tuple[str, str, float] | None:
    korean_matches = _collect_matches_from_mapping(
        original_query,
        KOREAN_RULES,
    )
    trauma_matches = _collect_matches_from_mapping(
        original_query,
        KOREAN_HEAD_TRAUMA_PATTERNS,
    )

    canonicals = _deduplicate_ordered_canonicals(
        korean_matches + trauma_matches,
    )
    return _build_rule_result(
        canonicals=canonicals,
        single_method="rule_ko",
        multi_method="rule_ko_multi",
    )


def _match_english_rules(internal_query: str) -> tuple[str, str, float] | None:
    english_matches = _collect_matches_from_mapping(
        internal_query,
        _get_english_variant_mapping(),
    )
    trauma_matches = _collect_matches_from_mapping(
        internal_query,
        ENGLISH_HEAD_TRAUMA_PATTERNS,
    )

    canonicals = _deduplicate_ordered_canonicals(
        english_matches + trauma_matches,
    )
    return _build_rule_result(
        canonicals=canonicals,
        single_method="rule_en",
        multi_method="rule_en_multi",
    )


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

        query_text = (internal_query or original_query).strip().lower()
        if not query_text:
            return None

        query_embedding = model.encode(
            [query_text],
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


def _build_fallback_result(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float]:
    fallback_source = (internal_query or original_query).strip().lower()
    if not fallback_source:
        return "", "empty_input", 0.0

    tokens = fallback_source.split()
    if tokens:
        return " ".join(tokens[:2]), "fallback_tokens", 0.0

    return fallback_source, "fallback_raw", 0.0


def normalize_symptom_query(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float]:
    """
    하이브리드 정규화
    1) 원문 기준 한국어/외상 룰
    2) 번역문 기준 영어/외상 룰
    3) ML classifier 기반 정규화
    4) semantic 정규화
    5) fallback

    복합 증상은 단일 canonical symptom으로 덮어쓰지 않고
    "fever | cough" 같은 구조로 반환한다.
    """
    original = (original_query or "").strip()
    internal = (internal_query or "").strip().lower()

    if not original and not internal:
        return "", "empty_input", 0.0

    korean_rule_result = _match_korean_rules(original)
    if korean_rule_result:
        return korean_rule_result

    english_rule_result = _match_english_rules(internal)
    if english_rule_result:
        return english_rule_result

    ml_result = _match_ml_rule(internal)
    if ml_result:
        return ml_result

    semantic_result = _match_semantic_rule(original, internal)
    if semantic_result:
        return semantic_result

    return _build_fallback_result(original, internal)