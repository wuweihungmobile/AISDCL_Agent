"""哨兵的**生命週期**：什麼樣的 session 值得一支 schtasks，什麼時候該把它收掉（回收側）。

武裝側完整的立案脈絡、門檻量測依據（`MIN_TURNS`／`MIN_SPAN_SECONDS` 怎麼量出來的）、
以及「為什麼判準不能長在 SessionStart」「閂鎖為何是一個檔案」的設計討論，已依內聚子
功能搬到 `tools/lib/sentinel_lifecycle_arm.py`（LOC 分級收斂，guardrail_lib ≤400 行棘輪
見 `check_loc_budget.py` 的 `[ROOT-TOOLS-WARN]`）；本檔只 `import` 委派，公開函式的
簽章與行為完全不變。本檔開頭以下只留**回收側**自己的設計討論。

🔴 R83 複審 A-01：本檔的「回收側」曾經一行都沒接上（武裝接通、回收沒接）
--------------------------------------------------------------------
落地當時本檔對 `tools/lib/schedule_backend.py` 的 import 數是 **0**：`sentinel_task_names()`
與 `_remove_task()` 自己硬寫 `powershell.exe`，於是在 mac 上實測 `_powershell` rc=**127**、
`sentinel_task_names()` 回 `[]`、`_remove_task()` 回 127，而同一刻 `launchctl list` 列著活著
的哨兵（每 900s 巡邏、永不自我解除）。**最貴的一半是回報**：GC 逐字印「（沒有任何
AutoSDD_Sentinel_* 工作…）」＝假陰性——專門用來發現增生的那支工具說一切正常。
處置（本輪）：列舉與移除**一律問 `schedule_backend.select()`**，本檔一行平台知識都不留；
並把「量不到」與「量到零」在列舉層分開（`None` vs `[]`），與下面 `reap_verdict` ② 同一條
紀律。附帶的減法：本檔那支 `_powershell` 整支刪除——它本來就是 `planner.run_powershell`
的第二個家（同一份知識：`powershell.exe` 5.1、`NO_WINDOW`、UTF-8 前置行、BOM+CRLF 落檔）。

回歸鎖：`tools/tests/test_context_budget_guard.py`（判準的紅綠、GC 的保護面，皆合成注入）
＋ `tools/tests/test_mac_endurance_r83.py`（回收臂真的接上 `select()`、列舉層的 None/[] 之別、
以及「排程器原語只有宣告過的家」那道全庫判準）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import endurance_env
import harness_feed
import quota_meter
import schedule_backend
from sentinel_lifecycle_arm import (
    ARM_MARKER_PREFIX,
    MIN_SPAN_SECONDS,  # noqa: F401  ← 再匯出
    MIN_TURNS,  # noqa: F401  ← 再匯出
    arm_marker_path,
    clear_arm_latch,  # noqa: F401  ← 再匯出
    maybe_arm,  # noqa: F401  ← 再匯出
    session_evidence,  # noqa: F401  ← 再匯出
    should_arm,  # noqa: F401  ← 再匯出
)

#: GC 判「這個 session 真的結束了」的閒置門檻。**刻意等於哨兵自己的自我解除門檻**
#: （`session_resume_planner.SENTINEL_IDLE_SECONDS`＝6 小時＞一個完整額度視窗）：
#: 比它短，GC 會在哨兵還在等額度回來時把它拆掉——那正是續航要防的事。
GC_IDLE_SECONDS = 6 * 3600.0

#: 任務書狀態塊的**終態**（工作已經結束，哨兵留著只是死工作）。
#: 🔴 R97（round-label-ok：非帳本追蹤的正式輪，僅沿用便於追蹤的標籤）：`resume_failed`＝`_run_resume()` 的 `subprocess.run` 本身炸掉（例外，不是  # noqa: E501
#: `claude` 自己的非零 rc）——同 `resumed` 一樣不會再被重試（`-Once` 觸發器已燒過），
#: 故同屬終態；漏列會讓 GC 把它誤判成「可能還在等額度」而永遠不收。
TERMINAL_STATES = frozenset({"disarmed", "abandoned", "resumed", "resume_failed", "done"})

#: 「閒置夠久就可以收」的狀態集合＝終態 ＋ **巡邏中**（`armed`／`sentinel`）。
#: 🔴 為什麼巡邏中的也算（本輪實跑 dry-run 才發現第一版漏了它）：一支 `armed` 的哨兵
#: 在逐字稿閒置達門檻時，**它自己的 `disarm` 分支下一次醒來就會把自己拆掉**（同一個
#: 6 小時門檻）⇒ GC 收它不會比它自己做的更激進，只是不必等下一次醒來。
#: 🔴 而 `waiting`（撞線了、正在等 reset）**永遠不收**：那段期間逐字稿本來就不會更新，
#: 只看閒置會把「正在等」誤判成「結束了」，而那是這整套續航唯一有價值的時刻。
#: 刻意用**列舉**而不是「不是 waiting 就收」：日後若長出新的等待型狀態，未列舉者一律
#: 落在「不收」那一側（未知 ⇒ 不動，與 `reap_verdict` ② 同一條紀律）。
REAPABLE_WHEN_IDLE = TERMINAL_STATES | frozenset({"armed", "sentinel"})

#: 哨兵工作名前綴（與 `session_resume_planner.sentinel_task_name` 同一個字面）。
TASK_PREFIX = "AutoSDD_Sentinel_"

# 🔴 **本檔曾經持有 `NO_WINDOW` 與 `PS_UTF8_PRELUDE` 兩個字面複本，本輪整組刪除**（墓碑）。
# 沿革：它們的唯一消費者是 R83 複審 A-01 收斂時整支刪掉的那個 `_powershell`（載具已交回
# `schedule_backend`／`planner.run_powershell`）⇒ 常數自那一刻起零消費者。當時**沒有**一併
# 刪掉，理由逐字寫著「相等鎖的另一端住 `tools/tests/test_context_budget_guard.py`，而那一檔
# 不在本包的授權面」，並附了可執行的達成判準（把 `"sentinel_lifecycle"` 從該測試的兩份名冊
# 移除、同輪刪掉兩個常數與 `subprocess` import）。
# 🔴 那句「不在授權面」在**下一包**（R83／PD 獨立驗證）就不再成立——兩支檔同時在射程內，
# 於是那段話從「誠實劃界」變成「一個會叫下一個人去繞路的過期約束」（與本輪 FC-1 判過的
# `arm_quota_wakeup` docstring 逐字同型：宣稱一件已經可以做／已經做完的事還做不到）。
# ⇒ 依它自己寫的判準結清。🔴 **判準本身也一併訂正**：原文寫的達成判準是
# 「`grep -c "NO_WINDOW\|PS_UTF8_PRELUDE" tools/lib/sentinel_lifecycle.py` ＝ 0」，而那個
# 數字在**任何**留有墓碑的世界裡都不是 0（本段自己就命中 3 次）⇒ 照抄它的人會判本輪沒做完。
# 可機械重跑的判準改成具名測試：`tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest
# ::test_the_duplicated_no_window_expression_still_equals_the_ssot` 內的反向釘（兩個名字
# `hasattr` 皆須為 False）——**加回來而不進相等鎖名冊就會紅**，這比數字元次數有鑑別力。
# 相等鎖仍有 `quota_meter`／`console_spawn_watch` 兩端在守 `guard` 那份 SSOT；掃描面檔數
# （`_CONSOLE_FREE_FLOOR`）不受影響——它由 glob 決定，與本檔 import 什麼無關。


# ───────────────────────────────────────────── 武裝側（`sentinel_lifecycle_arm` 委派，見上）
# `session_evidence`／`should_arm`／`arm_marker_path`／`clear_arm_latch`／`maybe_arm`／
# `MIN_TURNS`／`MIN_SPAN_SECONDS`／`ARM_MARKER_PREFIX` 一律從該檔 import（見檔頭），
# 本檔不重寫第二份邏輯。


# ──────────────────────────── SessionStart 交接可見性（v2.1.13 G2 批 (b)，施工圖 §3(b)5）
# 落點 WHY：SessionStart 的 additionalContext 只能由 hook 行程自身 stdout 發出，而
# `context_budget_guard.py` raw-line 棘輪餘裕 0 ⇒ 邏輯本體住本檔（hook 已 import 的家族），
# hook 側只接一行線。判準面（marker／目錄解析）住 `resume_route`→`endurance_env`，本檔
# 不抄第二份；`.ack` sidecar＝「人已看過」的磁碟憑證，同名換副檔名（`<sid>.md`→`<sid>.ack`）。
def announce_handbacks(emit, base: Path | None = None) -> str:
    """SessionStart 臂：未讀 handback（無 `.ack` sidecar）⇒ `emit` 出聲＋落 `.ack`；回出聲文字。

    · `emit` 回 False（訊息沒被排入）⇒ **不落 `.ack`**：下一個 session 再說一次——寧可
      重複出聲，不可靜默吞掉交接（「沒觸發＝可偵測」同向）。誠實劃界：`emit_to_model`
      是排隊、flush 在 atexit，「排入」是本層可驗的最強憑證，flush 失敗那一半本層看不見。
    · 永不拋例外、壞掉退安靜（回 ``""``）：hook 誤觸鎖死所有工具是判過的 P0
      （同 `spawn_sentinel` 取捨③）；lazy import 的理由同 `_planner_module()`。
    """
    try:
        import resume_route  # noqa: PLC0415 — 見 docstring（lazy：壞掉不得拖垮武裝側）
        home = base if base is not None else resume_route.handback_dir()
        rows = [p for p in sorted(home.glob("*.md"))
                if not p.with_suffix(".ack").exists()]
        if not rows:
            return ""
        text = "\n".join(_handback_note(p) for p in rows)
        if not emit(text):
            return ""
        for report in rows:
            with report.with_suffix(".ack").open("w", encoding="utf-8", newline="\n") as f:
                f.write(f"acked {time.time()}\n")
        return text
    except Exception:  # noqa: BLE001 — 見 docstring
        return ""


def _handback_note(path: Path) -> str:
    """一支 handback 檔的出聲摘要：檔名＋「## 做了什麼」首行＋「## 下一步指令」節全文。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    did = next((ln for ln in _section(text, "## 做了什麼").splitlines() if ln.strip()), "")
    nxt = _section(text, "## 下一步指令")
    return (f"🔴 未讀 handback（無頭續跑窗口的交接檔）：{path}\n"
            f"  做了什麼：{did or '（節空白）'}\n  ## 下一步指令\n{nxt or '（節空白）'}")


def _section(text: str, heading: str) -> str:
    """取 `heading` 之後、下一個 `## ` 之前的內容（不含標題行；找不到標題回 ``""``）。"""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == heading]
    if not starts:
        return ""
    start = starts[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")),
               len(lines))
    return "\n".join(lines[start:end]).strip()


# ───────────────────────────────────────────────────────── 回收側（CLI，hook 不會呼叫）
def sentinel_task_names() -> list[str] | None:
    """現存的哨兵工作名；`None`＝**量不到**（載具不可達／列舉指令 rc 非 0）。

    🔴 列舉原語由**排程後端**提供（`schedule_backend.select().list_jobs()`）——本檔一次都不問
    `os.name`、也不自持任何 `powershell.exe`／`launchctl`。R83 複審 A-01 的病正是這裡：修前
    它硬寫 `Get-ScheduledTask`，mac 上 rc=127 ⇒ 回 `[]`，而 `[]` 與「真的沒有哨兵」外觀相同
    ⇒ GC 回報一切正常，同一刻排程器裡有活著的哨兵。
    🔴 回 `None` 而不是 `[]` 是這一支的**全部價值所在**：假陰性在列舉層特別貴（查不到＝
    「沒有東西要收」），與下面 `reap_verdict` ② 的判例逐字同型（量不到 ≠ 量到零）。
    """
    return schedule_backend.select().list_jobs(TASK_PREFIX)


def session_of(task_name: str) -> str:
    return task_name[len(TASK_PREFIX):] if task_name.startswith(TASK_PREFIX) else ""


# ── 修3（R95；ADR-XPLAT-004 §2.9）：哨兵活性欄——armed stamp 對排程器現查的對比 ──
# 立案：2026-08-17 00:55 哨兵自我解除後，03:50 reset 時機器上零排程、空轉八小時；
# 期間 `--pace`／`--check` 照常回報額度與水位，沒有任何出口說「哨兵已經死了」。
# 對比的兩端都是既有讀數：stamp（`maybe_arm` 落款）＝「宣稱武裝過」，`list_jobs()`
# （平台各自的載具：Win＝Get-ScheduledTask、mac＝launchctl list）＝「現在還在不在」。
# 警語裡的查法向 `schedule_backend.select().evidence_hint()` 要（R-4.5.6-6：mac 憑證＝
# launchctl print 的 rc、Win＝NextRunTime 值——平台各一條住後端，本層不複寫）。
def liveness_problem(session_id: str, stamped: bool, jobs: list[str] | None) -> str:
    """純判準：不一致回警語；一致或本 session 沒宣稱過武裝時回 ``""``（安靜）。"""
    task = TASK_PREFIX + session_id
    if not stamped:
        return ""
    if jobs is None:
        return (f"⚠️ 哨兵活性：{task} 有 armed stamp，但排程器**列舉不到**（量不到 ≠ 沒有）。請以載具現查：{schedule_backend.select().evidence_hint()}")  # noqa: E501
    if task in jobs:
        return ""
    return (f"🔴 哨兵活性：armed stamp 說 {task} 已武裝，排程器現查卻沒有這支工作 ⇒ 哨兵已死、喚醒鏈斷線（2026-08-16 事故形狀）。重新武裝：python tools/session_resume_planner.py --arm-sentinel；取證：{schedule_backend.select().evidence_hint()}")  # noqa: E501


def liveness_line(session_id: str) -> str:
    """接線層：本機 stamp ＋ 載具現查餵給純判準（`--pace`／`--check` 共用這一個家）。"""
    return liveness_problem(session_id, arm_marker_path(session_id).exists(),
                            sentinel_task_names())


# PRD §4.5.8（v2.1.7）：`liveness_problem()` 的布林版——`quota_escalation.
# _heal_armed_drift()` 拿它決定該不該自動重新武裝，不必自己解析上面那兩則警語字串。
def armed_but_missing(task: str, jobs: list[str] | None) -> bool:
    """排程器**確定**查得到清單、但這支不在裡面 ⇒ 真漂移（`jobs is None`＝量不到，不算）。"""
    return jobs is not None and task not in jobs


def plan_evidence(plan: Path) -> tuple[str, str | None]:
    """任務書狀態塊裡的 `(transcript, state)`；讀不出來回 `("", None)`（＝「量不到」非「終態」）。

    🔴 ARCH-01（DEF-200-455 同根）：`transcript` 是哨兵武裝時寫進狀態塊、**它自己盯的**
    逐字稿絕對路徑（planner 的 `_sentinel_tick`／`_run_resume` 讀的也是這一格）＝GC 的**所有權
    證明**。GC 的目標（launchd／schtasks 工作）是 per-user 全域的，證據就必須和目標一樣全域；
    呼叫者 HOME 下的專案目錄只是本地證據，拿它判別人的哨兵＝隔離 HOME 下全機活哨兵被 bootout。

    解析走 planner 的 `parse_relay`（**唯一的家**，本檔不抄第二份格式知識）。
    lazy import：planner 會把 `.claude/hooks` 接進 `sys.path` 並 import 整條 hook 鏈，
    而本模組被那條鏈 import ⇒ 放在模組層會成環。放在函式內，hook 路徑一次都碰不到它。
    """
    planner = _planner_module()
    if planner is None:
        return "", None
    try:
        relay = planner.parse_relay(plan.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 讀不到就當「量不到」，判準那一側自己會保守處理
        return "", None
    if not isinstance(relay, dict):
        return "", None
    return str(relay.get("transcript") or ""), str(relay.get("state"))


def plan_state(plan: Path) -> str | None:
    """任務書狀態塊裡的 `state`；讀不出來回 `None`（＝「量不到」，不是「終態」）。"""
    return plan_evidence(plan)[1]


def reap_verdict(*, transcript_exists: bool | None, idle_seconds: float | None,
                 state: str | None, protected: bool,
                 min_idle: float = GC_IDLE_SECONDS) -> tuple[bool, str]:
    """純判準：這支哨兵可以收掉嗎。回 `(要不要收, 理由)`。

    順序即優先序，**最保守的先判**：
      ① 受保護（呼叫端指名 or 它是最近仍在寫的那一支）⇒ 絕不收。這一條擋在最前面，
         是因為誤收一支活著的哨兵＝把那個 session 的續航靜默弄丟，而弄丟是看不見的。
      ② `transcript_exists is None`（＝**量不到**：這支哨兵任務書記的逐字稿路徑取不到——任務書
         缺席／解析不出／沒有該欄／非絕對路徑）⇒ 絕不收。
      ③ 逐字稿（任務書記的那個絕對路徑）不存在 ⇒ 收（session 連檔都沒了，哨兵醒來也只會 fail-loud
         空轉）；**但**任務書狀態在 `REAPABLE_WHEN_IDLE` 之外（如 `waiting`）仍不收——與 ⑥ 同理，
         等額度期間不拆（ARCH-01 補的一道）。
      ④ 還在寫（閒置未達門檻）⇒ 不收。
      ⑤ 閒置達門檻 **且** 任務書是終態／根本讀不出來 ⇒ 收。
      ⑥ 其餘（閒置達門檻但狀態是 `waiting`／`sentinel`）⇒ **不收**：等額度的那段期間
         逐字稿本來就不會更新，這一格就是「不要在它最需要的時候把它拆掉」。

    🔴 ② 是本輪 dry-run 當場抓到的**我自己寫的缺陷**，照實留在這裡當判例：第一版把
    `transcript_exists` 宣告成 `bool`，於是「逐字稿目錄定位不到」（`_transcript_dir()`
    回 `None`）與「這個 session 的檔真的被刪了」擠進同一個 `False` ⇒ 實跑 dry-run 時
    **三支哨兵全被判為可收，包含當下正在跑的那一支**。這正是本 repo 通篇那條紀律
    （量不到 ≠ 量到零）在最貴的地方犯一次；而它之所以沒有變成事故，是因為這支工具
    預設 dry-run——那個設計決定在落地的當回合就付清了自己的成本。
    """
    if protected:
        return False, "protected（指名保留或逐字稿仍在寫）"
    if transcript_exists is None:
        return False, ("取不到這支哨兵任務書記的逐字稿路徑 ⇒ **量不到 ≠ 不存在**，一律拒絕回收"
                       "（任務書缺席／解析不出／沒有該欄，或 planner 載不進來）")
    if not transcript_exists:
        if state is None or state in REAPABLE_WHEN_IDLE:
            return True, "逐字稿不存在"
        return False, f"逐字稿不存在，但任務書狀態是 `{state}` ⇒ 可能還在等額度，不收"
    if idle_seconds is None or idle_seconds < min_idle:
        idle = "unknown" if idle_seconds is None else f"{idle_seconds / 3600:.1f}h"
        return False, f"逐字稿仍活躍（閒置 {idle} < {min_idle / 3600:.0f}h）"
    if state is None or state in REAPABLE_WHEN_IDLE:
        return True, f"閒置 {idle_seconds / 3600:.1f}h 且任務書狀態＝{state or '讀不出來'}"
    return False, (f"閒置已久，但任務書狀態是 `{state}`（不在可收清單內）"
                   "⇒ 可能還在等額度，不收")


def _planner_module():
    """lazy import `tools/session_resume_planner.py`；不可達回 `None`。

    🔴 `sys.path` 這一行不是防禦性程式碼：本檔以 `python tools/lib/sentinel_lifecycle.py`
    直跑時，直譯器只把 **`tools/lib`** 放進 `sys.path`，planner 住在它的**上一層** ⇒ 少了
    這一行 import 必失敗。而失敗的後果不是「少一個欄位」——見 `reap_verdict` ② 的判例。
    """
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        import session_resume_planner as planner  # noqa: PLC0415 — 見 docstring
    except Exception:  # noqa: BLE001
        return None
    return planner


def _transcript_dir() -> Path | None:
    """逐字稿目錄；`None`＝**定位不到**。現只供 `_newest_session()` 保護用；
    判決證據改走 `plan_evidence()`（哨兵自己任務書記的絕對路徑），不再以本目錄判孤兒。"""
    planner = _planner_module()
    if planner is None:
        return None
    try:
        return planner.project_transcript_dir(planner._REPO_ROOT)
    except Exception:  # noqa: BLE001
        return None


def _newest_session(base: Path | None) -> str:
    """「當前 session」的 id（DEF-200-478：判準唯一的家＝`harness_feed.pick_transcript()`，與
    `session_resume_planner.resolve_transcript()` 是同一個函式）：環境變數 `CLAUDE_CODE_SESSION_ID`
    對應的逐字稿優先（本 slug → 他 slug），沒有才退回最後修改的那一支（排程情境本來就沒有它）。

    🔴 這是 GC 的**安全底線**，不是便利功能：它讓「忘了加 --keep」不會演變成把正在跑的
    那一輪的續航拆掉。只看最後修改的舊版在多視窗下會保護到別人的 session（他窗一寫檔就成了
    「最後修改」，DEF-200-431 同型）。本 slug 目錄可以不存在（只從子目錄啟動過）：判準同 planner，
    上層 projects 目錄在即可跨 slug 找。
    """
    if base is None or not (base.is_dir() or base.parent.is_dir()):
        return ""
    found, _ = harness_feed.pick_transcript(base, None, os.environ)
    return found.stem if found else ""


def _remove_task(task: str) -> int:
    """移除一支哨兵；`0`＝**驗到它真的不見了**（rc 本身在兩個平台都不是憑證）。

    載具的唯一的家＝`schedule_backend`（Windows→`Unregister-ScheduledTask` ＋ 回查字樣；
    mac→先刪 plist 斷持久化、再 `bootout`、再 `launchctl print` 回讀）。本檔不留第二份。
    🔴 這條路在 mac 上是**已經實測過走得通**的那一條（舵手手動 `--remove-schtasks
    --task-name <label>` rc=0 收掉本輪孤兒走的正是它）⇒ 修前壞掉的只有「列舉」那一半，
    而那使 GC 比整支壞掉更危險：移除得動、卻永遠找不到要移除的東西。
    """
    return schedule_backend.select().disarm(task)


def _sweep_artifacts(session_id: str, tmp: Path) -> list[str]:
    """把該 session 的哨兵痕跡一起收掉（任務書／閂鎖／boot log／水位 state）。

    🔴 **R84／ARCH-06 已收（此前是本函式自陳的「兩個家」）**：任務書那一件現在交給
    `quota_escalation.reap_plans()`——「什麼時候可以刪任務書」的判準與 `unlink` 站點各自
    只剩一個家，全庫判準見 `tools/tests/test_mac_endurance_r83.py::PlanReapHasOneHomeTest`。
    本函式提供的**輸入**是「這個 session 已終態」（`session_id`），且刻意 `age=None`：GC 是
    拿著 `reap_verdict` 的裁決來的，與齡無關——分歧留在輸入，不留在規則。
    修前的自陳逐字寫著「改了一邊不會有任何東西轉紅」，那句話正是它自己的達成判準。

    lazy import：`quota_escalation` 在模組層 import `context_budget_guard`，而那一支又在
    模組層 import 本模組 ⇒ 放在檔頭會成環（形態與理由同 `_planner_module()`）。
    """
    from quota_escalation import reap_plans  # noqa: PLC0415 — 見 docstring（成環）

    gone = list(reap_plans(session_id=session_id, root=tmp, age=None))
    for name in (f"{ARM_MARKER_PREFIX}{session_id}.json",
                 f"autosdd_sentinel_boot_{session_id}.log",
                 f"autosdd_ctxguard_{session_id}.json"):
        path = tmp / name
        try:
            path.unlink()
            gone.append(name)
        except OSError:
            continue
    return gone


# 🔴 R83 複審連帶（「哨兵靜默消失」同族，本輪實機觀測到的那個形態）
# ----------------------------------------------------------------
# 上面那支 `_sweep_artifacts` 把任務書／閂鎖／boot log／水位 state **四件全部刪掉**，而
# `_remove_task` 又把排程本體拆掉 ⇒ `--apply` 跑完之後，「這支哨兵曾經存在、是誰收掉的、
# 為什麼收」在磁碟上一個字都不剩。那個磁碟狀態與本輪實機觀測到的病徵**完全同形**：哨兵
# 判過四次 `arm_reset`、log 某一刻起空白、`launchctl` 零命中——事後無從歸因，連「是被收掉
# 還是自己死了」都分不出來。根 CLAUDE.md〈反事後諸葛取證規則〉要的是「沒觸發＝可偵測」，
# 而回收是排程生命週期的另一半，同一條規則兩邊都得成立；此前只有武裝那一半有痕跡。
# 🔴 稽核痕跡檔（`autosdd_resume_log_*.jsonl`）刻意**不在** `_sweep_artifacts` 的清單裡，
# 就是為了留下這一行；它的路徑規則與格式的唯一的家＝planner（鍵是**任務書路徑**而不是
# session id，理由見 `planner.endurance_log_path` 上方那段），本檔不抄第二份。
def _record_reap(plan: Path, **fields: object) -> str:
    """把「GC 收掉了這一支」append 進續航稽核痕跡；回落檔路徑，**沒寫成回空字串**。

    🔴 回空字串而不是靜默成功：`planner.append_log` 對寫入失敗是刻意吞掉的（留不下痕跡
    不得升級成回收失敗），所以「有沒有真的留下痕跡」必須由呼叫端自己驗——判準是那個檔
    **變大了**，不是「指令沒有拋例外」（同本 repo 通篇「rc 不是憑證」那一條）。少了這半，
    「痕跡寫不進去」與「痕跡寫好了」外觀相同，而這一支存在的全部理由就是要讓兩者分得開。
    """
    planner = _planner_module()
    if planner is None:
        return ""
    try:
        trace = planner.endurance_log_path(plan)
        before = trace.stat().st_size if trace.is_file() else -1
        planner.append_log(trace, "gc_reaped", **fields)
        after = trace.stat().st_size if trace.is_file() else -1
    except Exception:  # noqa: BLE001 — 留不下痕跡不得讓回收本身失敗，但必須回報得出來
        return ""
    return str(trace) if after > before else ""


def gc(*, apply: bool = False, keep: tuple[str, ...] = (),
       min_idle: float = GC_IDLE_SECONDS, tmp_dir: str | None = None) -> list[dict] | None:
    """列出每支哨兵的處置；`apply=False`（預設）只看不動。`None`＝**列舉量不到**。

    🔴 預設 dry-run 是刻意的：這支工具的失手代價是不可逆的（拆掉別人正在等的續航），
    而它的**價值**在 dry-run 就已經全部兌現了——看清單本來就是掌舵者要的那件事。
    🔴 回 `None` 而不是空清單（R83 複審 A-01）：修前列舉失敗與「排程器裡真的沒有哨兵」
    塌成同一個 `[]`，於是 `main()` 印出「沒有任何工作」並 rc=0 ⇒ **假陰性被回報成成功**。
    這一格與 `reap_verdict` ② 是同一條紀律，只是那一支守的是「哪一支可以收」、
    這一支守的是「有沒有東西可收」——兩個問題各自都會把「量不到」讀成「量到零」。

    🔴 證據來源（ARCH-01，DEF-200-455 同根）：每支哨兵的存在／閒置／狀態**只**取自它自己任務書
    （`<tmp>/autosdd_resume_plan_<sid>.md`）狀態塊記的逐字稿絕對路徑（`plan_evidence`）；呼叫者
    的專案目錄（`_transcript_dir()`）只用來找「最近仍在寫的那一支」（`_newest_session` 保護），
    **不**用來判別人的哨兵。任務書缺席／解析不出／沒有該欄 ⇒ 量不到 ⇒ 不收；這不會留下殭屍，
    （前提＝該 job 自己醒得來；job 醒不來且任務書已被系統清掉的殭屍為已知殘餘，GC 恆量不到）
    三種哨兵下次醒來都自己處理（`session_resume_planner._sentinel_tick`）：缺席 ⇒
    `_abort_and_unregister`、解析不出 ⇒ `_heal_relay` 自癒、沒有該欄 ⇒ 逐字稿 `Path("")`
    不存在 ⇒ 靜默 disarm。
    """
    tasks = sentinel_task_names()
    if tasks is None:
        return None
    tmp = Path(tmp_dir or tempfile.gettempdir())
    protected_ids = set(keep) | {_newest_session(_transcript_dir())}
    now = time.time()
    rows: list[dict] = []
    for task in tasks:
        sid = session_of(task)
        plan = tmp / f"autosdd_resume_plan_{sid}.md"
        recorded, state = plan_evidence(plan)
        transcript = Path(recorded) if recorded else None
        # 🔴 沒記／非絕對路徑一律傳 `None`（＝量不到），**不得**塌成 `False`：那個塌陷正是本檔第一版
        # 實跑 dry-run 時把三支哨兵全判成可收的原因（相對路徑以 GC 自己的 cwd 解析＝又是本地證據）。
        exists = (transcript.is_file() if transcript is not None and transcript.is_absolute()
                  else None)
        idle = (now - transcript.stat().st_mtime) if exists else None
        reap, why = reap_verdict(transcript_exists=exists, idle_seconds=idle,
                                 state=state, protected=sid in protected_ids,
                                 min_idle=min_idle)
        row = {"task": task, "session_id": sid, "reap": reap, "why": why,
               "state": state, "idle_hours": None if idle is None else round(idle / 3600, 2)}
        if reap and apply:
            row["unregister_rc"] = _remove_task(task)
            row["swept"] = _sweep_artifacts(sid, tmp)
            # 痕跡**最後**寫：這一行要能同時交代排程與殘骸兩件事的結果，而它的落檔路徑
            # 只由任務書**路徑字串**推導（不讀那個檔）⇒ 殘骸已被刪掉不影響它。
            row["trace"] = _record_reap(plan, task=task, session_id=sid, why=why,
                                        unregister_rc=row["unregister_rc"], transcript=recorded,
                                        swept=row["swept"])
        rows.append(row)
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="哨兵生命週期：列出／回收已結束 session 的 schtasks 與任務書殘骸")
    parser.add_argument("--apply", action="store_true",
                        help="真的執行回收（預設只列出，不動任何東西）")
    parser.add_argument("--keep", action="append", default=[], metavar="SESSION_ID",
                        help="指名保留（可重複）。最近仍在寫的那一支逐字稿一律自動保留")
    parser.add_argument("--min-idle-hours", type=float, default=GC_IDLE_SECONDS / 3600,
                        dest="min_idle_hours", help="閒置多少小時才算「已結束」（預設 6）")
    args = parser.parse_args(argv)

    rows = gc(apply=args.apply, keep=tuple(args.keep),
              min_idle=args.min_idle_hours * 3600)
    backend = schedule_backend.select()
    # 🔴 兩個結局刻意分開，rc 也分開（R83 複審 A-01：修前它們是同一句話、同一個 rc=0）：
    if rows is None:
        print(f"❌ **量不到**：排程器（載具＝{backend.name}）的列舉失敗 ⇒ 這**不是**"
              "「沒有東西要收」。在拿到一次成功的列舉之前，不要相信「哨兵沒有增生」。\n"
              f"   現查指令：\n      {backend.evidence_hint()}", file=sys.stderr)
        return 1
    if not rows:
        print(f"✅ 排程器（載具＝{backend.name}）裡沒有任何 {TASK_PREFIX}* 工作。"
              "這是**量到的零**——量不到那一條走的是 rc=1 並印在 stderr。")
        return 0
    for row in rows:
        mark = "🗑 收" if row["reap"] else "✅ 留"
        if row["reap"] and args.apply:
            # 🔴 痕跡那一格刻意印在使用者看得到的地方，且「沒留下」要明說：回收把殘骸全刪，
            # 少了這一行，事後查「哨兵怎麼不見了」會完全查不到（見 `_record_reap` 的 WHY）。
            mark += (f"（rc={row.get('unregister_rc')}，殘骸 "
                     f"{len(row.get('swept') or [])} 件，痕跡＝"
                     f"{row.get('trace') or '❌ 沒留下（回收已完成，但事後無從歸因）'}）")
        print(f"{mark}  {row['task']}\n      {row['why']}")
    if not args.apply and any(r["reap"] for r in rows):
        # 🔴 動詞取自後端而不是寫死 `Unregister-ScheduledTask`：後者在 mac 上不存在，而這一行
        # 是使用者唯一會照著做的那一行（同 `quota_gate.evidence_hint()` 的 R83／F2-② 判例）。
        print(f"\n以上是 dry-run。要真的收：加 --apply（載具＝{backend.name}，"
              "會解除排程並刪殘骸；解除是否成立由後端自己回讀驗證，rc 不是憑證）")
    return 0


#: M-04（決定性判死版；M-03 的暫存檔差集降級為輔助訊號）：CI／pre-push 呼叫根層測試
#: runner 的漏斗點此前完全沒有一層偵測「這次測試執行期間是否真的觸碰了真的
#: launchd/schtasks」。`autosdd_leak_fence.jsonl` 與其他持久痕跡同居所（`endurance_env.
#: trace_dir()`），不開第二個家。
LEAK_FENCE_LOG_NAME = "autosdd_leak_fence.jsonl"

#: 圍籠掃描真排程器時用的工作名前綴。刻意**不收窄**成 `TASK_PREFIX`
#: （`AutoSDD_Sentinel_`）：洩漏源不只哨兵——續跑 job 與測試自造的別名同屬本 repo
#: 種下的排程，前綴收窄一格就等於對它們失明。字面與 `_arm_sentinel` 的既有判準
#: （`session_resume_planner.py` 的 `select().list_jobs("AutoSDD_")`）同一個，不發明第二種。
LEAK_FENCE_JOB_PREFIX = "AutoSDD_"


def _leak_fence_jobs(backend) -> list[str] | None:
    """真排程器上 `AutoSDD_*` 工作的快照。`None`＝**量不到**，不是「量到零」。

    列舉一律只經 `schedule_backend.select()`（本檔一行平台知識都不留，見檔頭
    R83 複審 A-01）。載具自己炸掉時吞成「量不到」：圍籠是量測器，量測器故障
    不得反過來變成測試跑不完的故障源——而「量不到」在下面**結構上不會判死**。
    """
    try:
        return backend.list_jobs(LEAK_FENCE_JOB_PREFIX)
    except OSError:
        return None


def leak_fence(run):
    """底線防護 ＋ **決定性**排程洩漏判死（M-04 A 面）。

    三件事，會讓 rc 變非零的只有第二件：

    (1) 忘記加 `AUTOSDD_SENTINEL_OFF=1` 的測試也有個底線（`setdefault`，不覆寫已設的值）。
    (2) 🔴 **判死面＝真排程器工作清單的前後差集**：`run()` 期間新增、**且收尾時仍然在**
        的 `AutoSDD_*` 工作＝沒有人收的殘骸 ⇒ rc 判非零（即使 `run()` 自己回 0）。
        收尾快照在 `run()` 之後才取，所以「註冊完又在同一次執行內解除」的合法暫時性
        工作結構上就不在差集裡，不必另寫一條判準去放行它。列舉回 `None`（量不到）
        ⇒ **不判死**：沒有證據不能扣帽子（同 `reap_verdict` ② 與 `_arm_sentinel` 對
        `list_jobs` 回 `None` 的既有 fail-open 紀律），只出聲說「量不到」，並明說那
        不等於「沒有洩漏」。
    (3) 輔助訊號＝`$TMPDIR` 頂層 `autosdd_*` 檔名差集：**只印不判**。新增的暫存檔證明
        不了排程被寫（並行 session 在武裝之前也會落檔），它只是更早期的警訊；M-03 曾
        把它當唯一訊號，弱判準當判死用正是本輪修掉的那件事。

    🔴 誠實劃界（兩面都是機率式，不是決定性的全部）：
      · **假陰性**：測試種下的 job 若在收尾快照前自己自我解除（tick 讀不到任務書
        ⇒ 拆掉自己），這裡看不到它曾經存在——T-f4b 事後 `launchctl list` 查無、卻在
        bootout log 留下五筆，就是這個形態。那一半要等 ADR-XPLAT-015 §3.6 的 ledger
        面（`SandboxBackend` 記下每一次被攔下的武裝）落地。
      · **假陽性**：另一個活 session 在本次執行期間**合法**武裝的哨兵也會落在差集裡
        （ADR §3.6 的 `alive`／`dead` 真值表未落地）。判紅時第一步先看 label 裡的
        session id 是不是自己這一場的。
    """
    # 字面（不 import `.claude/hooks/context_budget_guard.SENTINEL_OFF_ENV`）：本檔
    # 對 planner／hook 鏈一律走函式內 lazy import 以避免模組層成環（見 `_planner_module()`
    # 既有理由），這一個環境變數名不值得為它開一條新的耦合路徑。
    os.environ.setdefault("AUTOSDD_SENTINEL_OFF", "1")
    backend = schedule_backend.select()
    jobs_before = _leak_fence_jobs(backend)
    tmp = Path(tempfile.gettempdir())
    before = set(tmp.glob("autosdd_*"))
    rc = run()
    after = set(tmp.glob("autosdd_*"))
    jobs_after = _leak_fence_jobs(backend)
    new_files = sorted(str(p) for p in (after - before))
    if new_files:
        print(f"[leak_fence] 執行期間 $TMPDIR 新增 {len(new_files)} 個 autosdd_* 檔案"
              "（輔助訊號：只列不刪、**不判死**，判死看的是排程器清單）：")
        for p in new_files:
            print(f"  {p}")
    leaked: list[str] = []
    fence_rc = 0
    if jobs_before is None or jobs_after is None:
        print(f"[leak_fence] ⚠️  排程面**量不到**（載具＝{backend.name}）⇒ 本輪不判排程"
              "洩漏。不要把「量不到」讀成「沒有洩漏」。"
              f"現查：{backend.evidence_hint()}", file=sys.stderr)
    elif leaked := sorted(set(jobs_after) - set(jobs_before)):
        fence_rc = 1
        print(f"[leak_fence] ❌ 排程洩漏（決定性）：本次執行期間真排程器（載具＝"
              f"{backend.name}）多了 {len(leaked)} 支 {LEAK_FENCE_JOB_PREFIX}* 工作，"
              "且收尾時仍然在（沒有人收）⇒ 本次 rc 判非零：", file=sys.stderr)
        for label in leaked:
            print(f"  {label}", file=sys.stderr)
        print("   修法：種下它的測試要注入假後端（`patch.object(schedule_backend, "
              '"select", …)`）或 `addCleanup` 真的把它拆掉；人工清＝'
              "`python tools/lib/sentinel_lifecycle.py --apply`", file=sys.stderr)
    record = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "rc": rc,
              "new_temp_files": len(new_files), "carrier": backend.name,
              "jobs_before": None if jobs_before is None else len(jobs_before),
              "jobs_after": None if jobs_after is None else len(jobs_after),
              "leaked_jobs": leaked, "fence_rc": fence_rc}
    try:
        path = endurance_env.trace_dir() / LEAK_FENCE_LOG_NAME
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 落痕跡失敗不得反過來變成測試跑不完的故障源（同既有 append_log 紀律）
    return max(rc, 0, fence_rc)


#: 真實契約目錄（＝quota 快取目錄，DEF-200-445）下**有人會讀**的共享契約檔 glob（DEF-200-444）：
#: 配速契約 canonical（`pace_contract.CONTRACT_NAME`，引擎 `file_quota_meter.read_pace()`
#: 的讀取面）＋`_<家族>` 兄弟檔。刻意只看這一族：`autosdd_quota.json` 等真 session 本來就會
#: 在全套期間自己更新，全看＝常態假紅。以 `.json` 收尾＝不含 `write()` 的 staging 暫存檔
#: （`….json.<pid>.tmp`）。與 `pace_contract` 的字面相等鎖＝
#: `tools/tests/test_run_root_unittests.py::TempFenceTest`。
#: 常數名沿用 444（當時比對面是 TEMP），現比對面是快取目錄。
REAL_TEMP_WATCH_GLOB = "autosdd_pace*.json"

#: 三個變數一起指：Python `tempfile` 讀 TMPDIR→TEMP→TMP，Windows 原生 API／PowerShell 讀 TMP→TEMP，
#: 漏掉任何一個，某一類子行程就回到真實 TEMP。
TEMP_FENCE_ENV = ("TEMP", "TMP", "TMPDIR")

#: 同一個隔離根還要指到的第四個變數：quota 快取目錄（DEF-200-445）。配速契約與
#: `autosdd_quota.json` 一樣住在那裡、不在 TEMP——只隔離 TEMP 一族時，全套照樣寫引擎真的會讀的
#: 那一份。自帶 HOME 沙箱的測試（`_isolated_env` 之類）須自己清掉它，否則 HOME 管不到快取位置。
#: 第五個變數：持久痕跡目錄（`endurance_env.TRACE_DIR_ENV`）。卸載痕跡 `record_unload` 刻意以
#: passwd 家目錄落點、不吃隔離 HOME（DEF-200-455：隔離正是讓證據消失的原因），所以圍籬
#: 必須顯式把它指進隔離根，否則全套與單模組直跑會把 fixture 卸載列寫進真實 traces。
CACHE_FENCE_ENV = (quota_meter.CACHE_DIR_ENV, endurance_env.TRACE_DIR_ENV)

#: 隔離根前綴。刻意**不以 `autosdd_` 開頭**：`leak_fence` 的輔助訊號 glob 就是 `autosdd_*`，
#: 隔離根自己不得被它算成「新增的洩漏」。
TEMP_FENCE_PREFIX = endurance_env.FENCE_PREFIX  # SSOT 住 endurance_env：uid_trace_dir 要認得隔離根


def _watched_digests(root: Path) -> dict[str, str]:
    """`root` 頂層符合 `REAL_TEMP_WATCH_GLOB` 的 `檔名 -> sha256 前 16 碼`；
    讀不到（被鎖／剛被換掉）記 `?`。"""
    out: dict[str, str] = {}
    for path in sorted(root.glob(REAL_TEMP_WATCH_GLOB)):
        try:
            out[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        except OSError:
            out[path.name] = "?"
    return out


def fence_enter(parent: Path | None = None) -> dict:
    """隔離的**進**原語：TEMP／TMP／TMPDIR、快取目錄與 `tempfile.tempdir` 一起指向專屬隔離根，
    回還原用的 handle（`fence_exit` 的唯一輸入）。

    `temp_fence`（經 runner 的全套）與測試模組的 `setUpModule`／`tearDownModule`（單模組直跑，
    DEF-200-446）共用這組進出原語：環境變數的設定與還原只有這一處，不准有第二份。
    隔離根建在 `parent` 之下，預設＝**當下**的 `tempfile.gettempdir()`——所以巢狀合法：runner
    圍籬在外、模組圍籬在內時，內層建在外層隔離根之下，各自 `fence_exit` 各還各的（後進先出）。
    原值先記再改：`tempfile.tempdir` 也在內，含「尚未被快取」那個狀態（還原目標是原本的狀態）。
    handle 必須留到 `fence_exit`：丟掉最後一個參照，`TemporaryDirectory` 的 finalizer 會把仍在
    使用的隔離根提前刪掉（巢狀時用單一變數存放即踩到，所以模組層要用堆疊存放）。
    建不起隔離根＝handle 的 `root` 記 `None`、環境一個字不動、⚠️ 出聲不拋（量測器故障不得反過來
    變成測試跑不完的故障源）。
    """
    handle: dict = {"tempdir": tempfile.tempdir, "root": None, "saved": {
        n: os.environ.get(n) for n in TEMP_FENCE_ENV + CACHE_FENCE_ENV}}
    handle["parent"] = Path(parent or tempfile.gettempdir())
    try:
        handle["root"] = tempfile.TemporaryDirectory(
            prefix=TEMP_FENCE_PREFIX, dir=str(handle["parent"]), ignore_cleanup_errors=True)
    except OSError as exc:
        print(f"[temp_fence] ⚠️  隔離根建不起來（{exc}）⇒ 本輪全套**沒有**隔離 TEMP，"
              "測試會直接碰真實 TEMP 與快取目錄。", file=sys.stderr)
    else:
        os.environ.update(dict.fromkeys(TEMP_FENCE_ENV + CACHE_FENCE_ENV, handle["root"].name))
        # 持久痕跡釘到隔離根的子目錄：與 TEMP 同目錄時，讀取端的第二候選 `gettempdir()` 會讀到
        # 別支測試剛寫的結局檔（複審鏡 A R-1）。
        traces = endurance_env.fence_trace_dir(handle["root"].name)
        traces.mkdir(parents=True, exist_ok=True)
        os.environ[endurance_env.TRACE_DIR_ENV] = str(traces)
        tempfile.tempdir = handle["root"].name
    return handle


def fence_exit(handle: dict) -> None:
    """隔離的**出**原語：還原 `fence_enter` 記下的環境變數與 `tempfile.tempdir`，再清掉隔離根。
    原本沒設的變數 pop 回「沒設」（不是空字串）；`root` 為 `None`（當初建不起來）時只還原、不炸。

    後進先出被打破（目前的隔離根不是本 handle 的）＝⚠️ 點名、不拋、照樣清根。外層先出場時內層根
    一併被清，內層之後才出場時它的還原目標（外層根）已不存在：此時不再把環境寫回已刪目錄。
    """
    root = handle["root"]
    if root is not None:
        want = {n: root.name for n in handle["saved"]}
        want[endurance_env.TRACE_DIR_ENV] = str(endurance_env.fence_trace_dir(root.name))
        held = [(tempfile.tempdir, root.name),
                *((os.environ.get(n), want[n]) for n in handle["saved"]
                  if os.environ.get(n) is not None)]  # 被測試清掉的變數不算亂序（複審鏡 A N-11）
        if any(value != expect for value, expect in held):
            print(f"[temp_fence] ⚠️  fence_exit 亂序：目前隔離根 {tempfile.tempdir} ≠ 本 handle "
                  f"{root.name}（後進先出被打破；外層根已被清掉時，本層不再把環境還原進它）",
                  file=sys.stderr)
        if not handle["parent"].exists():
            root.cleanup()
            return
    tempfile.tempdir = handle["tempdir"]
    for name in handle["saved"]:
        os.environ.pop(name, None)
    os.environ.update({n: v for n, v in handle["saved"].items() if v is not None})
    if root is not None:
        root.cleanup()


def temp_fence(run, real_tmp: Path | None = None):
    """真實 TEMP 狀態圍籬（DEF-200-444／445）：`run()` 期間整個全套（含 worker 與孫行程）的暫存根
    與 quota 快取目錄（`AUTOSDD_QUOTA_CACHE_DIR`）指向同一個專屬隔離目錄、跑完清掉；並在前後比對
    **真實契約目錄**（＝`quota_meter.cache_path().parent`）下配速契約檔的雜湊，有變動印 ❌。
    **advisory：`run()` 的 rc 原樣回傳**（體例同 `console_orphan_census.wrap`）。
    `real_tmp` 僅供測試注入：同時充當隔離根的父目錄與比對面（生產路徑兩者分開——隔離根建在真實
    TEMP 下，比對面是快取目錄）。

    缺陷本體：`pace_contract.contract_path()` 取 `tempfile.gettempdir()`，全套裡上百處
    `pace_report`／`--pace` 因而把真實 TEMP 下的 autosdd_pace*.json 改寫成測試的假決策（實測：
    一次全套前後三份內容全變）。DEF-200-444 修時以為引擎讀的是 TEMP 那一份；實際上引擎自
    DEF-200-012 起讀家目錄，寫入端與讀取端目錄分家（DEF-200-445）。寫入端改走
    `quota_meter.cache_path()` 之後，全套寫的就是引擎真的會讀的那一份（TTL 內可能拿假決策當
    派工上限），所以圍籬現在**同時**隔離 TEMP 一族與快取目錄。逐站點注入補不完
    （`autosdd_quota*`／`autosdd_resume_*` 等同型站點還有一整族），所以在全套層一次隔離。
    三個機制缺一不可：
      ① 四個環境變數（TEMP／TMP／TMPDIR＋快取目錄）一起改，由 `fence_enter` 負責（worker 由
         `parallel_shard` 以 `dict(os.environ)` 複本 Popen，環境要在 `run_parallel` 之前改
         才帶得到）；
      ② 同步改 `tempfile.tempdir` 快取（Python 只在第一次 `gettempdir()` 讀環境變數：序列模式與
         主行程裡只改 env，對已快取的行程完全無效），同樣由 `fence_enter`／`fence_exit` 成對處理；
      ③ 真實路徑（TEMP 與快取目錄）在 `fence_enter` 改環境**之前**取得（比對面必須是真實契約
         目錄，不是隔離根）。

    🔴 誠實劃界：
      · 本函式的射程只含經 `tools/run_root_unittests.py` 的全套。單模組直跑
        （`python -m unittest <模組>`）不經它：會碰配速契約寫端的測試模組改在模組層自帶
        `fence_enter`／`fence_exit`（家族鎖＝`test_run_root_unittests.py` 的
        `TestWriterModulesDeclareTheModuleFence`）；其餘模組直跑仍照舊直接碰真實 TEMP 與真實
        快取目錄，修後真實契約住家目錄（或 `AUTOSDD_QUOTA_CACHE_DIR`）、TTL 900s 內引擎讀得到，
        所以**新增**寫端測試時務必接圍籬，或直跑時帶 `AUTOSDD_QUOTA_CACHE_DIR` 與 `TMPDIR`。
      · 子行程若以**不含** TEMP／TMP／TMPDIR／`AUTOSDD_QUOTA_CACHE_DIR` 的 env 啟動、或寫死真實
        路徑，圍籬管不到——那正是比對面存在的理由（只看配速契約一族；其餘由 `leak_fence` 的
        `autosdd_*` 新增差集輔助出聲，本圍籬內層於它，所以那行訊號同時是逃逸偵測器）。
      · ❌ 也可能是同時段真實 session 自己跑了 `--pace`：兩者無法從檔案內容區分，故 advisory。
      · 硬殺（taskkill /F／SIGKILL）會留下 `suite_tmp_*` 隔離根，可手動刪除。
      · 隔離根讓每條暫存路徑多 19 個字元（前綴＋8 碼隨機＋分隔符）：TEMP 本身已逼近 Windows
        MAX_PATH 的機器上，深層測試路徑（git 物件目錄）會先撞 260。實測（沙盒 TEMP 基底 132
        字元）：無圍籬過、有圍籬 3 支 git push 測試報 `Filename too long`；一般 TEMP（32~41
        字元）離 260 還有 80 字元以上餘裕。macOS／Linux 面本機未驗（tools/ 內無 unix socket，
        故不受 AF_UNIX 104 字元路徑上限影響）。
      · 建不起隔離根或清不乾淨＝只出聲（⚠️）不改 rc：量測器故障不得反過來變成全套跑不完的故障源。
      · `run()` 拋例外時：環境／快取照樣還原、隔離根照樣清掉，例外原樣往外拋，不做前後比對。
    """
    try:
        watched = Path(real_tmp) if real_tmp is not None else quota_meter.cache_path().parent
    except (OSError, RuntimeError):  # 取不到家目錄：少看一處，退回真實 TEMP（隔離根的父目錄）
        watched = None
    handle = fence_enter(real_tmp)
    watched = watched or handle["parent"]
    before = _watched_digests(watched)
    try:
        rc = run()
    finally:
        fence_exit(handle)
    left = (root := handle["root"]) is not None and Path(root.name).exists()
    if left:
        print(f"⚠️  真實 TEMP 圍籬：隔離根沒清乾淨（{root.name}；多半是殘存行程還握著檔案）"
              "——可手動刪除，不影響 rc。")
    after = _watched_digests(watched)
    drift = {name: "新增" if name not in before else "消失" if name not in after else "變更"
             for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)}
    if drift:
        listing = "、".join(f"{name}（{kind}）" for name, kind in drift.items())
        print(f"❌ 真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下的"
              f"配速契約檔有變動：{listing}；目錄 {watched}"
              "——疑似某個測試繞過了 TEMP／快取目錄隔離（子行程以不含 TEMP 與 "
              "AUTOSDD_QUOTA_CACHE_DIR 的 env 啟動／寫死真實路徑），"
              "也可能是同時段有真實 session 跑了 `--pace`（本圍籬無法區分）。advisory：不改 rc。"
              "引擎讀 autosdd_pace.json，TTL 內可能拿到假決策；處置＝在真實 session 重跑一次 "
              "`python tools/session_resume_planner.py --pace` 覆寫回真值。")
    else:
        state = ("隔離根已建立並清除" if root is not None and not left
                 else "隔離未完整（見上方 ⚠️）")
        print(f"✅ 真實 TEMP 圍籬：全套期間真實契約目錄（與 autosdd_quota.json 同目錄）下 "
              f"{REAL_TEMP_WATCH_GLOB} 零變動（前 {len(before)}／後 {len(after)} 份；"
              f"目錄 {watched}）；{state}。")
    return rc


if __name__ == "__main__":
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
