# enforces (governance rules): R-9.4
"""`spec_digest.py`（ADR-XPLAT-016 §4.3）的純函式鎖：換行正規化摘要、路徑正規化、超限判斷。

WHY（Rule 9，測意圖不只測行為）：凍結「綁內容」的價值全靠兩件事——①摘要與 AutoClaude adapter
的 `SddSpec.digest` **逐位元相同**（否則編譯端永遠對不上，每次都假紅或假綠）；②路徑一律落在
root 之下、鍵與實際被讀的檔一一對應（否則「核准的版本」與「被凍結的版本」可以悄悄分叉）。
本檔因此：
  · 以 ADR 寫明的公式 `sha256(read_text(encoding="utf-8").encode("utf-8"))` 在測試內獨立重算，
    對 LF／CRLF／CR／BOM＋LF／BOM＋CRLF／混合換行逐檔對拍（AutoClaude 不得被 SDD import，
    ADR-XPLAT-010 §2.1，所以只能在這裡以公式對拍，真正的跨子專案對拍在 Bridge 測試）；
  · 同時斷言**原始 bytes** 的摘要在 CRLF／CR 兩種檔上**不等**——證明正規化真的有作用（若有人
    改回原始 bytes，這兩列會紅）；
  · 路徑案例涵蓋相對（POSIX 形）、Windows 反斜線形、根內絕對、根內含 `..`、根外絕對、`..` 跳出
    根、目錄、缺檔、跟隨連結指向根外（fail-closed）。
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import spec_digest as sd  # noqa: E402

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# (標籤, 原始 bytes)——五種換行／BOM 組合＋混合＋非 ASCII＋空檔
_VARIANTS = [
    ("LF", b"# TCS\nAT-001-1-1\n"),
    ("CRLF", b"# TCS\r\nAT-001-1-1\r\n"),
    ("CR", b"# TCS\rAT-001-1-1\r"),
    ("BOM+LF", b"\xef\xbb\xbf# TCS\nAT-001-1-1\n"),
    ("BOM+CRLF", b"\xef\xbb\xbf# TCS\r\nAT-001-1-1\r\n"),
    ("mixed", b"a\r\nb\rc\nd"),
    ("non-ascii CRLF", "需求\r\n驗收\r\n".encode("utf-8")),
    ("empty", b""),
]


def _adapter_digest(path: Path) -> str:
    """ADR §4.3 寫明的 adapter 公式（`read_text` 會做通用換行轉換、不剝 BOM）。"""
    return "sha256:" + hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


# ───────────────────────── 摘要：與 adapter 公式逐位元相同 ─────────────────────────
@pytest.mark.parametrize("label,raw", _VARIANTS, ids=[v[0] for v in _VARIANTS])
def test_digest_equals_adapter_formula(tmp_path: Path, label: str, raw: bytes) -> None:
    f = tmp_path / "TCS.md"
    f.write_bytes(raw)
    assert sd.digest_bytes(raw) == _adapter_digest(f), f"{label}：與 adapter 的 SddSpec.digest 不相等"
    assert _DIGEST_RE.match(sd.digest_bytes(raw)), "值格式必須是 sha256:<64 位小寫 hex>"


@pytest.mark.parametrize("label", ["CRLF", "CR", "BOM+CRLF"])
def test_raw_bytes_digest_would_differ_so_normalisation_matters(label: str) -> None:
    """反向對照：若有人改成原始 bytes 摘要，CRLF／CR 檔會與 adapter 對不上。"""
    raw = dict(_VARIANTS)[label]
    raw_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    assert sd.digest_bytes(raw) != raw_digest


def test_same_text_in_different_newline_styles_has_one_digest() -> None:
    lf, crlf, cr = b"a\nb\n", b"a\r\nb\r\n", b"a\rb\r"
    assert sd.digest_bytes(lf) == sd.digest_bytes(crlf) == sd.digest_bytes(cr)


def test_bom_is_not_stripped() -> None:
    """BOM 不剝：有／無 BOM 是兩份不同的內容（adapter 的 read_text(utf-8) 也不剝）。"""
    assert sd.digest_bytes(b"\xef\xbb\xbfx\n") != sd.digest_bytes(b"x\n")


def test_normalize_newlines_order_is_crlf_then_cr() -> None:
    assert sd.normalize_newlines(b"a\r\n\r\nb\r") == b"a\n\nb\n"  # 先 CRLF 再 CR；不會把 CRLF 變兩個換行


@pytest.mark.parametrize("raw", [b"\xff\xfe\x00", b"abc\x80def", "中文".encode("utf-16")])
def test_non_utf8_is_rejected_with_doc_not_utf8(raw: bytes) -> None:
    with pytest.raises(sd.SpecDocError) as err:
        sd.digest_bytes(raw, label="docs/x.md")
    assert err.value.code == "doc_not_utf8"
    assert "docs/x.md" in err.value.detail


# ───────────────────────────── 超限判斷 ─────────────────────────────
def test_size_limit_boundary_is_inclusive() -> None:
    assert sd.MAX_DOC_BYTES == 16 * 1024 * 1024
    assert not sd.is_too_large(sd.MAX_DOC_BYTES)
    assert sd.is_too_large(sd.MAX_DOC_BYTES + 1)


def test_digest_doc_rejects_oversize_but_accepts_exact_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sd, "MAX_DOC_BYTES", 10)
    (tmp_path / "exact.md").write_bytes(b"x" * 10)
    (tmp_path / "over.md").write_bytes(b"x" * 11)
    assert sd.digest_doc(tmp_path, "exact.md")[0] == "exact.md"
    with pytest.raises(sd.SpecDocError) as err:
        sd.digest_doc(tmp_path, "over.md")
    assert err.value.code == "doc_too_large"


# ───────────────────────────── 根推導 ─────────────────────────────
def test_derive_root_from_conventional_state_dir(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    state = root / "build" / "reports" / "fsm"
    assert sd.derive_root(state, Path("fallback")) == root


def test_derive_root_falls_back_for_custom_state_dir(tmp_path: Path) -> None:
    fb = tmp_path / "framework"
    assert sd.derive_root(tmp_path / "custom-state", fb) == fb
    assert sd.derive_root(tmp_path / "build" / "reports" / "other", fb) == fb


def test_derive_root_case_folding_follows_platform(tmp_path: Path) -> None:
    """Windows 的目錄名大小寫不敏感 ⇒ `Build/Reports/FSM` 也是慣例目錄；POSIX 是另一個目錄。"""
    fb = tmp_path / "framework"
    root = tmp_path / "proj"
    got = sd.derive_root(root / "Build" / "Reports" / "FSM", fb)
    assert got == (root if sys.platform == "win32" else fb)


# ───────────────────────────── 路徑正規化 ─────────────────────────────
@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "docs" / "03_testing").mkdir(parents=True)
    (root / "docs" / "03_testing" / "TCS-X.md").write_bytes(b"a\r\nb\r\n")
    (tmp_path / "elsewhere.md").write_text("outside", encoding="utf-8")
    return root


def test_relative_posix_path_is_normalised_to_a_posix_key(project: Path) -> None:
    full, key = sd.normalize_doc(project, "docs/03_testing/TCS-X.md")
    assert key == "docs/03_testing/TCS-X.md"
    assert full.is_file()


def test_backslash_relative_path_follows_platform_semantics(project: Path) -> None:
    """鐵律三自問：反斜線在另一個平台是什麼值？只有 Windows 的 `pathlib` 把它當分隔符。
    Windows ⇒ 與 POSIX 形得到同一個鍵；POSIX ⇒ 那是一個檔名字元，找不到檔＝doc_not_found
    （不 skip：兩個平台各有一個確定的答案，Bridge 一律傳 POSIX 形，ADR §4.3）。"""
    doc = "docs\\03_testing\\TCS-X.md"
    if sys.platform == "win32":
        assert sd.normalize_doc(project, doc)[1] == "docs/03_testing/TCS-X.md"
    else:
        with pytest.raises(sd.SpecDocError) as err:
            sd.normalize_doc(project, doc)
        assert err.value.code == "doc_not_found"


def test_absolute_path_inside_root_is_accepted(project: Path) -> None:
    assert sd.normalize_doc(project, str(project / "docs" / "03_testing" / "TCS-X.md"))[1] == (
        "docs/03_testing/TCS-X.md"
    )


def test_dotdot_that_stays_inside_root_is_accepted(project: Path) -> None:
    assert sd.normalize_doc(project, "docs/../docs/03_testing/TCS-X.md")[1] == "docs/03_testing/TCS-X.md"


def test_absolute_path_outside_root_is_rejected(project: Path) -> None:
    with pytest.raises(sd.SpecDocError) as err:
        sd.normalize_doc(project, str(project.parent / "elsewhere.md"))
    assert err.value.code == "doc_outside_root"


def test_dotdot_escape_is_rejected(project: Path) -> None:
    with pytest.raises(sd.SpecDocError) as err:
        sd.normalize_doc(project, "../elsewhere.md")
    assert err.value.code == "doc_outside_root"


def test_outside_check_precedes_existence_check(project: Path) -> None:
    """根外且不存在的路徑回 doc_outside_root，不洩漏「根外某處有沒有這個檔」。"""
    with pytest.raises(sd.SpecDocError) as err:
        sd.normalize_doc(project, "../no-such-file.md")
    assert err.value.code == "doc_outside_root"


@pytest.mark.parametrize("doc", ["docs", "docs/nope.md", "", "."])
def test_directory_or_missing_file_is_doc_not_found(project: Path, doc: str) -> None:
    with pytest.raises(sd.SpecDocError) as err:
        sd.normalize_doc(project, doc)
    assert err.value.code == "doc_not_found"


def _make_dir_link(link: Path, target: Path) -> None:
    """建一個指向 `target` 的目錄連結。POSIX＝symlink；Windows 預設無 symlink 權限
    （WinError 1314），改用 junction（`resolve()` 對兩者的跟隨行為相同，這是本測試要鎖的性質）。"""
    if sys.platform == "win32":
        import _winapi  # noqa: PLC0415 — 只在 Windows 分支才有的 CPython 內部模組

        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


def _remove_dir_link(link: Path) -> None:
    """只移除連結本身、不動 target。鐵律三自問「在另一個平台是什麼值」：Windows 的 junction 是
    目錄項、要 `os.rmdir`；POSIX 的 symlink 是檔案項、`os.rmdir` 會 `NotADirectoryError`
    （整合輪 115 雲端 aisdlc-sdd-ci／macos-compat-ci 實紅），要 `os.unlink`。"""
    if sys.platform == "win32":
        os.rmdir(link)
    else:
        os.unlink(link)


def test_link_pointing_outside_root_is_rejected(tmp_path: Path) -> None:
    """跟隨連結：根內的連結指向根外 ⇒ `resolve()` 後落在根外 ⇒ doc_outside_root（fail-closed）。"""
    root = tmp_path / "proj"
    (root / "docs").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("x", encoding="utf-8")
    link = root / "docs" / "link"
    _make_dir_link(link, outside)
    try:
        with pytest.raises(sd.SpecDocError) as err:
            sd.normalize_doc(root, "docs/link/secret.md")
        assert err.value.code == "doc_outside_root"
    finally:
        _remove_dir_link(link)


def test_link_pointing_inside_root_keys_by_the_real_file(tmp_path: Path) -> None:
    """鍵與實際被讀的檔一一對應：連結指向根內另一處時，鍵是**真檔**的相對路徑。"""
    root = tmp_path / "proj"
    (root / "real").mkdir(parents=True)
    (root / "real" / "TCS.md").write_text("x", encoding="utf-8")
    (root / "docs").mkdir()
    link = root / "docs" / "alias"
    _make_dir_link(link, root / "real")
    try:
        assert sd.normalize_doc(root, "docs/alias/TCS.md")[1] == "real/TCS.md"
    finally:
        _remove_dir_link(link)


# ───────────────────────────── digest_doc／digest_docs ─────────────────────────────
def test_digest_doc_matches_adapter_formula_on_disk(project: Path) -> None:
    key, digest = sd.digest_doc(project, "docs/03_testing/TCS-X.md")
    assert key == "docs/03_testing/TCS-X.md"
    assert digest == _adapter_digest(project / "docs" / "03_testing" / "TCS-X.md")


def test_crlf_file_and_same_content_lf_file_have_the_same_digest(project: Path) -> None:
    (project / "docs" / "03_testing" / "TCS-LF.md").write_bytes(b"a\nb\n")  # TCS-X.md 是同內容的 CRLF 版
    assert sd.digest_doc(project, "docs/03_testing/TCS-X.md")[1] == sd.digest_doc(
        project, "docs/03_testing/TCS-LF.md"
    )[1]


def test_digest_docs_returns_a_single_key_set_in_first_seen_order(project: Path) -> None:
    (project / "docs" / "a.md").write_text("A", encoding="utf-8")
    (project / "docs" / "b.md").write_text("B", encoding="utf-8")
    keys, digests = sd.digest_docs(
        project, ["docs/b.md", "docs/a.md", str(project / "docs" / "b.md"), "docs/../docs/a.md"]
    )
    assert keys == ["docs/b.md", "docs/a.md"], "同一檔經不同寫法重複給時只留一筆、保首見順序"
    assert set(digests) == set(keys), "spec_docs 與摘要鍵必須是同一組字串"


def test_digest_docs_fails_on_the_first_bad_doc(project: Path) -> None:
    with pytest.raises(sd.SpecDocError) as err:
        sd.digest_docs(project, ["docs/03_testing/TCS-X.md", "docs/missing.md"])
    assert err.value.code == "doc_not_found"
