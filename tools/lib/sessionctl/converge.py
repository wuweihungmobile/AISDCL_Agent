"""sessionctl 收斂閘：主控 session 的上下文長到硬線，就不准再展開、回合結束要推回收斂。

WHY（R216 改寫）：硬線 85 萬是 autocompact（最小 881,938）之前的最後防線——autocompact 一次把上下文
砍到 1～2 萬，比交接包更失真；25 萬到 85 萬之間人要的是保留上下文，不是被推著換窗
（掌舵者 2026-11-18），所以不再要求「已出聲」（D12）。兩個接點共用同一組判準
（主控上下文 ≥ `AUTOSDD_SWITCH_HARD_CTX_TOKENS` ∧ 非無人 ∧ `AUTOSDD_SESSION_SWITCH_MODE=auto`）：
  · `converge_verdict`：PreToolUse 擋 Agent／Task／Workflow
    （只擋展開型；讀、改、測、SendMessage 不擋）；
  · `stop_verdict`：Stop 時（主控結束回合、即將閒置的唯一時點）推回一次，另要求無背景代理
    在跑、無已 finalize 的交接包、`stop_hook_active` 為假（至多一個額外回合，同
    `check_pending_handoff`）。
第三個判準＝park（`park.stop_verdict`：短窗額度快撞線卻沒有續航憑證）。
兩者都不寫閂鎖：`/compact` 之後上下文降下來就自動解除。任何例外一律放行（fail-open）。
"""
from __future__ import annotations

import os
from pathlib import Path

from . import control, keepwarm, roster, seal, supervise, switch

EXPAND_TOOLS = frozenset({"Agent", "Task", "Workflow"})
_LATCHLESS = "（不寫閂鎖：上下文降到門檻下即自動解除）"


def _gate(payload: dict, env) -> tuple[str, int, int] | None:
    """共用前提：回 `(sid, ctx, hard)`；任一前提不成立 ⇒ `None`（放行）。"""
    if env.get("AUTOSDD_UNATTENDED") or switch.switch_mode(env) != "auto":
        return None
    sid, raw = roster._payload_sid(payload), payload.get("transcript_path")
    if not sid or not isinstance(raw, str) or not raw.strip() or not Path(raw).is_file():
        return None
    ctx = roster._scan(Path(raw), False)["ctx_tokens"]
    hard = switch.threshold(switch.HARD_CTX_KEY, env)[0]
    return (sid, ctx, hard) if ctx is not None and ctx >= hard else None


def _exits(sid: str, env) -> str:
    done = seal.handed_over(sid, env)
    if done is not None:
        return (f"本 session 已交棒（包：{done}），請到新視窗；這裡不要再派工。\n"
                "  ② 或 /compact（上下文降到門檻下自動解除）\n"
                "  ③ 或 AUTOSDD_SESSION_SWITCH_MODE=notify（只出聲）\n")
    row = seal.latest_package(sid, env)
    where = (str(row["path"]) if row is not None and row["state"] == "live"
             else "（尚無交接包：python tools/sessionctl.py handoff --build）")
    return ("三條出口：\n"
            "  ① 等現有代理交卷 → 補完交接包主控層 → python tools/sessionctl.py handoff "
            f"--finalize {where} → --spawn\n"
            "  ② /compact（上下文降到門檻下自動解除）\n"
            "  ③ AUTOSDD_SESSION_SWITCH_MODE=notify（只出聲）\n")

def _wall_pretool(payload: dict, env, now, seams: dict) -> tuple[int, str]:
    """額度牆擋派（QuotaWall §6.1、W11a；判準 `quotawall.pretool_verdict`）。fail-open。

    WHY（H.2-2）：這是 rc 2 硬擋，輸入污染的代價是工作被擋；它的上線前提是 `ping_pp_eff` 的乾淨
    樣本門檻（REQ-QW-74，已在 `qw_calc`／`qw_schema`）已生效——順序鎖的行為斷言＝AT-QW-84。"""
    try:
        from . import qw_guard  # noqa: PLC0415 — lazy：只有 Agent／Task／Workflow 才付

        return qw_guard.pretool(payload, env, now=now, **seams)
    except Exception:  # noqa: BLE001
        return 0, ""


def converge_verdict(payload: dict, env, *, now=None, **seams) -> tuple[int, str]:
    """PreToolUse 收斂閘＋額度牆擋派：`(0, "")` 放行；`(2, 訊息)` 阻斷。任何例外 `(0, "")`。
    兩閘都成立只出收斂閘訊息＋一行額度牆摘要（REQ-QW-10）。`now`／`read_quota` 等為測試縫。"""
    try:
        if not isinstance(payload, dict) or payload.get("tool_name") not in EXPAND_TOOLS:
            return 0, ""
        if payload.get("agent_id"):  # 子代理自己的呼叫：閘管主控
            return 0, ""
        got = _gate(payload, env)
        wall_rc, wall_msg = _wall_pretool(payload, env, now, seams)
        if got is None:
            if wall_rc == 2:
                return 2, wall_msg
            # FR-W8：放行時帶一行掛監督附註；notify 模式的額度牆訊息（rc 0）一併帶出
            return 0, "\n".join(t for t in (wall_msg, supervise.dispatch_note(payload, env)) if t)
        sid, ctx, hard = got
        switch.trace("converge_block", sid=sid, ctx=ctx, hard=hard, tool=payload.get("tool_name"))
        summary = f"額度牆摘要：{wall_msg.splitlines()[0]}\n" if wall_rc == 2 and wall_msg else ""
        return 2, (f"🔴 收斂閘：主控上下文 {ctx:,} ≥ 硬線 {hard:,}（再長就撞 autocompact），"
                   f"不再展開 {payload.get('tool_name')}。"
                   "只擋 Agent／Task／Workflow，讀、改、跑測試、SendMessage 不擋。\n"
                   + _exits(sid, env) + summary + _LATCHLESS + "\n")
    except Exception:  # noqa: BLE001 — hook 內任何例外一律放行
        return 0, ""


def _finalized_wake(payload: dict, env) -> str:
    """已封存交接包（含已 ack／spawn＝已交棒）的 session 還掛著背景任務 ⇒ 推回（DEF-200-588）。

    WHY：背景任務一結束 harness 就叫醒這個 session；交接後它本來就不該再動，醒來那一下
    快取已冷、整份上下文重寫（sid eb1cb524，2026-11-15 08:34：一次 235,445 token）。
    重寫發生在模型能反應之前，所以唯一擋得住的時點是交接後結束回合的這一刻。
    包的判準用 `seal.wake_package`（不分 live／acked；E-HD-1：舊版只認 live，包被 ack 後失明；
    E-CW-1：只寫完主控層、未封存不算——代理仍在飛時先備包是合理路徑）。
    不看出聲與上下文門檻（事故當時 26.8 萬，在硬門檻之下）；payload 沒有
    `background_tasks` 欄就不判（fail-open）。"""
    if env.get("AUTOSDD_UNATTENDED") or switch.switch_mode(env) == "off":
        return ""
    sid = roster._payload_sid(payload)
    live = [t for t in (roster._tasks(payload) or [])
            if str(t.get("status") or "running") == "running"]
    if not sid or not live:
        return ""
    path = seal.wake_package(sid, env, payload.get("transcript_path"))
    if path is None:
        return ""
    if seal.handed_over(sid, env) is None:
        # 封存有效、尚未交棒（DES §4.2，A4）：只列「非代理、非監督」的背景任務（`ci_wait` 等）。
        # 在飛代理交監督閘看管（兩閘互斥，CI-1(d)：不得同時叫人殺代理又叫人掛 watch 監督它）；
        # keepwarm／watch shell 依設計掛著，保溫就是要叫醒本 session、醒來讀熱快取。
        # 已交棒者照舊全停（醒來就是整份重寫）。
        live = control.wakeable_tasks(live)
        if not live:
            return ""
    switch.trace("finalized_wake_block", sid=sid, tasks=len(live))
    return (f"冷叫醒閘（Stop）：交接包已封存（{path}），但本 session 還有 {len(live)} 個"
            "背景任務在跑——它一結束就會把這個已交棒的 session 叫醒，快取已冷、整份上下文重寫。"
            "請現在用 TaskStop 停掉它們（輸出已導檔者由新 session 重查，例："
            "python tools/ci_wait.py --commit <完整 SHA>），再結束回合。"
            "（只推回這一次；第二次 Stop 放行。）")


def stop_verdict(payload: dict, env=None, *, mute: str | None = None, raw_env=None,
                 **seams) -> str:
    """Stop 推回的合成（ARCH §1.4 互斥兩組；QuotaWall §6.2～§6.4）；回 reason，不成立 ⇒ `""`；
    任何例外 `""`。`mute`＝呼叫端（hook）已算好的 `qw_guard.mute` 結果（缺省自己算）；
    `raw_env`＝hook 行程的原始環境（主載具閘的 `off` 判準用，OIR 讓路注入不算）；其餘為測試縫。

    · 牆中（`mute=="wall"`）：整體回 `""`（只剩出聲，不推回）。
    · 有在飛子代理：冷叫醒閘（已交棒該 TaskStop）→ 額度牆在飛側（close ⇒ TaskStop 在飛代理，
      不得要求先封存）→ 監督閘（沒人看管該掛 watch）取第一個非空。
    · 無在飛子代理：冷叫醒閘（已交棒卻掛背景 shell）優先；否則封存閘、額度類（close 的收尾步驟／
      none 階段的既有 park 推回，主載具在跑時套 S-18 閂鎖／主載具閘）、保溫閘
      （`keepwarm.stop_verdict`：沒有任何背景任務在跑、人離開後快取會冷）成立者 **合併成一則**，
      次序 封存→park→主載具→保溫，只一個成立就出那一個；額度類已涵蓋 keepwarm 時不再重複保溫閘。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("stop_hook_active"):
            return ""  # 迴圈煞車：第二次 Stop 一律放行
        sid = roster._payload_sid(payload)
        supervise.record_crons(payload, sid)  # 只記錄、不影響任何判決
        from . import qw_guard  # noqa: PLC0415 — lazy：與 park 同一條「Stop 沒走到就不付」紀律

        if (qw_guard.mute(payload, env, **seams) if mute is None else mute) == "wall":
            return ""
        if sid and seal.agents_running(payload, sid):
            # WHY：在飛側只准冷叫醒閘（已交棒該 TaskStop）、額度牆（close 該 TaskStop）與監督閘
            # （沒人看管該掛 watch）；冷叫醒優先——互斥兩組見 ARCH §1.4；封存／park 要求無在飛
            # 代理，不在這一側。
            return (_finalized_wake(payload, env) or qw_guard.inflight(payload, env, **seams)
                    or supervise.stop_verdict(payload, env))
        wake = _finalized_wake(payload, env)
        if wake:
            return wake
        quota, covers = qw_guard.idle(payload, env, **seams)
        gate = "" if (quota or covers) else qw_guard.primary_gate(
            payload, env, raw_env=raw_env, now=seams.get("now"))
        keep = "" if (covers or gate) else keepwarm.stop_verdict(payload, env)
        return "\n\n".join(x for x in (seal.stop_verdict(payload, env), quota, gate, keep) if x)
    except Exception:  # noqa: BLE001 — fail-open
        return ""


def stop_notice(payload: dict, env=None, **seams) -> str:
    """S-18 閂鎖之後的 `systemMessage`「備援缺席」（不 block）；Stop 沒有推回時由 hook 帶出。"""
    try:
        from . import qw_guard  # noqa: PLC0415

        return qw_guard.stop_notice(payload, os.environ if env is None else env, **seams)
    except Exception:  # noqa: BLE001
        return ""
