"""improving_113 W2：無人續跑每個窗「醒來的第一個請求」成本落帳（PRD 喚醒成本記錄）。

資料全部來自本機逐字稿（零 token、零網路）。取值／組 record 是純函式，讀檔與 append 痕跡
分開；本檔不得 import 額度閘（防成環；AST 鎖＝tools/tests/test_resume_cost.py）。

定位法：planner 不記 spawn 時刻（守衛面零改動），改以逐字稿內「最後一筆早於 reset_at 的
真 assistant」為錨，其後第一筆真 assistant 的 message.usage 就是本窗首個請求。真 assistant
＝type 為 assistant、model 非合成佔位、usage 為 dict（取值慣例同 hook 的 scan_transcript）。
record 的 model 欄取自同一筆 assistant 的 message.model 原字串；缺鍵、空字串、非字串一律 None
（不猜、不拿空字串頂替；合成佔位本就不是真 assistant，故不會出現在這一欄）。型別契約在
build_record 這個唯一出口守，取值函式只回原始事實。

誠實劃界：
 ① 量不到一律 measured 為假、數值欄為 None，絕不寫 0——合成佔位與全零 usage 都不算量到。
 ② 同一 reset 週期的第二個起接力窗（relay_seq>=1）以 reset_at 為錨會抓到第一窗的首筆，
    故誠實標 measured 為假（reason=relay-chain-anchor），不拿別窗的數字冒充。
 ③ pct_before／pct_after 須兩者皆有值才填（`_run_resume` 前後各讀一次額度快取，不連網）；缺任一 ⇒
    兩欄皆 None，並以 `pct_note`「量不到：…」＋`pct_checked_at` 說明（收窗絕不為它外呼量測）。
"""
from __future__ import annotations

import contextlib
import json
from datetime import datetime
from pathlib import Path

import endurance_env
import quota_ledger
from quota_limits import SYNTHETIC_MODEL

#: 佔用 context 的三個 usage 欄（與 hook 同三欄；hook 是守衛面不動，故此處自持一份）。
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
#: 痕跡檔名；落在持久目錄 endurance_env.trace_dir() 底下（沒觸發＝檔不長大，可偵測）。
RECORD_NAME = "autosdd_resume_cost.jsonl"


def _epoch(raw: object) -> float | None:
    """ISO 時間字串（Z 後綴或帶 offset）→ epoch 秒；解不出回 None。"""
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _assistants(source):
    """真 assistant 記錄 (epoch, 原時間戳, message)，依檔案順序；source＝逐行 iterable 或路徑。"""
    opened = (Path(source).open(encoding="utf-8", errors="replace")
              if isinstance(source, (str, Path)) else contextlib.nullcontext(source))
    try:
        with opened as lines:
            for line in lines:
                try:
                    rec = json.loads(line) if '"assistant"' in line else None
                except ValueError:
                    continue
                msg = rec.get("message") if isinstance(rec, dict) else None
                if (not isinstance(msg, dict) or rec.get("type") != "assistant"
                        or msg.get("model") == SYNTHETIC_MODEL):
                    continue
                epoch, usage = _epoch(rec.get("timestamp")), msg.get("usage")
                if epoch is not None and isinstance(usage, dict):
                    yield epoch, str(rec["timestamp"]), msg
    except OSError:
        return


def last_assistant_before(source, cutoff: object) -> str | None:
    """最後一筆早於 cutoff 的真 assistant 的時間戳；沒有（或 cutoff 解不出）回 None。"""
    limit = _epoch(cutoff)
    if limit is None:
        return None
    hits = [(epoch, stamp) for epoch, stamp, _msg in _assistants(source) if epoch < limit]
    return max(hits)[1] if hits else None


def first_assistant_usage_after(source, after_ts: object) -> dict | None:
    """第一筆晚於 after_ts 的真 assistant，回 {"ts": 時間戳, "model": 原值, <三個 usage 欄>: 原值}。

    after_ts 為 None＝不設下界；非空卻解不出時刻回 None（寧缺勿猜）。沒有符合者回 None。
    """
    floor = float("-inf") if after_ts is None else _epoch(after_ts)
    if floor is None:
        return None
    for epoch, stamp, msg in _assistants(source):
        if epoch > floor:
            return {"ts": stamp, "model": msg.get("model"),
                    **{k: msg["usage"].get(k) for k in USAGE_KEYS}}
    return None


def pct_lost_note(pct_before: object, pct_after: object) -> str | None:
    """前後讀數有缺 ⇒ 「量不到：<哪一側>（原因）」；兩者皆有 ⇒ `None`（成本帳與結局檔共用）。"""
    lost = [n for n, p in (("前讀數", pct_before), ("後讀數", pct_after))
            if type(p) not in (int, float)]
    return (f"量不到：{'、'.join(lost)}（額度快取缺、過期或無五小時軸；收窗不外呼量測）"
            if lost else None)


def build_record(session_id: str, relay_seq: int | None, usage: dict | None, *, reason: str = "",
                 pct_before: float | None = None, pct_after: float | None = None,
                 recorded_at: str = "", pct_before_at: str | None = None,
                 pct_after_at: str | None = None) -> dict:
    """組一行成本 record（純函式）。usage＝first_assistant_usage_after 的回傳或 None。
    `pct_*_at`＝各自讀數的量測時刻（兩次讀數都有才填，與 pct 同一條規則）。"""
    raw = usage or {}
    model = raw.get("model")
    # type() 比對而非 isinstance：bool 是 int 的子類，True 會被收成 1（同 quota_gate 的紀律）。
    got = {k: raw[k] if type(raw.get(k)) is int else None for k in USAGE_KEYS}
    measured = any(got.values())  # 全 None／全 0 都不是量到（合成佔位長這樣）
    why = "" if measured else (reason or ("no-usage-count" if usage else "no-assistant-usage"))
    both = all(type(p) in (int, float) for p in (pct_before, pct_after))  # 兩次讀數皆有才填
    # 量不到要**說出來**（主控裁決：收窗時讀不到新鮮讀數就記 None＋原因，絕不為它外呼量測——
    # 無人窗口不得多燒額度）；`pct_checked_at`＝本列檢查時刻，不是額度量測時刻（量不到就沒有後者）。
    note = pct_lost_note(pct_before, pct_after)
    return {"session_id": session_id, "relay_seq": relay_seq, "measured": measured,
            "pct_note": note, "pct_checked_at": recorded_at if note else None,
            "first_assistant_ts": raw.get("ts"),
            "model": model if isinstance(model, str) and model else None,
            **(got if measured else dict.fromkeys(USAGE_KEYS)),
            "pct_before": pct_before if both else None, "pct_after": pct_after if both else None,
            "pct_before_at": pct_before_at if both else None,
            "pct_after_at": pct_after_at if both else None,
            "reason": why or None, "recorded_at": recorded_at}


def append_cost_record(record: dict, path: Path) -> bool:
    """append 一行 JSON（走 quota_ledger 的單次 os.write）；父目錄自建；寫不進去回 False 不拋。"""
    path = Path(path)
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
    return quota_ledger.append_record(path, record)


def _spawn_at(log: object) -> str | None:
    """本窗 spawn 時刻＝planner 於 subprocess.run 前落的最後一筆 relay_snapshot_before 的 at。"""
    last = None
    with contextlib.suppress(OSError):
        for line in Path(str(log)).open(encoding="utf-8", errors="replace"):
            if '"relay_snapshot_before"' in line:
                with contextlib.suppress(ValueError, AttributeError):
                    last = json.loads(line).get("at") or last
    return last


def _locate(state: dict, relay_seq: int, log: object = None) -> tuple[dict | None, str]:
    """(本窗首個請求的 usage 或 None, 量不到的原因)。"""
    source = str(state.get("transcript") or "")
    if not Path(source).is_file():  # 空字串＝Path(".")＝目錄，同樣判缺席
        return None, "transcript-missing"
    if spawn := (_spawn_at(log) if log else None):  # 接力窗與 reset_at 為空的 probe 路徑都靠它
        return first_assistant_usage_after(source, spawn), ""
    if relay_seq >= 1:
        return None, "relay-chain-anchor"
    anchor = last_assistant_before(source, state.get("reset_at"))
    return (first_assistant_usage_after(source, anchor), "") if anchor else (None, "no-anchor")


_FIVE_HOUR_KINDS = ("session", "five_hour", "5h")


def five_hour_reading(quota_gate: object, now: datetime | None = None) -> tuple[float | None, str | None]:  # noqa: E501
    """`(五小時軸 pct, 量測時刻)`：只讀額度快取（不連網）；快取不可用／無該軸 ⇒ `(None, None)`
    （量不到不猜）。`quota_gate` 由呼叫端注入（planner 傳自己的），本檔不 import 它。"""
    try:
        state = quota_gate.read_quota(now or datetime.now().astimezone())
        axis = next((a for a in state.axes if a.kind in _FIVE_HOUR_KINDS), None)
    except Exception:  # noqa: BLE001 — 旁路取數不得讓 spawn 失敗
        return None, None
    return (float(axis.pct), state.measured_at) if axis is not None else (None, None)


def record_window(state: dict, path: Path | None = None, log: object = None) -> dict:
    """settle_window 的單一接線點：量本窗首個請求並落一行；永不拋（旁路落帳不得讓收窗失敗）。
    五小時軸前後讀數取自 `state["pct_before"／"pct_after"]`（`_run_resume` 前後各讀一次，各自帶
    `…_at` 量測時刻）；缺任一 ⇒ 兩欄皆 None（既有「兩者皆有才填」規則）。"""
    sid, seq, stamp = str(state.get("session_id") or ""), None, ""
    try:
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        seq = int(state.get("relay_seq") or 0)
        usage, why = _locate(state, seq, log)
        rec = build_record(sid, seq, usage, reason=why, recorded_at=stamp,
                           pct_before=state.get("pct_before"), pct_after=state.get("pct_after"),
                           pct_before_at=state.get("pct_before_at"),
                           pct_after_at=state.get("pct_after_at"))
    except Exception as exc:  # noqa: BLE001 — 量不到也要留一行說明，不得讓 settle_window 失敗
        rec = build_record(sid, seq, None, reason=f"error:{type(exc).__name__}", recorded_at=stamp)
    with contextlib.suppress(Exception):  # 落帳失敗同樣只吞不拋（痕跡缺一行＝可偵測）
        append_cost_record(rec, path or endurance_env.trace_dir() / RECORD_NAME)
    return rec
