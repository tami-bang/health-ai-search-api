# app/core/auth_settings.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import os  # 용도: 환경변수 조회
from pathlib import Path  # 용도: 파일 경로 처리

from app.core.settings import DATA_DIR  # 용도: 공통 데이터 디렉토리 재사용

AUTH_DATA_DIR = Path(DATA_DIR) / "auth"
AUTH_USERS_JSON_PATH = AUTH_DATA_DIR / "users.json"
AUTH_STATE_JSON_PATH = AUTH_DATA_DIR / "auth_state.json"
AUTH_POLICIES_JSON_PATH = AUTH_DATA_DIR / "admin_policies.json"
AUTH_AUDIT_JSON_PATH = AUTH_DATA_DIR / "audit_logs.json"

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-in-production-very-strong-secret-key",
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"),
)
EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", "1440"),
)

USERNAME_MIN_LENGTH = int(os.getenv("USERNAME_MIN_LENGTH", "4"))
USERNAME_MAX_LENGTH = int(os.getenv("USERNAME_MAX_LENGTH", "30"))
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
PASSWORD_MAX_LENGTH = int(os.getenv("PASSWORD_MAX_LENGTH", "64"))
FULL_NAME_MAX_LENGTH = int(os.getenv("FULL_NAME_MAX_LENGTH", "50"))

DEV_EXPOSE_AUTH_TOKENS = os.getenv("DEV_EXPOSE_AUTH_TOKENS", "true").lower() == "true"
AUTH_REQUIRE_EMAIL_VERIFICATION = os.getenv(
    "AUTH_REQUIRE_EMAIL_VERIFICATION",
    "false",
).lower() == "true"

DEFAULT_SUPERUSER_USERNAME = os.getenv("DEFAULT_SUPERUSER_USERNAME", "superadmin")
DEFAULT_SUPERUSER_EMAIL = os.getenv("DEFAULT_SUPERUSER_EMAIL", "superadmin@example.com")
DEFAULT_SUPERUSER_PASSWORD = os.getenv("DEFAULT_SUPERUSER_PASSWORD", "ChangeMe123!")