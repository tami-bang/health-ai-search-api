# app/services/admin_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from typing import Any  # 용도: 공용 타입 힌트

from app.core.error_codes import ADMIN_POLICY_NOT_FOUND  # 용도: 정책 미존재 코드
from app.core.exceptions import AppException  # 용도: 앱 예외 처리
from app.repositories.auth_repository import load_admin_policies  # 용도: 정책 로드
from app.repositories.auth_repository import save_admin_policies  # 용도: 정책 저장
from app.services.audit_service import create_audit_log  # 용도: 감사 로그 저장
from app.services.audit_service import get_audit_logs  # 용도: 감사 로그 조회
from app.services.auth_service import create_operator_account  # 용도: 운영자 계정 생성
from app.services.auth_service import list_public_users  # 용도: 사용자 목록 조회
from app.services.auth_service import set_user_active_status  # 용도: 사용자 활성 상태 변경
from app.services.auth_service import update_user_role  # 용도: 역할 변경


def get_admin_policies() -> dict[str, Any]:
    return load_admin_policies()


def update_admin_policies(
    actor_user: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    policy_bundle = load_admin_policies()
    policies = dict(policy_bundle.get("policies", {}))

    for key, value in updates.items():
        if key not in policies:
            raise AppException(
                message=f"Policy not found: {key}",
                error_code=ADMIN_POLICY_NOT_FOUND,
                status_code=404,
            )
        policies[key] = value

    save_admin_policies(policies)

    create_audit_log(
        actor_user_id=actor_user.get("user_id"),
        actor_username=actor_user.get("username"),
        action="policy_updated",
        target_type="policy",
        target_id="service_policies",
        detail={
            "updates": updates,
        },
    )

    return {
        "message": "Policies updated.",
        "policies": policies,
    }


def get_admin_dashboard() -> dict[str, Any]:
    users = list_public_users()
    policies = load_admin_policies()
    logs = get_audit_logs(limit=20)

    role_counts: dict[str, int] = {}
    active_user_count = 0

    for user in users:
        role = str(user.get("role") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

        if bool(user.get("is_active")):
            active_user_count += 1

    return {
        "summary": {
            "total_users": len(users),
            "active_users": active_user_count,
            "role_counts": role_counts,
        },
        "policies": policies.get("policies", {}),
        "recent_audit_logs": logs,
    }


def list_admin_users() -> dict[str, Any]:
    return {
        "users": list_public_users(),
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
    return create_operator_account(
        actor_user=actor_user,
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
        full_name=full_name,
        role=role,
    )


def change_admin_user_role(
    actor_user: dict[str, Any],
    target_user_id: str,
    new_role: str,
) -> dict[str, Any]:
    return update_user_role(
        actor_user=actor_user,
        target_user_id=target_user_id,
        new_role=new_role,
    )


def change_admin_user_active_status(
    actor_user: dict[str, Any],
    target_user_id: str,
    is_active: bool,
) -> dict[str, Any]:
    return set_user_active_status(
        actor_user=actor_user,
        target_user_id=target_user_id,
        is_active=is_active,
    )


def list_audit_log_items(limit: int = 100) -> dict[str, Any]:
    return {
        "logs": get_audit_logs(limit=limit),
    }