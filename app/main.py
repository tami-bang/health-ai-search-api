# main.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from fastapi import FastAPI  # FastAPI 앱 생성
from fastapi import Query  # 쿼리 파라미터 검증
from fastapi import Request  # 예외 응답용 요청 객체
from fastapi.responses import JSONResponse  # JSON 예외 응답 반환

from app.core.exceptions import AppException  # 앱 공통 예외
from app.core.logging_config import configure_logging  # 로깅 초기화
from app.core.settings import APP_NAME  # 앱 이름 설정
from app.schemas import HealthResponse  # 헬스체크 응답 스키마
from app.schemas import SearchResponse  # 검색 응답 스키마
from app.services.health_status_service import build_live_status  # live 상태 생성
from app.services.health_status_service import build_ready_status  # ready 상태 생성
from app.services.symptom_search_service import search_symptom  # 증상 검색 서비스 진입점
from app.services.symptom_search_service import startup_search_dependencies  # 서버 시작 시 의존성 초기화

configure_logging()

app = FastAPI(
    title=APP_NAME,
    description="RAG 기반 헬스 증상 검색 + 응급도 분기 + 추천 질문 API",
)

@app.on_event("startup")
def startup_event() -> None:
    startup_search_dependencies()

@app.exception_handler(AppException)
def handle_app_exception(request: Request, error: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "message": error.message,
            "error_code": error.error_code,
            "path": str(request.url.path),
        },
    )

@app.get("/", response_model=dict)
def root() -> dict[str, str]:
    return {"message": f"{APP_NAME} is running"}

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")

@app.get("/health/live", response_model=dict)
def health_live() -> dict:
    return build_live_status()

@app.get("/health/ready", response_model=dict)
def health_ready() -> dict:
    return build_ready_status()

@app.post("/search", response_model=SearchResponse, summary="증상 검색")
def search(
    query: str = Query(..., description="사용자 증상 질의"),
) -> SearchResponse:
    response_data = search_symptom(query)
    return SearchResponse(**response_data)