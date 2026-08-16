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
    horizon = reset_horizon_phrase(act["branch"], binding_resets_at(decision))
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
    resets_at = binding_resets_at(decision)
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
def pace_line(decision: quota_policy.Decision) -> str:
    """**一行**：能派幾個／cap／band／距 reset／binding 是哪一軸（SA-02 要的五項）。"""
    head = (f"現在可派 {decision.recommended_fanout} 個 agent（硬上限 cap="
            f"{'不設限' if decision.cap is None else decision.cap}）"
            f"｜band={decision.band}")
    axis = decision.binding
    if axis is None:
        return head + "｜**量不到任何一軸**（這不是「額度很寬鬆」）"
    when = next((f"剩 {int(r.minutes)} 分鐘" for r in decision.per_axis
                 if r.axis is axis and r.minutes is not None), "reset 距離不明")
    return head + f"｜最緊的一條＝{axis.kind} {axis.pct:g}% {when}"


# 🔴 R93／DEF-200-122：Plan B 的「出聲」半邊（SA 裁決保留，不做狀態檔輪替）。純渲染，
# 讀落款最後一列的指紋與這次的指紋比對，不落任何新狀態檔。
def core_signature_change_note(last_fp, current_fp: tuple) -> str:
    """換方案的一行提示。`last_fp is None`（史上第一筆／全是舊格式列）⇒ 沒有基準，不出聲。"""
    if last_fp is None or tuple(last_fp) == tuple(current_fp):
        return ""
    old_s, new_s = "+".join(last_fp) or "(空)", "+".join(current_fp) or "(空)"
    return f"⚠️ 偵測到帳號軸組合改變（{old_s} → {new_s}）：攤提正在用新樣本重新累積\n"
