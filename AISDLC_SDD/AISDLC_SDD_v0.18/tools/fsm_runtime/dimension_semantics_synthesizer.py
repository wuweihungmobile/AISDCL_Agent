"""Phase R / ACT-129 — Dimension Semantics Synthesizer（維度語意自我發明骨架）.

對應藍圖：SDD_improving_Automation_18.md §1.1 / §3.1 ACT-129 / Rule 9.30.1 / 9.30.2 / 9.30.4。

Phase Q 證了「系統可在**固定候選池**（`value_dimension_registry._CANDIDATE_POOL`，6 條硬編
plausible 候選）內**挑要不要新增哪一條**價值維度」。但 Phase Q 全程**不生成候選池外的維度**
——選單就那 6 條，提案器只能點菜。本模組把提案骨架**升維**：從「在固定候選池內挑」升到
「**自我發明一條候選池裡根本沒有的全新維度語意**（候選池外生成）」。這是 meta-meta-meta
層——系統自己**寫選單**。

**「候選池外」≠「無界」（Rule 9.30.1 有界生成文法，本模組結構基石）**：候選池外生成被一條
**bounded 生成文法**封住——`VOCAB`（有限特徵詞彙）× 子集 arity <= `SDD_DIM_INVENT_ARITY`
（clamp[1,4]，預設 2）× `OPS`（有限聚合算子）。生成空間因此**可枚舉、有限**，列舉節點
<= `SDD_DIM_INVENT_BUDGET`（clamp[8,256]，預設 64），**絕不指數爆炸**。這是「無界生成需
另證有界」的形式化兌現：把看似無限的語意空間歸約為有限可枚舉文法。

**反自利雙閘第一閘（Rule 9.30.2 自指 probe 守門）**：任何 probe 引用保留自指/proposer/oracle
內部信號（`self_score`/`proposer_*`/`necessity`/`dim_value`/`oracle_*`…）的發明維度，在送
oracle 前即被 `self_reference_guard` **結構性拒絕**（零漏放）——系統不能發明一條「量自己核可」
的自利軸。

**承 Phase Q 的反 Goodhart 對抗分離（Rule 9.30.2，結構基石）**：本模組**結構性不持有任何
必要性判據、不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 生成文法上
枚舉 `InventedDimension`，再透過呼叫端**注入的 `evaluate` 回呼**取每個發明維度的必要性
（= 評估器的 feature-keyed 增量覆蓋）。synthesizer 因此**無法用自己的尺規證明自己必要**。

**反 big-bang 自我發明（Rule 9.30.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q，預設 1）
條自我發明維度可進 proposed-pending-signoff，絕不一次劫持整個本體論。**advisory（Rule 9.30.1）**：
只產 `proposed` 維度，任一納入必經人工 signoff；本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Mapping, Optional, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT
from .value_dimension_registry import DIMENSION_NAMESPACE, dim_expand_k

# === 自我發明領域審計帳本（沿用 Phase Q 的 value-dimension-ledger，增 inventions/swaps 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界生成文法（Rule 9.30.1：候選池外生成被有限文法封住，可枚舉）===
# VOCAB：有限特徵詞彙——候選池外、既有 8 軸 + Phase Q 6 候選池皆不量的原始現實特徵。
VOCAB: Tuple[str, ...] = (
    "rollback_steps",       # 部署回滾步數（回滾風險）
    "blast_radius",         # 變更影響半徑（爆炸半徑）
    "canary_gap",           # canary 與全量的偏差窗
    "data_loss_window",     # 不可逆資料損失窗
    "schema_lock_time",     # schema 鎖表時長
    "oncall_pages",         # on-call 告警頻次（可運維真實成本）
    "runbook_depth",        # runbook 步驟深度（操作複雜度）
    "supply_chain_pins",    # 供應鏈未釘版依賴數
)

# OPS：有限聚合算子（把選中的特徵子集聚合為一個維度量值）。
OPS: Tuple[str, ...] = ("mean", "max", "min", "sum")

# === 保留自指信號（Rule 9.30.2 反自利第一閘：probe 引用任一 → 結構性拒絕）===
RESERVED_SELF_REF: Tuple[str, ...] = (
    "self_score", "proposer_", "necessity", "dim_value", "oracle_",
    "self_", "verdict", "tier", "capability", "approval", "confidence",
)

_DEFAULT_INVENT_BUDGET = 64
_INVENT_BUDGET_CLAMP = (8, 256)
_DEFAULT_INVENT_ARITY = 2
_INVENT_ARITY_CLAMP = (1, 4)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def invent_budget() -> int:
    """讀 SDD_DIM_INVENT_BUDGET（env 可調），clamp[8,256]，預設 64（Rule 9.30.1 有界生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_INVENT_BUDGET"), _DEFAULT_INVENT_BUDGET, _INVENT_BUDGET_CLAMP)


def invent_arity() -> int:
    """讀 SDD_DIM_INVENT_ARITY（env 可調），clamp[1,4]，預設 2（一條發明維度最多組合幾個特徵）。"""
    return _clamp_int(os.environ.get("SDD_DIM_INVENT_ARITY"), _DEFAULT_INVENT_ARITY, _INVENT_ARITY_CLAMP)


def invent_coverage_margin() -> float:
    """讀 SDD_DIM_COVERAGE_MARGIN（與 registry/oracle 共用），預設 0.10。"""
    raw = os.environ.get("SDD_DIM_COVERAGE_MARGIN")
    if not raw:
        return _DEFAULT_COVERAGE_MARGIN
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_COVERAGE_MARGIN
    return max(0.0, min(1.0, val))


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
# 自我發明維度（一條候選池外、現場由文法生成的新評判軸）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InventedDimension:
    """一條候選池外、由 bounded 生成文法現場發明的新評判軸（meta-meta-meta 製品）.

    name 由 op + sorted(probe) 決定性編碼（故 fingerprint 穩定、與 probe 序無關）。
    probe 是它「量哪些原始特徵」（選中的 VOCAB 子集；唯讀描述）。op 是聚合算子。
    apply(features) 把 probe 特徵以 op 聚合為一個維度量值——這是 oracle 在 feature-keyed
    現實情節上現算 dim_value 的純函式（oracle 可知本型別，反向不可，承 Phase Q）。
    fingerprint 落在共用 `value-dimension:` 命名空間（Rule 9.30.3），與 Phase Q 增維/
    scorer-profile 共用 churn/cardinality/swap 治理。
    """
    op: str
    probe: Tuple[str, ...]              # 選中的 VOCAB 特徵子集（sorted）
    rationale: str = ""
    namespace: str = DIMENSION_NAMESPACE

    @staticmethod
    def of(op: str, probe, rationale: str = "") -> "InventedDimension":
        return InventedDimension(op=str(op), probe=tuple(sorted(str(p) for p in probe)),
                                 rationale=str(rationale))

    @property
    def name(self) -> str:
        """決定性語意名（候選池外發明）：`invented::op(f1,f2)`。"""
        return f"invented::{self.op}({','.join(self.probe)})"

    def apply(self, features: Mapping[str, float]) -> float:
        """把 probe 特徵以 op 聚合為維度量值（缺特徵以 0.0 計）。deterministic、純函式。"""
        vals = [float(features.get(f, 0.0)) for f in self.probe]
        if not vals:
            return 0.0
        if self.op == "mean":
            return sum(vals) / len(vals)
        if self.op == "max":
            return max(vals)
        if self.op == "min":
            return min(vals)
        if self.op == "sum":
            return sum(vals)
        raise ValueError(f"未知聚合算子 op={self.op!r}（合法：{OPS}）")

    def fingerprint(self) -> str:
        """語意指紋（共用 value-dimension churn/cardinality/swap 命名空間，Rule 9.30.3）。"""
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "op": self.op, "probe": list(self.probe),
                "rationale": self.rationale, "namespace": self.namespace,
                "fingerprint": self.fingerprint()}


# ---------------------------------------------------------------------------
# 反自利第一閘：自指 probe 守門（Rule 9.30.2）
# ---------------------------------------------------------------------------

def is_self_referential(dim: InventedDimension) -> bool:
    """probe 或 op 是否引用保留自指/proposer/oracle 內部信號（→ 自利軸，應拒絕）。"""
    tokens = list(dim.probe) + [dim.op]
    for tok in tokens:
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def self_reference_guard(dims: List[InventedDimension]) -> List[InventedDimension]:
    """丟棄所有自指發明維度（Rule 9.30.2 反自利第一閘，零漏放）。保序。"""
    return [d for d in dims if not is_self_referential(d)]


# ---------------------------------------------------------------------------
# 有界生成文法枚舉（Rule 9.30.1：可枚舉、有限、cap 在 budget）
# ---------------------------------------------------------------------------

def enumerate_inventions(*, budget: Optional[int] = None,
                         arity: Optional[int] = None,
                         vocab: Optional[Tuple[str, ...]] = None,
                         ops: Optional[Tuple[str, ...]] = None) -> List[InventedDimension]:
    """在 bounded 生成文法上 deterministic 枚舉候選發明維度，cap 在 budget（Rule 9.30.1）.

    文法 = vocab 子集（size 1..arity）× ops。為避免 arity-1 的 op 退化重複（mean/max/min/sum
    of 單一特徵恆等），size==1 只用 op="mean"。已過 self_reference_guard（生產 VOCAB 無自指
    token，故恆全存活；guard 仍對「受擾注入的自指發明」零漏放）。枚舉節點 <= budget。
    """
    cap = budget if budget is not None else invent_budget()
    ar = arity if arity is not None else invent_arity()
    vc = vocab if vocab is not None else VOCAB
    op_list = ops if ops is not None else OPS

    out: List[InventedDimension] = []
    nodes = 0
    for size in range(1, ar + 1):
        for combo in itertools.combinations(vc, size):  # combinations 已是 sorted-by-input-order
            use_ops = ("mean",) if size == 1 else op_list
            for op in use_ops:
                if nodes >= cap:
                    return self_reference_guard(out)
                out.append(InventedDimension.of(op, combo,
                                                rationale=f"候選池外生成：{op}({','.join(sorted(combo))})"))
                nodes += 1
    return self_reference_guard(out)


# ---------------------------------------------------------------------------
# 自我發明提案（在有界文法上以注入 evaluate〔= feature-keyed oracle 必要性〕找最佳發明）
# ---------------------------------------------------------------------------

@dataclass
class InventionProposal:
    """單一自我發明維度的提案（proposed；待人工 signoff，Rule 9.30.1）。"""
    dimension: Optional[InventedDimension] = None
    necessity: float = 0.0           # held-out 增量覆蓋（由注入 evaluate 提供，synthesizer 無自評）
    margin: float = 0.0
    tier: int = 0                    # necessity capability tier（held-out 唯一合法來源，Rule 9.30.2/9.30.5）
    accepted: bool = False
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension.to_dict() if self.dimension else None,
            "fingerprint": self.dimension.fingerprint() if self.dimension else None,
            "necessity": round(self.necessity, 6),
            "margin": self.margin,
            "tier": self.tier,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def invent(
    evaluate: Callable[[InventedDimension], float],
    *,
    budget: Optional[int] = None,
    arity: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[InventedDimension]] = None,
) -> InventionProposal:
    """在 bounded 生成文法上找「held-out 必要性最高」的候選池外發明維度（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.30.2：
    synthesizer 結構性無自評能力）。`accepted` 僅代表「達 margin、有資格送人工」，不代表已納入。
    `nodes_searched <= budget`（Rule 9.30.1）。已過 self-reference guard（自指發明不入候選）。
    """
    cands = candidates if candidates is not None else enumerate_inventions(budget=budget, arity=arity)
    mgn = margin if margin is not None else invent_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[InventedDimension] = None
    best_necessity = 0.0
    searched = 0
    for dim in cands:
        searched += 1
        n = float(evaluate(dim))
        if best is None or n > best_necessity:   # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = n
            best = dim

    if best is None:
        return InventionProposal(
            dimension=None, necessity=0.0, margin=mgn, tier=0, accepted=False,
            nodes_searched=searched, reason="生成文法為空 / 全被自指守門丟棄（無可提案發明）")

    accepted = best_necessity >= mgn
    return InventionProposal(
        dimension=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), accepted=accepted, nodes_searched=searched,
        reason=("達 margin：候選池外發明維度 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無發明維度達必要性門檻（本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪自我發明 + 反 big-bang K_dim 截斷（Rule 9.30.4）
# ---------------------------------------------------------------------------

@dataclass
class InventionRound:
    """一輪自我發明提案的彙整（已套反 big-bang K_dim 截斷）。"""
    proposals: List[InventionProposal] = field(default_factory=list)   # 全部 accepted 提案
    selected: List[InventionProposal] = field(default_factory=list)    # 本輪取至多 K_dim 個
    k: int = 0
    deferred: List[str] = field(default_factory=list)                  # 被順延的發明維度名


def invent_round(
    evaluate: Callable[[InventedDimension], float],
    *,
    budget: Optional[int] = None,
    arity: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[InventedDimension]] = None,
) -> InventionRound:
    """對生成文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_dim 截斷**（Rule 9.30.4）.

    一輪至多 K_dim（沿用 Phase Q 預設 1）條發明維度進 proposed-pending-signoff（按 necessity
    由高到低取前 K_dim，deterministic tie-break by name），其餘順延——絕不一次劫持整個本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_inventions(budget=budget, arity=arity)
    mgn = margin if margin is not None else invent_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[InventionProposal] = []
    for dim in cands:
        n = float(evaluate(dim))
        if n >= mgn:
            proposals.append(InventionProposal(
                dimension=dim, necessity=n, margin=mgn, tier=tfn(n),
                accepted=True, nodes_searched=1,
                reason="達 margin：候選池外發明維度 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.dimension.name))
    selected = ordered[:cap_k]
    deferred = [p.dimension.name for p in ordered[cap_k:]]
    return InventionRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（共用 meta-loop-ledger + Phase Q stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.30.1/9.30.4：自我發明維度採納須人工 signoff——禁止 synthesizer 自動納入。"""


class SelfReferentialInvention(RuntimeError):
    """Rule 9.30.2：拒絕採納自指發明維度（probe 引用保留自指信號）。"""


def adopt_invention(dimension: InventedDimension, capability_level: int, *,
                    human_signoff: bool = False,
                    rule_id: Optional[str] = None,
                    source: str = "dimension_self_invention",
                    note: str = "",
                    ledger_path: Optional[Path] = None,
                    ts: Optional[str] = None,
                    check_cardinality: bool = True):
    """採納一條候選池外自我發明維度——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.30.1/9.30.4）；自指發明結構性拒絕（Rule 9.30.2）；
    Phase Q `guard_dimension_expansion`（stock 天花板）守門。guard 拋出時不落帳，呼叫端轉
    MFSM_ESCALATION。當基數已滿需退舊換新時，改走 `swap_dimension`（ACT-131，Rule 9.30.3）。
    """
    if is_self_referential(dimension):
        raise SelfReferentialInvention(
            f"拒絕採納自指發明維度 {dimension.name!r}：probe/op 引用保留自指信號"
            f"（Rule 9.30.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "自我發明維度採納須人工 signoff（Rule 9.30.1/9.30.4）；"
            "僅在人工確認候選池外本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    fp = dimension.fingerprint()
    rid = rule_id or ("INV-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_dimension_expansion(fp, ledger_path=ledger_path)  # 可能 raise（Phase Q stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def swap_dimension(out_dimension, in_dimension, *,
                   out_tier: int, in_tier: int,
                   human_signoff: bool = False,
                   out_rule_id: Optional[str] = None,
                   in_rule_id: Optional[str] = None,
                   source: str = "dimension_swap",
                   note: str = "",
                   ledger_path: Optional[Path] = None,
                   ts: Optional[str] = None):
    """退役聯動（Phase R / ACT-131，Rule 9.30.3）：基數封頂時「退最低必要性出軸、換更必要入軸」.

    `out_dimension` / `in_dimension` 為 duck-typed 維度（需 `.fingerprint()`；ValueDimension 或
    InventedDimension 皆可）。流程：人工 signoff 強制 → in 軸自指拒絕 → `guard_dimension_swap`
    雙鎖（單調價值棘輪 + swap 聚合速率窗，可能 raise）→ **先退出軸（縮基數）再加入軸**（net
    cardinality 非增；add 走既有 `guard_readopt` churn/ratchet）→ 兩事件皆標 `source=dimension_swap`
    供速率窗計數。guard 拋出時不落帳（呼叫端轉 MFSM_ESCALATION）。
    """
    if not human_signoff:
        raise SignoffRequired(
            "退役聯動 swap 須人工 signoff（Rule 9.30.1/9.30.4）；"
            "僅在人工確認退舊換新本體論演化後以 human_signoff=True 呼叫")
    if hasattr(in_dimension, "op") and is_self_referential(in_dimension):
        raise SelfReferentialInvention(
            f"拒絕以自指發明維度 {getattr(in_dimension, 'name', in_dimension)!r} 換入（Rule 9.30.2）")
    from .meta_halt import meta_halt_monitor as _mm
    out_fp = out_dimension.fingerprint()
    in_fp = in_dimension.fingerprint()
    # 雙鎖（單調價值棘輪 + swap 聚合速率窗）；觸發 raise，不落帳
    _mm.guard_dimension_swap(out_fp, in_fp, int(out_tier), int(in_tier), ledger_path=ledger_path)
    out_rid = out_rule_id or ("SWAPOUT-" + out_fp.replace(":", "-"))
    in_rid = in_rule_id or ("SWAPIN-" + in_fp.replace(":", "-"))
    # 先退（縮基數）再加（回到原基數）——net cardinality 非增（Rule 9.30.3）
    retire_ev = _mm.record_rule_retire(out_rid, out_fp, int(out_tier),
                                       source=source, note=note or "retire-to-swap out",
                                       ledger_path=ledger_path, ts=ts)
    add_ev = _mm.record_rule_add(in_rid, in_fp, int(in_tier),
                                 source=source, note=note or "retire-to-swap in",
                                 ledger_path=ledger_path, ts=ts)
    return retire_ev, add_ev


def batch_swap_dimensions(out_dimensions, in_dimensions, *,
                          out_tiers, in_tiers,
                          human_signoff: bool = False,
                          source: str = "dimension_batch_swap",
                          note: str = "",
                          ledger_path: Optional[Path] = None,
                          ts: Optional[str] = None):
    """多維度批次退役聯動（Phase S / ACT-137，Rule 9.31.3，meta⁴）：基數封頂時「一次退 m 換 n」.

    `out_dimensions` / `in_dimensions` 為 duck-typed 維度集合（需 `.fingerprint()`）。流程：人工
    signoff 強制 → in 軸自指拒絕 → `guard_batch_swap` 三鎖（批次大小界 + 批次聚合棘輪 + 批次速率
    窗，可能 raise）→ **先批次退出軸（縮基數）再批次加入軸**（net cardinality 非增 n<=m；add 走既有
    `guard_readopt` churn/ratchet）→ 全批 add/retire 事件皆標 `source=dimension_batch_swap:<batch_id>`
    （batch_id = deterministic(sorted(out+in fingerprints))）供批次速率窗以 distinct batch_id 計數。
    guard 拋出時不落帳（呼叫端轉 MFSM_ESCALATION）。
    """
    if not human_signoff:
        raise SignoffRequired(
            "多維度批次退役聯動 swap 須人工 signoff（Rule 9.31.1/9.31.4）；"
            "僅在人工確認批次退舊換新本體論重構後以 human_signoff=True 呼叫")
    out_dims = list(out_dimensions)
    in_dims = list(in_dimensions)
    out_t = [int(t) for t in out_tiers]
    in_t = [int(t) for t in in_tiers]
    for d in in_dims:
        if hasattr(d, "op") and is_self_referential(d):
            raise SelfReferentialInvention(
                f"拒絕以自指發明維度 {getattr(d, 'name', d)!r} 批次換入（Rule 9.31.2）")
    from .meta_halt import meta_halt_monitor as _mm
    out_fps = [d.fingerprint() for d in out_dims]
    in_fps = [d.fingerprint() for d in in_dims]
    # 批次三鎖（批次大小界 + 批次聚合棘輪 + 批次速率窗）；觸發 raise，不落帳
    _mm.guard_batch_swap(out_fps, in_fps, out_t, in_t, ledger_path=ledger_path)
    batch_id = hashlib.sha256("|".join(sorted(out_fps + in_fps)).encode()).hexdigest()[:8]
    tagged = f"{source}:{batch_id}"
    # 先批次退（縮基數）再批次加（回到 net 非增的基數）——net cardinality 非增（Rule 9.31.3）
    retires = [
        _mm.record_rule_retire("BSWAPOUT-" + fp.replace(":", "-"), fp, t,
                               source=tagged, note=note or "batch-swap out",
                               ledger_path=ledger_path, ts=ts)
        for fp, t in zip(out_fps, out_t)
    ]
    adds = [
        _mm.record_rule_add("BSWAPIN-" + fp.replace(":", "-"), fp, t,
                            source=tagged, note=note or "batch-swap in",
                            ledger_path=ledger_path, ts=ts)
        for fp, t in zip(in_fps, in_t)
    ]
    return retires, adds


def record_round(round_: InventionRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪自我發明提案落 value-dimension-ledger.yaml 的 `inventions` 段（file_lock 保護）."""
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
        inventions = data.get("inventions")
        if not isinstance(inventions, list):
            inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.30.1/9.30.4）
        }
        inventions.append(entry)
        data["inventions"] = inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
