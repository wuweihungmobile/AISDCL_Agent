"""halt 標記檔（DEF-200-278／INV-H1c）的落盤與讀回——從 `quota_gate` 抽出的三支函式。"""
# 🔴 為何抽出：`quota_gate.py` 是 hub tier（預算 500，餘裕 0）；配速床接線（ADR-XPLAT-004 §2.15）
# 需要在 gate 內加數行。依「不調高預算、先抽出等量程式」原則，把最獨立的一族（標記檔路徑／寫／讀，
# 只依賴 `endurance_env` 的目錄 SSOT 與 json）搬到這裡；`quota_gate` 以單行 re-export，既有消費端
# （`quota_gate.write_halt_marker` 等，含 sentinel、planner、測試）零改動。
# 🔴 刻意沒有第二份路徑知識：目錄一律 `endurance_env.trace_dir()`（同哨兵痕跡的家）。
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import endurance_env


def halt_marker_path(sid: str) -> Path:
    """DEF-200-278／INV-H1c 落盤處，SSOT＝`endurance_env.trace_dir()`（同哨兵痕跡的家）。"""
    return endurance_env.trace_dir() / f"halt_{sid}.json"


def write_halt_marker(sid: str, data: dict) -> Path:
    """落一份持久 halt 標記，供哨兵下一輪巡邏讀（`halt_verdict()`）。寫檔失敗吞掉——
    標記是輔助憑證而非安全煞車（fail-open 是 P0）。"""
    path = halt_marker_path(sid)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        pass
    return path


def read_halt_marker(sid: str) -> dict | None:
    """讀不出來（沒有 sid／檔不存在／壞 JSON）一律回 `None`，呼叫端據此落回既有判定。"""
    if not sid:
        return None
    try:
        return json.loads(halt_marker_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

def halt_marker_probe_path(sid: str) -> Path:
    """halt 標記路徑，但**不**觸發 `endurance_env.trace_dir()` 的 `mkdir` 副作用（D23：
    `--check` 是「不寫檔」的既有契約——`PlannerCliTest.test_check_prints_usage_and_
    writes_nothing` 釘住）。解析規則與 `endurance_env._durable_dir_status()` 同源但只讀不建。
    QVD §9：自 `session_resume_planner._halt_marker_probe_path` 純搬移（騰 guardrail_cli 餘裕）。"""
    import os  # noqa: PLC0415

    override = os.environ.get(endurance_env.TRACE_DIR_ENV, "").strip()
    root = Path(override) if override else Path.home().joinpath(*endurance_env.TRACE_HOME_PARTS)
    return root / f"halt_{sid}.json"


def cache_account() -> str | None:
    """額度快取最近一次量到的帳號指紋（`account_key`；PRD R-4.1.7-1 寫入端用）。只讀身分欄、不判新鮮度
    （指紋是「最近一次伺服器回應的帳號」，不是讀數）；讀不到／缺鍵 ⇒ `None`。"""
    try:
        import quota_meter  # noqa: PLC0415 — 快取路徑 SSOT 在 meter（同 `quota_gate.quota_cache_path`）

        key = json.loads(quota_meter.cache_path().read_text(encoding="utf-8")).get("account_key")
    except Exception:  # noqa: BLE001 — 量不到＝None（呼叫端寫 null 並出聲）
        return None
    return key if isinstance(key, str) and key else None


def unmeasured_account_note(what: str) -> str:
    """R-4.1.7-1「量不到寫空值並出聲」的唯一文案。"""
    return f"ℹ️ {what}帳號指紋量不到 ⇒ 寫入 account=null（下一次量到帳號時依 R-4.1.7-5 判歸屬）\n"


def _aware(raw):
    import quota_messages  # noqa: PLC0415 — lazy：quota_messages 反向 re-export 本檔

    return quota_messages._aware(raw)  # noqa: SLF001 — 同一解析，不寫第二份


def halt_resets_at(decision):
    import quota_messages  # noqa: PLC0415

    return quota_messages.halt_resets_at(decision)


def _reset_skew() -> int:
    import quota_messages  # noqa: PLC0415

    return quota_messages.HALT_RESET_SKEW_SECONDS


# 🔴 DEF-200-274 第十輪／SA-04（反駁者在現行程式碼上重現）：`halt_verdict()` 判「標記
# 已過期（session 自行續跑過）」此前是零容忍嚴格比較——標記的 `at` 是 hook 處理當下的
# 牆鐘（見 `halt_marker_or_rejection()` 落盤那句 `"at": now.isoformat()`），而逐字稿的
# 真實 mtime 是 Claude Code 在 hook 結束後才把 tool_result／assistant 訊息 append 進去
# 的時刻 ⇒ mtime 天生可能晚於 `at` 幾十毫秒到幾秒。反駁者實測：mtime 晚 20ms ⇒ 誤判
# 過期、回 `None`（哨兵因此喪失 arm_reset 快路徑、落回 900s 巡邏）；commit c4a7e00 當時
# 只把測試治具的 mtime 撥早 5 秒規避現象，生產碼本身未動——本常數才是那一輪缺的另一半。
# 🔴 DEF-200-516（7-E）：現只用於**沒有 reset** 的標記（無兌現時刻可比）；有 reset 的標記改看
# 兌現時刻之後的活動，見 `halt_verdict`——halt 通知自己說收斂型工具照常可用，標記後 10 秒外必有
# 收斂活動，真機 5/5 標記在 14.5～430 s 內被判過期。這裡的 10 秒只吃時序雜訊。
# 🔴 與另外兩個名字相近的容忍窗語意不同、不得混用：`HALT_RESET_SKEW_SECONDS`
# （120s，reset 排程延遲的容忍）、`HALT_MARKER_MAX_CLOCK_SKEW_SECONDS`
# （600s，自檢牆鐘漂移的容忍）——三者各守不同的時脈落差，彼此不可互相取代。
HALT_MARKER_ACTIVITY_SKEW_SECONDS = 10

#: 必須與 `session_resume_planner.SENTINEL_INTERVAL_SECONDS` 同值（兩檔不能互相 import，同
#: `HALT_RESET_SKEW_SECONDS` 的 parity 手法）：PRD §4.5.7 R-4.5.7-1「主控閒置」門檻＝巡邏間隔。
HALT_QUIESCE_SECONDS = 900


def halt_verdict(halt_marker: dict | None, idle_seconds: float | None,
                 now: datetime, superseded_by: dict | None = None) -> dict | None:
    """halt 標記 → 既有 `arm_reset`／`probe`／`escalate` 判決（純函式，同本檔通篇紀律）。

    `None`＝標記不適用，呼叫端（`sentinel_decide`）落回既有的 idle-based 判定。
    標記失效＝**兌現時刻**（`reset_at + HALT_RESET_SKEW_SECONDS`）之後逐字稿仍有新活動 ⇒ session
    已自行續跑（人或前一次喚醒），不判定，否則哨兵會永遠卡在 `probe`；兌現時刻之前的活動（halt 後
    的收斂工作）不算。時刻已到而 session 在一個巡邏間隔內仍有活動 ⇒ 不叫醒（防雙窗），明說理由續巡。
    DEF-200-532：`superseded_by`（`sentinel_lifecycle_arm.superseding_session` 的回傳）＝同專案另一
    session 在標記之後已累積足夠活動（人已接手）⇒ `disarm`＋`clear_halt`，優先於其後的 `arm_reset`／
    `patrol`／`probe`：人在另一個視窗持續工作時任何自動喚醒都是雙窗。但本 session 已在兌現時刻後自行
    續跑的標記先失效（回 `None` 走 idle 判定）；他 session 接手只對仍有效的標記成立（真機 7c51b538：
    標記早被它自己兌現後的活動判失效，不得再以「接手」拆它）。沒有 `reset_at` 的標記維持舊判準、不看
    `superseded_by`。預設 `None` 時五個既有分支逐位元組同行為。
    """
    if not halt_marker:
        return None
    last = None if idle_seconds is None else now.timestamp() - idle_seconds  # 最新逐字稿活動
    reset_at = _aware(halt_marker.get("reset_at"))
    if reset_at is None:
        marker_at = _aware(halt_marker.get("at"))
        if (marker_at is not None and last is not None
                and last > marker_at.timestamp() + HALT_MARKER_ACTIVITY_SKEW_SECONDS):
            return None  # 無 reset 就沒有兌現時刻可比：沿用「標記後仍有活動 ⇒ 主控在場」舊判準
        return {"action": "escalate", "at": None,
                "reason": f"halt 標記存在但解不出 reset 時刻 ⇒ 拒絕用猜的重排：{halt_marker!r}"}
    fire_at = reset_at + timedelta(seconds=_reset_skew())
    if last is not None and last > fire_at.timestamp():
        return None
    if superseded_by:
        who, turns, span = (superseded_by[k] for k in ("sid", "turns", "span_seconds"))
        return {"action": "disarm", "at": None, "clear_halt": True, "superseded_by": who,
                "reason": f"halt 標記存在，但同專案另一 session {who[:8]} 於標記後已累積 "
                          f"{turns} 回合／{span:.0f}s 活動 ⇒ 人已接手（或已有續跑），本 session "
                          "不自動喚醒（防雙窗）；清 halt 標記、靜默解除"}
    if fire_at > now:
        return {"action": "arm_reset", "at": fire_at, "reset_at": reset_at,
                "reset_source": "halt-marker",
                "reason": f"偵測到自願 halt 標記；觀測 reset={reset_at} 尚未到 ⇒ "
                          "要求排程器改在那個時刻醒（本次零 token）"}
    if idle_seconds is not None and idle_seconds < HALT_QUIESCE_SECONDS:
        return {"action": "patrol", "at": now + timedelta(seconds=HALT_QUIESCE_SECONDS),
                "reason": f"自願 halt 標記的兌現時刻已到，但逐字稿 {idle_seconds:.0f}s 前仍有更新"
                          " ⇒ 不叫醒（防雙窗），續巡、下一輪再判（本次零 token）"}
    return {"action": "probe", "at": None,
            "reason": f"偵測到自願 halt 標記；觀測 reset={reset_at} 已過 ⇒ 花一次探測確認額度回來了沒"}  # noqa: E501


#: DEF-200-281／F-1：`quota_halt_actions()` 寫入 halt 標記前的自檢門檻——本輪事故的直接
#: 證據：`tools/tests/test_quota_policy.py` 一支未隔離的測試（module 常數
#: `NOW = datetime(2026, 8, 9, 5, 15, 3, tzinfo=UTC)`）在**任何真實 Claude Code session**
#: 裡跑 pytest 時，因為沒清 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_PROJECT_DIR`、也沒隔離
#: `AUTOSDD_TRACE_DIR`，把這個凍結在一個月前的 `now` 寫進**真實**
#: `~/.autosdd/traces/halt_<真實 sid>.json`——本場三份現場標記（`96d7f386-…`／
#: `8d8773f9-…`／`unknown`）逐位元組相同，且與本函式本機重現輸出逐位元組相同（見
#: `tools/tests/test_wake_chain_halt_r278.py::HaltMarkerSelfCheckTest`）。門檻只挑「大到
#: 不可能是正常時脈漂移／IO 延遲」的量級。
HALT_MARKER_MAX_CLOCK_SKEW_SECONDS = 600


def halt_marker_or_rejection(sid: str, decision: object, now: datetime,
                             transcript: object, source: str,
                             real_now: datetime | None = None,
                             account: str | None = None) -> tuple[dict | None, str | None]:
    """回 `(標記, None)`＝可以落盤，或 `(None, 拒寫理由)`。`account`＝取數當下的帳號指紋（QVD §7.3；
    `None` 寫 `null`，呼叫端出聲）。

    `real_now` 給測試注入；production 呼叫端不傳，落回真牆鐘——自檢不能拿被檢查的
    同一個 `now` 當基準，否則凍結的 `now` 會通過「自己與自己一致」的假陽性檢查。

    🔴 DEF-200-281 第二輪：`now` 缺 tzinfo（naive）時不得讓下面的相減拋
    `TypeError` 崩掉整條 halt 武裝路徑——方向＝當作不可信輸入直接拒寫，不猜時區
    （猜錯時區會讓 `at`/`reset_at` 全錯，與 RC-1 同型：寧可漏一次武裝機會）。
    """
    if now.tzinfo is None:
        return None, f"now={now!r} 缺 tzinfo（naive）⇒ 無法安全比對牆鐘，拒絕落盤"
    real_now = real_now or datetime.now().astimezone()
    resets_at = halt_resets_at(decision)
    skew = abs((real_now - now).total_seconds())
    if skew > HALT_MARKER_MAX_CLOCK_SKEW_SECONDS:
        return None, (f"now={now.isoformat()} 與牆鐘 {real_now.isoformat()} 差距 {skew:.0f}s"
                      f"（>{HALT_MARKER_MAX_CLOCK_SKEW_SECONDS}s）⇒ 疑似測試夾具洩漏或過期"
                      "快取，拒絕落盤")
    reset_dt = _aware(resets_at) if resets_at else None
    if reset_dt is not None and reset_dt < real_now:
        return None, (f"reset_at={resets_at} 已在過去（牆鐘 {real_now.isoformat()}）⇒ 拒絕"
                      "落一份保證讓 halt_verdict() 判定過期的標記")
    return {"sid": sid, "band": decision.band,
            "binding": decision.binding.kind if decision.binding is not None else "",
            "reset_at": str(resets_at or ""), "at": now.isoformat(),
            "transcript": str(transcript) if transcript else "",
            "resolved_source": source, "account": account or None}, None
