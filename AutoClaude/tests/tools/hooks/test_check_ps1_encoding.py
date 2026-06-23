"""tools/hooks/check_ps1_encoding.py 單元測試。

策略：
  - 純函式 fix_ps1_encoding()：非 .ps1 no-op / ASCII no-op / 已 BOM no-op /
    非 ASCII 無 BOM → 補 BOM（含 PS5.1 真實 parse 行為的位元驗證）
  - CLI 黑盒：缺 payload fail-open / Write 含中文 .ps1 → 自動補 BOM
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "check_ps1_encoding.py"
UTF8_BOM = b"\xef\xbb\xbf"


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
    spec = importlib.util.spec_from_file_location("_hook_check_ps1_encoding", HOOK_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_non_ps1_is_noop(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "note.txt"
    original = "中文內容".encode("utf-8")
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 非 .ps1 不動


def test_ascii_ps1_is_noop(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "ascii.ps1"
    original = b"Write-Output 'hello'\n"
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 純 ASCII 免補 BOM


def test_existing_bom_is_noop(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "bom.ps1"
    original = UTF8_BOM + "Write-Output '中文'\n".encode("utf-8")
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 已有 BOM 不重複補


def test_non_ascii_without_bom_gets_bom(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "zh.ps1"
    body = "Write-Output '已啟用'\n".encode("utf-8")
    f.write_bytes(body)  # 模擬 Write 工具：UTF-8 無 BOM
    assert mod.fix_ps1_encoding(f) == 1
    fixed = f.read_bytes()
    assert fixed.startswith(UTF8_BOM)
    assert fixed == UTF8_BOM + body  # 僅前置 BOM，內容不變


def test_cli_no_payload_fail_open():
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0  # fail-open


def test_cli_autofixes_chinese_ps1(tmp_path: Path):
    f = tmp_path / "cli.ps1"
    body = "# 註解\nWrite-Output '完成'\n".encode("utf-8")
    f.write_bytes(body)
    result = _run({"tool_input": {"file_path": str(f)}})
    assert result.returncode == 0  # 永不阻斷
    assert f.read_bytes().startswith(UTF8_BOM)
    assert "AUTO-FIX" in result.stderr
