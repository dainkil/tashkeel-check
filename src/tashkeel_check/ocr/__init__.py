"""문자 인식 백엔드와 텍스트 추출(ADR-021). 성능은 재지 않는다. 백엔드는 설정으로 바꾼다."""

from .base import OcrBackend, OcrResult
from .extract import Extracted, extract_text, make_backend

__all__ = ["Extracted", "OcrBackend", "OcrResult", "extract_text", "make_backend"]
