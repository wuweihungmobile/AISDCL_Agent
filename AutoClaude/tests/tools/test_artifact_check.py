"""AutoSDD_improving_96 W-96-1 — artifact_check 單測（RTM-96-1）。

測 doc/spec 步 backend-robust 把關工具：存在+夠大→0、不存在→1、太小→1、邊界 size==min→0。
"""
from __future__ import annotations

from autoclaude.artifact_check import check_artifact, main


def test_existing_file_meeting_min_bytes_ok(tmp_path):
    """RTM-96-1：檔案存在且 size >= min → ok。"""
    f = tmp_path / "SPEC.md"
    f.write_text("x" * 300, encoding="utf-8")
    ok, msg = check_artifact(str(f), 200)
    assert ok is True
    assert "OK" in msg


def test_missing_file_fails(tmp_path):
    """RTM-96-1：檔案不存在 → fail。"""
    ok, msg = check_artifact(str(tmp_path / "nope.md"), 1)
    assert ok is False
    assert "不存在" in msg


def test_file_too_small_fails(tmp_path):
    """RTM-96-1：檔案存在但 size < min → fail（防空檔/stub 假過）。"""
    f = tmp_path / "SPEC.md"
    f.write_text("tiny", encoding="utf-8")  # 4 bytes
    ok, msg = check_artifact(str(f), 200)
    assert ok is False
    assert "太小" in msg


def test_size_equals_min_is_ok(tmp_path):
    """RTM-96-1：邊界 size == min → ok（>= 而非 >）。"""
    f = tmp_path / "x.txt"
    f.write_bytes(b"a" * 10)
    ok, _ = check_artifact(str(f), 10)
    assert ok is True


def test_directory_is_not_a_valid_artifact(tmp_path):
    """目錄非檔案 → fail（防把目錄當成功 artifact）。"""
    ok, msg = check_artifact(str(tmp_path), 1)
    assert ok is False
    assert "不是檔案" in msg


def test_main_exit_codes(tmp_path):
    """main CLI exit code：成功 0 / 失敗 1。"""
    f = tmp_path / "doc.md"
    f.write_text("hello world content", encoding="utf-8")
    assert main([str(f), "--min-bytes", "5"]) == 0
    assert main([str(tmp_path / "missing.md"), "--min-bytes", "5"]) == 1
