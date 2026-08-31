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
import sys
import tempfile
import time
from pathlib import Path

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
            report.with_suffix(".ack").write_text(
                f"acked {time.time()}\n", encoding="utf-8", newline="\n")
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


def plan_state(plan: Path) -> str | None:
    """任務書狀態塊裡的 `state`；讀不出來回 `None`（＝「量不到」，不是「終態」）。

    解析走 planner 的 `parse_relay`（**唯一的家**，本檔不抄第二份格式知識）。
    lazy import：planner 會把 `.claude/hooks` 接進 `sys.path` 並 import 整條 hook 鏈，
    而本模組被那條鏈 import ⇒ 放在模組層會成環。放在函式內，hook 路徑一次都碰不到它。
    """
    planner = _planner_module()
    if planner is None:
        return None
    try:
        state = planner.parse_relay(plan.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 讀不到就當「量不到」，判準那一側自己會保守處理
        return None
    return str(state.get("state")) if isinstance(state, dict) else None


def reap_verdict(*, transcript_exists: bool | None, idle_seconds: float | None,
                 state: str | None, protected: bool,
                 min_idle: float = GC_IDLE_SECONDS) -> tuple[bool, str]:
    """純判準：這支哨兵可以收掉嗎。回 `(要不要收, 理由)`。

    順序即優先序，**最保守的先判**：
      ① 受保護（呼叫端指名 or 它是最近仍在寫的那一支）⇒ 絕不收。這一條擋在最前面，
         是因為誤收一支活著的哨兵＝把那個 session 的續航靜默弄丟，而弄丟是看不見的。
      ② `transcript_exists is None`（＝**量不到**：逐字稿目錄根本定位不到）⇒ 絕不收。
      ③ 逐字稿不存在 ⇒ 收（session 連檔都沒了，哨兵醒來也只會 fail-loud 空轉）。
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
        return False, ("逐字稿目錄定位不到 ⇒ **量不到 ≠ 不存在**，一律拒絕回收"
                       "（請先確認 tools/session_resume_planner.py 可 import）")
    if not transcript_exists:
        return True, "逐字稿不存在"
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
    """逐字稿目錄；`None`＝**定位不到**（不是「裡面沒有東西」，見 `reap_verdict` ②）。"""
    planner = _planner_module()
    if planner is None:
        return None
    try:
        return planner.project_transcript_dir(planner._REPO_ROOT)
    except Exception:  # noqa: BLE001
        return None


def _newest_session(base: Path | None) -> str:
    """最近被寫的那一支逐字稿的 session id（＝根 CLAUDE.md 對「當前 session」的既有判準）。

    🔴 這是 GC 的**安全底線**，不是便利功能：它讓「忘了加 --keep」不會演變成把正在跑的
    那一輪的續航拆掉。判準與 `session_resume_planner.resolve_transcript()` 逐字同源。
    """
    if base is None or not base.is_dir():
        return ""
    found = [p for p in base.glob("*.jsonl") if p.is_file()]
    return max(found, key=lambda p: p.stat().st_mtime).stem if found else ""


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
    """
    tasks = sentinel_task_names()
    if tasks is None:
        return None
    base = _transcript_dir()
    tmp = Path(tmp_dir or tempfile.gettempdir())
    protected_ids = set(keep) | {_newest_session(base)}
    now = time.time()
    rows: list[dict] = []
    for task in tasks:
        sid = session_of(task)
        # 🔴 `base is None` 一律傳 `None`（＝量不到），**不得**塌成 `False`：
        # 那個塌陷正是本檔第一版實跑 dry-run 時把三支哨兵全判成可收的原因。
        transcript = (base / f"{sid}.jsonl") if base is not None else None
        exists = None if base is None else bool(transcript and transcript.is_file())
        idle = (now - transcript.stat().st_mtime) if exists else None
        plan = tmp / f"autosdd_resume_plan_{sid}.md"
        state = plan_state(plan) if exists else None
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
                                        unregister_rc=row["unregister_rc"],
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


if __name__ == "__main__":
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
