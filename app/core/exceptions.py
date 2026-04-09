# exceptions.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

class AppException(Exception):
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class ValidationException(AppException):
    pass

class DependencyNotReadyException(AppException):
    pass

class RetrievalException(AppException):
    pass