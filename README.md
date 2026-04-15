# 🩺 Health AI Search API

증상 기반 자연어 입력을 의료 정보로 변환하고,  
외부 데이터 + 내부 지식 + AI 재정렬을 통해 최적의 결과를 제공하는 헬스케어 AI 검색 API
A FastAPI-based healthcare AI search API for symptom-driven queries

---

## Overview

`health-ai-search-api`는 사용자의 증상 입력을 기반으로  
정규화 → 외부 의료 데이터 검색 → AI 재정렬 → 응답 가공 → 다국어 처리까지 수행하는  
헬스케어 AI 검색 서비스입니다.

This project processes symptom input through normalization, external medical data retrieval, AI reranking, response formatting, and multilingual localization.

---

## Key Features

- **Symptom-based Search**  
  자연어 증상 입력 처리 (예: `"열이 나고 기침이 있어요"`)

- **Query Normalization**  
  입력 증상을 표준 의료 키워드로 변환

- **External Medical Data Retrieval**  
  MedlinePlus API 기반 건강 정보 검색

- **AI Reranking**  
  검색 결과를 AI 모델로 재정렬하여 정확도 향상

- **Response Formatting**  
  요약 + 구조화된 응답 생성

- **Multilingual Support**  
  한글 ↔ 영어 자동 번역

---

## Architecture

```text
User Query
→ Language Detection (language_utils.py)
→ Symptom Normalization (symptom_normalizer.py)

→ Dual Retrieval Layer
    ├── External API (medlineplus_client.py, retriever.py)
    ├── Internal Knowledge (internal_health_knowledge.py)
    └── Vector Search (internal_vector_store.py, chunker.py)

→ AI Reranking (ai_ranker.py)

→ Response Processing
    ├── Enrichment (response_enricher.py)
    ├── Formatting (formatter.py, response_formatter_v2.py)
    └── Question Suggestion (question_suggester.py)

→ LLM Generation (Optional)
    └── HuggingFace (hf_generation_service.py)

→ Localization (response_localizer.py, translator.py)

→ Triage (triage_service.py, triage_rules.py)

→ Final Response
```

---

## Project Structure

```text
app/
├── main.py                        # FastAPI entrypoint
├── core/
│   ├── settings.py
│   ├── symptom_rules.py
│   ├── triage_rules.py
│   └── response_builder.py
├── data/
│   └── internal_health_knowledge.py
├── services/
│   ├── symptom_search_service.py
│   ├── symptom_normalizer.py
│   ├── language_utils.py
│   ├── retriever.py
│   ├── medlineplus_client.py
│   ├── internal_vector_store.py
│   ├── chunker.py
│   ├── ai_ranker.py
│   ├── response_enricher.py
│   ├── formatter.py
│   ├── response_formatter_v2.py
│   ├── hf_generation_service.py
│   ├── response_localizer.py
│   ├── translator.py
│   ├── triage_service.py
│   └── question_suggester.py
└── schemas.py
```

---

## Tech Stack

### Backend
- FastAPI

### AI / Data
- scikit-learn
- sentence-transformers

### External API
- MedlinePlus

### Language Processing
- deep-translator

---

## 🔧 Installation

```bash
git clone https://github.com/tami-bang/health-ai-search-api.git
cd health-ai-search-api

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

---

## Run Server

```bash
uvicorn app.main:app --reload
```

### Swagger UI
http://127.0.0.1:8000/docs

---

## API Example

### Description

```
증상 입력 → 검색 → AI 재정렬 → 최종 응답까지 단일 API에서 처리
```

### Request

```http
POST /search?query=감기
```

### Response

```json
{
  "query": "감기",
  "top_result": {
    "title": "Common Cold",
    "summary": "...",
    "url": "..."
  }
}
```

---

## Design Focus

- External + Internal + Vector 기반 Hybrid Retrieval 구조  
  → 외부 API 의존도를 낮추고 검색 품질을 안정화하기 위해 설계

- AI 기반 결과 재정렬 Reranking Pipeline  
  → 단순 키워드 검색의 한계를 보완하기 위해 적용

- Enrichment + Formatter 분리  
  → 응답 품질과 유지보수성을 동시에 확보

- LLM 확장 가능한 AI 아키텍처  
  → 향후 생성형 응답까지 확장 가능하도록 설계

- Rule 기반 triage  
  → 의료 응답의 안전성을 확보하기 위한 최소한의 방어 로직

---

## What I Solved

- 자연어 증상 입력과 실제 의료 정보 간의 불일치 문제 해결
- 외부 API 결과의 품질 편차를 AI reranking으로 보완
- 다국어 입력/출력 처리 파이프라인 구축
- 단일 API에서 end-to-end 처리 구조 설계

---

## Future Improvements

- RAG 구조 확장 (Vector DB + Embedding)
- 증상 분류 모델 고도화
- 응급도 판단 로직 강화

---

## Author

GitHub: https://github.com/tami-bang
