"""설정 읽기와 오류별 CLI 종료 코드."""

import json

import pytest

from tashkeel_check.cli import main
from tashkeel_check.config import Settings, load_settings
from tashkeel_check.errors import AnalyzerUnavailable, ConfigError, InputError


def test_env_file_values_are_typed_and_existing_env_wins(clean_env, monkeypatch):
    env = clean_env / "custom.env"
    env.write_text("REPEATS=5\nHIGH_CONFIDENCE=0.9\nTEMPERATURE=\nENABLE_BUNDLE_SEARCH=true\n")
    monkeypatch.setenv("REPEATS", "7")
    s = load_settings(env)
    assert s.repeats == 7 and s.high_confidence == 0.9 and s.enable_bundle_search is True
    assert s.temperature is None  # 빈 값은 설정하지 않은 것


def test_invalid_setting_is_a_config_error(clean_env, monkeypatch):
    monkeypatch.setenv("HIGH_CONFIDENCE", "1.5")
    with pytest.raises(ConfigError, match="high_confidence"):
        load_settings()


def test_settings_constructor_ignores_the_environment(monkeypatch):
    monkeypatch.setenv("REPEATS", "9")
    assert Settings().repeats == 3


def test_errors_keep_standard_bases():
    assert issubclass(InputError, ValueError)
    assert issubclass(ConfigError, RuntimeError)
    assert issubclass(AnalyzerUnavailable, ConfigError)


def test_cli_exit_code_for_missing_api_key(clean_env, mini_doc, capsys):
    doc = clean_env / "doc.json"
    doc.write_text(json.dumps(mini_doc, ensure_ascii=False))
    assert main(["run", "--doc", str(doc), "--condition", "C1"]) == 3
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_cli_exit_code_for_bad_input(clean_env, capsys):
    doc = clean_env / "empty.json"
    doc.write_text(json.dumps({"doc_id": "empty", "segments": []}))
    assert main(["run", "--doc", str(doc), "--condition", "C1", "--fake"]) == 2
    assert "no segments" in capsys.readouterr().err


def test_cli_exit_code_for_bad_setting(clean_env, monkeypatch, capsys):
    monkeypatch.setenv("REPEATS", "0")
    assert main(["exp002", "--split", "dev", "--limit", "1"]) == 3
    assert "repeats" in capsys.readouterr().err
