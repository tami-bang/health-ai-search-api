# app/core/security.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import hashlib  # 용도: 토큰 해시 처리
import secrets  # 용도: 랜덤 토큰 생성
from datetime import UTC  # 용도: UTC 시간대 고정
from datetime import datetime  # 용도: 만료 시각 계산
from datetime import timedelta  # 용도: 토큰 만료 시간 계산
from typing import Any  # 용도: payload 타입 힌트

from jose import JWTError  # 용도: JWT 예외 처리
from jose import jwt  # 용도: JWT 인코딩/디코딩
from passlib.context import CryptContext  # 용도: 비밀번호 해시 처리

from app.core.auth_settings import JWT_ALGORITHM  # 용도: JWT 알고리즘 설정
from app.core.auth_settings import JWT_SECRET_KEY  # 용도: JWT 시크릿 키 설정

_PASSWORD_CONTEXT = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def from_iso(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def hash_password(password: str) -> str:
    return _PASSWORD_CONTEXT.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False

    try:
        return _PASSWORD_CONTEXT.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_jwt_token(
    subject: str,
    token_type: str,
    expires_minutes: int,
    extra_payload: dict[str, Any] | None = None,
) -> str:
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }

    if extra_payload:
        payload.update(extra_payload)

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_lookup_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mask_username(username: str) -> str:
    cleaned = str(username or "").strip()
    if len(cleaned) <= 2:
        return cleaned[:1] + "*" if cleaned else ""

    return cleaned[:2] + ("*" * max(1, len(cleaned) - 2))