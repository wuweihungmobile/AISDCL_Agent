#!/usr/bin/env python3
"""sessionctl 守衛（跳板）：Stop 出聲／推回；PreToolUse 續棒成本閘與收斂閘。

判準全在 `tools/lib/sessionctl/`（本檔零判準）：SendMessage 走 `roster.resume_gate`
（續棒看快取冷熱）；Agent／Task／Workflow 走 `converge.converge_verdict`（主控上下文達
硬線 850,000，不再要求先出聲；R216）。Stop：仍有背景代理在跑 ⇒
`{"systemMessage": ...}` rc 0；否則收斂閘成立 ⇒
`{"decision":"block","reason":...}` 推回一次（`stop_hook_active` 為真即放行，判準
`converge.stop_verdict`；其尾端另判 park＝額度停工憑證 `park.stop_verdict`，
逃生口 `AUTOSDD_PARK_GUARD_OFF`）。PreToolUse：rc 2 ＝阻斷（stderr 回饋模型）；解析不到一律放行。
PreToolUse／PowerShell、Bash：子代理（payload 有 `agent_id`）的前景呼叫 timeout > 270000 ms ⇒ rc 2，
指路 `sessionctl runlong`／`waitfor`（`longwait.pretool_verdict`；R216 WP-D、設計 §4.5 D13；行內豁免
`# keepwarm-ok: <WHY>`）；主控的 shell 呼叫不判、不付 import 成本。
UserPromptSubmit：呼叫 `forward.hook_output`（冷舊窗的真人提示自動轉送新 session；已交棒舊窗回
說明；R3 WP-5，ADR-XPLAT-004 §2.13）；輸出 block／additionalContext JSON，其餘無輸出。
任何例外 rc 0（fail-open，P0）；不 import planner（轉送的 spawn 在 `forward`／`handoff` 內）。
逃生口：`AUTOSDD_SESSIONCTL_GUARD_OFF`（刻意不與其他守衛共用）。回歸鎖
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
        event, tool = payload.get("hook_event_name"), payload.get("tool_name")
        if event == "UserPromptSubmit":  # 判準全在 forward.py：舊窗冷快取轉送／已交棒告知
            from lib.sessionctl import forward, oldwin  # noqa: PLC0415

            out = forward.hook_output(payload, os.environ)
            if out:
                _emit(out)
            elif note := "\n".join(filter(None, (
                    oldwin.take_unread_notice(str(payload.get("session_id") or "")),
                    oldwin.pending_manual_close(str(payload.get("session_id") or ""))))):
                _emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",  # 舊窗關（§7.1）
                                              "additionalContext": note}, "systemMessage": note})
            return 0
        if event == "PreToolUse" and tool in ("PowerShell", "Bash"):
            # 長前景閘（R216 WP-D）：只判子代理（帶 agent_id）；主控不付 import 成本
            if payload.get("agent_id"):
                from lib.sessionctl import longwait  # noqa: PLC0415

                rc, text = longwait.pretool_verdict(payload, os.environ)
                if rc == 2:
                    sys.stderr.write(text)
                    return 2
            return 0
        from lib.sessionctl import (  # noqa: PLC0415 — 真的要判才付 import 成本
            converge,
            oldwin,
            roster,
        )

        if event == "Stop":
            env = os.environ
            if not payload.get("stop_hook_active"):  # 完成閘讓路：OIR undriven 不叫掛保溫（§4.4）
                try:
                    from lib.openitems import gate  # noqa: PLC0415

                    if gate.keepwarm_yields(str(payload.get("session_id") or "")):
                        env = {**os.environ, "AUTOSDD_KEEPWARM_OFF": "1"}
                except Exception:  # noqa: BLE001 — 讓路壞了不得連累其他 Stop 閘
                    pass
            why = converge.stop_verdict(payload, env)  # 先判推回：背景 shell 不得蓋掉它
            msg = "" if why else roster.stop_message(payload)
            sid = str(payload.get("session_id") or "")
            if not why and (note := "\n".join(filter(None, (
                    oldwin.take_unread_notice(sid), oldwin.pending_manual_close(sid))))):
                # 舊窗關閉出聲（§7.1；notice 出聲一次、讀過即標已讀；放棄／降級後的
                # 「請手動關閉」每回合重提醒、直到舊視窗真的關掉為止——R217 F7，不得無聲）
                msg = f"{msg}\n{note}".strip()
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
