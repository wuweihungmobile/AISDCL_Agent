"""控制態事實讀取器（DES §3.1、§3.4、§6.5；REQ-CTL-06、15、16）。

WHY：`control.classify` 是純合成，事實要有人去讀。本檔向 `roster`／`supervise`／`holder`／`park`／
`seal`／`handoff` 取值組成 `Facts`；**憑證值（pid、心跳年齡、保溫／排程的下次叫醒時刻）一律取自
行程表、心跳檔、holder 列、park 標記檔，不取主控自述或標記文字**（掌舵者問題 3：看管狀態要對人眼
可見，且不能是假的）。任何一項讀不到就落回保守值（`none`／`unknown`／`None`＝印 `?`），不拋、不猜。

`segment(sid, transcript_path)` 給 `tools/statusline_context_feed.py`（statusLine 每則訊息都叫它）：
10 秒檔案快取、150 ms 時限、任何例外回空字串（fail-open，同該檔紀律）。
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

import endurance_env

from . import (
    agentbrief,
    control,
    handoff,
    holder,
    keepwarm,
    park,
    procstop,
    qw_schema,
    roster,
    seal,
    supervise,
    switch,
    switchfacts,
    switchplan,
)

SEG_CACHE_TTL = 10.0   # 秒；DES §6.5
SEG_TIMEOUT = 0.15     # 秒；DES §6.5（statusLine 不得因本檔變慢）
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _guard(fn: Callable[[], object], default: object) -> object:
    try:
        return fn()
    except Exception:  # noqa: BLE001 — 唯讀診斷：量不到落回保守值，不拋
        return default


def _transcript(payload: Mapping, sid: str) -> Path | None:
    raw = payload.get("transcript_path")
    if isinstance(raw, str) and raw.strip():
        return Path(raw)
    return roster._main_transcript(roster._projects(None), sid)


def _agent_facts(payload: Mapping, sid: str, env: Mapping) -> tuple[int, int, list]:
    """`(running, quiet, cut)`；running 優先取 payload 的 `background_tasks`（同
    `seal.agents_running`）。被切清單的判準單一家＝`agentbrief.cut_kind`（`usage_limit`／`stopped`／
    `residue`；W4）；被切的代理不再算 running／quiet（末筆是額度切斷訊息的代理，名冊可能仍因最後
    記錄很新而判 running）。"""
    projects = roster._payload_projects(dict(payload))
    snap = roster.snapshot(sid, projects_dir=projects, env=env, full=False)["agents"]
    tasks = roster._tasks(dict(payload))
    cut = agentbrief.cut_list(snap, sid, _transcript(payload, sid), projects)
    cut_ids = {c["id"] for c in cut}
    live = [a for a in snap if a["id"] not in cut_ids]
    running = (sum(1 for t in tasks if t.get("type") == "subagent"
                   and str(t.get("status") or "running") == "running")
               if tasks is not None else sum(1 for a in live if a["state"] == "running"))
    quiet = sum(1 for a in live if a["state"] == "quiet")
    return running, quiet, cut


def _supervision(payload: Mapping, sid: str, now: float) -> tuple[str, str | None, int | None,
                                                                    int | None, dict | None]:
    cred = supervise.credential(dict(payload), sid, now)
    beat = _guard(lambda: supervise.read_heartbeat(sid), None)
    beat = beat if isinstance(beat, dict) else None
    pid = beat.get("pid") if beat else None
    stamp = procstop.parse_iso(beat.get("heartbeat_at")) if beat else None
    age = int(now - stamp) if stamp is not None else None
    source = None if cred == supervise.NONE else (
        "payload" if roster._tasks(dict(payload)) is not None else "heartbeat")
    return cred, source, pid if isinstance(pid, int) else None, age, beat


def _beat_fresh(beat: dict, now: float) -> bool:
    stamp = procstop.parse_iso(beat.get("heartbeat_at"))
    return stamp is not None and now - stamp <= supervise.HEARTBEAT_FRESH_SECONDS


def _next_wake(sid: str, beat: dict | None, marker: dict | None, now: float) -> tuple[
        str | None, str | None]:
    """三個載具各自的「下次叫醒」取最早者：保溫錨（holder 列，行程活著才算）、watch 心跳的保溫點
    （心跳新鮮且 pid 活著）、park 標記主載具（armed）。都沒有 ⇒ `(None, None)`。"""
    found: list[tuple[float, str]] = []
    row = _guard(lambda: holder.read(sid), None)
    wake = _guard(lambda: qw_schema.holder_wake(row), None)
    if wake is not None and wake.wake_at is not None and _guard(
            lambda: holder.is_live(row), False):
        found.append((wake.wake_at, "keepwarm"))
    if beat and _guard(lambda: _beat_fresh(beat, now) and supervise.pid_alive(
            beat.get("pid")), False):
        stamp = qw_schema.parse_epoch(beat.get("keepwarm_at"))
        if stamp is not None:
            found.append((stamp, "watch"))
    if isinstance(marker, dict) and marker.get("status") == "armed":
        primary = qw_schema.marker_primary(marker).wake_at
        if primary is not None:
            found.append((primary, "park"))
    if not found:
        return None, None
    stamp, carrier = min(found)
    return qw_schema.iso(stamp), carrier


def control_state(payload: Mapping | None = None, sid: str | None = None,
                  env: Mapping | None = None, now: float | None = None) -> control.ControlState:
    """本 session 的控制態（DES §3.4 全欄位）。`pending_switch` 由 W5 的 `switchfacts.pending_state`
    供應（惰性建立）；`wall` 由 QW 接上，此處恆為 `False`（誠實：沒有來源就不猜）。"""
    payload = payload if isinstance(payload, Mapping) else {}
    env = os.environ if env is None else env
    at = time.time() if now is None else now
    sid = sid or roster._payload_sid(dict(payload))
    transcript = _guard(lambda: _transcript(payload, sid), None)
    running, quiet, cut = _guard(lambda: _agent_facts(payload, sid, env), (0, 0, []))  # type: ignore[misc]
    cred, source, pid, age, beat = _guard(  # type: ignore[misc]
        lambda: _supervision(payload, sid, at), (supervise.NONE, None, None, None, None))
    marker = _guard(lambda: park.read_marker(sid), None)
    wake, carrier = _guard(lambda: _next_wake(sid, beat, marker, at), (None, None))  # type: ignore[misc]
    pkg = _guard(lambda: seal.latest_package(sid, env), None)
    sealed = (_guard(lambda: seal.effective(pkg["path"], transcript), control.SEAL_UNREADABLE)
              if isinstance(pkg, dict) else control.SEAL_NONE)
    handed = _guard(lambda: seal.handed_over(sid, env), None)
    live = _guard(lambda: [r for r in handoff.list_handoffs(env=env)
                           if r["state"] == "live" and r["sid"] != str(sid)], [])
    park_row = ({"status": marker.get("status"), "primary": wake if carrier == "park" else None}
                if isinstance(marker, dict) else None)
    pending = switchfacts.pending_state(  # W5：惰性建立＋有效性（DES §7.4 兩個呼叫點之一）
        str(sid), transcript, running + quiet, env, datetime.fromtimestamp(at).astimezone())
    return control.classify(control.Facts(
        sid=str(sid), agents_running=running, agents_quiet=quiet, agents_cut=tuple(cut),
        supervision=cred, supervision_source=source, supervision_pid=pid, supervision_hb_age=age,
        next_wake=wake, next_wake_carrier=carrier, sealed=str(sealed),
        handed_over=str(handed) if handed else None, park=park_row, pending_switch=pending,
        unacked_pkg=str(live[-1]["path"]) if live else None))  # type: ignore[index]


# ───────────────────────────────────────────────────────── 換手決策（DES §7；REQ-CTL-22、30）
def plan(payload: Mapping | None = None, sid: str | None = None, env: Mapping | None = None,
         now: datetime | None = None, S: Mapping | None = None, trace: bool = True):
    """組出 `switchplan.Inputs`（全部取自既有真相源）並 `decide`；回 `(Inputs, Decision)`。
    在飛代理＝running＋quiet（都還沒交卷）；`ensure_pending` 經 `control_state` 惰性建立；`trace`
    為真時落 `switch_plan` 痕跡（非 STAY 與每 session 首次 STAY 理由）。"""
    payload = payload if isinstance(payload, Mapping) else {}
    env = os.environ if env is None else env
    now = (now or datetime.now()).astimezone()
    state = control_state(payload, sid, env, now.timestamp())
    sid = state.sid
    transcript = _guard(lambda: _transcript(payload, sid), None)
    ctx = switchfacts.ctx_of(transcript)
    tasks = roster._tasks(dict(payload))
    busy = state.agents_running + state.agents_quiet > 0 or any(
        str(t.get("status") or "running") == "running" for t in (tasks or []))
    pending = state.pending_switch
    inputs = switchplan.Inputs(
        ctx=ctx, hard=switch.threshold(switch.HARD_CTX_KEY, env)[0],
        compactions=switchfacts.compactions(transcript) if transcript else 0,
        r2=switch.threshold(switch.R2_KEY, env)[0], cache=switchfacts.cache_of(transcript, now),
        account_changed=switchfacts.account_changed(sid, now, S),
        quota=switchfacts.quota_facts(sid, transcript, env, now, S),
        agents=state.agents_running + state.agents_quiet, supervision=state.supervision,
        mode=switch.switch_mode(env), unattended=bool(env.get("AUTOSDD_UNATTENDED")),
        since_takeover_min=switchfacts.takeover_min(sid, env, now),
        sealed=control.sealed_raw(state.sealed), handed_over=bool(state.handed_over),
        pending_age_min=switchplan.age_min(pending, now),
        keepwarm_ok=not busy and not _guard(lambda: keepwarm.skip_reason(sid, env, ctx=ctx), "x"),
        env=env)
    decision = switchplan.decide(inputs)
    if trace:
        switchplan.trace_plan(sid, decision)
    return inputs, decision


# ───────────────────────────────────────────────────────── statusLine 區段（DES §6.5）
def _cache_file(sid: str) -> Path:
    return endurance_env.trace_dir_peek()[0] / "control" / f"{sid}.seg"


def _cache_read(sid: str, at: float, ttl: float) -> str | None:
    try:
        row = json.loads(_cache_file(sid).read_text(encoding="utf-8"))
        fresh = 0 <= at - float(row["at"]) <= ttl
        return str(row["text"]) if fresh and isinstance(row.get("text"), str) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _cache_write(sid: str, at: float, text: str) -> None:
    try:
        target = endurance_env.trace_dir() / "control" / f"{sid}.seg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"at": at, "text": text}), encoding="utf-8", newline="\n")
    except OSError:
        pass  # 快取只是優化，寫不進去不影響區段本身


def segment(sid: object, transcript_path: object = None, *, now: float | None = None,
            compute: Callable[[str, Mapping], str] | None = None, timeout: float = SEG_TIMEOUT,
            ttl: float = SEG_CACHE_TTL) -> str:
    """statusLine 的 `ctl: …` 區段；無內容、sid 不合、逾時、任何例外 ⇒ `""`（fail-open）。
    `transcript_path` 缺 ⇒ 退化為依 sid 找主逐字稿，不報錯。`compute` 是測試注入縫。"""
    try:
        if not isinstance(sid, str) or not _SID_RE.match(sid.strip()):
            return ""
        sid, at = sid.strip(), time.time() if now is None else now
        hit = _cache_read(sid, at, ttl)
        if hit is not None:
            return hit
        payload: dict = {"session_id": sid}
        if isinstance(transcript_path, str) and transcript_path.strip():
            payload["transcript_path"] = transcript_path
        box: list[str] = []

        def work() -> None:
            try:
                box.append(compute(sid, payload) if compute is not None else
                           control.segment_text(control_state(payload, sid, now=at)))
            except Exception:  # noqa: BLE001 — 區段壞了只是不顯示
                pass

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        worker.join(timeout)
        if not box:
            return ""
        _cache_write(sid, at, box[0])
        return box[0]
    except Exception:  # noqa: BLE001 — statusLine 永不可因本檔而空白／報錯
        return ""
