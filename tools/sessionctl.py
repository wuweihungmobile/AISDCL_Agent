"""sessionctl 命令列入口（薄殼：只分派，判準全在 `lib/sessionctl/`；ADR-XPLAT-004 §2.13）。

用法：python tools/sessionctl.py <handoff|status|stop|advice> [旗標]
  handoff --build｜--finalize <檔>｜--ack <檔>｜--spawn <檔>｜--list
      交接包（`handoff.cli`）
  status                                  名冊與掌控面（`roster.cli`，唯讀）
  stop --window <sid>｜--all-unattended   停無人視窗（`roster.cli`）
  advice [--family fable]                 模型平衡建議（只出聲）
子模組一律在分派時才 import（某一支還沒好，其餘子指令照常）；未知子指令 rc 3。
"""
from __future__ import annotations

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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    verb, rest = (args[0], args[1:]) if args else ("", [])
    if verb == "handoff":
        from lib.sessionctl import handoff

        return handoff.cli(rest)
    if verb in ("status", "stop"):
        from lib.sessionctl import roster

        return roster.cli(args)
    if verb == "advice":
        return _advice(rest)
    sys.stderr.write("sessionctl: 用法錯誤：子指令須為 handoff／status／stop／advice\n")
    return _USAGE_RC


if __name__ == "__main__":
    sys.exit(main())
