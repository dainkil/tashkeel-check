"""문자 인식 백엔드 인터페이스. 구현은 `ocrspace.py`(무료 API)와 `none.py`(거부)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OcrResult:
    text: str
    pages: int = 1
    warnings: list[str] = field(default_factory=list)
    backend: str = ""


class OcrBackend(Protocol):
    name: str

    def extract(self, data: bytes, mime: str, filename: str) -> OcrResult: ...


class NoOcrBackend:
    """문자 인식을 쓰지 않는다. 이미지나 텍스트 층 없는 PDF는 InputError(400)."""

    name = "none"

    def extract(self, data: bytes, mime: str, filename: str) -> OcrResult:
        from ..errors import InputError

        raise InputError(
            f"문자 인식 백엔드가 없어 이 파일을 읽을 수 없습니다: {filename}. "
            "텍스트(.txt/.md)나 텍스트 층이 있는 PDF를 넣거나, OCR_BACKEND를 설정하세요."
        )
