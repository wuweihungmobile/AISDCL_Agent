"""`handoff --ack` 成功後的「封存後事件」摘要（WP-SW D-SW-5／REQ-CTL-53；DES §24.5）。

立案（暴露證據）：交接包封存之後發生的事（keepwarm 主載具被殺、帳號切換、舊哨兵崩潰）新主控只能手翻痕跡；
包封存於 11-26 23:47:36 後的事件逐字稿與痕跡都有，卻沒有任何入口一次交代。本葉唯讀、零 token、預算
`ACK_SUMMARY_BUDGET_S`（2 秒）；任一項量不到寫「量不到：原因」；內部任何例外只回一行警告字串，ack 的 rc 由呼叫端
保持不變。內容四項：①owner 在封存戳之後的事件列（前綴白名單、升冪、至多 40 列）②owner 舊哨兵排程現況（取自
`sentgc.job_table` 同一次列舉，空值如實寫空）③舊視窗行程是否還在（驗身分，驗不到寫量不到）④本次 ack 撤銷 armed
park 標記的事實。不寫檔、不改任何狀態。
"""  # noqa: E501
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

ACK_SUMMARY_BUDGET_S = 2.0
ACK_SUMMARY_MAX_ROWS = 40
_PREFIXES = ("park_", "keepwarm_", "watch_", "account_switch", "park_early_", "sentinel_", "handoff_")  # noqa: E501


def _epoch(raw) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).strip()).timestamp()
    except ValueError:
        return None


def _sealed_at(pkg: Path) -> float | None:
    try:
        return _epoch(Path(pkg).with_suffix(".sealed").read_text(encoding="utf-8").strip())
    except OSError:
        return None


def _events(owner: str, since: float | None, deadline: float) -> tuple[list[dict], str]:
    import endurance_env  # noqa: PLC0415

    path = endurance_env.trace_dir_peek()[0] / "autosdd_session_switch.jsonl"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [], f"痕跡檔讀不到（{type(exc).__name__}）"
    if since is None:
        return [], "封存戳量不到（沒有 .sealed 或戳壞）"
    rows = []
    for line in lines:
        if time.monotonic() > deadline:
            return rows, "逾預算，已截斷"
        try:
            row = json.loads(line)
        except ValueError:
            continue
        at = _epoch(row.get("at")) if isinstance(row, dict) else None
        if (at is not None and at > since and str(row.get("event", "")).startswith(_PREFIXES)
                and row.get("sid") == owner):
            rows.append(row)
    return sorted(rows, key=lambda r: _epoch(r["at"]) or 0.0), ""


def _brief(row: dict) -> str:
    keep = {k: v for k, v in row.items() if k not in ("event", "at", "sid", "tb")}
    text = " ".join(f"{k}={str(v)[:60]}" for k, v in list(keep.items())[:6])
    local = datetime.fromisoformat(row["at"]).astimezone().strftime("%m-%d %H:%M:%S")
    return f"  {local} {row['event']} {text}".rstrip()


def _window(owner: str, proc_fn) -> str:
    try:
        state, detail = (proc_fn or _default_proc)(owner)
    except Exception as exc:  # noqa: BLE001
        return f"量不到：{type(exc).__name__}"
    return {"alive": f"仍在（pid {detail}，身分已驗）", "dead": "已不在（行程表無此 session 視窗）"}.get(  # noqa: E501
        state, f"量不到：{detail}")


def _default_proc(owner: str) -> tuple[str, object]:
    from . import procstop, roster  # noqa: PLC0415

    snap = roster.snapshot(None, runner=procstop.default_runner, full=False, all_projects=True)
    for win in snap["windows"]:
        if win.get("sid") == owner:
            return "alive", win["pid"]
    return "dead", None


def summary(pkg, acker_sid: str, env=None, *, table=None, proc_fn=None, now=None) -> str:
    """回摘要全文（含標題行）；`table`＝`sentgc.job_table` 同一次列舉結果（`None`＝量不到）。"""
    from . import handoff  # noqa: PLC0415

    start = time.monotonic()
    deadline = start + ACK_SUMMARY_BUDGET_S
    owner = handoff._sid_of(Path(pkg)) or ""  # noqa: SLF001
    out = [f"── 封存後事件摘要（owner {owner[:8] or '?'}；唯讀、零 token）──"]
    rows, why = _events(owner, _sealed_at(Path(pkg)), deadline)
    if why and not rows:
        out.append(f"① 事件：量不到：{why}")
    else:
        shown = rows[:ACK_SUMMARY_MAX_ROWS]
        out.append(f"① 封存戳之後的事件（{len(rows)} 列）：" + ("（無）" if not rows else ""))
        out += [_brief(r) for r in shown]
        if len(rows) > len(shown):
            out.append(f"  …已截斷 {len(rows) - len(shown)} 列")
        if why:
            out.append(f"  （{why}）")
    mine = [r for r in (table or []) if r.get("sid") == owner]
    if table is None:
        out.append("② 舊哨兵排程：量不到：排程器狀態列舉回 None")
    elif not mine:
        out.append(f"② 舊哨兵排程：（排程器無 AutoSDD_Sentinel_{owner} 工作）")
    for r in mine:
        out.append(f"② 舊哨兵排程 {r['name']}：State={r.get('state')}、LastTaskResult={r.get('last_result')}、"  # noqa: E501
                   f"LastRunTime={r.get('last_run')}、NextRunTime={r.get('next_run')}")
    out.append(f"③ 舊視窗行程：{_window(owner, proc_fn)}")
    cancelled = [r for r in rows if r.get("event") == "park_acked_cancel" and r.get("acker") == acker_sid]  # noqa: E501
    out.append("④ 本次 ack 撤銷了 owner 的 armed park 標記（park_acked_cancel）" if cancelled
               else "④ 本次 ack 未撤銷 park 標記")
    return "\n".join(out)
