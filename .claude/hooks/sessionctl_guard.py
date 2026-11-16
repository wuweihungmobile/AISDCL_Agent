#!/usr/bin/env python3
"""sessionctl 守衛（跳板）：Stop 出聲／推回；PreToolUse 續棒成本閘與收斂閘。

判準全在 `tools/lib/sessionctl/`（本檔零判準）：SendMessage 走 `roster.resume_gate`
（續棒看快取冷熱）；Agent／Task／Workflow 走 `converge.converge_verdict`（出聲後上下文達
硬門檻）。Stop：仍有背景代理在跑 ⇒ `{"systemMessage": ...}` rc 0；否則收斂閘成立 ⇒
`{"decision":"block","reason":...}` 推回一次（`stop_hook_active` 為真即放行，判準
`converge.stop_verdict`；其尾端另判 park＝額度停工憑證 `park.stop_verdict`，
逃生口 `AUTOSDD_PARK_GUARD_OFF`）。PreToolUse：rc 2 ＝阻斷（stderr 回饋模型）；解析不到一律放行。
任何例外 rc 0（fail-open，P0）；不 spawn、不 import planner。逃生口：
`AUTOSDD_SESSIONCTL_GUARD_OFF`（刻意不與其他守衛共用）。回歸鎖
`tools/tests/test_sessionctl_hooks.py`；設計＝ADR-XPLAT-004 §2.13.6、§2.14。
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "tools", "lib"))
sys.path.append(os.path.join(_ROOT, "tools"))  # `lib.sessionctl` 套件在 tools/ 之下
try:
    from platform_utils import init_utf8_streams, read_hook_payload  # type: ignore

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}


def _emit(doc: dict) -> None:
    sys.stdout.write(json.dumps(doc, ensure_ascii=True) + "\n")


def main() -> int:
    try:
        if os.environ.get("AUTOSDD_SESSIONCTL_GUARD_OFF"):
            return 0
        payload = read_hook_payload()
        from lib.sessionctl import converge, roster  # noqa: PLC0415 — 真的要判才付 import 成本

        event, tool = payload.get("hook_event_name"), payload.get("tool_name")
        if event == "Stop":
            why = converge.stop_verdict(payload, os.environ)  # 先判推回：背景 shell 不得蓋掉它
            msg = "" if why else roster.stop_message(payload)
            if why:
                _emit({"decision": "block", "reason": why})
            elif msg:
                _emit({"systemMessage": msg})
            return 0
        if event != "PreToolUse":
            return 0
        if tool == "SendMessage":
            rc, text = roster.resume_gate(payload, os.environ)
        elif tool in converge.EXPAND_TOOLS:
            rc, text = converge.converge_verdict(payload, os.environ)
        else:
            return 0
        if rc == 2:
            sys.stderr.write(text)
            return 2
        if text:
            sys.stderr.write(text + "\n")
            _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                          "additionalContext": text}})
        return 0
    except Exception:  # noqa: BLE001 — fail-open（P0：hook 崩潰不得演變成阻斷）
        return 0


if __name__ == "__main__":
    sys.exit(main())
