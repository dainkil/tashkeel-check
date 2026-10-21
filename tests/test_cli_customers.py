"""`tashkeel customers` 명령(ADR-019)."""

from __future__ import annotations

import pytest

from tashkeel_check.cli import main

from .conftest import DB_URL


def test_customers_needs_database_url(clean_env, capsys):
    assert main(["customers", "add", "--name", "x"]) == 3  # ConfigError
    assert "DATABASE_URL" in capsys.readouterr().err


@pytest.mark.db
def test_customers_add_list_revoke(clean_env, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    name = f"cli_{tmp_path.name}"
    assert main(["customers", "add", "--name", name]) == 0
    out = capsys.readouterr().out
    cid = next(line.split(": ", 1)[1] for line in out.splitlines() if line.startswith("customer_id: "))
    key = next(line.split(": ", 1)[1] for line in out.splitlines() if line.startswith("api_key: "))
    assert key.startswith("tk_") and "다시 보여 주지 않는다" in out
    assert main(["customers", "list"]) == 0
    listed = capsys.readouterr().out
    assert cid in listed and key not in listed and key[:9] in listed
    assert main(["customers", "revoke", cid]) == 0
    assert main(["customers", "revoke", cid]) == 2  # InputError: 이미 비활성
