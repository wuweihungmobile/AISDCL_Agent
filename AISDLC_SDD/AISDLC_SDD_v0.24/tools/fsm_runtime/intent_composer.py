"""Phase M M-M1 / ACT-097 — Intent Composer（跨意圖語義組合衝突偵測 + 組合帳本）.

對應藍圖：SDD_improving_Automation_13.md §1.2 / §3.1 ACT-097 / Rule 9.25.1~9.25.2。
形式化對應：formal/COMPOSITION_FSM.tla（獨立命名空間，reneg/conflicts 兩計數器）。

`value_planner`（Phase I）只做**逐意圖獨立 ROI 排序**，`FLEET_FSM`（Phase I）只證
**資源鎖層級**無死鎖；兩意圖完全可以各自正確取放鎖，卻在**共享 spec 節點**上留下
互相矛盾的規格。本模組是組合層的「事前一致性偵測」：

  1. compute_shared_nodes(intents) —— 找出被 ≥2 意圖同時觸及的 spec 節點。
  2. compute_conflicts(intents) —— 對共享節點偵測**語義方向相反**的立場（antonym /
     negation parity，純規則式 deterministic）。
  3. composition-ledger（build/state/composition-ledger.yaml）—— 記錄每個共享節點
     的「協商（negotiate）」事件，`compute_reneg(node)` 回該節點的再協商次數，供
     composition_halt_monitor 的 RenegotiationBounded 守門（破組合層 livelock）。

純離線、零外網、零 LLM（沿用 meta_ledger / spec_fragility_scorer 慣例）。advisory：
本模組只「偵測 + 落帳」，**絕不自動 commit 排程、絕不自動改 spec**——組合排程的最終
選定仍須 BACKLOG_PRIORITIZED 人工 signoff（Rule 8 / Rule 9.23.2）。
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .file_lock import file_lock
from .pattern_matcher import normalize
from .state_loader import REPO_ROOT

LEDGER_PATH = REPO_ROOT / "build" / "state" / "composition-ledger.yaml"


def default_ledger_path() -> Path:
    """預設組合帳本路徑，可由 `SDD_COMPOSITION_LEDGER_PATH` 環境變數覆寫（測試隔離）。"""
    override = os.environ.get("SDD_COMPOSITION_LEDGER_PATH")
    return Path(override) if override else LEDGER_PATH


# === 語義方向相反偵測（規則式，deterministic）===
# 共享節點上「立場對立」的反義詞對（任一方向命中即視為方向相反）。
_ANTONYM_PAIRS = (
    ("stackable", "exclusive"), ("forbidden", "allowed"), ("forbid", "allow"),
    ("disable", "enable"), ("deny", "permit"), ("reject", "accept"),
    ("required", "optional"), ("mandatory", "optional"), ("sync", "async"),
    ("synchronous", "asynchronous"), ("increase", "decrease"), ("max", "min"),
    ("disallow", "allow"), ("merge", "split"), ("on", "off"), ("true", "false"),
)
# 否定標記（中英）——negation parity 不一致 + 共享內容 token ⇒ 方向相反。
_NEG_TOKENS = frozenset({
    "not", "no", "never", "without", "禁止", "不可", "不能", "不", "否", "拒絕",
    "停用", "關閉", "不得",
})


@dataclass
class IntentSpec:
    """一個意圖在組合層的觸及面：node_stances = {共享 spec 節點 → 此意圖在該節點的立場}。"""
    intent_id: str
    title: str
    node_stances: Dict[str, str] = field(default_factory=dict)

    def nodes(self) -> set:
        return set(self.node_stances.keys())


@dataclass
class ConflictItem:
    node_id: str
    intent_a: str
    intent_b: str
    stance_a: str
    stance_b: str

    def describe(self) -> str:
        return (f"節點 {self.node_id}：意圖 {self.intent_a}「{self.stance_a}」 ⟂ "
                f"意圖 {self.intent_b}「{self.stance_b}」（語義方向相反）")


@dataclass
class CompositionResult:
    intents: List[str]
    shared_nodes: List[str]
    conflicts: List[ConflictItem] = field(default_factory=list)

    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def conflicting_nodes(self) -> List[str]:
        seen: List[str] = []
        for c in self.conflicts:
            if c.node_id not in seen:
                seen.append(c.node_id)
        return seen


def compute_shared_nodes(intents: List[IntentSpec]) -> List[str]:
    """被 ≥2 個意圖同時觸及的 spec 節點（排序穩定）。"""
    counts: Dict[str, int] = {}
    for it in intents:
        for n in it.nodes():
            counts[n] = counts.get(n, 0) + 1
    return sorted(n for n, c in counts.items() if c >= 2)


def _neg_parity(text: str) -> int:
    """否定標記出現次數的奇偶（0=偶，1=奇）。中文否定詞以子字串比對。"""
    low = text.lower()
    cnt = 0
    for tok in _NEG_TOKENS:
        if tok.isascii():
            cnt += low.split().count(tok)
        else:
            cnt += text.count(tok)
    return cnt % 2


def _strip_neg(text: str) -> str:
    """剝除否定標記後的原始文字（中英；用於判斷兩立場是否在談同一件事）。"""
    out = text
    for tok in _NEG_TOKENS:
        if tok.isascii():
            out = " ".join(w for w in out.split() if w.lower() != tok)
        else:
            out = out.replace(tok, "")
    return out


def _shares_content(a: str, b: str) -> bool:
    """兩立場（否定剝離後）是否在談同一件事：normalized token 交集，或 ≥2 字共同子字串。

    雙重判據兼顧英文（空白斷詞 → token 交集）與中文（無空白 → 字元子字串）。
    """
    sa, sb = _strip_neg(a), _strip_neg(b)
    ta = {t for t in normalize(sa).split() if t}
    tb = {t for t in normalize(sb).split() if t}
    if ta & tb:
        return True
    # ≥2 字共同子字串（中文友善）
    compact = sa.replace(" ", "")
    for i in range(len(compact) - 1):
        if compact[i:i + 2] and compact[i:i + 2] in sb.replace(" ", ""):
            return True
    return False


def is_conflict(stance_a: str, stance_b: str) -> bool:
    """兩立場在同一共享節點是否**語義方向相反**（deterministic, rule-based v1）。

    相反條件（任一成立）：
      (a) 反義詞跨立場出現（如 stackable ⟂ exclusive）；
      (b) 否定 parity 不一致 **且** 兩立場（否定剝離後）在談同一件事（共享內容）。
    相同正規化立場（或談不同面向、無對立）⇒ 不衝突（避免誤判）。
    """
    na, nb = normalize(stance_a), normalize(stance_b)
    if na == nb:
        return False
    # 反義詞在原始與正規化 token 上皆檢查（避免 normalize 同義詞折射改掉反義詞）。
    ta = set(na.split()) | set(stance_a.lower().split())
    tb = set(nb.split()) | set(stance_b.lower().split())
    for x, y in _ANTONYM_PAIRS:
        if (x in ta and y in tb) or (y in ta and x in tb):
            return True
    if _neg_parity(stance_a) != _neg_parity(stance_b) and _shares_content(stance_a, stance_b):
        return True
    return False


def compute_conflicts(intents: List[IntentSpec]) -> List[ConflictItem]:
    """對所有共享節點，逐意圖配對偵測語義方向相反（穩定排序，deterministic）。"""
    shared = compute_shared_nodes(intents)
    by_id = {it.intent_id: it for it in intents}
    ordered_ids = [it.intent_id for it in intents]
    conflicts: List[ConflictItem] = []
    for node in shared:
        holders = [iid for iid in ordered_ids if node in by_id[iid].node_stances]
        for i in range(len(holders)):
            for j in range(i + 1, len(holders)):
                a, b = holders[i], holders[j]
                sa = by_id[a].node_stances[node]
                sb = by_id[b].node_stances[node]
                if is_conflict(sa, sb):
                    conflicts.append(ConflictItem(node, a, b, sa, sb))
    return conflicts


def compose(intents: List[IntentSpec]) -> CompositionResult:
    """組合分析入口：算共享節點 + 衝突集（advisory，不落帳、不改 spec）。"""
    return CompositionResult(
        intents=[it.intent_id for it in intents],
        shared_nodes=compute_shared_nodes(intents),
        conflicts=compute_conflicts(intents),
    )


# ============ 組合帳本（per-共享節點 negotiate 事件，file_lock 保護）============

EVENT_NEGOTIATE = "negotiate"


def node_fingerprint(node_id: str) -> str:
    """共享節點識別指紋。

    節點 ID（如 AC-014）是**精確識別碼**——不可用 normalize 語意折射（會把 AC-014 與
    AC-099 的數字去掉而誤合為同一指紋）。只做小寫 + 去空白的輕量正規化以容忍大小寫差異。
    """
    return "".join(str(node_id).split()).lower()


def load_ledger(ledger_path: Optional[Path] = None) -> dict:
    path = Path(ledger_path) if ledger_path else default_ledger_path()
    if not path.exists():
        return {"schema_version": 1, "events": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {"schema_version": 1, "events": []}
    data.setdefault("schema_version", 1)
    data.setdefault("events", [])
    if not isinstance(data["events"], list):
        data["events"] = []
    return data


def record_negotiate(
    node_id: str,
    *,
    intent_a: str = "",
    intent_b: str = "",
    note: str = "",
    ledger_path: Optional[Path] = None,
    ts: Optional[str] = None,
) -> dict:
    """落盤一筆共享節點協商事件（file_lock 保護的 read-modify-write）。"""
    path = Path(ledger_path) if ledger_path else default_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    fp = node_fingerprint(node_id)
    with file_lock(lock):
        ledger = load_ledger(path)
        evs = [e for e in ledger.get("events", []) if isinstance(e, dict)]
        seq = (max((int(e.get("seq", 0)) for e in evs), default=0)) + 1
        ev = {
            "seq": seq,
            "ts": ts or _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "event_type": EVENT_NEGOTIATE,
            "node_id": str(node_id),
            "fingerprint": fp,
            "intent_a": str(intent_a),
            "intent_b": str(intent_b),
            "note": str(note),
        }
        ledger["events"] = evs + [ev]
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
        tmp.replace(path)
    return ev


def compute_reneg(node_id: str, *, ledger: Optional[dict] = None,
                  ledger_path: Optional[Path] = None) -> int:
    """回該共享節點指紋累計的協商（negotiate）次數 = 跨意圖再協商輪數。"""
    led = ledger if ledger is not None else load_ledger(ledger_path)
    fp = node_fingerprint(node_id)
    return sum(1 for e in led.get("events", [])
               if isinstance(e, dict) and e.get("event_type") == EVENT_NEGOTIATE
               and e.get("fingerprint") == fp)
