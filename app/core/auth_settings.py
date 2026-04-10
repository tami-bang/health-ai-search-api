# app/core/auth_settings.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import os  # 용도: 환경변수 조회

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "10080"))
EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", "60"))
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))

DEV_EXPOSE_AUTH_TOKENS = os.getenv("DEV_EXPOSE_AUTH_TOKENS", "true").lower() == "true"
AUTH_REQUIRE_EMAIL_VERIFICATION = os.getenv("AUTH_REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"

USERNAME_MIN_LENGTH = int(os.getenv("USERNAME_MIN_LENGTH", "4"))
USERNAME_MAX_LENGTH = int(os.getenv("USERNAME_MAX_LENGTH", "30"))
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
PASSWORD_MAX_LENGTH = int(os.getenv("PASSWORD_MAX_LENGTH", "64"))
FULL_NAME_MAX_LENGTH = int(os.getenv("FULL_NAME_MAX_LENGTH", "50"))