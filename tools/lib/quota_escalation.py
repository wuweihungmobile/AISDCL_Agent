"""續航協定的兩件事：**叫人**（等不到的額度）與**扇出續跑清單**（被打死的 agent）。"""
# WHY —— 為什麼是新的一支檔，而不是寫進 `tools/session_resume_planner.py`
# --------------------------------------------------------------------
# 續航這件事的家仍然是 planner，本檔是它的**被 import 的一方**（同 planner ↔
# `context_budget_guard` 的既有方向）。抽出來只有一個理由，而那個理由是量出來的：
# 落地當回合 planner 的 `count_loc` 是 **749/750**（`guardrail_cli` tier，餘裕 1 行），
# 而本 repo 對這個處境的既定解法逐字寫在 `check_loc_budget.py` 的 ROOT-TOOLS 指引裡
# ——「破線後不是調高預算，而是拆職責／抽共用模組（先例：tools/lib/ci_liveness.py）」。
# ⇒ 本檔是**那條指引指定的動作**，不是第四個家：判定層（`sentinel_decide`／`tick_plan`）
# 與編排層（`_sentinel_tick`／`_resume_tick`）一行都沒有搬走，搬走的只有「終態該對人與
# 對磁碟做什麼」這一段副作用。
#
# R81 補的是 R80 驗屍（`docs/04_planning/AutoSDD_improving_104.md` §4.5 R81-0）留下的
# 兩個**設計缺口**——都不是 bug，是「機制照著規格跑，而規格漏了一種情況」：
#
# 缺口 A（R81-0-a）：額度有兩條線，協定只認得一條
#   `classify_limit()` 早就分得出 `LIMIT_SPEND`，`sentinel_decide()`／`tick_plan()` 也
#   早就對它回 `escalate`／`stop`（＝**不排程**）。真正缺的是另外半件事：那兩支的理由
#   逐字都寫著「通知人」「叫人」，而實際的「人」只收得到一行 **stderr**——哨兵是由
#   schtasks 以 `pythonw.exe`（GUI 子系統、無 console）起的，那一行 stderr **沒有任何
#   終端會收到它**。⇒ 「不排程」做到了，「通知」結構上做不到，而兩者的痕跡完全相同
#   （狀態塊 `abandoned`、工作被移除、jsonl 多一行）。本檔補的是**載體**。
#
# 缺口 B（R81-0-b）：協定救的單位錯了——它救 session，而死的是扇出
#   R80 四次撞線主迴圈一次都沒死，死的是 subagent（42／55／1 個）。續跑那一段因此永遠
#   不會觸發、也**不該**觸發。真正需要被記下來的是「哪一個 workflow run、哪幾個 agent
#   被打死」，而那件事**讀檔就知道、成本為零**（同哨兵「巡邏不花 token」的前提）。
#
# 🔴 誠實劃界（`resumeFromRunId` 是**同 session only**，這是硬約束不是實作偷懶）：
# 本檔**不會**也不能自動把死掉的扇出重派。理由有兩層，兩層都擋得死：
#   ① 那個能力住在 Workflow 工具裡，只有**還活著的那個 session 內的模型回合**按得到；
#      本檔是一個 OS 排程器叫起來的 subprocess，沒有任何管道可以把工具呼叫注入進去。
#   ② session 真的死掉時，`runId` 對 `resumeFromRunId` 已無效（同 session only）。
# ⇒ 本檔交付的是**誠實的半自動**：把「續跑這件事需要的全部資訊」落到磁碟上的一個固定
# 位置，讓下一個舵手（人、或 R81-1／R81-2 的 AutoClaude）看得到、按得下去。
# 宣稱全自動會是一句在結構上就不成立的話，那比沒有功能更糟。
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

# 🔴 R84／ARCH-06 連帶：本檔**不得**再出現 `from datetime import UTC`（3.11+）。
# 立案是量出來的，不是潔癖：ARCH-06 讓 `tools/lib/sentinel_lifecycle.py`（hook 鏈上的檔）
# 靜態 import 本檔 ⇒ 本檔就進了 `test_mac_readiness_r82.hook_chain_py39_census()` 的射程，
# 而那張債表是 **shrink-only**（多一筆＝macOS 內建 python3（常年 3.9）上又多一個會靜默失能
# 的能力）。本輪實測：不改的話該鎖當場紅在 `{'tools/lib/quota_escalation.py':
# ['from datetime import UTC']}`。三條路只有這一條不是把門檻放寬：
#   ✗ 把自己加進那張債表 ⇒ 調高 shrink-only 門檻（而且那句話還是假的：本檔的 import 在
#     函式層，hook 鏈的 import 期一次都不會執行它）。
#   ✗ 改寫成 `timezone.utc` ⇒ 根層 ruff（`tools/ruff.toml`，`UP` 已選、target py311）當場
#     `UP017 Use datetime.UTC alias`（本輪 `--stdin-filename` 實測命中）⇒ 換一個閘門紅。
#   ✓ 這兩個時間戳本來就只是**給人看的稽核字串**（無人解析：全庫零斷言），改用
#     `time.strftime("%Y-%m-%dT%H:%M:%S%z")`——與 `schedule_backend._append_trace`／
#     `sentinel_lifecycle.maybe_arm` 逐字同一個既有慣例，3.9 相容，且仍帶 offset
#     （`TestNaiveLocalTimestampsAreNotPersisted` 禁的是不帶 offset 的 naive 字串）。
#: 稽核字串用的當地時間戳（帶 offset）。唯一的家在這裡，兩個消費者都取它。
_STAMP = "%Y-%m-%dT%H:%M:%S%z"

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import context_budget_guard as guard  # noqa: E402  # 逐字稿判讀的唯一實作（不另抄一份）

# 🔴 PRD §4.5.7／§4.5.8（v2.1.6／v2.1.7）：四支同層 sibling，供下方 `patrol_housekeeping()`
# 一族使用。零循環風險——本檔既有的 `guard` import 已證實這條路可通；`quota_gate`／
# `schedule_backend` 皆不 import 本檔（`quota_gate.py` 檔頭明文「本檔不得 import 那支
# hook」，方向反過來才對）；`sentinel_lifecycle` 對本檔的唯一參照是函式層 lazy import
# （`_sweep_artifacts` 內的 `from quota_escalation import reap_plans`），模組層不會成環。
# `endurance_env`／`quota_ledger` 是 PRD_Amendment_R112_WakeChain.md §3-1 A-4／§3-4
# （無主分支與通知補投佇列）共用的兩支 sibling（持久目錄 SSOT＋TTL 閂鎖原語），同
# `quota_availability.py`／`quota_stability.py` 既有依賴面，本檔不重抄第二份路徑解析
# 或互斥邏輯（六支依 ruff isort 字母序排列，順手併成一個區塊）。
import endurance_env  # noqa: E402
import quota_gate  # noqa: E402
import quota_ledger  # noqa: E402
import quota_policy  # noqa: E402
import schedule_backend  # noqa: E402
import sentinel_lifecycle  # noqa: E402

#: 🔴 固定檔名、**不帶 session id**。帶了就等於把「要人看的那張紙」藏進一個只有機器知道
#: 名字的地方——R80 的稽核痕跡 `autosdd_resume_log_<sid>.jsonl` 正是這個形態，整晚沒有
#: 任何人打開過它。一個名字、一個位置，人才有辦法把它加進自己的習慣。
NOTE_NAME = "AUTOSDD_ATTENTION.md"

#: 月度支出上限唯一會回來的路徑（本檔不猜、不等，只把人帶到這裡）。
USAGE_URL = "https://claude.ai/settings/usage"

#: 🔴 R82／HELM-01：桌面通知**預設關閉**，而這是使用者的直接指令（2026-08-09 逐字：
#: 「請確認並修正**無彈窗**執行」）。R81 版在 Windows 走的是一個**模態**對話框，會奪走
#: 焦點並杵在螢幕上十分鐘；而使用者三度收到它的那幾次，觸發原因是「開了沒做事就結束的
#: session 沒有留下逐字稿」——一個正常且常見的情形。⇒ 模態管道整條移除（見 `notify`），
#: 剩下的非模態管道也改成 opt-in：要它回來就設這個環境變數，模型改不到、人改得到。
NOTIFY_ENV = "AUTOSDD_DESKTOP_NOTIFY"

#: 「沒有敲」的兩個 rc，與 127（這台機器上沒有那條管道）刻意三者分開：稽核痕跡必須
#: 分得出「開關關著」「不值得打斷人」「敲了但失敗」，否則通知的失效仍然是靜默的。
NOTIFY_OFF_RC = -1
NOTIFY_NO_RESCUE_RC = -2

# ══════════════════════════════════════════════════════════════════════════
# PRD_Amendment_R112_WakeChain.md §3-4（DEF-200-236）：通知補投佇列
# ══════════════════════════════════════════════════════════════════════════
# 立案：`alert()` 對 `dead_agents == 0` 的 loud 情境刻意**不呼叫** `notify()`（HELM-01：
# 沒有東西要救就不敲桌面），回的 `NOTIFY_NO_RESCUE_RC` 因此從來沒有機會變成真的送達——
# 而 `relay_stopped {why:no_progress}` 這一種**正是**值得人知道的 halt（R115 開閥實彈 round-label-ok
# 演練實測逐字：`notify_rc=-2`，見 CrossPlatform_R115_Debt_Closure.md §4）。此前那個 -2
# 就此**永久丟失**，不會有第二次機會。修法（QA 鏡 N-SA-1 劃界訂正：接線範圍＝`alert()`
# 與 `_orphan_watch()` 兩處；`_idle_prepare_watch()` 的預警失投**尚未**入列，掛
# R116_HANDOFF §二 round-label-ok）：非「使用者關掉這條管道」（`NOTIFY_OFF_RC`）失投入列
# （居所同 `endurance_env.trace_dir()`），由既有 900 秒巡邏 tick 重投，逾 TTL 或重試
# 次數用盡才出隊——出隊必須**出聲**（stderr），不得靜默丟棄。
NOTIFY_QUEUE_NAME = "autosdd_notify_queue.json"

#: 佇列項目多久沒送達就放棄（不得無上限累積）。取值同 `PLAN_GC_AGE_SECONDS` 的量級理由：
#: 遠大於一個額度視窗（5 小時），確保跨一次 reset 仍有機會被下一次巡邏送達。
NOTIFY_QUEUE_TTL_SECONDS = 24 * 3600

#: 逐則重試上限（PRD §3-4 逐字「重試上限 3 次，次數落痕跡」）。
NOTIFY_QUEUE_MAX_ATTEMPTS = 3

#: 無主模式「叫人」節流窗（SD 鏡 SD-1 承接；PRD v2.1.12 :206 本要求 ownerless 專屬
#: 常數）。🔴 不得與巡邏 tick 間隔（`SENTINEL_INTERVAL_SECONDS`＝900）共用同一值：
#: TTL＝tick 週期時下一巡到達必然 age≈ttl ⇒ 幾乎每巡重敲（探針實測連續多 tick 全部
#: claimed）。取 4×tick＝人類響應時間尺度：被叫後一小時內不重敲，條件仍在則再叫。
ORPHAN_NOTIFY_THROTTLE_SECONDS = 3600

#: 任務書殘骸的回收年齡。取值理由：一支**還在等**的哨兵，其任務書可能整整一個額度視窗
#: （5 小時）都不會被寫到，所以門檻必須遠大於它；7 天則遠小於「這些檔已經在 %TEMP% 躺了
#: 好幾輪」的實況（R82 開場實測 26 份，含三份測試殘骸）。
PLAN_GC_AGE_SECONDS = 7 * 24 * 3600

#: Windows 的**非模態**桌面管道。托盤氣球：不奪焦、不要求點擊、自己會消失。
#: 🔴 刻意外呼 `powershell.exe`（5.1）而不是本行程手上的 pwsh 7：`System.Windows.Forms`
#: 在 PS Core 上不保證載得起來，而這條路的失敗方式是「靜默不出現」。落地當回合實測 rc=0。
_WIN_TOAST = (
    "Add-Type -AssemblyName System.Windows.Forms;"
    "Add-Type -AssemblyName System.Drawing;"
    "$n = New-Object System.Windows.Forms.NotifyIcon;"
    "$n.Icon = [System.Drawing.SystemIcons]::Information;"
    "$n.Visible = $true;"
    "$n.ShowBalloonTip(10000, {title}, {body}, 'Info');"
    "Start-Sleep -Milliseconds 1500;"
    "$n.Dispose()"
)


def _ps_literal(text: str) -> str:
    """PowerShell 單引號字串字面（內部單引號要寫成兩個，那是唯一的跳脫方式）。"""
    return "'" + " ".join(text.split()).replace("'", "''") + "'"


def note_path() -> Path:
    """叫人用的那一張紙（固定位置，見 `NOTE_NAME` 的 WHY）。"""
    return Path(tempfile.gettempdir()) / NOTE_NAME


def fanout_path(session_id: str) -> Path:
    """該 session 的扇出續跑清單（缺口 B 的落地產物）。"""
    return Path(tempfile.gettempdir()) / f"autosdd_fanout_{session_id}.json"


# 🔴 `newline="\n"`：本 repo 判過「Python 寫檔不指定 newline，Windows 上會寫出 CRLF」。
# 寫不進去**不得**升級為失敗——最壞情況是這一次沒留下紙，不能反過來變成故障源
# （同 `append_log` 的既有紀律）。回傳值讓呼叫端把「寫了沒」記進稽核痕跡。
def _write(path: Path, text: str) -> bool:
    """寫一支 UTF-8／LF 文字檔；回「寫成功了沒」。"""
    try:
        path.write_text(text, encoding="utf-8", newline="\n")
    except OSError:
        return False
    return True


# 佈局是**觀察到的**（非官方契約，故每一層都 fail-soft），R81 當回合實查兩個 session：
#   · `<sid>/subagents/workflows/<runId>/agent-*.jsonl` —— 每個扇出 agent 一支，**跑的
#     當下就在寫**，所以撞線那一刻查得到（不必等 run 結束）。
#   · `<sid>/workflows/scripts/<workflowName>-<runId>.js` —— workflow 腳本，**啟動時就
#     落地**。實查活體 run：`r81-scan-and-design-wf_b6f25b5b-535.js` 已在磁碟上。
#   · `<sid>/workflows/wf_<runId>.json` —— run 的總結，**只有跑完才寫**（實查活體 run
#     的 `workflows/` 底下只有 `scripts/`）⇒ 它**不能**當撞線當下的資料來源，這一點是
#     本函式刻意走目錄名而不走那支 json 的原因。
def workflow_runs(transcript: Path) -> list[dict]:
    """本 session 底下每一個 workflow run 的 `runId`／名稱／agent 逐字稿清單。"""
    root = transcript.with_suffix("")
    scripts: dict[str, str] = {}
    script_dir = root / "workflows" / "scripts"
    if script_dir.is_dir():
        for js in script_dir.glob("*wf_*.js"):
            name, _, run = js.stem.rpartition("-")
            scripts[run] = name
    folder = root / "subagents" / "workflows"
    if not folder.is_dir():
        return []
    return [{"run_id": run.name, "workflow": scripts.get(run.name, ""),
             "agents": sorted(run.glob("agent-*.jsonl"))}
            for run in sorted(folder.iterdir()) if run.is_dir()]


# 🔴 判準刻意是**同檔**證據，而 `guard.unhandled_limit_event` 用的是**全域**證據——
# 兩者不是同一個問題，別因為關鍵字相同就把它們對調：
#   · 全域證據回答「這個帳號的額度現在通不通」。同檔證據對這個問題 R80 實測假陽性
#     81.3%，成因是結構性的：被打死的 subagent 在自己的檔裡永遠不會再有下一則成功回應。
#   · 同檔證據回答「**這一個 agent 死了沒**」。上面那個「成因」對這個問題不是缺陷，
#     是唯一正確的判準——它死了，所以它的檔就停在那則撞線訊息上。
# 於是 R80 那份量測不但不否決本函式，它正是本函式的立案依據。
def quota_killed(path: Path) -> str:
    """這支 agent 逐字稿是不是**停在額度撞線上**；回撞線類型，空字串＝不是。"""
    event = guard.latest_limit_event(path)
    if event is None or event["kind"] not in (guard.LIMIT_SESSION, guard.LIMIT_SPEND):
        return ""
    return event["kind"] if event["timestamp"] > guard.latest_success_at([path]) else ""


def snapshot_fanout(transcript: Path, event: object) -> dict:
    """撞線當下記下「哪個 run、哪幾個 agent 被打死」；回稽核欄位（沒有死者就回 `{}`）。"""
    if not event or not transcript.is_file():
        return {}  # 巡邏那一支（99% 的呼叫）走這裡：零 I/O、零成本
    runs = []
    for run in workflow_runs(transcript):
        dead = [{"agent": p.stem, "kind": kind} for p in run["agents"]
                if (kind := quota_killed(p))]
        if dead:
            runs.append({"run_id": run["run_id"], "workflow": run["workflow"],
                         "agents_total": len(run["agents"]), "dead": dead})
    if not runs:
        return {}
    path = fanout_path(guard.session_id_of(transcript))
    ok = _write(path, json.dumps({
        "schema": "autosdd.fanout.v1", "session_id": guard.session_id_of(transcript),
        "transcript": str(transcript), "hit": event, "runs": runs,
        "at": time.strftime(_STAMP),
        # 🔴 這一格是規格不是說明文字：讀這份檔的人（或 AutoClaude）必須知道「自動
        # 續跑」在什麼條件下**結構上不成立**，否則它會被當成一個沒被按下的按鈕。
        "how_to_resume": [
            "① session 還活著（R80 四次撞線主迴圈都沒死，這是常態）：在**那個 session 內**"
            f"用 Workflow 的 resumeFromRunId={[r['run_id'] for r in runs]}"
            "——已完成的 agent 從 cache 回放，只重跑下面 dead 清單裡的那些。",
            "② session 已死：runId 對 resumeFromRunId **已無效**（同 session only），"
            "此時本檔的用途是重派清單——照 dead 逐一重新指派。",
            "🔴 兩種情況都**不會**由排程器自動按下：它是 OS 行程，沒有管道把工具呼叫"
            "注入進一個活著的 session。這是硬約束，不是還沒做。"],
    }, ensure_ascii=False, indent=2))
    return {"fanout": str(path) if ok else "", "fanout_written": ok,
            "dead_agents": sum(len(r["dead"]) for r in runs),
            "runs": [r["run_id"] for r in runs]}


# ══════════════════════════════════════════════════════════════════════════
# PRD §4.5.7（v2.1.6）：主控閒置盲區與預防性水位提醒
# ══════════════════════════════════════════════════════════════════════════
# 立案：撞線那一刻**之前**主控完全不知道水位已逼近（等 subagent 回覆期間零工具呼叫，
# `context_budget_guard.py` 只掛 Pre/PostToolUse，該窗口結構上不會被觸發）。修法掛在
# 既有哨兵巡邏——巡邏本來就每 900s 讀一次逐字稿，這裡只是多讀一眼「主控自己」多久沒
# 動過、再多讀一次額度快取。三件事一次到位：R-4.5.7-1（閒置量測，只看**主**逐字稿，
# 不含 subagent——否則扇出正忙時主控閒置會被 subagent 的 mtime 蓋過去）／R-4.5.7-2
# （水位進 prepare 帶且未 halt 才提醒，且刻意不寫任務書骨架，同 R-4.5.6-3 單檔雙寫者
# 禁令的精神）／R-4.5.7-3（走 `notify()` 桌面通道，不依賴主控下一次工具呼叫）。
def _main_transcript_idle_seconds(transcript: Path, now: float) -> float | None:
    """只讀**主**逐字稿最後一筆 `type=assistant`／`tool_use` 事件時間戳，回距今秒數。

    `None`＝這支檔案沒有任何可辨識的事件（讀不到／空檔／格式全不認得）。
    """
    last = None
    try:
        with transcript.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"timestamp"' not in line or '"type"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") not in (
                        "assistant", "tool_use"):
                    continue
                stamp = _epoch(record.get("timestamp"))
                if stamp is not None and (last is None or stamp > last):
                    last = stamp
    except OSError:
        return None
    return None if last is None else max(0.0, now - last)


def _epoch(raw: object) -> float | None:
    """ISO 時間戳→epoch 秒；認不出來回 `None`。只做相減，不持久化（同既有紀律）。"""
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _idle_prepare_watch(transcript: Path, now: datetime, idle_threshold: float) -> dict:
    """R-4.5.7-1／-2／-3：主控閒置中 ＋ 水位進 prepare 帶 ⇒ 桌面通知，不寫任務書骨架。"""
    idle = _main_transcript_idle_seconds(transcript, now.timestamp())
    if idle is None or idle < idle_threshold:
        return {"controller_idle_seconds": idle}
    policy, _ = quota_policy.load_policy(quota_gate.policy_env())
    decision = quota_policy.decide(quota_gate.read_quota(now), now, policy)
    if decision.band != quota_policy.BAND_PREPARE:
        return {"controller_idle_seconds": idle, "quota_band": decision.band}
    rc = notify("AutoSDD 額度即將見底", quota_policy.describe(decision))
    return {"controller_idle_seconds": idle, "quota_band": decision.band, "prepare_notify_rc": rc}


# ══════════════════════════════════════════════════════════════════════════
# PRD §4.5.8（v2.1.7）：哨兵武裝狀態漂移自癒
# ══════════════════════════════════════════════════════════════════════════
# 立案：`--pace` 的 `sentinel_lifecycle.liveness_line()` 只出聲、不動作——本機 armed
# stamp 說已武裝，排程器現查卻沒有這支工作時，此前唯一的處置是要求人手動重跑
# `--arm-sentinel`，不符合「不需要人類介入」的自動化閉環要求。修法：每次巡邏 tick 額外
# 核對一次「這支工作還在不在」，真的漂移（非量不到）就地重新武裝，不必等人發現。
# 🔴 誠實劃界：本檢查依附在巡邏 tick 本身——若排程器裡的工作被整條刪除且**再也不會
# 觸發**下一次 tick，這裡沒有任何辦法把它救回來（沒有事件源可以叫醒一支已經不存在的
# 排程）。它能治的是「工作還在（tick 因此被叫起），但 armed stamp 與現查不一致」這一類
# 可觀測的漂移，等同把 R-4.5.6-4 的「先自癒後解除」紀律用到「排程器現查」這一個新輸入上。
def _append_trace(path: Path, event: str, **fields: object) -> None:
    """append 一行 JSONL 稽核痕跡（py3.9 安全版；同檔既有 `_STAMP`／`time.strftime` 慣例，
    不引入 `datetime.now(UTC)`——`planner.append_log` 的字面複本會把本檔重新踩進
    ARCH-06 那個 hook 鏈 py3.9 census 的雷）。寫不進去不得升級為失敗，同 `_write` 的紀律。
    """
    record = {**fields, "event": event, "at": time.strftime(_STAMP)}
    try:
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _heal_armed_drift(state: dict, now: datetime, idle_threshold: float, tick: str,
                      log: Path) -> dict:
    """armed stamp 說已武裝但排程器查無此工作 ⇒ 自動重新武裝；回稽核欄位（`{}`＝沒漂移）。

    自癒成功與否都留一筆**與『巡邏／武裝／自癒（RELAY 版）／解除』互異**的事件名
    （`sentinel_armed_drift_healed`）——比照 R-4.5.6-4c 的紀律：不同失效形態要能從
    痕跡分辨出來，不能只靠 `sentinel_decided` 多幾個欄位（那一行每次巡邏都會印，
    多幾個欄位不足以讓「這次巡邏發生過漂移」在痕跡上一眼可辨）。
    """
    task = str(state.get("task_name") or "")
    if not task or state.get("state") in sentinel_lifecycle.TERMINAL_STATES:
        return {}
    if not sentinel_lifecycle.armed_but_missing(task, sentinel_lifecycle.sentinel_task_names()):
        return {}  # 量不到／確實還在 ⇒ 沒有漂移可自癒（量不到不得誤判成漂移）
    at = (now + timedelta(seconds=idle_threshold)).astimezone()
    at_expr = f"'{at.strftime('%Y-%m-%d %H:%M:%S')}'"
    rc, moment = schedule_backend.select().arm(
        str(state.get("plan_path") or ""), task, at_expr, tick, at)
    audit = {"armed_drift_healed": rc == 0, "armed_drift_rc": rc, "armed_drift_credential": moment}
    _append_trace(log, "sentinel_armed_drift_healed", task=task, **audit)
    # v2.1.13 G4／V-d2 後半：漂移自癒的重掛也可能失敗——修前此分支只記 audit，不清
    # armed stamp、不 loud，會留下一個「stamp 說已武裝、排程器現查卻沒有」的假閂鎖
    # （與 `relay_machine._rearm_after_stop()` 判準1同型的那個病，此前只有那一條有藥）。
    # 清 stamp 讓下一個互動 session 的 `maybe_arm()` 走正常武裝路，不留一個宣稱已重掛
    # 的假閂鎖（fail-safe 方向：寧可重新評估，不可假裝好了；
    # R112 §3-5「自癒的自癒」同型）。  # round-label-ok：引述章節號非自稱輪號
    if rc != 0:
        import sentinel_lifecycle_arm  # noqa: PLC0415 — 只在失敗路徑才需要（同 relay_machine 既有手法）  # noqa: E501

        session_id = sentinel_lifecycle.session_of(task) or str(state.get("session_id") or "")
        sentinel_lifecycle_arm.clear_arm_latch(session_id)
        alert(f"武裝狀態漂移自癒重掛失敗（rc={rc}）：喚醒鏈斷線，已清 arm latch 供下次 "
              "SessionStart 重新評估", state, loud=True)
    return audit


# ══════════════════════════════════════════════════════════════════════════
# PRD_Amendment_R112_WakeChain.md §3-1 A-4（DEF-200-234）：無主模式偵測
# ══════════════════════════════════════════════════════════════════════════
# 立案：主控死於 API 層 429 時，存活的背景 agent／Workflow 扇出沒有任何機制轉入
# 「無主」——續航協定救的是**排程**（等額度回來重新叫醒），對「這一刻正在燒 token
# 而沒有人統籌」這件事結構上是瞎的（`CrossPlatform_R111_Sentinel_Forensics_Mac.md`
# §4-6）。判準三值 {ownerless, owned, unmeasurable}——**量不到 ≠ 無主**，與本檔通篇
# `reap_verdict`／`armed_but_missing` 同一條紀律：看不到活體不等於沒有活體。
def _agents_liveness(transcript: Path, now: float, idle_threshold: float) -> str:
    """背景 workflow agent 逐字稿有沒有活體：`"alive"／"idle"／"unmeasurable"`。

    零侵入心跳＝**逐字稿檔案 mtime 新鮮度**（根 CLAUDE.md 鐵律六：比對面不含自己，
    裸 `pgrep` 在多支並行時會自己命中自己）；`workflow_runs()` 是既有的目錄佈局解析，
    本函式不重抄第二份。連 `subagents/workflows/` 目錄都定位不到＝**量不到**，不得
    誤判成「沒有活體」。

    🔴 已被 `quota_killed()` 判定為死者的 agent 從 mtime 候選中**排除**：一支 agent
    最後一次寫入往往正是它自己撞線的那一刻，mtime 因此結構上「新鮮」，若不排除會把
    「主控與這支 agent 同一次撞線一起死掉」誤判成「主控死了、agent 還活著」——本函式
    落地當回合在 `SpendLimitReachesAHumanTest` 真的撞見過這個假陽性（`_dead_agent()`
    造出的死者被算成 alive，把一支既有測試的既有主體撞線流程誤標成無主）。有 run
    可觀測、但排除死者後空無一物＝`"idle"`（**已經觀測到、且觀測到的是沒有活體**），
    不是 `"unmeasurable"`（那是保留給「連 run 目錄都找不到」的）。
    """
    if not transcript.is_file():
        return "unmeasurable"
    runs = workflow_runs(transcript)
    if not runs:
        return "unmeasurable"
    try:
        mtimes = [p.stat().st_mtime for run in runs for p in run["agents"]
                 if _exists(p) and not quota_killed(p)]
    except OSError:
        return "unmeasurable"  # N-3：_exists 與 stat 之間的 TOCTOU 競態，量不到就說量不到
    if not mtimes:
        return "idle"
    return "alive" if (now - max(mtimes)) < idle_threshold else "idle"


def _exists(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def ownerless_verdict(main_dead: bool, agents_state: str) -> str:
    """純判準：{ownerless, owned, unmeasurable}。`agents_state="unmeasurable"` 時
    一律回 `unmeasurable`——量不到背景活體不得被讀成「沒有活體」（＝owned）。
    簽名對 PRD §3-1 A-4 三參數形態的化簡（N-2）：`main_dead = unhandled_limit_event
    is not None` 已內含「主控閒置×未處理撞線」合取，語意等價。
    """
    if agents_state == "unmeasurable":
        return "unmeasurable"
    return "ownerless" if main_dead and agents_state == "alive" else "owned"


def orphan_mark_path(session_id: str) -> Path:
    """該 session 的無主條件標記（`claim_once` 的閂鎖，同時是「條件在不在」的憑證）。"""
    return endurance_env.trace_dir() / f"autosdd_orphan_{session_id}.json"


def _orphan_watch(transcript: Path, event: object, now: datetime, idle_threshold: float,
                  state: dict, log: Path) -> dict:
    """DEF-200-234：主控死亡（`event` 非 `None`）且背景 agent 仍有活體 ⇒ 無主分支。

    `claim_once` 節流「叫人」的頻率（同一 TTL 視窗只敲一次桌面），**不**節流痕跡本身
    ——`ownerless_verdict` 每次巡邏都算一次，讓「條件解除」能被即時偵測並清標記
    （`ownerless_cleared`）。投遞失敗不終結條件：失敗的通知交給 `queue_notify()`，
    由本檔既有的 `redeliver_queued()` 在下一次巡邏（≤900s）自動重投，不必等這裡再敲一次。
    """
    session_id = str(state.get("session_id") or guard.session_id_of(transcript))
    mark = orphan_mark_path(session_id)
    verdict = ownerless_verdict(event is not None, _agents_liveness(
        transcript, now.timestamp(), idle_threshold))
    if verdict == "unmeasurable":
        # A-2（Architect 鏡承接）：量不到 ≠ 條件解除——既有標記原樣保留、不清不投、
        # 不記 ownerless_cleared，留待下一巡能量到時再判（清標記只准由 "owned" 觸發）；
        # 無標記時維持既有安靜姿態（回空＝本次巡邏無事可記）。
        return {"ownerless_verdict": verdict} if mark.is_file() else {}
    if verdict != "ownerless":
        if not mark.is_file():
            return {}
        try:
            mark.unlink()
        except OSError:
            return {"ownerless_verdict": verdict}
        _append_trace(log, "ownerless_cleared", session_id=session_id, verdict=verdict)
        return {"ownerless_verdict": verdict, "ownerless_cleared": True}
    audit = {"ownerless_verdict": verdict}
    # SD-1：節流窗用專屬常數，不得借用 idle_threshold（那是活體新鮮度的尺，值＝tick 週期）。
    if quota_ledger.claim_once(mark, ORPHAN_NOTIFY_THROTTLE_SECONDS, now.timestamp()):
        rc = notify("AutoSDD 無主模式",
                   "主控已因額度撞線退場，背景任務仍在執行，目前無人統籌")
        if rc != 0:
            queue_notify("AutoSDD 無主模式",
                        "主控已因額度撞線退場，背景任務仍在執行，目前無人統籌",
                        rc, now.timestamp())
        _append_trace(log, "orphan_agents_detected", session_id=session_id, notify_rc=rc)
        audit["orphan_agents_detected"] = True
        audit["orphan_notify_rc"] = rc
    return audit


def patrol_housekeeping(transcript: Path, event: object, now: datetime, state: dict,
                        idle_threshold: float, tick: str, log: Path) -> dict:
    """每次巡邏的五件事：扇出死亡快照（既有）＋主控閒置預防提醒（§4.5.7）＋無主模式
    偵測（PRD_Amendment_R112 §3-1 A-4）＋武裝狀態漂移自癒（§4.5.8）＋通知補投佇列
    重投（§3-4）。合成一個字典，直接 `**` 進 `sentinel_decided` 痕跡。
    """
    audit = dict(snapshot_fanout(transcript, event))
    if event is None:
        audit.update(_idle_prepare_watch(transcript, now, idle_threshold))
    audit.update(_orphan_watch(transcript, event, now, idle_threshold, state, log))
    audit.update(_heal_armed_drift(state, now, idle_threshold, tick, log))
    audit.update(redeliver_queued(now.timestamp(), log))
    return audit


# 🔴 rc 一定要被記進稽核痕跡：通知的失效是**靜默**的——沒有人會因為「沒收到通知」而
# 去查。記下 rc 才讓「叫了人但沒叫到」與「根本沒叫」分得開（同本協定「觸發了但失敗
# vs 沒觸發」那條紀律）。回什麼都**不影響**流程：紙已經寫好了，通知只是把人帶過去。
#
# 🔴 R82／HELM-01 換掉了本函式的 Windows 管道，理由不逐字複述舊說法（本 repo 判過
# 「訂正註記引述假話等於製造新假話」），只寫現行判準：**這條管道一律不得奪焦、不得
# 要求點擊、不得留在螢幕上等人**。Windows 因此走托盤氣球（`_WIN_TOAST`），macOS 走
# `osascript display notification`，其餘走 `notify-send`——三者都是非模態的。
# 而且整條管道**預設關閉**（`NOTIFY_ENV`）：預設就不敲，是使用者的直接指令。
def notify(title: str, body: str) -> int:
    """盡力而為的**非模態**桌面通知；預設不敲。回 rc（見三個 `NOTIFY_*_RC` 與 127）。"""
    if not os.environ.get(NOTIFY_ENV):
        return NOTIFY_OFF_RC
    if sys.platform == "win32":
        argv = ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                "-Command", _WIN_TOAST.format(title=_ps_literal(title), body=_ps_literal(body))]
    elif sys.platform == "darwin":
        argv = ["osascript", "-e",
                f"display notification {json.dumps(body)} with title {json.dumps(title)}"]
    else:
        argv = ["notify-send", title, body]
    try:
        return subprocess.run(argv, capture_output=True, timeout=30, check=False,
                              creationflags=guard.NO_WINDOW).returncode
    except (OSError, subprocess.SubprocessError):
        return 127


def notify_queue_path() -> Path:
    """通知補投佇列的居所（同 `endurance_env.trace_dir()`，壽命與逃生口紀律一致）。"""
    return endurance_env.trace_dir() / NOTIFY_QUEUE_NAME


def _load_queue(path: Path) -> list[dict]:
    """讀佇列；讀不到／格式不對一律回空清單（量不到 ≠ 佇列裡真的沒有東西，但這裡的
    最壞代價只是少送一輪通知，不得升級為故障——同 `_write` 的既有紀律）。
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return raw if isinstance(raw, list) else []


def _save_queue(path: Path, items: list[dict]) -> bool:
    return _write(path, json.dumps(items, ensure_ascii=False, indent=2))


def queue_notify(title: str, body: str, rc: int, now: float) -> bool:
    """把一則投遞失敗的通知落進持久佇列；回「有沒有排進去」。

    `rc == NOTIFY_OFF_RC`（使用者**刻意**關掉這條管道，`NOTIFY_ENV` 未設）不入列——
    入列會讓預設關閉的桌面通知在每一次 loud 情境都排一則、重試三次後又出聲丟棄一次，
    與 R82／HELM-01「預設就不敲」的直接指令背道而馳。`rc == 0`（已送達）自然不入列。
    🔴 `NOTIFY_ENV` 未設時整支**提早短路**——不只是 `rc == NOTIFY_OFF_RC` 那一格：
    `alert()` 的 `NOTIFY_NO_RESCUE_RC`（沒東西要救時**根本不呼叫** `notify()`）與
    `NOTIFY_ENV` 無關、任何 `loud=True` 呼叫都會撞到它，若這裡不重複同一道關卡，
    佇列會在**每一個**現有測試（本檔數百支從未設過 `NOTIFY_ENV` 也從未預期本檔會碰
    `endurance_env.trace_dir()`）跑過 `alert()` 時，把記錄寫進**開發者真正的家目錄**
    ——本輪落地當回合全套實跑親自撞見：`SpendLimitReachesAHumanTest` 讀到同一台機器
    上其他測試遺留的 19 筆真實佇列項目並把它們全部標記「送達」。桌面通知本來就整條
    預設關閉，關掉時談「補投」沒有意義——沒有人在等一個永遠不會顯示的通知。
    """
    if rc == 0 or rc == NOTIFY_OFF_RC or not os.environ.get(NOTIFY_ENV):
        return False
    path = notify_queue_path()

    def _append() -> bool:
        items = _load_queue(path)
        items.append({"title": title, "body": body, "queued_at": now,
                     "attempts": 0, "last_rc": rc})
        return _save_queue(path, items)

    return quota_ledger.with_lock(path.with_suffix(".lock"), _append)


def redeliver_queued(now: float, log: Path, *, ttl: float = NOTIFY_QUEUE_TTL_SECONDS,
                     max_attempts: int = NOTIFY_QUEUE_MAX_ATTEMPTS) -> dict:
    """PRD_Amendment_R112 §3-4：每次巡邏重投佇列裡每一則。回稽核欄位（`{}`＝佇列空）。

    三個結局，逐則各自落痕跡（事件名與既有家族互異，同本檔一貫紀律）：
    送達＝`delivered=True`，移出佇列；逾 TTL 或重試次數用盡＝**出聲丟棄**（stderr，
    不靜默）＋移出佇列；仍失敗且未到上限＝原樣留著，下一次巡邏（≤900s）再試。
    """
    path = notify_queue_path()

    def _drain() -> tuple[list[dict], list[dict]]:
        items = _load_queue(path)
        if not items:
            return [], []
        kept: list[dict] = []
        results: list[dict] = []
        for item in items:
            title, body = str(item.get("title") or ""), str(item.get("body") or "")
            if now - float(item.get("queued_at") or 0) > ttl:
                print(f"🔴 通知逾期未送達，已丟棄（不靜默）：{title}", file=sys.stderr)
                results.append({"title": title, "delivered": False, "dropped": "ttl"})
                continue
            rc = notify(title, body)
            attempt = int(item.get("attempts") or 0) + 1
            if rc == 0:
                results.append({"title": title, "delivered": True, "attempt": attempt, "rc": rc})
                continue
            if attempt >= max_attempts:
                print(f"🔴 通知重投 {attempt} 次仍失敗，已丟棄（不靜默）：{title}",
                     file=sys.stderr)
                results.append({"title": title, "delivered": False,
                               "dropped": "max_attempts", "attempt": attempt, "rc": rc})
                continue
            kept.append({**item, "attempts": attempt, "last_rc": rc})
            results.append({"title": title, "delivered": False, "attempt": attempt, "rc": rc})
        _save_queue(path, kept)
        return kept, results

    kept, results = quota_ledger.with_lock(path.with_suffix(".lock"), _drain)
    for row in results:
        _append_trace(log, "notify_redelivered",
                      **{k: v for k, v in row.items() if k != "title"})
    return {"notify_queue_pending": len(kept)} if results else {}


# 🔴 R82／HELM-01 的第三面（殘骸）。前兩面（判定面、載具面）治的是「不該叫人的時候
# 叫了人」；本面治的是它留下的東西：`%TEMP%` 開場實測 26 份 `autosdd_resume_plan_*.md`，
# 其中三份是測試殘骸。每一份都對應一支已經下班（或從來沒開始）的哨兵，而沒有任何一段
# 程式碼負責把它們收掉 ⇒ 下一個人用 `Get-ChildItem` 看 `%TEMP%` 時拿到的是一堆過期事實
# （本 repo 對「查詢載具給出過期事實」有判例）。
# 判準刻意是**年齡**而不是「這支哨兵還在不在」：後者要問排程器，那是一次外部行程呼叫，
# 而這裡跑在終態路徑上、失敗不得升級為故障。年齡門檻的取值理由見 `PLAN_GC_AGE_SECONDS`。
#
# ══════════════════════════════════════════════════════════════════════════
# 🔴 R84／ARCH-06：「什麼時候可以刪任務書」收成**一個判準 ＋ 一個 unlink 站點**
# ══════════════════════════════════════════════════════════════════════════
# 病（`sentinel_lifecycle._sweep_artifacts` 的既有註解**自陳**過，而自陳不是機械物）：同一族
# 檔（`autosdd_resume_plan_*.md`）此前有**兩套刪除時機**——本檔按**齡**刪，`_sweep_artifacts`
# 按 **session_id** 刪四件。兩者今天不衝突只因判準軸不同（mtime vs id），而那一行自陳逐字
# 寫著「**改了一邊不會有任何東西轉紅**」⇒ 零機械物。任務書是〈可重啟點四條件〉第 2 條的
# 載體：任一邊把窗口改動一次，就可能刪掉另一邊還在等的那一份，而失效是靜默的
# （哨兵下一次醒來讀不到任務書 ⇒ `sentinel_aborted`，外觀與「正常下班」相近）。
#
# 收斂形狀（體例照 `Find-GitBash` 那條 SSOT 判例：知識只有一個家，消費者只提供輸入）：
#   · `plan_reap_verdict(path, session_id, now, age)` ＝**唯一的判準**。兩條規則、各自對應
#     一個呼叫端本來就有的輸入：**指名**（我知道這個 session 已終態）與**超齡**。
#   · `reap_plans(...)` ＝**唯一會 `unlink` 任務書的地方**。判準守衛＝
#     `tools/tests/test_mac_endurance_r83.py::PlanReapHasOneHomeTest`（全庫掃「同一個函式裡
#     同時出現任務書身分與 unlink」的站點，第二個家一律紅，含合成注入自證）。
# 🔴 `age=None` **不是**第二套政策，而是「這個呼叫端手上沒有年齡這個輸入」：GC 是拿著
#   `reap_verdict` 的裁決（這支哨兵已結束）來的，它要刪的就是那一份，與齡無關。判準仍然
#   只有一支——分歧留在**輸入**，不留在規則。
def plan_reap_verdict(path: object, session_id: str = "", now: float | None = None,
                      age: float | None = PLAN_GC_AGE_SECONDS, *, named: bool = False) -> str:
    """可以收這一份任務書嗎；回**理由字串**，`""`＝不收。純函式（紅綠由注入自證）。

    「指名」有兩種形態，因為兩個呼叫端手上的東西不同（**規則同一條，輸入不同**）：
    `named=True`＝呼叫端直接把那一份的**路徑**遞過來（終態路徑上的 `alert`，檔名不必帶
    前綴——它已經自己判過那是自己的任務書）；`session_id`＝呼叫端手上只有 **id**（GC 拿的
    是 `reap_verdict` 的裁決）。刻意不讓後者去猜前者：`gc_plans` 的 `current` 在既有測試裡
    就是一支叫 `plan.md` 的檔，用「名字必須帶前綴」去判它會**靜默少刪一份**（本輪實測：
    `test_the_silent_disarm_takes_its_own_plan_file_with_it` 當場轉紅，收斂前的行為是無條件刪）。
    """
    target = Path(str(path))
    if named:
        return "指名（呼叫端遞來路徑，已自行判定終態）"
    if session_id and target.name == f"{guard.PLAN_PREFIX}{session_id}.md":
        return f"指名（session `{session_id}` 已終態）"
    if age is None:
        return ""  # 沒有年齡這個輸入 ⇒ 只有「指名」那一條可能成立
    try:
        idle = (time.time() if now is None else now) - target.stat().st_mtime
    except OSError:  # 檔不在／stat 不動＝沒有可據以回收的事實，一律不收（量不到 ≠ 該刪）
        return ""
    return (f"超齡（{idle / 86400:.1f} 天未更新 ≥ {age / 86400:.0f} 天）"
            if idle >= age else "")


def reap_plans(*, session_id: str = "", root: object = None, now: float | None = None,
               age: float | None = PLAN_GC_AGE_SECONDS,
               extra: tuple = ()) -> list[str]:
    """**唯一**會刪 `autosdd_resume_plan_*.md` 的地方。回實際刪掉的檔名（可直接稽核）。

    `root` 是注入點：預設掃系統暫存（production 唯一的落點），測試把它指到沙箱——
    一支會真的去刪開發者 `%TEMP%` 的單元測試，是把驗證載具做成了副作用來源。
    `extra` 收「呼叫端手上那一份可能不在 `root` 底下」的情形（`gc_plans` 的 `current`）。
    """
    base = Path(str(root) if root else tempfile.gettempdir())
    victims = dict.fromkeys(base.glob(f"{guard.PLAN_PREFIX}*.md"), False)
    victims.update({Path(str(p)): True for p in extra})
    gone = []
    for path in sorted(victims):
        if not plan_reap_verdict(path, session_id, now, age, named=victims[path]):
            continue
        try:
            path.unlink()
        except OSError:
            continue  # 刪不掉最多是留著，不得反過來變成故障源（同 `_write` 的紀律）
        gone.append(path.name)
    return gone


def gc_plans(current: object = None, age: float = PLAN_GC_AGE_SECONDS,
             root: object = None) -> dict:
    """收掉任務書殘骸：`current` 這一份（終態了）＋ 所有超齡的。回稽核欄位。

    對外行為與簽名**逐字未變**（planner／`alert` 兩個呼叫端與既有測試都靠它）；改變的只有
    內部：判準與 unlink 都轉交上面那兩支，本函式只負責「把 `current` 換算成一個 session id
    這個輸入」。名字不帶前綴時換算出空字串 ⇒ 只剩超齡那一條，與修前對同一輸入同義。
    """
    name = Path(str(current)).name if current else ""
    sid = (name[len(guard.PLAN_PREFIX):-3]
           if name.startswith(guard.PLAN_PREFIX) and name.endswith(".md") else "")
    return {"gc_plans": len(reap_plans(session_id=sid, root=root, age=age,
                                       extra=(current,) if current else ()))}


# 終態的「叫人」。兩個呼叫端（哨兵的 `escalate`、續航探測的 `stop`）共用同一份——
# 這兩處此前各自寫了一行 `print(..., file=sys.stderr)`，而**兩處都跑在無 console 的
# 行程裡**：同一個缺口有兩個家，修一個等於沒修。
#
# 🔴 R82／HELM-01 的判定面在這裡收口成**三層，一層比一層吵**，而每一層的門檻都寫死在
# 參數上（不是靠呼叫端記得）：
#   · `loud=False`（＝哨兵正常下班／這個 session 根本沒開始）：**一個字都不留給人**，
#     只把殘骸收掉。這一層就是 HELM-01 的本體——它此前會走到最吵的那一層。
#   · `loud=True` 但 `dead_agents == 0`：寫紙（零打擾、人回來看得到），**不敲桌面**。
#   · `loud=True` 且 `dead_agents > 0`：這才是「有未處理撞線 **且** 有扇出待救」那個
#     合取——唯一值得主動打斷人的情形，因為只有人按得下 `resumeFromRunId`。
# `**_` 吃掉 `snapshot_fanout()` 回的其餘稽核欄位（`fanout`／`runs`／`fanout_written`），
# 讓呼叫端可以直接 `**fan` 攤進來而不必逐格挑——挑格子是下一個漏接的地方。
def alert(reason: str, state: dict, *, loud: bool = True, plan: object = None,
          dead_agents: int = 0, **_: object) -> dict:
    """終態處置：不吵時收殘骸；要吵時寫紙，且只有真的有東西要救才敲人。回稽核欄位。"""
    if not loud:
        return gc_plans(plan)
    fanout = fanout_path(str(state.get("session_id") or ""))
    note = note_path()
    ok = _write(note, "\n".join([
        "# 🔴 AutoSDD 續航協定：需要你動手",
        f"- 產生時間：{time.strftime(_STAMP)}",
        f"- 原因：{reason}",
        f"- session：`{state.get('session_id')}`",
        f"- 任務書：`{state.get('plan_path')}`",
        f"- 稽核痕跡：`{state.get('log_path')}`",
        "",
        "## 只有人做得到的動作",
        f"- 若原因是**月度支出上限**：到 {USAGE_URL} 提高上限。**排程等待對它無效**——"
        "它沒有 reset 可以等，等到天亮它還是滿的。",
        "- 若原因是探測次數用盡／解不出 reset 時刻：手動確認額度狀態後再重新武裝。",
        "",
        "## 被打死的扇出（若有）",
        f"- 清單：`{fanout}`" if fanout.is_file() else "- （本次沒有扇出續跑清單）",
        "- 🔴 `resumeFromRunId` 是**同 session only**，且沒有任何排程器按得到它。"
        "續跑要在活著的那個 session 內、由人或 AutoClaude 發動。",
        "",
        f"## 重啟指令\n```\nclaude -r {state.get('session_id')}\n```",
    ]) + "\n")
    rc = notify("AutoSDD 需要你", reason) if dead_agents else NOTIFY_NO_RESCUE_RC
    # DEF-200-236：`rc` 若不是「已送達」也不是「使用者刻意關掉」，落佇列讓下一次巡邏
    # 重投——`NOTIFY_NO_RESCUE_RC` 此前**永遠**到不了 `notify()`，等於這一類 halt
    # 通知結構上沒有第二次機會（R115 開閥實彈演練逐字重現 round-label-ok，見本檔 §3-4 立案段）。
    queued = queue_notify("AutoSDD 需要你", reason, rc, time.time())
    print(f"🔴 {reason}\n   ⚠️ 只有人做得到的動作 → {note}", file=sys.stderr)
    return {"note": str(note) if ok else "", "note_written": ok, "notify_rc": rc,
            "notify_queued": queued}


def main(argv: list[str]) -> int:
    """可重跑的殘骸清理入口：`python tools/lib/quota_escalation.py --gc-plans`。

    刻意做成本檔的 CLI 而不是 planner 的旗標：planner 的 `guardrail_cli` 餘裕實測只剩
    個位數行，而殘骸清理與「叫人／扇出清單」是同一個主題（都是寫在 `%TEMP%` 上、給人
    看的產物）。多開一支 CLI 檔才是本 repo 判過的護欄層自我增殖。
    """
    if "--gc-plans" not in argv:
        print("用法：python tools/lib/quota_escalation.py --gc-plans", file=sys.stderr)
        return 2
    print(f"已回收任務書殘骸 {gc_plans()['gc_plans']} 份"
          f"（門檻：{PLAN_GC_AGE_SECONDS // 86400} 天未更新）")
    return 0


if __name__ == "__main__":  # pragma: no cover
    # 🔴 本檔的 CLI 與升級路徑都印中文（用法字串、`已回收任務書殘骸 …`、`relay_problems`
    # 的 `🔴 {reason}`），而非 UTF-8 locale 下 stdout 直接 UnicodeEncodeError、stderr 降解
    # 成 \uXXXX（DEF-101-789 同型）。保護只掛在 `__main__`：本檔被 planner 與測試以模組
    # import，import 期換串流會污染載具。走 SSOT 而非就地 reconfigure，理由見
    # `tools/lib/platform_utils.py` 檔頭（那段實作曾被複製 8 份、6 份漏分支），且就地寫
    # 會撞 `test_platform_utils_dedup.py` 的 shrink-only 行內複本棘輪。
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    sys.exit(main(sys.argv[1:]))
