"""묶음 JSON 읽기. 파일 없음과 형식 오류를 다른 예외로 낸다(가이드 1단계)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..errors import InputError
from .schemas import Bundle


class BundleNotFound(InputError):
    """묶음 파일이 없다."""


class InvalidBundle(InputError):
    """묶음 파일이 JSON이 아니거나 구조가 맞지 않는다."""


def parse_bundle(obj: Any) -> Bundle:
    """dict를 Bundle로 검증한다. `gold` 키는 떼어 낸다(정답은 입력에 섞이지 않는다)."""
    if not isinstance(obj, dict):
        raise InvalidBundle("묶음은 JSON 객체여야 합니다")
    data = {k: v for k, v in obj.items() if k != "gold"}
    try:
        return Bundle.model_validate(data)
    except ValidationError as exc:
        raise InvalidBundle(
            f"묶음 구조 오류: {exc.errors()[0]['msg']} ({'.'.join(str(p) for p in exc.errors()[0]['loc'])})"
        ) from exc


def load_bundle_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BundleNotFound(f"묶음 파일이 없습니다: {p}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidBundle(f"묶음 파일이 UTF-8이 아닙니다: {p}") from exc
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidBundle(f"묶음 파일의 JSON 형식이 잘못됐습니다: {p} ({exc.msg}, line {exc.lineno})") from exc
    if not isinstance(obj, dict):
        raise InvalidBundle(f"묶음은 JSON 객체여야 합니다: {p}")
    return obj


def load_bundle(path: str | Path) -> Bundle:
    return parse_bundle(load_bundle_json(path))


def split_bundle_gold(obj: dict[str, Any]) -> tuple[Bundle, dict[str, Any] | None]:
    """합성 묶음 파일에서 정답을 떼어 낸다. 정답은 평가에만 쓴다."""
    return parse_bundle(obj), obj.get("gold")
