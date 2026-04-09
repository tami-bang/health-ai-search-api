# app/core/settings.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import os  # 용도: 환경변수 조회
from pathlib import Path  # 용도: 프로젝트 기준 경로 처리

# 앱 기본 정보
APP_NAME = "Health AI Search API"

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parents[2]

# 데이터/아티팩트 경로
DATA_DIR = BASE_DIR / "app" / "data"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# 실행 환경 설정
APP_ENV = os.getenv("APP_ENV", "local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 기능 플래그
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"
ENABLE_INTERNAL_SEARCH = os.getenv("ENABLE_INTERNAL_SEARCH", "true").lower() == "true"
ENABLE_EXTERNAL_SEARCH = os.getenv("ENABLE_EXTERNAL_SEARCH", "true").lower() == "true"
ENABLE_TRIAGE = os.getenv("ENABLE_TRIAGE", "true").lower() == "true"

# 요약 기능 플래그
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "false").lower() == "true"
DEFAULT_INCLUDE_SUMMARY = os.getenv("DEFAULT_INCLUDE_SUMMARY", "false").lower() == "true"
AI_SUMMARY_FAIL_OPEN = os.getenv("AI_SUMMARY_FAIL_OPEN", "true").lower() == "true"

# GPU / preload
ENABLE_GPU = os.getenv("ENABLE_GPU", "true").lower() == "true"
ENABLE_STARTUP_WARMUP = os.getenv("ENABLE_STARTUP_WARMUP", "false").lower() == "true"
SUMMARY_MODEL_PRELOAD = os.getenv("SUMMARY_MODEL_PRELOAD", "false").lower() == "true"

# 검색 입력 제한
SEARCH_QUERY_MIN_LENGTH = int(os.getenv("SEARCH_QUERY_MIN_LENGTH", "2"))
SEARCH_QUERY_MAX_LENGTH = int(os.getenv("SEARCH_QUERY_MAX_LENGTH", "300"))

# MedlinePlus 설정
MEDLINEPLUS_BASE_URL = os.getenv(
    "MEDLINEPLUS_BASE_URL",
    "https://wsearch.nlm.nih.gov/ws/query",
)
MEDLINEPLUS_TIMEOUT_SECONDS = float(os.getenv("MEDLINEPLUS_TIMEOUT_SECONDS", "4"))
MEDLINEPLUS_RETMAX = int(os.getenv("MEDLINEPLUS_RETMAX", "5"))
ENABLE_EXTERNAL_SEARCH_CACHE = os.getenv("ENABLE_EXTERNAL_SEARCH_CACHE", "true").lower() == "true"
MEDLINEPLUS_CACHE_TTL_SECONDS = int(os.getenv("MEDLINEPLUS_CACHE_TTL_SECONDS", "1800"))
MEDLINEPLUS_CACHE_MAX_SIZE = int(os.getenv("MEDLINEPLUS_CACHE_MAX_SIZE", "256"))

# 생성 모델 설정
HF_GENERATION_MODEL_NAME = os.getenv(
    "HF_GENERATION_MODEL_NAME",
    "google/flan-t5-base",
)
AI_SUMMARY_MAX_NEW_TOKENS = int(os.getenv("AI_SUMMARY_MAX_NEW_TOKENS", "120"))
AI_SUMMARY_MAX_CONTEXT_CHARS = int(os.getenv("AI_SUMMARY_MAX_CONTEXT_CHARS", "1800"))
AI_SUMMARY_MAX_ITEMS = int(os.getenv("AI_SUMMARY_MAX_ITEMS", "3"))
AI_SUMMARY_MAX_INPUT_TOKENS = int(os.getenv("AI_SUMMARY_MAX_INPUT_TOKENS", "1024"))
AI_SUMMARY_MIN_OUTPUT_CHARS = int(os.getenv("AI_SUMMARY_MIN_OUTPUT_CHARS", "20"))
AI_SUMMARY_NUM_BEAMS = int(os.getenv("AI_SUMMARY_NUM_BEAMS", "4"))
AI_SUMMARY_TEMPERATURE = float(os.getenv("AI_SUMMARY_TEMPERATURE", "0.2"))
AI_SUMMARY_REPETITION_PENALTY = float(os.getenv("AI_SUMMARY_REPETITION_PENALTY", "1.05"))
AI_SUMMARY_DO_SAMPLE = os.getenv("AI_SUMMARY_DO_SAMPLE", "false").lower() == "true"
AI_SUMMARY_EARLY_STOPPING = os.getenv("AI_SUMMARY_EARLY_STOPPING", "true").lower() == "true"

# summary 품질 제어
AI_SUMMARY_SENTENCE_LIMIT = int(os.getenv("AI_SUMMARY_SENTENCE_LIMIT", "2"))
AI_SUMMARY_FALLBACK_RESULT_LIMIT = int(os.getenv("AI_SUMMARY_FALLBACK_RESULT_LIMIT", "3"))
AI_SUMMARY_FALLBACK_SENTENCE_LIMIT = int(os.getenv("AI_SUMMARY_FALLBACK_SENTENCE_LIMIT", "2"))
AI_SUMMARY_ITEM_TITLE_MAX_CHARS = int(os.getenv("AI_SUMMARY_ITEM_TITLE_MAX_CHARS", "100"))
AI_SUMMARY_ITEM_SUMMARY_MAX_CHARS = int(os.getenv("AI_SUMMARY_ITEM_SUMMARY_MAX_CHARS", "260"))
AI_SUMMARY_PROMPT_LOG_MAX_CHARS = int(os.getenv("AI_SUMMARY_PROMPT_LOG_MAX_CHARS", "800"))
AI_SUMMARY_RAW_OUTPUT_LOG_MAX_CHARS = int(os.getenv("AI_SUMMARY_RAW_OUTPUT_LOG_MAX_CHARS", "600"))
AI_SUMMARY_CONTEXT_INCLUDE_SOURCE = os.getenv("AI_SUMMARY_CONTEXT_INCLUDE_SOURCE", "true").lower() == "true"
AI_SUMMARY_CONTEXT_INCLUDE_URL = os.getenv("AI_SUMMARY_CONTEXT_INCLUDE_URL", "false").lower() == "true"
AI_SUMMARY_PREFER_DIVERSE_RESULTS = os.getenv("AI_SUMMARY_PREFER_DIVERSE_RESULTS", "true").lower() == "true"
AI_SUMMARY_MAX_SYMPTOM_HINTS = int(os.getenv("AI_SUMMARY_MAX_SYMPTOM_HINTS", "3"))
AI_SUMMARY_CONTEXT_CANDIDATE_POOL = int(os.getenv("AI_SUMMARY_CONTEXT_CANDIDATE_POOL", "6"))

# summary 검증 규칙
AI_SUMMARY_REQUIRE_HINT_MATCH = os.getenv("AI_SUMMARY_REQUIRE_HINT_MATCH", "true").lower() == "true"
AI_SUMMARY_MIN_CONTEXT_OVERLAP_COUNT = int(
    os.getenv("AI_SUMMARY_MIN_CONTEXT_OVERLAP_COUNT", "2"),
)
AI_SUMMARY_MAX_UNSUPPORTED_KEYWORD_COUNT = int(
    os.getenv("AI_SUMMARY_MAX_UNSUPPORTED_KEYWORD_COUNT", "4"),
)

# 의료 안내 문구
AI_SUMMARY_KO_DISCLAIMER = os.getenv(
    "AI_SUMMARY_KO_DISCLAIMER",
    "이 내용은 참고용 건강 정보이며 의학적 진단이 아닙니다. 증상이 지속되거나 악화되면 의료진 상담이 필요합니다.",
)
AI_SUMMARY_EN_DISCLAIMER = os.getenv(
    "AI_SUMMARY_EN_DISCLAIMER",
    "This is general health information only and not a medical diagnosis. Seek medical care if symptoms continue or worsen.",
)

# RAG 설정
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
RAG_INTERNAL_TOP_K = int(os.getenv("RAG_INTERNAL_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))

# rerank 성능 제어
RERANK_CANDIDATE_LIMIT = int(os.getenv("RERANK_CANDIDATE_LIMIT", "12"))

# 검색 병렬 처리 설정
RETRIEVAL_MAX_WORKERS = int(os.getenv("RETRIEVAL_MAX_WORKERS", "6"))

# 질문 추천 설정
QUESTION_SUGGESTION_PER_SYMPTOM_LIMIT = int(
    os.getenv("QUESTION_SUGGESTION_PER_SYMPTOM_LIMIT", "2"),
)
QUESTION_SUGGESTION_TOTAL_LIMIT = int(
    os.getenv("QUESTION_SUGGESTION_TOTAL_LIMIT", "4"),
)

# 내부 지식 파일 경로
INTERNAL_KNOWLEDGE_JSON_PATH = os.getenv(
    "INTERNAL_KNOWLEDGE_JSON_PATH",
    str(DATA_DIR / "internal_health_docs.json"),
)

# sklearn 아티팩트 경로
SYMPTOM_MODEL_ARTIFACT_PATH = os.getenv(
    "SYMPTOM_MODEL_ARTIFACT_PATH",
    str(ARTIFACTS_DIR / "symptom_classifier.pkl"),
)
SYMPTOM_VECTORIZER_ARTIFACT_PATH = os.getenv(
    "SYMPTOM_VECTORIZER_ARTIFACT_PATH",
    str(ARTIFACTS_DIR / "symptom_vectorizer.pkl"),
)

# 학습 파이프라인 메타데이터
TRAINING_DATASET_NAME = os.getenv(
    "TRAINING_DATASET_NAME",
    "gretelai/symptom_to_diagnosis",
)
TRAINING_DATASET_VERSION = os.getenv(
    "TRAINING_DATASET_VERSION",
    "hf_default",
)
SYMPTOM_MODEL_VERSION = os.getenv(
    "SYMPTOM_MODEL_VERSION",
    "symptom-lr-v1",
)
TRAINING_RANDOM_STATE = int(os.getenv("TRAINING_RANDOM_STATE", "42"))

# Hugging Face 분류 모델 설정
HF_CLASSIFIER_BASE_MODEL_NAME = os.getenv(
    "HF_CLASSIFIER_BASE_MODEL_NAME",
    "distilbert-base-uncased",
)
HF_CLASSIFIER_MODEL_VERSION = os.getenv(
    "HF_CLASSIFIER_MODEL_VERSION",
    "symptom-hf-v1",
)
HF_CLASSIFIER_ARTIFACT_DIR = os.getenv(
    "HF_CLASSIFIER_ARTIFACT_DIR",
    str(ARTIFACTS_DIR / "hf_symptom_classifier"),
)
HF_CLASSIFIER_METADATA_PATH = os.getenv(
    "HF_CLASSIFIER_METADATA_PATH",
    str(ARTIFACTS_DIR / "hf_symptom_classifier_metadata.json"),
)
HF_CLASSIFIER_MAX_LENGTH = int(os.getenv("HF_CLASSIFIER_MAX_LENGTH", "160"))
HF_CLASSIFIER_NUM_EPOCHS = int(os.getenv("HF_CLASSIFIER_NUM_EPOCHS", "2"))
HF_CLASSIFIER_BATCH_SIZE = int(os.getenv("HF_CLASSIFIER_BATCH_SIZE", "16"))
HF_CLASSIFIER_LEARNING_RATE = float(os.getenv("HF_CLASSIFIER_LEARNING_RATE", "2e-5"))

# 추론 시 어떤 모델을 우선 사용할지 결정
PREFERRED_CLASSIFIER_BACKEND = os.getenv(
    "PREFERRED_CLASSIFIER_BACKEND",
    "hf",
).strip().lower()