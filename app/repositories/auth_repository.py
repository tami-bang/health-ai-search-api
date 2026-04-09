# app/repositories/auth_repository.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import json  # 용도: JSON 파일 저장/로드
from pathlib import Path  # 용도: 파일 경로 처리
from typing import Any  # 용도: 공용 dict 타입 힌트

from app.core.auth_settings import AUTH_AUDIT_JSON_PATH  # 용도: 감사 로그 파일 경로
from app.core.auth_settings import AUTH_DATA_DIR  # 용도: 인증 데이터 디렉토리 경로
from app.core.auth_settings import AUTH_POLICIES_JSON_PATH  # 용도: 정책 파일 경로
from app.core.auth_settings import AUTH_STATE_JSON_PATH  # 용도: 인증 상태 파일 경로
from app.core.auth_settings import AUTH_USERS_JSON_PATH  # 용도: 사용자 파일 경로
from app.core.auth_settings import DEFAULT_SUPERUSER_EMAIL  # 용도: 기본 수퍼유저 이메일
from app.core.auth_settings import DEFAULT_SUPERUSER_PASSWORD  # 용도: 기본 수퍼유저 비밀번호
from app.core.auth_settings import DEFAULT_SUPERUSER_USERNAME  # 용도: 기본 수퍼유저 아이디
from app.core.policy_settings import DEFAULT_ADMIN_POLICIES  # 용도: 기본 정책값
from app.core.role_permissions import ROLE_SUPERUSER  # 용도: 기본 수퍼유저 역할
from app.core.security import hash_password  # 용도: 기본 계정 비밀번호 해시
from app.core.security import to_iso  # 용도: 시간 문자열 변환
from app.core.security import utc_now  # 용도: 현재 UTC 시각 생성


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_parent_dir(path)

    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except Exception:
            return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_parent_dir(path)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def _build_default_superuser() -> dict[str, Any]:
    now_iso = to_iso(utc_now())
    return {
        "user_id": "user-superadmin-001",
        "username": DEFAULT_SUPERUSER_USERNAME,
        "email": DEFAULT_SUPERUSER_EMAIL,
        "full_name": "System Superuser",
        "password_hash": hash_password(DEFAULT_SUPERUSER_PASSWORD),
        "role": ROLE_SUPERUSER,
        "is_active": True,
        "is_email_verified": True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_login_at": None,
    }


def _ensure_default_superuser_exists() -> None:
    data = _read_json(AUTH_USERS_JSON_PATH, {"users": []})
    users = data.get("users", [])

    if not isinstance(users, list):
        users = []

    has_superuser = False

    for user in users:
        if not isinstance(user, dict):
            continue

        username = str(user.get("username", "")).strip().lower()
        email = str(user.get("email", "")).strip().lower()
        role = str(user.get("role", "")).strip().lower()

        if (
            username == DEFAULT_SUPERUSER_USERNAME.strip().lower()
            or email == DEFAULT_SUPERUSER_EMAIL.strip().lower()
            or role == ROLE_SUPERUSER
        ):
            has_superuser = True
            break

    if has_superuser:
        _write_json(AUTH_USERS_JSON_PATH, {"users": users})
        return

    users.insert(0, _build_default_superuser())
    _write_json(AUTH_USERS_JSON_PATH, {"users": users})


def init_auth_storage() -> None:
    AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not AUTH_USERS_JSON_PATH.exists():
        _write_json(AUTH_USERS_JSON_PATH, {"users": []})

    _ensure_default_superuser_exists()

    if not AUTH_STATE_JSON_PATH.exists():
        _write_json(
            AUTH_STATE_JSON_PATH,
            {
                "refresh_sessions": [],
                "password_reset_tokens": [],
                "email_verification_tokens": [],
            },
        )

    if not AUTH_POLICIES_JSON_PATH.exists():
        _write_json(
            AUTH_POLICIES_JSON_PATH,
            {
                "policies": DEFAULT_ADMIN_POLICIES,
                "updated_at": to_iso(utc_now()),
            },
        )

    if not AUTH_AUDIT_JSON_PATH.exists():
        _write_json(AUTH_AUDIT_JSON_PATH, {"logs": []})


def load_users() -> list[dict[str, Any]]:
    data = _read_json(AUTH_USERS_JSON_PATH, {"users": []})
    users = data.get("users", [])

    if not isinstance(users, list):
        return []

    return users


def save_users(users: list[dict[str, Any]]) -> None:
    _write_json(AUTH_USERS_JSON_PATH, {"users": users})


def load_auth_state() -> dict[str, Any]:
    data = _read_json(
        AUTH_STATE_JSON_PATH,
        {
            "refresh_sessions": [],
            "password_reset_tokens": [],
            "email_verification_tokens": [],
        },
    )

    if not isinstance(data, dict):
        return {
            "refresh_sessions": [],
            "password_reset_tokens": [],
            "email_verification_tokens": [],
        }

    data.setdefault("refresh_sessions", [])
    data.setdefault("password_reset_tokens", [])
    data.setdefault("email_verification_tokens", [])
    return data


def save_auth_state(state: dict[str, Any]) -> None:
    save_data = {
        "refresh_sessions": state.get("refresh_sessions", []),
        "password_reset_tokens": state.get("password_reset_tokens", []),
        "email_verification_tokens": state.get("email_verification_tokens", []),
    }
    _write_json(AUTH_STATE_JSON_PATH, save_data)


def load_admin_policies() -> dict[str, Any]:
    data = _read_json(
        AUTH_POLICIES_JSON_PATH,
        {
            "policies": DEFAULT_ADMIN_POLICIES,
            "updated_at": None,
        },
    )

    if not isinstance(data, dict):
        return {
            "policies": dict(DEFAULT_ADMIN_POLICIES),
            "updated_at": None,
        }

    policies = data.get("policies", {})
    if not isinstance(policies, dict):
        policies = {}

    merged_policies = dict(DEFAULT_ADMIN_POLICIES)
    merged_policies.update(policies)

    return {
        "policies": merged_policies,
        "updated_at": data.get("updated_at"),
    }


def save_admin_policies(policies: dict[str, Any]) -> None:
    _write_json(
        AUTH_POLICIES_JSON_PATH,
        {
            "policies": policies,
            "updated_at": to_iso(utc_now()),
        },
    )


def load_audit_logs() -> list[dict[str, Any]]:
    data = _read_json(AUTH_AUDIT_JSON_PATH, {"logs": []})
    logs = data.get("logs", [])

    if not isinstance(logs, list):
        return []

    return logs


def append_audit_log(log_item: dict[str, Any]) -> dict[str, Any]:
    logs = load_audit_logs()
    logs.append(log_item)
    _write_json(AUTH_AUDIT_JSON_PATH, {"logs": logs})
    return log_item


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    for user in load_users():
        if str(user.get("user_id")) == str(user_id):
            return user
    return None


def find_user_by_username(username: str) -> dict[str, Any] | None:
    cleaned = str(username or "").strip().lower()

    for user in load_users():
        if str(user.get("username", "")).strip().lower() == cleaned:
            return user
    return None


def find_user_by_email(email: str) -> dict[str, Any] | None:
    cleaned = str(email or "").strip().lower()

    for user in load_users():
        if str(user.get("email", "")).strip().lower() == cleaned:
            return user
    return None


def find_user_by_login_id(login_id: str) -> dict[str, Any] | None:
    user = find_user_by_username(login_id)
    if user:
        return user

    return find_user_by_email(login_id)


def insert_user(new_user: dict[str, Any]) -> dict[str, Any]:
    users = load_users()
    users.append(new_user)
    save_users(users)
    return new_user


def update_user(updated_user: dict[str, Any]) -> dict[str, Any]:
    users = load_users()

    for index, user in enumerate(users):
        if str(user.get("user_id")) == str(updated_user.get("user_id")):
            users[index] = updated_user
            save_users(users)
            return updated_user

    users.append(updated_user)
    save_users(users)
    return updated_user


def list_users() -> list[dict[str, Any]]:
    return load_users()


def count_active_superusers() -> int:
    count = 0
    for user in load_users():
        if str(user.get("role")) == ROLE_SUPERUSER and bool(user.get("is_active")):
            count += 1
    return count


def store_refresh_session(session_data: dict[str, Any]) -> dict[str, Any]:
    state = load_auth_state()
    state["refresh_sessions"].append(session_data)
    save_auth_state(state)
    return session_data


def find_refresh_session_by_jti(jti: str) -> dict[str, Any] | None:
    state = load_auth_state()

    for session in state.get("refresh_sessions", []):
        if str(session.get("jti")) == str(jti):
            return session
    return None


def revoke_refresh_session_by_jti(jti: str) -> bool:
    state = load_auth_state()
    updated = False

    for session in state.get("refresh_sessions", []):
        if str(session.get("jti")) == str(jti):
            session["is_revoked"] = True
            updated = True

    if updated:
        save_auth_state(state)

    return updated


def revoke_all_refresh_sessions_by_user_id(user_id: str) -> int:
    state = load_auth_state()
    revoked_count = 0

    for session in state.get("refresh_sessions", []):
        if str(session.get("user_id")) == str(user_id) and not bool(session.get("is_revoked")):
            session["is_revoked"] = True
            revoked_count += 1

    if revoked_count > 0:
        save_auth_state(state)

    return revoked_count


def store_password_reset_token(token_data: dict[str, Any]) -> dict[str, Any]:
    state = load_auth_state()
    state["password_reset_tokens"].append(token_data)
    save_auth_state(state)
    return token_data


def find_password_reset_token(token_hash: str) -> dict[str, Any] | None:
    state = load_auth_state()

    for token_item in state.get("password_reset_tokens", []):
        if str(token_item.get("token_hash")) == str(token_hash):
            return token_item
    return None


def mark_password_reset_token_used(token_hash: str) -> bool:
    state = load_auth_state()
    updated = False

    for token_item in state.get("password_reset_tokens", []):
        if str(token_item.get("token_hash")) == str(token_hash):
            token_item["is_used"] = True
            updated = True

    if updated:
        save_auth_state(state)

    return updated


def store_email_verification_token(token_data: dict[str, Any]) -> dict[str, Any]:
    state = load_auth_state()
    state["email_verification_tokens"].append(token_data)
    save_auth_state(state)
    return token_data


def find_email_verification_token(token_hash: str) -> dict[str, Any] | None:
    state = load_auth_state()

    for token_item in state.get("email_verification_tokens", []):
        if str(token_item.get("token_hash")) == str(token_hash):
            return token_item
    return None


def mark_email_verification_token_used(token_hash: str) -> bool:
    state = load_auth_state()
    updated = False

    for token_item in state.get("email_verification_tokens", []):
        if str(token_item.get("token_hash")) == str(token_hash):
            token_item["is_used"] = True
            updated = True

    if updated:
        save_auth_state(state)

    return updated