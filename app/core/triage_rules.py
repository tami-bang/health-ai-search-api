# app/core/triage_rules.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

TRIAGE_LEVEL_RED = "red"
TRIAGE_LEVEL_YELLOW = "yellow"
TRIAGE_LEVEL_GREEN = "green"

TRIAGE_MESSAGE_MAP: dict[str, str] = {
    TRIAGE_LEVEL_RED: (
        "Urgent warning signs are present. Seek immediate medical attention or emergency evaluation."
    ),
    TRIAGE_LEVEL_YELLOW: (
        "Some symptoms may need prompt medical review depending on severity, duration, or underlying conditions."
    ),
    TRIAGE_LEVEL_GREEN: (
        "This information may help with general understanding, but symptoms should still be monitored carefully."
    ),
}

# 확장 포인트:
# - 단순 substring 매칭을 넘어서 점수 기반으로 유지
# - 나중에 age / duration / chronic disease / medication history 룰을 같은 구조로 추가 가능
TRIAGE_SCORE_THRESHOLDS: dict[str, int] = {
    TRIAGE_LEVEL_RED: 4,
    TRIAGE_LEVEL_YELLOW: 2,
}

# 카테고리별로 나눠두면 유지보수 시 특정 도메인 룰만 수정 가능하다.
TRIAGE_RULE_GROUPS: dict[str, dict[str, list[dict[str, object]]]] = {
    "ko": {
        "respiratory_red_flags": [
            {"pattern": "호흡곤란", "score": 4},
            {"pattern": "숨이 차", "score": 4},
            {"pattern": "숨쉬기 힘들", "score": 4},
            {"pattern": "숨을 못 쉬", "score": 4},
        ],
        "neuro_red_flags": [
            {"pattern": "의식", "score": 4},
            {"pattern": "경련", "score": 4},
            {"pattern": "마비", "score": 4},
            {"pattern": "말이 어눌", "score": 4},
            {"pattern": "심한 두통", "score": 3},
            {"pattern": "극심한 두통", "score": 4},
        ],
        "cardio_red_flags": [
            {"pattern": "흉통", "score": 4},
            {"pattern": "가슴 통증", "score": 4},
        ],
        "bleeding_red_flags": [
            {"pattern": "피를 토", "score": 4},
            {"pattern": "혈변", "score": 4},
        ],
        "trauma_red_flags": [
            {"pattern": "머리 다친", "score": 4},
            {"pattern": "머리 부딪", "score": 4},
            {"pattern": "머리 외상", "score": 4},
        ],
        "dehydration_warning": [
            {"pattern": "심한 탈수", "score": 3},
            {"pattern": "탈수", "score": 2},
        ],
        "gastro_warning": [
            {"pattern": "반복 구토", "score": 3},
            {"pattern": "구토", "score": 1},
            {"pattern": "설사", "score": 1},
            {"pattern": "복통", "score": 1},
        ],
        "fever_warning": [
            {"pattern": "열이 계속", "score": 2},
            {"pattern": "지속되는 열", "score": 2},
            {"pattern": "발열", "score": 1},
            {"pattern": "고열", "score": 2},
        ],
        "progression_warning": [
            {"pattern": "악화", "score": 2},
            {"pattern": "심해지", "score": 2},
            {"pattern": "계속 아파", "score": 2},
        ],
    },
    "en": {
        "respiratory_red_flags": [
            {"pattern": "shortness of breath", "score": 4},
            {"pattern": "trouble breathing", "score": 4},
            {"pattern": "can't breathe", "score": 4},
        ],
        "neuro_red_flags": [
            {"pattern": "seizure", "score": 4},
            {"pattern": "confusion", "score": 4},
            {"pattern": "weakness on one side", "score": 4},
            {"pattern": "severe headache", "score": 3},
            {"pattern": "can't wake", "score": 4},
            {"pattern": "passed out", "score": 4},
            {"pattern": "fainting", "score": 4},
        ],
        "cardio_red_flags": [
            {"pattern": "chest pain", "score": 4},
        ],
        "bleeding_red_flags": [
            {"pattern": "coughing blood", "score": 4},
            {"pattern": "bloody stool", "score": 4},
        ],
        "trauma_red_flags": [
            {"pattern": "head injury", "score": 4},
            {"pattern": "hit my head", "score": 4},
            {"pattern": "head trauma", "score": 4},
        ],
        "dehydration_warning": [
            {"pattern": "severe dehydration", "score": 3},
            {"pattern": "dehydration", "score": 2},
        ],
        "gastro_warning": [
            {"pattern": "repeated vomiting", "score": 3},
            {"pattern": "vomiting", "score": 1},
            {"pattern": "diarrhea", "score": 1},
            {"pattern": "abdominal pain", "score": 1},
        ],
        "fever_warning": [
            {"pattern": "persistent fever", "score": 2},
            {"pattern": "high fever", "score": 2},
            {"pattern": "fever", "score": 1},
        ],
        "progression_warning": [
            {"pattern": "getting worse", "score": 2},
            {"pattern": "worsening", "score": 2},
            {"pattern": "ongoing cough", "score": 1},
        ],
    },
}