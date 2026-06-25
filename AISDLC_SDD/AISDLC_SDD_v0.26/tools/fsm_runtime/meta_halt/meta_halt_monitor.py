"""Phase L M-L1 / ACT-090 — Meta-Halt Monitor（元迴圈有界停機 runtime 守門）.

對應藍圖：SDD_improving_Automation_12.md §1.2 / §3.1 ACT-090 / Rule 9.24.1~9.24.2。
形式化對應：formal/META_FSM.tla（獨立命名空間，churn/cap 兩計數器）。

兩道有界停機守門（任一觸發即拒絕該次規則採納，呼叫端應導 MFSM_ESCALATION 人工裁決）：

  1. ChurnBounded（Rule 9.24.1）—— 任一規則語意指紋的「加→退→再加」循環次數
     ≤ SDD_META_CHURN_MAX（clamp[1,5]，預設 2）。超限即拒絕，破除 add↔retire 無限抖動。

  2. GraduationRatchet（Rule 9.24.2）—— 被 GC 退役過的指紋，**再採納必須挾帶
     capability_level 嚴格變化證據**（capability-delta）。無 capability 提升的同型
     re-adopt 一律拒絕（不能「學了又退、退了又學」白燒 token）。

關鍵：學習層 `exit_learning_commit("approved")` 與 GC `set_maturity()` 的採納/退役
路徑**必須經本守門**（Rule 9.24.1 禁止繞過）。本模組為純函式 + ledger 操作，可由
runtime / hook / test 安全呼叫。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import meta_ledger as _ledger

# META_FSM 狀態宇宙（與 formal/META_FSM.tla 的 MetaStates 同步；由
# tests/test_meta_halt.py 的 test_meta_fsm_states_match_python 守雙源一致，
# 比照 _HAPPY_PATH ↔ SDD_FSM.tla 的 Rule 9.18.1 精神）。
META_STATES = frozenset({
    "MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION",
})
META_TERMINALS = frozenset({"MFSM_STABLE", "MFSM_ESCALATION"})

_DEFAULT_CHURN_MAX = 2
_CHURN_MAX_CLAMP = (1, 5)

# Phase P / ACT-119 — 跨評分器聚合採納速率上限（CrossScorerChurnBounded, Rule 9.28.3）。
_DEFAULT_CALIB_ADOPT_RATE_MAX = 6
_CALIB_ADOPT_RATE_CLAMP = (2, 32)
_DEFAULT_CALIB_ADOPT_WINDOW = 12
_CALIB_ADOPT_WINDOW_CLAMP = (4, 256)

# Phase Q / ACT-125 — 價值維度基數 stock 天花板（DimensionCardinalityBounded, Rule 9.29.3）。
_DEFAULT_DIM_CARDINALITY_MAX = 16     # = 既有 8 軸 + headroom
_DIM_CARDINALITY_CLAMP = (1, 32)

# Phase R / ACT-131 — 維度退役聯動聚合速率上限 + 單調價值棘輪（SwapCadenceBounded, Rule 9.30.3）。
_DEFAULT_DIM_SWAP_RATE_MAX = 3
_DIM_SWAP_RATE_CLAMP = (1, 16)
_DEFAULT_DIM_SWAP_WINDOW = 12
_DIM_SWAP_WINDOW_CLAMP = (4, 256)
_DEFAULT_DIM_SWAP_MARGIN = 0          # 入軸 tier 須嚴格 > 出軸 tier + margin（預設嚴格大於）

# Phase S / ACT-137 — 詞彙生成 stock 天花板（VocabGenesisBounded, Rule 9.31.3，meta⁴）。
_DEFAULT_DIM_VOCAB_MAX = 24           # = 既有 8 條 VOCAB + headroom（詞彙基數天花板）
_DIM_VOCAB_CLAMP = (1, 64)

# Phase S / ACT-137 — 多維度批次退役聯動三鎖（BatchSwapCadenceBounded, Rule 9.31.3）。
_DEFAULT_DIM_BATCH_MAX = 3            # 單批次 |out|/|in| 上限（反 big-bang 本體論一次重寫）
_DIM_BATCH_CLAMP = (1, 8)
_DEFAULT_DIM_BATCH_RATE_MAX = 2       # 最近視窗內 distinct 批次操作數上限
_DIM_BATCH_RATE_CLAMP = (1, 8)
_DEFAULT_DIM_BATCH_WINDOW = 12        # 批次操作速率視窗
_DIM_BATCH_WINDOW_CLAMP = (4, 256)
_DEFAULT_DIM_BATCH_MARGIN = 0         # 批次入軸聚合 tier 須嚴格 > 批次出軸聚合 + margin

# Phase T / ACT-143 — 算子基數 stock 天花板（OperatorGenesisBounded, Rule 9.32.4，meta⁵）。
_DEFAULT_DIM_OP_MAX = 16              # = 既有 4 條 OPS + headroom（算子基數天花板）
_DIM_OP_CLAMP = (1, 64)
# Phase T / ACT-143 — 算子可計算性步數上限（OperatorComputabilityBounded, Rule 9.32.3）。
_DEFAULT_DIM_OP_STEP_MAX = 8          # 單一算子 cost() 上限（有界深度文法結構性保證 <=3）
_DIM_OP_STEP_CLAMP = (1, 64)

# Phase U / ACT-148 — 字母表基數 stock 天花板（AlphabetGenesisBounded, Rule 9.33.4，meta⁶）。
_DEFAULT_DIM_ALPHABET_MAX = 16        # = 既有 8+9 字母外 headroom（字母基數天花板）
_DIM_ALPHABET_CLAMP = (1, 64)

# Phase V / ACT-151 — 深度算子基數 stock 天花板（DepthGenesisBounded, Rule 9.34.4，meta⁷）。
_DEFAULT_DIM_DEPTH_MAX = 16           # = 既有深度-2 算子外 headroom（深度算子基數天花板）
_DIM_DEPTH_CLAMP = (1, 64)

# Phase W / ACT-154 — 互遞迴算子基數 stock 天花板（RecursionGenesisBounded, Rule 9.35.4，meta⁸）。
_DEFAULT_DIM_RECUR_MAX = 16           # = 既有非遞迴算子外 headroom（互遞迴算子基數天花板）
_DIM_RECUR_CLAMP = (1, 64)
_DEFAULT_DIM_RECUR_NODES = 4          # 呼叫圖節點數上界（Rule 9.35.1；與 operator_recursion_genesis.recur_nodes 同源）
_DIM_RECUR_NODES_CLAMP = (2, 8)


class ChurnBoundExceeded(RuntimeError):
    """Rule 9.24.1：規則指紋 add↔retire churn 觸頂——禁止再採納，導 MFSM_ESCALATION。"""


class GraduationRatchetViolation(RuntimeError):
    """Rule 9.24.2：再採納已退役指紋但無 capability-delta——禁止同型震盪。"""


class CrossScorerChurnExceeded(RuntimeError):
    """Rule 9.28.3：跨評分器聚合採納速率觸頂——偵測耦合震盪/調參風暴，導 MFSM_ESCALATION。

    per-fingerprint ChurnBounded 對「N 條各自有界、合起來 A→B→A 耦合震盪」盲目（每指紋
    皆首採、churn=0）。本守門以「最近視窗內跨所有 calibration 命名空間的總採納次數」設界，
    補上 per-fingerprint 看不見的耦合無限擾動（Phase P PP-2）。
    """


class DimensionCardinalityExceeded(RuntimeError):
    """Rule 9.29.3：現存活躍價值維度數觸頂 stock 天花板——偵測維度基數爆炸，導 MFSM_ESCALATION。

    per-fingerprint ChurnBounded（每條新維度首採、churn=0）與 Phase P 聚合速率窗
    （value-dimension 不以 `-profile:` 結尾、且增維可慢到不觸發速率窗）對「**維度數本身單調
    膨脹**」皆盲目。本守門以「現存活躍 value-dimension 指紋數（stock）」設天花板，補上
    per-fingerprint/聚合速率都看不見的維度基數爆炸（Phase Q PQ-2）。
    """


class SwapCadenceExceeded(RuntimeError):
    """Rule 9.30.3：退役聯動 swap 聚合速率觸頂——偵測定基數旋轉重寫本體論，導 MFSM_ESCALATION。

    達 cardinality cap 後反覆 retire 一條換一條（net 基數=0、stock 永不觸頂、每指紋 churn<=1），
    per-fingerprint ChurnBounded 與 Phase Q DimensionCardinalityBounded（stock）**皆盲目**。本守門
    以「最近視窗內被標記為 swap 的採納次數（聚合速率）」設界，補上定基數旋轉（Phase R PR-2）。
    """


class SwapValueRatchetViolation(RuntimeError):
    """Rule 9.30.3：退役聯動 swap 入軸 necessity tier 未嚴格 > 出軸 tier + margin——禁止 A↔B↔A
    非單調價值震盪（退舊換新必須換來嚴格更必要的軸，否則只是旋轉重寫本體論）。"""


class VocabCardinalityExceeded(RuntimeError):
    """Rule 9.31.3：現存活躍詞彙發明字（vocab-genesis）數觸頂 stock 天花板——偵測詞彙基數爆炸
    （meta⁴ 詞彙無界擴充），導 MFSM_ESCALATION。

    Phase R 的有界性建立在「VOCAB 固定 8 條」前提上；Phase S 讓系統自我發明 VOCAB 外的新原始
    特徵字，詞彙基數本身會單調膨脹（每字首採、per-fingerprint churn=0；批次速率窗只看 swap，
    皆盲目）。本守門以「現存活躍 vocab-genesis 指紋數（stock）」設天花板（Phase S PS-1）。"""


class BatchSwapSizeExceeded(RuntimeError):
    """Rule 9.31.3：多維度批次退役聯動的 |out|/|in| 超 SDD_DIM_BATCH_MAX——偵測「一次退 m 換 n
    批次劫持整個本體論」（反 big-bang 批次本體論一次重寫），禁止 swap。"""


class BatchSwapValueRatchetViolation(RuntimeError):
    """Rule 9.31.3：批次入軸聚合 tier 未嚴格 > 批次出軸聚合 + margin，或 min(in_tiers) 未嚴格 >
    max(out_tiers)——批次內高低互抵夾帶退步 swap（per-swap 棘輪逐條看會放過），禁止 swap。"""


class BatchSwapCadenceExceeded(RuntimeError):
    """Rule 9.31.3：多維度批次退役聯動的批次操作聚合速率觸頂——偵測批次旋轉重寫本體論
    （一個原子批次≠n 次 swap，per-swap SwapCadence 計數失真而盲目），導 MFSM_ESCALATION。

    達 cardinality cap 後反覆批次退舊換新（每批不同字、net 基數非增），per-swap SwapCadence
    （單次操作計數）與單調棘輪（單次 tier 比較）**皆盲目**。本守門以「最近視窗內 distinct 批次
    操作數」設界，補上批次旋轉（Phase S PS-2，meta⁴）。"""


class OperatorCardinalityExceeded(RuntimeError):
    """Rule 9.32.4：現存活躍算子發明（operator-genesis）數觸頂 stock 天花板——偵測算子基數爆炸
    （meta⁵ 算子無界擴充），導 MFSM_ESCALATION。

    Phase S 的有界性建立在「TRANSFORMS/OPS 固定 6+4 條」前提上；Phase T 讓系統自我發明 TRANSFORMS/
    OPS 外的新算子，算子基數本身會單調膨脹（每個算子首採、per-fingerprint churn=0；維度/詞彙 stock
    天花板皆盲目）。本守門以「現存活躍 operator-genesis 指紋數（stock）」設天花板（Phase T PT-1）。"""


class OperatorComputabilityExceeded(RuntimeError):
    """Rule 9.32.3：自我發明算子非全函式 / 計算步數 cost 超 SDD_DIM_OP_STEP_MAX / 隱含遞迴迴圈——
    偵測「被發明物本身不可證停機」（meta⁵ 最深停機危害），結構性拒絕採納，呼叫端轉 MFSM_ESCALATION。

    Phase Q/R/S 的被發明物都是『資料』，執行它們的是人類寫死全函式，根本無可計算性問題。Phase T 的
    被發明物是『算子』=『可執行計算』——若無界可非全函式 / 無界步數 / 不停機。本守門把「圖靈完備 vs
    保證停機」正面釘進框架自我擴充的產物本身：每個被發明算子須結構性全函式 + 有界步數（Phase T PT-2）。"""


class AlphabetCardinalityExceeded(RuntimeError):
    """Rule 9.33.4：現存活躍字母發明（alphabet-genesis）數觸頂 stock 天花板——偵測字母基數爆炸
    （meta⁶ 字母表無界擴充），導 MFSM_ESCALATION。

    Phase T 的有界性建立在「PRIMITIVES/COMBINATORS 固定 8+9 條」前提上；Phase U 讓系統自我發明字母表外的
    新運算字母，字母基數本身會單調膨脹（每個字母首採、per-fingerprint churn=0；維度/詞彙/算子 stock 天花板
    皆盲目）。本守門以「現存活躍 alphabet-genesis 指紋數（stock）」設天花板（Phase U PU-1，meta⁶）。"""


class ComputabilityClosureViolation(RuntimeError):
    """Rule 9.33.3：自我發明字母使擴充後 G(A') 整個算子代數出現非全函式 / cost 超 SDD_DIM_OP_STEP_MAX 的
    算子——偵測「被發明的生成規則本身破壞可計算性閉包」（meta⁶ 最深停機危害），結構性拒絕採納，呼叫端轉
    MFSM_ESCALATION。

    Phase T 的逐算子可計算性建立在「字母表本身人類寫死全 total」前提；Phase U 的被發明物是『字母元素』=
    『會被算子生成文法用來生成整個算子代數的生成規則零件』——一個非全函式 / 無界步數的字母原子污染的是
    **整代數**。本守門把停機問題從『產物可證停機』升級為『生成規則的閉包可證停機』：採納前枚舉擴充字母表後
    G(A') 整代數驗 fuzz-total + cost<=step_max（Phase U PU-2，meta⁶）。"""


class DepthCardinalityExceeded(RuntimeError):
    """Rule 9.34.4：現存活躍深度算子發明（depth-genesis）數觸頂 stock 天花板——偵測深度算子基數爆炸
    （meta⁷ 深度本體論無界擴充），導 MFSM_ESCALATION。

    Phase U 的有界性建立在「組合深度凍結 <=2」前提上（被發明物是『字母』，整代數深度恆 2）。Phase V 讓系統
    自我發明組合深度 >2 的新複合算子，深度算子基數本身會單調膨脹（每個深度算子首採、per-fingerprint churn=0；
    維度/詞彙/算子/字母 stock 天花板皆盲目）。本守門以「現存活躍 depth-genesis 指紋數（stock）」設天花板
    （Phase V PV-1，meta⁷）。"""


class DepthClosureViolation(RuntimeError):
    """Rule 9.34.3：自我發明深度算子使擴充深度後 G(A,depth) 整個深度算子代數出現非全函式 / cost 超
    SDD_DIM_OP_STEP_MAX（因 cost==depth，即深度超界）的算子——偵測「被自我擴充的步數參數本身破壞深度可計算性
    閉包」（meta⁷ 迄今最深停機危害，因 cost==depth 而最直接），結構性拒絕採納，呼叫端轉 MFSM_ESCALATION。

    Phase T/U 的可計算性建立在「組合深度人類凍結 <=2、故 cost 是小常數」前提；Phase V 自我擴充組合深度本身，
    而 cost==depth，深度無界 = 步數無界 = 不保證停機。本守門把停機問題從『生成規則零件可證停機』升級為
    『生成規則的結構性深度（步數）參數可證停機』：採納前枚舉擴充深度後 G(A,depth) 整代數驗 fuzz-total +
    cost<=step_max（即深度<=step_max，Phase V PV-2，meta⁷）。"""


class RecursionCardinalityExceeded(RuntimeError):
    """Rule 9.35.4：現存活躍互遞迴算子發明（recursion-genesis）數觸頂 stock 天花板——偵測互遞迴算子基數爆炸
    （meta⁸ 互遞迴本體論無界擴充），導 MFSM_ESCALATION。

    Phase T~V 的有界性建立在「算子代數零遞迴、運算式是有限樹」前提上。Phase W 讓系統自我發明會呼叫其他
    算子 / 自呼叫的互遞迴算子，互遞迴算子基數本身會單調膨脹（每個互遞迴算子首採、per-fingerprint churn=0；
    維度/詞彙/算子/字母/深度 stock 天花板皆盲目）。本守門以「現存活躍 recursion-genesis 指紋數（stock）」設
    天花板（Phase W PW-1，meta⁸）。"""


class RecursionClosureViolation(RuntimeError):
    """Rule 9.35.3：自我發明互遞迴算子的呼叫圖含無證書環（環中無回邊嚴格遞減下有界 rank → 可能不停機）/
    fuel 超 SDD_DIM_OP_STEP_MAX / 整代數出現非全函式算子——偵測「被自我擴充的互遞迴圖結構不可證良基終止」
    （meta⁸ 迄今唯一質變停機危害），結構性拒絕採納，呼叫端轉 MFSM_ESCALATION。

    Phase T~V 的停機建立在「算子代數零遞迴、運算式是有限樹、cost 是結構性有限量」前提；Phase W 自我擴充
    『算子可互相呼叫 / 自呼叫』，運算式樹變含環圖，**判定任意含環圖是否停機 = 停機問題（不可判定）**，「有界
    步數」device 結構性失效。本守門把停機問題從『有界步數靜態量』升級為『良基停機證書』：採納前枚舉呼叫圖
    驗 (acyclic ∨ 每邊嚴格遞減下有界 rank) ∧ fuel<=step_max ∧ 整代數 fuzz-total（Phase W PW-2，meta⁸；用全新
    device「良基測度終止」取代失效的「有界步數」）。"""


class EmbodiedGroundingViolation(RuntimeError):
    """Rule 9.36：自我發明能力被 META_FSM 納入（MFSM_GROW）前的具身接地閘 fail-closed——grounded verdict
    缺客觀 ExecutionObservation（沙箱從未真正跑過/壞過 → OQS inconclusive）→ 結構性拒絕採納，導 MFSM_ESCALATION。

    與 TLA+ EmbodiedGroundingBounded 100% 同構：Phase L~W 元迴圈的「評估」端一路是合成語料勝率（從不啟動沙箱）；
    Phase X 在納入前要求具身 grounded-verdict（sdd-evaluator 沙箱實跑 + OQS 接地）。具身接地的停機反諷在於——為讓
    元迴圈在真實環境驗證，引入了「真實沙箱可能 hang」這個新不停機源。本 fail-closed 杜絕「無客觀觀測卻放行納入」
    （否則零觀測 stub 會四維皆 default 1.0 → false green，瓦解接地目的）；沙箱硬 timeout 映 grounded_fail（FSM 不
    wall-clock wait，收 verdict 而非等沙箱），把具身接地侷限在可證有界停機（Phase X PX-1，Rule 9.36）。"""


def churn_max() -> int:
    """讀 SDD_META_CHURN_MAX（env 可調），clamp[1,5]，預設 2。"""
    raw = os.environ.get("SDD_META_CHURN_MAX")
    if not raw:
        return _DEFAULT_CHURN_MAX
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_CHURN_MAX
    lo, hi = _CHURN_MAX_CLAMP
    return max(lo, min(hi, val))


def _clamp_int_env(name: str, default: int, clamp: tuple) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    lo, hi = clamp
    return max(lo, min(hi, val))


def calib_adopt_rate_max() -> int:
    """讀 SDD_CALIB_ADOPT_RATE_MAX（env 可調），clamp[2,32]，預設 6（Rule 9.28.3）。"""
    return _clamp_int_env("SDD_CALIB_ADOPT_RATE_MAX",
                          _DEFAULT_CALIB_ADOPT_RATE_MAX, _CALIB_ADOPT_RATE_CLAMP)


def calib_adopt_window() -> int:
    """讀 SDD_CALIB_ADOPT_WINDOW（env 可調），clamp[4,256]，預設 12（聚合速率視窗）。"""
    return _clamp_int_env("SDD_CALIB_ADOPT_WINDOW",
                          _DEFAULT_CALIB_ADOPT_WINDOW, _CALIB_ADOPT_WINDOW_CLAMP)


def dimension_cardinality_max() -> int:
    """讀 SDD_DIM_CARDINALITY_MAX（env 可調），clamp[1,32]，預設 16（Rule 9.29.3 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_CARDINALITY_MAX",
                          _DEFAULT_DIM_CARDINALITY_MAX, _DIM_CARDINALITY_CLAMP)


def dim_swap_rate_max() -> int:
    """讀 SDD_DIM_SWAP_RATE_MAX（env 可調），clamp[1,16]，預設 3（Rule 9.30.3 swap 聚合速率）。"""
    return _clamp_int_env("SDD_DIM_SWAP_RATE_MAX",
                          _DEFAULT_DIM_SWAP_RATE_MAX, _DIM_SWAP_RATE_CLAMP)


def dim_swap_window() -> int:
    """讀 SDD_DIM_SWAP_WINDOW（env 可調），clamp[4,256]，預設 12（swap 聚合速率視窗）。"""
    return _clamp_int_env("SDD_DIM_SWAP_WINDOW",
                          _DEFAULT_DIM_SWAP_WINDOW, _DIM_SWAP_WINDOW_CLAMP)


def dim_swap_margin() -> int:
    """讀 SDD_DIM_SWAP_MARGIN（env 可調），預設 0（入軸 tier 須嚴格 > 出軸 tier + margin）。"""
    raw = os.environ.get("SDD_DIM_SWAP_MARGIN")
    if not raw:
        return _DEFAULT_DIM_SWAP_MARGIN
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_DIM_SWAP_MARGIN


def dim_vocab_max() -> int:
    """讀 SDD_DIM_VOCAB_MAX（env 可調），clamp[1,64]，預設 24（Rule 9.31.3 詞彙 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_VOCAB_MAX", _DEFAULT_DIM_VOCAB_MAX, _DIM_VOCAB_CLAMP)


def dim_batch_max() -> int:
    """讀 SDD_DIM_BATCH_MAX（env 可調），clamp[1,8]，預設 3（Rule 9.31.3 反 big-bang 批次大小）。"""
    return _clamp_int_env("SDD_DIM_BATCH_MAX", _DEFAULT_DIM_BATCH_MAX, _DIM_BATCH_CLAMP)


def dim_batch_rate_max() -> int:
    """讀 SDD_DIM_BATCH_RATE_MAX（env 可調），clamp[1,8]，預設 2（Rule 9.31.3 批次操作速率）。"""
    return _clamp_int_env("SDD_DIM_BATCH_RATE_MAX", _DEFAULT_DIM_BATCH_RATE_MAX, _DIM_BATCH_RATE_CLAMP)


def dim_batch_window() -> int:
    """讀 SDD_DIM_BATCH_WINDOW（env 可調），clamp[4,256]，預設 12（批次操作速率視窗）。"""
    return _clamp_int_env("SDD_DIM_BATCH_WINDOW", _DEFAULT_DIM_BATCH_WINDOW, _DIM_BATCH_WINDOW_CLAMP)


def dim_batch_margin() -> int:
    """讀 SDD_DIM_BATCH_MARGIN（env 可調），預設 0（批次入軸聚合 tier 須嚴格 > 出軸聚合 + margin）。"""
    raw = os.environ.get("SDD_DIM_BATCH_MARGIN")
    if not raw:
        return _DEFAULT_DIM_BATCH_MARGIN
    try:
        return max(0, int(raw))
    except ValueError:
        return _DEFAULT_DIM_BATCH_MARGIN


def dim_op_max() -> int:
    """讀 SDD_DIM_OP_MAX（env 可調），clamp[1,64]，預設 16（Rule 9.32.4 算子 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_OP_MAX", _DEFAULT_DIM_OP_MAX, _DIM_OP_CLAMP)


def dim_op_step_max() -> int:
    """讀 SDD_DIM_OP_STEP_MAX（env 可調），clamp[1,64]，預設 8（Rule 9.32.3 算子可計算性步數上限）。"""
    return _clamp_int_env("SDD_DIM_OP_STEP_MAX", _DEFAULT_DIM_OP_STEP_MAX, _DIM_OP_STEP_CLAMP)


def dim_alphabet_max() -> int:
    """讀 SDD_DIM_ALPHABET_MAX（env 可調），clamp[1,64]，預設 16（Rule 9.33.4 字母表 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_ALPHABET_MAX", _DEFAULT_DIM_ALPHABET_MAX, _DIM_ALPHABET_CLAMP)


def dim_depth_max() -> int:
    """讀 SDD_DIM_DEPTH_MAX（env 可調），clamp[1,64]，預設 16（Rule 9.34.4 深度算子 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_DEPTH_MAX", _DEFAULT_DIM_DEPTH_MAX, _DIM_DEPTH_CLAMP)


def dim_recur_max() -> int:
    """讀 SDD_DIM_RECUR_MAX（env 可調），clamp[1,64]，預設 16（Rule 9.35.4 互遞迴算子 stock 天花板）。"""
    return _clamp_int_env("SDD_DIM_RECUR_MAX", _DEFAULT_DIM_RECUR_MAX, _DIM_RECUR_CLAMP)


def dim_recur_nodes() -> int:
    """讀 SDD_DIM_RECUR_NODES（env 可調），clamp[2,8]，預設 4（Rule 9.35.1 互遞迴呼叫圖節點數上界）。

    與 operator_recursion_genesis.recur_nodes() 同源同義（藍圖 §3.1 ACT-154 點名之 getter）；生成端用
    recur_nodes() 封呼叫圖大小，本 getter 供 monitor/守門側查同一上界，兩者讀同一 env。
    """
    return _clamp_int_env("SDD_DIM_RECUR_NODES", _DEFAULT_DIM_RECUR_NODES, _DIM_RECUR_NODES_CLAMP)


@dataclass
class GuardResult:
    allowed: bool
    is_readopt: bool
    churn: int
    churn_max: int
    reason: str = ""


def guard_readopt(
    fingerprint: str,
    capability_level: int,
    *,
    ledger_path: Optional[Path] = None,
) -> GuardResult:
    """檢查一次「規則採納」是否合法（不寫入 ledger，純判定）。

    - 全新指紋（非再採納）→ 一律放行。
    - 再採納（指紋曾被退役）→ 同時要求：
        (a) ChurnBounded：compute_churn < churn_max；
        (b) GraduationRatchet：capability_level > 最近退役當下的 capability_level。
      任一不滿足 → raise（呼叫端轉 MFSM_ESCALATION）。
    """
    led = _ledger.load_ledger(ledger_path)
    readopt = _ledger.is_readopt(fingerprint, ledger=led)
    churn = _ledger.compute_churn(fingerprint, ledger=led)
    cmax = churn_max()

    if not readopt:
        return GuardResult(allowed=True, is_readopt=False, churn=churn,
                           churn_max=cmax, reason="fresh-add（非再採納，放行）")

    # 再採納：先驗 ChurnBounded
    if churn >= cmax:
        raise ChurnBoundExceeded(
            f"指紋 churn={churn} ≥ SDD_META_CHURN_MAX={cmax}：偵測 add↔retire 抖動，"
            f"禁止再採納指紋 {fingerprint!r}，導 MFSM_ESCALATION（Rule 9.24.1）"
        )

    # 再驗 GraduationRatchet（capability-delta）
    last_cap = _ledger.last_retire_capability(fingerprint, ledger=led)
    if last_cap is not None and int(capability_level) <= int(last_cap):
        raise GraduationRatchetViolation(
            f"再採納指紋 {fingerprint!r} 但 capability_level={capability_level} "
            f"未嚴格高於退役當下 {last_cap}：無 capability-delta 的同型震盪，"
            f"禁止採納（Rule 9.24.2）"
        )

    return GuardResult(allowed=True, is_readopt=True, churn=churn, churn_max=cmax,
                       reason="re-adopt 合法（churn 未觸頂 + 有 capability-delta）")


@dataclass
class CalibrationGuardResult:
    allowed: bool
    window_adds: int
    rate_max: int
    window: int
    distinct_namespaces: int
    reason: str = ""


def guard_calibration_adoption(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> CalibrationGuardResult:
    """Rule 9.28.3 CrossScorerChurnBounded：採納一個 calibration profile 前的**聚合速率守門**.

    在 per-fingerprint `guard_readopt` 之上**再加一層**：跨所有 calibration 命名空間
    （`*-profile:`），最近 `calib_adopt_window()` 筆事件中的總採納次數若已達
    `calib_adopt_rate_max()`，視為調參風暴 / 跨評分器耦合震盪 → raise（呼叫端轉
    MFSM_ESCALATION）。非 calibration 指紋（如 SLV 規則）不受此守門影響。

    ⚠️ 命名 vs 實作（誠實標註，消除「環偵測」字面誤導）：本守門對「A→B→A 耦合震盪環」
    採**聚合速率窗近似實現**（single-counter 抽象：聚合採納速率窗 + `distinct_namespaces`
    ≥2 的多命名空間診斷標籤），**並非顯式拓撲環偵測**（不重建採納順序圖、不找出實際 A→B→A
    循環邊）。理由：per-fingerprint churn 對「每指紋首採、合起來往復」盲目，而「密集跨命名
    空間採納」是耦合震盪的充分可觀測代理——只要聚合速率觸頂即攔停，無論底層是否真為閉環。
    更緊的「跨命名空間滑動窗聚合速率 + A→B→A 往復」語意由 runtime（本函式）+ chaos
    （`JOINT_CALIBRATION_FLAP` 100 輪 bounded）enforce/驗收（藍圖 §3.4 行 346 誠實分工）。
    """
    if not _ledger.is_calibration_fingerprint(fingerprint):
        return CalibrationGuardResult(
            allowed=True, window_adds=0, rate_max=calib_adopt_rate_max(),
            window=calib_adopt_window(), distinct_namespaces=0,
            reason="非 calibration 指紋（不受聚合速率守門）")
    win = calib_adopt_window()
    rate_max = calib_adopt_rate_max()
    led = _ledger.load_ledger(ledger_path)
    window_adds = _ledger.calibration_adds_in_window(win, ledger=led)
    distinct = len(_ledger.distinct_calibration_namespaces_in_window(win, ledger=led))
    if window_adds >= rate_max:
        coupling = "（疑似 A→B→A 跨評分器耦合震盪）" if distinct >= 2 else "（單評分器調參抖動）"
        raise CrossScorerChurnExceeded(
            f"最近 {win} 筆內 calibration 採納 {window_adds} 次 ≥ "
            f"SDD_CALIB_ADOPT_RATE_MAX={rate_max}{coupling}：整體價值系統不收斂，"
            f"禁止再採納，導 MFSM_ESCALATION（Rule 9.28.3）"
        )
    return CalibrationGuardResult(
        allowed=True, window_adds=window_adds, rate_max=rate_max, window=win,
        distinct_namespaces=distinct, reason="聚合速率未觸頂（放行）")


@dataclass
class DimensionGuardResult:
    allowed: bool
    active: int
    cardinality_max: int
    reason: str = ""


def guard_dimension_expansion(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> DimensionGuardResult:
    """Rule 9.29.3 DimensionCardinalityBounded：採納一條 value-dimension 前的**stock 天花板守門**.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍
    value-dimension 維度數（不含本次將 (re)add 的指紋）若已達 `dimension_cardinality_max()`，
    視為維度基數爆炸 / 本體論無界擴張 → raise（呼叫端轉 MFSM_ESCALATION）。非 value-dimension
    指紋（如 SLV 規則、scorer-profile）不受此守門影響。

    語意：最多容許 `dimension_cardinality_max()` 條同時活躍的價值維度。第 (max+1) 條（在已滿時）
    被拒絕——這正補上 per-fingerprint churn（每維度首採 churn=0）與 Phase P 聚合速率窗
    （value-dimension 不以 `-profile:` 結尾）都看不見的維度基數單調膨脹（Phase Q PQ-2）。
    """
    if not _ledger.is_dimension_fingerprint(fingerprint):
        return DimensionGuardResult(
            allowed=True, active=0, cardinality_max=dimension_cardinality_max(),
            reason="非 value-dimension 指紋（不受 stock 天花板守門）")
    dmax = dimension_cardinality_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_value_dimensions(ledger=led)
    # 排除本次將 (re)add 的指紋本身（re-adopt 退役過的維度時，它已不在活躍集合內；
    # fresh-add 時也不在）——active 為「除本維度外」的現存活躍數。
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= dmax:
        raise DimensionCardinalityExceeded(
            f"現存活躍價值維度 {active} 條 ≥ SDD_DIM_CARDINALITY_MAX={dmax}："
            f"維度基數爆炸 / 本體論無界擴張，禁止再增維，導 MFSM_ESCALATION（Rule 9.29.3）。"
            f"請人工檢視是否真需更多維度，或退役舊維度換新維度。"
        )
    return DimensionGuardResult(
        allowed=True, active=active, cardinality_max=dmax,
        reason="維度基數未觸頂（放行）")


@dataclass
class SwapGuardResult:
    allowed: bool
    in_tier: int
    out_tier: int
    margin: int
    window_swaps: int
    rate_max: int
    window: int
    reason: str = ""


def guard_dimension_swap(
    out_fingerprint: str,
    in_fingerprint: str,
    out_tier: int,
    in_tier: int,
    *,
    ledger_path: Optional[Path] = None,
) -> SwapGuardResult:
    """Rule 9.30.3 退役聯動雙鎖：在基數封頂時「退最低必要性出軸、換更必要入軸」前的守門.

    雙鎖（任一觸發 → raise，呼叫端轉 MFSM_ESCALATION / 拒絕 swap）：
      (a) **單調價值棘輪**：in_tier 須**嚴格 >** out_tier + `dim_swap_margin()`——退舊換新必須換來
          嚴格更必要的軸，否則 A↔B↔A 旋轉因價值不單調被擋（raise SwapValueRatchetViolation）。
      (b) **swap 聚合速率窗**：最近 `dim_swap_window()` 筆內被標記為 swap 的採納次數若已達
          `dim_swap_rate_max()`，視為定基數旋轉重寫本體論 → raise SwapCadenceExceeded。

    補上 per-fingerprint churn（每指紋只動一次）與 Phase Q cardinality stock（net 基數=0、永不觸頂）
    都看不見的定基數旋轉（Phase R PR-2）。in/out 皆須為 value-dimension 指紋。
    """
    if not (_ledger.is_dimension_fingerprint(in_fingerprint)
            and _ledger.is_dimension_fingerprint(out_fingerprint)):
        raise ValueError("guard_dimension_swap 僅適用 value-dimension 指紋（in/out 皆須是維度）")
    margin = dim_swap_margin()
    # (a) 單調價值棘輪
    if int(in_tier) <= int(out_tier) + margin:
        raise SwapValueRatchetViolation(
            f"退役聯動 swap 入軸 tier={in_tier} 未嚴格 > 出軸 tier={out_tier} + margin={margin}："
            f"非單調價值震盪（A↔B↔A 旋轉），禁止 swap（Rule 9.30.3）"
        )
    # (b) swap 聚合速率窗
    win = dim_swap_window()
    rate_max = dim_swap_rate_max()
    led = _ledger.load_ledger(ledger_path)
    window_swaps = _ledger.swap_adds_in_window(win, ledger=led)
    if window_swaps >= rate_max:
        raise SwapCadenceExceeded(
            f"最近 {win} 筆內退役聯動 swap {window_swaps} 次 ≥ SDD_DIM_SWAP_RATE_MAX={rate_max}："
            f"本體論在天花板上定基數旋轉重寫過快，禁止再 swap，導 MFSM_ESCALATION（Rule 9.30.3）。"
            f"請人工檢視是否真需替換維度。"
        )
    return SwapGuardResult(
        allowed=True, in_tier=int(in_tier), out_tier=int(out_tier), margin=margin,
        window_swaps=window_swaps, rate_max=rate_max, window=win,
        reason="退役聯動雙鎖未觸頂（單調價值棘輪 + swap 速率窗皆放行）")


@dataclass
class VocabGuardResult:
    allowed: bool
    active: int
    vocab_max: int
    reason: str = ""


def guard_vocab_genesis(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> VocabGuardResult:
    """Rule 9.31.3 VocabGenesisBounded：採納一個 vocab-genesis 詞彙發明字前的 **stock 天花板守門**（meta⁴）.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍 vocab-genesis
    詞彙字數（不含本次將 (re)add 的指紋）若已達 `dim_vocab_max()`，視為詞彙基數爆炸 / VOCAB 無界
    擴充 → raise（呼叫端轉 MFSM_ESCALATION）。非 vocab-genesis 指紋（如維度、scorer-profile）不受
    此守門影響。

    語意：最多容許 `dim_vocab_max()` 個同時活躍的詞彙發明字。第 (max+1) 個（在已滿時）被拒絕——
    這正補上 per-fingerprint churn（每字首採 churn=0）與批次速率窗（只看 swap）都看不見的詞彙基數
    單調膨脹（Phase S PS-1，meta⁴）。
    """
    if not _ledger.is_vocab_genesis_fingerprint(fingerprint):
        return VocabGuardResult(
            allowed=True, active=0, vocab_max=dim_vocab_max(),
            reason="非 vocab-genesis 指紋（不受詞彙 stock 天花板守門）")
    vmax = dim_vocab_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_vocab_genesis_features(ledger=led)
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= vmax:
        raise VocabCardinalityExceeded(
            f"現存活躍詞彙發明字 {active} 個 ≥ SDD_DIM_VOCAB_MAX={vmax}："
            f"詞彙基數爆炸 / VOCAB 無界擴充，禁止再發明詞彙，導 MFSM_ESCALATION（Rule 9.31.3）。"
            f"請人工檢視是否真需更多原始特徵字。"
        )
    return VocabGuardResult(
        allowed=True, active=active, vocab_max=vmax,
        reason="詞彙基數未觸頂（放行）")


@dataclass
class BatchSwapGuardResult:
    allowed: bool
    out_size: int
    in_size: int
    batch_max: int
    in_sum: int
    out_sum: int
    margin: int
    min_in_tier: int
    max_out_tier: int
    window_batches: int
    rate_max: int
    window: int
    reason: str = ""


def guard_batch_swap(
    out_fingerprints,
    in_fingerprints,
    out_tiers,
    in_tiers,
    *,
    ledger_path: Optional[Path] = None,
) -> BatchSwapGuardResult:
    """Rule 9.31.3 多維度批次退役聯動三鎖（meta⁴）：在基數封頂時「批次退 m 換 n」前的守門.

    三鎖（任一觸發 → raise，呼叫端轉 MFSM_ESCALATION / 拒絕批次 swap）：
      (a) **批次大小界 + net 非增**：|out|/|in| <= `dim_batch_max()`（反 big-bang 本體論一次重寫），
          且 |in| <= |out|（net cardinality 非增）→ 否則 raise BatchSwapSizeExceeded。
      (b) **批次聚合單調棘輪**：sum(in_tiers) 須**嚴格 >** sum(out_tiers) + `dim_batch_margin()`，
          **且** min(in_tiers) **嚴格 >** max(out_tiers)——杜絕「批次內高低互抵夾帶退步 swap」
          （per-swap 棘輪逐條看會放過），且擋 {A,B}↔{C,D} 批次旋轉 → 否則 raise
          BatchSwapValueRatchetViolation。
      (c) **批次操作聚合速率窗**：最近 `dim_batch_window()` 筆內 distinct 批次操作數若已達
          `dim_batch_rate_max()`，視為批次旋轉重寫本體論 → raise BatchSwapCadenceExceeded。

    補上 per-swap SwapCadence（單次操作計數）與單調棘輪（單次 tier 比較）都看不見的批次大小無界 /
    批次內互抵 / 批次旋轉（Phase S PS-2）。in/out 皆須為 value-dimension 指紋。
    """
    out_fps = list(out_fingerprints)
    in_fps = list(in_fingerprints)
    out_t = [int(t) for t in out_tiers]
    in_t = [int(t) for t in in_tiers]
    if not out_fps or not in_fps:
        raise ValueError("guard_batch_swap 需非空的 out/in 維度集合")
    if len(out_fps) != len(out_t) or len(in_fps) != len(in_t):
        raise ValueError("guard_batch_swap：fingerprints 與 tiers 長度須一致")
    if not all(_ledger.is_dimension_fingerprint(fp) for fp in out_fps + in_fps):
        raise ValueError("guard_batch_swap 僅適用 value-dimension 指紋（in/out 皆須是維度）")

    bmax = dim_batch_max()
    margin = dim_batch_margin()
    win = dim_batch_window()
    rate_max = dim_batch_rate_max()

    # (a) 批次大小界 + net 非增
    if len(out_fps) > bmax or len(in_fps) > bmax:
        raise BatchSwapSizeExceeded(
            f"批次退役 |out|={len(out_fps)} / |in|={len(in_fps)} 超 SDD_DIM_BATCH_MAX={bmax}："
            f"批次一次劫持整個本體論，禁止 swap（Rule 9.31.3 反 big-bang 批次）"
        )
    if len(in_fps) > len(out_fps):
        raise BatchSwapSizeExceeded(
            f"批次退役 |in|={len(in_fps)} > |out|={len(out_fps)}：net cardinality 增長，"
            f"禁止 swap（Rule 9.31.3 net 基數非增）"
        )
    # (b) 批次聚合單調棘輪 + 杜絕批次內互抵
    in_sum, out_sum = sum(in_t), sum(out_t)
    if in_sum <= out_sum + margin:
        raise BatchSwapValueRatchetViolation(
            f"批次入軸聚合 tier={in_sum} 未嚴格 > 批次出軸聚合 tier={out_sum} + margin={margin}："
            f"批次非單調價值增益（批次旋轉），禁止 swap（Rule 9.31.3）"
        )
    if min(in_t) <= max(out_t):
        raise BatchSwapValueRatchetViolation(
            f"批次最低入軸 tier={min(in_t)} 未嚴格 > 最高出軸 tier={max(out_t)}："
            f"批次內高低互抵夾帶退步 swap，禁止 swap（Rule 9.31.3 杜絕批次內互抵）"
        )
    # (c) 批次操作聚合速率窗
    led = _ledger.load_ledger(ledger_path)
    window_batches = _ledger.batch_swap_ops_in_window(win, ledger=led)
    if window_batches >= rate_max:
        raise BatchSwapCadenceExceeded(
            f"最近 {win} 筆內批次退役操作 {window_batches} 次 ≥ SDD_DIM_BATCH_RATE_MAX={rate_max}："
            f"本體論批次旋轉重寫過頻，禁止再批次 swap，導 MFSM_ESCALATION（Rule 9.31.3）。"
            f"請人工檢視是否真需批次替換維度。"
        )
    return BatchSwapGuardResult(
        allowed=True, out_size=len(out_fps), in_size=len(in_fps), batch_max=bmax,
        in_sum=in_sum, out_sum=out_sum, margin=margin,
        min_in_tier=min(in_t), max_out_tier=max(out_t),
        window_batches=window_batches, rate_max=rate_max, window=win,
        reason="批次退役三鎖未觸頂（批次大小界 + 批次聚合棘輪 + 批次速率窗皆放行）")


@dataclass
class OperatorGuardResult:
    allowed: bool
    active: int
    op_max: int
    reason: str = ""


def guard_operator_genesis(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> OperatorGuardResult:
    """Rule 9.32.4 OperatorGenesisBounded：採納一個 operator-genesis 算子發明前的 **stock 天花板守門**（meta⁵）.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍 operator-genesis
    算子數（不含本次將 (re)add 的指紋）若已達 `dim_op_max()`，視為算子基數爆炸 / OPS 無界擴充 →
    raise（呼叫端轉 MFSM_ESCALATION）。非 operator-genesis 指紋（如維度、詞彙、scorer-profile）不受
    此守門影響。

    語意：最多容許 `dim_op_max()` 個同時活躍的算子發明。第 (max+1) 個（在已滿時）被拒絕——這正補上
    per-fingerprint churn（每算子首採 churn=0）與維度/詞彙 stock 天花板都看不見的算子基數單調膨脹
    （Phase T PT-1，meta⁵）。
    """
    if not _ledger.is_operator_genesis_fingerprint(fingerprint):
        return OperatorGuardResult(
            allowed=True, active=0, op_max=dim_op_max(),
            reason="非 operator-genesis 指紋（不受算子 stock 天花板守門）")
    omax = dim_op_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_operator_genesis_features(ledger=led)
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= omax:
        raise OperatorCardinalityExceeded(
            f"現存活躍算子發明 {active} 個 ≥ SDD_DIM_OP_MAX={omax}："
            f"算子基數爆炸 / OPS 無界擴充，禁止再發明算子，導 MFSM_ESCALATION（Rule 9.32.4）。"
            f"請人工檢視是否真需更多轉換/聚合算子。"
        )
    return OperatorGuardResult(
        allowed=True, active=active, op_max=omax,
        reason="算子基數未觸頂（放行）")


@dataclass
class OperatorComputabilityResult:
    allowed: bool
    cost: int
    step_max: int
    total: bool
    reason: str = ""


def guard_operator_computability(
    operator,
    *,
    ledger_path: Optional[Path] = None,
) -> OperatorComputabilityResult:
    """Rule 9.32.3 OperatorComputabilityBounded：採納一個算子發明前的 **可計算性守門**（meta⁵ 最深停機）.

    把「圖靈完備 vs 保證停機」正面釘進框架自我擴充的產物本身——被發明物（算子=可執行計算）本身須可證
    停機。三證（任一不過 → raise OperatorComputabilityExceeded，呼叫端轉 MFSM_ESCALATION）：
      (a) **有界步數**：`operator.cost()` <= `dim_op_step_max()`（有界深度運算式樹結構性保證 <=3）；
      (b) **全函式**：`operator.is_total()` 對極端 fuzz 輸入零例外、無 NaN/inf（total PRIMITIVES ×
          total COMBINATORS 結構性保證）；
      (c) 零遞迴零迴圈由算子文法結構保證（test ast 斷言算子求值路徑無 while/遞迴，本守門以 (a)(b) 把
          結構保證轉成可機器驗證的客觀守門）。

    duck-typed：`operator` 需 `.cost()->int` 與 `.is_total()->bool`（e.g. operator_genesis.GenesisOperator；
    本守門不 import operator_genesis，避免循環依賴）。
    """
    step_max = dim_op_step_max()
    try:
        cost = int(operator.cost())
    except Exception as exc:  # noqa: BLE001
        raise OperatorComputabilityExceeded(
            f"算子 cost() 不可求值（{exc}）：被發明物不可證停機，禁止採納（Rule 9.32.3）")
    if cost > step_max:
        raise OperatorComputabilityExceeded(
            f"算子計算步數 cost={cost} > SDD_DIM_OP_STEP_MAX={step_max}："
            f"被發明算子計算步數無界（可能隱含遞迴/迴圈/超深運算式樹），禁止採納，導 MFSM_ESCALATION"
            f"（Rule 9.32.3 算子可計算性——把停機問題釘進自我擴充產物本身）。"
        )
    total = bool(operator.is_total())
    if not total:
        raise OperatorComputabilityExceeded(
            f"算子非全函式（某輸入無定義/拋例外/NaN/inf）：被發明物對某輸入不可證停機，禁止採納，"
            f"導 MFSM_ESCALATION（Rule 9.32.3 全函式保證）。"
        )
    return OperatorComputabilityResult(
        allowed=True, cost=cost, step_max=step_max, total=total,
        reason="算子可計算性三證通過（全函式 + cost<=step_max + 有界深度文法零遞迴零迴圈）")


@dataclass
class AlphabetGuardResult:
    allowed: bool
    active: int
    alphabet_max: int
    reason: str = ""


def guard_alphabet_genesis(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> AlphabetGuardResult:
    """Rule 9.33.4 AlphabetGenesisBounded：採納一個 alphabet-genesis 字母發明前的 **stock 天花板守門**（meta⁶）.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍 alphabet-genesis 字母數
    （不含本次將 (re)add 的指紋）若已達 `dim_alphabet_max()`，視為字母基數爆炸 / 字母表無界擴充 → raise
    （呼叫端轉 MFSM_ESCALATION）。非 alphabet-genesis 指紋（如維度、詞彙、算子、scorer-profile）不受此守門影響。

    語意：最多容許 `dim_alphabet_max()` 個同時活躍的字母發明。第 (max+1) 個（在已滿時）被拒絕——這正補上
    per-fingerprint churn（每字母首採 churn=0）與維度/詞彙/算子 stock 天花板都看不見的字母基數單調膨脹
    （Phase U PU-1，meta⁶）。
    """
    if not _ledger.is_alphabet_genesis_fingerprint(fingerprint):
        return AlphabetGuardResult(
            allowed=True, active=0, alphabet_max=dim_alphabet_max(),
            reason="非 alphabet-genesis 指紋（不受字母 stock 天花板守門）")
    amax = dim_alphabet_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_alphabet_genesis_features(ledger=led)
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= amax:
        raise AlphabetCardinalityExceeded(
            f"現存活躍字母發明 {active} 個 ≥ SDD_DIM_ALPHABET_MAX={amax}："
            f"字母基數爆炸 / 字母表無界擴充，禁止再發明字母，導 MFSM_ESCALATION（Rule 9.33.4）。"
            f"請人工檢視是否真需更多原始算子/組合算子字母。"
        )
    return AlphabetGuardResult(
        allowed=True, active=active, alphabet_max=amax,
        reason="字母基數未觸頂（放行）")


@dataclass
class ClosureGuardResult:
    allowed: bool
    total: bool
    max_cost: int
    step_max: int
    n_operators: int
    reason: str = ""


def guard_computability_closure(
    element,
    *,
    ledger_path: Optional[Path] = None,
) -> ClosureGuardResult:
    """Rule 9.33.3 ComputabilityClosureBounded：採納一個字母發明前的 **可計算性閉包守門**（meta⁶ 最深停機）.

    把「圖靈完備 vs 保證停機」正面釘進框架自我擴充的**生成規則本身**——被發明字母（生成算子的規則零件）
    擴充字母表後，文法 G(A') 生成的整個（仍有限的）算子代數須**每一個算子**皆可證停機。閉包三證（任一不過
    → raise ComputabilityClosureViolation，呼叫端轉 MFSM_ESCALATION）：
      (a) **閉包有界步數**：G(A') 整代數 max_cost <= `dim_op_step_max()`（有界深度文法結構性保證 <=3）；
      (b) **閉包全函式**：G(A') 整代數對極端 fuzz 輸入零例外、無 NaN/inf（total 原子的合成仍 total）；
      (c) 零遞迴零迴圈由字母表生成文法結構保證（test ast 斷言字母求值路徑無 while/遞迴，本守門以 (a)(b) 把
          結構保證轉成可機器驗證的客觀守門）。

    duck-typed：`element` 需 `.closure_report()` 回傳具 `.total`(bool)/`.max_cost`(int)/`.n_operators`(int)
    的物件（e.g. operator_alphabet_genesis.InventedPrimitive/InventedCombinator；本守門不 import
    operator_alphabet_genesis，避免循環依賴）。
    """
    step_max = dim_op_step_max()
    try:
        rep = element.closure_report()
        max_cost = int(rep.max_cost)
        total = bool(rep.total)
        n_ops = int(getattr(rep, "n_operators", 0))
    except Exception as exc:  # noqa: BLE001
        raise ComputabilityClosureViolation(
            f"字母可計算性閉包報告不可求值（{exc}）：被發明的生成規則本身不可證閉包停機，禁止採納（Rule 9.33.3）")
    if max_cost > step_max:
        raise ComputabilityClosureViolation(
            f"擴充字母表後 G(A') 整代數 max_cost={max_cost} > SDD_DIM_OP_STEP_MAX={step_max}："
            f"被發明字母使生成的算子代數計算步數無界（閉包破裂），禁止採納，導 MFSM_ESCALATION"
            f"（Rule 9.33.3 可計算性閉包——把停機問題釘進自我擴充的生成規則本身）。"
        )
    if not total:
        raise ComputabilityClosureViolation(
            f"擴充字母表後 G(A') 整代數出現非全函式算子（某輸入無定義/拋例外/NaN/inf）：被發明字母破壞可計算性"
            f"閉包，禁止採納，導 MFSM_ESCALATION（Rule 9.33.3 閉包全函式保證）。"
        )
    return ClosureGuardResult(
        allowed=True, total=total, max_cost=max_cost, step_max=step_max, n_operators=n_ops,
        reason="可計算性閉包三證通過（G(A') 整代數全函式 + max_cost<=step_max + 有界文法零遞迴零迴圈）")


@dataclass
class DepthGuardResult:
    allowed: bool
    active: int
    depth_max: int
    reason: str = ""


def guard_depth_genesis(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> DepthGuardResult:
    """Rule 9.34.4 DepthGenesisBounded：採納一個 depth-genesis 深度算子發明前的 **stock 天花板守門**（meta⁷）.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍 depth-genesis 深度算子數
    （不含本次將 (re)add 的指紋）若已達 `dim_depth_max()`，視為深度算子基數爆炸 / 深度本體論無界擴充 → raise
    （呼叫端轉 MFSM_ESCALATION）。非 depth-genesis 指紋（如維度、詞彙、算子、字母、scorer-profile）不受此守門影響。

    語意：最多容許 `dim_depth_max()` 個同時活躍的深度算子發明。第 (max+1) 個（在已滿時）被拒絕——這正補上
    per-fingerprint churn（每深度算子首採 churn=0）與維度/詞彙/算子/字母 stock 天花板都看不見的深度算子基數
    單調膨脹（Phase V PV-1，meta⁷）。
    """
    if not _ledger.is_depth_genesis_fingerprint(fingerprint):
        return DepthGuardResult(
            allowed=True, active=0, depth_max=dim_depth_max(),
            reason="非 depth-genesis 指紋（不受深度 stock 天花板守門）")
    dmax = dim_depth_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_depth_genesis_features(ledger=led)
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= dmax:
        raise DepthCardinalityExceeded(
            f"現存活躍深度算子發明 {active} 個 ≥ SDD_DIM_DEPTH_MAX={dmax}："
            f"深度算子基數爆炸 / 深度本體論無界擴充，禁止再發明深度算子，導 MFSM_ESCALATION（Rule 9.34.4）。"
            f"請人工檢視是否真需更深的複合算子。"
        )
    return DepthGuardResult(
        allowed=True, active=active, depth_max=dmax,
        reason="深度算子基數未觸頂（放行）")


@dataclass
class DepthClosureGuardResult:
    allowed: bool
    total: bool
    max_cost: int
    step_max: int
    depth: int
    n_operators: int
    reason: str = ""


def guard_depth_closure(
    depth_op,
    *,
    ledger_path: Optional[Path] = None,
) -> DepthClosureGuardResult:
    """Rule 9.34.3 DepthClosureBounded：採納一個深度算子發明前的 **深度可計算性閉包守門**（meta⁷ 迄今最深停機）.

    把「圖靈完備 vs 保證停機」正面釘進框架自我擴充文法的**結構性深度（步數）參數本身**——被自我擴充的組合深度
    **直接就是計算步數**（cost==depth），擴充深度後文法 G(A,depth) 生成的整個（仍有限的）深度算子代數須**每一個
    算子**皆可證停機。閉包三證（任一不過 → raise DepthClosureViolation，呼叫端轉 MFSM_ESCALATION）：
      (a) **閉包有界步數**：G(A,depth) 整代數 max_cost <= `dim_op_step_max()`（因 cost==depth，即深度<=step_max）；
      (b) **閉包全函式**：G(A,depth) 整代數對極端 fuzz 輸入零例外、無 NaN/inf（total 深度-2 基底 ∘ total 一元鏈
          的合成仍 total）；
      (c) 零遞迴零迴圈由深度生成文法結構保證（test ast 斷言深度求值路徑無 while/遞迴，本守門以 (a)(b) 把結構
          保證轉成可機器驗證的客觀守門）。

    duck-typed：`depth_op` 需 `.closure_report()` 回傳具 `.total`(bool)/`.max_cost`(int)/`.n_operators`(int)/
    `.depth`(int) 的物件（e.g. operator_depth_genesis.DepthOperator；本守門不 import operator_depth_genesis，
    避免循環依賴）。
    """
    step_max = dim_op_step_max()
    try:
        rep = depth_op.closure_report()
        max_cost = int(rep.max_cost)
        total = bool(rep.total)
        n_ops = int(getattr(rep, "n_operators", 0))
        depth = int(getattr(rep, "depth", 0))
    except Exception as exc:  # noqa: BLE001
        raise DepthClosureViolation(
            f"深度可計算性閉包報告不可求值（{exc}）：被自我擴充的步數參數本身不可證閉包停機，禁止採納（Rule 9.34.3）")
    if max_cost > step_max:
        raise DepthClosureViolation(
            f"擴充深度後 G(A,depth) 整代數 max_cost={max_cost} > SDD_DIM_OP_STEP_MAX={step_max}（depth={depth}）："
            f"被自我擴充的組合深度使生成的算子代數計算步數無界（因 cost==depth，深度本身超界 → 閉包破裂），禁止採納，"
            f"導 MFSM_ESCALATION（Rule 9.34.3 深度可計算性閉包——把停機問題釘進自我擴充文法的結構性步數參數本身）。"
        )
    if not total:
        raise DepthClosureViolation(
            f"擴充深度後 G(A,depth) 整代數出現非全函式算子（某輸入無定義/拋例外/NaN/inf）：被自我擴充的深度算子破壞"
            f"深度可計算性閉包，禁止採納，導 MFSM_ESCALATION（Rule 9.34.3 閉包全函式保證）。"
        )
    return DepthClosureGuardResult(
        allowed=True, total=total, max_cost=max_cost, step_max=step_max, depth=depth, n_operators=n_ops,
        reason="深度可計算性閉包三證通過（G(A,depth) 整代數全函式 + max_cost==depth<=step_max + 有界文法零遞迴零迴圈）")


@dataclass
class RecursionGuardResult:
    allowed: bool
    active: int
    recur_max: int
    reason: str = ""


def guard_recursion_genesis(
    fingerprint: str,
    *,
    ledger_path: Optional[Path] = None,
) -> RecursionGuardResult:
    """Rule 9.35.4 RecursionGenesisBounded：採納一個 recursion-genesis 互遞迴算子發明前的 **stock 天花板守門**（meta⁸）.

    在 per-fingerprint `guard_readopt`（churn/ratchet）之上**再加一層**：現存活躍 recursion-genesis 互遞迴算子數
    （不含本次將 (re)add 的指紋）若已達 `dim_recur_max()`，視為互遞迴算子基數爆炸 / 互遞迴本體論無界擴充 →
    raise（呼叫端轉 MFSM_ESCALATION）。非 recursion-genesis 指紋（如維度、詞彙、算子、字母、深度、scorer-profile）
    不受此守門影響。

    語意：最多容許 `dim_recur_max()` 個同時活躍的互遞迴算子發明。第 (max+1) 個（在已滿時）被拒絕——這正補上
    per-fingerprint churn（每互遞迴算子首採 churn=0）與維度/詞彙/算子/字母/深度 stock 天花板都看不見的互遞迴
    算子基數單調膨脹（Phase W PW-1，meta⁸）。
    """
    if not _ledger.is_recursion_genesis_fingerprint(fingerprint):
        return RecursionGuardResult(
            allowed=True, active=0, recur_max=dim_recur_max(),
            reason="非 recursion-genesis 指紋（不受互遞迴 stock 天花板守門）")
    rmax = dim_recur_max()
    led = _ledger.load_ledger(ledger_path)
    active_list = _ledger.active_recursion_genesis_features(ledger=led)
    active = len([fp for fp in active_list if fp != fingerprint])
    if active >= rmax:
        raise RecursionCardinalityExceeded(
            f"現存活躍互遞迴算子發明 {active} 個 ≥ SDD_DIM_RECUR_MAX={rmax}："
            f"互遞迴算子基數爆炸 / 互遞迴本體論無界擴充，禁止再發明互遞迴算子，導 MFSM_ESCALATION（Rule 9.35.4）。"
            f"請人工檢視是否真需更多互遞迴複合算子。"
        )
    return RecursionGuardResult(
        allowed=True, active=active, recur_max=rmax,
        reason="互遞迴算子基數未觸頂（放行）")


@dataclass
class RecursionClosureGuardResult:
    allowed: bool
    total: bool
    terminating: bool
    fuel: int
    max_cost: int
    step_max: int
    n_operators: int
    reason: str = ""


def guard_recursion_closure(
    rec_op,
    *,
    ledger_path: Optional[Path] = None,
) -> RecursionClosureGuardResult:
    """Rule 9.35.3 RecursionClosureBounded：採納一個互遞迴算子發明前的 **良基停機證書守門**（meta⁸ 迄今唯一質變停機）.

    把「圖靈完備 vs 保證停機」正面釘在**可判定 vs 不可判定的臨界線本身**——被自我擴充的『算子互遞迴圖』讓
    判定停機從可判定翻不可判定（判定任意含環圖停機 = 停機問題），故「有界步數」device 結構性失效。採納前必須
    出示**良基停機證書**：枚舉互遞迴算子（及其同拓樸 base 變動的整代數）的呼叫圖，斷言可證良基終止。證書四證
    （任一不過 → raise RecursionClosureViolation，呼叫端轉 MFSM_ESCALATION）：
      (a) **可證終止**：呼叫圖 acyclic（DAG，沿拓樸序至多訪 |N| 次必終止）∨ 每邊嚴格遞減下有界（>=0）rank
          （良基測度 → 無無窮遞減鏈 → 必終止）；
      (b) **燃料有界**：`fuel` <= `dim_op_step_max()`（良基停機證書的硬燃料上界）；
      (c) **閉包全函式**：整代數對極端 fuzz 輸入零例外、無 NaN/inf；
      (d) 求值器零真遞迴零 while 由互遞迴生成文法結構保證（test ast 斷言求值路徑無 while/無自呼叫函式，本守門以
          (a)(b)(c) 把結構保證轉成可機器驗證的客觀守門）。

    duck-typed：`rec_op` 需 `.closure_report()` 回傳具 `.total`(bool)/`.terminating`(bool)/`.fuel`(int)/
    `.max_cost`(int)/`.n_operators`(int) 的物件（e.g. operator_recursion_genesis.RecursiveOperator；本守門不
    import operator_recursion_genesis，避免循環依賴）。
    """
    step_max = dim_op_step_max()
    try:
        rep = rec_op.closure_report()
        total = bool(rep.total)
        terminating = bool(rep.terminating)
        fuel = int(rep.fuel)
        max_cost = int(rep.max_cost)
        n_ops = int(getattr(rep, "n_operators", 0))
    except Exception as exc:  # noqa: BLE001
        raise RecursionClosureViolation(
            f"互遞迴良基停機證書不可求值（{exc}）：被自我擴充的互遞迴圖結構不可證良基終止，禁止採納（Rule 9.35.3）")
    if not terminating:
        raise RecursionClosureViolation(
            f"互遞迴算子呼叫圖含無證書環（環中無回邊嚴格遞減下有界 rank → 可能不停機）：判定任意含環圖停機 = "
            f"停機問題（不可判定），「有界步數」device 失效；無良基測度證書，禁止採納，導 MFSM_ESCALATION"
            f"（Rule 9.35.3 互遞迴良基停機證書——用全新 device「良基測度終止」取代失效的「有界步數」）。"
        )
    if fuel > step_max or max_cost > step_max:
        raise RecursionClosureViolation(
            f"互遞迴算子 fuel={fuel} / max_cost={max_cost} > SDD_DIM_OP_STEP_MAX={step_max}："
            f"良基停機證書的硬燃料上界被突破，禁止採納，導 MFSM_ESCALATION（Rule 9.35.3）。"
        )
    if not total:
        raise RecursionClosureViolation(
            f"互遞迴算子整代數出現非全函式算子（某輸入無定義/拋例外/NaN/inf）：被自我擴充的互遞迴算子破壞良基停機"
            f"閉包全函式，禁止採納，導 MFSM_ESCALATION（Rule 9.35.3 閉包全函式保證）。"
        )
    return RecursionClosureGuardResult(
        allowed=True, total=total, terminating=terminating, fuel=fuel, max_cost=max_cost,
        step_max=step_max, n_operators=n_ops,
        reason="互遞迴良基停機證書四證通過（呼叫圖可證良基終止 + fuel<=step_max + 整代數全函式 + 求值器零真遞迴零 while）")


@dataclass
class EmbodiedGroundingGuardResult:
    allowed: bool          # grounded_pass → True（允許 MFSM_GROW）；否則 False（REJECT 不 churn）
    verdict: str           # grounded_pass / grounded_fail / spec_defect
    oqs: float
    grounded: bool         # 是否基於客觀 ExecutionObservation（True：已通過 fail-closed）
    reason: str = ""


def guard_embodied_grounding(grounding) -> EmbodiedGroundingGuardResult:
    """Rule 9.36 EmbodiedGroundingBounded：自我發明能力被 META_FSM 納入（MFSM_GROW）前的**具身接地閘守門**（Phase X）.

    與 TLA+ `EmbodiedGroundingBounded` **100% 同構**的 fail-closed 三段（守 Phase X PX-1）：
      (i) **grounded verdict 必基於 ExecutionObservation 客觀資料**——`grounding.observation` 為 None，或 OQS 客觀
          計分判定為 `inconclusive`（沙箱從未真正跑過/壞過，無客觀證據）→ raise `EmbodiedGroundingViolation`
          （呼叫端轉 MFSM_ESCALATION）。**本守門獨立用 output_quality_scorer 重新計分驗證，不盲信 oracle 的
          verdict 標籤**（對抗分離：guard 自證接地性）。
      (ii) **沙箱硬 timeout → grounded_fail**：`grounding.sandbox_timed_out` 為真 → allowed=False（FSM 不 wall-
          clock wait，收 verdict 而非等沙箱）——把「真實沙箱可能 hang」這個具身接地引入的新不停機源封死。
      (iii) **grounded_pass 才允許 GROW**：OQS verdict==pass（且非 timeout）→ allowed=True；其餘（runtime_fail /
          spec_defect）→ allowed=False（REJECT，回 OBSERVE 不增 churn）。

    duck-typed：`grounding` 需 `.observation`(ExecutionObservation | None) + 可選 `.spec_defect`(bool) +
    `.sandbox_timed_out`(bool)（e.g. embodied_grounding_oracle.GroundedVerdict）。本守門**惰性** import
    output_quality_scorer（避免循環依賴），且**不** import 任何 generator / embodied_grounding_oracle（對抗分離）。
    """
    from tools.fsm_runtime import output_quality_scorer as _oqs  # 惰性，避免循環依賴

    obs = getattr(grounding, "observation", None)
    spec_defect = bool(getattr(grounding, "spec_defect", False))
    sandbox_timed_out = bool(getattr(grounding, "sandbox_timed_out", False))

    # (i) fail-closed：grounded verdict 必基於客觀 ExecutionObservation。
    if obs is None:
        raise EmbodiedGroundingViolation(
            "具身接地閘 fail-closed：grounded verdict 缺 ExecutionObservation 客觀資料，禁止納入，"
            "導 MFSM_ESCALATION（Rule 9.36 EmbodiedGroundingBounded）。")
    try:
        res = _oqs.score(obs, spec_defect=spec_defect)
    except Exception as exc:  # noqa: BLE001
        raise EmbodiedGroundingViolation(
            f"具身觀測不可客觀計分（{exc}）：fail-closed，禁止納入，導 MFSM_ESCALATION（Rule 9.36）。")
    if res.verdict == "inconclusive":
        raise EmbodiedGroundingViolation(
            "具身接地閘 fail-closed：OQS 判定無客觀觀測（沙箱從未真正跑過/壞過 → inconclusive），"
            "禁止以零觀測 false-green 納入，導 MFSM_ESCALATION（Rule 9.36 EmbodiedGroundingBounded）。")

    # (ii) 沙箱硬 timeout → grounded_fail（FSM 不 wall-clock wait）。
    if sandbox_timed_out:
        return EmbodiedGroundingGuardResult(
            allowed=False, verdict="grounded_fail", oqs=res.score, grounded=True,
            reason="沙箱硬 timeout → grounded_fail，REJECT 不 churn（FSM 不 wall-clock wait，收 verdict 而非等沙箱）。")

    # (iii) grounded_pass 才允許 MFSM_GROW；其餘 REJECT 不 churn。
    if res.verdict == "pass":
        return EmbodiedGroundingGuardResult(
            allowed=True, verdict="grounded_pass", oqs=res.score, grounded=True,
            reason=f"具身接地通過（OQS={res.score:.4f}>=門檻、基於客觀觀測），允許 MFSM_GROW。")
    return EmbodiedGroundingGuardResult(
        allowed=False, verdict=("spec_defect" if res.verdict == "spec_defect" else "grounded_fail"),
        oqs=res.score, grounded=True,
        reason=f"具身接地未通過（OQS verdict={res.verdict}），REJECT 不 churn。")


# ===== Phase Y / ACT-160 — guard_visualization_bounded（Rule 9.37 VisualizationBounded）=====

class VisualizationViolation(RuntimeError):
    """Rule 9.37 VisualizationBounded fail-closed（→ MFSM_ESCALATION）：meta⁸ 互遞迴呼叫圖人類視覺化
    儀表板呈現給舵手前的有界 + 防偽守門違反。

    與 TLA+ `VisualizationBounded` 100% 同構：可審批性的停機反諷在於——為讓人類看懂而引入「渲染無界大圖
    可能 token 爆炸 / OOM」這個新不停機源（同 Phase X「真實沙箱可能 hang」結構）。本 fail-closed 杜絕：
    (i) render budget 逃逸（token 爆炸）；(ii) 拓樸視覺欺騙（畫的圖比跑的簡單/偽 rank/刪邊）；(iii) 接地視圖
    零觀測 false-green（複用 Phase X 接地紀律）。儀表板是 read-only 純觀察者，渲染不漂移 meta-loop 狀態。"""


@dataclass
class VisualizationGuardResult:
    allowed: bool          # 全部通過 → True（可呈現舵手 K=1 signoff）
    truncated: bool
    n_rendered_nodes: int
    rendered_chars: int
    audit_ok: bool         # 拓樸同構稽核（PY-2 防偽）是否通過
    reason: str = ""


def guard_visualization_bounded(view, op_dict) -> VisualizationGuardResult:
    """Rule 9.37 VisualizationBounded：meta⁸ 互遞迴呼叫圖人類視覺化儀表板呈現給舵手前的**有界 + 防偽守門**（Phase Y）.

    與 TLA+ `VisualizationBounded` **100% 同構**的 fail-closed 三段：
      (i) **render budget 不可逃逸**：render_json 顯示節點 > node_budget 而 view 未標 truncated（宣稱未截斷卻超界），
          或 dashboard markdown 字元數 > char_budget（token 爆炸風險）→ raise `VisualizationViolation`。
      (ii) **拓樸同構（PY-2 防偽）**：**獨立**呼叫 `verify_topology_consistency(render_json(view), op_dict)`——
          guard 不盲信 renderer，自 op_dict 重算窗格子圖比對；不同構（視覺欺騙：畫的圖比跑的簡單/偽 rank/刪邊）
          → raise。
      (iii) **接地不 false-green**：grounding.grounded_verdict==grounded_pass 但 has_observation 為 False（零觀測卻綠）
          → raise（複用 Phase X 接地 fail-closed）。

    全通過 → allowed=True。本守門**惰性** import recursion_topology_view（純渲染器，**非** generator/oracle，
    對抗分離不破），且**不** import 任何 generator / embodied_grounding_oracle / dimension_necessity_oracle。
    求值路徑零 while、零自呼叫（有界停機）。
    """
    from tools.fsm_runtime import recursion_topology_view as _v  # 惰性，純渲染器（非 generator/oracle）

    rj = _v.render_json(view)
    md = _v.render_dashboard_markdown(view)
    budget = getattr(view, "budget", None)
    node_budget = int(getattr(budget, "node_budget", 24))
    char_budget = int(getattr(budget, "char_budget", 8000))
    n_nodes = len(rj.get("nodes") or [])
    rendered_chars = len(md)

    # (0) **防禦縱深（真實大小誠實）**：view 自報的 n_total_nodes 必須 == op_dict 真實節點數——杜絕「繞過
    #     extract_topology 直接手構縮小 budget 的惡意 TopologyView 隱藏節點 / 謊稱算子更小」（攻擊者即使壓
    #     budget，也不得謊報總節點數；真實大小誠實揭露 ⇒ 即使截斷也不致視覺欺騙）。
    real_n = len((op_dict or {}).get("ranks") or [])
    try:
        if int(getattr(view, "n_total_nodes", real_n)) != real_n:
            raise VisualizationViolation(
                f"view 自報 n_total_nodes={getattr(view, 'n_total_nodes', None)} != op_dict 真實 {real_n}"
                f"（隱藏節點 / 謊稱算子更小，畫的圖比跑的簡單）→ fail-closed，導 MFSM_ESCALATION（Rule 9.37）。")
    except (TypeError, ValueError):
        raise VisualizationViolation(
            "view 自報 n_total_nodes 非法 → fail-closed，導 MFSM_ESCALATION（Rule 9.37）。")

    # (i) render budget fail-closed（不可逃逸 → 杜絕 token 爆炸 / OOM）。
    if n_nodes > node_budget and not getattr(view, "truncated", False):
        raise VisualizationViolation(
            f"渲染逃逸 node_budget（顯示 {n_nodes} > {node_budget} 卻未標 truncated）→ fail-closed，"
            f"禁止呈現，導 MFSM_ESCALATION（Rule 9.37 VisualizationBounded）。")
    if rendered_chars > char_budget:
        raise VisualizationViolation(
            f"渲染逃逸 char_budget（{rendered_chars} > {char_budget}，token 爆炸風險）→ fail-closed，"
            f"禁止呈現，導 MFSM_ESCALATION（Rule 9.37 VisualizationBounded）。")

    # (ii) 拓樸同構（PY-2 防偽，獨立重算不盲信 renderer 標籤；窗格錨定用**服務端權威 node_budget**，
    #      絕不採信 render_json 自報之 budget/cursor/n_total）。
    try:
        audit_ok = bool(_v.verify_topology_consistency(rj, op_dict, node_budget=node_budget))
    except _v.TopologyConsistencyError as exc:
        raise VisualizationViolation(
            f"拓樸防偽 fail-closed（{exc}）→ 禁止呈現視覺欺騙圖，導 MFSM_ESCALATION（Rule 9.37）。")

    # (iii) 接地 false-green fail-closed（零觀測不綠勾，複用 Phase X 接地紀律）。
    g = getattr(view, "grounding", None)
    if (g is not None and getattr(g, "grounded_verdict", "") == "grounded_pass"
            and not getattr(g, "has_observation", False)):
        raise VisualizationViolation(
            "接地視圖零觀測 false-green（grounded_pass 卻無客觀 ExecutionObservation）→ fail-closed，"
            "導 MFSM_ESCALATION（Rule 9.37 VisualizationBounded）。")

    return VisualizationGuardResult(
        allowed=True, truncated=bool(getattr(view, "truncated", False)),
        n_rendered_nodes=n_nodes, rendered_chars=rendered_chars, audit_ok=audit_ok,
        reason=(f"視覺化有界+防偽通過（顯示 {n_nodes}<=node_budget、{rendered_chars}<=char_budget、"
                f"拓樸同構、接地不 false-green），可呈現舵手 K=1 signoff。"))


def record_rule_add(
    rule_id: str,
    fingerprint: str,
    capability_level: int,
    *,
    source: str = "learning_layer",
    note: str = "",
    ledger_path: Optional[Path] = None,
    ts: Optional[str] = None,
) -> _ledger.MetaEvent:
    """學習層採納 verified 規則的**唯一合法入口**：先過 guard_readopt，再落盤。

    guard 拋出（ChurnBoundExceeded / GraduationRatchetViolation）時不寫入 ledger，
    由呼叫端轉 MFSM_ESCALATION（守 Rule 9.24.1 不可繞過守門）。
    """
    guard_readopt(fingerprint, capability_level, ledger_path=ledger_path)  # 可能 raise
    return _ledger.record_event(
        _ledger.EVENT_ADD, rule_id, fingerprint=fingerprint,
        capability_level=capability_level, source=source, note=note,
        ledger_path=ledger_path, ts=ts,
    )


def record_rule_retire(
    rule_id: str,
    fingerprint: str,
    capability_level: int = 0,
    *,
    source: str = "scaffold_gc",
    note: str = "",
    ledger_path: Optional[Path] = None,
    ts: Optional[str] = None,
) -> _ledger.MetaEvent:
    """GC 退役規則的記帳入口。退役本身永遠安全（縮小規則集），不被守門阻擋。"""
    return _ledger.record_event(
        _ledger.EVENT_RETIRE, rule_id, fingerprint=fingerprint,
        capability_level=capability_level, source=source, note=note,
        ledger_path=ledger_path, ts=ts,
    )


def classify_transition(event_type: str) -> str:
    """把一次 ledger 事件映射為 META_FSM 的瞬態（GROW / SHRINK）。"""
    if event_type in (_ledger.EVENT_ADD, _ledger.EVENT_FITNESS_ADD):
        return "MFSM_GROW"
    if event_type == _ledger.EVENT_RETIRE:
        return "MFSM_SHRINK"
    return "MFSM_OBSERVE"


def meta_state(*, ledger_path: Optional[Path] = None) -> str:
    """回傳元迴圈當前的持久態（observability）。

    - 任一指紋 churn ≥ churn_max → MFSM_ESCALATION（已觸頂，待人工）
    - 帳本為空 → MFSM_OBSERVE
    - 否則 → MFSM_STABLE（穩態不動點；GROW/SHRINK 為瞬態不持久）
    """
    led = _ledger.load_ledger(ledger_path)
    cmax = churn_max()
    for fp in _ledger.all_fingerprints(ledger=led):
        if _ledger.compute_churn(fp, ledger=led) >= cmax:
            return "MFSM_ESCALATION"
    # Phase P / ACT-119：跨評分器聚合採納速率觸頂亦升 ESCALATION（Rule 9.28.3）。
    if _ledger.calibration_adds_in_window(calib_adopt_window(), ledger=led) >= calib_adopt_rate_max():
        return "MFSM_ESCALATION"
    # Phase Q / ACT-125：價值維度基數觸頂 stock 天花板亦升 ESCALATION（Rule 9.29.3）。
    # 達天花板 = 本體論已不該再無界擴張，需人工裁決是否擴頂或退役舊維度。
    if len(_ledger.active_value_dimensions(ledger=led)) >= dimension_cardinality_max():
        return "MFSM_ESCALATION"
    # Phase R / ACT-131：退役聯動 swap 聚合速率觸頂亦升 ESCALATION（Rule 9.30.3）。
    # 定基數旋轉（net 基數=0、stock 永不觸頂、每指紋 churn<=1）由 swap 速率窗封死。
    if _ledger.swap_adds_in_window(dim_swap_window(), ledger=led) >= dim_swap_rate_max():
        return "MFSM_ESCALATION"
    # Phase S / ACT-137：詞彙基數觸頂 vocab stock 天花板亦升 ESCALATION（Rule 9.31.3，meta⁴）。
    # 達天花板 = 詞彙本體論已不該再無界擴充，需人工裁決是否擴頂或退役舊詞彙字。
    if len(_ledger.active_vocab_genesis_features(ledger=led)) >= dim_vocab_max():
        return "MFSM_ESCALATION"
    # Phase S / ACT-137：批次退役聯動操作聚合速率觸頂亦升 ESCALATION（Rule 9.31.3）。
    # 批次旋轉（一個原子批次≠n 次 swap，per-swap 速率窗計數失真）由 distinct 批次操作速率窗封死。
    if _ledger.batch_swap_ops_in_window(dim_batch_window(), ledger=led) >= dim_batch_rate_max():
        return "MFSM_ESCALATION"
    # Phase T / ACT-143：算子基數觸頂 operator stock 天花板亦升 ESCALATION（Rule 9.32.4，meta⁵）。
    # 達天花板 = 算子計算本體論已不該再無界擴充，需人工裁決是否擴頂或退役舊算子。
    if len(_ledger.active_operator_genesis_features(ledger=led)) >= dim_op_max():
        return "MFSM_ESCALATION"
    # Phase U / ACT-148：字母基數觸頂 alphabet stock 天花板亦升 ESCALATION（Rule 9.33.4，meta⁶）。
    # 達天花板 = 字母計算生成本體論已不該再無界擴充，需人工裁決是否擴頂或退役舊字母。
    if len(_ledger.active_alphabet_genesis_features(ledger=led)) >= dim_alphabet_max():
        return "MFSM_ESCALATION"
    # Phase V / ACT-151：深度算子基數觸頂 depth stock 天花板亦升 ESCALATION（Rule 9.34.4，meta⁷）。
    # 達天花板 = 深度計算生成本體論已不該再無界擴充，需人工裁決是否擴頂或退役舊深度算子。
    if len(_ledger.active_depth_genesis_features(ledger=led)) >= dim_depth_max():
        return "MFSM_ESCALATION"
    # Phase W / ACT-154：互遞迴算子基數觸頂 recursion stock 天花板亦升 ESCALATION（Rule 9.35.4，meta⁸）。
    # 達天花板 = 互遞迴計算生成本體論已不該再無界擴充，需人工裁決是否擴頂或退役舊互遞迴算子。
    if len(_ledger.active_recursion_genesis_features(ledger=led)) >= dim_recur_max():
        return "MFSM_ESCALATION"
    if not led.get("events"):
        return "MFSM_OBSERVE"
    return "MFSM_STABLE"
