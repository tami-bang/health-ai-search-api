# app/core/symptom_rules.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

DEFAULT_NOTICE = "This service is for informational purposes only and is not a medical diagnosis."  # 용도: 공통 안내 문구
MEDLINEPLUS_SOURCE_NAME = "MedlinePlus"  # 용도: 외부 검색 소스 표시명
MEDLINEPLUS_RETMAX = 5  # 용도: 외부 검색 최대 결과 수

NORMALIZER_SEMANTIC_THRESHOLD = 0.58  # 용도: semantic 정규화 임계값
NORMALIZER_ML_CONFIDENCE_THRESHOLD = 0.60  # 용도: ML 정규화 임계값
AI_FALLBACK_MIN_TOKEN_COUNT = 3  # 용도: AI fallback 최소 토큰 수
AI_FALLBACK_MIN_CONFIDENCE = 0.35  # 용도: AI fallback 최소 confidence

PREDICTED_LABEL_DISPLAY_MIN_CONFIDENCE = 0.20  # 용도: meta predicted_label 노출 최소 confidence
NORMALIZED_QUERY_SEPARATOR = " | "  # 용도: 복합 증상 normalized query 구분자
MAX_NORMALIZED_SYMPTOMS = 3  # 용도: 한 번에 실을 최대 증상 수

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
    "nosebleed": [
        "nosebleed",
        "nose bleed",
        "epistaxis",
        "bloody nose",
    ],
    "eye redness": [
        "eye redness",
        "red eye",
        "red eyes",
        "bloodshot eye",
        "bloodshot eyes",
        "conjunctivitis",
        "pink eye",
    ],
}

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
    "nosebleed": ["nosebleed", "nose bleed", "epistaxis", "bloody nose"],
    "eye redness": [
        "eye redness",
        "red eye",
        "bloodshot eyes",
        "conjunctivitis",
        "pink eye",
    ],
}

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
    "nosebleed": [
        "nosebleed",
        "nose bleed",
        "epistaxis",
        "bloody nose",
        "my nose is bleeding",
        "my nose won't stop bleeding",
        "bleeding from my nose",
    ],
    "eye redness": [
        "eye redness",
        "red eye",
        "red eyes",
        "bloodshot eye",
        "bloodshot eyes",
        "pink eye",
        "conjunctivitis",
        "my eyes are red",
        "my eye is red",
        "my eyes are bloodshot",
        "my eye is bloodshot",
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
    "코피": "nosebleed",
    "비출혈": "nosebleed",
    "코에서 피": "nosebleed",
    "눈 충혈": "eye redness",
    "눈이 충혈": "eye redness",
    "눈이 빨개": "eye redness",
    "눈이 붉어": "eye redness",
    "충혈된 눈": "eye redness",
    "충혈상태": "eye redness",
}