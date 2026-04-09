# app/services/hf_generation_service.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
from functools import lru_cache  # 모델 1회 로드 캐시
from typing import Any  # 반환 타입 힌트 보조

from app.core.settings import AI_SUMMARY_DO_SAMPLE  # 샘플링 사용 여부
from app.core.settings import AI_SUMMARY_EARLY_STOPPING  # 조기 종료 여부
from app.core.settings import AI_SUMMARY_MAX_INPUT_TOKENS  # 생성 입력 토큰 수 제한
from app.core.settings import AI_SUMMARY_MAX_NEW_TOKENS  # 생성 토큰 수 설정
from app.core.settings import AI_SUMMARY_NUM_BEAMS  # beam search 설정
from app.core.settings import AI_SUMMARY_REPETITION_PENALTY  # 반복 패널티 설정
from app.core.settings import AI_SUMMARY_TEMPERATURE  # 생성 temperature 설정
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
def get_generation_components() -> tuple[Any, Any, str, Any]:
    """
    pipeline 호환성 이슈를 피하려고 tokenizer/model을 직접 로드한다.
    추후 모델 교체 시 이 함수만 유지하면 호출부 수정 범위가 작다.
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


def _prepare_inputs(
    prompt: str,
    tokenizer: Any,
    device_name: str,
) -> dict[str, Any]:
    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        return {}

    tokenized_inputs = tokenizer(
        cleaned_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=AI_SUMMARY_MAX_INPUT_TOKENS,
    )

    return {
        key: value.to(device_name)
        for key, value in tokenized_inputs.items()
    }


def _build_generate_kwargs() -> dict[str, Any]:
    return {
        "max_new_tokens": AI_SUMMARY_MAX_NEW_TOKENS,
        "do_sample": AI_SUMMARY_DO_SAMPLE,
        "temperature": AI_SUMMARY_TEMPERATURE,
        "num_beams": AI_SUMMARY_NUM_BEAMS,
        "repetition_penalty": AI_SUMMARY_REPETITION_PENALTY,
        "early_stopping": AI_SUMMARY_EARLY_STOPPING,
    }


def generate_text(prompt: str) -> str:
    cleaned_prompt = (prompt or "").strip()
    if not cleaned_prompt:
        return ""

    tokenizer, model, device_name, torch = get_generation_components()
    inputs = _prepare_inputs(
        prompt=cleaned_prompt,
        tokenizer=tokenizer,
        device_name=device_name,
    )
    if not inputs:
        return ""

    generate_kwargs = _build_generate_kwargs()

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            **generate_kwargs,
        )

    generated_text = tokenizer.decode(
        output_ids[0],
        skip_special_tokens=True,
    ).strip()

    return generated_text