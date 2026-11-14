#!/usr/bin/env python3
"""sessionctl 守衛（跳板）：Stop 出聲仍在跑的背景代理；PreToolUse／SendMessage 續棒成本閘。

判準全在 `tools/lib/sessionctl/roster.py`（本檔零判準）。Stop：本回合結束仍有背景代理在跑 ⇒
stdout 印 `{"systemMessage": ...}`、rc 0、永不阻斷。PreToolUse（matcher=SendMessage）：目標代理
上下文 ≥ 門檻 ⇒ 互動出聲 rc 0、`AUTOSDD_UNATTENDED` 有設 rc 2 阻斷（stderr 回饋模型）；解析不到
一律放行。任何例外 rc 0（fail-open，P0）；不 spawn、不 import planner。
逃生口：`AUTOSDD_SESSIONCTL_GUARD_OFF`（刻意不與其他守衛共用）。回歸鎖
`tools/tests/test_sessionctl_hooks.py`。設計＝ADR-XPLAT-004 §2.13.6。
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, "tools", "lib"))
sys.path.append(os.path.join(_ROOT, "tools"))  # `lib.sessionctl` 套件在 tools/ 之下
try:
    from platform_utils import init_utf8_streams, read_hook_payload  # type: ignore[import-not-found]

    init_utf8_streams()
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_hook_payload() -> dict:  # type: ignore[misc]
        return {}


def main() -> int:
    try:
        if os.environ.get("AUTOSDD_SESSIONCTL_GUARD_OFF"):
            return 0
        payload = read_hook_payload()
        from lib.sessionctl import roster  # noqa: PLC0415 — 只有真的要判時才付 import 成本

        event = payload.get("hook_event_name")
        if event == "Stop":
            msg = roster.stop_message(payload)
            if msg:
                sys.stdout.write(json.dumps({"systemMessage": msg}, ensure_ascii=True) + "\n")
            return 0
        if event == "PreToolUse" and payload.get("tool_name") == "SendMessage":
            rc, text = roster.resume_gate(payload, os.environ)
            if rc == 2:
                sys.stderr.write(text)
                return 2
            if text:
                sys.stderr.write(text + "\n")
                sys.stdout.write(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "additionalContext": text}},
                    ensure_ascii=True) + "\n")
        return 0
    except Exception:  # noqa: BLE001 — fail-open（P0：hook 崩潰不得演變成阻斷）
        return 0


if __name__ == "__main__":
    sys.exit(main())
