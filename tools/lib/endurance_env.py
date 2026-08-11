"""續航鏈的**機器事實**：痕跡放哪才不會蒸發、以及這台機器會不會睡著。"""
# 立案 WHY 全部寫在 `#` 註解裡（`count_loc` 計 docstring、不計註解；`tools/lib/` 的
# `guardrail_lib` tier 上限 400），與 `tools/lib/schedule_backend.py` 檔頭同一手法。
#
# 🔴 為什麼是**新的一支檔**，而不是寫進 `tools/lib/schedule_backend.py`
# ------------------------------------------------------------------
# 那一檔落地當回合的 `count_loc` 是 **395/400（餘裕 5）**，而本檔要落的兩件事合計 40 餘行。
# 本 repo 對這個處境的解法逐字寫在 `AutoClaude/tools/check_loc_budget.py` 的 ROOT-TOOLS
# `override_reason` 裡——「破線後不是調高預算，而是拆職責／抽共用模組（先例：
# `tools/lib/ci_liveness.py`）」。⇒ 本檔是**那條指引指定的動作**，不是第二個平台知識的家：
# `schedule_backend` 仍然是「這台機器用哪一個 OS 排程器」的唯一提問點，本檔一個
# `launchctl`／`schtasks`／`-ScheduledTask` 都不碰（`CarrierPrimitivesHaveOneHomeTest` 的
# 射程因此不變）。
#
# 🔴 兩件事**為什麼同住一支檔**（它們是同一個主題，不是兩個湊在一起的功能）
# --------------------------------------------------------------------
# 共同性質：**它們都是「這台機器」的事實，不在 repo 裡、不隨 clone 走。**
#   · 痕跡目錄：`$TMPDIR`（macOS 的 `/var/folders/**/T`）會被 OS 定期清、重開機必清 ⇒
#     憑證在事後查不到，而「查不到」與「沒發生」外觀相同。
#   · 電源姿態：`pmset` 的 `sleep` 值決定 launchd 到底會不會醒來跑。
# 兩者共同構成 R73 那條判例的同一個形態（把一台機器的偶然事實當成常數）：本輪 ZT-03／
# SA-05 兩筆的根都是「一件只在這台機器上成立、且不會被任何人看見的事」。
# ⇒ 因此本檔的規則只有一條：**現查、出聲、絕不寫成常數**。
#
# ══════════════════════════════════════════════════════════════════════════
# ① 持久痕跡目錄（ZT-03／ZT-07）
# ══════════════════════════════════════════════════════════════════════════
# 病（複審當回合實測，不是假想）：R83 把「等父行程退場才 bootout」這個 P0 的**唯一決定性
# 憑證**（`parent-gone waited=20s`）寫在 `$TMPDIR/autosdd_sentinel_bootout_*.log`。複審日
# 逐字實測 `ls "$TMPDIR"/autosdd_sentinel_bootout_*.log` → `no matches found`、
# `grep -rl "parent-gone" "$TMPDIR"` rc=1 ⇒ 那個 P0 的修復在 repo 與機器上**都**沒有可稽核
# 憑證，只剩「程式碼看起來對」。同一份實測還發現痕跡檔的事件詞彙與交棒書宣稱不符
# （只有 `sentinel_woken`／`aborted`／`armed`，`probed`／`gc_reaped` 皆為 0）。
#
# 🔴 為什麼 `~/.autosdd/traces` 真的不會蒸發（這句話必須有理由，不能只是換個目錄）
#   · macOS 的 `$TMPDIR` 是**每次開機重建**的 per-user `/var/folders/**/T`，且系統的
#     periodic 清理會刪掉一段時間未存取的檔 ⇒ 它的語意本來就是「可以隨時消失」。
#   · `~`（家目錄）不參與那兩種清理，登出／重開機後仍在 ⇒ 一次真撞線的痕跡留得到下一輪
#     複審的手上，這正是〈反事後諸葛取證規則〉要的「沒觸發＝可偵測」。
# 🔴 為什麼**不**寫進 repo（這一條同樣重要，而且是 ZT-03 明文要求的邊界）
#   痕跡是機器狀態。寫進版控就會變成「第二個假常數」——下一輪讀到的是**某一台機器某一天**
#   的值，而它看起來像 repo 的事實（R73 `Find-GitBash`、R81 `core.quotepath` 兩個判例同型）。
#   ⇒ 家目錄是刻意選的中間地帶：**比 `$TMPDIR` 持久、比 repo 不具權威**。
# 逃生口 `AUTOSDD_TRACE_DIR`：CI／沙箱測試指到自己的暫存目錄（單元測試不得在開發者家目錄
# 留下移動零件——「驗證載具自己就是副作用來源」是本 repo 判過的形態）。
#
# ══════════════════════════════════════════════════════════════════════════
# ② 電源姿態（SA-05；訴求 6e 的**誠實化**，不是達成）
# ══════════════════════════════════════════════════════════════════════════
# 🔴 **本節不宣稱 6e 已達成，交付的是「失效變成可偵測的」。** 睡著的 Mac 不會被 launchd
# 喚醒：Windows `WakeToRun` 的對等物住在 `pmset repeat`／需要 sudo、不在 plist 裡，而本
# 專案**刻意不碰 sudo、不改動掌舵者機器的電源行為**（掌舵者已否決該方案）。
# 病：這件事此前**只活在一行註解裡**（`schedule_backend` 檔頭〈誠實劃界〉），而武裝路徑對
# `sleep != 0` 完全靜默——憑證會照樣印出一份看起來完全正常的三件式，於是「這台機器撐得過
# 0~5h reset」與「它一闔蓋就整段不觸發」在痕跡上**外觀相同**。本檔把它變成一句會被說出來
# 的話：`pmset -g custom` 現查、非 0 就在 stderr 出聲，並經憑證字串落進續航痕跡檔。
#
# 🔴 鐵律三（「這在另一個平台是什麼值」）在本節的兩個落點：
#   · `pmset` 在 Windows／Linux **不存在** ⇒ 判準先問平台，**非 darwin 一律連 spawn 都不做**
#     （不是「跑了失敗再說」：那會在每一次武裝多一個必然失敗的子行程，而它的訊息會被讀成
#     「這台機器量不到電源姿態」＝一句對非 mac 機器毫無意義的話）。
#   · `runner` 是注入參數而不是自己 `import subprocess`：載具的唯一的家在
#     `schedule_backend._run`（那一支已帶 `encoding=`／`errors=`／`creationflags` 三件的
#     既有紀律），本檔一行 spawn 都不持有 ⇒ 也就不可能漏掉那三件中的任何一件。
# 🔴 `量不到 ≠ 不會睡`（本 repo 通篇那條紀律，見 `sentinel_lifecycle.reap_verdict` ②）：
#   `pmset` rc 非 0 時**必須**出聲，而不是靜默當成「沒問題」。
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

#: 痕跡目錄的逃生口（測試／CI 指到沙箱用）。人設得到、模型改不到自己那一份。
TRACE_DIR_ENV = "AUTOSDD_TRACE_DIR"

#: 家目錄下的持久痕跡居所（相對於 `Path.home()`）。
TRACE_HOME_PARTS = (".autosdd", "traces")

#: 睡眠這件事的**唯一一份**措辭。兩個消費者（武裝路徑的 stderr、憑證字串）都取這一份，
#: 因為「同一句話兩個家」是本 repo 反覆判過的形態。
SLEEP_CAVEAT = ("睡著的 Mac **不會**被 launchd 喚醒（本專案**已知邊界**，非可設定項；"
                "Windows `WakeToRun` 的對等物是 `pmset repeat`，需 sudo，本專案不碰）"
                "⇒ 額度 reset 落在闔蓋期間時，續航要等到開蓋才會有人動作")

#: `_sleep_rows` 對「這裡不是 macOS」的回值。刻意**不是** 0（那會與「量到了、沒問題」
#: 撞在一起），也不是 1（那是一個真的失敗 rc）。
NOT_APPLICABLE = -1


# 持久痕跡目錄；拿不到就退回 `$TMPDIR`（**退化，不是失敗**：痕跡留不下來絕不可反過來
# 變成續航本身的故障源，同 `quota_escalation._write` 與 `planner.append_log` 的既有紀律）。
# 兩層都檢查是刻意的：`mkdir` 成功不等於寫得進去（目錄可能早就存在且唯讀），而那種失敗
# 的表徵正好是「痕跡檔不會長大」——與「沒觸發」完全同形。
def trace_dir() -> Path:
    override = os.environ.get(TRACE_DIR_ENV, "").strip()
    want = Path(override) if override else Path.home().joinpath(*TRACE_HOME_PARTS)
    try:
        want.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(tempfile.gettempdir())
    return want if os.access(want, os.W_OK) else Path(tempfile.gettempdir())


# `pmset -g custom` 裡「睡眠設定不是 0」的那幾行。回 `(rc, 逐行原文)`。
# 🔴 只認**行首**為 `sleep `：同一份輸出裡還有 `displaysleep`／`disksleep`／`standby`，
# 而那三個都**不會**讓機器停止執行 launchd job（螢幕關掉不等於系統睡著）。本機實測
# `displaysleep 10` 與 `sleep 0` 同時存在 ⇒ 用子字串比對會把「不會睡的機器」判成會睡，
# 而假警報會讓下一個人把整條警告關掉（本 repo 對「擋到讓人無法工作的守衛」有判例）。
# 🔴 值解析不出來（不是數字）一律算**有問題**：未知 ⇒ 保守側，同 `reap_verdict` ② 的方向。
def _sleep_rows(runner, platform_name: str | None = None) -> tuple[int, list[str]]:
    if (platform_name or sys.platform) != "darwin":
        return NOT_APPLICABLE, []
    rc, out = runner(["pmset", "-g", "custom"])
    rows = [line.strip() for line in out.splitlines()
            if line.strip().startswith("sleep ") and _minutes(line) != 0]
    return rc, rows


def _minutes(row: str) -> int:
    parts = row.split()
    return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else -1


# 「這台機器撐不撐得過一次 reset」的**問題**；`""`＝沒有問題要說（含非 macOS）。
# 純函式（runner 與 platform 都可注入）⇒ 紅綠由合成注入自證，不依賴跑測試那台機器的設定。
def sleep_trouble(runner, platform_name: str | None = None) -> str:
    rc, rows = _sleep_rows(runner, platform_name)
    if rc == NOT_APPLICABLE:
        return ""
    if rc != 0:
        return (f"電源姿態**量不到**（`pmset -g custom` rc={rc}）⇒ 這**不是**「不會睡」。"
                + SLEEP_CAVEAT)
    if not rows:
        return ""
    return f"這台機器的睡眠是開著的（pmset 現查：{'；'.join(rows)}）⇒ " + SLEEP_CAVEAT


# 憑證字串裡那一格。**永不留白**：留白會讓「現查過、這台機器不會睡」與「根本沒查」看起來
# 一模一樣，而那正是本檔在治的病（同 `schedule_backend._credential` 對 calendar 那一欄
# 「沒有就明說沒有」的既有處置）。
def posture_note(runner, platform_name: str | None = None) -> str:
    trouble = sleep_trouble(runner, platform_name)
    if trouble:
        return "🔴 " + trouble
    if (platform_name or sys.platform) != "darwin":
        return "電源姿態：不適用（非 macOS，本欄不對其他平台發言）"
    return "電源姿態＝各電源段 `sleep` 皆為 0（pmset 現查；**這台機器的現況**，不是本專案的保證）"


# 武裝路徑的出聲點。回「說了什麼」（`""`＝沒說），讓呼叫端與測試都驗得到它真的說了話。
def warn_if_sleepy(runner, platform_name: str | None = None) -> str:
    trouble = sleep_trouble(runner, platform_name)
    if trouble:
        print("⚠️ " + trouble, file=sys.stderr)
    return trouble
