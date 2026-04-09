# app/services/response_localizer.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from copy import deepcopy  # 원본 응답 안전 복사
from typing import Any  # dict/list 타입 힌트 보조

from app.services.translator import translate_text  # 응답 텍스트 번역


def _translate_result_item(
    item: dict[str, Any],
    target_lang: str,
) -> dict[str, Any]:
    localized = dict(item)

    if localized.get("title"):
        localized["title"] = translate_text(
            localized["title"],
            target_lang=target_lang,
        )

    if localized.get("summary"):
        localized["summary"] = translate_text(
            localized["summary"],
            target_lang=target_lang,
        )

    return localized


def _translate_question_suggestions(
    suggestions: list[Any],
    target_lang: str,
) -> list[Any]:
    translated_items: list[Any] = []

    for item in suggestions:
        if not item:
            translated_items.append(item)
            continue

        translated_items.append(
            translate_text(
                str(item),
                target_lang=target_lang,
            ),
        )

    return translated_items


def _translate_results_list(
    items: list[Any],
    target_lang: str,
) -> list[Any]:
    translated_items: list[Any] = []

    for item in items:
        if not isinstance(item, dict):
            translated_items.append(item)
            continue

        translated_items.append(
            _translate_result_item(
                item=item,
                target_lang=target_lang,
            ),
        )

    return translated_items


def _translate_guidance(
    guidance: dict[str, Any],
    target_lang: str,
) -> dict[str, Any]:
    localized_guidance = dict(guidance)

    # notice는 서비스 공통 문구라 언어별 고정값 유지
    localized_guidance["notice"] = "이 서비스는 정보 제공용이며 의학적 진단이 아닙니다."

    if localized_guidance.get("triage_message"):
        localized_guidance["triage_message"] = translate_text(
            localized_guidance["triage_message"],
            target_lang=target_lang,
        )

    suggestions = localized_guidance.get("question_suggestions", [])
    if isinstance(suggestions, list):
        localized_guidance["question_suggestions"] = _translate_question_suggestions(
            suggestions=suggestions,
            target_lang=target_lang,
        )

    return localized_guidance


def _translate_results_bundle(
    results_bundle: dict[str, Any],
    target_lang: str,
) -> dict[str, Any]:
    localized_bundle = dict(results_bundle)

    top_result = localized_bundle.get("top_result")
    if isinstance(top_result, dict):
        localized_bundle["top_result"] = _translate_result_item(
            item=top_result,
            target_lang=target_lang,
        )

    results = localized_bundle.get("results", [])
    if isinstance(results, list):
        localized_bundle["results"] = _translate_results_list(
            items=results,
            target_lang=target_lang,
        )

    related_topics = localized_bundle.get("related_topics", [])
    if isinstance(related_topics, list):
        localized_bundle["related_topics"] = _translate_results_list(
            items=related_topics,
            target_lang=target_lang,
        )

    if localized_bundle.get("ai_summary"):
        localized_bundle["ai_summary"] = translate_text(
            localized_bundle["ai_summary"],
            target_lang=target_lang,
        )

    # 유지보수 포인트:
    # summary_debug는 Swagger/디버깅 용도이므로 번역하지 않는다.
    # 모델 출력 품질 분석 시 원문 기준으로 보는 편이 안정적이다.
    if "summary_debug" in localized_bundle:
        localized_bundle["summary_debug"] = localized_bundle.get("summary_debug")

    return localized_bundle


def _translate_message(
    message: str | None,
    target_lang: str,
) -> str | None:
    if not message:
        return message

    return translate_text(
        message,
        target_lang=target_lang,
    )


def _should_skip_localization(target_lang: str) -> bool:
    if target_lang == "en":
        return True

    if target_lang != "ko":
        return True

    return False


def localize_response(
    data: dict[str, Any],
    target_lang: str,
) -> dict[str, Any]:
    result = deepcopy(data)

    if _should_skip_localization(target_lang):
        return result

    guidance = result.get("guidance", {})
    if isinstance(guidance, dict):
        result["guidance"] = _translate_guidance(
            guidance=guidance,
            target_lang="ko",
        )

    results_bundle = result.get("results_bundle", {})
    if isinstance(results_bundle, dict):
        result["results_bundle"] = _translate_results_bundle(
            results_bundle=results_bundle,
            target_lang="ko",
        )

    result["message"] = _translate_message(
        message=result.get("message"),
        target_lang="ko",
    )

    return result