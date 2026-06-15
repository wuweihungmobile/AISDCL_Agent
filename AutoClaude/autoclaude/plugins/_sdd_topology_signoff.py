"""_sdd_topology_signoff — SddGovernancePlugin 的 meta⁸ 拓樸儀表板載入 helper（W-14-2）。

對應 AutoSDD_improving_14.md A 軌 / DEF-01-009：sdd_governance_plugin.py 已貼近 plugin_entry
≤250 上限，DEF-01-009 watch 明載「擴充前先拆」——故本輪拓樸橋接邏輯抽出此 helper，使 plugin
本體維持餘量。純函式、fail-closed advisory（port raise → 吞例外回 ""，絕不拖垮治理鏈）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve_artifact(source: Any, artifact_rel: str, workflow_path: str | None) -> str | None:
    """``<workflow_path>/<artifact_rel>`` 存在則回絕對路徑字串，否則 None（無 source / 無 path 亦 None）。"""
    if source is None or not workflow_path:
        return None
    path = Path(workflow_path) / artifact_rel
    return str(path) if path.is_file() else None


def load_dashboard_markdown(source: Any, obs: Any, artifact_path: str) -> str:
    """經 port 載入儀表板 Markdown（fail-closed advisory）。

    儀表板缺 / 未過 PY-2 一致性稽核 / sidecar 不自洽 → port 端 raise；本端**吞例外回 ""**＝
    寧可不呈現也不端未稽核的圖盲簽（fail-closed），並記 advisory 事件供取證。
    """
    if source is None:
        return ""
    try:
        return source.load_dashboard(artifact_path).markdown
    except Exception as exc:  # noqa: BLE001 — fail-closed advisory
        obs.record_event("sdd.topology_dashboard_unavailable",
                         {"artifact": artifact_path, "reason": str(exc)[:200]})
        return ""
