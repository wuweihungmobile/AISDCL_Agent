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
#: `auto-continuation` 的字面只有一個家：`quota_limits.RESUME_ORIGIN`。
_CONVERSATION_ORIGINS = frozenset({"human", quota_limits.RESUME_ORIGIN})

#: 切斷通知的內文標記；「Usage limit reset · continuing automatically」（沒有 `at`）是續接通知。
_CUTOFF_MARK = "continuing automatically at"
_RESET_NOTICE_PREFIX = "Usage limit reset"

#: `usageLimitNote` 的兩個真機值（harness 2.1.303／304；語料 15 筆＝8＋7）：`wrap_up`＝寬限提示；
#: `release`＝harness 在 auto-continuation 之後 9～18 ms 附上的續接訊號（isMeta、turnCompanion、
#: 無 origin；字面住 `quota_limits.NOTE_RELEASE`，判準＝`quota_limits.is_resume_record`）。
#: 其餘值一律忽略（寧可不叫醒）。
_NOTE_WRAP_UP = "wrap_up"

#: 判「另有駕駛」的鏈頭門檻：spawn 之後同一份逐字稿出現幾條以上的鏈頭（見 `chain_heads_after`）。
OTHER_DRIVER_HEADS = 2


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


def _driver_kind(record: dict) -> str:
    """非合成的對話記錄回其種類（`assistant`／`human`／`auto-continuation`）；其餘回 `""`。

    限額記錄（`<synthetic>` assistant）本身不算有人在動：它是 harness 對撞線的回應，不是誰的作為。
    """
    if record.get("type") == "assistant":
        message = record.get("message")
        model = message.get("model") if isinstance(message, dict) else None
        return "" if model == quota_limits.SYNTHETIC_MODEL else "assistant"
    origin = _origin_kind(record)
    human = record.get("type") == "user" and isinstance(origin, str)
    return origin if human and origin in _CONVERSATION_ORIGINS else ""


def driver_after(transcript: Path | None, since_epoch: float, now: datetime) -> dict | None:
    """`since_epoch` 之後（至 `now` 為止）第一筆**非合成**的對話記錄 `{"timestamp", "kind"}`；
    沒有回 `None`。

    「有沒有別的駕駛」的**單一判準**（DEF-200-564；哨兵 `sentinel_decide`、`_run_resume` 的 spawn
    前閘、重放探針共用）。掃描面與 `newest_conversation_at` 同一批檔（主檔＋近 24 小時的 subagent
    檔：互動視窗把活派給 subagent 時主檔可能數分鐘不動）。`now` 是觀察時刻上界（生產路徑傳現在；
    重放探針傳 `--now`）。`kind`＝`assistant`（真 model）／`human`／`auto-continuation`。
    """
    if transcript is None or not transcript.is_file():
        return None
    upper, best = now.timestamp(), None
    for path in quota_limits.session_transcripts(transcript):
        for record in _records(path, '"assistant"', '"origin"'):
            kind, stamp = _driver_kind(record), _epoch(record.get("timestamp"))
            if kind and stamp is not None and since_epoch < stamp <= upper and (
                    best is None or stamp < best[0]):
                best = (stamp, str(record["timestamp"]), kind)
    return None if best is None else {"timestamp": best[1], "kind": best[2]}


def live_driver(transcript: Path | None, now: datetime, event: dict | None = None) -> dict | None:
    """「此刻有別的駕駛」＝一個巡邏間隔內（`HALT_QUIESCE_SECONDS`，與寬限提示「不叫醒」同一把尺）、
    且在撞線事件（有給才算）之後有非合成對話記錄（`driver_after`）。

    只看「事件之後」不夠：戳了死視窗就走的人類記錄會永遠擋住哨兵的續跑。只看「近期」也不夠：撞線前
    的正常活動不是事件之後的駕駛。兩條取交集（`since`＝兩者較晚者）。`event` 也可傳 `spawn_anchor`
    的錨（帶 `grace_s` 時錨再往後挪那麼多秒）。
    """
    floor, anchor = now.timestamp() - quota_messages.HALT_QUIESCE_SECONDS, event or {}
    stamp = _epoch(anchor.get("timestamp"))
    since = floor if stamp is None else max(floor, stamp + float(anchor.get("grace_s") or 0))
    return driver_after(transcript, since, now)


#: relay 前一棒收窗後仍可能落盤的尾巴（秒）：錨之後這麼短的記錄屬 leg 自己，不算另一駕駛。
RELAY_TAIL_GRACE_SECONDS = 2.0


def spawn_anchor(transcript: Path | None, state: dict) -> dict | None:
    """D5（`_run_resume` spawn 前閘）的錨 `{timestamp, source[, grace_s]}`（DEF-200-564 修復棒二）。

    兩個候選取**較晚者**（QA 複審 R2：過期的 prev_end 不得遮住較新的撞線）：
    ① `state["relay_prev_end"]`（relay 前一棒收窗時刻，`settle_window` 在排下一窗前寫入、
    隨狀態塊落盤；`grace_s` 讓 leg 收尾落盤的尾巴不算別人）；
    ② 未處理撞線事件的 timestamp（與哨兵撞線分支同一把錨）。
    兩者皆無 ⇒ `None`（退回「近一個巡邏間隔」窗：寬限／halt 路徑，以及修前武裝、
    狀態塊沒有 prev_end 的進行中 relay）。

    為何要錨：無頭 leg 與互動視窗寫同一份逐字稿，relay 下一窗在收窗後 `RESET_SKEW_SECONDS`（120 s）
    起、遠小於一個巡邏間隔 ⇒ 無錨時前一棒自己的記錄被當成另一駕駛，第二棒必被拒；首棒撞線前緊貼
    限額記錄的最後一則真回應同理。
    """
    prev = state.get("relay_prev_end")
    event = quota_limits.unhandled_limit_event(transcript) if transcript is not None and transcript.is_file() else None  # noqa: E501
    cands = [a for a in (
        {"timestamp": prev, "source": "relay_prev_end", "grace_s": RELAY_TAIL_GRACE_SECONDS} if _epoch(prev) is not None else None,  # noqa: E501
        {"timestamp": event["timestamp"], "source": "limit_event"} if event else None) if a]
    return max(cands, key=lambda a: _epoch(a["timestamp"]) or 0.0) if cands else None


def driver_verdict(event: dict | None, driver: dict | None, now: datetime) -> dict | None:
    """撞線事件之後另有駕駛 ⇒ `patrol`（由它接手、續巡；鍵集合與 `grace_verdict` 同形）；
    `None`＝沒有，呼叫端照舊（`sentinel_decide` 撞線分支在 reset 判斷之前先問它）。"""
    if driver is None:
        return None
    seen, hit = _epoch(driver.get("timestamp")), _epoch((event or {}).get("timestamp"))
    after = f"撞線後 {seen - hit:.0f}s " if seen is not None and hit is not None else "撞線後"
    return {"action": "patrol", "at": now + timedelta(seconds=quota_messages.HALT_QUIESCE_SECONDS),
            "reason": f"{after}已有另一駕駛的對話記錄（{driver['kind']}，{driver['timestamp']}）"
                      "⇒ 由它接手，續巡、不叫醒（防雙駕駛；本次零 token）"}


def chain_heads_after(transcript: Path, since_epoch: float) -> int:
    """`since_epoch` 之後新增的**鏈頭**數；一條鏈＝一個駕駛的對話接續（DEF-200-565）。

    鏈頭＝該時刻後的 uuid 記錄裡，`parentUuid`（compact 邊界的 `parentUuid` 為空、改取
    `logicalParentUuid`）不指向「該時刻後任何記錄」者。單一駕駛從 spawn 前的最後一筆接續寫
    ⇒ 恰 1 條；互動視窗也在寫同一份檔 ⇒ 兩條從 spawn 前記錄分岔、各自續寫 ⇒ ≥2 條
    （`OTHER_DRIVER_HEADS`）。
    只看主檔（subagent 檔有自己的鏈與 `isSidechain`）。真機佐證：事故 e9f8e2cb 兩支 leg 窗各 2 條，
    本機 117 支單駕駛無頭 leg 一律 1 條。檔案缺席／讀不動 ⇒ 0（量不到≠有人）。
    """
    parents: dict[str, object] = {}
    for record in _records(transcript, '"uuid"'):
        uid, stamp = record.get("uuid"), _epoch(record.get("timestamp"))
        if isinstance(uid, str) and stamp is not None and stamp > since_epoch and (
                record.get("isSidechain") is not True):
            parent = record.get("parentUuid")
            parents[uid] = record.get("logicalParentUuid") if parent is None else parent
    return sum(1 for parent in parents.values()
               if not isinstance(parent, str) or parent not in parents)


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
        elif quota_limits.is_resume_record(record):
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
