"""Phase O / ACT-111 — Objective Tuner（自我調參候選權重生成器）.

對應藍圖：SDD_improving_Automation_15.md §1.2 / §3.1 ACT-111 / Rule 9.27.1 / 9.27.3。

Phase N 的 `composition_objective_scorer` 證了「給定目標函式找全域最優排程」，但**目標函式
本身的權重（BATCH_W / LATENCY_W）是人工凍結常數**——系統不會從「哪些排程實際上跑得好」
這些已累積的現實，學到「我的目標權重設錯了」。本模組是 L10 完整最後一塊「離線活體元
迴圈」的**生成半邊（Generator）**：在 bounded 離散權重格點上搜出候選 profile。

**生成-評估對抗分離（Rule 9.27.2，反 Goodhart 的結構基石）**：本模組**結構性不持有任何
評分能力**——它只在候選格點上列舉 `WeightProfile`，再透過呼叫端**注入的 `evaluate` 回呼**
取得每個候選的品質。`evaluate` 由 `objective_replay_oracle`（評估半邊）提供，其語料是
tuner 看不到、content-hashed 凍結的 held-out 現實代理。tuner 因此**無法用自己的尺規給
自己打高分**（它根本沒有尺規）。

**有界（Rule 9.27.1）**：候選展開 ≤ `SDD_OBJ_TUNE_BUDGET`（clamp[8,256]，預設 64），
絕不指數爆炸。**advisory（Rule 9.27.3）**：只產 `proposed` profile，`OBJECTIVE_PROFILE_VERSION`
的 bump 必經人工 signoff；本模組**絕不自動 commit、絕不自寫 scorer 權重常數**。
純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import yaml

from . import composition_objective_scorer as _os
from .file_lock import file_lock
from .state_loader import REPO_ROOT

# obj-profile 元迴圈在共用 meta-loop-ledger 中的指紋命名空間（Rule 9.27.4）。
OBJ_PROFILE_NS = "obj-profile:"

TUNING_LEDGER_PATH = REPO_ROOT / "build" / "state" / "objective-tuning-ledger.yaml"
TUNING_REPORT_DIR = REPO_ROOT / "build" / "reports" / "objective-tuning"

# === 有界搜尋預算（Rule 9.27.1：超限即停，絕不指數爆炸）===
_DEFAULT_TUNE_BUDGET = 64
_TUNE_BUDGET_CLAMP = (8, 256)

# === 勝率門檻（Rule 9.27.2：候選須在 held-out 勝過 incumbent ≥ 此差距才取得 capability tier）===
_DEFAULT_WIN_MARGIN = 0.10
_WIN_MARGIN_CLAMP = (0.0, 1.0)

# 候選格點（deterministic）。刻意涵蓋退化點（batch_w=0 / latency_w=0）作為 Goodhart 誘餌，
# 讓 held-out oracle 有機會把「自評看似超低成本、真實卻很差」的退化權重攔下來。
_BATCH_W_GRID = (0.0, 0.5, 1.0, 1.5, 2.0)
_LATENCY_W_GRID = (0.0, 0.05, 0.1, 0.2, 0.35, 0.5)


def obj_tune_budget() -> int:
    """讀 SDD_OBJ_TUNE_BUDGET（env 可調），clamp[8,256]，預設 64。"""
    raw = os.environ.get("SDD_OBJ_TUNE_BUDGET")
    if not raw:
        return _DEFAULT_TUNE_BUDGET
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_TUNE_BUDGET
    lo, hi = _TUNE_BUDGET_CLAMP
    return max(lo, min(hi, val))


def obj_win_margin() -> float:
    """讀 SDD_OBJ_WIN_MARGIN（env 可調），clamp[0,1]，預設 0.10。"""
    raw = os.environ.get("SDD_OBJ_WIN_MARGIN")
    if not raw:
        return _DEFAULT_WIN_MARGIN
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_WIN_MARGIN
    lo, hi = _WIN_MARGIN_CLAMP
    return max(lo, min(hi, val))


@dataclass(frozen=True)
class WeightProfile:
    """一組目標函式權重（對應 composition_objective_scorer 的 BATCH_W / LATENCY_W）。"""
    batch_w: float
    latency_w: float

    def score_schedule(self, schedule: List[List[str]], values: Dict[str, float]) -> float:
        """用本 profile 的權重量化一個排程成本（鏡像 composition_objective_scorer.score_schedule）。

        注意：這是「用候選權重評排程成本」，**不是**評 profile 自身好壞——profile 的好壞
        只能由 held-out oracle 的真實結果判定（Rule 9.27.2，防自評）。
        """
        batch_count = len(schedule)
        latency = 0.0
        for i, batch in enumerate(schedule):
            latency += i * sum(values.get(x, 0.0) for x in batch)
        return round(batch_count * self.batch_w + latency * self.latency_w, 6)

    def fingerprint(self) -> str:
        """obj-profile 語意指紋（共用 meta-loop-ledger 的 churn 命名空間，Rule 9.27.4）。"""
        digest = hashlib.sha256(f"{self.batch_w}:{self.latency_w}".encode()).hexdigest()[:12]
        return f"{OBJ_PROFILE_NS}{digest}"

    def to_dict(self) -> dict:
        return {"batch_w": self.batch_w, "latency_w": self.latency_w}


def incumbent_profile() -> WeightProfile:
    """讀目前凍結的 incumbent 權重（**唯讀** composition_objective_scorer 常數）。

    Rule 9.27.3：tuner 只能讀 incumbent，**不能寫**——改 scorer 常數的權力只在人工 bump。
    """
    return WeightProfile(batch_w=_os.BATCH_W, latency_w=_os.LATENCY_W)


def candidate_grid(budget: Optional[int] = None,
                   *, incumbent: Optional[WeightProfile] = None) -> List[WeightProfile]:
    """deterministic 候選格點，cap 在 budget（Rule 9.27.1 SearchBounded）。

    排除與 incumbent 完全相同的點（提案無意義）。超 budget 時按穩定序截斷。
    """
    cap = budget if budget is not None else obj_tune_budget()
    inc = incumbent or incumbent_profile()
    grid: List[WeightProfile] = []
    for bw in _BATCH_W_GRID:
        for lw in _LATENCY_W_GRID:
            cand = WeightProfile(batch_w=bw, latency_w=lw)
            if cand == inc:
                continue
            grid.append(cand)
    return grid[:cap]


@dataclass
class TuningProposal:
    """調參提案（proposed；待人工 signoff，Rule 9.27.3）。"""
    candidate: WeightProfile
    incumbent: WeightProfile
    candidate_quality: float = 0.0   # held-out 真實品質（由注入 evaluate 提供）
    incumbent_quality: float = 0.0
    win_delta: float = 0.0
    win_margin: float = 0.0
    tier: int = 0                    # capability tier（held-out 勝率量化；Rule 9.27.5 唯一合法來源）
    accepted: bool = False           # 是否達 margin（達標才有資格送人工 signoff）
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate.to_dict(),
            "incumbent": self.incumbent.to_dict(),
            "candidate_fingerprint": self.candidate.fingerprint(),
            "candidate_quality": self.candidate_quality,
            "incumbent_quality": self.incumbent_quality,
            "win_delta": round(self.win_delta, 6),
            "win_margin": self.win_margin,
            "tier": self.tier,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動 verified/commit）
        }


def propose(
    evaluate: Callable[[WeightProfile], float],
    *,
    incumbent: Optional[WeightProfile] = None,
    budget: Optional[int] = None,
    win_margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
) -> TuningProposal:
    """在 bounded 候選格點上找「held-out 真實品質最高」的 profile（Generator 半邊）.

    Args:
        evaluate: **注入的評估器**（通常為 objective_replay_oracle.evaluate_profile）；
            回傳該 profile 在 held-out 現實代理上的真實品質（0~1，越高越好）。
            本函式**只呼叫它、絕不自算品質**——這是反 Goodhart 對抗分離的結構保證
            （Rule 9.27.2：tuner 結構性無自評能力）。
        tier_fn: 把 candidate 真實品質映射成 capability tier 的函式（預設 round(q*100)）；
            tier 是 GraduationRatchet 的 capability_level（Rule 9.27.5）。

    回傳 `TuningProposal`。`accepted` 僅代表「達 margin、有資格送人工」，**不代表已採納**
    （採納須人工 signoff + adopt_profile，Rule 9.27.3）。`nodes_searched ≤ budget`（Rule 9.27.1）。
    """
    inc = incumbent or incumbent_profile()
    margin = win_margin if win_margin is not None else obj_win_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))
    grid = candidate_grid(budget=budget, incumbent=inc)

    inc_quality = float(evaluate(inc))
    best: Optional[WeightProfile] = None
    best_quality = inc_quality
    searched = 0
    for cand in grid:
        searched += 1
        q = float(evaluate(cand))
        # deterministic tie-break：嚴格優於目前最佳才取代（穩定序保證可重現）。
        if q > best_quality:
            best_quality = q
            best = cand

    if best is None:
        return TuningProposal(
            candidate=inc, incumbent=inc,
            candidate_quality=inc_quality, incumbent_quality=inc_quality,
            win_delta=0.0, win_margin=margin, tier=tfn(inc_quality),
            accepted=False, nodes_searched=searched,
            reason="格點內無候選嚴格優於 incumbent（incumbent 已是區域最優或近最優）",
        )

    delta = round(best_quality - inc_quality, 6)
    accepted = delta >= margin
    return TuningProposal(
        candidate=best, incumbent=inc,
        candidate_quality=best_quality, incumbent_quality=inc_quality,
        win_delta=delta, win_margin=margin, tier=tfn(best_quality),
        accepted=accepted, nodes_searched=searched,
        reason=("達 margin：候選 held-out 真實品質顯著優於 incumbent，可送人工 signoff"
                if accepted else
                "未達 margin：候選雖略優但差距 < win_margin，不送 signoff（守反自評紀律）"),
    )


class SignoffRequired(RuntimeError):
    """Rule 9.27.3：obj-profile 採納須人工 signoff——禁止 tuner 自動 commit。"""


def adopt_profile(profile: WeightProfile, capability_level: int, *,
                  human_signoff: bool = False,
                  rule_id: Optional[str] = None,
                  source: str = "objective_tuner",
                  note: str = "",
                  ledger_path: Optional[Path] = None,
                  ts: Optional[str] = None):
    """採納一個 obj-profile——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger churn 預算**.

    這是「不增第六軌」的接縫（Rule 9.27.4）：obj-profile 的 add↔retire 元迴圈完全納入
    Phase L 既有 `META_FSM` 的 `ChurnBounded`/`GraduationRatchet`——指紋帶 `obj-profile:`
    命名空間，與 SLV 規則共用同一 churn 上限。

    人工 signoff 強制（Rule 9.27.3）：`human_signoff=False` 直接 raise，杜絕 tuner 自動 commit。
    guard 拋出（ChurnBoundExceeded / GraduationRatchetViolation）時不落帳，呼叫端轉 MFSM_ESCALATION。
    """
    if not human_signoff:
        raise SignoffRequired(
            "obj-profile 採納須人工 signoff（Rule 9.27.3）；"
            "僅在人工確認 OBJECTIVE_PROFILE_VERSION bump 後以 human_signoff=True 呼叫"
        )
    from .meta_halt import meta_halt_monitor as _mm
    fp = profile.fingerprint()
    rid = rule_id or ("OBJ-PROFILE-" + fp.split(":", 1)[1])
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def retire_profile(profile: WeightProfile, capability_level: int = 0, *,
                   rule_id: Optional[str] = None,
                   source: str = "objective_tuner",
                   note: str = "",
                   ledger_path: Optional[Path] = None,
                   ts: Optional[str] = None):
    """退役一個 obj-profile（被新 profile 取代）。退役永遠安全（縮小集合），不被守門阻擋。"""
    from .meta_halt import meta_halt_monitor as _mm
    fp = profile.fingerprint()
    rid = rule_id or ("OBJ-PROFILE-" + fp.split(":", 1)[1])
    return _mm.record_rule_retire(rid, fp, int(capability_level),
                                  source=source, note=note,
                                  ledger_path=ledger_path, ts=ts)


def record_proposal(proposal: TuningProposal, *,
                    ledger_path: Optional[Path] = None,
                    ts: Optional[str] = None) -> dict:
    """把提案落 objective-tuning-ledger.yaml（domain 審計鏈；file_lock 保護）.

    注意：本帳本是**領域審計**（記提案細節）；churn 治理走的是**共用 meta-loop-ledger**
    （adopt_profile / retire_profile，Rule 9.27.4），兩者分工不同。
    """
    path = Path(ledger_path) if ledger_path else TUNING_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    with file_lock(lock):
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", 1)
        events = data.get("events")
        if not isinstance(events, list):
            events = []
        entry = proposal.to_dict()
        entry["ts"] = ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        entry["signoff"] = "pending"   # 人工 signoff 狀態（Rule 9.27.3）
        events.append(entry)
        data["events"] = events
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
