# app/services/symptom_normalizer.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import logging  # 용도: 실행 로그 기록
import re  # 용도: 지속 시간/불필요 표현 정리
from functools import lru_cache  # 용도: prototype embedding 캐시

import numpy as np  # 용도: 임베딩 유사도 계산

from app.core.symptom_rules import ENGLISH_HEAD_TRAUMA_PATTERNS  # 용도: 영어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_HEAD_TRAUMA_PATTERNS  # 용도: 한국어 외상성 머리 충격 패턴
from app.core.symptom_rules import KOREAN_RULES  # 용도: 한국어 일반 증상 룰
from app.core.symptom_rules import MAX_NORMALIZED_SYMPTOMS  # 용도: 복합 증상 최대 개수
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 용도: 복합 증상 구분자
from app.core.symptom_rules import NORMALIZER_ML_CONFIDENCE_THRESHOLD  # 용도: ML 정규화 임계값
from app.core.symptom_rules import NORMALIZER_SEMANTIC_THRESHOLD  # 용도: semantic 정규화 임계값
from app.core.symptom_rules import SYMPTOM_RULES  # 용도: canonical symptom 룰 테이블
from app.services.ai_ranker import get_embedding_model  # 용도: 공용 임베딩 모델 재사용
from app.services.model_loader import predict_with_confidence  # 용도: 학습 모델 예측 사용

logger = logging.getLogger(__name__)

FORCE_SYMPTOM_RULES: dict[str, str] = {
    "비출혈": "nosebleed",
    "epistaxis": "nosebleed",
}  # 용도: 모호도 낮은 직접 의학 용어만 강제 매핑

DURATION_NOISE_PATTERNS: tuple[str, ...] = (
    r"\b\d+\s*분째\b",
    r"\b\d+\s*시간째\b",
    r"\b\d+\s*일째\b",
    r"\b\d+\s*주째\b",
    r"\b\d+\s*개월째\b",
    r"삼십분째",
    r"30분째",
    r"한시간째",
    r"두시간째",
)  # 용도: 증상명과 분리해서 봐야 하는 지속 시간 표현 제거

NON_SYMPTOM_NOISE_PATTERNS: tuple[str, ...] = (
    r"안\s*멈춰(?:요|요\.)?",
    r"멈추지\s*않(?:아요|아요\.)?",
    r"멈추질\s*않(?:아요|아요\.)?",
    r"안\s*그쳐(?:요|요\.)?",
    r"상태에요",
    r"상태예요",
)  # 용도: 검색 질의를 오염시키는 서술 표현 제거


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _remove_noise_patterns(text: str) -> str:
    cleaned_text = _normalize_text(text)

    for pattern in DURATION_NOISE_PATTERNS:
        cleaned_text = re.sub(pattern, " ", cleaned_text, flags=re.IGNORECASE)

    for pattern in NON_SYMPTOM_NOISE_PATTERNS:
        cleaned_text = re.sub(pattern, " ", cleaned_text, flags=re.IGNORECASE)

    return _normalize_text(cleaned_text)


def _resolve_forced_symptom(text: str) -> str | None:
    cleaned_text = _normalize_text(text)
    if not cleaned_text:
        return None

    for keyword, canonical in FORCE_SYMPTOM_RULES.items():
        if keyword in cleaned_text:
            return canonical

    return None


@lru_cache(maxsize=1)
def get_symptom_prototype_embeddings() -> tuple[list[str], np.ndarray]:
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
            cleaned_variant = _normalize_text(str(variant))
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
    cleaned_text = _normalize_text(text)
    if not cleaned_text:
        return []

    matches: list[tuple[int, str]] = []

    for keyword, canonical in mapping.items():
        cleaned_keyword = _normalize_text(str(keyword))
        keyword_index = cleaned_text.find(cleaned_keyword)
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


def _build_forced_result(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float] | None:
    forced_symptom = _resolve_forced_symptom(
        " ".join([
            _normalize_text(original_query),
            _normalize_text(internal_query),
        ])
    )
    if not forced_symptom:
        return None

    logger.info(
        "[NORMALIZER] forced symptom matched original=%s internal=%s canonical=%s",
        original_query,
        internal_query,
        forced_symptom,
    )
    return forced_symptom, "force_rule", 1.0


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
    cleaned_query = _normalize_text(internal_query)
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

        query_text = _normalize_text(internal_query or original_query)
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
    fallback_source = _remove_noise_patterns(internal_query or original_query)
    if not fallback_source:
        return "", "empty_input", 0.0

    forced_symptom = _resolve_forced_symptom(fallback_source)
    if forced_symptom:
        return forced_symptom, "force_rule_fallback", 1.0

    tokens = fallback_source.split()
    if tokens:
        return " ".join(tokens[:2]), "fallback_tokens", 0.0

    return fallback_source, "fallback_raw", 0.0


def _match_cleaned_rules(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float] | None:
    cleaned_original = _remove_noise_patterns(original_query)
    cleaned_internal = _remove_noise_patterns(internal_query)

    korean_rule_result = _match_korean_rules(cleaned_original)
    if korean_rule_result:
        return cleaned_original and korean_rule_result

    english_rule_result = _match_english_rules(cleaned_internal)
    if english_rule_result:
        return cleaned_internal and english_rule_result

    return None


def normalize_symptom_query(
    original_query: str,
    internal_query: str,
) -> tuple[str, str, float]:
    """
    하이브리드 정규화
    1) 직접 의학 용어 강제 매핑
    2) 원문 기준 한국어/외상 룰
    3) 번역문 기준 영어/외상 룰
    4) noise 제거 후 룰 재평가
    5) ML classifier 기반 정규화
    6) semantic 정규화
    7) fallback

    핵심 전략:
    - 특정 문장을 통째로 하드코딩하지 않고 canonical symptom 사전을 넓혀 대응한다.
    - 지속 시간/상태 표현은 제거한 뒤 룰을 한 번 더 평가해 유동성을 높인다.
    """
    original = _normalize_text(original_query)
    internal = _normalize_text(internal_query)

    if not original and not internal:
        return "", "empty_input", 0.0

    forced_result = _build_forced_result(
        original_query=original,
        internal_query=internal,
    )
    if forced_result:
        return forced_result

    korean_rule_result = _match_korean_rules(original)
    if korean_rule_result:
        return korean_rule_result

    english_rule_result = _match_english_rules(internal)
    if english_rule_result:
        return english_rule_result

    cleaned_rule_result = _match_cleaned_rules(
        original_query=original,
        internal_query=internal,
    )
    if cleaned_rule_result:
        return cleaned_rule_result

    ml_result = _match_ml_rule(internal)
    if ml_result:
        return ml_result

    semantic_result = _match_semantic_rule(original, internal)
    if semantic_result:
        return semantic_result

    return _build_fallback_result(original, internal)