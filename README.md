# 🩺 Health AI Search API

증상 기반 질의를 처리하는 AI 검색 API  
A FastAPI-based healthcare AI search API for symptom-driven queries

---

## 📌 Overview

`health-ai-search-api`는 사용자의 증상 입력을 기반으로  
정규화 → 외부 의료 데이터 검색 → AI 재정렬 → 응답 가공 → 다국어 처리까지 수행하는  
헬스케어 AI 검색 서비스입니다.

This project processes symptom input through normalization, external medical data retrieval, AI reranking, response formatting, and multilingual localization.

---

## 🚀 Key Features

- 🔍 **Symptom-based Search**  
  자연어 증상 입력 처리 (예: `"열이 나고 기침이 있어요"`)

- 🧠 **Query Normalization**  
  입력 증상을 표준 의료 키워드로 변환

- 🌐 **External Medical Data Retrieval**  
  MedlinePlus API 기반 건강 정보 검색

- 🤖 **AI Reranking**  
  검색 결과를 AI 모델로 재정렬하여 정확도 향상

- 📝 **Response Formatting**  
  요약 + 구조화된 응답 생성

- 🌍 **Multilingual Support**  
  한글 ↔ 영어 자동 번역

---

## 🏗️ Architecture

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

## 📂 Project Structure

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

## ⚙️ Tech Stack

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

## ▶️ Run Server

```bash
uvicorn app.main:app --reload
```

### Swagger UI
http://127.0.0.1:8000/docs

---

## 📡 API Example

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

## 💡 Design Focus

- External + Internal + Vector 기반 Hybrid Retrieval 구조
- AI 기반 결과 재정렬 Reranking Pipeline
- Enrichment + Formatter 분리로 응답 품질 개선
- LLM 확장 가능한 AI 아키텍처 설계
- Rule 기반 triage로 의료 응답 안전성 보완

---

## 📈 Future Improvements

- RAG 구조 확장 (Vector DB + Embedding)
- 증상 분류 모델 고도화
- 응급도 판단 로직 강화

---

## 👤 Author

GitHub: https://github.com/tami-bang