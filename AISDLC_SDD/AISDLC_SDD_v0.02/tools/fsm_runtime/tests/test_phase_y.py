"""Phase Y / ACT-159~161 — meta⁸ 互遞迴呼叫圖人類視覺化儀表板（VisualizationBounded）回歸測試.

對應藍圖：build/planning/active/SDD_improving_Automation_26.md
對應規則：CLAUDE.md Rule 9.37 / formal/META_FSM.tla VisualizationBounded

涵蓋：
  - ACT-159：META_FSM 補 VisualizationBounded 不變量（不增軸、不增狀態變數、13 distinct 不回歸）。
  - ACT-160：recursion_topology_view（PY-1 AST 同構投影 + PY-2 拓樸防偽 + PY-3 有界渲染 + 接地 fail-closed
            + 對抗分離）+ guard_visualization_bounded fail-closed ↔ TLA+ 100% 同構。
  - ACT-161：chaos VISUALIZATION_FLAP / VISUALIZATION_TOPOLOGY_DRIFT_FLAP + steersman dashboard + 治理。
"""
from __future__ import annotations

# enforces (governance rules): R-9.37

import ast
import copy
from pathlib import Path

import pytest

from tools.fsm_runtime import recursion_topology_view as V
from tools.fsm_runtime import output_quality_scorer as OQS
from tools.fsm_runtime import embodied_grounding_oracle as EG
from tools.fsm_runtime.operator_recursion_genesis import RecursiveOperator
from tools.fsm_runtime.operator_genesis import GenesisOperator
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM

ROOT = Path(__file__).resolve().parents[1]   # tools/fsm_runtime/


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
def _fan_op():
    """entry(rank1) 同時呼叫 3 個 sink(rank0)：分支呼叫圖（Phase V 線性鏈表達不出）。"""
    return RecursiveOperator.fan(GenesisOperator.of("sum", "sq"), 3, combine="mul")


def _chain_op(k=4):
    return RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), k, combine="mul")


def _grounded_pass():
    obs = OQS.ExecutionObservation(tests_total=10, tests_passed=10)
    return EG.evaluate_embodied_grounding(obs, obs)


# ---------------------------------------------------------------------------
# ACT-160 — PY-1 AST 同構投影 + critical path
# ---------------------------------------------------------------------------
def test_extract_topology_projects_to_dict_isomorphic():
    op = _fan_op()
    od = op.to_dict()
    view = V.extract_topology(od)
    assert view.n_total_nodes == od["n_nodes"]
    assert len(view.nodes) == od["n_nodes"]            # 4 nodes 全在窗內（<= node_budget）
    assert len(view.edges) == sum(len(c) for _, c in od["edges"])
    # rank 投影與 to_dict() 一致（不獨立再推導）。
    assert [n.rank for n in sorted(view.nodes, key=lambda x: x.id)] == od["ranks"]


def test_critical_path_marks_max_fuel_node():
    """fan hub（呼叫最多 callee）= 消耗最多 fuel 的算子 → 🔴 critical。"""
    view = V.extract_topology(_fan_op().to_dict())
    crit = [n for n in view.nodes if n.critical]
    assert len(crit) == 1
    assert crit[0].id == view.critical_path.max_fuel_node == 0   # entry 是 fan hub
    assert view.critical_path.fuel_at_node == 4                  # 1 base + 3 callee


def test_edge_rank_decrement_marks_well_founded():
    view = V.extract_topology(_chain_op(4).to_dict())
    assert view.edges, "chain 應有呼叫邊"
    for e in view.edges:
        assert e.rank_decrement > 0 and e.well_founded   # 嚴格遞減 rank ⇒ 良基


def test_break_point_explains_counter_forced_halt():
    """fuel 歸零 / rank→0 的終止判讀人類可讀。"""
    view = V.extract_topology(_chain_op(4).to_dict())
    assert "rank→" in view.critical_path.break_point or "fuel" in view.critical_path.break_point


# ---------------------------------------------------------------------------
# ACT-160 — PY-3 有界渲染（bulletproof：10⁶ 節點不卡死/不 OOM/不超 char_budget）
# ---------------------------------------------------------------------------
def test_render_bounded_under_char_budget():
    view = V.extract_topology(_fan_op().to_dict())
    md = V.render_dashboard_markdown(view)
    assert len(md) <= view.budget.char_budget


def test_bulletproof_million_node_graph_bounded_truncated():
    """10⁶ 節點對抗圖：只讀窗格切片 → 渲染 <= node_budget、輸出 <= char_budget、truncated。"""
    big = {"ranks": [0] * 1_000_000, "edges": [], "fuel": 4, "entry": 0,
           "name": "adv", "fingerprint": "recursion-genesis:adv",
           "terminating": True, "acyclic": True, "well_founded": True}
    view = V.extract_topology(big)
    md = V.render_dashboard_markdown(view)
    assert len(view.nodes) <= view.budget.node_budget
    assert view.truncated is True
    assert view.total_pages > 1
    assert len(md) <= view.budget.char_budget


def test_render_budget_env_clamped(monkeypatch):
    monkeypatch.setenv("SDD_VIZ_NODE_BUDGET", "999999")   # 超界 → clamp
    monkeypatch.setenv("SDD_VIZ_CHAR_BUDGET", "1")        # 低於下界 → clamp 至 1000
    b = V.render_budget()
    assert b.node_budget <= 256
    assert b.char_budget >= 1000


# ---------------------------------------------------------------------------
# ACT-160 — PY-2 拓樸防偽（verify_topology_consistency：畫的圖 == 跑的圖）
# ---------------------------------------------------------------------------
def test_verify_consistency_passes_for_faithful_render():
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    assert V.verify_topology_consistency(rj, od) is True


def test_verify_rejects_dropped_edge_visual_deception():
    """畫的圖比跑的簡單（刪窗內真相邊）→ fail-closed。"""
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    forged = copy.deepcopy(rj)
    forged["edges"] = forged["edges"][1:]
    forged["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(forged, od)


def test_verify_rejects_faked_rank():
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    forged = copy.deepcopy(rj)
    forged["nodes"][0]["rank"] = 999
    forged["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(forged, od)


def test_verify_rejects_dropped_node_simpler_graph():
    """QA M-1：丟節點 / 縮窗（畫的圖比跑的簡單，謊稱算子更小）→ 窗格錨定 fail-closed。"""
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    forged = copy.deepcopy(rj)
    forged["nodes"] = [n for n in forged["nodes"] if n["id"] != 3]   # 丟掉 node3
    forged["edges"] = [e for e in forged["edges"] if e["dst"] != 3]  # 連同邊 (0,3)
    forged["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(forged, od)


def test_verify_rejects_empty_render_for_nonempty_op():
    """QA M-1：什麼都不畫（空渲染）對非空算子 → 窗格錨定 fail-closed。"""
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    forged = copy.deepcopy(rj)
    forged["nodes"] = []
    forged["edges"] = []
    forged["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(forged, od)


def test_verify_rejects_forged_budget_cursor_window_shrink():
    """QA 對抗複驗 BYPASS-1/2/3+：攻擊者同步偽造 render_budget.node_budget / page.cursor / n_total_nodes /
    truncated 使自報窗格自洽縮空（把 4 節點 fan hub 偽裝成 2 節點/空的完整小圖）——窗格錨定改只採信任來源
    （op_dict + 服務端權威 budget），全部 fail-closed。"""
    op = _fan_op()
    od = op.to_dict()            # 真實 4 節點 fan hub
    rj = V.render_json(V.extract_topology(od))

    # BYPASS-1：偽造 cursor=99 + 空渲染（自報窗格 range(2376,4)=∅）。
    b1 = copy.deepcopy(rj)
    b1["nodes"] = []; b1["edges"] = []; b1["page"]["cursor"] = 99
    b1["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(b1, od)

    # BYPASS-2：偽造 node_budget=4 + cursor=2（自報窗格 range(8,4)=∅）+ 空渲染。
    b2 = copy.deepcopy(rj)
    b2["nodes"] = []; b2["edges"] = []
    b2["render_budget"]["node_budget"] = 4; b2["page"]["cursor"] = 2
    b2["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(b2, od)

    # BYPASS-3+（最嚴重）：偽造 node_budget=2/cursor=0/n_total_nodes=2/truncated=False，只畫 {0,1}
    # （謊稱「未截斷、僅 2 節點、1 頁」的完整小圖）。
    b3 = copy.deepcopy(rj)
    b3["nodes"] = [n for n in b3["nodes"] if n["id"] in (0, 1)]
    b3["edges"] = [e for e in b3["edges"] if e["dst"] in (0, 1)]
    b3["render_budget"]["node_budget"] = 2; b3["page"]["cursor"] = 0
    b3["n_total_nodes"] = 2; b3["truncated"] = False
    b3["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(b3, od)


def test_verify_faithful_render_passes_with_trusted_budget():
    """忠實渲染（含 guard 注入服務端權威 node_budget）不被誤殺。"""
    od = _fan_op().to_dict()
    rj = V.render_json(V.extract_topology(od))
    assert V.verify_topology_consistency(rj, od, node_budget=24) is True


def test_verify_rejects_fabricated_node():
    op = _fan_op()
    od = op.to_dict()
    rj = V.render_json(V.extract_topology(od))
    forged = copy.deepcopy(rj)
    forged["nodes"].append({"id": 9999, "base": "ghost", "rank": 0, "fuel_consumed": 1,
                            "calls": [], "visited": True, "critical": False, "entry": False})
    forged["consistency"]["audit_digest"] = None
    with pytest.raises(V.TopologyConsistencyError):
        V.verify_topology_consistency(forged, od)


# ---------------------------------------------------------------------------
# ACT-160 — 接地視圖 fail-closed（零觀測不 false-green）
# ---------------------------------------------------------------------------
def test_grounding_view_none_is_gray_placeholder():
    view = V.extract_topology(_fan_op().to_dict(), grounding=None)
    assert view.grounding.has_observation is False
    panel = V.render_grounding_panel(view)
    assert "灰佔位" in panel and "🟢" not in panel


def test_grounding_view_real_observation_renders_verdict():
    view = V.extract_topology(_fan_op().to_dict(), grounding=_grounded_pass())
    assert view.grounding.has_observation is True
    assert view.grounding.grounded_verdict == EG.GROUNDED_PASS


def test_grounding_inconclusive_no_false_green():
    obs = OQS.ExecutionObservation(tests_total=10, tests_passed=10)
    inconclusive = EG.evaluate_embodied_grounding(obs, OQS.ExecutionObservation())  # 零觀測
    view = V.extract_topology(_fan_op().to_dict(), grounding=inconclusive)
    assert view.grounding.has_observation is False
    assert "🟢" not in V.render_grounding_panel(view)


# ---------------------------------------------------------------------------
# ACT-160 — guard_visualization_bounded fail-closed ↔ TLA+ VisualizationBounded 100% 同構
# ---------------------------------------------------------------------------
def test_guard_allows_faithful_bounded_render():
    op = _fan_op()
    od = op.to_dict()
    view = V.extract_topology(od, grounding=_grounded_pass())
    res = MM.guard_visualization_bounded(view, od)
    assert res.allowed is True
    assert res.audit_ok is True


def test_guard_fail_closed_on_char_budget_escape():
    """(i) char_budget 逃逸（token 爆炸）→ raise VisualizationViolation。"""
    op = _fan_op()
    od = op.to_dict()
    tiny = V.RenderBudget(node_budget=24, edge_budget=48, depth_max=8, char_budget=1000)
    view = V.extract_topology(od, budget=tiny)
    # 人為把 char_budget 壓到極小（透過替換 budget）→ 渲染必超界。
    from dataclasses import replace
    view2 = replace(view, budget=V.RenderBudget(node_budget=24, edge_budget=48, depth_max=8, char_budget=10))
    with pytest.raises(MM.VisualizationViolation):
        MM.guard_visualization_bounded(view2, od)


def test_guard_fail_closed_on_topology_forgery():
    """(ii) 拓樸視覺欺騙 → guard 獨立重算攔下 → VisualizationViolation。"""
    op = _fan_op()
    od = op.to_dict()
    view = V.extract_topology(od)
    # 偽造 op_dict（讓 guard 重算的真相圖與 view 渲染不符：拔掉 entry 的 callee）。
    forged_od = copy.deepcopy(od)
    forged_od["edges"] = [[0, []]] + [[i, c] for i, c in forged_od["edges"][1:]]
    with pytest.raises(MM.VisualizationViolation):
        MM.guard_visualization_bounded(view, forged_od)


def test_guard_fail_closed_on_grounding_false_green():
    """(iii) 接地零觀測 false-green（grounded_pass 卻無觀測）→ raise。"""
    od = _fan_op().to_dict()
    forged_grounding = {"grounded_verdict": "grounded_pass", "observation": None}
    view = V.extract_topology(od, grounding=forged_grounding)
    with pytest.raises(MM.VisualizationViolation):
        MM.guard_visualization_bounded(view, od)


def test_guard_fail_closed_on_empty_dict_observation_false_green():
    """QA m-1：observation 為非 None 空 dict + grounded_pass（零訊號 false-green）→ has_observation False → raise。"""
    od = _fan_op().to_dict()
    forged_grounding = {"grounded_verdict": "grounded_pass", "observation": {}}
    view = V.extract_topology(od, grounding=forged_grounding)
    assert view.grounding.has_observation is False     # 空 dict 無實質訊號 → 不算客觀觀測
    with pytest.raises(MM.VisualizationViolation):
        MM.guard_visualization_bounded(view, od)


def test_guard_defense_in_depth_rejects_handcrafted_shrunk_view():
    """QA OBSERVATION 封死：繞過 extract_topology 手構惡意 TopologyView 謊報 n_total_nodes 小於 op_dict 真實
    （縮小算子隱藏節點）→ guard (0) 真實大小誠實 fail-closed。"""
    from dataclasses import replace
    od = _fan_op().to_dict()                 # 真實 4 節點 fan hub
    view = V.extract_topology(od)
    liar = replace(view, n_total_nodes=2)    # 謊稱算子只有 2 節點
    with pytest.raises(MM.VisualizationViolation):
        MM.guard_visualization_bounded(liar, od)


# ---------------------------------------------------------------------------
# ACT-160 — 對抗分離（recursion_topology_view 對 generator/oracle 不可見）+ guard 有界停機
# ---------------------------------------------------------------------------
def _imported_module_names(py_path: Path) -> set:
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[-1])
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names.add(mod.split(".")[-1])
            names.add(mod)
            for a in node.names:
                names.add(a.name)
    return names


_FORBIDDEN = {
    "operator_genesis", "operator_recursion_genesis", "operator_alphabet_genesis",
    "operator_depth_genesis", "dimension_semantics_synthesizer", "vocabulary_genesis",
    "dimension_necessity_oracle", "embodied_grounding_oracle",
}


def test_topology_view_adversarial_separation_no_generator_oracle_import():
    """Rule 9.37：recursion_topology_view 結構性不 import 任何 generator / oracle（純投影觀察者，AST 驗證）。"""
    leaked = _imported_module_names(ROOT / "recursion_topology_view.py") & _FORBIDDEN
    assert not leaked, f"視覺化模組不得 import generator/oracle（對抗分離），洩漏：{leaked}"


def test_guard_visualization_eval_path_no_while_no_recursion():
    """guard_visualization_bounded 求值路徑零 while / 零自呼叫（有界停機）。"""
    tree = ast.parse((ROOT / "meta_halt" / "meta_halt_monitor.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "guard_visualization_bounded":
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), "guard 不得含 while（有界停機）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != "guard_visualization_bounded", "guard 不得自呼叫"


def test_verify_consistency_no_while_no_recursion():
    """verify_topology_consistency 求值路徑零 while / 零自呼叫（有界停機）。"""
    tree = ast.parse((ROOT / "recursion_topology_view.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "verify_topology_consistency":
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != "verify_topology_consistency"


# ---------------------------------------------------------------------------
# ACT-159 — META_FSM 補 VisualizationBounded（不增軸 / 不增狀態變數 / 13 distinct 不回歸）
# ---------------------------------------------------------------------------
def test_meta_fsm_declares_visualization_invariant():
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "VisualizationBounded ==" in tla
    assert "VisualizationBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state_phase_y():
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track_phase_y():
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_visualization_leak():
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "VisualizationBounded" not in sdd and "visualization" not in sdd.lower()


# ---------------------------------------------------------------------------
# ACT-161 — chaos + steersman + 治理
# ---------------------------------------------------------------------------
def test_chaos_registers_visualization_flaps():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "VISUALIZATION_FLAP" in FAULT_TYPES
    assert "VISUALIZATION_TOPOLOGY_DRIFT_FLAP" in FAULT_TYPES


def test_chaos_visualization_flap_is_bounded():
    from tools.fsm_runtime.chaos_runner import _visualization_flap_is_bounded
    assert _visualization_flap_is_bounded() is True


def test_chaos_topology_drift_flap_is_bounded():
    from tools.fsm_runtime.chaos_runner import _visualization_topology_drift_flap_is_bounded
    assert _visualization_topology_drift_flap_is_bounded() is True


def test_steersman_renders_topology_dashboard():
    from tools.fsm_runtime import steersman_renderer as SR
    assert hasattr(SR, "render_recursion_topology_dashboard")
    view = V.extract_topology(_fan_op().to_dict(), grounding=_grounded_pass())
    md = SR.render_recursion_topology_dashboard(view)
    assert "Recursion Topology Dashboard" in md and "read-only" in md


def test_r937_rule_yaml_exists_and_indexed():
    gov = ROOT.parent.parent / "governance"
    rule = gov / "rules" / "R-9.37-recursion-topology-visualization-phase-y.yaml"
    assert rule.exists(), "R-9.37 規則 yaml 須落地"
    idx = (gov / "RULES_INDEX.md").read_text(encoding="utf-8")
    assert "9.37" in idx


def test_id_registry_next_free_advanced_phase_y():
    """收官 ID 翻牌：Phase Y 持有 ACT-159~161；Phase Z（v0.02）已徵用 162~171，
    前緣現為 ACT-172 / R-9.39（Phase Y 證據改驗 range 持有而非前緣值）。"""
    reg = (ROOT.parent.parent / "governance" / "ID_REGISTRY.yaml").read_text(encoding="utf-8")
    assert "[159, 161]" in reg          # Phase Y 持有證據
    assert "act: 172" in reg            # Phase Z 推進後前緣
    assert '"9.39"' in reg
