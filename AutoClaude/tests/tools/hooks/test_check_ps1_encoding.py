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
    original = "中文內容".encode()
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 非 .ps1 不動


def test_ascii_ps1_keeps_no_bom_but_gets_crlf(tmp_path: Path):
    """純 ASCII 仍不補 BOM（PS5.1 解 ASCII 無虞），但行尾照樣要收成 CRLF。"""
    mod = _load_hook_module()
    f = tmp_path / "ascii.ps1"
    f.write_bytes(b"Write-Output 'hello'\n")
    assert mod.fix_ps1_encoding(f) == 1
    assert f.read_bytes() == b"Write-Output 'hello'\r\n"  # 無 BOM、CRLF


def test_ascii_ps1_already_crlf_is_noop(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "ascii_crlf.ps1"
    original = b"Write-Output 'hello'\r\n"
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original


def test_existing_bom_is_noop(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "bom.ps1"
    original = UTF8_BOM + "Write-Output '中文'\r\n".encode()
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original  # 已有 BOM + CRLF 不重複動


def test_non_ascii_without_bom_gets_bom(tmp_path: Path):
    mod = _load_hook_module()
    f = tmp_path / "zh.ps1"
    body = "Write-Output '已啟用'\r\n".encode()
    f.write_bytes(body)  # 模擬 Write 工具：UTF-8 無 BOM（行尾已是 CRLF，隔離出 BOM 那一半）
    assert mod.fix_ps1_encoding(f) == 1
    fixed = f.read_bytes()
    assert fixed.startswith(UTF8_BOM)
    assert fixed == UTF8_BOM + body  # 僅前置 BOM，內容不變


# --- R79（D-ps1eol）：行尾正規化 —— 五道紅綠自證，缺一不可 -------------------


def test_lf_ps1_is_normalised_to_crlf(tmp_path: Path):
    """① 寫入者實際吐出的形態（LF）：修復後必須零孤立 LF。"""
    mod = _load_hook_module()
    f = tmp_path / "lf.ps1"
    f.write_bytes("# 中文註解\n$a = 1\nWrite-Output $a\n".encode())
    assert mod.fix_ps1_encoding(f) == 1
    data = f.read_bytes()
    assert data.startswith(UTF8_BOM)
    assert data.count(b"\r\n") == 3
    assert b"\n" not in data.replace(b"\r\n", b"")  # 零孤立 LF


def test_already_crlf_ps1_is_not_rewritten(tmp_path: Path):
    """② 冪等：已合規就不得重寫（否則每一次 Write 都多付一次磁碟寫入）。"""
    mod = _load_hook_module()
    f = tmp_path / "crlf.ps1"
    original = UTF8_BOM + "# 中文\r\n$a = 1\r\n".encode()
    f.write_bytes(original)
    before = f.stat().st_mtime_ns
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original
    assert f.stat().st_mtime_ns == before


def test_shell_scripts_are_out_of_scope(tmp_path: Path):
    """③ 射程不得擴大到 .sh —— 那邊的政策是**相反的**（LF），擴進去就是正面打架。"""
    mod = _load_hook_module()
    f = tmp_path / "x.sh"
    original = b"#!/usr/bin/env bash\necho hi\n"
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original


def test_mixed_eol_ps1_converges_to_crlf(tmp_path: Path):
    """④ 混合行尾（含單獨 CR）全部收斂成 CRLF。"""
    mod = _load_hook_module()
    f = tmp_path / "mixed.ps1"
    f.write_bytes(b"$a = 1\r\n$b = 2\n$c = 3\r$d = 4\r\n")
    assert mod.fix_ps1_encoding(f) == 1
    assert f.read_bytes() == b"$a = 1\r\n$b = 2\r\n$c = 3\r\n$d = 4\r\n"


def test_non_utf8_ps1_is_untouched_including_eol(tmp_path: Path):
    """⑤ 非合法 UTF-8 一律完全不動——UTF-16 的 `\\n` 是 `0A 00`，位元組層改行尾會毀檔。"""
    mod = _load_hook_module()
    f = tmp_path / "utf16.ps1"
    original = b"\xff\xfe" + "Write-Output '中文'\n".encode("utf-16-le")
    f.write_bytes(original)
    assert mod.fix_ps1_encoding(f) == 0
    assert f.read_bytes() == original


def test_lf_to_crlf_is_blob_neutral(tmp_path: Path):
    """⑥ 安全性硬證明：`.ps1` 在 .gitattributes 是 `text eol=crlf` ⇒ 這個自動修復
    結構上不可能改到入庫內容。沒有這一題，「auto-fix 而非 block」這個選擇就只是
    一句主張。"""
    mod = _load_hook_module()
    # 前提先自證：`.ps1` 真的掛著 `text eol=crlf`。少了這一句，這題在 attribute
    # 被人拿掉之後會變成「兩份都原樣存 ⇒ sha 不同 ⇒ 紅」還是「恆綠」都說不準。
    attr = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "check-attr", "text", "eol", "--", "tools/x.ps1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    assert attr.returncode == 0, attr.stderr
    assert "text: set" in attr.stdout and "eol: crlf" in attr.stdout, attr.stdout
    # 只讓**行尾**這一個變數動（兩份都帶 BOM），否則量到的是 BOM 造成的差異。
    src_lf = UTF8_BOM + "# 中文\n$a = 1\n".encode()
    fixed, actions = mod.normalize_ps_bytes(src_lf)
    assert actions == ["行尾正規化為 CRLF"], actions
    shas = []
    for name, data in (("lf", src_lf), ("crlf", fixed)):
        p = tmp_path / f"{name}.bin"
        p.write_bytes(data)
        r = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "hash-object", "--path", "tools/x.ps1", str(p)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        assert r.returncode == 0, r.stderr
        shas.append(r.stdout.strip())
    assert shas[0] == shas[1], f"LF 與 CRLF 兩份的 blob 不同（{shas}）⇒ 自動修復會改到入庫內容"


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
    body = "# 註解\nWrite-Output '完成'\n".encode()
    f.write_bytes(body)
    result = _run({"tool_input": {"file_path": str(f)}})
    assert result.returncode == 0  # 永不阻斷
    assert f.read_bytes().startswith(UTF8_BOM)
    assert "AUTO-FIX" in result.stderr


# --- improving_52（C 軌）：SA FIND-1 fail-soft 型別守門 + UTF-8 合法性閘縱深 ---


def test_psm1_psd1_suffixes_get_bom(tmp_path: Path):
    """G1：PS_SUFFIXES 三後綴皆應觸發補 BOM（原僅測 .ps1）。"""
    mod = _load_hook_module()
    body = "Write-Output '已啟用'\r\n".encode()
    for suffix in (".psm1", ".psd1"):
        f = tmp_path / f"mod{suffix}"
        f.write_bytes(body)
        assert mod.fix_ps1_encoding(f) == 1
        assert f.read_bytes() == UTF8_BOM + body


def test_utf16_le_bom_ps1_is_noop(tmp_path: Path):
    """SA FIND-2：UTF-16 LE（BOM FF FE）非合法 UTF-8 → no-op。

    不得前置 UTF-8 BOM，那會造成雙 BOM 損毀。
    """
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
        assert result.returncode == 0, (
            f"file_path={bad!r} 應 fail-soft，實得 rc={result.returncode}")


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
        assert result.returncode == 0, (
            f"payload={payload_json} 應 fail-soft，實得 rc={result.returncode}")


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
