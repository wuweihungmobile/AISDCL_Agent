# enforces (governance rules): R-SELF-STRIDE, R-9.3, R-9.1, R-9.20
"""W-38 — catch 覆蓋補強（閉合 DEF-19-001 catch 覆蓋 5/39→7/39 漸進缺口）測試。

improving_38：把 improving_19/20/37 已定義的 catch 三要件契約，新增到兩條**有唯一生產
ESCALATION 落點、僅缺 failure_mode** 的凍結規則：
  - W-38-1 → **R-SELF-STRIDE**（Loop Self-STRIDE）：SANDBOX_HARDENING_GATE policy_violation
    → ESCALATION（FSMRuntime.exit_sandbox_hardening_gate 的 record_escalation 落點）；
  - W-38-2 → **R-9.3**（邏輯一致性防護）：SPEC_AUDIT 於 SPEC_AUDIT_MAX_PER_STAGE 內無法解消
    矛盾 → ESCALATION（FSMRuntime.record_spec_audit 的 record_escalation 落點）。

每個 case 編碼「為何此行為重要」（Rule 9）：
  - flag ON：對應 escalate 分支真實觸發 → 對「failure_mode 已定義 + 顯式歸因」的規則 catch+1；
  - flag OFF：同一 escalate 分支行為逐字同 v0.15（catch 全程 0）＝零退化（flag 為唯一開關）；
  - **非重疊守門（DEF-18-001 核心）**：
      · R-SELF-STRIDE — verdict=pass 路徑轉 EXECUTION_EVALUATION，不 escalate → catch 恆 0；
      · R-9.3 — check_implementation_budget 的 implementation-budget-exceeded 直接 escalate
        落點（正交失敗模式、目前無規則承載），R-9.3 在該路徑 catch 恆 0，杜絕雙重歸因；
  - 真實凍結 governance 規則 R-SELF-STRIDE / R-9.3 已自描述 failure_mode（可參與 catch 自動歸因）。
沿用 improving_19/20/37 契約：fail-closed、只增 catch_count、永不 set_maturity（R-9.20 #11）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import rule_loader  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402
from tools.fsm_runtime.transition_rules import (  # noqa: E402
    IMPL_MAX_ITERATIONS,
    SPEC_AUDIT_MAX_PER_STAGE,
)

# 真實凍結 governance 規則目錄（用於「真實規則已具 failure_mode」斷言；唯讀）
# parents: [0]=tests [1]=fsm_runtime [2]=tools [3]=v0.16 根
_REAL_RULES_DIR = Path(__file__).resolve().parents[3] / "governance" / "rules"


def _write_rule(rules_dir: Path, rule_id: str, *, trigger_states, failure_mode="") -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": rule_id,
        "title": f"synthetic {rule_id}",
        "trigger_states": list(trigger_states),
        "severity": "high",
        "maturity": "active",
        "spec": "synthetic test rule",
        "test_ref": "",
    }
    if failure_mode:
        payload["failure_mode"] = failure_mode
    payload["scaffold_roi"] = {"fire_count": 0, "catch_count": 0, "false_positive_count": 0}
    (rules_dir / f"{rule_id}.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@pytest.fixture
def _w38_rules(tmp_path, monkeypatch):
    """隔離 rules_dir 種 R-SELF-STRIDE / R-9.3（failure_mode 非空 → 可參與 catch 自動歸因），
    避免污染 v0.16 凍結 governance。R-9.1 一併種入供非重疊守門（implementation budget）對照。"""
    rdir = tmp_path / "rules"
    _write_rule(rdir, "R-SELF-STRIDE", trigger_states=["SANDBOX_HARDENING_GATE"],
                failure_mode="SANDBOX_HARDENING_GATE policy_violation → ESCALATION（structural）")
    _write_rule(rdir, "R-9.3", trigger_states=["PR_REVIEW", "SPEC_AUDIT"],
                failure_mode="SPEC_AUDIT 上限內無法解消矛盾 → ESCALATION")
    _write_rule(rdir, "R-9.1", trigger_states=["*"],
                failure_mode="gate retry budget 耗盡 → ESCALATION")
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _catch_count(rules_dir: Path, rule_id: str) -> int:
    doc = yaml.safe_load((rules_dir / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    return int(doc["scaffold_roi"]["catch_count"])


def _rt(tmp_path, current, name="w38"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


# ---------- W-38-1 R-SELF-STRIDE：SANDBOX_HARDENING_GATE policy_violation → catch ----------

def test_rselfstride_catch_on_policy_violation_flag_on(tmp_path, monkeypatch, _w38_rules):
    """flag ON：sandbox 硬化閘 policy_violation escalate → R-SELF-STRIDE 守望的失敗模式真實
    發生 → catch+1。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "SANDBOX_HARDENING_GATE")
    res = rt.exit_sandbox_hardening_gate("policy_violation")
    assert res["to"] == "ESCALATION", "policy_violation 必直升 ESCALATION（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w38_rules, "R-SELF-STRIDE") == 1, "顯式歸因 + failure_mode 齊備 → catch+1"


def test_rselfstride_catch_flag_off_zero_regression(tmp_path, monkeypatch, _w38_rules):
    """flag OFF：同一 escalate 分支行為逐字同 v0.15——仍 escalate 但 catch 全程 0（零退化）。"""
    monkeypatch.delenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", raising=False)
    rt = _rt(tmp_path, "SANDBOX_HARDENING_GATE")
    res = rt.exit_sandbox_hardening_gate("policy_violation")
    assert res["to"] == "ESCALATION", "escalate 行為不受 flag 影響（catch 是純疊加記帳）"
    assert _catch_count(_w38_rules, "R-SELF-STRIDE") == 0, "flag OFF 不得記 catch（零退化）"


def test_rselfstride_not_attributed_on_sandbox_pass(tmp_path, monkeypatch, _w38_rules):
    """flag ON 但 verdict=pass：轉 EXECUTION_EVALUATION、不 escalate → R-SELF-STRIDE catch 恆 0。
    鎖死「唯一生產落點＝policy_violation；pass 路徑不搭便車」的無歧義映射（DEF-18-001 非重疊）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "SANDBOX_HARDENING_GATE")
    res = rt.exit_sandbox_hardening_gate("pass")
    assert res["verdict"] == "pass" and rt.state.current == "EXECUTION_EVALUATION"
    assert _catch_count(_w38_rules, "R-SELF-STRIDE") == 0, "pass 路徑不 escalate → 不得歸因"


# ---------- W-38-2 R-9.3：SPEC_AUDIT 耗盡無法解消 → catch ----------

def test_r93_catch_on_spec_audit_exhaustion_flag_on(tmp_path, monkeypatch, _w38_rules):
    """flag ON：SPEC_AUDIT 達上限仍無法解消矛盾 escalate → R-9.3 守望的失敗模式真實發生 → catch+1。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "PR_REVIEW")
    rt.state.retry("PR_REVIEW")["spec_audit_count"] = SPEC_AUDIT_MAX_PER_STAGE
    res = rt.record_spec_audit()
    assert res.get("escalated") is True, "spec_audit 耗盡必 escalate（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w38_rules, "R-9.3") == 1, "R-9.3 顯式歸因 + failure_mode 齊備 → catch+1"


def test_r93_catch_flag_off_zero_regression(tmp_path, monkeypatch, _w38_rules):
    """flag OFF：同一 escalate 分支行為逐字同 v0.15——仍 escalate 但 catch 全程 0（零退化）。"""
    monkeypatch.delenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", raising=False)
    rt = _rt(tmp_path, "PR_REVIEW")
    rt.state.retry("PR_REVIEW")["spec_audit_count"] = SPEC_AUDIT_MAX_PER_STAGE
    res = rt.record_spec_audit()
    assert res.get("escalated") is True, "escalate 行為不受 flag 影響"
    assert _catch_count(_w38_rules, "R-9.3") == 0, "flag OFF 不得記 catch（零退化）"


def test_r93_not_attributed_on_implementation_budget_exceeded(tmp_path, monkeypatch, _w38_rules):
    """flag ON：走 check_implementation_budget 的 implementation-budget-exceeded 直接 escalate
    落點（max_iterations 耗盡，非 SPEC_AUDIT 路徑）→ ESCALATION 但 R-9.3 catch 恆 0。鎖死
    「R-9.3 failure_mode 僅涵蓋 record_spec_audit 耗盡落點、不搭便車正交的 implementation budget
    落點」的無歧義映射意圖（DEF-18-001 寧缺勿濫，防雙重歸因污染 ROI）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "IMPLEMENTATION")
    rt.state.implementation_budget()["current_iteration"] = IMPL_MAX_ITERATIONS
    res = rt.check_implementation_budget()
    assert res.get("escalated") is True, "implementation budget 耗盡必 escalate（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w38_rules, "R-9.3") == 0, \
        "implementation-budget-exceeded 落點未接線 → R-9.3 不得被歸因（非重疊）"


# ---------- 真實凍結 governance：R-SELF-STRIDE / R-9.3 已自描述 failure_mode ----------

def test_real_rule_rselfstride_has_failure_mode():
    """凍結本體 R-SELF-STRIDE 必須自描述非空 failure_mode（要件①），否則生產環境
    SANDBOX_HARDENING_GATE policy_violation escalate 分支即便 flag ON 也因 fail-closed 不記 catch。"""
    doc = yaml.safe_load((_REAL_RULES_DIR / "R-SELF-STRIDE.yaml").read_text(encoding="utf-8"))
    assert doc.get("failure_mode", "").strip(), "R-SELF-STRIDE 須具非空 failure_mode（catch 可歸因）"


def test_real_rule_r93_has_failure_mode():
    """凍結本體 R-9.3 必須自描述非空 failure_mode（要件①），covering DEF-19-001。"""
    doc = yaml.safe_load(
        (_REAL_RULES_DIR / "R-9.3-logical-consistency-guard.yaml").read_text(encoding="utf-8")
    )
    assert doc.get("failure_mode", "").strip(), "R-9.3 須具非空 failure_mode（catch 可歸因）"
