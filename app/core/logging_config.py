# logging_config.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

import logging  # 실행 로그 기록
import sys  # stdout 스트림 연결

from app.core.settings import LOG_LEVEL  # 로그 레벨 설정값

_LOGGING_INITIALIZED = False

def configure_logging() -> None:
    global _LOGGING_INITIALIZED

    if _LOGGING_INITIALIZED:
        return

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    _LOGGING_INITIALIZED = True