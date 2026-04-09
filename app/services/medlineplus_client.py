# app/services/medlineplus_client.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
import re  # HTML 태그 제거
import time  # TTL 캐시 만료 계산
import xml.etree.ElementTree as ET  # XML 응답 파싱

import requests  # 외부 HTTP 요청

from app.core.settings import ENABLE_EXTERNAL_SEARCH_CACHE  # 외부 검색 캐시 사용 여부
from app.core.settings import MEDLINEPLUS_BASE_URL  # MedlinePlus API 주소
from app.core.settings import MEDLINEPLUS_CACHE_MAX_SIZE  # 캐시 최대 개수
from app.core.settings import MEDLINEPLUS_CACHE_TTL_SECONDS  # 캐시 유지 시간
from app.core.settings import MEDLINEPLUS_RETMAX  # 검색 개수 설정
from app.core.settings import MEDLINEPLUS_TIMEOUT_SECONDS  # 외부 요청 타임아웃


logger = logging.getLogger(__name__)

_CACHE: dict[str, dict[str, object]] = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0


def strip_html_tags(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _build_query_params(query: str) -> dict[str, str | int]:
    return {
        "db": "healthTopics",
        "term": query,
        "retmax": MEDLINEPLUS_RETMAX,
    }


def _extract_document_item(doc: ET.Element) -> dict[str, str]:
    item = {
        "title": "",
        "url": doc.attrib.get("url", "").strip(),
        "summary": "",
        "source": "MedlinePlus",
        "document_type": "external",
    }

    for content in doc.findall("content"):
        name = content.attrib.get("name", "").lower()
        text = "".join(content.itertext()).strip()

        if name == "title":
            item["title"] = strip_html_tags(text)
        elif name in ("fullsummary", "full-summary", "snippet"):
            cleaned = strip_html_tags(text)
            if not item["summary"] and cleaned:
                item["summary"] = cleaned
        elif name == "groupname":
            cleaned = strip_html_tags(text)
            if not item["summary"] and cleaned:
                item["summary"] = cleaned

    return item


def _cleanup_cache() -> None:
    if len(_CACHE) <= MEDLINEPLUS_CACHE_MAX_SIZE:
        return

    sorted_items = sorted(
        _CACHE.items(),
        key=lambda item: float(item[1].get("saved_at", 0.0)),
    )

    remove_count = len(_CACHE) - MEDLINEPLUS_CACHE_MAX_SIZE
    for key, _ in sorted_items[:remove_count]:
        _CACHE.pop(key, None)


def _get_cached_results(query: str) -> list[dict[str, str]] | None:
    global _CACHE_HITS, _CACHE_MISSES

    if not ENABLE_EXTERNAL_SEARCH_CACHE:
        _CACHE_MISSES += 1
        return None

    cached = _CACHE.get(query)
    if not cached:
        _CACHE_MISSES += 1
        return None

    saved_at = float(cached.get("saved_at", 0.0))
    if (time.time() - saved_at) > MEDLINEPLUS_CACHE_TTL_SECONDS:
        _CACHE.pop(query, None)
        _CACHE_MISSES += 1
        return None

    _CACHE_HITS += 1
    return list(cached.get("results", []))


def _save_cache(query: str, results: list[dict[str, str]]) -> None:
    if not ENABLE_EXTERNAL_SEARCH_CACHE:
        return

    _CACHE[query] = {
        "saved_at": time.time(),
        "results": results,
    }
    _cleanup_cache()


def get_medlineplus_cache_stats() -> dict[str, int | bool]:
    return {
        "enabled": ENABLE_EXTERNAL_SEARCH_CACHE,
        "cache_size": len(_CACHE),
        "hits": _CACHE_HITS,
        "misses": _CACHE_MISSES,
        "ttl_seconds": MEDLINEPLUS_CACHE_TTL_SECONDS,
    }


def clear_medlineplus_cache() -> None:
    _CACHE.clear()


def search_medlineplus(query: str) -> list[dict[str, str]]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    cached_results = _get_cached_results(cleaned_query)
    if cached_results is not None:
        return cached_results

    params = _build_query_params(cleaned_query)

    try:
        response = requests.get(
            MEDLINEPLUS_BASE_URL,
            params=params,
            timeout=MEDLINEPLUS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        results: list[dict[str, str]] = []

        for doc in root.findall(".//document"):
            item = _extract_document_item(doc)
            if item["title"]:
                results.append(item)

        _save_cache(cleaned_query, results)
        return results

    except requests.RequestException as error:
        logger.warning("[MEDLINEPLUS] request failed: %s", error)
        return []

    except ET.ParseError as error:
        logger.warning("[MEDLINEPLUS] parse failed: %s", error)
        return []