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
#
# 🔴 R102／PRD §4.2.4 R7：`trace_dir()` 此前把「退化了沒」這件事**吞掉**——呼叫端拿到的  round-label-ok  # noqa: E501
# 永遠只有最終目錄，分不出「這就是我要的家目錄」與「本次悄悄退回了 `$TMPDIR`」。遲滯
# 狀態機（`tools/lib/quota_availability.py`）的持久化落在這裡，而 R7 明文要求「退回系統
# 暫存」必須被**偵測**（loud 一次＋自檢文字＋該次判定視同 unmeasured）——沒有第二格
# 布林，那三件事在呼叫端結構上做不到。拆成 `trace_dir_status()` 是**延伸 SSOT**而不是
# 開第二個家：兩層判斷（`mkdir` 失敗／建了但不可寫）原封不動留在這裡，`trace_dir()` 改為
# 對第二格布林的相容包裝，行為對既有呼叫端逐字不變（回歸鎖＝本檔既有的
# `DurableTraceHomeTest` 五支，皆呼叫 `trace_dir()` 本身，未改動任何一支）。
# v2.1.13 G2（PRD_Amendment_R113_WakeChain_LastMile.md §3(b)1「共用」判決）：持久目錄的
# 解析形態（ENV 逃生口 → 家目錄居所 → 唯讀／建不出來時退回系統暫存）抽成**單一定義**，
# traces 與 handback 兩個居所共用——「同一句話兩個家」是本 repo 反覆判過的形態。兩層
# 判斷（`mkdir` 失敗／建了但不可寫）逐字承接自 `trace_dir_status()` 原文，行為零變。
def _durable_dir_status(env_var: str, parts: tuple[str, ...]) -> tuple[Path, bool]:
    override = os.environ.get(env_var, "").strip()
    want = Path(override) if override else Path.home().joinpath(*parts)
    try:
        want.mkdir(parents=True, exist_ok=True)
    except OSError:
        return Path(tempfile.gettempdir()), True
    if not os.access(want, os.W_OK):
        return Path(tempfile.gettempdir()), True
    return want, False


def trace_dir_status() -> tuple[Path, bool]:
    """`(目錄, 是否已退回系統暫存)`。`degraded=True` 時目錄恆為 `Path(tempfile.gettempdir())`。"""
    return _durable_dir_status(TRACE_DIR_ENV, TRACE_HOME_PARTS)


def trace_dir() -> Path:
    return trace_dir_status()[0]


#: handback 交接檔目錄的逃生口（v2.1.13 G2；慣例同 `TRACE_DIR_ENV`：測試／CI 指到沙箱，
#: 人設得到、模型改不到自己那一份）。
HANDBACK_DIR_ENV = "AUTOSDD_HANDBACK_DIR"

#: 家目錄下的持久交接居所（相對於 `Path.home()`；＝`~/.autosdd/handback`）。
HANDBACK_HOME_PARTS = (".autosdd", "handback")


def handback_dir_status() -> tuple[Path, bool]:
    """`(目錄, 是否已退回系統暫存)`——與 `trace_dir_status()` 同一份解析形態（見上）。

    消費端（`tools/lib/resume_route.py::handback_dir` 與 SessionStart 偵測）一律委派本檔，
    不得自帶第二份解析——壽命／逃生口紀律與 `~/.autosdd/traces` 同一條（§3(b)1）。
    """
    return _durable_dir_status(HANDBACK_DIR_ENV, HANDBACK_HOME_PARTS)


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


# ══════════════════════════════════════════════════════════════════════════
# ③ harness autocompact 姿態（ADR-XPLAT-014 §7.0-a/§7.0-b ⓿：自 session_resume_planner
#   搬入，讓出 planner 的 LOC 額度給缺陷① 的時刻解析階梯）
# ══════════════════════════════════════════════════════════════════════════
# 🔴 為什麼搬到本檔：這三支（autocompact_posture／report／check_report）與續航／排程／額度
# 三條主線無關——它們讀的是 harness 自己的 settings／env 與逐字稿水位，正是本檔的主題
# 「這台機器的環境姿態」。ADR §7.0-a 實測 planner 已 750/750（headroom 0），①② 一行寫不進去。
# 🔴 `guard` 一律**注入**（不 import）：本檔要維持 stdlib-only，才能被任何一側匯入而不成環
# （ADR §7.0-b：「import 期相依換成呼叫期相依」）。`HARD_RATIO` 進了比較式（:_report），
# 故為必填參數、不給預設兜底（給了＝在 lib 側複寫一份硬線＝同一份知識兩個家）。
# 原文逐字承接自 planner（僅簽章加 `guard`、常數改由本檔持有），行為零變。

#: harness 的 autocompact 開關判定（`claude.exe` 二進位內逐字）：
#: `if(DISABLE_COMPACT)return!1; if(env.DISABLE_AUTO_COMPACT)return!1;
#:  return config("autoCompactEnabled", true)` ⇒ 缺席即開啟。
_AUTOCOMPACT_KILL_ENVS = ("DISABLE_AUTO_COMPACT", "DISABLE_COMPACT")
_GLOBAL_CONFIG_KEY = "autoCompactEnabled"
#: R92：repo settings 的 env 區塊釘了這支（=90），posture 要能把現值秀出來（官方語意：
#: auto-compact window 的該百分比觸發、只能調低——見 ADR-XPLAT-008）。
_PCT_OVERRIDE_ENV = "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"


def autocompact_posture(guard) -> dict:
    """harness 自己那一半：現在到底有沒有東西在自動 compact，window 是多少。"""
    kills = {name: os.environ.get(name) for name in _AUTOCOMPACT_KILL_ENVS if os.environ.get(name)}
    config_path = Path(os.path.expanduser("~")) / ".claude.json"
    configured = guard.settings_value(_GLOBAL_CONFIG_KEY, [config_path])
    layer_off = [str(p) for p in guard.settings_chain() if guard.settings_value(_GLOBAL_CONFIG_KEY, [p]) is False]  # noqa: E501
    effective = not kills and guard.settings_value(_GLOBAL_CONFIG_KEY, guard.settings_chain()) is not False  # noqa: E501
    # B-02：行程 env 沒有時退而掃 settings 鏈各層的 env 區塊（宣告值；行程 env 有值優先）。
    pct = os.environ.get(_PCT_OVERRIDE_ENV) or next(
        (str(blk[_PCT_OVERRIDE_ENV]) for blk in (guard.settings_value("env", [p]) for p in guard.settings_chain())  # noqa: E501
         if isinstance(blk, dict) and blk.get(_PCT_OVERRIDE_ENV) is not None), None)
    window_env, window_setting = os.environ.get(guard.CC_WINDOW_ENV), guard.settings_value(guard.CC_WINDOW_KEY)  # noqa: E501
    return {"effective": effective, "kill_envs": kills, "config_path": str(config_path), "configured": configured,  # noqa: E501
            "window_env": window_env, "pct_override": pct, "window_setting": window_setting, "layer_off": layer_off,  # noqa: E501
            "window": window_env or window_setting or "auto"}


def autocompact_report(posture: dict, guard) -> str:
    state, seen = ("開啟" if posture["effective"] else "🔴 關閉"), ("未設（＝採用預設 true）" if posture["configured"] is None else repr(posture["configured"]))  # noqa: E501
    lines = [
        f"harness autocompact   {state}", "  判定鏈（依 claude.exe 二進位內的順序）",
        f"    1. 環境變數 {list(_AUTOCOMPACT_KILL_ENVS)} 任一為真 ⇒ 關閉　現況：{posture['kill_envs'] or '皆未設'}",  # noqa: E501
        f"    2. {posture['config_path']} 的 {_GLOBAL_CONFIG_KEY}（僅供稽核，非官方 settings 階層）　現況：{seen}",  # noqa: E501
        f"    3. settings 鏈 first-wins {_GLOBAL_CONFIG_KEY}（本欄即 `effective` 的依據）　現況："
        + ("🔴 有層設 false：" + "；".join(posture["layer_off"]) if posture["layer_off"] else "無任何一層設 false"),  # noqa: E501
        f"  pct override          {_PCT_OVERRIDE_ENV}={posture['pct_override']!r}（未設＝harness 預設觸發點；設了＝在 auto-compact window 的該百分比觸發，只能調低）",  # noqa: E501
        f"  window                {posture['window']}（{guard.CC_WINDOW_ENV}={posture['window_env']!r}；settings.{guard.CC_WINDOW_KEY}={posture['window_setting']!r}；兩者皆無時 CC 走 auto，且大於模型上限時由 CC 自己 capped）",  # noqa: E501
    ]
    # R92／D4（SD 複審 P3）：PCT_OVERRIDE 值域 1-100 無官方下界保證，調到 ≥ 硬線時
    # 94% 那則「壓縮未發生」警報會誤判一個只是「觸發點設得晚」的正常 autocompact。
    try:
        pct_val = float(posture["pct_override"]) if posture["pct_override"] is not None else None
    except ValueError:
        pct_val = None
    if pct_val is not None and pct_val >= guard.HARD_RATIO * 100:
        lines.append(f"  ⚠️  {_PCT_OVERRIDE_ENV}={pct_val:g} ≥ 硬線 {guard.HARD_RATIO:.0%}——94% 的「壓縮未發生」警報這裡可能只是觸發點設得比較晚，不是真失效，請對照這個值再下判斷。")  # noqa: E501
    # R92／D2：`effective` 已是 first-wins 算過的真值，不再需要「可能仍開啟」的模糊仗
    # ——只有 layer_off 非空但 effective 仍 True 時才提醒「你以為關了，其實沒關」。
    if not posture["effective"]:
        lines.append("  🔴 autocompact 目前的有效值是關閉：撞到 context 上限時會直接失去對話，而不是自動摘要。請在 /config 開回來，或拿掉相關環境變數／設定層。")  # noqa: E501
    elif posture["layer_off"]:
        lines.append("  ℹ️  有層宣告 false 但被更高優先層蓋過，目前有效值仍是開啟（僅供稽核）：" + "；".join(posture["layer_off"]))  # noqa: E501
    return "\n".join(lines) + "\n"


def check_report(data: dict, guard) -> str:
    """`--check` 的輸出。量不到時**明說量不到**，不印一個看起來像 0% 的數字。"""
    if data["used"] is None:
        return (f"❌ {data['transcript']}\n   掃不到任何帶 message.usage 的 assistant 記錄"
                " —— 「量不到」與「量到零」必須分得開，故不印百分比。"
                "逐字稿剛建立、或欄位格式已變更都會走到這裡。\n")
    tier = {None: f"低於 {guard.WARN_RATIO:.0%}", guard.TIER_WARN: f"≥{guard.WARN_RATIO:.0%}（建議 compact）",  # noqa: E501
            guard.TIER_HARD: f"≥{guard.HARD_RATIO:.0%}（停止開新戰場）"}[data["tier"]]
    return (
        f"session   {data['session_id']}\n逐字稿    {data['transcript']}\n"
        f"used      {data['used']:,}（input + cache_creation + cache_read；output_tokens 不計）\npeak      {data['peak_used']:,}（本 session 歷來最大，window 下界推論的輸入）\n"  # noqa: E501
        f"model     {data['model'] or '（逐字稿裡讀不到）'}（window 交叉否決的依據）\nwindow    {data['window']:,}〔{data['window_source']}〕\n水位      {data['ratio']:.1%}  → {tier}\n"  # noqa: E501
        f"硬擋資格  {'有' if data['may_block'] else '無（分母是保守下界猜測 ⇒ 只出聲不擋）'}（PreToolUse 阻斷模式的第三道放行條件）\n重啟指令  claude -r {data['session_id']}\nharness   姿態現查：--check-autocompact（autocompact 才是真正在做 compact 的東西）\n"  # noqa: E501
    )
