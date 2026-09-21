"""共享 CI infra：跨版 pytest 同跑 fail-loud guard（DEF-02-001）.

位於 ``AISDLC_SDD/`` 根（versioned 目錄之外，非任一 ``AISDLC_SDD_v0.0X`` 凍結本體，
免 Copy-on-Evolve）。僅薄包裝 ``scripts/cross_version_guard.py`` 的純偵測邏輯。

載入時機（AutoSDD_improving_05 §2.5 實證）：
- ``cd vX && pytest``（官方 gate）→ rootdir=vX，本 conftest 在 confcutdir 之上，**不載入/不干擾**。
- ``cd AISDLC_SDD && pytest``（bare，最常見 footgun）→ rootdir=AISDLC_SDD，本 conftest 載入。

為何用 ``pytest_configure`` 而非 ``pytest_load_initial_conftests``：後者有 chicken-and-egg
——rootdir conftest 是在該 hook 的 default 實作*之內*才被載入，自身實作不會被回呼（真 repo
實證不 fire）。``pytest_configure`` 時本 conftest 必已註冊，且版本目錄的 ``ImportPathMismatchError``
發生於其後的 collection 階段 → configure 先 raise，攔在碰撞之前。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from cross_version_guard import build_guard_message, versions_touched  # noqa: E402


def pytest_configure(config):
    raw_args = list(config.invocation_params.args)
    cwd = str(config.invocation_params.dir)
    versions = versions_touched(raw_args, cwd)
    if len(versions) > 1:
        raise pytest.UsageError(build_guard_message(versions))


# ──────────────────────────────────────────────────────────────
# R44（DEF-101-368，接續 DEF-101-363 方向①遺漏補完）：[WINDOWS-NATIVE-ONLY]
# skip 可見度機制 —— AISDLC_SDD 側對等實作
# ──────────────────────────────────────────────────────────────
# DEF-101-363 已在 AutoClaude/tests/conftest.py 落地 pytest_terminal_summary 可見度
# hook，並「補標籤」了 scripts/tests/test_install_post_commit_windowsapps_guard.py
# 的 `_WINDOWS_PATHEXT_SKIP`（見該檔），但當時只補了標籤字串本身，未在 AISDLC_SDD
# 側佈建對應的 terminal_summary hook：`python -m pytest scripts/tests/`（rootdir=本
# 檔所在的 AISDLC_SDD/）與 `cd AutoClaude && python -m pytest tests/` 是完全獨立的
# 兩個 pytest session，AutoClaude 側的 hook 涵蓋不到本檔的 skip（R44 SD 一審獨立對
# 抗式複審發現）。本節在本檔（`scripts/tests/` 的有效 confcutdir 之內，見上方
# `pytest_configure` docstring 對「cd AISDLC_SDD && pytest」載入時機的既有說明）補上
# 對等實作，純函式與印出副作用分離設計、常數命名與行為對齊 AutoClaude/tests/conftest.py，
# 確保未來新增的 [WINDOWS-NATIVE-ONLY] 標籤 skip 在 AISDLC_SDD 側也會被彙整凸顯。
pytest_plugins = ["pytester"]

WINDOWS_NATIVE_SKIP_TAG = "[WINDOWS-NATIVE-ONLY]"

# DEF-200-248（原 DEF-101-856 ③）：**反方向**的對稱標籤。SSOT＝根層
# `tools/lib/windows_skip_tags.py`（`POSIX_NATIVE_SKIP_TAG`／`MAC_NATIVE_SKIP_TAG`）；本檔比照
# 上一行 `WINDOWS_NATIVE_SKIP_TAG` 的既有慣例各持一份字面值，理由同 AutoClaude/tests/conftest.py
# ——pytest root 不同、刻意不 import 根層模組。此前本側只彙整 `[WINDOWS-NATIVE-ONLY]`，於是
# **在 Windows 上跑**（這台機器每天在跑的那一側）真正失去的覆蓋（他平台專屬 skip）零訊號，
# 「兩平台 skip 行為對齊」的宣稱因此無從佐證。回歸鎖＝
# `scripts/tests/test_conftest_windows_native_skip_report.py` 的反方向三支。
POSIX_NATIVE_SKIP_TAG = "[POSIX-NATIVE-ONLY]"
MAC_NATIVE_SKIP_TAG = "[MAC-NATIVE-ONLY]"
NON_WINDOWS_SKIP_TAGS = (POSIX_NATIVE_SKIP_TAG, MAC_NATIVE_SKIP_TAG)


def _skip_reason(report) -> str | None:
    """從一則 skipped ``TestReport`` 取出 reason 文字（同 AutoClaude/tests/conftest.py
    同名函式行為：``pytest.mark.skipif`` 與 ``pytest.skip()`` 皆固定產出
    ``(path, lineno, "Skipped: <reason>")`` 三元組 ``longrepr``）。非此形狀一律回
    ``None``，呼叫端視為「非本機制對象」略過，不誤判。
    """
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    return None


def windows_native_skips(terminalreporter) -> list[str]:
    """純函式（無 I/O 副作用）：從 ``terminalreporter.stats["skipped"]`` 篩出帶
    ``[WINDOWS-NATIVE-ONLY]`` 標籤者，回傳 nodeid 清單。與 ``pytest_terminal_summary``
    的印出副作用分離，可獨立單元測試。
    """
    tagged: list[str] = []
    for report in terminalreporter.stats.get("skipped", []):
        reason = _skip_reason(report)
        if reason and WINDOWS_NATIVE_SKIP_TAG in reason:
            tagged.append(report.nodeid)
    return tagged


def non_windows_native_skips(terminalreporter) -> list[str]:
    """純函式（與印出分離，比照 ``windows_native_skips``）：篩出帶
    ``[POSIX-NATIVE-ONLY]``／``[MAC-NATIVE-ONLY]`` 的 skip，回傳 nodeid 清單（DEF-200-248）。
    """
    tagged: list[str] = []
    for report in terminalreporter.stats.get("skipped", []):
        reason = _skip_reason(report)
        if reason and any(tag in reason for tag in NON_WINDOWS_SKIP_TAGS):
            tagged.append(report.nodeid)
    return tagged


def pytest_terminal_summary(terminalreporter, exitstatus, config):  # noqa: ARG001
    """在一般 ``skipped=N`` 摘要之外，另印出「僅原生 Windows 上才具驗證價值」的
    skip 清單（對等 AutoClaude/tests/conftest.py::pytest_terminal_summary），以及
    **反方向**（他平台專屬、本次因跑在本平台而沒跑）的清單（DEF-200-248）。刻意
    不用 emoji——`terminalreporter` 底層 TerminalWriter 在非 UTF-8 終端下無防護，
    印 emoji 會 UnicodeEncodeError 崩潰（見 DEF-101-069），純 ASCII 分隔線換取同等
    醒目效果更安全。
    """
    tagged_ids = windows_native_skips(terminalreporter)
    if tagged_ids:
        terminalreporter.write_sep("=", "WINDOWS-NATIVE-ONLY SKIPS (未在原生 Windows 環境驗證)")
        terminalreporter.write_line(
            f"{len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
            f"（非一般 skip，見 DEF-101-363/368）："
        )
        for node_id in tagged_ids:
            terminalreporter.write_line(f"  - {node_id}")
    posix_ids = non_windows_native_skips(terminalreporter)
    if posix_ids:
        # 平台名由 sys.platform 動態組字，不得寫死（同 AutoClaude 側 R82 DOC-01 的教訓：
        # 標題寫死「Windows」會讓 macOS 上的讀者以為這一段與自己無關）。
        terminalreporter.write_sep(
            "=", f"POSIX/MAC-NATIVE-ONLY SKIPS (本次跑在 {sys.platform} 上失去的覆蓋)")
        terminalreporter.write_line(
            f"{len(posix_ids)} 個他平台專屬測試本次「因為跑在 {sys.platform} 上而沒跑」"
            f"（DEF-200-248：反方向的覆蓋損失此前在 AISDLC_SDD 側無任何標籤／摘要／計數）："
        )
        for node_id in posix_ids:
            terminalreporter.write_line(f"  - {node_id}")


# ──────────────────────────────────────────────────────────────
# DEF-200-353／F-SD-01（多 CPU 第十八輪；對稱 AutoClaude/tests/conftest.py
# B1／DEF-200-328 同型缺口）：接根層 `tools/lib/cpu_budget.py` 的實體核心預算。
# ──────────────────────────────────────────────────────────────
# 立案：裸跑 `-n auto`（不經 `scripts/ci-gate.sh`／pre-push 的 cpu_budget 廣播）
# 時 xdist 退回內建演算法（psutil 缺席 → `os.sched_getaffinity` 於 mac 缺席 →
# `os.cpu_count()` 邏輯核），與 SSOT `cpu_budget.py`（互動環境＝實體核 -1）不一致
# （實測：`test_phase_h.py -n auto` 起 gw0..gw9 共 10 個，預算應為 9 個）。本節
# 鏡射 AutoClaude/tests/conftest.py 的七個名字與行為（見該檔同名函式/hook 的完整
# docstring），唯一差異是 `_CPU_BUDGET_PATH`——本檔位於 `AISDLC_SDD/`，其上一層
# 才是 monorepo 根。只走 CLI 契約（subprocess 呼叫 `cpu_budget.py --legs 1`），
# 不 import 根層 `tools/`：套件可能被獨立安裝、`path.exists()` 為 False 時必須
# 靜默退回 xdist 預設。
_CPU_BUDGET_PATH = Path(__file__).resolve().parent.parent / "tools" / "lib" / "cpu_budget.py"

#: `pytest_xdist_auto_num_workers` 的量測結果來源，供 `pytest_sessionstart` 印給人看。
_CPU_BUDGET_SOURCE_NOTE: str | None = None


def _positive_int(value: str | None) -> int | None:
    """把字串解析成正整數；空值／非數字／非正數一律回 None（純函式）。"""
    if not value:
        return None
    try:
        n = int(value.strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _cpu_budget_workers(env, path: Path, runner) -> int | None:
    """純函式：決定 xdist `-n auto` 的 worker 數。優先序（同 AutoClaude/tests/
    conftest.py 同名函式）：① `PYTEST_XDIST_AUTO_NUM_WORKERS` 為正整數 ⇒ 直接
    採用（尊重廣播／手動覆寫）；② `path` 不存在 ⇒ None（fail-open）；③ 呼叫
    `runner`（簽章比照 `subprocess.run`）取得 `cpu_budget.py --legs 1` 的
    stdout，為正整數才採用；④ 任何例外 ⇒ None（fail-open，本函式失敗不得弄垮
    整個 pytest session）。
    """
    override = _positive_int(env.get("PYTEST_XDIST_AUTO_NUM_WORKERS"))
    if override is not None:
        return override
    if not path.exists():
        return None
    try:
        result = runner(
            [sys.executable, str(path), "--legs", "1"],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        return _positive_int(result.stdout)
    except Exception:  # noqa: BLE001 — fail-open，見上方 ④
        return None


@pytest.hookimpl(optionalhook=True)  # 🔴 必須有：`-p no:xdist` 下 hookspec 不存在，
# 缺了會讓 pluggy 對未知 hookimpl 拋 PluginValidationError ⇒ INTERNALERROR。
def pytest_xdist_auto_num_workers(config):  # noqa: ARG001
    """xdist newhook（`firstresult=True`，僅 `-n auto` 時被呼叫）：回傳
    `cpu_budget.py` 算出的 worker 數；回傳 `None` 即交還 xdist 內建預設。
    """
    global _CPU_BUDGET_SOURCE_NOTE
    workers = _cpu_budget_workers(os.environ, _CPU_BUDGET_PATH, subprocess.run)
    if _positive_int(os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS")) is not None:
        source = "env"
    elif workers is not None:
        source = "cpu_budget"
    else:
        source = "xdist-default"
    shown = workers if workers is not None else "<xdist-default>"
    _CPU_BUDGET_SOURCE_NOTE = f"[cpu_budget] xdist workers={shown} source={source}"
    return workers


def pytest_sessionstart(session):
    """controller 端印一行 `[cpu_budget] xdist workers=<N> source=<...>`；只在
    controller 端（非 xdist worker）且 xdist 外掛確實已載入、且上面那支 hook
    確實被呼叫過（`-n auto`）時才印，避免對 `-p no:xdist` 或顯式 `-n <N>` 誤印。
    """
    config = session.config
    if hasattr(config, "workerinput"):
        return  # worker 端：這件事只在 controller 有意義
    if not config.pluginmanager.hasplugin("xdist"):
        return  # -p no:xdist：本 hook 不會被 xdist 呼叫，印了也是誤導
    if _CPU_BUDGET_SOURCE_NOTE is None:
        return  # 非 `-n auto`（例如顯式 `-n 3`）：xdist 未呼叫上面那支 hook
    terminalreporter = config.pluginmanager.getplugin("terminalreporter")
    if terminalreporter is not None:
        terminalreporter.write_line(_CPU_BUDGET_SOURCE_NOTE)


def _nodes_confirmed_line(n: int) -> str:
    """純函式：組出 xdist controller 端『node 數已確認』的一行輸出字串。"""
    return f"[cpu_budget] xdist nodes confirmed={n}"


# 🔴 `optionalhook=True` 理由同上方 `pytest_xdist_auto_num_workers`。
@pytest.hookimpl(optionalhook=True)
def pytest_xdist_setupnodes(config, specs):
    """controller 端印一行 `[cpu_budget] xdist nodes confirmed=<N>`（xdist 在建立
    任何 worker node 之前呼叫，天生只在 controller 端存在）。
    """
    terminalreporter = config.pluginmanager.getplugin("terminalreporter")
    if terminalreporter is not None:
        terminalreporter.write_line(_nodes_confirmed_line(len(specs)))
