"""五支 fsm_runtime CLI 的 stdout/stderr UTF-8 reconfigure 釘選（DEF-101-154 回歸鎖）.

WHY：Windows 主控台預設 code page（cp950 等）下，CLI print 非 ASCII（中文訊息、
✅/❌ 符號）會 UnicodeEncodeError 崩潰或亂碼——DEF-101-154 為五支 CLI 的 main 入口
統一加上 `stream.reconfigure(encoding="utf-8", errors="replace")`。此釘選鎖住
「五支 CLI 原始碼各含 reconfigure( 呼叫」：reconfigure 只在 Windows 非 UTF-8 終端
的執行期才炸，POSIX CI 永遠測不到，未來重構（改寫 main、抽共用 helper）若把它
刪掉將零訊號回歸——故以原始碼釘選補上機械訊號。
"""
from __future__ import annotations

from pathlib import Path

import pytest

_FSM_DIR = Path(__file__).resolve().parents[1]
_CLI_MODULES = ["id_registry", "intent_decomposer", "media_size_check", "spec_debate", "tlc_runner"]


@pytest.mark.parametrize("module", _CLI_MODULES)
def test_cli_has_utf8_reconfigure(module: str) -> None:
    src = (_FSM_DIR / f"{module}.py").read_text(encoding="utf-8")
    assert "reconfigure(" in src, (
        f"{module}.py 遺失 stdout/stderr reconfigure( UTF-8 釘選——DEF-101-154 回歸"
        f"（Windows 非 UTF-8 主控台將 UnicodeEncodeError 崩潰或亂碼）"
    )
