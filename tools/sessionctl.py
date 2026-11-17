"""sessionctl 命令列入口（薄殼：只分派，判準全在 `lib/sessionctl/`；ADR-XPLAT-004 §2.13）。

用法：python tools/sessionctl.py <handoff|status|stop|advice|rush|park|watch> [旗標]
  watch [--sid] [--stall-min] [--wall-min] [--ctx-max] [--poll-sec]
      背景代理監督（lib/sessionctl/watch；以 run_in_background 掛著，結束＝叫醒主控）
  park [旗標]  額度自願停工的續航（lib/sessionctl/park_cli）
  handoff --build｜--finalize <檔>｜--ack <檔>｜--spawn <檔>｜--list
      交接包（`handoff.cli`）
  status                                  名冊與掌控面（`roster.cli`，唯讀）
  stop --window <sid>｜--all-unattended   停無人視窗（`roster.cli`）
  advice [--family fable]                 模型平衡建議（只出聲）
  rush --hours <H> --why "<WHY>"｜--off｜--status   趕工戳記（只關配速床，≤5 小時）
子模組一律在分派時才 import（某一支還沒好，其餘子指令照常）；未知子指令 rc 3。
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作，本檔不另寫

_USAGE_RC = 3


def _advice(argv: list[str]) -> int:
    from lib.sessionctl import modelmix

    family = argv[argv.index("--family") + 1] if "--family" in argv[:-1] else "fable"
    import quota_gate  # noqa: PLC0415 — 與 `--pace` 同一個只讀快取

    now = datetime.now().astimezone()
    print(modelmix.advice_line(quota_gate.read_quota(now).axes, now=now, family=family))
    return 0


def _rush(argv: list[str]) -> int:
    import importlib  # noqa: PLC0415

    import lib.sessionctl  # noqa: F401,PLC0415 — 副作用：把 tools/lib 放進 sys.path

    return importlib.import_module("quota_rush").cli(argv)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    verb, rest = (args[0], args[1:]) if args else ("", [])
    if verb == "handoff":
        from lib.sessionctl import handoff

        return handoff.cli(rest)
    if verb in ("status", "stop"):
        from lib.sessionctl import roster

        rc = roster.cli(args)
        if verb == "status" and rc == 0:  # R3 WP-4B FR-W9：監督一行（依心跳檔）
            from lib.sessionctl import supervise

            sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
            sys.stdout.write((supervise.status_line(sid) if sid
                              else "監督：無法判斷（缺 CLAUDE_CODE_SESSION_ID）") + "\n")
        return rc
    if verb == "advice":
        return _advice(rest)
    if verb == "rush":  # ADR-XPLAT-004 §2.15 D2：趕工戳記（判準與讀寫全在 `lib/quota_rush.py`）
        return _rush(rest)
    if verb == "park":  # ADR-XPLAT-004 §2.17：額度自願停工續航
        from lib.sessionctl import park_cli

        return park_cli.cli(rest)
    if verb == "watch":  # R3 WP-4A：背景代理監督（阻塞到有事發生才結束＝叫醒主控）
        from lib.sessionctl import watch

        return watch.cli(rest)
    sys.stderr.write(
        "sessionctl: 用法錯誤：子指令須為 handoff／status／stop／advice／rush／park／watch\n")
    return _USAGE_RC


if __name__ == "__main__":
    sys.exit(main())
