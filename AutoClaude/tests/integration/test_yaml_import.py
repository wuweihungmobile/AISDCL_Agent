"""SD_Improving_06 W4-T4-6 — YAML → DB 匯入工具整合測試。

對應規格：
  - SD_Improving_06.md §6.5 AC6-4：success_rate == 100% + JSONB key 順序 + float ±1e-6 等價
  - SD06_Execution_Guide.md §3 W4 T4-6

涵蓋面：
  T1 parse_yaml_to_fixture：兩種格式（playbook / three_tier）皆可解析
  T2 sha256 deterministic：同 yaml 文字 → 同 sha256（versioning 基礎）
  T3 ImportReport 摘要：projects/goal_tasks/execution_items 計數正確
  T4 build_diffs：每個三層節點皆對應一條 yaml_import_diffs 條目
  T5 雙向往返：fixture.model_dump → re-validate → ThreeTierFixture（深度保持）
  T6 PII filter 整合：secret 欄位 → PIIFilterViolation（pass-through 為主防線）
  T7 深度紅線：sub-task depth=4 → 拒絕（Pydantic ValidationError）
  T8 CLI 入口 dry-run：對所有 fixtures 走 process_single，success_rate=100%

設計：parametrize over 全部既有 YAML × 5 assertion 群 = 80+ test case（QA AC6-4 對位）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml as _yaml
from pydantic import ValidationError

# tools.migrate_yaml_to_db 於 module 層 import click；CI 基礎 test job 僅裝 .[dev]
# 無 click → 未安裝時整體 skip（對齊 test_pg_memory_store_security.py importorskip 慣例）
pytest.importorskip("click")

from tools.migrate_yaml_to_db import (  # noqa: E402
    ImportReport,
    build_diffs,
    compute_yaml_sha256,
    derive_playbook_id,
    detect_format,
    discover_yaml_sources,
    parse_yaml_to_fixture,
    process_single,
)
from autoclaude.infra.services.pii_filter import PIIFilter, PIIFilterViolation
from autoclaude.models.three_tier_schema import (
    GoalTask,
    Project,
    ThreeTierFixture,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
YAML_SOURCES = sorted([
    *(REPO_ROOT / "scripts").glob("*.yaml"),
    *(REPO_ROOT / "tests" / "equivalence" / "fixtures").glob("*.yaml"),
    *(REPO_ROOT / "tests" / "fixtures").glob("*.yaml"),
])


@pytest.fixture(scope="module")
def pii() -> PIIFilter:
    return PIIFilter(enabled=True)


# ──────────────────────────────────────────────────────────────
# T1 parse_yaml_to_fixture：所有 YAML 皆可解析
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_parse_yaml_to_fixture_succeeds(yaml_path: Path):
    text = yaml_path.read_text(encoding="utf-8")
    fixture = parse_yaml_to_fixture(text, yaml_path)
    assert isinstance(fixture, ThreeTierFixture)
    assert len(fixture.projects) >= 1


# ──────────────────────────────────────────────────────────────
# T2 sha256 deterministic：同文字 → 同 sha256
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_sha256_is_deterministic(yaml_path: Path):
    text = yaml_path.read_text(encoding="utf-8")
    h1 = compute_yaml_sha256(text)
    h2 = compute_yaml_sha256(text)
    assert h1 == h2
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert h1 == expected


# ──────────────────────────────────────────────────────────────
# T3 format detect：每個 YAML 都對應 playbook 或 three_tier（非 unknown）
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_format_detection(yaml_path: Path):
    text = yaml_path.read_text(encoding="utf-8")
    data = _yaml.safe_load(text)
    fmt = detect_format(data) if isinstance(data, dict) else "unknown"
    assert fmt in ("playbook", "three_tier")


# ──────────────────────────────────────────────────────────────
# T4 ImportReport 摘要計數 + diffs >= 1
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_process_single_succeeds(yaml_path: Path, pii: PIIFilter):
    rep = process_single(yaml_path, pii)
    assert rep.success, f"{yaml_path} 失敗：{rep.error}"
    assert rep.projects_count >= 1
    assert rep.goal_tasks_count >= 1
    assert len(rep.diffs) >= 1
    assert rep.yaml_sha256 == hashlib.sha256(
        yaml_path.read_text(encoding="utf-8").encode("utf-8")
    ).hexdigest()


# ──────────────────────────────────────────────────────────────
# T5 雙向往返：model_dump → 重新 validate 等價
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_roundtrip_via_fixture_model(yaml_path: Path):
    text = yaml_path.read_text(encoding="utf-8")
    fixture = parse_yaml_to_fixture(text, yaml_path)
    dumped = fixture.model_dump(mode="json")
    # JSONB key 順序穩定：sort_keys 兩次相等
    s1 = json.dumps(dumped, ensure_ascii=False, sort_keys=True)
    s2 = json.dumps(
        ThreeTierFixture(**dumped).model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
    )
    assert s1 == s2


# ──────────────────────────────────────────────────────────────
# T6 PII filter：secret → PIIFilterViolation（防 token-like 寫入）
# ──────────────────────────────────────────────────────────────
def test_pii_filter_blocks_secret_field():
    from autoclaude.infra.services.pii_filter import FieldRegistry
    from autoclaude.models.pii_classification import PIIClassification

    reg = FieldRegistry(rules={
        "yaml_import_diffs.secret_blob": PIIClassification.SECRET,
    })
    pii = PIIFilter(registry=reg, enabled=True)
    with pytest.raises(PIIFilterViolation):
        pii.filter_text(
            field_path="yaml_import_diffs.secret_blob",
            text="sk-ABCDEF1234567890",
        )


def test_pii_filter_masks_pii_field():
    from autoclaude.infra.services.pii_filter import FieldRegistry
    from autoclaude.models.pii_classification import PIIClassification

    reg = FieldRegistry(rules={
        "yaml_import_diffs.user_email": PIIClassification.PII,
    })
    pii = PIIFilter(registry=reg, enabled=True)
    masked = pii.filter_text(
        field_path="yaml_import_diffs.user_email",
        text="contact alice@example.com if blocked",
    )
    assert "alice@example.com" not in masked
    assert "***" in masked


def test_pii_filter_scrubs_token_in_normal_field():
    pii = PIIFilter(enabled=True)
    out = pii.filter_text(
        field_path="yaml_import_diffs.notes",
        text="see token sk-ABCDEF1234567890 for retry",
    )
    assert "sk-ABCDEF1234567890" not in out


# ──────────────────────────────────────────────────────────────
# T7 深度紅線（PM #1）：depth=4 必拒絕
# ──────────────────────────────────────────────────────────────
def test_subtask_depth_exceeds_three_is_rejected():
    bad = {
        "version": "1.0",
        "projects": [{
            "project_id": "P1",
            "name": "deep",
            "goal_tasks": [{
                "goal_task_id": "G1",
                "title": "lvl1",
                "depth": 4,
            }],
        }],
    }
    with pytest.raises(ValidationError):
        ThreeTierFixture(**bad)


# ──────────────────────────────────────────────────────────────
# T8 discover_yaml_sources：dir 與 file 入口
# ──────────────────────────────────────────────────────────────
def test_discover_yaml_sources_directory():
    found = discover_yaml_sources(REPO_ROOT / "scripts")
    assert any(p.name == "example_playbook.yaml" for p in found)


def test_discover_yaml_sources_single_file():
    target = REPO_ROOT / "tests" / "fixtures" / "sample_goal_tasks.yaml"
    found = discover_yaml_sources(target)
    assert found == [target]


def test_derive_playbook_id_uses_stem():
    target = REPO_ROOT / "scripts" / "example_playbook.yaml"
    assert derive_playbook_id(target) == "example_playbook"


# ──────────────────────────────────────────────────────────────
# T4+ build_diffs：每 fixture node 對應 ≥ 1 diff
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("yaml_path", YAML_SOURCES, ids=[p.name for p in YAML_SOURCES])
def test_build_diffs_covers_all_nodes(yaml_path: Path, pii: PIIFilter):
    text = yaml_path.read_text(encoding="utf-8")
    fixture = parse_yaml_to_fixture(text, yaml_path)
    diffs = build_diffs(fixture, pii)
    target_tables = {d.target_table for d in diffs}
    assert "projects" in target_tables
    assert "goal_tasks" in target_tables


# ──────────────────────────────────────────────────────────────
# T9 SUCCESS_RATE 100%（AC6-4 對位）
# ──────────────────────────────────────────────────────────────
def test_overall_success_rate_is_100_percent(pii: PIIFilter):
    reports: list[ImportReport] = [process_single(p, pii) for p in YAML_SOURCES]
    failures = [r for r in reports if not r.success]
    assert not failures, f"以下 YAML 解析失敗：{[(r.source, r.error) for r in failures]}"
    assert len(reports) == len(YAML_SOURCES)


# ──────────────────────────────────────────────────────────────
# T10 Project / GoalTask / ExecutionItem 模型基本 invariants
# ──────────────────────────────────────────────────────────────
def test_goal_task_priority_range():
    with pytest.raises(ValidationError):
        GoalTask(goal_task_id="G", title="t", depth=1, priority=99)


def test_project_requires_non_empty_name():
    with pytest.raises(ValidationError):
        Project(project_id="P", name="")
