"""Phase Q / ACT-123 — Value Dimension Registry（價值維度自我擴充提案骨架）.

對應藍圖：SDD_improving_Automation_17.md §1.1 / §3.1 ACT-123 / Rule 9.29.1。

Phase O 證了「**一個**評分器的目標權重可被有界、反 Goodhart 地自校準」；Phase P 把它
泛化到「**整套固定 8 維**價值向量一致自校準（joint oracle + CrossScorerChurnBounded）」。
但 Phase O/P 全程**不改價值空間的維度數與種類**——8 條評判軸是硬編固定的。本模組把提案
骨架**升維**：從「在固定維度內提案權重 profile」升到「**對維度集合本身提案新增一條維度
（新評判軸）**」。這是 meta-meta 層——改變系統「在乎什麼」的本體論（ontology）。

**承 Phase O/P 的反 Goodhart 對抗分離（Rule 9.29.1/9.29.2，結構基石）**：本模組**結構性不
持有任何必要性判據、不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded
候選維度池上列舉 `ValueDimension`，再透過呼叫端**注入的 `evaluate` 回呼**取每個候選的必要性
（= 評估器的增量覆蓋）。proposer 因此**無法用自己的尺規證明自己必要**（它根本沒有必要性語料）。

**有界（Rule 9.29.1）**：候選維度展開 ≤ `SDD_DIM_PROPOSE_BUDGET`（clamp[4,128]，預設 32），
絕不指數爆炸。**反 big-bang 增維（Rule 9.29.4）**：一輪至多 `SDD_DIM_EXPAND_K`（預設 **1**，
比 Phase P calibration 的 K=2 更嚴——增維是更高賭注的本體論改動）個新維度可進
proposed-pending-signoff，絕不一次劫持整個本體論。**advisory（Rule 9.29.1）**：只產 `proposed`
維度，任一新維度的納入必經人工 signoff + `guard_dimension_expansion`；本模組**絕不自動納入、
絕不自寫維度集合常數**。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT

# === 增維提案領域審計帳本（churn/cardinality 治理另走共用 meta-loop-ledger，Rule 9.29.3）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"
DIM_REPORT_DIR = REPO_ROOT / "build" / "reports" / "value-dimension"

# value-dimension 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾，故與
# Phase P calibration 聚合速率守門互不干涉，Rule 9.29.3）。
DIMENSION_NAMESPACE = "value-dimension:"

# === 有界搜尋預算（Rule 9.29.1：超限即停，絕不指數爆炸）===
_DEFAULT_PROPOSE_BUDGET = 32
_PROPOSE_BUDGET_CLAMP = (4, 128)

# === 必要性門檻（Rule 9.29.2：候選維度須在 held-out 增量覆蓋 ≥ 此門檻才取得 tier）===
_DEFAULT_COVERAGE_MARGIN = 0.10
_COVERAGE_MARGIN_CLAMP = (0.0, 1.0)

# === 反 big-bang 增維 K_dim（Rule 9.29.4：一輪至多 K_dim 條新維度，預設 1）===
_DEFAULT_EXPAND_K = 1
_EXPAND_K_CLAMP = (1, 8)


def dim_propose_budget() -> int:
    """讀 SDD_DIM_PROPOSE_BUDGET（env 可調），clamp[4,128]，預設 32。"""
    return _clamp_int(os.environ.get("SDD_DIM_PROPOSE_BUDGET"), _DEFAULT_PROPOSE_BUDGET, _PROPOSE_BUDGET_CLAMP)


def dim_coverage_margin() -> float:
    """讀 SDD_DIM_COVERAGE_MARGIN（env 可調），clamp[0,1]，預設 0.10。"""
    raw = os.environ.get("SDD_DIM_COVERAGE_MARGIN")
    if not raw:
        return _DEFAULT_COVERAGE_MARGIN
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_COVERAGE_MARGIN
    lo, hi = _COVERAGE_MARGIN_CLAMP
    return max(lo, min(hi, val))


def dim_expand_k() -> int:
    """讀 SDD_DIM_EXPAND_K（env 可調），clamp[1,8]，預設 1（反 big-bang 增維，Rule 9.29.4）。"""
    return _clamp_int(os.environ.get("SDD_DIM_EXPAND_K"), _DEFAULT_EXPAND_K, _EXPAND_K_CLAMP)


def _clamp_int(raw: Optional[str], default: int, clamp: Tuple[int, int]) -> int:
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    lo, hi = clamp
    return max(lo, min(hi, val))


# ---------------------------------------------------------------------------
# 候選價值維度（一條候選新評判軸；meta-meta 層的提案製品）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValueDimension:
    """一條候選價值維度（新評判軸）.

    name 是維度語意名（e.g. "maintainability_cost"）；probe 是它「量什麼」的凍結描述子
    （唯讀；honesty——proposer 只描述，真正判斷必要性的權力在 oracle，Rule 9.29.1/9.29.5）。
    fingerprint 決定它在共用 meta-loop-ledger 的 `value-dimension:` 命名空間（Rule 9.29.3），
    與 SLV 規則 / scorer-profile 共用同一 churn 預算、但受獨立 stock 天花板封死。
    """
    name: str
    probe: Tuple[str, ...] = ()         # 它讀哪些特徵（凍結描述；非自評權重）
    rationale: str = ""
    namespace: str = DIMENSION_NAMESPACE

    @staticmethod
    def of(name: str, probe=(), rationale: str = "") -> "ValueDimension":
        return ValueDimension(name=str(name), probe=tuple(sorted(str(p) for p in probe)),
                              rationale=str(rationale))

    def fingerprint(self) -> str:
        """語意指紋（共用 meta-loop-ledger 的 churn 命名空間，Rule 9.29.1/9.29.3）。"""
        payload = self.name + "|" + ";".join(self.probe)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "probe": list(self.probe), "rationale": self.rationale,
                "namespace": self.namespace}


def is_dimension_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 value-dimension 命名空間（供 ACT-125 stock 停機過濾）。"""
    return bool(fingerprint) and fingerprint.startswith(DIMENSION_NAMESPACE)


# ---------------------------------------------------------------------------
# 候選維度池（單一真實來源：系統「正在考慮新增」的候選評判軸；bounded）
# ---------------------------------------------------------------------------

_CANDIDATE_POOL: List[ValueDimension] = []


def register_candidate(dim: ValueDimension) -> None:
    if all(d.name != dim.name for d in _CANDIDATE_POOL):
        _CANDIDATE_POOL.append(dim)


def _register_default_candidates() -> None:
    """預設候選維度池：固定 8 軸之外、系統「可能該也在乎」的候選評判軸（plausible，非誘餌）.

    誘餌（自利噪音軸 / 冗餘軸）一律在測試 fixture 直接構造，不入生產候選池——比照 Phase P
    的 _GOODHART_DECOY 設計：生產池只放合理候選，攻擊面由測試/凍結語料覆蓋。
    """
    if _CANDIDATE_POOL:
        return
    for nm, probe, why in (
        ("maintainability_cost", ("cyclomatic", "coupling", "churn_locality"),
         "8 軸過閘但生產頻見可維護性崩壞失敗——既有維度集體漏判"),
        ("security_surface", ("exposed_endpoints", "secret_density", "authz_gaps"),
         "安全曝面非任一既有軸所量；STRIDE 失敗常落既有維度盲區"),
        ("operability_cost", ("alert_noise", "rollback_complexity", "obs_gaps"),
         "可運維性（告警/回滾/可觀測）為交付後真實成本，既有軸不量"),
        ("data_integrity_risk", ("migration_irreversibility", "constraint_gaps"),
         "資料完整性風險（不可逆遷移/約束缺口）為既有軸盲區"),
        ("accessibility_cost", ("a11y_violations", "i18n_gaps"),
         "可及性/在地化缺口為使用者真實價值，既有軸不量"),
        ("carbon_cost", ("compute_intensity", "idle_waste"),
         "能耗/碳成本為新興真實約束，既有軸不量"),
    ):
        register_candidate(ValueDimension.of(nm, probe=probe, rationale=why))


_register_default_candidates()


def candidate_pool(*, budget: Optional[int] = None) -> List[ValueDimension]:
    """deterministic 候選維度池（按 name 穩定序），cap 在 budget（Rule 9.29.1 SearchBounded）。"""
    cap = budget if budget is not None else dim_propose_budget()
    ordered = sorted(_CANDIDATE_POOL, key=lambda d: d.name)
    return ordered[:cap]


def candidate_names() -> List[str]:
    return [d.name for d in candidate_pool()]


# ---------------------------------------------------------------------------
# 提案器（在 bounded 候選池上以注入 evaluate〔= oracle 必要性〕找最佳新維度）
# ---------------------------------------------------------------------------

@dataclass
class DimensionProposal:
    """單一候選新維度的提案（proposed；待人工 signoff，Rule 9.29.1）。"""
    dimension: ValueDimension
    necessity: float = 0.0           # held-out 增量覆蓋（由注入 evaluate 提供，proposer 無自評）
    margin: float = 0.0
    tier: int = 0                    # necessity capability tier（held-out 唯一合法來源，Rule 9.29.2/9.29.5）
    accepted: bool = False           # 達 margin（有資格送人工 signoff）
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.to_dict(),
            "fingerprint": self.dimension.fingerprint(),
            "necessity": round(self.necessity, 6),
            "margin": self.margin,
            "tier": self.tier,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def propose(
    evaluate: Callable[[ValueDimension], float],
    *,
    pool: Optional[List[ValueDimension]] = None,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
) -> DimensionProposal:
    """在 bounded 候選維度池上找「held-out 必要性最高」的新維度（Generator 半邊，meta-meta）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.29.2：
    proposer 結構性無自評能力）。`accepted` 僅代表「達 margin、有資格送人工」，**不代表已納入**
    （納入須人工 signoff + `adopt_dimension`，Rule 9.29.1）。`nodes_searched ≤ budget`（Rule 9.29.1）。
    """
    cands = pool if pool is not None else candidate_pool(budget=budget)
    mgn = margin if margin is not None else dim_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[ValueDimension] = None
    best_necessity = 0.0
    searched = 0
    for dim in cands:
        searched += 1
        n = float(evaluate(dim))
        if best is None or n > best_necessity:   # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = n
            best = dim

    if best is None:
        return DimensionProposal(
            dimension=ValueDimension.of("(none)"), necessity=0.0, margin=mgn,
            tier=0, accepted=False, nodes_searched=searched,
            reason="候選維度池為空（無維度可提案）")

    accepted = best_necessity >= mgn
    return DimensionProposal(
        dimension=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), accepted=accepted, nodes_searched=searched,
        reason=("達 margin：候選維度 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無候選維度達必要性門檻（價值維度可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪增維提案 + 反 big-bang K_dim 截斷（Rule 9.29.4）
# ---------------------------------------------------------------------------

@dataclass
class ExpansionRound:
    """一輪增維提案的彙整（已套反 big-bang K_dim 截斷）。"""
    proposals: List[DimensionProposal] = field(default_factory=list)   # 全部 accepted 提案
    selected: List[DimensionProposal] = field(default_factory=list)    # 本輪取至多 K_dim 個
    k: int = 0
    deferred: List[str] = field(default_factory=list)                  # 被順延的維度名


def propose_expansion_round(
    evaluate: Callable[[ValueDimension], float],
    *,
    pool: Optional[List[ValueDimension]] = None,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
) -> ExpansionRound:
    """對候選池跑提案，彙整 accepted 提案並套**反 big-bang K_dim 截斷**（Rule 9.29.4）.

    一輪至多 K_dim（預設 1）條新維度可進 proposed-pending-signoff（按 necessity 由高到低取前
    K_dim，deterministic tie-break by dimension name），其餘順延——絕不一次劫持整個本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = pool if pool is not None else candidate_pool(budget=budget)
    mgn = margin if margin is not None else dim_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[DimensionProposal] = []
    for dim in cands:
        n = float(evaluate(dim))
        if n >= mgn:
            proposals.append(DimensionProposal(
                dimension=dim, necessity=n, margin=mgn, tier=tfn(n),
                accepted=True, nodes_searched=1,
                reason="達 margin：候選維度 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.dimension.name))
    selected = ordered[:cap_k]
    deferred = [p.dimension.name for p in ordered[cap_k:]]
    return ExpansionRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 / 退役 — 走既有 meta_halt_monitor，共用 meta-loop-ledger + stock 天花板（Rule 9.29.3）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.29.1/9.29.4：value-dimension 採納須人工 signoff——禁止 registry 自動納入。"""


def adopt_dimension(dimension: ValueDimension, capability_level: int, *,
                    human_signoff: bool = False,
                    rule_id: Optional[str] = None,
                    source: str = "value_dimension_expansion",
                    note: str = "",
                    ledger_path: Optional[Path] = None,
                    ts: Optional[str] = None,
                    check_cardinality: bool = True):
    """採納一條 value-dimension——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    這是「不增第六軌」的接縫（Rule 9.29.3）：value-dimension 的 add↔retire 元迴圈完全納入
    既有 `META_FSM` 的 `ChurnBounded`/`GraduationRatchet`（per-fingerprint）+ Phase Q 新增的
    `DimensionCardinalityBounded`（stock 天花板，ACT-125）。

    人工 signoff 強制（Rule 9.29.1/9.29.4）：`human_signoff=False` 直接 raise。
    guard 拋出（ChurnBoundExceeded / GraduationRatchetViolation / DimensionCardinalityExceeded）
    時不落帳，呼叫端轉 MFSM_ESCALATION。
    """
    if not human_signoff:
        raise SignoffRequired(
            "value-dimension 採納須人工 signoff（Rule 9.29.1/9.29.4）；"
            "僅在人工確認本體論擴張後以 human_signoff=True 呼叫"
        )
    from .meta_halt import meta_halt_monitor as _mm
    fp = dimension.fingerprint()
    rid = rule_id or ("DIM-" + fp.replace(":", "-"))
    if check_cardinality:
        # Phase Q / ACT-125：維度基數 stock 天花板守門（meta-meta 停機，Rule 9.29.3）。
        _mm.guard_dimension_expansion(fp, ledger_path=ledger_path)  # 可能 raise
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def retire_dimension(dimension: ValueDimension, capability_level: int = 0, *,
                     rule_id: Optional[str] = None,
                     source: str = "value_dimension_expansion",
                     note: str = "",
                     ledger_path: Optional[Path] = None,
                     ts: Optional[str] = None):
    """退役一條 value-dimension。退役永遠安全（縮小維度集合），不被阻擋。"""
    from .meta_halt import meta_halt_monitor as _mm
    fp = dimension.fingerprint()
    rid = rule_id or ("DIM-" + fp.replace(":", "-"))
    return _mm.record_rule_retire(rid, fp, int(capability_level),
                                  source=source, note=note,
                                  ledger_path=ledger_path, ts=ts)


def record_round(round_: ExpansionRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪增維提案落 value-dimension-ledger.yaml（domain 審計鏈；file_lock 保護）.

    本帳本是**領域審計**（記提案細節 + 反 big-bang 截斷）；churn/cardinality 治理走的是
    **共用 meta-loop-ledger**（adopt_dimension / retire_dimension，Rule 9.29.3），分工不同。
    """
    path = Path(ledger_path) if ledger_path else DIM_LEDGER_PATH
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
        rounds = data.get("rounds")
        if not isinstance(rounds, list):
            rounds = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.29.1/9.29.4）
        }
        rounds.append(entry)
        data["rounds"] = rounds
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
