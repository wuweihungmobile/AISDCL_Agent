# enforces (governance rules): R-9.7, R-9.2, R-9.20
"""W-37-1 — catch 覆蓋補強（閉合 DEF-19-001 catch 覆蓋 4/39→5/39 漸進缺口）測試。

improving_37：把 improving_19/20 已定義的 catch 三要件契約，新增到 **R-9.7（Phase E M1
精準停機·9.7.2 HUMAN_PENDING 逾時 ≥168h 自動 ESCALATION）** 一條規則的 ESCALATION 真實落點
（FSMRuntime.escalate_human_pending_timeout，由 session_start hook 委派呼叫）。

每個 case 編碼「為何此行為重要」（Rule 9）：
  - flag ON：HUMAN_PENDING 逾時 escalate 分支真實觸發 → 對「failure_mode 已定義 + 顯式歸因」
    的 R-9.7 catch+1；
  - flag OFF：同一 escalate 分支行為逐字同 v0.14（catch 全程 0）＝零退化（flag 為唯一開關）；
  - **非重疊守門（DEF-18-001 核心意圖）**：R-9.7 的 failure_mode 僅涵蓋 9.7.2；9.7.3（AUTO_COMPACT
    per-stage 超限）的 escalate 落點歸 R-9.2（trigger_auto_compact），R-9.7 在該路徑 catch 恆 0，
    杜絕雙重歸因；
  - 真實凍結 governance 規則 R-9.7 已自描述 failure_mode（可參與 catch 自動歸因）。
沿用 improving_19/20 契約：fail-closed、只增 catch_count、永不 set_maturity（R-9.20 #11）。
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
# parents: [0]=tests [1]=fsm_runtime [2]=tools [3]=v0.15 根
_REAL_RULES_DIR = Path(__file__).resolve().parents[3] / "governance" / "rules"

_TIMEOUT_REASON = (
    "HUMAN_PENDING 逾時 200h (≥168h)，自動進入 ESCALATION (ACT-023)"
)


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
def _w37_rules(tmp_path, monkeypatch):
    """隔離 rules_dir 種 R-9.7 / R-9.2（failure_mode 非空 → 可參與 catch 自動歸因），
    避免污染 v0.15 凍結 governance。R-9.2 一併種入供非重疊守門測試使用。"""
    rdir = tmp_path / "rules"
    _write_rule(rdir, "R-9.7", trigger_states=["*", "HUMAN_PENDING"],
                failure_mode="HUMAN_PENDING 逾時 ≥168h → 自動 ESCALATION（9.7.2）")
    _write_rule(rdir, "R-9.2", trigger_states=["*"],
                failure_mode="per-stage auto_compact 超限 → ESCALATION")
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _catch_count(rules_dir: Path, rule_id: str) -> int:
    doc = yaml.safe_load((rules_dir / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    return int(doc["scaffold_roi"]["catch_count"])


def _rt(tmp_path, current, name="w37"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


def _drive_auto_compact_overflow(rt) -> dict:
    """把 auto_compact_state 預置到上限，再觸發一次 → projected > max → escalate 分支（9.7.3 路徑）。"""
    rt.state.current = "IMPLEMENTATION"
    rt.state.root["auto_compact_state"] = {
        "stage_key": rt.current_stage_key(),
        "count_per_stage": MAX_AUTO_COMPACT_PER_STAGE,
        "max_per_stage": MAX_AUTO_COMPACT_PER_STAGE,
    }
    return rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)


# ---------- R-9.7：HUMAN_PENDING 逾時 ≥168h → catch ----------

def test_r97_catch_on_human_pending_timeout_flag_on(tmp_path, monkeypatch, _w37_rules):
    """flag ON：HUMAN_PENDING 逾時 escalate → R-9.7 守望的失敗模式（9.7.2）真實發生 → catch+1。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "HUMAN_PENDING")
    rt.escalate_human_pending_timeout(reason=_TIMEOUT_REASON)
    assert rt.state.current == "ESCALATION", "逾時必直升 ESCALATION（既有不變式）"
    assert _catch_count(_w37_rules, "R-9.7") == 1, "R-9.7 顯式歸因 + failure_mode 齊備 → catch+1"


def test_r97_catch_flag_off_zero_regression(tmp_path, monkeypatch, _w37_rules):
    """flag OFF：同一 escalate 分支行為逐字同 v0.14——仍 escalate 但 catch 全程 0（零退化）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "0")  # v0.24 翻環後以顯式 '0' opt-out 表達 OFF
    rt = _rt(tmp_path, "HUMAN_PENDING")
    rt.escalate_human_pending_timeout(reason=_TIMEOUT_REASON)
    assert rt.state.current == "ESCALATION", "escalate 行為不受 flag 影響（catch 是純疊加記帳）"
    assert _catch_count(_w37_rules, "R-9.7") == 0, "flag OFF 不得記 catch（零退化）"


# ---------- 非重疊守門（DEF-18-001 核心意圖）：9.7.3 路徑不歸因 R-9.7 ----------

def test_r97_not_attributed_on_auto_compact_overflow(tmp_path, monkeypatch, _w37_rules):
    """flag ON：走 9.7.3（AUTO_COMPACT per-stage 超限）escalate 路徑 → 只 R-9.2 catch+1，
    R-9.7 catch 恆 0。鎖死「R-9.7 failure_mode 僅涵蓋 9.7.2、不搭便車 trigger_auto_compact」
    的無歧義映射意圖（DEF-18-001 寧缺勿濫，防雙重歸因污染 ROI）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt(tmp_path, "INIT")
    res = _drive_auto_compact_overflow(rt)
    assert res.get("escalated") is True, "per-stage 超限必 escalate（既有不變式）"
    assert rt.state.current == "ESCALATION"
    assert _catch_count(_w37_rules, "R-9.2") == 1, "9.7.3 路徑歸 R-9.2（trigger_auto_compact）"
    assert _catch_count(_w37_rules, "R-9.7") == 0, "R-9.7 不得在 auto_compact 路徑被歸因（非重疊）"


# ---------- 真實凍結 governance：R-9.7 已自描述 failure_mode ----------

def test_real_rule_r97_has_failure_mode():
    """凍結本體 R-9.7 必須自描述非空 failure_mode（要件①），否則生產環境 HUMAN_PENDING
    逾時 escalate 分支即便 flag ON 也因 fail-closed 而不記 catch（covering DEF-19-001）。"""
    doc = yaml.safe_load(
        (_REAL_RULES_DIR / "R-9.7-precise-halt-m1.yaml").read_text(encoding="utf-8")
    )
    assert doc.get("failure_mode", "").strip(), "R-9.7 須具非空 failure_mode（catch 可歸因）"
