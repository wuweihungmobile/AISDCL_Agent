# enforces (governance rules): R-9.2, R-9.22, R-9.20
"""W-20-1 — catch 覆蓋補強（閉合 DEF-19-001 catch 覆蓋 2/39 漸進缺口）測試。

improving_20：把 improving_19 已定義的 catch 三要件契約，從 R-9.1（gate retry）/ R-9.21
（monitor）兩呼叫點，擴到 **R-9.2（Context Budget·auto_compact per-stage 超限）** 與
**R-9.22（Phase J 規格自癒·spec_patch per-AC 上限耗盡）** 兩條規則的 ESCALATION 真實落點。

每個 case 編碼「為何此行為重要」（Rule 9）：
  - flag ON：對應 escalate 分支真實觸發 → 對「failure_mode 已定義 + 顯式歸因」的規則 catch+1；
  - flag OFF：兩 escalate 分支行為逐字同 v0.10（catch 全程 0）＝零退化（flag 為唯一開關）；
  - 真實凍結 governance 規則 R-9.2 / R-9.22 已自描述 failure_mode（可參與 catch 自動歸因）。
沿用 improving_19 契約：fail-closed、只增 catch_count、永不 set_maturity（R-9.20 #11）。
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
from tools.fsm_runtime.transition_rules import MAX_AUTO_COMPACT_PER_STAGE  # noqa: E402

# 真實凍結 governance 規則目錄（用於「真實規則已具 failure_mode」斷言；唯讀）
# parents: [0]=tests [1]=fsm_runtime [2]=tools [3]=v0.11 根
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
def _w20_rules(tmp_path, monkeypatch):
    """隔離 rules_dir 種 R-9.2 / R-9.22（failure_mode 非空 → 可參與 catch 自動歸因），
    避免污染 v0.11 凍結 governance。"""
    rdir = tmp_path / "rules"
    _write_rule(rdir, "R-9.2", trigger_states=["*"],
                failure_mode="per-stage auto_compact 超限 → ESCALATION")
    _write_rule(rdir, "R-9.22", trigger_states=["SPEC_PATCH_PROPOSAL"],
                failure_mode="spec_patch per-AC 上限耗盡 → ESCALATION")
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _catch_count(rules_dir: Path, rule_id: str) -> int:
    doc = yaml.safe_load((rules_dir / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    return int(doc["scaffold_roi"]["catch_count"])


def _rt(tmp_path, current, name="w20"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


def _drive_auto_compact_overflow(rt) -> dict:
    """把 auto_compact_state 預置到上限，再觸發一次 → projected > max → escalate 分支。"""
    rt.state.current = "IMPLEMENTATION"
    rt.state.root["auto_compact_state"] = {
        "stage_key": rt.current_stage_key(),
        "count_per_stage": MAX_AUTO_COMPACT_PER_STAGE,
        "max_per_stage": MAX_AUTO_COMPACT_PER_STAGE,
    }
    return rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)


def _drive_spec_patch_overflow(rt) -> dict:
    """把 spec_patch per-AC 計數預置到上限，再 enter 一次 → prior >= MAX → escalate 分支。"""
    rt.state.current = "SPEC_AUDIT"
    tracking = rt.state.root.setdefault("spec_patch_tracking", {})
    tracking.setdefault("count_per_ac", {})["AC-9"] = FSMRuntime.MAX_SPEC_PATCH_PER_AC
    save_state(rt.state)
    return rt.enter_spec_patch_proposal(ac_id="AC-9")


# ---------- R-9.2：auto_compact per-stage 超限 → catch ----------

def test_r92_catch_on_auto_compact_overflow_flag_on(tmp_path, monkeypatch, _w20_rules):
    """flag ON：auto_compact per-stage 超限 escalate → R-9.2 守望的失敗模式真實發生 → catch+1。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "INIT")
    res = _drive_auto_compact_overflow(rt)
    assert res.get("escalated") is True, "per-stage 超限必 escalate（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w20_rules, "R-9.2") == 1, "R-9.2 顯式歸因 + failure_mode 齊備 → catch+1"


def test_r92_catch_flag_off_zero_regression(tmp_path, monkeypatch, _w20_rules):
    """flag OFF：同一 escalate 分支行為逐字同 v0.10——仍 escalate 但 catch 全程 0（零退化）。"""
    monkeypatch.delenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", raising=False)
    rt = _rt(tmp_path, "INIT")
    res = _drive_auto_compact_overflow(rt)
    assert res.get("escalated") is True, "escalate 行為不受 flag 影響（catch 是純疊加記帳）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w20_rules, "R-9.2") == 0, "flag OFF 不得記 catch（零退化）"


# ---------- R-9.22：spec_patch per-AC 上限耗盡 → catch ----------

def test_r922_catch_on_spec_patch_overflow_flag_on(tmp_path, monkeypatch, _w20_rules):
    """flag ON：spec_patch per-AC 上限耗盡 escalate → R-9.22 守望的失敗模式真實發生 → catch+1。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "INIT")
    res = _drive_spec_patch_overflow(rt)
    assert res.get("escalated") is True, "per-AC 上限耗盡必直升 ESCALATION（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w20_rules, "R-9.22") == 1, "R-9.22 顯式歸因 + failure_mode 齊備 → catch+1"


def test_r922_catch_flag_off_zero_regression(tmp_path, monkeypatch, _w20_rules):
    """flag OFF：同一 escalate 分支行為逐字同 v0.10——仍 escalate 但 catch 全程 0（零退化）。"""
    monkeypatch.delenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", raising=False)
    rt = _rt(tmp_path, "INIT")
    res = _drive_spec_patch_overflow(rt)
    assert res.get("escalated") is True
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w20_rules, "R-9.22") == 0, "flag OFF 不得記 catch（零退化）"


# ---------- 真實凍結 governance：R-9.2 / R-9.22 已自描述 failure_mode ----------

@pytest.mark.parametrize("rule_file", [
    "R-9.2-context-budget.yaml",
    "R-9.22-adversarial-self-improving-phase-j.yaml",
])
def test_real_rule_has_failure_mode(rule_file):
    """凍結本體 R-9.2 / R-9.22 必須自描述非空 failure_mode（要件①），否則生產環境
    這兩條 escalate 分支即便 flag ON 也因 fail-closed 而不記 catch（covering DEF-19-001）。"""
    doc = yaml.safe_load((_REAL_RULES_DIR / rule_file).read_text(encoding="utf-8"))
    assert doc.get("failure_mode", "").strip(), f"{rule_file} 須具非空 failure_mode（catch 可歸因）"
