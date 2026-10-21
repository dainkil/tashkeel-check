"""업로드 파일 → 텍스트(ADR-021). .txt/.md는 그대로, .pdf는 텍스트 층을 먼저, 없으면 문자 인식, 이미지는 문자 인식.

텍스트 층 판정: pypdf가 뽑은 텍스트에 아랍어 토큰이 하나라도 있으면 텍스트 층으로 본다. 인식 성능은 재지 않는다.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from ..config import Settings
from ..errors import InputError
from ..text import Segment, nfc, segment_text, tokenize
from .base import NoOcrBackend, OcrBackend

TEXT_SUFFIXES = {".txt", ".md"}
PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}


@dataclass
class Extracted:
    text: str
    segments: list[Segment]
    source: str  # text | pdf_text | ocr
    backend: str | None = None
    pages: int = 1
    warnings: list[str] = field(default_factory=list)


def make_backend(settings: Settings) -> OcrBackend:
    if settings.ocr_backend == "ocrspace":
        from .ocrspace import OcrSpaceBackend

        return OcrSpaceBackend(settings.ocr_api_key, settings.ocr_endpoint, settings.ocr_max_bytes)
    return NoOcrBackend()


def _has_arabic(text: str) -> bool:
    segs = segment_text(text)
    return bool(segs) and any(t["script"] == "ar" for t in tokenize(segs))


def _pdf_text_layer(data: bytes, filename: str) -> tuple[str, int]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise InputError(f"PDF를 읽을 수 없습니다: {filename} ({exc})") from exc
    except Exception as exc:  # 암호화·손상 등
        raise InputError(f"PDF를 읽을 수 없습니다: {filename} ({type(exc).__name__})") from exc
    return "\n".join(pages), max(1, len(pages))


def extract_text(data: bytes, filename: str, backend: OcrBackend, max_bytes: int) -> Extracted:
    if not data:
        raise InputError(f"빈 파일입니다: {filename}")
    if len(data) > max_bytes:
        raise InputError(f"파일이 너무 큽니다({filename}, {len(data)} bytes > {max_bytes})")
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InputError(f"UTF-8 텍스트가 아닙니다: {filename}") from exc
        return _finish(text, "text", None, 1, [])
    if suffix in PDF_SUFFIXES:
        text, pages = _pdf_text_layer(data, filename)
        if _has_arabic(text):
            return _finish(text, "pdf_text", None, pages, [])
        res = backend.extract(data, MIME[suffix], filename)
        return _finish(res.text, "ocr", res.backend, res.pages or pages, res.warnings)
    if suffix in IMAGE_SUFFIXES:
        res = backend.extract(data, MIME[suffix], filename)
        return _finish(res.text, "ocr", res.backend, res.pages, res.warnings)
    allowed = ", ".join(sorted(TEXT_SUFFIXES | PDF_SUFFIXES | IMAGE_SUFFIXES))
    raise InputError(f"받지 않는 파일 형식입니다: {filename}. 가능한 형식: {allowed}")


def _finish(text: str, source: str, backend: str | None, pages: int, warnings: list[str]) -> Extracted:
    text = nfc(text)
    segments = segment_text(text)
    if not segments:
        raise InputError("빈 문서입니다. 읽을 수 있는 텍스트가 없습니다.")
    if not any(t["script"] == "ar" for t in tokenize(segments)):
        raise InputError("아랍어 토큰이 없습니다. 아랍 문자로 된 문서를 넣으세요.")
    return Extracted(text=text, segments=segments, source=source, backend=backend, pages=pages, warnings=warnings)
