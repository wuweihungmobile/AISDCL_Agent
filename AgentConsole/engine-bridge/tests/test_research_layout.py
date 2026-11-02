"""研究工作區：路徑消毒、目錄佈局、原子寫檔、`issue_scope.json` 的確定性渲染
（TCS-ResearchToPRD-P0-20261102 AC-960-3：AT-960-3-2、AT-960-3-E-1；另對拍框架模板的
契約區塊）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.errors import ApiError
from app.research import export, layout

FRAMEWORK = Path(__file__).resolve().parent / "fixtures" / "research" / "framework"
REQUIREMENTS = FRAMEWORK / "docs_template" / "sdd" / "requirements"
SCOPE_TEMPLATE = REQUIREMENTS / "ISSUE-SCOPE-TEMPLATE.md"
MATRIX_TEMPLATE = REQUIREMENTS / "EVIDENCE-MATRIX-TEMPLATE.md"


def contract_block(text: str, name: str) -> object:
    """框架模板的契約區塊：註解行 `<!-- r2p:contract=<名稱> -->` 其下一行起的 json 圍欄
    （各名稱恰一次）。"""
    marker = f"<!-- r2p:contract={name} -->"
    assert text.count(marker) == 1, f"{marker} 必須恰出現一次"
    after = text.split(marker, 1)[1]
    match = re.match(r"\s*```json\n(.*?)\n```", after, flags=re.S)
    assert match, f"{name} 後面不是 json 圍欄"
    return json.loads(match.group(1))


def make_dir_link(link: Path, target: Path) -> None:
    """目錄符號連結；Windows 無權限時改用 junction（不需系統管理員）。兩者都失敗＝測試失敗。"""
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        if sys.platform != "win32":
            raise
    done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                          capture_output=True, text=True, check=False)
    assert done.returncode == 0, f"建不出符號連結也建不出 junction：{done.stderr or done.stdout}"


def tree(path: Path) -> list[str]:
    return sorted(str(p.relative_to(path)) for p in path.rglob("*")) if path.exists() else []


@pytest.fixture
def research_root(tmp_path: Path) -> Path:
    root = tmp_path / "my-project"
    root.mkdir()
    return root


# ── AT-960-3-2：路徑消毒 ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("slug", [
    "..", "a/../b", "A", "a b", "a\x00b", "a" * 31, "", "-a", ".hidden", "a_b", "中文",
])
def test_AT_960_3_2_a_bad_slug_is_a_422_sanitization_failure_and_adds_nothing(
        research_root: Path, slug: str) -> None:
    before = tree(research_root.parent)
    with pytest.raises(ApiError) as caught:
        layout.resolve_workspace(research_root, slug, [research_root])
    body = caught.value.body
    assert (caught.value.status_code, body["reason"]) == (422, "sanitization_failed"), \
        f"slug={slug!r}"
    assert caught.value.body["violations"], "帶逐項違規"
    assert tree(research_root.parent) == before, "磁碟零新增"


def test_AT_960_3_2_a_symlink_or_junction_that_escapes_the_root_is_refused(
        tmp_path: Path, research_root: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    make_dir_link(research_root / "evil", outside)
    before = tree(tmp_path)
    with pytest.raises(ApiError) as caught:
        layout.resolve_workspace(research_root, "evil", [research_root])
    assert (caught.value.status_code, caught.value.body["reason"]) == (422, "sanitization_failed")
    assert caught.value.body["violations"][0]["rule"] == "outside_allowed_roots"
    assert tree(tmp_path) == before and tree(outside) == [], "沒有任何東西被建到連結的另一端"


def test_AT_960_3_2_a_good_slug_resolves_under_the_allowed_root(research_root: Path) -> None:
    path = layout.resolve_workspace(research_root, "agent-memory-gc", [research_root])
    assert path == (research_root / "agent-memory-gc").resolve()
    assert os.path.normcase(str(path)).startswith(os.path.normcase(str(research_root.resolve())))
    assert not path.exists(), "只解析、不建立"
    thirty = "a" * 30
    assert layout.resolve_workspace(research_root, thirty, [research_root]).name == thirty


def test_a_root_outside_the_allowed_roots_is_refused_even_for_a_good_slug(
        tmp_path: Path, research_root: Path) -> None:
    other = tmp_path / "other-allowed"
    other.mkdir()
    with pytest.raises(ApiError) as caught:
        layout.resolve_workspace(research_root, "ok-slug", [other])
    assert caught.value.body["reason"] == "sanitization_failed"


# ── 目錄佈局與寫檔 ────────────────────────────────────────────────────────────────────────────
def test_the_workspace_has_the_four_directories_and_creation_is_idempotent(
        research_root: Path) -> None:
    ws = research_root / "demo"
    layout.ensure_dirs(ws)
    assert [p.name for p in sorted(ws.iterdir())] == list(layout.WORKSPACE_DIRS) == [
        "00_research", "01_specs", "02_governance", "03_execution"]
    marker = ws / "00_research" / "keep.txt"
    marker.write_text("x", encoding="utf-8")
    layout.ensure_dirs(ws)
    assert marker.read_text(encoding="utf-8") == "x", "再呼叫不動既有內容"
    assert layout.fsm_state_dir(ws) == ws / "build" / "reports" / "fsm"
    assert layout.FSM_DIR_REL == "build/reports/fsm"


def test_a_file_squatting_a_directory_name_fails_loud_with_an_oserror(research_root: Path) -> None:
    ws = research_root / "demo"
    ws.mkdir()
    (ws / "01_specs").write_text("占位", encoding="utf-8")
    with pytest.raises(OSError):
        layout.ensure_dirs(ws)


@pytest.mark.parametrize("rel", [
    "../escape.txt", "a/../../escape.txt", "/abs.txt", "C:/abs.txt", "", "  ", "x\x00y", "a/..",
])
def test_safe_join_refuses_paths_that_are_not_workspace_relative(
        research_root: Path, rel: str) -> None:
    with pytest.raises(ApiError) as caught:
        layout.safe_join(research_root, rel)
    assert caught.value.body["reason"] == "sanitization_failed"


def test_write_workspace_file_is_atomic_utf8_lf_and_reports_the_byte_digest(
        research_root: Path) -> None:
    text = "第一行\n第二行 \"引號\"\n"
    done = layout.write_workspace_file(research_root, "00_research/notes/a.md", text)
    target = research_root / "00_research" / "notes" / "a.md"
    assert target.read_bytes() == text.encode("utf-8") and b"\r" not in target.read_bytes()
    assert done == layout.WrittenFile("00_research/notes/a.md", layout.sha256_text(text),
                                      len(text.encode("utf-8")), True)
    assert layout.file_digest(research_root, "00_research/notes/a.md") == (done.sha256, done.bytes)
    assert layout.file_digest(research_root, "00_research/notes/none.md") is None
    assert not list(target.parent.glob("*.tmp")), "暫存檔已清掉"


def test_write_workspace_file_without_overwrite_leaves_bytes_and_mtime_untouched(
        research_root: Path) -> None:
    first = layout.write_workspace_file(research_root, "a.txt", "舊內容\n")
    target = research_root / "a.txt"
    os.utime(target, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))
    mtime = target.stat().st_mtime_ns
    again = layout.write_workspace_file(research_root, "a.txt", "新內容\n", overwrite=False)
    assert again.written is False and again.sha256 == first.sha256
    assert target.read_text(encoding="utf-8") == "舊內容\n" and target.stat().st_mtime_ns == mtime
    forced = layout.write_workspace_file(research_root, "a.txt", "新內容\n")
    assert forced.written is True and target.read_text(encoding="utf-8") == "新內容\n"


# ── scope 驗證（模板 §1.2 的逐條對映） ────────────────────────────────────────────────────────
def good_scope(**override: object) -> dict:
    scope: dict = {
        "layers": {"academic": True, "industry": False, "oss": True, "community": False},
        "tech_stack": "Python 3.11；FastAPI", "in_scope": ["可由 Python 呼叫的方案"],
        "out_of_scope": ["付費 SDK"], "recency_years": 2,
        "applicability_axes": ["技術可行", "授權相容"], "target_scope_hint": "AISDLC_MODULE"}
    scope.update(override)
    return scope


def test_a_complete_scope_normalises_to_itself_and_defaults_fill_the_optional_keys() -> None:
    scope, violations = export.normalize_scope(good_scope())
    assert violations == [] and scope == good_scope()
    minimal, violations = export.normalize_scope({
        "layers": {"academic": True, "industry": False, "oss": False, "community": False},
        "in_scope": ["x"]})
    assert violations == []
    assert minimal["tech_stack"] == "" and minimal["out_of_scope"] == []
    assert minimal["recency_years"] == 3 and minimal["target_scope_hint"] == "UNDECIDED"
    assert minimal["applicability_axes"] == list(export.AXIS_LABELS)


@pytest.mark.parametrize(("override", "field", "rule"), [
    ({"layers": {"academic": False, "industry": False, "oss": False, "community": False}},
     "scope.layers", "at_least_one"),
    ({"layers": {"academic": True}}, "scope.layers.industry", "invalid_type"),
    ({"layers": {"academic": 1, "industry": 0, "oss": 0, "community": 0}},
     "scope.layers.academic", "invalid_type"),
    ({"layers": None}, "scope.layers", "required"),
    ({"in_scope": []}, "scope.in_scope", "invalid_length"),
    ({"in_scope": ["a"] * 21}, "scope.in_scope", "invalid_length"),
    ({"in_scope": ["  "]}, "scope.in_scope[0]", "invalid_item"),
    ({"in_scope": ["x" * 201]}, "scope.in_scope[0]", "invalid_item"),
    ({"in_scope": "x"}, "scope.in_scope", "invalid_type"),
    ({"out_of_scope": [1]}, "scope.out_of_scope", "invalid_type"),
    ({"tech_stack": "x" * 201}, "scope.tech_stack", "invalid_value"),
    ({"tech_stack": 5}, "scope.tech_stack", "invalid_value"),
    ({"target_scope_hint": "SOMETHING"}, "scope.target_scope_hint", "invalid_value"),
    ({"recency_years": 4}, "scope.recency_years", "invalid_value"),
    ({"recency_years": True}, "scope.recency_years", "invalid_value"),
    ({"applicability_axes": []}, "scope.applicability_axes", "invalid_length"),
    ({"applicability_axes": ["自創軸"]}, "scope.applicability_axes", "unknown_axis"),
    ({"applicability_axes": ["技術可行", "技術可行"]}, "scope.applicability_axes", "duplicate"),
    ({"applicability_axes": list(export.AXIS_LABELS) + ["成本"]}, "scope.applicability_axes",
     "invalid_length"),
    ({"stray": 1}, "scope.stray", "unknown_key"),
])
def test_each_scope_rule_is_enforced_with_the_field_and_rule_named(
        override: dict, field: str, rule: str) -> None:
    _scope, violations = export.normalize_scope(good_scope(**override))
    assert {"field": field, "rule": rule} in [
        {"field": v["field"], "rule": v["rule"]} for v in violations], violations


def test_a_non_object_scope_is_refused_and_field_violations_cover_title_topic_depth() -> None:
    assert export.normalize_scope("nope")[1][0]["rule"] == "invalid_type"
    assert export.normalize_scope(None)[1][0]["rule"] == "invalid_type"
    assert export.field_violations(title="t", topic="x" * 500, depth_level="DEEP") == []
    bad = export.field_violations(title="", topic="x" * 501, depth_level="FAST")
    assert [v["field"] for v in bad] == ["title", "topic", "depth_level"]
    too_long = export.field_violations(title="x" * 201, topic="ok", depth_level="QUICK")
    assert [v["field"] for v in too_long] == ["title"]
    assert [v["field"] for v in export.field_violations(
        title="t", topic="a\x00b", depth_level="QUICK")] == ["topic"]


def test_the_axis_labels_equal_the_framework_axis_registry() -> None:
    registry = contract_block(MATRIX_TEMPLATE.read_text(encoding="utf-8"), "axis_registry")
    assert tuple(registry.values()) == export.AXIS_LABELS, \
        "Bridge 的軸標籤必須等於框架登錄表（順序亦同）"


# ── AT-960-3-E-1：issue_scope.json 渲染的確定性 ───────────────────────────────────────────────
def project_row(**override: object) -> dict:
    row: dict = {
        "research_id": "6f1d3c2e-8a4b-4c5d-9e7f-0a1b2c3d4e5f", "rp_no": "RP-0007",
        "slug": "pdf-export-engine", "scope_rev": 1, "title": "PDF 匯出渲染方案選型",
        "topic": "在不新增常駐服務下，替維護者回答「PDF 匯出」；以三軸皆有證據驗收",
        "scope": good_scope(), "depth_level": "STANDARD", "created_by": "alice",
        "created_at": datetime(2026, 11, 2, 10, 0, 0, 123456, tzinfo=timezone(timedelta(hours=8)))}
    row.update(override)
    return row


def test_AT_960_3_E_1_rendering_the_same_row_twice_gives_identical_bytes() -> None:
    row = project_row()
    first, second = export.render_issue_scope(row), export.render_issue_scope(dict(row))
    assert first == second and first.encode("utf-8") == second.encode("utf-8")
    assert first.endswith("\n") and "\r" not in first, "LF 行尾"
    assert not first.startswith("\ufeff"), "無 BOM"
    assert "PDF 匯出渲染方案選型" in first and "\\u" not in first, "ensure_ascii 為假"


def test_AT_960_3_E_1_snake_case_keys_schema_rev_and_a_timezone_offset() -> None:
    doc = json.loads(export.render_issue_scope(project_row()))
    assert doc["schema_rev"] == 1
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", key) for key in doc), list(doc)
    assert doc["created_at"] == "2026-11-02T02:00:00+00:00", "統一成 UTC、秒精度"
    assert datetime.fromisoformat(doc["created_at"]).utcoffset() is not None
    # created_at 以不同時區表示同一時刻，渲染的位元組相同（不受資料庫連線時區影響）
    utc_row = project_row(created_at=datetime(2026, 11, 2, 2, 0, 0, tzinfo=UTC))
    assert export.render_issue_scope(utc_row) == export.render_issue_scope(project_row())
    assert export.utc_iso("2026-11-02T10:00:00+08:00") == "2026-11-02T02:00:00+00:00"
    with pytest.raises(ValueError):
        export.utc_iso("2026-11-02T10:00:00")
    with pytest.raises(ValueError):
        export.utc_iso(datetime(2026, 11, 2, 10, 0, 0))


def test_AT_960_3_E_1_chinese_quotes_and_newlines_survive_a_json_round_trip() -> None:
    scope = good_scope(in_scope=["含「引號」與 \"雙引號\" 的項目", "第一行\n第二行"],
                       tech_stack="換行\n與\t定位點")
    row = project_row(scope=scope, topic="含\n換行與\"引號\"的命題", title="標題「A」")
    text = export.render_issue_scope(row)
    doc = json.loads(text)
    assert doc["scope"]["in_scope"] == scope["in_scope"] and doc["topic"] == row["topic"]
    assert doc["title"] == row["title"] and doc["scope"]["tech_stack"] == scope["tech_stack"]
    assert export.render_issue_scope(row) == text, "含中文、引號與換行的列同樣確定"


def test_the_rendered_file_has_exactly_the_framework_template_contract_shape() -> None:
    """對拍：以標記從框架模板抽出 `issue_scope` 契約區塊（不手抄），鍵集合與鍵序必須逐位相同。"""
    template = contract_block(SCOPE_TEMPLATE.read_text(encoding="utf-8"), "issue_scope")
    doc = json.loads(export.render_issue_scope(project_row()))
    assert list(doc) == list(template), "頂層鍵序與模板一致"
    assert list(doc["scope"]) == list(template["scope"])
    assert list(doc["layers"]) == list(template["layers"]) == list(export.LAYER_KEYS)
    assert doc["schema_rev"] == template["schema_rev"] == export.ISSUE_SCOPE_SCHEMA_REV
    assert doc["depth_level"] in export.DEPTH_LEVELS
    assert template["depth_level"] in export.DEPTH_LEVELS
    assert template["scope"]["target_scope_hint"] in export.TARGET_SCOPES
    assert template["recency_years"] in export.RECENCY_YEARS
    assert tuple(template["applicability_axes"]) == export.AXIS_LABELS


def test_the_state_projection_has_the_documented_keys_and_is_utc() -> None:
    projection = export.build_state_projection(
        research_id="rid", flow={"step": "studio", "phase": "REVIEWING", "status": "RUNNING"},
        fsm={"project": "research-x", "state": "SCG_VALIDATION", "updated_at": "t",
             "frozen_stages": []},
        runs=[{"stage": "REVIEW", "status": "RUNNING"}],
        projected_at=datetime(2026, 11, 2, 12, 0, tzinfo=timezone(timedelta(hours=8))))
    assert set(projection) == {"schema_rev", "research_id", "flow", "fsm", "runs", "projected_at"}
    assert set(projection["flow"]) == {"step", "phase", "status"}
    assert set(projection["fsm"]) == {"project", "state", "updated_at", "frozen_stages"}
    assert projection["projected_at"] == "2026-11-02T04:00:00+00:00"
    text = export.render_state_json(projection)
    assert json.loads(text) == projection and text.endswith("\n") and "\r" not in text
