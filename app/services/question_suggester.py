# question_suggester.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원


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


def build_question_suggestions(
    normalized_query: str,
    detected_language: str,
) -> list[str]:
    language = "ko" if detected_language == "ko" else "en"
    symptom_key = (normalized_query or "").strip().lower()

    mapped = QUESTION_SUGGESTION_MAP.get(symptom_key, {})
    suggestions = mapped.get(language)

    if suggestions:
        return suggestions

    return DEFAULT_QUESTION_SUGGESTIONS[language]