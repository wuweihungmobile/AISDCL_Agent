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

設定方式範例（🔴 R83：本段原本只有 PowerShell 一種形態。`$env:X = …` 是 PowerShell 專屬
語法，mac/Linux 照抄會得到 `command not found`／參數解析錯誤，而這份說明的讀者一半在 mac
上——單平台指引長在「專門用來把人導向正解」的地方，比沒有指引更糟）：

  PowerShell：
    $env:AUTOCLAUDE_DB_DSN = 'postgresql+asyncpg://user:pass@localhost:5432/autoclaude?sslmode=require'
    $env:AUTOCLAUDE_TEST_PG_DSN = 'postgresql+asyncpg://user:pass@localhost:5432/autoclaude_test?sslmode=disable'
  bash / zsh：
    export AUTOCLAUDE_DB_DSN='postgresql+asyncpg://user:pass@localhost:5432/autoclaude?sslmode=require'
    export AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://user:pass@localhost:5432/autoclaude_test?sslmode=disable'

未設定 `AUTOCLAUDE_TEST_PG_DSN` 時，PG 契約測會自動 skip — 這是預期行為，
本機開發者 **不需** 安裝 PG 也能跑完全套測試（🔴 R83 複驗訂正：本行原本寫死「925+ 測試」，
而當回合實測早已是它的四倍餘。全 repo pytest 基線數字的**唯一站點**是根層 `ONBOARDING.md` §7，
本行不再重複——那個數字每輪都在動，寫在這裡就是第二個沒人會去改的家。
🔴 它此前**沒有任何鎖看得到**：`tools/check_pytest_baseline_sites.py` 的未納管站點發現面
當回合實測 114 支，本檔不在其中——「測試」二字不構成該掃描器的關鍵詞命中）。

🔴 想把上面那批 skip 一次消掉最大的一類：不必改程式、不必設環境變數，只要把 CI 對等 PG
容器拉起來（`docker compose -f docker-compose.ci.yml up -d`，daemon 要先開），本檔的
PG autodetect 會自動注入 DSN。完整做法／憑證行／現查指令見根層 `ONBOARDING.md` §7.1。

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


# ── R80 包 A（S3-06）：`AUTOCLAUDE_TEST_PG_DSN` 的形態驗證 ─────────────────────
#
# 🔴 缺陷本體（當回合逐檔實查）：這一個環境變數有**兩類驅動需求互斥**的消費端，而全 repo
# 對它零驗證：
#   · 非同步端（`tests/contract/test_pg_state_repository_contract.py:47`、
#     `test_pg_existing_schema_lock.py` 的 CRUD 快照）把它原封不動餵給
#     `sqlalchemy.ext.asyncio.create_async_engine` ⇒ **必須**帶 async driver（`+asyncpg`）；
#   · 同步端（`tests/contract/test_alembic_00*.py`、conftest 的 `_resolve_real_pg_dsn`）
#     一律先 `re.sub(r"\+asyncpg", "", raw)` 再交給 psycopg2 ⇒ 帶不帶都能跑。
# ⇒ 兩端的交集只有「帶 `+asyncpg`」這一種寫法，而那件事只寫在文件裡、沒有任何東西在驗。
# 照文件以外的**合法** DSN 形態設值（`postgresql://user:pass@host/db`，psycopg2 與
# libpq 都吃得下）時，非同步端那一批會在 fixture setup 硬炸，訊息由 SQLAlchemy 發出、
# 指向 driver 選型，**完全不提這個環境變數或這個 repo** ⇒ 使用者要自己從 SQLAlchemy 的
# 錯誤反推回「原來是我 export 的字串少了四個字」。
# 本函式把那個反推變成一句話，並且在**收集之前**就講（晚一步就變成 N 支 error 而不是一則指引）。
_ASYNC_DRIVERS = ("+asyncpg", "+psycopg", "+aiopg")

# 🔴 R83（掌舵者系統問題 #1／包 W2-B）：把「設一個環境變數」渲染成**兩個平台都能直接照抄**
# 的兩行，而不是只印 PowerShell 那一行。
#
# 缺陷本體（當回合在 macOS 上實測）：本檔上一版的 DSN 修法逐字印
# `$env:AUTOCLAUDE_TEST_PG_DSN = '…'`。`$env:` 是 **PowerShell 專屬**語法——bash/zsh 照抄會把
# `$env:AUTOCLAUDE_TEST_PG_DSN` 展開成空字串再把 `=` 當成指令名，得到一個與 DSN 毫無關係的
# 錯誤。這件事的難看之處在於**它長在一支專門用來「把人導向正解」的訊息上**：這則訊息存在的
# 全部理由，就是省下使用者從 SQLAlchemy 的錯誤反推回「我 export 的字串少了四個字」那段路，
# 而它自己在 mac 上又製造了一段同型的反推。
#
# 為何**兩行都印**而不是依 `sys.platform` 只印一行：這則訊息會被貼進缺陷帳本、CI log、
# 交棒書，讀它的人常常不在產生它的那台機器上（本 repo 的 macOS↔Windows 雙機交替工作流即是）。
# 只印一行的版本在那些場合會再一次變成單平台指引，而那正是本修法要根絕的形態。
# 代價是多一行輸出，換掉的是「讀者在另一個平台上照抄失敗」。
#
# 機械物：`tools/tests/test_skip_discoverability_r83.py`（本 repo 活文件與使用者可見訊息裡的
# 示範指令必須雙平台皆可照抄，零容忍＋行內豁免出口）。
_ENV_RECIPE_TEMPLATE = (
    "     PowerShell：  $env:{var} = '{value}'\n"
    "     bash / zsh：  export {var}='{value}'"
)


def two_platform_env_recipe(var: str, value: str) -> str:
    """回傳「設定環境變數 `var`＝`value`」的雙平台配方（兩行，各自標明平台）。

    純函式（無 I/O、無平台偵測）——刻意**不**依 `sys.platform` 擇一，理由見上方註解。
    """
    return _ENV_RECIPE_TEMPLATE.format(var=var, value=value)


def pg_dsn_problems(dsn: str | None, *, require_async: bool = True) -> list[str]:
    """純函式（無 I/O、無副作用）：這個 DSN 形態會不會讓非同步消費端在 setup 硬炸。

    回空 list ＝可用。刻意只驗「非同步端一定會踩到」的那一點，不做通用 URL 驗證——
    多驗一點就會開始誤擋合法寫法，而誤擋的成本比漏擋高（沒設 DSN 本來就只是 skip）。
    """
    if not dsn:
        return []
    if not dsn.startswith(("postgresql", "postgres")):
        return [
            f"AUTOCLAUDE_TEST_PG_DSN／AUTOCLAUDE_DB_DSN 的 scheme 不是 postgresql：{dsn!r}"
        ]
    if require_async and not any(drv in dsn for drv in _ASYNC_DRIVERS):
        return [
            f"AUTOCLAUDE_TEST_PG_DSN／AUTOCLAUDE_DB_DSN 少了 async driver：{dsn!r}\n"
            "   這個變數同時餵給兩類消費端，而它們的驅動需求互斥：\n"
            "     · 非同步端（tests/contract/test_pg_state_repository_contract.py 等）"
            "直接把它交給 sqlalchemy create_async_engine，**必須**帶 async driver；\n"
            "     · 同步端（tests/contract/test_alembic_00*.py）會自己 strip 掉 `+asyncpg`，"
            "帶不帶都能跑。\n"
            "   ⇒ 兩端的交集只有一種寫法。修法（把 `postgresql://` 改成 `postgresql+asyncpg://`）：\n"
            + two_platform_env_recipe("AUTOCLAUDE_TEST_PG_DSN", _with_asyncpg(dsn))
            + "\n"
            "   不修的話那一批會在 fixture setup 硬炸，而 SQLAlchemy 的錯誤訊息不會提到"
            "這個環境變數，也不會提到這個 repo。"
        ]
    return []


def _with_asyncpg(dsn: str) -> str:
    """把 `postgresql://…` 改寫成 `postgresql+asyncpg://…`（只動 scheme，其餘原封不動）。"""
    scheme, sep, rest = dsn.partition("://")
    return f"{scheme}+asyncpg{sep}{rest}" if sep else dsn


def _check_pg_dsn_shape() -> None:
    """顯式設過 DSN 時驗一次形態；不合格一律 fail-loud（`pytest.UsageError`）。

    🔴 為何是 fail-loud 而不是 skip：skip 的意思是「這次不驗這件事」，而這裡的實況是
    「你**要求**驗這件事、但你給的字串會讓它以看不懂的方式炸掉」——兩者不是同一件事，
    把後者降級成 skip 正是本包在治的那個病（真問題長得像已經被管好了）。
    自動偵測注入的 DSN 不會走到這裡出問題（它自己帶 `+asyncpg`），所以這道只會對
    「人自己 export 了一個合法但不相容的字串」說話。
    """
    # `require_async` 只對 `AUTOCLAUDE_TEST_PG_DSN` 為真——它才是那個「兩類消費端互斥」
    # 的變數；`AUTOCLAUDE_DB_DSN` 的消費端全部會自己 strip driver，對它要求 async
    # 就是誤擋（誠實劃界：這一條界線是逐檔查過消費端才畫的，不是憑對稱猜的）。
    for key, need_async in (("AUTOCLAUDE_TEST_PG_DSN", True), ("AUTOCLAUDE_DB_DSN", False)):
        for problem in pg_dsn_problems(os.environ.get(key), require_async=need_async):
            raise pytest.UsageError(f"[{key}] {problem}")


def pytest_configure(config):  # noqa: ARG001
    """在**收集之前**跑一次 PG 自動偵測（模組級 skipif 於收集時求值，晚一步就沒用了）。"""
    global _PG_AUTODETECT_NOTE
    _check_pg_dsn_shape()
    try:
        gate = _local_ci_gate()
        if gate is None:
            _PG_AUTODETECT_NOTE = f"跳過：載入不到 {_LOCAL_CI_GATE_PATH}"
            return
        _, why = gate.pg_autodetect()
        _PG_AUTODETECT_NOTE = why
        _autoenable_real_pg_e2e()
    except Exception as exc:  # noqa: BLE001 — 見上方第 ⑤ 條
        _PG_AUTODETECT_NOTE = f"跳過：自動偵測本身出錯（{type(exc).__name__}: {exc}）"


def _autoenable_real_pg_e2e() -> None:
    """PG 偵測到了就把 `SD07_REAL_PG_E2E_ENABLED` 一起打開（R81 包 F）。

    🔴 立案理由（掌舵者訴求 S3「徹底解決 skipped」）：本 repo 的紀律逐字寫著
    「skip 理由寫『需要 X』≠ X 缺席」——`pg_real` 這一族的真相是**未啟用**，不是缺件：
    同一個 `pytest_configure` 上一行才剛把一顆健康的 PG 的 DSN 注進環境變數，下一秒卻
    因為另一個旗標沒設而把 3 支測試整組 skip 掉。兩件事的判準來源必須一致，否則
    「本機有 PG」與「本機的 pg_real 有在跑」會永遠是兩個答案。

    刻意只在**沒有人顯式設過**時才動：顯式設 `false` 是一個決定（perf machine／CI 想關掉
    它），自動偵測不得覆寫人的決定。也刻意只在 DSN 真的就位後才開——開了旗標卻沒有 DSN
    只會把 skip 從一句話換成另一句話。

    🔴 R82 包 A2（ENV-01）**刻意不擴充到 `PG_REAL_ENABLED`**——這一格是本輪自己動手做了
    再量出來的反例，不是沿用前人結論：

      · 掃描結論是「只設一個環境變數就 `1 passed in 5.12s` ⇒ 那是欠債型，不是設計型」，
        本輪照做（在本函式一併打開第二個旗標）並實跑，**第一次確實綠**。
      · 但同一支測試在機器同時跑別的東西時實測
        `AssertionError: pgvector recall p95=51.703ms ≥ 50.0ms`（同一份語料、同一顆 PG，
        只差機器忙不忙）。它量的是**延遲 SLA**，而延遲對機器負載敏感 ⇒ 預設打開等於把一支
        會隨鄰居行為翻紅的測試塞進每一個開發者的預設迴圈。
      · ⇒ 原始設計「只在 perf machine 跑」在**這一點上是對的**（錯的是它的措辭，見該檔的
        reason 訂正）。把它自動打開會用一個真缺陷（flaky 閘門）換掉一個假缺陷（誤導文案）。

    保留為顯式 opt-in，配方寫在該檔 reason 裡（一行可貼）。這一格由
    `tests/tools/test_local_ci_gate.py` 的三支 ENV-01 判準釘住，避免下一個人照著掃描結論
    再做一次同樣的事。
    """
    if not (os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")):
        return
    if not os.environ.get("SD07_REAL_PG_E2E_ENABLED"):
        os.environ["SD07_REAL_PG_E2E_ENABLED"] = "true"


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
        # 🔴 R83：本 reason 原本只給 PowerShell 形態的配方（`$env:…`），mac/Linux 讀者照抄無效。
        # 這一則 reason 的**全部價值**就是「照著做就能讓它跑起來」，只在一個平台成立等於對另一
        # 半讀者失效——與本檔 `two_platform_env_recipe` 同一個修法，故改用同一支渲染器。
        reason="[ENV-DISABLED] SD_07 pg_real：未啟用 SD07_REAL_PG_E2E_ENABLED=true 或缺 "
               "DSN（PM #2）。【未啟用，非缺件】本機配方（R81 包 F 實測有效）：\n"
               + two_platform_env_recipe("SD07_REAL_PG_E2E_ENABLED", "true")
               + "\n（DSN 由本 conftest 的 PG autodetect 自動注入，通常不必手設）；"
               "再跑 `python tools/seed_kb.py --mock-pg-seed "
               "--pg-dsn <同一個 DSN>` 備妥語料，否則會換到更深的語料缺件閘"
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
        # 🔴 R82 包 A2（DOC-01）：平台名由 `sys.platform` 動態組字，不得寫死。
        # 修前逐字是「本次跑在 Windows 上失去的覆蓋」，而 2026-08-05 那次真的執行過的
        # macOS CI 輸出裡照樣印著這句話（`gh run view 31021778241 --log` 實測）——
        # 標題騙人與「機制沉默」是同一族失效，只是方向相反：它讓 macOS 上的讀者以為
        # 這一段與自己無關，於是那一側的覆蓋損失同樣沒有人看。
        terminalreporter.write_sep(
            "=", f"POSIX/MAC-NATIVE-ONLY SKIPS (本次跑在 {sys.platform} 上失去的覆蓋)")
        terminalreporter.write_line(
            f"{len(posix_ids)} 個他平台專屬測試本次「因為跑在 {sys.platform} 上而沒跑」"
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
