# app/services/response_enricher.py
from __future__ import annotations  # 용도: 최신 타입 힌트 문법 지원

import logging  # 용도: 실행 로그 기록
import re  # 용도: 텍스트 정리 처리
from typing import Any  # 용도: dict/list 타입 힌트 보조

from app.core.settings import AI_SUMMARY_CONTEXT_CANDIDATE_POOL  # 용도: context 후보 pool 크기
from app.core.settings import AI_SUMMARY_CONTEXT_INCLUDE_SOURCE  # 용도: source 포함 여부
from app.core.settings import AI_SUMMARY_CONTEXT_INCLUDE_URL  # 용도: url 포함 여부
from app.core.settings import AI_SUMMARY_EN_DISCLAIMER  # 용도: 영문 주의 문구
from app.core.settings import AI_SUMMARY_FAIL_OPEN  # 용도: 요약 실패 허용 여부
from app.core.settings import AI_SUMMARY_FALLBACK_RESULT_LIMIT  # 용도: fallback 결과 개수
from app.core.settings import AI_SUMMARY_FALLBACK_SENTENCE_LIMIT  # 용도: fallback 문장 수
from app.core.settings import AI_SUMMARY_ITEM_SUMMARY_MAX_CHARS  # 용도: 결과 summary 길이 제한
from app.core.settings import AI_SUMMARY_ITEM_TITLE_MAX_CHARS  # 용도: 결과 title 길이 제한
from app.core.settings import AI_SUMMARY_KO_DISCLAIMER  # 용도: 국문 주의 문구
from app.core.settings import AI_SUMMARY_MAX_CONTEXT_CHARS  # 용도: 요약 컨텍스트 길이 제한
from app.core.settings import AI_SUMMARY_MAX_ITEMS  # 용도: 요약 대상 결과 수 제한
from app.core.settings import AI_SUMMARY_MAX_SYMPTOM_HINTS  # 용도: symptom hint 수 제한
from app.core.settings import AI_SUMMARY_MIN_CONTEXT_OVERLAP_COUNT  # 용도: context 겹침 최소치
from app.core.settings import AI_SUMMARY_MIN_OUTPUT_CHARS  # 용도: 최소 출력 길이
from app.core.settings import AI_SUMMARY_MAX_UNSUPPORTED_KEYWORD_COUNT  # 용도: 허용할 비지원 키워드 수
from app.core.settings import AI_SUMMARY_PREFER_DIVERSE_RESULTS  # 용도: 결과 다양성 우선 여부
from app.core.settings import AI_SUMMARY_PROMPT_LOG_MAX_CHARS  # 용도: 프롬프트 로그 길이 제한
from app.core.settings import AI_SUMMARY_RAW_OUTPUT_LOG_MAX_CHARS  # 용도: raw 출력 로그 길이 제한
from app.core.settings import AI_SUMMARY_REQUIRE_HINT_MATCH  # 용도: symptom hint 필수 여부
from app.core.settings import AI_SUMMARY_SENTENCE_LIMIT  # 용도: 최종 문장 수 제한
from app.core.settings import ENABLE_AI_SUMMARY  # 용도: AI 요약 활성화 여부
from app.services.hf_generation_service import generate_text  # 용도: Hugging Face 텍스트 생성 호출

logger = logging.getLogger(__name__)

SUMMARY_OUTPUT_PREFIX_PATTERNS = [
    r"^(summary)\s*:\s*",
    r"^(answer)\s*:\s*",
    r"^(response)\s*:\s*",
    r"^(요약)\s*:\s*",
    r"^(답변)\s*:\s*",
    r"^(응답)\s*:\s*",
]

SUMMARY_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your",
    "have", "has", "been", "will", "would", "could", "should", "about",
    "than", "then", "them", "they", "their", "there", "when", "what",
    "where", "which", "while", "these", "those", "because", "through",
    "general", "information", "health", "medical", "result", "results",
    "using", "used", "common", "more", "most", "some", "such", "only",
    "user", "query", "symptom", "symptoms", "질문", "증상", "정보", "검색",
    "결과", "사용자", "관련", "대한", "있는", "없는", "작성", "요약", "답변",
}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _truncate_text(
    text: str,
    max_chars: int,
) -> str:
    cleaned_text = _normalize_whitespace(text)
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    return cleaned_text[: max_chars - 3].rstrip() + "..."


def _split_sentences(text: str) -> list[str]:
    normalized_text = _normalize_whitespace(text)
    if not normalized_text:
        return []

    normalized_text = normalized_text.replace("!", ".").replace("?", ".")
    raw_sentences = normalized_text.split(".")

    return [
        sentence.strip()
        for sentence in raw_sentences
        if sentence and sentence.strip()
    ]


def _trim_to_sentence_limit(
    text: str,
    sentence_limit: int,
) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return _normalize_whitespace(text)

    trimmed_sentences = sentences[:sentence_limit]
    return ". ".join(trimmed_sentences).strip() + "."


def _parse_symptom_hints(normalized_query: str | None) -> list[str]:
    cleaned_query = _normalize_whitespace(normalized_query or "").lower()
    if not cleaned_query:
        return []

    if "|" not in cleaned_query:
        return [cleaned_query][:AI_SUMMARY_MAX_SYMPTOM_HINTS]

    hints = [
        token.strip()
        for token in cleaned_query.split("|")
        if token and token.strip()
    ]
    return hints[:AI_SUMMARY_MAX_SYMPTOM_HINTS]


def _has_summary_source_content(
    item: dict[str, Any],
) -> bool:
    title = _normalize_whitespace(item.get("title", ""))
    summary = _normalize_whitespace(item.get("summary", ""))
    return bool(title or summary)


def _extract_item_signature(
    item: dict[str, Any],
) -> tuple[str, str]:
    title = _normalize_whitespace(item.get("title", "")).lower()
    source = _normalize_whitespace(item.get("source", "")).lower()
    return title, source


def _extract_search_text(
    item: dict[str, Any],
) -> str:
    title = _normalize_whitespace(item.get("title", ""))
    summary = _normalize_whitespace(item.get("summary", ""))
    return f"{title} {summary}".strip().lower()


def _count_title_hint_matches(
    item: dict[str, Any],
    symptom_hints: list[str],
) -> int:
    if not symptom_hints:
        return 0

    title_text = _normalize_whitespace(item.get("title", "")).lower()
    if not title_text:
        return 0

    return sum(1 for hint in symptom_hints if hint and hint in title_text)


def _count_text_hint_matches(
    item: dict[str, Any],
    symptom_hints: list[str],
) -> int:
    if not symptom_hints:
        return 0

    search_text = _extract_search_text(item)
    return sum(1 for hint in symptom_hints if hint and hint in search_text)


def _score_summary_item(
    item: dict[str, Any],
    symptom_hints: list[str],
) -> tuple[int, int, float, float, float]:
    """
    summary용 item 선별은 rerank 결과를 무시하지 않되,
    사용자 질의 symptom hint를 더 넓게 커버하는 결과를 우선한다.
    """
    text_hint_match_count = _count_text_hint_matches(item, symptom_hints)
    title_hint_match_count = _count_title_hint_matches(item, symptom_hints)
    hybrid_score = float(item.get("hybrid_score", 0.0) or 0.0)
    semantic_score = float(item.get("semantic_score", 0.0) or 0.0)
    keyword_boost = float(item.get("keyword_boost", 0.0) or 0.0)

    return (
        text_hint_match_count,
        title_hint_match_count,
        hybrid_score,
        semantic_score,
        keyword_boost,
    )


def _select_diverse_summary_items(
    ranked_items: list[dict[str, Any]],
    symptom_hints: list[str],
) -> list[dict[str, Any]]:
    candidate_items = ranked_items[:AI_SUMMARY_CONTEXT_CANDIDATE_POOL]
    if not candidate_items:
        return []

    sorted_candidates = sorted(
        candidate_items,
        key=lambda item: _score_summary_item(item, symptom_hints),
        reverse=True,
    )

    selected_items: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, str]] = set()

    for item in sorted_candidates:
        if not _has_summary_source_content(item):
            continue

        signature = _extract_item_signature(item)
        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        selected_items.append(item)

        if len(selected_items) >= AI_SUMMARY_MAX_ITEMS:
            break

    return selected_items


def _select_ordered_summary_items(
    ranked_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_items: list[dict[str, Any]] = []

    for item in ranked_items:
        if not _has_summary_source_content(item):
            continue

        selected_items.append(item)

        if len(selected_items) >= AI_SUMMARY_MAX_ITEMS:
            break

    return selected_items


def select_summary_items(
    ranked_items: list[dict[str, Any]],
    normalized_query: str | None,
) -> list[dict[str, Any]]:
    symptom_hints = _parse_symptom_hints(normalized_query)

    if AI_SUMMARY_PREFER_DIVERSE_RESULTS:
        diverse_items = _select_diverse_summary_items(
            ranked_items=ranked_items,
            symptom_hints=symptom_hints,
        )
        if diverse_items:
            return diverse_items

    return _select_ordered_summary_items(ranked_items)


def _build_context_block_lines(
    item: dict[str, Any],
    index: int,
) -> list[str]:
    title = _truncate_text(
        item.get("title", ""),
        AI_SUMMARY_ITEM_TITLE_MAX_CHARS,
    )
    summary = _truncate_text(
        item.get("summary", ""),
        AI_SUMMARY_ITEM_SUMMARY_MAX_CHARS,
    )
    source = _normalize_whitespace(item.get("source", ""))
    url = _normalize_whitespace(item.get("url", ""))

    block_lines: list[str] = [f"[Result {index}]"]

    if title:
        block_lines.append(f"Title: {title}")

    if summary:
        block_lines.append(f"Summary: {summary}")

    if AI_SUMMARY_CONTEXT_INCLUDE_SOURCE and source:
        block_lines.append(f"Source: {source}")

    if AI_SUMMARY_CONTEXT_INCLUDE_URL and url:
        block_lines.append(f"URL: {url}")

    return block_lines


def _build_context_blocks(
    ranked_items: list[dict[str, Any]],
    normalized_query: str | None,
) -> list[str]:
    context_blocks: list[str] = []

    selected_items = select_summary_items(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )

    for index, item in enumerate(selected_items, start=1):
        block_lines = _build_context_block_lines(
            item=item,
            index=index,
        )
        context_blocks.append("\n".join(block_lines).strip())

    return context_blocks


def _build_summary_context(
    ranked_items: list[dict[str, Any]],
    normalized_query: str | None,
) -> str:
    context_blocks = _build_context_blocks(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )
    if not context_blocks:
        return ""

    joined_context = "\n\n".join(context_blocks).strip()
    return _truncate_text(
        joined_context,
        AI_SUMMARY_MAX_CONTEXT_CHARS,
    )


def _build_symptom_hint_text(
    normalized_query: str | None,
) -> str:
    symptom_hints = _parse_symptom_hints(normalized_query)
    if not symptom_hints:
        return ""

    return ", ".join(symptom_hints)


def _build_ko_prompt(
    query: str,
    normalized_query: str | None,
    context_text: str,
) -> str:
    cleaned_query = _normalize_whitespace(query)
    hint_text = _build_symptom_hint_text(normalized_query)

    prompt_lines = [
        "다음 의료 검색 결과만 사용해서 사용자의 증상 질문에 대한 건강 정보 요약을 작성하라.",
        "규칙:",
        "1. 반드시 제공된 검색 결과에 있는 정보만 사용한다.",
        "2. 진단을 확정하지 않는다.",
        "3. 추측하거나 없는 정보를 추가하지 않는다.",
        "4. 질문에 포함된 주요 증상을 함께 반영한다.",
        "5. 핵심 정보와 일반적 주의사항을 최대 2문장으로 작성한다.",
        "6. 불필요한 서론 없이 바로 답변한다.",
        "",
        f"사용자 질문: {cleaned_query}",
    ]

    if hint_text:
        prompt_lines.append(f"핵심 증상 힌트: {hint_text}")

    prompt_lines.extend([
        "",
        f"검색 결과:\n{context_text}",
        "",
        "답변:",
    ])

    return "\n".join(prompt_lines).strip()


def _build_en_prompt(
    query: str,
    normalized_query: str | None,
    context_text: str,
) -> str:
    cleaned_query = _normalize_whitespace(query)
    hint_text = _build_symptom_hint_text(normalized_query)

    prompt_lines = [
        "Write a short health-information summary using only the search results below.",
        "Rules:",
        "1. Use only the provided results.",
        "2. Do not provide a definitive diagnosis.",
        "3. Do not add unsupported facts.",
        "4. Reflect the main symptoms in the user's query.",
        "5. Write the key information and practical caution in no more than 2 sentences.",
        "6. Start directly without extra introduction.",
        "",
        f"User query: {cleaned_query}",
    ]

    if hint_text:
        prompt_lines.append(f"Main symptom hints: {hint_text}")

    prompt_lines.extend([
        "",
        f"Search results:\n{context_text}",
        "",
        "Answer:",
    ])

    return "\n".join(prompt_lines).strip()


def _build_summary_prompt(
    query: str,
    detected_language: str,
    normalized_query: str | None,
    context_text: str,
) -> str:
    if detected_language == "ko":
        return _build_ko_prompt(
            query=query,
            normalized_query=normalized_query,
            context_text=context_text,
        )

    return _build_en_prompt(
        query=query,
        normalized_query=normalized_query,
        context_text=context_text,
    )


def _remove_output_prefixes(text: str) -> str:
    cleaned_text = _normalize_whitespace(text)

    for pattern in SUMMARY_OUTPUT_PREFIX_PATTERNS:
        cleaned_text = re.sub(
            pattern,
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

    return cleaned_text.strip()


def _clean_generated_summary(summary_text: str) -> str:
    cleaned_summary = _remove_output_prefixes(summary_text)
    cleaned_summary = _trim_to_sentence_limit(
        text=cleaned_summary,
        sentence_limit=AI_SUMMARY_SENTENCE_LIMIT,
    )

    return cleaned_summary.strip()


def _get_disclaimer(detected_language: str) -> str:
    if detected_language == "ko":
        return AI_SUMMARY_KO_DISCLAIMER

    return AI_SUMMARY_EN_DISCLAIMER


def _append_disclaimer(
    summary_text: str,
    detected_language: str,
) -> str:
    cleaned_summary = _normalize_whitespace(summary_text)
    if not cleaned_summary:
        return ""

    disclaimer = _normalize_whitespace(_get_disclaimer(detected_language))
    if not disclaimer:
        return cleaned_summary

    if disclaimer in cleaned_summary:
        return cleaned_summary

    return f"{cleaned_summary} {disclaimer}".strip()


def _validate_summary_output(summary_text: str) -> str:
    cleaned_summary = _clean_generated_summary(summary_text)
    if len(cleaned_summary) < AI_SUMMARY_MIN_OUTPUT_CHARS:
        logger.warning(
            "[SUMMARY] output rejected reason=too_short chars=%s text=%s",
            len(cleaned_summary),
            cleaned_summary,
        )
        return ""

    return cleaned_summary


def _build_log_preview(
    text: str,
    max_chars: int,
) -> str:
    return _truncate_text(text, max_chars)


def _build_extractive_summary_block(
    item: dict[str, Any],
) -> str:
    title = _normalize_whitespace(item.get("title", ""))
    summary = _normalize_whitespace(item.get("summary", ""))

    if not summary:
        return ""

    trimmed_summary = _trim_to_sentence_limit(
        text=summary,
        sentence_limit=AI_SUMMARY_FALLBACK_SENTENCE_LIMIT,
    )

    if title:
        return f"{title}: {trimmed_summary}"

    return trimmed_summary


def build_extractive_summary(
    ranked_items: list[dict[str, Any]],
    normalized_query: str | None = None,
) -> str | None:
    fallback_blocks: list[str] = []
    selected_items = select_summary_items(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )

    for item in selected_items[:AI_SUMMARY_FALLBACK_RESULT_LIMIT]:
        block = _build_extractive_summary_block(item)
        if not block:
            continue

        fallback_blocks.append(block)

    if not fallback_blocks:
        return None

    return " ".join(fallback_blocks).strip()


def _extract_keywords(text: str) -> set[str]:
    raw_tokens = re.findall(r"[a-zA-Z]{3,}|[가-힣]{2,}", _normalize_whitespace(text).lower())

    return {
        token
        for token in raw_tokens
        if token not in SUMMARY_STOPWORDS
    }


def _collect_context_keywords(
    selected_items: list[dict[str, Any]],
) -> set[str]:
    context_text_parts: list[str] = []

    for item in selected_items:
        title = _normalize_whitespace(item.get("title", ""))
        summary = _normalize_whitespace(item.get("summary", ""))

        if title:
            context_text_parts.append(title)

        if summary:
            context_text_parts.append(summary)

    return _extract_keywords(" ".join(context_text_parts))


def _collect_summary_keywords(
    summary_text: str,
) -> set[str]:
    return _extract_keywords(summary_text)


def _count_context_overlap(
    summary_keywords: set[str],
    context_keywords: set[str],
) -> int:
    return len(summary_keywords & context_keywords)


def _count_unsupported_keywords(
    summary_keywords: set[str],
    context_keywords: set[str],
) -> int:
    return len(summary_keywords - context_keywords)


def _has_required_hint_match(
    cleaned_summary: str,
    symptom_hints: list[str],
) -> bool:
    if not symptom_hints:
        return True

    lowered_summary = cleaned_summary.lower()
    return any(hint in lowered_summary for hint in symptom_hints if hint)


def evaluate_summary_quality(
    summary_text: str | None,
    normalized_query: str | None,
    ranked_items: list[dict[str, Any]],
) -> dict[str, Any]:
    cleaned_summary = _normalize_whitespace(summary_text or "")
    symptom_hints = _parse_symptom_hints(normalized_query)
    selected_items = select_summary_items(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )
    selected_titles = [
        _normalize_whitespace(item.get("title", ""))
        for item in selected_items
        if _normalize_whitespace(item.get("title", ""))
    ]

    if not cleaned_summary:
        return {
            "is_valid": False,
            "reason": "empty_summary",
            "symptom_hints": symptom_hints,
            "selected_titles": selected_titles,
            "context_overlap_count": 0,
            "unsupported_keyword_count": 0,
            "required_hint_matched": False,
        }

    summary_keywords = _collect_summary_keywords(cleaned_summary)
    context_keywords = _collect_context_keywords(selected_items)
    context_overlap_count = _count_context_overlap(
        summary_keywords=summary_keywords,
        context_keywords=context_keywords,
    )
    unsupported_keyword_count = _count_unsupported_keywords(
        summary_keywords=summary_keywords,
        context_keywords=context_keywords,
    )
    required_hint_matched = _has_required_hint_match(
        cleaned_summary=cleaned_summary,
        symptom_hints=symptom_hints,
    )

    if AI_SUMMARY_REQUIRE_HINT_MATCH and symptom_hints and not required_hint_matched:
        return {
            "is_valid": False,
            "reason": "missing_symptom_hint",
            "symptom_hints": symptom_hints,
            "selected_titles": selected_titles,
            "context_overlap_count": context_overlap_count,
            "unsupported_keyword_count": unsupported_keyword_count,
            "required_hint_matched": required_hint_matched,
        }

    if context_overlap_count < AI_SUMMARY_MIN_CONTEXT_OVERLAP_COUNT:
        return {
            "is_valid": False,
            "reason": "low_context_overlap",
            "symptom_hints": symptom_hints,
            "selected_titles": selected_titles,
            "context_overlap_count": context_overlap_count,
            "unsupported_keyword_count": unsupported_keyword_count,
            "required_hint_matched": required_hint_matched,
        }

    if unsupported_keyword_count > AI_SUMMARY_MAX_UNSUPPORTED_KEYWORD_COUNT:
        return {
            "is_valid": False,
            "reason": "too_many_unsupported_keywords",
            "symptom_hints": symptom_hints,
            "selected_titles": selected_titles,
            "context_overlap_count": context_overlap_count,
            "unsupported_keyword_count": unsupported_keyword_count,
            "required_hint_matched": required_hint_matched,
        }

    return {
        "is_valid": True,
        "reason": "accepted",
        "symptom_hints": symptom_hints,
        "selected_titles": selected_titles,
        "context_overlap_count": context_overlap_count,
        "unsupported_keyword_count": unsupported_keyword_count,
        "required_hint_matched": required_hint_matched,
    }


def build_summary_debug(
    detected_language: str,
    normalized_query: str | None,
    ranked_items: list[dict[str, Any]],
    ai_summary: str | None,
    ai_summary_model: str | None,
    quality_result: dict[str, Any] | None,
    summary_status: str,
) -> dict[str, Any]:
    selected_items = select_summary_items(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )

    selected_titles = [
        _normalize_whitespace(item.get("title", ""))
        for item in selected_items
        if _normalize_whitespace(item.get("title", ""))
    ]

    return {
        "detected_language": detected_language,
        "normalized_query": normalized_query,
        "symptom_hints": _parse_symptom_hints(normalized_query),
        "used_result_count": len(selected_items),
        "used_result_titles": selected_titles,
        "summary_generated": bool(ai_summary),
        "summary_model": ai_summary_model,
        "summary_status": summary_status,
        "quality_result": quality_result,
    }


def generate_ai_summary(
    query: str,
    detected_language: str,
    ranked_items: list[dict[str, Any]],
    normalized_query: str | None = None,
) -> str | None:
    if not ENABLE_AI_SUMMARY:
        logger.info("[SUMMARY] skipped reason=disabled")
        return None

    context_text = _build_summary_context(
        ranked_items=ranked_items,
        normalized_query=normalized_query,
    )
    if not context_text:
        logger.warning("[SUMMARY] skipped reason=empty_context")
        return None

    prompt = _build_summary_prompt(
        query=query,
        detected_language=detected_language,
        normalized_query=normalized_query,
        context_text=context_text,
    )

    logger.info(
        "[SUMMARY] prompt=%s",
        _build_log_preview(
            text=prompt,
            max_chars=AI_SUMMARY_PROMPT_LOG_MAX_CHARS,
        ),
    )

    try:
        generated_text = generate_text(prompt)
        logger.info(
            "[SUMMARY] raw_output=%s",
            _build_log_preview(
                text=generated_text,
                max_chars=AI_SUMMARY_RAW_OUTPUT_LOG_MAX_CHARS,
            ),
        )

        validated_summary = _validate_summary_output(generated_text)
        if not validated_summary:
            logger.warning("[SUMMARY] rejected reason=validation_failed")
            return None

        final_summary = _append_disclaimer(
            summary_text=validated_summary,
            detected_language=detected_language,
        )
        logger.info(
            "[SUMMARY] accepted final=%s",
            _build_log_preview(
                text=final_summary,
                max_chars=AI_SUMMARY_RAW_OUTPUT_LOG_MAX_CHARS,
            ),
        )

        return final_summary

    except Exception as error:
        logger.warning("[SUMMARY] generation failed query=%s error=%s", query, error)

        if not AI_SUMMARY_FAIL_OPEN:
            raise

        return None