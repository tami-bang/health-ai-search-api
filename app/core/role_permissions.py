# app/core/role_permissions.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from app.core.roles import ALL_ROLES  # 용도: 전체 역할 목록 조회
from app.core.roles import ROLE_ADMIN  # 용도: admin 역할 상수
from app.core.roles import ROLE_MEMBER  # 용도: member 역할 상수
from app.core.roles import ROLE_OPERATOR  # 용도: operator 역할 상수
from app.core.roles import ROLE_SUPERUSER  # 용도: superuser 역할 상수

PERMISSION_VIEW_SELF = "view:self"
PERMISSION_UPDATE_SELF = "update:self"
PERMISSION_CHANGE_PASSWORD = "auth:change_password"

PERMISSION_ADMIN_USER_READ = "admin:user:read"
PERMISSION_ADMIN_USER_CREATE = "admin:user:create"
PERMISSION_ADMIN_USER_ROLE_UPDATE = "admin:user:role:update"
PERMISSION_ADMIN_USER_STATUS_UPDATE = "admin:user:status:update"
PERMISSION_ADMIN_POLICY_READ = "admin:policy:read"
PERMISSION_ADMIN_POLICY_UPDATE = "admin:policy:update"
PERMISSION_ADMIN_AUDIT_READ = "admin:audit:read"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_MEMBER: {
        PERMISSION_VIEW_SELF,
        PERMISSION_UPDATE_SELF,
        PERMISSION_CHANGE_PASSWORD,
    },
    ROLE_OPERATOR: {
        PERMISSION_VIEW_SELF,
        PERMISSION_UPDATE_SELF,
        PERMISSION_CHANGE_PASSWORD,
        PERMISSION_ADMIN_USER_READ,
        PERMISSION_ADMIN_AUDIT_READ,
    },
    ROLE_ADMIN: {
        PERMISSION_VIEW_SELF,
        PERMISSION_UPDATE_SELF,
        PERMISSION_CHANGE_PASSWORD,
        PERMISSION_ADMIN_USER_READ,
        PERMISSION_ADMIN_USER_CREATE,
        PERMISSION_ADMIN_USER_ROLE_UPDATE,
        PERMISSION_ADMIN_USER_STATUS_UPDATE,
        PERMISSION_ADMIN_POLICY_READ,
        PERMISSION_ADMIN_POLICY_UPDATE,
        PERMISSION_ADMIN_AUDIT_READ,
    },
    ROLE_SUPERUSER: {
        PERMISSION_VIEW_SELF,
        PERMISSION_UPDATE_SELF,
        PERMISSION_CHANGE_PASSWORD,
        PERMISSION_ADMIN_USER_READ,
        PERMISSION_ADMIN_USER_CREATE,
        PERMISSION_ADMIN_USER_ROLE_UPDATE,
        PERMISSION_ADMIN_USER_STATUS_UPDATE,
        PERMISSION_ADMIN_POLICY_READ,
        PERMISSION_ADMIN_POLICY_UPDATE,
        PERMISSION_ADMIN_AUDIT_READ,
    },
}


def normalize_role(role: str | None) -> str:
    cleaned_role = str(role or "").strip().lower()

    if cleaned_role in ALL_ROLES:
        return cleaned_role

    return ROLE_MEMBER


def is_valid_role(role: str | None) -> bool:
    return str(role or "").strip().lower() in ALL_ROLES


def get_role_permissions(role: str | None) -> set[str]:
    normalized_role = normalize_role(role)
    return ROLE_PERMISSIONS.get(normalized_role, set())


def has_permission(role: str | None, permission: str) -> bool:
    if not permission:
        return False

    return permission in get_role_permissions(role)


def has_role(
    role: str | None,
    allowed_roles: list[str] | tuple[str, ...] | set[str],
) -> bool:
    normalized_role = normalize_role(role)
    normalized_allowed_roles = {
        normalize_role(item)
        for item in allowed_roles
    }
    return normalized_role in normalized_allowed_roles