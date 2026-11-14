"""sessionctl 收斂閘：出聲之後主控 session 的上下文長到硬門檻，就不准再展開、回合結束要推回收斂。

WHY：`advise_once` 出聲只是提醒，之後在 30 萬 token 的上下文裡繼續派工或閒置，
每一輪都重付整份快取。兩個接點共用同一組判準（出聲在先 ∧ 主控上下文 ≥
`AUTOSDD_SWITCH_HARD_CTX_TOKENS` ∧ 非無人 ∧ `AUTOSDD_SESSION_SWITCH_MODE=auto`）：
  · `converge_verdict`：PreToolUse 擋 Agent／Task／Workflow
    （只擋展開型；讀、改、測、SendMessage 不擋）；
  · `stop_verdict`：Stop 時（主控結束回合、即將閒置的唯一時點）推回一次，另要求無背景代理
    在跑、無已 finalize 的交接包、`stop_hook_active` 為假（至多一個額外回合，同
    `check_pending_handoff`）。
兩者都不寫閂鎖：`/compact` 之後上下文降下來就自動解除。任何例外一律放行（fail-open）。
"""
from __future__ import annotations

import os
from pathlib import Path

from . import handoff, roster, switch

EXPAND_TOOLS = frozenset({"Agent", "Task", "Workflow"})
_LATCHLESS = "（不寫閂鎖：上下文降到門檻下即自動解除）"


def _gate(payload: dict, env) -> tuple[str, int, int] | None:
    """共用前提：回 `(sid, ctx, hard)`；任一前提不成立 ⇒ `None`（放行）。"""
    if env.get("AUTOSDD_UNATTENDED") or switch.switch_mode(env) != "auto":
        return None
    sid, raw = roster._payload_sid(payload), payload.get("transcript_path")
    if not sid or not isinstance(raw, str) or not raw.strip() or not Path(raw).is_file():
        return None
    if not handoff.is_advised(sid, env=env):
        return None
    ctx = roster._scan(Path(raw), False)["ctx_tokens"]
    hard = switch.threshold(switch.HARD_CTX_KEY, env)[0]
    return (sid, ctx, hard) if ctx is not None and ctx >= hard else None


def _latest_live(sid: str, env) -> tuple[Path | None, bool]:
    """該 sid 最新 live 交接包與它是否已 finalize。"""
    rows = [r for r in handoff.list_handoffs(env=env)
            if r["sid"] == sid and r["state"] == "live"]
    if not rows:
        return None, False
    path = rows[-1]["path"]
    return path, handoff.finalize(path)[0] == 0


def _exits(sid: str, env) -> str:
    path, _ = _latest_live(sid, env)
    where = (str(path) if path is not None
             else "（尚無交接包：python tools/sessionctl.py handoff --build）")
    return ("三條出口：\n"
            "  ① 等現有代理交卷 → 補完交接包主控層 → python tools/sessionctl.py handoff "
            f"--finalize {where} → --spawn\n"
            "  ② /compact（上下文降到門檻下自動解除）\n"
            "  ③ AUTOSDD_SESSION_SWITCH_MODE=notify（只出聲）\n")


def converge_verdict(payload: dict, env) -> tuple[int, str]:
    """PreToolUse 收斂閘：`(0, "")` 放行；`(2, 訊息)` 阻斷。任何例外 `(0, "")`。"""
    try:
        if not isinstance(payload, dict) or payload.get("tool_name") not in EXPAND_TOOLS:
            return 0, ""
        if payload.get("agent_id"):  # 子代理自己的呼叫：閘管主控
            return 0, ""
        got = _gate(payload, env)
        if got is None:
            return 0, ""
        sid, ctx, hard = got
        switch.trace("converge_block", sid=sid, ctx=ctx, hard=hard, tool=payload.get("tool_name"))
        return 2, (f"🔴 收斂閘：本 session 已出聲要求換 session，"
                   f"且主控上下文 {ctx:,} ≥ 門檻 {hard:,}，"
                   f"不再展開 {payload.get('tool_name')}（每多一輪就重付整份快取）。"
                   "只擋 Agent／Task／Workflow，讀、改、跑測試、SendMessage 不擋。\n"
                   + _exits(sid, env) + _LATCHLESS + "\n")
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return 0, ""


def _agents_running(payload: dict, sid: str) -> bool:
    """本回合結束時仍有背景**代理**在跑（背景 shell 不算）；優先讀 payload `background_tasks`。"""
    tasks = roster._tasks(payload)
    if tasks is not None:
        return any(t.get("type") == "subagent" and str(t.get("status") or "running") == "running"
                   for t in tasks)
    return bool(roster.running(sid, projects_dir=roster._payload_projects(payload)))


def stop_verdict(payload: dict, env=None) -> str:
    """Stop 推回：回要放進 `decision:block` 的 reason；不成立 ⇒ `""`。任何例外 `""`。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("stop_hook_active"):
            return ""  # 迴圈煞車：第二次 Stop 一律放行
        got = _gate(payload, env)
        if got is None:
            return ""
        sid, ctx, hard = got
        if _agents_running(payload, sid) or _latest_live(sid, env)[1]:
            return ""
        switch.trace("converge_stop_block", sid=sid, ctx=ctx, hard=hard)
        return (f"收斂閘（Stop）：本 session 已出聲要求換 session，"
                f"主控上下文 {ctx:,} ≥ 門檻 {hard:,}，"
                "沒有背景代理在跑、也沒有已 finalize 的交接包——"
                "現在結束回合只會閒置在大上下文裡，下一次醒來整份重寫快取。"
                "請這一回合就收斂：\n" + _exits(sid, env)
                + "（只推回這一次；第二次 Stop 放行。）" + _LATCHLESS)
    except Exception:  # noqa: BLE001 — fail-open
        return ""
