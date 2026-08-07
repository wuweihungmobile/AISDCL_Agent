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


# ──────────────────────────────────────────────────────────────
# R79 收輪（掌舵者系統問題 S3／QA 實測）：PG 自動偵測掛到**本機預設路徑**上
# ──────────────────────────────────────────────────────────────
# 缺陷本體（QA 當回合親跑）：R79 落地的 `local_ci_gate.pg_autodetect()` 機制本身是好的
# （直接呼叫它回 True），但它當時**只有 local_ci_gate 一個呼叫端**，而掌舵者實際在跑的
# 那條路（`python -m pytest tests/ -q`，不設任何環境變數）根本不經過它 ⇒ 修完之後那個
# 數字仍是 136 skipped，一支都沒少。「掛錯入口」對使用者而言與「沒做」是同一件事。
# conftest 是 pytest **一定**會載的那一層，掛在這裡才會對每一個入口生效（本機直跑／
# pre-push 的 AutoClaude leg／CI test job），而不是只對「有人記得跑 local_ci_gate」生效。
#
# 安全性——四條剎車全部沿用 `local_ci_gate.pg_autodetect()`，本檔**不複製任何一條判斷**
# （同一份知識只有一個家；這是本 repo 最常復發的缺陷形態）：
#   ① 使用者已顯式設過任一 DSN 變數 ⇒ 不碰（顯式優先）；② `CI` 有值 ⇒ 不跑；
#   ③ 本行程已在跑某支測試 ⇒ 不跑；④ 那顆 DB 必須真的被 migrate 過才注入。
#   偵測不到 PG 就**靜默不注入**——沒有 Docker／沒有 PG 的機器一切照舊，不會多一個紅字。
#   整條關掉：`AUTOCLAUDE_NO_PG_AUTODETECT=1`。
# 本檔另加第 ⑤ 條：載入或呼叫失敗一律吞掉並記下理由。這裡 fail-open 是對的——失敗時
# 事情回到「沒有這個機制」的原狀，而不是讓一個為了方便而加的東西有能力弄垮整個 session。
_LOCAL_CI_GATE_PATH = Path(__file__).resolve().parent.parent / "tools" / "local_ci_gate.py"

#: `pytest_configure` 的量測結果，供 `pytest_terminal_summary` 印給人看。
_PG_AUTODETECT_NOTE: str | None = None


def _local_ci_gate():
    """載入 `AutoClaude/tools/local_ci_gate.py`；失敗回 None。

    刻意以檔案路徑載入而不是 `sys.path.insert(0, tools/)`：那會讓整個 session 的
    top-level 匯入空間多出一整個目錄的模組名，而本檔是**最早**被載入的那一層，遮蔽
    範圍最大。註冊回 `sys.modules["local_ci_gate"]` 是為了與
    `tests/tools/test_local_ci_gate.py` 共用**同一個模組物件**——兩份副本會各有一份
    模組級狀態，那正是「同一份知識兩個家」的執行期版本。
    """
    import importlib.util

    cached = sys.modules.get("local_ci_gate")
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location("local_ci_gate", _LOCAL_CI_GATE_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["local_ci_gate"] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop("local_ci_gate", None)
        raise
    return module


def pytest_configure(config):  # noqa: ARG001
    """在**收集之前**跑一次 PG 自動偵測（模組級 skipif 於收集時求值，晚一步就沒用了）。"""
    global _PG_AUTODETECT_NOTE
    try:
        gate = _local_ci_gate()
        if gate is None:
            _PG_AUTODETECT_NOTE = f"跳過：載入不到 {_LOCAL_CI_GATE_PATH}"
            return
        _, why = gate.pg_autodetect()
        _PG_AUTODETECT_NOTE = why
    except Exception as exc:  # noqa: BLE001 — 見上方第 ⑤ 條
        _PG_AUTODETECT_NOTE = f"跳過：自動偵測本身出錯（{type(exc).__name__}: {exc}）"


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

# R74（PKG-4 E）：**反方向**的對稱標籤。SSOT＝根層 `tools/lib/windows_skip_tags.py`
# （`POSIX_NATIVE_SKIP_TAG`／`MAC_NATIVE_SKIP_TAG`），此處比照上一行 `WINDOWS_NATIVE_
# SKIP_TAG` 的既有慣例各持一份字面值——兩套測試框架 pytest root 不同、本檔刻意不 import
# 根層模組（本檔頭已載明「兩套測試框架不強求共用同一檔案，但邏輯必須一致」）。
# 形態不一致由 `tools/tests/test_platform_neutral_paths.py::TestSkipDirectionAndTagSymmetry`
# 那一組的靜態判準看著：它掃 `AutoClaude/tests` 整棵樹，reason 沒帶標籤的站點會被棘輪擋。
#
# WHY 這一段非加不可：本檔原本只把 `[WINDOWS-NATIVE-ONLY]` 那一批另印成醒目清單，
# 於是在 **Windows 上跑** 時（此機器每天在跑的那一側）真正的覆蓋損失一筆都不會被凸顯
# ——那一批全落在反方向，而反方向此前沒有標籤、沒有摘要、沒有計數。
#
# 🔴 R76 誠實補記（R76-15）：上面那句「非加不可」在 R74~R75 兩輪裡**沒有兌現**——
# 機制加了，但 `AutoClaude/tests` 的 6 個 posix-only 站點 0/6 帶標籤，`non_windows_
# native_skips()` 在 Windows 上恆回空清單 ⇒ 本區塊連續兩輪一行都沒印過，而
# `skip_tag_policy._POSIX_TAG_RATCHET` 把那 6 筆凍結成「可見欠債」讓鎖同時恆綠。
# R76 把 6 筆全補標（棘輪降為 0、並加 shrink-only 天花板擋住「把基線改大」這條出口），
# 同一批測試實測印出 17 行。教訓：**加一個為了看見 X 的機制，若 X 的入口（標籤）沒人
# 補，機制與看著它的鎖會一起沉默**，而沉默的方向永遠是「看起來很乾淨」。
# 本區塊自 R76 起有回歸鎖：`tests/test_conftest_windows_native_skip_report.py` 的
# 反方向兩支（正向＋負向），刪掉本區塊或把標籤篩選改成「全收」都會當場紅。
POSIX_NATIVE_SKIP_TAG = "[POSIX-NATIVE-ONLY]"
MAC_NATIVE_SKIP_TAG = "[MAC-NATIVE-ONLY]"
NON_WINDOWS_SKIP_TAGS = (POSIX_NATIVE_SKIP_TAG, MAC_NATIVE_SKIP_TAG)


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


def non_windows_native_skips(terminalreporter) -> list[str]:
    """純函式（無 I/O 副作用，與印出分離，比照 `windows_native_skips`）：篩出帶
    `[POSIX-NATIVE-ONLY]`／`[MAC-NATIVE-ONLY]` 的 skip，回傳 nodeid 清單。"""
    tagged: list[str] = []
    for report in terminalreporter.stats.get("skipped", []):
        reason = _skip_reason(report)
        if reason and any(tag in reason for tag in NON_WINDOWS_SKIP_TAGS):
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
    if tagged_ids:
        terminalreporter.write_sep("=", "WINDOWS-NATIVE-ONLY SKIPS (未在原生 Windows 環境驗證)")
        terminalreporter.write_line(
            f"{len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
            f"（非一般 skip，見 DEF-101-348/R44）："
        )
        for node_id in tagged_ids:
            terminalreporter.write_line(f"  - {node_id}")
    posix_ids = non_windows_native_skips(terminalreporter)
    if posix_ids:
        terminalreporter.write_sep(
            "=", "POSIX/MAC-NATIVE-ONLY SKIPS (本次跑在 Windows 上失去的覆蓋)")
        terminalreporter.write_line(
            f"{len(posix_ids)} 個非 Windows 專屬測試本次「因為跑在 Windows 上而沒跑」"
            f"（R74／PKG-4 E：反方向的覆蓋損失此前無任何標籤／摘要／計數）："
        )
        for node_id in posix_ids:
            terminalreporter.write_line(f"  - {node_id}")
    # R79 收輪：**剖面標記**——把「這次是在有沒有 PG 的條件下跑的」寫進輸出本身。
    # 消費者＝`local_ci_gate.py --census-only`（push 通道與 CI 用它判 skip 分群天花板）。
    # 它讀的是別的行程留下的 log，而 conftest 注入的 DSN 只存在於 **pytest 這個行程**的
    # env 裡，不會傳給任何父行程 ⇒ 只有這裡說得準，就必須由這裡寫下來。標記字串由
    # local_ci_gate 產生（唯一真相源），本檔不自己拼；載不到就不印——`--census-only`
    # 會因為找不到標記而 fail-loud，那正確：剖面量不到時任何天花板比較都沒有意義。
    try:
        gate = _local_ci_gate()
    except Exception:  # noqa: BLE001 — 印摘要不得有能力弄垮 session（同 pytest_configure）
        gate = None
    if gate is not None:
        terminalreporter.write_line(gate.pg_marker_line(gate.pg_dsn_in_effect()))
    if _PG_AUTODETECT_NOTE:
        terminalreporter.write_line(f"[PG autodetect] {_PG_AUTODETECT_NOTE}")
