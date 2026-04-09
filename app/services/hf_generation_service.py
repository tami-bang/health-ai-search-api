# hf_generation_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from functools import lru_cache  # 모델 1회 로드 캐시

from app.core.settings import AI_SUMMARY_MAX_NEW_TOKENS  # 생성 토큰 수 설정
from app.core.settings import ENABLE_GPU  # GPU 사용 여부 설정
from app.core.settings import HF_GENERATION_MODEL_NAME  # 생성 모델명 설정

logger = logging.getLogger(__name__)

def _resolve_device() -> str:
    """
    transformers model.to()에 맞춰 문자열 장치명을 반환한다.
    """
    if not ENABLE_GPU:
        return "cpu"

    try:
        import torch  # GPU 가능 여부 확인

        if torch.cuda.is_available():
            return "cuda"
    except Exception as error:
        logger.warning("[HF] torch device check failed: %s", error)

    return "cpu"

@lru_cache(maxsize=1)
def get_generation_components():
    """
    pipeline task 호환성 이슈를 피하려고
    tokenizer/model을 직접 로드해서 generate로 처리한다.
    """
    import torch  # 텐서 장치 이동
    from transformers import AutoModelForSeq2SeqLM  # seq2seq 생성 모델 로드
    from transformers import AutoTokenizer  # 토크나이저 로드

    device_name = _resolve_device()

    logger.info("[HF] loading generation model: %s", HF_GENERATION_MODEL_NAME)
    logger.info("[HF] generation device: %s", device_name)

    tokenizer = AutoTokenizer.from_pretrained(HF_GENERATION_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(HF_GENERATION_MODEL_NAME)
    model = model.to(device_name)
    model.eval()

    return tokenizer, model, device_name, torch

def generate_text(prompt: str) -> str:
    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        return ""

    tokenizer, model, device_name, torch = get_generation_components()

    inputs = tokenizer(
        cleaned_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
    )

    inputs = {key: value.to(device_name) for key, value in inputs.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=AI_SUMMARY_MAX_NEW_TOKENS,
        )

    generated_text = tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True,
    ).strip()

    return generated_text