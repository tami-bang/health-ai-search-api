# app/api/admin_router.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from fastapi import APIRouter  # 용도: 관리자 라우터 등록
from fastapi import Depends  # 용도: 인증/권한 의존성 주입
from fastapi import Query  # 용도: 쿼리 파라미터 선언

from app.dependencies.auth_dependencies import require_admin_or_superuser  # 용도: admin 이상 접근 제한
from app.dependencies.auth_dependencies import require_operator_or_admin  # 용도: operator 이상 접근 제한
from app.schemas import AdminCreateUserRequest  # 용도: 관리자 사용자 생성 요청 스키마
from app.schemas import AdminPolicyUpdateRequest  # 용도: 관리자 정책 수정 요청 스키마
from app.schemas import AdminUpdateUserRoleRequest  # 용도: 관리자 역할 변경 요청 스키마
from app.schemas import AdminUpdateUserStatusRequest  # 용도: 관리자 사용자 상태 변경 요청 스키마
from app.services.admin_service import change_admin_user_role  # 용도: 관리자 역할 변경 서비스
from app.services.admin_service import change_admin_user_status  # 용도: 관리자 상태 변경 서비스
from app.services.admin_service import create_admin_user  # 용도: 관리자 사용자 생성 서비스
from app.services.admin_service import get_admin_audit_logs  # 용도: 감사 로그 조회 서비스
from app.services.admin_service import get_admin_policies  # 용도: 관리자 정책 조회 서비스
from app.services.admin_service import get_admin_user_list  # 용도: 관리자 사용자 목록 조회 서비스
from app.services.admin_service import update_admin_policies  # 용도: 관리자 정책 수정 서비스

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/users")
def list_users(
    current_user: dict = Depends(require_operator_or_admin),
) -> dict:
    return get_admin_user_list()


@router.post("/users")
def create_user(
    payload: AdminCreateUserRequest,
    current_user: dict = Depends(require_admin_or_superuser),
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
def update_user_role(
    target_user_id: str,
    payload: AdminUpdateUserRoleRequest,
    current_user: dict = Depends(require_admin_or_superuser),
) -> dict:
    return change_admin_user_role(
        actor_user=current_user,
        target_user_id=target_user_id,
        new_role=payload.role,
    )


@router.patch("/users/{target_user_id}/status")
def update_user_status(
    target_user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user: dict = Depends(require_admin_or_superuser),
) -> dict:
    return change_admin_user_status(
        actor_user=current_user,
        target_user_id=target_user_id,
        is_active=payload.is_active,
    )


@router.get("/policies")
def read_admin_policies(
    current_user: dict = Depends(require_operator_or_admin),
) -> dict:
    return get_admin_policies()


@router.patch("/policies")
def patch_admin_policies(
    payload: AdminPolicyUpdateRequest,
    current_user: dict = Depends(require_admin_or_superuser),
) -> dict:
    return update_admin_policies(
        actor_user=current_user,
        updates=payload.updates,
    )


@router.get("/audit-logs")
def read_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None),
    actor_username: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    current_user: dict = Depends(require_operator_or_admin),
) -> dict:
    return get_admin_audit_logs(
        limit=limit,
        action=action,
        actor_username=actor_username,
        target_id=target_id,
    )