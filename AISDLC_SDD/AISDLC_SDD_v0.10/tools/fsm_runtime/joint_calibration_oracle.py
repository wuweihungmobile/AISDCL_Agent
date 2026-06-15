"""Phase P / ACT-118 — Joint Calibration Oracle（跨評分器反 Goodhart 聯合評估器）.

對應藍圖：SDD_improving_Automation_16.md §1.1 / §3.1 ACT-118 / Rule 9.28.2 / 9.28.5。

這是 Phase P 的**靈魂與安全紅線**。Phase O 的 `objective_replay_oracle` 只評**一個**評分器
的權重——它在「該評分器自己的語料」上驗證沒退步。但一體化後，8 個評分器是同一價值觀的
8 個投影，**彼此耦合**：把 `adversarial` 攻擊強度調弱，會使一個「整體很差」的 pipeline 候選
不再被攻擊懲罰而被選中，而 `fragility`/`ambiguity` 各自的 per-scorer oracle **看不到這個
跨評分器的接縫效應**。N 個各自誠實的 per-scorer oracle，攔不住「在接縫處作弊」。

本模組是**pipeline 級**聯合評估器：把一個**候選價值向量**（≤K 個被同時提案的 profile +
其餘 incumbent）整套套進凍結的 pipeline 級 held-out 歷史情節，量**整體真實結果**勝率。

反 Goodhart 結構保證（承 Phase O 三保證，推到一體化層級）：
  1. **唯一持有 pipeline 現實**：只有本模組讀 `knowledge/held-out-corpus/JOINT-*.yaml`；
     `scorer_calibration_registry`（生成器）結構性看不到語料（它只收注入的 evaluate）。
  2. **聯合真實品質才算數（Rule 9.28.2/9.28.5）**：joint tier = 候選向量在 pipeline held-out
     上「聯合選出的候選的真實品質」；任何 per-scorer 自評/單獨 oracle 通過**不得**充當聯合
     capability-delta。**per 通過但 joint 不通過 → 一律以 joint 為準**（攔接縫作弊）。
  3. **凍結 + 防竄改 + 有界**：語料 content-hashed，重放筆數 ≤ `SDD_REPLAY_MAX_CASES`
     （重用 counterfactual_replay 既有上限）。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .counterfactual_replay import replay_max   # 重用既有重放筆數上限（Rule 9.28.2）
from .scorer_calibration_registry import CalibrationProfile, wired_specs
from .state_loader import REPO_ROOT

HELD_OUT_CORPUS_DIR = REPO_ROOT / "knowledge" / "held-out-corpus"

# 一個候選價值向量：scorer_name → 該評分器的 profile（候選或 incumbent）。
ValueVector = Dict[str, CalibrationProfile]


@dataclass
class JointCandidate:
    """一個 pipeline 候選結果：各評分器對它的特徵 + 整體**已知真實品質**.

    features[scorer_name][weight_name] = 該候選在該權重維度上的特徵值；某評分器 profile
    對此候選的成本 = Σ weight(name) × feature(name)（lower = 該評分器偏好它）。
    real_quality = 若此候選被聯合選中的**整體真實結果**（OQS／低 escalation／低返工），
    生成器看不到。
    """
    real_quality: float
    features: Dict[str, Dict[str, float]]


@dataclass
class JointHeldOutCase:
    """一筆 pipeline 級現實代理：一個 pipeline 問題 + 多個候選結果及其已知真實品質。"""
    case_id: str
    candidates: List[JointCandidate]

    def select(self, vector: ValueVector) -> JointCandidate:
        """價值向量依各評分器成本之**和**挑成本最低的候選（argmin；deterministic tie-break）。

        關鍵：向量用各評分器**自己的尺規**挑候選，但挑中後的**真實品質**由語料決定，向量
        無從影響——這就是反 Goodhart 的核心，且**接縫效應**（弱化某評分器使壞候選被選中）
        會誠實反映在被選候選的低 real_quality 上（Rule 9.28.2/9.28.5）。
        """
        best_idx = 0
        best_cost = None
        for idx, cand in enumerate(self.candidates):
            cost = _joint_cost(vector, cand)
            if best_cost is None or cost < best_cost:   # 嚴格更低才取代（穩定 tie-break）
                best_cost = cost
                best_idx = idx
        return self.candidates[best_idx]

    def real_quality_under(self, vector: ValueVector) -> float:
        return float(self.select(vector).real_quality)


def _score_features(profile: CalibrationProfile, features: Dict[str, float]) -> float:
    """單一評分器對一候選的成本 = Σ weight(name) × feature(name)。"""
    return sum(profile.weight(k) * float(v) for k, v in features.items())


def _joint_cost(vector: ValueVector, cand: JointCandidate) -> float:
    """候選的聯合成本 = Σ over 向量中也出現在候選 features 的評分器之成本。"""
    total = 0.0
    for scorer_name, profile in vector.items():
        feats = cand.features.get(scorer_name)
        if feats:
            total += _score_features(profile, feats)
    return round(total, 6)


@dataclass
class JointVerdict:
    """pipeline 級聯合對抗評估結論（聯合 capability tier 唯一合法來源，Rule 9.28.5）。"""
    candidate_quality: float
    incumbent_quality: float
    win_delta: float
    win_margin: float
    tier: int                    # = round(candidate_quality*100)，joint capability_level
    passes_margin: bool
    examined: int
    corpus_fingerprint: str = ""
    changed_scorers: List[str] = field(default_factory=list)

    def evidence_line(self) -> str:
        return (f"pipeline 級聯合評估：候選向量整體真實品質 {self.candidate_quality:.2f} "
                f"vs incumbent {self.incumbent_quality:.2f}（Δ={self.win_delta:+.2f}，"
                f"margin {self.win_margin:.2f}）｜檢視 {self.examined} 筆 pipeline 現實代理"
                f"｜本輪變動：{', '.join(self.changed_scorers) or '（無）'}"
                f"{'｜達標' if self.passes_margin else '｜未達標（接縫 Goodhart 必落此）'}")


def corpus_fingerprint(corpus: List[JointHeldOutCase]) -> str:
    """語料 content hash（凍結 + 防竄改證據；Rule 9.28.2）。"""
    payload = [
        {"case_id": c.case_id,
         "candidates": [{"real_quality": jc.real_quality, "features": jc.features}
                        for jc in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_vector(vector: ValueVector, corpus: List[JointHeldOutCase],
                    *, max_cases: Optional[int] = None) -> float:
    """一個候選價值向量在 pipeline 級 held-out 上的**整體真實品質**（0~1，越高越好）.

    = 該向量在每個 case 上聯合選出的候選的真實品質之平均。重放筆數 clamp
    `SDD_REPLAY_MAX_CASES`（Rule 9.28.2，有界）。
    """
    if not corpus:
        return 0.0
    cap = max_cases if max_cases is not None else replay_max()
    examined = corpus[:cap]
    total = sum(c.real_quality_under(vector) for c in examined)
    return round(total / len(examined), 6)


def evaluate_joint(candidate_vector: ValueVector, incumbent_vector: ValueVector,
                   corpus: List[JointHeldOutCase], *,
                   win_margin: float, max_cases: Optional[int] = None) -> JointVerdict:
    """對抗式比較候選向量 vs incumbent 向量，產出**聯合** capability tier（Rule 9.28.5 誠實）。

    這是「per 通過但 joint 不通過 → 以 joint 為準」的釘死處：candidate_vector 即使每個變動
    評分器在自己 per-scorer oracle 上通過，只要 pipeline 級聯合真實品質未勝 incumbent ≥ margin，
    就 `passes_margin=False`，拿不到聯合 tier（呼叫端據此拒絕採納）。
    """
    cap = max_cases if max_cases is not None else replay_max()
    examined = min(len(corpus), cap)
    cq = evaluate_vector(candidate_vector, corpus, max_cases=cap)
    iq = evaluate_vector(incumbent_vector, corpus, max_cases=cap)
    delta = round(cq - iq, 6)
    changed = [n for n in sorted(candidate_vector)
               if incumbent_vector.get(n) != candidate_vector.get(n)]
    return JointVerdict(
        candidate_quality=cq,
        incumbent_quality=iq,
        win_delta=delta,
        win_margin=win_margin,
        tier=int(round(cq * 100)),       # 聯合 tier 唯一來源 = pipeline held-out 真實品質
        passes_margin=delta >= win_margin,
        examined=examined,
        corpus_fingerprint=corpus_fingerprint(corpus),
        changed_scorers=changed,
    )


# ---------------------------------------------------------------------------
# 價值向量組裝（incumbent 全集 + 套用本輪 ≤K 候選）
# ---------------------------------------------------------------------------

def incumbent_vector(specs=None) -> ValueVector:
    """全 wired 評分器的 incumbent 向量（唯讀凍結權重）。"""
    specs = specs if specs is not None else wired_specs()
    return {s.name: s.incumbent() for s in specs}


def apply_selection(base_vector: ValueVector, value_vector: ValueVector) -> ValueVector:
    """把本輪選中的 ≤K 候選 profile 疊到 incumbent 全集上，產出候選向量（其餘維持 incumbent）。"""
    merged = dict(base_vector)
    merged.update(value_vector)
    return merged


# ---------------------------------------------------------------------------
# pipeline 級聯合語料載入（凍結 YAML；只有本模組讀，生成器結構性無此路徑）
# ---------------------------------------------------------------------------

def load_joint_corpus(corpus_dir: Optional[Path] = None) -> List[JointHeldOutCase]:
    """載入 knowledge/held-out-corpus/JOINT-*.yaml 凍結語料（deterministic 檔名序）。"""
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[JointHeldOutCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("JOINT-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = [
            JointCandidate(
                real_quality=float(c["real_quality"]),
                features={str(sn): {str(k): float(v) for k, v in feats.items()}
                          for sn, feats in (c.get("features") or {}).items()},
            )
            for c in doc.get("candidates", [])
        ]
        cases.append(JointHeldOutCase(case_id=str(doc.get("case_id", p.stem)),
                                      candidates=cands))
    return cases
