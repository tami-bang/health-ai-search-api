# app/services/audit_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import uuid  # 용도: 감사 로그 ID 생성
from typing import Any  # 용도: 공용 타입 힌트

from app.core.security import to_iso  # 용도: 시간 문자열 변환
from app.core.security import utc_now  # 용도: 현재 시각 생성
from app.repositories.auth_repository import append_audit_log  # 용도: 감사 로그 저장
from app.repositories.auth_repository import load_audit_logs  # 용도: 감사 로그 조회


def create_audit_log(
    actor_user_id: str | None,
    actor_username: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    log_item = {
        "audit_id": f"audit-{uuid.uuid4().hex}",
        "actor_user_id": actor_user_id,
        "actor_username": actor_username,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail or {},
        "created_at": to_iso(utc_now()),
    }
    return append_audit_log(log_item)


def get_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    logs = load_audit_logs()
    ordered_logs = sorted(
        logs,
        key=lambda item: str(item.get("created_at") or ""),
        reverse=True,
    )
    return ordered_logs[: max(1, limit)]