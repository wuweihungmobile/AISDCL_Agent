"""額度決策的**人話面**：reset 期程分支判定 ＋ 把 `Decision` 講成一段給人讀的字。

R88／LOC-01 的落地物。此前這一族住在 `tools/lib/quota_gate.py`，而 R87 為了訴求 6c
補上 `posture_line()`（+24 行）之後該檔實測 **524 > 500**（`guardrail_hub` tier），
連帶把 5 支「tier 預警帶必須非阻塞」的契約測試染紅——它們斷言的是 `rc==0`，而檔案層
真違規讓 `rc==1`，於是**測試名稱與失敗原因無關**，讀起來像預警帶壞掉。

🔴 **為什麼是這一族被切出來，而不是隨便切 24 行**（`check_loc_budget` 的 override_reason
逐字要求「先拆職責／抽共用模組」，先例＝`tools/lib/ci_liveness.py`）：本族的輸入是
**已經算好的 `Decision`**，輸出是**字串**，一個字都不碰快取讀寫／派發帳／閂鎖／spawn。
`quota_gate` 剩下的職責因此收斂成「取快取 → 呼叫 `decide()` → 記帳／擋下／說話」，
其中「說話」外包給本檔。

🔴 **誰刻意留在 `quota_gate` 沒有跟著搬**（射程誠實劃界，不是漏搬）：
  · `quota_throttle_message()` — 它吃 `UNBOUNDED_FANOUT_TOOLS`／`FANOUT_WINDOW_SECONDS`
    ／`QUOTA_OFF_ENV` 三個**閘門常數**，搬過來會讓 `quota_messages → quota_gate` 反向成立
    ⇒ 循環 import。它呼叫的 `throttle_horizon_line()` 走 `quota_gate` 的 re-export 解析。
  · `pace_report()`／`pace_state()` — 讀快取、記燃燒帳、寫檔案契約（狀態與 IO 層），不是純
    渲染。（`posture_line()` 後來搬進本檔：快取路徑由 `pace_report()` 傳入，本檔仍不碰
    `quota_cache_path()`；見本輪證據檔〈九〉。）

🔴 **相依方向是單向的**：本檔**不得** import `quota_gate`。與 `quota_gate` 檔頭同一條
規則：`tools/lib/*` 只准**裸名 import**（`from lib import X` 會讓同一份原始碼在同一個
行程裡有兩個模組物件，實測 `e1 is e2` → False）。

🔴 **消費端零改動**：`quota_gate` 對本檔的 9 個符號做 re-export，既有呼叫端
（`.claude/hooks/context_budget_guard.py`／`tools/session_resume_planner.py`
／`tools/lib/sentinel_lifecycle.py`／`tools/lib/schedule_backend.py`）與測試沿用
`quota_gate.<name>` 仍然解析得到。re-export 的經典陷阱（測試 patch 了 `quota_gate.X`
而內部呼叫走本檔的 X）在本次**實查過不成立**：全庫對本族符號的 patch／monkeypatch
命中 0，測試只以屬性方式碰 `quota_gate.apply_env_defaults` 與 `quota_gate.quota_gate`。

回歸鎖：沿用 `tools/tests/test_context_budget_guard.py`（本次搬移不新增判準，
搬移的正確性由「同一批既有測試搬移前後皆綠」承擔）。
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # 排程載具：拿不到時只影響 `evidence_hint()` 那一句，不影響其餘渲染
    import schedule_backend  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    schedule_backend = None  # type: ignore[assignment]

try:
    import platform_utils  # type: ignore[import-not-found]  # 同目錄 SSOT：is_windows()
except Exception:  # noqa: BLE001 — 見上方 fail-open 紀律；不可達就回 POSIX 版澄清句
    platform_utils = None  # type: ignore[assignment]

# `quota_pace` 是本族的葉子（它一支同層模組都不 import）⇒ 相依方向仍是單向的，
# 且 `quota_policy` 早就 import 它（`as W`）：本行沒有新增任何一條相依邊的方向。
import quota_pace  # noqa: E402
import quota_policy  # noqa: E402

#: reset 多遠以內才值得「排程等它」。5 小時視窗最遠 5h、週視窗最遠 7 天，中間這個
#: 缺口大到不需要精確：取 6 小時。方向鎖守的是「七天後才 reset 的線不得被排程」。
RESET_ARM_HORIZON_SECONDS = 6 * 3600

QUOTA_BRANCH_ARM = "arm"
QUOTA_BRANCH_NOTIFY = "notify"
QUOTA_BRANCH_ESCALATE = "escalate"

#: 🔴 同一份字面在 `tools/lib/quota_escalation.py:USAGE_URL` 另有一個家；本檔**不 import
#: 它**——那支模組在模組層就會去碰排程載具，而本檔要能在純渲染的單元測試裡零副作用載入。
USAGE_URL = "https://claude.ai/settings/usage"


def _aware(raw: object) -> datetime | None:
    """ISO 字串 → aware datetime；解不出來回 `None`。"""
    # 🔴 aware 是硬要求（R80 判準「naive 本地時間戳不得被持久化」）：naive 相減跨 DST
    # 會靜默差 3600 秒。本機時區不實施 DST ⇒ 這個缺陷在本機結構上重現不了。
    try:
        moment = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo is not None else None


def reset_branch(resets_at: object, now: datetime) -> str:
    """95% 那道該做什麼：`arm`（排程等它）／`notify`（等沒有意義）／`escalate`（沒有 reset）。"""
    # 🔴 分支由**資料**決定，不由桶名決定（禁止寫死桶名清單：live payload 當時 17 個
    # 頂層鍵，`claude.exe` 內嵌名單只有 8 個 ⇒ schema 正在長）。三條線的差別本來就是
    # 「reset 有多遠」：five_hour ≤5h、weekly 最長 7 天、spend **根本沒有 reset**。
    # 這一條是設計洞不是細節：把「95% ⇒ 排程等 reset」寫成無條件，會在週額度上排一支
    # 七天後才響的工作，而痕跡全綠——那與 R59 事故同形。
    moment = _aware(resets_at)
    if moment is None:
        return QUOTA_BRANCH_ESCALATE
    delta = (moment - now).total_seconds()
    return QUOTA_BRANCH_NOTIFY if delta > RESET_ARM_HORIZON_SECONDS else QUOTA_BRANCH_ARM


def binding_resets_at(decision: quota_policy.Decision) -> object:
    """產生 min 的那一軸的 `resets_at`；量不到（`binding is None`）時回 `None`。"""
    return decision.binding.resets_at if decision.binding is not None else None


# 🔴 修4／R-4.5.6-5（R95；ADR-XPLAT-004 §2.9 事故次因）：halt 武裝分支不得只看
# binding 單軸——2026-08-16 00:42 binding 軸無 reset ⇒ escalate-only 未武裝，而
# five_hour 軸 03:50 reset 後工作實際可續（時間線逐字＝Pace 證據檔 §7-R95-修4）。
# 方向鎖：候選含 binding 自己 ⇒ min 只會更早、不會更晚；全 ≥halt 軸皆無可解析 reset
# 時回 binding 原值，讓 `reset_branch()` 走 escalate——「可等的 reset 被判成 escalate」
# 在結構上不可能發生。ARM 的 6 小時視界仍由 `reset_branch()` 把關（R59 同形防護）。
# 掃描面刻意是 per_axis 全軸（含保險軸）：喚醒錯付的代價是一次探測，漏喚醒是空轉整窗。
def halt_resets_at(decision: quota_policy.Decision) -> object:
    """halt 帶該等的 reset＝**≥halt 各軸**中最早可解析者；全軸皆無 ⇒ binding 原值。"""
    stamps = [r.axis.resets_at for r in decision.per_axis
              if r.band == quota_policy.BAND_HALT and _aware(r.axis.resets_at) is not None]
    return min(stamps, key=_aware) if stamps else binding_resets_at(decision)


#: DEF-200-278／INV-H2：必須與 `tools/session_resume_planner.py::RESET_SKEW_SECONDS`
#: 同值——兩檔不能互相 import（單向規則，見本檔與 `quota_gate.py` 檔頭），故各自具名
#: ＋parity 測試守同值（先例：`test_find_git_bash_parity.py` 對 `_extract_py_candidates`）。
HALT_RESET_SKEW_SECONDS = 120


def halted_band_line(halt_marker: dict | None, now: datetime) -> str | None:
    """D23（SD-07；DEF-200-275 第六輪）：`--pace`／`--check` 在本 sid 的 halt 標記
    未過期時該印的那一行；`None`＝沒有適用的 halt 標記，呼叫端落回既有判定。

    純函式（同本檔通篇紀律）：不讀任何檔，`halt_marker` 由呼叫端已經呼叫過
    `quota_gate.read_halt_marker(sid)` 取得——本檔不得反向 import `quota_gate`
    （見檔頭〈相依方向是單向的〉）。刻意不打任何 API：halt 標記已經把答案寫在磁碟上，
    不需要再花一次探測才知道（那正是 SD-07 要堵的洞——INV-H3 之前，`--pace`/`--check`
    在 halt 期間會落到 `unmeasured` 判定，可能連帶觸發 `quota_meter` 補量探測，而 halt
    期間不該再花任何一次 API）。DEF-200-435：本行此前逐字宣稱「量不到本來就是事實」，
    快取仍新鮮時那句為假（`--check` 末行共用本行）——措辭只陳述「本行只讀標記檔」，
    逐軸真實讀數由 `halted_pace_text()` 補在本行之後。
    """
    if not halt_marker:
        return None
    reset_at = _aware(halt_marker.get("reset_at"))
    if reset_at is not None and reset_at <= now:
        return None  # 已過期：不算「halted」，落回既有判定（會走 probe 分支自然恢復）
    reset_text = halt_marker.get("reset_at") or "（無法解析）"
    return (f"🔴 halted，reset 於 {reset_text}"
            "（本 sid 的 halt 標記尚未過期；這一行只讀標記檔、不打 API，逐軸讀數看 `--pace`）")


def halted_pace_text(halted: str, state: quota_policy.QuotaState, now: datetime,
                     policy: quota_policy.Policy, model: str | None = None) -> str:
    """`--pace` 在本 sid 有未過期 halt 標記時的全文（DEF-200-435）。純函式：`state` 由呼叫端讀快取。

    快取新鮮 ⇒ 標記行之後印逐軸真實讀數（`describe`，仍不打 API）；快取真的不可用才說沒有讀數。
    此前一律只回標記行、第二次 `--pace` 起模型拿不到任何數字，且那一行宣稱「量不到本來就是事實」。
    判讀本身確實停止時再補「換模型有沒有用」（與 halt 首則／重複訊息／提醒同一句）；不停止時不印——
    標記是 session 級、判讀是依 `model` 算的，兩者可以不同步，印出結論會是假話。
    """
    if not state.usable():
        return halted + "\n  （沒有新鮮快取可讀：halt 期間不打 API 補量，所以本次沒有逐軸讀數）\n"
    decision = quota_policy.decide(state, now, policy, active_model=model)
    hint = f"  {halt_model_hint(decision)}\n" if decision.band == quota_policy.BAND_HALT else ""
    return f"{halted}\n  {quota_policy.describe(decision)}\n{hint}"


# 🔴 DEF-200-274 第十輪／SA-04（反駁者在現行程式碼上重現）：`halt_verdict()` 判「標記
# 已過期（session 自行續跑過）」此前是零容忍嚴格比較——標記的 `at` 是 hook 處理當下的
# 牆鐘（見 `halt_marker_or_rejection()` 落盤那句 `"at": now.isoformat()`），而逐字稿的
# 真實 mtime 是 Claude Code 在 hook 結束後才把 tool_result／assistant 訊息 append 進去
# 的時刻 ⇒ mtime 天生可能晚於 `at` 幾十毫秒到幾秒。反駁者實測：mtime 晚 20ms ⇒ 誤判
# 過期、回 `None`（哨兵因此喪失 arm_reset 快路徑、落回 900s 巡邏）；commit c4a7e00 當時
# 只把測試治具的 mtime 撥早 5 秒規避現象，生產碼本身未動——本常數才是那一輪缺的另一半。
# 本容忍窗判的是「session 是否真的自行續跑」：真續跑會持續產生活動、遠超這個量級，
# 10 秒只吃時序雜訊，不吃真實續跑。
# 🔴 與另外兩個名字相近的容忍窗語意不同、不得混用：`HALT_RESET_SKEW_SECONDS`
# （120s，reset 排程延遲的容忍）、`HALT_MARKER_MAX_CLOCK_SKEW_SECONDS`
# （600s，自檢牆鐘漂移的容忍）——三者各守不同的時脈落差，彼此不可互相取代。
HALT_MARKER_ACTIVITY_SKEW_SECONDS = 10


def halt_verdict(halt_marker: dict | None, idle_seconds: float | None,
                 now: datetime) -> dict | None:
    """halt 標記 → 既有 `arm_reset`／`probe`／`escalate` 判決（純函式，同本檔通篇紀律）。

    `None`＝標記不適用，呼叫端（`sentinel_decide`）落回既有的 idle-based 判定。
    「最新活動晚於標記**超過** `HALT_MARKER_ACTIVITY_SKEW_SECONDS` 容忍窗」代表 session
    已自行續跑過，此時標記過期——不判定，否則哨兵會永遠卡在 `probe`（那是本輪要修的
    無做工空轉的鏡像新形態）；容忍窗只吃 hook 落盤與逐字稿 append 之間的先天時序雜訊，
    不放大成「已續跑」的誤判空間（見上方常數定義的 SA-04 立案）。
    """
    if not halt_marker:
        return None
    marker_at = _aware(halt_marker.get("at"))
    if (marker_at is not None and idle_seconds is not None
            and (now.timestamp() - idle_seconds)
                > marker_at.timestamp() + HALT_MARKER_ACTIVITY_SKEW_SECONDS):
        return None
    reset_at = _aware(halt_marker.get("reset_at"))
    if reset_at is None:
        return {"action": "escalate", "at": None,
                "reason": f"halt 標記存在但解不出 reset 時刻 ⇒ 拒絕用猜的重排：{halt_marker!r}"}
    fire_at = reset_at + timedelta(seconds=HALT_RESET_SKEW_SECONDS)
    if fire_at > now:
        return {"action": "arm_reset", "at": fire_at, "reset_at": reset_at,
                "reset_source": "halt-marker",
                "reason": f"偵測到自願 halt 標記；觀測 reset={reset_at} 尚未到 ⇒ "
                          "要求排程器改在那個時刻醒（本次零 token）"}
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


def halt_marker_or_rejection(sid: str, decision: quota_policy.Decision, now: datetime,
                             transcript: object, source: str,
                             real_now: datetime | None = None) -> tuple[dict | None, str | None]:
    """回 `(標記, None)`＝可以落盤，或 `(None, 拒寫理由)`。

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
            "resolved_source": source}, None


# 憑證是真的、**指路是假的**——那個 cmdlet 在 mac 不存在，而 `NextRunTime` 這個概念 launchd
# 從不提供（`launchctl print` 輸出裡 next／fire／due 皆不存在，R83 實測）。同型判例：
# 「憑證裡混一句假話，比沒有那一欄更難看見」（`schedule_backend._readback` 的 depth-1 訂正）。
def evidence_hint() -> str:
    """「怎麼查它真的排進去了」——唯一的家＝本機那個排程後端。"""
    return (schedule_backend.select().evidence_hint() if schedule_backend is not None
            else "排程載具不可達（import 失敗）⇒ 本工具**說不出**取證指令；"
                 "在拿到憑證之前不要把它當成已排程。")


# 🔴 DEF-200-200 ③：`reset_branch()` 對**已經過去**的時刻回 `arm`（負的 delta 當然
# `<= 6h`），於是這三支句子把一個死掉的時刻播報成「6 小時內／很快就會自己解除」。`now`
# 是選配（既有呼叫端一個字都不改）：**有給才判得出來**已過期，沒給就沿用舊句子——但
# 生產路徑（`throttle_horizon_line`）一律有 `now`，故缺省值不是靜默漏洞。
def expiry_phrase(resets_at: object, minutes: float, note: str) -> str:
    """已過期那一句：說出**過去多久**與**該做什麼**，兩義各自指向不同的子系統。"""
    ago = int(abs(minutes))
    if note == quota_pace.EXPIRY_SKEW:
        return (f"reset 在 {resets_at}，比這份讀數的量測時刻**還早** {ago} 分鐘 ⇒ "
                "本機鐘與伺服器不一致（先校時，不是等它）")
    return (f"reset 在 {resets_at}，**已經過去 {ago} 分鐘** ⇒ 這份讀數屬於已經翻頁的"
            "死視窗（重量一次即可，不是等它自己解除）")


def reset_horizon_phrase(branch: str, resets_at: object, now: datetime | None = None,
                         measured_at: object = None) -> str:
    """三支分支各自的「這條線的 reset 有多遠」——**唯一的家**（R82／Q2-07 的減法那一半）。

    🔴 halt 與 throttle 此前各自寫了一份幾乎逐字相同的三分支句子（含兩處硬寫的 URL），
    而既有鎖只認「沒有 reset 可以等」這個字樣、不認結構 ⇒ 兩份漂移不會有任何東西轉紅。
    收成一份之後，兩支呼叫端各自只補**自己的動作句**（halt＝排程是錯的動作、
    throttle＝這道節流不會自己解除），三支分支的字串仍**彼此不同**——那條不變式
    （否則「不排程」與「排不了」外觀相同）是被保留的，不是被參數化掉的。
    """
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：{USAGE_URL}"
    if now is not None:
        minutes, note = quota_pace.expiry_of(resets_at, now, measured_at)
        if quota_pace.expired(note):
            return expiry_phrase(resets_at, minutes, note)
    hours = RESET_ARM_HORIZON_SECONDS // 3600
    if branch == QUOTA_BRANCH_NOTIFY:
        return f"reset 在 {resets_at}（**遠超 {hours} 小時**）"
    return f"reset 在 {resets_at}（{hours} 小時內）"


# 收斂型工具清單那句的**單一導出**：簡報（`session_brief.py`）與 halt／量不到三種訊息都呼叫它，
# 不得在別處抄第二份清單、也不得對成句做字串手術。限定語＝寫壞的指令只擋**那一次呼叫**，工具
# 本身沒被停用；Windows 的 Bash 由鐵律一 hook（`block_bash_on_windows.py`）另行停用，所以那
# 一邊列 PowerShell。刻意不含全形分號與「，只有」：呼叫端拿它組句。
def convergent_tools_clause(windows: bool | None = None) -> str:
    """收斂型工具清單句：清單與限定語只在這裡寫一次。POSIX 列 Bash、Windows 列 PowerShell，
    兩者只差殼；`None`＝以 `_is_windows()` 現查平台。"""
    shell = "PowerShell" if _is_windows(windows) else "Bash"
    return f"收斂型工具（Read／Write／Edit／{shell}／git，寫壞的 {shell} 只擋那一次呼叫）不受影響"


_HALT_DONE = "你剛才那次工具呼叫已正常執行完成"
_HALT_PAUSE = "，只有扇出型（Task／Agent／Workflow／WebFetch／WebSearch）暫停；"
# Windows 上 Bash 工具由鐵律一 hook 整支停用：只換清單不夠，還要明講哪些工具照常可用；句中不引述
# 「不能寫檔」之類的症狀字面（引述即預示，與 `session_brief.py` 一致；SD-195-04）。
# （與 `session_brief.py` 的 Windows 簡報句是姊妹站點，兩處各有自己的後半）。
_HALT_WINDOWS_NOTE = ("（Windows：Bash 工具另由鐵律一 hook 停用，跑指令用 PowerShell 工具、"
                      "改檔用 Write／Edit，不要先試 Bash；其餘工具照常可用，清單見前句）")
_HALT_PACE = "真實數字現查：`python tools/session_resume_planner.py --pace`"


def _is_windows(windows: bool | None = None) -> bool:
    """平台判準的單一入口：`None` 時以同目錄 SSOT `platform_utils.is_windows()` 現查——本檔
    不得自己寫 `os.name`／`sys.platform` 分支（根 CLAUDE.md〈Windows 側單一載具原則〉鐵律三）。
    import 失敗時一律 fail-open 回 POSIX：hook 行程不保證 `tools/lib` 以外的模組在
    `sys.path` 上，組句失敗不得反過來擋住 halt 訊息本身。"""
    if windows is not None:
        return windows
    try:
        return bool(platform_utils.is_windows())
    except Exception:  # noqa: BLE001 — 見上：fail-open 回 POSIX 版
        return False


def _halt_rest(windows: bool) -> str:
    """halt 澄清句首句**之後**的全部：清單句＋扇出暫停＋（Windows 括號）＋現查指令。兩種首句
    （已執行完成／沒有執行）共用它，PreToolUse 版因此不必對成句做字串手術。"""
    return (convergent_tools_clause(windows) + _HALT_PAUSE
            + (_HALT_WINDOWS_NOTE if windows else "") + _HALT_PACE)


# POSIX 版的公開常數（既有回歸鎖與呼叫端沿用）；Windows 版走 `halt_convergent_clarification(True)`。
HALT_CONVERGENT_CLARIFICATION = f"{_HALT_DONE}；{_halt_rest(False)}"


def halt_convergent_clarification(windows: bool | None = None, event: str = "PostToolUse",
                                  tool: str = "") -> str:
    """halt 帶收斂型工具澄清句，平台感知版（DEF-200-413）；平台判準見 `_is_windows()`。

    DEF-200-435：`event="PreToolUse"`＝扇出工具根本沒執行，首句「你剛才那次工具呼叫已正常
    執行完成」對它是假話（且與同則訊息的「扇出型工具一律不執行」互相矛盾）⇒ 只換首句，
    其餘同源（`_halt_rest()`）；預設值的輸出與換首句前逐字相同。
    """
    first = (f"這次 {tool or '扇出型'} 呼叫已被擋下、沒有執行" if event == "PreToolUse"
             else _HALT_DONE)
    return f"{first}；{_halt_rest(_is_windows(windows))}"


def degraded_detail(reason: str, refresh_failed: bool) -> str:
    """量不到通知的 detail（DEF-200-453）：本行程的補量真的失敗才說「取數失敗」，否則引快取
    自己的 `reason` 原句（stale-cache／expired-window 的原句本來就寫「不是取數壞掉」）。
    後半句恆真：走到這裡就是逐字稿地板也沒有。史料見
    docs/06_quality/CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九〉。"""
    return ("取數失敗" if refresh_failed else reason) + "，且逐字稿裡沒有未復原的撞線可以當地板"


def degraded_convergent_clarification(windows: bool | None = None) -> str:
    """量不到通知（PostToolUse）的收斂型工具澄清句（DEF-200-453）。

    與 halt 版同源——清單句與平台判準各只有一個家（`convergent_tools_clause()`／
    `_is_windows()`）；後半的「只有扇出型…暫停」是 halt 專屬，量不到時扇出型只是被收緊到
    硬上限（`degraded_cap`）而不是停用，照抄會叫模型停派，所以這裡自己組後半。"""
    return (f"{_HALT_DONE}；{convergent_tools_clause(_is_windows(windows))}"
            "，扇出型工具只受上面那個硬上限約束，量到讀數就依真實水位重判。")


def degraded_message(source: str, detail: str, posture: str, trace: object, ttl: int,
                     event: str = "PreToolUse") -> str:
    """量不到通知全文（純渲染；閂鎖、痕跡、發射在 `quota_gate.note_degraded`）。PostToolUse 的
    通知是工具跑完**之後**才出現的紅字，補一句澄清；PreToolUse 被評估的就是扇出呼叫本身，
    「已正常執行完成」對它是假話，不借用。"""
    text = (f"⚠️  額度水位**量不到**（source={source}）⇒ {posture}\n"
            f"   這不是「額度很寬鬆」：{detail}。\n"
            f"   現查：`python tools/lib/quota_meter.py --json`（失敗時會印 reason）；"
            f"痕跡：{trace}\n"
            f"   （同一個 source 每 {ttl} 秒只說一次）\n")
    if event != "PostToolUse":
        return text
    return text + f"   {degraded_convergent_clarification()}\n"


# 🔴 **開頭不再印裸百分比**（R82／M7）：舊版第一行是「額度水位 54%（≥95%…）」，而裸的
# 「54%」正是掌舵者當場誤讀的**那個**形狀——那個數字沒有說自己是哪一桶、什麼時候 reset。
# 改由 `quota_policy.describe()` 逐軸渲染，每一個 % 都自帶 `kind=` 與剩餘分鐘（或明文
# 「reset 距離不明」），而且**每一軸都說**，不是只說最緊的那一格。
def _halt_subject(kind: str, decision: quota_policy.Decision, model: str | None) -> str:
    """halt 訊息首行括號內那一段：哪條軸、哪個模型、reset 何時。CC 摺疊列只顯示首行，這三件
    事不在首行就只看得到別的（DEF-200-435：重複訊息首行曾是 describe() 的軸傾印）。"""
    return (f"最緊的一條＝{kind}；模型={model or '未知'}；"
            f"reset={halt_resets_at(decision) or '沒有 reset 可等'}")


def _halted_axes(decision: quota_policy.Decision) -> list:
    """真的在煞車、且在停止水位的軸。被排除的分軌軸（`NOTE_MODEL_EXCLUDED`）與保險軸不算——
    它們沒進 cap 聚合，沒在煞車。"""
    return [r.axis for r in decision.per_axis
            if r.band == quota_policy.BAND_HALT and r.axis.kind not in quota_policy.FALLBACK_KINDS
            and quota_policy.NOTE_MODEL_EXCLUDED not in r.note]


def halt_is_model_scoped(decision: quota_policy.Decision) -> bool:
    """停止的軸是不是**全部**都是模型分軌軸（只停某個家族）；有一條全模型共用軸也停止 ⇒ False。"""
    halted = _halted_axes(decision)
    return bool(halted) and all(a.kind in quota_policy.MODEL_SCOPED_KINDS for a in halted)


def halt_model_hint(decision: quota_policy.Decision, own_window: bool = True) -> str:
    """halt 帶「換模型有沒有用」那一句（DEF-200-435）。

    只有**進 cap 聚合**的停止軸全是模型分軌軸時，改派別家族的子 agent 才有用；只要有一條全
    模型共用的軸也在停止水位，換模型就沒用（判準＝`halt_is_model_scoped()`）。提醒本視窗自己的
    回合仍耗該模型額度：子 agent 派得出去不等於父視窗的額度沒在燒；別家族自己的 cap 與派發帳
    仍適用，所以說「不受這條軸限制」而不說「照常」。

    DEF-200-436：`own_window=False`＝呼叫端是派工目標閘（`halt_dispatch_message()`），閘門端看
    不到視窗家族（視窗多半屬別家模型）⇒ 不替視窗下結論，省略「本視窗自己的回合…」那半句；其餘
    呼叫端的 `model` 就是視窗自己的模型（進 cap 聚合的分軌軸只含該家族），那半句為真。
    """
    if halt_is_model_scoped(decision):
        names = "／".join(sorted({a.scope_model or a.kind for a in _halted_axes(decision)}))
        tail = ("；但本視窗自己的回合仍耗該模型額度，長工作請用 `/model` 切換家族。"
                if own_window else "。")
        return (f"換模型有用：停止的只有模型分軌軸（{names}）⇒ 派 Agent 時帶 `model:` 指定不是"
                f" {names} 的家族，即可不受這條軸限制地派發（仍受各軸 cap）{tail}")
    return "換模型沒有用：停止的軸是全模型共用 ⇒ 只能等 reset 或提額，先做不扇出的收斂工作。"


def quota_halt_message(decision: quota_policy.Decision, act: dict, event: str = "PostToolUse",
                       tool: str = "", model: str | None = None) -> str:
    """halt 的首則訊息。三支分支**字串必須不同**，否則「不排程」與「排不了」外觀相同。

    DEF-200-435：`event` 決定這則話的性質——`PreToolUse`＝扇出工具被擋下的阻斷訊息（rc=2，
    明說這次呼叫沒有執行）；其餘＝工具已跑完的一次性提醒（exit 0、走 additionalContext，
    **不是錯誤**：CC 把 PostToolUse 的 rc=2 標成 hook error，人與模型都讀成「工具被擋」）。
    """
    blocked = event == "PreToolUse"
    subject = _halt_subject(act["kind"] or "未知", decision, model)
    head = (f"🔴 額度到達**停止**水位（{subject}）⇒ **停止派發**：扇出型工具一律不執行。\n"
            if blocked else
            f"🟡 額度到達**停止**水位（{subject}）——這是一次性提醒，不是錯誤；"
            f"{convergent_tools_clause(_is_windows())}，照常可用。\n")
    failed = act.get("failed")  # 副作用拋例外時 `halt_actions_guarded()` 放進來的失敗原因
    no_plan = "（執行失敗，見下）" if failed else "（寫不出來——逐字稿路徑不可得）"
    head += (f"   {halt_convergent_clarification(event=event, tool=tool)}\n"
             f"   {halt_model_hint(decision)}\n"
             f"   {quota_policy.describe(decision)}\n"
             f"   任務書：{act['plan'] or no_plan}\n")
    # 修4：期程句印**被選中的** reset（≥halt 最早可 reset 軸），不再印 binding 的 None。
    # DEF-200-200 ③：`now` 走 `act.get`（`quota_halt_actions` 已把它放進去）——既有直接
    # 組 act dict 的呼叫端沒有這一鍵時沿用舊句子，不會因為缺鍵就炸掉。
    horizon = reset_horizon_phrase(act["branch"], halt_resets_at(decision),
                                   act.get("now"), act.get("measured_at"))
    if failed:
        tail = (f"   ⚠️ 任務書／喚醒動作執行失敗（{failed}）⇒ 不保證已留下任務書、也不保證已武裝"
                "喚醒；halt 本身照常生效。收斂後請手動跑 `python tools/session_resume_planner.py` "
                "補任務書。\n")
    elif act["posix"]:
        # 🔴 SA-B7：沒有排程載具的平台若沿用 weekly 那支「不排程」的靜默路徑，
        # 「不排程」與「排不了」會長得一模一樣。
        # 🔴 R83／F2-② 訂正本句的平台清單（原文寫「schtasks 只在 Windows 成立…mac/Linux
        # 請自行以 launchd／cron 掛」——R83 已把 mac 接上 launchd ⇒ `posix` 這個鍵在 mac
        # 上是 False，這一支**走不到** mac；把 mac 寫在這裡是拿過期事實當指引）。
        tail = ("   ⚠️ 本平台**沒有排程載具**（Windows 走 schtasks、macOS 走 "
                "launchd，本平台兩者皆無）⇒ 已寫任務書，但**沒有武裝任何喚醒**。"
                "請自行以 cron／systemd-timer 掛，或留在這裡等人回來。\n")
    elif act["branch"] == QUOTA_BRANCH_ARM and act["armed"]:
        tail = f"   ✅ 已武裝喚醒（{horizon}）。{evidence_hint()}\n"
    elif act["branch"] == QUOTA_BRANCH_ARM:
        tail = ("   ⚠️ 這一條的 reset 近在眼前、本來該武裝喚醒，但**這次沒有武裝**："
                + ("哨兵逃生口有設（AUTOSDD_SENTINEL_OFF）。\n" if act["sentinel_off"]
                   else "拿不到逐字稿路徑 ⇒ 沒有可以掛的任務書。\n"))
    elif act["branch"] == QUOTA_BRANCH_NOTIFY:
        tail = (f"   🔴 這一條的 {horizon} ⇒ 「等」幾乎沒有意義，"
                "本次**刻意不排程**（排一支七天後才響的工作而痕跡全綠＝R59 事故同形）。"
                "改做不吃額度的工作，或降扇出／切小模型。\n")
    else:
        tail = (f"   🔴 這一條{horizon} ⇒ 排程是錯的動作，"
                "只有人去提額才會回來。\n")
    if blocked:
        return head + tail
    # 提醒是模型這一輪唯一會收到的 halt 訊息：reset 時刻一定要在；同一視窗不會再說第二次。
    return (head + tail + ("" if horizon in tail else f"   {horizon}\n")
            + "   （同一視窗不再重複提醒；只有扇出型工具被擋下時才會再說一次。）\n")


#: DEF-200-452：`band=unmeasured`（`binding is None`）的期程句。「沒有 reset 可以等…只有人去提額」
#: 是替**量到的軸沒有 reset**（月度支出）寫的，量不到誤入同一句會與同則訊息「重量一次即可，不是
#: 取數壞掉」自相矛盾、還叫人去提額；量不到與 reset 無關，答案是等下一次補量或現查 `--pace`。
UNMEASURED_HORIZON_LINE = (
    "   ⏳ 這道收緊是因為額度**量不到**，不是在等 reset：下一次補量（每個快取 TTL 至多一次）"
    "拿到讀數就依真實水位重判；現查：`python tools/session_resume_planner.py --pace`。\n")


def telemetry_retry_line(retry_after: object, now: datetime) -> str:
    """量不到若是遙測端點限流（429），補一句伺服器自己報的恢復時刻；沒有、解不出或已過去 ⇒ `""`
    （此時整句逐字等於沒有 Retry-After 的量不到句）。字面自帶尺名（遙測通道），不與額度尺的
    「節流」共用詞；那是模型額度的話，見本輪證據檔〈九〉。"""
    when = _aware(retry_after)
    if when is None or when <= now:
        return ""
    return (f"   📡 遙測通道（usage 端點）被限流，伺服器回報 {retry_after} 之後可再量；"
            "這與模型額度無關。\n")


# halt 帶用 `reset_branch()` 分得出 arm／notify／escalate，**throttle 帶此前完全不分**
# ⇒ 週額度偏高時 cap 會連續套用好幾天，與 five_hour 同水位（最多 5 小時）代價差一個
# 數量級，而訊息裡讀不出差別。
# 🔴 R82 訂正本段的舊結語（原文寫「本行只把差別說出來，**不動 cap 的階梯**，因為按 reset
# 距離分檔是政策決定」——那句話已被裁決推翻，故不留著當現行說法）：cap 現在**本來就**是
# `f(pct, horizon)` 的函式，reset 距離已經進了階梯本身；本行說的是同一件事的人話面，
# 兩者同源於 `quota_policy`，不是兩個判準。
def throttle_horizon_line(decision: quota_policy.Decision, now: datetime,
                          measured_at: object = None) -> str:
    """節流帶要說出「這道限制會套多久」。已過期的時刻**不得**說「很快就會自己解除」。"""
    if decision.band == quota_policy.BAND_UNMEASURED:
        return UNMEASURED_HORIZON_LINE + telemetry_retry_line(decision.retry_after, now)
    # 🔴 DEF-200-435：cap 被遲滯維持（低於 binding 軸自己的 cap）時，下面所有以 binding 的 reset
    # 為期程的句子都不成立——放寬由最小停留時間決定，與那條軸的 reset 無關（實測：各軸 cap=2、
    # 終值 cap=1 的 Opus 視窗被告知「連續套用好幾天」，真因是分鐘尺度的遲滯）。
    own = next((r.cap for r in decision.per_axis if r.axis is decision.binding), None)
    if decision.cap is not None and own is not None and decision.cap < own:
        dwell = int(quota_policy.DEFAULT_POLICY.min_dwell_seconds)
        return (f"   ⏳ 目前 cap={decision.cap} 由遲滯維持（這條軸自己的 cap 是 {own}）：各軸水位"
                f"不變的話，每個最小停留時間（出廠 {dwell} 秒，可由 .env 調）最多放寬 1 階，"
                "不是要等到那條軸的 reset。\n")
    # 修4：halt 帶改讀多軸選擇——撞牆期間人唯一持續看得到的就是這一則（R89 判例），
    # binding 無 reset 時印「不會自己解除」而喚醒其實已武裝＝訊息說假話。
    resets_at = (halt_resets_at(decision) if decision.band == quota_policy.BAND_HALT
                 else binding_resets_at(decision))
    branch = reset_branch(resets_at, now)
    horizon = reset_horizon_phrase(branch, resets_at, now, measured_at)
    # 🔴 DEF-200-200 ③：這一行此前對已過去的時刻逐字說「很快就會自己解除」——那是假話，
    # 而假話的方向是**叫人繼續等**一個不會發生的事件（DEF-200-044 的無做工空轉同形）。
    if quota_pace.expired(quota_pace.expiry_of(resets_at, now, measured_at)[1]):
        return f"   ⏳ 這一條的 {horizon}。\n"
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"   ⏳ 這一條{horizon} ⇒ 這道節流不會自己解除。\n"
    # 🔴 DEF-200-435：本句是五個語境共用的（Agent 節流／Workflow 節流／halt 重複阻斷／`--pace`／
    # prepare），所以只准寫**每個語境都為真**的話——此前多帶的「被擋的這一次只要等窗口清空就能再派」
    # 只對 Agent 節流成立（halt 的 cap=0 等任何窗口都派不出去；Workflow 與窗口無關；`--pace`／
    # prepare 沒有「被擋的這一次」），等於叫人等一個不會來的事件。窗口滾動的說法留在 Agent 分支。
    # DEF-200-435：放寬與否要依帶別如實說——非停止帶同水位下 cap 隨 reset 逼近 2→4→8，不得斷言
    # 不會放寬；停止帶 cap 恆為 0、到 reset 才解除，不得說會逐步放寬（鎖＝
    # `ThrottleBandSaysHowLongItLastsTest`）。
    if branch == QUOTA_BRANCH_NOTIFY:
        halted = decision.band == quota_policy.BAND_HALT
        eases = ("要等到 reset 才解除，停止帶不隨時間放寬" if halted
                 else "水位不變時，隨 reset 逼近才逐步放寬")
        return (f"   ⏳ 這一條的 {horizon} ⇒ 這個 cap 會**連續套用好幾天**（{eases}）。"
                "改做不吃額度的工作，或降扇出／切小模型。\n")
    return f"   ⏳ 這一條的 {horizon} ⇒ 這道節流很快就會自己解除。\n"


# 🔴 R158（主控裁決）：`quota_gate.py` 1140-1147 那則重複訊息（halt 閂鎖命中後、每次 round-label-ok
# Read／Bash 都印，撞牆期間人唯一持續看得到的版本）整段搬回人話面這個家——組字邏輯只
# 一個家，不是把常數搬過去、組字留在呼叫端兩處各自維護。輸出與搬移前相同，另加一行
# `HALT_CONVERGENT_CLARIFICATION`（DECISION P2；見
# `tools/tests/test_context_budget_guard.py` 的既有回歸鎖）。
def quota_halt_repeat_message(decision: quota_policy.Decision, now: datetime,
                              event: str = "PostToolUse", tool: str = "",
                              model: str | None = None) -> str:
    """halt 閂鎖命中後的重複訊息。同一個 `reset_branch()`，`quota_halt_message()` 的
    第三個出口——`act` 那份 dict 只在**第一次**觸發時建立（見 `quota_gate.py` 的閂鎖
    註解），這裡只吃 `decision`／`now` 兩個原語，不依賴 `act`。

    DEF-200-435：首行直接點明停止水位／哪條軸／哪個模型／reset 時刻（此前首行是 describe() 的
    軸傾印，CC 摺疊列看到 `band=free cap=None` 排第一，與 halt 相反）；`event`／`tool` 讓
    PreToolUse 的阻斷如實說「這次呼叫沒有執行」。describe() 仍逐軸印出，只是不再當首行。
    """
    kind = decision.binding.kind if decision.binding is not None else "未知"
    return (f"🔴 額度仍在停止水位（{_halt_subject(kind, decision, model)}）："
            "扇出一律不執行，任務書已在磁碟上。\n"
            f"   {halt_convergent_clarification(event=event, tool=tool)}\n"
            f"   {halt_model_hint(decision)}\n"
            f"   {quota_policy.describe(decision)}\n"
            + throttle_horizon_line(decision, now))


def halt_latch_key(sid: str, model: str | None, decision: quota_policy.Decision) -> str:
    """halt 閂鎖鍵：(逐字稿 sid, 模型家族, 停止軸, reset 分鐘)——換任何一格才再說一次
    （DEF-200-435）。reset 截到分鐘：`resets_at` 有次秒級抖動（它是 now＋剩餘算出來的）。
    sid 進鍵是因為閂鎖檔是 machine-wide 單檔；模型進鍵是因為同一視窗換家族後停止的軸可能
    換了一批（Fable 停止、改派 Sonnet 不該被前一則提醒吃掉）。"""
    return (f"halt@{sid}@{model or '-'}@{decision.binding.kind}"
            f"@{str(halt_resets_at(decision))[:16]}")


#: hook 求 `active_model` 時把 `tool_input.model` 當「派工目標」的工具（`Workflow` 看不到內部）。
DISPATCH_TARGET_TOOLS = ("Agent", "Task")


def dispatch_target(payload: object, event: str) -> str:
    """這次呼叫是 PreToolUse×Agent／Task 且 `tool_input.model` 認得出家族 ⇒ 該家族字；否則 `""`。

    與 hook `main()` 求 `active_model` 時的「派工目標」同一判準：fork 忽略 model、吃父模型；
    inherit／缺席／認不出／形狀不對一律退回視窗模型。hook（`.claude/hooks/`）本檔不得 import，
    所以這是同一判準的第二份複本——漂移由 `test_context_budget_guard.py` 逐形態比對 hook 實際
    傳進閘門的 `active_model`（`QuotaGateDecidesOnTheDispatchTargetModelTest`）。
    """
    ti = payload.get("tool_input") if isinstance(payload, dict) else None
    if (event != "PreToolUse" or not isinstance(ti, dict) or ti.get("subagent_type") == "fork"
            or payload.get("tool_name") not in DISPATCH_TARGET_TOOLS):
        return ""
    return quota_policy.family_key(ti.get("model"))


def halt_dispatch_scoped(payload: object, event: str, model: str | None,
                         decision: quota_policy.Decision) -> bool:
    """這次 halt 是不是「只針對這一次派工指名的模型」（DEF-200-436）。

    成立＝hook 問的是派工目標（`dispatch_target()` 等於 `model`）**且**停止的只有模型分軌軸
    （`halt_is_model_scoped()`）。此時視窗自己的模型是否也停止，閘門端看不出來（Sonnet 視窗派
    `fable` 與 Fable 視窗派 `fable` 的 PreToolUse payload 除逐字稿路徑外逐字相同，而視窗模型
    只有 hook 讀得到）⇒ 只擋這一次，不替視窗落 session 級副作用（halt 標記／任務書／喚醒）：
    自己沒停止的視窗被標成 halted，`--pace` 會略過「現在可派」直到目標家族 reset（數天）。視窗
    自己的停止由它自己的工具事件落地。有一條全模型共用軸也在停止 ⇒ 不論派往哪一家視窗自己都
    停了，照舊走副作用。
    """
    return (bool(model) and dispatch_target(payload, event) == model
            and halt_is_model_scoped(decision))


def halt_dispatch_message(decision: quota_policy.Decision, now: datetime, tool: str,
                          model: str | None) -> str:
    """派工指名的模型已在停止水位、只擋這一次呼叫的阻斷訊息（DEF-200-436；rc=2 由 `halt_notice`
    給）。不宣稱任何視窗級的事（任務書／喚醒／標記）：那些沒有做。"""
    kind = decision.binding.kind if decision.binding is not None else "未知"
    return (f"🔴 這次 {tool or '扇出型'} 呼叫指名的模型（{model}）已到額度**停止**水位"
            f"（{_halt_subject(kind, decision, model)}）⇒ 這次呼叫已被擋下、沒有執行。\n"
            "   只擋這一次派工：沒有替整個視窗落 halt 標記／任務書／喚醒（視窗自己的模型若也停止，"
            "會在視窗自己的工具事件上另行提醒）。\n"
            f"   {halt_convergent_clarification(event='PreToolUse', tool=tool)}\n"
            f"   {halt_model_hint(decision, own_window=False)}\n"
            f"   {quota_policy.describe(decision)}\n"
            + throttle_horizon_line(decision, now))


def halt_notice(decision: quota_policy.Decision, now: datetime, event: str, tool: str,
                act: dict | None, model: str | None = None,
                scoped: bool = False) -> tuple[str, int]:
    """halt 帶這一次要說什麼、以什麼 rc 說，回 `(text, rc)`（DEF-200-435；純函式）。

    `act` 只在閂鎖首見時非空（重複呼叫傳 `None`/`False`）。`PreToolUse`＝扇出邊緣，工具真的
    被擋 ⇒ rc=2，首則／重複各一版，皆明說這次呼叫沒有執行。其餘事件（`PostToolUse`）＝工具
    已跑完、沒有東西可擋 ⇒ 只在首見時以 rc=0 提醒一次（呼叫端走 `additionalContext`，不走
    stderr），之後 `("", 0)` 完全安靜。`scoped`（`halt_dispatch_scoped()`，DEF-200-436）＝只擋這一次
    派工、不落視窗級副作用 ⇒ 不吃閂鎖、每次都出聲（rc=2），訊息點名目標模型。
    """
    if scoped:
        return halt_dispatch_message(decision, now, tool, model), 2
    if event == "PreToolUse":
        return ((quota_halt_message(decision, act, event, tool, model) if act
                 else quota_halt_repeat_message(decision, now, event, tool, model)), 2)
    return (quota_halt_message(decision, act, event, tool, model), 0) if act else ("", 0)


def halt_actions_guarded(run, payload: dict, decision: quota_policy.Decision, now: datetime,
                         **kw: object) -> dict:
    """halt 副作用（任務書／喚醒／標記）的安全殼（DEF-200-435）。

    `run`＝`quota_gate.quota_halt_actions`（注入；本檔不得 import `quota_gate`）。副作用拋例外時
    回一份帶 `failed` 的 act，而不是讓例外冒到 hook 的 catch-all——那會讓 rc=0 **放行**（煞車本身
    消失）、提醒也丟，而閂鎖已先寫 ⇒ 之後永遠靜默。煞車與提醒不得依賴副作用成功；副作用只試一次
    （閂鎖仍是先寫：若改成動作成功後才寫，平行的 hook 行程在動作期間全數讀到「沒說過」而各自
    spawn 一輪，持續失敗時更是每次呼叫都重試的 spawn 風暴）。
    """
    try:
        return run(payload, decision, now, **kw)
    except Exception as why:  # noqa: BLE001 — 副作用壞掉不得帶走煞車與提醒
        binding = decision.binding
        return {"branch": reset_branch(halt_resets_at(decision), now), "plan": "", "armed": False,
                "now": now, "failed": f"{type(why).__name__}: {why}", "sentinel_off": False,
                "posix": False, "kind": binding.kind if binding is not None else ""}


# ── 6C：85~95%「準備下一次 reset」那一帶真的要做的事（R84／SA-03）────────────────
# 🔴 立案（SA 合成 86% 快取走真閘實測，逐字）：`event=PostToolUse tool=Read rc=0
# stderr_bytes=0 plan_writer_calls=0`；`event=PreToolUse tool=Read rc=0 stderr_bytes=0`。
# 對照 96%：`PostToolUse rc=2 stderr_bytes=569 plan_writer_calls=1`。
# 也就是說 prepare 帶今天唯一真的會發生的事，是 PreToolUse×`Workflow` 被擋
# （`UNBOUNDED_FANOUT_TOOLS` 實測只有這一個成員）；`Task`／`Agent`／`Read` 在 86% 全部
# 靜默放行，訴求 6C 要的「提前準備下一次 reset」**一份任務書都沒有**，而外觀與「額度
# 很健康」完全相同。R83 交棒書把射程記成只有 PostToolUse，實測是兩個事件都靜默。
# 🔴 為什麼**不**在這一帶回 2：85% 不是停止水位，擋下收斂型工作會讓人連收斂都做不完
#   （本 repo 判過「擋到讓人無法工作的守衛會被整個關掉」）。這一帶要的是**出聲＋留下
#   可重啟點**，節流本身仍由既有的 cap／派發帳承接（prepare 帶 cap=2 已經在擋 Workflow）。
def quota_prepare_message(decision: quota_policy.Decision, plan: str, now: datetime) -> str:
    """prepare 帶那一次性的訊息。**不擋任何東西**，只說話 ＋ 指向已落磁碟的任務書。"""
    return (f"🟡 額度進入**準備**水位（85~95%）⇒ 現在就收斂，別開新戰場。\n"
            f"   {quota_policy.describe(decision)}\n"
            f"   可重啟點任務書：{plan or '（寫不出來——逐字稿路徑不可得）'}\n"
            + throttle_horizon_line(decision, now)
            + "   下一步：把手上的工作收到可重啟點（工作樹狀態確定／任務書落磁碟），"
              "現查還能派幾個：`python tools/session_resume_planner.py --pace`。\n")


# 🔴 binding 一律具名（SA-06）：此前它恆是資訊量最低的那一軸（cap 平手時期程不明的軸
# 必勝，實測 live 快取 `binding=nimbus_quill`＝0%、reset 不明、完全不消耗），於是真正的
# 約束（weekly 那一族）在訊息裡不具名。`_binding_key` 已同輪修好，這裡只負責呈現。
#: 🔴 R96／B-2：`--pace` 印的「現在可派幾個」此前**沒有扣掉本視窗已用次數**。實測（R96
#: 收尾當回合）：`--pace` 印「現在可派 2 個 agent（硬上限 cap=2）」的同一刻，`Agent` 被
#: `quota_gate()` 擋下、理由逐字是「每 300s 最多 2 次扇出，本視窗已用 2 次 ⇒ 不執行」。
#: 根 CLAUDE.md〈現查指令速查表〉明文要求「**派工前**問『現在能派幾個 agent』→ `--pace`」
#: ⇒ 官方指定的派工前置出口會給出一個當場就會被守衛擋下的數字。成因是兩個出口讀不同的
#: 東西：本行讀 cap 側（`recommended_fanout`），守衛讀滾動視窗派發帳（`live_dispatches()`）。
#: 🔴 **cap 與 live 兩個原始值都必須留在畫面上**（QA 具體要求）：只印差值時，「cap 很寬但
#: 這個視窗剛好用滿」與「cap 本來就是 0」在畫面上同形，而那兩件事要 operator 做的事不同
#: （前者等幾分鐘就好、後者要去看水位／提額）。
#: 🔴 free 帶（`cap is None`）措辭**逐字不變**：那一帶沒有滾動視窗預算（`quota_gate()` 對
#: `cap is None` 直接早退、連派發帳都不記），印一個 `cap − live` 就是替一道不存在的節流
#: 編數字——同本檔對 `model_hint_line()` free 帶的既有處置（「印出來就是一句假話」）。
#: 🔴 **為什麼是 `min(rec, cap−live)` 而不是逐字的 `cap−live`**（與複審建議的差異，照實記）：
#: 純差值在「視窗還空著、但配速建議比 cap 低」時會把畫面數字**放大**（實測 cap=4／live=0
#: ／rec=2 ⇒ 差值印 4、今天印 2）——那一格從來沒有壞過，而放大是本檔唯一不准無證據發生的
#: 方向（同 `quota_policy.decide()` 對攤提夾 0 的判詞）。取 min 之後兩個病都不在：畫面數字
#: 恆 ≤ 守衛真的會放行的量（`live_dispatches() >= cap` 即擋），也恆 ≤ 配速建議（R86 攤提
#: 那條軸不被本行悄悄繞過）。`live == cap` 時 min 的結果仍是 0，QA 指名的跨層對帳鎖照樣成立。
#: 🔴 R96 二審（SD／QA 各自獨立注射命中同一個缺口）：上面這一整段辯護在寫下的當時**零觀測
#: 者**——把本行改成純差值 `max(0, cap - live)`，R96 新增的四支全部 GREEN。結構成因是
#: `test_a_full_window_reads_as_zero_on_both_sides` 刻意構造 `live == cap`，而**在那一格
#: `min(rec, cap−live)` 與純差值同為 0** ⇒ 兩式在唯一被斷言的格子上重合，其餘三支一支都不
#: 碰 `--pace` 的數字。⇒ 公式本身現由
#: `test_context_budget_guard.py::WindowUsageIsToldTheSameWayByBothOutletsTest::
#: test_an_empty_window_is_paced_by_the_recommendation_not_by_the_raw_cap` 直接釘住（兩格
#: ＋兩道前提斷言，三種實作各自都會被打紅；紅端自證見該 docstring）。
#: 🔴 `live` **刻意沒有預設值**（R96 二審／SD）：漏傳的新呼叫端會印「本視窗已用 **0** 次」
#: ——那正是第一輪 D1 修掉的那個形態（本檔判例逐字：「訊息裡混一句假話比少一欄更難看見」），
#: 而預設值讓同一個病復發時**外觀與正確輸出相同**。拿掉之後它變成 `TypeError`：全 repo 只有
#: 兩個呼叫端（`quota_gate.pace_report()` 與本族的渲染鎖），兩者本來就顯式傳值 ⇒ 零成本。
def pace_line(decision: quota_policy.Decision, live: int, max_fanout: int) -> str:
    """**一行**：能派幾個／cap／band／距 reset／binding 是哪一軸（SA-02 要的五項）。
    `max_fanout` 必填（同 `live`）：擋不了人的兩種 cap 要連同它的值說出口（見本輪證據檔〈九〉）。"""
    if decision.cap is None:
        head = (f"現在可派 {decision.recommended_fanout} 個 agent（硬上限 cap=不設限）"
                f" ⇒ 這一格結構上不擋任何扇出（節流由 rec 諮詢值承擔；max_fanout={max_fanout}）")
    else:
        left = min(decision.recommended_fanout, max(0, decision.cap - live))
        head = (f"現在可派 {left} 個 agent（硬上限 cap={decision.cap}，"
                f"本視窗已用 {live} 次）")
        if decision.cap >= max_fanout:
            head += f" ⇒ cap 已等於 max_fanout={max_fanout}，等同無節流"
    head += f"｜band={decision.band}"
    axis = decision.binding
    if axis is None:
        return head + "｜**量不到任何一軸**（這不是「額度很寬鬆」）"
    when = next((f"剩 {int(r.minutes)} 分鐘" for r in decision.per_axis
                 if r.axis is axis and r.minutes is not None), "reset 距離不明")
    return head + f"｜最緊的一條＝{axis.kind} {axis.pct:g}% {when}"


def posture_line(path: Path) -> str:
    """派工**前置檢查**那一行：帳號指紋 ＋ credits 姿態（R87／`DEF-200-R87-spend`）。

    🔴 掌舵者裁決逐字：「配置 Agents 前，要先知道 Account Type and Account 是否有
    Usage credits 再進行配置」。事故當下 `--pace` 只講得出水位，講不出
    「訂閱窗用完之後還有沒有救」——而後者才是 13 個 subagent 全滅的直接原因。

    🔴 三種讀不出來的情形一律回報**無 fallback**（保守方向）：快取不可用、
    取數層版本較舊（沒有 `posture` 欄）、欄位形狀不對。「量不到 ≠ 量到零」。
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        posture = data["posture"]
        fingerprint = tuple(posture["plan_fingerprint"])
    except (OSError, ValueError, KeyError, TypeError):
        return "派工前置：帳號姿態讀不出來 ⇒ 一律當作**無 credits fallback**（保守）"
    if not posture.get("credits_present"):
        state = "此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆"
    elif posture.get("fallback_available"):
        state = "credits **可用** ⇒ 訂閱窗用完後仍有 fallback"
    else:
        why = "已耗盡" if posture.get("credits_exhausted") else ""
        why += "、" if why and not posture.get("credits_enabled") else ""
        why += "已停用" if not posture.get("credits_enabled") else ""
        state = f"credits {why} ⇒ **無 fallback**，訂閱窗即硬牆"
    return f"派工前置：方案指紋={'+'.join(fingerprint) or '(空)'}｜{state}"


# 🔴 `DEF-200-169`：扇出滾動視窗那一行的**渲染面**。取數／推算住 `quota_gate.
# fanout_window_left()`（那裡才碰得到派發帳與 `FANOUT_WINDOW_SECONDS`）；本檔只把它講成人話。
# 🔴 `window` 是**參數**而不是 import：`FANOUT_WINDOW_SECONDS` 住 `quota_gate`，而本檔
# 依檔頭那條單向規則**不得** import 它（會成環）。同 `quota_throttle_message()` 留在
# `quota_gate` 的理由，只是方向相反：那一支搬不過來，這一支把常數當參數收進來。
# 🔴 三支分支的字串**必須彼此不同**（同 `quota_halt_message()` 的既有不變式）：
# 「量不到」與「視窗全空」在畫面上同形，就等於把一個 fail-open 講成一句好消息。
# 🔴 措辭刻意不含「這道節流」——那個字面是額度軸節流期程句的專屬字樣，free 帶對它有
# 具名的 `assertNotIn` 對照組（`test_a_free_band_keeps_its_own_wording` 同族），而本行
# 在**每一帶**都會印（滾動視窗與額度帶無關），混用會讓那道對照組的語意漂掉。
def fanout_window_line(left: tuple | None, live: int, window: int) -> str:
    """扇出視窗那一行：`left` 直接吃 `quota_gate.fanout_window_left()` 的三態回傳值。"""
    if left is None:
        return (f"   ⏱ 扇出視窗：派發帳原語不可達 ⇒ 這 {window}s 視窗**量不到**"
                "（不是「還很空」）\n")
    seconds, age = left
    if seconds is None:
        return f"   ⏱ 扇出視窗：{window}s 內帳上 0 筆 ⇒ **視窗全空**，現在派不必等\n"
    return (f"   ⏱ 扇出視窗：剩 {seconds} 秒（帳上 {live} 筆，最舊 {age} 秒前）⇒ 再等 "
            f"{seconds} 秒，最舊那筆就滾出 {window}s 視窗、釋出 1 個名額\n")


# 🔴 R95／PRD §4.2.3 第 7 步的人話面：模型降級**建議**行。觸發判定住 `quota_policy.
# decide()`（converge 帶起、或模型分軌 kind 進 notice 帶起），這裡只渲染。空 hint ⇒
# 空字串——free 帶印一行降級建議就是一句假話（「訊息裡混一句假話比少一欄更難看見」）。
# 方向鎖：cap／rec 在 `decide()` 內先算完才產生 `model_hint`，本行結構上改不動任何節流。
def model_hint_line(decision: quota_policy.Decision) -> str:
    """`--pace` 的降級建議行。收緊帶才出現；只建議、不自動改任何模型設定。"""
    if not decision.model_hint:
        return ""
    return (f"   🔻 降級建議：kind={decision.model_hint} 已進收緊帶 ⇒ 建議派工帶 "
            "model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。\n")


# 🔴 R93／DEF-200-122：Plan B 的「出聲」半邊（SA 裁決保留，不做狀態檔輪替）。純渲染，
# 讀落款最後一列的指紋與這次的指紋比對，不落任何新狀態檔。
def core_signature_change_note(last_fp, current_fp: tuple) -> str:
    """換方案的一行提示。`last_fp is None`（史上第一筆／全是舊格式列）⇒ 沒有基準，不出聲。"""
    if last_fp is None or tuple(last_fp) == tuple(current_fp):
        return ""
    old_s, new_s = "+".join(last_fp) or "(空)", "+".join(current_fp) or "(空)"
    return f"⚠️ 偵測到帳號軸組合改變（{old_s} → {new_s}）：攤提正在用新樣本重新累積\n"
