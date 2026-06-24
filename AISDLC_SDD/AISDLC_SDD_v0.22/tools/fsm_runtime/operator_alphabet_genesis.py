"""Phase U / ACT-147 — Operator Alphabet Genesis Grammar（組合算子文法的自我擴充，meta⁶）.

對應藍圖：SDD_improving_Automation_21.md §1.1 / §1.2 / §3.1 ACT-147 / Rule 9.33.1 / 9.33.2 / 9.33.3 / 9.33.4。

Phase T 證了「系統可在**固定算子字母表** `PRIMITIVES`（operator_genesis.PRIMITIVES，8 條硬編：mean/max/
min/sum/range/median/mad/last）+ `COMBINATORS`（9 條硬編：identity/abs/neg/clip01/sq + diff/ratio_safe/
max2/min2）之上**自我發明 TRANSFORMS/OPS 外的新算子**」。但 Phase T 的「每個被發明算子全函式 + 有界步數」
之所以成立，其證明的**地基**是『字母表 `PRIMITIVES`/`COMBINATORS` 本身被人類凍結、逐條手證過全 total +
O(n) + cost-1』。本模組把骨架**升維**：從「在固定字母表上發明算子」升到「**自我發明一個 `PRIMITIVES`/
`COMBINATORS` 字母表裡根本沒有的全新原始算子/組合算子（= 擴充算子生成文法的字母表本身）**」。這是 meta⁶
層——系統自己**寫『會被算子生成文法用來生成每一個算子的最底層運算原子』**。

**可計算性閉包是本模組的靈魂與最深停機紅線（Rule 9.33.3，ComputabilityClosure）**：Phase T 的被發明物是
「一個算子」，其可計算性是**逐個產物**檢查；Phase U 的被發明物是「字母表元素」=「**會被文法用來生成整個
算子代數的生成規則零件**」。一個非全函式 / 非 O(n) / 隱含遞迴的字母原子，被文法用後會污染**整代數**。故
可計算性須由『單一算子可證停機』升級為**閉包性質**：擴充字母表 A→A' 後，文法 G(A') 生成的整個（仍有限
的）算子代數中**每一個算子**仍全函式 + 有界步數——「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充的
**生成規則本身（meta⁶）**而非僅其產物。本模組用一條**有界字母表生成文法**結構性兌現「可計算性閉包需另證
有界」：

  - `ATOM_REDUCERS`（有限、全 total list-reduction、O(n) 單遍累積、零遞迴零迴圈、cost-1）：
    acc_sum/acc_count/acc_sumabs/acc_sumsq/acc_max/acc_min/acc_first——對任何輸入（含空）皆有定義。
  - `POST_MAPS`（有限、全 total 純量後變換）：identity/sqrt_safe/recip_safe/log1p_safe/clip01/negate
    （sqrt_safe 對負數取 abs、recip_safe 對 0 回退、log1p_safe 對 <=-1 回退）。
  - `BINARY_ATOMS`（有限、全 total 二元原子、cost-1）：wmean/hypot/geo_safe/harmonic_safe/absdiff
    （geo_safe/harmonic_safe 對非法域回退）。
  - 一個被發明 primitive = `post_map ∘ base_reducer`（list[float]->float，全函式、單遍、cost-1）；
    一個被發明 combinator = 一元 POST_MAP 或二元 BINARY_ATOM（純量運算、cost-1）。
  - **可計算性閉包定理**：若被發明字母由 total 原子組成，則擴充字母表後 G(A') 整代數每個算子仍 total +
    cost<=3（total 的合成仍 total；cost=prim_evals+1）——**可計算性在字母表擴充下封閉**。`verify_computability_closure`
    把此閉包**可機器驗證化**（枚舉 G(A') 整代數 fuzz-total + cost<=step_max）。

**「PRIMITIVES/COMBINATORS 外」≠「無界」（Rule 9.33.1 有界字母表生成文法）**：生成空間 = `ATOM_REDUCERS`
（有限）× `POST_MAPS`（有限）+ `BINARY_ATOMS`（有限）→ 可枚舉、有限，列舉節點 <= `SDD_DIM_ALPHABET_BUDGET`
（clamp[8,128]，預設 32），**絕不指數爆炸**。

**反自利雙閘第一閘（Rule 9.33.2 字母自指守門）**：任何 base_reducer/post_map/binary_atom/probe 引用保留
自指/proposer/oracle 內部信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的字母，在送 oracle
前即被 `alphabet_self_reference_guard` **結構性拒絕**（零漏放）。

**承 Phase T 的反 Goodhart 對抗分離（Rule 9.33.2，結構基石）**：本模組**結構性不持有任何必要性判據、
不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 字母表生成文法上枚舉字母元素，再透過
呼叫端**注入的 `evaluate` 回呼**取每個發明字母的必要性。

**反 big-bang 字母發明（Rule 9.33.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q/R/S/T，預設 1）個字母
發明可進 proposed-pending-signoff。**advisory（Rule 9.33.1）**：只產 `proposed` 字母，任一納入必經人工
signoff；本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網、字母求值路徑零 `while`/零遞迴/零自呼叫（守 OPEN-10.6 + Rule 9.33.3）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT
# 沿用 operator_genesis 的飽和投影 / fuzz 集 / 參照 probe / 保留自指信號 / 既有字母表（operator_genesis
# 結構性不 import oracle，故透過它取這些常數不會把 oracle 牽連進來，對抗分離不破；且 operator_genesis
# 不 import 本模組，依賴單向：alphabet → operator → synthesizer）。
from . import operator_genesis as _og
from .operator_genesis import _finite, _FUZZ_VALUE_SETS, REFERENCE_PROBE, RESERVED_SELF_REF
from .value_dimension_registry import dim_expand_k

# alphabet-genesis 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾、亦非
# `value-dimension:` / `vocab-genesis:` / `operator-genesis:`，故與既有各 stock 天花板互不干涉，
# Rule 9.33.4 分開治理）。
ALPHABET_GENESIS_NAMESPACE = "alphabet-genesis:"

# === 自我發明領域審計帳本（沿用 Phase R/S/T 的 value-dimension-ledger，增 alphabet_inventions 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界字母表生成文法（Rule 9.33.1/9.33.3：PRIMITIVES/COMBINATORS 外字母被有限文法封住、可枚舉、可計算性閉包）===
# ATOM_REDUCERS：有限原始歸約器（list[float] -> float，全 total、O(n) 單遍累積、零遞迴零迴圈、cost-1）。
ATOM_REDUCERS: Tuple[str, ...] = (
    "acc_sum", "acc_count", "acc_sumabs", "acc_sumsq", "acc_max", "acc_min", "acc_first",
)

# POST_MAPS：有限後變換（float -> float，全 total）。
POST_MAPS: Tuple[str, ...] = (
    "identity", "sqrt_safe", "recip_safe", "log1p_safe", "clip01", "negate",
)

# BINARY_ATOMS：有限二元原子（(float, float) -> float，全 total、cost-1）。
BINARY_ATOMS: Tuple[str, ...] = (
    "wmean", "hypot", "geo_safe", "harmonic_safe", "absdiff",
)

# 被發明 combinator 的二元 apply 參照原始算子（供 oracle 把二元字母轉成 probe 上的純量）。
_COMB_REF_A = "max"
_COMB_REF_B = "min"
_COMB_REF_UNARY = "mean"

_DEFAULT_ALPHABET_BUDGET = 32
_ALPHABET_BUDGET_CLAMP = (8, 128)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def alphabet_budget() -> int:
    """讀 SDD_DIM_ALPHABET_BUDGET（env 可調），clamp[8,128]，預設 32（Rule 9.33.1 有界字母表生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_ALPHABET_BUDGET"),
                      _DEFAULT_ALPHABET_BUDGET, _ALPHABET_BUDGET_CLAMP)


def alphabet_coverage_margin() -> float:
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
# 字母原子求值（全 total、零遞迴零迴圈於語意；唯一的 for 是 O(n) 一遍累積）
# ---------------------------------------------------------------------------

def _reduce(name: str, vals: Sequence[float]) -> float:
    """原始歸約器求值（list[float] -> float）。**全 total**：空輸入回 0.0、回值經 `_finite` 投影故恆有限、
    永不拋例外（Rule 9.33.3）。每個 reducer 為單次 O(n) 累積（一遍掃描，無遞迴、無 while、無巢狀迴圈）。"""
    xs = [float(v) for v in vals]
    if not xs:
        return 0.0
    if name == "acc_sum":
        return _finite(float(sum(xs)))
    if name == "acc_count":
        return _finite(float(len(xs)))
    if name == "acc_sumabs":
        return _finite(sum(abs(x) for x in xs))
    if name == "acc_sumsq":
        return _finite(sum(x * x for x in xs))
    if name == "acc_max":
        return _finite(max(xs))
    if name == "acc_min":
        return _finite(min(xs))
    if name == "acc_first":
        return _finite(xs[0])
    raise ValueError(f"未知原始歸約器 base_reducer={name!r}（合法：{ATOM_REDUCERS}）")


def _post(name: str, a: float) -> float:
    """後變換求值（float -> float）。**全 total**：非法域回退、回值經 `_finite` 投影、永不拋例外（Rule 9.33.3）。"""
    a = float(a)
    if name == "identity":
        return _finite(a)
    if name == "sqrt_safe":
        return _finite(math.sqrt(abs(a)))            # total：負數取 abs
    if name == "recip_safe":
        return _finite(1.0 / a if a != 0.0 else 0.0)  # total：0 回退
    if name == "log1p_safe":
        return _finite(math.log1p(a) if a > -1.0 else 0.0)  # total：<=-1 回退（log1p 定義域）
    if name == "clip01":
        return _finite(0.0 if a < 0.0 else (1.0 if a > 1.0 else a))
    if name == "negate":
        return _finite(-a)
    raise ValueError(f"未知後變換 post_map={name!r}（合法：{POST_MAPS}）")


def _binary_atom(name: str, a: float, b: float) -> float:
    """二元原子求值。**全 total**：非法域回退、回值經 `_finite` 投影、永不拋例外（Rule 9.33.3）。"""
    a, b = float(a), float(b)
    if name == "wmean":
        return _finite((a + b) / 2.0)
    if name == "hypot":
        return _finite(math.sqrt(a * a + b * b))
    if name == "geo_safe":
        return _finite(math.sqrt(abs(a) * abs(b)))        # total：abs 後開根
    if name == "harmonic_safe":
        s = a + b
        return _finite(2.0 * a * b / s if s != 0.0 else 0.0)  # total：0 分母回退
    if name == "absdiff":
        return _finite(abs(a - b))
    raise ValueError(f"未知二元原子 binary_atom={name!r}（合法：{BINARY_ATOMS}）")


# ---------------------------------------------------------------------------
# 自我發明字母元素（PRIMITIVES/COMBINATORS 外、現場由字母表生成文法生成的新運算字母）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InventedPrimitive:
    """一個 PRIMITIVES 外、由 bounded 字母表生成文法現場發明的新原始算子（meta⁶ 製品）.

    被發明 primitive = `post_map ∘ base_reducer`：reduce(vals)=post_map(base_reducer(vals))。
    - reduce(vals): list[float] -> float，**全函式**（空輸入回 0.0、無例外）、單遍、cost-1。
    - apply(features): 把 probe 特徵以此 primitive 聚合為純量（供 oracle feature-grounded 評估，
      duck-typed `.apply()`/`.name`，反向不可——本模組不 import oracle）。
    """
    base_reducer: str
    post_map: str = "identity"
    probe: Tuple[str, ...] = REFERENCE_PROBE
    rationale: str = ""
    namespace: str = ALPHABET_GENESIS_NAMESPACE
    kind: str = "primitive"

    @staticmethod
    def of(base_reducer: str, post_map: str = "identity",
           probe: Optional[Sequence[str]] = None, rationale: str = "") -> "InventedPrimitive":
        pr = tuple(str(p) for p in (probe if probe is not None else REFERENCE_PROBE))
        return InventedPrimitive(base_reducer=str(base_reducer), post_map=str(post_map),
                                 probe=pr, rationale=str(rationale))

    @property
    def name(self) -> str:
        """決定性語意名：`prim::post_map(base_reducer)`（identity 後變換省略）。"""
        if self.post_map == "identity":
            return f"prim::{self.base_reducer}"
        return f"prim::{self.post_map}({self.base_reducer})"

    def reduce(self, vals: Sequence[float]) -> float:
        """作為 primitive 的 callable（list[float] -> float）。全函式、單遍、cost-1。"""
        return _post(self.post_map, _reduce(self.base_reducer, vals))

    def apply(self, features: Mapping[str, float]) -> float:
        """把 probe 特徵以此 primitive 聚合為純量（缺特徵以 0.0 計）。全函式、deterministic。"""
        vals = [float(features.get(f, 0.0)) for f in self.probe]
        return self.reduce(vals)

    def cost(self) -> int:
        """作為 primitive 在算子內的計算步數貢獻（Rule 9.33.3）：恆 1（單遍歸約 + total 後變換）。"""
        return 1

    def closure_report(self) -> "ClosureReport":
        """可計算性閉包報告（Rule 9.33.3）：把本字母併入字母表後，G(A') 整代數的 total/max_cost。"""
        return verify_computability_closure(self)

    def fingerprint(self) -> str:
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "base_reducer": self.base_reducer,
                "post_map": self.post_map, "probe": list(self.probe), "cost": self.cost(),
                "rationale": self.rationale, "namespace": self.namespace,
                "fingerprint": self.fingerprint()}


@dataclass(frozen=True)
class InventedCombinator:
    """一個 COMBINATORS 外、由 bounded 字母表生成文法現場發明的新組合算子（meta⁶ 製品）.

    被發明 combinator = 一元 POST_MAP（unary）或二元 BINARY_ATOM（binary）。
    - combine(a[, b]): 純量運算，**全函式**、cost-1。
    - apply(features): 用固定參照原始算子把 probe 轉成純量再套 combinator（供 oracle 評估）。
    """
    atom: str
    arity: str = "binary"             # "binary"（BINARY_ATOMS）或 "unary"（POST_MAPS）
    probe: Tuple[str, ...] = REFERENCE_PROBE
    rationale: str = ""
    namespace: str = ALPHABET_GENESIS_NAMESPACE
    kind: str = "combinator"

    @staticmethod
    def of(atom: str, arity: str = "binary",
           probe: Optional[Sequence[str]] = None, rationale: str = "") -> "InventedCombinator":
        pr = tuple(str(p) for p in (probe if probe is not None else REFERENCE_PROBE))
        ar = "binary" if str(arity) == "binary" else "unary"
        return InventedCombinator(atom=str(atom), arity=ar, probe=pr, rationale=str(rationale))

    @property
    def is_binary(self) -> bool:
        return self.arity == "binary"

    @property
    def name(self) -> str:
        return f"comb::{self.atom}" + ("" if self.is_binary else "/1")

    def combine(self, a: float, b: Optional[float] = None) -> float:
        """作為 combinator 的 callable。全函式、cost-1。"""
        if self.is_binary:
            return _binary_atom(self.atom, a, 0.0 if b is None else b)
        return _post(self.atom, a)

    def apply(self, features: Mapping[str, float]) -> float:
        """用固定參照原始算子把 probe 轉成純量再套 combinator（供 oracle feature-grounded 評估）。"""
        vals = [float(features.get(f, 0.0)) for f in self.probe]
        if self.is_binary:
            a = _og._prim(_COMB_REF_A, vals)
            b = _og._prim(_COMB_REF_B, vals)
            return self.combine(a, b)
        a = _og._prim(_COMB_REF_UNARY, vals)
        return self.combine(a)

    def cost(self) -> int:
        return 1

    def closure_report(self) -> "ClosureReport":
        return verify_computability_closure(self)

    def fingerprint(self) -> str:
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "atom": self.atom, "arity": self.arity,
                "probe": list(self.probe), "cost": self.cost(), "rationale": self.rationale,
                "namespace": self.namespace, "fingerprint": self.fingerprint()}


AlphabetElement = Union[InventedPrimitive, InventedCombinator]


# ---------------------------------------------------------------------------
# 可計算性閉包驗證（Rule 9.33.3，PU-2 核心）— 把字母併入字母表後枚舉 G(A') 整代數驗 total + 有界步數
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClosureReport:
    """擴充字母表後 G(A') 整個算子代數的可計算性閉包報告（Rule 9.33.3）。"""
    total: bool
    max_cost: int
    n_operators: int
    element_name: str = ""

    def ok(self, step_max: int) -> bool:
        return self.total and self.max_cost <= step_max


def _existing_primitive_callables() -> List[Tuple[str, Callable[[Sequence[float]], float]]]:
    return [(nm, (lambda vals, n=nm: _og._prim(n, vals))) for nm in _og.PRIMITIVES]


def _existing_unary_combinator_callables() -> List[Tuple[str, Callable[[float], float]]]:
    return [(nm, (lambda a, n=nm: _og._comb(n, a))) for nm in _og.UNARY_COMBINATORS]


def _existing_binary_combinator_callables() -> List[Tuple[str, Callable[[float, float], float]]]:
    return [(nm, (lambda a, b, n=nm: _og._comb(n, a, b))) for nm in _og.BINARY_COMBINATORS]


def verify_computability_closure(
    element: AlphabetElement,
    *,
    fuzz: Optional[List[List[float]]] = None,
) -> ClosureReport:
    """枚舉「把 `element` 併入字母表後」的整個算子代數 G(A')，對每個算子 fuzz-total + 計 max_cost（Rule 9.33.3）.

    這是可計算性閉包定理（§1.2）的**機器驗證**：被發明字母由 total 原子組成 → 擴充字母表後 G(A') 整代數
    每個算子仍全函式（total 的合成仍 total）+ cost<=3（cost=prim_evals+1）。枚舉:
      - unary 算子：comb(prim(vals))，cost=2；
      - binary 算子：comb(prim_a(vals), prim_b(vals))，cost=3。
    對每個算子 × `_FUZZ_VALUE_SETS`（極端輸入：空/單元素/負/0/極大含浮點上限 1e200/1e308）fuzz；任一拋例外 /
    NaN / inf → total=False（閉包破裂）。本函式不寫盤、不呼叫 oracle、零遞迴零迴圈（唯一 for 是有限枚舉）。
    """
    fz = fuzz if fuzz is not None else _FUZZ_VALUE_SETS

    prims = list(_existing_primitive_callables())
    unary_combs = list(_existing_unary_combinator_callables())
    binary_combs = list(_existing_binary_combinator_callables())

    if isinstance(element, InventedPrimitive):
        prims.append((element.name, element.reduce))
    elif isinstance(element, InventedCombinator):
        if element.is_binary:
            binary_combs.append((element.name, element.combine))
        else:
            unary_combs.append((element.name, lambda a, e=element: e.combine(a)))
    else:
        # duck-typed 未知字母型別：嘗試當 primitive（有 .reduce）或 combinator（有 .combine）
        if hasattr(element, "reduce"):
            prims.append((getattr(element, "name", "?"), element.reduce))
        elif hasattr(element, "combine"):
            binary_combs.append((getattr(element, "name", "?"), element.combine))
        else:
            # 既無 reduce 也無 combine：無法判定其可計算性閉包 → fail-closed（視為不通過），
            # 與 guard_computability_closure 對缺 closure_report() 時 raise 的 fail-closed 立場對齊。
            return ClosureReport(
                total=False,
                max_cost=0,
                n_operators=0,
                element_name=getattr(element, "name", "?"),
            )

    total = True
    max_cost = 0
    n_ops = 0

    def _bad(r: float) -> bool:
        return (r != r) or r in (math.inf, -math.inf)

    # 一元算子：comb(prim(vals))，cost=2
    for _cn, comb in unary_combs:
        for _pn, prim in prims:
            n_ops += 1
            cost = 2
            max_cost = max(max_cost, cost)
            for vals in fz:
                try:
                    r = comb(prim(vals))
                except Exception:  # noqa: BLE001 — 任何例外 = 閉包破裂（非全函式）
                    total = False
                    break
                if _bad(r):
                    total = False
                    break
            if not total:
                break
        if not total:
            break

    # 二元算子：comb(prim_a(vals), prim_b(vals))，cost=3
    if total:
        for _cn, comb in binary_combs:
            for (pa_n, pa), (pb_n, pb) in itertools.product(prims, prims):
                if pa_n == pb_n:
                    continue   # 兩臂相同退化，跳過（沿用 operator_genesis 慣例）
                n_ops += 1
                cost = 3
                max_cost = max(max_cost, cost)
                for vals in fz:
                    try:
                        r = comb(pa(vals), pb(vals))
                    except Exception:  # noqa: BLE001
                        total = False
                        break
                    if _bad(r):
                        total = False
                        break
                if not total:
                    break
            if not total:
                break

    return ClosureReport(total=total, max_cost=max_cost, n_operators=n_ops,
                         element_name=getattr(element, "name", "?"))


# ---------------------------------------------------------------------------
# 反自利第一閘：字母自指守門（Rule 9.33.2）
# ---------------------------------------------------------------------------

def is_alphabet_self_referential(element: AlphabetElement) -> bool:
    """字母元素的任一欄位是否引用保留自指/proposer/oracle 內部信號（→ 自利字母）。"""
    tokens: List[str] = []
    if isinstance(element, InventedPrimitive):
        tokens = [element.base_reducer, element.post_map] + list(element.probe)
    elif isinstance(element, InventedCombinator):
        tokens = [element.atom, element.arity] + list(element.probe)
    else:
        for attr in ("base_reducer", "post_map", "atom", "arity"):
            v = getattr(element, attr, None)
            if v is not None:
                tokens.append(str(v))
        tokens += [str(p) for p in getattr(element, "probe", ())]
    for tok in tokens:
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def alphabet_self_reference_guard(elements: List[AlphabetElement]) -> List[AlphabetElement]:
    """丟棄所有自指字母（Rule 9.33.2 反自利第一閘，零漏放）。保序。"""
    return [e for e in elements if not is_alphabet_self_referential(e)]


# ---------------------------------------------------------------------------
# 有界字母表生成文法枚舉（Rule 9.33.1：可枚舉、有限、cap 在 budget；每個字母結構性 total + cost-1）
# ---------------------------------------------------------------------------

def enumerate_genesis_alphabet(*, budget: Optional[int] = None,
                               probe: Optional[Sequence[str]] = None,
                               atom_reducers: Optional[Tuple[str, ...]] = None,
                               post_maps: Optional[Tuple[str, ...]] = None,
                               binary_atoms: Optional[Tuple[str, ...]] = None
                               ) -> List[AlphabetElement]:
    """在 bounded 字母表生成文法上 deterministic 枚舉候選字母元素，cap 在 budget（Rule 9.33.1）.

    文法 = ATOM_REDUCERS × POST_MAPS（生成 InventedPrimitive）+ BINARY_ATOMS + 一元 POST_MAPS（生成
    InventedCombinator）。固定 probe。已過 alphabet_self_reference_guard（生產原子無自指 token，故恆全
    存活；guard 仍對「受擾注入的自指字母」零漏放）。枚舉節點 <= budget。**每個產出字母結構性 total + cost-1**。
    """
    cap = budget if budget is not None else alphabet_budget()
    pr = tuple(probe) if probe is not None else REFERENCE_PROBE
    reducers = atom_reducers if atom_reducers is not None else ATOM_REDUCERS
    maps = post_maps if post_maps is not None else POST_MAPS
    bins = binary_atoms if binary_atoms is not None else BINARY_ATOMS

    # 兩條 deterministic 子串流：primitive（reducer × post_map）與 combinator（binary atoms + 一元 maps）。
    prim_stream: List[AlphabetElement] = [
        InventedPrimitive.of(red, pm, probe=pr, rationale=f"字母表外生成 primitive：{pm}({red})")
        for red in reducers for pm in maps
    ]
    comb_stream: List[AlphabetElement] = [
        InventedCombinator.of(atom, "binary", probe=pr,
                              rationale=f"字母表外生成 combinator（二元）：{atom}")
        for atom in bins
    ] + [
        InventedCombinator.of(pm, "unary", probe=pr,
                              rationale=f"字母表外生成 combinator（一元）：{pm}")
        for pm in maps if pm != "identity"   # identity 一元與既有 identity combinator 退化重複
    ]

    # round-robin 交錯，使任何 budget 切片皆同時含 primitive 與 combinator 兩型（Rule 9.33.1 有界、可枚舉、
    # 兩型皆可被自我發明）。枚舉節點 <= cap。
    out: List[AlphabetElement] = []
    i = j = 0
    while len(out) < cap and (i < len(prim_stream) or j < len(comb_stream)):
        if i < len(prim_stream):
            out.append(prim_stream[i]); i += 1
            if len(out) >= cap:
                break
        if j < len(comb_stream):
            out.append(comb_stream[j]); j += 1
    return alphabet_self_reference_guard(out)


def expanded_alphabet(accepted_element_names) -> Tuple[str, ...]:
    """meta⁶ 對 meta⁵ 的供料：基礎字母表（PRIMITIVES ∪ COMBINATORS）∪ 已採納字母發明名（去重保序）.

    operator_genesis 之後可在這擴充後的字母表上組合算子（把固定字母表換成 expanded_alphabet）。
    """
    seen = list(_og.PRIMITIVES) + list(_og.COMBINATORS)
    for nm in accepted_element_names:
        if nm not in seen:
            seen.append(str(nm))
    return tuple(seen)


# ---------------------------------------------------------------------------
# 字母自我發明提案（在有界字母表文法上以注入 evaluate〔= feature-grounded oracle 必要性〕找最佳）
# ---------------------------------------------------------------------------

@dataclass
class AlphabetProposal:
    """單一字母發明的提案（proposed；待人工 signoff，Rule 9.33.1）。"""
    element: Optional[AlphabetElement] = None
    necessity: float = 0.0
    margin: float = 0.0
    tier: int = 0
    cost: int = 0
    closure_ok: bool = False        # 可計算性閉包證據（Rule 9.33.3）
    closure_max_cost: int = 0
    accepted: bool = False
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "element": self.element.to_dict() if self.element else None,
            "fingerprint": self.element.fingerprint() if self.element else None,
            "necessity": round(self.necessity, 6),
            "margin": self.margin,
            "tier": self.tier,
            "cost": self.cost,
            "closure_ok": self.closure_ok,
            "closure_max_cost": self.closure_max_cost,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",
        }


def _closure_facts(element: AlphabetElement) -> Tuple[bool, int]:
    rep = verify_computability_closure(element)
    return rep.total, rep.max_cost


def alphabet_genesis(
    evaluate: Callable[[AlphabetElement], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[AlphabetElement]] = None,
) -> AlphabetProposal:
    """在 bounded 字母表生成文法上找「held-out 必要性最高」的 PRIMITIVES/COMBINATORS 外字母發明（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.33.2）。`accepted` 僅代表
    「達 margin、有資格送人工」，不代表已納入。`nodes_searched <= budget`。已過 alphabet self-reference guard。
    """
    cands = candidates if candidates is not None else enumerate_genesis_alphabet(budget=budget)
    mgn = margin if margin is not None else alphabet_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[AlphabetElement] = None
    best_necessity = 0.0
    searched = 0
    for e in cands:
        searched += 1
        n = float(evaluate(e))
        if best is None or n > best_necessity:
            best_necessity = n
            best = e

    if best is None:
        return AlphabetProposal(
            element=None, necessity=0.0, margin=mgn, tier=0, cost=0, closure_ok=False,
            closure_max_cost=0, accepted=False, nodes_searched=searched,
            reason="字母表文法為空 / 全被自指守門丟棄（無可提案字母）")

    total, max_cost = _closure_facts(best)
    accepted = best_necessity >= mgn
    return AlphabetProposal(
        element=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), cost=best.cost(), closure_ok=total, closure_max_cost=max_cost,
        accepted=accepted, nodes_searched=searched,
        reason=("達 margin：PRIMITIVES/COMBINATORS 外字母發明 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無字母發明達必要性門檻（字母本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪字母自我發明 + 反 big-bang K_alpha 截斷（Rule 9.33.4）
# ---------------------------------------------------------------------------

@dataclass
class AlphabetRound:
    """一輪字母自我發明提案的彙整（已套反 big-bang K_alpha 截斷）。"""
    proposals: List[AlphabetProposal] = field(default_factory=list)
    selected: List[AlphabetProposal] = field(default_factory=list)
    k: int = 0
    deferred: List[str] = field(default_factory=list)


def alphabet_genesis_round(
    evaluate: Callable[[AlphabetElement], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[AlphabetElement]] = None,
) -> AlphabetRound:
    """對字母表文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_alpha 截斷**（Rule 9.33.4）.

    一輪至多 K_alpha（沿用 Phase Q/R/S/T 預設 1）個字母發明進 proposed-pending-signoff（按 necessity 由高
    到低取前 K_alpha，deterministic tie-break by name），其餘順延——絕不一次劫持整個字母本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_genesis_alphabet(budget=budget)
    mgn = margin if margin is not None else alphabet_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[AlphabetProposal] = []
    for e in cands:
        n = float(evaluate(e))
        if n >= mgn:
            total, max_cost = _closure_facts(e)
            proposals.append(AlphabetProposal(
                element=e, necessity=n, margin=mgn, tier=tfn(n), cost=e.cost(),
                closure_ok=total, closure_max_cost=max_cost, accepted=True, nodes_searched=1,
                reason="達 margin：PRIMITIVES/COMBINATORS 外字母發明 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.element.name))
    selected = ordered[:cap_k]
    deferred = [p.element.name for p in ordered[cap_k:]]
    return AlphabetRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（可計算性閉包守門 + 共用 meta-loop-ledger + 字母 stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.33.1/9.33.4：字母發明採納須人工 signoff——禁止 genesis 自動納入。"""


class SelfReferentialAlphabet(RuntimeError):
    """Rule 9.33.2：拒絕採納自指字母（base_reducer/post_map/atom/probe 引用保留自指信號）。"""


def adopt_genesis_alphabet(element: AlphabetElement, capability_level: int, *,
                           human_signoff: bool = False,
                           rule_id: Optional[str] = None,
                           source: str = "operator_alphabet_genesis",
                           note: str = "",
                           ledger_path: Optional[Path] = None,
                           ts: Optional[str] = None,
                           check_cardinality: bool = True,
                           check_closure: bool = True):
    """採納一個 PRIMITIVES/COMBINATORS 外字母發明——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.33.1/9.33.4）；自指字母結構性拒絕（Rule 9.33.2）；
    `guard_computability_closure`（可計算性閉包：擴充後 G(A') 整代數 total + cost<=step_max，Rule 9.33.3）+
    `guard_alphabet_genesis`（字母 stock 天花板，Rule 9.33.4）守門。guard 拋出時不落帳，呼叫端轉 MFSM_ESCALATION。
    """
    if is_alphabet_self_referential(element):
        raise SelfReferentialAlphabet(
            f"拒絕採納自指字母 {getattr(element, 'name', '?')!r}：欄位引用保留自指信號"
            f"（Rule 9.33.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "字母發明採納須人工 signoff（Rule 9.33.1/9.33.4）；"
            "僅在人工確認 PRIMITIVES/COMBINATORS 外字母計算生成本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    if check_closure:
        _mm.guard_computability_closure(element, ledger_path=ledger_path)  # 可能 raise（可計算性閉包）
    fp = element.fingerprint()
    rid = rule_id or ("ALG-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_alphabet_genesis(fp, ledger_path=ledger_path)  # 可能 raise（字母 stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def record_round(round_: AlphabetRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪字母自我發明提案落 value-dimension-ledger.yaml 的 `alphabet_inventions` 段（file_lock 保護）."""
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
        alphabet_inventions = data.get("alphabet_inventions")
        if not isinstance(alphabet_inventions, list):
            alphabet_inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",
        }
        alphabet_inventions.append(entry)
        data["alphabet_inventions"] = alphabet_inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
