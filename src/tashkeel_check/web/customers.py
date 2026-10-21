"""고객과 API 키(ADR-019). 키는 발급 때 한 번만 평문으로 보이고, 저장은 sha256 해시뿐이다.

DB가 없으면 메모리 저장소다(테스트·개발). 인증 자체는 `web/auth.py`가 한다.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .db import Database, new_id

KEY_PREFIX = "tk_"


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_hex(24)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


def key_prefix(key: str) -> str:
    return key[: len(KEY_PREFIX) + 6]


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    key_prefix: str
    active: bool
    created_at: datetime | None = None
    revoked_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }


class CustomerStore(Protocol):
    def add(self, name: str) -> tuple[Customer, str]: ...  # (고객, 평문 키 — 이번 한 번만)
    def by_key(self, key: str) -> Customer | None: ...  # 활성 고객만
    def list(self) -> list[Customer]: ...
    def revoke(self, customer_id: str) -> bool: ...
    def count_active(self) -> int: ...


class MemoryCustomerStore:
    def __init__(self) -> None:
        self._by_hash: dict[str, Customer] = {}

    def add(self, name: str) -> tuple[Customer, str]:
        key = generate_key()
        c = Customer(id=new_id(), name=name, key_prefix=key_prefix(key), active=True, created_at=datetime.now(UTC))
        self._by_hash[hash_key(key)] = c
        return c, key

    def by_key(self, key: str) -> Customer | None:
        c = self._by_hash.get(hash_key(key))
        return c if c is not None and c.active else None

    def list(self) -> list[Customer]:
        return sorted(self._by_hash.values(), key=lambda c: c.created_at or datetime.min.replace(tzinfo=UTC))

    def revoke(self, customer_id: str) -> bool:
        for h, c in self._by_hash.items():
            if c.id == customer_id and c.active:
                self._by_hash[h] = Customer(c.id, c.name, c.key_prefix, False, c.created_at, datetime.now(UTC))
                return True
        return False

    def count_active(self) -> int:
        return sum(1 for c in self._by_hash.values() if c.active)


def _from_row(row: dict[str, Any]) -> Customer:
    return Customer(
        id=row["id"],
        name=row["name"],
        key_prefix=row["key_prefix"],
        active=bool(row["active"]),
        created_at=row.get("created_at"),
        revoked_at=row.get("revoked_at"),
    )


class DbCustomerStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, name: str) -> tuple[Customer, str]:
        key = generate_key()
        row = self.db.insert_customer(name, hash_key(key), key_prefix(key))
        return _from_row(row), key

    def by_key(self, key: str) -> Customer | None:
        row = self.db.customer_by_hash(hash_key(key))
        return None if row is None or not row["active"] else _from_row(row)

    def list(self) -> list[Customer]:
        return [_from_row(r) for r in self.db.list_customers()]

    def revoke(self, customer_id: str) -> bool:
        return self.db.revoke_customer(customer_id)

    def count_active(self) -> int:
        try:
            return self.db.count_active_customers()
        except Exception:  # DB 불통: 인증은 열어 두고, 작업 생성이 503을 낸다(기존 동작)
            return 0
