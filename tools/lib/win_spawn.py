"""無 console 父行程下 spawn 子行程的**防彈窗**兩層防線（唯一的家）。

WHY 這一段從 `.claude/hooks/context_budget_guard.py` 搬出來（R84／C8 的減法）：
它此前住在那支 hook 裡，而 `tools/lib/quota_meter.py`、`tools/session_resume_planner.py`
等消費者是**反過來** `import context_budget_guard` 去取 `NO_WINDOW`／`quiet_python()`
——共用知識住在 hook 裡、由 lib 去 import hook，方向是倒的（`quota_meter.py` 因此
還留了一份「同一個表達式的第二份字面」當備援）。搬到本檔之後方向正過來，且 hook 那支
的 raw-line 棘輪（`AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES`）也因此
真的變小而不是被調高——那條棘輪訊息逐字要的就是「先刪死碼／抽共用模組」。

🔴 本檔刻意**不提供 fallback stub**（與 `quota_limits.py` 同判例、理由逐字相同）：
`NO_WINDOW` 是原語不是能力提供者，給它 `0` 當 fallback 等於讓同一個表達式有第二個家，
而且會在 Windows 上**用錯的答案靜默通過**（旗標沒帶、視窗照彈，失效無聲）。消費端
（hook）以 `sys.path.insert(tools/lib)` 直接 import，不可達時是響的失敗。

搬移是**逐字**搬移：下面每一行的量測值、矩陣與訂正註記都保持原文，一個字都沒有重寫
（重寫等於把當初量到的東西換成今天的轉述，那正是本 repo 反覆判過的病）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: 🔴 R80：在**無 console 的父行程**下 spawn console 子行程時必帶的 creationflags。
#:
#: 立案（掌舵者當場回報「哨兵每 15 分鐘彈一個視窗」，R79 只治了排程 Action 那一層）：
#: hook 行程與 schtasks 的 `pythonw.exe` 都**沒有 console**，而 `python.exe`／
#: `powershell.exe`／`claude.exe` 全是 console 子系統應用 ⇒ Windows 必定替子行程新配置
#: 一個 console，那就是跳到使用者臉上的那個視窗。
#:
#: 🔴 **R80 訂正本段（我自己的第一版在這裡寫了一句過度一般化的假話，照實留下訂正）**。
#: 第一版逐字宣稱「`DETACHED_PROCESS` 會把 `CREATE_NO_WINDOW` 抵銷掉」，依據是一張**只用
#: venv 的 `python.exe` 當子行程**量出來的表。複驗者指出本 venv 由 **uv** 建立
#: （`pyvenv.cfg` 有 `uv = 0.8.22`），其 `python.exe` 是 **trampoline**（274,712 bytes，
#: 對照真直譯器 103,192 bytes）：它會 re-spawn 真的直譯器，而**不把 creationflags 傳下去**
#: ⇒ 那張表量到的是 trampoline 的行為，不是旗標語意。
#:
#: 重量後的完整矩陣（pythonw 當無 console 父行程；子行程自報 `GetConsoleWindow()`／
#: `IsWindowVisible`。`0`＝沒有 console＝不會有視窗）：
#:
#:   子行程載具            none    CNW   DET|CNW   DET    NEWGRP|CNW   NEWGRP
#:   base python.exe      可見     0       0        0         0        可見
#:   venv python.exe      可見     0     可見      可見        0        可見   ← trampoline
#:   base pythonw.exe       0      0       0        0         0          0
#:   venv pythonw.exe       0      0       0        0         0          0
#:
#: 三個結論，方向都與第一版不同：
#:  ① `DET|CNW` 在**真直譯器**上是好的，只有穿過 trampoline 時才翻面 ⇒ 那句「抵銷」是
#:     載具效應，不是旗標語意。**射程誠實劃界**：本重現依賴「venv 由 uv 建立」；走
#:     `python -m venv` 回退路徑的 venv 是否同樣翻面，**未驗**。不得寫成平台常數。
#:  ② `CNW` 與 `NEWGRP|CNW` 是**唯二在四種載具上全部為 0** 的組合 ⇒ 本常數取後者。
#:  ③ **pythonw 那兩列全 0，與旗標無關** ⇒ 載具本身就足以抑制視窗。
#: ⇒ 故本檔採**兩層各自獨立成立**（缺一層仍安全）：載具走 `quiet_python()`、旗標走本常數。
#: 六組的 stderr／rc 都完整回得來 ⇒ 抑制視窗不以可觀測性為代價。
#:
#: 為什麼用 `CREATE_NEW_PROCESS_GROUP` 而不是 `DETACHED_PROCESS`：舊寫法想要的是「子行程
#: 不受父行程生死牽連」。實測那件事**不需要** `DETACHED_PROCESS`——本常數的組合下，父行程
#: （pythonw）退場後 8 秒，子行程仍自己把痕跡檔寫了出來（父死 02:02:50、子寫檔 02:02:58）。
#: `CREATE_NEW_PROCESS_GROUP` 保留了真正有用的那一半（Ctrl-C／Ctrl-Break 不會沿著父行程的
#: 行程群組傳進來），而且它在 trampoline 上不像 `DETACHED_PROCESS` 那樣翻面。
#:
#: `getattr` 而不是直接取屬性：這三個常數在 POSIX 的 `subprocess` 上**不存在**（鐵律三
#: 「這在另一個平台是什麼值」）。取 0 ＝不加任何旗標，正是 POSIX 上正確的值。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def quiet_python() -> str:
    """回本檔 spawn 子行程該用的直譯器路徑——**兩層防線的第二層**。

    上表第三、四列：`pythonw.exe`（GUI 子系統）在**全部六種旗標組合下**都是 0，
    連 trampoline 那一列也是 ⇒ 換掉載具這件事本身就足以抑制視窗，與旗標無關。
    故本函式與 `NO_WINDOW` **各自獨立成立**：任一層被未來的人改掉，另一層仍撐得住。

    🔴 為什麼是 `with_name` 而不是靠 PATH：實測本機**兩個 session 的 `python` 解析到不同
    東西**（互動 session → venv；schtasks 起的 headless → pyenv shim，後者沒有
    `pythonw.exe`）。取「與當前直譯器同目錄」才與 session 怎麼被啟動無關。
    找不到就退回 `sys.executable`——少一層防線，不是壞掉（旗標那層仍在）。

    🔴 R84／C3-P1b：退回這件事**必須出聲**。此前它是靜默的，而哨兵路徑上另一層
    （排程 Principal 的 S4U → InteractiveToken 回退）同樣靜默 ⇒ 兩層一起失效時
    使用者看到的是每 15 分鐘一個黑框，而工具側**零痕跡**可查。出聲只寫 stderr、
    不改回傳值也不拋例外：這是降級不是故障，判紅會讓沒有 pythonw 的機器整條武裝不了。
    每個行程只講一次（哨兵 tick 會反覆呼叫，洗版等同沒講）。
    """
    if os.name != "nt":
        return sys.executable  # POSIX 沒有 console 這回事，也沒有 pythonw（鐵律三）
    quiet = Path(sys.executable).with_name("pythonw.exe")
    if quiet.is_file():
        return str(quiet)
    global _QUIET_PYTHON_FALLBACK_ANNOUNCED
    if not _QUIET_PYTHON_FALLBACK_ANNOUNCED:
        _QUIET_PYTHON_FALLBACK_ANNOUNCED = True
        sys.stderr.write(
            f"⚠️ QUIET-PYTHON-FALLBACK：找不到 {quiet}，退回 console 版直譯器 "
            f"{sys.executable} ⇒ 防彈窗只剩旗標那一層。"
            "（本行是**痕跡**不是錯誤；要治本請確認 venv 內有 pythonw.exe）\n")
    return sys.executable


#: `quiet_python()` 的一次性痕跡旗標（見該函式）。模組層而非函式屬性：後者在
#: `runpy` 重載時會被靜默重置，而重載正是哨兵 tick 每次都會做的事。
_QUIET_PYTHON_FALLBACK_ANNOUNCED = False
