# app/core/policy_settings.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

DEFAULT_ADMIN_POLICIES: dict[str, object] = {
    "allow_public_signup": True,
    "require_email_verification": False,
    "allow_operator_user_creation": True,
    "allow_admin_policy_update": True,
    "audit_log_default_limit": 100,
    "max_audit_log_limit": 500,
    "service_mode": "mvp",
    "healthcare_domain_guard_enabled": True,
    "ai_summary_enabled": True,
    "rag_enabled": True,
}