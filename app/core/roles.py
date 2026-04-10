# app/core/roles.py

from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

ROLE_MEMBER = "member"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"
ROLE_SUPERUSER = "superuser"

ALL_ROLES = (
    ROLE_MEMBER,
    ROLE_OPERATOR,
    ROLE_ADMIN,
    ROLE_SUPERUSER,
)