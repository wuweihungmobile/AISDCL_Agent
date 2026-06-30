"""Phase L M-L1 / ACT-089 — Meta-Loop Ledger（自我改進元迴圈 churn 帳本）.

對應藍圖：SDD_improving_Automation_12.md §3.1 ACT-089 / Rule 9.24.1。

純離線、零外網。記錄每次治理規則的 add（學習層 verified commit）/ retire（GC
set_maturity→audit-only|deprecated）事件，附 **語意指紋**（pattern_matcher.normalize
規則 title/spec，使「語意同型」的規則被視為同一指紋）+ `capability_level_at` + 時戳。

核心查詢 `compute_churn(fingerprint)`：回傳該指紋的「再採納」次數 = 被退役後又重新
加入的次數（add-after-retire）。這是 meta_halt_monitor 的 ChurnBounded 判據基座，也
對應 META_FSM.tla 的 `churn` 變數。

設計選擇（沿用 file_lock / pattern_matcher / yaml 既有慣例）：
- 帳本落盤 `build/state/meta-loop-ledger.yaml`，不常駐 context（漸進式揭露）。
- 事件僅存 add / retire / fitness_add；「是否為再採納」由 ledger 結構推導，呼叫端
  不需自行判斷（避免分類旁路）。
- `ts` 與 `capability_level` 由 caller 提供（避免 Date.now 不確定性，比照 scaffold_gc）。
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

from ..file_lock import file_lock
from ..pattern_matcher import normalize

_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = _ROOT / "build" / "state" / "meta-loop-ledger.yaml"


def default_ledger_path() -> Path:
    """預設帳本路徑（生產路徑），可由 `SDD_META_LEDGER_PATH` 環境變數覆寫。

    新增此覆寫鉤子是為了讓接線進生產路徑的 `exit_learning_commit` /
    `set_maturity` 在測試環境（conftest 設環境變數指向 tmp）下不會污染 repo 的
    真實 `build/state/meta-loop-ledger.yaml`；未設環境變數時行為與既有完全相同。
    """
    override = os.environ.get("SDD_META_LEDGER_PATH")
    if override:
        return Path(override)
    return LEDGER_PATH

# 事件型別
EVENT_ADD = "add"             # 學習層 commit verified 規則（GROW）
EVENT_RETIRE = "retire"       # GC set_maturity→audit-only|deprecated（SHRINK）
EVENT_FITNESS_ADD = "fitness_add"  # FSE 新增 fitness function（GROW，不計 rule churn）
EVENT_TYPES = (EVENT_ADD, EVENT_RETIRE, EVENT_FITNESS_ADD)


@dataclass
class MetaEvent:
    seq: int
    ts: str
    event_type: str
    rule_id: str
    fingerprint: str
    capability_level: int = 0
    source: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "ts": self.ts,
            "event_type": self.event_type,
            "rule_id": self.rule_id,
            "fingerprint": self.fingerprint,
            "capability_level": self.capability_level,
            "source": self.source,
            "note": self.note,
        }


def fingerprint_of(text: str) -> str:
    """規則語意指紋：以 pattern_matcher.normalize 把 title/spec 折射成語意 token bag。

    使「字面不同但語意同型」的規則（重學的 SLV' vs 原 SLV）收斂到同一指紋，
    是 churn 偵測能抓到「換皮重學」的關鍵。
    """
    return normalize(text)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


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


def _events(ledger: dict) -> List[dict]:
    return [e for e in ledger.get("events", []) if isinstance(e, dict)]


def record_event(
    event_type: str,
    rule_id: str,
    *,
    fingerprint: str,
    capability_level: int = 0,
    source: str = "",
    note: str = "",
    ledger_path: Optional[Path] = None,
    ts: Optional[str] = None,
) -> MetaEvent:
    """落盤一筆 churn 事件（file_lock 保護的 read-modify-write）。"""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"invalid event_type={event_type!r}; expected {EVENT_TYPES}")
    path = Path(ledger_path) if ledger_path else default_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".lock")
    with file_lock(lock):
        ledger = load_ledger(path)
        evs = _events(ledger)
        seq = (max((int(e.get("seq", 0)) for e in evs), default=0)) + 1
        ev = MetaEvent(
            seq=seq,
            ts=ts or _now_iso(),
            event_type=event_type,
            rule_id=str(rule_id),
            fingerprint=str(fingerprint),
            capability_level=int(capability_level),
            source=str(source),
            note=str(note),
        )
        ledger["events"] = evs + [ev.to_dict()]
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        tmp.replace(path)
    return ev


def events_for(fingerprint: str, *, ledger: Optional[dict] = None,
               ledger_path: Optional[Path] = None) -> List[dict]:
    led = ledger if ledger is not None else load_ledger(ledger_path)
    return [e for e in _events(led) if e.get("fingerprint") == fingerprint]


def compute_churn(fingerprint: str, *, ledger: Optional[dict] = None,
                  ledger_path: Optional[Path] = None) -> int:
    """回傳該指紋的「再採納」次數 = 被 retire 後又 add 的次數（add-after-retire）。

    序列 add→（churn 0）；add→retire→（churn 0，僅退役）；add→retire→add（churn 1，
    再採納一次）；add→retire→add→retire→add（churn 2）。對應 META_FSM.tla 的 churn 變數。
    fitness_add 不計入 rule churn（不同維度）。
    """
    seq = [e for e in events_for(fingerprint, ledger=ledger, ledger_path=ledger_path)
           if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
    seq.sort(key=lambda e: int(e.get("seq", 0)))
    churn = 0
    retired_since_last_add = False
    for e in seq:
        et = e.get("event_type")
        if et == EVENT_RETIRE:
            retired_since_last_add = True
        elif et == EVENT_ADD:
            if retired_since_last_add:
                churn += 1            # add-after-retire = 一次再採納
            retired_since_last_add = False
    return churn


def is_readopt(fingerprint: str, *, ledger: Optional[dict] = None,
               ledger_path: Optional[Path] = None) -> bool:
    """下一次 add 是否會構成「再採納」（= 此指紋最近一筆 add/retire 事件為 retire）。"""
    seq = [e for e in events_for(fingerprint, ledger=ledger, ledger_path=ledger_path)
           if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
    if not seq:
        return False
    seq.sort(key=lambda e: int(e.get("seq", 0)))
    return seq[-1].get("event_type") == EVENT_RETIRE


def last_retire_capability(fingerprint: str, *, ledger: Optional[dict] = None,
                           ledger_path: Optional[Path] = None) -> Optional[int]:
    """此指紋最近一次 retire 當下的 capability_level（GraduationRatchet 比較基準）。"""
    seq = [e for e in events_for(fingerprint, ledger=ledger, ledger_path=ledger_path)
           if e.get("event_type") == EVENT_RETIRE]
    if not seq:
        return None
    seq.sort(key=lambda e: int(e.get("seq", 0)))
    return int(seq[-1].get("capability_level", 0))


def all_fingerprints(*, ledger: Optional[dict] = None,
                     ledger_path: Optional[Path] = None) -> List[str]:
    led = ledger if ledger is not None else load_ledger(ledger_path)
    seen: List[str] = []
    for e in _events(led):
        fp = e.get("fingerprint")
        if fp and fp not in seen:
            seen.append(fp)
    return seen


# ---------------------------------------------------------------------------
# Phase P / ACT-119 — 跨評分器聚合停機支撐（CrossScorerChurnBounded, Rule 9.28.3）
# ---------------------------------------------------------------------------
#
# Phase O 的 per-fingerprint ChurnBounded 對「N 條各自有界、合起來耦合震盪」的調參迴圈
# 盲目：A 採納改環境→B incumbent 看似變差→B 採納改回→A 變差→A 採**另一個**新 profile…
# 每步都是不同指紋的首次採納，per-fingerprint churn 皆 0，卻整體無限自我擾動燒 token。
# 本節提供「聚合採納速率窗」基座：跨所有 calibration 命名空間（`*-profile:`）在最近視窗內
# 的總採納次數有界——這正補上 per-fingerprint 看不見的耦合無限擾動。

def is_calibration_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於評分器校準命名空間（`<scorer>-profile:` 前綴）。

    校準命名空間（obj-profile / adversarial-profile / fragility-profile / ambiguity-profile
    / oqs-profile / debate-profile / trajectory-profile / comp-fragility-profile）的 namespace
    一律以 `-profile` 結尾；SLV 規則指紋為 normalize() token bag（無 `:` 命名空間），故不誤判。
    """
    if not fingerprint or ":" not in fingerprint:
        return False
    ns = fingerprint.split(":", 1)[0]
    return ns.endswith("-profile")


def calibration_adds_in_window(window: int, *, ledger: Optional[dict] = None,
                               ledger_path: Optional[Path] = None) -> int:
    """最近 `window` 筆 ledger 事件中，calibration 命名空間的 ADD 次數（聚合速率）。

    這是 CrossScorerChurnBounded 的判據基座：把「最近一段時間內、跨所有評分器的採納」
    一起計數——無論是單一評分器抖動還是 A→B→A 耦合震盪，密集採納都會被此速率窗攔下。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    evs = sorted(_events(led), key=lambda e: int(e.get("seq", 0)))
    recent = evs[-window:] if window > 0 else evs
    return sum(1 for e in recent
               if e.get("event_type") == EVENT_ADD
               and is_calibration_fingerprint(str(e.get("fingerprint", ""))))


def distinct_calibration_namespaces_in_window(window: int, *, ledger: Optional[dict] = None,
                                              ledger_path: Optional[Path] = None) -> List[str]:
    """最近 `window` 筆事件中、出現 ADD 的 distinct calibration 命名空間（耦合判據/診斷用）。"""
    led = ledger if ledger is not None else load_ledger(ledger_path)
    evs = sorted(_events(led), key=lambda e: int(e.get("seq", 0)))
    recent = evs[-window:] if window > 0 else evs
    seen: List[str] = []
    for e in recent:
        fp = str(e.get("fingerprint", ""))
        if e.get("event_type") == EVENT_ADD and is_calibration_fingerprint(fp):
            ns = fp.split(":", 1)[0] + ":"
            if ns not in seen:
                seen.append(ns)
    return seen


# ---------------------------------------------------------------------------
# Phase Q / ACT-125 — 維度基數有界停機支撐（DimensionCardinalityBounded, Rule 9.29.3）
# ---------------------------------------------------------------------------
#
# Phase O 的 per-fingerprint ChurnBounded、Phase P 的 CrossScorerChurnBounded 都只管「固定維度
# 內 profile 的採納速率」——它們對「**維度數本身單調膨脹**」（每條新維度只首採一次、per-指紋
# churn=0、聚合速率也可任意慢）結構性盲目。Phase Q 把「增維」這條新迴圈納管：value-dimension
# 的 add↔retire 共用既有 churn/ratchet（退役維度再採納須挾 necessity capability-delta），**但
# 額外受一條 stock 天花板封死**——現存活躍維度數有界，補上 churn/速率窗都看不見的維度基數爆炸。

DIMENSION_NAMESPACE = "value-dimension:"


def is_dimension_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 value-dimension 命名空間（`value-dimension:` 前綴）。

    注意：`value-dimension` **不以 `-profile` 結尾**，故 `is_calibration_fingerprint` 對它回 False
    ——value-dimension 與 calibration profile 互不干涉（Rule 9.29.3：分開治理，stock 天花板 vs 聚合速率）。
    """
    return bool(fingerprint) and fingerprint.startswith(DIMENSION_NAMESPACE)


def active_value_dimensions(*, ledger: Optional[dict] = None,
                            ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 value-dimension 指紋（stock）= 已 add 且其後未被 retire 的維度.

    這是 DimensionCardinalityBounded 的 stock 判據基座：對每個 value-dimension 指紋取其
    add/retire 事件序列，最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_dimension_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase R / ACT-131 — 維度退役聯動聚合速率支撐（SwapCadenceBounded, Rule 9.30.3）
# ---------------------------------------------------------------------------
#
# Phase Q 的 DimensionCardinalityBounded（stock）對「達天花板後反覆退一條換一條」**結構性盲目**：
# 每次 retire-to-swap = retire 1 + add 1，net cardinality=0（stock 永不觸頂），且每條維度
# per-fingerprint churn 可 <=1（retire A 換 B、retire B 換 C…，每指紋只動一次）——ChurnBounded
# （per-fingerprint）與 DimensionCardinalityBounded（stock）**皆看不見這條「定基數旋轉」的新無界
# 迴圈**。本節提供「swap 聚合速率窗」基座：最近視窗內被標記為 swap 的採納次數有界——補上
# per-fingerprint churn 與 cardinality stock 都看不見的定基數旋轉重寫本體論（Phase R PR-2）。

SWAP_SOURCE = "dimension_swap"


def is_swap_event(event: dict) -> bool:
    """事件是否為退役聯動 swap 的一環（source 以 `dimension_swap` 標記）。"""
    return str(event.get("source", "")).startswith(SWAP_SOURCE)


def swap_adds_in_window(window: int, *, ledger: Optional[dict] = None,
                        ledger_path: Optional[Path] = None) -> int:
    """最近 `window` 筆 ledger 事件中，被標記為 swap 的 ADD 次數（退役聯動聚合速率）.

    這是 SwapCadenceBounded 的判據基座：每次 retire-to-swap 落一筆 swap-ADD；把「最近一段時間
    內的 swap 採納」一起計數——無論是 A→B→A 往復還是 A→B→C→D 旋轉，定基數密集 swap 都會被此
    速率窗攔下（per-fingerprint churn / cardinality stock 皆盲目，Phase R PR-2）。

    註：批次退役聯動（`dimension_batch_swap:<id>`，Phase S）**不**計入此 per-swap 速率窗——
    `is_swap_event` 以 `dimension_swap` 前綴判定，而 `dimension_batch_swap` **不**以 `dimension_swap`
    起頭（是 `dimension_b...`），故批次走獨立的 `batch_swap_ops_in_window`（Rule 9.31.3 分開治理）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    evs = sorted(_events(led), key=lambda e: int(e.get("seq", 0)))
    recent = evs[-window:] if window > 0 else evs
    return sum(1 for e in recent if e.get("event_type") == EVENT_ADD and is_swap_event(e))


# ---------------------------------------------------------------------------
# Phase S / ACT-137 — 詞彙生成自我擴充（VocabGenesisBounded, Rule 9.31.3，meta⁴）
# ---------------------------------------------------------------------------
#
# Phase R 的有界性建立在「VOCAB 是固定 8 條」前提上（候選池外≠無界，靠 VOCAB×arity×OPS 可枚舉）。
# Phase S 讓系統**自我發明 VOCAB 外的新原始特徵字**（meta⁴），VOCAB 不再固定——詞彙基數本身
# 會單調膨脹（每個新字首採、per-fingerprint churn=0；批次速率窗只看 swap，皆盲目）。本節提供
# 「vocab-genesis 命名空間 + stock 判據基座」：現存活躍詞彙發明字有界——補上 per-fingerprint
# churn / 批次速率窗都看不見的詞彙基數爆炸（Phase S PS-1）。

VOCAB_GENESIS_NAMESPACE = "vocab-genesis:"


def is_vocab_genesis_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 vocab-genesis 命名空間（`vocab-genesis:` 前綴）.

    注意：`vocab-genesis` 不以 `-profile` 結尾、亦非 `value-dimension:` 前綴，故與 calibration
    聚合速率守門、value-dimension stock 天花板互不干涉（Rule 9.31.3：詞彙與維度分開治理）。
    """
    return bool(fingerprint) and fingerprint.startswith(VOCAB_GENESIS_NAMESPACE)


def active_vocab_genesis_features(*, ledger: Optional[dict] = None,
                                  ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 vocab-genesis 指紋（stock）= 已 add 且其後未被 retire 的詞彙發明字.

    這是 VocabGenesisBounded 的 stock 判據基座：對每個 vocab-genesis 指紋取其 add/retire 事件
    序列，最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單（Phase S PS-1，meta⁴）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_vocab_genesis_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase S / ACT-137 — 多維度批次退役聯動聚合速率（BatchSwapCadenceBounded, Rule 9.31.3）
# ---------------------------------------------------------------------------
#
# Phase R 的 SwapCadenceBounded（per-swap-ADD 計數）+ 單調棘輪（per-swap tier 比較）對「一次退 m
# 換 n 的批次操作」**結構性盲目**：批次大小無界（一次劫持整個本體論）、批次內高低互抵（夾帶退步
# swap）、批次旋轉（一個原子批次≠n 次 swap，per-swap 速率窗計數失真）。本節提供「批次操作聚合
# 速率窗」基座：每次批次 retire-to-swap 以 `dimension_batch_swap:<batch_id>` 標記其 add 事件，
# batch_id = deterministic(sorted(in+out fingerprints))；最近視窗內 **distinct batch_id 數** 即批次
# 操作數——補上 per-swap SwapCadence / 單調棘輪都看不見的批次旋轉（Phase S PS-2，meta⁴）。

BATCH_SWAP_SOURCE = "dimension_batch_swap"


def is_batch_swap_event(event: dict) -> bool:
    """事件是否為多維度批次退役聯動的一環（source 以 `dimension_batch_swap` 標記）.

    `dimension_batch_swap` 不以 `dimension_swap` 起頭（是 `dimension_b...`），故 `is_swap_event`
    對它回 False——批次與 per-swap 分開治理（Rule 9.31.3）。
    """
    return str(event.get("source", "")).startswith(BATCH_SWAP_SOURCE)


def batch_id_of(event: dict) -> str:
    """從批次事件的 source（`dimension_batch_swap:<batch_id>`）取出 batch_id（無則回空字串）。"""
    src = str(event.get("source", ""))
    if ":" in src and src.startswith(BATCH_SWAP_SOURCE):
        return src.split(":", 1)[1]
    return ""


def batch_swap_ops_in_window(window: int, *, ledger: Optional[dict] = None,
                             ledger_path: Optional[Path] = None) -> int:
    """最近 `window` 筆 ledger 事件中，distinct 批次操作數（批次退役聚合速率）.

    這是 BatchSwapCadenceBounded 的判據基座：一個批次操作的 n 筆 add 共用同一 batch_id，故計
    **distinct batch_id** 而非 add 筆數——精準把「一個原子批次算一次操作」（per-swap 速率窗會把
    它誤算成 n 次）。最近視窗內 distinct batch_id 數即批次操作頻率（Phase S PS-2，meta⁴）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    evs = sorted(_events(led), key=lambda e: int(e.get("seq", 0)))
    recent = evs[-window:] if window > 0 else evs
    seen: set = set()
    for e in recent:
        if e.get("event_type") == EVENT_ADD and is_batch_swap_event(e):
            bid = batch_id_of(e)
            if bid:
                seen.add(bid)
    return len(seen)


# ---------------------------------------------------------------------------
# Phase T / ACT-143 — 轉換算子文法自我擴充（OperatorGenesisBounded, Rule 9.32.4，meta⁵）
# ---------------------------------------------------------------------------
#
# Phase S 的有界性建立在「TRANSFORMS/OPS 固定 6+4 條」前提上（被發明物是『資料』，執行它們的是人類
# 寫死全函式）。Phase T 讓系統**自我發明 TRANSFORMS/OPS 外的新算子**（meta⁵），被發明物第一次是
# 『可執行計算』——算子基數本身會單調膨脹（每個新算子首採、per-fingerprint churn=0；維度/詞彙 stock
# 天花板對它皆盲目）。本節提供「operator-genesis 命名空間 + stock 判據基座」：現存活躍算子發明有界
# ——補上 per-fingerprint churn / 維度/詞彙 stock 都看不見的算子基數爆炸（Phase T PT-1）。

OPERATOR_GENESIS_NAMESPACE = "operator-genesis:"


def is_operator_genesis_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 operator-genesis 命名空間（`operator-genesis:` 前綴）.

    注意：`operator-genesis` 不以 `-profile` 結尾、亦非 `value-dimension:` / `vocab-genesis:` 前綴，
    故與 calibration 聚合速率守門、維度/詞彙 stock 天花板互不干涉（Rule 9.32.4：算子與維度/詞彙分開治理）。
    """
    return bool(fingerprint) and fingerprint.startswith(OPERATOR_GENESIS_NAMESPACE)


def active_operator_genesis_features(*, ledger: Optional[dict] = None,
                                     ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 operator-genesis 指紋（stock）= 已 add 且其後未被 retire 的算子發明.

    這是 OperatorGenesisBounded 的 stock 判據基座：對每個 operator-genesis 指紋取其 add/retire 事件
    序列，最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單（Phase T PT-1，meta⁵）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_operator_genesis_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase U / ACT-148 — 組合算子文法自我擴充（AlphabetGenesisBounded, Rule 9.33.4，meta⁶）
# ---------------------------------------------------------------------------
#
# Phase T 的有界性建立在「算子字母表 PRIMITIVES/COMBINATORS 固定 8+9 條」前提上（被發明物是『一個算子』，
# 逐個產物查可計算性）。Phase U 讓系統**自我發明 PRIMITIVES/COMBINATORS 外的新運算字母**（meta⁶），被發明
# 物是『會被文法用來生成整個算子代數的生成規則零件』——字母基數本身會單調膨脹（每個新字母首採、
# per-fingerprint churn=0；維度/詞彙/算子 stock 天花板對它皆盲目）。本節提供「alphabet-genesis 命名空間 +
# stock 判據基座」：現存活躍字母發明有界——補上 per-fingerprint churn / 維度/詞彙/算子 stock 都看不見的
# 字母基數爆炸（Phase U PU-1）。

ALPHABET_GENESIS_NAMESPACE = "alphabet-genesis:"


def is_alphabet_genesis_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 alphabet-genesis 命名空間（`alphabet-genesis:` 前綴）.

    注意：`alphabet-genesis` 不以 `-profile` 結尾、亦非 `value-dimension:` / `vocab-genesis:` /
    `operator-genesis:` 前綴，故與 calibration 聚合速率守門、維度/詞彙/算子 stock 天花板互不干涉
    （Rule 9.33.4：字母與維度/詞彙/算子分開治理）。
    """
    return bool(fingerprint) and fingerprint.startswith(ALPHABET_GENESIS_NAMESPACE)


def active_alphabet_genesis_features(*, ledger: Optional[dict] = None,
                                     ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 alphabet-genesis 指紋（stock）= 已 add 且其後未被 retire 的字母發明.

    這是 AlphabetGenesisBounded 的 stock 判據基座：對每個 alphabet-genesis 指紋取其 add/retire 事件
    序列，最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單（Phase U PU-1，meta⁶）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_alphabet_genesis_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase V / ACT-151 — 算子組合深度文法自我擴充（DepthGenesisBounded, Rule 9.34.4，meta⁷）
# ---------------------------------------------------------------------------
#
# Phase U 的有界性建立在「組合深度被人類凍結在 <=2」前提上（被發明物是『字母』，整代數深度恆 2、cost 恆小常數）。
# Phase V 讓系統**自我發明組合深度 >2 的新複合算子**（meta⁷），被自我擴充物是『文法的結構性深度參數本身』——
# 關鍵：cost==depth（一元基底）/ depth+1（二元基底），「自我擴充深度」字面上就是「自我擴充計算步數」。深度算子
# 基數本身會單調膨脹（每個新深度算子首採、per-fingerprint churn=0；維度/詞彙/算子/字母 stock 天花板對它皆盲目）。
# 本節提供「depth-genesis 命名空間 + stock 判據基座」：現存活躍深度算子發明有界——補上 per-fingerprint churn /
# 維度/詞彙/算子/字母 stock 都看不見的深度算子基數爆炸（Phase V PV-1）。

DEPTH_GENESIS_NAMESPACE = "depth-genesis:"


def is_depth_genesis_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 depth-genesis 命名空間（`depth-genesis:` 前綴）.

    注意：`depth-genesis` 不以 `-profile` 結尾、亦非 `value-dimension:` / `vocab-genesis:` /
    `operator-genesis:` / `alphabet-genesis:` 前綴，故與 calibration 聚合速率守門、維度/詞彙/算子/字母 stock
    天花板互不干涉（Rule 9.34.4：深度與維度/詞彙/算子/字母分開治理）。
    """
    return bool(fingerprint) and fingerprint.startswith(DEPTH_GENESIS_NAMESPACE)


def active_depth_genesis_features(*, ledger: Optional[dict] = None,
                                  ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 depth-genesis 指紋（stock）= 已 add 且其後未被 retire 的深度算子發明.

    這是 DepthGenesisBounded 的 stock 判據基座：對每個 depth-genesis 指紋取其 add/retire 事件序列，
    最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單（Phase V PV-1，meta⁷）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_depth_genesis_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase W / ACT-154 — 算子間互遞迴文法自我擴充（RecursionGenesisBounded, Rule 9.35.4，meta⁸）
# ---------------------------------------------------------------------------
#
# Phase T~V 的有界性建立在「算子代數結構性零遞迴、運算式是有限樹」前提上（被發明物是算子/字母/深度，求值
# 路徑無 while/無自呼叫、cost 是結構性有限量）。Phase W 讓系統**自我發明會呼叫其他算子 / 自呼叫的互遞迴
# 算子**（meta⁸），被自我擴充物是『算子是否可互相引用 / 自引用這個結構參數本身』——互遞迴算子基數本身會單調
# 膨脹（每個新互遞迴算子首採、per-fingerprint churn=0；維度/詞彙/算子/字母/深度 stock 天花板對它皆盲目）。
# 本節提供「recursion-genesis 命名空間 + stock 判據基座」：現存活躍互遞迴算子發明有界——補上 per-fingerprint
# churn / 維度/詞彙/算子/字母/深度 stock 都看不見的互遞迴算子基數爆炸（Phase W PW-1）。

RECURSION_GENESIS_NAMESPACE = "recursion-genesis:"


def is_recursion_genesis_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 recursion-genesis 命名空間（`recursion-genesis:` 前綴）.

    注意：`recursion-genesis` 不以 `-profile` 結尾、亦非 `value-dimension:` / `vocab-genesis:` /
    `operator-genesis:` / `alphabet-genesis:` / `depth-genesis:` 前綴，故與 calibration 聚合速率守門、維度/
    詞彙/算子/字母/深度 stock 天花板互不干涉（Rule 9.35.4：互遞迴與維度/詞彙/算子/字母/深度分開治理）。
    """
    return bool(fingerprint) and fingerprint.startswith(RECURSION_GENESIS_NAMESPACE)


def active_recursion_genesis_features(*, ledger: Optional[dict] = None,
                                      ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 recursion-genesis 指紋（stock）= 已 add 且其後未被 retire 的互遞迴算子發明.

    這是 RecursionGenesisBounded 的 stock 判據基座：對每個 recursion-genesis 指紋取其 add/retire 事件序列，
    最後一筆為 ADD 即「目前活躍」。回傳 distinct 活躍指紋清單（Phase W PW-1，meta⁸）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_recursion_genesis_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active


# ---------------------------------------------------------------------------
# Phase X / ACT-157 — embodied-grounding 命名空間（具身接地閘）.
# ---------------------------------------------------------------------------
# Phase L~W 把元迴圈自我演化能力推到 meta⁸，但「評估」端一路是合成語料勝率——從不啟動沙箱、
# 從不查真實日誌（GAP-X1，由 Phase X 切片 FF-16 量測 surface）。Phase X 完整版在 META_FSM 納入
# （MFSM_GROW）前插一道 EMBODIED_GROUNDING_GATE：自我發明能力被納入前須由 sdd-evaluator 在沙箱
# 實跑、產出具身 grounded-verdict（OQS 接地）。每個具身接地事件為一個 `embodied-grounding:` 命名
# 空間指紋，其 add↔retire 與既有 SLV/scorer-profile/value-dimension/vocab/operator/alphabet/depth/
# recursion-genesis 共用本軌同一 churn 預算（不增第六軌、不新增狀態變數，故 META 13 distinct 不回歸）。

EMBODIED_GROUNDING_NAMESPACE = "embodied-grounding:"


def is_embodied_grounding_fingerprint(fingerprint: str) -> bool:
    """指紋是否屬於 embodied-grounding 命名空間（`embodied-grounding:` 前綴）.

    與 calibration 聚合速率守門、維度/詞彙/算子/字母/深度/互遞迴 stock 天花板互不干涉
    （Rule 9.36：具身接地與其他自我擴充迴圈分開治理，共用同一 churn 預算）。
    """
    return bool(fingerprint) and fingerprint.startswith(EMBODIED_GROUNDING_NAMESPACE)


def active_embodied_grounding_features(*, ledger: Optional[dict] = None,
                                       ledger_path: Optional[Path] = None) -> List[str]:
    """現存活躍 embodied-grounding 指紋（stock）= 已 add 且其後未被 retire 的具身接地納入.

    對每個 embodied-grounding 指紋取其 add/retire 事件序列，最後一筆為 ADD 即「目前活躍」。
    回傳 distinct 活躍指紋清單（Phase X / ACT-157，具身接地閘 churn 折疊基座）。
    """
    led = ledger if ledger is not None else load_ledger(ledger_path)
    active: List[str] = []
    for fp in all_fingerprints(ledger=led):
        if not is_embodied_grounding_fingerprint(fp):
            continue
        seq = [e for e in events_for(fp, ledger=led)
               if e.get("event_type") in (EVENT_ADD, EVENT_RETIRE)]
        if not seq:
            continue
        seq.sort(key=lambda e: int(e.get("seq", 0)))
        if seq[-1].get("event_type") == EVENT_ADD:
            active.append(fp)
    return active
