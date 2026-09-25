"""全套層孤兒 console 偵測（console_qa 事故輪；DEF-200-388 系列鄰居）。

WHY 抽成獨立檔：`tools/run_root_unittests.py` 是 special-tier LOC 零餘裕棘輪管的檔
（見該檔 DEF-200-162 段——`AutoClaude/tools/check_loc_budget.py` 現查 budget==loc==777，
一行都加不進去）。本檔把「盤點孤兒 console」整段邏輯接走，呼叫端只留一次 `wrap()`
呼叫（單行取代單行，零行數成本）。

事故背景：本機曾累積 630 個 `OpenConsole.exe -Embedding`（父 svchost）＋630 個孤兒
`conhost.exe`（父行程已不存在）＋一個 8196 handle 的 Windows Terminal，約 9 GB——根因
是某個可達的 `subprocess.run`／`Popen` 缺 `creationflags`，在無 console 的 pythonw 宿主
下每觸發一次就讓 Windows 新配置一個 console。本檔在全套 unittest 開始前／結束後各盤點
一次，結束後比開始多即 fail-loud（見 `report_delta` 的假紅風險評估與判準）。

判準（兩種孤兒形態，逐一具名而非「凡是 console 就算」）：
  - `OpenConsole.exe`（不論父行程是誰）——事故本體，每次觸發各生一個新 PID；
  - 父行程已消失的 `conhost.exe`——傳統 console host 的孤兒形態，同一事故的另一半。
  `WindowsTerminal.exe` 本體刻意不計：那是 UI 殼進程，使用者本來就可能開著一個在跑，
  不是本 repo 的 bug 會直接生出的東西（`OpenConsole.exe` 才是每次觸發各生一個那個）。

🔴 假紅風險評估與判準等級（rc 是否變紅）：全套跑在開發者自己的機器上，若使用者在
~60～160 秒的執行窗口內自己開一個新 Windows Terminal 分頁，會被算成「新增」而觸發
本判準的誤判——這個風險不可忽略且無法從外部區分「使用者操作」與「本 repo 的 bug」。
本檔因此採**advisory（只出聲、不判紅）**：這支 runner 的 rc 是 pre-push／CI 的把關者，
讓一個與本輪修復無關的巧合操作把全部推送擋下來，代價比「漏抓一次孤兒累積、留到下次
才被發現」更高——同一取捨方向見本檔呼叫端既有的 `report_skip_census`（未登記平台）／
`report_module_timings`（純印）等 advisory 先例。若未來要升級成阻斷級，建議先收集本
判準在真實 pre-push 使用下的誤判率（同 `tools/probe/shell_command_corpus.py --summary`
的量測優先於直覺的既有紀律），而非現在就用直覺猜一個門檻。

測試：`tools/tests/test_run_root_unittests.py`（接線與 `wrap()` 行為）。
"""
from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

try:
    from win_spawn import NO_WINDOW  # 本檔常被無 console 的 CI/排程宿主呼叫，見該模組 WHY
except ImportError:  # pragma: no cover - 理論上不會發生（同目錄 tools/lib 內的 sibling）
    NO_WINDOW = 0

#: 已存在孤兒數超過這個數字時，除了 delta 之外**額外**警告一次「這台機器已經欠了
#: 一屁股債」——純提醒，不影響 rc（判準只看 delta，見模組 docstring）。
_PRE_EXISTING_DEBT_WARN_THRESHOLD = 20

#: PowerShell 探測指令：一行印一個 `名稱|PID`。`conhost.exe` 只在父行程已消失
#: （`Get-Process -Id <ppid>` 查不到）時才算孤兒；`OpenConsole.exe` 不論父行程是誰。
_PROBE_CMD = (
    "Get-CimInstance Win32_Process | Where-Object { "
    "($_.Name -eq 'OpenConsole.exe') -or "
    "($_.Name -eq 'conhost.exe' -and -not (Get-Process -Id $_.ParentProcessId "
    "-EA SilentlyContinue)) } | ForEach-Object { \"$($_.Name)|$($_.ProcessId)\" }"
)


def snapshot() -> set[tuple[str, int]] | None:
    """目前的孤兒候選 `(行程名, PID)` 集合；非 Windows 回 `None`（無此概念，呼叫端
    據此略過整段判準——console 配置是 Windows 專屬概念，鐵律三：單平台判準不外推）。
    量測失敗（powershell.exe 解析不到／逾時）一律回空集合，不得讓診斷輔助本身變成
    新的失敗來源。
    """
    if sys.platform != "win32":
        return None
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", _PROBE_CMD],
            capture_output=True, encoding="utf-8", errors="replace", timeout=30,
            check=False, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return set()
    out: set[tuple[str, int]] = set()
    for line in (proc.stdout or "").splitlines():
        name, _, pid = line.strip().partition("|")
        if name and pid.isdigit():
            out.add((name, int(pid)))
    return out


def report_delta(
    before: set[tuple[str, int]] | None, after: set[tuple[str, int]] | None
) -> int:
    """比較前後快照並印出結果。回傳值刻意恆為 `0`（advisory，見模組 docstring 的
    假紅風險評估）——呼叫端仍可自行選擇是否採納回傳值影響 rc，本函式不代為決定。
    """
    if before is None or after is None:
        return 0
    if len(before) > _PRE_EXISTING_DEBT_WARN_THRESHOLD:
        print(f"⚠️  全套開始前機器上已有 {len(before)} 個孤兒 console 候選（存量債，"
              f"非本輪新增）：{sorted(before)}")
    new = after - before
    if new:
        print(f"❌ 全套執行期間新增了 {len(new)} 個孤兒 console 候選：{sorted(new)}"
              "——疑似某個可達的 subprocess spawn 缺 creationflags（也可能是使用者同一"
              "時間自己開了新 Windows Terminal 分頁，見本檔假紅風險評估）。處置：手動 "
              "`Stop-Process -Id <PID> -Force` 清掉；定位缺旗標站點見 "
              "tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest。")
    else:
        # DEF-200-397：零增長時此前完全不印，log 分不出「跑了且乾淨」
        # 與「這段根本沒被執行」——advisory 語意不變（仍只出聲、不影響 rc）。
        print(f"✅ 孤兒 console 普查：零增長（前 {len(before)}／後 {len(after)}）。")
    return 0


def wrap(fn: Callable[[], int]) -> int:
    """在 `fn()` 前後各盤點一次孤兒 console 並印出 delta；`fn()` 的 rc 原樣回傳
    （本判準是 advisory，不影響 rc——理由見模組 docstring）。"""
    before = snapshot()
    rc = fn()
    report_delta(before, snapshot())
    return rc
