"""업로드한 파일에서 묶음을 만든다(`POST /v1/bundles`).

받는 파일:
- `.json` 하나에 `documents`가 있으면 묶음 JSON 그대로(다른 파일과 섞지 못한다).
- `.json`에 `segments`가 있으면 서류 하나(`document_id` 없으면 파일 이름).
- `.txt`·`.md`는 서류 하나. 빈 줄이 아닌 줄마다 구간 하나(`s01`, `s02`, …). 대상 ID는 붙지 않으므로
  라벨 칸의 고유명사는 "대상 ID 없음"으로 대기에 오른다(ADR-018: ID를 추측하지 않는다).
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

from ..errors import InputError
from .loader import parse_bundle
from .schemas import Bundle

MAX_FILES = 20
MAX_BYTES = 2 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md"}


def _decode(name: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise InputError(f"파일이 너무 큽니다({name}, {len(data)} bytes > {MAX_BYTES})")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError(f"UTF-8 텍스트가 아닙니다: {name}") from exc


def _text_document(name: str, text: str, document_type: str) -> dict[str, Any]:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    segments = [{"segment_id": f"s{i:02d}", "text": line} for i, line in enumerate(lines, start=1)]
    if not segments:
        raise InputError(f"빈 파일입니다: {name}")
    return {"document_id": PurePosixPath(name).stem, "document_type": document_type, "segments": segments}


def bundle_from_uploads(
    files: list[tuple[str, bytes]],
    bundle_id: str | None = None,
    customer_id: str | None = None,
    document_type: str = "document",
    entities: str | None = None,
) -> Bundle:
    if not files:
        raise InputError("파일이 없습니다")
    if len(files) > MAX_FILES:
        raise InputError(f"파일이 너무 많습니다({len(files)} > {MAX_FILES})")
    entity_map: dict[str, Any] = {}
    if entities:
        try:
            entity_map = json.loads(entities)
        except json.JSONDecodeError as exc:
            raise InputError(f"entities가 JSON이 아닙니다: {exc.msg}") from exc
        if not isinstance(entity_map, dict):
            raise InputError("entities는 {대상 ID: 종류} 객체여야 합니다")

    bundle_obj: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = []
    for name, data in files:
        suffix = PurePosixPath(name).suffix.lower()
        text = _decode(name, data)
        if suffix == ".json":
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                raise InputError(f"JSON 형식 오류({name}): {exc.msg} (line {exc.lineno})") from exc
            if isinstance(obj, dict) and "documents" in obj:
                if bundle_obj is not None:
                    raise InputError("묶음 JSON은 하나만 올릴 수 있습니다")
                bundle_obj = obj
            elif isinstance(obj, dict) and "segments" in obj:
                documents.append({"document_id": PurePosixPath(name).stem, "document_type": document_type, **obj})
            else:
                raise InputError(f"묶음(documents)도 서류(segments)도 아닙니다: {name}")
        elif suffix in TEXT_SUFFIXES:
            documents.append(_text_document(name, text, document_type))
        else:
            raise InputError(f"지원하지 않는 파일 형식입니다: {name} (.json, .txt, .md)")

    if bundle_obj is not None:
        if documents:
            raise InputError("묶음 JSON과 서류 파일을 함께 올릴 수 없습니다")
        obj = dict(bundle_obj)
    else:
        obj = {"bundle_id": bundle_id or "upload", "documents": documents}
    if bundle_id:
        obj["bundle_id"] = bundle_id
    if customer_id:
        obj["customer_id"] = customer_id
    if entity_map:
        obj["entities"] = {**obj.get("entities", {}), **entity_map}
    return parse_bundle(obj)  # 구조 오류 → InvalidBundle(InputError)
