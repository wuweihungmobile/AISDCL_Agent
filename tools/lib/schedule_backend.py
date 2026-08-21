"""排程後端 —— 「這台機器用哪一個 OS 排程器」這個問題的唯一提問點（射程見下方〈射程〉）。"""
# 立案 WHY、憑證設計、以及每一條實測依據全部在下面的 `#` 註解區。寫成註解而不是
# docstring 是本 repo 既定作法（`count_loc` 計 docstring、不計註解；`tools/lib/*` 的
# `guardrail_lib` tier 上限 400），與 `tools/session_resume_planner.py` 檔頭同一手法。
#
# 🔴 〈射程〉——「唯一提問點」這句話原本是**無限定版**，而它在寫下的那一輪就有反例
# ---------------------------------------------------------------------------
# R83 複審 A-02／F-6 訂正（原句逐字：「…這個問題的**唯一提問點**（R83／W2-A）。」）。
# 反例逐字（複審者當回合實測，本輪已修）：`tools/lib/sentinel_lifecycle.py` 的**回收臂**
# 對本檔的 import 數是 **0**，它自己硬寫 `powershell.exe` 去列舉哨兵 ⇒ mac 上那支
# `_powershell` rc=**127**、`sentinel_task_names()` 回 `[]`，而同一刻 `launchctl list` 列著
# 活著的哨兵、每 900s 巡邏、永不自我解除。**回報是「沒有任何工作」**＝假陰性，而 GC 正是
# 用來發現增生的那支工具 ⇒ 它比壞掉更危險（壞掉會被看見，回報一切正常不會）。
# 更難看見的一半：守這句宣稱的鎖當時只讀 `.claude/hooks/context_budget_guard.py` 一支檔
# ⇒ **有鎖在守假話**（檔案在、判準在、測試全綠），本 repo 判過這比沒鎖更貴。
#
# ⇒ 本輪的處置是兩件事一起做，而不是把宣稱降級了事：
#   ① 回收臂接上 `select()`（見下方 `list_jobs`；`sentinel_lifecycle` 的 `powershell.exe`
#      那一份因此整支刪除——它本來就是 `planner.run_powershell` 的第二個家）。
#   ② 這句宣稱改成**有機械物守得住**的版本，射程逐字寫在這裡：
#      · 射程＝`tools/`／`.claude/hooks/` 底下所有**非測試** `.py`。凡把排程器原語
#        （argv 首字為 `launchctl`／`schtasks`，或腳本內含 `-ScheduledTask` cmdlet）
#        餵給 runner（`subprocess.*`／`run_powershell`／`_powershell`／`_run`）的站點，
#        一律只能住在**宣告過的家**裡。判準＝`tools/tests/test_mac_endurance_r83.py::
#        CarrierPrimitivesHaveOneHomeTest`——分母是現查出來的檔集合（不是寫死清單），
#        新站點一律紅；豁免必須具名並附理由（理由留空不算豁免）。
#      · **不含** `.ps1`／`.sh`：`tools/install_mac_nightly.sh` 仍自持一整套 launchd 原語
#        （legacy `load/unload` vs 本檔的 `bootstrap/bootout`、`launchctl list` vs `print`）
#        ⇒ launchd 知識今天仍有**兩個家**。本輪不修，明文登記（複審 A-05）。
#      · **不含**「先把腳本存成模組常數、再餵給 runner」那個形態（判準只看呼叫點的引數）
#        ⇒ `tools/check_scheduled_task_drift.py` 因此不在今天的命中集內。這是判準的
#        已知盲區，寫在這裡而不是留給下一個人自己發現。
#
# 病（掌舵者訴求 3／6，P0）
# ------------------------
# 「額度耗盡 → 排程喚醒 → 續跑」這條鏈在 mac 上**整條缺席**，而缺席的表徵是綠的：
#   · `python tools/session_resume_planner.py --arm-sentinel` 在 mac 上逐字印
#     「❌ 本功能只在 Windows 成立…」而**整條指令 rc 仍是 0**（本輪複驗，見交付報告）；
#   · `.claude/hooks/context_budget_guard.py` 的武裝臂有多處 `os.name != "nt"` 早退
#     ⇒ SessionStart／PostToolUse 在 mac 上一行都不會武裝。
# 量測臂（`--check`／`--check-autocompact`）在 mac 一直是好的 ⇒ 壞掉的只有排程臂。
#
# 為什麼是**新的一個模組**，而不是在 planner 裡多長幾個 `if os.name == "nt"`
# --------------------------------------------------------------------------
# planner 已經有一處 `os.name != "nt"`（`run_powershell`），hook 那一側有六處。再補一個
# 平台就是十幾處各自為政的平台判斷——本 repo 對「同一份知識住兩個家」有反覆的判例
# （R73 `Find-GitBash`、R79 `NO_WINDOW`、R82 兩份 `Popen`）。本檔把那個問題收斂成一個
# 函式（`select()`），其餘所有消費者一律問它、不自己問 `os.name`。
# 🔴 刻意**不**放進 `tools/lib/sentinel_lifecycle.py`：那一檔的主題是「什麼樣的 session
# 值得一支排程、什麼時候該收」＝**判準**，與「這台機器用哪個排程器」＝**載具**是兩個
# 會各自演化的軸。合在一起會讓 mac 支援與門檻調整互相絆住。
#
# 🔴 取證憑證在 mac 與 Windows 是**相反**的（本輪三組實測，逐字見交付報告）
# ---------------------------------------------------------------------
# Windows：`Get-ScheduledTask` 對**不存在**的工作回 **rc=0**（非終止錯誤）⇒ rc 沒有鑑別
#   力，憑證只能是 `NextRunTime` 這個**值**（根 CLAUDE.md〈反事後諸葛取證規則〉）。
# macOS：`launchctl print gui/<uid>/<label>` 對不存在的 label 回 **rc=113**、對存在的回
#   **rc=0** ⇒ **rc 在這一側是有鑑別力的**，可以當第一道閘。
#   但 mac **沒有** `NextRunTime` 的對等物：`launchctl print` 的輸出裡 `next`／`fire`／
#   `due` 全部命中 0（實測），launchd 從不告訴任何人「下次幾點跑」。
#
# ⇒ mac 的憑證是**三件式**，三件都成立才發：
#   ① `launchctl print` rc=0            —— 證明 launchd 此刻的 gui 網域裡真的有這個 label
#                                          （不存在時是 113，不是 0 ⇒ 這一格不是假綠）。
#   ② **descriptor 回讀相符**            —— `run interval = N seconds` 與 `arguments = {…}`
#                                          是 **launchd 自己印出來的**，不是我們寫進 plist
#                                          的那份。兩者比對相等，才證明「排出去的參數就是
#                                          我要的那一組」。少了這一件，「有一支同名工作」
#                                          與「有一支會做正確事情的工作」分不開。
#   ③ **plist 落地路徑**                 —— 同樣取 launchd 自報的 `path = …`。它證明這支
#                                          排程是**持久化**的，登出／重開機後會被重新載入。
#                                          `install_mac_nightly.sh` 檔頭記載過這個 macOS
#                                          專屬狀態：「已載入但磁碟上 plist 已被刪」＝一支
#                                          註定死掉的排程，而 `launchctl list` 照樣列它。
#
# 🔴 這組憑證**證明不了**什麼（誠實劃界，不准包裝成 NextRunTime 的等價物）
#   · **下次幾點跑**：launchd 不報。任何「下次 HH:MM」都是**我們**拿 interval 推算的，
#     不是排程器的陳述。所以本檔的憑證字串裡一個推算時刻都不放——放了就會有人把它當成
#     排程器回報的值來引用，那正是 Windows 側 `NextRunTime` 之所以是憑證的理由被掏空。
#   · **睡著的 Mac 會不會醒來跑**：不會。launchd 只在機器醒著時補跑錯過的一輪
#     （man launchd.plist）。Windows `WakeToRun` 的 mac 對等物住在 `pmset repeat`、需要
#     sudo，不在 plist 裡（`install_mac_nightly.sh` 的 R82 MAC-04 段已把這件事量清楚）。
#     ⇒ 闔蓋過夜時哨兵不會醒，額度回來的偵測會延到開蓋。**這是真缺口，本包不假裝補上。**
#   · **它跑起來會不會成功**：憑證只證明排程存在且參數正確，不證明被排的程式會做對事。
#
# 🔴 mac 的觸發：`StartInterval`（巡邏底盤）＋ `StartCalendarInterval`（真正的時刻）
# ---------------------------------------------------------------------------
# Windows 側每一次 tick 都用 `-Once -At <時刻>` 重排自己（`Register-ScheduledTask
# -Force`）。那個形狀在 mac 上做不到的那一半是實測出來的：launchd job 在自己的行程裡
# **同步**對自己 `launchctl bootout`，會被 launchd 當場終止——合成實驗逐字：job 寫下
# `start <epoch>` 之後，`bootout` 那一行的 rc **從未被寫進 log**，行程死在那裡。
#
# 🔴 **R83-B 訂正本段的結論（原結論的前半為真、後半是一句假話，故不逐字複述）**。
# 原結論是「launchd 走重複觸發、**不吃時刻**，所以 `at` 這個參數刻意不使用」。前半（重複
# 觸發當底盤）今天仍然成立且保留；後半**在寫下的那一輪就是錯的**，而它的代價已經發生：
#   · 事實一（本輪逐位元組實測）：四個相異 `at_expr`（`'2026-08-10 23:02:00'`／
#     `'2027-01-01 00:00:00'`／`(Get-Date).AddHours(5)`／空字串）產出的 plist
#     **sha256 完全相同**，相異指紋數 = 1 ⇒ 那個引數結構上到不了 plist。
#   · 事實二：而決策層（`sentinel_decide` 的 `arm_reset`）當時逐字印「⇒ **重排到那個
#     時刻**（本次零 token）」。**那句話是假的**，而它是唯一有人會讀的那一行。
#   · 代價：本輪真實撞線語料裡同一個判定連印四次（22:06／22:21／22:36／22:51，`fire_at`
#     每次都是 23:02:00），掌舵者據此判定「喚醒完全不 WORK」並開了一個 P0。**假話造成
#     假診斷**——這正是本 repo 通篇在防的那一件事，只是這次它發生在防它的那一段自己身上。
# ⇒ 而 launchd **其實吃時刻**：原語是 `StartCalendarInterval`，`tools/install_mac_nightly.sh`
#   的 nightly plist 早就在用它（Hour/Minute）。本輪三組真機實測把它接起來：
#   · E2：`launchctl print gui/501/com.autoclaude.nightly` 回讀逐字
#     `stream = com.apple.launchd.calendarinterval` ＋ `descriptor = { "Minute" => 0
#     "Hour" => 2 }` ⇒ **launchd 自己會把時刻講回來**，所以它可以當憑證（見 `_CAL_KEYS`）。
#   · E3：同一份 plist 內 `StartInterval = 3600` 與 `StartCalendarInterval = 23:25`
#     **共存**，回讀兩者皆在，且 calendar 真的觸發（逐字 `E3 FIRED 23:25:04`、
#     `runs = 1`、`last exit code = 0`）⇒ 兩個原語不互斥。
#   · ⇒ 故本檔的形狀是**兩者並用**，而不是二選一：
#       `StartInterval` = 自我修復的底盤（漏掉一次 calendar 不會讓哨兵死掉、
#                          自殺路徑仍然結構上不存在）；
#       `StartCalendarInterval` = 真正被要求的那個時刻（只在它是**真的截止時刻**時才寫，
#                          見 `_calendar_of`）。
# 收斂掉的量：`arm_reset` 之後「reset 到了卻沒有人動作」的最壞死等時間，由**一整個巡邏
# 間隔**（900s；本輪實測 reset 23:00、實際動作 23:06:33 ＝ 393 秒死等）降到 ≤60 秒
# （calendar 是分鐘粒度，且 `_calendar_of` 只往後取整、絕不提早）。根 CLAUDE.md
# 〈額度耗盡〉那一節把這個量講成「巡邏間隔決定的是 reset 之後最壞多久才有人動作」，
# 所以它正是這一節在意的那個數字。
# 仍然照實寫的代價：
#   · `tick_plan` 的暫時性錯誤退避 `TRANSIENT_RETRY_SECONDS`（300s < 900s）在 mac 上
#     實際粒度仍是 900s ⇒ 暫時性錯誤的重試會慢最多 10 分鐘。`_calendar_of` 刻意不替它
#     寫 calendar：那會讓每一次 502 都觸發一輪 bootout+bootstrap（見下一段的風險），
#     用一次 10 分鐘的延遲換掉一個結構性風險是划算的。
#   · **睡著的 Mac 一樣不會醒**。`StartCalendarInterval` 只是「醒著時到點會跑」（錯過的
#     那一輪 launchd 會在下次醒來補跑），Windows `WakeToRun` 的對等物住在 `pmset repeat`
#     ／需要 sudo、不在 plist 裡。本包**不碰 sudo、不宣稱補上這一格**（`DEF-200-020` 已
#     登記「6e 不得宣稱達成」），憑證字串因此明文帶著這一句。
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 「這台機器」的兩個事實（痕跡的持久居所、電源姿態）唯一的家。**不是**第二個平台知識的家：
# 本檔仍是排程載具唯一的提問點，那一檔一個 `launchctl`／`schtasks` 都不碰；它被抽出來的
# 理由是本檔 `count_loc` 落地當回合為 395/400（餘裕 5），而那正是 ROOT-TOOLS
# `override_reason` 指定的動作（「破線後不是調高預算，而是拆職責／抽共用模組」）。
import endurance_env
from schedule_backend_calendar import (
    _append_trace,
    _calendar_of,
    _descriptor_problems,
    _first_int,
    _labels_with_prefix,
    _unsafe_name,
)

#: 兩個後端把憑證寫進續航狀態塊的**不同鍵**。刻意不共用 `next_run_time` 一個鍵：
#: 那個鍵名在 mac 上是一句假話（launchd 不報 next-run），而把 launchd 憑證塞進一個叫
#: 「下次執行時間」的欄位，就是把「推算值」偽裝成「排程器回報值」。
#: `relay_problems()` 改成「兩鍵任一非空」，所以守衛強度一格都沒放鬆：拿不到憑證仍然
#: 不准把 state 寫成 armed／waiting。
CRED_KEY_SCHTASKS = "next_run_time"
CRED_KEY_LAUNCHD = "schedule_credential"

#: launchd 對**不存在**的服務回這個 rc（本機實測；存在時 0）。它是 mac 側第一道閘。
LAUNCHCTL_ENOENT_RC = 113

#: LaunchAgent 的家。放這裡（不是 `/Library/LaunchAgents`）＝使用者網域、不需要 sudo，
#: 與 `tools/install_mac_nightly.sh` 同一個家族。
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

#: `launchctl print` 會把 `StartCalendarInterval` 回讀成 `event triggers` 裡的一個
#: `descriptor`（真機實測逐字：`stream = com.apple.launchd.calendarinterval` 之後
#: `"Minute" => 0` / `"Hour" => 2`）。**這件事很重要**：它讓「時刻真的排進去了」變成一個
#: 由 launchd **自己**陳述的憑證，而不是我們回讀自己剛寫的 plist——後者正是〈反事後諸葛〉
#: 那條規則要防的形態。四個鍵刻意全部釘住（見 `_calendar_of` 為何連 Month/Day 一起寫）。
_CAL_KEYS = ("Month", "Day", "Hour", "Minute")

#: 延後子行程「等父行程真的退場」的上界（秒）。
#: 🔴 這個常數取代的是一個**寫死的 3 秒 sleep**，而那 3 秒是 R83-B 這個 P0 的根因：
#: `disarm()` 之後主行程還要做多久，隨**呼叫端**而異——`_sentinel_tick` 的 disarm／
#: escalate 分支只再寫一行 log（3 秒夠），而 `_resume_tick` 的 resume 分支在 disarm 之後
#: 才跑 `_run_resume`（`subprocess.run(..., timeout=3600)`）⇒ 3 秒後 bootout 把整個 job
#: 連同那一跑一起殺掉。真機合成實驗逐字重現（R83-B，本機 macOS 25.5.0）：長工作寫到
#: `t+2s` 就沒有下一行，`bootout rc=0` 落在 4 秒後，代表 `append_log(resumed)` 的那一行
#: **永遠寫不出來**。它與本輪真實撞線語料逐字同形（`probed` 23:06:37 → `bootout rc=0`
#: 23:06:41 → 沒有任何 `resumed` 事件）。
#: ⇒ 修法不是「把 3 改大一點」（那只是換一個會過期的猜測），而是讓那句原本就寫在
#: `disarm` 上方的話**變成真的**：「主行程把該寫的都寫完、正常退場，然後才 bootout」。
#: 上界必須大於 `_run_resume` 的 `timeout=3600`，否則最長的那一跑仍會被砍。
#: 誠實劃界：等的是 pid，pid 在一小時內被回收再指到別的行程理論上可能——後果只是
#: bootout 晚一點（等到那個無關行程也退場或撞上界），不是失效。
DEFER_WAIT_CAP_SECONDS = 3900

#: 無視窗旗標。語意的唯一的家＝`.claude/hooks/context_budget_guard.NO_WINDOW`；本檔
#: **複製同一個表達式**而不 import 它——依賴方向是 `tools → .claude/hooks`，而本檔正是
#: 那一側 hook 的被 import 者（`session_resume_planner` 同時 import 兩者），直接反向
#: import 會成環。相等由 `tools/tests/test_context_budget_guard.py` 的複製品名冊守著。
#: 🔴 R84／C3-P2 為什麼補在本檔：本檔的兩個 spawn 站點是**哨兵路徑上僅存的裸 spawn**
#: ——`_run()` 每個 tick 都會叫（schtasks 查詢／註冊），`_defer()` 起延後的 `/bin/sh`。
#: Windows 上不帶旗標 spawn console 子系統程式，父行程是 pythonw（無 console）時會
#: **新配置一個視窗**＝彈窗從這裡漏出來。POSIX 上 `getattr(..., 0)` 回 0＝不加旗標，
#: 正是這個平台上正確的值（鐵律三「這在另一個平台是什麼值」）。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


# 跑一個外部指令，回 `(rc, stdout+stderr)`。跑不起來一律 `(127, 訊息)`。
def _run(argv: list[str], timeout: int = 60) -> tuple[int, str]:
    # `encoding=`／`errors=` 明寫：`tools/tests/test_subprocess_encoding_hygiene.py`
    # 守的那一條（預設編碼在不同平台不同，非 ASCII 會靜默降解）。
    try:
        proc = subprocess.run(argv, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False,
                              creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# 🔴 R83／F2-② 立案：`evidence_hint()` —— 「怎麼查它真的排進去了」是**載具**的性質，
# 所以它的家在這裡，不在訊息產生端。修前 `tools/lib/quota_gate.quota_halt_message()`
# 在 halt／armed 那一支硬寫 `Get-ScheduledTask …` 與「憑證是 `NextRunTime`」，而 R83 把
# mac 接上 launchd 之後那條路在 mac 上**走得到**（`posix` 由 `has_carrier()` 決定 ⇒ mac
# 是 False）⇒ 武裝是真的、憑證是真的，**指路是假的**：那個 cmdlet 在 mac 不存在，而
# `NextRunTime` 這個概念 launchd 從不提供（見檔頭〈誠實劃界〉）。
# 「憑證裡混一句假話，比沒有那一欄更難看見」——本檔 `_readback` 的 depth-1 訂正同一條判例。
#
# 🔴 `list_jobs()` 的**刪除 → 回補**沿革（F2-⑤ 落地，R83 複審 A-01／A-06 回補）
# ---------------------------------------------------------------------------
# 原判斷（逐字保留為沿革，它在當時是對的）：`list_jobs()` 從 `LaunchdBackend`／
# `NoCarrierBackend` **刪除**而不是補一支給 `SchtasksBackend`——依據是實查而非偏好：全庫
# `list_jobs` 只有那兩個 `def`，零呼叫端、零測試 ⇒ 死碼；補第三支＝為一個不存在的呼叫端
# 寫推測性程式碼（Rule 2）。原註記自己還寫了那句話的失效條件：「**哪天真的有消費者，補的
# 時候三支一起補**」。
# 🔴 那一天就是同一輪的複審日：消費者**當時就存在**，只是住在還沒重構的另一側——
# `sentinel_lifecycle.sentinel_task_names()` 就是這支方法的 Windows 孿生，而它有活消費者
# （`gc()`）。⇒ 「零呼叫端」在字面上為真、在語意上為假，而那筆減法把 mac 回收臂的修法從
# 「叫一個現成方法」變成「先補回原語」（複審 A-06 逐字）。
# 回補時三個後端**一起**補（單平台判準不可無條件外推，DEF-101-766 的形態，只是這次外推的
# 是**介面**：`select().list_jobs(...)` 若只有 mac 有，同一行在 Windows 上 `AttributeError`）。
# 對稱本身由 `test_mac_endurance_r83.BackendInterfaceIsSymmetricTest` 機械守（任一後端多一個
# 或少一個公開方法即紅）。
#
# 🔴 回傳型別是 `list[str] | None`，而 `None` **不等於** `[]`
# ------------------------------------------------------
# `None`＝**量不到**（載具不可達／列舉指令 rc 非 0）；`[]`＝量到了、真的沒有工作。這一格
# 就是本 repo 通篇那條紀律（量不到 ≠ 量到零，見 `sentinel_lifecycle.reap_verdict` ② 的判例）
# 在**列舉層**的落點，而塌成 `[]` 的代價已經實測發生過：GC 逐字回報「（沒有任何
# AutoSDD_Sentinel_* 工作…）」，同一刻 `launchctl list` 列著活著的哨兵。**假陰性在這一支
# 特別貴**：查不到就等於「沒有東西要收」，於是專門用來發現增生的那支工具回報一切正常。
# 哨兵工作名前綴。唯一的家＝`tools/lib/sentinel_lifecycle.TASK_PREFIX`。
def _task_prefix() -> str:
    # lazy import 的理由同 `_planner()`：那支模組會被 hook 鏈 import，模組層取用易成環。
    # 取不到時回空字串 ⇒ 取證指令退化成「列全部」，那仍然是可執行的真指令，不是假話。
    try:
        import sentinel_lifecycle  # noqa: PLC0415 — 見上
    except Exception:  # noqa: BLE001 — 取不到前綴不得讓整支訊息炸掉
        return ""
    return str(getattr(sentinel_lifecycle, "TASK_PREFIX", ""))


# lazy import `tools/session_resume_planner.py`；不可達回 `None`。
# 形態與理由逐字同 `tools/lib/sentinel_lifecycle._planner_module()`：本檔被 planner
# import，模組層反向 import 會成環；而 schtasks 那一整套知識（PowerShell 載具、UTF-8
# 前置、單引號跳脫、`NextRunTime` 解析）的**唯一的家**在 planner，本檔不抄第二份。
# （本段由 docstring 改寫為註解，理由同檔頭第 2~4 行宣告的既定作法：`count_loc` 計
#  docstring、不計註解，而本檔為了 R83-B 的 calendar 觸發需要騰出額度。一字未刪。）
def _planner():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        import session_resume_planner as planner  # noqa: PLC0415 — 見 docstring
    except Exception:  # noqa: BLE001 — 不可達＝這個後端做不了事，不是崩潰
        return None
    return planner


# ─────────────────────────────────────────────────────────── Windows：schtasks
# 🔴 本類別**一行新知識都沒有**：四個方法全部把工作交回 planner 既有的實作，body 與
# 搬家前逐字相同。這是刻意的——本包的驗收條件之一是「Windows 那一側行為零改變」，而
# 「順手改一下」正是那種零改變宣稱最常破掉的地方。
class SchtasksBackend:
    """Windows 排程載具。憑證＝`NextRunTime` 這個**值**（rc 在這一側沒有鑑別力）。"""

    name = "schtasks"
    credential_key = CRED_KEY_SCHTASKS

    # 註冊／重排並當場取證。回 `(rc, NextRunTime)`；拿不到憑證一律 rc=1。
    # body 與搬家前的 `session_resume_planner._register_at_expr` **逐字相同**。
    # `at_expr` 是 PowerShell 觸發運算式（`'2026-08-09 09:02:00'` 或
    # `(Get-Date).AddHours(5)`），時區收斂由呼叫端做完（見 planner 的 R80 段）。
    # 🔴 `at` 在本後端**刻意不使用**，而這一次「不使用」是對的：`schtasks` 的
    # `-Once -At <時刻>` 本來就吃時刻，那個語意已經完整地由 `at_expr` 表達 ⇒ 再讀一次
    # 結構化的 `at` 只會製造第二個真相源。本包的驗收條件之一是「Windows 那一側行為零
    # 改變」，所以這裡連一行都不動（替身實測見 `WindowsPathIsUnchangedTest`）。
    # （docstring → 註解，理由同檔頭第 2~4 行的既定作法，一字未刪。）
    def arm(self, plan_path: str, task_name: str, at_expr: str, tick: str,
            at: datetime | None = None) -> tuple[int, str]:
        planner = _planner()
        if planner is None:
            return 1, ""
        proc = planner.run_powershell(
            planner.endurance_schtasks_script(plan_path, task_name, at_expr, tick))
        print(proc.stdout, end="")
        moment = planner.next_run_time(proc.stdout)
        if proc.returncode != 0 or not moment:
            print(f"❌ 排程沒有成立（rc={proc.returncode}，NextRunTime 取不到）⇒ "
                  "本工具**不會**說它已排程。\n" + (proc.stderr or ""), file=sys.stderr)
            return 1, ""
        return 0, moment

    # `--verify-schtasks`：只取證既有排程。拿不到 `NextRunTime` 一律 rc=1。
    def verify_cli(self, task_name: str) -> int:
        planner = _planner()
        if planner is None:
            return 1
        proc = planner.run_powershell(
            planner._EVIDENCE_TEMPLATE.format(task=planner._ps_single_quote(task_name)) + "\n")
        print(proc.stdout, end="")
        moment = planner.next_run_time(proc.stdout)
        if proc.returncode != 0 or not moment:
            print(f"❌ 取不到 `{task_name}` 的 NextRunTime（rc={proc.returncode}）"
                  "⇒ 不准宣稱它已排程。\n" + (proc.stderr or ""), file=sys.stderr)
            return 1
        print(self.credential_line(moment))
        return 0

    # 移除排程並**驗證它真的不見了**（rc 不是憑證，`Get-ScheduledTask` 才是）。
    def disarm(self, task_name: str) -> int:
        planner = _planner()
        if planner is None:
            return 1
        task_q = planner._ps_single_quote(task_name)
        proc = planner.run_powershell(
            f"Unregister-ScheduledTask -TaskName '{task_q}' -Confirm:$false\n"
            f"if (Get-ScheduledTask -TaskName '{task_q}' "
            "-ErrorAction SilentlyContinue) { Write-Output 'STILL-PRESENT' } "
            "else { Write-Output 'REMOVED' }\n")
        print(proc.stdout, end="")
        if "REMOVED" not in proc.stdout:
            print(f"❌ `{task_name}` 沒有真的被移除（rc={proc.returncode}）\n"
                  + (proc.stderr or ""), file=sys.stderr)
            return 1
        return 0

    # 現存工作名（前綴過濾）；`None`＝量不到，見檔頭〈回傳型別〉。
    # 🔴 一律 `Get-ScheduledTask`：`schtasks /query` 在本機實測會回**空**＝假陰性
    # （根 CLAUDE.md〈查詢載具自己也會騙人〉）。載具走 `planner.run_powershell` 而不是本檔
    # 的 `_run`：那一支帶 `NO_WINDOW` ＋ UTF-8 前置行 ＋ BOM/CRLF 落檔，少了它在無 console
    # 的父行程（pythonw hook）下會替使用者彈一個視窗，而本檔的 `_run` 一個旗標都不帶。
    def list_jobs(self, prefix: str) -> list[str] | None:
        planner = _planner()
        if planner is None:
            return None
        pat = planner._ps_single_quote(prefix)
        proc = planner.run_powershell(
            "Get-ScheduledTask | Where-Object { $_.TaskName -like '" + pat
            + "*' } | ForEach-Object { $_.TaskName }\n")
        return None if proc.returncode != 0 else _labels_with_prefix(proc.stdout, prefix)

    def credential_line(self, moment: str) -> str:
        return (f"✅ NextRunTime = {moment}　←（憑證；宣稱『已排程』時必須連它一起貼）")

    def evidence_hint(self) -> str:
        return ("憑證是 `NextRunTime` 這個**值**，不是 rc（`Get-ScheduledTask` 對不存在的"
                f"工作回 rc=0）：\n      Get-ScheduledTask | Where-Object TaskName -like "
                f"'{_task_prefix()}*' | Get-ScheduledTaskInfo")


# ─────────────────────────────────────────────────────────── macOS：launchd
class LaunchdBackend:
    """macOS 排程載具。憑證＝rc(113/0) ＋ descriptor 回讀 ＋ plist 落地路徑（見檔頭）。"""

    name = "launchd"
    credential_key = CRED_KEY_LAUNCHD

    # launchd 的使用者網域字串。`gui/<uid>`＝登入 session 的網域。
    def domain(self) -> str:
        # 🔴 `hasattr` 不是防禦性程式碼（鐵律三「這在另一個平台是什麼值」）：`os.getuid`
        # 在 Windows 上**根本不存在**，直接取會 AttributeError ⇒ 那不是「行為不同」而是
        # 「直接炸掉」。本類別今天只由 `select()` 在 darwin 上回傳，但那是**呼叫端的**
        # 性質，會隨呼叫端改變而失效；守衛判準因此是站點級的，不接受「只有那條路走得到」
        # 這種推論。回空字串會讓網域字串明顯不合法（launchctl 立刻拒絕），而不是靜默指向
        # 一個錯的網域。
        if not hasattr(os, "getuid"):
            return ""
        return f"gui/{os.getuid()}"

    def plist_path(self, task_name: str) -> Path:
        return LAUNCH_AGENTS_DIR / f"{task_name}.plist"

    # 武裝／確保已武裝。回 `(rc, 憑證字串)`；憑證任一件不成立即 `(1, "")`。
    # 🔴 `at_expr`（PowerShell 運算式）在本後端仍然**不使用**，但那不再表示「時刻被忽略」
    # ——時刻走 `at` 這個結構化參數（見檔頭 R83-B 那一段與 `_calendar_of`）。兩個參數並存
    # 是刻意的：時區收斂＋格式化留在 `register_endurance`（與載具無關、且既有回歸鎖
    # `ResetFrameIsNotTheMachineClockTest` 打在那個落點），而「時刻」這個語意本身要下沉到
    # 吃得動它的地方。`at=None` ＝呼叫端沒有時刻可給（例：`--print-schtasks-command` 的
    # `DEFAULT_AT_EXPR` 是一段 PowerShell 運算式，解析它是假精確）。
    def arm(self, plan_path: str, task_name: str, at_expr: str, tick: str,
            at: datetime | None = None) -> tuple[int, str]:
        planner = _planner()
        if planner is None or _unsafe_name(task_name):
            print("❌ launchd 武裝拒絕："
                  f"{'planner 不可達' if planner is None else 'label 含路徑分隔符或空白'}"
                  f"（task_name={task_name!r}）", file=sys.stderr)
            return 1, ""
        if not Path(plan_path).is_file():
            # 與 Windows 註冊腳本第一行同一條規則：任務書不存在就不准註冊。它寫在武裝端
            # 而不是任務書裡——任務書不存在時沒有人讀得到寫在它裡面的規則。
            print(f"❌ 任務書不存在，拒絕註冊：{plan_path}", file=sys.stderr)
            return 1, ""
        # 🔴 R84／SA-05：訴求 6e 的**誠實化**（不是達成）。「睡著的 Mac 不會被 launchd
        # 喚醒」此前只活在本檔檔頭一行註解裡，而武裝路徑對 `sleep != 0` **完全靜默** ⇒
        # 憑證照樣印出一份看起來完全正常的三件式。出聲點放在這裡（拒絕註冊的兩條路之後、
        # 真的要排程之前）：只有真的要武裝時才說，而那正是人會讀到訊息的那一刻。
        # 落進痕跡的路徑是憑證字串（見 `_credential`），不另開第二個寫檔點。
        endurance_env.warn_if_sleepy(_run)
        interval = int(planner.SENTINEL_INTERVAL_SECONDS)
        want = self._argv(planner, plan_path, task_name, tick)
        want_cal = _calendar_of(at, interval)
        want_path = str(self.plist_path(task_name))
        # 🔴 plist **每次都重寫**，而且寫在讀回讀之前。理由是 macOS 專屬的一個狀態：
        # 「已載入、但磁碟上的 plist 已被刪」——`launchctl print` 照樣印出 `path = …`
        # （它報的是當初載入的來源），於是憑證的第 ③ 件（已持久化）會是**假的**，而那支
        # 排程登出／重開機後就再也不會回來。`install_mac_nightly.sh` 檔頭把這個狀態記成
        # 硬判準（R68-M31）。寫檔不會動到記憶體裡那一份 ⇒ 對正在跑的 tick 完全安全。
        if not self._write_plist(task_name, want, interval, want_cal):
            return 1, ""
        live = self._readback(task_name)
        if live is not None and not _descriptor_problems(live, want, interval, want_path,
                                                        want_cal):
            # 冪等路徑：已載入且參數完全相符 ⇒ **不碰排程器**。這一格不是效能優化，是
            # 正確性——tick 自己就跑在這支 job 裡，任何 bootout 都會把自己殺掉（實測）。
            # 🔴 R83-B：它同時也是「churn 的上界」——`arm_reset` 連續四個 tick 要求的是
            # **同一個** reset 時刻，第一次寫進 calendar 之後，後三次回讀相符 ⇒ 一次都不
            # 動排程器。所以下面那條重載路徑最多每「相異截止時刻」走一次。
            return 0, self._credential(task_name, live)
        if live is not None:
            if os.environ.get("XPC_SERVICE_NAME") == task_name:
                # 🔴 R83-B 把這一格從 fail-loud 換成**延後重載**（原文的處置逐字是「不動
                # 它」＋rc=1＝讓狀態塊變成 abandoned）。原處置在當時是對的：唯一能表達新
                # 時刻的動作是 bootout+bootstrap，而同步做會把自己殺掉。但接上 calendar
                # 之後，「本 tick 跑在 job 內」正是 `arm_reset` 的**常態**（決策是在 tick
                # 裡做的）⇒ 沿用 fail-loud 會讓每一次撞線都把哨兵標成 abandoned，比修之前
                # 更糟。而 `_defer` 現在等的是「父行程真的退場」（不再是猜 3 秒），所以
                # 「退場之後才重載」這條路是可用的：job 不存在的窗只有毫秒級。
                # 誠實劃界（本包不假裝關掉它）：若那次 bootstrap 三次重試都失敗，哨兵就
                # 真的沒了，而狀態塊會停在 waiting ⇒ **靜默**。能給的界只有兩個，都寫在
                # 這裡：① 子行程把 bootout／bootstrap／print 三個 rc 都寫進痕跡檔（沒觸發
                # ＝那個檔不會長大，是可偵測的）；② plist 仍在磁碟上 ⇒ 下次登入會被重新
                # 載入。憑證字串因此明文不宣稱「重載已完成」（見 `_deferred_credential`）。
                return 0, self._deferred_credential(
                    task_name, want_cal, self._defer_relaunch(task_name, want_path))
            _run(["launchctl", "bootout", f"{self.domain()}/{task_name}"])
        rc, out = _run(["launchctl", "bootstrap", self.domain(), want_path])
        live = self._readback(task_name)
        problems = ["launchctl print 取不到（rc != 0）"] if live is None else \
            _descriptor_problems(live, want, interval, want_path, want_cal)
        if problems:
            print(f"❌ launchd 武裝沒有成立（bootstrap rc={rc}）：" + "；".join(problems)
                  + f"\n{out}", file=sys.stderr)
            return 1, ""
        return 0, self._credential(task_name, live)

    # 只取證既有排程：印 `launchctl print` 全文 ＋ 三件式憑證；不成立 rc=1。
    # 🔴 R83／QA 訂正——**這一支原本只驗「存在」，卻印出「相符」**。原實作在 rc=0 之後
    # 直接發憑證，而憑證字串裡寫著「run interval …〔與請求相符〕｜argv 回讀 N 項相符」
    # ——那兩句話在這條路上**從來沒有被比對過**（`_descriptor_problems` 只在 `arm()` 裡
    # 跑）。QA 複驗當回合的實測：把 job 換成每 7 秒跑一次 `/bin/echo I-AM-NOT-THE-SENTINEL`
    # 的 plist 再 bootstrap，本指令仍回 **rc=0** 並逐字印
    # 「run interval = 7 seconds〔launchd 回讀，與請求相符〕｜argv 回讀 2 項相符」。
    # 那正是〈反事後諸葛〉那條規則要防的形態：憑證存在、但憑證不回答那個問題。
    # Windows 那一側沒有這個對稱缺口——`NextRunTime` 是排程器**自己算的**值，它不需要
    # 比對任何請求就已經是憑證。
    # 本側檢查得到的是**不需要原始請求**的那幾件（見 `_verify_problems`）；argv 逐項
    # 比對做不到（verify 不知道當初那份任務書的路徑），所以憑證的 argv 那一句改成
    # 「未逐項比對」——把做不到的事寫出來，而不是把它說成做到了。
    # （本段由 docstring 改寫為註解，理由同 `disarm` 上方那一句，一字未刪。）
    def verify_cli(self, task_name: str) -> int:
        rc, out = _run(["launchctl", "print", f"{self.domain()}/{task_name}"])
        print(out, end="")
        live = self._readback(task_name)
        if live is None:
            print(f"❌ `{task_name}` 不在 {self.domain()}（launchctl print rc={rc}；"
                  f"{LAUNCHCTL_ENOENT_RC}＝不存在）⇒ 不准宣稱它已排程。", file=sys.stderr)
            return 1
        problems = self._verify_problems(task_name, live)
        if problems:
            print(f"❌ `{task_name}` 在 {self.domain()} 裡存在，但它**不是**本工具武裝的那一"
                  "支續航哨兵：" + "；".join(problems)
                  + "\n   ⇒ 存在不等於憑證，不准拿它宣稱續航已排程。", file=sys.stderr)
            return 1
        print(self.credential_line(self._credential(task_name, live, argv_verified=False)))
        return 0

    # verify 這一側**驗得到**的那幾件；空＝可以發憑證。純函式化的判準，紅綠由注入自證。
    # 與 `_descriptor_problems` 刻意分家：那一支比對的是「這一次的請求」，只有 `arm()`
    # 手上有；這一支比對的是「不依賴請求也必須成立的性質」——plist 是我們持有的那一份、
    # 巡邏間隔是現行常數、argv 裡跑的是 planner 本體。三件都與載入者無關，所以驗得到。
    # 🔴 R83-B 刻意**不**在這裡判 calendar：verify 不知道當初那個截止時刻是什麼，
    # 「有沒有 calendar」在這一側是合法的兩種狀態（巡邏中／等 reset 中）⇒ 判它就是假紅。
    # 憑證字串仍然會把回讀到的 calendar 印出來（`_credential`），那是陳述而不是判準。
    # （docstring → 註解，理由同上。）
    def _verify_problems(self, task_name: str, live: dict) -> list[str]:
        planner = _planner()
        problems = []
        want_path = str(self.plist_path(task_name))
        path = str(live.get("path") or "").strip()
        if path != want_path:
            problems.append(f"launchd 載入的 plist 是 {path!r}，不是我們持有的 {want_path!r}")
        if planner is not None:
            if live.get("interval") != int(planner.SENTINEL_INTERVAL_SECONDS):
                problems.append(f"run interval 回讀 {live.get('interval')!r}，"
                                f"現行巡邏間隔是 {int(planner.SENTINEL_INTERVAL_SECONDS)}")
            me = str(Path(planner.__file__).resolve())
            if me not in [str(item) for item in (live.get("argv") or [])]:
                problems.append(f"argv 裡沒有 planner 本體（{me}）⇒ 這支 job 跑的不是續航哨兵")
        return problems

    # 解除：**先斷持久化**（刪 plist），再拆記憶體裡那一份。
    # 🔴 兩條路，差別是「拆的人是不是自己」——這一格是本包最貴的實測換來的：
    # job 在自己的行程裡同步 `launchctl bootout` 自己，會被 launchd 當場終止，
    # `bootout` 那一行的 rc 從來寫不出來（合成實驗逐字重現）。而 `_sentinel_tick`
    # 的 disarm／escalate 分支在解除**之後**還要叫人、還要寫稽核痕跡 ⇒ 同步拆會讓
    # 「正常下班」與「需要人介入」這兩條路的痕跡一起消失，正好是這整套續航唯一
    # 有價值的那一格。故自我解除改成 detached 延後拆（實測：主行程把該寫的都寫完、
    # 正常退場，3 秒後子行程才 bootout，rc=0、`launchctl print` 隨即回 113）。
    # （本段由 docstring 改寫為註解：`count_loc` 計 docstring、不計註解，而本檔為了回補
    #   `list_jobs` 需要騰出額度——同檔頭第 2~4 行宣告的既定作法，一字未刪。）
    def disarm(self, task_name: str) -> int:
        if _unsafe_name(task_name):
            return 1
        plist = self.plist_path(task_name)
        try:
            plist.unlink()
        except OSError:
            pass  # 本來就不在＝已經斷了持久化，不是失敗
        target = f"{self.domain()}/{task_name}"
        if os.environ.get("XPC_SERVICE_NAME") == task_name:
            # 自我解除：延後拆掉記憶體裡那一份。`_defer` 現在等的是「父行程真的退場」，
            # 這正是本呼叫點需要的語意——見 `DEFER_WAIT_CAP_SECONDS`（R83-B 的 P0 根因）。
            self._defer(task_name, f'launchctl bootout "{target}"; echo "bootout rc=$?";')
            # 🔴 回 0 的**射程**：同步驗到的是「持久化已斷」（plist 不在了 ⇒ 下次登入不會
            # 回來）。記憶體裡那一份的拆除是延後的，它的 rc 由子行程寫進下面那支痕跡檔
            # ——「沒觸發＝這個檔不會長大」，仍然是可偵測的，不是靜默假設。
            return 0
        _run(["launchctl", "bootout", target])
        # rc 不是憑證（同 Windows 那一側的紀律，只是這裡的憑證是「查不到了」）。
        return 0 if self._readback(task_name) is None else 1

    # 現存工作名（前綴過濾）；`None`＝量不到，見檔頭〈回傳型別〉。
    # 🔴 原語刻意取 `launchctl list`（三欄 `PID\tStatus\tLabel`）而不是逐個 `print`：
    # `tools/install_mac_nightly.sh` 的 `launchctl list | awk '$3 == l'` 已經是這個形態，
    # 兩家至少在**用哪一個原語列舉**這件事上同源（劃界：那一家仍自持 legacy load/unload
    # 與自己的存在性判準，見檔頭〈射程〉第二點）。複審當回合實測 `launchctl list` 對現存
    # 哨兵**查得到**（不是假陰性），所以這一側的 `None` 只會來自 launchctl 真的失敗。
    def list_jobs(self, prefix: str) -> list[str] | None:
        rc, out = _run(["launchctl", "list"])
        return None if rc != 0 else _labels_with_prefix(out, prefix)

    def evidence_hint(self) -> str:
        return ("憑證是 `launchctl print` 的 rc（0＝在、"
                f"{LAUNCHCTL_ENOENT_RC}＝不存在）＋ descriptor 回讀；launchd **不報**"
                f"「下次幾點跑」：\n      launchctl list | grep {_task_prefix()}\n"
                f"      launchctl print {self.domain()}/<label>")

    def credential_line(self, moment: str) -> str:
        return ("✅ 排程憑證：" + moment
                + "\n   🔴 這**不是** NextRunTime：launchd 從不報「下次幾點跑」"
                  "（print 輸出裡 next／fire／due 皆不存在）。上面三件證明的是"
                  "「此刻存在、參數就是我要的那組、且已持久化」，**不**證明下次觸發時刻、"
                  "也**不**證明睡著的 Mac 會醒來（那要 `pmset repeat`，需 sudo）。")

    # ── 以下是 launchd 專屬細節，外面不必知道 ──────────────────────────────
    # job 要跑的 argv。與 Windows Action 同一件事：叫**planner 自己**回來。
    def _argv(self, planner, plan_path: str, task_name: str, tick: str) -> list[str]:
        return [sys.executable, str(Path(planner.__file__).resolve()), tick,
                "--plan", plan_path, "--task-name", task_name]

    # 產 plist → `plutil -lint` → 落地。lint 不過一律不留檔（不製造死排程）。
    def _write_plist(self, task_name: str, argv: list[str], interval: int,
                     calendar: dict | None = None) -> bool:
        planner = _planner()
        root = str(Path(planner.__file__).resolve().parents[1]) if planner else str(Path.cwd())
        # 🔴 R84／ZT-07：這支 log 收的是 job 自己的 stdout/stderr，也就是**這條鏈走過哪幾個
        # 分支**（`哨兵判定 patrol／probe／arm_reset／disarm：…` 那一行）。它原本住在
        # `$TMPDIR` ⇒ 重開機即消失，而複審實測到的病徵正是「交棒書引用的事件詞彙在痕跡檔
        # 裡一個都查不到」。改用 `endurance_env.trace_dir()`（家目錄；理由見該檔 ①）。
        log = endurance_env.trace_dir() / f"autosdd_sentinel_launchd_{task_name}.log"
        body = {
            "Label": task_name,
            "ProgramArguments": argv,
            "StartInterval": interval,
            # 🔴 `RunAtLoad` 刻意 False（與 `install_mac_nightly.sh` 相反，理由不同）：
            # 那一支是 nightly，錯過一輪要補跑；哨兵是巡邏，載入即跑只會讓武裝那一刻
            # 多一次無意義的 tick（而武裝本身就是剛剛才判過的）。
            "RunAtLoad": False,
            # cwd。R80 P0 的第一層在 mac 的對等：沒有它時 job 的 cwd 是 `/`，而續跑那一跑
            # 用 cwd 決定「本 session 允許的工作目錄」，也用它推逐字稿目錄 slug。
            "WorkingDirectory": root,
            # PATH：LaunchAgent 的預設 PATH 只有 `/usr/bin:/bin:/usr/sbin:/sbin`（實測），
            # 而探針要跑的 `claude` 通常裝在 `~/.local/bin` ⇒ 少了這一行，每一次真撞線後
            # 的探測都會是 `FileNotFoundError` → 分類成 LIMIT_UNKNOWN → fail-closed 永遠
            # 等下去。取武裝當下的 PATH（機器本地事實，不寫死任何一台機器的路徑）。
            "EnvironmentVariables": {"PATH": os.environ.get("PATH", "")},
            "StandardOutPath": str(log),
            "StandardErrorPath": str(log),
        }
        # 🔴 只在**真的有截止時刻**時才多這一個鍵（`_calendar_of` 判）。不寫死成永遠存在，
        # 是因為巡邏那一支的「下次時刻」本來就等於 `StartInterval` 的下一跳，多寫一個
        # calendar 只會讓每一次 tick 都與回讀不符 ⇒ 每 15 分鐘 bootout+bootstrap 一輪。
        if calendar:
            body["StartCalendarInterval"] = calendar
        path = self.plist_path(task_name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(plistlib.dumps(body))
        except OSError as exc:
            print(f"❌ plist 寫不進去：{path}（{exc}）", file=sys.stderr)
            return False
        rc, out = _run(["plutil", "-lint", str(path)])
        if rc != 0:
            try:
                path.unlink()
            except OSError:
                pass
            print(f"❌ 產出的 plist 未通過 plutil -lint：{out}", file=sys.stderr)
            return False
        return True

    # `launchctl print` 的**回讀值**；不存在（rc=113）或讀不出來一律 `None`。
    # 🔴 回讀的是 launchd 自己印的東西，不是我們剛寫進 plist 的那份。這個區別就是
    # 「憑證」與「我下了指令」的區別——後者正是 R59 事故的形狀。
    # （docstring → 註解，理由同上。）
    def _readback(self, task_name: str) -> dict | None:
        rc, out = _run(["launchctl", "print", f"{self.domain()}/{task_name}"])
        if rc != 0:
            return None
        found: dict = {"interval": None, "path": "", "argv": [], "state": "",
                       "calendar": {}}
        collecting = False
        in_cal = False
        depth = 0
        for line in out.splitlines():
            text = line.strip()
            if collecting:
                if text.startswith("}"):
                    collecting = False
                    depth -= 1
                else:
                    found["argv"].append(text)
                continue
            if text.startswith("arguments = {"):
                collecting = True
                depth += 1
                continue
            # 🔴 R83／QA 訂正：只認**最外層**（depth 1）的欄位。`launchctl print` 的輸出是
            # 巢狀的，而 `state = ` 在裡面出現**三次**：job 自己那一個在 depth 1，另外兩個
            # 在 `resource coalition`／`jetsam coalition` 子區塊（depth 2）裡。原本的
            # 「掃到就覆蓋」是最後一個贏 ⇒ 憑證回報的永遠是 coalition 的 `active`。
            # 本機實測（QA 複驗）：`launchctl list` 印 PID `-`、`print` 的 depth-1 逐字
            # `state = not running`，而憑證同一刻印 `state = active`。它不參與閘門判定，
            # 所以不會造成假武裝——但它**寫在憑證字串裡**，而憑證是取證規則要求貼出來的
            # 那一行；憑證裡混一句假話，比沒有那一欄更難看見（本 repo 對「有鎖在守假話」
            # 的判例同型）。第一次執行之前 coalition 區塊還不存在，所以這個缺陷**只在 job
            # 跑過至少一次之後才出現**——那正是它躲過武裝當下那次取證的原因。
            if depth == 1:
                if text.startswith("run interval = "):
                    found["interval"] = _first_int(text)
                elif text.startswith("path = "):
                    found["path"] = text.partition("=")[2].strip()
                elif text.startswith("state = "):
                    found["state"] = text.partition("=")[2].strip()
            # 🔴 calendar 的回讀刻意**不看 depth**：它住在 `event triggers` → `<label>.<n>`
            # → `descriptor` 裡（真機 depth 4），而那條路徑上有一個 launchd 自己編的數字
            # 鍵 ⇒ 用 depth／鍵名定位都會綁死在一個會漂移的形狀上。改以「看到
            # `stream = …calendarinterval` 之後、且鍵名在 `_CAL_KEYS` 白名單內」定位：
            # 白名單讓 `event channels` 區塊裡那些 `"port" => …` 之類的欄位不會被誤收。
            if text.startswith("stream = com.apple.launchd.calendarinterval"):
                in_cal = True
            key, _, val = text.partition(" => ")
            if in_cal and key.strip('"') in _CAL_KEYS and val.strip().isdigit():
                found["calendar"][key.strip('"')] = int(val.strip())
            depth += text.count("{") - text.count("}")
        return found

    # 憑證的字串形態。**刻意不含任何由我們推算出來的時刻**（見檔頭〈誠實劃界〉）。
    # `argv_verified` 是 R83／QA 訂正補上的：憑證裡的每一句話都必須對應**這一次真的做過
    # 的比對**。`arm()` 手上有原始請求，argv 是逐項比對過的；`verify_cli()` 沒有（它不
    # 知道當初那份任務書的路徑），所以那一句改寫成「未逐項比對」。預設 True 是因為只有
    # verify 這一條路做不到——把例外寫在例外的那個呼叫點，而不是讓兩邊都含糊其詞。
    # 🔴 R83-B 新增 calendar 那一欄。它與上面那句「不含推算出來的時刻」**不衝突**，差別正是
    # 這整套憑證紀律的核心：這個時刻是 `launchctl print` 的 `descriptor` 講出來的（launchd
    # 自報），不是我們拿間隔去推的。沒有 calendar 時這一欄明說「只有巡邏觸發」＋最壞死等
    # 秒數，而不是留白——留白會讓「排到了確切時刻」與「只是每 15 分鐘碰運氣」看起來一樣。
    # （本段由 docstring 改寫為註解，理由同 `_planner` 上方那一句。）
    def _credential(self, task_name: str, live: dict, *, argv_verified: bool = True) -> str:
        argv_piece = (f"argv 回讀 {len(live['argv'])} 項與請求逐項相符" if argv_verified else
                      f"argv 回讀 {len(live['argv'])} 項、planner 本體在列"
                      "〔未逐項比對：verify 這一側拿不到當初的任務書路徑〕")
        cal = live.get("calendar") or {}
        # 睡著不會醒那一句刻意**不**在這裡重複：`credential_line()` 已經帶著它，同一句話
        # 兩個家就是本 repo 反覆判過的形態（而這一支的輸出正是它的參數）。
        cal_piece = (f"StartCalendarInterval = {_cal_text(cal)}〔launchd 自報的 descriptor，"
                     "證明那個時刻真的排進去了〕" if cal else
                     f"**無** calendar ⇒ 只有巡邏觸發，最壞 {live['interval']} 秒後才有人動作")
        return (f"launchd {self.domain()}/{task_name}"
                f"｜launchctl print rc=0（不存在時是 {LAUNCHCTL_ENOENT_RC}）"
                f"｜run interval = {live['interval']} seconds〔launchd 回讀，與請求相符〕"
                f"｜{argv_piece}"
                f"｜plist = {live['path']}〔launchd 自報，證明已持久化〕"
                f"｜{cal_piece}"
                # 🔴 R84／SA-05：**這一格與 `credential_line()` 的那一句不是同一句話**
                # （上面那段刻意不重複的是「睡著不會醒」這個**通則**）。這一格是「**這台
                # 機器**現在的 pmset 讀數」＝一次量測，而量測不能住在通則那一支：通則對
                # 每台機器都成立，讀數每台不同。它也是這條鏈唯一會把電源姿態寫進續航痕跡
                # 檔的路（憑證字串會被 `append_log(..., credential=…)` 原封不動記下來）。
                f"｜{endurance_env.posture_note(_run)}"
                f"｜state = {live['state'] or '(未報)'}")

    # 延後重載那一條路專屬的憑證。**它刻意與 `_credential` 不同形**：那一支的每一句都是
    # launchd 的回讀，這一支手上的回讀還是舊參數 ⇒ 只能陳述「已落地、尚未載入」。
    # 這正是〈反事後諸葛〉那條規則的落點：貼得出來的是 plist 與痕跡檔，貼不出來的是
    # 「launchd 現在拿著新時刻」——所以後者一個字都不能寫。
    def _deferred_credential(self, task_name: str, cal: dict | None, trace: Path) -> str:
        return (f"launchd {self.domain()}/{task_name}｜plist 已落地並帶 "
                f"StartCalendarInterval = {_cal_text(cal or {})}（`plutil -lint` 通過）"
                "｜🔴 **launchd 此刻回讀的仍是舊參數，本欄不宣稱重載已完成**：本 tick 就跑在"
                "該 job 內，同步 bootout 會把自己殺掉（實測）⇒ 重載由脫離本 job 的子行程在本"
                f" tick 退場後執行，bootout／bootstrap／print 三個 rc 寫入 {trace}")

    # 延後、脫離本 job 的 launchctl 動作。**等的是「父行程真的退場」，不是一個猜出來的
    # 秒數**——原因與量測全文在 `DEFER_WAIT_CAP_SECONDS` 上方（R83-B 的 P0 根因）。
    # 回傳痕跡檔路徑：呼叫端要把它寫進憑證，好讓「沒觸發」是可偵測的而不是靜默假設。
    def _defer(self, task_name: str, cmds: str) -> Path:
        # 🔴 R84／ZT-03：`parent-gone waited=Ns` 是 R83 那個 P0（等父行程退場才 bootout）的
        # **唯一決定性憑證**，而它原本落在 `$TMPDIR` ⇒ 複審日實測整組檔已蒸發（`ls` 逐字
        # `no matches found`、`grep -rl parent-gone "$TMPDIR"` rc=1）⇒ 修好了與沒修好在事後
        # 外觀相同。持久居所與「為什麼它真的不會蒸發」的理由見 `endurance_env` ①。
        trace = endurance_env.trace_dir() / f"autosdd_sentinel_bootout_{task_name}.log"
        script = (f'p={os.getpid()}; n=0; '
                  f'while kill -0 $p 2>/dev/null && [ $n -lt {DEFER_WAIT_CAP_SECONDS} ]; '
                  f'do sleep 1; n=$((n+1)); done; '
                  f'{{ echo "parent-gone waited=${{n}}s at $(date -u +%Y-%m-%dT%H:%M:%SZ)"; '
                  f'{cmds} }} >> "{trace}" 2>&1')
        try:
            # `start_new_session=True`：脫離本 job 的行程群組。少了它，launchd 拆掉這支
            # job 時會把子行程一起收走，於是延後那一拆永遠不會發生（而且是靜默的）。
            subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except (OSError, ValueError) as exc:
            _append_trace(trace, {"event": "defer_failed", "error": str(exc)})
        return trace

    # 自我重載：`bootout` → `bootstrap`（唯一能讓 launchd 換掉觸發條件的動作組）。
    # `for` 重試三次的理由是誠實的：bootstrap 是這條路上**唯一**會讓哨兵整支消失的一步，
    # 而它失敗時沒有任何人在看（見 `arm()` 內那段〈誠實劃界〉）。三個 rc 都寫進痕跡檔。
    def _defer_relaunch(self, task_name: str, plist: str) -> Path:
        dom = self.domain()
        return self._defer(task_name, (
            f'launchctl bootout "{dom}/{task_name}"; echo "bootout rc=$?"; '
            f'i=1; while [ $i -le 3 ]; do launchctl bootstrap "{dom}" "{plist}" && break; '
            f'sleep 2; i=$((i+1)); done; echo "bootstrap rc=$? tries=$i"; '
            f'launchctl print "{dom}/{task_name}" >/dev/null; echo "print rc=$?";'))


# ─────────────────────────────────────────────────── 其餘平台：明說沒有載具
class NoCarrierBackend:
    """Linux 等：**明說做不到**，不假裝。武裝一律 rc=1，且訊息說得出替代方案。"""

    name = "none"
    credential_key = CRED_KEY_SCHTASKS

    # `at` 與 `at_expr` 都不使用（沒有載具＝沒有東西吃時刻）。簽名仍與另兩個後端逐字相同：
    # 「單平台判準不可無條件外推」在這裡外推的是**介面**——少一個參數，同一行呼叫在 Linux
    # 上就是 `TypeError`，而那是本 repo 判過的 DEF-101-766 形態（見 `list_jobs` 的沿革）。
    def arm(self, plan_path: str, task_name: str, at_expr: str, tick: str,
            at: datetime | None = None) -> tuple[int, str]:
        print(f"❌ 本平台（os.name={os.name!r}／sys.platform={sys.platform!r}）沒有已實作的"
              "排程載具：Windows 走 schtasks、macOS 走 launchd。Linux 請自行以 cron／"
              "systemd-timer 掛，本檔刻意不假裝支援它。", file=sys.stderr)
        return 1, ""

    def verify_cli(self, task_name: str) -> int:
        return self.arm("", task_name, "", "")[0]

    def disarm(self, task_name: str) -> int:
        return 0  # 沒有載具＝沒有東西要拆，這一格回 0 不是宣稱「拆成功了」

    # 🔴 這一格回 `[]`（＝**量到了**、真的沒有工作）而**不是** `None`（量不到）：沒有排程
    # 載具的平台上「排程器裡有幾支哨兵」是有確定答案的——零。回 `None` 會讓 Linux 上的 GC
    # 每次都 fail-loud 說「量不到」，而那是假的告警；把兩者混同的代價正好與 mac 那一側相反。
    def list_jobs(self, prefix: str) -> list[str] | None:
        return []

    def credential_line(self, moment: str) -> str:
        return f"（本平台沒有排程載具，不會有憑證）{moment}"

    def evidence_hint(self) -> str:
        return ("本平台**沒有排程載具** ⇒ 沒有任何取證指令。不要把「沒有東西可查」"
                "讀成「查過了、沒問題」。")


# ─────────────────────────────────────────────────────────── 唯一的提問點
# 🔴 **整個 repo 只有這個函式可以問「這台機器是什麼平台」來決定排程載具。** 兩個參數是
# 測試注入縫（同 `tools/lib/windows_skip_tags.py` 的既有形態）：平台這一軸的注入接縫只能
# 有一個，兩個家就會各自漂移。判 `os.name == "nt"` 而不是 `sys.platform.startswith("win")`
# ——與 repo 內其餘既有站點同一個判準，換一種寫法會讓「同一個問題兩種答案」變得可能。
def select(os_name: str | None = None, platform_name: str | None = None):
    """回這台機器該用的排程後端物件。"""
    name = os.name if os_name is None else os_name
    plat = sys.platform if platform_name is None else platform_name
    if name == "nt":
        return SchtasksBackend()
    if plat == "darwin":
        return LaunchdBackend()
    return NoCarrierBackend()


def has_carrier(os_name: str | None = None, platform_name: str | None = None) -> bool:
    """這台機器上到底有沒有排程載具。hook 端拿它取代六處 `os.name != "nt"` 早退。"""
    return select(os_name, platform_name).name != "none"


# `_unsafe_name`／`_labels_with_prefix` 一律從 `schedule_backend_calendar` import（見檔頭）：
# 純函式、無模組層可變狀態依賴，搬遷理由與範圍見該檔檔頭說明，本檔不重寫第二份邏輯。


# `_calendar_of`／`_first_int`／`_descriptor_problems`／`_append_trace` 一律從
# `schedule_backend_calendar` import（見檔頭）：純函式、無模組層可變狀態依賴，搬遷理由與
# 完整設計討論見該檔檔頭說明，本檔不重寫第二份邏輯。

# calendar descriptor 的人讀形態。走 `_CAL_KEYS` 的順序而不是 dict 的插入順序，這樣
# 「plist 寫進去的那一份」與「launchd 回讀的那一份」印出來可以逐字比對。
# 🔴 本函式**刻意留在原檔**（未隨其餘純函式搬遷）：它依賴 `_CAL_KEYS`，而 `_CAL_KEYS`
# 同時被 `LaunchdBackend._readback` 用裸名讀取——兩者搬走會讓兩檔互相 import，代價大於
# 省下的兩行（見 `schedule_backend_calendar.py` 檔頭說明）。
def _cal_text(cal: dict) -> str:
    return "-".join(f"{k}={cal[k]}" for k in _CAL_KEYS if k in cal) or "(無)"
