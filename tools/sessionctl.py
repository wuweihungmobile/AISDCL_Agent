"""sessionctl 命令列入口（薄殼：只分派，判準全在 `lib/sessionctl/`；ADR-XPLAT-004 §2.13）。

用法：python tools/sessionctl.py <子指令> [旗標]
  子指令：handoff|status|stop|advice|rush|park|watch|keepwarm|runlong|waitfor|oldwin
  watch [--sid] [--stall-min] [--wall-min] [--ctx-max] [--poll-sec]
      背景代理監督（lib/sessionctl/watch；以 run_in_background 掛著，結束＝叫醒主控）
  keepwarm [--sid] [--min] [--poll-sec]
      主控快取保溫（lib/sessionctl/keepwarm；閒置到「最後一筆記錄＋45 分」才結束＝叫醒主控）
  runlong --out <檔> -- <argv…>｜waitfor --done <檔>.done [--max-sec]
      子代理長等待（lib/sessionctl/longwait；runlong 背景跑、waitfor 每段 <5 分鐘前景回來看）
  oldwin --retry <舊 sid> --pkg <包> [--new-sid --job --trace-dir --quiet]｜--sweep｜--status
      舊視窗有條件自動關閉的重試／回收（lib/sessionctl/oldwin_sched；判準 oldwin、park 路
      oldwin_park）
  park [旗標]  額度自願停工的續航（lib/sessionctl/park_cli）
  handoff --build｜--finalize <檔>｜--ack <檔>｜--spawn <檔>｜--list
      交接包（`handoff.cli`）
  status [--session] [--all-projects] [--json]  控制行＋名冊與掌控面（唯讀；預設只列本 repo）
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
    import importlib  # noqa: PLC0415

    import lib.sessionctl  # noqa: F401,PLC0415 — 副作用：把 tools/lib 放進 sys.path

    # 排程 job 的環境不帶過邊界：居所與行為開關隨 argv 的 `--job-env` 轉送，入口最先套用
    # （值不合法 rc 2、沙盒居所已刪 rc 9；遇第一個 `--` 即停，`runlong -- <argv…>` 的旗標不被吃）
    args = importlib.import_module("endurance_env").apply_job_env_or_exit(
        list(sys.argv[1:] if argv is None else argv))
    verb, rest = (args[0], args[1:]) if args else ("", [])
    if verb == "handoff":
        from lib.sessionctl import handoff

        return handoff.cli(rest)
    if verb in ("status", "stop"):
        from lib.sessionctl import roster

        if verb == "status":  # W3：名冊之前先印 `control:` 一行；`--json` 另走（DES §6.3）
            # 控制行是輔助資訊：算不出來就降級一行、名冊照常
            # （status 不因它中斷；同 statusLine 的 fail-open 紀律）
            try:
                from lib.sessionctl import statuscmd

                if (json_rc := statuscmd.json_or_none(args[1:])) is not None:
                    return json_rc
                sys.stdout.write(statuscmd.control_text(args[1:]))
            except Exception as exc:  # noqa: BLE001 — 見上；降級行帶例外類名，不靜默
                if "--json" in args[1:]:
                    sys.stdout.write(f'{{"control": null, "error": "{type(exc).__name__}"}}\n')
                    return 1
                sys.stdout.write(f"control: ?（量不到：{type(exc).__name__}）\n")
        rc = roster.cli(args)
        if verb == "status" and rc == 0:  # R3 WP-4B FR-W9：監督一行（依心跳檔）
            from lib.sessionctl import oldwin_sched, rv_orphans, supervise

            sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
            sys.stdout.write((supervise.status_line(sid) if sid
                              else "監督：無法判斷（缺 CLAUDE_CODE_SESSION_ID）") + "\n")
            sys.stdout.write(oldwin_sched.status_text())  # R217：舊窗重試排程與「只提醒」列
            sys.stdout.write(rv_orphans.status_line() + "\n")  # 真機驗證租約帳孤兒（只讀）
        return rc
    if verb == "oldwin":  # R217 §7.1：舊視窗有條件自動關閉的重試／回收入口
        from lib.sessionctl import oldwin_sched

        return oldwin_sched.cli(rest)
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
    if verb == "keepwarm":  # R216：主控快取保溫（阻塞到截止才結束＝叫醒主控，鐵律六的事件源）
        from lib.sessionctl import keepwarm

        return keepwarm.cli(rest)
    if verb in ("runlong", "waitfor"):  # R216 WP-D：子代理長等待（背景跑＋每段 <5 分鐘前景回來看）
        from lib.sessionctl import longwait

        return longwait.cli_runlong(rest) if verb == "runlong" else longwait.cli_waitfor(rest)
    sys.stderr.write("sessionctl: 用法錯誤：子指令須為 "
                     "handoff／status／stop／advice／rush／park／watch／keepwarm／runlong／waitfor／"
                     "oldwin\n")
    return _USAGE_RC


if __name__ == "__main__":
    sys.exit(main())
