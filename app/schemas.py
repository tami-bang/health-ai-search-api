# app/schemas.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

from typing import Any  # 용도: 가변 debug 필드 타입 정의

from pydantic import BaseModel  # 용도: 요청/응답 스키마 정의
from pydantic import Field  # 용도: 필드 기본값 및 제약 정의


class TopicItem(BaseModel):
    title: str = ""
    summary: str | None = None
    url: str = ""
    source: str | None = None
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
    query: str = Field(
        ...,
        min_length=2,
        description="사용자 증상 또는 상태 입력",
        examples=["숨이 안 쉬어져요"],
    )


class TriageResponse(BaseModel):
    query: str
    detected_language: str
    triage_level: str
    triage_message: str
    triage_score: int
    matched_patterns: list[str]