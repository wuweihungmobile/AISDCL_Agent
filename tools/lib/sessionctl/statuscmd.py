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
