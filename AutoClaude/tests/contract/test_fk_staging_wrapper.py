"""tests/contract/test_fk_staging_wrapper.py — D-05（SD_09 W0 三次 zero-trust audit 補建）。

對應 AC-SD09-15 / F-05 ADR-SD09-001 §2.3 紅線 ❌21：
  `tests/integration/fixtures/fk_staging_1m_wrapper.py` 的契約測試
  ≥ 3 case：
    1. test_no_pg_env_returns_skipped — 無 PG env 時必須 skipped 不 raise
    2. test_dsn_resolution_priority    — AUTOCLAUDE_DB_DSN 優先於 AUTOCLAUDE_PG_DSN
    3. test_masked_dsn_output          — 含 user:pass@host 的 DSN 不可洩漏密碼

均以 monkeypatch / mock 替代 subprocess，不依賴真 PG / bash / psql。
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.integration.fixtures import fk_staging_1m_wrapper as wrapper_module
from tests.integration.fixtures.fk_staging_1m_wrapper import fk_staging_1m_dryrun


@pytest.fixture(autouse=True)
def _clear_pg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """每個 case 先清空 PG 相關 env，避免本機殘留干擾。"""
    monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
    monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)


def test_no_pg_env_returns_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """無 PG env + 無 explicit DSN → status='skipped' 並含 reason，不 raise。"""
    # 額外保險：模擬 psql / bash 都不存在亦不該影響 skipped 判定
    monkeypatch.setattr(wrapper_module.shutil, "which", lambda _: None)

    result = fk_staging_1m_dryrun()

    assert result["status"] == "skipped"
    assert "no_pg_env" in result["reason"]
    assert "AUTOCLAUDE_DB_DSN" in result["reason"]
    assert result["rows"] == 1_000_000
    assert result["dry_run"] is True


def test_dsn_resolution_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTOCLAUDE_DB_DSN > AUTOCLAUDE_PG_DSN；只設 PG_DSN 也能解析到。"""
    # 情境 A：兩者都設 → 必須選 DB_DSN
    monkeypatch.setenv("AUTOCLAUDE_DB_DSN", "postgresql://u:p@host/db_new")
    monkeypatch.setenv("AUTOCLAUDE_PG_DSN", "postgresql://u:p@host/db_old")
    assert wrapper_module._resolve_dsn(None) == "postgresql://u:p@host/db_new"

    # explicit 參數最優先
    assert (
        wrapper_module._resolve_dsn("postgresql://explicit/x")
        == "postgresql://explicit/x"
    )

    # 情境 B：只設 PG_DSN（deprecated）依舊回得到
    monkeypatch.delenv("AUTOCLAUDE_DB_DSN", raising=False)
    assert wrapper_module._resolve_dsn(None) == "postgresql://u:p@host/db_old"

    # 情境 C：兩者都無
    monkeypatch.delenv("AUTOCLAUDE_PG_DSN", raising=False)
    assert wrapper_module._resolve_dsn(None) is None


def test_masked_dsn_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ok 路徑 mock subprocess.run，回傳的 dsn_masked 不可含明文密碼。"""
    monkeypatch.setenv("AUTOCLAUDE_DB_DSN", "postgresql://alice:s3cret@db.local:5432/app")

    # mock 環境檢查：強制視為「有 PG 環境」
    monkeypatch.setattr(
        wrapper_module, "_has_pg_environment", lambda _dsn: (True, "ok")
    )

    fake_completed = SimpleNamespace(
        returncode=0,
        stdout="step ok\n" * 5,
        stderr="",
    )
    with patch.object(subprocess, "run", return_value=fake_completed) as patched_run:
        result = fk_staging_1m_dryrun(rows=10_000)

    assert patched_run.called, "subprocess.run 必須被呼叫"
    assert result["status"] == "ok"
    assert result["returncode"] == 0
    assert result["rows"] == 10_000
    assert "dsn_masked" in result
    # 紅線：明文密碼絕對不可出現在輸出
    assert "s3cret" not in result["dsn_masked"], (
        f"DSN 密碼洩漏：{result['dsn_masked']!r}"
    )
    # 但 dsn_masked 仍應保留 db 名 / host 結構（便於 debug）
    assert "db.local" in result["dsn_masked"] or "***" in result["dsn_masked"]
