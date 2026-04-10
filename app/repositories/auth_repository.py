# app/repositories/auth_repository.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import json  # 용도: JSON 파일 저장/조회
from pathlib import Path  # 용도: 파일 경로 처리
from typing import Any  # 용도: 공용 타입 힌트

from app.core.policy_settings import DEFAULT_ADMIN_POLICIES  # 용도: 기본 관리자 정책 로드
from app.core.roles import ROLE_SUPERUSER  # 용도: superuser 역할 비교

_AUTH_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "auth"
_USERS_FILE = _AUTH_DATA_DIR / "users.json"
_REFRESH_SESSIONS_FILE = _AUTH_DATA_DIR / "refresh_sessions.json"
_EMAIL_VERIFICATION_TOKENS_FILE = _AUTH_DATA_DIR / "email_verification_tokens.json"
_PASSWORD_RESET_TOKENS_FILE = _AUTH_DATA_DIR / "password_reset_tokens.json"
_ADMIN_POLICIES_FILE = _AUTH_DATA_DIR / "admin_policies.json"
_AUDIT_LOGS_FILE = _AUTH_DATA_DIR / "audit_logs.json"


def _ensure_auth_data_dir() -> None:
    _AUTH_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_json_list_file(file_path: Path) -> None:
    if file_path.exists():
        return

    file_path.write_text("[]", encoding="utf-8")


def _ensure_json_dict_file(file_path: Path, default_item: dict[str, Any]) -> None:
    if file_path.exists():
        return

    file_path.write_text(
        json.dumps(default_item, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init_auth_storage() -> None:
    _ensure_auth_data_dir()
    _ensure_json_list_file(_USERS_FILE)
    _ensure_json_list_file(_REFRESH_SESSIONS_FILE)
    _ensure_json_list_file(_EMAIL_VERIFICATION_TOKENS_FILE)
    _ensure_json_list_file(_PASSWORD_RESET_TOKENS_FILE)
    _ensure_json_list_file(_AUDIT_LOGS_FILE)
    _ensure_json_dict_file(
        _ADMIN_POLICIES_FILE,
        {"policies": dict(DEFAULT_ADMIN_POLICIES)},
    )


def _read_json_list(file_path: Path) -> list[dict[str, Any]]:
    init_auth_storage()

    try:
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []

        loaded_data = json.loads(raw_text)

        if isinstance(loaded_data, list):
            return loaded_data

        return []
    except Exception:
        return []


def _write_json_list(file_path: Path, items: list[dict[str, Any]]) -> None:
    init_auth_storage()
    file_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_json_dict(file_path: Path) -> dict[str, Any]:
    init_auth_storage()

    try:
        raw_text = file_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return {}

        loaded_data = json.loads(raw_text)

        if isinstance(loaded_data, dict):
            return loaded_data

        return {}
    except Exception:
        return {}


def _write_json_dict(file_path: Path, item: dict[str, Any]) -> None:
    init_auth_storage()
    file_path.write_text(
        json.dumps(item, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_users() -> list[dict[str, Any]]:
    return _read_json_list(_USERS_FILE)


def _save_users(users: list[dict[str, Any]]) -> None:
    _write_json_list(_USERS_FILE, users)


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    for user in list_users():
        if str(user.get("user_id")) == str(user_id):
            return user

    return None


def find_user_by_username(username: str) -> dict[str, Any] | None:
    normalized_username = str(username or "").strip().lower()

    for user in list_users():
        if str(user.get("username", "")).strip().lower() == normalized_username:
            return user

    return None


def find_user_by_email(email: str) -> dict[str, Any] | None:
    normalized_email = str(email or "").strip().lower()

    for user in list_users():
        if str(user.get("email", "")).strip().lower() == normalized_email:
            return user

    return None


def find_user_by_login_id(login_id: str) -> dict[str, Any] | None:
    user = find_user_by_username(login_id)

    if user:
        return user

    return find_user_by_email(login_id)


def insert_user(user: dict[str, Any]) -> None:
    users = list_users()
    users.append(dict(user))
    _save_users(users)


def update_user(updated_user: dict[str, Any]) -> None:
    users = list_users()
    updated_users: list[dict[str, Any]] = []

    for user in users:
        if str(user.get("user_id")) == str(updated_user.get("user_id")):
            updated_users.append(dict(updated_user))
            continue

        updated_users.append(user)

    _save_users(updated_users)


def count_active_superusers() -> int:
    active_count = 0

    for user in list_users():
        if str(user.get("role")) == ROLE_SUPERUSER and bool(user.get("is_active")):
            active_count += 1

    return active_count


def _load_refresh_sessions() -> list[dict[str, Any]]:
    return _read_json_list(_REFRESH_SESSIONS_FILE)


def _save_refresh_sessions(items: list[dict[str, Any]]) -> None:
    _write_json_list(_REFRESH_SESSIONS_FILE, items)


def store_refresh_session(session_data: dict[str, Any]) -> None:
    sessions = _load_refresh_sessions()
    sessions.append(dict(session_data))
    _save_refresh_sessions(sessions)


def find_refresh_session_by_jti(jti: str) -> dict[str, Any] | None:
    for session in _load_refresh_sessions():
        if str(session.get("jti")) == str(jti):
            return session

    return None


def revoke_refresh_session_by_jti(jti: str) -> int:
    sessions = _load_refresh_sessions()
    updated_count = 0
    updated_sessions: list[dict[str, Any]] = []

    for session in sessions:
        if str(session.get("jti")) == str(jti) and not bool(session.get("is_revoked")):
            copied_session = dict(session)
            copied_session["is_revoked"] = True
            updated_sessions.append(copied_session)
            updated_count += 1
            continue

        updated_sessions.append(session)

    _save_refresh_sessions(updated_sessions)
    return updated_count


def revoke_all_refresh_sessions_by_user_id(user_id: str) -> int:
    sessions = _load_refresh_sessions()
    updated_count = 0
    updated_sessions: list[dict[str, Any]] = []

    for session in sessions:
        if str(session.get("user_id")) == str(user_id) and not bool(session.get("is_revoked")):
            copied_session = dict(session)
            copied_session["is_revoked"] = True
            updated_sessions.append(copied_session)
            updated_count += 1
            continue

        updated_sessions.append(session)

    _save_refresh_sessions(updated_sessions)
    return updated_count


def _load_email_verification_tokens() -> list[dict[str, Any]]:
    return _read_json_list(_EMAIL_VERIFICATION_TOKENS_FILE)


def _save_email_verification_tokens(items: list[dict[str, Any]]) -> None:
    _write_json_list(_EMAIL_VERIFICATION_TOKENS_FILE, items)


def store_email_verification_token(token_data: dict[str, Any]) -> None:
    tokens = _load_email_verification_tokens()
    tokens.append(dict(token_data))
    _save_email_verification_tokens(tokens)


def find_email_verification_token(token_hash: str) -> dict[str, Any] | None:
    for token_item in _load_email_verification_tokens():
        if str(token_item.get("token_hash")) == str(token_hash):
            return token_item

    return None


def mark_email_verification_token_used(token_hash: str) -> int:
    tokens = _load_email_verification_tokens()
    updated_count = 0
    updated_tokens: list[dict[str, Any]] = []

    for token_item in tokens:
        if str(token_item.get("token_hash")) == str(token_hash) and not bool(token_item.get("is_used")):
            copied_token = dict(token_item)
            copied_token["is_used"] = True
            updated_tokens.append(copied_token)
            updated_count += 1
            continue

        updated_tokens.append(token_item)

    _save_email_verification_tokens(updated_tokens)
    return updated_count


def _load_password_reset_tokens() -> list[dict[str, Any]]:
    return _read_json_list(_PASSWORD_RESET_TOKENS_FILE)


def _save_password_reset_tokens(items: list[dict[str, Any]]) -> None:
    _write_json_list(_PASSWORD_RESET_TOKENS_FILE, items)


def store_password_reset_token(token_data: dict[str, Any]) -> None:
    tokens = _load_password_reset_tokens()
    tokens.append(dict(token_data))
    _save_password_reset_tokens(tokens)


def find_password_reset_token(token_hash: str) -> dict[str, Any] | None:
    for token_item in _load_password_reset_tokens():
        if str(token_item.get("token_hash")) == str(token_hash):
            return token_item

    return None


def mark_password_reset_token_used(token_hash: str) -> int:
    tokens = _load_password_reset_tokens()
    updated_count = 0
    updated_tokens: list[dict[str, Any]] = []

    for token_item in tokens:
        if str(token_item.get("token_hash")) == str(token_hash) and not bool(token_item.get("is_used")):
            copied_token = dict(token_item)
            copied_token["is_used"] = True
            updated_tokens.append(copied_token)
            updated_count += 1
            continue

        updated_tokens.append(token_item)

    _save_password_reset_tokens(updated_tokens)
    return updated_count


def load_admin_policies() -> dict[str, Any]:
    stored_data = _read_json_dict(_ADMIN_POLICIES_FILE)
    stored_policies = stored_data.get("policies", {}) if isinstance(stored_data, dict) else {}

    merged_policies = dict(DEFAULT_ADMIN_POLICIES)
    merged_policies.update(dict(stored_policies or {}))

    return {
        "policies": merged_policies,
    }


def save_admin_policies(policies: dict[str, Any]) -> dict[str, Any]:
    merged_policies = dict(DEFAULT_ADMIN_POLICIES)
    merged_policies.update(dict(policies or {}))

    saved_data = {
        "policies": merged_policies,
    }
    _write_json_dict(_ADMIN_POLICIES_FILE, saved_data)
    return saved_data


def append_audit_log(log_item: dict[str, Any]) -> None:
    logs = _read_json_list(_AUDIT_LOGS_FILE)
    logs.append(dict(log_item))
    _write_json_list(_AUDIT_LOGS_FILE, logs)


def load_audit_logs() -> list[dict[str, Any]]:
    return _read_json_list(_AUDIT_LOGS_FILE)