# 🩺 Health AI Search API

증상 기반 자연어 입력을 처리하여  
검색 → AI → 의사결정까지 수행하는  
FastAPI 기반 헬스케어 AI 검색 시스템

---

## Overview

health-ai-search-api는 단순 검색 API가 아닌  
검색 결과 생성 + 의미 보정 + 위험도 판단까지 포함하는  
End-to-End 처리 시스템입니다.

사용자의 자연어 증상을 입력받아 다음 과정을 수행합니다.

- 증상 정규화 (Normalization)
- 다중 소스 검색 (Hybrid Retrieval)
- AI 기반 재정렬 (Reranking)
- 응급도 판단 (Triage)
- 사용자 응답 생성

---

## Problem

기존 의료 검색 시스템의 구조적 한계

- 자연어 증상과 의료 용어 간 불일치
- 외부 API 결과 품질 편차
- 키워드 기반 검색의 낮은 정확도
- 일부 query에서 결과 미출력 (zero-result)
- LLM 기반 요약 사용 시 latency 증가

---

## Solution Strategy

### 1. Retrieval-first 구조

- LLM 의존도를 낮춘 검색 중심 구조
- 기본 결과를 빠르게 확보
- summary는 optional로 분리

---

### 2. Hybrid Retrieval

다중 검색 소스를 결합하여 결과 누락을 최소화

- Internal Knowledge
- External API (MedlinePlus)
- Vector Semantic Search

→ recall 및 coverage 향상

---

### 3. AI Reranking

검색 결과를 후처리하여 품질 개선

- semantic similarity
- keyword boost
- priority boost

→ relevance 향상

---

### 4. Optional Summary

- summary 선택 실행 구조
- latency와 정보량 간 trade-off 제어

---

## Architecture

    User Query
    → Language Detection
    → Symptom Normalization

    → Hybrid Retrieval
       ├─ Internal
       ├─ External API
       └─ Vector Search

    → AI Reranking
    → Triage Evaluation

    → Response Formatting
    → Optional Summary
    → Localization

    → Final Response

---

## Response Pipeline

1. Input Validation  
2. Language Detection  
3. Symptom Normalization  
4. Retrieval  
5. AI Reranking  
6. Triage Evaluation  
7. Summary (Optional)  
8. Response Formatting  

---

## Performance (Measured)

아래 수치는 로컬 개발 환경에서 직접 측정한 값입니다.  
측정 결과는 external API 호출 여부, 캐시 상태, query 내용에 따라 달라질 수 있습니다.

### Measured Result

| Endpoint | Measured Time | Note |
|------|------:|------|
| /search | 약 3543 ms | external API 호출 포함 |
| /search/summary | 평균 약 143 ms | extractive fallback 기반 |
| /search/summary | 단일 측정 약 171 ms | 단건 실행 기준 |

---

### /search/summary Internal Breakdown

| Stage | Time |
|------|------:|
| normalization | ~92 ms |
| prediction | ~50 ms |
| rerank | ~26 ms |
| retrieval | ~5 ms |
| summary | ~2 ms |

---

### Performance Notes

- `/search`는 external API 의존으로 latency 변동이 큼
- `/search/summary`는 현재 full LLM이 아닌 fallback 기반으로 동작
- 현재 측정값은 “구현 상태 기준 실제 성능”임

---

## Example API

POST /search/summary

    {
      "query": "코피가 30분째 안 멈춰요",
      "include_summary": true
    }

---

Response

    {
      "query": "코피가 30분째 안 멈춰요",
      "guidance": {
        "triage_level": "urgent"
      },
      "results_bundle": {
        "top_result": {
          "title": "Nosebleed"
        },
        "ai_summary": {
          "summary": "지속적인 코피는 추가 확인이 필요합니다."
        }
      }
    }

---

## Current Issues (실제 검증 기반)

| 문제 | 영향 |
|------|------|
| UTF-8 encoding 이슈 | query 깨짐 |
| normalization 실패 | fallback 증가 |
| 일부 query 결과 없음 | UX 저하 |
| irrelevant 결과 | 신뢰도 감소 |
| external API latency | 응답 지연 |

---

## Improvement Roadmap

| 영역 | 계획 |
|------|------|
| Encoding | UTF-8 처리 안정화 |
| Normalization | rule 확장 |
| Retrieval | relevance 개선 |
| External API | 캐싱 적용 |
| Latency | 구조 최적화 |
| Summary | LLM 품질 개선 |
| Architecture | RAG 확장 |

---

## Tech Stack

### Backend
- FastAPI

### AI / NLP
- scikit-learn
- sentence-transformers

### External API
- MedlinePlus

### Language Processing
- deep-translator

---

## Project Structure

    app/
    ├── main.py
    ├── core/
    ├── services/
    ├── data/
    └── schemas.py

---

## What This Project Demonstrates

- Retrieval 중심 AI 시스템 설계
- Hybrid Search Architecture 구현
- AI Reranking 적용
- 의료 UX 기반 Triage 설계
- Latency-aware 구조 설계
- 실제 문제 기반 개선 접근

---

## Author

GitHub: https://github.com/tami-bang