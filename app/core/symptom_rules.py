# app/core/symptom_rules.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

# 공통 설정값
DEFAULT_NOTICE = "This service is for informational purposes only and is not a medical diagnosis."
MEDLINEPLUS_SOURCE_NAME = "MedlinePlus"
MEDLINEPLUS_RETMAX = 5

# 정규화 / fallback 기준값
NORMALIZER_SEMANTIC_THRESHOLD = 0.58
NORMALIZER_ML_CONFIDENCE_THRESHOLD = 0.60
AI_FALLBACK_MIN_TOKEN_COUNT = 3
AI_FALLBACK_MIN_CONFIDENCE = 0.35

# 증상별 검색 확장 키워드
# 확장 포인트:
# - 실제 검색 품질이 안 좋은 증상만 여기 추가하면 됨
# - retriever에서 이 매핑을 참고해 검색 query를 넓힌다
SYMPTOM_SEARCH_EXPANSIONS: dict[str, list[str]] = {
    "runny nose": [
        "runny nose",
        "rhinitis",
        "common cold",
        "allergy",
    ],
    "cough": [
        "cough",
        "common cold",
        "bronchitis",
    ],
    "fever": [
        "fever",
        "infection",
        "flu",
    ],
    "diarrhea": [
        "diarrhea",
        "gastroenteritis",
        "dehydration",
    ],
    "headache": [
        "headache",
        "migraine",
        "tension headache",
    ],
    "concussion": [
        "concussion",
        "head injury",
        "brain injury",
    ],
    "sore throat": [
        "sore throat",
        "pharyngitis",
        "common cold",
    ],
    "nausea": [
        "nausea",
        "vomiting",
        "stomach flu",
    ],
    "abdominal pain": [
        "abdominal pain",
        "stomach pain",
        "digestive problems",
    ],
}

# broad/general 문서보다 증상 직접 관련 문서를 우선시키기 위한 힌트
SYMPTOM_PRIORITY_KEYWORDS: dict[str, list[str]] = {
    "runny nose": ["runny nose", "rhinitis", "allergy", "cold"],
    "cough": ["cough", "bronchitis", "cold"],
    "fever": ["fever", "flu", "infection"],
    "diarrhea": ["diarrhea", "dehydration"],
    "headache": ["headache", "migraine"],
    "concussion": ["concussion", "head injury"],
    "sore throat": ["sore throat", "pharyngitis"],
    "nausea": ["nausea", "vomiting"],
    "abdominal pain": ["abdominal pain", "stomach pain"],
}

# 영어 canonical symptom + 영어 변형 표현
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

ENGLISH_HEAD_TRAUMA_PATTERNS: dict[str, str] = {
    "hit my head": "concussion",
    "bumped my head": "concussion",
    "head injury": "concussion",
    "head trauma": "concussion",
    "hurt my head": "concussion",
}

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