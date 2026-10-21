"""파일 → 텍스트 추출(ADR-021). 인식 성능은 재지 않는다. OCR 백엔드는 가짜로 둔다."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from tashkeel_check.config import Settings
from tashkeel_check.errors import ConfigError, InputError
from tashkeel_check.ocr import extract_text, make_backend
from tashkeel_check.ocr.base import NoOcrBackend, OcrResult
from tashkeel_check.ocr.ocrspace import parse_response

ARABIC = "وكالة خاصة\nحضر السيد سالم بن حمد المسلم.\nPrincipal: Salem bin Hamad Al Muslim\n"


class FakeOcr:
    name = "fake"

    def __init__(self, text: str = ARABIC) -> None:
        self.text = text
        self.calls: list[tuple[str, str, int]] = []

    def extract(self, data: bytes, mime: str, filename: str) -> OcrResult:
        self.calls.append((mime, filename, len(data)))
        return OcrResult(text=self.text, pages=2, warnings=["w"], backend=self.name)


def _blank_pdf() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_text_file_is_split_into_segments():
    ex = extract_text(ARABIC.encode("utf-8"), "doc.txt", NoOcrBackend(), 1 << 20)
    assert ex.source == "text" and ex.backend is None and len(ex.segments) == 3
    assert ex.segments[0]["segment_id"] == "s01" and ex.segments[0]["text"] == "وكالة خاصة"


def test_markdown_with_bom_is_accepted():
    ex = extract_text(("﻿" + ARABIC).encode("utf-8"), "doc.md", NoOcrBackend(), 1 << 20)
    assert ex.text.startswith("وكالة")


@pytest.mark.parametrize(
    ("data", "name", "msg"),
    [
        (b"", "doc.txt", "빈 파일"),
        (b"\xff\xfe\x00", "doc.txt", "UTF-8"),
        (b"Principal: Salem", "doc.txt", "아랍어 토큰이 없습니다"),
        (b"\n\n", "doc.txt", "빈 문서"),
        (ARABIC.encode("utf-8"), "doc.docx", "받지 않는 파일 형식"),
    ],
)
def test_bad_text_inputs_are_input_errors(data, name, msg):
    with pytest.raises(InputError, match=msg):
        extract_text(data, name, NoOcrBackend(), 1 << 20)


def test_size_limit_is_checked_before_reading():
    with pytest.raises(InputError, match="너무 큽니다"):
        extract_text(b"x" * 11, "doc.txt", NoOcrBackend(), 10)


def test_image_goes_to_backend_and_none_backend_is_400():
    fake = FakeOcr()
    ex = extract_text(b"\x89PNG....", "scan.png", fake, 1 << 20)
    assert ex.source == "ocr" and ex.backend == "fake" and ex.pages == 2 and ex.warnings == ["w"]
    assert fake.calls == [("image/png", "scan.png", 8)]
    with pytest.raises(InputError, match="문자 인식 백엔드가 없어"):
        extract_text(b"\x89PNG....", "scan.png", NoOcrBackend(), 1 << 20)


def test_pdf_without_text_layer_goes_to_backend():
    fake = FakeOcr()
    ex = extract_text(_blank_pdf(), "scan.pdf", fake, 1 << 20)
    assert ex.source == "ocr" and fake.calls[0][0] == "application/pdf"
    with pytest.raises(InputError, match="문자 인식 백엔드가 없어"):
        extract_text(_blank_pdf(), "scan.pdf", NoOcrBackend(), 1 << 20)


def test_broken_pdf_is_input_error():
    with pytest.raises(InputError, match="PDF를 읽을 수 없습니다"):
        extract_text(b"%PDF-1.4 garbage", "broken.pdf", NoOcrBackend(), 1 << 20)


def test_ocrspace_response_parsing():
    body = {
        "ParsedResults": [
            {"ParsedText": "وكالة خاصة\r\n", "ErrorMessage": ""},
            {"ParsedText": "سالم", "ErrorMessage": "low"},
        ],
        "IsErroredOnProcessing": False,
    }
    r = parse_response(body)
    assert r.text == "وكالة خاصة\nسالم" and r.pages == 2 and r.warnings == ["low"] and r.backend == "ocrspace"
    with pytest.raises(InputError, match="문자 인식에 실패"):
        parse_response({"IsErroredOnProcessing": True, "ErrorMessage": ["bad file"]})
    with pytest.raises(InputError, match="비어 있습니다"):
        parse_response({"ParsedResults": [{"ParsedText": "  "}], "IsErroredOnProcessing": False})


def test_backend_factory_follows_settings():
    assert make_backend(Settings()).name == "none"
    assert make_backend(Settings(ocr_backend="ocrspace", ocr_api_key="k")).name == "ocrspace"
    with pytest.raises(ConfigError, match="OCR_API_KEY"):
        make_backend(Settings(ocr_backend="ocrspace"))
