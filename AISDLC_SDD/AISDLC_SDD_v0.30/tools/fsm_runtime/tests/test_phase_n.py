# enforces (governance rules): R-9.26
"""Phase N / ACT-105~108 — 全域組合最佳化 + NP-hard 搜尋形式化停機 回歸守門.

涵蓋：
  - ACT-105 Objective Scorer：成本函式（批次數主導 + 高價值早做）、feasibility、凍結版本
  - ACT-106 Composition Optimizer：bounded B&B 找已知最優、SearchBounded、deterministic、
    optimal/gap 誠實、預算耗盡無解→escalate
  - ACT-107 Optimization-Halt Monitor + OPTIMIZATION_FSM.tla：guard_expand、opt_state；
    離線 BFS（reachable=N/N + 每態可達 terminal）、雙源狀態一致、cfg invariant/property 宣告
  - ACT-108 steersman 整合（最優排程建議 advisory）
  - opt-in 完整 TLC（SDD_RUN_TLC=1）
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tools.fsm_runtime import composition_objective_scorer as OS
from tools.fsm_runtime import composition_optimizer as OPT
from tools.fsm_runtime import optimization_halt_monitor as OM

ROOT = Path(__file__).resolve().parent.parent
OPT_TLA = ROOT / "formal" / "OPTIMIZATION_FSM.tla"
OPT_CFG = ROOT / "formal" / "OPTIMIZATION_FSM.cfg"


# ---------------------------------------------------------------------------
# ACT-105 — Objective Scorer
# ---------------------------------------------------------------------------


def test_fewer_batches_lower_cost():
    vals = {"A": 1.0, "B": 1.0, "C": 1.0}
    one = OS.score_schedule([["A", "B", "C"]], vals)
    three = OS.score_schedule([["A"], ["B"], ["C"]], vals)
    assert one < three


def test_high_value_early_lower_cost():
    vals = {"A": 3.0, "B": 1.0}
    early = OS.score_schedule([["A"], ["B"]], vals)   # 高價值 A 在前
    late = OS.score_schedule([["B"], ["A"]], vals)    # 高價值 A 在後 → 較貴
    assert early < late


def test_is_feasible_respects_k_and_conflicts():
    p = OS.OptProblem(values={"A": 1, "B": 1, "C": 1},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    assert OS.is_feasible([["A", "C"], ["B"]], p)          # 合法
    assert not OS.is_feasible([["A", "B"], ["C"]], p)      # A,B 衝突同批
    assert not OS.is_feasible([["A", "B", "C"]], p)        # 超 K
    assert not OS.is_feasible([["A"], ["B"]], p)           # 漏 C


def test_objective_profile_version_frozen():
    assert OS.OBJECTIVE_PROFILE_VERSION == "v1.0"


def test_lower_bound_batches():
    p = OS.OptProblem(values={"A": 1, "B": 1, "C": 1, "D": 1}, max_parallel=2)
    assert OS.lower_bound_batches(p) == 2   # ceil(4/2)


# ---------------------------------------------------------------------------
# ACT-106 — Composition Optimizer（bounded B&B）
# ---------------------------------------------------------------------------


def test_optimizer_finds_known_optimal():
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    r = OPT.optimize(p, node_budget=256)
    assert r.feasible and r.optimal
    assert len(r.schedule) == 2            # 最優 = 2 批（A,B 須分批）
    assert r.best_cost == 2.2              # {A,C},{B}: 2*1 + 0.1*(1*2)=2.2
    assert OS.is_feasible(r.schedule, p)


def test_optimizer_is_search_bounded():
    p = OS.OptProblem(values={x: 1.0 for x in "ABCDEF"}, max_parallel=3)
    r = OPT.optimize(p, node_budget=20)
    assert r.nodes_expanded <= 20          # SearchBounded 硬上限


def test_optimizer_deterministic():
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    r1 = OPT.optimize(p, node_budget=256)
    r2 = OPT.optimize(p, node_budget=256)
    assert r1.schedule == r2.schedule and r1.best_cost == r2.best_cost


def test_optimizer_escalates_when_budget_too_small():
    """預算內找不到任何完整可行排程 → escalated（OPT_ESCALATION）。"""
    p = OS.OptProblem(values={x: 1.0 for x in "ABCD"}, max_parallel=4)
    r = OPT.optimize(p, node_budget=1)
    assert r.escalated and not r.feasible and r.schedule is None
    assert r.nodes_expanded <= 1


def test_optimizer_budget_limited_is_bounded_and_honest():
    """預算受限時：node 展開必有界，且結果誠實（escalate 或 best-so-far，Rule 9.26.1/9.26.5）。"""
    p = OS.OptProblem(values={x: 1.0 for x in "ABCDE"}, max_parallel=5)
    r = OPT.optimize(p, node_budget=3)
    assert r.nodes_expanded <= 3                          # SearchBounded
    assert r.escalated or (r.feasible and not r.optimal)  # 誠實：非謊報 proven-optimal


def test_optimizer_optimal_implies_consistent_flags():
    """optimal=True ⟹ feasible 且非 escalated（旗標自洽，Rule 9.26.5 誠實）。"""
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    r = OPT.optimize(p, node_budget=256)
    assert (not r.optimal) or (r.feasible and not r.escalated)


def test_optimizer_empty_problem():
    r = OPT.optimize(OS.OptProblem(values={}), node_budget=256)
    assert r.feasible and r.optimal and r.schedule == [] and r.nodes_expanded == 0


def test_optimizer_gap_zero_when_optimal():
    """gap 語意（Rule 9.26.5）：optimal=True → gap=0（已證最優，非次優）。"""
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    r = OPT.optimize(p, node_budget=256)
    assert r.optimal and r.gap == 0.0


def test_optimizer_write_report(tmp_path):
    """§2 承諾產物：落盤 OPT-SCHEDULE-{date}.md（與 L/M 對稱）。"""
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    r = OPT.optimize(p, node_budget=256)
    path = OPT.write_report(r, out_dir=tmp_path, today="2026-06-03")
    assert path.exists() and "Composition Optimization" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ACT-107 — Optimization-Halt Monitor
# ---------------------------------------------------------------------------


def test_opt_node_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_OPT_NODE_BUDGET", raising=False)
    assert OM.opt_node_budget() == 256
    monkeypatch.setenv("SDD_OPT_NODE_BUDGET", "9999")
    assert OM.opt_node_budget() == 4096
    monkeypatch.setenv("SDD_OPT_NODE_BUDGET", "1")
    assert OM.opt_node_budget() == 8
    monkeypatch.setenv("SDD_OPT_NODE_BUDGET", "garbage")
    assert OM.opt_node_budget() == 256


def test_guard_expand_allows_and_blocks():
    assert OM.guard_expand(5, budget=10).allowed
    with pytest.raises(OM.SearchBudgetExceeded):
        OM.guard_expand(10, budget=10)


def test_opt_state_classifier():
    assert OM.opt_state(found=True, exhausted=False) == "OPT_SCHEDULED"
    assert OM.opt_state(found=True, exhausted=True) == "OPT_SCHEDULED"
    assert OM.opt_state(found=False, exhausted=True) == "OPT_ESCALATION"
    assert OM.opt_state(found=False, exhausted=False) == "OPT_EXPAND"


# ---------------------------------------------------------------------------
# ACT-107 — OPTIMIZATION_FSM.tla 形式化（離線 BFS + 雙源一致）
# ---------------------------------------------------------------------------


def _read_opt_tla() -> str:
    return OPT_TLA.read_text(encoding="utf-8")


def _named_sets(tla: str) -> dict:
    out: dict = {}
    for m in re.finditer(r"^([A-Z][A-Za-z_]*)\s*==\s*\{([^}]*)\}", tla, re.MULTILINE):
        items = re.findall(r'"([A-Z_]+)"', m.group(2))
        if items:
            out[m.group(1)] = set(items)
    return out


def _opt_pairs(tla: str) -> set:
    sets = _named_sets(tla)
    pairs: set = set()
    block_re = re.compile(
        r"^([A-Z][A-Za-z_]*)\s*==\s*((?:.|\n)*?)(?=\n[A-Z][A-Za-z_]*\s*==|\n====|\Z)",
        re.MULTILINE,
    )
    for m in block_re.finditer(tla):
        body = m.group(2)
        dst_m = re.search(r"ostate'\s*=\s*\"([A-Z_]+)\"", body)
        if not dst_m:
            continue
        dst = dst_m.group(1)
        srcs: set = set()
        for g in re.finditer(r"(?<!')\bostate\s*=\s*\"([A-Z_]+)\"", body):
            srcs.add(g.group(1))
        for g in re.finditer(r"ostate\s*\\in\s*\{([^}]*)\}", body):
            srcs |= set(re.findall(r'"([A-Z_]+)"', g.group(1)))
        for g in re.finditer(r"ostate\s*\\in\s*([A-Z][A-Za-z_]*)", body):
            srcs |= sets.get(g.group(1), set())
        for s in srcs:
            pairs.add((s, dst))
    return pairs


def test_optimization_fsm_states_match_python():
    sets = _named_sets(_read_opt_tla())
    assert sets.get("OptStates") == set(OM.OPTIMIZATION_STATES)
    assert sets.get("OptTerminals") == set(OM.OPTIMIZATION_TERMINALS)


def test_optimization_fsm_all_states_reachable_offline():
    tla = _read_opt_tla()
    pairs = _opt_pairs(tla)
    declared = _named_sets(tla)["OptStates"]
    fwd: dict = {}
    for s, d in pairs:
        fwd.setdefault(s, set()).add(d)
    seen = {"OPT_OBSERVE"}
    stack = ["OPT_OBSERVE"]
    while stack:
        for nxt in fwd.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    dead = declared - seen
    assert not dead, f"OPTIMIZATION_FSM reachable < 100%：死狀態 {sorted(dead)}"


def test_optimization_fsm_every_state_reaches_terminal_offline():
    tla = _read_opt_tla()
    pairs = _opt_pairs(tla)
    sets = _named_sets(tla)
    declared = sets["OptStates"]
    terminals = sets["OptTerminals"]
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
    assert not stuck, f"無法抵達 terminal 的狀態（潛在無限搜尋）：{sorted(stuck)}"


def test_optimization_fsm_cfg_declares_invariants_and_liveness():
    cfg = OPT_CFG.read_text(encoding="utf-8")
    for inv in ("TypeOK", "SearchBounded", "ScheduledImpliesFound",
                "EscalationExhausted", "StableIsFixpoint"):
        assert inv in cfg, f"OPTIMIZATION_FSM.cfg 缺 INVARIANT {inv}"
    assert "EventuallyScheduled" in cfg, "OPTIMIZATION_FSM.cfg 缺 liveness PROPERTY"


def test_single_track_sdd_fsm_unaffected_by_optimization():
    sdd_tla = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "OPT_" not in sdd_tla, "OPTIMIZATION 狀態洩漏進單軌 SDD_FSM.tla（破 Rule 9.26.2）"


# ---------------------------------------------------------------------------
# ACT-108 — steersman 整合
# ---------------------------------------------------------------------------


def test_steersman_render_optimal_schedule():
    from tools.fsm_runtime.steersman_renderer import render_optimal_schedule
    p = OS.OptProblem(values={"A": 3.0, "B": 2.0, "C": 1.0},
                      conflict_edges={frozenset({"A", "B"})}, max_parallel=2)
    md = render_optimal_schedule(p, node_budget=256)
    assert "Composition Optimization" in md and "BACKLOG_PRIORITIZED" in md


def test_steersman_render_escalation():
    from tools.fsm_runtime.steersman_renderer import render_optimal_schedule
    p = OS.OptProblem(values={x: 1.0 for x in "ABCD"}, max_parallel=4)
    md = render_optimal_schedule(p, node_budget=1)
    assert "OPT_ESCALATION" in md


# ---------------------------------------------------------------------------
# ACT-107 — opt-in 完整 TLC
# ---------------------------------------------------------------------------


@pytest.mark.tlc
def test_optimization_fsm_tlc_full_verification_opt_in():
    """完整 TLC 窮舉 OPTIMIZATION_FSM（5 safety + 1 liveness）。需 SDD_RUN_TLC=1 + java + jar。"""
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
    res = T.run_tlc(depth=50, tla="OPTIMIZATION_FSM.tla", cfg="OPTIMIZATION_FSM.cfg")
    assert res["ok"], f"OPTIMIZATION_FSM TLC 驗證失敗：{res.get('log_tail') or res.get('error')}"
    assert res["distinct"] > 0
