# app/services/medlineplus_client.py
# app/services/medlineplus_client.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
import re  # HTML 태그 제거
import time  # 캐시 TTL 계산
import xml.etree.ElementTree as ET  # XML 응답 파싱
from collections import OrderedDict  # LRU 스타일 캐시 관리
from typing import Any  # 타입 힌트 보조

import requests  # 외부 HTTP 요청

from app.core.settings import ENABLE_EXTERNAL_SEARCH_CACHE  # 외부 검색 캐시 사용 여부
from app.core.settings import MEDLINEPLUS_BASE_URL  # MedlinePlus base url
from app.core.settings import MEDLINEPLUS_CACHE_MAX_SIZE  # 캐시 최대 개수
from app.core.settings import MEDLINEPLUS_CACHE_TTL_SECONDS  # 캐시 TTL
from app.core.settings import MEDLINEPLUS_RETMAX  # 검색 개수 설정
from app.core.settings import MEDLINEPLUS_TIMEOUT_SECONDS  # 외부 요청 타임아웃
from app.core.symptom_rules import MEDLINEPLUS_SOURCE_NAME  # 소스명 상수

logger = logging.getLogger(__name__)

_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_CACHE_STATS = {
    "hit_count": 0,
    "miss_count": 0,
    "request_count": 0,
    "error_count": 0,
}


def strip_html_tags(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _normalize_cache_key(query: str) -> str:
    return (query or "").strip().lower()


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
        "source": MEDLINEPLUS_SOURCE_NAME,
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


def _is_cache_enabled() -> bool:
    return ENABLE_EXTERNAL_SEARCH_CACHE


def _is_cache_entry_valid(cached_at: float) -> bool:
    return (time.time() - cached_at) < MEDLINEPLUS_CACHE_TTL_SECONDS


def _read_from_cache(cache_key: str) -> list[dict[str, str]] | None:
    if not _is_cache_enabled():
        return None

    cached = _CACHE.get(cache_key)
    if not cached:
        _CACHE_STATS["miss_count"] += 1
        return None

    cached_at = float(cached.get("cached_at", 0.0))
    if not _is_cache_entry_valid(cached_at):
        _CACHE.pop(cache_key, None)
        _CACHE_STATS["miss_count"] += 1
        return None

    _CACHE.move_to_end(cache_key)
    _CACHE_STATS["hit_count"] += 1
    return list(cached.get("items", []))


def _write_to_cache(cache_key: str, items: list[dict[str, str]]) -> None:
    if not _is_cache_enabled():
        return

    _CACHE[cache_key] = {
        "cached_at": time.time(),
        "items": list(items),
    }
    _CACHE.move_to_end(cache_key)

    while len(_CACHE) > MEDLINEPLUS_CACHE_MAX_SIZE:
        _CACHE.popitem(last=False)


def _parse_search_results(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    results: list[dict[str, str]] = []

    for doc in root.findall(".//document"):
        item = _extract_document_item(doc)
        if item["title"]:
            results.append(item)

    return results


def search_medlineplus(query: str) -> list[dict[str, str]]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    _CACHE_STATS["request_count"] += 1
    cache_key = _normalize_cache_key(cleaned_query)

    cached_items = _read_from_cache(cache_key)
    if cached_items is not None:
        return cached_items

    params = _build_query_params(cleaned_query)

    try:
        response = requests.get(
            MEDLINEPLUS_BASE_URL,
            params=params,
            timeout=MEDLINEPLUS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        results = _parse_search_results(response.text)
        _write_to_cache(cache_key, results)
        return results

    except requests.RequestException as error:
        _CACHE_STATS["error_count"] += 1
        logger.warning("[MEDLINEPLUS] request failed: query=%s error=%s", cleaned_query, error)
        return []

    except ET.ParseError as error:
        _CACHE_STATS["error_count"] += 1
        logger.warning("[MEDLINEPLUS] parse failed: query=%s error=%s", cleaned_query, error)
        return []


def get_medlineplus_cache_stats() -> dict[str, Any]:
    return {
        "enabled": _is_cache_enabled(),
        "ttl_seconds": MEDLINEPLUS_CACHE_TTL_SECONDS,
        "max_size": MEDLINEPLUS_CACHE_MAX_SIZE,
        "current_size": len(_CACHE),
        "hit_count": int(_CACHE_STATS["hit_count"]),
        "miss_count": int(_CACHE_STATS["miss_count"]),
        "request_count": int(_CACHE_STATS["request_count"]),
        "error_count": int(_CACHE_STATS["error_count"]),
    }