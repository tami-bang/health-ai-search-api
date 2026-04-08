# response_enricher.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from typing import Any  # dict/list 타입 힌트 보조

from app.core.settings import AI_SUMMARY_FAIL_OPEN  # 생성 실패 허용 여부
from app.core.settings import AI_SUMMARY_MAX_CONTEXT_CHARS  # 입력 길이 제한
from app.core.settings import AI_SUMMARY_MAX_ITEMS  # 컨텍스트 최대 문서 수
from app.core.settings import ENABLE_AI_SUMMARY  # 생성 기능 사용 여부
from app.services.hf_generation_service import generate_text  # Hugging Face 생성 호출

logger = logging.getLogger(__name__)


def _truncate_text(text: str, max_length: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[:max_length].rstrip()


def _build_context_from_items(items: list[dict[str, Any]]) -> str:
    """
    검색 결과를 생성 모델 입력 컨텍스트로 변환
    - retriever/ranker 구조와 생성 구조를 느슨하게 결합하려고 분리
    """
    lines: list[str] = []

    for index, item in enumerate(items[:AI_SUMMARY_MAX_ITEMS], start=1):
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        url = str(item.get("url", "")).strip()

        block = [
            f"[Document {index}]",
            f"Title: {title}",
            f"Summary: {summary}",
        ]

        if url:
            block.append(f"URL: {url}")

        lines.append("\n".join(block))

    context = "\n\n".join(lines)
    return _truncate_text(context, AI_SUMMARY_MAX_CONTEXT_CHARS)


def _build_summary_prompt(
    query: str,
    detected_language: str,
    context: str,
) -> str:
    """
    모델 프롬프트 생성
    - 언어별 출력을 안정적으로 맞추기 위해 프롬프트에서 제어
    """
    language_name = "Korean" if detected_language == "ko" else "English"

    return f"""
You are a healthcare information assistant.
Use only the provided search results.
Do not diagnose.
Do not invent facts.
Write the answer in {language_name}.

User question:
{query}

Search results:
{context}

Task:
1. Briefly explain the most relevant health topic.
2. Mention 1-2 related considerations only if supported by the search results.
3. Add a short caution that this is informational and not a diagnosis.
4. Keep the answer concise and readable.
""".strip()


def generate_ai_summary(
    query: str,
    detected_language: str,
    ranked_items: list[dict[str, Any]],
) -> str | None:
    """
    검색 결과 기반 AI 요약 생성
    - 결과가 없으면 생성하지 않음
    - 실패해도 검색 API 전체가 죽지 않게 fail-open 유지
    """
    if not ENABLE_AI_SUMMARY:
        return None

    if not ranked_items:
        return None

    try:
        context = _build_context_from_items(ranked_items)
        if not context:
            return None

        prompt = _build_summary_prompt(
            query=query,
            detected_language=detected_language,
            context=context,
        )
        summary = generate_text(prompt)
        cleaned_summary = (summary or "").strip()

        return cleaned_summary or None

    except Exception as error:
        logger.warning("[AI_SUMMARY] generation failed: %s", error)

        if AI_SUMMARY_FAIL_OPEN:
            return None

        raise