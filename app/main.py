# app/main.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from contextlib import asynccontextmanager  # FastAPI lifespan 처리

from fastapi import FastAPI  # FastAPI 앱 생성

from app.api.triage_router import router as triage_router  # triage 라우터 등록
from app.core.logging_config import configure_logging  # 공통 로그 초기화
from app.core.settings import APP_NAME  # 앱 이름 설정
from app.schemas import SearchRequest  # 검색 요청 스키마
from app.services.health_status_service import build_live_status  # 라이브 상태 응답 생성
from app.services.health_status_service import build_metrics_status  # 메트릭 상태 응답 생성
from app.services.health_status_service import build_ready_status  # 준비 상태 응답 생성
from app.services.symptom_search_service import search_symptom  # 증상 검색 서비스
from app.services.symptom_search_service import startup_search_dependencies  # 의존성 초기화

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_search_dependencies()
    yield


app = FastAPI(
    title=APP_NAME,
    lifespan=lifespan,
)

app.include_router(triage_router)


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
        force_summary=False,
    )


@app.post("/search/summary")
def search_with_summary(request: SearchRequest) -> dict:
    # /search/summary 는 body 값과 무관하게 summary 생성을 강제한다.
    return search_symptom(
        query=request.query,
        include_summary=True,
        force_summary=True,
    )