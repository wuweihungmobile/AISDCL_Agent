"""確定性閘門（`app/research/gates/**`；TCS-ResearchToPRD-P0 AC-960-9／11／12）。

純函式單元測試：證據驗證（模板 16 條）、矩陣渲染與資料列對拍、PRD 草擬預檢 P0-1～P0-9、
加權與判定（整數 W100）。基準是夾具 `scripts/content/` 的黃金證據與 PRD：先釘「黃金件全過」，
再對每條規則做**單一突變**，要求恰該規則被點名——只改一處、點名那一條，才證明規則真的在判。
"""
from __future__ import annotations

import ast
import copy
import json
import re
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.research import export
from app.research.db import ResearchDbError
from app.research.gate_cli import run as run_gate_cli
from app.research.gates import aggregate, prd_schema
from app.research.gates.evidence import (
    CELL_MAX_CHARS,
    MIN_EVIDENCE_ROWS,
    EvidenceContext,
    compute_unanchored,
    dedupe_rows,
    is_license_pending,
    license_pending_numbers,
    normalize_locator,
    number_tokens,
    strength,
    validate_evidence_items,
)
from app.research.gates.ingest import plan_ingest
from app.research.gates.review_card import validate_review_dimension
from app.research.gates.schemas import (
    DIMENSION_FLOOR,
    DIMENSIONS,
    REVIEW_THRESHOLD,
    SCG_RETRY_LIMIT,
    W100_WEIGHTS,
)
from tests import test_research_db as db_tests
from tests import test_research_orchestrator as orch_tests

rdb = db_tests.rdb                      # 夾具（重新匯出）：拋棄式資料庫
tree, rig = orch_tests.tree, orch_tests.rig                 # 夾具（重新匯出）：FSM 樹與活 Bridge
CONTENT =Path(__file__).resolve().parent / "fixtures" / "research" / "scripts" / "content"
GOLDEN: dict[str, Any] = json.loads((CONTENT / "evidence_items.json").read_text(encoding="utf-8"))
PRD_V1 = (CONTENT / "PRD_v1.md").read_text(encoding="utf-8")
ROWS = {f"E-00{i}": {"f7": "V2", "strength": "MEDIUM", "unanchored": False} for i in range(1, 5)}
HEX64 = "a" * 64


def evidence(edit: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    doc = copy.deepcopy(GOLDEN)
    if edit is not None:
        edit(doc)
    return doc


def hit_rules(doc: Any, ctx: EvidenceContext | None = None) -> set[str]:
    return {v.rule for v in validate_evidence_items(doc, ctx)}


# ══ AT-960-9-1：evidence_items.json 依模板 16 條驗證規則嚴格驗證 ═════════════════════════════════
def test_AT_960_9_1_the_golden_evidence_file_passes_every_rule() -> None:
    assert validate_evidence_items(GOLDEN) == []
    ctx = EvidenceContext(issue_scope={"scope_rev": 1, "applicability_axes": []},
                          issue_scope_sha256=GOLDEN["issue_scope_sha256"])
    assert [v.rule for v in validate_evidence_items(GOLDEN, ctx) if v.rule == "R16"] == []


def _set(path: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def edit(doc: dict[str, Any]) -> None:
        node: Any = doc
        keys = re.findall(r"[^.\[\]]+", path)
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value

    return edit


def _add_orphan(doc: dict[str, Any]) -> None:
    doc["sources"].append({**doc["sources"][1], "source_no": "S-007", "title": "孤兒來源"})
    doc["honest_bounds"]["summary_only"].append("S-007")
    doc["honest_bounds"]["not_read_fully"].append("S-007")


def _drop_counter(doc: dict[str, Any]) -> None:
    del doc["counter_evidence"][0]


def _not_found_without_bound(doc: dict[str, Any]) -> None:
    doc["honest_bounds"]["not_found"] = []


def _dup_number(doc: dict[str, Any]) -> None:
    doc["items"][1]["evidence_no"] = "E-001"


def _extra_unanchored(doc: dict[str, Any]) -> None:
    doc["items"][0]["unanchored"] = True


def _drop_axis(doc: dict[str, Any]) -> None:
    del doc["items"][0]["f5"]["cost"]


def _drop_summary(doc: dict[str, Any]) -> None:
    doc["honest_bounds"]["summary_only"].remove("S-006")


MUTATIONS: dict[str, tuple[str, Callable[[dict[str, Any]], None]]] = {
    "schema_rev": ("R1", _set("schema_rev", 2)),
    "researcher_wrote_unanchored": ("R1", _extra_unanchored),
    "duplicate_evidence_no": ("R2", _dup_number),
    "http_url": ("R3", _set("sources[0].url", "http://example.org/papers/example-001")),
    "bad_commit": ("R3", _set("sources[1].git_commit", "xyz")),
    "url_not_in_any_search": ("R4", _set("sources[2].url", "https://example.org/blog/unseen")),
    "item_cites_a_t3_clue": ("R5", _set("items[0].source_no", "S-004")),
    "t3_without_clue_flag": ("R5", _set("sources[3].clue_only", False)),
    "v3_without_fetch_refs": ("R6", _set("sources[0].verification", "V3")),
    "unknown_source": ("R7", _set("items[0].source_no", "S-099")),
    "f7_above_the_source": ("R7", _set("items[3].f7", "V3")),
    "empty_claim": ("R8", _set("items[0].claim", "")),
    "unregistered_risk_tag": ("R8", _set("items[0].f4", ["UNANCHORED"])),
    "missing_applicability_axis": ("R8", _drop_axis),
    "repo_without_license": ("R8", _set("sources[1].license_spdx", None)),
    "pipe_in_a_cell": ("R9", _set("items[0].claim", "甲|乙")),
    "newline_in_a_cell": ("R9", _set("items[0].f1", "第一行\n第二行")),
    "cell_over_600_chars": ("R9", _set("items[0].f6", "長" * 601)),
    "item_without_counter": ("R11", _drop_counter),
    "not_found_missing_from_bounds": ("R11", _not_found_without_bound),
    "strength_differs_from_the_function": ("R12", _set("items[0].strength", "STRONG")),
    "orphan_source": ("R13", _add_orphan),
    "bounds_miss_a_source": ("R14", _drop_summary),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_AT_960_9_1_each_single_mutation_names_its_rule(name: str) -> None:
    rule, edit = MUTATIONS[name]
    found = hit_rules(evidence(edit))
    assert GOLDEN != evidence(edit) and rule in found, (name, found)


def test_AT_960_9_1_the_cell_limit_is_inclusive_a_600_character_cell_passes_and_601_is_named_r9(
) -> None:
    """儲存格上限 600 是「含」邊界：恰 600 字元合格、601 字元才點名 R9（突變 `>`→`>=` 會讓
    前者誤判）。"""
    assert CELL_MAX_CHARS == 600, "TCS §5.1 值域常數"
    exact = evidence(_set("items[0].f6", "長" * CELL_MAX_CHARS))
    assert validate_evidence_items(exact) == [], "恰 600 字元：整份檔案仍然合格"
    over = evidence(_set("items[0].f6", "長" * (CELL_MAX_CHARS + 1)))
    assert "R9" in hit_rules(over) and hit_rules(over) == {"R9"}
    # 其他文字欄位（不只 f6）同一條界線：search_log 的 query 與 sources 的 title 各驗一次
    assert validate_evidence_items(evidence(_set("sources[0].title", "題" * CELL_MAX_CHARS))) == []
    assert "R9" in hit_rules(evidence(_set("sources[0].title", "題" * (CELL_MAX_CHARS + 1))))


def test_AT_960_9_1_context_rules_r15_and_r16() -> None:
    doc = evidence()
    assert "R16" in hit_rules(doc, EvidenceContext(issue_scope_sha256=HEX64))
    assert "R16" not in hit_rules(doc, EvidenceContext(
        issue_scope_sha256=HEX64, accept_template_sentinel=True))
    assert "R16" in hit_rules(doc, EvidenceContext(issue_scope={"scope_rev": 2}))
    doc["sources"][0]["fetch_refs"] = ["F-0001"]
    assert "R16" in hit_rules(doc, EvidenceContext(fetch_index={}))
    good = {"F-0001": {"observed_by": "BRIDGE", "outcome": "OK"}}
    assert "R16" not in hit_rules(doc, EvidenceContext(fetch_index=good))
    bad = {"F-0001": {"observed_by": "AGENT_DECLARED", "outcome": "OK"}}
    assert "R16" in hit_rules(doc, EvidenceContext(fetch_index=bad))


def test_AT_960_9_1_a_structurally_broken_file_reports_only_structure() -> None:
    assert hit_rules(["not", "an", "object"]) == {"R1"}
    assert hit_rules({**GOLDEN, "items": "x"}) == {"R1"}
    assert hit_rules({k: v for k, v in GOLDEN.items() if k != "honest_bounds"}) == {"R1"}


def test_AT_960_9_1_the_gate_cli_exits_non_zero_and_prints_each_violation(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    (ws / "00_research").mkdir(parents=True)
    bad = evidence(_set("items[0].claim", ""))
    (ws / "00_research" / "evidence_items.json").write_text(json.dumps(bad), encoding="utf-8")
    sha = "0" * 63 + "1"
    rc, lines = run_gate_cli(["evidence", "--workspace", str(ws), "--issue-scope-sha256", sha,
                              "--accept-template-sentinel"])
    assert rc != 0 and any("R8" in line for line in lines)
    (ws / "00_research" / "evidence_items.json").write_text(json.dumps(GOLDEN), encoding="utf-8")
    rc_ok, lines_ok = run_gate_cli(["evidence", "--workspace", str(ws), "--issue-scope-sha256",
                                    sha, "--accept-template-sentinel"])
    assert rc_ok == 0, lines_ok


# ══ AT-960-9-8：strength 函式表驅動（模板 §3.3）════════════════════════════════════════════════
STRENGTH_TABLE = [
    # tier, f7, f4, conclusion → expected
    ("T1", "V3", [], "LIMIT", "STRONG"), ("T1", "V3", [], "IRRELEVANT", "STRONG"),
    ("T1", "V3", [], "WEAKEN", "MEDIUM"), ("T1", "V3", [], "NOT_FOUND", "MEDIUM"),
    ("T1", "V3", [], "NOT_SEARCHED", "MEDIUM"), ("T1", "V3", ["IMM"], "LIMIT", "MEDIUM"),
    ("T1", "V3", ["SELF"], "LIMIT", "MEDIUM"), ("T1", "V3", ["SCOPE"], "LIMIT", "MEDIUM"),
    ("T1", "V3", ["LOCK", "DEP", "LIC", "SEC", "COMP"], "LIMIT", "STRONG"),
    ("T1", "V2", [], "LIMIT", "MEDIUM"), ("T1", "V2", [], "WEAKEN", "WEAK"),
    ("T2", "V3", [], "LIMIT", "MEDIUM"), ("T2", "V3", [], "WEAKEN", "WEAK"),
    ("T2", "V2", [], "LIMIT", "WEAK"), ("T2", "V2", [], "WEAKEN", "CANDIDATE"),
    ("T1", "V1", [], "LIMIT", "CANDIDATE"), ("T2", "V1", [], "LIMIT", "CANDIDATE"),
    ("T3", "V2", [], "LIMIT", "CANDIDATE"), ("T3", "V3", [], "LIMIT", "CANDIDATE"),
    ("T1", "V1", [], "WEAKEN", "CANDIDATE"),
]


@pytest.mark.parametrize("tier, f7, f4, conclusion, expected", STRENGTH_TABLE)
def test_AT_960_9_8_strength_follows_the_template_table(
        tier: str, f7: str, f4: list[str], conclusion: str, expected: str) -> None:
    assert strength(tier, f7, f4, conclusion) == expected


# ══ AT-960-9-4：F2 數字錨定（執行層計算）══════════════════════════════════════════════════════
def test_AT_960_9_4_numbers_are_anchored_literally_or_after_normalisation() -> None:
    assert number_tokens("吞吐 1,200 頁每分鐘，對照 450 頁") == ["1200", "450"]
    assert compute_unanchored("1200 頁每分鐘", "V2", ["實測 1,200 頁每分鐘"]) is False
    assert compute_unanchored("1200 頁每分鐘", "V2", ["實測 1200 pages"]) is False
    assert compute_unanchored("延遲 0.50 ms", "V2", ["latency 0.5 ms"]) is False
    assert compute_unanchored("1200 頁每分鐘", "V2", ["全文只有 450 頁"]) is True
    assert compute_unanchored("1200 頁", "V2", ["共 12001 頁"]) is True, "不得以子字串蒙混"
    assert compute_unanchored("1200 頁", "V1", ["與數字無關的原文"]) is False, "V1 列不比對"
    assert compute_unanchored("1200 頁", "V2", []) is False, "宣告型列（無抓取原文）不比對"


def test_AT_960_9_4_the_ingest_plan_flags_unanchored_rows_and_counts_qualifying_ones() -> None:
    doc = evidence()
    doc["sources"][0]["fetch_refs"] = ["F-0001"]
    raw = {"F-0001": "基準 X 單機 8 核、1000 頁文件：1200 頁每分鐘，對照組 450 頁每分鐘"}
    plan = plan_ingest(doc, matrix_version=1, raw_text_of=raw.get)
    assert plan.unanchored == [] and plan.qualifying == 4 and plan.enough
    doc["items"][0]["f2"] = "吞吐 9999 頁每分鐘"
    flagged = plan_ingest(doc, matrix_version=1, raw_text_of=raw.get)
    assert flagged.unanchored == ["E-001"] and flagged.enough
    row = next(r for r in flagged.items if r["evidence_no"] == "E-001")
    assert row["unanchored"] is True
    assert flagged.index["rows"]["E-001"]["unanchored"] is True
    assert flagged.qualifying == plan.qualifying - 1
    declared = [s for s in flagged.searches if s["observed_by"] == "AGENT_DECLARED"]
    assert len(declared) == len(doc["search_log"])
    later = plan_ingest(doc, matrix_version=2, raw_text_of=raw.get, known_search_nos=[1, 2, 3])
    assert [s["search_no"] for s in later.searches] == [4, 5, 6, 7, 8], "增補只入庫新增的搜尋"


def test_AT_960_9_4_the_evidence_gate_is_open_at_exactly_three_qualifying_rows_and_shut_at_two(
) -> None:
    """證據閘（PRD §5.1.1）：層級 ≥ V2、非 UNANCHORED、非 clue_only 的列至少
    `MIN_EVIDENCE_ROWS`＝3。邊界兩側各釘一次：恰 3 列放行、2 列不放行（突變 3→2 會讓後者
    誤放行）。"""
    assert MIN_EVIDENCE_ROWS == 3, "初值、未校準：常數登記並以測試釘住"

    def plan_of(edit: Callable[[dict[str, Any]], None] | None = None) -> Any:
        return plan_ingest(evidence(edit), matrix_version=1, raw_text_of=lambda _ref: None)

    def v1(*indexes: int) -> Callable[[dict[str, Any]], None]:
        def edit(doc: dict[str, Any]) -> None:
            for index in indexes:
                doc["items"][index]["f7"] = "V1"
        return edit

    assert (plan_of().qualifying, plan_of().enough) == (4, True)
    three = plan_of(v1(3))
    assert (three.qualifying, three.enough) == (3, True), "恰 3 列合格：證據閘開"
    two = plan_of(v1(2, 3))
    assert (two.qualifying, two.enough) == (2, False), "2 列合格：證據閘不開"
    # 其餘三種「不合格」的形態各自讓合格列少一列：clue_only 來源、UNANCHORED 列
    clue = plan_of(lambda doc: doc["items"][3].update(source_no="S-004"))
    assert (clue.qualifying, clue.enough) == (3, True), "引用 T3 線索來源的列不算合格"
    doc = evidence()
    doc["sources"][0]["fetch_refs"] = ["F-0001"]
    unanchored = plan_ingest(doc, matrix_version=1, raw_text_of={"F-0001": "與數字無關"}.get)
    assert unanchored.unanchored == ["E-001"] and unanchored.qualifying == 3 and unanchored.enough


# ══ AT-960-9-5：再次研究產生新矩陣版本，舊版保留，檔案雜湊等於最新版 ═════════════════════════════
def test_AT_960_9_5_a_second_research_run_adds_a_matrix_version_and_keeps_the_old_rows(
        rig: Any) -> None:
    import hashlib

    rid = orch_tests.create(rig)
    orch_tests.run_stage(rig, rid, "research")
    orch_tests.run_stage(rig, rid, "research")                 # 增補：原樣保留前一版，編號延續
    ws = Path(orch_tests.project(rig, rid)["workspace_path"])
    artifacts = {kind: rig.db.query(
        "SELECT version, sha256, content FROM {s}.research_artifacts WHERE research_id = %s "
        "AND kind = %s ORDER BY version", (rid, kind)) for kind in ("EVIDENCE_MATRIX",
                                                                    "EVIDENCE_ITEMS")}
    assert [a["version"] for a in artifacts["EVIDENCE_MATRIX"]] == [1, 2]
    assert [a["version"] for a in artifacts["EVIDENCE_ITEMS"]] == [1, 2]
    latest = hashlib.sha256((ws / "00_research" / "evidence_matrix.md").read_bytes()).hexdigest()
    assert artifacts["EVIDENCE_MATRIX"][-1]["sha256"] == latest, "檔案 sha256 等於最新版"
    items = rig.db.query("SELECT matrix_version, evidence_no FROM {s}.research_evidence_items "
                         "WHERE research_id = %s ORDER BY matrix_version, evidence_no", (rid,))
    by_version: dict[int, list[str]] = {}
    for row in items:
        by_version.setdefault(int(row["matrix_version"]), []).append(row["evidence_no"])
    assert set(by_version) == {1, 2} and by_version[1] == by_version[2], "舊版證據列保留"
    assert artifacts["EVIDENCE_ITEMS"][0]["content"] == artifacts["EVIDENCE_ITEMS"][1]["content"]
    assert [r["status"] for r in orch_tests.runs_of(rig, rid, "RESEARCH")] == [
        "SUCCEEDED", "SUCCEEDED"]


# ══ AT-960-9-6、9-7：授權待查、定位符去重 ═════════════════════════════════════════════════════
def test_AT_960_9_6_license_pending_counts_gpl_family_and_unknown_licenses() -> None:
    sources = {"S-1": {"license_spdx": "GPL-3.0-only"}, "S-2": {"license_spdx": "AGPL-3.0"},
               "S-3": {"license_spdx": "Apache-2.0"}, "S-4": {"license_spdx": None},
               "S-5": {"license_spdx": "UNKNOWN"}, "S-6": {"license_spdx": "LGPL-2.1"},
               "S-7": {"license_spdx": "MIT"}, "S-8": {"license_spdx": "未見"}}
    items = [{"evidence_no": f"E-00{i}", "source_no": f"S-{i}"} for i in range(1, 9)]
    assert license_pending_numbers(items, sources) == ["E-001", "E-002", "E-004", "E-005",
                                                       "E-008"]
    head = render(evidence()).text.split("\n")[3]            # 矩陣頁頂：GPL／AGPL 與未見的計數
    assert head.startswith("> 授權待查：3 筆") and "E-001、E-003、E-004" in head


LICENSE_CASES: dict[str, Any] = json.loads(
    (CONTENT.parents[1] / "license_pending_cases.json").read_text(encoding="utf-8"))


def test_AT_960_9_6_the_shared_table_decides_every_license_case_like_the_frontend() -> None:
    """D-80 雙端對拍：這張表也由前端 `isLicensePending` 的測試逐列斷言；Bridge 這端逐列都要對。"""
    cases = LICENSE_CASES["cases"]
    assert LICENSE_CASES["schema"] == 1
    wrong = [(c["license_spdx"], c["pending"]) for c in cases
             if is_license_pending(c["license_spdx"]) is not c["pending"]]
    assert wrong == [], f"與共用期望表不符：{wrong}"
    texts = [c["license_spdx"] for c in cases if c["license_spdx"] is not None]
    unknowns = {t for t in texts if t.strip().casefold() == "unknown"}
    assert len(unknowns) >= 3, "UNKNOWN 的大小寫與空白變體"
    assert sum(t.strip().upper().startswith("LGPL") for t in texts) >= 2, "LGPL 列"
    composite = sum(bool(re.search(r"\b(OR|AND|WITH)\b", t, re.IGNORECASE)) for t in texts)
    assert composite >= 5, "複合式列"
    gpl_family = sum(re.match(r"\s*A?GPL", t, re.IGNORECASE) is not None for t in texts)
    assert gpl_family >= 5, "GPL／AGPL 列"
    assert sum(c["pending"] for c in cases) >= 8 and sum(not c["pending"] for c in cases) >= 8


def test_AT_960_9_6_the_matrix_header_and_the_license_cell_follow_the_same_table() -> None:
    """渲染路徑：授權待查計數（資安審查輸入同源）與矩陣授權欄的「未見」，對每個表列都與判準一致。"""
    for case in LICENSE_CASES["cases"]:
        def edit(doc: dict[str, Any], spdx: Any = case["license_spdx"]) -> None:
            doc["sources"][0]["license_spdx"] = spdx          # E-001 的來源 S-001
            for other in (2, 4):                  # S-003、S-005 原為 null：先壓成已知授權
                doc["sources"][other]["license_spdx"] = "MIT"
        text = render(evidence(edit)).text
        head = text.split("\n")[3]
        expected = 1 if case["pending"] else 0
        assert head.startswith(f"> 授權待查：{expected} 筆"), (case["license_spdx"], head)
        row = next(ln for ln in text.split("\n") if ln.startswith("| S-001 |"))
        cell = [c.strip() for c in row.strip().strip("|").split("|")][7]
        spdx = case["license_spdx"]
        unknown = spdx is None or spdx.strip().casefold() in ("", "unknown", "未見")
        assert cell == ("未見" if unknown else spdx), (spdx, cell)


def test_AT_960_9_7_locators_are_normalised_and_duplicates_keep_a_reference_count() -> None:
    a = normalize_locator("https://Example.ORG/p/x/?utm_source=a&b=2&a=1#frag")
    assert a == "https://example.org/p/x?a=1&b=2"
    assert normalize_locator("https://example.org/p/x?a=1&b=2&fbclid=z") == a
    assert normalize_locator(None, "10.1000/ABC.001") == "doi:10.1000/abc.001"
    assert normalize_locator("https://example.org/a", "10.1/X") == "doi:10.1/x"
    assert normalize_locator("not a url ") == "not a url"
    merged = dedupe_rows([
        {"id": "S-001", "url": "https://example.org/p/x?utm_medium=m"},
        {"id": "S-002", "url": "https://EXAMPLE.org/p/x/"},
        {"id": "S-003", "url": "https://example.org/p/y"},
        {"id": "S-004", "doi": "10.5/A", "url": "https://doi.org/10.5/A"},
        {"id": "S-005", "doi": "10.5/a", "url": "https://dx.doi.org/10.5/a"}])
    assert [(r["id"], r["ref_count"]) for r in merged] == [
        ("S-001", 2), ("S-003", 1), ("S-004", 2)], "先到者保留編號、路徑不同者獨立"


# ══ AT-960-9-E-3：增補只增不改（R15）══════════════════════════════════════════════════════════
def test_AT_960_9_E_3_a_supplement_must_keep_every_previous_row_bit_for_bit() -> None:
    prev = evidence()
    ctx = EvidenceContext(previous=prev)
    assert hit_rules(evidence(), ctx) == set(), "原樣保留：合格"

    def add_source(doc: dict[str, Any]) -> None:
        doc["sources"].append({**doc["sources"][1], "source_no": "S-007", "title": "新增來源"})
        doc["items"].append({**doc["items"][1], "evidence_no": "E-005", "source_no": "S-007"})
        doc["counter_evidence"].append({**doc["counter_evidence"][3], "evidence_no": "E-005"})
        doc["honest_bounds"]["summary_only"].append("S-007")
        doc["honest_bounds"]["not_read_fully"].append("S-007")

    assert hit_rules(evidence(add_source), ctx) == set(), "只新增、編號延續：合格"
    cases = {
        "drop_a_row": lambda d: d["items"].pop(0),
        "edit_a_source": lambda d: d["sources"][0].update(title="被改過"),
        "drop_a_search": lambda d: d["search_log"].pop(),
        "edit_an_item": lambda d: d["items"][1].update(f6="被改過的限制"),
    }
    for name, edit in cases.items():
        assert "R15" in hit_rules(evidence(edit), ctx), name

    older = evidence()                      # 前一版沒有 S-003：現在才出現的 S-003 低於前一版最大號
    older["sources"] = [s for s in older["sources"] if s["source_no"] != "S-003"]
    assert "R15" in hit_rules(evidence(), EvidenceContext(previous=older))


# ══ AT-960-9-2：矩陣的確定性渲染 ══════════════════════════════════════════════════════════════
def render(doc: dict[str, Any], *, version: int = 1, unanchored: tuple[str, ...] = ()
           ) -> export.RenderedMatrix:
    items = [{**i, "unanchored": i["evidence_no"] in unanchored} for i in doc["items"]]
    return export.render_evidence_matrix(
        version=version, scope_rev=doc["scope_rev"],
        axes_labels=["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"],
        sources=doc["sources"], items=items, counters=doc["counter_evidence"],
        bounds=doc["honest_bounds"])


def test_AT_960_9_2_the_matrix_layout_is_deterministic_and_follows_the_template() -> None:
    doc = evidence()
    first, second = render(doc), render(doc)
    assert first.text == second.text, "同樣輸入兩次輸出位元組相同"
    lines = first.text.split("\n")
    assert lines[0] == "<!-- r2p:evidence_matrix schema_rev=1 version=1 -->"
    assert lines[1].startswith("# 證據矩陣（version 1；scope_rev 1）")
    assert lines[3].startswith("> 授權待查：") and lines[4].startswith("> UNANCHORED：")
    headings = [line for line in lines if line.startswith("## ")]
    assert headings == ["## A 來源表", "## B 證據表", "## C 反證", "## D 線索區", "## E 誠實劃界"]
    table = [line for line in lines if line.startswith("| ID ")][0]
    assert table.count("|") - 1 == 17, "證據表十七欄"
    assert [c.strip() for c in table.strip("|").split("|")] == list(export.ITEM_HEADERS)
    source_header = [line for line in lines if line.startswith("| S-NNN | 標題 | 作者機構")][0]
    assert source_header.count("|") - 1 == 11
    assert "S-004" not in first.text.split("## D 線索區")[0], "T3 來源不進 A 來源表"
    assert export.CLUE_PURPOSE in first.text.split("## D 線索區")[1]
    for sentence in export.HONEST_SENTENCES:
        assert sentence in first.text
    for row in (ln for ln in lines if ln.startswith("| E-0")):
        assert "\n" not in row and row.endswith("|")


def test_AT_960_9_2_unanchored_rows_are_marked_and_long_cells_move_to_notes() -> None:
    doc = evidence()
    marked = render(doc, unanchored=("E-002",))
    assert "> UNANCHORED：1 筆" in marked.text
    row = next(ln for ln in marked.text.split("\n") if ln.startswith("| E-002 |"))
    assert row.rstrip(" |").endswith(export.UNANCHORED_MARK.strip())
    assert export.UNANCHORED_MARK not in render(doc).text
    long_doc = evidence(_set("items[0].f6", "長" * 700))
    out = render(long_doc)
    assert "見 notes/E-001.md" in out.text and "長" * 700 not in out.text
    assert out.notes == {"00_research/notes/E-001.md": "# E-001 附註\n\n## F6 限制\n\n"
                         + "長" * 700 + "\n"}
    with pytest.raises(ValueError):
        export._cell("甲|乙")


# ══ AT-960-9-E-2：渲染與資料列逐欄對拍 ═════════════════════════════════════════════════════════
def test_AT_960_9_E_2_each_matrix_row_equals_the_ingest_rows_cell_for_cell() -> None:
    doc = evidence()
    plan = plan_ingest(doc, matrix_version=1, raw_text_of=lambda _n: None)
    text = export.render_evidence_matrix(
        version=1, scope_rev=1,
        axes_labels=["技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本"],
        sources=doc["sources"], items=plan.items_rendered, counters=doc["counter_evidence"],
        bounds=doc["honest_bounds"]).text
    b_block = text.split("## B 證據表")[1].split("## C 反證")[0]
    by_row = {ln.split("|")[1].strip(): [c.strip() for c in ln.strip().strip("|").split("|")]
              for ln in b_block.split("\n") if ln.startswith("| E-0")}
    assert sorted(by_row) == ["E-001", "E-002", "E-003", "E-004"]
    sources = {s["source_no"]: s for s in plan.sources}
    for item in plan.items:
        cells = by_row[item["evidence_no"]]
        src = sources[item["source_no"]]
        assert cells[3] == src["title"] and cells[4] == src["authors_org"]
        assert cells[7] == src["tier"] and cells[8] == item["f7_verification"]
        assert cells[10] == item["f1_mechanism"] and cells[11] == item["f2_evidence"]
        assert cells[12] == item["f3_critique"] and cells[15] == item["f6_limits"]
        assert cells[13] == ("、".join(item["f4_risk_tags"]) or "無")
        assert cells[2] == (item["candidate"] or "—")
    c_block = text.split("## C 反證")[1].split("## D 線索區")[0]
    e_block = text.split("## E 誠實劃界")[1]
    for counter in doc["counter_evidence"]:
        assert counter["note"] in c_block and counter["conclusion"] in c_block
    for no in doc["honest_bounds"]["summary_only"] + doc["honest_bounds"]["not_read_fully"]:
        assert f"- {no}" in e_block
    for nf in doc["honest_bounds"]["not_found"]:
        assert f"- {nf['query']}（{nf['date']}）：{nf['result']}" in e_block


# ══ AT-960-9-3：引用預檢代碼 ══════════════════════════════════════════════════════════════════
def test_AT_960_9_3_citation_codes_equal_the_template_table_and_each_one_is_raised() -> None:
    assert prd_schema.CITES_CODES == (
        "CITES_MISSING", "CITES_V1", "CITES_UNANCHORED", "CITES_CANDIDATE")
    assert prd_schema.cite_findings(PRD_V1, ROWS) == []
    rows = {**ROWS, "E-001": {"f7": "V1", "strength": "CANDIDATE", "unanchored": False},
            "E-002": {"f7": "V2", "strength": "MEDIUM", "unanchored": True},
            "E-003": {"f7": "V2", "strength": "CANDIDATE", "unanchored": False}}
    del rows["E-004"]
    found = {(f.code, f.evidence_no) for f in prd_schema.cite_findings(PRD_V1, rows)}
    assert found == {("CITES_V1", "E-001"), ("CITES_UNANCHORED", "E-002"),
                     ("CITES_CANDIDATE", "E-003"), ("CITES_MISSING", "E-004")}
    codes = {v.message.split()[0] for v in prd_schema.precheck_draft(PRD_V1, evidence_rows=rows)}
    assert set(prd_schema.CITES_CODES) <= codes


# ══ AT-960-11-2／11-3／11-4／11-E-2：草擬預檢 P0 ═══════════════════════════════════════════════
def p0(text: str, rows: dict[str, Any] | None = ROWS) -> set[str]:
    return {v.rule for v in prd_schema.precheck_draft(text, evidence_rows=rows)}


def swap(old: str, new: str, count: int = 1) -> str:
    assert old in PRD_V1, old
    return PRD_V1.replace(old, new, count)


def test_AT_960_11_2_the_fixture_prd_passes_and_each_structural_defect_is_named() -> None:
    assert prd_schema.precheck_draft(PRD_V1, evidence_rows=ROWS) == []
    cases = {
        "P0-1": [swap("<!-- r2p:section=3 -->\n", ""),
                 PRD_V1 + "\n<!-- r2p:section=2 -->\n"],
        "P0-2": [swap("<!-- r2p:section=6 -->\n", "<!-- r2p:section=6 -->\n一段沒有標題的字\n")],
        "P0-3": [swap("## 📅 8. 時程與里程碑 (Timeline & Milestones)", "## 📅 時程與里程碑"),
                 swap("## 📋 文檔元數據", "## 📋 其他")],
        "P0-4": [PRD_V1 + "\n待補：{{TODO}}\n"],
    }
    for rule, texts in cases.items():
        for text in texts:
            assert rule in p0(text), rule


def test_AT_960_11_2_a_failing_draft_is_refused_by_the_gate_cli_with_the_missing_items(
        tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    (ws / "01_specs").mkdir(parents=True)
    (ws / "01_specs" / "PRD_draft.md").write_text(swap("<!-- r2p:section=3 -->\n", ""),
                                                  encoding="utf-8")
    rc, lines = run_gate_cli(["draft", "--workspace", str(ws)])
    assert rc != 0 and any("P0-1" in line for line in lines)


def test_AT_960_11_3_citations_must_exist_in_the_matrix_and_the_research_table_must_cite() -> None:
    missing_rows = {k: v for k, v in ROWS.items() if k != "E-003"}
    assert "P0-7" in p0(PRD_V1, missing_rows)
    uncited = swap("| 預先編譯樣板可明顯提高批次渲染吞吐量 | [E-001] |",
                   "| 預先編譯樣板可明顯提高批次渲染吞吐量 | |")
    assert "P0-7" in p0(uncited)
    no_table = swap("#### 研究依據", "#### 其他說明")
    assert "P0-7" in p0(no_table)
    assert "P0-7" not in p0(PRD_V1, None), "沒給 evidence_rows 時只判研究依據表的子句"


def test_AT_960_11_4_every_feature_has_boundaries_and_every_us_and_ac_is_cross_referenced() -> None:
    cases = [
        swap("- **邊界條件（Boundary Conditions）**:", "- **其他條件**:"),
        swap("#### US-002 查詢並重跑失敗項", "#### US-003 查詢並重跑失敗項"),
        swap("#### AC-002-2 重跑只含失敗項", "#### AC-002-9 重跑只含失敗項"),
    ]
    for text in cases:
        assert "P0-6" in p0(text)
    start, end = PRD_V1.index("#### AC-001-1"), PRD_V1.index("#### AC-001-2")
    gherkin = PRD_V1[:start] + PRD_V1[start:end].replace("Then", "那麼") + PRD_V1[end:]
    assert gherkin != PRD_V1 and any("Gherkin 缺 Then" in v.message for v in
                                     prd_schema.precheck_draft(gherkin, evidence_rows=ROWS))
    orphan = PRD_V1 + "\n#### AC-009-1 沒人引用的驗收\n- Given 甲 When 乙 Then 丙\n"
    assert any("沒有被任何 US 引用" in v.message
               for v in prd_schema.precheck_draft(orphan, evidence_rows=ROWS))


def test_AT_960_11_E_2_ids_are_rule_7_numeric_without_r2p_prefixes_or_duplicates() -> None:
    assert "P0-5" in p0(PRD_V1 + "\n- AC-R2P-001 不得出現\n")
    assert "P0-5" in p0(PRD_V1 + "\n- F-1 位數不合\n")
    assert "P0-5" in p0(PRD_V1 + "\n#### F-001 重複定義的功能\n")
    assert "P0-5" not in p0(PRD_V1)
    fenced = PRD_V1 + "\n```text\nAC-R2P-001 在程式碼區塊內不判\n```\n"
    assert "P0-5" not in p0(fenced)


def test_AT_960_11_2_chapter_nine_and_the_license_column_are_checked() -> None:
    assert "P0-8" in p0(swap("### 9.2 資料模型", "### 資料模型"))
    assert "P0-9" in p0(swap("```mermaid", "```text"))
    assert "P0-8" in p0(swap("| 授權條款 |", "| 其他欄 |"))


# ══ AT-960-12-1：加權總分以整數 W100 計算 ═════════════════════════════════════════════════════
A, P, Q, S = DIMENSIONS


def scores(a: int, p: int, q: int, s: int) -> dict[str, int]:
    return {A: a, P: p, Q: q, S: s}


W100_CASES = [
    (scores(85, 85, 84, 86), 8495, "84.95"), (scores(85, 85, 85, 85), 8500, "85.00"),
    (scores(90, 90, 90, 90), 9000, "90.00"), (scores(100, 100, 100, 100), 10000, "100.00"),
    (scores(0, 0, 0, 0), 0, "0.00"), (scores(60, 60, 60, 60), 6000, "60.00"),
    (scores(70, 80, 90, 100), 2100 + 2000 + 2250 + 2000, "83.50"),
    (scores(79, 79, 79, 79), 7900, "79.00"), (scores(99, 98, 97, 96), 9765, "97.65"),
]


@pytest.mark.parametrize("given, w100, shown", W100_CASES)
def test_AT_960_12_1_w100_and_the_exact_two_decimal_display(
        given: dict[str, int], w100: int, shown: str) -> None:
    assert aggregate.w100_of(given) == w100
    total = aggregate.weighted_total_of(w100)
    assert isinstance(total, Decimal) and aggregate.format_weighted(total) == shown
    assert total == Decimal(shown) and total.as_tuple().exponent == -2


def test_AT_960_12_1_the_weights_are_the_product_constants_and_never_round() -> None:
    assert dict(W100_WEIGHTS) == {A: 30, P: 25, Q: 25, S: 20} and sum(W100_WEIGHTS.values()) == 100
    assert (REVIEW_THRESHOLD, DIMENSION_FLOOR, SCG_RETRY_LIMIT) == (85, 60, 3)
    assert aggregate.THRESHOLD_W100 == 8500
    for bad in ({A: 85, P: 85, Q: 84}, {A: 85, P: 85, Q: 84, S: 86.0},
                {A: 85, P: 85, Q: 84, S: True}, {A: 85, P: 85, Q: 84, S: "86"}):
        with pytest.raises(ValueError):
            aggregate.w100_of(bad)


FORBIDDEN_CALLS = {"round", "float"}


def rounding_sites(source: str) -> list[str]:
    """`round(`／`float(` 呼叫與任何 `ROUND_` 名稱（含 `decimal.ROUND_*`、匯入）。"""
    hits = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and (
                node.func.id in FORBIDDEN_CALLS):
            hits.append(f"call {node.func.id} L{node.lineno}")
        names = [getattr(node, "id", None), getattr(node, "attr", None)]
        if isinstance(node, ast.alias):
            names.append(node.name)
        hits += [f"{n} L{getattr(node, 'lineno', 0)}" for n in names
                 if isinstance(n, str) and n.startswith("ROUND_")]
    return hits


def test_AT_960_12_1_the_judgement_path_has_no_rounding_or_float_and_the_scanner_can_fail() -> None:
    source = Path(aggregate.__file__).read_text(encoding="utf-8")
    assert rounding_sites(source) == []
    assert rounding_sites("x = round(84.95)\ny = float(a)\n") == ["call round L1", "call float L2"]
    assert rounding_sites("from decimal import ROUND_HALF_UP\n") == ["ROUND_HALF_UP L1"]
    assert rounding_sites("q = d.quantize(1, rounding=decimal.ROUND_DOWN)\n") != []


# ══ AT-960-12-2：判定表 ═══════════════════════════════════════════════════════════════════════
def decide(given: dict[str, int] | None, *, precheck: bool = True, p1: int = 0,
           gate: dict[str, Any] | None = None, post_human: bool = False) -> aggregate.Decision:
    return aggregate.decide(aggregate.RoundInputs(precheck, given, p1), gate,
                            post_human=post_human)


def test_AT_960_12_2_the_four_conditions_each_veto_a_pass_on_their_own() -> None:
    ok = decide(scores(90, 90, 90, 90))
    assert (ok.verdict, ok.gate_call, ok.judgement.passed) == ("PASS", "PASS", True)
    assert all(ok.judgement.conditions.values())
    exact = decide(scores(85, 85, 85, 85))
    assert exact.verdict == "PASS" and exact.judgement.w100 == 8500, "W100 剛好 8500 通過"
    # TCS 首組輸入：預檢過、W100 8500、最低維度恰 60、未結 P1 為 0 ⇒ PASS（地板與門檻兩個邊界
    # 同時成立）
    edge = decide(scores(100, 100, 60, 75))
    assert (edge.judgement.w100, edge.judgement.min_dimension_score) == (8500, 60)
    assert edge.verdict == "PASS" and edge.gate_call == "PASS" and edge.judgement.passed is True
    assert edge.judgement.conditions["all_dimensions_ge_floor"] is True, "最低維度恰 60：不低於地板"
    floor_only = decide(scores(100, 100, 100, 60))               # 只有地板在邊界、W100 遠高於門檻
    assert floor_only.judgement.w100 == 9200 and floor_only.verdict == "PASS"
    assert floor_only.judgement.conditions["all_dimensions_ge_floor"] is True
    below_floor = decide(scores(100, 100, 100, 59))
    assert below_floor.judgement.conditions["all_dimensions_ge_floor"] is False
    cases = {
        "W100 差一格（8495）": (decide(scores(85, 85, 84, 86)), "weighted_ge_threshold"),
        "最低維度 59": (decide(scores(100, 100, 100, 59)), "all_dimensions_ge_floor"),
        "未結 P1": (decide(scores(90, 90, 90, 90), p1=1), "no_open_p1"),
        "預檢不過": (decide(None, precheck=False), "precheck_passed"),
    }
    for label, (decision, key) in cases.items():
        assert decision.verdict == "REVISE" and decision.gate_call == "FAIL", label
        assert decision.judgement.conditions[key] is False, label
        assert decision.judgement.passed is False, label
    assert decide(scores(100, 100, 100, 59)).judgement.w100 == 9180, "分數夠高但地板不過仍不過"
    unscored = decide(None, precheck=False).judgement
    assert (unscored.w100, unscored.weighted_total, unscored.min_dimension_score) == (
        None, None, None), "預檢不過＝不計分"


def test_AT_960_12_2_verdict_follows_the_fsm_reply_and_post_human_never_calls_gate_pass() -> None:
    failing = scores(80, 80, 80, 80)
    assert decide(failing, gate={"retry_count": 1, "escalated": False}).verdict == "REVISE"
    assert decide(failing, gate={"retry_count": 2, "escalated": False}).verdict == "REVISE"
    third = decide(failing, gate={"retry_count": 3, "escalated": True})
    assert (third.verdict, third.escalated, third.gate_call) == ("ESCALATE", True, "FAIL")
    assert decide(failing, gate={"retry_count": 3}).verdict == "ESCALATE", "缺 escalated 鍵看計數"
    assert decide(failing, gate={"retry_count": 2}).verdict == "REVISE"
    assert decide(failing, gate={"retry_count": 3, "escalated": False}).verdict == "REVISE", (
        "以 FSM 回傳為準，Bridge 不自建計數")
    assert decide(failing).verdict == "REVISE", "回傳尚未取得時暫為 REVISE"
    passed_human = decide(scores(90, 90, 90, 90), post_human=True)
    assert (passed_human.verdict, passed_human.gate_call) == ("PASS", None)
    failed_human = decide(failing, post_human=True, gate={"retry_count": 1})
    assert failed_human.gate_call == "FAIL", "POST_HUMAN 未通過仍呼叫 gate FAIL"


# ══ AT-960-12-E-3：負控——84.95 必須不過，8500 通過，DB 的 CHECK 與判定一致 ═══════════════════════
def test_AT_960_12_E_3_the_negative_control_84_95_fails_and_85_00_passes() -> None:
    near = decide(scores(85, 85, 84, 86))
    assert near.judgement.w100 == 8495 and str(near.judgement.weighted_total) == "84.95"
    assert near.judgement.passed is False and near.verdict == "REVISE"
    edge = decide(scores(85, 85, 85, 85))
    assert edge.judgement.w100 == 8500 and str(edge.judgement.weighted_total) == "85.00"
    assert edge.judgement.passed is True and edge.verdict == "PASS"
    # 若先四捨五入再比，84.95 會被當成 85（假通過）——整數判定與「四捨五入後比較」必須不同
    assert round(float(near.judgement.weighted_total)) >= REVIEW_THRESHOLD
    assert near.judgement.passed is False


def test_AT_960_12_E_3_the_database_check_agrees_with_the_judgement(rdb: Any) -> None:
    db, ids, _calls = db_tests.seeded_round_one(rdb)
    row = db_tests.next_round(db, ids, 2)
    row.update(passed=True, verdict="PASS", weighted_score="84.95", min_dimension_score=85,
               fsm_gate_result="PASS", fsm_retry_count=0)
    with pytest.raises(ResearchDbError) as caught:
        db.insert_review_round(research_id=ids.research, actor="bridge", round=row)
    assert caught.value.sqlstate == "23514", (
        "passed=true 而 84.95 < 85.00：CHECK 擋下")
    assert [r["round_no"] for r in db.query(
        "SELECT round_no FROM {s}.research_review_rounds WHERE research_id = %s ORDER BY 1",
        (ids.research,))] == [1], "被擋的輪不留任何列"
    row["weighted_score"] = "85.00"                      # 邊界：整數判定通過者，DB 同樣放行
    assert db.insert_review_round(research_id=ids.research, actor="bridge",
                                  round=row)["applied"] is True


# ══ AT-960-12-3（單元部分）：審查者單維度輸出的邊界規則 ═══════════════════════════════════════════
REVIEW_ARCH: dict[str, Any] = json.loads(
    (CONTENT / "reviews" / "common" / "round-1" / "architecture.json").read_text(encoding="utf-8"))


def review_doc(edit: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    doc = copy.deepcopy(REVIEW_ARCH)
    if edit is not None:
        edit(doc)
    return doc


def review_rules(doc: dict[str, Any]) -> list[tuple[str, str]]:
    """(規則, 路徑) 清單；證據編號取黃金證據檔的四列。"""
    return [(v.rule, v.path) for v in validate_review_dimension(
        doc, dimension="ARCHITECTURE", round_no=1, prd_sha256=REVIEW_ARCH["prd_sha256"],
        evidence_numbers=ROWS)]


def with_item_score(score: int, note: str) -> Callable[[dict[str, Any]], None]:
    """第一個 rubric 項目改成指定分數與說明；`score` 一併改成五項之和（加總規則不是被測對象）。"""
    def edit(doc: dict[str, Any]) -> None:
        doc["rubric"][0].update(score=score, note=note)
        doc["score"] = sum(r["score"] for r in doc["rubric"])
    return edit


def test_AT_960_12_3_the_golden_reviewer_file_is_valid() -> None:
    assert review_rules(review_doc()) == []


def test_AT_960_12_3_an_item_scoring_18_or_more_must_cite_a_prd_anchor_in_its_note() -> None:
    """score≥18 的 rubric 項目 note 必含 `§`：恰 18 無 § ⇒ V3；17 無 § ⇒ 通過；18 有 § ⇒ 通過
    （突變 `>=18`→`>=19` 會讓第一條漏網）。"""
    bare = "沒有任何錨點的泛泛說明"
    assert review_rules(review_doc(with_item_score(18, bare))) == [("V3", "rubric[0].note")]
    assert review_rules(review_doc(with_item_score(19, bare))) == [("V3", "rubric[0].note")]
    assert review_rules(review_doc(with_item_score(20, bare))) == [("V3", "rubric[0].note")]
    assert review_rules(review_doc(with_item_score(17, bare))) == []
    assert review_rules(review_doc(with_item_score(0, bare))) == []
    assert review_rules(review_doc(with_item_score(18, "已核對 §9.3：邊界清楚"))) == []


def anchored(anchor: str) -> Callable[[dict[str, Any]], None]:
    def edit(doc: dict[str, Any]) -> None:
        doc["defects"][0]["prd_anchor"] = anchor
    return edit


def test_AT_960_12_3_a_defect_anchor_must_name_one_of_the_14_house_chapters() -> None:
    """prd_anchor 的章號是家規 14 章之一（§1～§14）：§14 通過、§15 與 §0 拒絕（突變
    `1[0-4]`→`1[0-5]` 會讓 §15 通過）；節號與 ID 後綴照文法。"""
    good = ["§1", "§9", "§10", "§14", "§9.4", "§14.12", "§6/NFR-001", "§1.2/AC-001-1"]
    bad = ["§15", "§0", "§19", "§100", "§9.123", "9.4", "§", "§ 9", "§9.4/xx", "§9.4/"]
    for anchor in good:
        assert review_rules(review_doc(anchored(anchor))) == [], anchor
    for anchor in bad:
        found = review_rules(review_doc(anchored(anchor)))
        assert found == [("V4", "defects[0].prd_anchor")], anchor
