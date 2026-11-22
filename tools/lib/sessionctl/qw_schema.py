"""QuotaWall 跨包欄名 schema 葉模組（R218 Q1；DES S-12、REQ-QW-63）。

WHY：holder 增欄、park 標記、保溫帳與痕跡事件名，生產端（Q2 keepwarm／Q3 park）與消費端
（Q1 quotawall／seal／Q4 守衛）分屬並行包。欄名字面若各寫一份，改名即靜默不一致；所以十一個跨包
欄名**只住本檔**（AT-QW-61 以原始碼掃描鎖：整串等於欄名的字串常數只准出現在這裡），其他模組只
import 常數與本檔的讀寫函式。本檔只依標準庫（結構上不可能與 quotawall／park 成環）。

時間欄一律存 ISO（aware）字串供人讀，讀取函式回 epoch 秒（float）供算術。
"""
from __future__ import annotations

from datetime import datetime
from typing import NamedTuple

# ── 十一個跨包欄名（AT-QW-61 掃描鎖的對象）
MK_PRIMARY_WAKE_AT = "primary_wake_at"      # park 標記：主載具預定醒來時刻
MK_PRIMARY_SOURCE = "primary_source"        # park 標記：reset（短窗 reset，含 --why）｜at（--at）
MK_BACKUP_FIRE_AT = "backup_fire_at"        # park 標記：備援排程到點（primary＋寬限）
MK_CLOSE_STUCK_WINDOW = "close_stuck_window"  # park 標記：登記當下的殺窗開關
MK_DESKTOP_NOTIFY = "desktop_notify"        # park 標記：登記當下的桌面通知偏好原值
HOLDER_WAKE_AT = "wake_at"                  # holder 列：主載具預定醒來時刻
HOLDER_TARGET_SOURCE = "target_source"      # holder 列：目標來源 park｜reset｜none
EV_SPAWNING = "session_switch_spawning"     # 痕跡事件：spawn 意圖（先於任何 spawn 呼叫）
LEDGER_LAST_PING_PCT = "last_ping_pct"      # 保溫帳：上一次 ping 叫醒時的短窗讀數
LEDGER_LAST_PING_AT = "last_ping_at"        # 保溫帳：上一次 ping 叫醒時刻
LEDGER_PING_COSTS = "ping_costs"            # 保溫帳：相鄰兩次 ping 的讀數差（最近 5 筆）
# ── 不在掃描鎖內的欄名（太通用、掃描會製造假紅）；同樣只由本檔定義
HOLDER_MODE = "mode"
SPAWN_ATTEMPT_KEY = "attempt"               # spawning／失敗列的同 attempt 配對鍵

#: 目標來源的合法值（holder `target_source`）。
TARGET_SOURCES = ("park", "reset", "none")
#: 主載具模式；只有帶目標的 chain／single 才是 S-18 的「主載具憑證」。
MODES = ("chain", "single", "periodic")
#: spawning 意圖的有效期（秒）。＝max(handoff.SPAWN_WAIT_SECONDS 30，park_cli 續跑等待 30)＋60；
#: 測試釘「≥ 兩個等待常數＋30」。WHY 有期限：job 在寫下意圖後、終態列前崩潰＝永久「已交棒」＝
#: 舊窗被告知交棒而新窗沒起來（零駕駛）；逾時且無成功列即可確定 job 已死（S-13，QA3 P2-6）。
SPAWN_INTENT_TTL_SEC = 90
#: 保溫帳 `ping_costs` 保留筆數與計畫取平均的筆數（S-25）。
COSTS_KEEP = 5
COSTS_MEAN_N = 3
_RESERVED_HOLDER_KEYS = frozenset({"schema", "sid", "pid", "proc_start"})


def parse_epoch(text) -> float | None:
    """aware ISO 字串 → epoch 秒；缺／壞／naive ⇒ None（naive 不持久化，跨 DST 靜默錯）。"""
    try:
        when = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return when.timestamp() if when.tzinfo is not None else None


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


# ───────────────────────────────────────────────────────────── holder
class HolderWake(NamedTuple):
    wake_at: float | None
    mode: str | None
    target_source: str | None


def holder_extra(wake_at: float, mode: str, target_source: str) -> dict:
    """`holder.acquire(..., extra=)` 要寫的三欄（生產端 Q2 呼叫）。"""
    return {HOLDER_WAKE_AT: iso(wake_at), HOLDER_MODE: mode, HOLDER_TARGET_SOURCE: target_source}


def holder_wake(row) -> HolderWake | None:
    """從 holder 列讀主載具計畫；列缺席／沒有 wake_at（舊格式）⇒ None（＝維持排除，即舊行為）。"""
    if not isinstance(row, dict):
        return None
    wake = parse_epoch(row.get(HOLDER_WAKE_AT))
    if wake is None:
        return None
    mode, src = row.get(HOLDER_MODE), row.get(HOLDER_TARGET_SOURCE)
    return HolderWake(wake, mode if mode in MODES else None,
                      src if src in TARGET_SOURCES else None)


def safe_holder_extra(extra: dict | None) -> dict:
    """`holder.acquire` 套用前的過濾：不得覆蓋 schema／sid／pid／proc_start。"""
    return {k: v for k, v in (extra or {}).items() if k not in _RESERVED_HOLDER_KEYS}


# ───────────────────────────────────────────────────────────── park 標記
class Primary(NamedTuple):
    wake_at: float | None
    source: str | None          # reset｜at
    backup_fire_at: float | None
    close_stuck_window: bool
    desktop_notify: str


def marker_extra(primary_wake_at: float, primary_source: str, backup_fire_at: float,
                 close_stuck_window: bool, desktop_notify) -> dict:
    """`park` 登記要併進標記的五欄（生產端 Q3 呼叫）；`desktop_notify` 存登記行程環境原值字串。"""
    return {MK_PRIMARY_WAKE_AT: iso(primary_wake_at), MK_PRIMARY_SOURCE: primary_source,
            MK_BACKUP_FIRE_AT: iso(backup_fire_at),
            MK_CLOSE_STUCK_WINDOW: bool(close_stuck_window),
            MK_DESKTOP_NOTIFY: "" if desktop_notify is None else str(desktop_notify)}


def marker_primary(marker) -> Primary:
    """讀標記五欄；缺席（R217 舊標記）⇒ 全空值。"""
    m = marker if isinstance(marker, dict) else {}
    src = m.get(MK_PRIMARY_SOURCE)
    return Primary(parse_epoch(m.get(MK_PRIMARY_WAKE_AT)), src if src in ("reset", "at") else None,
                   parse_epoch(m.get(MK_BACKUP_FIRE_AT)), m.get(MK_CLOSE_STUCK_WINDOW) is True,
                   str(m.get(MK_DESKTOP_NOTIFY) or ""))


# ───────────────────────────────────────────────────────────── spawn 意圖
def intent_live(at, now: float, ttl: float | None = None) -> bool:
    """`at` 起 TTL 內才算「正在開窗」；`at` 解不出或在未來太遠 ⇒ 不算。"""
    stamp = parse_epoch(at)
    return stamp is not None and 0 <= now - stamp <= (SPAWN_INTENT_TTL_SEC if ttl is None else ttl)


def is_failure_row(rec: dict) -> bool:
    """同 attempt 的失敗列：`session_switch_spawned`（既有事件）或 spawning 自身帶 `ok=False`。"""
    return rec.get("ok") is False and rec.get("event") in ("session_switch_spawned", EV_SPAWNING)


# ───────────────────────────────────────────────────────────── 保溫帳（S-25）
def ping_costs(row) -> list[float]:
    """保溫帳 `ping_costs`（最近 5 筆，舊→新）；缺席／壞值 ⇒ []。非有限或負值整筆丟棄。"""
    raw = row.get(LEDGER_PING_COSTS) if isinstance(row, dict) else None
    if not isinstance(raw, list):
        return []
    out = [float(x) for x in raw if type(x) in (int, float) and 0 <= x < float("inf")]
    return out[-COSTS_KEEP:]


def last_ping(row) -> tuple[float, float] | None:
    """`(last_ping_pct, last_ping_at 的 epoch)`；任一缺 ⇒ None（歸零後或從未 ping）。"""
    if not isinstance(row, dict):
        return None
    pct, at = row.get(LEDGER_LAST_PING_PCT), parse_epoch(row.get(LEDGER_LAST_PING_AT))
    return (float(pct), at) if type(pct) in (int, float) and at is not None else None


def ledger_extra(last_pct: float | None, last_at: float | None, costs) -> dict:
    """保溫帳三欄（生產端 Q2 併進 `record_ping` 的列）；`last_*` 為 None ⇒ 寫空（＝清空）。"""
    return {LEDGER_LAST_PING_PCT: last_pct,
            LEDGER_LAST_PING_AT: None if last_at is None else iso(last_at),
            LEDGER_PING_COSTS: [float(c) for c in list(costs)[-COSTS_KEEP:]]}


def append_cost(costs, delta: float) -> list[float]:
    """追加一筆實測 Δ，只留最近 `COSTS_KEEP` 筆。"""
    return [*list(costs), float(delta)][-COSTS_KEEP:]


def measured_mean(costs) -> float | None:
    """近 `COSTS_MEAN_N` 筆平均；沒有任何實測 ⇒ None。"""
    recent = list(costs)[-COSTS_MEAN_N:]
    return sum(recent) / len(recent) if recent else None
