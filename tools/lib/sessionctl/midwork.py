"""半路停工判準：主控說「接下來我還要做事」，卻在沒有任何背景工作會叫醒它的狀態下結束回合。

立案（掌舵者真機回報）：sid 16496139-2bf1-43a1-bb3d-5b6650fa8273，2026-11-17。主控收完子代理交卷、
親驗通過，最後一則寫「…記進計畫檔，現查額度後派下一棒。」就結束回合；當時沒有背景代理／背景任務、
工作樹有 7 個未提交的檔、沒問任何問題 ⇒ 沒有東西會叫醒它，閒置約 6.8 小時，醒來快取已冷、
整份重寫約 20 萬 token。既有 `check_pending_handoff.py` 只認「把決定留給掌舵者」的詞表。

判準（狀態為主、措辭為輔；全部成立才命中，純函式、無副作用除了一次有逾時的 `git status`）
------------------------------------------------------------------------------------
1. Stop payload 有 `background_tasks` 欄位且其中沒有任何 running 項（欄位缺席＝舊 harness ⇒ 不判）。
2. 最後一則回覆命中進行式詞表（`midwork_hits`）：引號內、緊鄰否定、他人負責（掌舵者／新 session…）
   的句子不算；回覆內出現合法換手標記（`HANDOFF_EXIT_RE`）整則不判。
3. 狀態佐證：本回合做過非唯讀工具，或工作樹髒（`git status --porcelain` 非空）；兩者都量不到不判。
（非 stop_hook_active／非無人窗口／本回合無 AskUserQuestion 由呼叫端 hook 判。）

誠實劃界：只認詞表；`background_tasks` 欄位的語意以 harness 為準（roster._tasks 同讀法）；
本 repo 工作樹平常就髒（帳本、perf 基線），所以佐證一旦措辭命中幾乎恆成立——真正的鑑別力在
措辭＋「沒有任何背景工作」兩項。
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable

#: 非唯讀工具＝本回合「做過事」的證據；唯讀集合之外一律算。
READONLY_TOOLS = frozenset({"Read", "Grep", "Glob"})

_NEXT = r"(?:接著|接下來|然後|隨後|稍後|待會|馬上|立刻|立即|現在就)"
_ACT = (r"(?:派|跑|做|修|寫|驗|推送|提交|審|查|續|執行|處理|進行|開始|重跑|重驗|收尾|合併|"
        r"commit|push)(?!了|過|完|好)")
#: 進行式詞表。刻意用「時序詞＋短距離內動作詞」，不收裸「下一步」：交接包節名「下一步確切指令」
#: 與「下一步請掌舵者…」都不是主控自己要做的事。
MIDWORK_RE = re.compile(
    rf"({_NEXT}[我就會要將再先還親全]{{0,2}}\s?{_ACT}"
    rf"|下一步[是為：:，,]?\s*(?:我)?(?:要|會|將)?{_ACT}"
    r"|現查[^。！？!?\n]{0,12}後(?:派|跑|做|再)"
    r"|立刻續做|正在進行|這不是收尾)")
#: 否定：看詞前 8 個字元（與 `check_pending_handoff.NEGATION_WINDOW` 同尺度）。
_NEGATION_RE = re.compile(r"(沒有|不會|不需|無需|不必|不用|不再|不要|未|無須|別)")
_NEGATION_WINDOW = 8
#: 他人負責或條件／等人的句子不是「我現在接著做」：掌舵者／新 session 做、等人親打或說「繼續」
#: （額度停工另由 park 判準守）、假設句（描述守衛本身的文字）、反問句。
_OTHER_OWNER_RE = re.compile(
    r"(掌舵者|您|新 ?session|新視窗|新代理|新對話|接手|由.{0,6}負責|親打|說一聲|請你|等你|"
    r"若|如果|假如|萬一|[？?]\s*$)")
_SENTENCE_RE = re.compile(r"(?<=[。！？!?\n])")
#: 合法換手標記：回覆自述已封存／已 park／已 spawn ⇒ 這個停是續航協定的正規出口。
HANDOFF_EXIT_RE = re.compile(
    r"(handoff\s+--(?:spawn|finalize)|sessionctl\.py\s+park|PARK_VERDICT=|park\s+--done|"
    r"已封存|已交棒|已\s*park|已\s*spawn)", re.IGNORECASE)


def midwork_hits(text: str, is_quoted: Callable[[str, int, int], bool]) -> list[dict]:
    """措辭那一半：`text` 裡「主控自述接下來還要做事」的句子（`[]`＝沒有）。"""
    if HANDOFF_EXIT_RE.search(text):
        return []
    hits: list[dict] = []
    for sentence in _SENTENCE_RE.split(text):
        if not sentence.strip() or _OTHER_OWNER_RE.search(sentence):
            continue
        for match in MIDWORK_RE.finditer(sentence):
            if is_quoted(sentence, match.start(), match.end()):
                continue
            if _NEGATION_RE.search(sentence[max(0, match.start() - _NEGATION_WINDOW):match.end()]):
                continue
            hits.append({"word": match.group(0), "sentence": sentence.strip()[:200]})
    return hits


def background_idle(payload: dict) -> bool:
    """Stop payload 帶 `background_tasks` 且沒有任何會叫醒主控做事的 running 項。
    欄位缺席（舊 harness）回 False ⇒ 不判（fail-open）。讀法同 `roster._tasks`。

    純保溫／監督 shell（`sessionctl.py watch`／`keepwarm`）預設不算「會叫醒主控做事」的背景工作
    （判準單一家＝roster.is_supervision_shell，REQ-WP-22；不複製正則）；**例外（QuotaWall S-18）**：
    帶目標的主載具（running shell ∧ holder 活、`wake_at` 在未來、mode∈chain／single）是會在
    預定時刻叫醒主控續工的事件源 ⇒ 有它在就不是閒置，半路停工不判。`periodic` 只保溫不續工，
    維持排除（舊行為）。競態寬限：holder 尚未寫入但有 running 的本 sid keepwarm shell ⇒ 同一
    背景任務 id 只寬限一次（`qw_latch.latch_grace`；**有副作用，一個 Stop 只准呼叫一次**）。"""
    if "background_tasks" not in payload:
        return False
    raw = payload["background_tasks"]
    rows = [raw] if isinstance(raw, dict) else raw if isinstance(raw, list) else []
    running = [r for r in rows
               if isinstance(r, dict) and str(r.get("status") or "running") == "running"]
    if any(not _is_supervision(r) for r in running):
        return False
    return not (running and _primary_event_source(payload, running))


def _primary_event_source(payload: dict, shells: list[dict]) -> bool:
    """S-18：running 的監督 shell 之中是否有「會在預定時刻叫醒主控續工」的主載具；判不出 ⇒ False
    （維持排除＝舊行為）。"""
    try:
        from datetime import datetime  # noqa: PLC0415

        from . import holder, qw_latch, roster  # noqa: PLC0415 — lazy：hook 鏈不為這一格預付成本

        sid = roster._payload_sid(payload)
        if not sid:
            return False
        if qw_latch.primary_live(payload, sid, datetime.now().astimezone()):
            return True
        if holder.read(sid) is not None:
            return False
        for task in shells:
            cmd = str(task.get("command") or "")
            if roster.KEEPWARM_CMD_RE.search(cmd) and sid in cmd:
                return qw_latch.latch_grace(sid, task.get("id"))
        return False
    except Exception:  # noqa: BLE001
        return False


def _is_supervision(task: dict) -> bool:
    try:
        from . import roster  # noqa: PLC0415 — lazy：hook 鏈不為這一格預付 import 成本
        return roster.is_supervision_shell(task)
    except Exception:  # noqa: BLE001 — 判不出來＝不排除（退回舊行為：任何 running 都算工作）
        return False


def tree_dirty(cwd: str) -> bool | None:
    """工作樹有未提交改動？量不到（非 git／逾時／任何錯）回 None。逾時 3 秒、無 console 視窗。"""
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", "status", "--porcelain"], cwd=cwd,
            capture_output=True, encoding="utf-8", errors="replace", timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:  # noqa: BLE001 — 量不到＝不佐證，不是故障
        return None
    return bool(proc.stdout.strip()) if proc.returncode == 0 else None


def did_work(tools: set[str], cwd: str, dirty: Callable[[str], bool | None] = tree_dirty) -> bool:
    """狀態佐證：本回合有非唯讀 tool_use，或工作樹髒；都量不到回 False。"""
    return bool(tools - READONLY_TOOLS) or dirty(cwd) is True


def block_message(hits: list[dict]) -> str:
    """推回主控的那一句（可滿足性：三條出路都在句內）。"""
    words = "／".join(sorted({str(h.get("word")) for h in hits}))
    return (f"🔴 你說接下來還要做事（命中：{words}），但現在沒有任何背景工作會叫醒你——結束回合"
            "＝閒置到有人回來、快取冷掉後整份重寫（2026-11-17 事故：閒置 6.8 小時、約 20 萬 "
            "token）。"
            "現在就做下一步；真的要停，先封存交接包（`handoff --finalize`）並 `--spawn`／"
            "`python tools/sessionctl.py park`，或用 AskUserQuestion 問掌舵者。（只推回這一次；"
            "第二次 Stop 放行。）")
