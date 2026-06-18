"""Phase O / ACT-112 — Objective Replay Oracle（反 Goodhart held-out 評估器）.

對應藍圖：SDD_improving_Automation_15.md §1.2 / §3.1 ACT-112 / Rule 9.27.2 / 9.27.5。

這是元最佳化 GAN 的**評估半邊（Evaluator）**，也是整份 Phase O 的**安全紅線**：當系統
要自我調整「評判一切的目標權重」時，最大的風險是**評估器墮落成生成器**——tuner 學到
「把某權重設成 0，每個排程成本看似超低」，於是用自己的尺規給自己打高分（Goodhart 崩塌）。

本模組用**框架自身歷史的 held-out 現實代理語料**當試金石，反 Goodhart 的結構保證有三：

  1. **唯一持有現實**：只有本模組讀 `knowledge/held-out-corpus/`；`objective_tuner` 結構性
     看不到語料（它只收到注入的 `evaluate` 回呼），無法為了贏而「背題」。
  2. **真實品質才算數（Rule 9.27.5）**：一個 profile 的好壞 = 它在 held-out 上「挑出的排程
     的真實品質」，**不是** profile 自評的成本分數。Goodhart 退化權重會挑到「自評成本看似
     最低、真實品質卻很差」的陷阱排程 → 真實品質崩 → 拿不到 capability tier。
  3. **凍結 + 防竄改**：語料 content-hashed（`corpus_fingerprint`），重放筆數有界
     `SDD_REPLAY_MAX_CASES`（重用 counterfactual_replay 的既有上限）。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .counterfactual_replay import replay_max  # 重用既有重放筆數上限（Rule 9.27.2/9.24.4）
from .objective_tuner import WeightProfile
from .state_loader import REPO_ROOT

HELD_OUT_CORPUS_DIR = REPO_ROOT / "knowledge" / "held-out-corpus"

# schedule = 有序批次清單；每個 candidate = (schedule, real_quality 0~1)
Schedule = List[List[str]]
Candidate = Tuple[Schedule, float]


@dataclass(frozen=True)
class HeldOutCase:
    """一筆 held-out 現實代理：一個排程問題 + 多個候選排程及其**已知真實品質**.

    real_quality 是「現實」——框架歷史上該排程實測的綜合品質（OQS／低 escalation／低返工），
    由 caller 從既有落盤訊號彙整、content-hashed 凍結。tuner 看不到此欄位。
    """
    case_id: str
    values: Dict[str, float]
    candidates: Tuple[Candidate, ...]   # 須為 tuple（frozen + hashable）

    def pick(self, profile: WeightProfile) -> Candidate:
        """profile 依自身權重挑成本最低的候選排程（argmin score；deterministic tie-break）。

        關鍵：profile 用**自己的尺規**挑排程，但挑中後的**真實品質**由語料決定，profile
        無從影響——這就是反 Goodhart 的核心（Rule 9.27.2/9.27.5）。
        """
        best_idx = 0
        best_score = None
        for idx, (sched, _q) in enumerate(self.candidates):
            s = profile.score_schedule(sched, self.values)
            # 嚴格更低才取代 → 同分時保留較前者（穩定、可重現的 tie-break）。
            if best_score is None or s < best_score:
                best_score = s
                best_idx = idx
        return self.candidates[best_idx]

    def real_quality_under(self, profile: WeightProfile) -> float:
        return float(self.pick(profile)[1])


@dataclass
class OracleVerdict:
    """held-out 對抗評估結論（capability tier 的唯一合法來源，Rule 9.27.5）。"""
    candidate_quality: float
    incumbent_quality: float
    win_delta: float
    win_margin: float
    tier: int                    # = round(candidate_quality * 100)，GraduationRatchet 的 capability_level
    passes_margin: bool
    examined: int
    corpus_fingerprint: str = ""

    def evidence_line(self) -> str:
        return (f"held-out 對抗評估：候選真實品質 {self.candidate_quality:.2f} "
                f"vs incumbent {self.incumbent_quality:.2f}（Δ={self.win_delta:+.2f}，"
                f"margin {self.win_margin:.2f}）｜檢視 {self.examined} 筆現實代理"
                f"{'｜達標' if self.passes_margin else '｜未達標（疑似自評放水則必落此）'}")


def corpus_fingerprint(corpus: List[HeldOutCase]) -> str:
    """語料 content hash（凍結 + 防竄改證據；Rule 9.27.2）。"""
    payload = [
        {"case_id": c.case_id, "values": c.values,
         "candidates": [[s, q] for (s, q) in c.candidates]}
        for c in corpus
    ]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate_profile(profile: WeightProfile, corpus: List[HeldOutCase],
                     *, max_cases: Optional[int] = None) -> float:
    """一個 profile 在 held-out 現實代理上的**真實品質**（0~1，越高越好）.

    = 該 profile 依自身權重挑出的排程，其真實品質在語料上的平均。這就是注入給
    `objective_tuner.propose` 的 `evaluate` 回呼——tuner 只看得到這個數字、看不到語料。
    重放筆數 clamp `SDD_REPLAY_MAX_CASES`（Rule 9.27.2/9.24.4，有界）。
    """
    if not corpus:
        return 0.0
    cap = max_cases if max_cases is not None else replay_max()
    examined = corpus[:cap]
    total = sum(c.real_quality_under(profile) for c in examined)
    return round(total / len(examined), 6)


def evaluate_candidate(candidate: WeightProfile, incumbent: WeightProfile,
                       corpus: List[HeldOutCase], *,
                       win_margin: float, max_cases: Optional[int] = None) -> OracleVerdict:
    """對抗式比較候選 vs incumbent，產出 capability tier（Rule 9.27.5 誠實）。"""
    cap = max_cases if max_cases is not None else replay_max()
    examined = min(len(corpus), cap)
    cq = evaluate_profile(candidate, corpus, max_cases=cap)
    iq = evaluate_profile(incumbent, corpus, max_cases=cap)
    delta = round(cq - iq, 6)
    return OracleVerdict(
        candidate_quality=cq,
        incumbent_quality=iq,
        win_delta=delta,
        win_margin=win_margin,
        tier=int(round(cq * 100)),       # tier 唯一來源 = held-out 真實品質（防自評，Rule 9.27.5）
        passes_margin=delta >= win_margin,
        examined=examined,
        corpus_fingerprint=corpus_fingerprint(corpus),
    )


def make_evaluator(corpus: List[HeldOutCase], *, max_cases: Optional[int] = None):
    """產生注入給 `objective_tuner.propose` 的 `evaluate` 回呼（封裝語料，對 tuner 不透明）。

    這是對抗分離的接縫：tuner 只拿到這個 closure，**拿不到 corpus 本體**（Rule 9.27.2）。
    """
    def _evaluate(profile: WeightProfile) -> float:
        return evaluate_profile(profile, corpus, max_cases=max_cases)
    return _evaluate


# ---------------------------------------------------------------------------
# held-out 語料載入（凍結 YAML；只有本模組讀，tuner 結構性無此路徑）
# ---------------------------------------------------------------------------

def load_corpus(corpus_dir: Optional[Path] = None) -> List[HeldOutCase]:
    """載入 knowledge/held-out-corpus/*.yaml 凍結語料（deterministic 檔名序）。"""
    target = corpus_dir or HELD_OUT_CORPUS_DIR
    cases: List[HeldOutCase] = []
    if not target.exists():
        return cases
    for p in sorted(target.glob("HELDOUT-*.yaml")):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        cands = tuple(
            (list(map(list, c["schedule"])), float(c["real_quality"]))
            for c in doc.get("candidates", [])
        )
        cases.append(HeldOutCase(
            case_id=str(doc.get("case_id", p.stem)),
            values={str(k): float(v) for k, v in (doc.get("values") or {}).items()},
            candidates=cands,
        ))
    return cases
