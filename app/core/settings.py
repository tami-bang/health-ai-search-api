# settings.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import os  # 환경변수 조회


APP_NAME = "Health AI Search API"

# Hugging Face 생성 모델 설정
# 처음에는 가벼운 instruct 계열로 시작하고, 나중에 교체는 여기서만 하면 됨
HF_GENERATION_MODEL_NAME = os.getenv(
    "HF_GENERATION_MODEL_NAME",
    "google/flan-t5-base",
)

# 생성 기능 on/off
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "true").lower() == "true"

# GPU 자동 사용 여부
ENABLE_GPU = os.getenv("ENABLE_GPU", "true").lower() == "true"

# 생성 길이 제한
AI_SUMMARY_MAX_NEW_TOKENS = int(os.getenv("AI_SUMMARY_MAX_NEW_TOKENS", "180"))

# 생성 입력 길이 제한
AI_SUMMARY_MAX_CONTEXT_CHARS = int(os.getenv("AI_SUMMARY_MAX_CONTEXT_CHARS", "2200"))

# 검색 결과 컨텍스트에 포함할 최대 개수
AI_SUMMARY_MAX_ITEMS = int(os.getenv("AI_SUMMARY_MAX_ITEMS", "3"))

# 모델 로드 실패 시 기존 검색 응답만 유지
AI_SUMMARY_FAIL_OPEN = os.getenv("AI_SUMMARY_FAIL_OPEN", "true").lower() == "true"

# RAG 설정
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
RAG_INTERNAL_TOP_K = int(os.getenv("RAG_INTERNAL_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))