"""SddTopologyDashboardAdapter — SDD 拓樸審批儀表板產物消費器（adapter tier ≤400 LOC）。

對應 AutoSDD_improving_14.md A 軌（W-14-1）。實作
``core/ports/topology_dashboard.ITopologyDashboardSource``。

橋接哲學（**鏡像 SddToPlaybookAdapter 讀 FSM-STATE**——消費 SDD 資料產物，非 import 程式碼）：
AutoClaude（指揮官）不 import AISDLC_SDD（手腳）的 ``tools.fsm_runtime``、不重寫渲染器，只
消費 SDD 端 ``render_recursion_topology_dashboard``（Markdown）+ ``render_json``（JSON
sidecar）已產出的產物。

fail-closed 反視覺欺騙（與 SDD 端 PY-2 互補的縱深第二道）：
  1. sidecar 缺 / 不可解析 → raise（不靜默放行空圖）。
  2. ``consistency.verified`` 非 True → raise（SDD 端 verify_topology_consistency 未過 /
     未附 verdict，不得端到舵手面前盲簽）。
  3. **獨立重算**：從 sidecar 自報 nodes/edges 重算 digest，與其宣稱 ``audit_digest``
     不符 → raise（sidecar 內部不自洽 = 被竄改 / 偽造；AutoClaude 端不盲信標籤）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...core.ports.topology_dashboard import (
    DashboardNotVerifiedError,
    TopologyDashboard,
    recompute_sidecar_digest,
)


class SddTopologyDashboardAdapter:
    """讀 SDD 渲染產物（Markdown + JSON sidecar），fail-closed 稽核後回傳 TopologyDashboard。"""

    def __init__(self, observability: IObservabilityPort | None = None) -> None:
        self._obs = observability or NullObservability()

    def load_dashboard(self, artifact_path: str) -> TopologyDashboard:
        md_path = Path(artifact_path)
        if not md_path.is_file():
            raise FileNotFoundError(f"拓樸儀表板 Markdown 產物不存在：{artifact_path}")
        markdown = md_path.read_text(encoding="utf-8")

        sidecar_path = md_path.with_suffix(".json")
        if not sidecar_path.is_file():
            self._obs.record_event("sdd.topology_dashboard_reject", {
                "artifact": artifact_path, "reason": "sidecar_missing"})
            raise DashboardNotVerifiedError(
                f"儀表板 sidecar 不存在（缺 PY-2 一致性 verdict，fail-closed）：{sidecar_path}")
        try:
            sidecar: dict[str, Any] = json.loads(
                sidecar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            self._obs.record_event("sdd.topology_dashboard_reject", {
                "artifact": artifact_path, "reason": "sidecar_unparseable"})
            raise DashboardNotVerifiedError(
                f"儀表板 sidecar 不可解析（fail-closed）：{exc}") from exc

        consistency = sidecar.get("consistency") or {}
        if consistency.get("verified") is not True:
            self._obs.record_event("sdd.topology_dashboard_reject", {
                "artifact": artifact_path, "reason": "not_verified"})
            raise DashboardNotVerifiedError(
                "儀表板缺 PY-2 consistency.verified=True verdict（SDD 端拓樸防偽未過 / "
                "未附 verdict，fail-closed 反視覺欺騙，拒呈現）")

        claimed_digest = consistency.get("audit_digest")
        try:
            recomputed = recompute_sidecar_digest(sidecar)
        except (KeyError, TypeError, ValueError) as exc:
            self._obs.record_event("sdd.topology_dashboard_reject", {
                "artifact": artifact_path, "reason": "digest_recompute_failed"})
            raise DashboardNotVerifiedError(
                f"儀表板 sidecar nodes/edges 非法、digest 無法獨立重算（fail-closed）：{exc}"
            ) from exc
        if claimed_digest != recomputed:
            self._obs.record_event("sdd.topology_dashboard_reject", {
                "artifact": artifact_path, "reason": "digest_mismatch",
                "claimed": claimed_digest, "recomputed": recomputed})
            raise DashboardNotVerifiedError(
                f"儀表板 sidecar 自報 audit_digest={claimed_digest} 與其 nodes/edges 重算"
                f"={recomputed} 不符（sidecar 內部不自洽 = 被竄改 / 偽造，fail-closed）")

        termination = sidecar.get("termination") or {}
        dashboard = TopologyDashboard(
            markdown=markdown,
            operator_fingerprint=str(sidecar.get("operator_fingerprint") or ""),
            terminating=bool(termination.get("terminating", False)),
            consistency_verified=True,
            audit_digest=str(claimed_digest),
        )
        self._obs.record_event("sdd.topology_dashboard_loaded", {
            "artifact": artifact_path,
            "fingerprint": dashboard.operator_fingerprint,
            "terminating": dashboard.terminating})
        return dashboard
