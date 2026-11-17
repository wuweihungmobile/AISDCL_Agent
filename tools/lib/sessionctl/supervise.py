"""sessionctl 監督憑證與 Stop 監督閘（R3 WP-4B；ARCH §1.3／§1.4／§1.9；FR-W5～W9、FR-S4）。

WHY：主控派出背景子代理後直接結束回合、沒人看管（21 天 655 個區間）。`sessionctl watch`
（WP-4A）是看管程序；本檔補「沒掛就推回」。判準三處共用同一個 `credential`：
  · `stop_verdict`：Stop 推回（有在飛子代理 ∧ 憑證不是 valid，至多一次）；
  · `watching_text`：憑證 valid 時 Stop 出聲改字樣（FR-W7，由 `roster.stop_message` 薄呼叫）；
  · `status_line`：`status` 的一行（只能用心跳副證，status 沒有 payload）。
全部 fail-open：讀不動、例外一律當 valid／空字串——寧可漏推，不可擋死回合結束。
時鐘、讀心跳、pid 探測皆以參數注入（不為測試加環境變數）。
sessionctl 不得 import wastecensus；事件名常數由測試與量測端核對相等。
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import endurance_env

from . import handoff, procstop, roster, switch, watch

EV_SUPERVISE_STOP_BLOCK = "supervise_stop_block"
# WHY 180 秒＝6 個輪詢間隔（watch.POLL_SECONDS＝30）：連 6 輪沒寫心跳才算卡死，
# 單次磁碟／排程抖動不誤判。
HEARTBEAT_FRESH_SECONDS = 180.0
WATCH_CMD_MARK = "sessionctl.py watch"
WATCH_CMD = "python tools/sessionctl.py watch"
VALID, STUCK, NONE = "valid", "stuck", "none"
_BASE_CTX_NOTE = "子代理起步底盤約 8.4 萬 token，上下文預算＝底盤＋工作空間"


def _epoch_now(now) -> float:
    if now is None:
        return time.time()
    return now.timestamp() if isinstance(now, datetime) else float(now)


def read_heartbeat(sid: str) -> dict | None:
    """心跳檔內容；不存在 ⇒ `None`；讀不動／壞 JSON ⇒ 拋（呼叫端 fail-open 當 valid）。"""
    path = watch.heartbeat_path(sid)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("heartbeat is not an object")
    return data


def pid_alive(pid) -> bool:
    """Windows 沿 `handoff._alive`；其他平台 `os.kill(pid, 0)`（sys.platform 守衛內）。"""
    if sys.platform == "win32":
        return handoff._alive(pid)
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # PermissionError 等：行程存在
    return True


def _fresh(beat: dict, now: float) -> bool:
    stamp = procstop.parse_iso(beat.get("heartbeat_at"))
    return stamp is not None and now - stamp <= HEARTBEAT_FRESH_SECONDS


def _main_proof(tasks: list[dict]) -> bool:
    return any(t.get("type") == "shell" and str(t.get("status") or "running") == "running"
               and WATCH_CMD_MARK in str(t.get("command") or "") for t in tasks)


def credential(payload: dict, sid: str, now=None, *, heartbeat_reader=read_heartbeat,
               alive=pid_alive) -> str:
    """監督憑證四態（ARCH §1.3）：`valid`／`stuck`／`none`；任何例外 ⇒ `valid`（fail-open）。

    主證＝payload `background_tasks` 內有 running 的 `sessionctl.py watch` shell（它結束才會叫醒
    主控；別的終端手跑的 watch 不算）。副證＝心跳檔新鮮。
    舊 harness 沒有該欄 ⇒ 只剩副證＋pid 活著。"""
    try:
        at = _epoch_now(now)
        tasks = roster._tasks(payload)
        beat = heartbeat_reader(sid)
        if tasks is None:
            ok = beat is not None and _fresh(beat, at) and alive(beat.get("pid"))
            return VALID if ok else NONE
        if not _main_proof(tasks):
            return NONE
        return STUCK if beat is not None and not _fresh(beat, at) else VALID
    except Exception:  # noqa: BLE001 — fail-open
        return VALID


def _agents(payload: dict) -> list[dict]:
    return [t for t in (roster._tasks(payload) or [])
            if t.get("type") == "subagent" and str(t.get("status") or "running") == "running"]


def _reason(cred: str, n: int) -> str:
    head = (f"監督閘（Stop）：還有 {n} 支背景子代理在跑，卻沒有有效的監督憑證——"
            "交卷／停滯／超時沒人叫醒你。\n")
    tail = "（只推回這一次；第二次 Stop 放行。）"
    if cred == STUCK:
        return (head + "監督程序看起來卡死了（心跳超過 3 分鐘沒更新）："
                "先 TaskStop 那個 watch 背景 shell，"
                f"再重掛：{WATCH_CMD}（run_in_background、輸出導檔）。" + tail)
    return (head + f"請現在掛上：{WATCH_CMD}"
            "（Bash／PowerShell 工具用 run_in_background、輸出導檔），"
            "它在代理交卷、停滯、超時、額度到線或快取快冷時結束，harness 會叫醒你。" + tail)


def stop_verdict(payload: dict, env=None, now=None, *, heartbeat_reader=read_heartbeat,
                 alive=pid_alive) -> str:
    """Stop 監督閘：回 reason；不推回 ⇒ `""`。
    只看子代理（背景 shell／workflow／monitor 不觸發）。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("stop_hook_active"):
            return ""
        if env.get("AUTOSDD_UNATTENDED") or switch.switch_mode(env) != "auto":
            return ""
        sid, agents = roster._payload_sid(payload), _agents(payload)
        if not sid or not agents:
            return ""
        cred = credential(payload, sid, now, heartbeat_reader=heartbeat_reader, alive=alive)
        if cred == VALID:
            return ""
        switch.trace(EV_SUPERVISE_STOP_BLOCK, sid=sid, n_agents=len(agents), credential=cred)
        return _reason(cred, len(agents))
    except Exception:  # noqa: BLE001 — fail-open
        return ""


def watching_text(payload: dict, sid: str, n_agents: int, now=None, *,
                  heartbeat_reader=read_heartbeat, alive=pid_alive) -> str:
    """憑證 valid 時 Stop 出聲的字樣（FR-W7）；不是 valid／例外 ⇒ `""`（呼叫端維持原字樣）。"""
    try:
        if credential(payload, sid, now, heartbeat_reader=heartbeat_reader, alive=alive) != VALID:
            return ""
        beat = heartbeat_reader(sid) or {}
        stamp = procstop.parse_iso(beat.get("keepwarm_at"))
        when = datetime.fromtimestamp(stamp).astimezone().strftime("%H:%M") if stamp else "未知"
        stall = beat.get("stall_min")
        gate = f"{stall:g} 分" if isinstance(stall, (int, float)) else "未知"
        return f"{n_agents} 支背景代理由監督程序看管中（下次叫醒最晚 {when}；停滯門檻 {gate}）。"
    except Exception:  # noqa: BLE001
        return ""


def dispatch_note(payload: dict, env=None, now=None, *, heartbeat_reader=read_heartbeat) -> str:
    """PreToolUse／Agent｜Task 放行時的一行附註（FR-W8）：沒有新鮮心跳才出；子代理自己的呼叫、
    無人窗口、模式 off ⇒ 空字串。"""
    env = os.environ if env is None else env
    try:
        if not isinstance(payload, dict) or payload.get("tool_name") not in ("Agent", "Task"):
            return ""
        if payload.get("agent_id") or env.get("AUTOSDD_UNATTENDED"):
            return ""
        if switch.switch_mode(env) == "off":
            return ""
        sid = roster._payload_sid(payload)
        beat = heartbeat_reader(sid) if sid else None
        if beat is not None and _fresh(beat, _epoch_now(now)):
            return ""
        return (f"派工後同一回合掛監督：{WATCH_CMD}（run_in_background、輸出導檔）；"
                f"{_BASE_CTX_NOTE}")
    except Exception:  # noqa: BLE001
        return ""


def status_line(sid: str, now=None, *, heartbeat_reader=read_heartbeat, alive=pid_alive) -> str:
    """`status` 的一行（FR-W9）。status 沒有 payload ⇒ 只能依心跳檔判斷（字樣標明）。"""
    try:
        at = _epoch_now(now)
        beat = heartbeat_reader(sid)
        if beat is None:
            return "監督：無（依心跳檔；沒有 watch 在跑）"
        age = at - (procstop.parse_iso(beat.get("heartbeat_at")) or at)
        state = "有效" if _fresh(beat, at) and alive(beat.get("pid")) else "卡死"
        kw = procstop.parse_iso(beat.get("keepwarm_at"))
        kw_txt = datetime.fromtimestamp(kw).astimezone().strftime("%H:%M") if kw else "未知"
        return (f"監督：{state}（依心跳檔；pid {beat.get('pid')}、啟動 {beat.get('started_at')}、"
                f"keepwarm {kw_txt}、心跳距今 {int(age)} 秒、"
                f"門檻 {int(HEARTBEAT_FRESH_SECONDS)} 秒）")
    except Exception as exc:  # noqa: BLE001 — status 是唯讀診斷
        return f"監督：量不到（{type(exc).__name__}）"


def _crons_path(sid: str) -> Path:
    return endurance_env.trace_dir() / "watch" / f"{sid}.crons"


def record_crons(payload: dict, sid: str) -> None:
    """Stop 時記下 `session_crons` 是否非空（FR-S4）；payload 沒有該欄就不寫；不拋。"""
    try:
        if not isinstance(payload, dict) or "session_crons" not in payload or not sid:
            return
        path = _crons_path(sid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("1" if payload["session_crons"] else "0", encoding="utf-8", newline="\n")
    except OSError:
        pass


def crons_state(sid: str) -> bool | None:
    """讀 `record_crons` 的記錄：有排程 ⇒ True、無 ⇒ False、讀不到 ⇒ None。"""
    try:
        raw = _crons_path(sid).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return True if raw == "1" else False if raw == "0" else None
