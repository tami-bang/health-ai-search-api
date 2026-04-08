# symptom_rules.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

# 공통 설정값
DEFAULT_NOTICE = "This service is for informational purposes only and is not a medical diagnosis."
MEDLINEPLUS_SOURCE_NAME = "MedlinePlus"
MEDLINEPLUS_RETMAX = 5

# 정규화 / fallback 기준값
NORMALIZER_SEMANTIC_THRESHOLD = 0.58
AI_FALLBACK_MIN_TOKEN_COUNT = 3
AI_FALLBACK_MIN_CONFIDENCE = 0.35

# 검색용 canonical symptom + 영어 변형 표현
SYMPTOM_RULES: dict[str, list[str]] = {
    "abdominal pain": [
        "abdominal pain",
        "stomach pain",
        "stomachache",
        "stomach ache",
        "belly pain",
        "my stomach hurts",
        "my belly hurts",
        "pain in my abdomen",
        "pain in my stomach",
        "abdominal cramps",
        "my abdomen hurts",
    ],
    "headache": [
        "headache",
        "head pain",
        "my head hurts",
        "pain in my head",
        "migraine",
        "my head is pounding",
        "splitting headache",
    ],
    "concussion": [
        "concussion",
        "head injury",
        "hit my head",
        "bumped my head",
        "i hit my head",
        "i bumped my head",
        "head trauma",
    ],
    "runny nose": [
        "runny nose",
        "nasal discharge",
        "my nose is running",
    ],
    "fever": [
        "fever",
        "high temperature",
        "temperature",
        "feverish",
        "i have a fever",
    ],
    "diarrhea": [
        "diarrhea",
        "loose stool",
        "watery stool",
    ],
    "cough": [
        "cough",
        "coughing",
        "dry cough",
        "wet cough",
    ],
    "sore throat": [
        "sore throat",
        "throat pain",
        "pain in my throat",
    ],
    "nausea": [
        "nausea",
        "feel nauseous",
        "vomiting",
        "throwing up",
        "want to vomit",
    ],
}

# 한국어 외상성 머리 충격 패턴
# 확장 포인트: 충돌/낙상/교통사고 관련 표현 추가 시 여기만 수정
KOREAN_HEAD_TRAUMA_PATTERNS: dict[str, str] = {
    "머리를 부딪": "concussion",
    "머리 부딪": "concussion",
    "머리를 박": "concussion",
    "머리 박": "concussion",
    "머리를 맞": "concussion",
    "머리 맞": "concussion",
    "머리를 다쳤": "concussion",
    "머리 다쳤": "concussion",
    "머리 다침": "concussion",
    "머리 충격": "concussion",
    "머리 외상": "concussion",
}

# 영어 외상성 머리 충격 패턴
ENGLISH_HEAD_TRAUMA_PATTERNS: dict[str, str] = {
    "hit my head": "concussion",
    "bumped my head": "concussion",
    "head injury": "concussion",
    "head trauma": "concussion",
    "hurt my head": "concussion",
}

# 한국어 일반 증상 룰
# 확장 포인트: 새 증상 추가 시 if/elif 대신 여기만 수정
KOREAN_RULES: dict[str, str] = {
    "복통": "abdominal pain",
    "배가 아파": "abdominal pain",
    "배가 아프": "abdominal pain",
    "속이 아파": "abdominal pain",
    "속이 쓰려": "abdominal pain",
    "두통": "headache",
    "머리가 아파": "headache",
    "머리가 아프": "headache",
    "머리가 깨질": "headache",
    "콧물": "runny nose",
    "기침": "cough",
    "열": "fever",
    "발열": "fever",
    "설사": "diarrhea",
    "목이 아파": "sore throat",
    "목이 따가": "sore throat",
    "인후": "sore throat",
    "메스꺼움": "nausea",
    "구토": "nausea",
    "토할 것 같": "nausea",
}