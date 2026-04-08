# chunker.py
from __future__ import annotations  # 최신 타입 힌트 문법 지원


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """
    너무 복잡한 tokenizer 기반 chunking 대신
    지금 프로젝트 단계에서는 유지보수 쉬운 문자 기반 chunking으로 둔다.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    if chunk_size <= 0:
        return [cleaned]

    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size // 4)

    chunks: list[str] = []
    start_index = 0
    text_length = len(cleaned)

    while start_index < text_length:
        end_index = min(start_index + chunk_size, text_length)
        chunk = cleaned[start_index:end_index].strip()

        if chunk:
            chunks.append(chunk)

        if end_index >= text_length:
            break

        start_index = max(0, end_index - chunk_overlap)

    return chunks