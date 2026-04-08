# hf_generation_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from functools import lru_cache  # 모델 1회 로드 캐시

from app.core.settings import AI_SUMMARY_MAX_NEW_TOKENS  # 생성 토큰 수 설정
from app.core.settings import ENABLE_GPU  # GPU 사용 여부 설정
from app.core.settings import HF_GENERATION_MODEL_NAME  # 생성 모델명 설정

logger = logging.getLogger(__name__)


def _resolve_device() -> int:
    """
    transformers pipeline device 규칙:
    - GPU 사용 시 cuda:0 => 0
    - CPU 사용 시 -1
    """
    if not ENABLE_GPU:
        return -1

    try:
        import torch  # GPU 가능 여부 확인

        if torch.cuda.is_available():
            return 0

    except Exception as error:
        logger.warning("[HF] torch device check failed: %s", error)

    return -1


@lru_cache(maxsize=1)
def get_generation_pipeline():
    """
    생성 모델 lazy load
    - 앱 시작 시 강제 로드하지 않고 첫 요청에만 로드
    - 모델 교체는 settings.py에서만 수정
    """
    from transformers import pipeline  # Hugging Face pipeline 생성

    device = _resolve_device()

    logger.info("[HF] loading generation model: %s", HF_GENERATION_MODEL_NAME)
    logger.info("[HF] generation device: %s", "gpu" if device >= 0 else "cpu")

    generator = pipeline(
        task="text2text-generation",
        model=HF_GENERATION_MODEL_NAME,
        device=device,
    )
    return generator


def generate_text(prompt: str) -> str:
    """
    생성 모델 공통 진입점
    - 나중에 OpenAI / vLLM / TGI로 바꿔도 호출부 수정 범위를 줄이기 위해 분리
    """
    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        return ""

    generator = get_generation_pipeline()

    outputs = generator(
        cleaned_prompt,
        max_new_tokens=AI_SUMMARY_MAX_NEW_TOKENS,
        truncation=True,
    )

    if not outputs:
        return ""

    first_output = outputs[0] if isinstance(outputs, list) else {}
    generated_text = str(first_output.get("generated_text", "")).strip()
    return generated_text