"""tools/hooks/check_sh_eol.py 單元測試。

對應 CLAUDE.md §Nightly / CI 取證紀律 #8（SD_09 W0 P0-AUDIT-31 修復項）。
策略：
  - CLI 黑盒測試：缺 payload / 非 .sh / .sh LF / .sh CRLF / 不存在檔
  - 直接呼叫 check_sh_eol() 測純函式行為
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "check_sh_eol.py"


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def _load_hook_module():
    spec = importlib.util.spec_from_file_location("_hook_check_sh_eol", HOOK_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_payload_fail_open():
    """無 payload → exit 0（fail-open，不阻斷無關工具）。"""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0


def test_non_sh_file_passes():
    """非 .sh / .bash → exit 0。"""
    result = _run({"tool_input": {"file_path": "autoclaude/main.py"}})
    assert result.returncode == 0


def test_real_repo_sh_files_are_lf():
    """真實 repo 內所有 .sh 應為 LF（紀律 #8 全域驗證）。"""
    sh_files = list(PROJECT_ROOT.glob("tools/**/*.sh"))
    assert sh_files, "預期 repo 含至少一個 .sh（如 tools/run_mutmut_in_docker.sh）"
    for sh in sh_files:
        rel = sh.relative_to(PROJECT_ROOT)
        result = _run({"tool_input": {"file_path": str(sh)}})
        assert result.returncode == 0, f"{rel} CRLF 違規：{result.stderr}"


def test_crlf_sh_blocks(tmp_path, monkeypatch):
    """偽造 CRLF 的 .sh → exit 2。"""
    mod = _load_hook_module()
    fake_sh = tmp_path / "bad.sh"
    fake_sh.write_bytes(b"#!/bin/bash\r\necho hello\r\n")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    rc = mod.check_sh_eol(Path("bad.sh"))
    assert rc == 2


def test_lf_sh_passes(tmp_path, monkeypatch):
    """純 LF 的 .sh → exit 0。"""
    mod = _load_hook_module()
    fake_sh = tmp_path / "good.sh"
    fake_sh.write_bytes(b"#!/bin/bash\necho hello\n")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    rc = mod.check_sh_eol(Path("good.sh"))
    assert rc == 0


def test_missing_sh_passes(tmp_path, monkeypatch):
    """檔案不存在 → exit 0（fail-open；可能是 Edit 後路徑變動）。"""
    mod = _load_hook_module()
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    rc = mod.check_sh_eol(Path("missing.sh"))
    assert rc == 0


def test_bash_extension_also_checked(tmp_path, monkeypatch):
    """.bash 副檔名也納入檢查（與 .gitattributes 對齊）。"""
    mod = _load_hook_module()
    fake = tmp_path / "lib.bash"
    fake.write_bytes(b"#!/bin/bash\r\nexport X=1\r\n")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path)
    rc = mod.check_sh_eol(Path("lib.bash"))
    assert rc == 2
