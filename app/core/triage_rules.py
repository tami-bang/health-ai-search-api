# triage_rules.py
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
# - 지금은 실무형 단순 룰 기반
# - 나중에 증상 조합 점수화, ML 분류, 의학 도메인 룰엔진으로 교체 가능
RED_FLAG_PATTERNS: dict[str, list[str]] = {
    "ko": [
        "숨이 차",
        "호흡곤란",
        "숨쉬기 힘들",
        "의식",
        "경련",
        "가슴 통증",
        "흉통",
        "피를 토",
        "혈변",
        "말이 어눌",
        "마비",
        "쓰러",
        "심한 탈수",
        "심하게 아파",
        "극심한 두통",
        "머리 다친",
        "머리 부딪",
        "반복 구토",
    ],
    "en": [
        "shortness of breath",
        "trouble breathing",
        "chest pain",
        "seizure",
        "passed out",
        "fainting",
        "confusion",
        "coughing blood",
        "bloody stool",
        "severe dehydration",
        "severe headache",
        "head injury",
        "hit my head",
        "repeated vomiting",
        "can't wake",
        "weakness on one side",
    ],
}

YELLOW_FLAG_PATTERNS: dict[str, list[str]] = {
    "ko": [
        "열이 계속",
        "지속되는 열",
        "계속 아파",
        "악화",
        "심해지",
        "탈수",
        "복통",
        "설사",
        "구토",
        "두통",
    ],
    "en": [
        "persistent fever",
        "getting worse",
        "worsening",
        "dehydration",
        "abdominal pain",
        "diarrhea",
        "vomiting",
        "headache",
        "ongoing cough",
    ],
}