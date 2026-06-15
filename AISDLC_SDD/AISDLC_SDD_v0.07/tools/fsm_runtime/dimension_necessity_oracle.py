"""Phase Q / ACT-124 — Dimension Necessity Oracle（維度必要性反 Goodhart 評估器）.

對應藍圖：SDD_improving_Automation_17.md §1.1 / §3.1 ACT-124 / Rule 9.29.2 / 9.29.5。

這是 Phase Q 的**靈魂與安全紅線**。Phase P 的 `joint_calibration_oracle` 只評**固定維度**上的
權重向量——它在「固定 8 軸」的座標系裡驗證向量真實品質。但增維後，系統能發明**一條新軸**，
而 Phase P 的聯合 oracle **對「這條新軸到底必不必要、是不是冗餘、是不是只是換個方式給自己
打高分」完全盲目**。N 維固定的 oracle，攔不住「自利噪音軸 / 既有軸再投影的冗餘軸」。

本模組是 **meta-meta** 評估器：把一條**候選新維度**套進凍結的現實情節，量**兩個正交判據**：
  1. **增量覆蓋（incremental coverage）**：augmented 向量（既有維度 + 新維度，以 argmin 選候選）
     vs baseline 向量（僅既有維度）在凍結情節上選出候選的**真實品質增益**。增益 ≥ margin →
     新軸抓到既有維度集體漏判的真實失敗（**必要**）；≈ 0 → 自利噪音軸（自評高、真實零增量）。
  2. **非冗餘度（non-redundancy）**：新維度對候選的排序與既有維度排序的**最大一致率
     （pairwise concordance）**。一致率 ≥ 門檻 → 新軸只是既有某軸的再投影（**冗餘**，過擬合/
     自我背書）→ 即使增量覆蓋 > 0 也拒絕。

反 Goodhart 結構保證（承 Phase O/P 三保證，推到 meta-meta 層級）：
  1. **唯一持有必要性現實**：只有本模組讀 `knowledge/held-out-corpus/DIM-*.yaml`；
     `value_dimension_registry`（proposer）結構性看不到語料（它只收注入的 evaluate）。
  2. **必要性真實品質才算數（Rule 9.29.2/9.29.5）**：necessity tier = 候選維度在 held-out 上的
     （增量覆蓋 ∧ 非冗餘）勝率；任何 proposer 自評/自算覆蓋率**不得**充當必要性 capability-delta。
     **proposer 自評必要、但 oracle 判不必要/冗餘 → 一律以 oracle 為準**。
  3. **凍結 + 防竄改 + 有界**：語料 content-hashed，重放筆數 ≤ `SDD_REPLAY_MAX_CASES`
     （重用 counterfactual_replay 既有上限）。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .counterfactual_replay import replay_max   # 重用既有重放筆數上限（Rule 9.29.2）
from .state_loader import REPO_ROOT
from .value_dimension_registry import ValueDimension  # 僅型別；oracle 可知 proposer 型別（反向不可）

HELD_OUT_CORPUS_DIR = REPO_ROOT / "knowledge" / "held-out-corpus"

# === 非冗餘門檻（Rule 9.29.2：與既有維度排序一致率 ≥ 此門檻 → 冗餘軸，拒絕）===
_DEFAULT_REDUNDANCY_MAX = 0.95
_REDUNDANCY_MAX_CLAMP = (0.0, 1.0)

# === augmented 選擇的新維度權重（deterministic）===
_DEFAULT_AUG_WEIGHT = 1.0

# === 必要性增量覆蓋門檻（與 registry 共用同一 env SDD_DIM_COVERAGE_MARGIN）===
_DEFAULT_COVERAGE_MARGIN = 0.10


def dim_redundancy_max() -> float:
    """讀 SDD_DIM_REDUNDANCY_MAX（env 可調），clamp[0,1]，預設 0.95。"""
    raw = os.environ.get("SDD_DIM_REDUNDANCY_MAX")
    if not raw:
        return _DEFAULT_REDUNDANCY_MAX
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_REDUNDANCY_MAX
    lo, hi = _REDUNDANCY_MAX_CLAMP
    return max(lo, min(hi, val))


def dim_aug_weight() -> float:
    """讀 SDD_DIM_AUG_WEIGHT（env 可調），預設 1.0（augmented 選擇的新維度權重）。"""
    raw = os.environ.get("SDD_DIM_AUG_WEIGHT")
    if not raw:
        return _DEFAULT_AUG_WEIGHT
    try:
        return float(raw)
    except ValueError:
        return _DEFAULT_AUG_WEIGHT


def dim_coverage_margin() -> float:
    """讀 SDD_DIM_COVERAGE_MARGIN（與 registry 共用），預設 0.10。"""
    raw = os.environ.get("SDD_DIM_COVERAGE_MARGIN")
    if not raw:
        return _DEFAULT_COVERAGE_MARGIN
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_COVERAGE_MARGIN
    return max(0.0, min(1.0, val))


@dataclass
class DimCandidate:
    """一個 pipeline 候選結果，及既有維度/候選新維度對它的測量 + 整體**已知真實品質**.

    existing_cost = 既有固定維度集合對此候選的聚合成本（lower = 既有維度偏好它；baseline 選擇用）。
    dim_value = 候選**新維度**對此候選的測量（lower = 新維度偏好它；augmented 選擇加權用）。
    real_quality = 若此候選被選中的**整體真實結果**（OQS／低 escalation／低返工），proposer 看不到。
    """
    real_quality: float
    existing_cost: float
    dim_value: float


@dataclass
class DimHeldOutCase:
    """一筆維度必要性現實代理：一個 pipeline 問題 + 多個候選結果及其已知真實品質。"""
    case_id: str
    dimension_name: str
    candidates: List[DimCandidate]

    def _select(self, augmented: bool, aug_weight: float) -> DimCandidate:
        """argmin 選候選：baseline 僅 existing_cost；augmented 加 aug_weight×dim_value。"""
        best_idx = 0
        best_cost = None
        for idx, c in enumerate(self.candidates):
            cost = c.existing_cost + (aug_weight * c.dim_value if augmented else 0.0)
            if best_cost is None or cost < best_cost:   # 嚴格更低才取代（穩定 tie-break）
                best_cost = cost
                best_idx = idx
        return self.candidates[best_idx]

    def baseline_quality(self) -> float:
        return float(self._select(False, 0.0).real_quality)

    def augmented_quality(self, aug_weight: float) -> float:
        return float(self._select(True, aug_weight).real_quality)

    def concordance(self) -> float:
        """新維度 dim_value 排序與既有 existing_cost 排序的 pairwise 一致率（Kendall-τ 風格）.

        對每一對候選 (i,j)，比較 sign(dim_value_i − dim_value_j) 與 sign(existing_cost_i −
        existing_cost_j) 是否同號。一致率 = 同號對數 / 總對數。一致率高 → 新維度只是既有維度的
        再投影（冗餘）。tie（任一邊差為 0）的對不計入分母（無排序資訊）。
        """
        cs = self.candidates
        agree = 0
        total = 0
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                de = cs[i].existing_cost - cs[j].existing_cost
                dd = cs[i].dim_value - cs[j].dim_value
                if de == 0 or dd == 0:
                    continue
                total += 1
                if (de > 0) == (dd > 0):
                    agree += 1
        if total == 0:
            return 0.0           # 無可比對 → 視為非冗餘（無排序資訊）
        return agree / total


@dataclass
class DimensionVerdict:
    """維度必要性評估結論（necessity capability tier 唯一合法來源，Rule 9.29.5）。"""
    dimension_name: str
    baseline_quality: float
    augmented_quality: float
    incremental_coverage: float
    coverage_margin: float
    redundancy: float
    redundancy_max: float
    tier: int                    # = round(incremental_coverage*100) when necessary else 0
    necessary: bool              # coverage ≥ margin ∧ redundancy < redundancy_max
    examined: int
    corpus_fingerprint: str = ""

    def evidence_line(self) -> str:
        return (f"維度必要性評估『{self.dimension_name}』：增量覆蓋 {self.incremental_coverage:+.2f}"
                f"（augmented {self.augmented_quality:.2f} vs baseline {self.baseline_quality:.2f}，"
                f"margin {self.coverage_margin:.2f}）｜非冗餘度（一致率 {self.redundancy:.2f} < "
                f"門檻 {self.redundancy_max:.2f}）｜檢視 {self.examined} 筆現實代理"
                f"{'｜必要' if self.necessary else '｜不必要（維度 Goodhart：噪音軸或冗餘軸必落此）'}")


def corpus_fingerprint(corpus: List[DimHeldOutCase]) -> str:
    """語料 content hash（凍結 + 防竄改證據；Rule 9.29.2）。"""
    payload = [
        {"case_id": c.case_id, "dimension_name": c.dimension_name,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "dim_value": jc.dim_value} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_dimension(dimension: ValueDimension, corpus: List[DimHeldOutCase], *,
                       coverage_margin: Optional[float] = None,
                       redundancy_max: Optional[float] = None,
                       aug_weight: Optional[float] = None,
                       max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一條候選新維度在凍結現實情節上是否**必要且非冗餘**（Rule 9.29.2/9.29.5 誠實）。

    這是「proposer 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」的釘死處：候選維度即使
    proposer 在自己尺規上認為必要，只要 held-out 增量覆蓋未達 margin（噪音軸）或非冗餘度
    一致率達門檻（冗餘軸），就 `necessary=False`，拿不到必要性 tier（呼叫端據此拒絕採納）。

    僅取 corpus 中 dimension_name 與 dimension.name 相符的 case；重放筆數 clamp
    `SDD_REPLAY_MAX_CASES`（Rule 9.29.2，有界）。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()

    relevant = [c for c in corpus if c.dimension_name == dimension.name]
    examined_cases = relevant[:cap]
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=dimension.name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=corpus_fingerprint(corpus))

    base = round(sum(c.baseline_quality() for c in examined_cases) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in examined_cases) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in examined_cases), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=dimension.name,
        baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=corpus_fingerprint(corpus),
    )


def necessity_score(dimension: ValueDimension, corpus: List[DimHeldOutCase], *,
                    coverage_margin: Optional[float] = None,
                    redundancy_max: Optional[float] = None,
                    aug_weight: Optional[float] = None,
                    max_cases: Optional[int] = None) -> float:
    """供 registry.propose 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「proposer 結構性無自評」的接縫：proposer 只拿到這個由 oracle 算出的純量，自己沒有
    必要性語料、無法給自己打分（Rule 9.29.2 對抗分離）。
    """
    v = evaluate_dimension(dimension, corpus, coverage_margin=coverage_margin,
                           redundancy_max=redundancy_max, aug_weight=aug_weight,
                           max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


# ---------------------------------------------------------------------------
# 維度必要性凍結語料載入（只有本模組讀，proposer 結構性無此路徑）
# ---------------------------------------------------------------------------

def load_necessity_corpus(corpus_dir: Optional[Path] = None) -> List[DimHeldOutCase]:
    """載入 knowledge/held-out-corpus/DIM-*.yaml 凍結語料（deterministic 檔名序）。"""
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[DimHeldOutCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("DIM-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            DimCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                dim_value=float(c["dim_value"]),
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(DimHeldOutCase(
            case_id=str(doc.get("case_id", p.stem)),
            dimension_name=str(doc.get("dimension_name", "")),
            candidates=cands))
    return cases


# ===========================================================================
# Phase R / ACT-130 — feature-keyed 必要性評估（候選池外自我發明維度反 Goodhart）
# ===========================================================================
#
# Phase Q 的 evaluate_dimension **靠 dimension_name 匹配**凍結語料——它只能評「語料事先知道
# 名字」的固定候選池維度。但 Phase R 讓系統**現場發明一條候選池外的新軸**（名字事先不在語料
# 裡），by-name oracle 對它 examined=0 → 永遠判不必要 → 自我發明根本無法被合法驗證。
#
# 本節升級為 **feature-keyed**：對一條現場發明、語料事先不知名字的軸，把它的 `apply(features)`
# probe 套到凍結語料候選的**特徵向量**上**現算** dim_value，再量同樣的 (增量覆蓋 ∧ 非冗餘)。
# 語料因此 name-agnostic（所有 case 皆相關）——synthesizer 仍結構性看不到語料（它只收注入的
# evaluate），對抗分離不變（Rule 9.30.2）。oracle 可知 synthesizer 的 InventedDimension 介面
# （只用 duck-typed `.apply()` / `.name`，反向不可——synthesizer 不 import oracle）。


@dataclass
class FeatureCandidate:
    """一個 pipeline 候選，及其**完整原始特徵向量** + 既有維度聚合成本 + 已知真實品質.

    features = 候選池外原始特徵（rollback_steps / blast_radius / …），供現場發明的軸以 apply()
    現算 dim_value。existing_cost = 既有固定維度集合對此候選的聚合成本（baseline 選擇用）。
    real_quality = 若此候選被選中的整體真實結果，synthesizer 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class FeatureCase:
    """一筆 feature-keyed 必要性現實代理（name-agnostic，供現場發明維度評估）。"""
    case_id: str
    candidates: List[FeatureCandidate]


def feature_corpus_fingerprint(corpus: List[FeatureCase]) -> str:
    """feature 語料 content hash（凍結 + 防竄改證據；Rule 9.30.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_invented_dimension(dim, corpus: List[FeatureCase], *,
                                coverage_margin: Optional[float] = None,
                                redundancy_max: Optional[float] = None,
                                aug_weight: Optional[float] = None,
                                max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一條**候選池外現場發明**的維度在凍結 feature 現實情節上是否**必要且非冗餘**.

    `dim` 是 duck-typed 發明維度（需 `.apply(features)->float` 與 `.name`，e.g.
    dimension_semantics_synthesizer.InventedDimension）。本函式把 dim 的 probe 套到每筆 case
    候選的特徵向量現算 dim_value（**不靠 dimension_name**），再量 (a) 增量覆蓋（augmented vs
    baseline 真實品質增益）+ (b) 非冗餘度（與既有 existing_cost 排序的最大一致率），回
    `DimensionVerdict`。「synthesizer 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」
    （Rule 9.30.2/9.30.5）。重放筆數 clamp `SDD_REPLAY_MAX_CASES`（有界）。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(dim, "name", "(invented)")

    examined_cases = list(corpus)[:cap]    # name-agnostic：所有 case 皆相關
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=feature_corpus_fingerprint(corpus))

    # 現場把發明維度的 probe 套到候選特徵向量，建立等價 DimHeldOutCase（重用既有增量覆蓋/非冗餘）。
    built: List[DimHeldOutCase] = []
    for fc in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(dim.apply(c.features))) for c in fc.candidates]
        built.append(DimHeldOutCase(case_id=fc.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=feature_corpus_fingerprint(corpus),
    )


def necessity_score_invented(dim, corpus: List[FeatureCase], *,
                             coverage_margin: Optional[float] = None,
                             redundancy_max: Optional[float] = None,
                             aug_weight: Optional[float] = None,
                             max_cases: Optional[int] = None) -> float:
    """供 synthesizer.invent 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「synthesizer 結構性無自評」的接縫：synthesizer 只拿到這個由 oracle 算出的純量，自己
    沒有 feature 必要性語料、無法給自己打分（Rule 9.30.2 對抗分離）。
    """
    v = evaluate_invented_dimension(dim, corpus, coverage_margin=coverage_margin,
                                    redundancy_max=redundancy_max, aug_weight=aug_weight,
                                    max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_feature_corpus(corpus_dir: Optional[Path] = None) -> List[FeatureCase]:
    """載入 knowledge/held-out-corpus/INV-*.yaml 凍結 feature 語料（deterministic 檔名序）.

    只有本模組讀；synthesizer 結構性無此路徑（Rule 9.30.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[FeatureCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("INV-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            FeatureCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(FeatureCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases


# ===========================================================================
# Phase S / ACT-136 — feature-grounded 詞彙必要性評估（VOCAB 外詞彙自我發明反 Goodhart，meta⁴）
# ===========================================================================
#
# Phase R 的 evaluate_invented_dimension 評的是「現場發明維度在 VOCAB **已知特徵向量**上的增量
# 覆蓋」——它預設語料的特徵向量**已含 VOCAB 全部 8 條**。但 Phase S 讓系統**自我發明一個 VOCAB
# 外的新原始特徵字**（meta⁴），這個字**語料事先沒有這個欄位名字**。
#
# 本節升級為 **feature-grounded（不靠特徵欄名、靠原始信號源的真實情節）**：對一個現場發明、語料
# 事先沒有此欄名字的原始特徵字，在**含該原始信號源欄位**的凍結 feature-genesis 語料上，以發明字
# 建一條探針維度量同樣的 (增量覆蓋 ∧ 非冗餘)。語料因此以原始信號源為錨（所有 case 皆相關）——
# vocabulary_genesis 仍結構性看不到語料（它只收注入的 evaluate），對抗分離不變（Rule 9.31.2）。
# oracle 可知 vocabulary_genesis 的 GenesisFeature 介面（只用 duck-typed `.apply()` / `.name`，
# 反向不可——vocabulary_genesis 不 import oracle）。


@dataclass
class GenesisCandidate:
    """一個 pipeline 候選，及其**含原始信號源欄位的特徵向量** + 既有 VOCAB 聚合成本 + 已知真實品質.

    features = 含 VOCAB 外原始信號源欄位（secret.window / identity.rate / …），供現場發明的詞彙字
    以 apply() 現算 dim_value。existing_cost = 既有 VOCAB 全維度對此候選的聚合成本（baseline 選擇用）。
    real_quality = 若此候選被選中的整體真實結果，vocabulary_genesis 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class GenesisCase:
    """一筆 feature-grounded 詞彙必要性現實代理（以原始信號源為錨，供現場發明詞彙字評估）。"""
    case_id: str
    candidates: List[GenesisCandidate]


def genesis_corpus_fingerprint(corpus: List[GenesisCase]) -> str:
    """feature-genesis 語料 content hash（凍結 + 防竄改證據；Rule 9.31.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_genesis_feature(gf, corpus: List[GenesisCase], *,
                             coverage_margin: Optional[float] = None,
                             redundancy_max: Optional[float] = None,
                             aug_weight: Optional[float] = None,
                             max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一個**VOCAB 外現場發明**的原始特徵字在凍結 feature-genesis 現實情節上是否**必要且非冗餘**.

    `gf` 是 duck-typed 詞彙發明字（需 `.apply(features)->float` 與 `.name`，e.g.
    vocabulary_genesis.GenesisFeature）。本函式把 gf 當單一特徵探針套到每筆 case 候選的特徵向量
    現算 dim_value（**不靠特徵欄名匹配**），再量 (a) 增量覆蓋（augmented〔既有 VOCAB 全維度 +
    發明字〕vs baseline〔僅既有 VOCAB 全維度〕真實品質增益）+ (b) 非冗餘度（與既有 existing_cost
    排序的最大一致率），回 `DimensionVerdict`。「genesis 自評必要、但 oracle 判不必要/冗餘 → 以
    oracle 為準」（Rule 9.31.2/9.31.5）。重放筆數 clamp `SDD_REPLAY_MAX_CASES`（有界）。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(gf, "name", "(genesis)")

    examined_cases = list(corpus)[:cap]    # feature-grounded：所有 case 皆相關（以原始信號源為錨）
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=genesis_corpus_fingerprint(corpus))

    built: List[DimHeldOutCase] = []
    for gc in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(gf.apply(c.features))) for c in gc.candidates]
        built.append(DimHeldOutCase(case_id=gc.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=genesis_corpus_fingerprint(corpus),
    )


def necessity_score_genesis(gf, corpus: List[GenesisCase], *,
                            coverage_margin: Optional[float] = None,
                            redundancy_max: Optional[float] = None,
                            aug_weight: Optional[float] = None,
                            max_cases: Optional[int] = None) -> float:
    """供 vocabulary_genesis.genesis 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「genesis 結構性無自評」的接縫：genesis 只拿到這個由 oracle 算出的純量，自己沒有
    feature-genesis 必要性語料、無法給自己打分（Rule 9.31.2 對抗分離）。
    """
    v = evaluate_genesis_feature(gf, corpus, coverage_margin=coverage_margin,
                                 redundancy_max=redundancy_max, aug_weight=aug_weight,
                                 max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_genesis_corpus(corpus_dir: Optional[Path] = None) -> List[GenesisCase]:
    """載入 knowledge/held-out-corpus/VOC-*.yaml 凍結 feature-genesis 語料（deterministic 檔名序）.

    只有本模組讀；vocabulary_genesis 結構性無此路徑（Rule 9.31.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[GenesisCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("VOC-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            GenesisCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(GenesisCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases


# ===========================================================================
# Phase T / ACT-142 — feature-grounded 算子必要性評估（TRANSFORMS/OPS 外算子自我發明反 Goodhart，meta⁵）
# ===========================================================================
#
# Phase S 的 evaluate_genesis_feature 評的是「現場發明詞彙在既有 OPS/TRANSFORMS **算出的特徵向量**上
# 的增量覆蓋」——它預設『計算』永遠是那 6+4 條人類寫死的全函式算子。但 Phase T 讓系統**自我發明一個
# TRANSFORMS/OPS 外的新算子**（meta⁵），被發明物第一次是『可執行計算』而非『資料』。
#
# 本節升級為 **對算子的 feature-grounded 評估**：對一個現場發明、語料事先不知名字的新算子，把它（以
# 固定參照 probe 聚合）套到凍結語料候選的特徵向量上**現算** dim_value（= operator.apply(features)），
# 再量同樣的 (增量覆蓋 ∧ 非冗餘)——隔離「這個新算子相對既有 OPS 全算子有沒有帶來真實增量」。語料因此
# 以固定 probe 為錨（所有 case 皆相關）——operator_genesis 仍結構性看不到語料（它只收注入的 evaluate），
# 對抗分離不變（Rule 9.32.2）。oracle 可知 operator_genesis 的 GenesisOperator 介面（duck-typed
# `.apply()` / `.name`，反向不可——operator_genesis 不 import oracle）。


@dataclass
class OperatorCandidate:
    """一個 pipeline 候選，及其**含固定參照 probe 欄位的特徵向量** + 既有 OPS 聚合成本 + 已知真實品質.

    features = 含參照 probe 欄位（rollback_steps / blast_radius / canary_gap / …），供現場發明的算子
    以 apply() 在 probe 上現算 dim_value。existing_cost = 既有 OPS 全算子對此候選的最佳聚合成本
    （baseline 選擇用）。real_quality = 若此候選被選中的整體真實結果，operator_genesis 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class OperatorCase:
    """一筆 feature-grounded 算子必要性現實代理（以固定參照 probe 為錨，供現場發明算子評估）。"""
    case_id: str
    candidates: List[OperatorCandidate]


def operator_corpus_fingerprint(corpus: List[OperatorCase]) -> str:
    """feature-grounded 算子必要性語料 content hash（凍結 + 防竄改證據；Rule 9.32.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_genesis_operator(go, corpus: List[OperatorCase], *,
                              coverage_margin: Optional[float] = None,
                              redundancy_max: Optional[float] = None,
                              aug_weight: Optional[float] = None,
                              max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一個**TRANSFORMS/OPS 外現場發明**的算子在凍結算子必要性現實情節上是否**必要且非冗餘**.

    `go` 是 duck-typed 算子發明（需 `.apply(features)->float` 與 `.name`，e.g.
    operator_genesis.GenesisOperator）。本函式把 go 在固定參照 probe 上聚合套到每筆 case 候選的特徵
    向量現算 dim_value（**不靠算子名匹配**），再量 (a) 增量覆蓋（augmented〔既有 OPS 全算子最佳 +
    發明算子〕vs baseline〔僅既有 OPS 全算子最佳〕真實品質增益）+ (b) 非冗餘度（與既有 existing_cost
    排序的最大一致率），回 `DimensionVerdict`。「genesis 自評必要、但 oracle 判不必要/冗餘 → 以
    oracle 為準」（Rule 9.32.2/9.32.5）。重放筆數 clamp `SDD_REPLAY_MAX_CASES`（有界）。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(go, "name", "(operator)")

    examined_cases = list(corpus)[:cap]    # feature-grounded：所有 case 皆相關（以固定參照 probe 為錨）
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=operator_corpus_fingerprint(corpus))

    built: List[DimHeldOutCase] = []
    for oc in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(go.apply(c.features))) for c in oc.candidates]
        built.append(DimHeldOutCase(case_id=oc.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=operator_corpus_fingerprint(corpus),
    )


def necessity_score_operator(go, corpus: List[OperatorCase], *,
                             coverage_margin: Optional[float] = None,
                             redundancy_max: Optional[float] = None,
                             aug_weight: Optional[float] = None,
                             max_cases: Optional[int] = None) -> float:
    """供 operator_genesis.operator_genesis 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「operator_genesis 結構性無自評」的接縫：genesis 只拿到這個由 oracle 算出的純量，自己沒有
    算子必要性語料、無法給自己打分（Rule 9.32.2 對抗分離）。
    """
    v = evaluate_genesis_operator(go, corpus, coverage_margin=coverage_margin,
                                  redundancy_max=redundancy_max, aug_weight=aug_weight,
                                  max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_operator_corpus(corpus_dir: Optional[Path] = None) -> List[OperatorCase]:
    """載入 knowledge/held-out-corpus/OPR-*.yaml 凍結算子必要性語料（deterministic 檔名序）.

    只有本模組讀；operator_genesis 結構性無此路徑（Rule 9.32.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[OperatorCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("OPR-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            OperatorCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(OperatorCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases


# ===========================================================================
# Phase U / ACT-148 — feature-grounded 字母表必要性評估（PRIMITIVES/COMBINATORS 外字母自我發明反 Goodhart，meta⁶）
# ===========================================================================
#
# Phase T 的 evaluate_genesis_operator 評的是「現場發明算子在既有字母表 **算出的特徵向量**上的增量覆蓋」
# ——它預設『字母表』永遠是那 8+9 條人類寫死的全 total 原子。但 Phase U 讓系統**自我發明一個 PRIMITIVES/
# COMBINATORS 外的新運算字母**（meta⁶），被發明物是『會被文法用來生成每一個算子的生成規則零件』。
#
# 本節升級為 **對字母表元素的 feature-grounded 評估**：對一個現場發明、語料事先不知名字的新字母，用它（以
# 固定參照 probe）生成一個算子並套到凍結語料候選的特徵向量上**現算** dim_value（= element.apply(features)），
# 再量同樣的 (增量覆蓋 ∧ 非冗餘)——隔離「這個新字母相對既有字母表全算子有沒有帶來真實增量」。語料因此
# 以固定 probe 為錨（所有 case 皆相關）——operator_alphabet_genesis 仍結構性看不到語料（它只收注入的
# evaluate），對抗分離不變（Rule 9.33.2）。oracle 可知 operator_alphabet_genesis 的字母介面（duck-typed
# `.apply()` / `.name`，反向不可——operator_alphabet_genesis 不 import oracle）。


@dataclass
class AlphabetCandidate:
    """一個 pipeline 候選，及其**含固定參照 probe 欄位的特徵向量** + 既有字母表聚合成本 + 已知真實品質.

    features = 含參照 probe 欄位（rollback_steps / blast_radius / canary_gap / …），供現場發明的字母以
    apply() 在 probe 上生成的算子現算 dim_value。existing_cost = 既有字母表全算子對此候選的最佳聚合成本
    （baseline 選擇用）。real_quality = 若此候選被選中的整體真實結果，operator_alphabet_genesis 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class AlphabetCase:
    """一筆 feature-grounded 字母必要性現實代理（以固定參照 probe 為錨，供現場發明字母評估）。"""
    case_id: str
    candidates: List[AlphabetCandidate]


def alphabet_corpus_fingerprint(corpus: List[AlphabetCase]) -> str:
    """feature-grounded 字母必要性語料 content hash（凍結 + 防竄改證據；Rule 9.33.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_genesis_alphabet(element, corpus: List[AlphabetCase], *,
                              coverage_margin: Optional[float] = None,
                              redundancy_max: Optional[float] = None,
                              aug_weight: Optional[float] = None,
                              max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一個**PRIMITIVES/COMBINATORS 外現場發明**的字母在凍結字母必要性現實情節上是否**必要且非冗餘**.

    `element` 是 duck-typed 字母發明（需 `.apply(features)->float` 與 `.name`，e.g.
    operator_alphabet_genesis.InventedPrimitive/InventedCombinator）。本函式把「用 element 在固定參照 probe
    生成的算子」套到每筆 case 候選的特徵向量現算 dim_value（**不靠字母名匹配**），再量 (a) 增量覆蓋
    （augmented〔既有字母表全算子最佳 + 發明字母生成的算子〕vs baseline〔僅既有字母表全算子最佳〕真實品質
    增益）+ (b) 非冗餘度（與既有 existing_cost 排序的最大一致率），回 `DimensionVerdict`。「genesis 自評
    必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」（Rule 9.33.2/9.33.5）。重放筆數 clamp `SDD_REPLAY_MAX_CASES`。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(element, "name", "(alphabet)")

    examined_cases = list(corpus)[:cap]    # feature-grounded：所有 case 皆相關（以固定參照 probe 為錨）
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=alphabet_corpus_fingerprint(corpus))

    built: List[DimHeldOutCase] = []
    for ac in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(element.apply(c.features))) for c in ac.candidates]
        built.append(DimHeldOutCase(case_id=ac.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=alphabet_corpus_fingerprint(corpus),
    )


def necessity_score_alphabet(element, corpus: List[AlphabetCase], *,
                             coverage_margin: Optional[float] = None,
                             redundancy_max: Optional[float] = None,
                             aug_weight: Optional[float] = None,
                             max_cases: Optional[int] = None) -> float:
    """供 operator_alphabet_genesis 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「operator_alphabet_genesis 結構性無自評」的接縫：genesis 只拿到這個由 oracle 算出的純量，自己沒有
    字母必要性語料、無法給自己打分（Rule 9.33.2 對抗分離）。
    """
    v = evaluate_genesis_alphabet(element, corpus, coverage_margin=coverage_margin,
                                  redundancy_max=redundancy_max, aug_weight=aug_weight,
                                  max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_alphabet_corpus(corpus_dir: Optional[Path] = None) -> List[AlphabetCase]:
    """載入 knowledge/held-out-corpus/ALG-*.yaml 凍結字母必要性語料（deterministic 檔名序）.

    只有本模組讀；operator_alphabet_genesis 結構性無此路徑（Rule 9.33.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[AlphabetCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("ALG-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            AlphabetCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(AlphabetCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases


# ===========================================================================
# Phase V / ACT-151 — feature-grounded 深度必要性評估（深度 >2 算子自我發明反 Goodhart，meta⁷）
# ===========================================================================
#
# Phase U 的 evaluate_genesis_alphabet 評的是「現場發明字母在**固定深度 <=2** 算出的特徵向量上的增量覆蓋」
# ——它預設『組合深度』永遠是 <=2。但 Phase V 讓系統**自我發明一個組合深度 >2 的新複合算子**（meta⁷），被
# 自我擴充物是『文法的結構性深度參數本身』。
#
# 本節升級為 **對深度算子的 feature-grounded 評估**：對一個現場發明、語料事先不知名字的更深複合算子，用它
# 套到凍結語料候選的特徵向量上**現算** dim_value（= depth_op.apply(features)），再量同樣的 (增量覆蓋 ∧ 非冗餘)
# ——隔離「這個更深算子相對既有所有 <=2 淺算子（以 existing_cost 為錨）有沒有帶來真實增量（非線性交互）」。
# operator_depth_genesis 仍結構性看不到語料（它只收注入的 evaluate），對抗分離不變（Rule 9.34.2）。oracle 可知
# operator_depth_genesis 的深度算子介面（duck-typed `.apply()` / `.name`，反向不可——operator_depth_genesis 不
# import oracle）。


@dataclass
class DepthCandidate:
    """一個 pipeline 候選，及其**含固定參照 probe 欄位的特徵向量** + 既有淺算子聚合成本 + 已知真實品質.

    features = 含參照 probe 欄位（rollback_steps / blast_radius / canary_gap / …），供現場發明的更深算子以
    apply() 在 probe 上現算 dim_value。existing_cost = 既有所有深度 <=2 淺算子對此候選的最佳聚合成本
    （baseline 選擇用）。real_quality = 若此候選被選中的整體真實結果，operator_depth_genesis 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class DepthCase:
    """一筆 feature-grounded 深度必要性現實代理（以固定參照 probe 為錨，供現場發明深度算子評估）。"""
    case_id: str
    candidates: List[DepthCandidate]


def depth_corpus_fingerprint(corpus: List[DepthCase]) -> str:
    """feature-grounded 深度必要性語料 content hash（凍結 + 防竄改證據；Rule 9.34.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_genesis_depth(depth_op, corpus: List[DepthCase], *,
                           coverage_margin: Optional[float] = None,
                           redundancy_max: Optional[float] = None,
                           aug_weight: Optional[float] = None,
                           max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一個**深度 >2 現場發明**的複合算子在凍結深度必要性現實情節上是否**必要且非冗餘**.

    `depth_op` 是 duck-typed 深度算子發明（需 `.apply(features)->float` 與 `.name`，e.g.
    operator_depth_genesis.DepthOperator）。本函式把「該更深算子」套到每筆 case 候選的特徵向量現算 dim_value
    （**不靠算子名匹配**），再量 (a) 增量覆蓋（augmented〔既有所有淺算子最佳 + 該深度算子〕vs baseline〔僅淺
    算子最佳〕真實品質增益）+ (b) 非冗餘度（與既有 existing_cost 排序的最大一致率），回 `DimensionVerdict`。
    「genesis 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」（Rule 9.34.2/9.34.5）。重放筆數 clamp
    `SDD_REPLAY_MAX_CASES`。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(depth_op, "name", "(depth)")

    examined_cases = list(corpus)[:cap]    # feature-grounded：所有 case 皆相關（以固定參照 probe 為錨）
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=depth_corpus_fingerprint(corpus))

    built: List[DimHeldOutCase] = []
    for dc in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(depth_op.apply(c.features))) for c in dc.candidates]
        built.append(DimHeldOutCase(case_id=dc.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=depth_corpus_fingerprint(corpus),
    )


def necessity_score_depth(depth_op, corpus: List[DepthCase], *,
                          coverage_margin: Optional[float] = None,
                          redundancy_max: Optional[float] = None,
                          aug_weight: Optional[float] = None,
                          max_cases: Optional[int] = None) -> float:
    """供 operator_depth_genesis 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「operator_depth_genesis 結構性無自評」的接縫：genesis 只拿到這個由 oracle 算出的純量，自己沒有
    深度必要性語料、無法給自己打分（Rule 9.34.2 對抗分離）。
    """
    v = evaluate_genesis_depth(depth_op, corpus, coverage_margin=coverage_margin,
                               redundancy_max=redundancy_max, aug_weight=aug_weight,
                               max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_depth_corpus(corpus_dir: Optional[Path] = None) -> List[DepthCase]:
    """載入 knowledge/held-out-corpus/DPT-*.yaml 凍結深度必要性語料（deterministic 檔名序）.

    只有本模組讀；operator_depth_genesis 結構性無此路徑（Rule 9.34.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[DepthCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("DPT-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            DepthCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(DepthCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases


# ===========================================================================
# Phase W / ACT-154 — feature-grounded 互遞迴必要性評估（互遞迴算子自我發明反 Goodhart，meta⁸）
# ===========================================================================
#
# Phase V 的 evaluate_genesis_depth 評的是「現場發明深度算子（非遞迴有限樹）在固定參照算出的特徵向量上的
# 增量覆蓋」——它預設算子代數『零遞迴、是有限樹』。但 Phase W 讓系統**自我發明一個會呼叫其他算子 / 自呼叫
# 的互遞迴算子**（meta⁸），被自我擴充物是『算子是否可互相引用 / 自引用這個結構參數本身』。
#
# 本節升級為 **對互遞迴算子的 feature-grounded 評估**：對一個現場發明、語料事先不知名字的互遞迴算子，用它
# 套到凍結語料候選的特徵向量上**現算** dim_value（= rec_op.apply(features)），再量同樣的 (增量覆蓋 ∧ 非冗餘)
# ——隔離「這個互遞迴算子相對既有所有非遞迴算子（以 existing_cost 為錨）有沒有帶來真實增量（遞迴交互）」。
# operator_recursion_genesis 仍結構性看不到語料（它只收注入的 evaluate），對抗分離不變（Rule 9.35.2）。oracle
# 可知 operator_recursion_genesis 的互遞迴算子介面（duck-typed `.apply()` / `.name`，反向不可——
# operator_recursion_genesis 不 import oracle）。


@dataclass
class RecursionCandidate:
    """一個 pipeline 候選，及其**含固定參照 probe 欄位的特徵向量** + 既有非遞迴算子聚合成本 + 已知真實品質.

    features = 含參照 probe 欄位（rollback_steps / blast_radius / canary_gap / …），供現場發明的互遞迴算子以
    apply() 在 probe 上現算 dim_value。existing_cost = 既有所有非遞迴算子對此候選的最佳聚合成本（baseline
    選擇用）。real_quality = 若此候選被選中的整體真實結果，operator_recursion_genesis 看不到。
    """
    real_quality: float
    existing_cost: float
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class RecursionCase:
    """一筆 feature-grounded 互遞迴必要性現實代理（以固定參照 probe 為錨，供現場發明互遞迴算子評估）。"""
    case_id: str
    candidates: List[RecursionCandidate]


def recursion_corpus_fingerprint(corpus: List[RecursionCase]) -> str:
    """feature-grounded 互遞迴必要性語料 content hash（凍結 + 防竄改證據；Rule 9.35.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "existing_cost": jc.existing_cost,
                         "features": dict(sorted(jc.features.items()))} for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_genesis_recursion(rec_op, corpus: List[RecursionCase], *,
                               coverage_margin: Optional[float] = None,
                               redundancy_max: Optional[float] = None,
                               aug_weight: Optional[float] = None,
                               max_cases: Optional[int] = None) -> DimensionVerdict:
    """評估一個**互遞迴現場發明**的複合算子在凍結互遞迴必要性現實情節上是否**必要且非冗餘**.

    `rec_op` 是 duck-typed 互遞迴算子發明（需 `.apply(features)->float` 與 `.name`，e.g.
    operator_recursion_genesis.RecursiveOperator）。本函式把「該互遞迴算子」套到每筆 case 候選的特徵向量現算
    dim_value（**不靠算子名匹配**），再量 (a) 增量覆蓋（augmented〔既有所有非遞迴算子最佳 + 該互遞迴算子〕vs
    baseline〔僅非遞迴算子最佳〕真實品質增益）+ (b) 非冗餘度（與既有 existing_cost 排序的最大一致率），回
    `DimensionVerdict`。「genesis 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」（Rule 9.35.2/9.35.5）。
    重放筆數 clamp `SDD_REPLAY_MAX_CASES`。
    """
    mgn = coverage_margin if coverage_margin is not None else dim_coverage_margin()
    rmax = redundancy_max if redundancy_max is not None else dim_redundancy_max()
    w = aug_weight if aug_weight is not None else dim_aug_weight()
    cap = max_cases if max_cases is not None else replay_max()
    name = getattr(rec_op, "name", "(recursion)")

    examined_cases = list(corpus)[:cap]    # feature-grounded：所有 case 皆相關（以固定參照 probe 為錨）
    n = len(examined_cases)
    if n == 0:
        return DimensionVerdict(
            dimension_name=name, baseline_quality=0.0, augmented_quality=0.0,
            incremental_coverage=0.0, coverage_margin=mgn, redundancy=0.0,
            redundancy_max=rmax, tier=0, necessary=False, examined=0,
            corpus_fingerprint=recursion_corpus_fingerprint(corpus))

    built: List[DimHeldOutCase] = []
    for rc in examined_cases:
        cands = [DimCandidate(real_quality=c.real_quality, existing_cost=c.existing_cost,
                              dim_value=float(rec_op.apply(c.features))) for c in rc.candidates]
        built.append(DimHeldOutCase(case_id=rc.case_id, dimension_name=name, candidates=cands))

    base = round(sum(c.baseline_quality() for c in built) / n, 6)
    aug = round(sum(c.augmented_quality(w) for c in built) / n, 6)
    coverage = round(aug - base, 6)
    redundancy = round(max(c.concordance() for c in built), 6)
    necessary = (coverage >= mgn) and (redundancy < rmax)
    return DimensionVerdict(
        dimension_name=name, baseline_quality=base, augmented_quality=aug,
        incremental_coverage=coverage, coverage_margin=mgn,
        redundancy=redundancy, redundancy_max=rmax,
        tier=int(round(coverage * 100)) if necessary else 0,
        necessary=necessary, examined=n,
        corpus_fingerprint=recursion_corpus_fingerprint(corpus),
    )


def necessity_score_recursion(rec_op, corpus: List[RecursionCase], *,
                              coverage_margin: Optional[float] = None,
                              redundancy_max: Optional[float] = None,
                              aug_weight: Optional[float] = None,
                              max_cases: Optional[int] = None) -> float:
    """供 operator_recursion_genesis 注入的必要性純量：必要則回增量覆蓋、不必要（噪音/冗餘）回 0.0.

    這是「operator_recursion_genesis 結構性無自評」的接縫：genesis 只拿到這個由 oracle 算出的純量，自己沒有
    互遞迴必要性語料、無法給自己打分（Rule 9.35.2 對抗分離）。
    """
    v = evaluate_genesis_recursion(rec_op, corpus, coverage_margin=coverage_margin,
                                   redundancy_max=redundancy_max, aug_weight=aug_weight,
                                   max_cases=max_cases)
    return v.incremental_coverage if v.necessary else 0.0


def load_recursion_corpus(corpus_dir: Optional[Path] = None) -> List[RecursionCase]:
    """載入 knowledge/held-out-corpus/RCR-*.yaml 凍結互遞迴必要性語料（deterministic 檔名序）.

    只有本模組讀；operator_recursion_genesis 結構性無此路徑（Rule 9.35.2 對抗分離）。
    """
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[RecursionCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("RCR-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            RecursionCandidate(
                real_quality=float(c["real_quality"]),
                existing_cost=float(c["existing_cost"]),
                features={str(k): float(v) for k, v in (c.get("features", {}) or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(RecursionCase(case_id=str(doc.get("case_id", p.stem)), candidates=cands))
    return cases
