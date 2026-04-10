# app/services/admin_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from typing import Any  # 용도: 공용 타입 힌트

from app.core.role_permissions import is_valid_role  # 용도: 역할 유효성 검증
from app.core.roles import ROLE_ADMIN  # 용도: admin 역할 상수
from app.core.roles import ROLE_OPERATOR  # 용도: operator 역할 상수
from app.core.roles import ROLE_SUPERUSER  # 용도: superuser 역할 상수
from app.repositories.auth_repository import load_admin_policies  # 용도: 관리자 정책 조회
from app.repositories.auth_repository import save_admin_policies  # 용도: 관리자 정책 저장
from app.services.audit_service import create_audit_log  # 용도: 감사 로그 기록
from app.services.audit_service import list_audit_logs  # 용도: 감사 로그 조회
from app.services.auth_service import create_operator_account  # 용도: 관리자 생성 사용자 등록 재사용
from app.services.auth_service import list_public_users  # 용도: 사용자 목록 조회 재사용
from app.services.auth_service import set_user_active_status  # 용도: 사용자 상태 변경 재사용
from app.services.auth_service import update_user_role  # 용도: 사용자 역할 변경 재사용


def _validate_target_role(role: str) -> str:
    cleaned_role = str(role or "").strip().lower()

    if not is_valid_role(cleaned_role):
        raise ValueError("Invalid role.")

    return cleaned_role


def _ensure_actor_can_create_role(
    actor_user: dict[str, Any],
    target_role: str,
) -> None:
    actor_role = str(actor_user.get("role") or "").strip().lower()

    if actor_role == ROLE_OPERATOR:
        raise ValueError("Operator cannot create users.")

    if actor_role == ROLE_ADMIN and target_role == ROLE_SUPERUSER:
        raise ValueError("Admin cannot create superuser.")


def _ensure_actor_can_assign_role(
    actor_user: dict[str, Any],
    target_role: str,
) -> None:
    actor_role = str(actor_user.get("role") or "").strip().lower()

    if actor_role == ROLE_ADMIN and target_role == ROLE_SUPERUSER:
        raise ValueError("Admin cannot assign superuser role.")


def get_admin_user_list() -> dict[str, Any]:
    users = list_public_users()

    return {
        "count": len(users),
        "users": users,
    }


def create_admin_user(
    actor_user: dict[str, Any],
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    full_name: str | None,
    role: str,
) -> dict[str, Any]:
    validated_role = _validate_target_role(role)
    _ensure_actor_can_create_role(
        actor_user=actor_user,
        target_role=validated_role,
    )

    return create_operator_account(
        actor_user=actor_user,
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
        full_name=full_name,
        role=validated_role,
    )


def change_admin_user_role(
    actor_user: dict[str, Any],
    target_user_id: str,
    new_role: str,
) -> dict[str, Any]:
    validated_role = _validate_target_role(new_role)
    _ensure_actor_can_assign_role(
        actor_user=actor_user,
        target_role=validated_role,
    )

    return update_user_role(
        actor_user=actor_user,
        target_user_id=target_user_id,
        new_role=validated_role,
    )


def change_admin_user_status(
    actor_user: dict[str, Any],
    target_user_id: str,
    is_active: bool,
) -> dict[str, Any]:
    return set_user_active_status(
        actor_user=actor_user,
        target_user_id=target_user_id,
        is_active=is_active,
    )


def get_admin_policies() -> dict[str, Any]:
    return load_admin_policies()


def update_admin_policies(
    actor_user: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    current_policies = load_admin_policies().get("policies", {})
    merged_policies = dict(current_policies)
    merged_policies.update(dict(updates or {}))

    saved_result = save_admin_policies(merged_policies)

    create_audit_log(
        actor_user_id=actor_user.get("user_id"),
        actor_username=actor_user.get("username"),
        action="admin_policy_updated",
        target_type="policy",
        target_id="admin_policies",
        detail={
            "updated_keys": sorted(list(dict(updates or {}).keys())),
        },
    )

    return saved_result


def get_admin_audit_logs(
    limit: int = 100,
    action: str | None = None,
    actor_username: str | None = None,
    target_id: str | None = None,
) -> dict[str, Any]:
    logs = list_audit_logs(
        limit=limit,
        action=action,
        actor_username=actor_username,
        target_id=target_id,
    )

    return {
        "count": len(logs),
        "logs": logs,
    }