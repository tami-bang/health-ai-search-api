from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from contextlib import asynccontextmanager  # 용도: FastAPI lifespan 처리

from fastapi import FastAPI  # 용도: FastAPI 앱 생성
from fastapi import Request  # 용도: 예외 핸들러 요청 객체
from fastapi.middleware.cors import CORSMiddleware  # 용도: 프론트엔드 CORS 허용
from fastapi.responses import JSONResponse  # 용도: 예외 응답 생성

from app.api.admin_router import router as admin_router  # 용도: 관리자 라우터 등록
from app.api.auth_router import router as auth_router  # 용도: auth 라우터 등록
from app.api.triage_router import router as triage_router  # 용도: triage 라우터 등록
from app.core.exceptions import AppException  # 용도: 앱 공통 예외 처리
from app.core.logging_config import configure_logging  # 용도: 공통 로그 초기화
from app.core.settings import APP_NAME  # 용도: 앱 이름 설정
from app.repositories.auth_repository import init_auth_storage  # 용도: auth 저장소 초기화
from app.schemas import SearchRequest  # 용도: 검색 요청 스키마
from app.services.health_status_service import build_live_status  # 용도: 라이브 상태 응답 생성
from app.services.health_status_service import build_metrics_status  # 용도: 메트릭 상태 응답 생성
from app.services.health_status_service import build_ready_status  # 용도: 준비 상태 응답 생성
from app.services.symptom_search_service import search_symptom  # 용도: 증상 검색 서비스
from app.services.symptom_search_service import startup_search_dependencies  # 용도: 검색 의존성 초기화


# 유지보수 포인트:
# - 프론트엔드 주소가 추가되면 이 리스트만 수정하면 된다.
# - localhost / 127.0.0.1 둘 다 허용해 개발 환경 차이를 줄인다.
ALLOWED_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_search_dependencies()
    init_auth_storage()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        lifespan=lifespan,
    )

    configure_cors(app)
    register_exception_handlers(app)
    register_routers(app)
    register_health_routes(app)
    register_search_routes(app)

    return app


def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.message,
                "error_code": exc.error_code,
            },
        )


def register_routers(app: FastAPI) -> None:
    app.include_router(triage_router)
    app.include_router(auth_router)
    app.include_router(admin_router)


def register_health_routes(app: FastAPI) -> None:
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


def register_search_routes(app: FastAPI) -> None:
    @app.post("/search")
    def search(request: SearchRequest) -> dict:
        return search_symptom(
            query=request.query,
            include_summary=request.include_summary,
            force_summary=False,
        )

    @app.post("/search/summary")
    def search_with_summary(request: SearchRequest) -> dict:
        return search_symptom(
            query=request.query,
            include_summary=True,
            force_summary=True,
        )


app = create_app()