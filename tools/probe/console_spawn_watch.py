#!/usr/bin/env python3
"""**誰生出了 console 行程** — 黑框彈跳的歸因量測器（Windows）。

WHY —— 為什麼要一支常駐在 repo 裡的偵測器，而不是一次性腳本
-------------------------------------------------------------
掌舵者兩度回報「有 cmd 不定時跳出執行」。第一輪的處置是**推論**：逐一檢查我們自己的
spawn 站點有沒有帶 `creationflags`、檢查排程 Action 是不是 `pythonw.exe`、檢查 hook 有沒有
退回 shell form——每一項都查得漂亮，然後結論是「我們這邊看起來很乾淨」。
🔴 那個結論**沒有量測支撐**：它只證明「我們知道的那幾條路是乾淨的」，對「我們不知道的
那條路」結構上失明。而黑框是別人的行程也彈得出來的東西 ⇒ 只有**看著行程被生出來**
才答得了「是誰」。

同一件事會再發生（換一台機器、換一個排程工具、裝一個新 IDE 外掛），所以偵測器留在 repo。

取數管道的選擇（三選一，這裡說明為什麼選這個）
----------------------------------------------
① `__InstanceCreationEvent WITHIN <秒> WHERE TargetInstance ISA 'Win32_Process'` ← **採用**
   · 不需提權（暫時性 WMI 訂閱；需要提權的是**永久**訂閱）。
   · payload 是完整的 `Win32_Process` ⇒ 一次拿到 `CommandLine`＋`ParentProcessId`，
     而「誰生的」正是本量測唯一要回答的問題。
② `Win32_ProcessStartTrace`：ETW 背景、不漏極短命行程，但**沒有 `CommandLine`**，
   而且在多數非提權情境註冊會被拒。拿不到命令列就歸因不了（`cmd.exe` 本身不說話）。
③ 輪詢 `Get-CimInstance Win32_Process` 差分：零風險但**會漏掉比輪詢間隔短的行程**，
   而閃一下就消失的黑框正好就是那一種 ⇒ 用它會系統性地漏掉標的。

🔴 誠實劃界（①的已知盲點，不要把零命中讀成「不存在」）：
  · `WITHIN` 是 WMI 內部的輪詢秒數，比它更短命的行程仍可能漏。預設 0.2 秒已是實務下限，
    再小會讓 WMI 自己吃掉可觀 CPU。
  · 只看得到**本使用者權限看得到的**行程；session 0 的服務類行程（S4U 排程工作即屬此類）
    拿不到命令列時會落進「無法歸因」那一格，不會被硬塞進任何一邊。
  · 量測窗之外發生的事，這支不會知道。所以窗要**涵蓋一次哨兵 tick**（見 `--seconds`）。
  · 🔴 本量測器量的是**行程建立**，不是**視窗可見**（DEF-200-417）：`conhost.exe` 建立事件
    多半是 `CREATE_NO_WINDOW` 下的隱形視窗，Win11 上使用者真的看得到的黑框承載者其實是
    `WindowsTerminal.exe`／`OpenConsole.exe`（真機實測：class `CASCADIA_HOSTING_WINDOW_CLASS`，
    事件序 CREATE→FOREGROUND→SHOW）。「哪一筆建立事件真的變成了一扇可見視窗」量不到；
    那個問題由 `tools/probe/flash_watch.py`（`SetWinEventHook`）回答。

用法
----
    python tools/probe/console_spawn_watch.py --seconds 960 --out %TEMP%\\spawn.jsonl
    python tools/probe/console_spawn_watch.py --report %TEMP%\\spawn.jsonl

回歸鎖：`tools/tests/test_context_budget_guard.py::ConsoleSpawnAttributionTest`
（歸因三分類的紅綠皆合成注入）。**刻意不另開鎖檔**：`tools/tests/` 有逐檔行數淨額棘輪
（`test_adr_xplat001_c1c2_lock._FROZEN_GUARD_LINES`），而「黑框從哪來」與該檔既有的
`ConsoleFreeSpawnTest`（spawn 站點必帶 no-window 旗標）是同一個主題的兩半：
一個問「我們有沒有寫對」，一個問「實際上是誰在彈」。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

#: 無視窗旗標。語意的唯一的家＝`.claude/hooks/context_budget_guard.NO_WINDOW`。本檔複製
#: 同一個表達式（probe 不得 import hook：那條依賴會把 probe 綁進 hook 的相依鏈），
#: 相等由 `tools/tests/test_console_spawn_watch.py` 守著。🔴 這支量測器自己**絕不可以**
#: 成為它要量的那個現象的來源——否則它會量到自己。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

#: 同上，唯一的家＝`context_budget_guard.PS_UTF8_PRELUDE`。本量測器會把命令列（含中文路徑）
#: 印進報表，少了它 PS 5.1 會以主控台 codepage 寫 stdout ⇒ 非 ASCII 命令列在報表裡降解，
#: 而**降解過的命令列仍然非空** ⇒ 歸因判準照樣分類，只是分錯。
PS_UTF8_PRELUDE = ("$OutputEncoding = [Console]::OutputEncoding = "
                   "[Text.UTF8Encoding]::new($false)\n")

#: 只登記這些映像名。全部行程都記會讓一次 15 分鐘的窗長到沒人看得完，而**黑框**這件事
#: 只由 console 子系統的映像產生。`conhost.exe` 一定要在裡面：它是「有沒有配置到一個
#: console」最直接的證據，而它的父行程就是答案。
#: 🔴 `WindowsTerminal.exe`／`OpenConsole.exe`（DEF-200-417 真機實測補）：Win11 上這兩者才是
#: 使用者**真的看得到**的黑框承載者（從無 console 的父行程 spawn `powershell.exe` 且不帶
#: `CREATE_NO_WINDOW` 時，彈出的是 `WindowsTerminal.exe`＋自己的 `PseudoConsoleWindow`，
#: 不是傳統 `conhost.exe`）；反過來，`conhost.exe 0x4` 多半正是 `CREATE_NO_WINDOW` 建出來的
#: **隱形**視窗——把它算進「有黑框」會高估，漏了前兩者則會對真正彈出來的那個失明。
CONSOLE_IMAGES = ("cmd.exe", "conhost.exe", "powershell.exe", "pwsh.exe",
                  "schtasks.exe", "python.exe", "pythonw.exe", "bash.exe",
                  "git.exe", "wsl.exe", "wscript.exe", "cscript.exe",
                  "WindowsTerminal.exe", "OpenConsole.exe")

#: 報表〈可見視窗承載者〉那一行的映像名子集（小寫比對；DEF-200-417）。獨立成常數只為
#: 讓 `report()` 那一行不用把兩個字面值又抄一次、行也不至於破 100 字元上限。
_VISIBLE_CARRIER_IMAGES = frozenset({"windowsterminal.exe", "openconsole.exe"})

#: 判「這是本 repo 造成的」的字面。以**路徑與檔名**為準而不是行程名：同一支
#: `powershell.exe` 可能是我們叫的、也可能是別人叫的，只有命令列分得開。
#: 🔴 `git-hooks`／`.venv` 兩條是首跑實測補上的：本 repo 的閘門測試會在系統暫存下造合成
#: repo 再跑 `tools/git-hooks/pre-commit`（Git Bash），那些 `bash.exe` 命令列裡**沒有**
#: repo 根路徑（它們指向暫存目錄）⇒ 首版把自己人判成了外人。低報「我方命中」與過報一樣
#: 貴：它會讓「本 repo 側乾淨」這個結論建立在漏算上。
_REPO_MARKERS = ("session_resume_planner.py", ".claude/hooks", ".claude\\hooks",
                 "autosdd_", "AutoSDD_", "sentinel_lifecycle.py", "console_spawn_watch.py",
                 "git-hooks", ".venv")


def repo_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    return Path(__file__).resolve().parents[2]


def build_pid_index(records: list[dict]) -> dict[int, tuple[str, str]]:
    """掃過**整份**量測記錄，建 `ProcessId → (Name, CommandLine)` 對照表（DEF-200-417）。

    🔴 WHY：WMI 事件是非同步佇列，事件到達順序不保證「父行程的建立事件」比「子行程的
    建立事件」先寫進 jsonl；而父行程若比 `Get-CimInstance` 回呼還短命（見 `classify()`
    docstring 的實例），`ParentCommandLine` 在那一筆記錄裡會是空字串——但那個父行程
    **自己的** `__InstanceCreationEvent` 通常已經先被記過一筆（它建立時間本來就早於
    它生出的子行程）。呼叫端（`report()`）本來就是離線讀完整份 jsonl 才分類，先掃一輪
    建表不多花一次 I/O。
    """
    index: dict[int, tuple[str, str]] = {}
    for record in records:
        pid = record.get("ProcessId")
        if pid is None:
            continue
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            continue
        index[pid_int] = (str(record.get("Name") or ""), str(record.get("CommandLine") or ""))
    return index


def classify(
    record: dict, root: str, pid_index: dict[int, tuple[str, str]] | None = None,
) -> tuple[str, str]:
    """歸因：回 `(類別, 理由)`。類別＝`repo`／`foreign`／`unattributable`。

    🔴 判準的順序即優先序，而且「無法歸因」是**一等公民**而不是垃圾桶：把拿不到命令列
    的行程硬塞進任何一邊，就是本 repo 判過的「量不到 ≠ 量到零」。它必須在報表上自己
    佔一格，讓讀者知道這次量測有多少東西是說不清楚的。

    `pid_index`（DEF-200-417）＝`build_pid_index()` 的結果，預設 `None`（既有呼叫端逐字
    不變）。真機實測：`claude.exe → bash.exe -c "…pythonw.exe …statusline_context_feed.py"`
    （父 pid 9676）比 `Get-CimInstance` 查父行程的回呼快，回呼查到時父行程已 `<gone>`，
    `ParentName`／`ParentCommandLine` 皆空——但 9676 自己的建立事件早先已經被記過一筆，
    `pid_index` 查得到它的命令列。查得到就頂替 `ParentCommandLine` 續往下判；**查不到才
    真的是「無法歸因」**——不得因為查表落空就倒向 `foreign`（`foreign` 必須有正面證據：
    父命令列非空且不含任何 `_REPO_MARKERS`）。
    """
    haystack = " ".join(str(record.get(k) or "") for k in
                        ("CommandLine", "ExecutablePath", "ParentCommandLine"))
    if not haystack.strip():
        parent_cmd = ""
        ppid = record.get("ParentProcessId")
        if pid_index and ppid not in (None, ""):
            try:
                entry = pid_index.get(int(ppid))
            except (TypeError, ValueError):
                entry = None
            if entry:
                parent_cmd = entry[1]
        if not parent_cmd.strip():
            return "unattributable", "命令列與父命令列皆取不到（行程太短命或權限不足）"
        haystack = parent_cmd
    low = haystack.lower()
    if root and root.lower() in low:
        return "repo", f"命令列含本 repo 路徑：{root}"
    for marker in _REPO_MARKERS:
        if marker.lower() in low:
            return "repo", f"命令列含本 repo 標記字面：{marker}"
    # 🔴 首跑實測補的一格（**低報我方命中**，而這正是本檔檔頭說要防的事）：窗內抓到 3 筆
    # `cmd.exe /c "pytest …"`，父行程是 `python -m pytest tests/ -q`（cwd 在 AutoClaude），
    # 命令列**一個 repo 路徑都沒有** ⇒ 首版把它們判成「非本 repo」。它們其實是
    # `execution/evaluator.py` 的 `shell=True`（Windows 上就是 `cmd.exe /c`）。
    # 判準刻意不改成「父行程是 python 就算我們的」——別人的 Python 也會這樣起 cmd；
    # 而是獨立成第四格 `shell-hop`：**這是 `shell=True` 的形狀，需要人去確認是誰的**。
    # 把它塞進 repo 是過報、塞進 foreign 是低報，兩個方向都會讓報表說謊。
    # 🔴 刻意**不**要求命令列裡出現 `/c`：那 3 筆裡有 1 筆的 `CommandLine` 是 `null`
    # （行程太短命，WMI 抓到時已經拿不到），只有父命令列在。要求 `/c` 會讓「最短命的
    # 那一個」——也就是最像黑框的那一個——剛好掉出這一格。判準只問兩件看得到的事：
    # 這是 cmd.exe，而且它的父行程是 Python。
    if (str(record.get("Name") or "").lower() in ("cmd.exe", "sh.exe")
            and str(record.get("ParentName") or "").lower().startswith("python")):
        return "shell-hop", ("`cmd.exe /c` 由 Python 父行程起＝`shell=True` 的形狀。"
                             "本 repo 已知有兩個 `shell=True` 站點（execution/evaluator.py"
                             "／mutation_applier/_conditional.py）⇒ 需人工確認是不是它們。"
                             f"父命令列：{str(record.get('ParentCommandLine') or '')[:120]}")
    return "foreign", f"命令列不含任何本 repo 標記：{haystack[:160]}"


def _watch_script(seconds: float, out: Path, within: float) -> str:
    """產生 WMI 訂閱腳本。父行程資訊在**事件當下**就查，晚一步父行程可能已經消失。"""
    out_q = str(out).replace("'", "''")
    names = ",".join(f"'{n}'" for n in CONSOLE_IMAGES)
    return (
        PS_UTF8_PRELUDE
        + "$ErrorActionPreference = 'Stop'\n"
        f"$keep = @({names})\n"
        f"$deadline = (Get-Date).AddSeconds({seconds})\n"
        "$q = \"SELECT * FROM __InstanceCreationEvent WITHIN "
        f"{within} WHERE TargetInstance ISA 'Win32_Process'\"\n"
        "Register-CimIndicationEvent -Query $q -SourceIdentifier AutoSDDProcWatch\n"
        "while ((Get-Date) -lt $deadline) {\n"
        "  $ev = Wait-Event -SourceIdentifier AutoSDDProcWatch -Timeout 2\n"
        "  if (-not $ev) { continue }\n"
        "  $p = $ev.SourceEventArgs.NewEvent.TargetInstance\n"
        "  Remove-Event -EventIdentifier $ev.EventIdentifier\n"
        "  if ($keep -notcontains $p.Name) { continue }\n"
        "  $par = Get-CimInstance Win32_Process -Filter "
        "\"ProcessId=$($p.ParentProcessId)\" -EA SilentlyContinue\n"
        "  $obj = [ordered]@{\n"
        "    at = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fff')\n"
        "    Name = $p.Name; ProcessId = $p.ProcessId\n"
        "    CommandLine = $p.CommandLine; ExecutablePath = $p.ExecutablePath\n"
        "    ParentProcessId = $p.ParentProcessId\n"
        "    ParentName = $(if ($par) { $par.Name } else { '<gone>' })\n"
        "    ParentCommandLine = $(if ($par) { $par.CommandLine } else { '' })\n"
        "  }\n"
        f"  Add-Content -Path '{out_q}' -Encoding UTF8 -Value "
        "(ConvertTo-Json -Compress -InputObject $obj)\n"
        "}\n"
        "Unregister-Event -SourceIdentifier AutoSDDProcWatch\n"
        "Write-Output 'watch-complete'\n"
    )


def watch(seconds: float, out: Path, within: float = 0.2) -> int:
    """跑一次量測窗。回 rc（0＝訂閱成立且跑完）。"""
    if os.name != "nt":
        print("❌ 本量測器只在 Windows 成立（WMI ＋ console 子系統是 Windows 概念）。"
              "mac/Linux 的對等問題與對等工具不同，本檔刻意不假裝支援。", file=sys.stderr)
        return 1
    holder = Path(tempfile.mkdtemp(prefix="autosdd_spawnwatch_")) / "run.ps1"
    holder.write_text(_watch_script(seconds, out, within),
                      encoding="utf-8-sig", newline="\r\n")
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(holder)],
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=seconds + 120, check=False, creationflags=NO_WINDOW)
    if proc.returncode != 0 or "watch-complete" not in (proc.stdout or ""):
        print(f"❌ 量測沒有跑完（rc={proc.returncode}）。**不得**把它讀成「零命中」：\n"
              f"{(proc.stderr or proc.stdout or '')[:800]}", file=sys.stderr)
        return 1
    return 0


def report(path: Path, root: str | None = None) -> int:
    """讀 jsonl，按三類印出歸因報表。"""
    base = root if root is not None else str(repo_root())
    if not path.is_file():
        print(f"❌ 量測檔不存在：{path}（沒有量到 ≠ 沒有發生）", file=sys.stderr)
        return 1
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    pid_index = build_pid_index(records)
    buckets: dict[str, list[tuple[dict, str]]] = {
        "repo": [], "shell-hop": [], "foreign": [], "unattributable": []}
    for record in records:
        kind, why = classify(record, base, pid_index)
        buckets[kind].append((record, why))
    total = len(records)
    print(f"量測檔 {path}　console 類行程建立事件 {total} 筆")
    # 🔴 DEF-200-417：分開列出「誰是可見視窗的承載者」與「誰多半是隱形視窗」，見
    # CONSOLE_IMAGES 上方註解——這兩行不是三分類歸因的替代品，是同一份記錄的另一個切面。
    visible_n = sum(1 for r in records
                    if str(r.get("Name") or "").lower() in _VISIBLE_CARRIER_IMAGES)
    conhost_n = sum(1 for r in records if str(r.get("Name") or "").lower() == "conhost.exe")
    print(f"可見視窗承載者（WindowsTerminal.exe／OpenConsole.exe）建立事件 {visible_n} 筆")
    print(f"conhost.exe（多半是 CREATE_NO_WINDOW 隱形視窗）建立事件 {conhost_n} 筆")
    labels = {"repo": "① 本 repo 造成", "foreign": "② 非本 repo 造成",
              "unattributable": "③ 無法歸因",
              "shell-hop": "①b `shell=True` 的 cmd 跳板（需人工確認是不是本 repo）"}
    for kind in ("repo", "shell-hop", "foreign", "unattributable"):
        rows = buckets[kind]
        print(f"\n{labels[kind]}：{len(rows)} 筆")
        seen: dict[str, int] = {}
        for record, _why in rows:
            key = (f"{record.get('Name')} ← {record.get('ParentName')} :: "
                   f"{(record.get('CommandLine') or '')[:120]}")
            seen[key] = seen.get(key, 0) + 1
        for key, count in sorted(seen.items(), key=lambda kv: -kv[1]):
            print(f"   x{count:<4d} {key}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="誰生出了 console 行程（黑框歸因）")
    parser.add_argument("--seconds", type=float, default=960.0,
                        help="量測窗長度。預設 960＝16 分鐘，刻意 > 哨兵 900 秒巡邏間隔")
    parser.add_argument("--within", type=float, default=0.2,
                        help="WMI 內部輪詢秒數（比它更短命的行程仍可能漏，見檔頭劃界）")
    parser.add_argument("--out", default="", help="事件 jsonl 落點")
    parser.add_argument("--report", default="", help="只讀既有 jsonl 印歸因報表")
    args = parser.parse_args(argv)

    if args.report:
        return report(Path(args.report))
    out = Path(args.out or (Path(tempfile.gettempdir()) / "autosdd_spawn_watch.jsonl"))
    rc = watch(args.seconds, out, args.within)
    return rc or report(out)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
