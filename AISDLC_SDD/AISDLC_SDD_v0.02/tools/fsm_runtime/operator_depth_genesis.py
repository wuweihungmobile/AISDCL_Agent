"""Phase V / ACT-150 — Operator Depth Genesis Grammar（算子組合深度文法的自我擴充，meta⁷）.

對應藍圖：SDD_improving_Automation_22.md §1.1 / §1.2 / §3.1 ACT-150 / Rule 9.34.1 / 9.34.2 / 9.34.3 / 9.34.4。

Phase T 證了「系統可在固定算子字母表上自我發明算子」、Phase U 證了「系統可自我發明字母表外的新運算
字母」。但 Phase T/U 的可計算性論證有一個**共同的、未被言明的地基**：**組合深度被人類凍結在 `<=2`**
（`operator_genesis.enumerate_genesis_operators` 只生成一元 `comb(prim)`/二元 `comb(prim,prim)`，
`GenesisOperator.cost()` 結構性 `<=3`）。系統至今換得出算子、換得出字母，**卻換不出『更深的運算式樹』**。
本模組把骨架**升維**：從「在固定深度上發明算子/字母」升到「**自我發明一個組合深度 `>2` 的全新複合算子
（= 擴充算子生成文法的『組合深度上界』這個結構參數本身）**」。這是 meta⁷ 層——系統自己**寫『文法用多深
的運算式樹去生成算子』的結構性深度參數**。

**深度可計算性閉包是本模組的靈魂與迄今最深停機紅線（Rule 9.34.3，DepthClosure，且因 cost==depth 而最直接）**：
Phase T 的「每算子 cost<=3」、Phase U 的「擴充字母表後整代數 cost<=3」之所以成立，其地基是『組合深度凍結
`<=2`，故 cost() 是小常數』。一旦讓系統自我發明組合深度本身，**`cost()` 變成深度 `d` 的單調遞增函數**——本
設計裡一個深度算子 = 一個深度-2 基底算子（cost 2 或 3）外接一條長度 `d-2` 的一元 combinator 鏈，故
**`cost == depth`（一元基底）/ `depth+1`（二元基底）**。「自我擴充組合深度」字面上就是「自我擴充計算
步數」，深度上界就是停機臨界。故可計算性須由『字母表擴充下封閉』升級為**深度閉包性質**：擴充深度
`A_d → A_{d'}` 後，文法 `G(A, d')` 生成的整個（仍有限的）深度算子代數中**每一個算子**仍全函式 ∧
cost==depth <= STEP_MAX。本模組用一條**有界深度生成文法**結構性兌現「深度需另證有界」：

  - 深度算子 = `chain_unary_k(... chain_unary_1( base ))`，base ∈ 深度-2 算子代數（operator_genesis），
    chain_unary_i ∈ `DEPTH_CHAIN_COMBINATORS`（abs/neg/clip01/sq——皆 total 一元、cost-1；排除 identity
    避免退化 padding）。
  - `depth` = 2 + len(chain)；鏈長 `1..SDD_DIM_DEPTH_LIMIT-2`（深度 `3..SDD_DIM_DEPTH_LIMIT`）。
  - `apply()` 以**有界 for 迴圈走鏈**套用一元 combinator 於 base 標量——**全函式、零遞迴零 while、cost==depth**。
  - **深度可計算性閉包定理**：base 由 Phase T 證 total + cost∈{2,3}、每個 chain unary 皆 total + cost-1，故
    擴充深度後 G(A,depth) 整代數每算子仍 total + `cost==depth`——`I_d(A,D')` 成立 ⟺ `D'<=STEP_MAX`，即
    **深度可計算性閉包等價於「深度本身有硬上界 = STEP_MAX」**。`verify_depth_closure` 把此閉包**可機器
    驗證化**（枚舉 G(A,depth) 整代數 fuzz-total + cost<=step_max）。

**「深度 `<=2` 外」≠「無界」（Rule 9.34.1 有界深度生成文法）**：生成空間 = 有限深度-2 基底 × 有限一元鏈
（鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`）→ 可枚舉、有限，列舉節點 <= `SDD_DIM_DEPTH_BUDGET`（clamp[8,128]，
預設 32），深度 <= `SDD_DIM_DEPTH_LIMIT`（clamp[2,16]，預設 6），**絕不指數爆炸**。

**反自利第一閘（Rule 9.34.2 深度自指守門）**：任何 base/chain/probe 引用保留自指/proposer/oracle 內部信號
（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的深度算子，在送 oracle 前即被 `depth_self_reference_guard`
**結構性拒絕**（零漏放）。

**承 Phase T/U 的反 Goodhart 對抗分離（Rule 9.34.2，結構基石）**：本模組**結構性不持有任何必要性判據、
不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 深度生成文法上枚舉深度算子，再透過呼叫端
**注入的 `evaluate` 回呼**取每個發明深度算子的必要性。

**反 big-bang 深度發明（Rule 9.34.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q~U，預設 1）個深度發明可進
proposed-pending-signoff。**advisory（Rule 9.34.1）**：只產 `proposed` 深度算子，任一納入必經人工 signoff；
本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網、深度求值路徑零 `while`/零遞迴/零自呼叫（守 OPEN-10.6 + Rule 9.34.3）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Mapping, Optional, Sequence, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT
# 沿用 operator_genesis 的深度-2 算子代數 / 飽和投影 / fuzz 集 / 參照 probe / 保留自指信號（operator_genesis
# 結構性不 import oracle，故透過它取這些常數不會把 oracle 牽連進來，對抗分離不破；依賴單向：
# depth → operator → synthesizer，operator_genesis 不 import 本模組）。
from . import operator_genesis as _og
from .operator_genesis import GenesisOperator, _finite, _FUZZ_VALUE_SETS, REFERENCE_PROBE, RESERVED_SELF_REF
from .value_dimension_registry import dim_expand_k

# depth-genesis 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾、亦非 `value-dimension:` /
# `vocab-genesis:` / `operator-genesis:` / `alphabet-genesis:`，故與既有各 stock 天花板互不干涉，
# Rule 9.34.4 分開治理）。
DEPTH_GENESIS_NAMESPACE = "depth-genesis:"

# === 自我發明領域審計帳本（沿用 Phase R/S/T/U 的 value-dimension-ledger，增 depth_inventions 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界深度生成文法（Rule 9.34.1/9.34.3：深度 `<=2` 外生成被有限文法封住、可枚舉、深度可計算性閉包）===
# 深度鏈一元 combinator（全 total、cost-1；排除 identity 避免退化 padding——identity 鏈只增 cost 不增語意）。
DEPTH_CHAIN_COMBINATORS: Tuple[str, ...] = ("abs", "neg", "clip01", "sq")

_DEFAULT_DEPTH_BUDGET = 32
_DEPTH_BUDGET_CLAMP = (8, 128)

# 組合深度上界（Rule 9.34.1/9.34.3：鏈長 <= depth_limit-2，深度 <= depth_limit；因 cost==depth，深度上界
# 即步數上界——深度可計算性閉包的結構性兌現）。
_DEFAULT_DEPTH_LIMIT = 6
_DEPTH_LIMIT_CLAMP = (2, 16)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def depth_budget() -> int:
    """讀 SDD_DIM_DEPTH_BUDGET（env 可調），clamp[8,128]，預設 32（Rule 9.34.1 有界深度生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_DEPTH_BUDGET"), _DEFAULT_DEPTH_BUDGET, _DEPTH_BUDGET_CLAMP)


def depth_limit() -> int:
    """讀 SDD_DIM_DEPTH_LIMIT（env 可調），clamp[2,16]，預設 6（Rule 9.34.1/9.34.3 組合深度上界）。

    深度 <= depth_limit；因 cost==depth，深度上界即步數上界（深度可計算性閉包結構性兌現）。
    """
    return _clamp_int(os.environ.get("SDD_DIM_DEPTH_LIMIT"), _DEFAULT_DEPTH_LIMIT, _DEPTH_LIMIT_CLAMP)


def depth_coverage_margin() -> float:
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
# 自我發明深度算子（一個組合深度 >2、現場由深度生成文法生成的新複合算子）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DepthOperator:
    """一個組合深度 `>2`、由 bounded 深度生成文法現場發明的新複合算子（meta⁷ 製品）.

    深度算子 = `chain_unary_k(... chain_unary_1( base ))`：
    - base：operator_genesis.GenesisOperator（深度-2 算子，`comb(primary[,secondary])`）。
    - chain：一元 combinator 序列（DEPTH_CHAIN_COMBINATORS，鏈長 `1..depth_limit-2`），由內而外套用。

    apply(features)：先以 base 把 probe 特徵聚合為標量，再以**有界 for 迴圈走鏈**套用一元 combinator——
    **全函式**（base/chain 皆 total + `_finite` 飽和投影、無例外）、**零遞迴零 while**、deterministic。
    depth() = 2 + len(chain)；cost() = base.cost() + len(chain) == depth（一元基底）/ depth+1（二元基底）
    ——**cost 是深度的單調函數，故深度上界就是停機臨界**（Rule 9.34.3）。fingerprint 落 `depth-genesis:`
    命名空間（Rule 9.34.4），與維度/詞彙/算子/字母/scorer-profile 分開治理（深度走獨立 stock 天花板
    DepthGenesisBounded）。
    """
    base: GenesisOperator
    chain: Tuple[str, ...] = ()
    probe: Tuple[str, ...] = REFERENCE_PROBE
    rationale: str = ""
    namespace: str = DEPTH_GENESIS_NAMESPACE

    @staticmethod
    def of(base: GenesisOperator, chain: Sequence[str],
           probe: Optional[Sequence[str]] = None, rationale: str = "") -> "DepthOperator":
        pr = tuple(str(p) for p in (probe if probe is not None else (base.probe or REFERENCE_PROBE)))
        return DepthOperator(base=base, chain=tuple(str(c) for c in chain), probe=pr,
                             rationale=str(rationale))

    def depth(self) -> int:
        """組合深度 = 2（深度-2 基底）+ 鏈長。深度算子須 depth >= 3（chain 非空）。"""
        return 2 + len(self.chain)

    @property
    def name(self) -> str:
        """決定性語意名：`depth::chain_outer(...chain_inner(base_core))@probe|d=<depth>`。"""
        prim = self.base.primary
        if _og.is_binary_combinator(self.base.combinator):
            core = f"{self.base.combinator}({prim},{self.base.secondary})"
        else:
            core = f"{self.base.combinator}({prim})"
        applied = core
        for u in self.chain:                       # 由內而外（chain[-1] 最外層）
            applied = f"{u}({applied})"
        return f"depth::{applied}@{'+'.join(self.probe)}|d={self.depth()}"

    def apply(self, features: Mapping[str, float]) -> float:
        """把 probe 特徵以深度算子聚合為純量（缺特徵以 0.0 計）。**全函式、deterministic、cost==depth、零遞迴零 while**。

        唯一的迴圈是「有界 for 走鏈」（鏈長 = depth-2 有限）——無遞迴、無 while、無對輸入規模的巢狀掃描。
        """
        # base 以 base.probe 聚合，但本深度算子的 probe 為權威（base 與 self 共用同一 probe）。
        vals = [float(features.get(f, 0.0)) for f in self.probe]
        a = _og._prim(self.base.primary, vals)
        if _og.is_binary_combinator(self.base.combinator):
            b = _og._prim(self.base.secondary or self.base.primary, vals)
            acc = _og._comb(self.base.combinator, a, b)
        else:
            acc = _og._comb(self.base.combinator, a)
        for u in self.chain:                       # 有界 for 走鏈（鏈長有限、零遞迴零 while）
            acc = _og._comb(u, acc)
        return _finite(acc)

    def cost(self) -> int:
        """深度算子計算步數（Rule 9.34.3）：base cost + 鏈長 == depth（一元基底）/ depth+1（二元基底）.

        結構性線性於深度（非指數）——cost 是深度的單調函數，故深度上界就是步數上界（停機臨界）。
        """
        return self.base.cost() + len(self.chain)

    def is_total(self, *, samples: Optional[List[List[float]]] = None) -> bool:
        """全函式驗證（Rule 9.34.3）：對極端輸入 fuzz，apply 永不拋例外、無 NaN/inf。

        既然由 total 深度-2 基底 ∘ total 一元鏈組成，這在結構上恆真；本方法以 fuzz 把「結構保證」
        轉成「可機器驗證的客觀守門」（guard_depth_closure / verify_depth_closure 呼叫）。
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

    def closure_report(self) -> "DepthClosureReport":
        """深度可計算性閉包報告（Rule 9.34.3）：把本深度算子所在深度的整個 G(A,depth) 代數驗 total + max_cost。"""
        return verify_depth_closure(self)

    def fingerprint(self) -> str:
        """語意指紋（depth-genesis stock 命名空間，Rule 9.34.4）。"""
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "base": self.base.name, "chain": list(self.chain),
                "depth": self.depth(), "probe": list(self.probe), "cost": self.cost(),
                "rationale": self.rationale, "namespace": self.namespace,
                "fingerprint": self.fingerprint()}


# ---------------------------------------------------------------------------
# 深度可計算性閉包驗證（Rule 9.34.3，PV-2 核心）— 枚舉 G(A,depth) 整代數驗 total + 有界步數（因 cost==depth）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DepthClosureReport:
    """擴充深度後 G(A,depth) 整個深度算子代數的深度可計算性閉包報告（Rule 9.34.3）。"""
    total: bool
    max_cost: int
    n_operators: int
    depth: int = 0
    element_name: str = ""

    def ok(self, step_max: int) -> bool:
        return self.total and self.max_cost <= step_max


_CLOSURE_BASE_CAP = 24    # 閉包枚舉的深度-2 基底數上限（有界、deterministic；整代數 cost 與深度算子相同）


def verify_depth_closure(
    depth_op: DepthOperator,
    *,
    fuzz: Optional[List[List[float]]] = None,
    base_cap: int = _CLOSURE_BASE_CAP,
) -> DepthClosureReport:
    """枚舉「深度算子所在深度的整個 G(A,depth) 代數」，對每個算子 fuzz-total + 計 max_cost（Rule 9.34.3）.

    這是深度可計算性閉包定理（§1.2）的**機器驗證**：深度算子由 total 深度-2 基底 ∘ total 一元鏈組成 →
    擴充深度後 G(A,depth) 整代數每個算子仍全函式（total 的合成仍 total）+ `cost==depth`（線性於深度）。
    枚舉 G(A,depth) = {（每個深度-2 基底）× depth_op.chain}（同深度結構，base 變動，cap base_cap，deterministic）
    ∪ {depth_op 本身}（確保受擾注入的 op 必被 fuzz）。對每個算子 × `_FUZZ_VALUE_SETS`（極端輸入：空/單元素/負
    /0/極大含浮點上限 1e200/1e308）fuzz；任一拋例外 / NaN / inf → total=False（閉包破裂，如 chain 含未知
    combinator）。max_cost = 整代數最大 cost（== depth〔一元基底〕/ depth+1〔二元基底〕）；若 max_cost >
    step_max 即深度超界（因 cost==depth，深度本身超界）。本函式不寫盤、不呼叫 oracle、零遞迴零迴圈
    （唯一 for 是有限枚舉 + 有界鏈走訪）。
    """
    fz = fuzz if fuzz is not None else _FUZZ_VALUE_SETS

    # 同深度結構的整代數（base 變動、chain 固定為 depth_op.chain）+ depth_op 本身（去重）。
    bases = _og.enumerate_genesis_operators(budget=base_cap, probe=depth_op.probe)
    family: List[DepthOperator] = [depth_op]
    seen = {depth_op.name}
    for b in bases:
        cand = DepthOperator.of(b, depth_op.chain, probe=depth_op.probe)
        if cand.name not in seen:
            seen.add(cand.name)
            family.append(cand)

    total = True
    max_cost = 0
    n_ops = 0

    def _bad(r: float) -> bool:
        return (r != r) or r in (math.inf, -math.inf)

    for op in family:
        n_ops += 1
        max_cost = max(max_cost, op.cost())
        for vals in fz:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(op.probe)}
            try:
                r = op.apply(feats)
            except Exception:   # noqa: BLE001 — 任何例外 = 閉包破裂（非全函式）
                total = False
                break
            if _bad(r):
                total = False
                break
        if not total:
            break

    return DepthClosureReport(total=total, max_cost=max_cost, n_operators=n_ops,
                              depth=depth_op.depth(), element_name=depth_op.name)


# ---------------------------------------------------------------------------
# 反自利第一閘：深度自指守門（Rule 9.34.2）
# ---------------------------------------------------------------------------

def is_depth_self_referential(depth_op: DepthOperator) -> bool:
    """base/chain/probe 是否引用保留自指/proposer/oracle 內部信號（→ 自利深度算子）。"""
    tokens: List[str] = [depth_op.base.primary, depth_op.base.combinator, depth_op.base.secondary]
    tokens += list(depth_op.chain)
    tokens += list(depth_op.probe)
    tokens += list(depth_op.base.probe)
    for tok in tokens:
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def depth_self_reference_guard(ops: List[DepthOperator]) -> List[DepthOperator]:
    """丟棄所有自指深度算子（Rule 9.34.2 反自利第一閘，零漏放）。保序。"""
    return [o for o in ops if not is_depth_self_referential(o)]


# ---------------------------------------------------------------------------
# 有界深度生成文法枚舉（Rule 9.34.1：可枚舉、有限、cap 在 budget；每個深度算子結構性全函式 + cost==depth）
# ---------------------------------------------------------------------------

def enumerate_genesis_depth(*, budget: Optional[int] = None,
                            limit: Optional[int] = None,
                            probe: Optional[Sequence[str]] = None,
                            base_cap: int = 12) -> List[DepthOperator]:
    """在 bounded 深度生成文法上 deterministic 枚舉候選深度算子，cap 在 budget（Rule 9.34.1）.

    文法 = 深度-2 基底（operator_genesis.enumerate_genesis_operators，cap base_cap）× 一元鏈
    （DEPTH_CHAIN_COMBINATORS，鏈長 `1..limit-2`）。鏈長由短到長枚舉（先淺後深），每組 (base, chain)
    產一個深度算子。已過 depth_self_reference_guard（生產 base/chain/probe 無自指 token，故恆全存活；
    guard 仍對「受擾注入的自指深度算子」零漏放）。枚舉節點 <= budget、深度 <= limit。
    **每個產出深度算子結構性全函式 + cost==depth（線性於深度，零遞迴零迴圈）**。
    """
    cap = budget if budget is not None else depth_budget()
    lim = limit if limit is not None else depth_limit()
    pr = tuple(probe) if probe is not None else REFERENCE_PROBE
    bases = _og.enumerate_genesis_operators(budget=base_cap, probe=pr)
    max_chain = max(1, lim - 2)

    out: List[DepthOperator] = []
    # 鏈長由短到長（先生成 depth-3，再 depth-4…），每長度內 base × chain-tuple deterministic 枚舉。
    for chain_len in range(1, max_chain + 1):
        chains = _enumerate_chains(chain_len)
        for ch in chains:
            for b in bases:
                if len(out) >= cap:
                    return depth_self_reference_guard(out)
                out.append(DepthOperator.of(
                    b, ch, probe=pr,
                    rationale=f"深度外生成（depth={2 + chain_len}）：{'∘'.join(reversed(ch))}({b.name})"))
    return depth_self_reference_guard(out)


def _enumerate_chains(chain_len: int) -> List[Tuple[str, ...]]:
    """deterministic 枚舉長度 chain_len 的一元 combinator 鏈（DEPTH_CHAIN_COMBINATORS^chain_len）.

    為避免鏈長爆炸（4^k），實作以「對角線 + 單一 combinator 重複」生成有代表性且 deterministic 的有限集：
    每個 combinator 各自重複 chain_len 次（k 條）+ 相鄰 combinator 配對輪轉（k 條），共有界。
    """
    combs = DEPTH_CHAIN_COMBINATORS
    chains: List[Tuple[str, ...]] = []
    # (1) 單一 combinator 重複（abs^k, neg^k, clip01^k, sq^k）
    for c in combs:
        chains.append(tuple([c] * chain_len))
    # (2) 相鄰 combinator 輪轉（c_i, c_{i+1}, c_i, ...），避免退化重複、保有界
    for i in range(len(combs)):
        a, b = combs[i], combs[(i + 1) % len(combs)]
        ch = tuple((a if k % 2 == 0 else b) for k in range(chain_len))
        if ch not in chains:
            chains.append(ch)
    return chains


def expanded_depth_ops(accepted_depth_names) -> Tuple[str, ...]:
    """meta⁷ 對外的供料：已採納深度算子發明名（deterministic 去重保序）.

    供 steersman / 後續層引用「系統已自我擴充到哪些更深複合算子」。
    """
    seen: List[str] = []
    for nm in accepted_depth_names:
        if nm not in seen:
            seen.append(str(nm))
    return tuple(seen)


# ---------------------------------------------------------------------------
# 深度自我發明提案（在有界深度文法上以注入 evaluate〔= feature-grounded oracle 必要性〕找最佳）
# ---------------------------------------------------------------------------

@dataclass
class DepthProposal:
    """單一深度發明的提案（proposed；待人工 signoff，Rule 9.34.1）。"""
    operator: Optional[DepthOperator] = None
    necessity: float = 0.0
    margin: float = 0.0
    tier: int = 0
    cost: int = 0
    depth: int = 0
    closure_ok: bool = False        # 深度可計算性閉包證據（Rule 9.34.3）
    closure_max_cost: int = 0
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
            "depth": self.depth,
            "closure_ok": self.closure_ok,
            "closure_max_cost": self.closure_max_cost,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def _closure_facts(depth_op: DepthOperator) -> Tuple[bool, int]:
    rep = verify_depth_closure(depth_op)
    return rep.total, rep.max_cost


def depth_genesis(
    evaluate: Callable[[DepthOperator], float],
    *,
    budget: Optional[int] = None,
    limit: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[DepthOperator]] = None,
) -> DepthProposal:
    """在 bounded 深度生成文法上找「held-out 必要性最高」的深度 `>2` 算子發明（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.34.2）。`accepted` 僅代表
    「達 margin、有資格送人工」，不代表已納入。`nodes_searched <= budget`。已過 depth self-reference guard。
    """
    cands = candidates if candidates is not None else enumerate_genesis_depth(budget=budget, limit=limit)
    mgn = margin if margin is not None else depth_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[DepthOperator] = None
    best_necessity = 0.0
    searched = 0
    for op in cands:
        searched += 1
        n = float(evaluate(op))
        if best is None or n > best_necessity:   # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = n
            best = op

    if best is None:
        return DepthProposal(
            operator=None, necessity=0.0, margin=mgn, tier=0, cost=0, depth=0, closure_ok=False,
            closure_max_cost=0, accepted=False, nodes_searched=searched,
            reason="深度文法為空 / 全被自指守門丟棄（無可提案深度算子）")

    total, max_cost = _closure_facts(best)
    accepted = best_necessity >= mgn
    return DepthProposal(
        operator=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), cost=best.cost(), depth=best.depth(),
        closure_ok=total, closure_max_cost=max_cost,
        accepted=accepted, nodes_searched=searched,
        reason=("達 margin：深度 >2 算子發明 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無深度發明達必要性門檻（深度本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪深度自我發明 + 反 big-bang K_depth 截斷（Rule 9.34.4）
# ---------------------------------------------------------------------------

@dataclass
class DepthRound:
    """一輪深度自我發明提案的彙整（已套反 big-bang K_depth 截斷）。"""
    proposals: List[DepthProposal] = field(default_factory=list)
    selected: List[DepthProposal] = field(default_factory=list)
    k: int = 0
    deferred: List[str] = field(default_factory=list)


def depth_genesis_round(
    evaluate: Callable[[DepthOperator], float],
    *,
    budget: Optional[int] = None,
    limit: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[DepthOperator]] = None,
) -> DepthRound:
    """對深度文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_depth 截斷**（Rule 9.34.4）.

    一輪至多 K_depth（沿用 Phase Q~U 預設 1）個深度發明進 proposed-pending-signoff（按 necessity 由高到低取
    前 K_depth，deterministic tie-break by name），其餘順延——絕不一次劫持整個深度本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_genesis_depth(budget=budget, limit=limit)
    mgn = margin if margin is not None else depth_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[DepthProposal] = []
    for op in cands:
        n = float(evaluate(op))
        if n >= mgn:
            total, max_cost = _closure_facts(op)
            proposals.append(DepthProposal(
                operator=op, necessity=n, margin=mgn, tier=tfn(n), cost=op.cost(), depth=op.depth(),
                closure_ok=total, closure_max_cost=max_cost, accepted=True, nodes_searched=1,
                reason="達 margin：深度 >2 算子發明 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.operator.name))
    selected = ordered[:cap_k]
    deferred = [p.operator.name for p in ordered[cap_k:]]
    return DepthRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（深度可計算性閉包守門 + 共用 meta-loop-ledger + 深度 stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.34.1/9.34.4：深度發明採納須人工 signoff——禁止 genesis 自動納入。"""


class SelfReferentialDepth(RuntimeError):
    """Rule 9.34.2：拒絕採納自指深度算子（base/chain/probe 引用保留自指信號）。"""


def adopt_genesis_depth(depth_op: DepthOperator, capability_level: int, *,
                        human_signoff: bool = False,
                        rule_id: Optional[str] = None,
                        source: str = "operator_depth_genesis",
                        note: str = "",
                        ledger_path: Optional[Path] = None,
                        ts: Optional[str] = None,
                        check_cardinality: bool = True,
                        check_closure: bool = True):
    """採納一個深度 `>2` 算子發明——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.34.1/9.34.4）；自指深度算子結構性拒絕（Rule 9.34.2）；
    `guard_depth_closure`（深度可計算性閉包：擴充深度後 G(A,depth) 整代數 total + cost<=step_max，Rule 9.34.3）+
    `guard_depth_genesis`（深度 stock 天花板，Rule 9.34.4）守門。guard 拋出時不落帳，呼叫端轉 MFSM_ESCALATION。
    """
    if is_depth_self_referential(depth_op):
        raise SelfReferentialDepth(
            f"拒絕採納自指深度算子 {depth_op.name!r}：base/chain/probe 引用保留自指信號"
            f"（Rule 9.34.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "深度發明採納須人工 signoff（Rule 9.34.1/9.34.4）；"
            "僅在人工確認深度 >2 算子計算生成本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    if check_closure:
        _mm.guard_depth_closure(depth_op, ledger_path=ledger_path)  # 可能 raise（深度可計算性閉包）
    fp = depth_op.fingerprint()
    rid = rule_id or ("DPT-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_depth_genesis(fp, ledger_path=ledger_path)  # 可能 raise（深度 stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def record_round(round_: DepthRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪深度自我發明提案落 value-dimension-ledger.yaml 的 `depth_inventions` 段（file_lock 保護）."""
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
        depth_inventions = data.get("depth_inventions")
        if not isinstance(depth_inventions, list):
            depth_inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.34.1/9.34.4）
        }
        depth_inventions.append(entry)
        data["depth_inventions"] = depth_inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
