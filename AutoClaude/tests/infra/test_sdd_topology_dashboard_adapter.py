"""W-14-1 契約測：SddTopologyDashboardAdapter（meta⁸ 拓樸審批儀表板橋接消費器）。

對應 AutoSDD_improving_14.md A 軌 / RTM AT-14-1-*。

測試意圖（Rule 9 — 驗證 WHY，非僅 WHAT）：
  - 橋接「消費已渲染產物、非 import SDD 程式碼」的契約成立（round-trip 還原拓樸欄位）。
  - **fail-closed 反視覺欺騙**才是本橋接存在的理由：缺檔 / 缺 verdict / 偽 verified /
    digest 不自洽，任一都必須拒呈現（raise），杜絕把 SDD 端稽核不過的圖盲簽端到舵手面前。
"""
from __future__ import annotations

import json

import pytest

from autoclaude.core.ports.topology_dashboard import (
    DashboardNotVerifiedError,
    canonical_graph_digest,
)
from autoclaude.infra.adapters.sdd_topology_dashboard_adapter import (
    SddTopologyDashboardAdapter,
)


def _well_formed_sidecar() -> dict:
    """自洽 sidecar：2 節點 1 邊，audit_digest 由同一正規化慣例算出（鏡像 SDD render_json）。"""
    nodes = [
        {"id": 0, "rank": 1, "src": None},
        {"id": 1, "rank": 0},
    ]
    edges = [{"src": 0, "dst": 1, "rank_decrement": 1, "well_founded": True}]
    digest = canonical_graph_digest(
        [0, 1], {0: 1, 1: 0}, [(0, 1)])
    return {
        "schema_version": 1,
        "view": "recursion_topology",
        "operator_fingerprint": "fp:abc123",
        "termination": {"terminating": True, "acyclic": True, "well_founded": True},
        "nodes": nodes,
        "edges": edges,
        "consistency": {"verified": True, "audit_digest": digest},
    }


def _write_artifact(tmp_path, sidecar: dict | None, *, markdown: str = "# 拓樸儀表板\n圖內容",
                    write_sidecar: bool = True):
    md = tmp_path / "topology_dashboard.md"
    md.write_text(markdown, encoding="utf-8")
    if write_sidecar:
        side = tmp_path / "topology_dashboard.json"
        side.write_text(json.dumps(sidecar), encoding="utf-8")
    return str(md)


class _RecordingObs:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def record_event(self, name, payload):
        self.events.append((name, payload))

    # NullObservability 其餘介面在本測未觸發；adapter 僅用 record_event


def test_round_trip_verified_dashboard(tmp_path):
    """AT-14-1-1：合法已稽核產物 → 還原 TopologyDashboard 全欄（presenter 契約成立）。"""
    obs = _RecordingObs()
    path = _write_artifact(tmp_path, _well_formed_sidecar())
    dash = SddTopologyDashboardAdapter(observability=obs).load_dashboard(path)

    assert dash.consistency_verified is True
    assert dash.terminating is True
    assert dash.operator_fingerprint == "fp:abc123"
    assert dash.audit_digest.startswith("sha256:")
    assert "拓樸儀表板" in dash.markdown
    assert any(n == "sdd.topology_dashboard_loaded" for n, _ in obs.events)


def test_missing_markdown_raises_filenotfound(tmp_path):
    """AT-14-1-2：Markdown 產物不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        SddTopologyDashboardAdapter().load_dashboard(str(tmp_path / "nope.md"))


def test_missing_sidecar_fail_closed(tmp_path):
    """AT-14-1-3：缺 sidecar（無 PY-2 verdict）→ fail-closed 拒呈現。"""
    obs = _RecordingObs()
    path = _write_artifact(tmp_path, None, write_sidecar=False)
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter(observability=obs).load_dashboard(path)
    assert any(p.get("reason") == "sidecar_missing" for _, p in obs.events)


def test_not_verified_fail_closed(tmp_path):
    """AT-14-1-4：sidecar consistency.verified 非 True → fail-closed（反盲簽）。"""
    obs = _RecordingObs()
    sidecar = _well_formed_sidecar()
    sidecar["consistency"]["verified"] = False
    path = _write_artifact(tmp_path, sidecar)
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter(observability=obs).load_dashboard(path)
    assert any(p.get("reason") == "not_verified" for _, p in obs.events)


def test_verified_absent_fail_closed(tmp_path):
    """AT-14-1-5：verified 欄缺失（非 None 而是不存在）→ fail-closed（不得因省略而 false-green）。"""
    sidecar = _well_formed_sidecar()
    del sidecar["consistency"]["verified"]
    path = _write_artifact(tmp_path, sidecar)
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter().load_dashboard(path)


def test_tampered_digest_mismatch_fail_closed(tmp_path):
    """AT-14-1-6：sidecar 宣稱 verified=True 但 nodes 被竄改、digest 不自洽 → 獨立重算攔截。

    模擬「畫的圖比跑的簡單」攻擊在橋接層的變體：偽 verified + 改 rank 但忘改 digest。
    """
    obs = _RecordingObs()
    sidecar = _well_formed_sidecar()
    # 竄改節點 rank（偽造更良基的圖），但保留原 audit_digest → 自報不自洽
    sidecar["nodes"][0]["rank"] = 99
    path = _write_artifact(tmp_path, sidecar)
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter(observability=obs).load_dashboard(path)
    assert any(p.get("reason") == "digest_mismatch" for _, p in obs.events)


def test_unparseable_sidecar_fail_closed(tmp_path):
    """AT-14-1-7：sidecar 非合法 JSON → fail-closed。"""
    md = tmp_path / "topology_dashboard.md"
    md.write_text("# md", encoding="utf-8")
    (tmp_path / "topology_dashboard.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter().load_dashboard(str(md))


def test_malformed_nodes_fail_closed(tmp_path):
    """AT-14-1-8：sidecar nodes 缺 id/rank → 重算失敗 fail-closed（不靜默放行）。"""
    obs = _RecordingObs()
    sidecar = _well_formed_sidecar()
    sidecar["nodes"] = [{"id": 0}]  # 缺 rank
    path = _write_artifact(tmp_path, sidecar)
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter(observability=obs).load_dashboard(path)
    assert any(p.get("reason") == "digest_recompute_failed" for _, p in obs.events)
