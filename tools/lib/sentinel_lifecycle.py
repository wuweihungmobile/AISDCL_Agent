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

回歸鎖：`tools/tests/test_context_budget_guard.py`（判準的紅綠、GC 的保護面，皆合成注入）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

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

#: 無視窗旗標。語意的唯一的家＝`.claude/hooks/context_budget_guard.NO_WINDOW`；本檔不能
#: import 它（hook → quota_gate → …，反向會成環），故複製表達式並由相等鎖守著不漂開
#: （見 `tools/lib/quota_meter.NO_WINDOW` 上方那段的同一組理由）。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

#: 同上，理由與唯一的家見 `context_budget_guard.PS_UTF8_PRELUDE`（相等鎖守著兩份不漂開）。
PS_UTF8_PRELUDE = ("$OutputEncoding = [Console]::OutputEncoding = "
                   "[Text.UTF8Encoding]::new($false)\n")


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
def _powershell(script: str, timeout: int = 120) -> tuple[int, str]:
    """跑一段 PowerShell，回 `(rc, stdout)`。

    🔴 指名 `powershell.exe`（5.1）而不是 `pwsh`：schtasks 相關操作在本 repo 一律以它為準
    （見 `session_resume_planner.run_powershell` 的同一段理由），而本機兩個引擎的預設編碼
    不同。`creationflags`：本檔的 CLI 也可能被無 console 的父行程叫到，理由見 `NO_WINDOW`。
    """
    holder = Path(tempfile.mkdtemp(prefix="autosdd_sentinel_gc_")) / "run.ps1"
    # UTF-8 前置行：本檔會印出工作名與理由，而 PS 5.1 預設以主控台 codepage 寫 stdout
    # ⇒ 非 ASCII 會降解（同 `guard.PS_UTF8_PRELUDE` 的立案）。本檔不能 import guard（成環），
    # 故複製同一個字面，並由 `test_context_budget_guard.py` 的相等鎖守著不漂開。
    holder.write_text(PS_UTF8_PRELUDE + script, encoding="utf-8-sig", newline="\r\n")
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(holder)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, check=False, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return proc.returncode, proc.stdout


def sentinel_task_names() -> list[str]:
    """現存的哨兵工作名。

    🔴 一律用 `Get-ScheduledTask`：`schtasks /query` 在本機實測會回空＝假陰性
    （根 CLAUDE.md〈查詢載具自己也會騙人〉）。而假陰性在**這一支**特別危險——
    查不到就等於「沒有東西要收」，GC 會回報一切正常。
    """
    rc, out = _powershell(
        f"Get-ScheduledTask | Where-Object {{ $_.TaskName -like '{TASK_PREFIX}*' }} "
        "| ForEach-Object { $_.TaskName }\n")
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip().startswith(TASK_PREFIX)]


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
    quoted = task.replace("'", "''")
    rc, _ = _powershell(
        f"Unregister-ScheduledTask -TaskName '{quoted}' -Confirm:$false\n"
        f"if (Get-ScheduledTask -TaskName '{quoted}' -EA SilentlyContinue) "
        "{ exit 1 } else { exit 0 }\n")
    return rc


def _sweep_artifacts(session_id: str, tmp: Path) -> list[str]:
    """把該 session 的哨兵痕跡一起收掉（任務書／閂鎖／boot log／水位 state）。"""
    gone = []
    for name in (f"autosdd_resume_plan_{session_id}.md",
                 f"{ARM_MARKER_PREFIX}{session_id}.json",
                 f"autosdd_sentinel_boot_{session_id}.log",
                 f"autosdd_ctxguard_{session_id}.json"):
        path = tmp / name
        try:
            path.unlink()
            gone.append(name)
        except OSError:
            continue
    return gone


def gc(*, apply: bool = False, keep: tuple[str, ...] = (),
       min_idle: float = GC_IDLE_SECONDS, tmp_dir: str | None = None) -> list[dict]:
    """列出每支哨兵的處置；`apply=False`（預設）只看不動。

    🔴 預設 dry-run 是刻意的：這支工具的失手代價是不可逆的（拆掉別人正在等的續航），
    而它的**價值**在 dry-run 就已經全部兌現了——看清單本來就是掌舵者要的那件事。
    """
    base = _transcript_dir()
    tmp = Path(tmp_dir or tempfile.gettempdir())
    protected_ids = set(keep) | {_newest_session(base)}
    now = time.time()
    rows: list[dict] = []
    for task in sentinel_task_names():
        sid = session_of(task)
        # 🔴 `base is None` 一律傳 `None`（＝量不到），**不得**塌成 `False`：
        # 那個塌陷正是本檔第一版實跑 dry-run 時把三支哨兵全判成可收的原因。
        transcript = (base / f"{sid}.jsonl") if base is not None else None
        exists = None if base is None else bool(transcript and transcript.is_file())
        idle = (now - transcript.stat().st_mtime) if exists else None
        state = plan_state(tmp / f"autosdd_resume_plan_{sid}.md") if exists else None
        reap, why = reap_verdict(transcript_exists=exists, idle_seconds=idle,
                                 state=state, protected=sid in protected_ids,
                                 min_idle=min_idle)
        row = {"task": task, "session_id": sid, "reap": reap, "why": why,
               "state": state, "idle_hours": None if idle is None else round(idle / 3600, 2)}
        if reap and apply:
            row["unregister_rc"] = _remove_task(task)
            row["swept"] = _sweep_artifacts(sid, tmp)
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
    if not rows:
        print("（沒有任何 AutoSDD_Sentinel_* 工作；或 Get-ScheduledTask 取不到——"
              "後者是假陰性，請自行現查一次）")
        return 0
    for row in rows:
        mark = "🗑 收" if row["reap"] else "✅ 留"
        if row["reap"] and args.apply:
            mark += f"（rc={row.get('unregister_rc')}，殘骸 {len(row.get('swept') or [])} 件）"
        print(f"{mark}  {row['task']}\n      {row['why']}")
    if not args.apply and any(r["reap"] for r in rows):
        print("\n以上是 dry-run。要真的收：加 --apply（會 Unregister-ScheduledTask 並刪殘骸）")
    return 0


if __name__ == "__main__":
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
