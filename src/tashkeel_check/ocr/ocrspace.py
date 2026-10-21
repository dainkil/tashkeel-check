"""OCR.space 무료 API 백엔드(ADR-021). 파일을 제3자 서버로 보낸다. 민감 서류는 텍스트로 넣는다.

응답 형식(2026-10 기준): {"ParsedResults": [{"ParsedText": "...", "ErrorMessage": ""}], "IsErroredOnProcessing": bool,
"ErrorMessage": [...]}. 무료 등급의 파일 크기·페이지 상한은 공식 문서를 따른다(설정 `ocr_max_bytes`).
"""

from __future__ import annotations

from typing import Any

import httpx

from ..errors import ConfigError, InputError
from .base import OcrResult

LANGUAGE = "ara"


def parse_response(body: dict[str, Any], backend: str = "ocrspace") -> OcrResult:
    """응답 JSON → OcrResult. 처리 오류는 InputError."""
    if body.get("IsErroredOnProcessing"):
        msg = body.get("ErrorMessage")
        if isinstance(msg, list):
            msg = "; ".join(str(m) for m in msg)
        raise InputError(f"문자 인식에 실패했습니다: {msg or body.get('ErrorDetails') or '원인 불명'}")
    results = body.get("ParsedResults") or []
    texts = [str(r.get("ParsedText") or "") for r in results]
    warnings = [str(r["ErrorMessage"]) for r in results if r.get("ErrorMessage")]
    text = "\n".join(t.strip("\r\n") for t in texts if t.strip())
    if not text.strip():
        raise InputError("문자 인식 결과가 비어 있습니다. 해상도가 더 높은 스캔을 넣거나 텍스트로 넣으세요.")
    return OcrResult(text=text, pages=max(1, len(results)), warnings=warnings, backend=backend)


class OcrSpaceBackend:
    name = "ocrspace"

    def __init__(self, api_key: str | None, endpoint: str, max_bytes: int, timeout: float = 60.0) -> None:
        if not api_key:
            raise ConfigError("OCR_BACKEND=ocrspace에는 OCR_API_KEY가 필요합니다")
        self.api_key = api_key
        self.endpoint = endpoint
        self.max_bytes = max_bytes
        self.timeout = timeout

    def extract(self, data: bytes, mime: str, filename: str) -> OcrResult:
        if len(data) > self.max_bytes:
            raise InputError(f"문자 인식 파일 상한을 넘었습니다({len(data)} bytes > {self.max_bytes}): {filename}")
        form = {"language": LANGUAGE, "isOverlayRequired": "false", "OCREngine": "2", "scale": "true"}
        try:
            r = httpx.post(
                self.endpoint,
                headers={"apikey": self.api_key},
                data=form,
                files={"file": (filename, data, mime)},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ConfigError(f"문자 인식 서버에 연결하지 못했습니다: {exc}") from exc
        if r.status_code != 200:
            raise ConfigError(f"문자 인식 서버 오류 {r.status_code}: {r.text[:200]}")
        try:
            body = r.json()
        except ValueError as exc:
            raise ConfigError("문자 인식 서버 응답이 JSON이 아닙니다") from exc
        return parse_response(body, self.name)
