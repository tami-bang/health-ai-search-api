# app/services/audit_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import uuid  # 용도: 감사 로그 ID 생성
from typing import Any  # 용도: 공용 타입 힌트

from app.core.security import to_iso  # 용도: UTC 시간 문자열 변환
from app.core.security import utc_now  # 용도: 현재 UTC 시간 조회
from app.repositories.auth_repository import append_audit_log  # 용도: 감사 로그 저장
from app.repositories.auth_repository import load_audit_logs  # 용도: 감사 로그 목록 조회


def create_audit_log(
    actor_user_id: str | None,
    actor_username: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit_log = {
        "audit_log_id": f"audit-{uuid.uuid4().hex}",
        "actor_user_id": str(actor_user_id or ""),
        "actor_username": str(actor_username or ""),
        "action": str(action or ""),
        "target_type": str(target_type or ""),
        "target_id": str(target_id or ""),
        "detail": dict(detail or {}),
        "created_at": to_iso(utc_now()),
    }
    append_audit_log(audit_log)
    return audit_log


def _match_exact_filter(value: str, expected: str | None) -> bool:
    if not expected:
        return True

    return str(value or "") == str(expected or "")


def _match_contains_filter(value: str, keyword: str | None) -> bool:
    if not keyword:
        return True

    return str(keyword).lower() in str(value or "").lower()


def list_audit_logs(
    limit: int = 100,
    action: str | None = None,
    actor_username: str | None = None,
    target_id: str | None = None,
) -> list[dict[str, Any]]:
    reversed_logs = list(reversed(load_audit_logs()))
    filtered_logs: list[dict[str, Any]] = []

    for log_item in reversed_logs:
        if not _match_exact_filter(str(log_item.get("action", "")), action):
            continue

        if not _match_contains_filter(str(log_item.get("actor_username", "")), actor_username):
            continue

        if not _match_exact_filter(str(log_item.get("target_id", "")), target_id):
            continue

        filtered_logs.append(log_item)

        if len(filtered_logs) >= limit:
            break

    return filtered_logs