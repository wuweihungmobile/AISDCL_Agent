#!/usr/bin/env python3
"""把根 CLAUDE.md 的〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉變成可執行的東西。

WHY
---
那一節寫得很完整——三段式水位、「可重啟點」四條件、任務書必含四項、重啟指令、
反「事後諸葛」取證規則——但它**全部是散文**，零機械物。而它自己記載的立案事故正是
「散文擋不住」的實例：R59 撞 Token 99% 時用 `CronCreate` 排了 45 分鐘後續跑並向使用者
宣稱「會自動繼續」，時間到完全沒觸發（`CronList` 對它的標記就是 `[session-only]`），
整段工作停擺而使用者以為在推進。

本檔提供三件那一節要求、但目前只能靠人記得的事：
  · `--check`：把「現在幾 %」變成一個可以現查的數字（水位判定與
    `.claude/hooks/context_budget_guard.py` **共用同一份實作**，見下方 import 的 WHY）；
  · 產出「可重啟點任務書」骨架，四項欄位齊備、無法自動得知的部分留 `TODO:` 佔位；
  · `--print-schtasks-command`：**只印不執行**的離線排程指令 ＋ 它的取證指令。

🔴 本檔不建立任何排程、也不宣稱建立過
--------------------------------------
根 CLAUDE.md〈反「事後諸葛」取證規則〉逐字要求：宣稱「已排程／會自動繼續」的**同一則
輸出**必須附排程器自己回報的下次執行時間實測輸出，貼不出來就不准宣稱。註冊 S4U 任務
需要提權，session 內做不到也驗不了 ⇒ 本檔的處置是**只印指令**，並在同一段輸出裡附上
取證指令。這不是功能缺漏，是那條規則的直接落地。

🔴 任務書裡的「已驗證什麼」一律是 `TODO:`，本檔不代填
------------------------------------------------------
它沒有辦法知道你驗過什麼。自動填一句「已通過」就是憑空製造一則沒有 tool_result 支撐的
宣稱——那正是本 repo 反覆記載的頭號缺陷形態。骨架的價值在於「欄位在那裡、空著很刺眼」，
不在於幫人省下寫字。

用法
----
    python tools/session_resume_planner.py --check              # 只印水位，不寫檔
    python tools/session_resume_planner.py                      # 產任務書骨架
    python tools/session_resume_planner.py --out <path>
    python tools/session_resume_planner.py --session-id <id>
    python tools/session_resume_planner.py --transcript <a.jsonl>
    python tools/session_resume_planner.py --print-schtasks-command

測試：tools/tests/test_context_budget_guard.py（與被它共用的 hook 同一支鎖）
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

# 🔴 依賴方向刻意是「tools → .claude/hooks」而不是反過來（本 repo 對「同一份知識住
# 兩個家」有反覆的判例，其中一次就長在專門防它的那一節自己身上）：那支 hook 由
# `runpy.run_path` 起，`sys.path` 既不含 `.claude/hooks/` 也不含 `tools/` ⇒ 它**不能**
# import 任何東西，只能是被 import 的那一方。於是「怎麼算水位／怎麼判 window」的唯一
# 實作住在 hook 裡，本檔是它的消費者。反過來寫的話那份判準會有兩個家，而其中一個
# （hook 那個）在結構上無法委派出去。
# 同理 `project_transcript_dir`（逐字稿目錄的 slug 推導）已有唯一實作在
# `tools/probe/audit_session.py`，本檔取用而不抄一份。
# （下面兩段被 ruff 的 isort 判為不同 section：`.claude/hooks` 不在其 src 內 ⇒ 視為
#   第三方；`tools/` 內的則是 first-party。分段是它要的形狀，不是隨手排的。）
import context_budget_guard as guard  # noqa: E402  # 水位判定唯一實作（見上方 WHY）

import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端印中文／emoji 防崩潰
from probe.audit_session import project_transcript_dir  # noqa: E402

#: 任務書預設落點＝系統暫存。刻意不落在 repo 內：`tools/tests/test_platform_neutral_paths.py`
#: 有一道「repo 內不得有可寫暫存目錄」的判準，而任務書天生是 untracked 的機器本地產物。
PLAN_PREFIX = guard.PLAN_PREFIX

#: `--print-schtasks-command` 的四項補跑保護。**建構 cmdlet 的參數名與 Settings 物件的
#: 屬性名不同且極性相反**（DEF-101-249，真機實測）：物件屬性叫 DisallowStartIfOnBatteries／
#: StopIfGoingOnBatteries，而 New-ScheduledTaskSettingsSet 的參數叫 -AllowStartIfOnBatteries／
#: -DontStopIfGoingOnBatteries。抄錯只在真機非 -WhatIf 呼叫時才會拋 NamedParameterNotFound，
#: 語法解析與 CI 一律看不到 ⇒ 這裡逐字沿用 tools/install_windows_nightly.ps1 的既有寫法。
_SCHTASKS_SETTINGS = (
    "New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun "
    "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries"
)


def resolve_transcript(
    session_id: str | None = None,
    transcript: str | None = None,
    repo_root: Path | None = None,
) -> Path | None:
    """定位本 session 的逐字稿；`None`＝找不到（呼叫端負責 fail-loud）。

    優先序：`--transcript` 顯式路徑 → `--session-id` 對應的 `<id>.jsonl` →
    專案目錄下**最後修改**的那一支（根 CLAUDE.md 對「當前 session」的既有判準）。
    """
    if transcript:
        candidate = Path(transcript)
        return candidate if candidate.is_file() else None
    base = project_transcript_dir(repo_root or _REPO_ROOT)
    if not base.is_dir():
        return None
    if session_id:
        candidate = base / f"{session_id}.jsonl"
        return candidate if candidate.is_file() else None
    found = [p for p in base.glob("*.jsonl") if p.is_file()]
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def measure(transcript: Path) -> dict:
    """水位量測（純資料）。判定一律走 hook 的實作，本檔不重寫一份判準。"""
    used, peak = guard.scan_usage(transcript)
    window, source = guard.resolve_window(peak, os.environ.get(guard.WINDOW_ENV))
    return {
        "session_id": guard.session_id_of(transcript),
        "transcript": str(transcript),
        "used": used,
        "peak_used": peak,
        "window": window,
        "window_source": source,
        "ratio": (used / window) if (used is not None and window > 0) else None,
        "tier": guard.tier_of(used, window) if used is not None else None,
    }


def check_report(data: dict) -> str:
    """`--check` 的輸出。量不到時**明說量不到**，不印一個看起來像 0% 的數字。"""
    if data["used"] is None:
        return (
            f"❌ {data['transcript']}\n"
            "   掃不到任何帶 message.usage 的 assistant 記錄 —— 「量不到」與「量到零」"
            "必須分得開，故不印百分比。逐字稿剛建立、或欄位格式已變更都會走到這裡。\n"
        )
    tier = {None: "低於 75%", guard.TIER_WARN: "≥75%（建議 compact）",
            guard.TIER_HARD: "≥90%（停止開新戰場）"}[data["tier"]]
    return (
        f"session   {data['session_id']}\n"
        f"逐字稿    {data['transcript']}\n"
        f"used      {data['used']:,}"
        f"（input + cache_creation + cache_read；output_tokens 不計）\n"
        f"peak      {data['peak_used']:,}（本 session 歷來最大，window 下界推論的輸入）\n"
        f"window    {data['window']:,}〔{data['window_source']}〕\n"
        f"水位      {data['ratio']:.1%}  → {tier}\n"
        f"重啟指令  claude -r {data['session_id']}\n"
    )


def schtasks_command(session_id: str, plan_path: str,
                     task_name: str = "AutoSDD_SessionResume") -> str:
    """離線排程指令 ＋ 取證指令。**本函式只組字串，不執行任何東西。**"""
    return (
        "# 🔴 以下指令本工具**沒有執行**，也沒有建立任何排程。註冊 S4U 任務需提權，\n"
        "#    session 內做不到也驗不了（根 CLAUDE.md 已載明此路無法從 session 內部試跑）。\n"
        "# 🔴 執行完**必須**貼出最後那道取證指令的輸出才准宣稱「已排程」——\n"
        "#    「我下了指令」不等於「它真的排進去了」（反『事後諸葛』取證規則）。\n"
        f"$claude  = (Get-Command claude).Source\n"
        f"$action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "
        f"('-NoProfile -ExecutionPolicy Bypass -Command \"& $claude -p -r "
        f"{session_id} (Get-Content -Raw -Encoding utf8 ''{plan_path}'')\"')\n"
        "$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddHours(5)   "
        "# ← 改成 CLI 印的 reset 時間\n"
        f"$settings = {_SCHTASKS_SETTINGS}\n"
        f"Register-ScheduledTask -TaskName '{task_name}' -Action $action "
        "-Trigger $trigger -Settings $settings\n"
        "\n"
        "# 取證（沒有這行的輸出就不准宣稱已排程；查排程一律用 Get-ScheduledTask，\n"
        "#  schtasks /query 在本機實測會回空＝假陰性）：\n"
        f"Get-ScheduledTask -TaskName '{task_name}' | Get-ScheduledTaskInfo | "
        "Format-List TaskName,LastRunTime,LastTaskResult,NextRunTime\n"
    )


def render_plan(data: dict, now: str) -> str:
    """任務書骨架。四項欄位齊備；無法自動得知的一律 `TODO:`，本檔不代填。"""
    used = f"{data['used']:,}" if data["used"] is not None else "（量不到）"
    ratio = f"{data['ratio']:.1%}" if data["ratio"] is not None else "（量不到）"
    return f"""# 可重啟點任務書 — session `{data['session_id']}`

> 由 `tools/session_resume_planner.py` 產生於 {now}。
> 🔴 **這是骨架，不是報告**。帶 `TODO:` 的欄位本工具**無法**自動得知，必須由當事人填。
> 本工具刻意不代填「已驗證」——憑空生出一則沒有 tool_result 支撐的宣稱，正是本 repo
> 反覆記載的頭號缺陷形態（`[[no-fabricated-tool-output]]`）。

## 0. 量測（本工具當場實測，非宣稱）

| 項目 | 值 |
| --- | --- |
| session id | `{data['session_id']}` |
| 逐字稿 | `{data['transcript']}` |
| context used | {used} |
| context window | {data['window']:,}〔{data['window_source']}〕 |
| 水位 | {ratio} |

## 1. 已驗證什麼（附實測數字與 rc）

TODO: 逐條列。每一條都必須附**當回合真跑的輸出 ＋ rc**；貼不出輸出的一律寫「未驗證」，
不要寫「應該會過」。範例格式：`python tools/run_root_unittests.py` → rc=0，Ran N tests。

## 2. 還沒做什麼

TODO: 逐條列，含「為什麼還沒做」（被什麼擋住／等誰）。

## 3. 下一步的確切指令

重啟本 session（唯一不依賴 session 存活的路）：

```powershell
claude -r {data['session_id']}
```

TODO: 重啟後要跑的第一組指令，**寫絕對路徑**（PowerShell 工具的 cwd 會跨呼叫持續，
相對路徑會找錯地方）。

## 4. 禁止事項

- 🔴 重啟後**第一件事是重驗**，不採信本檔任何「已通過」宣稱（對自己上一段也要 zero-trust）。
- 不准 `--no-verify`；不准設 `AUTOCLAUDE_SKIP_HOOKS`；不准設 `SDD_HOOKS_DISABLE`。
- 不准調高任何門檻／棘輪上限來換綠燈。
- Windows 側：不准用 Bash 工具（鐵律一）、不准裸 `cd`（鐵律二）、
  不准在接了管線的指令後讀 `$LASTEXITCODE`。
- 不准宣稱「已排程／會自動繼續」而沒有附排程器回報的 `NextRunTime`。
- TODO: 本輪特有的禁止事項（例如「不要動 X 檔，另一包正在上面作業」）。

## 5. 排程（本工具**沒有**建立任何排程）

要離線續跑就自己跑 `python tools/session_resume_planner.py --print-schtasks-command`
拿指令，執行後貼出取證輸出。`CronCreate` 不是離線排程（`CronList` 標 `[session-only]`）。
"""


def build_parser() -> argparse.ArgumentParser:
    # `allow_abbrev=False`：前綴縮寫會「好心地」把打錯的旗標補全成合法旗標，
    # 那正是 R67-D20 實測到的假綠來源（`--check-snapsho` → `--check-snapshot`）。
    parser = argparse.ArgumentParser(
        prog="session_resume_planner.py", allow_abbrev=False,
        description="可重啟點任務書產生器 ＋ session context 水位現查",
    )
    parser.add_argument("--session-id", help="session id（逐字稿檔名去副檔名）")
    parser.add_argument("--transcript", help="直接指定逐字稿 .jsonl 路徑")
    parser.add_argument("--out", help="任務書落點（預設：系統暫存）")
    parser.add_argument("--check", action="store_true",
                        help="只印當前 context 用量與百分比，不寫檔")
    parser.add_argument("--print-schtasks-command", action="store_true",
                        dest="print_schtasks",
                        help="只印離線排程指令與取證指令，**不執行、不註冊**"
                             "（會一併產生任務書：排程起來的那一跑要吃它）")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    transcript = resolve_transcript(args.session_id, args.transcript)
    if transcript is None:
        print(
            "❌ 找不到逐字稿。依序試過：--transcript / --session-id / "
            f"{project_transcript_dir(_REPO_ROOT)} 下最後修改的 *.jsonl。\n"
            "   fail-loud 是刻意的：定位不到 session 時產出的任務書會綁錯 session id，"
            "而那個 id 正是重啟指令唯一的參數。",
            file=sys.stderr,
        )
        return 1

    data = measure(transcript)

    if args.check:
        print(check_report(data), end="")
        if args.print_schtasks:
            print(
                "ℹ️  --check 不寫檔，故不印 schtasks 指令：那段指令要引用任務書的路徑，"
                "而任務書還沒產生。拿掉 --check 再跑一次。",
                file=sys.stderr,
            )
        return 0

    out = Path(args.out) if args.out else (
        Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{data['session_id']}.md"
    )
    now = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_plan(data, now), encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"❌ 任務書寫檔失敗：{out}（{exc}）", file=sys.stderr)
        return 1

    print(f"✅ 可重啟點任務書骨架已寫到：{out}")
    print("   🔴 帶 TODO: 的欄位本工具不代填——它不知道你驗過什麼。")
    print(f"   重啟指令（可直接複製）：claude -r {data['session_id']}")
    if args.print_schtasks:
        print()
        print(schtasks_command(data["session_id"], str(out)), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
