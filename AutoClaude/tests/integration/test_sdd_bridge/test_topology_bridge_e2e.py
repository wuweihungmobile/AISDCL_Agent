"""W-14-3 e2e 橋接載具：AutoClaude 消費**真實 SDD 渲染器**產出的 meta⁸ 拓樸審批儀表板。

對應 AutoSDD_improving_14.md A 軌 / RTM AT-14-3-*。

這是本輪 A 軌「指揮官 × 手腳」橋接的端到端證據：
  手腳（AISLDC_SDD v0.05，真實 `render_recursion_topology_dashboard` +
  `verify_topology_consistency`）產出儀表板產物 → 指揮官（AutoClaude
  `SddTopologyDashboardAdapter` + `SddGovernancePlugin` + `EscalationDump`）消費並
  surface 到舵手審批介面。**零 import 跨 package、零重寫渲染器**——AutoClaude 純當 presenter。

並含 fail-closed 反視覺欺騙攻防：竄改**真實**產物（翻 rank / 撤 verified）→ 指揮官端拒呈現。

SDD 子專案不在 AutoClaude package path 上 → 以 subprocess（cwd=v0.05 namespace root）跑
producer 產生真實產物；SDD 目錄缺席則 skip（不阻斷 AutoClaude 獨立 CI）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from autoclaude.core.ports.topology_dashboard import DashboardNotVerifiedError
from autoclaude.infra.adapters.sdd_topology_dashboard_adapter import (
    SddTopologyDashboardAdapter,
)
from autoclaude.models.escalation import EscalationDump

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SDD_DIR = _REPO_ROOT / "AISDLC_SDD" / "AISDLC_SDD_v0.05"
_SDD_PRESENT = (_SDD_DIR / "tools" / "fsm_runtime" / "recursion_topology_view.py").is_file()

pytestmark = pytest.mark.skipif(
    not _SDD_PRESENT, reason="AISLDC_SDD v0.05 不在此 checkout（AutoClaude 獨立 CI）")

# producer：在 SDD namespace root 內，用**真實**渲染器 + PY-2 稽核產出儀表板 + sidecar。
_PRODUCER = '''
import json, sys
from tools.fsm_runtime.operator_recursion_genesis import RecursiveOperator
from tools.fsm_runtime.operator_genesis import GenesisOperator
from tools.fsm_runtime import recursion_topology_view as v
from tools.fsm_runtime.steersman_renderer import render_recursion_topology_dashboard

out_md = sys.argv[1]
out_json = sys.argv[2]
op = RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul")
d = op.to_dict()
view = v.extract_topology(d)
md = render_recursion_topology_dashboard(view)
rj = v.render_json(view)
# 真實 PY-2：verify_topology_consistency 通過才標 verified（bridge sidecar 契約）。
rj["consistency"]["verified"] = bool(
    v.verify_topology_consistency(rj, d, node_budget=view.budget.node_budget))
open(out_md, "w", encoding="utf-8").write(md)
open(out_json, "w", encoding="utf-8").write(json.dumps(rj, ensure_ascii=False))
'''


def _produce_real_artifact(tmp_path: Path) -> Path:
    md = tmp_path / "recursion_topology_dashboard.md"
    sidecar = md.with_suffix(".json")
    # 以 -c 執行（cwd=v0.05 namespace root → sys.path[0]="" 解析為 cwd，tools.fsm_runtime 可載）。
    proc = subprocess.run(
        [sys.executable, "-c", _PRODUCER, str(md), str(sidecar)],
        cwd=str(_SDD_DIR), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, f"SDD producer 失敗：{proc.stderr}"
    assert md.is_file() and sidecar.is_file()
    return md


def test_consume_real_sdd_rendered_dashboard(tmp_path):
    """AT-14-3-1：AutoClaude adapter 消費真實 SDD 渲染產物 → 還原拓樸（presenter 契約端到端成立）。"""
    md = _produce_real_artifact(tmp_path)
    dash = SddTopologyDashboardAdapter().load_dashboard(str(md))

    assert dash.consistency_verified is True
    assert dash.terminating is True
    assert dash.operator_fingerprint.startswith("recursion-genesis:")
    assert dash.audit_digest.startswith("sha256:")
    # 真實舵手 wrapper 的招牌字樣（render_recursion_topology_dashboard）。
    assert "互遞迴呼叫圖可審批儀表板" in dash.markdown


def test_real_dashboard_surfaces_into_escalation(tmp_path):
    """AT-14-3-2：真實儀表板 surface 進 EscalationDump → 舵手於指揮官端看得到那張圖。"""
    md = _produce_real_artifact(tmp_path)
    dash = SddTopologyDashboardAdapter().load_dashboard(str(md))
    dump = EscalationDump(
        playbook_path="p.yaml", step_id="recur-signoff", step_name="互遞迴算子納入",
        total_attempts=1, failure_chain=[], final_eval_output="", is_stuck=False,
        is_diverging=False, suspect_test_file=False,
        topology_dashboard=dash.markdown)
    out = dump.to_markdown()
    assert "拓樸審批儀表板" in out and "互遞迴呼叫圖可審批儀表板" in out


def test_independent_digest_matches_real_renderer(tmp_path):
    """AT-14-3-3：AutoClaude 端獨立重算 digest == 真實 SDD render_json 的 audit_digest（慣例同步）。

    若 SDD 端 _canonical_graph 慣例漂移，本斷言即時失敗揭露（防 bridge 默默失效）。
    """
    from autoclaude.core.ports.topology_dashboard import recompute_sidecar_digest

    md = _produce_real_artifact(tmp_path)
    sidecar = json.loads(md.with_suffix(".json").read_text(encoding="utf-8"))
    assert recompute_sidecar_digest(sidecar) == sidecar["consistency"]["audit_digest"]


def test_tampered_real_rank_fail_closed(tmp_path):
    """AT-14-3-4：竄改真實產物的 node rank（偽造更良基的圖）但留原 digest → 獨立重算攔截拒呈現。"""
    md = _produce_real_artifact(tmp_path)
    sidecar_path = md.with_suffix(".json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["nodes"][0]["rank"] = sidecar["nodes"][0]["rank"] + 7  # 視覺欺騙
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter().load_dashboard(str(md))


def test_real_unverified_fail_closed(tmp_path):
    """AT-14-3-5：撤掉真實產物的 verified verdict → 指揮官端 fail-closed 拒呈現（不盲簽）。"""
    md = _produce_real_artifact(tmp_path)
    sidecar_path = md.with_suffix(".json")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["consistency"].pop("verified", None)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(DashboardNotVerifiedError):
        SddTopologyDashboardAdapter().load_dashboard(str(md))
