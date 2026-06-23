"""Phase I M5 / ACT-070~071 — Fleet Orchestration（艦隊並行協調層）.

落實 SDD_improving_Automation_09.md §5.4 / PI-1：把單軌閉環擴展為「同一專案多
feature 並行自治」。每軌跑自己的單軌 FSM（SDD_FSM，已形式化證明 + liveness），
本模組為其上的**協調層**（非 per-track FSM 內的狀態），提供：

  - TrackRegistry：登記/註銷並行軌道（FSM-STATE-{project}-{track_id}.yaml，ACT-070）
  - SpecDependencyLock：跨軌共享 spec 區段 advisory lock + **全域鎖序防死鎖**
    （resource-ordering：所有軌道一律以 canonical 排序順序取鎖 → 無循環等待 → 無死鎖）
  - MergeArbiter：試 merge → textual conflict→IMPLEMENTATION / semantic→SPEC_AUDIT / clean→proceed
  - join：等待所有軌道抵達 join 點（PARALLEL_TRACK_JOIN 概念）

協調層的安全性（no-deadlock / bounded join）由 formal/FLEET_FSM.tla（parametric，
state[Feature]，ACT-072）證明。純 stdlib，確定性，零外部依賴。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ===================== ACT-070：Track Registry =====================

@dataclass
class Track:
    project: str
    track_id: str
    state_path: str = ""
    status: str = "active"   # active | joined | merged | aborted


class TrackRegistry:
    """登記同一 project 下並行的多個 feature track。"""

    def __init__(self, project: str):
        self.project = project
        self._tracks: Dict[str, Track] = {}

    def register(self, track_id: str) -> Track:
        from .state_loader import track_state_path
        if track_id in self._tracks:
            return self._tracks[track_id]
        t = Track(project=self.project, track_id=track_id,
                  state_path=str(track_state_path(self.project, track_id)))
        self._tracks[track_id] = t
        return t

    def unregister(self, track_id: str) -> None:
        self._tracks.pop(track_id, None)

    def tracks(self) -> List[Track]:
        return list(self._tracks.values())

    def active(self) -> List[Track]:
        return [t for t in self._tracks.values() if t.status == "active"]


# ===================== ACT-071：Spec Dependency Lock（全域鎖序防死鎖）=====================

class DeadlockRisk(RuntimeError):
    """偵測到可能的循環等待（理論上全域鎖序下不會發生；作為防禦性斷言）。"""


class SpecDependencyLock:
    """跨軌共享 spec 區段的 advisory lock。

    **全域鎖序（resource ordering）防死鎖**：任何軌道一次取多把鎖時，一律先對
    lock keys 做 canonical 排序再依序取得。所有軌道遵守同一全域順序 ⇒ 不可能
    形成循環等待 ⇒ 結構性無死鎖（Coffman 條件之「circular wait」被破壞）。
    """

    def __init__(self):
        self._held: Dict[str, str] = {}   # lock_key -> track_id

    def _conflicts(self, track_id: str, keys: List[str]) -> List[str]:
        return [k for k in keys if self._held.get(k) not in (None, track_id)]

    def acquire_all(self, track_id: str, keys: List[str]) -> Tuple[bool, List[str]]:
        """嘗試一次取得 keys 的所有鎖（全域排序）。

        回傳 (acquired, conflicts)。acquired=True → 全部取得；False → 有衝突，
        **不取任何鎖**（all-or-nothing，避免部分持有造成的循環等待）。
        """
        ordered = sorted(set(keys))                    # 全域 canonical 鎖序
        conflicts = self._conflicts(track_id, ordered)
        if conflicts:
            return False, conflicts
        for k in ordered:
            self._held[k] = track_id
        return True, []

    def release_all(self, track_id: str) -> None:
        self._held = {k: owner for k, owner in self._held.items() if owner != track_id}

    def holder(self, key: str) -> Optional[str]:
        return self._held.get(key)

    def held_by(self, track_id: str) -> Set[str]:
        return {k for k, owner in self._held.items() if owner == track_id}


# ===================== ACT-071：Merge Arbitration =====================

@dataclass
class MergeResult:
    verdict: str            # "clean" | "textual" | "semantic"
    target_state: str       # 對應 per-track FSM 出口
    conflicting_paths: List[str] = field(default_factory=list)
    note: str = ""


# 語意衝突訊號：契約 / spec / 不變量層級的衝突（需 SPEC_AUDIT 裁決）
_SEMANTIC_SIGNALS = (
    "openapi", "contract", "invariant", "inv-", "schema", "spec",
    "ac-", "api-", "breaking",
)


def arbitrate_merge(
    track_id: str,
    *,
    textual_conflicts: Optional[List[str]] = None,
    semantic_conflicts: Optional[List[str]] = None,
) -> MergeResult:
    """ACT-071：試 merge 後的衝突分類仲裁。

    - 有 semantic conflict（契約/spec/不變量層級）→ SPEC_AUDIT（語意需重審規格）
    - 否則有 textual conflict（行級）→ IMPLEMENTATION（重做實作以解 textual）
    - 皆無 → clean → RELEASE_READY（可進交付）

    semantic 優先於 textual（語意衝突更嚴重，呼應 diagnostic structural > transient）。
    """
    sem = list(semantic_conflicts or [])
    txt = list(textual_conflicts or [])
    if sem:
        return MergeResult(verdict="semantic", target_state="SPEC_AUDIT",
                           conflicting_paths=sem,
                           note=f"track {track_id} 語意衝突（契約/spec/INV）→ 需 SPEC_AUDIT 裁決")
    if txt:
        return MergeResult(verdict="textual", target_state="IMPLEMENTATION",
                           conflicting_paths=txt,
                           note=f"track {track_id} 行級 textual 衝突 → 回 IMPLEMENTATION 重解")
    return MergeResult(verdict="clean", target_state="RELEASE_READY",
                       note=f"track {track_id} merge 乾淨 → 可進交付")


def classify_conflict_paths(paths: List[str]) -> Tuple[List[str], List[str]]:
    """把衝突檔路徑分成 (semantic, textual)。spec/contract/api 類視為 semantic。"""
    sem, txt = [], []
    for p in paths:
        low = p.lower()
        (sem if any(sig in low for sig in _SEMANTIC_SIGNALS) else txt).append(p)
    return sem, txt


# ===================== ACT-071：Parallel Track Join =====================

def all_joined(registry: TrackRegistry, join_status: str = "joined") -> bool:
    """PARALLEL_TRACK_JOIN：所有 active 軌道是否都抵達 join 點。"""
    tracks = registry.tracks()
    return bool(tracks) and all(t.status in (join_status, "merged") for t in tracks)


# ===================== Phase J / ACT-079：Fleet Decision Aggregator =====================
# 補 L6 缺口 PJ-4：M5 N 軌並行，attention_budget 雖去重+DIGEST，但 N 軌同時
# HUMAN_PENDING 時仍是「N 個獨立問題丟給人」。本聚合器以 pattern_matcher 對「待決問題」
# 跨軌聚類，同根因合併成單一 decision request（「approve 此項解鎖 K 軌」），讓掌舵者
# 不被規模淹沒。硬白名單：P0/structural 問題永不折疊（Rule 9.22.6）。

from dataclasses import dataclass as _dataclass  # noqa: E402
from .pattern_matcher import is_same_pattern as _is_same_pattern  # noqa: E402


@_dataclass
class PendingDecision:
    track_id: str
    question: str          # 待決問題（去重 key）
    category: str = "transient"   # "structural"==P0（硬白名單，永不折疊）
    summary: str = ""

    @property
    def is_p0(self) -> bool:
        return self.category == "structural"


@_dataclass
class AggregatedDecision:
    root_question: str
    track_ids: List[str] = field(default_factory=list)
    category: str = "transient"
    folded: bool = True     # True=同根因聚合；structural 為 False（永不折疊）

    @property
    def unblocks(self) -> int:
        return len(self.track_ids)


def aggregate_pending(pending: List[PendingDecision]) -> List[AggregatedDecision]:
    """跨軌聚合 HUMAN_PENDING 待決問題。同根因（語意同模式）合併為一個 decision；
    P0/structural 永不折疊（各自獨立保留，Rule 9.22.6）。"""
    p0 = [d for d in pending if d.is_p0]
    rest = [d for d in pending if not d.is_p0]

    out: List[AggregatedDecision] = []
    # structural 永不折疊：每個獨立成一個 decision（folded=False）
    for d in p0:
        out.append(AggregatedDecision(
            root_question=d.question, track_ids=[d.track_id],
            category="structural", folded=False,
        ))
    # 非 P0：語意同模式聚類
    groups: List[List[PendingDecision]] = []
    for d in rest:
        placed = False
        for g in groups:
            if _is_same_pattern(g[0].question, d.question):
                g.append(d)
                placed = True
                break
        if not placed:
            groups.append([d])
    for g in groups:
        out.append(AggregatedDecision(
            root_question=g[0].question,
            track_ids=[d.track_id for d in g],
            category="transient",
            folded=len(g) > 1,
        ))
    return out


def write_decision_digest(
    aggregated: List[AggregatedDecision],
    *,
    out_dir=None,
    today: Optional[str] = None,
) -> str:
    """產出 build/reports/fleet/DECISION-DIGEST-{date}.md（一問解鎖 K 軌）。"""
    import datetime as _dt
    from pathlib import Path
    if out_dir is None:
        from .state_loader import REPO_ROOT
        out_dir = REPO_ROOT / "build" / "reports" / "fleet"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    path = out_dir / f"DECISION-DIGEST-{date}.md"
    total_tracks = sum(a.unblocks for a in aggregated)
    lines = [
        f"# 艦隊決策 Digest — {date}（ACT-079）",
        "",
        f"- 聚合後 decision 數：{len(aggregated)}",
        f"- 涵蓋軌道數：{total_tracks}",
        "",
        "| root_question | 類別 | 解鎖軌道數 | 軌道 | 折疊 |",
        "|---------------|------|-----------|------|------|",
    ]
    for a in sorted(aggregated, key=lambda x: (x.category != "structural", -x.unblocks)):
        lines.append(
            f"| {a.root_question} | {a.category} | {a.unblocks} | "
            f"{', '.join(a.track_ids)} | {'否(P0)' if not a.folded and a.category=='structural' else ('是' if a.folded else '否')} |"
        )
    lines += ["", "> P0/structural 永不折疊（硬白名單，Rule 9.22.6）；一個 approve 解鎖 K 軌。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
