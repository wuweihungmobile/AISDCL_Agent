"""框架模板 ↔ Bridge 常數的對拍（TCS-ResearchToPRD-P0 AT-960-12-E-1；D-43：模板是 SSOT）。

三份框架模板（`ISSUE-SCOPE`、`EVIDENCE-MATRIX`、`ADVERSARIAL-REVIEW-CARD`）各以
`<!-- r2p:contract=<名稱> -->` 標記其後的第一個 ```json 區塊；本檔抽出全部九個區塊並要求：
範例通過 Bridge 的驗證器、登錄表與參數逐值等於 Bridge 的常數。來源兩份：夾具框架（永遠跑）與真 SDD
樹（`SDD_ROOT` 不在＝TOOL-ABSENCE 跳過）——模板被改動而 Bridge 沒跟上時，真樹那一份會紅。
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from app.research.gates import schemas
from app.research.gates.evidence import validate_evidence_items
from app.research.gates.review_card import validate_review_card, validate_review_dimension
from tests.research_stage_support import FRAMEWORK
from tests.test_research_fsm_ops import real_sdd_root

CONTRACT = re.compile(r"<!--\s*r2p:contract=([a-z_]+)\s*-->\s*\n```json\n(.*?)\n```", re.S)
TEMPLATES = {
    "ISSUE-SCOPE-TEMPLATE.md": {"issue_scope"},
    "EVIDENCE-MATRIX-TEMPLATE.md": {"evidence_items", "axis_registry", "risk_tag_registry"},
    "ADVERSARIAL-REVIEW-CARD-TEMPLATE.md": {"review_params", "rubric_registry",
                                            "review_dimension", "review_dimension_qa",
                                            "review_card"},
}
ALL_NAMES = set().union(*TEMPLATES.values())


@pytest.fixture(params=["fixture", "real"])
def requirements(request: pytest.FixtureRequest) -> Path:
    base = FRAMEWORK if request.param == "fixture" else real_sdd_root()
    return base / "docs_template" / "sdd" / "requirements"


def extract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    found = CONTRACT.findall(text)
    names = [name for name, _body in found]
    assert len(names) == len(set(names)), f"{path.name} 有重複的標記：{names}"
    return {name: json.loads(body) for name, body in found}


@pytest.fixture
def blocks(requirements: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for filename, expected in TEMPLATES.items():
        found = extract(requirements / filename)
        assert set(found) == expected, f"{filename}：區塊集合 {sorted(found)}"
        merged.update(found)
    return merged


def plain(value: Any) -> Any:
    """常數表（MappingProxyType、tuple）轉成 JSON 可比的純資料。"""
    def convert(obj: Any) -> Any:
        return dict(obj) if hasattr(obj, "keys") else list(obj)

    return json.loads(json.dumps(value, default=convert, ensure_ascii=False))


def registry_diffs(block: Any, constant: Any) -> list[str]:
    left, right = plain(block), plain(constant)
    if left == right:
        return []
    if isinstance(left, dict) and isinstance(right, dict):
        keys = sorted(set(left) | set(right))
        return [f"{key}: 模板 {left.get(key)!r}／Bridge {right.get(key)!r}"
                for key in keys if left.get(key) != right.get(key)]
    return [f"模板 {left!r}／Bridge {right!r}"]


def test_AT_960_12_E_1_exactly_nine_marked_json_blocks_exist(blocks: dict[str, Any]) -> None:
    assert set(blocks) == ALL_NAMES and len(blocks) == 9


def test_AT_960_12_E_1_registries_and_parameters_equal_the_bridge_constants(
        blocks: dict[str, Any]) -> None:
    assert registry_diffs(blocks["axis_registry"], schemas.AXIS_REGISTRY) == []
    assert registry_diffs(blocks["risk_tag_registry"], schemas.RISK_TAG_REGISTRY) == []
    assert registry_diffs(blocks["review_params"], schemas.REVIEW_PARAMS) == []
    assert registry_diffs(blocks["rubric_registry"], schemas.RUBRIC_REGISTRY) == []
    params = blocks["review_params"]
    assert params["threshold"] == schemas.REVIEW_THRESHOLD
    assert params["dimension_floor"] == schemas.DIMENSION_FLOOR
    assert params["weights"] == dict(schemas.REVIEW_WEIGHTS)


def test_AT_960_12_E_1_the_template_samples_pass_the_bridge_validators(
        blocks: dict[str, Any]) -> None:
    assert schemas.validate_issue_scope(blocks["issue_scope"]) == []
    assert validate_evidence_items(blocks["evidence_items"]) == []
    for name in ("review_dimension", "review_dimension_qa"):
        doc = blocks[name]
        problems = validate_review_dimension(
            doc, dimension=doc["dimension"], round_no=doc["round"], prd_sha256=doc["prd_sha256"])
        assert problems == [], (name, [(p.rule, p.path, p.message) for p in problems])
    card = validate_review_card(blocks["review_card"])
    assert card == [], [(p.rule, p.path, p.message) for p in card]


def test_AT_960_12_E_1_the_comparison_can_fail_a_value_a_key_and_a_sample(
        blocks: dict[str, Any]) -> None:
    """負控：改一個登錄值、多一個鍵、壞一個範例欄位，對拍都必須回報。"""
    axes = copy.deepcopy(blocks["axis_registry"])
    axes["cost"] = "成本（改）"
    assert registry_diffs(axes, schemas.AXIS_REGISTRY) == [
        "cost: 模板 '成本（改）'／Bridge '成本'"]
    axes = {**blocks["axis_registry"], "extra": "多出來的軸"}
    assert registry_diffs(axes, schemas.AXIS_REGISTRY) == [
        "extra: 模板 '多出來的軸'／Bridge None"]
    params = copy.deepcopy(blocks["review_params"])
    params["threshold"] = 80
    assert registry_diffs(params, schemas.REVIEW_PARAMS) != []
    rubric = copy.deepcopy(blocks["rubric_registry"])
    rubric["QA"]["items"] = rubric["QA"]["items"][:-1]
    assert registry_diffs(rubric, schemas.RUBRIC_REGISTRY) != []
    broken = copy.deepcopy(blocks["evidence_items"])
    broken["items"][0]["claim"] = ""
    assert validate_evidence_items(broken) != []
    scope = copy.deepcopy(blocks["issue_scope"])
    scope["slug"] = "Bad Slug"
    assert schemas.validate_issue_scope(scope) != []
    dim = copy.deepcopy(blocks["review_dimension"])
    dim["score"] = dim["score"] + 1
    assert validate_review_dimension(
        dim, dimension=dim["dimension"], round_no=dim["round"], prd_sha256=dim["prd_sha256"]) != []
    other = copy.deepcopy(blocks["review_card"])
    other["final_verdict"] = "MAYBE"
    assert validate_review_card(other) != []
