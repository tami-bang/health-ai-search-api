# question_suggester.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from app.core.settings import QUESTION_SUGGESTION_PER_SYMPTOM_LIMIT  # 증상별 추천 개수 제한
from app.core.settings import QUESTION_SUGGESTION_TOTAL_LIMIT  # 전체 추천 개수 제한
from app.core.symptom_rules import NORMALIZED_QUERY_SEPARATOR  # 복합 증상 구분자


QUESTION_SUGGESTION_MAP: dict[str, dict[str, list[str]]] = {
    "fever": {
        "en": [
            "How long has the fever lasted?",
            "What symptoms should make fever urgent?",
            "How can I manage fever at home?",
        ],
        "ko": [
            "열이 며칠째 지속되면 병원을 가야 하나요?",
            "발열과 함께 있으면 위험한 증상은 무엇인가요?",
            "집에서 열을 관리할 때 주의할 점은 무엇인가요?",
        ],
    },
    "headache": {
        "en": [
            "What warning signs can happen with headache?",
            "When does a headache need urgent care?",
            "What are common causes of headache?",
        ],
        "ko": [
            "두통과 함께 나타나면 위험한 증상은 무엇인가요?",
            "어떤 두통은 빨리 진료를 받아야 하나요?",
            "두통의 흔한 원인은 무엇인가요?",
        ],
    },
    "concussion": {
        "en": [
            "What symptoms can happen after a head injury?",
            "When should someone go to the ER after hitting their head?",
            "What warning signs suggest concussion is getting worse?",
        ],
        "ko": [
            "머리를 부딪힌 뒤 어떤 증상을 주의해야 하나요?",
            "머리 충격 후 언제 응급실에 가야 하나요?",
            "뇌진탕이 의심될 때 악화 신호는 무엇인가요?",
        ],
    },
    "diarrhea": {
        "en": [
            "When is diarrhea dangerous?",
            "How do I know if diarrhea is causing dehydration?",
            "What symptoms with diarrhea need medical review?",
        ],
        "ko": [
            "설사가 위험한 경우는 언제인가요?",
            "설사로 탈수가 의심되는 신호는 무엇인가요?",
            "설사와 함께 병원 진료가 필요한 증상은 무엇인가요?",
        ],
    },
    "cough": {
        "en": [
            "When is a cough considered serious?",
            "What symptoms with cough need urgent care?",
            "What are common causes of cough?",
        ],
        "ko": [
            "기침이 위험한 경우는 언제인가요?",
            "기침과 함께 응급으로 봐야 하는 증상은 무엇인가요?",
            "기침의 흔한 원인은 무엇인가요?",
        ],
    },
    "abdominal pain": {
        "en": [
            "What warning signs with abdominal pain need urgent care?",
            "What conditions can cause abdominal pain?",
            "When should abdominal pain be checked by a doctor?",
        ],
        "ko": [
            "복통과 함께 응급으로 봐야 하는 증상은 무엇인가요?",
            "복통의 흔한 원인은 무엇인가요?",
            "복통이 있을 때 언제 병원 진료가 필요한가요?",
        ],
    },
    "sore throat": {
        "en": [
            "When is a sore throat more serious than a common cold?",
            "What symptoms with sore throat need medical review?",
            "How can I manage sore throat at home?",
        ],
        "ko": [
            "목 통증이 감기보다 더 심각할 수 있는 경우는 언제인가요?",
            "목 통증과 함께 진료가 필요한 증상은 무엇인가요?",
            "집에서 목 통증을 관리하는 방법은 무엇인가요?",
        ],
    },
    "nausea": {
        "en": [
            "When is nausea a warning sign?",
            "What symptoms with nausea need medical review?",
            "What are common causes of nausea?",
        ],
        "ko": [
            "메스꺼움이 위험 신호일 수 있는 경우는 언제인가요?",
            "메스꺼움과 함께 진료가 필요한 증상은 무엇인가요?",
            "메스꺼움의 흔한 원인은 무엇인가요?",
        ],
    },
    "runny nose": {
        "en": [
            "When is a runny nose part of a cold versus allergy?",
            "What symptoms with runny nose need medical review?",
            "How can I manage a runny nose at home?",
        ],
        "ko": [
            "콧물이 감기와 알레르기 중 어느 쪽에 더 가까운지 어떻게 보나요?",
            "콧물과 함께 진료가 필요한 증상은 무엇인가요?",
            "집에서 콧물을 관리하는 방법은 무엇인가요?",
        ],
    },
}


def _sorted_combination_key(*symptoms: str) -> tuple[str, ...]:
    return tuple(sorted(
        str(symptom).strip().lower()
        for symptom in symptoms
        if str(symptom).strip()
    ))


COMBINATION_QUESTION_SUGGESTIONS: dict[tuple[str, ...], dict[str, list[str]]] = {
    _sorted_combination_key("fever", "cough"): {
        "en": [
            "Could fever and cough suggest flu or another respiratory infection?",
            "What symptoms with fever and cough need urgent care?",
            "When should I see a doctor for fever and cough together?",
        ],
        "ko": [
            "발열과 기침이 함께 있을 때 독감이나 호흡기 감염을 의심할 수 있나요?",
            "발열과 기침이 함께 있을 때 응급으로 봐야 하는 증상은 무엇인가요?",
            "발열과 기침이 같이 있을 때 언제 진료를 받아야 하나요?",
        ],
    },
    _sorted_combination_key("abdominal pain", "diarrhea"): {
        "en": [
            "Could abdominal pain and diarrhea suggest gastroenteritis or food-related illness?",
            "What symptoms with abdominal pain and diarrhea need urgent care?",
            "How do I watch for dehydration with abdominal pain and diarrhea?",
        ],
        "ko": [
            "복통과 설사가 함께 있을 때 위장염이나 음식 관련 문제를 의심할 수 있나요?",
            "복통과 설사가 같이 있을 때 응급으로 봐야 하는 증상은 무엇인가요?",
            "복통과 설사가 함께 있을 때 탈수는 어떻게 확인하나요?",
        ],
    },
}


DEFAULT_QUESTION_SUGGESTIONS: dict[str, list[str]] = {
    "en": [
        "What symptoms should I monitor?",
        "When should I seek medical care?",
        "What related conditions are commonly associated with this symptom?",
    ],
    "ko": [
        "어떤 증상을 추가로 관찰해야 하나요?",
        "언제 진료를 받아야 하나요?",
        "이 증상과 함께 흔히 관련되는 상태는 무엇인가요?",
    ],
}


def _parse_normalized_symptoms(normalized_query: str) -> list[str]:
    cleaned_query = (normalized_query or "").strip()
    if not cleaned_query:
        return []

    if NORMALIZED_QUERY_SEPARATOR not in cleaned_query:
        return [cleaned_query.lower()]

    return [
        symptom.strip().lower()
        for symptom in cleaned_query.split(NORMALIZED_QUERY_SEPARATOR)
        if symptom and symptom.strip()
    ]


def _build_combination_key(symptom_keys: list[str]) -> tuple[str, ...]:
    return _sorted_combination_key(*symptom_keys)


def _append_unique_suggestions(
    target: list[str],
    seen_suggestions: set[str],
    suggestions: list[str],
    limit: int,
) -> None:
    for suggestion in suggestions:
        if suggestion in seen_suggestions:
            continue

        seen_suggestions.add(suggestion)
        target.append(suggestion)

        if len(target) >= limit:
            return


def build_question_suggestions(
    normalized_query: str,
    detected_language: str,
) -> list[str]:
    language = "ko" if detected_language == "ko" else "en"
    symptom_keys = _parse_normalized_symptoms(normalized_query)

    if not symptom_keys:
        return DEFAULT_QUESTION_SUGGESTIONS[language]

    merged_suggestions: list[str] = []
    seen_suggestions: set[str] = set()

    combination_key = _build_combination_key(symptom_keys)
    combination_suggestions = COMBINATION_QUESTION_SUGGESTIONS.get(
        combination_key,
        {},
    ).get(language, [])

    _append_unique_suggestions(
        target=merged_suggestions,
        seen_suggestions=seen_suggestions,
        suggestions=combination_suggestions,
        limit=QUESTION_SUGGESTION_TOTAL_LIMIT,
    )

    if len(merged_suggestions) >= QUESTION_SUGGESTION_TOTAL_LIMIT:
        return merged_suggestions

    for symptom_key in symptom_keys:
        mapped = QUESTION_SUGGESTION_MAP.get(symptom_key, {})
        symptom_suggestions = mapped.get(language, [])

        _append_unique_suggestions(
            target=merged_suggestions,
            seen_suggestions=seen_suggestions,
            suggestions=symptom_suggestions[:QUESTION_SUGGESTION_PER_SYMPTOM_LIMIT],
            limit=QUESTION_SUGGESTION_TOTAL_LIMIT,
        )

        if len(merged_suggestions) >= QUESTION_SUGGESTION_TOTAL_LIMIT:
            return merged_suggestions

    if merged_suggestions:
        return merged_suggestions

    return DEFAULT_QUESTION_SUGGESTIONS[language]