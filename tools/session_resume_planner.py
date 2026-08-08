#!/usr/bin/env python3
"""把根 CLAUDE.md 的〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉變成可執行的東西。"""
# 用法、立案 WHY 與各項限制全部在下方的 `#` 註解區——**內容一字未刪，只是換了住處**：
# `count_loc` 計 docstring 行、不計註解行，說明文字寫成註解是 repo 既定作法
# （`AutoClaude/tools/check_loc_budget.py` 的 TIER-WARN 指引逐字如此），而本檔的
# `guardrail_cli` 餘裕曾只剩 1 行（R79 四方複審實測）。門檻一格都沒有調高。
# 🔴 R79 續航補洞包**再壓一次**（同一個手法、同樣一字未刪）：本輪新增預防性哨兵，
# 而本檔餘裕只剩 31 行。下面十幾支函式的長 WHY 一律由 docstring 搬成緊鄰其上的 `#`
# 註解區，每支只留一行摘要 docstring。**沒有調高任何門檻，也沒有刪任何一句理由。**
# WHY
# ---
# 那一節寫得很完整——三段式水位、「可重啟點」四條件、任務書必含四項、重啟指令、
# 反「事後諸葛」取證規則——但它**全部是散文**，零機械物。而它自己記載的立案事故正是
# 「散文擋不住」的實例：R59 撞 Token 99% 時用 `CronCreate` 排了 45 分鐘後續跑並向使用者
# 宣稱「會自動繼續」，時間到完全沒觸發（`CronList` 對它的標記就是 `[session-only]`），
# 整段工作停擺而使用者以為在推進。
#
# 本檔提供那一節要求、但目前只能靠人記得的事：
#   · `--check`：把「現在幾 %」變成一個可以現查的數字（水位判定與
#     `.claude/hooks/context_budget_guard.py` **共用同一份實作**，見下方 import 的 WHY）；
#   · `--check-autocompact`：harness 自己那一半的姿態現查（**autocompact 被關掉時 rc=1**）；
#   · 產出「可重啟點任務書」骨架，四項欄位齊備、無法自動得知的部分留 `TODO:` 佔位；
#   · `--print-schtasks-command`：**只印不執行**的離線排程指令 ＋ 它的取證指令；
#   · `--register-schtasks` ／ `--verify-schtasks` ／ `--remove-schtasks`：真的註冊／
#     取證／移除（R79 新增，理由見下一段）。
#
# 🔴 「只印不執行」這條限制的依據已被實測推翻，故本輪解除（照實寫）
# ------------------------------------------------------------------
# R78 版的本段逐字寫「註冊 S4U 任務需要提權，session 內做不到也驗不了 ⇒ 本檔的處置是
# **只印指令**」。兩個前提在 R79 各被實測一次：
#   · 「session 內 spawn `claude` 會死結」（`DEF-101-089`，`CLAUDECODE=1`）——當回合
#     真跑，兩組對照皆 `rc=0`：繼承 `CLAUDECODE=1` 者 4.0s、剝掉者 3.6s。**沒有死結。**
#     🔴 射程：該實測用的是 `claude -p` 非互動 spawn。樹上另有一批用 wexpect pty 的測試
#     仍以舊前提 skip；那條路徑 R79 收斂輪**已複驗**（上一版此處寫「沒有複驗過」，已過期），
#     結論是**在巢狀 session 內仍掛住**：`PtyWrapper.start()` 三次都沒回返（180/180/45s）、
#     `claude.exe` 從未被啟動、剝除 `CLAUDECODE` 的對照組行為相同。
#     ⇒ 反證**只對 subprocess 這一路成立**，不遞移到 pty 路。
#     逐字量測見 docs/06_quality/CrossPlatform_R79_Debt_Audit.md 的 `## DEF-101-913` 節。
#   · 「註冊排程一定要提權」——`Register-ScheduledTask` 註冊**當前使用者**的工作不需要
#     提權（需要提權的是 S4U／`-User SYSTEM` 那種）。
# 於是「排程重啟」這條路第一次變成**可以在 session 內端到端驗證**的東西，而不是一段
# 只能相信的指令字串。取證規則本身一個字都沒放寬：`--register-schtasks` 會在同一段輸出
# 裡自動跑 `Get-ScheduledTask | Get-ScheduledTaskInfo` 並把 `NextRunTime` 印出來，
# **印不出來就回非零 rc**——「我下了指令」不等於「它真的排進去了」。
#
# 🔴 任務書裡的「已驗證什麼」一律是 `TODO:`，本檔不代填
# ------------------------------------------------------
# 它沒有辦法知道你驗過什麼。自動填一句「已通過」就是憑空製造一則沒有 tool_result 支撐的
# 宣稱——那正是本 repo 反覆記載的頭號缺陷形態。骨架的價值在於「欄位在那裡、空著很刺眼」，
# 不在於幫人省下寫字。
#
# 用法
# ----
#     python tools/session_resume_planner.py --check              # 只印水位，不寫檔
#     python tools/session_resume_planner.py                      # 產任務書骨架
#     python tools/session_resume_planner.py --out <path>
#     python tools/session_resume_planner.py --session-id <id>
#     python tools/session_resume_planner.py --transcript <a.jsonl>
#     python tools/session_resume_planner.py --print-schtasks-command
#
# 測試：tools/tests/test_context_budget_guard.py（與被它共用的 hook 同一支鎖）
#
# 🔴 職責目前是兩件事（水位量測＋任務書 vs 續航編排），本輪只做壓縮不做拆分。
# 拆法與連動點已具名寫在 docs/04_planning/R79_HANDOFF.md §4.3，別在這裡再寫第二份。
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
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
_SCHTASKS_SETTINGS = ("New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun "
                      "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries")

#: 🔴 R79 續修：與 `tools/install_windows_nightly.ps1` 的兩支既有工作對齊（該檔 R69
#: S-5 段）。S4U＝以該使用者身分跑但**不需登入、不存密碼**，工作落在 session 0 ⇒
#: 不會有視窗跳到使用者臉上。**但註冊 S4U 需要提權**（該檔已載明，本輪非提權真機
#: 複測：`Register-ScheduledTask ... -LogonType S4U` → 「存取被拒」，工作根本沒建），
#: 而哨兵的主要武裝路徑是 SessionStart hook＝一律非提權 ⇒ 只掛 S4U 會讓武裝整條斷掉。
#: 故採「S4U 優先、失敗回退預設 Principal」，**不彈視窗這件事改由載具保證**（見
#: `_no_console_python`）：兩層各自獨立成立，任一層在時都不彈。
_SCHTASKS_PRINCIPAL = ("New-ScheduledTaskPrincipal -UserId \"$env:USERDOMAIN\\$env:USERNAME\" "
                       "-LogonType S4U -RunLevel Limited")


# 優先序：`--transcript` 顯式路徑 → `--session-id` 對應的 `<id>.jsonl` →
# 專案目錄下**最後修改**的那一支（根 CLAUDE.md 對「當前 session」的既有判準）。
def resolve_transcript(
    session_id: str | None = None,
    transcript: str | None = None,
    repo_root: Path | None = None,
) -> Path | None:
    """定位本 session 的逐字稿；`None`＝找不到（呼叫端負責 fail-loud）。"""
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


# 🔴 R79：window 的證據來源改由 `guard.window_evidence()` 一次收齊（環境變數兩支＋
# settings 鏈的 `autoCompactWindow`／`model`＋逐字稿實跑 model 的交叉否決）。此前
# 本檔只餵得進 `AUTOSDD_CONTEXT_WINDOW` 一個來源 ⇒ 在 1M 機器上印出來的百分比是
# 真值的五倍，而它正是掌舵者拿來判「要不要 compact」的那個數字。
def measure(transcript: Path) -> dict:
    """水位量測（純資料）。判定一律走 hook 的實作，本檔不重寫一份判準。"""
    used, peak, model = guard.scan_transcript(transcript)
    window, source = guard.resolve_window(peak, **guard.window_evidence(model))
    return {
        "session_id": guard.session_id_of(transcript),
        "transcript": str(transcript),
        "used": used,
        "peak_used": peak,
        "model": model,
        "window": window,
        "window_source": source,
        "may_block": guard.may_block(source),
        "ratio": (used / window) if (used is not None and window > 0) else None,
        "tier": guard.tier_of(used, window) if used is not None else None,
    }


#: harness 的 autocompact 開關判定（`claude.exe` 二進位內逐字）：
#: `if(DISABLE_COMPACT)return!1; if(env.DISABLE_AUTO_COMPACT)return!1;
#:  return config("autoCompactEnabled", true)` ⇒ 缺席即開啟。
_AUTOCOMPACT_KILL_ENVS = ("DISABLE_AUTO_COMPACT", "DISABLE_COMPACT")
_GLOBAL_CONFIG_KEY = "autoCompactEnabled"


# 🔴 為何這一格必須是**現查**而不是文件裡的一句話：R78 的 hook docstring 逐字寫
# 「實查三處，這兩件事在這一層零機械物」，三處裡沒有一處是 Claude Code 自己——
# 於是我們花了一輪做偵測器，卻沒人去查那件事本來有沒有內建解。答案是有，而且
# **預設就開著**。這個函式讓「開著沒」變成每次都能重跑的量測，不是一次性的結論。
def autocompact_posture() -> dict:
    """harness 自己那一半：現在到底有沒有東西在自動 compact，window 是多少。"""
    kills = {name: os.environ.get(name) for name in _AUTOCOMPACT_KILL_ENVS
             if os.environ.get(name)}
    config_path = Path(os.path.expanduser("~")) / ".claude.json"
    configured: object = None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            configured = data.get(_GLOBAL_CONFIG_KEY)
    except (OSError, ValueError):
        configured = None
    enabled = not kills and configured is not False
    window_env = os.environ.get(guard.CC_WINDOW_ENV)
    window_setting = guard.settings_value(guard.CC_WINDOW_KEY)
    return {"enabled": enabled, "kill_envs": kills, "config_path": str(config_path),
            "configured": configured, "window_env": window_env,
            "window_setting": window_setting,
            "window": window_env or window_setting or "auto"}


def autocompact_report(posture: dict) -> str:
    state = "開啟" if posture["enabled"] else "🔴 關閉"
    seen = ("未設（＝採用預設 true）" if posture["configured"] is None
            else repr(posture["configured"]))
    lines = [
        f"harness autocompact   {state}", "  判定鏈（依 claude.exe 二進位內的順序）",
        f"    1. 環境變數 {list(_AUTOCOMPACT_KILL_ENVS)} 任一為真 ⇒ 關閉"
        f"　現況：{posture['kill_envs'] or '皆未設'}",
        f"    2. {posture['config_path']} 的 {_GLOBAL_CONFIG_KEY}　現況：{seen}",
        f"  window                {posture['window']}"
        f"（{guard.CC_WINDOW_ENV}={posture['window_env']!r}；"
        f"settings.{guard.CC_WINDOW_KEY}={posture['window_setting']!r}；"
        "兩者皆無時 CC 走 auto，且大於模型上限時由 CC 自己 capped）",
    ]
    if not posture["enabled"]:
        lines.append("  🔴 autocompact 被關掉了：撞到 context 上限時會直接失去對話，"
                     "而不是自動摘要。請在 /config 開回來，或拿掉上面那個環境變數。")
    return "\n".join(lines) + "\n"


def check_report(data: dict) -> str:
    """`--check` 的輸出。量不到時**明說量不到**，不印一個看起來像 0% 的數字。"""
    if data["used"] is None:
        return (f"❌ {data['transcript']}\n   掃不到任何帶 message.usage 的 assistant 記錄"
                " —— 「量不到」與「量到零」必須分得開，故不印百分比。"
                "逐字稿剛建立、或欄位格式已變更都會走到這裡。\n")
    tier = {None: "低於 75%", guard.TIER_WARN: "≥75%（建議 compact）",
            guard.TIER_HARD: "≥90%（停止開新戰場）"}[data["tier"]]
    return (
        f"session   {data['session_id']}\n逐字稿    {data['transcript']}\n"
        f"used      {data['used']:,}（input + cache_creation + cache_read；"
        f"output_tokens 不計）\npeak      {data['peak_used']:,}"
        "（本 session 歷來最大，window 下界推論的輸入）\n"
        f"model     {data['model'] or '（逐字稿裡讀不到）'}（window 交叉否決的依據）\n"
        f"window    {data['window']:,}〔{data['window_source']}〕\n"
        f"水位      {data['ratio']:.1%}  → {tier}\n"
        f"硬擋資格  {'有' if data['may_block'] else '無（分母是保守下界猜測 ⇒ 只出聲不擋）'}"
        f"（PreToolUse 阻斷模式的第三道放行條件）\n重啟指令  claude -r "
        f"{data['session_id']}\nharness   姿態現查：--check-autocompact"
        "（autocompact 才是真正在做 compact 的東西）\n"
    )


#: 排程工作預設名。
DEFAULT_TASK_NAME = "AutoSDD_SessionResume"

#: 醒來要走哪一支的旗標字面。兩支 tick 的差別只有一件事：**要不要花額度**。
RESUME_TICK = "--resume-tick"
SENTINEL_TICK = "--sentinel-tick"

# ─────────────────────────────── Auto Pilot（R79；掌舵者逐字裁決「現在開，但禁止 commit/push」）
# 🔴 `--allow-resume` 的預設在本輪由**關**翻成**開**。關閉的唯一理由（headless
# `claude -p` 到底跑不跑本 repo 的 hooks？若不跑，那個無人看管的回合會是全 repo 唯一
# 沒有護欄的地方）已被兩個探針實證推翻：
#   · SessionStart 會跑——探針前 `AutoSDD_*` 排程工作數 0，跑一次 `claude -p` 之後
#     變 1（SessionStart hook 自己武裝了哨兵）。
#   · PreToolUse 會跑——`claude -p ... --allowed-tools "Bash"` 的 Bash 呼叫在執行前
#     被 `.claude/hooks/block_bash_on_windows.py` 攔下，`echo` 一次都沒跑到。
# ⇒ 那一跑受禁 Bash／禁裸 cd／禁接管線讀 rc／context 阻斷等全部既有護欄保護。
#
# **怎麼關掉**（兩個出口，任一即可，都不需要改 code）：
#   ① 手動路徑：`--no-allow-resume`（`BooleanOptionalAction` 自動產生的否定旗標）。
#   ② 排程／hook 路徑：設環境變數 `AUTOSDD_RESUME_OFF=1`。這一個才是實務上有用的
#      那一個——哨兵是由 SessionStart hook 武裝的，沒有人會去改它的參數，但環境變數
#      是模型改不到、人改得到的那一層（同 `AUTOSDD_SENTINEL_OFF` 的形態）。
#      🔴 射程誠實劃界：它只影響**武裝當下**寫進狀態塊的 `allow_resume`。已經武裝出去
#      的排程讀的是任務書裡那一格，事後設這個變數不會改變它——要收回已武裝的那一支，
#      改任務書狀態塊的 `allow_resume` 或直接 `--remove-schtasks`。
#
# 掌舵者開這一格的**條件**是「禁止 commit／push」，而那個條件不靠本檔自律：
# `_run_resume()` spawn 時注入 `AUTOSDD_UNATTENDED=1`，由 PreToolUse 守衛
# `.claude/hooks/lint_powershell_command.py` 在那一跑的每一次 PowerShell 呼叫上硬擋
# （exit 2，且不吃行內豁免）。訊號名住在這裡是因為**注入端是這裡**；hook 那一側是
# 消費者，兩邊的字面由 `tools/tests/test_check_hooks_liveness.py` 的注入證明綁在一起。
UNATTENDED_ENV = "AUTOSDD_UNATTENDED"
RESUME_OFF_ENV = "AUTOSDD_RESUME_OFF"
#: 預設觸發時刻運算式。留成 PowerShell 運算式而不是寫死時間：使用者要改成 CLI 印的
#: reset 時間時，改的是同一個字串，印出來的與真的註冊出去的**不會分岔**。
#:
#: 🔴 R79：這個預設**只在 `--register-schtasks` 手動路徑上還算數，且它是猜的**。
#: `--arm-endurance` 一律不使用它——那條路的觸發時刻只能從逐字稿觀測（見
#: `guard.parse_reset_at` 的 WHY：全庫 7 個相異 reset 值沒有一個落在 5 小時格點上，
#: 本檔實測 `3:50am`／`12:20pm` 這種值就是反證）。把「當下機器的偶然事實寫成常數」
#: 是本 repo 反覆判過的形態（R73 同型）；此處保留它只是為了不動既有手動路徑的行為，
#: 並在下面這個常數旁把它的地位講清楚：**它不是 reset 時刻，是一個預設猜測**。
DEFAULT_AT_EXPR = "(Get-Date).AddHours(5)"

#: 探測重試上限。上界＝5 × 一次探測（本檔實測 31,847 tokens／$0.0176）≈ 16 萬 tokens，
#: 約等於主 session 醒來一次的 3/4。**這個數字是挑的、不是量出來的**，照實寫：它是
#: 「盡量救回來」與「別把剛回來的額度先吃掉一塊」之間的一個取捨點，要改就改這裡。
#: 有硬上限本身才是重點——沒有上限的重排在額度最緊的時候會持續燒。
MAX_PROBE_ATTEMPTS = 5

#: 觸發時刻相對 reset 時刻的安全邊際。reset 是滾動視窗，踩點觸發會在邊界上失敗。
RESET_SKEW_SECONDS = 120

#: 暫時性錯誤的重排間隔（不計入 `MAX_PROBE_ATTEMPTS`——壞的是別的東西，不是額度）。
TRANSIENT_RETRY_SECONDS = 300

#: 哨兵巡邏間隔。
#: 🔴 **R80 訂正本格的立案理由（結論不變、理由過期，照實寫）**。原文寫的是「全庫實測那
#: 一次真實撞線 08:44 撞、`resets 9am` ⇒ hit→reset 只有 16 分鐘，巡邏間隔必須小於它，
#: 才保證即使在**已觀測到的最短窗**裡也至少醒一次」。那句話的依據是**單一事件**；R80 以
#: 全庫 1,433 支逐字稿重量（`tools/probe/reset_window_distribution.py`，14 個相異 episode）
#: 得到最短窗是 **0.5 分鐘**、4/14 個 episode ≤16 分 ⇒ 900 秒**並不**小於最短觀測窗，
#: 原文在字面上已不成立，不能留著當現行說法。
#: 真正成立的性質：間隔決定「reset 之後最壞多久才會有人動作」。窗比間隔短時那一次走的是
#: `probe` 而非 `arm_reset` ⇒ **代價是一次探測，不是失效**。方向仍是「愈小愈好」，取捨與
#: 「為何不改成 50 分鐘」見 ADR-XPLAT-004 §2.7。
#: 為什麼可以取這麼密：每次巡邏是**讀檔，零 token**（`latest_limit_event` 掃逐字稿 ＋
#: 一次 `stat`），成本只有排程器喚醒與一次 python 啟動 ⇒ 這一側沒有需要權衡的東西。
#: 對照被否決的 `ScheduleWakeup` 接力：那個方案每醒一次要花一個模型回合（實測約 20.7 萬
#: tokens），所以它才被迫把間隔拉到 50 分鐘——成本結構不同，取值就不同。
SENTINEL_INTERVAL_SECONDS = 900

#: 自我解除門檻：逐字稿多久沒動就認定「工作已經結束了，哨兵可以下班」。
#: 取 6 小時的理由是它必須**大於一個完整的額度視窗**（5 小時）：等額度的那段期間逐字稿
#: 本來就不會更新，門檻若短於視窗，哨兵會在最需要它的時候把自己拆掉。加一小時邊際。
#: （實際上等待期間走不到這一格——那時有未處理事件，走的是前兩支。這個門檻守的是
#: 「人闔上筆電走了」那種真的結束，讓死哨兵不會永遠留在排程表裡當假訊號。）
SENTINEL_IDLE_SECONDS = 6 * 3600

#: 機器可讀狀態塊的字面 sentinel。刻意用「找 sentinel → `json.loads`」的子字串掃描，
#: **不解析 markdown**：任務書是給人看的，它的標題層級與表格排版會被人改，而狀態塊
#: 不該因為有人調了一個標題就讀不出來。一份檔、兩個面（人讀六節、機器讀這一塊），
#: 沒有第二個家——續航狀態與可重啟點任務書是同一個主題的兩半。
RELAY_BEGIN = "<!-- AUTOSDD-RELAY-BEGIN -->"
RELAY_END = "<!-- AUTOSDD-RELAY-END -->"

#: 狀態塊必填鍵。缺一即 fail-loud，不靜默補預設——補出來的預設會讓「狀態檔壞掉」
#: 長得跟「狀態正常」一模一樣，而這份檔是整條續航鏈唯一的地板。
RELAY_REQUIRED = ("schema", "session_id", "plan_path", "state", "kind",
                  "reset_at", "reset_source", "attempts", "max_attempts",
                  "allow_resume", "task_name")
RELAY_SCHEMA = "autosdd.resume/1"

#: 取證指令。查排程一律用 `Get-ScheduledTask`——`schtasks /query` 在本機實測會回空
#: ＝假陰性（根 CLAUDE.md〈查詢載具自己也會騙人〉）。
#: `{task}` 一律先過 `_ps_single_quote`，理由見該函式。
_EVIDENCE_TEMPLATE = (
    "Get-ScheduledTask -TaskName '{task}' | Get-ScheduledTaskInfo | "
    "Format-List TaskName,LastRunTime,LastTaskResult,NextRunTime"
)


# PowerShell 單引號字串的跳脫：內部的單引號要寫成兩個，這是**唯一**的跳脫方式
# （單引號字串不吃反引號跳脫）。
# 🔴 為何需要：任務書落點與工作名都是外部輸入。`%TEMP%` 會帶使用者名（`O'Brien` 這種
# 姓氏在 Windows 完全合法，NTFS 也允許路徑含 `'`），`--task-name` 更是使用者直接給的。
# 未跳脫時整段註冊腳本會在那個字元提前結束字串 ⇒ 輕則語法錯誤，重則後面的字被當成
# 指令跑掉（注入），而且失效發生在 `powershell.exe` 那一端、本行程只看得到一個 rc。
# 射程誠實劃界：只處理單引號。雙引號不必處理——Windows 檔名不允許 `"`，而本檔所有
# 內插點都落在單引號字串裡。**`at_expr` 刻意不跳脫**：它按設計就是一段 PowerShell
# 運算式（預設值 `(Get-Date).AddHours(5)` 就是），跳脫會讓它失效；它的來源是 `--at`
# （人手打的）或本檔自己用 `strftime` 產的字面時間，不是路徑那種外部字串。
def _ps_single_quote(text: str) -> str:
    return text.replace("'", "''")


# 🔴 印出來的與真的執行的必須是同一份字串（R78 立案理由：只有「印」這一條路時，
# 那段指令從未被任何人跑過，而「沒被跑過的指令」與「沒有指令」在可靠度上是同一件事）。
# R79 把它與續航路徑收成**同一個產生器**（`endurance_schtasks_script`）——此前這裡
# 另有一份把整份任務書內嵌進 `-Command` 當 prompt 的實作，那份有兩個獨立缺陷
# （任務書一長就撞命令列長度上限；骨架裡的 `TODO:` 佔位會被當成指令餵進去），
# 而且它與續航那份是同一件事的兩個家。
def schtasks_command(plan_path: str, task_name: str = DEFAULT_TASK_NAME,
                     at_expr: str = DEFAULT_AT_EXPR) -> str:
    """`--print-schtasks-command` 的輸出：註冊腳本 ＋ 它沒有被執行的聲明。"""
    return (
        "# 🔴 以下指令本次**沒有執行**，也沒有建立任何排程（本旗標只印）。\n#    要真的"
        "註冊並當場取證：改用 --register-schtasks（同一份字串，不是另一份）。\n"
        "# 🔴 執行完**必須**貼出最後那道取證指令的輸出才准宣稱「已排程」——\n"
        "#    「我下了指令」不等於「它真的排進去了」（反『事後諸葛』取證規則）。\n"
        f"# 🔴 `{at_expr}` 是**猜的**，不是 reset 時刻。要正確的觸發時刻請改用\n"
        "#    --arm-endurance（它從逐字稿原文觀測，見 ADR-XPLAT-004 §2.1）；"
        "還沒撞線就想掛著請用 --arm-sentinel。\n"
        + endurance_schtasks_script(plan_path, task_name, at_expr))


# 🔴 刻意指名 5.1 而不是 pwsh 7：schtasks 兩支 job 的 Action 跑的就是它，排程相關
# 的東西要在**生產引擎**上驗（根 CLAUDE.md 鐵律一 R77 訂正）。
# 走 `-File` 加暫存檔而不是 `-Command` 加長字串：內嵌引號在跨行程傳遞時會被吃掉
# （本 repo 已有兩筆實測判例），而排程指令裡的引號正好是意義所在。
# 🔴 非 Windows 一律 fail-loud 而不是讓它去撞 `FileNotFoundError`（鐵律三：寫任何
# 東西都要自問「這在另一個平台是什麼值」）。`schtasks` 整條路本來就只在 Windows
# 成立，mac/Linux 的對等物是 `launchd`／`cron`，那是另一件事，不在本檔射程內——
# 此處明說做不到，不假裝。
def run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    """把一段 PowerShell 丟給 **`powershell.exe`（5.1）** 跑。"""
    if os.name != "nt":
        return subprocess.CompletedProcess(
            args=["powershell.exe"], returncode=1, stdout="",
            stderr="❌ 本功能只在 Windows 成立（schtasks + powershell.exe）。"
                   f"當前 os.name={os.name!r}。mac/Linux 請改用 launchd／cron，"
                   "本檔刻意不假裝支援它。")
    holder = Path(tempfile.mkdtemp(prefix="autosdd_schtasks_")) / "run.ps1"
    # BOM ＋ CRLF：PS 5.1 對無 BOM 的 UTF-8 會以 ANSI codepage 誤讀（本 repo 的
    # check_ps1_encoding.py 立案理由），`.ps1` 行尾政策亦為 CRLF。
    holder.write_text(script, encoding="utf-8-sig", newline="\r\n")
    try:
        return subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(holder)],
            capture_output=True, encoding="utf-8", errors="replace",
            # 父行程若是 pythonw（排程 Action 的載具，見 endurance_schtasks_script）
            # 就沒有 console，此時開一個 console 子行程會**新配置一個視窗**＝彈窗又
            # 回來了。旗標讓這一層獨立成立，不依賴 LogonType。
            # 🔴 R80：改取 `guard.NO_WINDOW`（唯一真相源住 hook 那一側，理由同本檔頂端
            # 「依賴方向刻意是 tools → .claude/hooks」那段——hook 結構上不能 import，
            # 只能是被 import 的那一方）。它比原本的裸 CREATE_NO_WINDOW 多帶
            # CREATE_NEW_PROCESS_GROUP，實測不影響 rc／stdout／stderr。
            timeout=120, check=False, creationflags=guard.NO_WINDOW)
    finally:
        try:
            holder.unlink()
            holder.parent.rmdir()
        except OSError:
            pass


# 這個函式就是「反事後諸葛」那條規則的可執行形態：呼叫端拿不到非空字串就**不准**
# 宣稱已排程，而且必須回非零 rc。
def next_run_time(text: str) -> str:
    """從取證輸出裡挑出 `NextRunTime` 那一行的值；找不到回空字串。"""
    for line in text.splitlines():
        if line.strip().lower().startswith("nextruntime"):
            _, _, value = line.partition(":")
            return value.strip()
    return ""


# ─────────────────────────────────────────────── 續航協定（R79；ADR-XPLAT-004）
# 一句話：**額度用完 → 從錯誤訊息觀測 reset 時刻 → 排一次性 schtasks → 到點探測 →
# 通了就續跑、沒通就從新訊息重排**。等待期間零 token、終端可關、機器可睡。


def render_relay(state: dict) -> str:
    """狀態塊的字串形態（人讀的任務書與機器讀的狀態是同一份檔）。"""
    body = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    return f"{RELAY_BEGIN}\n```json\n{body}\n```\n{RELAY_END}\n"


# 🔴 兩者刻意都回 `None` 而**呼叫端必須靠 `has_relay()` 分辨**：「沒有續航武裝過」
# 與「武裝過但狀態壞了」是兩件事，後者要大聲，前者不必。這正是本 repo 反覆記載的
# 「量不到 ≠ 量到零」，只是換到狀態檔這一層。
def parse_relay(text: str) -> dict | None:
    """從任務書全文取回狀態塊；`None`＝沒有狀態塊 **或** 塊在但 JSON 壞掉。"""
    head = text.find(RELAY_BEGIN)
    tail = text.find(RELAY_END, head + 1) if head >= 0 else -1
    if head < 0 or tail < 0:
        return None
    body = text[head + len(RELAY_BEGIN):tail].strip()
    body = body.removeprefix("```json").removesuffix("```").strip()
    try:
        data = json.loads(body)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def has_relay(text: str) -> bool:
    """任務書裡有沒有狀態塊（不管它讀不讀得出來）。見 `parse_relay` 的 WHY。"""
    return RELAY_BEGIN in text and RELAY_END in text


def relay_problems(state: object) -> list[str]:
    """狀態塊的體檢清單（空＝健康）。純函式，紅綠由注入自證。"""
    if not isinstance(state, dict):
        return ["狀態塊不是物件"]
    problems = [f"缺必填鍵 `{key}`" for key in RELAY_REQUIRED if key not in state]
    if state.get("schema") != RELAY_SCHEMA:
        problems.append(f"schema 不是 {RELAY_SCHEMA}（讀到 {state.get('schema')!r}）")
    # 🔴 取證守衛：`next_run_time` 是空的就**不准**宣稱排程成立。這是「反事後諸葛」
    # 那條規則在狀態檔這一層的形態——rc 不是憑證，`NextRunTime` 這個**值**才是
    # （`Get-ScheduledTask` 對不存在的工作回 rc=0，只讀 rc 會是假綠）。
    live = state.get("state") in ("armed", "waiting")
    if live and not str(state.get("next_run_time") or "").strip():
        problems.append("state 已是 armed/waiting，但 next_run_time 是空的"
                        "（＝沒有憑證卻宣稱已排程）")
    # 🔴 猜出來的 reset 不得用來武裝：排程會成立、NextRunTime 也拿得到，取證規則照樣
    # 綠——但它醒在錯的時間。「憑證存在、但憑證不回答那個問題」是最難看見的一種假綠。
    # `operator` 是哨兵那一路：它的觸發時刻是巡邏間隔（人選的常數），**不是**在宣稱
    # 任何 reset 時刻，所以它不在「猜 reset」這個禁令的射程內。
    if live and state.get("reset_source") not in (
            "transcript-verbatim", "probe-verbatim", "operator"):
        problems.append(f"reset_source={state.get('reset_source')!r} 不是觀測值 ⇒ "
                        "不准用來武裝（猜出來的時刻會讓它醒在錯的時間）")
    return problems


# **「觸發了但失敗」與「根本沒觸發」必須分得開**——後者的形狀正是 R59 那次事故
# （宣稱了、沒發生、沒有人知道）。
# 🔴 鍵一定是**任務書路徑**，不是 session id。被叫起來的那一跑要在讀任何東西之前
# 就先留下「我被叫起來了」——而那個時間點它手上唯一有的就是 `--plan`（session id
# 住在還沒讀的狀態塊裡）。本輪實測過拿 session id 當鍵的後果：開場那一行寫進
# `..._r79plan.jsonl`、其餘寫進 `..._r79probe.jsonl`，同一條稽核痕跡有兩個家，
# 而「早期失敗」那一行剛好落在沒有人會去看的那一個檔裡＝這道機制守的東西自己漏掉。
def endurance_log_path(plan: Path) -> Path:
    """每一次醒來的稽核痕跡（哨兵巡邏與續航探測共用同一支檔）。"""
    return (Path(tempfile.gettempdir())
            / f"autosdd_resume_log_{guard.session_id_of(plan)}.jsonl")


def append_log(path: Path, event: str, **fields: object) -> None:
    """append 一行 JSONL。寫不進去不得升級為失敗——最壞情況是這一跑沒有留下痕跡。"""
    # 🔴 `at`／`event` 兩個保留鍵**刻意寫在 `**fields` 之後**，讓呼叫端蓋不掉它們。
    # R79 補洞包的端到端實測抓到的真缺陷：呼叫端寫 `append_log(..., at=decision["at"])`
    # 時，那個 kwarg 直接覆寫了記錄自己的時間戳 ⇒ 痕跡上寫著一個**未來**的時刻
    # （實測：事件真的發生在 21:24，記錄寫成 23:26）。而「這件事何時發生」正是整條
    # 稽核痕跡唯一在回答的問題——讓「觸發了」與「沒觸發」分得開的那一格。
    # 同一次修復把呼叫端的參數改名為 `fire_at`（是「下次何時響」，不是「現在幾點」）。
    record = {**fields, "event": event,
              "at": datetime.now(UTC).astimezone().isoformat(timespec="seconds")}
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


# 🔴 探針必須真的花額度才有鑑別力（[[驗證載具要能觸發 bug]]）：不吃額度的探針對
# 「額度回來了沒」這個問題零判別力。成本以 `--model haiku` ＋ 空 cwd 壓到最低——
# 本檔實測一次 31,847 tokens／$0.0176，而主 session 醒來一次是它的六倍以上
# （成本正比於自己的 context，且會隨 session 長大；探針是常數）。
# 🔴 這也是**哨兵為什麼不用探測就能知道「撞了沒」**的對照組：探測回答的是「額度回來
# 了沒」，那件事只能問伺服器；而「撞了沒」寫在逐字稿裡，讀檔即可、成本為零。
# 失敗方向刻意 fail-closed：rc 非零而又分類不出來時回 `LIMIT_UNKNOWN` 且 `open=False`
# ——「不確定額度回來了沒」時當成沒回來，只會多等一輪；反過來會在沒額度時去跑續跑，
# 白燒一次主 session 的成本。
def probe_quota(claude: str = "claude", model: str = "haiku") -> dict:
    """花**一次**最便宜的呼叫問「額度回來了沒」。回 `{open, kind, rc, text}`。"""
    workdir = Path(tempfile.mkdtemp(prefix="autosdd_probe_"))
    try:
        proc = subprocess.run(
            [claude, "-p", "ok", "--model", model, "--output-format", "json"],
            cwd=str(workdir), capture_output=True, encoding="utf-8",
            # 🔴 R80：這一站此前漏帶旗標。它由哨兵那一跑（pythonw ⇒ 無 console）呼叫，
            # 而 `claude.exe` 是 console 子系統應用 ⇒ 每一次真撞線後的探測都會彈一個視窗。
            errors="replace", timeout=180, check=False, creationflags=guard.NO_WINDOW)
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        rc = proc.returncode
    except (OSError, subprocess.SubprocessError) as exc:
        return {"open": False, "kind": guard.LIMIT_UNKNOWN, "rc": 127, "text": str(exc)}
    finally:
        try:
            workdir.rmdir()
        except OSError:
            pass
    kind = guard.classify_limit(text)
    is_open = rc == 0 and kind == guard.LIMIT_UNKNOWN
    return {"open": is_open, "kind": kind, "rc": rc, "text": text[:2000]}


# 回 `{action, reason, at, state}`，`action ∈ resume|rearm|stop`。
def tick_plan(state: dict, verdict: dict, now: datetime) -> dict:
    """探測完之後**該做什麼**的唯一判定。純函式——整條續航鏈的大腦，必須可注入。"""
    kind, attempts = verdict["kind"], int(state.get("attempts") or 0)
    if verdict["open"]:
        return {"action": "resume", "reason": "探針通過＝額度已恢復",
                "at": None, "state": "resumed"}
    if kind == guard.LIMIT_SPEND:
        # 🔴 這一格是本協定最貴的誤判的解藥：月度支出上限等再久都不會回來。
        return {"action": "stop", "at": None, "state": "abandoned",
                "reason": "月度支出上限——等待無效，只有人去提額才會回來"}
    if kind == guard.LIMIT_TRANSIENT:
        # 壞的是別的東西，不計入 attempts（否則幾次 502 就把重試預算吃光）。
        return {"action": "rearm", "reason": "伺服器暫時性錯誤，短退避後再探",
                "at": now + timedelta(seconds=TRANSIENT_RETRY_SECONDS),
                "state": "waiting"}
    if attempts + 1 >= int(state.get("max_attempts") or MAX_PROBE_ATTEMPTS):
        return {"action": "stop", "at": None, "state": "abandoned",
                "reason": f"已探測 {attempts + 1} 次仍未恢復，達上限 ⇒ 硬停並通知人"}
    fresh = guard.parse_reset_at(verdict["text"], now)
    if fresh is None:
        # 🔴 認不出新的 reset 時刻就**明說**，不准退回固定 5 小時（見 parse_reset_at）。
        return {"action": "stop", "at": None, "state": "abandoned",
                "reason": "額度仍未恢復，且探針輸出裡解不出新的 reset 時刻 ⇒ "
                          "拒絕用猜的時間重排（猜出來的排程會醒在錯的時間）"}
    return {"action": "rearm", "reason": f"額度仍未恢復，改依新觀測的 reset {fresh}",
            "at": fresh + timedelta(seconds=RESET_SKEW_SECONDS), "state": "waiting"}


# ─────────────────────────── 預防性哨兵（R79 補洞包；ADR-XPLAT-004 §2.6）
# 🔴 本段補的是 `--arm-endurance` 的**觸發層**缺口，不是它的判定層。
# `--arm-endurance` 要求「先觀測到 reset 時刻」，而額度耗盡的那一刻是 16 秒內全掛、
# 沒有任何人還在跑指令 ⇒ 它只在「已撞線且 reset 未到」那個很窄的窗裡有用，而那個窗
# 恰好是沒有人會去用它的時候。實測逐字：撞線後補跑它得到 rc=1「reset 已經過去 ⇒ 沒有
# 東西需要等」——判斷是對的，但那正說明它到得太晚。
# 🔴 讓預防性武裝變得可能的關鍵洞察：**探測是為了知道「額度回來了沒」；要知道
# 「額度撞了沒」根本不用探測——讀逐字稿就行，成本是零。** 於是哨兵可以在還沒撞線時
# 就掛上去，平時每次醒來只讀檔（零 token），只有真的撞線那一次才花一次探測。
# 額度耗盡在 Claude Code 的 hook 體系裡**沒有任何觸發點**（它是 API 層的失敗，不是
# 工具呼叫失敗，PreToolUse／PostToolUse 都不會被叫到）⇒ 預防性武裝是唯一的路。
#
# 🔴 **R80 訂正本段規格**：原規格把 `handled_through` 的立案理由掛在一個**恆真且與額度
# 無關**的推論上。原句只保存在 ADR-XPLAT-004 §2.6（那裡它是 P0 的根因原件），本處刻意
# **不複製**它——本 repo 判過「訂正註記逐字引述假話＝製造新假話」。
# 🔴 而本段自己就是那條紀律的又一個實例：R80 二審（NEW-ARCH-R80B-06）實測本註記的上一版
# 寫著「故不複述它」，緊接四行卻把整句抄了出來 ⇒ **自稱不複述本身變成一句假話，而被複述
# 的那句仍留在樹裡**，下一個 grep 到它的人會以為那是現行規格。
# 它為什麼不成立：武裝是一個純本機 subprocess、零 API 呼叫，額度早就見底時它照樣跑得動、
# 照樣把撞線標成已處理（實證：撞線後兩分鐘就被標成已解決，此後每次巡邏都合法地判 patrol，
# 哨兵整晚失明）。
# 那正是本輪 P0 的根因，而修法已經落地在別處：**「已處理」現在由 `guard.
# unhandled_limit_event()` 以「事件之後有沒有一則真的成功 API 回應」這個復原證據判定**
# （`type=assistant` ＋ 真 model ＋ 有 `message.usage`，讀檔即可、成本為零）。
# ⇒ `handled_through` 這個參數**已降為稽核欄位**：`_sentinel_tick` 傳空字串，
# production 走不到「被它擋下」那條分支。它保留在簽名裡只為了①狀態塊的可讀性、
# ②讓舊狀態塊仍能被讀。誰要是把它改回「唯一的已處理判準」，就是把 P0 裝回去。
# 誠實劃界：這個參數若真的被傳非空值，比較是 ISO-8601-Z 字串的字典序（harness 的格式
# 固定，故等價於時序）；兩邊都是空字串時走「未處理」那一側，交由復原證據那一層裁決。
#
# 🔴 R80 時區框架：`now` 的時區就是解讀 `resets 9am` 的框架（訊息自報時區時以它優先，
# 見 `guard.declared_zone`）。本函式**不讀機器的本地時區**——讀了就會讓同一份語料在
# 容器（UTC）與本機（UTC+8）給出相反的答案，那是 act 實跑抓到的兩個紅。
def sentinel_decide(event: dict | None, handled_through: object,
                    idle_seconds: float, now: datetime) -> dict:
    """哨兵醒來後的四分支判定。純函式——預防鏈的大腦，每一支都要能單獨注入。"""
    if event and str(event.get("timestamp") or "") > str(handled_through or ""):
        if event["kind"] == guard.LIMIT_SPEND:
            return {"action": "escalate", "at": None,
                    "reason": "月度支出上限——等待無效，只有人去 claude.ai 提額才會回來"}
        reset_at = guard.parse_reset_at(
            event["text"], local_time(event["timestamp"], now.tzinfo) or now)
        if reset_at is None:
            return {"action": "escalate", "at": None,
                    "reason": "偵測到撞線但訊息裡解不出 reset 時刻 ⇒ 拒絕用猜的重排"
                              f"（猜出來的會醒在錯的時間）。逐字：{event['text'][:80]}"}
        at = reset_at + timedelta(seconds=RESET_SKEW_SECONDS)
        if at > now:
            return {"action": "arm_reset", "at": at, "reset_at": reset_at,
                    "reset_source": "transcript-verbatim",
                    "reason": f"偵測到未處理的撞線；觀測 reset={reset_at} 尚未到 ⇒ "
                              "重排到那個時刻（本次零 token）"}
        return {"action": "probe", "at": None,
                "reason": f"偵測到未處理的撞線；觀測 reset={reset_at} 已過 ⇒ "
                          "花一次探測確認額度回來了沒"}
    if idle_seconds < SENTINEL_IDLE_SECONDS:
        return {"action": "patrol",
                "at": now + timedelta(seconds=SENTINEL_INTERVAL_SECONDS),
                "reason": f"無未處理撞線；逐字稿 {idle_seconds:.0f}s 前仍有更新 ⇒ "
                          "session 還活著，續巡（本次零 token）"}
    return {"action": "disarm", "at": None,
            "reason": f"無未處理撞線，且逐字稿已靜止 {idle_seconds:.0f}s "
                      f"（≥{SENTINEL_IDLE_SECONDS}s）⇒ 工作已結束，自我解除"}


# 哨兵是 **per-session** 的：共用一個工作名會讓新 session 靜默蓋掉舊 session 還在等的
# 那一支。顯式給了 `--task-name` 就聽人的（測試與人工操作都要能指定）。
#
# 🔴 R79 已知設計問題（**本輪不修**，交棒下一輪）：per-session ＋ SessionStart **無條件**
# 武裝＝每一次 headless `claude -p` 呼叫都會生出一支自己的哨兵（每個 headless session
# 有自己的 session id）。本輪實測：跑兩次探針之後機器上有 3 支 `AutoSDD_Sentinel_*`。
# 6 小時的 `SENTINEL_IDLE_SECONDS` 會讓它們自己下班，所以不會無限長；但 Auto Pilot
# 開啟後短時間內的堆積是真的——續跑那一跑本身也是一個 headless session，它也會武裝
# 一支。可能的處置（都需要先決定語意，故不在本輪射程）：同一個 repo 只留一支（以
# repo 路徑而非 session id 命名，武裝時 `-Force` 覆蓋）；或 SessionStart 先數一次現有
# 哨兵、超過 N 支就不再武裝；或對 headless session（`claude -p`）整個不武裝——但最後
# 這條會把「續跑那一跑自己撞線」的續航能力一起關掉，是取捨不是純改善。
def sentinel_task_name(session_id: str, given: str = DEFAULT_TASK_NAME) -> str:
    """哨兵的 schtasks 工作名。"""
    return given if given != DEFAULT_TASK_NAME else f"AutoSDD_Sentinel_{session_id}"


# 🔴 R79 修的缺陷：舊寫法把**整份任務書內容**內嵌進 `-Command` 當 prompt。三個問題
# ——任務書一長就撞命令列長度上限；骨架裡的 `TODO:` 佔位會被當成指令餵給無人看管的
# 那一跑；而且它把「要不要續跑」這個決策交給了一個沒有判準的模型回合。改成叫回本檔
# 之後，醒來的第一段是**確定性的 Python**：先留痕、再判定、再動作。
# `tick` 選的是醒來要走哪一支：`--resume-tick`＝已撞線在等額度（醒來必探測）；
# `--sentinel-tick`＝預防性巡邏（醒來只讀檔，零 token）。兩者共用同一份註冊腳本。
def runner_action_argument(plan_path: str, task_name: str, tick: str = RESUME_TICK) -> str:
    """schtasks Action 的參數字串：叫**本檔**回來，不是叫一個模型回合。"""
    return (f'"{Path(__file__).resolve()}" {tick} '
            f'--plan "{plan_path}" --task-name "{task_name}"')


# 🔴 「任務書不存在就中止」寫在 **Action 自己**裡，不是寫在任務書裡——任務書不存在時
# 沒有人讀得到寫在它裡面的規則（`%TEMP%` 有清理策略，5 小時跨度真的會發生）。
def endurance_schtasks_script(plan_path: str, task_name: str, at_expr: str,
                              tick: str = RESUME_TICK) -> str:
    """續航／哨兵排程的註冊腳本。與手動路徑共用取證段，但 Action 指向 runner。"""
    # 🔴 R79 續修的**本體**（掌舵者當場回報：哨兵每 15 分鐘彈一個 console 視窗）。
    # 根因不在「醒來做了什麼」，而在**載具**：`sys.executable` 是 console 子系統的
    # `python.exe`，在 Interactive 登入類型下 Windows 必定替它開一個視窗。既有兩支
    # nightly 工作不彈，是因為它們是 S4U（跑在 session 0）——而 S4U 註冊需提權、
    # 哨兵的武裝路徑（SessionStart hook）拿不到（見 `_SCHTASKS_PRINCIPAL`）⇒ 只調
    # LogonType 治不了非提權那條路。`pythonw.exe` 是同一個直譯器的 GUI 子系統版本，
    # **不配置 console**，故不論 LogonType 為何都不彈。
    # 代價已查證：`sys.stdout`／`sys.stderr` 為 `None`。CPython 的 `print()` 對
    # `stdout is None` 是靜默 no-op（不拋例外），`_stdio_utf8` 亦已明文處理該情境；
    # 而本檔的稽核痕跡一律 `append_log()` 寫檔、不靠 stdout ⇒ 可觀測性零損失。
    # 🔴 R80：載具解析收斂到 `guard.quiet_python()`（唯一真相源住 hook 那一側，同本檔
    # 頂端「依賴方向刻意是 tools → .claude/hooks」那段）。此前這裡自己算一份 pythonw，
    # 與 hook 內兩處 spawn 各算各的＝同一份知識三個家。
    python = _ps_single_quote(guard.quiet_python())
    plan_q = _ps_single_quote(plan_path)
    task_q = _ps_single_quote(task_name)
    argument = _ps_single_quote(runner_action_argument(plan_path, task_name, tick))
    return (
        "$ErrorActionPreference = 'Stop'\n"
        f"if (-not (Test-Path '{plan_q}')) {{ throw '任務書不存在，拒絕註冊：{plan_q}' }}\n"
        # 🔴 R80 P0 的第一層。`New-ScheduledTaskAction` 不給 `-WorkingDirectory` 時，
        # 排程起的行程 cwd ＝ `C:\\Windows\\System32`（實測：本機哨兵的 Action 那一格是
        # **空字串**）。後果不是「路徑不方便」而是**續跑那一跑結構上做不了任何事**：
        # 它起的 `claude -p -r` 把「本 session 允許的工作目錄」鎖在 system32，於是連
        # 任務書都讀不到（實測逐字：Read → 權限未授予；Get-Content → 「本 session 允許
        # 的工作目錄只有 C:\\WINDOWS\\system32」）。五段流程全部觸發成功，卻在最後一步
        # 空轉——正是本 repo 反覆判過的「機制蓋好沒接電」的下一個變體：接了電但踩空。
        # 值刻意由 `_REPO_ROOT`（＝`Path(__file__).resolve().parents[1]`）推導而**不寫死**：
        # 把一台機器的 checkout 路徑寫成常數是 DEF-101-778 的判例，`tools/tests/
        # test_platform_neutral_paths.py` 會逐行掃出來判紅。Action 的 Arguments 帶的是
        # 本檔的絕對路徑，所以這個推導在排程行程裡同樣成立（端到端已實證）。
        f"$action  = New-ScheduledTaskAction -Execute '{python}' "
        f"-Argument '{argument}' -WorkingDirectory '{_ps_single_quote(str(_REPO_ROOT))}'\n"
        f"$trigger = New-ScheduledTaskTrigger -Once -At {at_expr}\n"
        f"$settings = {_SCHTASKS_SETTINGS}\n"
        f"$principal = {_SCHTASKS_PRINCIPAL}\n"
        f"$common = @{{TaskName='{task_q}'; Action=$action; Trigger=$trigger; "
        "Settings=$settings; Force=$true}\n"
        "try { Register-ScheduledTask @common -Principal $principal -EA Stop | Out-Null }\n"
        "catch { Register-ScheduledTask @common | Out-Null }\n"
        "\n"
        f"{_EVIDENCE_TEMPLATE.format(task=task_q)}\n"
    )


# 🔴 R79 Auto Pilot：`--register-schtasks` 那條手動路徑此前在 `main()` 裡另存一份
# **逐字相同**的九行（跑腳本 → 取 `NextRunTime` → 拿不到就 rc=1）。同一份知識兩個家、
# 改一個另一個不會紅，是本 repo 反覆判過的形態；收成一處順帶把本檔騰出 LOC 餘裕。
def _register_at_expr(plan_path: str, task: str, at_expr: str, tick: str) -> tuple[int, str]:
    """註冊排程並當場取證。回 `(rc, next_run_time)`；拿不到憑證一律 rc=1。"""
    proc = run_powershell(endurance_schtasks_script(plan_path, task, at_expr, tick))
    print(proc.stdout, end="")
    moment = next_run_time(proc.stdout)
    if proc.returncode != 0 or not moment:
        print(f"❌ 排程沒有成立（rc={proc.returncode}，NextRunTime 取不到）⇒ "
              "本工具**不會**說它已排程。\n" + (proc.stderr or ""), file=sys.stderr)
        return 1, ""
    return 0, moment


# 🔴 R80：`at.astimezone()` 不是裝飾。`strftime` 會把 offset **無聲丟掉**，而
# `New-ScheduledTaskTrigger -At '<字串>'` 一律以**機器本地時區**解讀它 ⇒ `at` 若帶的是
# 別的時區（本輪的 reset 時刻現在可能來自訊息自報的時區），排程就會醒在錯的時刻，
# 而 `NextRunTime` 照樣拿得到＝取證規則全綠的假綠。先換算到本機框架再丟 offset，
# 才是「丟掉的那個資訊本來就已經被用掉了」。
def register_endurance(state: dict, at: datetime, tick: str = RESUME_TICK) -> tuple[int, str]:
    """註冊／重排並取證。回 `(rc, next_run_time)`；拿不到憑證一律 rc=1。"""
    return _register_at_expr(state["plan_path"], state["task_name"],
                             f"'{at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}'", tick)


def write_relay(plan: Path, state: dict) -> None:
    """把狀態塊寫回任務書（有就替換、沒有就附加）。任務書仍是同一支檔。"""
    text = plan.read_text(encoding="utf-8")
    block = render_relay(state)
    if has_relay(text):
        head, tail = text.find(RELAY_BEGIN), text.find(RELAY_END) + len(RELAY_END)
        text = text[:head] + block.rstrip("\n") + text[tail:]
    else:
        text = text.rstrip("\n") + "\n\n## 6. 續航狀態（機器讀；人讀上面六節）\n\n" + block
    plan.write_text(text, encoding="utf-8", newline="\n")


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

## 5. 排程

🔴 **這一節不是真相源**：這份骨架產生時本工具還沒建立任何排程，而排程之後的實況
一律以底下〈續航狀態〉那個機器可讀區塊為準（沒有那個區塊＝沒有武裝過續航）。
把狀態抄成散文會讓同一份檔對同一件事有兩種說法，那正是本 repo 反覆判過的形態。

- 額度耗盡要自動續航：`python tools/session_resume_planner.py --arm-endurance`
  （從逐字稿觀測 reset 時刻、註冊一次性 schtasks、當場取證）。
- 只想拿指令自己跑：`--print-schtasks-command`。
- `CronCreate` 不是離線排程（`CronList` 標 `[session-only]`）；`ScheduleWakeup` 也不是
  （它不寫磁碟、沒有可查詢的登錄、沒有 NextRunTime ⇒ **沒有任何憑證**，事後無從得知
  它排到了沒有——那正是 R59 事故的形狀）。離線排程只有 `schtasks` 一條路。
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
    parser.add_argument("--check-autocompact", action="store_true", dest="check_autocompact",
                        help="只印 harness 的 autocompact 姿態；**被關掉時 rc=1**"
                             "（不需要逐字稿，可單獨跑）")
    parser.add_argument("--print-schtasks-command", action="store_true", dest="print_schtasks",
                        help="只印離線排程指令與取證指令，**不執行、不註冊**"
                             "（會一併產生任務書：排程起來的那一跑要吃它）")
    parser.add_argument("--register-schtasks", action="store_true", dest="register_schtasks",
                        help="真的註冊排程並當場取證；拿不到 NextRunTime 一律 rc=1")
    parser.add_argument("--verify-schtasks", action="store_true", dest="verify_schtasks",
                        help="只取證既有排程（Get-ScheduledTask + NextRunTime）")
    parser.add_argument("--remove-schtasks", action="store_true", dest="remove_schtasks",
                        help="移除排程並驗證它真的不見了")
    parser.add_argument("--task-name", default=DEFAULT_TASK_NAME,
                        help=f"排程工作名稱（預設 {DEFAULT_TASK_NAME}）")
    parser.add_argument("--at", default=DEFAULT_AT_EXPR,
                        help=f"觸發時刻（PowerShell 運算式／時間字串；預設 {DEFAULT_AT_EXPR}）")
    parser.add_argument("--arm-endurance", action="store_true", dest="arm_endurance",
                        help="額度耗盡續航武裝：從逐字稿觀測 reset 時刻 → 寫任務書＋狀態塊 → "
                             "註冊一次性 schtasks → 取證。月度支出上限一律拒絕武裝（等待無效）")
    parser.add_argument("--probe-quota", action="store_true", dest="probe_quota",
                        help="花一次最便宜的呼叫問「額度回來了沒」；額度通時 rc=0、耗盡時 rc=1")
    parser.add_argument("--arm-sentinel", action="store_true", dest="arm_sentinel",
                        help="**預防性**武裝：還沒撞線就掛一支哨兵。不需要已觀測的 reset 時刻，"
                             "到點只讀逐字稿（零 token），偵測到撞線才自動轉成續航排程。"
                             "這是 --arm-endurance 的觸發層")
    parser.add_argument("--sentinel-tick", action="store_true", dest="sentinel_tick",
                        help="**哨兵被叫起來的那一支**：留痕 → 讀檔判定 → 續巡／重排到 reset／"
                             "探測／自我解除。不該由人手動跑（除了驗證它）")
    parser.add_argument("--resume-tick", action="store_true", dest="resume_tick",
                        help="**schtasks 叫起來的那一支**：留痕 → 探測 → 續跑或重排。"
                             "不該由人手動跑（除了驗證它）")
    parser.add_argument("--plan", help="--resume-tick／--sentinel-tick 要讀的任務書絕對路徑")
    parser.add_argument("--allow-resume", action=argparse.BooleanOptionalAction,
                        dest="allow_resume", default=os.environ.get(RESUME_OFF_ENV) is None,
                        help="允許醒來那一跑真的執行 `claude -p -r` 續跑工作。**R79 起預設開啟**"
                             f"（掌舵者拍板）。要關：`--no-allow-resume` 或設 {RESUME_OFF_ENV}=1"
                             f"（排程／hook 路徑唯一有效的出口）。無人看管 ⇒ {UNATTENDED_ENV} 配 "
                             "PreToolUse 守衛硬擋 commit／push")
    parser.add_argument("--probe-command", default="claude",
                        help="探針用的 claude 執行檔（測試注入用）")
    return parser


def _schtasks_verify(task_name: str) -> int:
    proc = run_powershell(_EVIDENCE_TEMPLATE.format(task=_ps_single_quote(task_name)) + "\n")
    print(proc.stdout, end="")
    moment = next_run_time(proc.stdout)
    if proc.returncode != 0 or not moment:
        print(f"❌ 取不到 `{task_name}` 的 NextRunTime（rc={proc.returncode}）"
              "⇒ 不准宣稱它已排程。\n" + (proc.stderr or ""), file=sys.stderr)
        return 1
    print(f"✅ NextRunTime = {moment}　←（這一行就是憑證，宣稱『已排程』時必須連它一起貼）")
    return 0


def _schtasks_remove(task_name: str) -> int:
    task_q = _ps_single_quote(task_name)
    proc = run_powershell(
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


# 必須換到「解讀 `resets 9am` 的那個框架」：那個字串是牆上時刻（括號裡就寫著
# `Asia/Taipei`），拿 UTC 的「現在」去解「下一個 9am」會整整差掉時差。
# 🔴 R80：`tz` 由參數傳入，**不再無條件讀機器的本地時區**。act 在 Linux 容器實跑抓到
# 的兩個紅（`arm_reset` != `probe`）根因就在這裡：錨點取機器時區、`now` 由呼叫端給，
# 同一份語料因此有**兩個框架**，容器（UTC）與本機（UTC+8）判定翻面。`tz=None` 沿用
# `datetime.astimezone()` 的既有語意（機器本地），所以既有呼叫端行為一字未變。
def local_time(stamp: str, tz: object = None) -> datetime | None:
    """逐字稿的 ISO-8601（UTC，`Z` 結尾）→ 指定時區（預設機器本地）；壞值回 `None`。"""
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(tz)
    except (TypeError, ValueError):
        return None


# 狀態塊的共同骨架。三條路（續航武裝／哨兵武裝／哨兵重排）共用同一份鍵集合，
# 少一個鍵就會被 `relay_problems()` 判紅——那個判準只有在鍵真的來自同一個家時才對得上。
def _base_state(session_id: str, plan: Path, args, kind: str, task: str) -> dict:
    """武裝時寫進任務書的狀態塊骨架（各路再各自覆寫自己那幾格）。"""
    return {"schema": RELAY_SCHEMA, "session_id": session_id, "plan_path": str(plan),
            "state": "armed", "kind": kind, "reset_at": "", "reset_source": "operator",
            "attempts": 0, "max_attempts": MAX_PROBE_ATTEMPTS, "task_name": task,
            "allow_resume": bool(args.allow_resume), "next_run_time": "",
            "log_path": str(endurance_log_path(plan))}


# 武裝／重排的共同尾段。三條路走同一份，是因為「拿不到 `NextRunTime` 卻仍把 state
# 寫成 armed」這種假綠只要有一條路漏掉就等於沒有防；集中一處才有辦法一次證完。
def _register_and_record(plan: Path, state: dict, at: datetime, tick: str) -> tuple[int, str]:
    """寫狀態 → 註冊排程 → 取憑證 → 把憑證（或 abandoned）寫回狀態。"""
    write_relay(plan, state)
    rc, moment = register_endurance(state, at, tick)
    state["next_run_time"] = moment
    if rc != 0:
        state["state"] = "abandoned"
    write_relay(plan, state)
    return rc, moment


def _arm_endurance(args, transcript: Path, plan: Path) -> int:
    """武裝續航：觀測 → 分類 → 算觸發時刻 → 註冊 → 取證。任何一步取不到憑證即 rc=1。"""
    event = guard.latest_limit_event(transcript)
    if event is None:
        print("❌ 逐字稿裡沒有任何額度／錯誤事件（`type=assistant` ＋ "
              f"`model={guard.SYNTHETIC_MODEL}`）⇒ 沒有東西可以等，不武裝。\n   續航是"
              "**對已經發生的撞線**做的處置，不是預先掛著的定時器——要預防性的請用 "
              "--arm-sentinel（它不需要已觀測的 reset 時刻）。", file=sys.stderr)
        return 1
    kind = event["kind"]
    if kind == guard.LIMIT_SPEND:
        print("🔴 撞到的是**月度支出上限**，不是 session 額度——等待無效，排程等於白燒探測。"
              f"\n   逐字：{event['text']}\n   請去 claude.ai 提額；提完再重跑本指令。\n",
              file=sys.stderr)
        return 1
    if kind != guard.LIMIT_SESSION:
        print(f"❌ 事件分類為 {kind}（非 session 額度），不武裝（fail-closed）。\n"
              f"   逐字：{event['text']}\n", file=sys.stderr)
        return 1
    anchor = local_time(event["timestamp"]) or datetime.now().astimezone()
    reset_at = guard.parse_reset_at(event["text"], anchor)
    if reset_at is None:
        print("❌ 訊息裡解不出 reset 時刻 ⇒ **拒絕退回「假設 5 小時」**。\n"
              f"   逐字：{event['text']}\n   reset 是滾動視窗（全庫 7 個相異值沒有一個"
              "落在 5 小時格點上），猜出來的時刻會讓排程醒在錯的時間，"
              "而取證規則照樣是綠的。\n", file=sys.stderr)
        return 1
    now = datetime.now().astimezone()
    if reset_at + timedelta(seconds=RESET_SKEW_SECONDS) <= now:
        print(f"ℹ️  觀測到的 reset 時刻 {reset_at} 已經過去（現在 {now}）⇒ 額度應該早就"
              "回來了，沒有東西需要等。要確認就跑 --probe-quota。", file=sys.stderr)
        return 1
    state = _base_state(guard.session_id_of(transcript), plan, args, kind,
                        args.task_name)
    state.update(reset_at=reset_at.isoformat(), reset_source="transcript-verbatim",
                 observed_at=event["timestamp"], observed_text=event["text"],
                 transcript=str(transcript))
    rc, moment = _register_and_record(
        plan, state, reset_at + timedelta(seconds=RESET_SKEW_SECONDS), RESUME_TICK)
    if rc != 0:
        return 1
    append_log(endurance_log_path(plan), "armed", reset_at=reset_at.isoformat(),
               next_run_time=moment, allow_resume=bool(args.allow_resume))
    print(f"✅ NextRunTime = {moment}　←（憑證；宣稱『已排程』時必須連它一起貼）")
    print(f"   觀測到的 reset：{reset_at}（來源：逐字稿原文，非推算）")
    print(f"   任務書＋狀態塊：{plan}")
    print(f"   稽核痕跡：{state['log_path']}（沒觸發＝這個檔不會長大，是可偵測的）")
    print("   ℹ️  醒來那一跑會自動續跑（Auto Pilot 預設開；禁 commit／push，由 "
          f"{UNATTENDED_ENV} 配 PreToolUse 守衛硬擋）。" if args.allow_resume else
          f"   ℹ️  已關閉自動續跑（--no-allow-resume／{RESUME_OFF_ENV}）⇒ 醒來只探測＋留痕。")
    return 0


# 真的開一個無人看管的模型回合（R79 起**預設開啟**，見上方 Auto Pilot 區塊的 WHY 與
# 兩個關閉出口）。抽成函式是因為兩條路都會走到它：`--resume-tick` 的 resume 分支、
# 以及哨兵探測到額度回來的那一支。同一份知識不留兩個家——**注入無人看管訊號的站點
# 也因此只有一個**，這正是它抽出來的價值：漏注入是靜默的（護欄不會出聲說自己沒被
# 掛上），而只有一個站點的東西才有辦法一次證完。
def _run_resume(args, state: dict, log: Path) -> int:
    """額度回來且已授權時，真的把工作續跑起來（帶無人看管訊號）。"""
    prompt = (f"讀 {state['plan_path']}，照它第 3 節做。"
              "🔴 第一件事是重驗，不採信該檔任何「已通過」宣稱。遵守第 4 節〈禁止事項〉。"
              "🔴 本回合無人看管，禁止 commit／push"
              "（已由 PreToolUse 守衛硬擋，不是請求）——改動留在工作樹讓人回來收。")
    # 🔴 R80 P0 的第二層（兩層都補才算修好，缺任一層續跑那一跑都做不了事）。
    # · `cwd=_REPO_ROOT`：沒有它時 cwd 繼承自排程行程＝system32，而 Claude Code 用 cwd
    #   決定「本 session 允許的工作目錄」⇒ 續跑碰不到 repo 一個檔。**排程 Action 的
    #   `-WorkingDirectory` 不能取代它**：那一層管的是 planner 自己的 cwd，這一層管的是
    #   被 spawn 的 `claude` 的 cwd；今天兩層剛好同值，但只補上層等於把正確性寄託在
    #   「planner 從不改自己的 cwd」這個沒有人在守的假設上。cwd 同時也是 `-r` 找得到
    #   session 的條件（逐字稿住 `~/.claude/projects/<由 cwd 推出的 slug>/`）。
    # · `--add-dir`：任務書落在 `%TEMP%`（刻意不進 repo——repo 內不得有可寫暫存目錄，
    #   且未追蹤檔會漂進好幾道以 `git status`／`git ls-files` 為掃描面的鎖）。cwd 改成
    #   repo 根之後 `%TEMP%` 仍在允許目錄之外，所以必須顯式把它加進去。旗標實查
    #   `claude --help`：`--add-dir <directories...>  Additional directories to allow
    #   tool access to`（非憑印象）。傳**任務書所在目錄**而不是整個 `%TEMP%` 的父層，
    #   射程剛好一個目錄。
    #   🔴 **`prompt` 必須排在 `--add-dir` 前面**，這是 R80 端到端實測踩到的真缺陷：
    #   該旗標的值是**變長的**（`<directories...>`），放在 prompt 前面時它會把 prompt
    #   一起吃掉當成目錄 ⇒ `claude` 認為這一跑沒有 prompt，rc=1、stdout 全空、逐字
    #   `Error: No deferred tool marker found in the resumed session...Provide a prompt
    #   to continue the conversation.`。修前修後各實測一次（prompt 在後 rc=1／prompt
    #   在前 rc=0），順序由 `ConsoleFreeSpawnTest` 的姊妹鎖釘住。
    # · `creationflags`：見 `guard.NO_WINDOW`。少了它，無人看管的續跑會彈一個視窗。
    proc = subprocess.run(
        [args.probe_command, "-p", "-r", state["session_id"], prompt,
         "--add-dir", str(Path(state["plan_path"]).parent)],
        capture_output=True, encoding="utf-8", errors="replace", timeout=3600,
        check=False, creationflags=guard.NO_WINDOW, cwd=str(_REPO_ROOT),
        env={**os.environ, UNATTENDED_ENV: "1"})
    # 🔴 `err=` 是 R80 補的：此前只記 stdout，而上面那個 argv 缺陷的表現正好是
    # 「rc=1、stdout 全空」⇒ 稽核痕跡看得到「失敗了」卻看不到**為什麼**，我是靠手工
    # 重跑一次才找出原因的。無人看管的那一跑沒有人在看 stderr，它只有這一個家。
    append_log(log, "resumed", rc=proc.returncode, err=(proc.stderr or "")[:300],
               out=(proc.stdout or "")[:400])
    print((proc.stdout or "")[:2000])
    return proc.returncode


def _resume_tick(args) -> int:
    """**schtasks 叫起來的那一支**。第一件事就是留痕——讓「觸發了但失敗」與「沒觸發」分得開。"""
    plan = Path(args.plan or "unknown")
    log = endurance_log_path(plan)
    append_log(log, "woken", plan=str(plan))
    if not plan.is_file():
        append_log(log, "aborted", why="任務書不存在")
        print(f"❌ 任務書不存在：{plan}（地板沒了，無法續跑）", file=sys.stderr)
        return 1
    text = plan.read_text(encoding="utf-8")
    state = parse_relay(text)
    if state is None:
        why = "狀態塊在但 JSON 壞掉" if has_relay(text) else "任務書裡沒有狀態塊"
        append_log(log, "aborted", why=why)
        print(f"❌ {why} ⇒ 拒絕動作。", file=sys.stderr)
        return 1
    log = Path(state.get("log_path") or log)
    problems = relay_problems(state)
    if problems:
        append_log(log, "aborted", why="；".join(problems))
        print("❌ 狀態塊體檢不過：\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1

    verdict = probe_quota(args.probe_command)
    append_log(log, "probed", rc=verdict["rc"], kind=verdict["kind"],
               quota_open=verdict["open"])
    decision = tick_plan(state, verdict, datetime.now().astimezone())
    print(f"探針 rc={verdict['rc']} kind={verdict['kind']} open={verdict['open']}")
    print(f"判定 {decision['action']}：{decision['reason']}")

    if decision["action"] == "stop":
        state["state"] = decision["state"]
        state["next_run_time"] = ""
        write_relay(plan, state)
        # 終態要把排程收掉。`-Once` 觸發器不會再響，但留著一支死工作會讓下一個人
        # 用 `Get-ScheduledTask` 查現況時看到一支「還在」的續航工作——而它其實已經
        # 放棄了。本 repo 對「查詢載具給出過期事實」有判例，這裡不留那個坑。
        append_log(log, "stopped", why=decision["reason"],
                   unregister_rc=_schtasks_remove(state["task_name"]))
        print(f"🔴 {decision['reason']}", file=sys.stderr)
        return 1
    if decision["action"] == "rearm":
        state["state"] = decision["state"]
        if verdict["kind"] != guard.LIMIT_TRANSIENT:
            state["attempts"] = int(state.get("attempts") or 0) + 1
            state["reset_source"] = "probe-verbatim"
            state["reset_at"] = (decision["at"]
                                 - timedelta(seconds=RESET_SKEW_SECONDS)).isoformat()
        rc, moment = _register_and_record(plan, state, decision["at"], RESUME_TICK)
        append_log(log, "rearmed", fire_at=decision["at"].isoformat(),
                   next_run_time=moment, attempts=state["attempts"])
        return rc
    # action == resume
    state["state"] = "resumed"
    state["next_run_time"] = ""
    write_relay(plan, state)
    _schtasks_remove(state["task_name"])  # 同上：終態不留死工作
    if not state.get("allow_resume"):
        append_log(log, "quota_back_no_resume")
        print("✅ 額度已恢復。狀態塊記著 allow_resume=false（帶了 --no-allow-resume／"
              f"{RESUME_OFF_ENV}，或它是 R79 之前武裝的）⇒ 人回來跑："
              f"claude -r {state['session_id']}")
        return 0
    return _run_resume(args, state, log)


# 預防性武裝。與 `_arm_endurance` 的差別是**它不需要任何已觀測的 reset 時刻**：
# 觸發時刻是巡邏間隔（operator 選的常數），而不是一個被猜出來的 reset——所以
# `reset_source` 誠實記成 `operator`、`reset_at` 留空。這一點很重要：`relay_problems()`
# 禁止用猜出來的 reset 武裝，而哨兵**根本沒有在宣稱**任何 reset 時刻。
def _arm_sentinel(args, transcript: Path, plan: Path) -> int:
    """哨兵武裝：註冊一支一次性 schtasks，到點只讀檔（零 token）。"""
    session_id = guard.session_id_of(transcript)
    # 🔴 R80：`handled_through` 改記「全域最後一次成功 API 回應」，不再記「最後一筆撞線」。
    # 舊寫法的立案理由是「我此刻跑得動武裝指令 ⇒ 額度是通的 ⇒ 既有撞線必然都已解決」——
    # 那句話**是假的**（武裝零 API 呼叫），而它正是哨兵整晚失明的主因。本欄現在只作稽核，
    # 真正的「已處理」判定在 `guard.unhandled_limit_event` 內以復原證據做。
    state = _base_state(session_id, plan, args, "sentinel",
                        sentinel_task_name(session_id, args.task_name))
    state.update(transcript=str(transcript), handled_through=guard.latest_success_at(
        guard.session_transcripts(transcript)) if transcript.is_file() else "")
    at = datetime.now().astimezone() + timedelta(seconds=SENTINEL_INTERVAL_SECONDS)
    rc, moment = _register_and_record(plan, state, at, SENTINEL_TICK)
    append_log(endurance_log_path(plan), "sentinel_armed" if rc == 0 else "arm_failed",
               task=state["task_name"], next_run_time=moment,
               handled_through=state["handled_through"])
    if rc != 0:
        return 1
    print(f"✅ NextRunTime = {moment}　←（憑證；宣稱『已排程』時必須連它一起貼）\n"
          f"   哨兵 {state['task_name']}：每 {SENTINEL_INTERVAL_SECONDS}s 醒一次，"
          "平時只讀逐字稿＝零 token；只有真的撞線那一次才花一次探測。\n"
          f"   已處理到：{state['handled_through'] or '（本 session 尚無撞線事件）'}\n"
          f"   任務書＋狀態塊：{plan}\n"
          f"   稽核痕跡：{state['log_path']}（沒觸發＝這個檔不會長大，是可偵測的）")
    return 0


# 哨兵醒來。**第一件事是留痕**（與 `_resume_tick` 同一條紀律：讓「觸發了但早期失敗」
# 與「根本沒觸發」分得開），第二件事才是讀狀態。
def _sentinel_tick(args) -> int:
    """schtasks 叫起來的巡邏那一支：留痕 → 讀檔判定 → 四分支。"""
    plan = Path(args.plan or "unknown")
    log = endurance_log_path(plan)
    append_log(log, "sentinel_woken", plan=str(plan))
    state = parse_relay(plan.read_text(encoding="utf-8")) if plan.is_file() else None
    problems = relay_problems(state) if state is not None else ["任務書／狀態塊讀不出來"]
    if problems:
        append_log(log, "sentinel_aborted", why="；".join(problems))
        print("❌ 哨兵拒絕動作：\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    log = Path(state.get("log_path") or log)
    transcript = Path(str(state.get("transcript") or ""))
    now = datetime.now().astimezone()
    # 逐字稿不見了＝哨兵瞎了。刻意 fail-loud＋自我解除，而不是靜默當成「工作結束」
    # ——後者會讓一個瞎掉的哨兵與一個正常下班的哨兵留下完全相同的痕跡。
    # 🔴 R80 P0 修復點（哨兵整晚失明的那一格）。三處都換掉，理由全文在
    # `context_budget_guard.unhandled_limit_event` 上方那段：
    #  · 事件來源 `latest_limit_event` → `unhandled_limit_event`：前者只看**主逐字稿的
    #    最後一筆**，本次事故裡那一筆是 `quota_spend`，把更早、仍未解決的 `quota_session`
    #    整個蓋掉；後者掃主檔＋subagent，並以「全域復原證據」判未處理（實測假陽性 0.0%）。
    #  · `handled_through` 傳 `""`：那個欄位的立案理由（「我跑得動武裝指令 ⇒ 額度是通的」）
    #    **是假的**——武裝是零 API 呼叫的本機 subprocess。實證它把撞線後兩分鐘就標成已解決。
    #    「已處理」現在由復原證據判定，不再由一個推論判定。欄位保留只作稽核用。
    #  · 閒置秒數改用**全 session 最新** mtime：扇出時主逐字稿可能很久沒被寫，只看它會把
    #    正在狂跑的 session 誤判成閒置，而閒置到門檻就會自我解除。
    decision = sentinel_decide(
        guard.unhandled_limit_event(transcript), "",
        now.timestamp() - guard.newest_activity_at(guard.session_transcripts(transcript)),
        now) if transcript.is_file() else {
        "action": "escalate", "at": None,
        "reason": f"狀態塊指的逐字稿不存在（{transcript}）⇒ 哨兵已瞎，自我解除並叫人"}
    append_log(log, "sentinel_decided", action=decision["action"],
               reason=decision["reason"])
    print(f"哨兵判定 {decision['action']}：{decision['reason']}")
    if decision["action"] == "probe":
        # 🔴 交棒給既有的續航機器，不另寫一份：`--resume-tick` 已經有探測、`tick_plan`
        # 判定、重排／硬停、終態收掉排程的完整實作。它重排時掛的是 `--resume-tick`，
        # 那正確——一旦進入「等額度」模式，醒來就該探測而不是巡邏。
        return _resume_tick(args)
    if decision["action"] in ("disarm", "escalate"):
        state["state"] = "disarmed" if decision["action"] == "disarm" else "abandoned"
        state["next_run_time"] = ""
        write_relay(plan, state)
        rc = _schtasks_remove(state["task_name"])
        append_log(log, "sentinel_" + decision["action"], unregister_rc=rc,
                   why=decision["reason"])
        if decision["action"] == "escalate":
            print(f"🔴 {decision['reason']}", file=sys.stderr)
            return 1
        return rc
    if decision["action"] == "arm_reset":
        state.update(state="waiting", reset_source=decision["reset_source"],
                     reset_at=decision["reset_at"].isoformat())
    rc, moment = _register_and_record(plan, state, decision["at"], SENTINEL_TICK)
    append_log(log, "sentinel_rearmed", action=decision["action"],
               fire_at=decision["at"].isoformat(), next_run_time=moment)
    return rc


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.sentinel_tick:
        return _sentinel_tick(args)
    if args.resume_tick:
        return _resume_tick(args)
    if args.probe_quota:
        verdict = probe_quota(args.probe_command)
        print(f"quota_open={verdict['open']}  kind={verdict['kind']}  rc={verdict['rc']}")
        print(verdict["text"][:600])
        return 0 if verdict["open"] else 1

    # 這三個模式不需要逐字稿，先處理（否則在找不到 session 的機器上連查姿態都做不到）。
    if args.check_autocompact:
        posture = autocompact_posture()
        print(autocompact_report(posture), end="")
        return 0 if posture["enabled"] else 1
    if args.verify_schtasks and not args.register_schtasks:
        return _schtasks_verify(args.task_name)
    if args.remove_schtasks:
        return _schtasks_remove(args.task_name)

    transcript = resolve_transcript(args.session_id, args.transcript)
    if transcript is None and args.arm_sentinel and args.transcript:
        # 🔴 唯一一個「路徑還不存在也接受」的入口，而且理由是結構性的：哨兵由
        # SessionStart 武裝，而那一刻逐字稿檔案往往還沒被建立出來。它不做量測、
        # 只把路徑記進狀態塊供巡邏時讀 ⇒ 綁錯 session 的風險為零（路徑是 harness
        # 在 payload 裡給的）。其餘入口一律維持 fail-loud。
        transcript = Path(args.transcript)
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
    # 兩條武裝路的差別在被呼叫的那個函式，不在這個分派——合成一句是為了騰出 LOC
    # 餘裕（本檔 `guardrail_cli` tier 上限 750，門檻一格都沒有調高），語意不變：
    # `--arm-sentinel` 仍優先於 `--arm-endurance`。
    if args.arm_sentinel or args.arm_endurance:
        print()
        arm = _arm_sentinel if args.arm_sentinel else _arm_endurance
        return arm(args, transcript, out)
    if args.print_schtasks:
        print("\n" + schtasks_command(str(out), args.task_name, args.at), end="")
    if args.register_schtasks:
        print()
        rc, moment = _register_at_expr(str(out), args.task_name, args.at, RESUME_TICK)
        if rc != 0:
            return 1
        print(f"✅ NextRunTime = {moment}　←（憑證；宣稱『已排程』時必須連它一起貼）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
