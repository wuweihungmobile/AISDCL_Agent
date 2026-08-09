# enforces (governance rules): R-9.24
"""Phase L M-L1 / ACT-089~090 — Meta-Loop Halting 回歸守門.

涵蓋：
  - ACT-089 Meta-Loop Ledger：churn 計數、再採納偵測、capability 追蹤、指紋
  - ACT-090 Meta-Halt Monitor：ChurnBounded / GraduationRatchet 兩道有界停機守門
  - ACT-090 META_FSM.tla：離線可達性 BFS（reachable=N/N + 每態可達 terminal）、
    雙源狀態一致（.tla ↔ meta_halt_monitor.META_STATES）、cfg invariant/property 宣告
  - opt-in 完整 TLC 窮舉（SDD_RUN_TLC=1）
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tools.fsm_runtime.meta_halt import meta_ledger as L
from tools.fsm_runtime.meta_halt import meta_halt_monitor as M

ROOT = Path(__file__).resolve().parent.parent
META_TLA = ROOT / "formal" / "META_FSM.tla"
META_CFG = ROOT / "formal" / "META_FSM.cfg"


# ---------------------------------------------------------------------------
# ACT-089 — Meta-Loop Ledger
# ---------------------------------------------------------------------------


def _ledger(tmp_path: Path) -> Path:
    return tmp_path / "meta-loop-ledger.yaml"


def test_fingerprint_collapses_semantic_variants():
    """語意同型（換皮重學）的規則應收斂到同一指紋。"""
    a = L.fingerprint_of("AC P95 latency exceeded 200ms at concurrency 100")
    b = L.fingerprint_of("AC P95 latency > 200ms at concurrency 100")
    assert a == b and a != ""


def test_empty_ledger_zero_churn(tmp_path):
    p = _ledger(tmp_path)
    assert L.compute_churn("fp-x", ledger_path=p) == 0
    assert L.is_readopt("fp-x", ledger_path=p) is False


def test_single_add_is_not_readopt(tmp_path):
    p = _ledger(tmp_path)
    L.record_event(L.EVENT_ADD, "SLV-100", fingerprint="fp-a", capability_level=0, ledger_path=p)
    assert L.compute_churn("fp-a", ledger_path=p) == 0
    assert L.is_readopt("fp-a", ledger_path=p) is False


def test_add_then_retire_zero_churn_then_readopt_pending(tmp_path):
    p = _ledger(tmp_path)
    L.record_event(L.EVENT_ADD, "SLV-100", fingerprint="fp-a", capability_level=0, ledger_path=p)
    L.record_event(L.EVENT_RETIRE, "SLV-100", fingerprint="fp-a", capability_level=0, ledger_path=p)
    assert L.compute_churn("fp-a", ledger_path=p) == 0  # 僅退役，尚未再採納
    assert L.is_readopt("fp-a", ledger_path=p) is True  # 下一次 add 將構成再採納
    assert L.last_retire_capability("fp-a", ledger_path=p) == 0


def test_readopt_increments_churn(tmp_path):
    p = _ledger(tmp_path)
    L.record_event(L.EVENT_ADD, "SLV-100", fingerprint="fp-a", capability_level=0, ledger_path=p)
    L.record_event(L.EVENT_RETIRE, "SLV-100", fingerprint="fp-a", capability_level=0, ledger_path=p)
    L.record_event(L.EVENT_ADD, "SLV-101", fingerprint="fp-a", capability_level=1, ledger_path=p)
    assert L.compute_churn("fp-a", ledger_path=p) == 1


def test_three_synthetic_jitter_sequences_detected(tmp_path):
    """ACT-089 驗收：3 條人工合成 add↔retire 抖動序列，churn 應 ≥ 2。"""
    for i in range(3):
        p = tmp_path / f"jitter-{i}.yaml"
        fp = f"fp-jitter-{i}"
        # add → retire → add → retire → add  ⇒ 2 次再採納
        L.record_event(L.EVENT_ADD, f"R{i}a", fingerprint=fp, capability_level=0, ledger_path=p)
        L.record_event(L.EVENT_RETIRE, f"R{i}a", fingerprint=fp, capability_level=0, ledger_path=p)
        L.record_event(L.EVENT_ADD, f"R{i}b", fingerprint=fp, capability_level=1, ledger_path=p)
        L.record_event(L.EVENT_RETIRE, f"R{i}b", fingerprint=fp, capability_level=1, ledger_path=p)
        L.record_event(L.EVENT_ADD, f"R{i}c", fingerprint=fp, capability_level=2, ledger_path=p)
        assert L.compute_churn(fp, ledger_path=p) == 2


def test_normal_monotone_sequences_zero_churn(tmp_path):
    """正常單調序列（純新增不同指紋）churn 恆 0，不誤判。"""
    p = _ledger(tmp_path)
    for n in range(17):
        L.record_event(L.EVENT_ADD, f"SLV-{200+n}", fingerprint=f"fp-fresh-{n}",
                       capability_level=0, ledger_path=p)
    for n in range(17):
        assert L.compute_churn(f"fp-fresh-{n}", ledger_path=p) == 0
    assert sorted(L.all_fingerprints(ledger_path=p)) == sorted(f"fp-fresh-{n}" for n in range(17))


def test_fitness_add_not_counted_as_rule_churn(tmp_path):
    p = _ledger(tmp_path)
    L.record_event(L.EVENT_FITNESS_ADD, "FF-16", fingerprint="fp-ff", ledger_path=p)
    L.record_event(L.EVENT_FITNESS_ADD, "FF-16", fingerprint="fp-ff", ledger_path=p)
    assert L.compute_churn("fp-ff", ledger_path=p) == 0


def test_invalid_event_type_rejected(tmp_path):
    p = _ledger(tmp_path)
    with pytest.raises(ValueError):
        L.record_event("bogus", "X", fingerprint="fp", ledger_path=p)


# ---------------------------------------------------------------------------
# ACT-090 — Meta-Halt Monitor（兩道有界停機守門）
# ---------------------------------------------------------------------------


def test_churn_max_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_META_CHURN_MAX", raising=False)
    assert M.churn_max() == 2
    monkeypatch.setenv("SDD_META_CHURN_MAX", "4")
    assert M.churn_max() == 4
    monkeypatch.setenv("SDD_META_CHURN_MAX", "99")
    assert M.churn_max() == 5   # clamp 上界
    monkeypatch.setenv("SDD_META_CHURN_MAX", "0")
    assert M.churn_max() == 1   # clamp 下界
    monkeypatch.setenv("SDD_META_CHURN_MAX", "garbage")
    assert M.churn_max() == 2   # 非數字 → 預設


def test_fresh_add_always_allowed(tmp_path):
    p = _ledger(tmp_path)
    r = M.guard_readopt("fp-new", capability_level=0, ledger_path=p)
    assert r.allowed and r.is_readopt is False


def test_readopt_with_capability_delta_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_META_CHURN_MAX", "2")
    p = _ledger(tmp_path)
    M.record_rule_add("SLV-100", "fp-a", 0, ledger_path=p)
    M.record_rule_retire("SLV-100", "fp-a", 0, ledger_path=p)
    # 再採納，capability 0→1（有 delta）→ 放行
    r = M.guard_readopt("fp-a", capability_level=1, ledger_path=p)
    assert r.allowed and r.is_readopt is True


def test_readopt_without_capability_delta_blocked(tmp_path):
    """GraduationRatchet（Rule 9.24.2）：再採納但 capability 未提升 → 拒絕。"""
    p = _ledger(tmp_path)
    M.record_rule_add("SLV-100", "fp-a", 1, ledger_path=p)
    M.record_rule_retire("SLV-100", "fp-a", 1, ledger_path=p)
    with pytest.raises(M.GraduationRatchetViolation):
        M.guard_readopt("fp-a", capability_level=1, ledger_path=p)   # 仍 1，無 delta
    with pytest.raises(M.GraduationRatchetViolation):
        M.guard_readopt("fp-a", capability_level=0, ledger_path=p)   # 退步更糟


def test_churn_bound_exceeded_blocks(tmp_path, monkeypatch):
    """ChurnBounded（Rule 9.24.1）：churn 達上限後再採納 → 拒絕，導 ESCALATION。"""
    monkeypatch.setenv("SDD_META_CHURN_MAX", "2")
    p = _ledger(tmp_path)
    # 製造 churn=2 的序列（add→retire→add→retire→add，每次 readopt 帶 cap-delta）
    M.record_rule_add("R-a", "fp-z", 0, ledger_path=p)
    M.record_rule_retire("R-a", "fp-z", 0, ledger_path=p)
    M.record_rule_add("R-b", "fp-z", 1, ledger_path=p)        # readopt #1（churn→1）
    M.record_rule_retire("R-b", "fp-z", 1, ledger_path=p)
    M.record_rule_add("R-c", "fp-z", 2, ledger_path=p)        # readopt #2（churn→2）
    M.record_rule_retire("R-c", "fp-z", 2, ledger_path=p)
    assert L.compute_churn("fp-z", ledger_path=p) == 2
    # 第三次再採納 → churn 已達上限 2 → ChurnBoundExceeded
    with pytest.raises(M.ChurnBoundExceeded):
        M.record_rule_add("R-d", "fp-z", 3, ledger_path=p)


def test_record_rule_add_routes_block_before_persist(tmp_path):
    """守門拋出時不得落盤該 add（避免帳本被污染）。"""
    p = _ledger(tmp_path)
    M.record_rule_add("R-a", "fp-q", 1, ledger_path=p)
    M.record_rule_retire("R-a", "fp-q", 1, ledger_path=p)
    before = len(L.load_ledger(p)["events"])
    with pytest.raises(M.GraduationRatchetViolation):
        M.record_rule_add("R-b", "fp-q", 1, ledger_path=p)
    after = len(L.load_ledger(p)["events"])
    assert after == before  # 被拒的 add 未落盤


def test_meta_state_classifier(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_META_CHURN_MAX", "2")
    p = _ledger(tmp_path)
    assert M.meta_state(ledger_path=p) == "MFSM_OBSERVE"      # 空帳本
    M.record_rule_add("R-a", "fp-s", 0, ledger_path=p)
    assert M.meta_state(ledger_path=p) == "MFSM_STABLE"        # 有事件、未觸頂
    assert M.classify_transition(L.EVENT_ADD) == "MFSM_GROW"
    assert M.classify_transition(L.EVENT_RETIRE) == "MFSM_SHRINK"


def test_meta_state_escalation_when_churn_topped(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_META_CHURN_MAX", "2")
    p = _ledger(tmp_path)
    # 直接落盤一條 churn=2 的序列（繞過 monitor 模擬歷史狀態）
    L.record_event(L.EVENT_ADD, "R-a", fingerprint="fp-e", capability_level=0, ledger_path=p)
    L.record_event(L.EVENT_RETIRE, "R-a", fingerprint="fp-e", capability_level=0, ledger_path=p)
    L.record_event(L.EVENT_ADD, "R-b", fingerprint="fp-e", capability_level=1, ledger_path=p)
    L.record_event(L.EVENT_RETIRE, "R-b", fingerprint="fp-e", capability_level=1, ledger_path=p)
    L.record_event(L.EVENT_ADD, "R-c", fingerprint="fp-e", capability_level=2, ledger_path=p)
    assert M.meta_state(ledger_path=p) == "MFSM_ESCALATION"


# ---------------------------------------------------------------------------
# ACT-090 — META_FSM.tla 形式化（離線 BFS + 雙源一致）
# ---------------------------------------------------------------------------


def _read_meta_tla() -> str:
    return META_TLA.read_text(encoding="utf-8")


def _named_sets(tla: str) -> dict:
    out: dict = {}
    for m in re.finditer(r"^([A-Z][A-Za-z_]*)\s*==\s*\{([^}]*)\}", tla, re.MULTILINE):
        items = re.findall(r'"([A-Z_]+)"', m.group(2))
        if items:
            out[m.group(1)] = set(items)
    return out


def _meta_pairs(tla: str) -> set:
    """從含 `mstate' = "DST"` 的 action 區塊抽 (src, dst) pair。"""
    sets = _named_sets(tla)
    pairs: set = set()
    block_re = re.compile(
        r"^([A-Z][A-Za-z_]*)\s*==\s*((?:.|\n)*?)(?=\n[A-Z][A-Za-z_]*\s*==|\n====|\Z)",
        re.MULTILINE,
    )
    for m in block_re.finditer(tla):
        body = m.group(2)
        dst_m = re.search(r"mstate'\s*=\s*\"([A-Z_]+)\"", body)
        if not dst_m:
            continue
        dst = dst_m.group(1)
        srcs: set = set()
        # 單值 guard：mstate = "X"（排除 mstate'）
        for g in re.finditer(r"(?<!')\bmstate\s*=\s*\"([A-Z_]+)\"", body):
            srcs.add(g.group(1))
        # 集合 guard：mstate \in { ... }
        for g in re.finditer(r"mstate\s*\\in\s*\{([^}]*)\}", body):
            srcs |= set(re.findall(r'"([A-Z_]+)"', g.group(1)))
        # 具名集合 guard：mstate \in NamedSet
        for g in re.finditer(r"mstate\s*\\in\s*([A-Z][A-Za-z_]*)", body):
            srcs |= sets.get(g.group(1), set())
        for s in srcs:
            pairs.add((s, dst))
    return pairs


def test_meta_fsm_states_match_python():
    """雙源一致（Rule 9.24.3 精神）：.tla MetaStates ↔ monitor.META_STATES。"""
    sets = _named_sets(_read_meta_tla())
    assert sets.get("MetaStates") == set(M.META_STATES)
    assert sets.get("MetaTerminals") == set(M.META_TERMINALS)


def test_meta_fsm_all_states_reachable_offline():
    """從 MFSM_OBSERVE BFS 必達所有宣告狀態（reachable=N/N，無死狀態）。"""
    tla = _read_meta_tla()
    pairs = _meta_pairs(tla)
    declared = _named_sets(tla)["MetaStates"]
    fwd: dict = {}
    for s, d in pairs:
        fwd.setdefault(s, set()).add(d)
    seen = {"MFSM_OBSERVE"}
    stack = ["MFSM_OBSERVE"]
    while stack:
        for nxt in fwd.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    dead = declared - seen
    assert not dead, f"META_FSM reachable < 100%：死狀態 {sorted(dead)}"


def test_meta_fsm_every_state_reaches_terminal_offline():
    """反向 BFS 自 {STABLE, ESCALATION}：所有狀態皆可抵達 terminal（EventuallyMetaStable 結構必要條件）。"""
    tla = _read_meta_tla()
    pairs = _meta_pairs(tla)
    sets = _named_sets(tla)
    declared = sets["MetaStates"]
    terminals = sets["MetaTerminals"]
    rev: dict = {}
    for s, d in pairs:
        rev.setdefault(d, set()).add(s)
    can_reach = set(terminals)
    stack = list(terminals)
    while stack:
        for prv in rev.get(stack.pop(), ()):
            if prv not in can_reach:
                can_reach.add(prv)
                stack.append(prv)
    stuck = declared - can_reach
    assert not stuck, f"無法抵達 terminal 的狀態（潛在無界 churn）：{sorted(stuck)}"


def test_meta_fsm_cfg_declares_invariants_and_liveness():
    cfg = META_CFG.read_text(encoding="utf-8")
    for inv in ("TypeOK", "ChurnBounded", "GraduationRatchet", "ReadoptGated",
                "StableIsFixpoint"):
        assert inv in cfg, f"META_FSM.cfg 缺 INVARIANT {inv}"
    assert "EventuallyMetaStable" in cfg, "META_FSM.cfg 缺 liveness PROPERTY"


def test_meta_fsm_cfg_declares_stable_is_fixpoint():
    """缺口 2：META_FSM.cfg 的 INVARIANT 區塊須含 StableIsFixpoint（藍圖 §2.2/§3.1 字面）。"""
    cfg = META_CFG.read_text(encoding="utf-8")
    assert "StableIsFixpoint" in cfg, "META_FSM.cfg 缺 INVARIANT StableIsFixpoint"
    tla = _read_meta_tla()
    assert "StableIsFixpoint ==" in tla, "META_FSM.tla 缺 StableIsFixpoint 定義"


@pytest.mark.tlc
def test_meta_fsm_tlc_full_verification_opt_in():
    """完整 TLC 窮舉 META_FSM（5 safety + 1 liveness）。需 SDD_RUN_TLC=1 + java + jar。"""
    if os.environ.get("SDD_RUN_TLC") != "1":
        pytest.skip("[ENV-DISABLED] 未啟用五軌 TLA+/TLC 窮舉（set SDD_RUN_TLC=1）——**未啟用，非缺件**："
            "本機實查 java 與 tools/fsm_runtime/formal/lib/tla2tools.jar 都在，接上後實跑 "
            "`33 passed in 304.36s`（R82 實測）。304 秒不該進 PR fast gate，而本 repo **目前**"
            "沒有任何自動通道跑它（實查 .github/workflows 與 run_local_nightly.* 對 SDD_RUN_TLC "
            "零命中）⇒ 這是誠實的零覆蓋，不是「等 nightly」。承接輪次 R83：建 nightly 的 "
            "sdd-tlc stage（比照既有 sdd-chaos stage 的接法）。離線可達性不變量仍常駐守門")
    from tools.fsm_runtime import tlc_runner as T
    if T.find_java() is None or not T.jar_path().exists():
        pytest.skip("[TOOL-ABSENCE] java 或 tla2tools.jar 不存在——這一條是真缺件（與上面那條 ENV-DISABLED 不同軸）：裝 JDK 或跑 tools/fsm_runtime/formal/run_tlc.sh 讓它自動下載 jar")
    res = T.run_tlc(depth=50, tla="META_FSM.tla", cfg="META_FSM.cfg")
    assert res["ok"], f"META_FSM TLC 驗證失敗：{res.get('log_tail') or res.get('error')}"
    assert res["distinct"] > 0


# ---------------------------------------------------------------------------
# ACT-090 缺口 1 — meta_halt_monitor 接線到生產路徑（exit_learning_commit / set_maturity）
# ---------------------------------------------------------------------------


def _verified_rule_fixture(td: Path, slv_id: str = "SLV-777") -> Path:
    """approved 流程需要的 verified YAML fixture（與 test_slv_generator 同型）。"""
    import yaml as _yaml
    target = td / f"{slv_id}.yaml"
    doc = {
        "id": slv_id,
        "name": "fixture verified rule",
        "source": "FPL-001 auto-generated 2026-04-24",
        "trust_level": "verified",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-04-24",
        "scope": "temporal",
        "purpose": "test fixture",
        "scan_targets": ["docs/01_requirements/FRD-*.md"],
        "required_qualifiers": ["必須不為空"],
        "failure_examples": [],
        "pass_examples": [],
        "severity": "CRITICAL",
        "blocks_scg": True,
        "source_fpl": "FPL-001",
    }
    target.write_text(_yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
                      encoding="utf-8")
    return target


def _runtime_at_release(td: Path):
    from tools.fsm_runtime.state_loader import load_state, save_state
    from tools.fsm_runtime.fsm_runtime import FSMRuntime
    project = "meta-halt-wire-test"
    state_path = td / f"FSM-STATE-{project}.yaml"
    state = load_state(project, path=state_path, create_if_missing=True)
    state.root["current_state"] = "RELEASE"
    save_state(state)
    return FSMRuntime(state)


def _fixture_fingerprint() -> str:
    """生產接線對 fixture 推導的指紋（name + scope + purpose，刻意排除 id）。"""
    return L.fingerprint_of("fixture verified rule temporal test fixture")


def test_wiring_approved_exit_records_add_event(tmp_path, monkeypatch):
    """(a) approved exit_learning_commit 必在預設 ledger 落一筆 add 事件。"""
    ledger = tmp_path / "meta-loop-ledger.yaml"
    monkeypatch.setenv("SDD_META_LEDGER_PATH", str(ledger))
    rt = _runtime_at_release(tmp_path)
    rule_path = _verified_rule_fixture(tmp_path, "SLV-777")
    rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-777",
                             proposed_rule_path=str(rule_path))
    res = rt.exit_learning_commit("approved", reason="wire test")
    assert res["to"] == "RELEASE" and rt.state.current == "RELEASE"
    assert res["meta_halt"]["recorded"] is True
    events = L.load_ledger(ledger)["events"]
    adds = [e for e in events if e["event_type"] == L.EVENT_ADD]
    assert len(adds) == 1, f"approved exit 未落 add 事件：{events}"
    assert adds[0]["fingerprint"] == _fixture_fingerprint()
    assert adds[0]["source"] == "learning_layer"


def test_wiring_churn_jitter_routes_to_escalation(tmp_path, monkeypatch):
    """(b) 連續抖動序列觸 ChurnBounded → exit 導 ESCALATION（非 RELEASE）、不外炸。"""
    monkeypatch.setenv("SDD_META_CHURN_MAX", "2")
    ledger = tmp_path / "meta-loop-ledger.yaml"
    monkeypatch.setenv("SDD_META_LEDGER_PATH", str(ledger))
    fp = _fixture_fingerprint()
    # 預先把 ledger 灌到 churn == 2（add→retire→add→retire→add，每次 readopt 帶 cap-delta）。
    L.record_event(L.EVENT_ADD, "SLV-a", fingerprint=fp, capability_level=0, ledger_path=ledger)
    L.record_event(L.EVENT_RETIRE, "SLV-a", fingerprint=fp, capability_level=0, ledger_path=ledger)
    L.record_event(L.EVENT_ADD, "SLV-b", fingerprint=fp, capability_level=1, ledger_path=ledger)
    L.record_event(L.EVENT_RETIRE, "SLV-b", fingerprint=fp, capability_level=1, ledger_path=ledger)
    L.record_event(L.EVENT_ADD, "SLV-c", fingerprint=fp, capability_level=2, ledger_path=ledger)
    L.record_event(L.EVENT_RETIRE, "SLV-c", fingerprint=fp, capability_level=2, ledger_path=ledger)
    assert L.compute_churn(fp, ledger_path=ledger) == 2

    rt = _runtime_at_release(tmp_path)
    rule_path = _verified_rule_fixture(tmp_path, "SLV-777")  # 同語意 → 同指紋（換皮重學）
    rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-777",
                             proposed_rule_path=str(rule_path))
    res = rt.exit_learning_commit("approved", reason="jitter readopt")
    # 守門攔截 → 導 ESCALATION（結構性），例外不外炸破 FSM
    assert res["to"] == "ESCALATION" and rt.state.current == "ESCALATION"
    assert res["meta_halt"]["blocked"] is True
    assert res["meta_halt"]["violation"] == "ChurnBounded"
    # 被拒的 add 不得落盤（churn 維持 2）
    assert L.compute_churn(fp, ledger_path=ledger) == 2


def test_wiring_set_maturity_retire_records_retire_event(tmp_path, monkeypatch):
    """(c) set_maturity 退役方向（active→audit-only）在 ledger 落一筆 retire 事件。"""
    import yaml as _yaml
    from tools.fsm_runtime import rule_loader as RL
    ledger = tmp_path / "meta-loop-ledger.yaml"
    monkeypatch.setenv("SDD_META_LEDGER_PATH", str(ledger))
    rdir = tmp_path / "rules"
    rdir.mkdir()
    (rdir / "R-9.99-demo.yaml").write_text(_yaml.safe_dump({
        "id": "R-9.99", "title": "demo retire rule", "trigger_states": ["*"],
        "maturity": "active", "spec": "demo spec text",
        "scaffold_roi": {"fire_count": 0, "catch_count": 0, "false_positive_count": 0},
    }, allow_unicode=True), encoding="utf-8")

    r = RL.set_maturity("R-9.99", "audit-only", reviewed_by="human@x", rules_dir=rdir)
    assert r.maturity == "audit-only"
    events = L.load_ledger(ledger)["events"]
    retires = [e for e in events if e["event_type"] == L.EVENT_RETIRE]
    assert len(retires) == 1, f"退役未落 retire 事件：{events}"
    assert retires[0]["fingerprint"] == L.fingerprint_of("demo retire rule demo spec text")
    assert retires[0]["source"] == "scaffold_gc"


def test_wiring_set_maturity_to_active_records_no_retire(tmp_path, monkeypatch):
    """非退役方向（如維持/提升成熟度）不應落 retire 事件。"""
    import yaml as _yaml
    from tools.fsm_runtime import rule_loader as RL
    ledger = tmp_path / "meta-loop-ledger.yaml"
    monkeypatch.setenv("SDD_META_LEDGER_PATH", str(ledger))
    rdir = tmp_path / "rules"
    rdir.mkdir()
    (rdir / "R-9.98-demo.yaml").write_text(_yaml.safe_dump({
        "id": "R-9.98", "title": "stay active", "trigger_states": ["*"],
        "maturity": "audit-only", "spec": "x",
        "scaffold_roi": {"fire_count": 0, "catch_count": 0, "false_positive_count": 0},
    }, allow_unicode=True), encoding="utf-8")
    RL.set_maturity("R-9.98", "active", reviewed_by="human@x", rules_dir=rdir)  # 復職（非退役）
    events = L.load_ledger(ledger)["events"]
    assert not any(e["event_type"] == L.EVENT_RETIRE for e in events)
