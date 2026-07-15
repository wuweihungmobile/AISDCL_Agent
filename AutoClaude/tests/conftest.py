"""
頂層 conftest（測試環境共用設定）。

本檔目前用於記錄測試會用到的環境變數，並在未來需要時擴充共用 fixture。

──────────────────────────────────────────────
PostgreSQL DSN 環境變數命名（L2 finding 統一說明）
──────────────────────────────────────────────

AutoClaude 在不同情境下會讀取下列三個環境變數，請勿混用：

- `AUTOCLAUDE_DB_DSN`：Production / 一般測試主要 DSN（推薦使用）。
  讀取位置：`factory.py`、`alembic/env.py`。
- `AUTOCLAUDE_PG_DSN`：Legacy 名稱（已 deprecated，仍向後相容）。
  `factory.py` 解析優先序為 `AUTOCLAUDE_DB_DSN` > 本項。
- `AUTOCLAUDE_TEST_PG_DSN`：**契約測試專用**，避免污染本地正式 DB。
  讀取位置：`tests/contract/test_pg_state_repository_contract.py`。

設定方式範例（PowerShell）：

  $env:AUTOCLAUDE_DB_DSN = "postgresql+asyncpg://user:pass@localhost:5432/autoclaude?sslmode=require"
  $env:AUTOCLAUDE_TEST_PG_DSN = "postgresql+asyncpg://user:pass@localhost:5432/autoclaude_test?sslmode=disable"

未設定 `AUTOCLAUDE_TEST_PG_DSN` 時，PG 契約測會自動 skip — 這是預期行為，
本機開發者 **不需** 安裝 PG 也能跑完所有 925+ 測試。

──────────────────────────────────────────────
跨平台測試 fixture 撰寫紀律（四方複審 S21）
──────────────────────────────────────────────

若本套件日後出現「複製 `sys.executable` 偽裝健康 venv」或「建立 symlink 模擬快取」
這類平台敏感 fixture 需求，請比照 `tools/tests/_platform_helpers.py`
（`copy_functional_interpreter()` / `create_symlink_or_skip()`）的邏輯撰寫對稱
fixture——該檔已記錄 DEF-101-064／DEF-101-069 的完整踩雷細節（sys.executable 在
Windows venv-launcher 佈局下依賴同層 pyvenv.cfg、非管理者帳號無 symlink 建立權限
等），不必重新踩雷。兩套測試框架 pytest root 不同，不強求共用同一檔案，但邏輯必須
一致、且新 fixture 合入前須至少於一次目標平台的真實 CI run 驗證過（mock
`sys.platform` 不算數；見根層 ONBOARDING.md §10 與 DEF-101-064／DEF-101-069）。
"""
from __future__ import annotations

import os
import re

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="重新生成等價測試快照（test_kernel_snapshot.py / test_runner_snapshot.py）",
    )


# SD_09 W2 後續處理（2026-05-21）— pytest-randomly cross-test cwd state leak 防漏 fixture
# 對應 SD_Improving_09.md §523 範圍外議題「pre-existing test isolation」。
# 即便目前測試無顯式 os.chdir，pytest-randomly 隨機順序可能觸發 import-time side-effect 或
# 第三方 plugin（如 hypothesis profile load）暗中變更 cwd → 後續測試 Path() 相對寫入錯位。
# autouse 全域保險：每個 test 前 snapshot cwd，test 結束自動還原（即使 raise）。
@pytest.fixture(autouse=True)
def _preserve_cwd():
    """SD_09 W2：防 cross-test cwd state leak（pytest-randomly 隨機順序保險）。

    僅在 cwd 實際被變更時才印 WARN 並還原，避免污染正常測試輸出。
    """
    import os as _os
    original_cwd = _os.getcwd()
    try:
        yield
    finally:
        current_cwd = _os.getcwd()
        if current_cwd != original_cwd:
            import sys as _sys
            _sys.stderr.write(
                f"::warning::cwd leak detected; restoring "
                f"{current_cwd!r} -> {original_cwd!r}\n"
            )
            try:
                _os.chdir(original_cwd)
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────
# SD_07 W2 T2-7：opt-in PG fixture（PM #2）
#
# `pg_real` marker 標記的測試，當下列條件全部滿足時執行：
#   - 環境變數 SD07_REAL_PG_E2E_ENABLED=true
#   - 環境變數 AUTOCLAUDE_TEST_PG_DSN 或 AUTOCLAUDE_DB_DSN
# 否則自動 skip（本地預設、CI nightly 啟用）。
#
# 此 fixture 不 autouse；測試需明確標 `@pytest.mark.pg_real`，或函式參數
# 引入 `real_pg_dsn` fixture。
# ──────────────────────────────────────────────────────────────


def _resolve_real_pg_dsn() -> str | None:
    if os.environ.get("SD07_REAL_PG_E2E_ENABLED", "").lower() != "true":
        return None
    raw = (
        os.environ.get("AUTOCLAUDE_TEST_PG_DSN")
        or os.environ.get("AUTOCLAUDE_DB_DSN")
    )
    if not raw:
        return None
    # asyncpg → psycopg2 兼容（contract test 內 _FakeSql 直接用 DSN）
    return re.sub(r"\+asyncpg", "", raw)


@pytest.fixture(scope="session")
def real_pg_dsn() -> str:
    """SD_07 T2-7：真實 PG DSN fixture（opt-in via pg_real marker / env vars）。

    缺少任一啟用條件 → skip，不阻塞 local 開發 / 一般 CI。
    """
    dsn = _resolve_real_pg_dsn()
    if dsn is None:
        pytest.skip(
            "SD_07 真實 PG e2e 未啟用 — 需 SD07_REAL_PG_E2E_ENABLED=true + "
            "AUTOCLAUDE_TEST_PG_DSN（或 AUTOCLAUDE_DB_DSN）（PM #2）。"
        )
    return dsn


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """自動為 pg_real 標記但未啟用真實 PG 的測試加 skip reason（CI 友善 log）。"""
    if _resolve_real_pg_dsn() is not None:
        return  # 啟用條件滿足 — 不需 skip
    skip_marker = pytest.mark.skip(
        reason="SD_07 pg_real：未啟用 SD07_REAL_PG_E2E_ENABLED=true 或缺 DSN（PM #2）"
    )
    for item in items:
        if "pg_real" in item.keywords:
            item.add_marker(skip_marker)
