# app/core/policy_settings.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

DEFAULT_ADMIN_POLICIES: dict[str, object] = {
    "allow_public_signup": True,
    "require_email_verification": False,
    "allow_operator_account_creation": True,
    "enable_ai_summary": True,
    "enable_external_search": True,
    "enable_internal_search": True,
    "enable_triage": True,
    "maintenance_mode": False,
}