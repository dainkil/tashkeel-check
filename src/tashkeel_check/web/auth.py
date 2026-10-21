"""API 키 인증(ADR-019). 키는 `X-API-Key` 헤더, `Authorization: Bearer`, 또는 `?api_key=`(SSE용) 순서로 읽는다.

AUTH=auto(기본)는 활성 고객이 하나라도 있으면 인증 필수, 없으면 열림(개발·가짜 모델 경험 유지).
required는 항상, disabled는 절대 요구하지 않는다. 인증된 요청의 데이터는 전부 그 고객에 묶인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from fastapi import Request

from ..config import Settings
from ..errors import TashkeelError
from .customers import CustomerStore

AuthMode = Literal["required", "disabled"]


class AuthError(TashkeelError):
    """API 키가 없거나 틀렸다(401)."""


@dataclass(frozen=True)
class Principal:
    customer_id: str | None  # 인증을 끈 경우에만 None
    name: str
    authenticated: bool

    @property
    def scope(self) -> str | None:
        """저장소 조회 범위. 인증되면 그 고객, 아니면 범위 없음."""
        return self.customer_id if self.authenticated else None


ANONYMOUS = Principal(customer_id=None, name="anonymous", authenticated=False)


def auth_mode(settings: Settings, customers: CustomerStore) -> AuthMode:
    if settings.auth == "required":
        return "required"
    if settings.auth == "disabled":
        return "disabled"
    return "required" if customers.count_active() > 0 else "disabled"


def extract_key(request: Request) -> str | None:
    key = request.headers.get("x-api-key")
    if key:
        return key.strip()
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    q = request.query_params.get("api_key")
    return q.strip() if q else None


def authenticate(settings: Settings, customers: CustomerStore, request: Request) -> Principal:
    key = extract_key(request)
    if key:
        customer = customers.by_key(key)
        if customer is None:
            raise AuthError("API 키가 틀렸거나 비활성입니다")
        return Principal(customer_id=customer.id, name=customer.name, authenticated=True)
    if auth_mode(settings, customers) == "required":
        raise AuthError("API 키가 필요합니다(X-API-Key 헤더 또는 Authorization: Bearer)")
    return ANONYMOUS


def current_customer(request: Request) -> Principal:
    """FastAPI 의존성. 앱 기동 때 `app.state.rt`에 둔 Runtime의 설정·고객 저장소를 쓴다."""
    rt: Any = request.app.state.rt
    return authenticate(rt.settings, rt.customers, request)
