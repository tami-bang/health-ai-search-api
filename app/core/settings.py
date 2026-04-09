# app/core/settings.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import os  # 환경변수 조회
from pathlib import Path  # 프로젝트 기준 경로 처리


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

# 요약은 기본 비활성화로 두고 필요할 때만 켜게 한다.
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
AI_SUMMARY_MAX_ITEMS = int(os.getenv("AI_SUMMARY_MAX_ITEMS", "2"))

# RAG 설정
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
RAG_INTERNAL_TOP_K = int(os.getenv("RAG_INTERNAL_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))

# 내부 지식 파일 경로
INTERNAL_KNOWLEDGE_JSON_PATH = os.getenv(
    "INTERNAL_KNOWLEDGE_JSON_PATH",
    str(DATA_DIR / "internal_health_docs.json"),
)

# 학습/추론 분리용 아티팩트 경로
SYMPTOM_MODEL_ARTIFACT_PATH = os.getenv(
    "SYMPTOM_MODEL_ARTIFACT_PATH",
    str(ARTIFACTS_DIR / "symptom_classifier.pkl"),
)
SYMPTOM_VECTORIZER_ARTIFACT_PATH = os.getenv(
    "SYMPTOM_VECTORIZER_ARTIFACT_PATH",
    str(ARTIFACTS_DIR / "symptom_vectorizer.pkl"),
)