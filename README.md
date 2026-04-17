# 🩺 Health AI Search API

증상 기반 자연어 입력을 의료 정보로 변환하고,  
Hybrid Retrieval + AI Reranking + Optional Summary 구조를 통해  
검색 품질과 응답 성능을 함께 개선하는 헬스케어 AI 검색 API

---

## Overview

health-ai-search-api는 단순 검색 API가 아닌  
검색 → AI → 의사결정 흐름을 통합한 End-to-End 시스템입니다.

사용자의 자연어 증상 입력을 기반으로

- 증상 정규화 (Normalization)
- 다중 소스 검색 (Hybrid Retrieval)
- AI 기반 재정렬 (Reranking)
- 응급도 판단 (Triage)
- 사용자 행동 유도 응답 생성

까지 수행합니다.

---

## Problem

기존 의료 검색 시스템의 한계

- 자연어 증상 ↔ 의료 용어 불일치
- 외부 API 결과 품질 편차
- 키워드 기반 검색의 낮은 정확도
- 일부 query에서 결과 미출력 (zero-result)
- LLM 사용 시 latency 증가

---

## Solution Strategy

### 1. Retrieval-first 구조

- LLM 중심이 아닌 검색 중심 설계
- 빠른 응답 + 안정적인 기본 결과 확보
- summary는 optional로 분리

---

### 2. Hybrid Retrieval

다중 검색 소스를 결합

- Internal Knowledge
- External API (MedlinePlus)
- Vector Semantic Search

→ recall 및 coverage 향상

---

### 3. AI Reranking

검색 결과 후처리

- semantic similarity
- keyword boost
- priority boost

→ relevance 개선

---

### 4. Optional Summary

- summary 선택 실행
- latency와 품질 trade-off 제어

---

## Performance (Measured)

로컬 환경 기준 실제 측정 (PowerShell Measure-Command)

### /search

- 약 3543 ms (≈ 3.5s)

특징:
- external API 호출 포함
- latency 변동 존재

---

### /search/summary

- 평균 약 143 ms
- 단일 측정 약 171 ms

내부 breakdown:

- normalization: ~92 ms
- prediction: ~50 ms
- rerank: ~26 ms
- retrieval: ~5 ms
- summary: ~2 ms

---

### 핵심 해석

- /search는 external dependency 영향으로 느림
- /search/summary는 현재 extractive fallback 기반으로 빠르게 동작
- summary는 LLM이 아닌 fallback 경로로 실행됨

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

- 일부 한글 입력에서 encoding 문제 발생
- normalization 실패 시 fallback 처리됨
- query → "??? 형태로 깨짐"
- 결과 relevance 저하
- summary는 현재 extractive fallback 기반
- 일부 query에서 irrelevant result 발생
- external API 의존으로 latency 발생

---

## What This Project Demonstrates

- Retrieval 중심 AI 서비스 설계
- Hybrid Search Architecture
- AI Reranking 시스템
- 의료 UX 기반 Triage 설계
- Latency-aware Summary 구조
- 실제 문제 기반 시스템 개선 접근

---

## Improvement Roadmap

- UTF-8 입력 처리 안정화
- normalization rule 확장
- retrieval relevance 개선
- external API 캐싱 적용
- latency 최적화
- LLM summary 품질 개선
- RAG 구조 확장

---

## Tech Stack

Backend
- FastAPI

AI / NLP
- scikit-learn
- sentence-transformers

External API
- MedlinePlus

Language Processing
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

## Author

GitHub: tami-bang