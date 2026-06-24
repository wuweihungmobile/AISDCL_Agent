"""Phase S / ACT-135 — Vocabulary Genesis Grammar（生成文法詞彙的自我擴充，meta⁴）.

對應藍圖：SDD_improving_Automation_19.md §1.1 / §3.1 ACT-135 / Rule 9.31.1 / 9.31.2 / 9.31.4。

Phase R 證了「系統可在**固定特徵詞彙 `VOCAB`**（`dimension_semantics_synthesizer.VOCAB`，8 條硬編
原始特徵）上**組合**（子集 × OPS）發明維度」。但 Phase R 的有界性**完全建立在「VOCAB 固定 8 條」
這一前提**之上——「候選池外」≠「無界」靠的正是 `VOCAB（有限）× arity × OPS = 可枚舉`。Phase R
換不出選單上沒有的新『字』。本模組把詞彙骨架**升維**：從「在固定 8 個字上組合」升到「**自我發明
一個 VOCAB 裡根本沒有的全新原始特徵字**（詞彙外生成）」。這是 meta⁴ 層——系統自己**寫詞彙**。

**「VOCAB 外」≠「無界」（Rule 9.31.1 有界詞彙生成文法，本模組結構基石）**：詞彙外生成被一條
**bounded 詞彙生成文法**封住——`SOURCES`（有限原始信號源）× `TRANSFORMS`（有限轉換算子）。生成
空間因此**可枚舉、有限**，列舉節點 <= `SDD_DIM_VOCAB_BUDGET`（clamp[8,128]，預設 32），**絕不指數
爆炸**。這是「更深的無界生成需另證有界」的形式化兌現：把看似無限的詞彙空間歸約為有限可枚舉文法。

**反自利雙閘第一閘（Rule 9.31.2 詞彙自指守門）**：任何 source/transform 引用保留自指/proposer/
oracle 內部信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的發明字，在送 oracle 前即被
`vocab_self_reference_guard` **結構性拒絕**（零漏放）——系統不能發明一個「量自己核可」的自利原始字。

**承 Phase R 的反 Goodhart 對抗分離（Rule 9.31.2，結構基石）**：本模組**結構性不持有任何必要性
判據、不 import 任何必要性評估器模組、不讀必要性語料**——它只在 bounded 詞彙生成文法上枚舉
`GenesisFeature`，再透過呼叫端**注入的 `evaluate` 回呼**取每個發明字的必要性（= 評估器的
feature-grounded 增量覆蓋）。genesis 因此**無法用自己的尺規證明自己必要**。

**反 big-bang 詞彙發明（Rule 9.31.4）**：一輪至多 `SDD_DIM_EXPAND_K`（沿用 Phase Q/R，預設 1）
個詞彙發明字可進 proposed-pending-signoff，絕不一次劫持整個詞彙本體論。**advisory（Rule 9.31.1）**：
只產 `proposed` 詞彙字，任一納入必經人工 signoff；本模組**絕不自動納入、絕不自寫常數**。

純函式、deterministic、零 LLM、零外網（守 OPEN-10.6）。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import itertools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import yaml

from .file_lock import file_lock
from .state_loader import REPO_ROOT
# 沿用 synthesizer 的保留自指信號集 + 既有 VOCAB（synthesizer 結構性不 import oracle，故
# 透過它取得 VOCAB/RESERVED_SELF_REF 不會把 oracle 牽連進來，對抗分離不破）。
from .dimension_semantics_synthesizer import RESERVED_SELF_REF, VOCAB as _BASE_VOCAB
from .value_dimension_registry import DIMENSION_NAMESPACE, dim_expand_k

# vocab-genesis 共用命名空間（meta-loop-ledger 指紋前綴；不以 `-profile:` 結尾、亦非
# `value-dimension:`，故與 calibration 聚合速率、維度 stock 天花板互不干涉，Rule 9.31.3）。
VOCAB_GENESIS_NAMESPACE = "vocab-genesis:"

# === 自我發明領域審計帳本（沿用 Phase R 的 value-dimension-ledger，增 vocab_inventions/batch_swaps 段）===
DIM_LEDGER_PATH = REPO_ROOT / "build" / "state" / "value-dimension-ledger.yaml"

# === 有界詞彙生成文法（Rule 9.31.1：VOCAB 外生成被有限文法封住，可枚舉）===
# SOURCES：有限原始信號源——VOCAB 外、既有 8 條 VOCAB 連『字』都沒有的更底層原始信號類別。
SOURCES: Tuple[str, ...] = (
    "secret",       # 密鑰 / 憑證相關原始信號
    "identity",     # 身分 / 授權相關原始信號
    "network",      # 網路 / 連線相關原始信號
    "quota",        # 配額 / 限流相關原始信號
    "tenant",       # 多租戶隔離相關原始信號
    "cache",        # 快取 / 一致性相關原始信號
)

# TRANSFORMS：有限轉換算子（把一個原始信號源轉為一條可量測的原始特徵）。
TRANSFORMS: Tuple[str, ...] = ("rate", "window", "depth", "delta", "ratio", "count")

_DEFAULT_VOCAB_BUDGET = 32
_VOCAB_BUDGET_CLAMP = (8, 128)

# 必要性增量覆蓋門檻（與 registry/oracle 共用同一 env SDD_DIM_COVERAGE_MARGIN）。
_DEFAULT_COVERAGE_MARGIN = 0.10


def vocab_budget() -> int:
    """讀 SDD_DIM_VOCAB_BUDGET（env 可調），clamp[8,128]，預設 32（Rule 9.31.1 有界詞彙生成）。"""
    return _clamp_int(os.environ.get("SDD_DIM_VOCAB_BUDGET"), _DEFAULT_VOCAB_BUDGET, _VOCAB_BUDGET_CLAMP)


def vocab_coverage_margin() -> float:
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
# 詞彙發明字（一個 VOCAB 外、現場由詞彙文法生成的新原始特徵字）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenesisFeature:
    """一個 VOCAB 外、由 bounded 詞彙生成文法現場發明的新原始特徵字（meta⁴ 製品）.

    term 是它在 feature 向量裡的鍵（`source.transform`，e.g. `secret.window`）——synthesizer
    之後可在 `expanded_vocab()` = 基礎 VOCAB ∪ 已採納 term 上組合維度。
    apply(features) 把它當單一特徵探針讀 features[term]——oracle 在 feature-grounded 現實情節上
    現算 dim_value（不靠特徵欄名匹配；oracle 可知本型別，反向不可——genesis 不 import oracle）。
    fingerprint 落在 `vocab-genesis:` 命名空間（Rule 9.31.3），與維度/scorer-profile 分開治理
    （詞彙走獨立 stock 天花板 VocabGenesisBounded）。
    """
    source: str
    transform: str
    rationale: str = ""
    namespace: str = VOCAB_GENESIS_NAMESPACE

    @staticmethod
    def of(source: str, transform: str, rationale: str = "") -> "GenesisFeature":
        return GenesisFeature(source=str(source), transform=str(transform), rationale=str(rationale))

    @property
    def term(self) -> str:
        """新詞彙字（feature 向量鍵）：`source.transform`。"""
        return f"{self.source}.{self.transform}"

    @property
    def name(self) -> str:
        """決定性語意名（VOCAB 外發明）：`vocab::source.transform`。"""
        return f"vocab::{self.term}"

    def apply(self, features) -> float:
        """把此詞彙字當單一特徵探針讀（缺則 0.0）。deterministic、純函式（供 oracle feature-grounded 現算）。"""
        return float(features.get(self.term, 0.0))

    def fingerprint(self) -> str:
        """語意指紋（vocab-genesis stock 命名空間，Rule 9.31.3）。"""
        digest = hashlib.sha256(self.name.encode()).hexdigest()[:12]
        return f"{self.namespace}{digest}"

    def to_dict(self) -> dict:
        return {"name": self.name, "term": self.term, "source": self.source,
                "transform": self.transform, "rationale": self.rationale,
                "namespace": self.namespace, "fingerprint": self.fingerprint()}


# ---------------------------------------------------------------------------
# 反自利第一閘：詞彙自指守門（Rule 9.31.2）
# ---------------------------------------------------------------------------

def is_vocab_self_referential(gf: GenesisFeature) -> bool:
    """source 或 transform 是否引用保留自指/proposer/oracle 內部信號（→ 自利字，應拒絕）。"""
    for tok in (gf.source, gf.transform):
        low = str(tok).lower()
        for reserved in RESERVED_SELF_REF:
            if reserved.endswith("_"):
                if low.startswith(reserved):
                    return True
            elif reserved in low:
                return True
    return False


def vocab_self_reference_guard(features: List[GenesisFeature]) -> List[GenesisFeature]:
    """丟棄所有自指詞彙發明字（Rule 9.31.2 反自利第一閘，零漏放）。保序。"""
    return [g for g in features if not is_vocab_self_referential(g)]


# ---------------------------------------------------------------------------
# 有界詞彙生成文法枚舉（Rule 9.31.1：可枚舉、有限、cap 在 budget）
# ---------------------------------------------------------------------------

def enumerate_genesis_features(*, budget: Optional[int] = None,
                               sources: Optional[Tuple[str, ...]] = None,
                               transforms: Optional[Tuple[str, ...]] = None) -> List[GenesisFeature]:
    """在 bounded 詞彙生成文法上 deterministic 枚舉候選詞彙發明字，cap 在 budget（Rule 9.31.1）.

    文法 = sources × transforms。已過 vocab_self_reference_guard（生產 SOURCES/TRANSFORMS 無自指
    token，故恆全存活；guard 仍對「受擾注入的自指詞彙」零漏放）。枚舉節點 <= budget。
    """
    cap = budget if budget is not None else vocab_budget()
    src = sources if sources is not None else SOURCES
    tr = transforms if transforms is not None else TRANSFORMS

    out: List[GenesisFeature] = []
    nodes = 0
    for s, t in itertools.product(src, tr):
        if nodes >= cap:
            return vocab_self_reference_guard(out)
        out.append(GenesisFeature.of(s, t, rationale=f"詞彙外生成：{s}.{t}"))
        nodes += 1
    return vocab_self_reference_guard(out)


def expanded_vocab(accepted_terms) -> Tuple[str, ...]:
    """meta⁴ 對 meta-meta-meta 的供料：基礎 VOCAB ∪ 已採納詞彙發明字 term（deterministic 去重保序）.

    synthesizer 之後可在這擴充後的詞彙上組合維度（Phase R `enumerate_inventions(vocab=...)`）。
    """
    seen = list(_BASE_VOCAB)
    for t in accepted_terms:
        if t not in seen:
            seen.append(str(t))
    return tuple(seen)


# ---------------------------------------------------------------------------
# 詞彙自我發明提案（在有界詞彙文法上以注入 evaluate〔= feature-grounded oracle 必要性〕找最佳）
# ---------------------------------------------------------------------------

@dataclass
class GenesisProposal:
    """單一詞彙發明字的提案（proposed；待人工 signoff，Rule 9.31.1）。"""
    feature: Optional[GenesisFeature] = None
    necessity: float = 0.0           # held-out 增量覆蓋（由注入 evaluate 提供，genesis 無自評）
    margin: float = 0.0
    tier: int = 0                    # necessity capability tier（held-out 唯一合法來源，Rule 9.31.2/9.31.5）
    accepted: bool = False
    nodes_searched: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "feature": self.feature.to_dict() if self.feature else None,
            "fingerprint": self.feature.fingerprint() if self.feature else None,
            "necessity": round(self.necessity, 6),
            "margin": self.margin,
            "tier": self.tier,
            "accepted": self.accepted,
            "nodes_searched": self.nodes_searched,
            "reason": self.reason,
            "maturity": "proposed",   # 強制 proposed（禁自動納入/commit）
        }


def genesis(
    evaluate: Callable[[GenesisFeature], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    tier_fn: Optional[Callable[[float], int]] = None,
    candidates: Optional[List[GenesisFeature]] = None,
) -> GenesisProposal:
    """在 bounded 詞彙生成文法上找「held-out 必要性最高」的 VOCAB 外詞彙發明字（Generator 半邊）.

    本函式**只呼叫注入的 `evaluate`、絕不自算必要性**（反 Goodhart 對抗分離，Rule 9.31.2：
    genesis 結構性無自評能力）。`accepted` 僅代表「達 margin、有資格送人工」，不代表已納入。
    `nodes_searched <= budget`（Rule 9.31.1）。已過 vocab self-reference guard（自指字不入候選）。
    """
    cands = candidates if candidates is not None else enumerate_genesis_features(budget=budget)
    mgn = margin if margin is not None else vocab_coverage_margin()
    tfn = tier_fn or (lambda q: int(round(q * 100)))

    best: Optional[GenesisFeature] = None
    best_necessity = 0.0
    searched = 0
    for gf in cands:
        searched += 1
        n = float(evaluate(gf))
        if best is None or n > best_necessity:   # 嚴格更高才取代（穩定序保證可重現）
            best_necessity = n
            best = gf

    if best is None:
        return GenesisProposal(
            feature=None, necessity=0.0, margin=mgn, tier=0, accepted=False,
            nodes_searched=searched, reason="詞彙文法為空 / 全被自指守門丟棄（無可提案詞彙）")

    accepted = best_necessity >= mgn
    return GenesisProposal(
        feature=best, necessity=best_necessity, margin=mgn,
        tier=tfn(best_necessity), accepted=accepted, nodes_searched=searched,
        reason=("達 margin：VOCAB 外詞彙發明字 held-out 增量覆蓋顯著，可送人工 signoff"
                if accepted else
                "未達 margin：無詞彙發明字達必要性門檻（詞彙本體論可能已足夠，守反自評紀律）"),
    )


# ---------------------------------------------------------------------------
# 一輪詞彙自我發明 + 反 big-bang K_vocab 截斷（Rule 9.31.4）
# ---------------------------------------------------------------------------

@dataclass
class GenesisRound:
    """一輪詞彙自我發明提案的彙整（已套反 big-bang K_vocab 截斷）。"""
    proposals: List[GenesisProposal] = field(default_factory=list)   # 全部 accepted 提案
    selected: List[GenesisProposal] = field(default_factory=list)    # 本輪取至多 K_vocab 個
    k: int = 0
    deferred: List[str] = field(default_factory=list)                # 被順延的詞彙發明字名


def genesis_round(
    evaluate: Callable[[GenesisFeature], float],
    *,
    budget: Optional[int] = None,
    margin: Optional[float] = None,
    k: Optional[int] = None,
    candidates: Optional[List[GenesisFeature]] = None,
) -> GenesisRound:
    """對詞彙文法跑自我發明，彙整 accepted 提案並套**反 big-bang K_vocab 截斷**（Rule 9.31.4）.

    一輪至多 K_vocab（沿用 Phase Q/R 預設 1）個發明字進 proposed-pending-signoff（按 necessity
    由高到低取前 K_vocab，deterministic tie-break by name），其餘順延——絕不一次劫持整個詞彙本體論。
    """
    cap_k = k if k is not None else dim_expand_k()
    cands = candidates if candidates is not None else enumerate_genesis_features(budget=budget)
    mgn = margin if margin is not None else vocab_coverage_margin()
    tfn = lambda q: int(round(q * 100))

    proposals: List[GenesisProposal] = []
    for gf in cands:
        n = float(evaluate(gf))
        if n >= mgn:
            proposals.append(GenesisProposal(
                feature=gf, necessity=n, margin=mgn, tier=tfn(n),
                accepted=True, nodes_searched=1,
                reason="達 margin：VOCAB 外詞彙發明字 held-out 增量覆蓋顯著，可送人工 signoff"))
    ordered = sorted(proposals, key=lambda p: (-p.necessity, p.feature.name))
    selected = ordered[:cap_k]
    deferred = [p.feature.name for p in ordered[cap_k:]]
    return GenesisRound(proposals=proposals, selected=selected, k=cap_k, deferred=deferred)


# ---------------------------------------------------------------------------
# 採納 — 走既有 meta_halt_monitor（共用 meta-loop-ledger + 詞彙 stock 天花板）
# ---------------------------------------------------------------------------

class SignoffRequired(RuntimeError):
    """Rule 9.31.1/9.31.4：詞彙發明字採納須人工 signoff——禁止 genesis 自動納入。"""


class SelfReferentialGenesis(RuntimeError):
    """Rule 9.31.2：拒絕採納自指詞彙發明字（source/transform 引用保留自指信號）。"""


def adopt_genesis_feature(feature: GenesisFeature, capability_level: int, *,
                          human_signoff: bool = False,
                          rule_id: Optional[str] = None,
                          source: str = "vocab_genesis",
                          note: str = "",
                          ledger_path: Optional[Path] = None,
                          ts: Optional[str] = None,
                          check_cardinality: bool = True):
    """採納一個 VOCAB 外詞彙發明字——**走既有 `meta_halt_monitor`、共用 meta-loop-ledger**.

    人工 signoff 強制（Rule 9.31.1/9.31.4）；自指詞彙結構性拒絕（Rule 9.31.2）；
    `guard_vocab_genesis`（詞彙 stock 天花板，Rule 9.31.3）守門。guard 拋出時不落帳，呼叫端轉
    MFSM_ESCALATION。
    """
    if is_vocab_self_referential(feature):
        raise SelfReferentialGenesis(
            f"拒絕採納自指詞彙發明字 {feature.name!r}：source/transform 引用保留自指信號"
            f"（Rule 9.31.2 反自利第一閘）")
    if not human_signoff:
        raise SignoffRequired(
            "詞彙發明字採納須人工 signoff（Rule 9.31.1/9.31.4）；"
            "僅在人工確認 VOCAB 外詞彙本體論發明後以 human_signoff=True 呼叫")
    from .meta_halt import meta_halt_monitor as _mm
    fp = feature.fingerprint()
    rid = rule_id or ("VOC-" + fp.replace(":", "-"))
    if check_cardinality:
        _mm.guard_vocab_genesis(fp, ledger_path=ledger_path)  # 可能 raise（詞彙 stock）
    return _mm.record_rule_add(rid, fp, int(capability_level),
                               source=source, note=note,
                               ledger_path=ledger_path, ts=ts)


def record_round(round_: GenesisRound, *,
                 ledger_path: Optional[Path] = None,
                 ts: Optional[str] = None) -> dict:
    """把一輪詞彙自我發明提案落 value-dimension-ledger.yaml 的 `vocab_inventions` 段（file_lock 保護）."""
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
        vocab_inventions = data.get("vocab_inventions")
        if not isinstance(vocab_inventions, list):
            vocab_inventions = []
        entry = {
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "k": round_.k,
            "selected": [p.to_dict() for p in round_.selected],
            "deferred": list(round_.deferred),
            "n_accepted": len(round_.proposals),
            "signoff": "pending",   # 人工 signoff 狀態（Rule 9.31.1/9.31.4）
        }
        vocab_inventions.append(entry)
        data["vocab_inventions"] = vocab_inventions
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return entry
