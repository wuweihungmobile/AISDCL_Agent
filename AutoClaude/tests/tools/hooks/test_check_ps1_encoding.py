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


# --- improving_52（C 軌）：SA FIND-1 fail-soft 型別守門 + UTF-8 合法性閘縱深 ---


def test_psm1_psd1_suffixes_get_bom(tmp_path: Path):
    """G1：PS_SUFFIXES 三後綴皆應觸發補 BOM（原僅測 .ps1）。"""
    mod = _load_hook_module()
    body = "Write-Output '已啟用'\n".encode("utf-8")
    for suffix in (".psm1", ".psd1"):
        f = tmp_path / f"mod{suffix}"
        f.write_bytes(body)
        assert mod.fix_ps1_encoding(f) == 1
        assert f.read_bytes() == UTF8_BOM + body


def test_utf16_le_bom_ps1_is_noop(tmp_path: Path):
    """SA FIND-2：UTF-16 LE（BOM FF FE）非合法 UTF-8 → no-op，不得前置 UTF-8 BOM 造成雙 BOM 損毀。"""
    mod = _load_hook_module()
    f = tmp_path / "utf16le.ps1"
    original = "Write-Output '中文'\n".encode("utf-16-le")
    original = b"\xff\xfe" + original  # 加 UTF-16 LE BOM
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 位元級不動，無 EF BB BF 前置


def test_big5_ps1_is_noop(tmp_path: Path):
    """SA FIND-3：既有 Big5/cp950 .ps1 非合法 UTF-8 → no-op，不得補 BOM 製造矛盾檔。"""
    mod = _load_hook_module()
    f = tmp_path / "big5.ps1"
    original = "Write-Output '中文'\n".encode("cp950")  # Big5，含 0x80+ 但非合法 UTF-8
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 不動


def test_cli_wrong_type_file_path_fail_soft():
    """SA FIND-1：file_path 為 list/int（非 str）→ 必須安全 exit 0，不得拋例外。"""
    for bad in ([1, 2], 12345):
        result = _run({"tool_input": {"file_path": bad}})
        assert result.returncode == 0, f"file_path={bad!r} 應 fail-soft，實得 rc={result.returncode}"


def test_cli_non_dict_tool_input_fail_soft():
    """SA FIND-1：tool_input 非 dict（list/str）或頂層非 dict → 安全 exit 0。"""
    for payload_json in ('{"tool_input": [1,2,3]}', '{"tool_input": "oops"}', "[1,2,3]", "42"):
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input=payload_json,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0, f"payload={payload_json} 應 fail-soft，實得 rc={result.returncode}"


def test_cli_empty_file_path_noop(tmp_path: Path):
    """G6：file_path 為空字串 → main 的 isinstance/falsy 守門 → 安全 exit 0。"""
    result = _run({"tool_input": {"file_path": ""}})
    assert result.returncode == 0


def test_cli_bad_json_fail_open():
    """G9：壞 JSON（非空、非合法）→ read_hook_payload 吞 JSONDecodeError → exit 0。"""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="{bad json",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0
