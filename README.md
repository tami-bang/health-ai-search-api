# 🩺 Health AI Search API

증상 기반 자연어 입력을 의료 정보로 변환하고,  
External + Internal + AI Reranking을 통해 최적의 결과를 제공하는 헬스케어 AI 검색 API

A FastAPI-based healthcare AI search API for symptom-driven queries

---

## Overview

`health-ai-search-api`는 사용자의 증상 입력을 기반으로  
정규화 → 검색 → AI 재정렬 → triage 판단 → 응답 가공 → 다국어 처리까지 수행하는  
End-to-End 헬스케어 AI 검색 서비스입니다.

This system processes symptom queries through normalization, hybrid retrieval, AI reranking, triage evaluation, and response formatting.

---

## Problem & Solution

### Problem
- 자연어 증상 입력은 의료 용어와 불일치
- 외부 API 결과 품질이 일정하지 않음
- 단순 검색으로는 사용자에게 의미 있는 정보 제공 어려움
- 의료 서비스 특성상 위험도 판단 필요

### Solution
- Symptom Normalization Pipeline으로 입력 구조화
- External + Internal + Vector 기반 Hybrid Retrieval
- AI Reranking으로 검색 품질 개선
- Rule 기반 Triage로 위험도 판단
- AI Summary 및 구조화 응답으로 사용자 이해도 향상

---

## Key Features

- Symptom-based Search  
  자연어 증상 입력 처리

- Query Normalization  
  다양한 표현을 표준 의료 키워드로 변환

- Hybrid Retrieval  
  External + Internal + Vector 검색 구조

- AI Reranking  
  의미 기반 결과 재정렬

- Triage Evaluation  
  응급도 판단 (red / yellow / green)

- AI Summary (Optional)  
  요약 생성 (LLM 또는 Extractive)

- Multilingual Support  
  한글 ↔ 영어 자동 변환

---

## Architecture

User Query  
→ Language Detection  
→ Symptom Normalization  

→ Hybrid Retrieval  
→ AI Reranking  
→ Triage Evaluation  

→ Response Processing  
→ LLM Summary (Optional)  
→ Localization  

→ Final Response  

---

## Response Pipeline

1. 입력 검증  
2. 언어 감지 및 번역  
3. 증상 정규화  
4. 검색 (internal + external + vector)  
5. AI reranking  
6. triage 판단  
7. summary 생성  
8. 응답 포맷팅  

---

## Example API

### Request
POST /search/summary

{
  "query": "코피가 30분째 안 멈춰요",
  "include_summary": true
}

---

### Response
{
  "query": "코피가 30분째 안 멈춰요",
  "meta": {
    "request_id": "uuid",
    "total_results": 3
  },
  "guidance": {
    "triage_level": "urgent",
    "triage_message": "출혈이 지속되고 있습니다. 의료진 상담이 필요합니다.",
    "question_suggestions": [
      "얼마나 자주 발생하나요?",
      "다른 증상도 있나요?"
    ]
  },
  "results_bundle": {
    "top_result": {
      "title": "Nosebleed",
      "snippet": "코피는 다양한 원인으로 발생할 수 있습니다.",
      "url": "https://..."
    },
    "results": [],
    "related_topics": [],
    "ai_summary": {
      "summary": "지속적인 코피는 혈관 문제 또는 질환과 관련될 수 있습니다.",
      "key_findings": [
        "출혈 지속",
        "점막 손상 가능성"
      ],
      "recommendations": [
        "코를 압박",
        "병원 방문"
      ],
      "disclaimer": "의학적 진단이 아닙니다."
    }
  }
}

---

## Project Structure

app/  
├── main.py  
├── core/  
├── services/  
├── data/  
└── schemas.py  

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

## Installation

git clone https://github.com/tami-bang/health-ai-search-api.git  
cd health-ai-search-api  

python -m venv .venv  
.venv\Scripts\activate  

pip install -r requirements.txt  

---

## Run Server

uvicorn app.main:app --reload  

Swagger  
http://127.0.0.1:8000/docs  

---

## Design Focus

- Hybrid Retrieval 구조로 검색 품질 안정화  
- AI Reranking으로 의미 기반 검색 강화  
- Triage 기반 안전성 확보  
- LLM 확장 가능한 구조 설계  
- Formatter 분리로 유지보수성 확보  

---

## What I Solved

- 자연어 → 의료 정보 매핑 문제 해결  
- 검색 품질 편차 문제 해결  
- 다국어 처리 파이프라인 구축  
- End-to-End AI 검색 시스템 설계  

---

## Future Improvements

- RAG 구조 고도화  
- 증상 분류 모델 개선  
- LLM 기반 Summary 품질 향상  

---

## Author

https://github.com/tami-bang