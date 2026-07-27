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
import sys
from pathlib import Path

import pytest

# 啟用 pytester 內建 plugin —— test_windows_native_skip_report.py 用它以子行程
# 方式驗證 pytest_terminal_summary() 的印出副作用（見該檔說明）。這是 pytest 官方
# 文件記載的啟用方式，須放在 testpaths 的頂層 conftest.py（本檔即是），放在巢狀
# conftest.py 會被 pytest 拒絕。
pytest_plugins = ["pytester"]


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
# R56（跨平台複審）：裸 `python` 解析保險 — 自 tests/equivalence/conftest.py 上移
# ──────────────────────────────────────────────────────────────
# 原 fixture 只掛在 tests/equivalence/，但同一根因（macOS `/usr/bin` 與多數現代
# Linux distro 的乾淨 PATH 上只有 `python3`、沒有裸 `python`；Windows 則因 venv
# Scripts/ 內就有 python.exe 而不會踩到）在 equivalence/ 以外還影響至少 6 個目錄的
# 測試——未 activate venv、直接以 `<repo>/.venv/bin/python -m pytest` 呼叫時，
# 走 `subprocess.run(shell=True)` 的 evaluator（ShellEvaluator / evaluator.py /
# SDD adapter 推導出的 `python -m pytest ...`）會拿到 `/bin/sh: python: command
# not found`（rc=127），macOS 實測 11 個測試硬失敗。fixture 留在子目錄等於讓
# 「是否套用平台保險」取決於測試檔放在哪個資料夾，與被測行為無關。
#
# 本 fixture 只 prepend 當前直譯器所在目錄，不覆寫整個 PATH；刻意以 monkeypatch
# 施作（function scope 自動還原），對「明確自帶 env= 的隔離子行程」完全無影響——
# 例如 tests/infra/test_sdd_to_playbook_adapter.py::
# test_evaluator_cmd_actually_runnable_without_bare_python 以 `env={"PATH": <只放
# pytest symlink 的隔離目錄>}` 執行，其「PATH 上沒有裸 python」的迴歸鎖語意不受
# 本 fixture 影響（該測試原本反而因 `shutil.which("pytest")` 找不到 pytest 而在未
# activate venv 時直接 assert 失敗，上移後才真正跑得到它要鎖的東西）。
@pytest.fixture(autouse=True)
def _interpreter_dir_on_path(monkeypatch):
    """讓子行程的裸 `python` 一律解析到當前直譯器（venv 未 activate 亦可）。"""
    py_dir = str(Path(sys.executable).parent)
    path = os.environ.get("PATH", "")
    if path.split(os.pathsep)[:1] != [py_dir]:
        monkeypatch.setenv("PATH", py_dir + os.pathsep + path if path else py_dir)


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


# ──────────────────────────────────────────────────────────────
# R44（DEF-101-348 方向①遺漏補完）：[WINDOWS-NATIVE-ONLY] skip 可見度機制
# ──────────────────────────────────────────────────────────────
# R43 已為 tools/tests/（unittest 執行路徑）補上此機制
# （tools/run_root_unittests.py 的 `WINDOWS_NATIVE_SKIP_TAG` /
# `report_windows_native_skips()`），但完全沒有涵蓋 AutoClaude/tests/（pytest
# 執行路徑）——test_perception.py::TestCloseKillsCmdShimGrandchild 正是該機制
# 最初的動機來源（DEF-101-348 質疑的就是這支測試），實作範圍卻漏掉它。
# 本節補上 pytest 對等版：於 `pytest_terminal_summary` 掃描本次 session 的
# skipped 清單，篩出 reason 內含 `[WINDOWS-NATIVE-ONLY]` 標籤者另印一段清單
# （即使 `-q` 也不會被吞掉——terminal summary 一律印出，不受 verbosity 影響）。
WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"


def _skip_reason(report) -> str | None:
    """從一則 skipped `TestReport` 取出 reason 文字。

    pytest 對 skip 的 `report.longrepr` 固定是 `(path, lineno, "Skipped: <reason>")`
    三元組（`pytest.mark.skipif` 與 `pytest.skip()` 走同一條 `TestReport.from_item_and_call`
    路徑，格式一致；已用實際跑出的 report 驗證過，非憑印象假設 `_pytest/reports.py`
    行為）。非此形狀（例如 collect error 之類）一律回 None，呼叫端視為「非本機制
    對象」略過，不誤判。
    """
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return None


def windows_native_skips(terminalreporter) -> list[str]:
    """純函式（無 I/O 副作用）：從 `terminalreporter.stats["skipped"]` 篩出帶
    `[WINDOWS-NATIVE-ONLY]` 標籤者，回傳 nodeid 清單。與 `pytest_terminal_summary`
    的印出副作用分離（比照 tools/run_root_unittests.py::windows_native_skips 同款
    設計：純函式可獨立單元測試，不會因為呼叫它而污染真實終端輸出）。
    """
    tagged: list[str] = []
    for report in terminalreporter.stats.get("skipped", []):
        reason = _skip_reason(report)
        if reason and WINDOWS_NATIVE_SKIP_TAG in reason:
            tagged.append(report.nodeid)
    return tagged


def pytest_terminal_summary(terminalreporter, exitstatus, config):  # noqa: ARG001
    """在一般 `skipped=N` 摘要之外，另印出「僅原生 Windows 上才具驗證價值」的
    skip 清單（R44，DEF-101-348 方向①補完；對等
    tools/run_root_unittests.py::report_windows_native_skips()）。刻意不用
    emoji（✅/❌/⚠️）——`tools/_stdio_utf8.py` 記載的 DEF-101-069 landmine：
    Windows 非 UTF-8 終端印 emoji 會直接 UnicodeEncodeError 崩潰，而
    `terminalreporter` 底層 TerminalWriter 未做這層保護，用純 ASCII 分隔線
    （`write_sep`）換取同等「不會被淹沒在 -q 摘要裡」的醒目效果更安全。
    """
    tagged_ids = windows_native_skips(terminalreporter)
    if not tagged_ids:
        return
    terminalreporter.write_sep("=", "WINDOWS-NATIVE-ONLY SKIPS (未在原生 Windows 環境驗證)")
    terminalreporter.write_line(
        f"{len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
        f"（非一般 skip，見 DEF-101-348/R44）："
    )
    for node_id in tagged_ids:
        terminalreporter.write_line(f"  - {node_id}")
