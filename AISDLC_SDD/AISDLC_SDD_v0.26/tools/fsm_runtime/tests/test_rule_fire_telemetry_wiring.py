# enforces (governance rules): R-9.20
"""W-18-1 / W-18-2 — 規則命中遙測接入 FSM 主迴圈（B 軸 L4→L5 信號）測試。

驗證 improving_18：把 on-watch fire 記帳接入 transition() 主迴圈，flag-gated、fail-closed、
紅線守界（只增 fire_count 計數，active 規則退役仍 🔴 人工 set_maturity(reviewed_by=)）。閉合
DEF-17-001 點名的「fire_count=0」根因，使 GC 有非零資料可驅動退役提議。

improving_62（v0.24，B L5 telemetry 活體化）：flag 預設由 OFF 翻為 **ON**（unset → 進態即記
on-watch fire 活體；顯式 falsy=0/false/no/off → opt-out 還原 v0.08 不記 fire）。Case 1 改寫為
default-ON 活體驗收、Case 2 為顯式 opt-out 零退化守；紅線恆守（遙測永不 set_maturity）。
（測試套 conftest autouse 預設把兩 flag 設 "0" 保護凍結 governance；default-ON 案以 delenv 覆寫。）

每個 case 編碼「為何此行為重要」（Rule 9）：default-ON 活體自走（fire_count 真實累積）、顯式
opt-out 零退化、fail-closed 不阻塞轉態、R-9.20 #11 紅線遙測永不退役、L5 信號度量穩健、catch
側誠實揭露未接（DEF-18-001）。
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


def _write_rule(rules_dir: Path, rule_id: str, *, trigger_states, maturity="active",
                fire_count=0, catch_count=0) -> None:
    """寫一份最小合法 R-*.yaml 規則檔到 rules_dir（供遙測隔離測試，不污染框架真規則）。"""
    rules_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": rule_id,
        "title": f"synthetic {rule_id}",
        "trigger_states": list(trigger_states),
        "severity": "medium",
        "maturity": maturity,
        "spec": "synthetic test rule",
        "test_ref": "",
        "scaffold_roi": {
            "fire_count": fire_count, "catch_count": catch_count,
            "false_positive_count": 0,
        },
    }
    (rules_dir / f"{rule_id}.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@pytest.fixture
def _isolated_rules(tmp_path, monkeypatch):
    """把 rule_loader.RULES_DIR 導向 tmp，避免遙測寫入污染 v0.09 凍結 governance 規則。

    種子三規則：global（trigger '*'，任何轉態都命中）、SCENARIO_DETECT 專屬、
    SPEC_DRAFTING 專屬（轉到 SCENARIO_DETECT 時不該命中＝驗選擇性）。
    """
    rdir = tmp_path / "rules"
    _write_rule(rdir, "R-glob", trigger_states=["*"])
    _write_rule(rdir, "R-scn", trigger_states=["SCENARIO_DETECT"])
    _write_rule(rdir, "R-spec", trigger_states=["SPEC_DRAFTING"])
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _fire_count(rules_dir: Path, rule_id: str) -> int:
    doc = yaml.safe_load((rules_dir / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    return int(doc["scaffold_roi"]["fire_count"])


def _rt_in_init(tmp_path, name="ft18"):
    """建一個處 INIT 的 runtime（待測 transition INIT→SCENARIO_DETECT）。"""
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = "INIT"
    save_state(st)
    return FSMRuntime(st)


# ---------- Case 1：default ON（unset）= L5 活體自走（improving_62 翻環）----------

def test_default_on_transition_records_fire(tmp_path, monkeypatch, _isolated_rules):
    """改寫自 v0.23 Case 1（原斷言 delenv→fire 0）：v0.24 翻環後 unset = 預設 ON。

    為何重要（Rule 9 / R-62-1）：B L5 telemetry 活體化的**定義性驗收**——env 完全未設
    （production 常態）時，transition 進態即對命中規則記 on-watch fire（fire_count 真實累積），
    無需手動 opt-in。這是「遙測活體常態」相對 v0.23「opt-in 鷹架」的根本差異。
    （conftest autouse 預設把 flag 設 "0"；此處 delenv 覆寫回 unset 以驗預設 ON。）
    """
    monkeypatch.delenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", raising=False)  # 覆寫 conftest，unset = 預設 ON
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="t")
    assert rt.state.current == "SCENARIO_DETECT"
    assert _fire_count(_isolated_rules, "R-glob") == 1, "v0.24 預設 ON：unset 即記 fire（活體化）"
    assert _fire_count(_isolated_rules, "R-scn") == 1, "命中規則記 on-watch fire"
    assert _fire_count(_isolated_rules, "R-spec") == 0, "非命中狀態規則不得記（選擇性不變）"


# ---------- Case 2：顯式 opt-out（=0）= 還原 v0.08 不記 fire（零退化逃生閥）----------

def test_explicit_opt_out_records_no_fire(tmp_path, monkeypatch, _isolated_rules):
    """顯式 opt-out（flag='0'）= 還原 v0.08 不記 fire 行為（零退化逃生閥）。

    為何重要（Rule 9）：翻預設 ON 後仍須保留「顯式關閉即還原純轉態」的保守模式；flag=0 是唯一
    關閉開關（覆寫 v0.24 預設 ON）。
    """
    monkeypatch.setenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", "0")
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="t")
    assert _fire_count(_isolated_rules, "R-glob") == 0, "顯式 opt-out 不記 fire（零退化）"


# ---------- Case 3：flag ON = L5 自走（命中規則記 on-watch fire、選擇性）----------

def test_flag_on_transition_records_on_watch_fire(tmp_path, monkeypatch, _isolated_rules):
    """flag ON + transition→SCENARIO_DETECT：命中規則（glob + scn）各 fire+1，非命中（spec）不動。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="t")
    assert _fire_count(_isolated_rules, "R-glob") == 1, "global 規則任何轉態都命中"
    assert _fire_count(_isolated_rules, "R-scn") == 1, "SCENARIO_DETECT 專屬命中"
    assert _fire_count(_isolated_rules, "R-spec") == 0, "非命中狀態規則不得記 fire（選擇性）"


# ---------- Case 4：fire_count 真實累積並持久化（GAP-X2 fire 側閉合）----------

def test_flag_on_fire_count_accumulates_persisted(tmp_path, monkeypatch, _isolated_rules):
    """flag ON 多次轉態 → R-glob fire_count 累積且持久化（閉合 DEF-17-001 fire_count=0）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="1")
    rt.transition("AGENT_LOAD", reason="2")
    rt.transition("SPEC_DRAFTING", reason="3")
    # 三次轉態 global 規則命中 3 次；spec 規則只在進 SPEC_DRAFTING 命中 1 次
    assert _fire_count(_isolated_rules, "R-glob") == 3
    assert _fire_count(_isolated_rules, "R-spec") == 1


# ---------- Case 5：fail-closed（記帳失敗不阻塞已完成的轉態）----------

def test_telemetry_failure_fail_closed(tmp_path, monkeypatch, _isolated_rules):
    """flag ON + record_state_fires 拋例外 → fail-closed：轉態仍完成（已 save_state 落定）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", "1")

    def _boom(*a, **k):
        raise RuntimeError("synthetic telemetry failure")

    monkeypatch.setattr(rule_loader, "record_state_fires", _boom)
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="t")
    assert rt.state.current == "SCENARIO_DETECT", "fail-closed：記帳失敗不回滾轉態"


# ---------- Case 6：R-9.20 #11 紅線（遙測永不自動退役）----------

def test_red_line_telemetry_never_set_maturity(tmp_path, monkeypatch, _isolated_rules):
    """flag ON 全程零 set_maturity 呼叫：遙測只增計數，退役維持人工 gate（R-9.20 #11）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_FIRE_TELEMETRY", "1")
    calls = []
    real = rule_loader.set_maturity

    def _spy(*a, **k):
        calls.append((a, k))
        return real(*a, **k)

    monkeypatch.setattr(rule_loader, "set_maturity", _spy)
    rt = _rt_in_init(tmp_path)
    rt.transition("SCENARIO_DETECT", reason="t")
    assert calls == [], "遙測記帳路徑絕不可呼叫 set_maturity（退役須人工）"


# ---------- Case 7：rule_fire_telemetry_stats 度量穩健 + XAI 證書（誠實揭露 catch 未接）----------

def test_telemetry_stats_robust_and_certificate(tmp_path, monkeypatch, _isolated_rules):
    """純讀 stats：不報錯、auto_retire=False；W-19 起 catch_side_wired=True 且揭露
    catch_attribution_coverage（種子規則無 failure_mode → 覆蓋率 0，誠實反映 fail-closed）。"""
    rt = _rt_in_init(tmp_path)
    stats = rt.rule_fire_telemetry_stats()
    assert stats["rules_tracked"] >= 0
    assert isinstance(stats["fire_ladder"], list)
    assert stats["graduation_min_fires"] == rule_loader.GRADUATION_MIN_FIRES
    cert = stats["safety_certificate"]
    assert cert["auto_retire"] is False, "XAI 守界：遙測永不自動退役恆真"
    assert cert["catch_side_wired"] is True, "W-19：catch 側已接線（顯式可歸因，閉合 DEF-18-001）"
    cov = cert["catch_attribution_coverage"]
    assert cov["rules_with_failure_mode"] == 0, "種子規則皆無 failure_mode → 覆蓋率 0（fail-closed）"
    assert cov["attributed_rule_ids"] == []
    assert "set_maturity" in cert["human_gate"]


# ---------- Case 8：fire_ladder 降冪 + retirement_eligible 判定 ----------

def test_telemetry_stats_ladder_and_eligible(tmp_path, monkeypatch):
    """注入不同 fire/catch 規則 → fire_ladder 依 fire 降冪 + retirement_eligible（fire≥門檻∧catch=0）。"""
    rdir = tmp_path / "rules"
    threshold = rule_loader.GRADUATION_MIN_FIRES
    # R-hot：fire 達門檻、catch=0 → 退役候選；R-busy：fire 高但有 catch → 不候選；
    # R-cold：fire 低 → 不候選
    _write_rule(rdir, "R-hot", trigger_states=["*"], fire_count=threshold, catch_count=0)
    _write_rule(rdir, "R-busy", trigger_states=["*"], fire_count=threshold + 5, catch_count=3)
    _write_rule(rdir, "R-cold", trigger_states=["*"], fire_count=10, catch_count=0)
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    rt = _rt_in_init(tmp_path)
    stats = rt.rule_fire_telemetry_stats()
    fires = [row["fire_count"] for row in stats["fire_ladder"]]
    assert fires == sorted(fires, reverse=True), "fire_ladder 須降冪（行使最多排最前）"
    assert stats["fire_ladder"][0]["rule_id"] == "R-busy", "fire 最高排最前"
    assert "R-hot" in stats["retirement_eligible"], "fire≥門檻∧catch=0＝退役候選"
    assert "R-busy" not in stats["retirement_eligible"], "有 catch（高 ROI）不候選"
    assert "R-cold" not in stats["retirement_eligible"], "fire 未達門檻不候選"
    assert stats["total_fires"] == threshold + (threshold + 5) + 10
