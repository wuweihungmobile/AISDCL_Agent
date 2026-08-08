#!/usr/bin/env python3
"""Claude Code hook 啟動器（exec form 用）— 取代原本散在 `.claude/settings.json`
十個條目裡那份逐字複製十遍的 `python -c "…runpy…"` shell shim。

**為什麼要有這支檔**：Windows 上 Claude Code 的 shell form hook 是用 Git Bash 的
`bash.exe -c` 跑的，而 `bash.exe` 是 console 子系統程式、CC 生它時沒有帶
`windowsHide` ⇒ 每觸發一次 hook 就閃一個 console 視窗。exec form（條目帶 `args`
欄位）不經 shell、直接 spawn，把 `command` 指到 GUI 子系統的 `pythonw.exe` 即可
零視窗（R80 實測：shell form 一次 hook 產生 1 個 conhost，exec form 產生 0 個）。
而 exec form 的 `command` 只能是**一個執行檔路徑**，塞不進那段 `-c` 程式碼——
所以「把十份 shim 收成一個家」不是順手美化，是治彈窗的必要條件。

行為與舊 shim **逐項等價**（刻意不改語意）：
  - 專案根 = `CLAUDE_PROJECT_DIR`（CC 注入），未設時回退 cwd
  - argv[1] = 目標腳本的 repo 相對路徑（一律正斜線寫法，本檔負責轉平台分隔符）
  - 目標腳本**缺檔＝exit 0（fail-open）**，絕不讓缺檔演變成 PreToolUse deny
    （`.claude/settings.json` description 記載過的 P0：hook 誤觸 deny 會把所有工具硬鎖死）
  - `os.chdir(root)`、`sys.argv = [目標絕對路徑] + 其餘引數`、`runpy.run_path(..., '__main__')`

唯一新增的一件事（pythonw 專屬危害，`python.exe` 上不存在）：GUI 子系統程式在
**沒有被接管線**時 `sys.stdout` / `sys.stderr` / `sys.stdin` 會是 `None`，
目標腳本裡任何 `print()` 會炸 AttributeError。CC 現況是三條都接管線（R80 六個
marker 實測 `stdout_is_none=false`），但那是 CC 的實作細節、不是契約 ⇒ 這裡補上
devnull 兜底，讓契約不依賴它。🔴 誠實劃界：**這個兜底本身沒有被驗證觸發過**
（試過 DETACHED_PROCESS 製造 None 流，實測拿到 `[False, False, False]`，條件沒造出來）
——它是未驗證的保險，不是已驗證的行為。

本檔的行為契約由 `tools/tests/test_check_hooks_liveness.py` 機械釘住
（`TestHookLauncherContract`：stdin 直通／argv 形態／cwd／缺檔 fail-open／
exit 2 不被吞掉）。**改這支檔之前先讀那組測試**：它是全部 hook 的唯一入口，
把 fail-open 改成別的東西等於一次弄壞六支守衛。

🔴 兩個平台各有一條會失敗，而失敗是 **fail-open**（只記一行 ERROR、工具照跑）：
Windows 條目在 POSIX 是 ENOENT（`.venv/Scripts/pythonw.exe` 不存在）、
POSIX 條目在 Windows 是 EFTYPE（`.py` 不能直接 spawn）。**這代表「hook 全部靜默
消失」與「修好了」的螢幕表徵一模一樣**，所以本檔的存在同時要求兩道現查：
  · 宣告與實況綁定：`tools/tests/test_check_hooks_liveness.py` 的載具存在性判準
  · 一行現查（見根 CLAUDE.md〈Windows 側單一載具原則〉）：
    `Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\\Scripts\\pythonw.exe')`
"""
from __future__ import annotations

import os
import runpy
import sys


def _ensure_streams() -> None:
    """pythonw 在無管線時三條標準流皆為 None；補 devnull，避免目標腳本 print 炸掉。"""
    if sys.stdin is None:
        sys.stdin = open(os.devnull, encoding="utf-8")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


def main() -> None:
    _ensure_streams()
    if len(sys.argv) < 2:
        sys.exit(0)  # 沒給目標＝什麼都不做，絕不 exit 2
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    target = os.path.join(root, *sys.argv[1].split("/"))
    if not os.path.isfile(target):
        sys.exit(0)  # fail-open：缺檔靜默失效（與舊 shim 同）
    os.chdir(root)
    sys.argv = [target] + sys.argv[2:]
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
