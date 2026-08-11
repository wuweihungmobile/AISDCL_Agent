"""哨兵的**生命週期**：什麼樣的 session 值得一支 schtasks，什麼時候該把它收掉。

WHY —— 立案（掌舵者當場截圖：工作排程器裡三支 `AutoSDD_Sentinel_*`，問「是正常的 JOB 嗎」）
---------------------------------------------------------------------------------------
`context_budget_guard.arm_sentinel()` 此前在 **SessionStart 無條件武裝**。那個形狀的代價
是量得到的（本輪開場實測，逐字稿目錄 `d--CursorProject-AISDCL-Agent`）：

  · 排程器裡 3 支哨兵，其中 **2 支屬於活了 5 秒與 12 秒的 session**；
  · `%TEMP%` 累積 30 份 `autosdd_resume_plan_*.md`、24 份 `autosdd_sentinel_boot_*.log`；
  · 那 24 份 boot log 對應 24 次武裝，而真正在做事的 session 只有個位數。

`tools/session_resume_planner.py` 的 `sentinel_task_name()` 上方早就把這件事寫成「R79 已知
設計問題（本輪不修）」，並列了三條候選處置。本檔是其中**第三條**的落地，且刻意不是前兩條：

  ✗「同一個 repo 只留一支」——會讓兩個真的在跑的 session 互相蓋掉對方的續航。
  ✗「對 headless `claude -p` 整個不武裝」——那條路把**續跑那一跑自己撞線**的續航能力
    一起關掉（原註記自己就寫了「是取捨不是純改善」）。
  ✓ **延後武裝**：不在 SessionStart 註冊，改在「這個 session 已經累積到值得續航的工作量」
    才註冊。它同時滿足兩邊——短命探針一支都不武裝，而**長跑的 headless 續跑仍然會**，
    因為判準問的是工作量，不是這個 session 是怎麼被啟動的。

🔴 為什麼判準不能長在 SessionStart 那一刻（這是設計的核心限制，不是實作偷懶）
-----------------------------------------------------------------------------
SessionStart 觸發時**逐字稿檔案往往還不存在**（`arm_sentinel` 的既有註解就是這樣寫的，
且 planner 的 `--arm-sentinel` 為此特別放行「檔案不存在也照樣武裝」）⇒ 那一刻手上沒有
任何可以量的東西。payload 的欄位也分不出來：本輪實測六支短命 session 的逐字稿與主
session **結構完全同形**（同樣 24 個 record key、第一筆同為 `queue-operation`、
`isSidechain` 全 0），差別只在**規模**。⇒ 唯一分得開的東西是「累積了多少」，而那要等。

判準與它的量測依據（🔴 這兩個門檻是量出來的，不是選出來的）
-------------------------------------------------------
本輪把該目錄下全部 **83 支**逐字稿逐支量了 `(assistant 回合數, 首尾時間跨度)`：

  · 掌舵者點名的六支短命 session：一律 **2 回合、跨度 ≤ 12 秒**（4/5/7/7/11/12s）。
  · 另有 13 支同族的探針／中止 session：4~15 回合。
  · 真正在做事的 session：**最少 38 回合 / 853 秒**，其餘一路到 1,046 回合。

⇒ 門檻取 `MIN_TURNS = 24`、`MIN_SPAN_SECONDS = 600`，**兩者皆須成立**（AND）。
  · 對六支元凶的邊際：回合數 12 倍、跨度 50 倍——不是踩線通過。
  · 那 13 支探針全數被回合數擋下（最大 15 < 24）。
  · 83 支裡被誤擋的真實 session 是 **1 支**（45 回合但只活了 504 秒）⇒ 誠實劃界：
    一個 8 分鐘就結束的 session 不會拿到續航。代價有界（它已經結束了），而反方向
    （為每一支 5 秒探針留一支每 15 分鐘醒來的排程）正是掌舵者當場回報的那個問題。
🔴 兩者取 AND 而不是 OR 是刻意的：OR 會讓「開著沒動 20 分鐘」與「3 分鐘內狂跑」各自
  單獨成立，而那兩種都不是「值得續航」的形狀。

成本：`maybe_arm()` 在**閂鎖已設**時只做一次 `Path.exists()`（武裝過的 session 走這條，
＝絕大多數呼叫）。未武裝時才掃一次逐字稿，而未武裝的 session 依定義都還很小
（元凶那六支是 18~20 KB）。

閂鎖為什麼是一個**檔案**而不是沿用 guard 的 tier 閂鎖
----------------------------------------------------
`context_budget_guard` 的 `remember_latch()` 只會**加鍵**、沒有刪鍵的路，而本主題需要
「SessionStart 時把它清掉」：`claude -r` 續接一個已下班（6 小時閒置自我解除）的 session
時，若閂鎖清不掉就再也不會重新武裝——那會把續航能力靜默弄丟。用獨立的 marker 檔可以
一行 `unlink`，而且它自己就是**可稽核痕跡**（裡面記了武裝當下量到的回合數與跨度，
回答「這一支為什麼會存在」）。

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
import json
import sys
import tempfile
import time
from pathlib import Path

import schedule_backend
from quota_limits import SYNTHETIC_MODEL

#: 值得續航的最小 assistant 回合數。取值依據見模組 docstring（實測分佈，非拍腦袋）。
MIN_TURNS = 24
#: 值得續航的最小存活跨度（秒）＝逐字稿首尾時間戳之差。
MIN_SPAN_SECONDS = 600.0

#: 武裝閂鎖的檔名前綴（放系統暫存，與其餘哨兵痕跡同一個家）。
ARM_MARKER_PREFIX = "autosdd_sentinel_armed_"

#: GC 判「這個 session 真的結束了」的閒置門檻。**刻意等於哨兵自己的自我解除門檻**
#: （`session_resume_planner.SENTINEL_IDLE_SECONDS`＝6 小時＞一個完整額度視窗）：
#: 比它短，GC 會在哨兵還在等額度回來時把它拆掉——那正是續航要防的事。
GC_IDLE_SECONDS = 6 * 3600.0

#: 任務書狀態塊的**終態**（工作已經結束，哨兵留著只是死工作）。
TERMINAL_STATES = frozenset({"disarmed", "abandoned", "resumed", "done"})

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


# ───────────────────────────────────────────────────────── 武裝側（hook 會呼叫這一段）
def session_evidence(transcript: Path) -> tuple[int, float]:
    """單趟掃逐字稿，回 `(assistant 回合數, 首尾跨度秒)`。掃不動一律回 `(0, 0.0)`。

    三個與 `guard.scan_transcript` 一致的紀律（同一份逐字稿、同一種壞行處置）：
      ① 以子字串預篩，絕大多數行不進 `json.loads`；
      ② 壞行跳過（逐字稿常有正在寫入的半截尾行），一行壞掉不得讓守衛崩潰；
      ③ `<synthetic>` 不算回合——那筆是 harness 在額度耗盡時寫進去的佔位，
         不是一次模型呼叫（`guard.scan_transcript` 對同一筆也是整筆退出）。
    """
    turns = 0
    first = last = None
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"timestamp"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                stamp = _epoch_of(record.get("timestamp"))
                if stamp is not None:
                    first = stamp if first is None or stamp < first else first
                    last = stamp if last is None or stamp > last else last
                if record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if isinstance(message, dict) and message.get("model") != SYNTHETIC_MODEL:
                    turns += 1
    except OSError:
        return 0, 0.0
    span = (last - first) if (first is not None and last is not None) else 0.0
    return turns, max(0.0, span)


def _epoch_of(raw: object) -> float | None:
    """ISO 時間戳 → epoch 秒；認不出來回 `None`。

    🔴 只做**相減**（跨度），從不持久化：本 repo 有具名判準禁止持久化 naive 本地時間戳
    （跨 DST 相減實測差 3600 秒且完全靜默）。`Z` 手動換成 `+00:00` 是因為
    `datetime.fromisoformat` 在 3.11 之前不吃 `Z`，而本 repo 下限是 3.11——留著不花錢，
    去掉會讓這支在別人的舊直譯器上安靜地少算跨度。
    """
    if not isinstance(raw, str):
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def should_arm(turns: int, span_seconds: float, *, min_turns: int = MIN_TURNS,
               min_span: float = MIN_SPAN_SECONDS) -> bool:
    """純判準（紅綠由注入自證）：這個 session 累積到值得一支排程了嗎。"""
    return turns >= min_turns and span_seconds >= min_span


def arm_marker_path(session_id: str, tmp_dir: str | None = None) -> Path:
    return Path(tmp_dir or tempfile.gettempdir()) / f"{ARM_MARKER_PREFIX}{session_id}.json"


def clear_arm_latch(session_id: str, tmp_dir: str | None = None) -> bool:
    """SessionStart 呼叫：把上一輪的武裝閂鎖清掉，讓 `claude -r` 續接時能重新評估。

    回「有沒有真的刪到檔」。刪不掉一律吞掉——閂鎖清不掉最多是少一次重新武裝，
    絕不可反過來變成 hook 的故障源（`.claude/settings.json` 記載過的 P0）。
    """
    try:
        arm_marker_path(session_id, tmp_dir).unlink()
    except OSError:
        return False
    return True


def maybe_arm(transcript: Path, session_id: str, *, plan_path: str, spawn,
              tmp_dir: str | None = None, min_turns: int = MIN_TURNS,
              min_span: float = MIN_SPAN_SECONDS) -> str:
    """PostToolUse 呼叫：夠格才武裝。回一個**理由字串**（供痕跡與測試斷言）。

    `spawn` 是注入點（production 傳 `guard.spawn_sentinel`）：單元測試因此驗得到整條
    決策，而不會在開發機上真的註冊一支排程——「驗證載具自己就是副作用來源」是本 repo
    判過的形態（`quota_escalation.gc_plans` 的 `root` 注入點同一條理由）。
    """
    marker = arm_marker_path(session_id, tmp_dir)
    if marker.exists():
        return "latched"
    turns, span = session_evidence(transcript)
    if not should_arm(turns, span, min_turns=min_turns, min_span=min_span):
        return f"below-threshold(turns={turns}/{min_turns},span={span:.0f}/{min_span:.0f}s)"
    if not spawn(str(transcript), plan_path):
        return "spawn-failed"
    try:
        marker.write_text(json.dumps(
            {"session_id": session_id, "turns": turns, "span_seconds": round(span, 1),
             "armed_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "transcript": str(transcript)},
            ensure_ascii=False), encoding="utf-8", newline="\n")
    except OSError:
        # 閂鎖寫不進去＝下一次工具呼叫會再武裝一次（`Force=$true`，冪等）。
        # 明說而不是靜默：兩者的痕跡必須分得開。
        return "armed-unlatched"
    return "armed"


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
