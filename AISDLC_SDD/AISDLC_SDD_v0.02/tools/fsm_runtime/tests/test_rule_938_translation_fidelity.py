# enforces: R-9.38
"""R-9.38 Playbook 翻譯保真規則 — 登記層強制測試（Phase Z / ACT-164）。

行為層（AT↔step 100% 映射 / 白名單模板 / weak_regex audit）的完整測試位於
AutoClaude 側：`AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py` 與
`test_gherkin_to_regex.py`（跨 repo 邊界，FF-8 不可達）。本檔守 SDD 側登記層：
規則 yaml 結構完整、rule_loader 於 trigger_states 命中載入、RULES_INDEX 同步。
"""
from __future__ import annotations

from pathlib import Path

import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
RULE_FILE = FRAMEWORK_ROOT / "governance" / "rules" / "R-9.38-playbook-translation-fidelity.yaml"


def _load() -> dict:
    return yaml.safe_load(RULE_FILE.read_text(encoding="utf-8"))


def test_rule_yaml_exists_with_required_fields():
    assert RULE_FILE.exists(), "R-9.38 規則 yaml 須落地（Phase Z / ACT-164）"
    doc = _load()
    assert doc["id"] == "R-9.38"
    assert doc["maturity"] == "active"
    assert doc["severity"] == "high"
    assert set(doc["trigger_states"]) == {"IMPLEMENTATION", "PR_REVIEW"}


def test_spec_pins_translation_fidelity_invariants():
    """規則本文必須釘住三個保真不變量（缺一即為規則被掏空）。"""
    spec = _load()["spec"]
    assert "一對一" in spec and "SPEC_AUDIT" in spec       # AT↔step 雙向映射 + 違反處置
    assert "白名單" in spec and "SPEC_TAINTED" in spec     # evaluator 模板白名單
    assert "weak_regex" in spec and "silent" in spec       # audit 留痕、禁 silent fallback


def test_rule_loader_loads_for_trigger_states():
    from tools.fsm_runtime import rule_loader

    for state in ("IMPLEMENTATION", "PR_REVIEW"):
        loaded = rule_loader.load_for_state(state)
        ids = {getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
               for r in loaded}
        assert "R-9.38" in ids, f"R-9.38 須於 {state} 被 lazy-load"


def test_rules_index_row_synced():
    idx = (FRAMEWORK_ROOT / "governance" / "RULES_INDEX.md").read_text(encoding="utf-8")
    assert "R-9.38-playbook-translation-fidelity.yaml" in idx
