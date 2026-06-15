"""Phase T / ACT-141 — Operator Genesis Grammar（轉換算子文法的自我擴充，meta⁵）.

對應藍圖：SDD_improving_Automation_20.md §1.1 / §3.1 ACT-141 / Rule 9.32.1 / 9.32.2 / 9.32.3 / 9.32.4。

Phase S 證了「系統可在**固定轉換算子** `TRANSFORMS`（vocabulary_genesis.TRANSFORMS，6 條硬編：
rate/window/depth/delta/ratio/count；維度聚合 dimension_semantics_synthesizer.OPS，4 條硬編：
mean/max/min/sum）上**自我發明 VOCAB 外的新原始特徵『字』**」。但 Phase S 的被發明物本質上是
**『標籤 / 資料』**——`transform` 只是個字串，真正的『計算』永遠是那 6+4 條人類寫死、保證全函式、
保證 O(n) 停機的運算。本模組把骨架**升維**：從「在固定算子上發明詞彙」升到「**自我發明一個
TRANSFORMS/OPS 裡根本沒有的全新轉換/聚合算子語意**」。這是 meta⁵ 層——系統自己**寫算子**（=寫一段
會被嵌進評估迴圈反覆執行的計算）。

**算子可計算性是本模組的靈魂與最深停機紅線（Rule 9.32.3，前所有 Phase 不存在的危害）**：Phase Q/R/S
的被發明物都是「資料」，執行它們的是人類寫死全函式；Phase T 的被發明物是「算子」=「可執行計算」。
若允許任意計算，自我發明的算子可**非全函式**（某輸入無定義/拋例外）、**無界步數**（隱含遞迴/迴圈）、
甚至**不停機**——這正是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充的產物本身。本模組用一條
**有界算子生成文法**結構性兌現「算子可計算性需另證有界」：

  - `PRIMITIVES`（有限、全 total list-reduction、O(n) 一遍掃描、零遞迴零迴圈）：mean/max/min/sum/
    range/median/mad/last——對任何輸入（含空）皆有定義、永不拋例外。
  - `COMBINATORS`（有限、全 total）：identity/abs/neg/clip01/sq（一元後變換）+ diff/ratio_safe/max2/
    min2（有界元數二元組合，ratio_safe 對 0 分母回退）。
  - 一個算子 = **有界深度（<=2）的運算式樹**，故 `cost()` 結構性 <= 常數（一元 2 / 二元 3）<=
    `SDD_DIM_OP_STEP_MAX`——**每個被發明的算子可證停機（全函式 + 有界步數），而整個閉環仍靠
    LLM+紙帶維持圖靈完備**。把可執行計算刻意設計成 sub-Turing 的有限代數。

**「TRANSFORMS/OPS 外」≠「無界」（Rule 9.32.1 有界算子生成文法）**：生成空間 = `PRIMITIVES`（有限）×
`COMBINATORS`（有限）→ 可枚舉、有限，列舉節點 <= `SDD_DIM_OP_BUDGET`（clamp[8,128]，預設 32），
**絕不指數爆炸**。

**反自利雙閘第一閘（Rule 9.32.2 算子自指守門）**：任何 primitive/combinator/secondary/probe 引用保留
自指/proposer/oracle 內部信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的算子，在送 oracle
前即被 `operator_self_reference_guard` **結構性拒絕**（零漏放）——系統不能發明一個「計算自己核可」的
自利算子。

**承 Phase S 的反 Goodhart 對抗分離（Rule 9.32.2，結構基石）**：本模組**結構性不持有任何必要性判據、
不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 算子生成文法上枚舉 `GenesisOperator`，
再透過呼叫端**注入的 `evaluate` 回呼**取每個發明算子的必要性。genesis 因此**無法用自己的尺規證明自己
必要**。

**反 big-bang 算子發明（Rule 9.32.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q/R/S，預設 1）個
算子發明可進 proposed-pending-signoff，絕不一次劫持整個算子本體論。**advisory（Rule 9.32.1）**：只產
`proposed` 算子，任一納入必經人工 signoff；本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網、算子求值路徑零 `while`/零遞迴/零自呼叫（守 OPEN-10.6 + Rule 9.32.3）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Mapping, Optional, Sequence, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT
# 沿用 synthesizer 的保留自指信號集 + 既有 OPS / VOCAB（synthesizer 結構性不 import oracle，故
# 透過它取得這些常數不會把 oracle 牽連進來，對抗分離不破）。
from .dimension_semantics_synthesizer import OPS as _BASE_OPS, RESERVED_SELF_REF, VOCAB as _BASE_VOCAB
from .value_dimension_registry import dim_expand_k

# operator-genesis 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾、亦非
# `value-dimension:` / `vocab-genesis:`，故與 calibration 聚合速率、維度/詞彙 stock 天花板互不干涉，
# Rule 9.32.4 分開治理）。
OPERATOR_GENESIS_NAMESPACE = "operator-genesis:"

# === 自我發明領域審計帳本（沿用 Phase R/S 的 value-dimension-ledger，增 operator_inventions 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界算子生成文法（Rule 9.32.1/9.32.3：TRANSFORMS/OPS 外生成被有限文法封住、可枚舉、全函式、有界步數）===
# PRIMITIVES：有限原始算子（list[float] -> float，全 total、O(n) 一遍掃描、零遞迴零迴圈）。
PRIMITIVES: Tuple[str, ...] = (
    "mean", "max", "min", "sum", "range", "median", "mad", "last",
)

# COMBINATORS：有限組合算子。一元（作用於 primary 輸出）+ 二元（需 secondary primitive）。
UNARY_COMBINATORS: Tuple[str, ...] = ("identity", "abs", "neg", "clip01", "sq")
BINARY_COMBINATORS: Tuple[str, ...] = ("diff", "ratio_safe", "max2", "min2")
COMBINATORS: Tuple[str, ...] = UNARY_COMBINATORS + BINARY_COMBINATORS

# 預設參照 probe（base VOCAB 子集；OPR 必要性語料以此為錨——量「新算子在固定 probe 上的增量覆蓋」）。
REFERENCE_PROBE: Tuple[str, ...] = tuple(_BASE_VOCAB[:3])  # rollback_steps / blast_radius / canary_gap

_DEFAULT_OP_BUDGET = 32
_OP_BUDGET_CLAMP = (8, 128)

# 算子可計算性步數上限（Rule 9.32.3：每個算子 cost() 須 <= 此值；有界深度文法結構性保證 <=3）。
_DEFAULT_OP_STEP_MAX = 8
_OP_STEP_MAX_CLAMP = (1, 64)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def op_budget() -> int:
    """讀 SDD_DIM_OP_BUDGET（env 可調），clamp[8,128]，預設 32（Rule 9.32.1 有界算子生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_OP_BUDGET"), _DEFAULT_OP_BUDGET, _OP_BUDGET_CLAMP)


def op_step_max() -> int:
    """讀 SDD_DIM_OP_STEP_MAX（env 可調），clamp[1,64]，預設 8（Rule 9.32.3 算子可計算性步數上限）。"""
    return _clamp_int(os.environ.get("SDD_DIM_OP_STEP_MAX"), _DEFAULT_OP_STEP_MAX, _OP_STEP_MAX_CLAMP)


def op_coverage_margin() -> float:
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
# 原始算子 / 組合算子求值（全 total、零遞迴零迴圈於語意；唯一的 for 是 O(n) 一遍聚合）
# ---------------------------------------------------------------------------

# 浮點上限飽和界（Rule 9.32.3 算子可計算性）：把 ±inf 飽和到有限大值、NaN 歸零，使任何算子
# apply() 對任何輸入（含極大輸入導致 overflow，如 sq(1e308)）皆結構性恆回**有限 float**——
# 兌現「算子無 NaN/inf（全函式）」的宣稱。正常範圍（|x| 遠小於 1e300）值不受影響、deterministic。
_FINITE_BOUND = 1e300


def _finite(x: float) -> float:
    """把任意 float 投影到有限域：+inf→1e300、-inf→-1e300、nan→0.0、其餘原樣回傳（Rule 9.32.3）。"""
    if x != x:            # NaN
        return 0.0
    if x == math.inf:
        return _FINITE_BOUND
    if x == -math.inf:
        return -_FINITE_BOUND
    return x


def _prim(name: str, vals: Sequence[float]) -> float:
    """原始算子求值（list[float] -> float）。**全 total**：空輸入回 0.0、回值經 `_finite` 投影故恆有限、
    永不拋例外（Rule 9.32.3）。

    每個 primitive 為單次 O(n) 聚合（一遍掃描，無遞迴、無 while、無對輸入規模的巢狀迴圈）。
    """
    xs = [float(v) for v in vals]
    if not xs:
        return 0.0
    if name == "mean":
        return _finite(sum(xs) / len(xs))
    if name == "max":
        return _finite(max(xs))
    if name == "min":
        return _finite(min(xs))
    if name == "sum":
        return _finite(float(sum(xs)))
    if name == "range":
        return _finite(max(xs) - min(xs))
    if name == "median":
        s = sorted(xs)
        n = len(s)
        mid = n // 2
        return _finite(s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0)
    if name == "mad":  # mean absolute deviation
        m = sum(xs) / len(xs)
        return _finite(sum(abs(x - m) for x in xs) / len(xs))
    if name == "last":
        return _finite(xs[-1])
    raise ValueError(f"未知原始算子 primitive={name!r}（合法：{PRIMITIVES}）")


def _comb(name: str, a: float, b: Optional[float] = None) -> float:
    """組合算子求值。**全 total**：ratio_safe 對 0 分母回退、回值經 `_finite` 投影故恆有限（如
    sq(1e308) overflow→飽和到 1e300）、永不拋例外（Rule 9.32.3）。"""
    a = float(a)
    if name == "identity":
        return _finite(a)
    if name == "abs":
        return _finite(abs(a))
    if name == "neg":
        return _finite(-a)
    if name == "clip01":
        return _finite(0.0 if a < 0.0 else (1.0 if a > 1.0 else a))
    if name == "sq":
        return _finite(a * a)
    # 二元（需 b）
    bb = 0.0 if b is None else float(b)
    if name == "diff":
        return _finite(a - bb)
    if name == "ratio_safe":
        return _finite(a / bb if bb != 0.0 else 0.0)   # total：0 分母回退（反非全函式）
    if name == "max2":
        return _finite(max(a, bb))
    if name == "min2":
        return _finite(min(a, bb))
    raise ValueError(f"未知組合算子 combinator={name!r}（合法：{COMBINATORS}）")


def is_binary_combinator(name: str) -> bool:
    return name in BINARY_COMBINATORS


# ---------------------------------------------------------------------------
# 自我發明算子（一個 TRANSFORMS/OPS 外、現場由算子文法生成的新轉換/聚合算子）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenesisOperator:
    """一個 TRANSFORMS/OPS 外、由 bounded 算子生成文法現場發明的新算子（meta⁵ 製品）.

    算子 = 有界深度運算式樹：`combinator(primary[, secondary])` 作用於 `probe` 特徵聚合值。
    - 一元 combinator：result = comb( prim(primary, probe_vals) )
    - 二元 combinator：result = comb( prim(primary, probe_vals), prim(secondary, probe_vals) )

    apply(features) 把 probe 特徵以算子聚合為一個純量——**全函式**（空輸入回 0.0、ratio_safe 0
    分母回退、無例外），供 oracle 在 feature-grounded 現實情節上現算 dim_value（oracle 可知本型別，
    反向不可——genesis 不 import oracle）。cost() = primitive 評估 + combinator 運算次數（結構性 <=3，
    Rule 9.32.3 算子可計算性）。fingerprint 落在 `operator-genesis:` 命名空間（Rule 9.32.4），與
    維度/詞彙/scorer-profile 分開治理（算子走獨立 stock 天花板 OperatorGenesisBounded）。
    """
    primary: str
    combinator: str = "identity"
    secondary: str = ""               # 僅二元 combinator 用；一元時為 ""
    probe: Tuple[str, ...] = REFERENCE_PROBE
    rationale: str = ""
    namespace: str = OPERATOR_GENESIS_NAMESPACE

    @staticmethod
    def of(primary: str, combinator: str = "identity", secondary: str = "",
           probe: Optional[Sequence[str]] = None, rationale: str = "") -> "GenesisOperator":
        pr = tuple(str(p) for p in (probe if probe is not None else REFERENCE_PROBE))
        sec = str(secondary) if is_binary_combinator(combinator) else ""
        return GenesisOperator(primary=str(primary), combinator=str(combinator),
                               secondary=sec, probe=pr, rationale=str(rationale))

    @property
    def name(self) -> str:
        """決定性語意名（TRANSFORMS/OPS 外發明）：`op::comb(primary[,secondary])@probe`。"""
        inner = self.primary if not is_binary_combinator(self.combinator) else f"{self.primary},{self.secondary}"
        return f"op::{self.combinator}({inner})@{'+'.join(self.probe)}"

    def apply(self, features: Mapping[str, float]) -> float:
        """把 probe 特徵以算子聚合為純量（缺特徵以 0.0 計）。**全函式、deterministic、有界步數**。"""
        vals = [float(features.get(f, 0.0)) for f in self.probe]
        a = _prim(self.primary, vals)
        if is_binary_combinator(self.combinator):
            b = _prim(self.secondary or self.primary, vals)
            return _comb(self.combinator, a, b)
        return _comb(self.combinator, a)

    def cost(self) -> int:
        """算子計算步數（Rule 9.32.3）：primitive 評估數 + 1 個 combinator 運算。一元=2、二元=3。

        結構性有界——算子是有界深度（<=2）運算式樹，無遞迴、無迴圈，故 cost 恆為小常數。
        """
        prim_evals = 2 if is_binary_combinator(self.combinator) else 1
        return prim_evals + 1

    def is_total(self, *, samples: Optional[List[List[float]]] = None) -> bool:
        """全函式驗證（Rule 9.32.3）：對極端輸入 fuzz，apply 永不拋例外。

        既然由 total PRIMITIVES × total COMBINATORS 組成，這在結構上恆真；本方法以 fuzz 把
        「結構保證」轉成「可機器驗證的客觀守門」（guard_operator_computability 呼叫）。
        """
        fuzz = samples if samples is not None else _FUZZ_VALUE_SETS
        for vals in fuzz:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(self.probe)}
            try:
                r = self.apply(feats)
            except Exception:   # noqa: BLE001 — 任何例外 = 非全函式
                return False
            if r != r or r in (math.inf, -math.inf):   # NaN / inf 視為非全函式
                return False
        return True

    def fingerprint(self) -> str:
        """語意指紋（operator-genesis stock 命名空間，Rule 9.32.4）。"""
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "primary": self.primary, "combinator": self.combinator,
                "secondary": self.secondary, "probe": list(self.probe), "cost": self.cost(),
                "rationale": self.rationale, "namespace": self.namespace,
                "fingerprint": self.fingerprint()}


# 全函式 fuzz 輸入集（極端：空/單元素/負/0/極大含浮點上限/混合）——供 is_total /
# guard_operator_computability。含接近浮點上限的樣本（1e200/1e308），使 fuzz 真正覆蓋 overflow 邊界
# （如 sq(1e308) → a*a overflow），驗證 `_finite` 飽和投影令 apply 結構性恆回有限 float（Rule 9.32.3）。
_FUZZ_VALUE_SETS: List[List[float]] = [
    [], [0.0], [0.0, 0.0, 0.0], [-5.0], [1e18, -1e18], [0.0, 1.0, -1.0],
    [3.5], [2.0, 2.0], [-1.0, 0.0, 1.0, 1e9], [1e-18, 0.0],
    [1e200, -1e200], [1e308], [1e308, 1e308, 1e308], [-1e308, 1e308],
    [1e154, 1e154], [1e300, 1e300, -1e300],
]


# ---------------------------------------------------------------------------
# 反自利第一閘：算子自指守門（Rule 9.32.2）
# ---------------------------------------------------------------------------

def is_operator_self_referential(go: GenesisOperator) -> bool:
    """primary/combinator/secondary/probe 是否引用保留自指/proposer/oracle 內部信號（→ 自利算子）。"""
    tokens = [go.primary, go.combinator, go.secondary] + list(go.probe)
    for tok in tokens:
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def operator_self_reference_guard(ops: List[GenesisOperator]) -> List[GenesisOperator]:
    """丟棄所有自指算子（Rule 9.32.2 反自利第一閘，零漏放）。保序。"""
    return [o for o in ops if not is_operator_self_referential(o)]


# ---------------------------------------------------------------------------
# 有界算子生成文法枚舉（Rule 9.32.1：可枚舉、有限、cap 在 budget；每個算子結構性全函式 + 有界步數）
# ---------------------------------------------------------------------------

def enumerate_genesis_operators(*, budget: Optional[int] = None,
                                probe: Optional[Sequence[str]] = None,
                                primitives: Optional[Tuple[str, ...]] = None,
                                combinators: Optional[Tuple[str, ...]] = None) -> List[GenesisOperator]:
    """在 bounded 算子生成文法上 deterministic 枚舉候選算子，cap 在 budget（Rule 9.32.1）.

    文法 = primitives × combinators（二元 combinator 另配 secondary primitive）。固定 probe（量「新
    算子在固定 probe 上的增量覆蓋」以隔離算子貢獻）。已過 operator_self_reference_guard（生產
    PRIMITIVES/COMBINATORS 無自指 token，故恆全存活；guard 仍對「受擾注入的自指算子」零漏放）。
    枚舉節點 <= budget。**每個產出算子結構性全函式 + cost<=3**（有界深度運算式樹）。
    """
    cap = budget if budget is not None else op_budget()
    pr = tuple(probe) if probe is not None else REFERENCE_PROBE
    prims = primitives if primitives is not None else PRIMITIVES
    combs = combinators if combinators is not None else COMBINATORS

    out: List[GenesisOperator] = []
    nodes = 0
    for comb in combs:
        if is_binary_combinator(comb):
            for p, s in itertools.product(prims, prims):
                if p == s:
                    continue   # 二元組合兩臂相同退化（diff→0、ratio_safe→1…），跳過
                if nodes >= cap:
                    return operator_self_reference_guard(out)
                out.append(GenesisOperator.of(p, comb, secondary=s, probe=pr,
                                              rationale=f"算子外生成：{comb}({p},{s})"))
                nodes += 1
        else:
            for p in prims:
                if nodes >= cap:
                    return operator_self_reference_guard(out)
                out.append(GenesisOperator.of(p, comb, probe=pr,
                                              rationale=f"算子外生成：{comb}({p})"))
                nodes += 1
    return operator_self_reference_guard(out)


def expanded_ops(accepted_operator_names) -> Tuple[str, ...]:
    """meta⁵ 對 meta-meta-meta 的供料：基礎 OPS ∪ 已採納算子發明名（deterministic 去重保序）.

    synthesizer 之後可在這擴充後的算子上組合維度（把 Phase R 的固定 OPS 換成 expanded_ops）。
    """
    seen = list(_BASE_OPS)
    for nm in accepted_operator_names:
        if nm not in seen:
            seen.append(str(nm))
    return tuple(seen)


# ---------------------------------------------------------------------------
# 算子自我發明提案（在有界算子文法上以注入 evaluate〔= feature-grounded oracle 必要性〕找最佳）
# ---------------------------------------------------------------------------

@dataclass
class OperatorProposal:
    """單一算子發明的提案（proposed；待人工 signoff，Rule 9.32.1）。"""
    operator: Optional[GenesisOperator] = None
    necessity: float = 0.0           # held-out 增量覆蓋（由注入 evaluate 提供，genesis 無自評）
    margin: float = 0.0
    tier: int = 0                    # necessity capability tier（held-out 唯一合法來源，Rule 9.32.2/9.32.5）
    cost: int = 0                    # 算子計算步數（Rule 9.32.3 可計算性證據）
    accepted: bool = False
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "operator": self.operator.to_dict() if self.operator else None,
            "fingerprint": self.operator.fingerprint() if self.operator else None,
            "necessity": round(self.necessity, 6),
            "margin": self.margin,
            "tier": self.tier,
            "cost": self.cost,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def operator_genesis(
    evaluate: Callable[[GenesisOperator], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[GenesisOperator]] = None,
) -> OperatorProposal:
    """在 bounded 算子生成文法上找「held-out 必要性最高」的 TRANSFORMS/OPS 外算子發明（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.32.2：genesis
    結構性無自評能力）。`accepted` 僅代表「達 margin、有資格送人工」，不代表已納入。
    `nodes_searched <= budget`（Rule 9.32.1）。已過 operator self-reference guard（自指算子不入候選）。
    """
    cands = candidates if candidates is not None else enumerate_genesis_operators(budget=budget)
    mgn = margin if margin is not None else op_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[GenesisOperator] = None
    best_necessity = 0.0
    searched = 0
    for go in cands:
        searched += 1
        n = float(evaluate(go))
        if best is None or n > best_necessity:   # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = n
            best = go

    if best is None:
        return OperatorProposal(
            operator=None, necessity=0.0, margin=mgn, tier=0, cost=0, accepted=False,
            nodes_searched=searched, reason="算子文法為空 / 全被自指守門丟棄（無可提案算子）")

    accepted = best_necessity >= mgn
    return OperatorProposal(
        operator=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), cost=best.cost(), accepted=accepted, nodes_searched=searched,
        reason=("達 margin：TRANSFORMS/OPS 外算子發明 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無算子發明達必要性門檻（算子本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪算子自我發明 + 反 big-bang K_op 截斷（Rule 9.32.4）
# ---------------------------------------------------------------------------

@dataclass
class OperatorRound:
    """一輪算子自我發明提案的彙整（已套反 big-bang K_op 截斷）。"""
    proposals: List[OperatorProposal] = field(default_factory=list)   # 全部 accepted 提案
    selected: List[OperatorProposal] = field(default_factory=list)    # 本輪取至多 K_op 個
    k: int = 0
    deferred: List[str] = field(default_factory=list)                 # 被順延的算子發明名


def operator_genesis_round(
    evaluate: Callable[[GenesisOperator], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[GenesisOperator]] = None,
) -> OperatorRound:
    """對算子文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_op 截斷**（Rule 9.32.4）.

    一輪至多 K_op（沿用 Phase Q/R/S 預設 1）個算子發明進 proposed-pending-signoff（按 necessity 由高
    到低取前 K_op，deterministic tie-break by name），其餘順延——絕不一次劫持整個算子本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_genesis_operators(budget=budget)
    mgn = margin if margin is not None else op_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[OperatorProposal] = []
    for go in cands:
        n = float(evaluate(go))
        if n >= mgn:
            proposals.append(OperatorProposal(
                operator=go, necessity=n, margin=mgn, tier=tfn(n), cost=go.cost(),
                accepted=True, nodes_searched=1,
                reason="達 margin：TRANSFORMS/OPS 外算子發明 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.operator.name))
    selected = ordered[:cap_k]
    deferred = [p.operator.name for p in ordered[cap_k:]]
    return OperatorRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（可計算性守門 + 共用 meta-loop-ledger + 算子 stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.32.1/9.32.4：算子發明採納須人工 signoff——禁止 genesis 自動納入。"""


class SelfReferentialOperator(RuntimeError):
    """Rule 9.32.2：拒絕採納自指算子（primary/combinator/secondary/probe 引用保留自指信號）。"""


def adopt_genesis_operator(operator: GenesisOperator, capability_level: int, *,
                           human_signoff: bool = False,
                           rule_id: Optional[str] = None,
                           source: str = "operator_genesis",
                           note: str = "",
                           ledger_path: Optional[Path] = None,
                           ts: Optional[str] = None,
                           check_cardinality: bool = True,
                           check_computability: bool = True):
    """採納一個 TRANSFORMS/OPS 外算子發明——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.32.1/9.32.4）；自指算子結構性拒絕（Rule 9.32.2）；
    `guard_operator_computability`（可計算性：cost<=step_max + fuzz-total，Rule 9.32.3）+
    `guard_operator_genesis`（算子 stock 天花板，Rule 9.32.4）守門。guard 拋出時不落帳，呼叫端轉
    MFSM_ESCALATION。
    """
    if is_operator_self_referential(operator):
        raise SelfReferentialOperator(
            f"拒絕採納自指算子 {operator.name!r}：primary/combinator/secondary/probe 引用保留自指信號"
            f"（Rule 9.32.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "算子發明採納須人工 signoff（Rule 9.32.1/9.32.4）；"
            "僅在人工確認 TRANSFORMS/OPS 外算子計算本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    if check_computability:
        _mm.guard_operator_computability(operator, ledger_path=ledger_path)  # 可能 raise（可計算性）
    fp = operator.fingerprint()
    rid = rule_id or ("OPR-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_operator_genesis(fp, ledger_path=ledger_path)  # 可能 raise（算子 stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def record_round(round_: OperatorRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪算子自我發明提案落 value-dimension-ledger.yaml 的 `operator_inventions` 段（file_lock 保護）."""
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
        operator_inventions = data.get("operator_inventions")
        if not isinstance(operator_inventions, list):
            operator_inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.32.1/9.32.4）
        }
        operator_inventions.append(entry)
        data["operator_inventions"] = operator_inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
