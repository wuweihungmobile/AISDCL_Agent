"""Phase W / ACT-153 — Operator Recursion Genesis Grammar（算子間互遞迴文法的自我擴充，meta⁸）.

對應藍圖：SDD_improving_Automation_23.md §1.1 / §1.2 / §3.1 ACT-153 / Rule 9.35.1 / 9.35.2 / 9.35.3 / 9.35.4。

Phase T 證了「系統可在固定算子字母表上自我發明算子」、U 證了「自我發明字母表外的新運算字母」、V 證了
「自我發明組合深度 >2 的新複合算子」。但 Phase T/U/V 的停機論證有一個**共同的、未被言明的最深地基**：
**被發明的算子代數結構性零遞迴、零迴圈、零自呼叫**（`apply` 都是「list-reduction ∘ 有界 for 走鏈」，
運算式是有限樹，總步數 = 樹節點數這個結構性有限量，故「有界步數」device 足以保證停機）。系統至今換得出
算子、字母、深度，**卻換不出『算子互相呼叫 / 自呼叫』**。本模組把骨架**升維**：從「在非遞迴上發明算子/
字母/深度」升到「**自我發明一個會呼叫其他算子（甚至自呼叫）的互遞迴複合算子**（= 擴充算子生成文法的
『算子是否可互相引用 / 自引用』這個結構參數本身）」。這是 meta⁸ 層——系統自己**寫『算子互相呼叫的呼叫
圖』**。

**互遞迴良基停機證書是本模組的靈魂與迄今唯一質變停機紅線（Rule 9.35.3，RecursionClosure）**：
Phase T 的「cost<=3」、U 的「擴充字母表後整代數 cost<=3」、V 的「cost==depth<=STEP_MAX」之所以成立，其
共同地基是『算子代數零遞迴、運算式是有限樹，故總步數是結構性有限量』。一旦讓系統自我發明『算子可互相
呼叫 / 自呼叫』，運算式「樹」變成運算式「圖」（可含環）。一個含環呼叫圖**可以是停機的**（每次繞環嚴格
逼近一個下界 = 有良基遞減測度）、**也可以是不停機的**（無窮迴圈）；而「判定一個任意互遞迴算子是否停機」
**字面上就是停機問題本身（不可判定）**。故「有界步數」device 在此**結構性失效**（不能枚舉含環圖去數步數，
那等於解停機問題）。停機性必須由『有界步數靜態量』升級為**良基停機證書（Well-Founded Termination
Certificate）**：

  - 互遞迴算子 = 帶 rank 的呼叫圖 `(nodes, edges)`；每節點 = 一個 Phase T 深度-2 base 算子 + 一個 rank。
  - **有界互遞迴生成文法只生成「DAG（無環，結構良基）∨ 每條邊嚴格遞減下有界（>=0）rank」的呼叫圖**，
    且硬燃料 `fuel <= SDD_DIM_OP_STEP_MAX`——故有良基測度 `(rank, fuel)`，由良基歸納必終止
    （Agda/Coq/Idris 全函式語言的可判定停機邊界）。
  - `apply()` 以**有界 fuel 工作集（for _ in range(fuel) 走呼叫圖）**走訪——**全函式、零真遞迴零 while、
    步數<=fuel**。即使證書因實作瑕疵被繞過，fuel 硬上界仍保證求值器結構上不可能真無窮跑。
  - **良基停機證書定理**：DAG 沿拓樸序至多訪問 |N| 次必終止；含環但每回邊嚴格遞減下有界 rank → 良基測度
    lexicographic 嚴格遞減且下有界 → 無無窮遞減鏈 → 必終止。`verify_recursion_closure` 把此證書**可機器
    驗證化**（枚舉呼叫圖驗 (acyclic ∨ well-founded-rank) ∧ fuel<=step_max ∧ 整代數 fuzz-total）。

**meta⁸ 不讓算子代數真正跨入圖靈完備（那會使停機不可判定）**——而是安裝一道把互遞迴侷限在「可證良基
終止之全函式片段」的證書，凡無法出示良基測度者結構性拒絕、導 MFSM_ESCALATION。整個閉環仍靠 LLM+紙帶
維持圖靈完備。把「圖靈完備 vs 保證停機」正面釘在**可判定 vs 不可判定的臨界線本身**——用全新 device「良基
測度終止」取代失效的「有界步數」。

**「非遞迴外」≠「無界」（Rule 9.35.1 有界互遞迴生成文法）**：生成空間 = 有限節點集（每節點 = base 算子）×
有限帶 rank 呼叫邊集 → 可枚舉、有限，列舉節點 <= `SDD_DIM_RECUR_BUDGET`（clamp[8,128]，預設 32），
呼叫圖節點 <= `SDD_DIM_RECUR_NODES`（clamp[2,8]，預設 4），**絕不指數爆炸**。

**反自利第一閘（Rule 9.35.2 互遞迴自指守門）**：任何 node base / probe 引用保留自指/proposer/oracle 內部
信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的互遞迴算子，在送 oracle 前即被
`recursion_self_reference_guard` **結構性拒絕**（零漏放）。

**承 Phase T/U/V 的反 Goodhart 對抗分離（Rule 9.35.2，結構基石）**：本模組**結構性不持有任何必要性判據、
不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 互遞迴生成文法上枚舉互遞迴算子，再透過
呼叫端**注入的 `evaluate` 回呼**取每個發明互遞迴算子的必要性。

**反 big-bang 互遞迴發明（Rule 9.35.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q~V，預設 1）個互遞迴
發明可進 proposed-pending-signoff。**advisory（Rule 9.35.1）**：只產 `proposed` 互遞迴算子，任一納入必經
人工 signoff；本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網、求值路徑零 `while`/零真遞迴/零自呼叫函式（守 OPEN-10.6 + Rule 9.35.3）。
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
# recursion → operator → synthesizer，operator_genesis 不 import 本模組）。
from . import operator_genesis as _og
from .operator_genesis import GenesisOperator, _finite, _FUZZ_VALUE_SETS, REFERENCE_PROBE, RESERVED_SELF_REF
from .value_dimension_registry import dim_expand_k

# recursion-genesis 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾、亦非 `value-dimension:` /
# `vocab-genesis:` / `operator-genesis:` / `alphabet-genesis:` / `depth-genesis:`，故與既有各 stock 天花板
# 互不干涉，Rule 9.35.4 分開治理）。
RECURSION_GENESIS_NAMESPACE = "recursion-genesis:"

# === 自我發明領域審計帳本（沿用 Phase R/S/T/U/V 的 value-dimension-ledger，增 recursion_inventions 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界互遞迴生成文法（Rule 9.35.1/9.35.3：非遞迴外生成被有限文法封住、可枚舉、良基停機證書）===
# 路徑折疊算子（全 total）：互遞迴走呼叫圖時把 base 標量沿執行路徑折疊（mul/sum/max2/min2 皆 total）。
RECURSION_FOLD_COMBINATORS: Tuple[str, ...] = ("mul", "sum", "max2", "min2")

_DEFAULT_RECUR_BUDGET = 32
_RECUR_BUDGET_CLAMP = (8, 128)

# 呼叫圖節點數上界（Rule 9.35.1/9.35.3：節點 <= recur_nodes；fuel <= step_max，故步數有界）。
_DEFAULT_RECUR_NODES = 4
_RECUR_NODES_CLAMP = (2, 8)

# 算子可計算性步數上限（沿用 Phase T/V SDD_DIM_OP_STEP_MAX；fuel <= 此值——良基停機證書的硬燃料上界）。
_DEFAULT_OP_STEP_MAX = 8
_OP_STEP_MAX_CLAMP = (1, 64)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def recur_budget() -> int:
    """讀 SDD_DIM_RECUR_BUDGET（env 可調），clamp[8,128]，預設 32（Rule 9.35.1 有界互遞迴生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_RECUR_BUDGET"), _DEFAULT_RECUR_BUDGET, _RECUR_BUDGET_CLAMP)


def recur_nodes() -> int:
    """讀 SDD_DIM_RECUR_NODES（env 可調），clamp[2,8]，預設 4（Rule 9.35.1 呼叫圖節點數上界）。"""
    return _clamp_int(os.environ.get("SDD_DIM_RECUR_NODES"), _DEFAULT_RECUR_NODES, _RECUR_NODES_CLAMP)


def recur_step_max() -> int:
    """讀 SDD_DIM_OP_STEP_MAX（env 可調），clamp[1,64]，預設 8（Rule 9.35.3 良基停機證書硬燃料上界）。"""
    return _clamp_int(os.environ.get("SDD_DIM_OP_STEP_MAX"), _DEFAULT_OP_STEP_MAX, _OP_STEP_MAX_CLAMP)


def recur_coverage_margin() -> float:
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
# 路徑折疊 + 下一個 callee 選擇（模組級純函式；非遞迴、非 while；供 apply 走呼叫圖）
# ---------------------------------------------------------------------------

def _fold(combine: str, a: float, b: float) -> float:
    """沿執行路徑折疊兩個 base 標量（全 total，經 `_finite` 飽和投影故恆有限）。"""
    a = float(a)
    b = float(b)
    if combine == "mul":
        return _finite(a * b)
    if combine == "sum":
        return _finite(a + b)
    if combine == "max2":
        return _finite(max(a, b))
    if combine == "min2":
        return _finite(min(a, b))
    # 未知折疊算子 → total 回退（不拋例外，反非全函式；guard 由閉包 fuzz 攔結構異常）
    return _finite(a)


def _eval_order(ranks: Sequence[int]) -> List[int]:
    """良基求值序：rank 升序（更低 rank 先，tie → 索引序）.

    因生成文法保證每條呼叫邊嚴格遞減 rank（ranking function 證書），升序處理保證每個 callee 必先於
    其 caller 算出——良基歸納，零真遞迴、零 while。本函式為純排序（驗證/求值共用）。
    """
    return sorted(range(len(ranks)), key=lambda i: (ranks[i], i))


# ---------------------------------------------------------------------------
# 互遞迴算子（一個會呼叫其他算子 / 自呼叫、現場由互遞迴生成文法生成的新複合算子）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecursionNode:
    """互遞迴算子呼叫圖的一個節點：一個 base 算子 + 一個良基測度 rank + 對其他節點的呼叫邊.

    - base：operator_genesis.GenesisOperator（深度-2 算子，total + cost<=3）。
    - rank：良基測度（>=0）；生成文法保證每條邊 rank 嚴格遞減 → 呼叫圖良基（DAG）。
    - calls：callee 節點索引（**可指向其他節點 → 真互遞迴；指向更低 rank 即可證良基終止**）。
    """
    base: GenesisOperator
    rank: int = 0
    calls: Tuple[int, ...] = ()


@dataclass(frozen=True)
class RecursiveOperator:
    """一個會呼叫其他算子 / 自呼叫、由 bounded 互遞迴生成文法現場發明的新複合算子（meta⁸ 製品）.

    互遞迴算子 = 帶 rank 的呼叫圖（nodes + edges）+ entry + fold combinator + 硬燃料 fuel。

    apply(features)：先把每節點 base 對 probe 聚合為標量，再從 entry 以**有界 fuel 工作集（for _ in
    range(fuel) 走呼叫圖、每步沿 rank 嚴格遞減邊前進）**把標量沿執行路徑折疊——**全函式**（base/fold 皆
    total + `_finite` 飽和投影、無例外）、**零真遞迴零 while**、deterministic。fuel = 證書認證之硬步數
    上界（<= STEP_MAX，良基測度上界）。cost() = fuel（== 良基測度上界）。fingerprint 落
    `recursion-genesis:` 命名空間（Rule 9.35.4），與維度/詞彙/算子/字母/深度/scorer-profile 分開治理
    （互遞迴走獨立 stock 天花板 RecursionGenesisBounded）。
    """
    nodes: Tuple[RecursionNode, ...]
    entry: int = 0
    fuel: int = 0                       # 0 → 由節點數派生（= len(nodes)，DAG 路徑長度上界）
    probe: Tuple[str, ...] = REFERENCE_PROBE
    combine: str = "mul"
    rationale: str = ""
    namespace: str = RECURSION_GENESIS_NAMESPACE

    @staticmethod
    def chain(base: GenesisOperator, depth: int, *, combine: str = "mul",
              probe: Optional[Sequence[str]] = None, rationale: str = "") -> "RecursiveOperator":
        """便利建構：`depth` 個 base 節點的嚴格遞減 rank 呼叫鏈（0→1→…→depth-1，rank depth-1..0）.

        這是「真互遞迴的最小可證良基終止形態」——node i（rank depth-1-i）呼叫 node i+1（rank 更低），
        故呼叫圖良基（DAG）。
        """
        d = max(2, int(depth))
        pr = tuple(str(p) for p in (probe if probe is not None else (base.probe or REFERENCE_PROBE)))
        ns = tuple(
            RecursionNode(base=base, rank=d - 1 - i, calls=((i + 1,) if i + 1 < d else ()))
            for i in range(d)
        )
        return RecursiveOperator(nodes=ns, entry=0, fuel=d, probe=pr, combine=str(combine),
                                 rationale=str(rationale))

    @staticmethod
    def fan(base: GenesisOperator, width: int, *, combine: str = "mul",
            probe: Optional[Sequence[str]] = None, rationale: str = "") -> "RecursiveOperator":
        """便利建構：一個 entry 算子**同時呼叫 `width` 個更低 rank 的 sink 算子**（分支呼叫圖）.

        這是「一個算子呼叫**多個**其他算子（分支 / 共享 / 重匯聚）」的最小形態——**Phase V 線性深度鏈
        表達不出、Phase W 互遞迴呼叫圖才有的結構**。entry（rank 1）呼叫 node 1..width（皆 rank 0 sink），
        其結果由 fold 組合。呼叫圖良基（每條邊 rank 1→0 嚴格遞減），ranking function 證書通過。
        """
        w = max(1, int(width))
        pr = tuple(str(p) for p in (probe if probe is not None else (base.probe or REFERENCE_PROBE)))
        entry_node = RecursionNode(base=base, rank=1, calls=tuple(range(1, w + 1)))
        sinks = tuple(RecursionNode(base=base, rank=0, calls=()) for _ in range(w))
        return RecursiveOperator(nodes=(entry_node,) + sinks, entry=0, fuel=w + 1, probe=pr,
                                 combine=str(combine), rationale=str(rationale))

    def _ranks(self) -> List[int]:
        return [int(nd.rank) for nd in self.nodes]

    def n_nodes(self) -> int:
        return len(self.nodes)

    def _fuel(self) -> int:
        """硬燃料上界（良基測度上界）：明示 fuel 取 min(fuel, |N|)；否則 = |N|（DAG 路徑長度上界）。"""
        n = len(self.nodes)
        if self.fuel and self.fuel > 0:
            return min(int(self.fuel), max(1, n))
        return max(1, n)

    @property
    def name(self) -> str:
        """決定性語意名：`rec::<fold>[<base0>|r=..→..]@probe|n=<nodes>`。"""
        spec = ";".join(f"{nd.base.name}@r{nd.rank}->{','.join(str(c) for c in nd.calls)}"
                        for nd in self.nodes)
        return f"rec::{self.combine}[{spec}]@{'+'.join(self.probe)}|n={self.n_nodes()}"

    def apply(self, features: Mapping[str, float]) -> float:
        """把 probe 特徵以互遞迴算子（**良基 fold 走整張呼叫圖**）聚合為純量。**全函式、deterministic、零真遞迴零 while**.

        真互遞迴呼叫圖求值：以 rank 升序（更低 rank 先）逐節點，把該節點 base 與其**所有 callee 已算值**折疊
        （`for j in node.calls`——一個算子可呼叫**多個**其他算子：分支 / 共享 / 重匯聚，這正是 Phase V 線性深度
        鏈表達不出、Phase W 才有的呼叫圖結構）。因每條呼叫邊嚴格遞減 rank（ranking function 證書），升序處理
        保證每個 callee 必先於 caller 算出——良基歸納，**零真遞迴、零 while、零自呼叫函式**；步數 = 節點數
        <= fuel <= STEP_MAX。即使呼叫圖被受擾注入成含環，fuel 硬上界仍保證結構上不可能真無窮跑（PW-2 雙保險）。
        """
        n = len(self.nodes)
        if n == 0:
            return 0.0
        node_base = [float(self.nodes[i].base.apply(features)) for i in range(n)]
        ranks = [int(self.nodes[i].rank) for i in range(n)]
        value = [0.0] * n
        budget = self._fuel()
        steps = 0
        for i in _eval_order(ranks):            # 有界 for（節點數 <= fuel），零真遞迴零 while
            if steps >= budget:
                break
            acc = node_base[i]
            for j in self.nodes[i].calls:       # 折疊**所有** callee 已算值（真互遞迴呼叫圖：可多 callee）
                if 0 <= j < n:
                    acc = _fold(self.combine, acc, value[j])
            value[i] = _finite(acc)
            steps += 1
        return _finite(value[self.entry if 0 <= self.entry < n else 0])

    def cost(self) -> int:
        """互遞迴算子計算步數上界（Rule 9.35.3）= 硬燃料 fuel（== 良基測度上界，<= STEP_MAX）.

        非遞迴有限樹的 cost 是「樹節點數」這個靜態量；互遞迴的 cost 是「良基測度終止的硬步數上界」這個
        全新 device——admit 遞迴但侷限在可證良基終止之全函式片段。零自呼叫、零 while。
        """
        return self._fuel()

    def is_total(self, *, samples: Optional[List[List[float]]] = None) -> bool:
        """全函式驗證（Rule 9.35.3）：對極端輸入 fuzz，apply 永不拋例外、無 NaN/inf。"""
        fuzz = samples if samples is not None else _FUZZ_VALUE_SETS
        for vals in fuzz:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(self.probe)}
            try:
                r = self.apply(feats)
            except Exception:   # noqa: BLE001 — 任何例外 = 非全函式
                return False
            if r != r or r in (math.inf, -math.inf):
                return False
        return True

    def termination_certificate(self) -> "TerminationCertificate":
        """良基停機證書（Rule 9.35.3，PW-2 核心）：呼叫圖帶一個**良基 ranking function**（每條呼叫邊嚴格遞減
        下有界 >=0 rank）∧ fuel<=step_max。

        ranking function 是結構/良基遞迴的**教科書級可判定停機證書**：若存在 R:nodes→ℕ 使每條呼叫邊
        `R(callee) < R(caller)`，則呼叫圖良基（⟹ 無環 ⟹ 可證終止，rank 即嚴格遞減的良基測度）。我們**要求**
        被發明算子出示這個 ranking function（`well_founded`）——它把「可含環、判定停機不可判定」的呼叫圖空間
        侷限到「可證良基終止之全函式片段」（Agda/Coq/Idris 結構遞迴邊界）。凡無 ranking function 者（即可能
        含環者）一律 `terminating=False`、拒絕。`acyclic`（Kahn's）為獨立交叉驗證（ranking ⟹ acyclic，雙證
        防實作瑕疵）。device 之新在於：Phase V 用『有界運算式樹深度』，Phase W 用『呼叫圖上的 ranking
        function』——後者能承載 Phase V 線性鏈表達不出的**分支 / 共享 / 重匯聚呼叫圖**，且仍可判定終止。
        """
        n = len(self.nodes)
        ranks = self._ranks()
        ranks_lb = all(r >= 0 for r in ranks)
        # well_founded = 存在良基 ranking function：每條呼叫邊嚴格遞減下有界 rank。
        well_founded = ranks_lb
        for i in range(n):
            for j in self.nodes[i].calls:
                if not (0 <= j < n) or ranks[j] >= ranks[i]:
                    well_founded = False
        acyclic = _is_acyclic(self.nodes)   # 獨立交叉驗證（ranking ⟹ acyclic）
        fuel = self._fuel()
        # terminating = 可證良基終止：須出示 ranking function（well_founded）；acyclic 為交叉驗證。
        # 因有限 rank 上「含環 ∧ 每邊嚴格遞減 rank」為空集，well_founded ⟺ acyclic-with-ranking，
        # 兩者同真——但本判定以 ranking function 為**主證書**（凡無 ranking 者即可能含環，一律拒絕）。
        terminating = well_founded and acyclic and ranks_lb
        reason = (f"良基停機證書通過（呼叫圖帶良基 ranking function：每條呼叫邊嚴格遞減下有界 rank ⟹ "
                  f"良基無環 ⟹ 可證終止；fuel={fuel}）") if terminating else \
                 ("良基停機證書失敗（呼叫圖無良基 ranking function——某呼叫邊未嚴格遞減下有界 rank、"
                  "即可能含環 → 可能不停機；判定任意圖停機=停機問題不可判定，故拒絕）")
        return TerminationCertificate(
            terminating=terminating, acyclic=acyclic, well_founded=well_founded,
            fuel=fuel, max_cost=self.cost(), n_nodes=n, reason=reason)

    def closure_report(self) -> "RecursionClosureReport":
        """良基停機閉包報告（Rule 9.35.3）：把整個（同拓樸、base 變動的）互遞迴算子代數驗終止 + total + max_cost。"""
        return verify_recursion_closure(self)

    def fingerprint(self) -> str:
        """語意指紋（recursion-genesis stock 命名空間，Rule 9.35.4）。"""
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        cert = self.termination_certificate()
        return {"name": self.name, "n_nodes": self.n_nodes(), "fuel": self._fuel(),
                "combine": self.combine, "entry": self.entry,
                "ranks": self._ranks(), "cost": self.cost(),
                "edges": [[i, list(nd.calls)] for i, nd in enumerate(self.nodes)],
                "terminating": cert.terminating, "acyclic": cert.acyclic,
                "well_founded": cert.well_founded,
                "probe": list(self.probe), "rationale": self.rationale,
                "namespace": self.namespace, "fingerprint": self.fingerprint()}


# ---------------------------------------------------------------------------
# 良基停機證書（Rule 9.35.3，PW-2 核心）— 呼叫圖良基測度終止 + fuel 硬上界（全新 device，取代有界步數）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TerminationCertificate:
    """單一互遞迴算子的良基停機證書（Rule 9.35.3）。"""
    terminating: bool
    acyclic: bool
    well_founded: bool
    fuel: int
    max_cost: int
    n_nodes: int
    reason: str = ""

    def ok(self, step_max: int) -> bool:
        return self.terminating and self.fuel <= step_max and self.max_cost <= step_max


@dataclass(frozen=True)
class RecursionClosureReport:
    """整個（同拓樸、base 變動的）互遞迴算子代數的良基停機閉包報告（Rule 9.35.3）。"""
    total: bool
    terminating: bool
    acyclic: bool
    well_founded: bool
    fuel: int
    max_cost: int
    n_operators: int
    reason: str = ""

    def ok(self, step_max: int) -> bool:
        return self.total and self.terminating and self.fuel <= step_max and self.max_cost <= step_max


_CLOSURE_BASE_CAP = 24    # 閉包枚舉的 base 算子數上限（有界、deterministic；整代數同拓樸、fuel 相同）


def _is_acyclic(nodes: Sequence["RecursionNode"]) -> bool:
    """Kahn's 拓樸排序判定呼叫圖是否無環（DAG）。本函式為**驗證器**（非求值器），可用 while（有界）.

    DAG ⟺ 拓樸排序可移除全部節點。含環圖則殘留無法移除的節點 → 回 False（→ 良基停機證書失敗）。
    """
    n = len(nodes)
    indeg = [0] * n
    adj: List[List[int]] = []
    for i in range(n):
        outs = [j for j in nodes[i].calls if 0 <= j < n]
        adj.append(outs)
        for j in outs:
            indeg[j] += 1
    queue = [i for i in range(n) if indeg[i] == 0]
    removed = 0
    head = 0
    while head < len(queue):                 # 驗證器 while（有界：每節點至多入隊一次）
        u = queue[head]
        head += 1
        removed += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                queue.append(v)
    return removed == n


def verify_recursion_closure(
    rec_op: RecursiveOperator,
    *,
    fuzz: Optional[List[List[float]]] = None,
    base_cap: int = _CLOSURE_BASE_CAP,
) -> RecursionClosureReport:
    """枚舉「同拓樸、base 變動的整個互遞迴算子代數」，對每個算子驗良基停機證書 + fuzz-total（Rule 9.35.3）.

    這是良基停機證書定理（§1.2）的**機器驗證**：互遞迴算子由 total base 沿良基終止呼叫圖折疊組成 →
    整代數每算子仍全函式（total 的有限折疊仍 total）+ 可證終止（呼叫圖 DAG ∨ 每邊嚴格遞減下有界 rank）。
    枚舉代數 = {（每個 base）以 rec_op 同拓樸/同 fold/同 fuel 套用} ∪ {rec_op 本身}（確保受擾注入的 op 必被
    驗）。對每個算子 × `_FUZZ_VALUE_SETS`（極端輸入）fuzz；任一拋例外 / NaN / inf → total=False。
    terminating = 整代數每算子皆出示良基 ranking function（well_founded ∧ acyclic）；max_cost = 整代數最大
    cost（== fuel）。本函式不寫盤、不呼叫 oracle，求值用 RecursiveOperator.apply（零真遞迴零 while）。

    **閉包涵蓋面誠實標註（QA m-3）**：本枚舉**固定呼叫圖拓樸（ranks/calls/fold/fuel），僅變動 base 算子**，
    故證的是「該呼叫圖在任意 base 變動下仍 total + 仍可證良基終止」。呼叫圖本身的良基性（ranking function
    存在）由**生成文法結構性保證**（chain/fan 只產嚴格遞減 rank 邊）+ **per-op `termination_certificate`
    逐一驗證**（well_founded ∧ acyclic），而非由本閉包枚舉跑遍所有可能 rank/邊配置——因生成空間的拓樸有限
    且每個皆已過 ranking 證書，閉包範圍與生成空間一致、無漏洞。
    """
    fz = fuzz if fuzz is not None else _FUZZ_VALUE_SETS
    pr = rec_op.probe

    # 同拓樸結構的整代數（base 變動、ranks/calls/fold/fuel 固定）+ rec_op 本身（去重）。
    bases = _og.enumerate_genesis_operators(budget=base_cap, probe=pr)
    family: List[RecursiveOperator] = [rec_op]
    seen = {rec_op.name}
    for b in bases:
        ns = tuple(RecursionNode(base=b, rank=nd.rank, calls=nd.calls) for nd in rec_op.nodes)
        cand = RecursiveOperator(nodes=ns, entry=rec_op.entry, fuel=rec_op.fuel,
                                 probe=pr, combine=rec_op.combine)
        if cand.name not in seen:
            seen.add(cand.name)
            family.append(cand)

    total = True
    terminating = True
    acyclic_all = True
    well_founded_all = True
    max_cost = 0
    n_ops = 0

    def _bad(r: float) -> bool:
        return (r != r) or r in (math.inf, -math.inf)

    for op in family:
        n_ops += 1
        cert = op.termination_certificate()
        max_cost = max(max_cost, cert.max_cost)
        if not cert.terminating:
            terminating = False
        if not cert.acyclic:
            acyclic_all = False
        if not cert.well_founded:
            well_founded_all = False
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

    return RecursionClosureReport(
        total=total, terminating=terminating, acyclic=acyclic_all, well_founded=well_founded_all,
        fuel=rec_op._fuel(), max_cost=max_cost, n_operators=n_ops,
        reason="良基停機閉包：整代數 total + 可證終止 + fuel<=step_max" if (total and terminating)
        else "良基停機閉包破裂（整代數出現非全函式 / 含無證書環不可證終止算子）")


# ---------------------------------------------------------------------------
# 反自利第一閘：互遞迴自指守門（Rule 9.35.2）
# ---------------------------------------------------------------------------

def is_recursion_self_referential(rec_op: RecursiveOperator) -> bool:
    """node base / probe 是否引用保留自指/proposer/oracle 內部信號（→ 自利互遞迴算子）。"""
    tokens: List[str] = list(rec_op.probe)
    for nd in rec_op.nodes:
        tokens += [nd.base.primary, nd.base.combinator, nd.base.secondary]
        tokens += list(nd.base.probe)
    for tok in tokens:
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def recursion_self_reference_guard(ops: List[RecursiveOperator]) -> List[RecursiveOperator]:
    """丟棄所有自指互遞迴算子（Rule 9.35.2 反自利第一閘，零漏放）。保序。"""
    return [o for o in ops if not is_recursion_self_referential(o)]


# ---------------------------------------------------------------------------
# 有界互遞迴生成文法枚舉（Rule 9.35.1：可枚舉、有限、cap 在 budget；每個算子結構性良基終止 + 全函式）
# ---------------------------------------------------------------------------

def enumerate_genesis_recursion(*, budget: Optional[int] = None,
                                nodes: Optional[int] = None,
                                fuel: Optional[int] = None,
                                probe: Optional[Sequence[str]] = None,
                                base_cap: int = 8) -> List[RecursiveOperator]:
    """在 bounded 互遞迴生成文法上 deterministic 枚舉候選互遞迴算子，cap 在 budget（Rule 9.35.1）.

    文法 = 深度-2 base（operator_genesis.enumerate_genesis_operators，cap base_cap）× 呼叫圖節點數
    `2..recur_nodes` × fold combinator（RECURSION_FOLD_COMBINATORS）。每個 (base, k, fold) 產一個
    **嚴格遞減 rank 呼叫鏈**（0→1→…→k-1，rank k-1..0，DAG 良基），fuel=k <= recur_nodes <= step_max。
    節點數由小到大枚舉（先簡單後複雜），每組 deterministic。已過 recursion_self_reference_guard。
    **每個產出互遞迴算子結構性良基終止（DAG）+ 全函式 + fuel<=step_max（零真遞迴零 while）**。
    """
    cap = budget if budget is not None else recur_budget()
    max_nodes = nodes if nodes is not None else recur_nodes()
    pr = tuple(probe) if probe is not None else REFERENCE_PROBE
    bases = _og.enumerate_genesis_operators(budget=base_cap, probe=pr)
    out: List[RecursiveOperator] = []
    # (1) 線性遞減 rank 呼叫鏈（node i 呼叫 node i+1，DAG 良基）。
    for k in range(2, max(2, max_nodes) + 1):
        for fold in RECURSION_FOLD_COMBINATORS:
            for b in bases:
                if len(out) >= cap:
                    return recursion_self_reference_guard(out)
                op = RecursiveOperator.chain(
                    b, k, combine=fold, probe=pr,
                    rationale=f"互遞迴外生成 chain（nodes={k},fold={fold}）：{fold}-fold over {b.name}×{k}")
                if fuel is not None:
                    op = RecursiveOperator(nodes=op.nodes, entry=op.entry, fuel=int(fuel),
                                           probe=pr, combine=fold, rationale=op.rationale)
                out.append(op)
    # (2) 分支呼叫圖（一個 entry 算子同時呼叫多個更低 rank sink——真互遞迴呼叫圖，Phase V 線性鏈表達不出）。
    for width in range(2, max(2, max_nodes)):     # width+1 <= max_nodes 個節點
        for fold in RECURSION_FOLD_COMBINATORS:
            for b in bases:
                if len(out) >= cap:
                    return recursion_self_reference_guard(out)
                op = RecursiveOperator.fan(
                    b, width, combine=fold, probe=pr,
                    rationale=f"互遞迴外生成 fan（entry 呼叫 {width} sink,fold={fold}）：{b.name}")
                if fuel is not None:
                    op = RecursiveOperator(nodes=op.nodes, entry=op.entry, fuel=int(fuel),
                                           probe=pr, combine=fold, rationale=op.rationale)
                out.append(op)
    return recursion_self_reference_guard(out)


def expanded_recursion_ops(accepted_recursion_names) -> Tuple[str, ...]:
    """meta⁸ 對外的供料：已採納互遞迴算子發明名（deterministic 去重保序）.

    供 steersman / 後續層引用「系統已自我擴充到哪些互遞迴複合算子」。
    """
    seen: List[str] = []
    for nm in accepted_recursion_names:
        if nm not in seen:
            seen.append(str(nm))
    return tuple(seen)


# ---------------------------------------------------------------------------
# 互遞迴自我發明提案（在有界互遞迴文法上以注入 evaluate〔= feature-grounded oracle 必要性〕找最佳）
# ---------------------------------------------------------------------------

@dataclass
class RecursionProposal:
    """單一互遞迴發明的提案（proposed；待人工 signoff，Rule 9.35.1）。"""
    operator: Optional[RecursiveOperator] = None
    necessity: float = 0.0
    margin: float = 0.0
    tier: int = 0
    cost: int = 0
    fuel: int = 0
    terminating: bool = False        # 良基停機證書證據（Rule 9.35.3）
    acyclic: bool = False
    well_founded: bool = False
    closure_ok: bool = False
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
            "fuel": self.fuel,
            "terminating": self.terminating,
            "acyclic": self.acyclic,
            "well_founded": self.well_founded,
            "closure_ok": self.closure_ok,
            "closure_max_cost": self.closure_max_cost,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def _closure_facts(rec_op: RecursiveOperator) -> Tuple[bool, bool, bool, bool, int]:
    rep = verify_recursion_closure(rec_op)
    return rep.total, rep.terminating, rep.acyclic, rep.well_founded, rep.max_cost


def recursion_genesis(
    evaluate: Callable[[RecursiveOperator], float],
    *,
    budget: Optional[int] = None,
    nodes: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[RecursiveOperator]] = None,
) -> RecursionProposal:
    """在 bounded 互遞迴生成文法上找「held-out 必要性最高」的互遞迴算子發明（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.35.2）。`accepted` 僅代表
    「達 margin、有資格送人工」，不代表已納入。`nodes_searched <= budget`。已過 recursion self-reference guard。
    """
    cands = candidates if candidates is not None else enumerate_genesis_recursion(budget=budget, nodes=nodes)
    mgn = margin if margin is not None else recur_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[RecursiveOperator] = None
    best_necessity = 0.0
    searched = 0
    for op in cands:
        searched += 1
        nval = float(evaluate(op))
        if best is None or nval > best_necessity:    # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = nval
            best = op

    if best is None:
        return RecursionProposal(
            operator=None, necessity=0.0, margin=mgn, tier=0, cost=0, fuel=0,
            terminating=False, acyclic=False, well_founded=False, closure_ok=False,
            closure_max_cost=0, accepted=False, nodes_searched=searched,
            reason="互遞迴文法為空 / 全被自指守門丟棄（無可提案互遞迴算子）")

    total, terminating, acyclic, well_founded, max_cost = _closure_facts(best)
    accepted = best_necessity >= mgn
    return RecursionProposal(
        operator=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), cost=best.cost(), fuel=best._fuel(),
        terminating=terminating, acyclic=acyclic, well_founded=well_founded,
        closure_ok=(total and terminating), closure_max_cost=max_cost,
        accepted=accepted, nodes_searched=searched,
        reason=("達 margin：互遞迴算子發明 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無互遞迴發明達必要性門檻（互遞迴本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪互遞迴自我發明 + 反 big-bang K_recur 截斷（Rule 9.35.4）
# ---------------------------------------------------------------------------

@dataclass
class RecursionRound:
    """一輪互遞迴自我發明提案的彙整（已套反 big-bang K_recur 截斷）。"""
    proposals: List[RecursionProposal] = field(default_factory=list)
    selected: List[RecursionProposal] = field(default_factory=list)
    k: int = 0
    deferred: List[str] = field(default_factory=list)


def recursion_genesis_round(
    evaluate: Callable[[RecursiveOperator], float],
    *,
    budget: Optional[int] = None,
    nodes: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[RecursiveOperator]] = None,
) -> RecursionRound:
    """對互遞迴文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_recur 截斷**（Rule 9.35.4）.

    一輪至多 K_recur（沿用 Phase Q~V 預設 1）個互遞迴發明進 proposed-pending-signoff（按 necessity 由高到
    低取前 K_recur，deterministic tie-break by name），其餘順延——絕不一次劫持整個互遞迴本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_genesis_recursion(budget=budget, nodes=nodes)
    mgn = margin if margin is not None else recur_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[RecursionProposal] = []
    for op in cands:
        nval = float(evaluate(op))
        if nval >= mgn:
            total, terminating, acyclic, well_founded, max_cost = _closure_facts(op)
            proposals.append(RecursionProposal(
                operator=op, necessity=nval, margin=mgn, tier=tfn(nval), cost=op.cost(), fuel=op._fuel(),
                terminating=terminating, acyclic=acyclic, well_founded=well_founded,
                closure_ok=(total and terminating), closure_max_cost=max_cost, accepted=True,
                nodes_searched=1,
                reason="達 margin：互遞迴算子發明 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.operator.name))
    selected = ordered[:cap_k]
    deferred = [p.operator.name for p in ordered[cap_k:]]
    return RecursionRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（良基停機證書守門 + 共用 meta-loop-ledger + 互遞迴 stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.35.1/9.35.4：互遞迴發明採納須人工 signoff——禁止 genesis 自動納入。"""


class SelfReferentialRecursion(RuntimeError):
    """Rule 9.35.2：拒絕採納自指互遞迴算子（node base/probe 引用保留自指信號）。"""


def adopt_genesis_recursion(rec_op: RecursiveOperator, capability_level: int, *,
                            human_signoff: bool = False,
                            rule_id: Optional[str] = None,
                            source: str = "operator_recursion_genesis",
                            note: str = "",
                            ledger_path: Optional[Path] = None,
                            ts: Optional[str] = None,
                            check_cardinality: bool = True,
                            check_closure: bool = True):
    """採納一個互遞迴算子發明——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.35.1/9.35.4）；自指互遞迴算子結構性拒絕（Rule 9.35.2）；
    `guard_recursion_closure`（良基停機證書：呼叫圖 acyclic ∨ well-founded + fuel<=step_max + 整代數 total，
    Rule 9.35.3）+ `guard_recursion_genesis`（互遞迴 stock 天花板，Rule 9.35.4）守門。guard 拋出時不落帳，
    呼叫端轉 MFSM_ESCALATION。
    """
    if is_recursion_self_referential(rec_op):
        raise SelfReferentialRecursion(
            f"拒絕採納自指互遞迴算子 {rec_op.name!r}：node base/probe 引用保留自指信號"
            f"（Rule 9.35.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "互遞迴發明採納須人工 signoff（Rule 9.35.1/9.35.4）；"
            "僅在人工確認互遞迴算子計算生成本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    if check_closure:
        _mm.guard_recursion_closure(rec_op, ledger_path=ledger_path)  # 可能 raise（良基停機證書）
    fp = rec_op.fingerprint()
    rid = rule_id or ("RCR-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_recursion_genesis(fp, ledger_path=ledger_path)  # 可能 raise（互遞迴 stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def record_round(round_: RecursionRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪互遞迴自我發明提案落 value-dimension-ledger.yaml 的 `recursion_inventions` 段（file_lock 保護）."""
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
        recursion_inventions = data.get("recursion_inventions")
        if not isinstance(recursion_inventions, list):
            recursion_inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.35.1/9.35.4）
        }
        recursion_inventions.append(entry)
        data["recursion_inventions"] = recursion_inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
