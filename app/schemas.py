from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from typing import Any  # 용도: 가변 debug 필드 타입 정의

from pydantic import BaseModel  # 용도: 요청/응답 스키마 정의
from pydantic import EmailStr  # 용도: 이메일 형식 검증
from pydantic import Field  # 용도: 필드 기본값 및 제약 정의


class TopicItem(BaseModel):
    # 프론트 호환 필드
    id: str
    title: str = ""
    snippet: str | None = None
    url: str = ""
    source: str | None = None
    category: str | None = None
    relevance_score: float | None = None

    # 기존 백엔드 고도화 필드
    summary: str | None = None
    document_type: str | None = None
    semantic_score: float | None = None
    keyword_boost: float | None = None
    hybrid_score: float | None = None
    reranked_by: str | None = None


class SearchMeta(BaseModel):
    detected_language: str | None = None
    internal_query: str | None = None
    normalized_query: str | None = None
    normalize_method: str | None = None
    normalize_score: float | None = None
    predicted_label: str | None = None
    model_confidence: float | None = None
    model_backend: str | None = None
    model_version: str | None = None
    search_query: str | None = None
    is_error: bool | None = None
    error_code: str | None = None
    timings: dict[str, float] = Field(default_factory=dict)


class SearchGuidance(BaseModel):
    notice: str
    triage_level: str
    triage_message: str
    triage_score: int = 0
    matched_patterns: list[str] = Field(default_factory=list)
    question_suggestions: list[str] = Field(default_factory=list)


class SearchResultsBundle(BaseModel):
    top_result: TopicItem | None = None
    results: list[TopicItem] = Field(default_factory=list)
    related_topics: list[TopicItem] = Field(default_factory=list)
    ai_summary: str | None = None
    ai_summary_model: str | None = None
    summary_included: bool = False
    summary_debug: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str
    meta: SearchMeta
    guidance: SearchGuidance
    results_bundle: SearchResultsBundle
    message: str | None = None


class HealthResponse(BaseModel):
    status: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="증상 질의")
    include_summary: bool = Field(False, description="AI 요약 포함 여부")


class TriageRequest(BaseModel):
    # 기존 단일 query 요청도 계속 허용
    query: str | None = Field(
        default=None,
        min_length=2,
        description="사용자 증상 또는 상태 입력",
        examples=["숨이 안 쉬어져요"],
    )

    # 프론트 multi-field 요청 지원
    symptoms: list[str] = Field(default_factory=list, description="증상 목록")
    duration: str | None = Field(default=None, description="지속 기간")
    severity: int | None = Field(default=None, ge=1, le=10, description="중증도 1-10")
    age: int | None = Field(default=None, ge=0, description="나이")
    additional_info: str | None = Field(default=None, description="추가 정보")


class TriagePattern(BaseModel):
    pattern_id: str
    pattern_name: str
    confidence: float
    description: str


class TriageMatchedRule(BaseModel):
    group_name: str
    pattern: str
    score: int
    source_language: str | None = None


class TriageRiskFactor(BaseModel):
    factor_id: str
    label: str
    score: int
    category: str


class TriageScoreBreakdown(BaseModel):
    base_score: int = 0
    adjustment_score: int = 0
    total_score: int = 0


class TriageGuidanceMeta(BaseModel):
    emergency: bool = False
    urgent: bool = False
    display_level: str | None = None


class TriageResponse(BaseModel):
    # 기존 백엔드 필드 유지
    query: str
    detected_language: str
    triage_level: str
    triage_message: str
    triage_score: int

    # 프론트 호환 구조 확장
    matched_patterns: list[TriagePattern] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    disclaimer: str = "This triage tool provides general guidance only and is not medical advice."

    # 백엔드 고도화 + 프론트 확장 필드
    matched_rule_names: list[str] = Field(default_factory=list)
    matched_rule_details: list[TriageMatchedRule] = Field(default_factory=list)
    risk_factors: list[TriageRiskFactor] = Field(default_factory=list)
    score_breakdown: TriageScoreBreakdown | None = None
    guidance_meta: TriageGuidanceMeta | None = None

    # 요청 컨텍스트 반영 필드
    duration: str | None = None
    severity: int | None = None
    age: int | None = None
    additional_info: str | None = None

    # 디버그/확장 포인트
    debug: dict[str, Any] | None = None


class PublicUser(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    full_name: str = ""
    role: str = "member"
    is_active: bool
    is_email_verified: bool
    created_at: str | None = None
    updated_at: str | None = None
    last_login_at: str | None = None


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=30, description="로그인 아이디")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)
    full_name: str | None = Field(default=None, max_length=50)


class LoginRequest(BaseModel):
    login_id: str = Field(..., min_length=3, description="아이디 또는 이메일")
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class ForgotIdRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    login_id: str = Field(..., min_length=3, description="아이디 또는 이메일")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)


class EmailVerificationRequest(BaseModel):
    token: str = Field(..., min_length=10)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=50)


class AdminCreateUserRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)
    confirm_password: str = Field(..., min_length=8, max_length=64)
    full_name: str | None = Field(default=None, max_length=50)
    role: str = Field(..., description="superuser/admin/operator/member")


class AdminUpdateUserRoleRequest(BaseModel):
    role: str = Field(..., description="superuser/admin/operator/member")


class AdminUpdateUserStatusRequest(BaseModel):
    is_active: bool


class AdminPolicyUpdateRequest(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class AuditLogQuery(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)


class AuditLogItem(BaseModel):
    audit_log_id: str
    actor_user_id: str = ""
    actor_username: str = ""
    action: str = ""
    target_type: str = ""
    target_id: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class AdminUserListResponse(BaseModel):
    count: int
    users: list[PublicUser] = Field(default_factory=list)


class AdminPolicyResponse(BaseModel):
    policies: dict[str, Any] = Field(default_factory=dict)


class AdminAuditLogListResponse(BaseModel):
    count: int
    logs: list[AuditLogItem] = Field(default_factory=list)