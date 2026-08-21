"""哨兵生命週期 —— **武裝側**：session 累積到什麼程度才值得被判定為「該武裝一支哨兵」。

本檔是 `tools/lib/sentinel_lifecycle.py` 依內聚子功能拆出的一半（該檔 LOC 分級收斂：
guardrail_lib ≤400 行棘輪，見 `check_loc_budget.py` 的 `[ROOT-TOOLS-WARN]`）。下面是
武裝側完整的立案脈絡與門檻量測依據——**原文搬遷，未經改寫**；回收側（GC／
`schedule_backend` delegation／R83 複審 A-01）的設計討論仍留在 `sentinel_lifecycle.py`，
不在此複製第二份。`sentinel_lifecycle.py` 對本檔一律用 `import` 委派，公開函式的
簽章與行為完全不變。

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
"""
from __future__ import annotations

import json
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
