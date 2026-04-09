# app/core/role_permissions.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

ROLE_SUPERUSER = "superuser"
ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_MEMBER = "member"

ROLE_HIERARCHY: dict[str, int] = {
    ROLE_MEMBER: 10,
    ROLE_OPERATOR: 20,
    ROLE_ADMIN: 30,
    ROLE_SUPERUSER: 40,
}

ROLE_PERMISSION_MAP: dict[str, set[str]] = {
    ROLE_MEMBER: {
        "search:use",
        "triage:use",
        "profile:read",
        "profile:update",
    },
    ROLE_OPERATOR: {
        "search:use",
        "triage:use",
        "profile:read",
        "profile:update",
        "audit:read",
        "policy:read",
        "member:read",
    },
    ROLE_ADMIN: {
        "search:use",
        "triage:use",
        "profile:read",
        "profile:update",
        "audit:read",
        "policy:read",
        "policy:update",
        "member:read",
        "member:create_operator",
        "member:update_role",
        "member:activate",
        "member:deactivate",
    },
    ROLE_SUPERUSER: {
        "search:use",
        "triage:use",
        "profile:read",
        "profile:update",
        "audit:read",
        "policy:read",
        "policy:update",
        "member:read",
        "member:create_operator",
        "member:update_role",
        "member:activate",
        "member:deactivate",
        "member:manage_superuser",
    },
}


def is_valid_role(role: str) -> bool:
    return str(role or "").strip().lower() in ROLE_PERMISSION_MAP


def normalize_role(role: str) -> str:
    return str(role or "").strip().lower()


def get_permissions_by_role(role: str) -> set[str]:
    normalized_role = normalize_role(role)
    return set(ROLE_PERMISSION_MAP.get(normalized_role, set()))


def has_permission(role: str, permission_code: str) -> bool:
    permissions = get_permissions_by_role(role)
    return permission_code in permissions


def is_same_or_higher_role(actor_role: str, target_role: str) -> bool:
    actor_level = ROLE_HIERARCHY.get(normalize_role(actor_role), 0)
    target_level = ROLE_HIERARCHY.get(normalize_role(target_role), 0)
    return actor_level >= target_level