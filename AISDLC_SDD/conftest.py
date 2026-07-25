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
import sys

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


def pytest_terminal_summary(terminalreporter, exitstatus, config):  # noqa: ARG001
    """在一般 ``skipped=N`` 摘要之外，另印出「僅原生 Windows 上才具驗證價值」的
    skip 清單（對等 AutoClaude/tests/conftest.py::pytest_terminal_summary）。刻意
    不用 emoji——`terminalreporter` 底層 TerminalWriter 在非 UTF-8 終端下無防護，
    印 emoji 會 UnicodeEncodeError 崩潰（見 DEF-101-069），純 ASCII 分隔線換取同等
    醒目效果更安全。
    """
    tagged_ids = windows_native_skips(terminalreporter)
    if not tagged_ids:
        return
    terminalreporter.write_sep("=", "WINDOWS-NATIVE-ONLY SKIPS (未在原生 Windows 環境驗證)")
    terminalreporter.write_line(
        f"{len(tagged_ids)} 個 Windows 專屬測試本次「未在原生 Windows 環境驗證」"
        f"（非一般 skip，見 DEF-101-363/368）："
    )
    for node_id in tagged_ids:
        terminalreporter.write_line(f"  - {node_id}")
