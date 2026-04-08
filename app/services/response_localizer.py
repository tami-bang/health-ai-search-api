# response_localizer.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from copy import deepcopy  # 원본 응답 안전 복사

from app.services.translator import translate_text  # 응답 텍스트 번역


def _translate_result_item(item: dict, target_lang: str) -> dict:
    localized = dict(item)

    if localized.get("title"):
        localized["title"] = translate_text(localized["title"], target_lang=target_lang)

    if localized.get("summary"):
        localized["summary"] = translate_text(localized["summary"], target_lang=target_lang)

    return localized


def localize_response(data: dict, target_lang: str) -> dict:
    result = deepcopy(data)

    if target_lang == "en":
        return result

    if target_lang != "ko":
        return result

    guidance = result.get("guidance", {})
    if isinstance(guidance, dict):
        guidance["notice"] = "이 서비스는 정보 제공용이며 의학적 진단이 아닙니다."

        if guidance.get("triage_message"):
            guidance["triage_message"] = translate_text(
                guidance["triage_message"],
                target_lang="ko",
            )

        suggestions = guidance.get("question_suggestions", [])
        if isinstance(suggestions, list):
            guidance["question_suggestions"] = [
                translate_text(item, target_lang="ko") if item else item
                for item in suggestions
            ]

    results_bundle = result.get("results_bundle", {})
    if isinstance(results_bundle, dict):
        top_result = results_bundle.get("top_result")
        if isinstance(top_result, dict):
            results_bundle["top_result"] = _translate_result_item(top_result, target_lang="ko")

        results = results_bundle.get("results", [])
        if isinstance(results, list):
            results_bundle["results"] = [
                _translate_result_item(item, target_lang="ko") if isinstance(item, dict) else item
                for item in results
            ]

        related_topics = results_bundle.get("related_topics", [])
        if isinstance(related_topics, list):
            results_bundle["related_topics"] = [
                _translate_result_item(item, target_lang="ko") if isinstance(item, dict) else item
                for item in related_topics
            ]

        if results_bundle.get("ai_summary"):
            results_bundle["ai_summary"] = translate_text(
                results_bundle["ai_summary"],
                target_lang="ko",
            )

    if result.get("message"):
        result["message"] = translate_text(result["message"], target_lang="ko")

    return result