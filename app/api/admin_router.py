# app/api/admin_router.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from fastapi import APIRouter  # 용도: 관리자 라우터 등록
from fastapi import Depends  # 용도: 인증 의존성 주입

from app.dependencies.auth_dependencies import require_permission  # 용도: 권한 검증 의존성
from app.schemas import AdminCreateUserRequest  # 용도: 관리자 생성 요청 스키마
from app.schemas import AdminPolicyUpdateRequest  # 용도: 정책 변경 요청 스키마
from app.schemas import AdminUpdateUserRoleRequest  # 용도: 역할 변경 요청 스키마
from app.schemas import AdminUpdateUserStatusRequest  # 용도: 활성 상태 변경 요청 스키마
from app.services.admin_service import change_admin_user_active_status  # 용도: 사용자 상태 변경 서비스
from app.services.admin_service import change_admin_user_role  # 용도: 사용자 역할 변경 서비스
from app.services.admin_service import create_admin_user  # 용도: 관리자 계정 생성 서비스
from app.services.admin_service import get_admin_dashboard  # 용도: 운영 대시보드 서비스
from app.services.admin_service import get_admin_policies  # 용도: 정책 조회 서비스
from app.services.admin_service import list_admin_users  # 용도: 사용자 목록 조회 서비스
from app.services.admin_service import list_audit_log_items  # 용도: 감사 로그 조회 서비스
from app.services.admin_service import update_admin_policies  # 용도: 정책 수정 서비스

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/dashboard")
def admin_dashboard(
    current_user: dict = Depends(require_permission("audit:read")),
) -> dict:
    return get_admin_dashboard()


@router.get("/users")
def admin_users(
    current_user: dict = Depends(require_permission("member:read")),
) -> dict:
    return list_admin_users()


@router.post("/users")
def admin_create_user(
    payload: AdminCreateUserRequest,
    current_user: dict = Depends(require_permission("member:create_operator")),
) -> dict:
    return create_admin_user(
        actor_user=current_user,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        full_name=payload.full_name,
        role=payload.role,
    )


@router.patch("/users/{target_user_id}/role")
def admin_change_role(
    target_user_id: str,
    payload: AdminUpdateUserRoleRequest,
    current_user: dict = Depends(require_permission("member:update_role")),
) -> dict:
    return change_admin_user_role(
        actor_user=current_user,
        target_user_id=target_user_id,
        new_role=payload.role,
    )


@router.patch("/users/{target_user_id}/status")
def admin_change_status(
    target_user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user: dict = Depends(require_permission("member:deactivate")),
) -> dict:
    return change_admin_user_active_status(
        actor_user=current_user,
        target_user_id=target_user_id,
        is_active=payload.is_active,
    )


@router.get("/policies")
def admin_policies(
    current_user: dict = Depends(require_permission("policy:read")),
) -> dict:
    return get_admin_policies()


@router.patch("/policies")
def admin_update_policies(
    payload: AdminPolicyUpdateRequest,
    current_user: dict = Depends(require_permission("policy:update")),
) -> dict:
    return update_admin_policies(
        actor_user=current_user,
        updates=payload.updates,
    )


@router.get("/audit-logs")
def admin_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(require_permission("audit:read")),
) -> dict:
    return list_audit_log_items(limit=limit)