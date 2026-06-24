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


def test_record_creates_dir(tmp_path):
    nested = tmp_path / "sub" / "dir"
    sink = FileTranslationLearningSink(str(nested))
    sink.record_proposal("proj", _p("AT-001"))
    assert (nested / "PROPOSALS-proj.jsonl").is_file()
