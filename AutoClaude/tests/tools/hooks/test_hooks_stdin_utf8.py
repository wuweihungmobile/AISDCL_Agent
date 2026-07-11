"""五支 hook 的 stdin UTF-8 解碼回歸鎖（跨平台四方複審 P1-2）。

為何重要：zh-TW Windows 的 pipe 預設 cp950，Claude Code 卻以 UTF-8 送 JSON payload。
修復前 read_hook_payload() 以裸 sys.stdin.read() 在 cp950 文字層解含中文的 UTF-8
bytes → UnicodeDecodeError → hook 崩潰、阻斷級守門靜默失效。修復後改讀
sys.stdin.buffer 以 UTF-8+replace 解碼，不受 pipe 文字層編碼影響。本測試以
PYTHONIOENCODING=cp950 模擬 zh-TW Windows pipe（任何平台皆可重現該缺陷）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = PROJECT_ROOT / "tools" / "hooks"

HOOK_SCRIPTS = [
    "enforce_docs_path.py",
    "loc_budget_check.py",
    "check_sh_eol.py",
    "check_ps1_encoding.py",
    "check_lang.py",
]


def _run_cp950(script: str, payload: dict) -> subprocess.CompletedProcess:
    """以 PYTHONIOENCODING=cp950 啟動 hook、stdin 餵 UTF-8 bytes（不走 text 層）。"""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUTF8"}
    env["PYTHONIOENCODING"] = "cp950"
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / script)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=30,
    )


@pytest.mark.parametrize("script", HOOK_SCRIPTS)
def test_utf8_payload_with_chinese_survives_cp950_pipe(script: str):
    """含繁中的 UTF-8 payload 在 cp950 pipe 下不得拋 UnicodeDecodeError（benign → rc 0）。"""
    payload = {
        "tool_input": {"file_path": "docs/05_development/中文檔名_測試.md"},
        "note": "繁體中文內容 🔴",
    }
    result = _run_cp950(script, payload)
    stderr = result.stderr.decode("utf-8", "replace")
    assert b"UnicodeDecodeError" not in result.stderr, stderr
    assert result.returncode == 0, f"rc={result.returncode} stderr={stderr}"


def test_enforce_docs_path_blocks_chinese_path_under_cp950():
    """cp950 pipe 下 payload 仍被完整解碼：非白名單繁中 .md 路徑必須照常 rc 2 阻斷。"""
    payload = {"tool_input": {"file_path": "隨意目錄/筆記.md"}}
    result = _run_cp950("enforce_docs_path.py", payload)
    stderr = result.stderr.decode("utf-8", "replace")
    assert result.returncode == 2, f"rc={result.returncode} stderr={stderr}"
    assert "隨意目錄/筆記.md" in stderr  # 解碼保真：原繁中路徑須原樣出現在阻斷訊息
