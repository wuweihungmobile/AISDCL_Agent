"""ITopologyDashboardSource — meta⁸ 互遞迴拓樸審批儀表板來源契約（contract tier ≤400 LOC）。

對應 AutoSDD_improving_14.md A 軌（AISDLC-SDD × AutoClaude 深度整合）：把 AISDLC_SDD
（手腳）已落地的 Recursion Topology Dashboard（Phase Y / ACT-160~161 / R-9.37）橋接到
AutoClaude（指揮官）的 signoff / escalation 人類審批介面——讓舵手在指揮官端看得到那張
帶 rank/fuel 的互遞迴呼叫圖，不再盲簽。

設計（**鏡像 ISpecSource**：core 僅依賴本介面，SDD 產物格式知識封裝於 infra adapter
``autoclaude.infra.adapters.sdd_topology_dashboard_adapter``）：

  - AutoClaude 純當 **presenter**——渲染與 PY-2 拓樸防偽（verify_topology_consistency）
    仍由 SDD 權威端產出，AutoClaude 不 import SDD（跨 package、不破微核心邊界）、不重寫
    渲染器（不雙頭漂移）。
  - 本端 **fail-closed 反視覺欺騙**：產物缺 PY-2 一致性 verdict、或 sidecar 自報拓樸與其
    宣稱 audit_digest 不自洽 → 拒呈現（raise），絕不把 SDD 端都稽核不過的圖端到舵手面前。
    此為「橋接層」的反視覺欺騙，與 SDD 端 PY-2 是縱深防禦的兩道（AutoClaude 端獨立重算
    digest、不盲信 sidecar 標籤）。

core-purity contract（.importlinter #2）：本檔 import 模式與 ISpecSource / IEvaluator 相同
（Protocol + dataclass，零 execution / infra 相依），不破壞 core 純度。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


class DashboardNotVerifiedError(RuntimeError):
    """儀表板產物未通過 PY-2 一致性稽核（疑視覺欺騙 / 未稽核 / sidecar 內部不自洽）。

    橋接層 fail-closed 反視覺欺騙：SDD 端 ``verify_topology_consistency`` 都驗不過、未附
    稽核 verdict、或 sidecar 自報 (nodes,edges,ranks) 重算 digest 與其宣稱 audit_digest
    不符的拓樸圖，不得端到指揮官舵手面前盲簽。
    """


@dataclass(frozen=True)
class TopologyDashboard:
    """已渲染、已 PY-2 稽核的拓樸審批儀表板快照（消費 SDD ``render_recursion_topology_dashboard`` 產物）。"""

    markdown: str               # 人類可讀三視圖 Markdown（拓樸 / 終止 / 接地）
    operator_fingerprint: str   # 算子指紋（對齊 to_dict()["fingerprint"]）
    terminating: bool           # 良基停機證書是否成立
    consistency_verified: bool  # PY-2 verify_topology_consistency verdict（必 True 才得呈現）
    audit_digest: str           # 正規化窗格圖指紋（"sha256:..."；供跨端獨立比對）


# 橋接 sidecar digest 約定（**鏡像** SDD recursion_topology_view._canonical_graph 的
# 正規化雜湊慣例——僅複製「指紋慣例」而非渲染器，供 AutoClaude 端 import-free 獨立重算）。
# 若 SDD 端慣例漂移，W-14-3 以**真實 SDD 渲染器**產 sidecar 的 e2e 載具會即時失敗揭露。
def canonical_graph_digest(
    node_ids: Sequence[int],
    rank_of: Mapping[int, int],
    edges: Sequence[tuple[int, int]],
) -> str:
    """(nodes, ranks, edges) 正規化指紋（排序去重 → sha256[:16]，含 "sha256:" 前綴）。"""
    nodes_sorted = sorted(int(i) for i in node_ids)
    ranks_sorted = sorted((int(i), int(rank_of[i])) for i in node_ids)
    edges_sorted = sorted((int(u), int(w)) for (u, w) in edges)
    blob = repr((nodes_sorted, ranks_sorted, edges_sorted))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def recompute_sidecar_digest(sidecar: Mapping[str, Any]) -> str:
    """從 render_json sidecar 自報的 nodes/edges 獨立重算窗格 digest（不信任其自報 audit_digest）。

    僅消費 sidecar 自身宣稱的 (id, rank, src, dst)；catch「sidecar 宣稱的圖 ↔ 宣稱的
    digest」內部不自洽（被竄改 / 偽造），與 SDD 端 PY-2「渲染 ↔ to_dict() 真相」互補。
    """
    nodes = sidecar.get("nodes") or []
    edges = sidecar.get("edges") or []
    node_ids = [int(n["id"]) for n in nodes]
    rank_of = {int(n["id"]): int(n["rank"]) for n in nodes}
    edge_pairs = [(int(e["src"]), int(e["dst"])) for e in edges]
    return canonical_graph_digest(node_ids, rank_of, edge_pairs)


class ITopologyDashboardSource(Protocol):
    """SDD 拓樸審批儀表板產物 → AutoClaude 人類審批介面的契約。

    實作：``autoclaude.infra.adapters.sdd_topology_dashboard_adapter.SddTopologyDashboardAdapter``
    """

    def load_dashboard(self, artifact_path: str) -> TopologyDashboard:
        """讀取 SDD 端產出的儀表板產物（Markdown 本體 + JSON sidecar），fail-closed 稽核後回傳。

        產物約定（**鏡像 ISpecSource 讀 build/reports/fsm/FSM-STATE**——消費資料產物，非 import 程式碼）：
          - ``<artifact_path>``：``render_recursion_topology_dashboard`` 輸出之 Markdown。
          - ``<artifact_path>`` 去副檔名 + ``.json``：``render_json`` sidecar，須含
            ``consistency.verified``(bool，SDD 端 verify_topology_consistency 結果) +
            ``consistency.audit_digest`` + ``operator_fingerprint`` + ``termination.terminating``
            + ``nodes``/``edges``。

        Raises:
            DashboardNotVerifiedError: sidecar 缺 / ``verified`` 非 True / 重算 digest 不符
                （fail-closed 反視覺欺騙）。
            FileNotFoundError: Markdown 或 sidecar 產物不存在。
        """
        ...
