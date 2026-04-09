# app/services/auth_service.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import uuid  # 용도: 사용자 ID 생성
from typing import Any  # 용도: 공용 타입 힌트

from jose import JWTError  # 용도: JWT 예외 처리

from app.core.auth_settings import ACCESS_TOKEN_EXPIRE_MINUTES  # 용도: access token 만료분
from app.core.auth_settings import AUTH_REQUIRE_EMAIL_VERIFICATION  # 용도: 이메일 인증 필수 여부
from app.core.auth_settings import DEV_EXPOSE_AUTH_TOKENS  # 용도: 개발용 토큰 노출 여부
from app.core.auth_settings import EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES  # 용도: 이메일 인증 토큰 만료분
from app.core.auth_settings import FULL_NAME_MAX_LENGTH  # 용도: 이름 길이 제한
from app.core.auth_settings import PASSWORD_MAX_LENGTH  # 용도: 비밀번호 길이 제한
from app.core.auth_settings import PASSWORD_MIN_LENGTH  # 용도: 비밀번호 길이 제한
from app.core.auth_settings import PASSWORD_RESET_TOKEN_EXPIRE_MINUTES  # 용도: 비밀번호 재설정 토큰 만료분
from app.core.auth_settings import REFRESH_TOKEN_EXPIRE_MINUTES  # 용도: refresh token 만료분
from app.core.auth_settings import USERNAME_MAX_LENGTH  # 용도: 아이디 길이 제한
from app.core.auth_settings import USERNAME_MIN_LENGTH  # 용도: 아이디 길이 제한
from app.core.error_codes import ADMIN_INVALID_ROLE  # 용도: 역할 검증 에러 코드
from app.core.error_codes import AUTH_ACCOUNT_INACTIVE  # 용도: 비활성 계정 에러 코드
from app.core.error_codes import AUTH_EMAIL_ALREADY_EXISTS  # 용도: 이메일 중복 에러 코드
from app.core.error_codes import AUTH_EMAIL_NOT_VERIFIED  # 용도: 이메일 미인증 에러 코드
from app.core.error_codes import AUTH_INVALID_CREDENTIALS  # 용도: 로그인 실패 에러 코드
from app.core.error_codes import AUTH_INVALID_TOKEN  # 용도: 토큰 오류 코드
from app.core.error_codes import AUTH_PASSWORD_MISMATCH  # 용도: 비밀번호 불일치 에러 코드
from app.core.error_codes import AUTH_PASSWORD_WEAK  # 용도: 약한 비밀번호 에러 코드
from app.core.error_codes import AUTH_REFRESH_TOKEN_REVOKED  # 용도: refresh revoke 에러 코드
from app.core.error_codes import AUTH_USER_NOT_FOUND  # 용도: 사용자 없음 에러 코드
from app.core.error_codes import AUTH_USERNAME_ALREADY_EXISTS  # 용도: 아이디 중복 에러 코드
from app.core.exceptions import AuthException  # 용도: 인증 예외 처리
from app.core.role_permissions import ROLE_MEMBER  # 용도: 기본 회원 역할
from app.core.role_permissions import ROLE_OPERATOR  # 용도: 운영자 역할
from app.core.role_permissions import ROLE_SUPERUSER  # 용도: 수퍼유저 역할
from app.core.role_permissions import is_valid_role  # 용도: 역할 검증
from app.core.security import create_jwt_token  # 용도: JWT 생성
from app.core.security import decode_jwt_token  # 용도: JWT 해석
from app.core.security import from_iso  # 용도: ISO 시간 파싱
from app.core.security import generate_raw_token  # 용도: 랜덤 토큰 생성
from app.core.security import hash_lookup_token  # 용도: 토큰 해시
from app.core.security import hash_password  # 용도: 비밀번호 해시
from app.core.security import mask_username  # 용도: 아이디 마스킹
from app.core.security import to_iso  # 용도: ISO 시간 문자열 변환
from app.core.security import utc_now  # 용도: 현재 UTC 시간
from app.core.security import verify_password  # 용도: 비밀번호 검증
from app.repositories.auth_repository import count_active_superusers  # 용도: 수퍼유저 수 조회
from app.repositories.auth_repository import find_email_verification_token  # 용도: 이메일 인증 토큰 조회
from app.repositories.auth_repository import find_password_reset_token  # 용도: 비밀번호 재설정 토큰 조회
from app.repositories.auth_repository import find_refresh_session_by_jti  # 용도: refresh 세션 조회
from app.repositories.auth_repository import find_user_by_email  # 용도: 이메일 사용자 조회
from app.repositories.auth_repository import find_user_by_id  # 용도: ID 사용자 조회
from app.repositories.auth_repository import find_user_by_login_id  # 용도: 로그인 ID 사용자 조회
from app.repositories.auth_repository import find_user_by_username  # 용도: 아이디 사용자 조회
from app.repositories.auth_repository import insert_user  # 용도: 사용자 생성
from app.repositories.auth_repository import load_admin_policies  # 용도: 서비스 정책 조회
from app.repositories.auth_repository import mark_email_verification_token_used  # 용도: 이메일 인증 토큰 사용 처리
from app.repositories.auth_repository import mark_password_reset_token_used  # 용도: 비밀번호 재설정 토큰 사용 처리
from app.repositories.auth_repository import revoke_all_refresh_sessions_by_user_id  # 용도: 전체 세션 만료
from app.repositories.auth_repository import revoke_refresh_session_by_jti  # 용도: refresh 세션 만료
from app.repositories.auth_repository import store_email_verification_token  # 용도: 이메일 인증 토큰 저장
from app.repositories.auth_repository import store_password_reset_token  # 용도: 비밀번호 재설정 토큰 저장
from app.repositories.auth_repository import store_refresh_session  # 용도: refresh 세션 저장
from app.repositories.auth_repository import update_user  # 용도: 사용자 정보 저장
from app.services.audit_service import create_audit_log  # 용도: 감사 로그 기록


def _validate_username(username: str) -> str:
    cleaned_username = str(username or "").strip()

    if len(cleaned_username) < USERNAME_MIN_LENGTH or len(cleaned_username) > USERNAME_MAX_LENGTH:
        raise AuthException(
            message="Invalid username length.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=400,
        )

    return cleaned_username


def _validate_full_name(full_name: str | None) -> str:
    cleaned_full_name = str(full_name or "").strip()

    if len(cleaned_full_name) > FULL_NAME_MAX_LENGTH:
        raise AuthException(
            message="Full name is too long.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=400,
        )

    return cleaned_full_name


def _validate_password_strength(password: str) -> str:
    cleaned_password = str(password or "")

    if len(cleaned_password) < PASSWORD_MIN_LENGTH or len(cleaned_password) > PASSWORD_MAX_LENGTH:
        raise AuthException(
            message="Password length is invalid.",
            error_code=AUTH_PASSWORD_WEAK,
            status_code=400,
        )

    has_alpha = any(character.isalpha() for character in cleaned_password)
    has_digit = any(character.isdigit() for character in cleaned_password)

    if not has_alpha or not has_digit:
        raise AuthException(
            message="Password must include letters and numbers.",
            error_code=AUTH_PASSWORD_WEAK,
            status_code=400,
        )

    return cleaned_password


def _ensure_passwords_match(password: str, confirm_password: str) -> None:
    if str(password) != str(confirm_password):
        raise AuthException(
            message="Passwords do not match.",
            error_code=AUTH_PASSWORD_MISMATCH,
            status_code=400,
        )


def _build_public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user.get("user_id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "full_name": user.get("full_name", ""),
        "role": user.get("role", ROLE_MEMBER),
        "is_active": bool(user.get("is_active")),
        "is_email_verified": bool(user.get("is_email_verified")),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "last_login_at": user.get("last_login_at"),
    }


def _build_token_response(user: dict[str, Any], refresh_token: str, access_token: str) -> dict[str, Any]:
    response = {
        "message": "Login success.",
        "user": _build_public_user(user),
        "token_type": "bearer",
    }

    if DEV_EXPOSE_AUTH_TOKENS:
        response["access_token"] = access_token
        response["refresh_token"] = refresh_token

    return response


def _create_refresh_session(user: dict[str, Any], refresh_token: str) -> None:
    payload = decode_jwt_token(refresh_token)
    session_data = {
        "jti": payload.get("jti"),
        "user_id": user.get("user_id"),
        "token_type": "refresh",
        "is_revoked": False,
        "created_at": to_iso(utc_now()),
        "expires_at": None,
    }
    store_refresh_session(session_data)


def _issue_tokens(user: dict[str, Any]) -> tuple[str, str]:
    access_token = create_jwt_token(
        subject=str(user.get("user_id")),
        token_type="access",
        expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        extra_payload={
            "username": user.get("username"),
            "role": user.get("role", ROLE_MEMBER),
        },
    )
    refresh_token = create_jwt_token(
        subject=str(user.get("user_id")),
        token_type="refresh",
        expires_minutes=REFRESH_TOKEN_EXPIRE_MINUTES,
        extra_payload={
            "username": user.get("username"),
            "role": user.get("role", ROLE_MEMBER),
        },
    )
    _create_refresh_session(user=user, refresh_token=refresh_token)
    return access_token, refresh_token


def _ensure_user_can_login(user: dict[str, Any]) -> None:
    if not bool(user.get("is_active")):
        raise AuthException(
            message="Account is inactive.",
            error_code=AUTH_ACCOUNT_INACTIVE,
            status_code=403,
        )

    policies = load_admin_policies().get("policies", {})
    require_email_verification = bool(
        policies.get("require_email_verification", AUTH_REQUIRE_EMAIL_VERIFICATION),
    )

    if require_email_verification and not bool(user.get("is_email_verified")):
        raise AuthException(
            message="Email verification required.",
            error_code=AUTH_EMAIL_NOT_VERIFIED,
            status_code=403,
        )


def _create_single_use_lookup_token(expires_minutes: int) -> tuple[str, str]:
    raw_token = generate_raw_token()
    token_hash = hash_lookup_token(raw_token)
    expires_at = to_iso(utc_now())
    return raw_token, token_hash


def get_user_from_access_token(token: str) -> dict[str, Any]:
    try:
        payload = decode_jwt_token(token)
    except JWTError as error:
        raise AuthException(
            message="Invalid access token.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        ) from error

    if payload.get("type") != "access":
        raise AuthException(
            message="Invalid token type.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    user_id = str(payload.get("sub") or "")
    user = find_user_by_id(user_id)

    if not user:
        raise AuthException(
            message="User not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    if not bool(user.get("is_active")):
        raise AuthException(
            message="Account is inactive.",
            error_code=AUTH_ACCOUNT_INACTIVE,
            status_code=403,
        )

    return user


def signup_user(
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    full_name: str | None = None,
    role: str = ROLE_MEMBER,
    actor_user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policies = load_admin_policies().get("policies", {})

    if actor_user is None and not bool(policies.get("allow_public_signup", True)):
        raise AuthException(
            message="Public signup is disabled.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=403,
        )

    cleaned_username = _validate_username(username)
    cleaned_email = str(email or "").strip().lower()
    cleaned_full_name = _validate_full_name(full_name)

    _ensure_passwords_match(password=password, confirm_password=confirm_password)
    validated_password = _validate_password_strength(password)

    if find_user_by_username(cleaned_username):
        raise AuthException(
            message="Username already exists.",
            error_code=AUTH_USERNAME_ALREADY_EXISTS,
            status_code=409,
        )

    if find_user_by_email(cleaned_email):
        raise AuthException(
            message="Email already exists.",
            error_code=AUTH_EMAIL_ALREADY_EXISTS,
            status_code=409,
        )

    if not is_valid_role(role):
        raise AuthException(
            message="Invalid role.",
            error_code=ADMIN_INVALID_ROLE,
            status_code=400,
        )

    now_iso = to_iso(utc_now())
    user = {
        "user_id": f"user-{uuid.uuid4().hex}",
        "username": cleaned_username,
        "email": cleaned_email,
        "full_name": cleaned_full_name,
        "password_hash": hash_password(validated_password),
        "role": role,
        "is_active": True,
        "is_email_verified": False if role == ROLE_MEMBER else True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "last_login_at": None,
    }
    insert_user(user)

    create_audit_log(
        actor_user_id=actor_user.get("user_id") if actor_user else user.get("user_id"),
        actor_username=actor_user.get("username") if actor_user else user.get("username"),
        action="user_created" if actor_user else "user_signed_up",
        target_type="user",
        target_id=user.get("user_id"),
        detail={
            "username": user.get("username"),
            "role": user.get("role"),
        },
    )

    response = {
        "message": "Signup success.",
        "user": _build_public_user(user),
    }

    if not bool(user.get("is_email_verified")):
        response["verification"] = resend_verification(email=cleaned_email)

    return response


def login_user(login_id: str, password: str) -> dict[str, Any]:
    user = find_user_by_login_id(login_id)

    if not user:
        raise AuthException(
            message="Invalid credentials.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=401,
        )

    if not verify_password(password, str(user.get("password_hash", ""))):
        raise AuthException(
            message="Invalid credentials.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=401,
        )

    _ensure_user_can_login(user)

    user["last_login_at"] = to_iso(utc_now())
    user["updated_at"] = to_iso(utc_now())
    update_user(user)

    access_token, refresh_token = _issue_tokens(user)

    create_audit_log(
        actor_user_id=user.get("user_id"),
        actor_username=user.get("username"),
        action="user_logged_in",
        target_type="user",
        target_id=user.get("user_id"),
        detail={},
    )

    return _build_token_response(
        user=user,
        refresh_token=refresh_token,
        access_token=access_token,
    )


def refresh_user_tokens(refresh_token: str) -> dict[str, Any]:
    try:
        payload = decode_jwt_token(refresh_token)
    except JWTError as error:
        raise AuthException(
            message="Invalid refresh token.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        ) from error

    if payload.get("type") != "refresh":
        raise AuthException(
            message="Invalid token type.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    jti = str(payload.get("jti") or "")
    session = find_refresh_session_by_jti(jti)

    if not session or bool(session.get("is_revoked")):
        raise AuthException(
            message="Refresh token revoked.",
            error_code=AUTH_REFRESH_TOKEN_REVOKED,
            status_code=401,
        )

    user_id = str(payload.get("sub") or "")
    user = find_user_by_id(user_id)

    if not user:
        raise AuthException(
            message="User not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    _ensure_user_can_login(user)
    revoke_refresh_session_by_jti(jti)

    access_token, new_refresh_token = _issue_tokens(user)

    create_audit_log(
        actor_user_id=user.get("user_id"),
        actor_username=user.get("username"),
        action="token_refreshed",
        target_type="user",
        target_id=user.get("user_id"),
        detail={},
    )

    return _build_token_response(
        user=user,
        refresh_token=new_refresh_token,
        access_token=access_token,
    )


def logout_user(refresh_token: str) -> dict[str, Any]:
    try:
        payload = decode_jwt_token(refresh_token)
    except JWTError as error:
        raise AuthException(
            message="Invalid refresh token.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        ) from error

    jti = str(payload.get("jti") or "")
    revoke_refresh_session_by_jti(jti)

    return {
        "message": "Logout success.",
    }


def logout_all_sessions(current_user: dict[str, Any]) -> dict[str, Any]:
    revoked_count = revoke_all_refresh_sessions_by_user_id(str(current_user.get("user_id")))

    create_audit_log(
        actor_user_id=current_user.get("user_id"),
        actor_username=current_user.get("username"),
        action="logout_all_sessions",
        target_type="user",
        target_id=current_user.get("user_id"),
        detail={
            "revoked_count": revoked_count,
        },
    )

    return {
        "message": "All sessions logged out.",
        "revoked_count": revoked_count,
    }


def get_me(current_user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user": _build_public_user(current_user),
    }


def update_me(current_user: dict[str, Any], full_name: str | None = None) -> dict[str, Any]:
    current_user["full_name"] = _validate_full_name(full_name)
    current_user["updated_at"] = to_iso(utc_now())
    update_user(current_user)

    create_audit_log(
        actor_user_id=current_user.get("user_id"),
        actor_username=current_user.get("username"),
        action="profile_updated",
        target_type="user",
        target_id=current_user.get("user_id"),
        detail={},
    )

    return {
        "message": "Profile updated.",
        "user": _build_public_user(current_user),
    }


def forgot_id(email: str) -> dict[str, Any]:
    user = find_user_by_email(email)

    if not user:
        return {
            "message": "If the email exists, account info has been prepared.",
        }

    return {
        "message": "Account info found.",
        "masked_username": mask_username(str(user.get("username", ""))),
    }


def forgot_password(login_id: str) -> dict[str, Any]:
    user = find_user_by_login_id(login_id)

    if not user:
        return {
            "message": "If the account exists, reset info has been prepared.",
        }

    raw_token = generate_raw_token()
    token_hash = hash_lookup_token(raw_token)

    store_password_reset_token(
        {
            "token_hash": token_hash,
            "user_id": user.get("user_id"),
            "is_used": False,
            "created_at": to_iso(utc_now()),
        },
    )

    create_audit_log(
        actor_user_id=user.get("user_id"),
        actor_username=user.get("username"),
        action="password_reset_requested",
        target_type="user",
        target_id=user.get("user_id"),
        detail={},
    )

    response = {
        "message": "Password reset token created.",
    }

    if DEV_EXPOSE_AUTH_TOKENS:
        response["reset_token"] = raw_token

    return response


def reset_password(token: str, new_password: str, confirm_password: str) -> dict[str, Any]:
    _ensure_passwords_match(password=new_password, confirm_password=confirm_password)
    validated_password = _validate_password_strength(new_password)

    token_hash = hash_lookup_token(token)
    token_item = find_password_reset_token(token_hash)

    if not token_item or bool(token_item.get("is_used")):
        raise AuthException(
            message="Invalid reset token.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    user = find_user_by_id(str(token_item.get("user_id")))
    if not user:
        raise AuthException(
            message="User not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    user["password_hash"] = hash_password(validated_password)
    user["updated_at"] = to_iso(utc_now())
    update_user(user)
    mark_password_reset_token_used(token_hash)
    revoke_all_refresh_sessions_by_user_id(str(user.get("user_id")))

    create_audit_log(
        actor_user_id=user.get("user_id"),
        actor_username=user.get("username"),
        action="password_reset_completed",
        target_type="user",
        target_id=user.get("user_id"),
        detail={},
    )

    return {
        "message": "Password reset success.",
    }


def resend_verification(email: str) -> dict[str, Any]:
    user = find_user_by_email(email)

    if not user:
        return {
            "message": "If the email exists, verification info has been prepared.",
        }

    if bool(user.get("is_email_verified")):
        return {
            "message": "Email already verified.",
        }

    raw_token = generate_raw_token()
    token_hash = hash_lookup_token(raw_token)

    store_email_verification_token(
        {
            "token_hash": token_hash,
            "user_id": user.get("user_id"),
            "is_used": False,
            "created_at": to_iso(utc_now()),
        },
    )

    response = {
        "message": "Verification token created.",
    }

    if DEV_EXPOSE_AUTH_TOKENS:
        response["verification_token"] = raw_token

    return response


def verify_email(token: str) -> dict[str, Any]:
    token_hash = hash_lookup_token(token)
    token_item = find_email_verification_token(token_hash)

    if not token_item or bool(token_item.get("is_used")):
        raise AuthException(
            message="Invalid verification token.",
            error_code=AUTH_INVALID_TOKEN,
            status_code=401,
        )

    user = find_user_by_id(str(token_item.get("user_id")))
    if not user:
        raise AuthException(
            message="User not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    user["is_email_verified"] = True
    user["updated_at"] = to_iso(utc_now())
    update_user(user)
    mark_email_verification_token_used(token_hash)

    create_audit_log(
        actor_user_id=user.get("user_id"),
        actor_username=user.get("username"),
        action="email_verified",
        target_type="user",
        target_id=user.get("user_id"),
        detail={},
    )

    return {
        "message": "Email verified.",
        "user": _build_public_user(user),
    }


def change_password(
    current_user: dict[str, Any],
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> dict[str, Any]:
    if not verify_password(current_password, str(current_user.get("password_hash", ""))):
        raise AuthException(
            message="Current password is invalid.",
            error_code=AUTH_INVALID_CREDENTIALS,
            status_code=401,
        )

    _ensure_passwords_match(password=new_password, confirm_password=confirm_password)
    validated_password = _validate_password_strength(new_password)

    current_user["password_hash"] = hash_password(validated_password)
    current_user["updated_at"] = to_iso(utc_now())
    update_user(current_user)
    revoke_all_refresh_sessions_by_user_id(str(current_user.get("user_id")))

    create_audit_log(
        actor_user_id=current_user.get("user_id"),
        actor_username=current_user.get("username"),
        action="password_changed",
        target_type="user",
        target_id=current_user.get("user_id"),
        detail={},
    )

    return {
        "message": "Password changed successfully. Please login again.",
    }


def list_public_users() -> list[dict[str, Any]]:
    from app.repositories.auth_repository import list_users  # 용도: 사용자 목록 로드

    return [_build_public_user(user) for user in list_users()]


def create_operator_account(
    actor_user: dict[str, Any],
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    full_name: str | None,
    role: str,
) -> dict[str, Any]:
    return signup_user(
        username=username,
        email=email,
        password=password,
        confirm_password=confirm_password,
        full_name=full_name,
        role=role,
        actor_user=actor_user,
    )


def update_user_role(
    actor_user: dict[str, Any],
    target_user_id: str,
    new_role: str,
) -> dict[str, Any]:
    if not is_valid_role(new_role):
        raise AuthException(
            message="Invalid role.",
            error_code=ADMIN_INVALID_ROLE,
            status_code=400,
        )

    target_user = find_user_by_id(target_user_id)
    if not target_user:
        raise AuthException(
            message="Target user not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    if str(target_user.get("role")) == ROLE_SUPERUSER and new_role != ROLE_SUPERUSER:
        if count_active_superusers() <= 1:
            raise AuthException(
                message="Cannot demote the last active superuser.",
                error_code="ADMIN_CANNOT_DEMOTE_LAST_SUPERUSER",
                status_code=400,
            )

    target_user["role"] = new_role
    target_user["updated_at"] = to_iso(utc_now())
    update_user(target_user)

    create_audit_log(
        actor_user_id=actor_user.get("user_id"),
        actor_username=actor_user.get("username"),
        action="role_updated",
        target_type="user",
        target_id=target_user.get("user_id"),
        detail={
            "new_role": new_role,
        },
    )

    return {
        "message": "User role updated.",
        "user": _build_public_user(target_user),
    }


def set_user_active_status(
    actor_user: dict[str, Any],
    target_user_id: str,
    is_active: bool,
) -> dict[str, Any]:
    target_user = find_user_by_id(target_user_id)
    if not target_user:
        raise AuthException(
            message="Target user not found.",
            error_code=AUTH_USER_NOT_FOUND,
            status_code=404,
        )

    if str(target_user.get("role")) == ROLE_SUPERUSER and not is_active:
        if count_active_superusers() <= 1:
            raise AuthException(
                message="Cannot deactivate the last active superuser.",
                error_code="ADMIN_CANNOT_DEMOTE_LAST_SUPERUSER",
                status_code=400,
            )

    target_user["is_active"] = bool(is_active)
    target_user["updated_at"] = to_iso(utc_now())
    update_user(target_user)

    if not is_active:
        revoke_all_refresh_sessions_by_user_id(str(target_user.get("user_id")))

    create_audit_log(
        actor_user_id=actor_user.get("user_id"),
        actor_username=actor_user.get("username"),
        action="user_status_updated",
        target_type="user",
        target_id=target_user.get("user_id"),
        detail={
            "is_active": bool(is_active),
        },
    )

    return {
        "message": "User status updated.",
        "user": _build_public_user(target_user),
    }