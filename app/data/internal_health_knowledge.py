# internal_health_knowledge.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원


# 확장 포인트:
# - 나중에 JSON/DB/관리자 입력으로 바꿔도 서비스 레이어는 그대로 유지되게
#   내부 지식 원문만 따로 분리했다.
INTERNAL_HEALTH_DOCUMENTS: list[dict[str, str]] = [
    {
        "document_id": "internal-fever-001",
        "title": "Fever basics",
        "source": "InternalKnowledge",
        "url": "",
        "content": (
            "Fever means a body temperature that is higher than normal. "
            "It is often a sign that the body is responding to infection or inflammation. "
            "A fever itself is not always dangerous, but very high fever, persistent fever, "
            "or fever with trouble breathing, confusion, seizure, severe dehydration, or chest pain "
            "may require urgent medical attention."
        ),
    },
    {
        "document_id": "internal-headache-001",
        "title": "Headache overview",
        "source": "InternalKnowledge",
        "url": "",
        "content": (
            "Headache can happen for many reasons including tension, dehydration, lack of sleep, infection, "
            "or migraine. Sudden severe headache, headache with weakness, trouble speaking, fainting, "
            "high fever, stiff neck, or head injury are warning signs that should not be ignored."
        ),
    },
    {
        "document_id": "internal-diarrhea-001",
        "title": "Diarrhea overview",
        "source": "InternalKnowledge",
        "url": "",
        "content": (
            "Diarrhea refers to loose or watery stools. It may be caused by infection, food intolerance, "
            "medication, or digestive disorders. Persistent diarrhea, blood in stool, severe abdominal pain, "
            "signs of dehydration, or diarrhea in very young children or older adults needs careful attention."
        ),
    },
    {
        "document_id": "internal-cough-001",
        "title": "Cough overview",
        "source": "InternalKnowledge",
        "url": "",
        "content": (
            "Cough can be related to cold, flu, allergies, asthma, reflux, or other respiratory conditions. "
            "Cough with shortness of breath, chest pain, bluish lips, coughing blood, or worsening symptoms "
            "should be medically evaluated promptly."
        ),
    },
    {
        "document_id": "internal-concussion-001",
        "title": "Head injury and concussion",
        "source": "InternalKnowledge",
        "url": "",
        "content": (
            "A concussion is a type of brain injury that can happen after a blow to the head or body. "
            "Symptoms may include headache, dizziness, nausea, confusion, light sensitivity, or memory problems. "
            "Loss of consciousness, repeated vomiting, severe worsening headache, seizure, confusion, unequal pupils, "
            "or difficulty waking up can be emergency warning signs."
        ),
    },
]