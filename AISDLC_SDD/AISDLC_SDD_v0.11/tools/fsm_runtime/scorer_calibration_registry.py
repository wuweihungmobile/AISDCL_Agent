"""Phase P / ACT-117 — Scorer Calibration Registry（全評分器一體化自校準骨架）.

對應藍圖：SDD_improving_Automation_16.md §1.1 / §3.1 ACT-117 / Rule 9.28.1。

Phase O 的 `objective_tuner` 證了「**一個**評分器（composition_objective_scorer）的目標
權重可被有界、反 Goodhart 地自校準」。但框架有 **≥8 個凍結評分側寫**（SCORER_VERSION×2、
ADVERSARIAL/SPEC_DEBATE/FRAGILITY/TRAJECTORY/COMPOSITION_FRAGILITY/OBJECTIVE_PROFILE_VERSION）。
本模組把 Phase O 的「生成器骨架」**泛化為對任意評分器泛型的 `ScorerTuner`**：每個評分器
只要登記（namespace + 凍結版本常數參照〔唯讀〕 + 權重格點 schema + incumbent 權重），
即共用同一條「bounded 格點生成 → 注入 evaluate 取真實品質 → proposed-only → 人工 bump」骨架。

**承 Phase O 的反 Goodhart 對抗分離（Rule 9.28.1/9.28.2，結構基石）**：本模組**結構性不
持有任何評分能力、不 import 任何 oracle**——它只在候選格點上列舉 `CalibrationProfile`，
再透過呼叫端**注入的 `evaluate` 回呼**取得每個候選的真實品質。tuner 因此無法用自己的
尺規給自己打高分（它根本沒有尺規）。

**有界（Rule 9.28.1）**：每評分器候選展開 ≤ `SDD_CALIB_TUNE_BUDGET`（clamp[8,256]，預設
64），絕不指數爆炸。**反 big-bang（Rule 9.28.4）**：一輪至多 `SDD_CALIB_BIGBANG_K`（預設
2）個評分器可進 proposed-pending-bump，絕不一次改整套價值系統。**advisory（Rule 9.28.1）**：
只產 `proposed` profile，任一 `*_PROFILE_VERSION` 的 bump 必經人工 signoff；本模組**絕不
自動 commit、絕不自寫任何 scorer 權重常數**。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT

# === 一體化調參帳本（領域審計；churn 治理另走共用 meta-loop-ledger，Rule 9.28.3）===
CALIB_LEDGER_PATH = REPO_ROOT / "build" / "state" / "scorer-calibration-ledger.yaml"
CALIB_REPORT_DIR = REPO_ROOT / "build" / "reports" / "scorer-calibration"

# === 有界搜尋預算（Rule 9.28.1：超限即停，絕不指數爆炸）===
_DEFAULT_TUNE_BUDGET = 64
_TUNE_BUDGET_CLAMP = (8, 256)

# === 勝率門檻（Rule 9.28.2：候選須在 held-out 勝過 incumbent ≥ 此差距才取得 tier）===
_DEFAULT_WIN_MARGIN = 0.10
_WIN_MARGIN_CLAMP = (0.0, 1.0)

# === 反 big-bang K（Rule 9.28.4：一輪至多 K 個評分器可進 proposed-pending-bump）===
_DEFAULT_BIGBANG_K = 2
_BIGBANG_K_CLAMP = (1, 16)


def calib_tune_budget() -> int:
    """讀 SDD_CALIB_TUNE_BUDGET（env 可調），clamp[8,256]，預設 64。"""
    return _clamp_int(os.environ.get("SDD_CALIB_TUNE_BUDGET"), _DEFAULT_TUNE_BUDGET, _TUNE_BUDGET_CLAMP)


def calib_win_margin() -> float:
    """讀 SDD_CALIB_WIN_MARGIN（env 可調），clamp[0,1]，預設 0.10。"""
    raw = os.environ.get("SDD_CALIB_WIN_MARGIN")
    if not raw:
        return _DEFAULT_WIN_MARGIN
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_WIN_MARGIN
    lo, hi = _WIN_MARGIN_CLAMP
    return max(lo, min(hi, val))


def calib_bigbang_k() -> int:
    """讀 SDD_CALIB_BIGBANG_K（env 可調），clamp[1,16]，預設 2（反 big-bang，Rule 9.28.4）。"""
    return _clamp_int(os.environ.get("SDD_CALIB_BIGBANG_K"), _DEFAULT_BIGBANG_K, _BIGBANG_K_CLAMP)


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
# 泛型校準側寫（對任意評分器泛型；對應各評分器的凍結權重面）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationProfile:
    """一個評分器的一組候選權重（泛化自 objective_tuner.WeightProfile）.

    weights 以「排序後的 (name, value) tuple」儲存，保證 fingerprint deterministic、
    與 dict 插入序無關。namespace 決定它在共用 meta-loop-ledger 的指紋命名空間
    （Rule 9.28.1/9.28.3），與 SLV 規則 / obj-profile 共用同一 churn 預算。
    """
    namespace: str
    weights: Tuple[Tuple[str, float], ...]

    @staticmethod
    def of(namespace: str, weights: Dict[str, float]) -> "CalibrationProfile":
        norm = tuple(sorted((str(k), float(v)) for k, v in weights.items()))
        return CalibrationProfile(namespace=namespace, weights=norm)

    def as_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.weights}

    def weight(self, name: str) -> float:
        return self.as_dict().get(name, 0.0)

    def fingerprint(self) -> str:
        """語意指紋（共用 meta-loop-ledger 的 churn 命名空間，Rule 9.28.1/9.28.3）。"""
        payload = self.namespace + "|" + ";".join(f"{k}={v}" for k, v in self.weights)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"namespace": self.namespace, "weights": self.as_dict()}


@dataclass(frozen=True)
class ScorerSpec:
    """一個評分器在一體化校準骨架中的登記項.

    Attributes:
        name: 評分器短名（e.g. "objective" / "adversarial" / "fragility" / "ambiguity"）。
        namespace: 共用 meta-loop-ledger 指紋命名空間（e.g. "obj-profile:"）。
        version_const: 凍結版本常數的「模組.屬性」路徑（唯讀；honesty——tuner 只讀不寫，
            真正 bump 的權力只在人工，Rule 9.28.1/9.28.5）。
        weight_grid: 每個權重維度的離散候選格點（bounded；Rule 9.28.1）。
        incumbent_weights: 目前凍結的 incumbent 權重（唯讀）。
        wired: True = 已具體接入（有格點 + held-out 語料，本份高耦合三器 + objective）；
            False = 已登記命名空間但接入分批（OPEN-P.3 預設：骨架一次到位、接入分批）。
        note: 說明。
    """
    name: str
    namespace: str
    version_const: str
    weight_grid: Dict[str, Tuple[float, ...]]
    incumbent_weights: Dict[str, float]
    wired: bool = True
    note: str = ""

    def incumbent(self) -> CalibrationProfile:
        return CalibrationProfile.of(self.namespace, self.incumbent_weights)


# ---------------------------------------------------------------------------
# 註冊表（單一真實來源：全評分器版本面）
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, ScorerSpec] = {}


def register(spec: ScorerSpec) -> None:
    _REGISTRY[spec.name] = spec


def get_spec(name: str) -> ScorerSpec:
    return _REGISTRY[name]


def all_specs() -> List[ScorerSpec]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def wired_specs() -> List[ScorerSpec]:
    return [s for s in all_specs() if s.wired]


def namespaces() -> List[str]:
    return [s.namespace for s in all_specs()]


def is_calibration_namespace(fingerprint: str) -> bool:
    """指紋是否屬於任一已登記校準命名空間（供 ACT-119 聚合停機過濾）。"""
    return any(fingerprint.startswith(ns) for ns in namespaces())


# === 預設登記：高耦合三器（adversarial↔fragility↔ambiguity）+ objective（O 已驗證）===
# 其餘 4 器（oqs / debate / trajectory / comp_fragility）登記命名空間但 wired=False
# （OPEN-P.3 預設：骨架一次到位、接入分批降風險；待單一驗證穩定再翻 wired）。

def _register_defaults() -> None:
    if _REGISTRY:
        return
    register(ScorerSpec(
        name="objective", namespace="obj-profile:",
        version_const="composition_objective_scorer.OBJECTIVE_PROFILE_VERSION",
        weight_grid={"batch_w": (0.0, 0.5, 1.0, 1.5, 2.0),
                     "latency_w": (0.0, 0.05, 0.1, 0.2, 0.35, 0.5)},
        incumbent_weights={"batch_w": 1.0, "latency_w": 0.1},
        wired=True, note="Phase O 已驗證；一體化骨架沿用其格點，與 objective_tuner 等價"))
    register(ScorerSpec(
        name="adversarial", namespace="adversarial-profile:",
        version_const="adversarial_synthesizer.ADVERSARIAL_PROFILE_VERSION",
        weight_grid={"attack_strength_w": (0.0, 0.5, 1.0, 1.5, 2.0),
                     "breadth_w": (0.0, 0.25, 0.5, 1.0)},
        incumbent_weights={"attack_strength_w": 1.0, "breadth_w": 0.5},
        wired=True, note="高耦合：攻擊強度↓會使 fragility 誤判脆弱規格↓（接縫 Goodhart）"))
    register(ScorerSpec(
        name="fragility", namespace="fragility-profile:",
        version_const="spec_fragility_scorer.FRAGILITY_PROFILE_VERSION",
        weight_grid={"threshold_w": (0.5, 1.0, 1.5, 2.0),
                     "history_w": (0.0, 0.15, 0.3, 0.5)},
        incumbent_weights={"threshold_w": 1.0, "history_w": 0.3},
        wired=True, note="高耦合：閾值↑會放過脆弱規格、把代價轉嫁下游"))
    register(ScorerSpec(
        name="ambiguity", namespace="ambiguity-profile:",
        version_const="ambiguity_scorer.SCORER_VERSION",
        weight_grid={"block_threshold_w": (0.5, 1.0, 1.5, 2.0),
                     "dimension_w": (0.0, 0.25, 0.5, 1.0)},
        incumbent_weights={"block_threshold_w": 1.0, "dimension_w": 0.5},
        wired=True, note="高耦合：block 閾值放寬→更多規格過閘→返工代價落 objective 盲區"))
    # 接入分批（staged；Rule 9.28.1 骨架已涵蓋，待 wired 翻牌）
    for nm, ns, vc in (
        ("oqs", "oqs-profile:", "output_quality_scorer.SCORER_VERSION"),
        ("debate", "debate-profile:", "spec_debate.SPEC_DEBATE_PROFILE_VERSION"),
        ("trajectory", "trajectory-profile:", "capability_trajectory_monitor.TRAJECTORY_PROFILE_VERSION"),
        ("comp_fragility", "comp-fragility-profile:", "composition_blast_analyzer.COMPOSITION_FRAGILITY_PROFILE_VERSION"),
    ):
        register(ScorerSpec(name=nm, namespace=ns, version_const=vc,
                            weight_grid={}, incumbent_weights={}, wired=False,
                            note="已登記命名空間；接入分批（OPEN-P.3），待單一驗證穩定再翻 wired"))


_register_defaults()


# ---------------------------------------------------------------------------
# 泛型生成器（ScorerTuner；泛化自 objective_tuner.propose）
# ---------------------------------------------------------------------------

def candidate_grid(spec: ScorerSpec, *, budget: Optional[int] = None) -> List[CalibrationProfile]:
    """deterministic 候選格點（笛卡兒積），cap 在 budget（Rule 9.28.1 SearchBounded）。

    排除與 incumbent 完全相同的點。超 budget 時按穩定序截斷。staged（wired=False）無格點。
    """
    if not spec.weight_grid:
        return []
    cap = budget if budget is not None else calib_tune_budget()
    inc = spec.incumbent()
    names = sorted(spec.weight_grid)
    grid: List[CalibrationProfile] = []
    for combo in itertools.product(*(spec.weight_grid[n] for n in names)):
        cand = CalibrationProfile.of(spec.namespace, dict(zip(names, combo)))
        if cand == inc:
            continue
        grid.append(cand)
    return grid[:cap]


@dataclass
class CalibrationProposal:
    """單一評分器的調參提案（proposed；待人工 signoff，Rule 9.28.1）。"""
    scorer_name: str
    candidate: CalibrationProfile
    incumbent: CalibrationProfile
    candidate_quality: float = 0.0   # held-out 真實品質（由注入 evaluate 提供）
    incumbent_quality: float = 0.0
    win_delta: float = 0.0
    win_margin: float = 0.0
    tier: int = 0                    # capability tier（held-out 唯一合法來源；Rule 9.28.2/9.28.5）
    accepted: bool = False           # 達 margin（達標才有資格送人工 signoff）
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "scorer_name": self.scorer_name,
            "namespace": self.candidate.namespace,
            "candidate": self.candidate.as_dict(),
            "incumbent": self.incumbent.as_dict(),
            "candidate_fingerprint": self.candidate.fingerprint(),
            "candidate_quality": self.candidate_quality,
            "incumbent_quality": self.incumbent_quality,
            "win_delta": round(self.win_delta, 6),
            "win_margin": self.win_margin,
            "tier": self.tier,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動 verified/commit）
        }


def propose(
    spec: ScorerSpec,
    evaluate: Callable[[CalibrationProfile], float],
    *,
    budget: Optional[int] = None,
    win_margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
) -> CalibrationProposal:
    """在 bounded 候選格點上找「held-out 真實品質最高」的 profile（Generator 半邊，泛型）.

    結構同 objective_tuner.propose：本函式**只呼叫注入的 `evaluate`、絕不自算品質**（反
    Goodhart 對抗分離，Rule 9.28.2：tuner 結構性無自評能力）。`accepted` 僅代表「達 margin、
    有資格送人工」，**不代表已採納**（採納須人工 signoff + adopt_profile，Rule 9.28.1）。
    `nodes_searched ≤ budget`（Rule 9.28.1）。
    """
    inc = spec.incumbent()
    margin = win_margin if win_margin is not None else calib_win_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))
    grid = candidate_grid(spec, budget=budget)

    inc_quality = float(evaluate(inc))
    best: Optional[CalibrationProfile] = None
    best_quality = inc_quality
    searched = 0
    for cand in grid:
        searched += 1
        q = float(evaluate(cand))
        if q > best_quality:      # 嚴格優於目前最佳才取代（穩定序保證可重現）
            best_quality = q
            best = cand

    if best is None:
        return CalibrationProposal(
            scorer_name=spec.name, candidate=inc, incumbent=inc,
            candidate_quality=inc_quality, incumbent_quality=inc_quality,
            win_delta=0.0, win_margin=margin, tier=tfn(inc_quality),
            accepted=False, nodes_searched=searched,
            reason="格點內無候選嚴格優於 incumbent（incumbent 已是區域最優或近最優）",
        )

    delta = round(best_quality - inc_quality, 6)
    accepted = delta >= margin
    return CalibrationProposal(
        scorer_name=spec.name, candidate=best, incumbent=inc,
        candidate_quality=best_quality, incumbent_quality=inc_quality,
        win_delta=delta, win_margin=margin, tier=tfn(best_quality),
        accepted=accepted, nodes_searched=searched,
        reason=("達 margin：候選 held-out 真實品質顯著優於 incumbent，可送人工 signoff"
                if accepted else
                "未達 margin：候選雖略優但差距 < win_margin，不送 signoff（守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪一體化提案 + 反 big-bang 截斷（Rule 9.28.4）
# ---------------------------------------------------------------------------

@dataclass
class CalibrationRound:
    """一輪全評分器提案的彙整（已套反 big-bang K 截斷）。"""
    proposals: List[CalibrationProposal] = field(default_factory=list)   # 全部 accepted 提案
    selected: List[CalibrationProposal] = field(default_factory=list)    # 本輪取至多 K 個
    k: int = 0
    deferred: List[str] = field(default_factory=list)                    # 被順延的評分器名

    def value_vector(self) -> Dict[str, CalibrationProfile]:
        """本輪候選價值向量（scorer_name → 候選 profile），供 joint oracle 聯合評估（ACT-118）。"""
        return {p.scorer_name: p.candidate for p in self.selected}


def propose_round(
    evaluators: Dict[str, Callable[[CalibrationProfile], float]],
    *,
    budget: Optional[int] = None,
    win_margin: Optional[float] = None,
    k: Optional[int] = None,
) -> CalibrationRound:
    """對所有 wired 評分器各跑 propose，彙整 accepted 提案並套**反 big-bang K 截斷**.

    Rule 9.28.4：一輪至多 K 個評分器可進 proposed-pending-bump（按 win_delta 由高到低取
    前 K，deterministic tie-break by scorer_name），其餘順延——絕不一次改整套價值系統。
    evaluators 只提供 wired 且有對應評估器的評分器（per-scorer held-out 由 ACT-118 注入）。
    """
    cap_k = k if k is not None else calib_bigbang_k()
    proposals: List[CalibrationProposal] = []
    for spec in wired_specs():
        ev = evaluators.get(spec.name)
        if ev is None:
            continue
        p = propose(spec, ev, budget=budget, win_margin=win_margin)
        if p.accepted:
            proposals.append(p)
    # 反 big-bang：按 (win_delta desc, scorer_name asc) 取前 K
    ordered = sorted(proposals, key=lambda p: (-p.win_delta, p.scorer_name))
    selected = ordered[:cap_k]
    deferred = [p.scorer_name for p in ordered[cap_k:]]
    return CalibrationRound(proposals=proposals, selected=selected,
                            k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 / 退役 — 走既有 meta_halt_monitor，共用 meta-loop-ledger churn 預算（Rule 9.28.3）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.28.1/9.28.4：calibration profile 採納須人工 signoff——禁止 tuner 自動 commit。"""


def adopt_profile(profile: CalibrationProfile, capability_level: int, *,
                  human_signoff: bool = False,
                  rule_id: Optional[str] = None,
                  source: str = "scorer_calibration",
                  note: str = "",
                  ledger_path: Optional[Path] = None,
                  ts: Optional[str] = None,
                  check_aggregate: bool = True):
    """採納一個 calibration profile——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    這是「不增第六軌」的接縫（Rule 9.28.3）：8 評分器的 profile add↔retire 元迴圈完全納入
    既有 `META_FSM` 的 `ChurnBounded`/`GraduationRatchet`（per-fingerprint）+ Phase P 新增的
    `CrossScorerChurnBounded`（聚合採納速率，ACT-119）。

    人工 signoff 強制（Rule 9.28.1/9.28.4）：`human_signoff=False` 直接 raise。
    guard 拋出（ChurnBoundExceeded / GraduationRatchetViolation / CrossScorerChurnExceeded）
    時不落帳，呼叫端轉 MFSM_ESCALATION。
    """
    if not human_signoff:
        raise SignoffRequired(
            "calibration profile 採納須人工 signoff（Rule 9.28.1/9.28.4）；"
            "僅在人工確認對應 *_PROFILE_VERSION bump 後以 human_signoff=True 呼叫"
        )
    from .meta_halt import meta_halt_monitor as _mm
    fp = profile.fingerprint()
    rid = rule_id or ("CALIB-" + fp.replace(":", "-"))
    if check_aggregate:
        # Phase P / ACT-119：聚合採納速率守門（跨評分器耦合停機，Rule 9.28.3）。
        _mm.guard_calibration_adoption(fp, ledger_path=ledger_path)  # 可能 raise
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def retire_profile(profile: CalibrationProfile, capability_level: int = 0, *,
                   rule_id: Optional[str] = None,
                   source: str = "scorer_calibration",
                   note: str = "",
                   ledger_path: Optional[Path] = None,
                   ts: Optional[str] = None):
    """退役一個 calibration profile（被新 profile 取代）。退役永遠安全（縮小集合），不被阻擋。"""
    from .meta_halt import meta_halt_monitor as _mm
    fp = profile.fingerprint()
    rid = rule_id or ("CALIB-" + fp.replace(":", "-"))
    return _mm.record_rule_retire(rid, fp, int(capability_level),
                                  source=source, note=note,
                                  ledger_path=ledger_path, ts=ts)


def record_round(round_: CalibrationRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪提案落 scorer-calibration-ledger.yaml（domain 審計鏈；file_lock 保護）.

    本帳本是**領域審計**（記提案細節 + 反 big-bang 截斷）；churn 治理走的是**共用
    meta-loop-ledger**（adopt_profile / retire_profile，Rule 9.28.3），兩者分工不同。
    """
    path = Path(ledger_path) if ledger_path else CALIB_LEDGER_PATH
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
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.28.1/9.28.4）
        }
        rounds.append(entry)
        data["rounds"] = rounds
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
