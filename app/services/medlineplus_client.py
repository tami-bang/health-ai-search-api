# medlineplus_client.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import re  # HTML 태그 제거
import xml.etree.ElementTree as ET  # XML 응답 파싱

import requests  # 외부 HTTP 요청

from app.core.symptom_rules import MEDLINEPLUS_RETMAX  # 검색 개수 설정


BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"


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


def search_medlineplus(query: str) -> list[dict[str, str]]:
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    params = _build_query_params(cleaned_query)

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        results: list[dict[str, str]] = []

        for doc in root.findall(".//document"):
            item = _extract_document_item(doc)
            if item["title"]:
                results.append(item)

        return results

    except requests.RequestException as error:
        return [{
            "title": "Request Error",
            "url": "",
            "summary": str(error),
            "source": "MedlinePlus",
            "document_type": "external_error",
        }]
    except ET.ParseError as error:
        return [{
            "title": "Parse Error",
            "url": "",
            "summary": str(error),
            "source": "MedlinePlus",
            "document_type": "external_error",
        }]