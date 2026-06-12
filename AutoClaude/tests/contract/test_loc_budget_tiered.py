"""LOC budget tiered policy contract tests — SD_07 W0 T0-5.

ADR-SD07-001 v1.0 §4.2 / §5 / §6：驗證分級制 budget 表生效、絕對紅線 750
不可突破、override 機制可控管。
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

clb = importlib.import_module("tools.check_loc_budget")


# ── 分級表結構驗證 ───────────────────────────────────────────


def test_loc_tiers_table_matches_adr_sd07_001():
    """ADR-SD07-001 §4.2 表格七層：data / plugin_entry / strategy /
    adapter / contract / service + absolute_limit。"""
    expected = {
        "data": 150,
        "plugin_entry": 250,
        "strategy": 300,
        "adapter": 400,
        "contract": 400,
        "service": 500,
    }
    for tier, budget in expected.items():
        assert tier in clb.LOC_TIERS, f"tier '{tier}' missing"
        assert clb.LOC_TIERS[tier]["budget"] == budget, (
            f"tier '{tier}' budget should be {budget}"
        )
    assert clb.ABSOLUTE_LIMIT == 750


# ── 分級判定（classify_file）─────────────────────────────────


@pytest.mark.parametrize(
    "rel_path,expected_tier,expected_budget",
    [
        ("autoclaude/models/playbook.py", "data", 150),
        ("autoclaude/core/ports/brain.py", "data", 150),
        ("autoclaude/plugins/notification_plugin.py", "plugin_entry", 250),
        ("autoclaude/plugins/checkpoint/plugin.py", "plugin_entry", 250),
        ("autoclaude/core/services/mutation/revise_current.py", "strategy", 300),
        ("autoclaude/infra/adapters/minimax_brain.py", "adapter", 400),
        ("autoclaude/infra/repositories/pg_state_repository.py", "adapter", 400),
        ("autoclaude/core/hookspec.py", "contract", 400),
        ("autoclaude/core/wiring.py", "contract", 400),
        ("autoclaude/execution/types.py", "contract", 400),
        ("autoclaude/core/services/auto_resume.py", "service", 500),
        ("autoclaude/execution/playbook_runner.py", "service", 500),
        ("autoclaude/execution/steps_orchestrator/_impl.py", "service", 500),
    ],
)
def test_classify_file_matches_tier(rel_path, expected_tier, expected_budget):
    tier, budget = clb.classify_file(Path(rel_path))
    assert tier == expected_tier, f"{rel_path} should be tier '{expected_tier}', got '{tier}'"
    assert budget == expected_budget


def test_unclassified_file_defaults_to_absolute_limit():
    """未匹配任何 tier 的檔案以 absolute_limit (750) 為預設 budget。"""
    tier, budget = clb.classify_file(Path("autoclaude/some_new_subsystem/foo.py"))
    assert tier == "unclassified"
    assert budget == clb.ABSOLUTE_LIMIT


# ── 各分級邊界（≥ 6 case 對齊執行指南 G0 驗證）──────────────


def test_data_tier_budget_enforced():
    assert clb.LOC_TIERS["data"]["budget"] == 150


def test_plugin_entry_tier_budget_enforced():
    """Plugin 公開 API ≤ 250；SD_06 W3 落地 12/12 plugin 全合規。"""
    assert clb.LOC_TIERS["plugin_entry"]["budget"] == 250


def test_strategy_tier_budget_enforced():
    assert clb.LOC_TIERS["strategy"]["budget"] == 300


def test_adapter_tier_budget_enforced():
    assert clb.LOC_TIERS["adapter"]["budget"] == 400


def test_contract_tier_budget_enforced():
    assert clb.LOC_TIERS["contract"]["budget"] == 400


def test_service_tier_budget_enforced():
    assert clb.LOC_TIERS["service"]["budget"] == 500


def test_absolute_limit_750_enforced():
    """ADR §4.2 #7 全域絕對紅線。"""
    assert clb.ABSOLUTE_LIMIT == 750


# ── override 機制 ────────────────────────────────────────────


def test_override_file_loads_when_present():
    """`.loc-budget.toml` 存在時可被解析。"""
    overrides = clb.load_overrides()
    assert isinstance(overrides, dict)
    # 規劃階段已豁免 prompt_builder.py（純函式集中）
    assert "autoclaude/decision/prompt_builder.py" in overrides
    entry = overrides["autoclaude/decision/prompt_builder.py"]
    assert entry["tier"] == "service"
    assert "reason" in entry and len(entry["reason"]) > 0


def test_override_applied_in_build_reports():
    """override 應將檔案 tier 與 budget 升級至指定層級。"""
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    pb = next(
        r for r in reports if r.rel_path == "autoclaude/decision/prompt_builder.py"
    )
    assert pb.tier == "service"
    assert pb.budget == 500
    assert pb.override_reason is not None


# ── 絕對紅線真實掃描 ────────────────────────────────────────


def test_no_file_exceeds_absolute_limit_750():
    """任何層級不得超 750 LOC（紅線 ❌14 + ❌16 防 god-class 復活）。"""
    overrides = clb.load_overrides()
    reports = clb.build_reports(overrides)
    over = [r for r in reports if r.loc > clb.ABSOLUTE_LIMIT]
    assert not over, (
        "absolute red line breach (> 750 LOC):\n"
        + "\n".join(f"  {r.rel_path}: {r.loc}" for r in over)
    )


# ── 政策版本標記 ────────────────────────────────────────────


def test_policy_version_marker_present_in_env_example():
    """`.env.example` 必含 LOC_BUDGET_POLICY_VERSION=v2 以追蹤政策落地版本。"""
    env_path = PROJECT_ROOT / ".env.example"
    text = env_path.read_text(encoding="utf-8")
    assert "LOC_BUDGET_POLICY_VERSION=v2" in text
