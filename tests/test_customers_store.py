"""고객·API 키 저장소와 사용량 집계(ADR-019). 메모리 저장소는 항상, Postgres는 db 마커."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from tashkeel_check.web.customers import KEY_PREFIX, MemoryCustomerStore, hash_key
from tashkeel_check.web.usage import MemoryUsageStore, UsageRecord, summarize


def test_memory_store_issues_key_once_and_hashes_it():
    store = MemoryCustomerStore()
    c, key = store.add("acme")
    assert key.startswith(KEY_PREFIX) and len(key) == len(KEY_PREFIX) + 48
    assert c.key_prefix == key[:9] and c.active
    assert store.by_key(key) == c and store.by_key(key + "x") is None
    assert store.count_active() == 1 and [x.id for x in store.list()] == [c.id]
    assert hash_key(key) == hash_key(" " + key + "\n")  # 공백만 정리


def test_revoke_disables_key():
    store = MemoryCustomerStore()
    c, key = store.add("acme")
    assert store.revoke(c.id) and not store.revoke(c.id)
    assert store.by_key(key) is None and store.count_active() == 0
    assert store.list()[0].active is False and store.list()[0].revoked_at is not None


def test_usage_summary_filters_by_customer_and_window():
    store = MemoryUsageStore()
    t0 = datetime(2026, 10, 21, 12, tzinfo=UTC)
    store.record(
        UsageRecord(customer_id="a", kind="document", total_tokens=10, llm_calls=1, n_segments=3, created_at=t0)
    )
    store.record(UsageRecord(customer_id="a", kind="bundle_label", n_segments=5, created_at=t0 + timedelta(days=1)))
    store.record(UsageRecord(customer_id="b", kind="document", total_tokens=99, created_at=t0))
    store.record(UsageRecord(customer_id="a", kind="document", total_tokens=7, created_at=t0 - timedelta(days=40)))
    body = store.summary("a", t0 - timedelta(days=1), t0 + timedelta(days=2))
    assert body["totals"] == {
        "jobs": 2,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 10,
        "llm_calls": 1,
        "segments": 8,
        "arabic_tokens": 0,
    }
    assert [d["day"] for d in body["by_day"]] == ["2026-10-21", "2026-10-22"]
    assert {k["kind"]: k["jobs"] for k in body["by_kind"]} == {"bundle_label": 1, "document": 1}
    assert store.summary(None, t0, t0 + timedelta(hours=1))["totals"]["jobs"] == 2  # 범위 없음 = 전체
    assert summarize([], t0, t0)["totals"]["jobs"] == 0


@pytest.mark.db
def test_postgres_customer_store_and_usage(tmp_path):
    from tashkeel_check.web.customers import DbCustomerStore
    from tashkeel_check.web.db import Database
    from tashkeel_check.web.usage import DbUsageStore

    db = Database(os.environ["DATABASE_URL"])
    store = DbCustomerStore(db)
    name = f"cust_{tmp_path.name}"
    c, key = store.add(name)
    assert store.by_key(key) is not None and store.by_key(key).id == c.id
    assert any(x.id == c.id and x.key_prefix == c.key_prefix for x in store.list())
    assert store.count_active() >= 1
    usage = DbUsageStore(db)
    usage.record(UsageRecord(customer_id=c.id, kind="document", total_tokens=5, n_segments=2))
    body = usage.summary(c.id, datetime.now(UTC) - timedelta(minutes=5), datetime.now(UTC) + timedelta(minutes=5))
    assert body["totals"]["jobs"] == 1 and body["totals"]["total_tokens"] == 5
    assert store.revoke(c.id) and store.by_key(key) is None
