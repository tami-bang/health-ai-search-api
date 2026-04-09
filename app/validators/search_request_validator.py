# search_request_validator.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원

from app.core.error_codes import EMPTY_QUERY  # 빈 입력 에러 코드
from app.core.error_codes import INVALID_QUERY  # 잘못된 입력 에러 코드
from app.core.error_codes import QUERY_TOO_LONG  # 최대 길이 초과 에러 코드
from app.core.error_codes import QUERY_TOO_SHORT  # 최소 길이 미달 에러 코드
from app.core.exceptions import ValidationException  # 입력 검증 예외
from app.core.settings import SEARCH_QUERY_MAX_LENGTH  # 최대 입력 길이 설정
from app.core.settings import SEARCH_QUERY_MIN_LENGTH  # 최소 입력 길이 설정

def validate_search_query(query: str) -> str:
    if query is None:
        raise ValidationException(
            message="검색어가 비어 있습니다.",
            error_code=EMPTY_QUERY,
            status_code=422,
        )

    cleaned_query = str(query).strip()

    if not cleaned_query:
        raise ValidationException(
            message="검색어가 비어 있습니다.",
            error_code=EMPTY_QUERY,
            status_code=422,
        )

    if len(cleaned_query) < SEARCH_QUERY_MIN_LENGTH:
        raise ValidationException(
            message=f"검색어는 최소 {SEARCH_QUERY_MIN_LENGTH}자 이상이어야 합니다.",
            error_code=QUERY_TOO_SHORT,
            status_code=422,
        )

    if len(cleaned_query) > SEARCH_QUERY_MAX_LENGTH:
        raise ValidationException(
            message=f"검색어는 최대 {SEARCH_QUERY_MAX_LENGTH}자까지 입력할 수 있습니다.",
            error_code=QUERY_TOO_LONG,
            status_code=422,
        )

    if "\x00" in cleaned_query:
        raise ValidationException(
            message="검색어에 허용되지 않는 문자가 포함되어 있습니다.",
            error_code=INVALID_QUERY,
            status_code=422,
        )

    return cleaned_query