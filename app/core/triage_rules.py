# app/core/triage_rules.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

TRIAGE_LEVEL_RED = "red"  # 용도: red 레벨 상수
TRIAGE_LEVEL_YELLOW = "yellow"  # 용도: yellow 레벨 상수
TRIAGE_LEVEL_GREEN = "green"  # 용도: green 레벨 상수

TRIAGE_SUPPORTED_LANGUAGES = {"ko", "en"}  # 용도: triage 지원 언어
TRIAGE_DEFAULT_LANGUAGE = "en"  # 용도: 기본 triage 메시지 언어

TRIAGE_MESSAGE_MAP_BY_LANGUAGE: dict[str, dict[str, str]] = {
    "ko": {
        TRIAGE_LEVEL_RED: (
            "즉시 의료진 평가가 필요할 수 있는 위험 신호가 있습니다. "
            "응급실 또는 가까운 의료기관에 바로 문의하세요."
        ),
        TRIAGE_LEVEL_YELLOW: (
            "증상의 정도나 지속 시간에 따라 빠른 진료 검토가 필요할 수 있습니다. "
            "가능하면 이른 시간 안에 의료진 상담을 고려하세요."
        ),
        TRIAGE_LEVEL_GREEN: (
            "현재 정보는 일반적인 참고용입니다. "
            "증상이 지속되거나 악화되면 의료진 상담이 필요할 수 있습니다."
        ),
    },
    "en": {
        TRIAGE_LEVEL_RED: (
            "Urgent warning signs are present. Seek immediate medical attention or emergency evaluation."
        ),
        TRIAGE_LEVEL_YELLOW: (
            "Some symptoms may need prompt medical review depending on severity, duration, or underlying conditions."
        ),
        TRIAGE_LEVEL_GREEN: (
            "This information may help with general understanding, but symptoms should still be monitored carefully."
        ),
    },
}

TRIAGE_SCORE_THRESHOLDS: dict[str, int] = {
    TRIAGE_LEVEL_RED: 4,
    TRIAGE_LEVEL_YELLOW: 2,
}  # 용도: triage 점수 임계값

TRIAGE_RULE_GROUPS: dict[str, dict[str, list[dict[str, object]]]] = {
    "ko": {
        "respiratory_red_flags": [
            {"pattern": "호흡곤란", "score": 4},
            {"pattern": "숨이 차", "score": 4},
            {"pattern": "숨차", "score": 4},
            {"pattern": "숨쉬기 힘들", "score": 4},
            {"pattern": "숨을 못 쉬", "score": 4},
            {"pattern": "숨이 안 쉬어", "score": 4},
            {"pattern": "숨이 안 쉬어져", "score": 4},
            {"pattern": "숨이 안 쉬어져요", "score": 4},
            {"pattern": "숨을 쉴 수 없", "score": 4},
            {"pattern": "호흡이 힘들", "score": 4},
            {"pattern": "호흡이 어려", "score": 4},
            {"pattern": "숨막", "score": 4},
        ],
        "neuro_red_flags": [
            {"pattern": "의식", "score": 4},
            {"pattern": "의식이 흐려", "score": 4},
            {"pattern": "정신이 혼미", "score": 4},
            {"pattern": "경련", "score": 4},
            {"pattern": "마비", "score": 4},
            {"pattern": "말이 어눌", "score": 4},
            {"pattern": "말이 잘 안 나와", "score": 4},
            {"pattern": "심한 두통", "score": 3},
            {"pattern": "극심한 두통", "score": 4},
        ],
        "cardio_red_flags": [
            {"pattern": "흉통", "score": 4},
            {"pattern": "가슴 통증", "score": 4},
            {"pattern": "가슴이 아파", "score": 4},
            {"pattern": "가슴이 너무 아파", "score": 4},
            {"pattern": "가슴이 심하게 아파", "score": 4},
            {"pattern": "가슴이 조여", "score": 4},
            {"pattern": "가슴이 답답", "score": 3},
        ],
        "bleeding_red_flags": [
            {"pattern": "피를 토", "score": 4},
            {"pattern": "토혈", "score": 4},
            {"pattern": "객혈", "score": 4},
            {"pattern": "혈변", "score": 4},
            {"pattern": "검은 변", "score": 4},
            {"pattern": "코피가 안 멈춰", "score": 4},
            {"pattern": "코피가 멈추지", "score": 4},
            {"pattern": "출혈이 안 멈춰", "score": 4},
            {"pattern": "출혈이 멈추지", "score": 4},
            {"pattern": "피가 안 멈춰", "score": 4},
            {"pattern": "피가 멈추지", "score": 4},
            {"pattern": "코피가 계속", "score": 3},
            {"pattern": "코피가 삼십분째", "score": 3},
            {"pattern": "코피가 30분째", "score": 3},
        ],
        "trauma_red_flags": [
            {"pattern": "머리 다친", "score": 4},
            {"pattern": "머리 부딪", "score": 4},
            {"pattern": "머리 외상", "score": 4},
            {"pattern": "넘어져서 머리", "score": 4},
        ],
        "dehydration_warning": [
            {"pattern": "심한 탈수", "score": 3},
            {"pattern": "탈수", "score": 2},
            {"pattern": "소변이 안 나와", "score": 2},
            {"pattern": "입이 너무 마", "score": 2},
        ],
        "gastro_warning": [
            {"pattern": "반복 구토", "score": 3},
            {"pattern": "계속 토", "score": 2},
            {"pattern": "토해", "score": 1},
            {"pattern": "구토", "score": 1},
            {"pattern": "설사", "score": 1},
            {"pattern": "복통", "score": 1},
            {"pattern": "배가 아파", "score": 1},
            {"pattern": "배가 계속 아파", "score": 2},
            {"pattern": "배가 너무 아파", "score": 2},
        ],
        "fever_warning": [
            {"pattern": "열이 계속", "score": 2},
            {"pattern": "열이 계속 나", "score": 2},
            {"pattern": "열이 이틀째", "score": 2},
            {"pattern": "열이 며칠째", "score": 2},
            {"pattern": "지속되는 열", "score": 2},
            {"pattern": "발열", "score": 1},
            {"pattern": "고열", "score": 2},
            {"pattern": "열이 나", "score": 1},
        ],
        "eye_warning": [
            {"pattern": "눈 충혈", "score": 1},
            {"pattern": "눈이 충혈", "score": 1},
            {"pattern": "눈이 빨개", "score": 1},
            {"pattern": "눈이 붉어", "score": 1},
            {"pattern": "눈이 아프", "score": 2},
            {"pattern": "시야가 흐려", "score": 3},
            {"pattern": "눈부심", "score": 2},
        ],
        "progression_warning": [
            {"pattern": "악화", "score": 2},
            {"pattern": "심해지", "score": 2},
            {"pattern": "계속 아파", "score": 2},
            {"pattern": "이틀째", "score": 1},
            {"pattern": "며칠째", "score": 1},
        ],
    },
    "en": {
        "respiratory_red_flags": [
            {"pattern": "shortness of breath", "score": 4},
            {"pattern": "trouble breathing", "score": 4},
            {"pattern": "can't breathe", "score": 4},
            {"pattern": "cannot breathe", "score": 4},
            {"pattern": "difficulty breathing", "score": 4},
        ],
        "neuro_red_flags": [
            {"pattern": "seizure", "score": 4},
            {"pattern": "confusion", "score": 4},
            {"pattern": "altered mental status", "score": 4},
            {"pattern": "weakness on one side", "score": 4},
            {"pattern": "severe headache", "score": 3},
            {"pattern": "can't wake", "score": 4},
            {"pattern": "passed out", "score": 4},
            {"pattern": "fainting", "score": 4},
        ],
        "cardio_red_flags": [
            {"pattern": "chest pain", "score": 4},
            {"pattern": "severe chest pain", "score": 4},
            {"pattern": "tight chest", "score": 4},
        ],
        "bleeding_red_flags": [
            {"pattern": "coughing blood", "score": 4},
            {"pattern": "vomiting blood", "score": 4},
            {"pattern": "bloody stool", "score": 4},
            {"pattern": "black stool", "score": 4},
            {"pattern": "nosebleed won't stop", "score": 4},
            {"pattern": "nose bleed won't stop", "score": 4},
            {"pattern": "persistent bleeding", "score": 4},
            {"pattern": "bleeding for 30 minutes", "score": 4},
            {"pattern": "nosebleed for 30 minutes", "score": 4},
        ],
        "trauma_red_flags": [
            {"pattern": "head injury", "score": 4},
            {"pattern": "hit my head", "score": 4},
            {"pattern": "head trauma", "score": 4},
        ],
        "dehydration_warning": [
            {"pattern": "severe dehydration", "score": 3},
            {"pattern": "dehydration", "score": 2},
            {"pattern": "not urinating", "score": 2},
        ],
        "gastro_warning": [
            {"pattern": "repeated vomiting", "score": 3},
            {"pattern": "persistent vomiting", "score": 3},
            {"pattern": "vomiting", "score": 1},
            {"pattern": "diarrhea", "score": 1},
            {"pattern": "abdominal pain", "score": 1},
            {"pattern": "stomach pain", "score": 1},
            {"pattern": "ongoing abdominal pain", "score": 2},
        ],
        "fever_warning": [
            {"pattern": "persistent fever", "score": 2},
            {"pattern": "high fever", "score": 2},
            {"pattern": "fever", "score": 1},
            {"pattern": "fever for two days", "score": 2},
            {"pattern": "fever for several days", "score": 2},
        ],
        "eye_warning": [
            {"pattern": "eye redness", "score": 1},
            {"pattern": "red eye", "score": 1},
            {"pattern": "bloodshot eyes", "score": 1},
            {"pattern": "bloodshot eye", "score": 1},
            {"pattern": "eye pain", "score": 2},
            {"pattern": "blurred vision", "score": 3},
            {"pattern": "light sensitivity", "score": 2},
        ],
        "progression_warning": [
            {"pattern": "getting worse", "score": 2},
            {"pattern": "worsening", "score": 2},
            {"pattern": "ongoing cough", "score": 1},
            {"pattern": "for two days", "score": 1},
            {"pattern": "for several days", "score": 1},
        ],
    },
}