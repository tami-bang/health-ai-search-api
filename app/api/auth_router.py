# app/api/auth_router.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from fastapi import APIRouter  # 용도: 인증 라우터 등록
from fastapi import Depends  # 용도: 인증 의존성 주입

from app.dependencies.auth_dependencies import get_current_user  # 용도: 현재 로그인 사용자 조회
from app.schemas import ChangePasswordRequest  # 용도: 비밀번호 변경 요청 스키마
from app.schemas import EmailVerificationRequest  # 용도: 이메일 인증 요청 스키마
from app.schemas import ForgotIdRequest  # 용도: 아이디 찾기 요청 스키마
from app.schemas import ForgotPasswordRequest  # 용도: 비밀번호 찾기 요청 스키마
from app.schemas import LoginRequest  # 용도: 로그인 요청 스키마
from app.schemas import LogoutRequest  # 용도: 로그아웃 요청 스키마
from app.schemas import RefreshTokenRequest  # 용도: 토큰 재발급 요청 스키마
from app.schemas import ResendVerificationRequest  # 용도: 인증 재발급 요청 스키마
from app.schemas import ResetPasswordRequest  # 용도: 비밀번호 재설정 요청 스키마
from app.schemas import SignupRequest  # 용도: 회원가입 요청 스키마
from app.schemas import UpdateProfileRequest  # 용도: 프로필 수정 요청 스키마
from app.services.auth_service import change_password  # 용도: 비밀번호 변경 서비스
from app.services.auth_service import forgot_id  # 용도: 아이디 찾기 서비스
from app.services.auth_service import forgot_password  # 용도: 비밀번호 찾기 서비스
from app.services.auth_service import get_me  # 용도: 내 정보 조회 서비스
from app.services.auth_service import login_user  # 용도: 로그인 서비스
from app.services.auth_service import logout_all_sessions  # 용도: 전체 세션 로그아웃 서비스
from app.services.auth_service import logout_user  # 용도: 로그아웃 서비스
from app.services.auth_service import refresh_user_tokens  # 용도: 토큰 재발급 서비스
from app.services.auth_service import resend_verification  # 용도: 인증 재발급 서비스
from app.services.auth_service import reset_password  # 용도: 비밀번호 재설정 서비스
from app.services.auth_service import signup_user  # 용도: 회원가입 서비스
from app.services.auth_service import update_me  # 용도: 내 정보 수정 서비스
from app.services.auth_service import verify_email  # 용도: 이메일 인증 서비스

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/signup")
def signup(payload: SignupRequest) -> dict:
    return signup_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        full_name=payload.full_name,
    )


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    return login_user(
        login_id=payload.login_id,
        password=payload.password,
    )


@router.post("/refresh")
def refresh(payload: RefreshTokenRequest) -> dict:
    return refresh_user_tokens(
        refresh_token=payload.refresh_token,
    )


@router.post("/logout")
def logout(payload: LogoutRequest) -> dict:
    return logout_user(
        refresh_token=payload.refresh_token,
    )


@router.post("/logout-all")
def logout_all(
    current_user: dict = Depends(get_current_user),
) -> dict:
    return logout_all_sessions(current_user=current_user)


@router.get("/me")
def me(
    current_user: dict = Depends(get_current_user),
) -> dict:
    return get_me(current_user=current_user)


@router.patch("/me")
def update_profile(
    payload: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return update_me(
        current_user=current_user,
        full_name=payload.full_name,
    )


@router.post("/verify-email")
def verify_email_endpoint(payload: EmailVerificationRequest) -> dict:
    return verify_email(token=payload.token)


@router.post("/resend-verification")
def resend_verification_endpoint(payload: ResendVerificationRequest) -> dict:
    return resend_verification(email=payload.email)


@router.post("/forgot-id")
def forgot_id_endpoint(payload: ForgotIdRequest) -> dict:
    return forgot_id(email=payload.email)


@router.post("/forgot-password")
def forgot_password_endpoint(payload: ForgotPasswordRequest) -> dict:
    return forgot_password(login_id=payload.login_id)


@router.post("/reset-password")
def reset_password_endpoint(payload: ResetPasswordRequest) -> dict:
    return reset_password(
        token=payload.token,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )


@router.post("/change-password")
def change_password_endpoint(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return change_password(
        current_user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )