# app/dependencies/auth_dependencies.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from collections.abc import Callable  # 용도: 의존성 팩토리 타입 힌트
from typing import Any  # 용도: 공용 타입 힌트

from fastapi import Depends  # 용도: FastAPI 의존성 주입
from fastapi import HTTPException  # 용도: HTTP 예외 반환
from fastapi import status  # 용도: HTTP 상태코드 상수
from fastapi.security import HTTPAuthorizationCredentials  # 용도: Bearer 인증정보 타입
from fastapi.security import HTTPBearer  # 용도: Authorization Bearer 파싱

from app.core.role_permissions import has_role  # 용도: 역할 허용 여부 검증
from app.core.roles import ROLE_ADMIN  # 용도: admin 역할 상수
from app.core.roles import ROLE_OPERATOR  # 용도: operator 역할 상수
from app.core.roles import ROLE_SUPERUSER  # 용도: superuser 역할 상수
from app.services.auth_service import get_user_from_access_token  # 용도: access token 사용자 조회

_http_bearer = HTTPBearer(auto_error=False)


def _extract_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    token = str(credentials.credentials or "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
) -> dict[str, Any]:
    token = _extract_bearer_token(credentials)

    try:
        return get_user_from_access_token(token)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error


def require_roles(*allowed_roles: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _dependency(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if not has_role(current_user.get("role"), allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

        return current_user

    return _dependency


def require_operator_or_admin(
    current_user: dict[str, Any] = Depends(
        require_roles(
            ROLE_OPERATOR,
            ROLE_ADMIN,
            ROLE_SUPERUSER,
        ),
    ),
) -> dict[str, Any]:
    return current_user


def require_admin_or_superuser(
    current_user: dict[str, Any] = Depends(
        require_roles(
            ROLE_ADMIN,
            ROLE_SUPERUSER,
        ),
    ),
) -> dict[str, Any]:
    return current_user


def require_superuser(
    current_user: dict[str, Any] = Depends(
        require_roles(
            ROLE_SUPERUSER,
        ),
    ),
) -> dict[str, Any]:
    return current_user