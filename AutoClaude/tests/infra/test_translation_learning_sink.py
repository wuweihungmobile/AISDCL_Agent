"""W-60-2 FileTranslationLearningSink 單測（improving_60，R-60-7）。

Rule 9：測試編碼「為何」——提議須(1)跨 session 持久化（append round-trip）、
(2)讀回支援 dedup（at_id 可取集）、(3)fail-soft（畸形行/缺檔不 raise，諮詢不阻斷）、
(4)project 名路徑穿越消毒（安全）。
"""
from __future__ import annotations

from autoclaude.core.ports.translation_learning import TranslationProposal
from autoclaude.infra.adapters.translation_learning_sink import (
    FileTranslationLearningSink,
)


def _p(at_id: str) -> TranslationProposal:
    return TranslationProposal(
        at_id=at_id, failing_runs=2, total_runs=3, rationale=f"r-{at_id}",
    )


def test_record_then_list_roundtrip(tmp_path):
    sink = FileTranslationLearningSink(str(tmp_path))
    sink.record_proposal("proj", _p("AT-001"))
    sink.record_proposal("proj", _p("AT-002"))
    out = sink.list_proposals("proj")
    assert [x.at_id for x in out] == ["AT-001", "AT-002"]
    assert out[0].status == "proposed"
    assert out[0].failing_runs == 2


def test_list_missing_file_returns_empty(tmp_path):
    sink = FileTranslationLearningSink(str(tmp_path))
    assert sink.list_proposals("never") == ()


def test_list_dedup_set_usable(tmp_path):
    sink = FileTranslationLearningSink(str(tmp_path))
    sink.record_proposal("proj", _p("AT-001"))
    already = {x.at_id for x in sink.list_proposals("proj")}
    assert already == {"AT-001"}


def test_malformed_line_skipped_fail_soft(tmp_path):
    sink = FileTranslationLearningSink(str(tmp_path))
    sink.record_proposal("proj", _p("AT-001"))
    # 注入畸形行
    target = tmp_path / "PROPOSALS-proj.jsonl"
    with target.open("a", encoding="utf-8") as f:
        f.write("{not json\n")
        f.write("[]\n")  # 非 dict
        f.write('{"no_at_id": 1}\n')  # 缺 at_id
    out = sink.list_proposals("proj")
    assert [x.at_id for x in out] == ["AT-001"]  # 只保留合法行


def test_project_name_path_traversal_sanitized(tmp_path):
    """惡意 project 名（路徑穿越）→ 消毒後仍寫在 base_dir 內，不逃逸。"""
    sink = FileTranslationLearningSink(str(tmp_path))
    sink.record_proposal("../../etc/evil", _p("AT-001"))
    # 不應在 base_dir 外建立檔案；消毒後檔名落在 base_dir 內
    escaped = (tmp_path / ".." / ".." / "etc").resolve()
    assert not (escaped / "PROPOSALS-evil.jsonl").exists()
    files = list(tmp_path.glob("PROPOSALS-*.jsonl"))
    assert len(files) == 1  # 落在 base_dir 內


def test_sanitize_reserved_name_writes_safe_real_file(tmp_path):
    """R42 二審回歸（DEF-101-346 追記）：`_sanitize`（本模組私有函式）的
    `.lstrip("._")` 曾把 SSOT `_sanitize_log_filename` 為保留裝置名補上的逃逸
    前導底線一併剝除，導致淨化後裸露為保留名本身，防護沒生效。

    注意：本模組公開方法（`record_proposal`/`list_proposals`）一律先固定字面
    前綴 ``PROPOSALS-`` 再消毒，故 project 參數即使是 `"CON"`，組出的完整字串
    `"PROPOSALS-CON"` 也不等於保留名——無法透過公開方法端到端觸發本缺陷
    （結構性不可達）。因此本測試直接呼叫私有 `_sanitize` 函式，並把結果**實際
    寫入磁碟檔案**驗證真實落地檔名，而非僅比較字串。"""
    from autoclaude.infra.adapters.translation_learning_sink import _sanitize

    for reserved in ("CON", "con", "NUL", "PRN", "COM1", "LPT9"):
        safe_name = _sanitize(reserved)
        target = tmp_path / f"{safe_name}.jsonl"
        target.write_text("x", encoding="utf-8")
        assert target.is_file()
        assert target.stem.upper() != reserved.upper(), (
            f"保留裝置名 {reserved!r} 消毒後仍裸露：{target.name!r}"
        )
        assert target.stem.lstrip("_").upper() == reserved.upper()


def test_record_creates_dir(tmp_path):
    nested = tmp_path / "sub" / "dir"
    sink = FileTranslationLearningSink(str(nested))
    sink.record_proposal("proj", _p("AT-001"))
    assert (nested / "PROPOSALS-proj.jsonl").is_file()


# ── improving_61 W-61-3 / R-61-8：weak_runs additive 持久化 ──────────────────

def test_roundtrip_weak_runs(tmp_path):
    """weak_runs 寫出後讀回保真（第二信號強度跨 session 持久化）。"""
    sink = FileTranslationLearningSink(str(tmp_path))
    sink.record_proposal("proj", TranslationProposal(
        at_id="AT-009", failing_runs=0, total_runs=4, rationale="r", weak_runs=3,
    ))
    out = sink.list_proposals("proj")
    assert len(out) == 1
    assert out[0].weak_runs == 3
    assert out[0].failing_runs == 0


def test_legacy_proposal_missing_weak_runs_reads_zero(tmp_path):
    """improving_60 既有 proposals 紀錄無 weak_runs 欄 → 讀回 0（向後相容）。"""
    target = tmp_path / "PROPOSALS-proj.jsonl"
    target.write_text(
        '{"at_id":"AT-001","failing_runs":2,"total_runs":3,'
        '"rationale":"r","status":"proposed"}\n',
        encoding="utf-8",
    )
    out = FileTranslationLearningSink(str(tmp_path)).list_proposals("proj")
    assert len(out) == 1
    assert out[0].weak_runs == 0
