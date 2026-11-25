"""`sessionctl status` 的控制行與 `--json`（DES §6.3；REQ-CTL-15）。

入口 `tools/sessionctl.py` 只呼叫本檔（薄殼無判準）：名冊之前先印 `control:` 一行；`--json` 帶
`control` 物件與名冊快照。sid 取 `--session`，缺席取 `CLAUDE_CODE_SESSION_ID`；兩者皆無 ⇒ 明說無法
判斷，不猜。憑證值由 `controlfacts` 向行程表／心跳檔／排程器取，不取自述。
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from collections.abc import Mapping, Sequence

from . import control, controlfacts, procstop, roster


def _sid_of(args: Sequence[str], env: Mapping) -> str:
    for i, arg in enumerate(args[:-1]):
        if arg == "--session" and args[i + 1].strip():
            return args[i + 1].strip()
    return str(env.get("CLAUDE_CODE_SESSION_ID", "")).strip()


def control_text(args: Sequence[str] = (), env: Mapping | None = None) -> str:
    """名冊之前的 `control:` 一行（含換行）；量不到 sid／讀取失敗也印一行說明，不拋。"""
    env = os.environ if env is None else env
    sid = _sid_of(args, env)
    if not sid:
        return "control: 無法判斷（缺 CLAUDE_CODE_SESSION_ID，也沒給 --session）\n"
    try:
        return control.status_line(controlfacts.control_state({}, sid, env)) + "\n"
    except Exception as exc:  # noqa: BLE001 — status 是唯讀診斷
        return f"control: 量不到（{type(exc).__name__}）\n"


_UNMEASURED = "量不到"


def _fmt(value) -> str:
    return _UNMEASURED if value is None else str(value)


def plan_render(inputs, decision) -> str:
    """`switch-plan` 的人讀輸出：Inputs、Decision、reason、carrier、credential（量不到標明）。"""
    q = inputs.quota
    rows = [f"Inputs: ctx={_fmt(inputs.ctx)} hard={_fmt(inputs.hard)} "
            f"compactions={inputs.compactions}/r2={_fmt(inputs.r2)} cache={inputs.cache} "
            f"account_changed={inputs.account_changed} agents={inputs.agents} "
            f"supervision={inputs.supervision} sealed={inputs.sealed} "
            f"handed_over={inputs.handed_over} mode={inputs.mode} unattended={inputs.unattended} "
            f"since_takeover_min={_fmt(inputs.since_takeover_min)} "
            f"pending_age_min={_fmt(inputs.pending_age_min)} keepwarm_ok={inputs.keepwarm_ok}",
            f"Quota: action={_fmt(q.action)} win={_fmt(q.win)} wk={_fmt(q.wk)} vid={_fmt(q.vid)} "
            f"credential={q.credential} "
            f"wait_min={_fmt(q.wait_min)} target_axis={q.target_axis}",
            f"Decision: {decision.action}", f"reason: {decision.reason}",
            f"carrier: {_fmt(decision.carrier)}", f"credential: {_fmt(decision.credential)}",
            f"flags: keepwarm={decision.flags.keepwarm} prefer_fresh={decision.flags.prefer_fresh}"]
    if decision.target:
        rows.append(f"target: {decision.target}")
    return "\n".join(rows) + f"\nSWITCH_PLAN={decision.action} reason={decision.reason}\n"


def switch_plan_cli(args: Sequence[str], env: Mapping | None = None) -> int:
    """`sessionctl switch-plan [--sid S] [--json]`：唯讀（惟 `ensure_pending` 惰性建立標記，
    DES §7.4）、零 token；rc 0（量不到的輸入標「量不到」）。sid 缺席 ⇒ rc 2 並明說。"""
    env = os.environ if env is None else env
    sid = next((args[i + 1] for i, a in enumerate(args[:-1]) if a == "--sid"), "") \
        or str(env.get("CLAUDE_CODE_SESSION_ID", "")).strip()
    if not sid:
        sys.stderr.write("switch-plan：缺 --sid 且 CLAUDE_CODE_SESSION_ID 未設 ⇒ 無法判斷\n")
        return 2
    inputs, decision = controlfacts.plan({}, sid, env)
    if "--json" in args:
        row = dataclasses.asdict(inputs)
        row.pop("env", None)
        sys.stdout.write(json.dumps({"inputs": row, "decision": dataclasses.asdict(decision)},
                                    ensure_ascii=False, default=str) + "\n")
    else:
        sys.stdout.write(plan_render(inputs, decision))
    return 0


def json_or_none(args: Sequence[str], env: Mapping | None = None) -> int | None:
    """帶 `--json` ⇒ 印 `{"control": {...}, ...名冊快照}` 並回 rc 0；沒帶 ⇒ `None`（走文字）。"""
    if "--json" not in args:
        return None
    env = os.environ if env is None else env
    sid = _sid_of(args, env)
    session = next((args[i + 1] for i, a in enumerate(args[:-1]) if a == "--session"), None)
    snap = roster.snapshot(session, runner=procstop.default_runner,
                           all_projects="--all-projects" in args)
    try:
        state = dataclasses.asdict(controlfacts.control_state({}, sid, env)) if sid else None
    except Exception:  # noqa: BLE001 — 量不到寫 null，不猜
        state = None
    sys.stdout.write(json.dumps({"control": state, **snap}, ensure_ascii=False, default=str)
                     + "\n")
    return 0
