"""規格摘要演算法鏡像（F-6 的單元面）：換行正規化的文字雜湊，與 adapter 的 `SddSpec.digest` 同
值。"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app import spec_digest as sd

_BODY = "# 規格\n\n| AC | AT |\n|---|---|\n| AC-001-1 | AT-001-1-1 |\n"
_VARIANTS = {
    "lf": _BODY.encode("utf-8"),
    "crlf": _BODY.replace("\n", "\r\n").encode("utf-8"),
    "cr": _BODY.replace("\n", "\r").encode("utf-8"),
    "bom_lf": b"\xef\xbb\xbf" + _BODY.encode("utf-8"),
    "bom_crlf": b"\xef\xbb\xbf" + _BODY.replace("\n", "\r\n").encode("utf-8"),
}


def _adapter_style_digest(path: Path) -> str:
    """adapter 的算法（`sdd_to_playbook_adapter.py:137`）：文字模式讀檔再編碼。"""
    return "sha256:" + hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


@pytest.mark.parametrize("variant", sorted(_VARIANTS))
def test_the_digest_equals_the_adapter_digest_for_every_newline_and_bom_variant(
        variant: str, tmp_path: Path) -> None:
    path = tmp_path / "spec.md"
    path.write_bytes(_VARIANTS[variant])
    assert sd.file_digest(path) == _adapter_style_digest(path)


def test_lf_crlf_and_cr_files_with_the_same_text_share_one_digest(tmp_path: Path) -> None:
    digests = {}
    for variant in ("lf", "crlf", "cr"):
        path = tmp_path / f"{variant}.md"
        path.write_bytes(_VARIANTS[variant])
        digests[variant] = sd.file_digest(path)
    assert len(set(digests.values())) == 1, "換行不同不得造成假紅"
    raw = {v: "sha256:" + hashlib.sha256(_VARIANTS[v]).hexdigest() for v in ("lf", "crlf", "cr")}
    assert len(set(raw.values())) == 3, \
        "對照組：原始 bytes 的雜湊三個都不同（所以不能用原始 bytes）"


def test_a_bom_is_not_stripped_so_it_changes_the_digest(tmp_path: Path) -> None:
    plain, bom = tmp_path / "p.md", tmp_path / "b.md"
    plain.write_bytes(_VARIANTS["lf"])
    bom.write_bytes(_VARIANTS["bom_lf"])
    assert sd.file_digest(plain) != sd.file_digest(bom)


def test_digest_format_is_sha256_colon_64_lowercase_hex() -> None:
    value = sd.text_digest("x")
    assert value.startswith("sha256:") and len(value) == len("sha256:") + 64
    assert value == value.lower()


def test_non_utf8_oversize_and_missing_files_are_distinct_failures(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "bin.md"
    binary.write_bytes(b"\xff\xfe\x00abc\x80")
    with pytest.raises(sd.DocNotUtf8Error):
        sd.file_digest(binary)
    big = tmp_path / "big.md"
    big.write_text("x" * 64, encoding="utf-8")
    monkeypatch.setattr(sd, "MAX_DOC_BYTES", 32)
    with pytest.raises(sd.DocTooLargeError):
        sd.file_digest(big)
    with pytest.raises(OSError):
        sd.file_digest(tmp_path / "missing.md")
    with pytest.raises(OSError):
        # 目錄：Windows 是 PermissionError、POSIX 是 IsADirectoryError
        sd.file_digest(tmp_path)
