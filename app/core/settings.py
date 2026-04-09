# settings.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import os  # 환경변수 조회
from pathlib import Path  # 프로젝트 기준 경로 및 파일 경로 관리


# 앱 기본 정보
APP_NAME = "Health AI Search API"

# 프로젝트 루트 경로
# 예: C:/Users/.../health-ai-search-api
BASE_DIR = Path(__file__).resolve().parents[2]

# 내부 데이터 파일들이 위치한 디렉토리
# 현재 구조 기준: <project_root>/app/data
DATA_DIR = BASE_DIR / "app" / "data"

# 학습 결과물, 캐시, 모델 산출물 등을 저장할 디렉토리
# 예: vectorizer.pkl, model.pkl, 임시 아티팩트 등
ARTIFACTS_DIR = BASE_DIR / "artifacts"


# 실행 환경 설정
# local / dev / prod 같은 실행 모드 구분용
APP_ENV = os.getenv("APP_ENV", "local")

# 로그 레벨 설정
# DEBUG / INFO / WARNING / ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# 기능 on/off 플래그
# 번역 기능 사용 여부
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "true").lower() == "true"

# 내부 문서 검색(RAG용 내부 지식 검색) 사용 여부
ENABLE_INTERNAL_SEARCH = os.getenv("ENABLE_INTERNAL_SEARCH", "true").lower() == "true"

# 외부 검색(MedlinePlus 등) 사용 여부
ENABLE_EXTERNAL_SEARCH = os.getenv("ENABLE_EXTERNAL_SEARCH", "true").lower() == "true"

# 응급도/주의도 분기 기능 사용 여부
ENABLE_TRIAGE = os.getenv("ENABLE_TRIAGE", "true").lower() == "true"

# AI 요약 생성 기능 사용 여부
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "true").lower() == "true"

# GPU 자동 사용 여부
# 사용 가능한 환경이면 generation 모델 로드 시 GPU 활용
ENABLE_GPU = os.getenv("ENABLE_GPU", "true").lower() == "true"


# 검색 입력값 제한
# 최소 검색어 길이
SEARCH_QUERY_MIN_LENGTH = int(os.getenv("SEARCH_QUERY_MIN_LENGTH", "2"))

# 최대 검색어 길이
SEARCH_QUERY_MAX_LENGTH = int(os.getenv("SEARCH_QUERY_MAX_LENGTH", "300"))


# 외부 의료 검색 API(MedlinePlus) 설정
# 외부 요청 타임아웃(초)
MEDLINEPLUS_TIMEOUT_SECONDS = float(os.getenv("MEDLINEPLUS_TIMEOUT_SECONDS", "10"))

# 최대 검색 결과 개수
MEDLINEPLUS_RETMAX = int(os.getenv("MEDLINEPLUS_RETMAX", "5"))


# Hugging Face 생성 모델 설정
# 처음에는 가벼운 instruct 계열로 시작하고,
# 추후 다른 생성 모델로 교체하더라도 여기만 수정하면 됨
HF_GENERATION_MODEL_NAME = os.getenv(
    "HF_GENERATION_MODEL_NAME",
    "google/flan-t5-base",
)

# 생성 응답 최대 토큰 수
AI_SUMMARY_MAX_NEW_TOKENS = int(os.getenv("AI_SUMMARY_MAX_NEW_TOKENS", "180"))

# 생성 모델 입력에 넣을 최대 컨텍스트 길이(문자 수 기준)
AI_SUMMARY_MAX_CONTEXT_CHARS = int(os.getenv("AI_SUMMARY_MAX_CONTEXT_CHARS", "2200"))

# 생성 컨텍스트에 포함할 최대 검색 결과 개수
AI_SUMMARY_MAX_ITEMS = int(os.getenv("AI_SUMMARY_MAX_ITEMS", "3"))

# 생성 모델 로드/추론 실패 시에도
# 전체 검색 API는 죽이지 않고 기존 검색 응답만 반환할지 여부
AI_SUMMARY_FAIL_OPEN = os.getenv("AI_SUMMARY_FAIL_OPEN", "true").lower() == "true"


# RAG(내부 문서 검색) 설정
# 문서를 나눌 chunk 크기
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "420"))

# chunk 간 겹치는 문자 수
# 문맥 단절을 줄이기 위해 일부 overlap 유지
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))

# 내부 검색 시 상위 몇 개 chunk를 가져올지 설정
RAG_INTERNAL_TOP_K = int(os.getenv("RAG_INTERNAL_TOP_K", "4"))

# 내부 검색 결과 최소 유사도 점수 기준
# 이 값보다 낮으면 관련성이 낮다고 보고 제외 가능
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.35"))


# 내부 지식 문서 JSON 파일 경로
# 기본값: <project_root>/app/data/internal_health_docs.json
INTERNAL_KNOWLEDGE_JSON_PATH = os.getenv(
    "INTERNAL_KNOWLEDGE_JSON_PATH",
    str(DATA_DIR / "internal_health_docs.json"),
)