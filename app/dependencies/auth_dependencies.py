# app/dependencies/auth_dependencies.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from collections.abc import Callable  # 용도: 의존성 팩토리 타입 힌트

from fastapi import Depends  # 용도: 의존성 주입
from fastapi import Header  # 용도: Authorization 헤더 읽기

from app.core.error_codes import AUTH_INVALID_TOKEN  # 용도: 토큰 오류 코드
from app.core.error_codes import AUTH_PERMISSION_DENIED  # 용도: 권한 부족 오류 코드
from app.core.exceptions import AuthException  # 용도: 인증 예외
from app.core.exceptions import PermissionDeniedException  # 용도: 권한 예외
from app.core.role_permissions import has_permission  # 용도: 권한 체크
from app.services.auth_service import get_user_from_access_token  # 용도: access token 사용자 조회


def _extract_bearer_token(authorization: str | None) -> str:
    cleaned_authorization = str(authorization or "").strip()
    prefix = "bearer "

    if not cleaned_authorization.lower().startswith(prefix):
        raise AuthException(
            message="Authorization bearer token is required.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    token = cleaned_authorization[len(prefix):].strip()
    if not token:
        raise AuthException(
            message="Access token is required.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    return token


def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    token = _extract_bearer_token(authorization)
    return get_user_from_access_token(token)


def require_permission(permission_code: str) -> Callable:
    def _permission_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = str(current_user.get("role") or "")

        if not has_permission(user_role, permission_code):
            raise PermissionDeniedException(
                message="Permission denied.",
                error_code=AUTH_PERMISSION_DENIED,
                status_code=403,
            )

        return current_user

    return _permission_dependency