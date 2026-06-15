"""W-14-2 測：meta⁸ 拓樸審批儀表板 surface 進 AutoClaude 人類審批介面。

對應 AutoSDD_improving_14.md A 軌 / RTM AT-14-2-*。

測試意圖（Rule 9）：橋接的價值＝「舵手在指揮官端 escalation 看得到那張已稽核的圖」，
且 fail-closed——未過稽核的圖**寧可不呈現**（advisory 吞例外回 ""），絕不盲簽端到舵手面前。
"""
from __future__ import annotations

import json
from pathlib import Path

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.ports.observability import NullObservability
from autoclaude.core.ports.topology_dashboard import canonical_graph_digest
from autoclaude.infra.adapters.sdd_topology_dashboard_adapter import (
    SddTopologyDashboardAdapter,
)
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin


class _SpyObs(NullObservability):
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


def _write_dashboard(workflow_path: Path, *, verified: bool = True, markdown="# 拓樸圖\nMermaid…"):
    """在 <workflow_path>/build/reports/ 寫一張（預設已稽核的）儀表板產物。"""
    out = workflow_path / "build" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    md = out / "recursion_topology_dashboard.md"
    md.write_text(markdown, encoding="utf-8")
    digest = canonical_graph_digest([0, 1], {0: 1, 1: 0}, [(0, 1)])
    sidecar = {
        "operator_fingerprint": "fp:demo",
        "termination": {"terminating": True},
        "nodes": [{"id": 0, "rank": 1}, {"id": 1, "rank": 0}],
        "edges": [{"src": 0, "dst": 1}],
        "consistency": {"verified": verified, "audit_digest": digest},
    }
    md.with_suffix(".json").write_text(json.dumps(sidecar), encoding="utf-8")
    return md


def _playbook(workflow_path: str):
    return Playbook(project="p", workflow_type="aisdlc_sdd",
                    workflow_path=workflow_path,
                    tasks=[PlaybookTask(step_id="s", name="n", prompt="x")])


def _ctx(playbook):
    return HookContext(phase=KernelPhase.PRE_RUN, playbook=playbook, task=None, payload={})


def _plugin(obs=None):
    return SddGovernancePlugin(
        observability=obs,
        topology_dashboard_source=SddTopologyDashboardAdapter(observability=obs))


def test_pre_run_autoloads_verified_dashboard(tmp_path):
    """AT-14-2-1：PRE_RUN 自既有 SDD 渲染產物 fail-closed 載入儀表板 → 舵手可取得。"""
    _write_dashboard(tmp_path)
    plugin = _plugin()
    plugin.on_event(_ctx(_playbook(str(tmp_path))))
    assert "拓樸圖" in plugin.pending_topology_dashboard()


def test_pre_run_no_artifact_empty(tmp_path):
    """AT-14-2-2：無產物（多數 SDD 跑非 recursion signoff）→ pending 為空，零干擾。"""
    plugin = _plugin()
    plugin.on_event(_ctx(_playbook(str(tmp_path))))
    assert plugin.pending_topology_dashboard() == ""


def test_pre_run_fail_closed_not_surfaced(tmp_path):
    """AT-14-2-3：產物未過 PY-2 稽核（verified=False）→ 不呈現（advisory 吞例外）+ 記事件。"""
    _write_dashboard(tmp_path, verified=False)
    obs = _SpyObs()
    plugin = _plugin(obs)
    plugin.on_event(_ctx(_playbook(str(tmp_path))))
    assert plugin.pending_topology_dashboard() == ""
    assert any(n == "sdd.topology_dashboard_unavailable" for n, _ in obs.events)


def test_non_sdd_workflow_skips_dashboard(tmp_path):
    """AT-14-2-4：非 SDD workflow → plugin 全程 no-op，不載儀表板。"""
    _write_dashboard(tmp_path)
    plugin = _plugin()
    pb = Playbook(project="p", workflow_type="auto", workflow_path=str(tmp_path),
                  tasks=[PlaybookTask(step_id="s", name="n", prompt="x")])
    plugin.on_event(_ctx(pb))
    assert plugin.pending_topology_dashboard() == ""


def test_snapshot_restore_preserves_dashboard(tmp_path):
    """AT-14-2-5：儀表板隨 snapshot/restore 跨 session 持久（additive，不破既有欄）。"""
    _write_dashboard(tmp_path)
    plugin = _plugin()
    plugin.on_event(_ctx(_playbook(str(tmp_path))))
    snap = plugin.snapshot()
    assert "topology_dashboard" in snap and snap["topology_dashboard"]

    restored = _plugin()
    restored.restore(snap)
    assert restored.pending_topology_dashboard() == plugin.pending_topology_dashboard()


def test_escalation_dump_renders_topology_section():
    """AT-14-2-6：EscalationDump.to_markdown 嵌入儀表板段（舵手於指揮官端可審批）。"""
    dump = EscalationDump(
        playbook_path="p.yaml", step_id="s", step_name="n", total_attempts=1,
        failure_chain=[], final_eval_output="", is_stuck=False, is_diverging=False,
        suspect_test_file=False, topology_dashboard="# 互遞迴呼叫圖\nrank/fuel…")
    md = dump.to_markdown()
    assert "拓樸審批儀表板" in md and "互遞迴呼叫圖" in md


def test_escalation_dump_without_topology_omits_section():
    """AT-14-2-7：無儀表板（預設 ""）→ 不渲染該段（零退化，既有 dump 不變）。"""
    dump = EscalationDump(
        playbook_path="p.yaml", step_id="s", step_name="n", total_attempts=1,
        failure_chain=[], final_eval_output="", is_stuck=False, is_diverging=False,
        suspect_test_file=False)
    assert "拓樸審批儀表板" not in dump.to_markdown()


def test_dump_escalation_resolver_pulls_from_plugin(tmp_path):
    """AT-14-2-8：choke-point resolver 自 runner 上 sdd_governance plugin 取 pending 儀表板；缺則 ""。"""
    from autoclaude.execution.escalation_dumper import _resolve_topology_dashboard

    _write_dashboard(tmp_path)
    plugin = _plugin()
    plugin.on_event(_ctx(_playbook(str(tmp_path))))

    class _Runner:
        _sdd_governance_plugin = plugin

    class _Bare:
        pass

    assert "拓樸圖" in _resolve_topology_dashboard(_Runner())
    assert _resolve_topology_dashboard(_Bare()) == ""  # facade 無 plugin → 零退化
