# app/main.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from contextlib import asynccontextmanager  # FastAPI lifespan 처리

from fastapi import FastAPI  # FastAPI 앱 생성
from pydantic import BaseModel  # 요청 스키마 정의
from pydantic import Field  # 요청 필드 제약 정의

from app.core.logging_config import configure_logging  # 공통 로그 초기화
from app.core.settings import APP_NAME  # 앱 이름 설정
from app.services.health_status_service import build_live_status  # 라이브 상태 응답 생성
from app.services.health_status_service import build_metrics_status  # 메트릭 상태 응답 생성
from app.services.health_status_service import build_ready_status  # 준비 상태 응답 생성
from app.services.symptom_search_service import search_symptom  # 증상 검색 서비스
from app.services.symptom_search_service import startup_search_dependencies  # 의존성 초기화
from app.services.triage_service import evaluate_triage_level  # triage 단독 평가
from app.services.language_utils import detect_query_language  # 질의 언어 감지
from app.services.translator import translate_text  # 한국어 질의 내부 번역


configure_logging()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="증상 질의")
    include_summary: bool = Field(False, description="AI 요약 포함 여부")


class TriageRequest(BaseModel):
    query: str = Field(..., min_length=2, description="증상 질의")


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_search_dependencies()
    yield


app = FastAPI(
    title=APP_NAME,
    lifespan=lifespan,
)


@app.get("/")
def root() -> dict:
    return {"message": f"{APP_NAME} is running"}


@app.get("/health")
def health() -> dict:
    return build_live_status()


@app.get("/ready")
def ready() -> dict:
    return build_ready_status()


@app.get("/metrics")
def metrics() -> dict:
    return build_metrics_status()


@app.post("/search")
def search(request: SearchRequest) -> dict:
    return search_symptom(
        query=request.query,
        include_summary=request.include_summary,
    )


@app.post("/search/summary")
def search_with_summary(request: SearchRequest) -> dict:
    return search_symptom(
        query=request.query,
        include_summary=True,
    )


@app.post("/triage")
def triage(request: TriageRequest) -> dict:
    detected_language = detect_query_language(request.query)
    internal_query = request.query

    if detected_language == "ko":
        translated = translate_text(
            request.query,
            target_lang="en",
            source_lang="auto",
        )
        internal_query = translated.strip() if translated and translated.strip() else request.query

    triage_level, triage_message = evaluate_triage_level(
        query=request.query,
        internal_query=internal_query,
        normalized_query=internal_query,
        detected_language=detected_language,
    )

    return {
        "query": request.query,
        "detected_language": detected_language,
        "triage_level": triage_level,
        "triage_message": triage_message,
    }