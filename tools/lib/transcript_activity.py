"""哨兵的「session 還活著」判準＝**對話記錄**，與 harness 限額記錄的辨識（DEF-200-560／562）。

WHY（2026-10-21 事故；設計全文＝ADR-XPLAT-004 §2.10）
----------------------------------------------------
主控依 harness 寬限提示自願收尾後，哨兵整晚 16 次巡邏全判 `patrol`（「逐字稿 N 秒前仍有更新
⇒ session 還活著」），額度回來了卻沒有人叫醒它。成因有二：

① 「活著」讀的是**檔案 mtime**（`quota_limits.newest_activity_at`），而 harness 在 session
   閒置時仍每小時追加無 timestamp 的 `cost-state`／`last-prompt`／`file-history-snapshot`，
   收尾後還寫 `system/away_summary` ⇒ mtime 永遠像剛更新過（DEF-200-560）。本檔改以**對話
   記錄**的 timestamp 判：`type=assistant`，或 `type=user` 且 `origin.kind` 屬人類／
   auto-continuation。🔴 `isMeta` 不是判準：auto-continuation 那筆自己就是 `isMeta:true`，
   而寬限提示（同為 `isMeta:true`）沒有 `origin`——判準看 `origin.kind`，不看 `isMeta`。
② harness 2.1.303 起把額度撞線寫成三種新記錄，而偵測面（`quota_limits.
   unhandled_limit_event`）只認「`type=assistant` ＋ `model=<synthetic>`」（DEF-200-562）：
   寬限提示（user，`usageLimitNote:"wrap_up"`）、切斷通知（system，內文 `continuing
   automatically at <時刻>`）、續接記錄（auto-continuation／`Usage limit reset`／
   `usageLimitNote:"release"`）。它們由本檔以**獨立通道**辨識，不塞進既有事件那條路：寬限提示
   沒有 reset 時刻，塞進去會走到「解不出 reset ⇒ escalate ⇒ 哨兵自拆」。
   🔴 `usageLimitNote` 有兩個真機值（語料 15 筆＝8 `wrap_up`＋7 `release`）：`release` 是
   harness 在 auto-continuation 之後 9～18 ms 附上的「[Earlier usage-limit notes no longer
   apply…]」（isMeta、turnCompanion、無 origin）＝**續接訊號、不是提示**。把任何帶該鍵的記錄
   都當提示，會在 harness 剛自動續接、續跑回合於寬限期內結束並靜止後誤判 probe（F-1，QA 鏡審
   P1）。未知值一律忽略（寧可不叫醒）。

🔴 相依方向：本檔只 import `quota_limits`／`quota_messages`，**不得**被它們、`quota_gate` 或
hook 檔 import（單向；消費者＝`tools/session_resume_planner.py` 與測試）。`tools/lib/*` 一律
裸名 import。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import quota_limits  # noqa: E402
import quota_messages  # noqa: E402

#: 寬限期：harness 在寬限提示之後允許的收尾時間沒有契約值（實測 40 s／91 s），取一個巡邏間隔。
#: 🔴 這個數字是**挑的、不是量出來的**。與 `quota_messages.HALT_QUIESCE_SECONDS` 同值但語意不同
#: （那個是巡邏間隔、這個是收尾容許）：兩檔不互相取值，由 parity 測試釘住同值。
GRACE_ALLOWANCE_SECONDS = 900

#: `grace_verdict` 的 `arm_reset` 寫進狀態塊的 `reset_source`，須登記於
#: `relay_machine.RESET_SOURCES`（`relay_problems` 以它判「不是觀測值 ⇒ 不准用來武裝」）。
#: 字面在兩處（同 `halt-marker`），由 `test_wake_chain_halt_r278.py` 的橋接測試綁在一起。
RESET_SOURCE = "harness-cutoff-notice"

#: 算「對話」的 user 記錄來源。`peer`／`task-notification` 等其餘來源不是續跑證據。
_CONVERSATION_ORIGINS = frozenset({"human", "auto-continuation"})

#: 切斷通知的內文標記；「Usage limit reset · continuing automatically」（沒有 `at`）是續接通知。
_CUTOFF_MARK = "continuing automatically at"
_RESET_NOTICE_PREFIX = "Usage limit reset"

#: `usageLimitNote` 的兩個真機值（harness 2.1.303／304；語料 15 筆＝8＋7）：`wrap_up`＝寬限提示；
#: `release`＝harness 在 auto-continuation 之後 9～18 ms 附上的續接訊號（isMeta、turnCompanion、
#: 無 origin）。其餘值一律忽略（寧可不叫醒）。
_NOTE_WRAP_UP, _NOTE_RELEASE = "wrap_up", "release"


def _epoch(raw: object) -> float | None:
    """ISO 時間戳→epoch 秒；認不出來回 `None`（只做相減，不持久化）。"""
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _records(path: Path, *needles: str):
    """該檔的 JSON 記錄（dict）。壞行跳過（逐字稿常有半截尾行）；`needles` 非空時只解析含任一
    字面的行——逐字稿動輒數十 MB，絕大多數行（attachment／api-request-blob）與判準無關。"""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if needles and not any(needle in line for needle in needles):
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict):
                    yield record
    except OSError:
        return


def _origin_kind(record: dict) -> object:
    origin = record.get("origin")
    return origin.get("kind") if isinstance(origin, dict) else None


def _is_conversation(record: dict) -> bool:
    kind = record.get("type")
    return kind == "assistant" or (
        kind == "user" and _origin_kind(record) in _CONVERSATION_ORIGINS)


def newest_conversation_at(paths: list[Path]) -> float | None:
    """這批逐字稿裡**對話記錄**的最新 timestamp（epoch 秒）；一筆都沒有回 `None`。

    對話記錄＝`type=assistant`（含 subagent 檔），或 `type=user` 且 `origin.kind` 為 `human`／
    `auto-continuation`。**不算**：寬限提示（`isMeta` user、無 `origin`）、tool_result 型
    user、`type=system`（含 `away_summary`）、`attachment`、無 timestamp 的 `cost-state`／
    `last-prompt`／`file-history-snapshot`、`queue-operation`。`None` 讓呼叫端傳 `idle=None`
    ＝「從來沒有被建立」那一支。
    """
    best: float | None = None
    for path in paths:
        for record in _records(path, '"assistant"', '"origin"'):
            if not _is_conversation(record):
                continue
            stamp = _epoch(record.get("timestamp"))
            if stamp is not None and (best is None or stamp > best):
                best = stamp
    return best


def usage_limit_signals(main_transcript: Path) -> dict:
    """主逐字稿裡 harness 2.1.303 的三種限額記錄（只讀**主**檔：寬限提示自述 subagent 收不到）。

    回 `{"note_at", "cutoff_text", "cutoff_at", "reset_notice_at"}`，缺席的欄位為 `""`，皆取
    該類**最後一筆**（以 timestamp 為準）：`note_at`＝`usageLimitNote == "wrap_up"` 的 user
    記錄（**只認這個值**，其他值一律忽略＝寧可不叫醒）；`cutoff_*`＝內文含
    `continuing automatically at` 的 `type=system` 記錄；`reset_notice_at`＝
    `origin.kind=="auto-continuation"` 或 `usageLimitNote == "release"` 的 user 記錄（`release`
    是 harness 於 auto-continuation 後 9～18 ms 附上的續接訊號，**不是提示**），或內文以
    `Usage limit reset` 起頭的 system 記錄。
    """
    best: dict[str, tuple[float, str, str]] = {}  # 欄位 → (epoch, 原 timestamp, 內文)

    def keep(field: str, record: dict, text: str = "") -> None:
        stamp = _epoch(record.get("timestamp"))
        if stamp is not None and (field not in best or stamp > best[field][0]):
            best[field] = (stamp, str(record["timestamp"]), text)

    for record in _records(main_transcript, "usageLimitNote", _CUTOFF_MARK,
                           _RESET_NOTICE_PREFIX, "auto-continuation"):
        kind, content = record.get("type"), record.get("content")
        note = record.get("usageLimitNote")
        if kind == "user" and note == _NOTE_WRAP_UP:
            keep("note_at", record)
        elif kind == "user" and (
                note == _NOTE_RELEASE or _origin_kind(record) == "auto-continuation"):
            keep("reset_notice_at", record)
        elif kind == "system" and isinstance(content, str):
            if _CUTOFF_MARK in content:
                keep("cutoff_at", record, content)
            elif content.startswith(_RESET_NOTICE_PREFIX):
                keep("reset_notice_at", record)
    empty = (0.0, "", "")
    return {"note_at": best.get("note_at", empty)[1],
            "cutoff_text": best.get("cutoff_at", empty)[2],
            "cutoff_at": best.get("cutoff_at", empty)[1],
            "reset_notice_at": best.get("reset_notice_at", empty)[1]}


def _continue_at(signals: dict, note_ts: float, now: datetime) -> datetime | None:
    """切斷通知自報的下次續接時刻；沒有、早於寬限提示、或解不出時刻都回 `None`。

    `continuing automatically at 12:10am` 是 harness 在**同一台機器**上以本地時間算繪的牆上
    時刻（無日期、無時區）⇒ 以切斷記錄當下的時刻、用 `now` 的時區解成「下一個尚未發生的」
    那一刻（`quota_limits.parse_reset_at`）。
    """
    cut_ts = _epoch(signals["cutoff_at"])
    if cut_ts is None or cut_ts <= note_ts:
        return None
    return quota_limits.parse_reset_at(signals["cutoff_text"],
                                       datetime.fromtimestamp(cut_ts, now.tzinfo))


def unhandled_grace_note(main_transcript: Path, paths: list[Path], now: datetime) -> dict | None:
    """還沒被處理的 harness 寬限提示；`None`＝沒有、或已被處理。

    已處理的兩個充分條件：(i) 寬限提示之後有續接記錄（auto-continuation／`release`／`Usage
    limit reset`）——harness 自己接上了；(ii) 寬限期（`GRACE_ALLOWANCE_SECONDS`）之後仍有對話記錄
    ——人或喚醒已續跑。寬限期**之內**的對話是主控依提示做的收尾，不算已處理。回
    `{"timestamp", "continue_at", "source"}`；`continue_at` 見 `_continue_at`（`now` 只
    提供時區框架）。
    """
    signals = usage_limit_signals(main_transcript)
    note_ts = _epoch(signals["note_at"])
    if note_ts is None:
        return None
    reset_ts = _epoch(signals["reset_notice_at"])
    if reset_ts is not None and reset_ts > note_ts:
        return None
    last = newest_conversation_at(paths)
    if last is not None and last > note_ts + GRACE_ALLOWANCE_SECONDS:
        return None
    return {"timestamp": signals["note_at"], "continue_at": _continue_at(signals, note_ts, now),
            "source": "harness-usage-limit-note"}


def grace_verdict(note: dict | None, idle_seconds: float | None, now: datetime) -> dict | None:
    """寬限提示 → 既有 `arm_reset`／`patrol`／`probe` 判決（純函式；鍵集合與 `sentinel_decide`
    既有分支同形）。

    `None`＝提示不適用（呼叫端落回 idle 判定）。harness 自報的續接時刻（兌現時刻＝它＋
    `HALT_RESET_SKEW_SECONDS`）還沒到 ⇒ 排到那一刻；已到或沒有時刻 ⇒ 對話靜止滿一個巡邏
    間隔才探測，未滿＝人或 harness 仍在動，不叫醒（防雙窗）。`idle_seconds=None`（量不到）
    與 `halt_verdict` 同樣走 probe。
    """
    if note is None:
        return None
    skew = timedelta(seconds=quota_messages.HALT_RESET_SKEW_SECONDS)
    quiesce = quota_messages.HALT_QUIESCE_SECONDS
    resume_at, stamp = note.get("continue_at"), note["timestamp"]
    if resume_at is not None and resume_at + skew > now:
        return {"action": "arm_reset", "at": resume_at + skew, "reset_at": resume_at,
                "reset_source": RESET_SOURCE,
                "reason": f"偵測到 harness 切斷通知；它自報的續接時刻 {resume_at} 尚未到 ⇒ "
                          "要求排程器改在那個時刻醒（本次零 token）；醒來若 harness 已自行續接"
                          "就續巡、不叫醒"}
    if idle_seconds is not None and idle_seconds < quiesce:
        return {"action": "patrol", "at": now + timedelta(seconds=quiesce),
                "reason": f"偵測到 harness 寬限提示（{stamp}），對話靜止 {idle_seconds:.0f}s"
                          f"（< {quiesce}s 一個巡邏間隔）⇒ 不叫醒（防雙窗），續巡、下一輪"
                          "再判（本次零 token）"}
    return {"action": "probe", "at": None,
            "reason": f"偵測到 harness 寬限提示（{stamp}）後對話已靜止 ≥ {quiesce}s、且沒有 "
                      "reset／續接通知 ⇒ 花一次探測確認額度回來了沒"}


def conversation_view(transcript: Path, now: datetime) -> tuple[float | None, dict | None]:
    """planner 每次巡邏的唯一入口：`(對話靜止秒數, 未處理的寬限提示)`。

    逐字稿不存在 ⇒ `(None, None)`。掃描面與 `quota_limits.unhandled_limit_event` 同一批檔
    （主檔＋近 24 小時的 subagent 檔）。靜止秒數取 `max(0, now - 最新對話)`；一筆對話都沒有
    ⇒ `None`（見 `newest_conversation_at`）。
    """
    if not transcript.is_file():
        return None, None
    paths = quota_limits.session_transcripts(transcript)
    stamp = newest_conversation_at(paths)
    idle = None if stamp is None else max(0.0, now.timestamp() - stamp)
    return idle, unhandled_grace_note(transcript, paths, now)
