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
  · `pace_report()`／`pace_state()`／`posture_line()` — 前兩者讀快取、記燃燒帳、寫檔案
    契約（狀態與 IO 層）；`posture_line()` 讀 `quota_cache_path()`。三者都不是純渲染。

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

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # 排程載具：拿不到時只影響 `evidence_hint()` 那一句，不影響其餘渲染
    import schedule_backend  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    schedule_backend = None  # type: ignore[assignment]

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


# 憑證是真的、**指路是假的**——那個 cmdlet 在 mac 不存在，而 `NextRunTime` 這個概念 launchd
# 從不提供（`launchctl print` 輸出裡 next／fire／due 皆不存在，R83 實測）。同型判例：
# 「憑證裡混一句假話，比沒有那一欄更難看見」（`schedule_backend._readback` 的 depth-1 訂正）。
def evidence_hint() -> str:
    """「怎麼查它真的排進去了」——唯一的家＝本機那個排程後端。"""
    return (schedule_backend.select().evidence_hint() if schedule_backend is not None
            else "排程載具不可達（import 失敗）⇒ 本工具**說不出**取證指令；"
                 "在拿到憑證之前不要把它當成已排程。")


def reset_horizon_phrase(branch: str, resets_at: object) -> str:
    """三支分支各自的「這條線的 reset 有多遠」——**唯一的家**（R82／Q2-07 的減法那一半）。

    🔴 halt 與 throttle 此前各自寫了一份幾乎逐字相同的三分支句子（含兩處硬寫的 URL），
    而既有鎖只認「沒有 reset 可以等」這個字樣、不認結構 ⇒ 兩份漂移不會有任何東西轉紅。
    收成一份之後，兩支呼叫端各自只補**自己的動作句**（halt＝排程是錯的動作、
    throttle＝這道節流不會自己解除），三支分支的字串仍**彼此不同**——那條不變式
    （否則「不排程」與「排不了」外觀相同）是被保留的，不是被參數化掉的。
    """
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：{USAGE_URL}"
    hours = RESET_ARM_HORIZON_SECONDS // 3600
    if branch == QUOTA_BRANCH_NOTIFY:
        return f"reset 在 {resets_at}（**遠超 {hours} 小時**）"
    return f"reset 在 {resets_at}（{hours} 小時內）"


# 🔴 **開頭不再印裸百分比**（R82／M7）：舊版第一行是「額度水位 54%（≥95%…）」，而裸的
# 「54%」正是掌舵者當場誤讀的**那個**形狀——那個數字沒有說自己是哪一桶、什麼時候 reset。
# 改由 `quota_policy.describe()` 逐軸渲染，每一個 % 都自帶 `kind=` 與剩餘分鐘（或明文
# 「reset 距離不明」），而且**每一軸都說**，不是只說最緊的那一格。
def quota_halt_message(decision: quota_policy.Decision, act: dict) -> str:
    """halt 的一次性訊息。三支分支**字串必須不同**，否則「不排程」與「排不了」外觀相同。"""
    head = (f"🔴 額度到達**停止**水位（最緊的一條＝{act['kind'] or '未知'}）⇒ **停止派發**："
            "扇出型工具一律不執行；收斂（讀檔／寫檔／跑 git）不受影響。\n"
            f"   {quota_policy.describe(decision)}\n"
            f"   任務書：{act['plan'] or '（寫不出來——逐字稿路徑不可得）'}\n")
    # 修4：期程句印**被選中的** reset（≥halt 最早可 reset 軸），不再印 binding 的 None。
    horizon = reset_horizon_phrase(act["branch"], halt_resets_at(decision))
    if act["posix"]:
        # 🔴 SA-B7：沒有排程載具的平台若沿用 weekly 那支「不排程」的靜默路徑，
        # 「不排程」與「排不了」會長得一模一樣。
        # 🔴 R83／F2-② 訂正本句的平台清單（原文寫「schtasks 只在 Windows 成立…mac/Linux
        # 請自行以 launchd／cron 掛」——R83 已把 mac 接上 launchd ⇒ `posix` 這個鍵在 mac
        # 上是 False，這一支**走不到** mac；把 mac 寫在這裡是拿過期事實當指引）。
        return head + ("   ⚠️ 本平台**沒有排程載具**（Windows 走 schtasks、macOS 走 "
                       "launchd，本平台兩者皆無）⇒ 已寫任務書，但**沒有武裝任何喚醒**。"
                       "請自行以 cron／systemd-timer 掛，或留在這裡等人回來。\n")
    if act["branch"] == QUOTA_BRANCH_ARM and act["armed"]:
        return head + f"   ✅ 已武裝喚醒（{horizon}）。{evidence_hint()}\n"
    if act["branch"] == QUOTA_BRANCH_ARM:
        return head + ("   ⚠️ 這一條的 reset 近在眼前、本來該武裝喚醒，但**這次沒有武裝**："
                       + ("哨兵逃生口有設（AUTOSDD_SENTINEL_OFF）。\n" if act["sentinel_off"]
                          else "拿不到逐字稿路徑 ⇒ 沒有可以掛的任務書。\n"))
    if act["branch"] == QUOTA_BRANCH_NOTIFY:
        return head + (f"   🔴 這一條的 {horizon} ⇒ 「等」幾乎沒有意義，"
                       "本次**刻意不排程**（排一支七天後才響的工作而痕跡全綠＝R59 事故同形）。"
                       "改做不吃額度的工作，或降扇出／切小模型。\n")
    return head + (f"   🔴 這一條{horizon} ⇒ 排程是錯的動作，"
                   "只有人去提額才會回來。\n")


# halt 帶用 `reset_branch()` 分得出 arm／notify／escalate，**throttle 帶此前完全不分**
# ⇒ 週額度偏高時 cap 會連續套用好幾天，與 five_hour 同水位（最多 5 小時）代價差一個
# 數量級，而訊息裡讀不出差別。
# 🔴 R82 訂正本段的舊結語（原文寫「本行只把差別說出來，**不動 cap 的階梯**，因為按 reset
# 距離分檔是政策決定」——那句話已被裁決推翻，故不留著當現行說法）：cap 現在**本來就**是
# `f(pct, horizon)` 的函式，reset 距離已經進了階梯本身；本行說的是同一件事的人話面，
# 兩者同源於 `quota_policy`，不是兩個判準。
def throttle_horizon_line(decision: quota_policy.Decision, now: datetime) -> str:
    """節流帶要說出「這道限制會套多久」。"""
    # 修4：halt 帶改讀多軸選擇——撞牆期間人唯一持續看得到的就是這一則（R89 判例），
    # binding 無 reset 時印「不會自己解除」而喚醒其實已武裝＝訊息說假話。
    resets_at = (halt_resets_at(decision) if decision.band == quota_policy.BAND_HALT
                 else binding_resets_at(decision))
    branch = reset_branch(resets_at, now)
    horizon = reset_horizon_phrase(branch, resets_at)
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"   ⏳ 這一條{horizon} ⇒ 這道節流不會自己解除。\n"
    if branch == QUOTA_BRANCH_NOTIFY:
        return (f"   ⏳ 這一條的 {horizon} ⇒ 這道節流會**連續套用好幾天**，不是等一下"
                "就好。改做不吃額度的工作，或降扇出／切小模型。\n")
    return f"   ⏳ 這一條的 {horizon} ⇒ 這道節流很快就會自己解除。\n"


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
#: 那條軸不被本行悄悄繞過）。`live == cap` 時 min 的結果仍是 0，QA 指名的跨層對帳鎖不受影響。
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
def pace_line(decision: quota_policy.Decision, live: int) -> str:
    """**一行**：能派幾個／cap／band／距 reset／binding 是哪一軸（SA-02 要的五項）。"""
    if decision.cap is None:
        head = f"現在可派 {decision.recommended_fanout} 個 agent（硬上限 cap=不設限）"
    else:
        left = min(decision.recommended_fanout, max(0, decision.cap - live))
        head = (f"現在可派 {left} 個 agent（硬上限 cap={decision.cap}，"
                f"本視窗已用 {live} 次）")
    head += f"｜band={decision.band}"
    axis = decision.binding
    if axis is None:
        return head + "｜**量不到任何一軸**（這不是「額度很寬鬆」）"
    when = next((f"剩 {int(r.minutes)} 分鐘" for r in decision.per_axis
                 if r.axis is axis and r.minutes is not None), "reset 距離不明")
    return head + f"｜最緊的一條＝{axis.kind} {axis.pct:g}% {when}"


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
