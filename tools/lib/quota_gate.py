"""額度水位節流閘（訴求 a／b）：**與 context 水位完全分開的第二把尺**。

R82／Q2-02 的落地物。此前這一整條軸住在 `.claude/hooks/context_budget_guard.py` 裡，
佔該檔 535 raw 行（36%）——而它與 context 水位**零交集**：輸入是額度快取／逐字稿撞線，
輸出是「這次扇出准不准」，一個字都不碰 window 判定與 `block_verdict()`。

🔴 **搬移的方向與安全條件**（照抄 Q2-02 掃描結論，不是事後合理化）：
  · hook → 本檔是**單向**的。本檔**不得** import 那支 hook（`tools/lib/quota_escalation.py`
    走的是反向，那是它的既有契約，不是本檔可以照抄的先例）——雙向 import 會在 `runpy`
    以 `__main__` 起 hook 時把它整支載入第二次。
  · hook 端對本檔的 import 走 `try/except → None → 額度軸整條退化成「量不到」`，
    **不得** hard import：本檔缺席不可以把 context 阻斷也一起帶走。
  · 本檔要用到的四個 hook 端能力（阻斷工具名單／閂鎖讀寫／任務書產生器／喚醒武裝）
    一律**參數注入**，不反向取用。注入而不是 import 的理由是可測性：每一個依賴都能在
    測試裡換成假的，而不必去動 hook 的模組狀態。

🔴 **這是「搬家」不是「淨減」**（誠實劃界，R81 收尾包在同一個位置踩過）：repo 總行數
不因搬移本身變小。本檔內真正的減法只有兩處，各自具名：
  ① `reset_horizon_phrase()` 把 halt／throttle 兩支各自寫過一次的三分支句子收成一份；
  ② `arm_quota_wakeup` 的 spawn 實作退回 hook，與 `arm_sentinel` 合成同一支。

相依規則（同 hook 檔）：`tools/lib/*` 只准**裸名 import**——`from lib import X` 會讓
同一份原始碼在同一行程裡有兩個模組物件。能力提供者（meter／ledger）一律 try/except
退化成「量不到」；判讀原語（quota_limits／quota_policy）hard import，給 stub 等於讓同一份
字面有第二個家。

🔴 **R84／ARCH-10：上一段在寫下的當時是一句對磁碟為假的規則，本輪把磁碟改成真的。**
`tools/lib/quota_escalation.py` 曾是**唯一**以 `from lib import …` 被載入的同層模組
（兩個站點：`tools/session_resume_planner.py`、`tools/tests/test_context_budget_guard.py`），
兩者本輪一起改成裸名。危害不是假想：同一份原始碼以兩種寫法載入時實測是**兩個相異物件**
（`import quota_escalation` vs `from lib import quota_escalation` ⇒ `e1 is e2` → False），
於是「測試 patch 了一個、production 用的是另一個」這種靜默失效隨時可以發生。
🔴 射程誠實劃界：`from lib import …` 這個寫法在本 repo 別處仍大量存在（`check_script_parity`
／`archive_defect_log`／`sync_onboarding_baselines` …），本規則**不**宣稱管得到它們——
它管的是 quota 這一族，因為只有這一族同時被 hook 行程與 CLI 行程載入。
現查（本行落地後應**零**命中）：
`grep -rn "from lib import quota" tools .claude AutoClaude`

🔴 **R82／HELM-04 接線：本檔不再擁有任何門檻與階梯**（合議裁決規格 S2／S9）。此前
`QUOTA_THROTTLE_PCT=80`／`QUOTA_HALT_PCT=95`／`THROTTLE_FANOUT_CAP=2`／`quota_tier_of(pct)`
／`fanout_cap(pct)` 住在本檔，而它們**只吃一個純量**：`pct=79 @3 分鐘後 reset` 與
`pct=79 @240 分鐘後 reset` 的輸出逐字相同（實測 `tier=normal cap=None`），80 倍的時間
尺度差在程式裡結構上不存在。判讀整條搬到 `tools/lib/quota_policy.py`，本檔只負責
**取快取 → 呼叫 `decide()` 一次 → 記帳／擋下／說話**。五個符號一律**刪除不留 deprecated**：
留一個「暫時沒人叫」的版本等於把缺陷留在原地等下一個呼叫端（同 meter 對 `worst()` 的處置）。

回歸鎖：`tools/tests/test_context_budget_guard.py`（合成注入，逐條驗紅）。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 額度快取的**檔案契約**（檔名＋schema）與**取數**唯一的家＝`tools/lib/quota_meter.py`。
# meter 不可達時本符號為 `None`，額度軸整條退化成「量不到」＝不節流，而不是崩潰。
try:
    import quota_meter  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 能力提供者可降級（fail-open 是 P0）
    quota_meter = None  # type: ignore[assignment]

# 跨行程原語（派發帳／TTL 名額／痕跡）唯一的家＝`tools/lib/quota_ledger.py`。同一種
# fail-open：不可達時本符號為 `None`，扇出節流整條退化成「不記帳」。
try:
    import quota_ledger  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    quota_ledger = None  # type: ignore[assignment]

# 🔴 R88／LOC-01：排程**載具**的參照隨 `evidence_hint()` 一起搬到 `quota_messages.py`，
# 本檔**刻意不留**一份 `import schedule_backend`——搬移後它在本檔零使用，留著就是同一份
# 參照兩個家，而且是**會靜默騙人**的那一種：測試 patch 本檔這一份時，真正被呼叫的是
# `quota_messages` 那一份 ⇒ 「patch 了卻沒有生效」。這不是假想，本次搬移第一版就是這樣
# 被兩支既有測試抓到的（`QuotaHaltMessagePointsAtThisPlatformTest` 兩支同時紅）。

# 落款目錄的 SSOT。🔴 **持久目錄**（`~/.autosdd/traces`）而不是 `$TMPDIR`：R84／ZT-03 判過
# 系統暫存重開機即消失，而「事後查不到」不等於「沒發生」。跨窗攤提的換算比只能從**歷時**
# 差分推估 ⇒ 落款一蒸發，這條軸就永遠只有 0 個樣本、永遠走保守側。
# 刻意**沒有** try/except（同 `quota_limits` 那一行的判準）：它是一個純粹的路徑 SSOT，
# 自己就已經把「拿不到家目錄／目錄唯讀」退化成 `$TMPDIR`（見該檔 `trace_dir()`），
# 給它第二層 fallback 等於讓同一份退化知識有兩個家，而那正是本 repo 反覆判過的形態。
import endurance_env  # noqa: E402

# 判讀原語。**刻意沒有 try/except**：能力提供者可以降級，判讀原語不行——給它
# fallback stub 等於讓同一份字面有第二個家，而且會用錯的答案靜默通過。
import pace_contract  # noqa: E402  # R86：配速檔案契約的寫入端（引擎側唯一的傳遞方式）
import quota_pace  # noqa: E402  # R86：窗長／燃燒率／跨窗攤提（同樣是判讀原語）
import quota_policy  # noqa: E402
from quota_limits import parse_reset_at, unhandled_limit_event  # noqa: E402

# 🔴 R88／LOC-01：**人話面**整族搬到 `quota_messages.py`（立案與射程劃界見該檔檔頭）。
# 這裡 re-export 是為了讓四個既有消費端與測試沿用 `quota_gate.<name>` 零改動；
# 方向是單向的（本檔 → quota_messages），反向 import 會造成循環。
from quota_messages import (  # noqa: E402,F401
    QUOTA_BRANCH_ARM,
    QUOTA_BRANCH_ESCALATE,
    QUOTA_BRANCH_NOTIFY,
    RESET_ARM_HORIZON_SECONDS,
    USAGE_URL,
    _aware,
    binding_resets_at,
    evidence_hint,
    pace_line,
    quota_halt_message,
    quota_prepare_message,
    reset_branch,
    reset_horizon_phrase,
    throttle_horizon_line,
)

# ── 兩道的分工（掌舵者訴求 b 逐字；門檻值本身住 `quota_policy.ENV_SPEC`）─────────
#   水位偏高 ⇒ 少派 agent：扇出型工具受**滾動視窗派發預算**節制，超出即 `exit 2`（那次
#         呼叫不會發生）。這是機械的併發下降，不是印一行字給模型看。
#   halt 帶 ⇒ 停止並準備喚醒：扇出全擋（cap=0）＋ 一次性閂鎖（寫任務書 → 依 reset 距離分三支）。
#   🔴 本檔**不複寫任何一個數字**：四個錨點（50／70／85／95）與三檔 horizon 乘數的唯一的家
#      是 `quota_policy.Policy`／`ENV_SPEC`，且皆可由 `.env` 調整（訴求 6c）。

#: 滾動視窗長度。同樣是挑的：它決定「節流帶裡每小時最多派幾個」（2/5min ≈ 24/hr）。
#: 取滾動視窗而不是併發計數，理由是結構性的，見 `live_dispatches` 上方那段。
FANOUT_WINDOW_SECONDS = 300
#: 快取新鮮度上限。🔴 **不是**由「1.2pp/min 線性外推」推導的——那個推導已被第三個量測點
#: 證偽（視窗翻頁時 utilization 會**驟降** 48pp，這個量非單調、在邊界不連續）。它就是挑的，
#: 重量入口＝`python tools/lib/quota_meter.py --watch <秒>`，不另開探針檔。
QUOTA_CACHE_TTL_SECONDS = 180
#: 同步刷新的逾時上界（R81 收斂新增，見 `refresh_quota_blocking`）。取 4 秒的依據是量出來的
#: ——端點 RTT 三次實測 0.33／0.36／0.41 秒，4 秒約 10 倍餘裕；逾時的正確方向是
#: 「量不到」而不是「慢慢等」，因為這一格**在 hook 的關鍵路徑上**（那是刻意的取捨）。
QUOTA_SYNC_TIMEOUT_SECONDS = 4
#: 額度守衛的逃生口。刻意不沿用 hook 的 `AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF`：
#: 三者關掉的是三件不同的事（context 阻斷／續航哨兵／額度節流），共用一個開關會讓「我只是
#: 想暫時別被擋」順手把另外兩層一起關掉，而那件事沒有人會注意到。
QUOTA_OFF_ENV = "AUTOSDD_QUOTA_GUARD_OFF"
#: 🔴 `QUOTA_CAP_ENV`（`AUTOSDD_QUOTA_FANOUT_CAP`）的墓碑：cap 覆寫的讀取與夾制整條搬到
#: `quota_policy.ENV_SPEC`／`Policy.fanout_cap_override`（那裡它是**上限**，只收緊不放寬；
#: 舊版把它當乘法的 base，於是 `=8` 在 near 檔實得 16——一個名字叫 CAP 的旋鈕給出比使用者
#: 要求還鬆的值）。本檔留一個同名常數就是同一份字面兩個家，故連常數一起刪。

#: 🔴 **量到的失明面，寫成政策而不是寫成藉口**（SD-B1）。R81 實測：
#:  · `Workflow` 的 tool_result **47/47** 是「launched in background」⇒ 那次工具呼叫在
#:    內部 agent 生出來**之前**就結束了；
#:  · `%TEMP%` 的 `autosdd_sentinel_boot_*.log` 19 支，**沒有一支**的 sid 長得像 subagent
#:    ⇒ SessionStart hook 對 workflow 內部 agent **一次都沒有觸發過**；
#:  · 但 subagent 逐字稿裡 `PreToolUse:` 命中 136 次（Bash 105／PowerShell 25／Read 6）
#:    ⇒ 那些 agent **自己的每一次工具呼叫**都會跑本閘。
#: 合起來的結論：我們攔得到「派發」與「被派出去的人再往下派」，但攔不到「一個已經啟動的
#: workflow 在內部生出 42 個 agent」那一刻——**那一刻沒有任何 hook 會被叫到**。
#: ⇒ 既然一次 `Workflow` 啟動是一個**事後無法界住**的扇出，節流帶唯一誠實的處置就是
#: 不讓它啟動。這不是「擋不到所以放棄」，是把量到的失明面換成一條擋得住的政策。
UNBOUNDED_FANOUT_TOOLS = ("Workflow",)

#: 派發帳。🔴 **刻意不帶 session id**（SA-B5／SD-B1）：額度是 per-account 的單一池，而
#: 每個 subagent／每一次 headless 跑都有自己的 sid ⇒ per-sid 的帳等於 N 個載體各拿一份
#: cap，根本沒有界住帳號層級的燒用量。一個帳號、一份帳。
#: 🔴 它是**一個目錄**（一次派發＝一個目錄項），不是一個 JSONL 檔。換形態的理由是量出來
#: 的，見 `tools/lib/quota_ledger.py` 的 docstring（舊形態在 8 行程 × 40 筆的 barrier 探針
#: 下實測掉 30.9%、且撕行被靜默丟棄）。
FANOUT_LEDGER_NAME = "autosdd_quota_dispatch.d"
#: 降級痕跡（B2：「量不到」不得是靜默的）。per-account，同上不帶 sid。
QUOTA_TRACE_NAME = "autosdd_quota_degraded.jsonl"
#: 降級出聲的 per-source 閂鎖檔前綴。用 TTL 名額而不是 state 檔：後者是 read-modify-write，
#: 在 42 個平行 hook 下自己就會掉紀錄。
DEGRADED_STAMP_PREFIX = "autosdd_quota_degraded_"
#: 95% 閂鎖的家（同樣 per-account）。
QUOTA_LATCH_NAME = "autosdd_quota_latch.json"
#: 跨窗攤提的落款檔名（R86）。住持久目錄，見 `burn_ledger_path()`。
BURN_LEDGER_NAME = "quota_burn.jsonl"

#: 🔴 R88／LOC-01：分支字面、`USAGE_URL` 與三支期程 helper 一併搬到 `quota_messages.py`
#: （本檔頂部 re-export）。那支是**不 import 任何 hook 的葉子模組** ⇒ 上一版此處記載的
#: 「把 URL 下沉到雙方都能安全 import 的葉子模組是正解，但那支檔不在本包所有權內」
#: 這筆交棒，正解已經存在：`quota_escalation.py` 現在可以改指本檔搬去的那一份。


# 🔴 `quota_tier_of(pct)` 與 `fanout_cap(pct)` 的墓碑（R82／HELM-04，**刻意不留
# deprecated 版本**）。兩者都只吃一個純量水位，於是 `(水位, 距 reset 幾分鐘)` 這個二元組
# 的後半在簽章層就不存在——`fanout_cap(79)` 無論 reset 在 3 分鐘後還是 4 小時後都回同一個
# 答案。判讀改由 `quota_policy.decide()` 對**全部軸**做，本檔一個門檻都不持有。
# 回歸鎖：`tools/tests/test_quota_policy.py::TestM5ScanSurfaceScope`（掃本檔，
# 「只吃純量卻含決策詞」的函式定義即紅）＋ 本檔的
# `tools/tests/test_context_budget_guard.py::QuotaDecisionEntryIsSingleTest`（spy 半）。


# 🔴 立案（複驗鏡實測「全 repo 沒有任何 `.env` 載入器」）：`.env.example` 只是一份說明檔，
# 使用者照著把值寫進 `.env` 之後**沒有任何東西會去讀它** ⇒ 「設了沒生效而沒有人知道」，
# 正是訴求 6c 最容易假交付的一格。
# 優先序沿用本 repo 既有慣例（**env > 檔案**）：`.claude/settings.json` 的 `env` 區塊與
# shell 匯出的值必須贏過檔案，否則臨時覆寫會被一份忘了改的 `.env` 靜默吃掉。
# 讀不到檔一律當空（額度守衛不得因為缺一個選配檔就變成故障源）。
# 🔴 R82／C1：解析**不在本檔**。此前這裡自己寫了一份 `partition("=")` + `strip()`，
# 而生成端 `render_env_example()` 產出的是 `KEY=值<補白>#說明`（同一行）⇒ 說明整段留在
# 值裡，12 個帶值的鍵**全部**解析失敗、全部退回預設，而 `.env.example` 逐字宣稱「本檔
# 由 policy_env() 讀進來」。同一份格式知識住兩個家、只有生成端那個家被鎖住（判準拿生成
# 物跟自己比，從不呼叫消費者）。唯一的解析器現在是 `quota_policy.parse_env_text()`。
# `root` 是**注入點**（預設 repo 根）：沒有它就只能靠改真實 `.env` 來驗，而那件事
# 不可重入也留痕跡。
def policy_env(root: Path | None = None) -> dict:
    """門檻的環境來源：repo 根 `.env` 當**預設**、`os.environ` 覆寫（訴求 6c）。"""
    try:
        base = root or Path(__file__).resolve().parents[2]
        text = (base / ".env").read_text(encoding="utf-8")
    except OSError:
        return dict(os.environ)
    return {**quota_policy.parse_env_text(text), **os.environ}


# 🔴 R82／C2：**逃生口也必須吃 `.env`**，否則 `.env.example` 印出來的那四個開關是假話。
# 實測（複審鏡）：`.env` 裡設 `AUTOSDD_QUOTA_GUARD_OFF=1` ⇒ 仍 rc=2（沒放行）；設成真
# 環境變數 ⇒ rc=0。原因是三個逃生口（本檔的 `QUOTA_OFF_ENV`、hook 的 `SENTINEL_OFF_ENV`
# ／`GUARD_OFF_ENV`）讀的都是 `os.environ`，一律不經 `policy_env()`。
# 「安全逃生口靜默失效」比沒有文件更糟：人以為關掉了，守衛照擋，而兩者外觀相同。
#
# 修法刻意是**一次前置填充**而不是「把每個讀取點改寫成 policy_env()」，理由是射程：
# `SENTINEL_OFF_ENV` 有一個讀取點住在 `arm_sentinel()` 裡，而那段本輪由另一個包持有
# ⇒ 逐點改寫會留下一個改不到的縫，且那個縫**正是本條在治的靜默失效**。填充一次之後，
# 每一個 `os.environ.get(<我們自己宣告的鍵>)` 都會看到 `.env`，包括改不到的那一個。
# 三條硬邊界：
#   ① **只填 `ENV_SPEC` 宣告過的鍵**——`.env` 是本 repo 放機密的地方（api_key／DSN），
#      整份灌進 `os.environ` 會讓機密隨 `Popen` 繼承到子行程。白名單＝我們自己的 SSOT。
#   ② **只在該鍵於行程 env 缺席時才填**——優先序仍是 env > 檔案（同 `policy_env`）。
#   ③ 呼叫點是 hook 的 `main()`（不是模組層）：模組層副作用會讓「import 這支 hook 的
#      測試」被開發機上的 `.env` 影響，那是一種難以定位的跨測試污染。
def apply_env_defaults(env, root: Path | None = None) -> list[str]:
    """把 `.env` 裡我們自己宣告的鍵填成行程級預設；回「這次真的填了哪幾個」。"""
    values = policy_env(root)
    filled = []
    for spec in quota_policy.ENV_SPEC:
        if str(values.get(spec.name, "")).strip() and not str(env.get(spec.name, "")).strip():
            env[spec.name] = values[spec.name]
            filled.append(spec.name)
    return filled


def quota_cache_path() -> Path:
    """`tools/lib/quota_meter.py` 寫的那一份。

    🔴 **檔名與 schema 都不在本檔**：此前這兩個字面在 meter（唯一寫者）、讀者、測試檔
    各有一份**互不相關**的複本，而所有既有快取測試都傳明確 `path` 給 `read_quota()`
    ⇒ 「閘讀的正好是 meter 寫的那一支」這個**生產綁定零覆蓋**：改掉 meter 的
    `CACHE_NAME`，meter 寫新檔、閘讀不到 → `pct=None` → 永遠不節流，而全套測試照綠。
    meter 不可達時刻意回**目錄**本身（讀出來必是 OSError）⇒ 額度軸整條退化成「量不到」。
    """
    return (quota_meter.cache_path() if quota_meter is not None
            else Path(tempfile.gettempdir()))


def quota_schema() -> str:
    """快取 schema 字串；唯一的家在 meter。meter 不可達時回 `""`（⇒ 每份快取都判無效）。"""
    return quota_meter.SCHEMA if quota_meter is not None else ""


def fanout_ledger_path() -> Path:
    return Path(tempfile.gettempdir()) / FANOUT_LEDGER_NAME


def quota_latch_path() -> Path:
    return Path(tempfile.gettempdir()) / QUOTA_LATCH_NAME


def burn_ledger_path() -> Path:
    """跨窗攤提的落款（**持久目錄**，見檔頭 `endurance_env` 那段；沙箱走該檔的逃生口）。"""
    return endurance_env.trace_dir() / BURN_LEDGER_NAME


# 🔴 為什麼要落款：換算比 r（短窗 pp／長窗 pp）只能從**歷時差分**推估，而快取只存最新一
# 次 ⇒ 沒有落款就結構上沒有樣本。R86 實測今天三個時刻（21:24／22:16／22:29）的兩軸讀數
# 給出 r 的量級 6~15，而它們全部只活在對話裡——這一支就是把那種觀測變成可累積的資料。
# 同一個 `measured_at` 只寫一次：`--pace` 可能在同一份快取上被連呼數次。
# 失敗一律吞掉：落款是**取數的副產品**，不得讓 `--pace` 掛掉（同 `note_degraded` 的紀律）。
def record_burn(state: quota_policy.QuotaState, live: int = 0) -> bool:
    """把這一次的逐軸讀數 append 一列。回傳「有沒有真的寫」。"""
    if not state.usable() or not state.measured_at:
        return False
    try:
        path = burn_ledger_path()   # `trace_dir()` 自己 mkdir 過了，這裡不重複一份
        if path.exists() and state.measured_at in path.read_text(encoding="utf-8"):
            return False
        with path.open("a", encoding="utf-8") as handle:
            handle.write(quota_pace.row_of(
                state.measured_at, [(a.kind, a.pct) for a in state.axes], live))
    except OSError:
        return False
    return True


def burn_ratio() -> tuple:
    """`(r|None, note)`：由落款＋外部校準先驗推估換算比。樣本不足**說出來**。"""
    try:
        text = burn_ledger_path().read_text(encoding="utf-8")
    except OSError:
        text = ""
    return quota_pace.estimate_ratio(
        quota_pace.rows_from_jsonl(text) + list(quota_pace.SEED_OBSERVATIONS))


# 🔴 R86（Dev 包挖出、本檔修）：`source` 與 `reason` 現在可以**不同**。`source` 是分類器
# （降級痕跡的檔名、測試的相等鎖都吃它，必須是穩定的短字面），`reason` 是給人看的那一句。
# 病：畫面印「量不到任何一軸」，而事實是「資料在、只是超過 TTL」——**這兩者要求 operator
# 做不同的事**（前者去看網路／憑證，後者只要重量一次），而分不出來時人會往錯的方向查。
def _blank(source: str, reason: str = "") -> quota_policy.QuotaState:
    """量不到的 `QuotaState`：`axes == ()`，而**為什麼**量不到寫在 `source`／`reason`。"""
    return quota_policy.QuotaState((), "", source, reason or source)


# 🔴 **逐軸進、逐軸出**（R82／HELM-04）：舊版把 meter 挑好的那一桶投影成頂層
# `{pct, kind, resets_at}` 三個純量再回傳，於是其餘每一桶的 reset 期程在那一行被丟掉。
# 現在每一軸自帶自己的 `resets_at`，判讀層才有辦法算 `cap = f(pct, horizon)`。
# `resets_at` 一律**原字串原封不動**帶過去：轉本地／重新格式化會製造 naive 時間戳，
# 而跨 DST 的 naive 相減實測差 3600 秒且完全靜默（本 repo 已有具名機械物禁止持久化它）。
def read_quota(now: datetime, path: Path | None = None) -> quota_policy.QuotaState:
    """讀快取並判新鮮度。回 `QuotaState`；`axes == ()`＝量不到（`source` 說得出原因）。"""
    try:
        data = json.loads((path or quota_cache_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _blank("no-cache")
    if not isinstance(data, dict):
        return _blank("bad-cache")
    if data.get("schema") != quota_schema():
        # 🔴 「schema 升版了」與「根本沒有快取」是兩件事，而它們此前共用 `no-cache`
        # 這一個字面 ⇒ 痕跡讀起來一樣。schema 升版是**會發生**的（meter 自己記載過端點
        # 的頂層鍵正在長），而它的正確處置是去看 meter，不是去看網路。
        return _blank("schema-mismatch")
    measured = _aware(data.get("measured_at"))
    # `type(...) in (int, float)` 而不是 `isinstance`：`bool` 是 `int` 的子類，
    # `True` 會被 isinstance 收成 pct=1.0 這種假讀數（同 meter 的 `normalize_pct` 紀律）。
    axes = tuple(
        quota_policy.Axis(str(a.get("kind") or ""), float(a["pct"]), a.get("resets_at"),
                          a.get("group"), a.get("is_active"), a.get("severity"),
                          str(a.get("via") or ""))
        for a in data.get("axes") or []
        if isinstance(a, dict) and type(a.get("pct")) in (int, float))
    if measured is None or not axes:
        return _blank("bad-cache")
    if (now - measured).total_seconds() > QUOTA_CACHE_TTL_SECONDS:
        # 🔴 SA-B4：過期的舊值**不得直接被採信**。這個量非單調（視窗翻頁會驟降）也非
        # 等速（率完全取決於當下在做什麼），所以「上調一個安全邊際」同樣是猜。
        # ⇒ 降級到「量不到」，而量不到有自己的 cap（`degraded_cap`），不是不設限。
        # 出聲那一半的落點是 `note_degraded()`，由 `quota_gate()` 在該分支呼叫。
        # 🔴 R86：把 age／TTL 兩個數字帶進 `reason`——「量不到」與「量到了但太舊」在畫面上
        # 此前完全同形，而它們要求 operator 做的事不同（見 `_blank` 上方那段）。
        return _blank("stale-cache", f"stale-cache（資料在，但已 "
                      f"{int((now - measured).total_seconds())}s > TTL "
                      f"{QUOTA_CACHE_TTL_SECONDS}s ⇒ 重量一次即可，不是取數壞掉）")
    return quota_policy.QuotaState(axes, str(data.get("measured_at") or ""), "cache", "ok")


# 🔴 為什麼是「滾動視窗的派發率」而不是「in-flight 併發數」（SD-B1 的正面答覆）：
# 用 PreToolUse 記 dispatched、PostToolUse 記 completed 去算 in-flight，在這個 harness 上
# **恆讀 ≈0**——`Workflow` 47/47 是「launched in background」，那次呼叫在扇出開始前就結束、
# PostToolUse 當場觸發、completed 立刻追平 dispatched ⇒ cap 永遠綁不到。
# 而且那個形狀還自帶一個 SA-B6 的洩漏：被擋下的呼叫留下永遠不會有 completed 的 dispatched
# ⇒ 計數器只增不減、永久過度節流，外觀卻像「額度一直很緊」。
# 改記派發率之後兩個病一起消失：不需要 completed（不必動 PostToolUse 的註冊面）、
# 視窗一滾就自癒。而且**它更貼近被限制的資源**：額度是燒用量，不是併發數。
def claim_dispatch(root: Path, now: datetime) -> Path | None:
    """記一筆派發，回自己那一個目錄項。委派共用層，本檔不留第二份實作。"""
    return (quota_ledger.claim_dispatch(root, now.timestamp())
            if quota_ledger is not None else None)


def release_dispatch(entry: Path | None) -> bool:
    """把自己那一筆撤掉（`unlink` 自己 `O_EXCL` 建出來的目錄項，不是第二次 append）。"""
    return quota_ledger.release_dispatch(entry) if quota_ledger is not None else False


def live_dispatches(root: Path, now: datetime, window: int = FANOUT_WINDOW_SECONDS) -> int:
    """視窗內還算數的派發數。讀不到一律回 0（量不到 ≠ 節流）。

    🔴 **讀不懂的目錄項要出聲，不得靜默跳過**（SD-B1 required_change ②）：舊版對解析
    失敗的行 `except ValueError: continue`，於是撕行被丟掉、帳目變小，而變小的方向正好
    是「看起來還有預算」——一個只會往放行方向錯的計數器。
    """
    if quota_ledger is None:
        return 0
    floor = now.timestamp() - window
    live, unreadable = quota_ledger.count_dispatches(root, floor)
    if unreadable:
        note_degraded("ledger-unreadable", f"派發帳裡有 {unreadable} 個讀不懂的目錄項")
    quota_ledger.prune_dispatches(root, floor)
    return live


def claim_refresh_slot() -> bool:
    """本 TTL 視窗內還沒有人量過 ⇒ 佔住這個位子回 `True`。這是**成本節流器**。

    用一支獨立的嘗試痕跡（不是快取本身）當節流器，因為要記的是「試過了」不是「成功了」：
    端點掛掉時不會寫快取 ⇒ 沒有這一格，每一次扇出呼叫都會再去打一次端點。

    🔴 舊實作是 check-then-act，零原子性 ⇒ 16 個壁鐘 barrier 對齊的行程實測
    **CLAIM=16 SKIP=0**（設計意圖 1），也就是這個成本節流器在它唯一要治的情境下完全
    失效。原子性住在共用層的 `claim_once()`（`O_CREAT|O_EXCL`）。
    """
    return (quota_ledger.claim_once(refresh_stamp_path(), QUOTA_CACHE_TTL_SECONDS)
            if quota_ledger is not None else False)


# 🔴 R84：這一格從 `claim_refresh_slot()` 內的寫死路徑抽成一支可 swap 的函式，理由與
# `quota_trace_path`／`degraded_stamp_path` **逐字同構**（見那道 `trace_isolation_problems`
# 鎖的立案）：它是額度軸第三個落在生產暫存的檔，而唯一的差別是它此前**沒有注入點**
# ⇒ 任何走到刷新路徑的測試都會吃掉真的那個 180 秒名額，此後真的需要補量時靜默不補。
def refresh_stamp_path() -> Path:
    """成本節流器的痕跡檔（本 TTL 視窗內「已經有人試過量」的那一格）。"""
    return Path(tempfile.gettempdir()) / "autosdd_quota_refresh.stamp"


def quota_trace_path() -> Path:
    return Path(tempfile.gettempdir()) / QUOTA_TRACE_NAME


def degraded_stamp_path(source: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in source)
    return Path(tempfile.gettempdir()) / f"{DEGRADED_STAMP_PREFIX}{safe}.stamp"


def note_degraded(source: str, detail: str, *, event: str = "PreToolUse") -> str:
    """額度軸降級時**出一次聲 ＋ 留一行痕跡**；回「這一次真的說出口的那段話」（`""`＝沒說）。

    🔴 立案（SD-B2 四支注入探針，落地前實測全部 rc=0／stderr 0 bytes／零痕跡）：
    `quota_gate()` 在量不到且無地板時直接 `return 0`，而且是在任何狀態字被算出來**之前**
    ⇒ 「量不到」這個狀態在 production 一次都到不了。後果：token 過期、斷網、schema
    升版、meter import 失敗，四種情況與「額度很健康」外觀完全一致 ⇒ 全部不可偵測。
    本檔的第二個消費者是 `.env` 設錯（`load_policy` 的 `problems`）：同一個形狀。

    出聲帶 per-source TTL 閂鎖（不是每次都吵）：每次工具呼叫都出聲的守衛會被整個關掉，
    那是本 repo 反覆判過的形態。閂鎖用的是**原子的** `claim_once()`——42 個平行 hook
    同時降級時恰好一個說話，而不是 42 個一起說（或因為 state 檔互踩而說得沒有規律）。
    """
    if quota_ledger is None:
        return ""
    if not quota_ledger.claim_once(degraded_stamp_path(source), QUOTA_CACHE_TTL_SECONDS):
        return ""
    trace = quota_trace_path()
    quota_ledger.append_record(trace, {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source, "detail": detail, "pid": os.getpid(),
        "state": quota_policy.BAND_UNMEASURED})
    msg = (
        f"⚠️  額度水位**量不到**（source={source}）⇒ 本次不節流，扇出照常放行。\n"
        f"   這不是「額度很寬鬆」：{detail}。\n"
        f"   現查：`python tools/lib/quota_meter.py --json`（失敗時會印 reason）；"
        f"痕跡：{trace}\n"
        f"   （同一個 source 每 {QUOTA_CACHE_TTL_SECONDS} 秒只說一次）\n")
    sys.stderr.write(msg)
    # 🔴 R82／L4-02：stderr 在這條放行路上沒有讀者（契約自述：要 exit 2 才回饋給模型），
    # 而 L4 依設計必須不節流 ⇒ 換通道不換 rc。完整立案與紅綠自證見
    # `QuotaDegradationReachesTheModelTest`。
    # 🔴 R83／D3 訂正上一段那句已死的射程宣稱（原文逐字：「`quota_gate()` 只由 PreToolUse
    # 分支呼叫 ⇒ 事件名恆為真」）。本輪把閘接上 PostToolUse 之後那句話就是假的，而它的
    # 失效**外觀與「額度很健康」完全相同**：`hookSpecificOutput` 的 `hookEventName` 與
    # 實際事件不符時，Claude Code 直接把整個 `additionalContext` 丟掉 ⇒ 降級通報靜默失效
    # ——正是這支函式當初立案要治的那個病，只是改由接線引入。⇒ 事件名一律由呼叫端傳，
    # 本檔不再假設自己被誰呼叫。預設留 `PreToolUse` 是為了既有呼叫端的行為逐字不變。
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": event, "additionalContext": msg}}, ensure_ascii=False))
    return msg


def refresh_quota_blocking(timeout: int = QUOTA_SYNC_TIMEOUT_SECONDS, *,
                           event: str = "PreToolUse") -> bool:
    """**同步**量一次並寫進 `quota_cache_path()`；回「有沒有拿到新讀數」。

    🔴 這一格**推翻了**「網路呼叫永遠不在 hook 的關鍵路徑上」那條舊設計取捨，理由照實
    記下（不逐字複述原說法當現行說法）：舊形態是快取過期時 fire-and-forget 起一支刷新器、
    **本次仍用舊值判定**，而舊值被 `read_quota()` 正確地降級成「量不到」⇒ 淨效果是
    **過期就對任意規模的扇出全數放行**（複審探針實測：快取過期 600s／額度 99% 時，
    42 次 `Agent` 派發放行 42、擋下 0）。
    而「過期」是常態不是罕見：唯一的刷新呼叫點就在這條「已經量不到」的支線上、
    哨兵巡邏一次都不刷快取、TTL 又只有 180 秒 ⇒ 任何 ≥3 分鐘的非扇出工作之後，
    下一波扇出整批通過（本機佐證：刷新痕跡與快取 `measured_at` 之間 69 分鐘零自動刷新）。

    代價量過了，不是猜的：端點 RTT 實測 **0.33／0.36／0.41 秒**，逾時上界 4 秒；且它
    **只在扇出型工具**上、每 TTL 至多一次（`claim_refresh_slot`）⇒ 不是「給每一次工具
    呼叫加上網路延遲」那個被否決的形態。收斂型工具（讀檔、寫檔、跑 git）在上游
    `tool not in blocking` 就返回了，一次都碰不到這裡。
    """
    if quota_meter is None:
        note_degraded("meter-missing", "取數器 import 不到（共用層不可達）", event=event)
        return False
    try:
        # 🔴 走 `measure_detail` 而不是 `measure`：舊版把失效理由丟掉，四種失效在這裡
        # 外觀相同 ⇒ 連要寫進痕跡的東西都不存在。
        reading, reason = quota_meter.measure_detail(timeout)
        if reading is None:
            note_degraded(reason, "同步取數失敗（本 TTL 視窗唯一的一次嘗試）", event=event)
            return False
        return quota_meter.write_cache(reading, quota_cache_path())
    except Exception:  # noqa: BLE001 — 取數失敗最多是仍然量不到，不得變成故障源
        note_degraded("meter-crashed", "取數器自己拋了例外（已吞掉，不阻斷）", event=event)
        return False


def quota_floor_reading(payload: dict, now: datetime) -> quota_policy.QuotaState | None:
    """L3 地板：逐字稿裡有**未復原**的撞線 ⇒ 水位下界 100%。`None`＝連地板都沒有。

    🔴 ADR-XPLAT-005 §2.1 與 Quota_Review D03 都用「逐字稿那層地板永遠在」替 L4 不節流
    辯護，而實作端 `quota_gate()` 曾**一次都沒有呼叫過** `unhandled_limit_event()`
    ⇒ 那層地板當時只存在於文件裡。這裡把它真的接上：離線、零 token、不依賴網路，
    正是 meter 全死時唯一還算數的證據。
    """
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    if transcript is None or not transcript.is_file():
        return None
    event = unhandled_limit_event(transcript)
    if event is None:
        return None
    reset = parse_reset_at(event.get("text"), now)
    # 單軸的 `QuotaState`：地板只知道「這一條線撞了」，對其餘各軸零資訊 ⇒ 不得假造它們。
    return quota_policy.QuotaState(
        (quota_policy.Axis(kind=str(event.get("kind") or ""), pct=100.0,
                           resets_at=reset.isoformat() if reset else None,
                           via="transcript-floor"),),
        now.isoformat(timespec="seconds"), "transcript-floor", "transcript-floor")


def quota_halt_actions(payload: dict, decision: quota_policy.Decision, now: datetime, *,
                       plan_writer, waker) -> dict:
    """halt 閂鎖那一刻真的做的事。回稽核欄位（給訊息與測試讀）。

    `plan_writer(transcript) -> str` 與 `waker(transcript, plan) -> dict` 都由 hook 端
    注入：spawn 與平台判斷（`os.name`／哨兵逃生口）是 hook 行程的事，本檔只讀它們的回報。
    🔴 哨兵的既有逃生口在這裡也算數：關掉時**必須在訊息裡說出來**——「關掉了所以沒武裝」
    與「武裝了」外觀相同就是假綠。
    """
    branch = reset_branch(binding_resets_at(decision), now)
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    plan = plan_writer(transcript) if transcript and transcript.is_file() else ""
    arm = waker(transcript, plan) if branch == QUOTA_BRANCH_ARM else {}
    return {"branch": branch, "plan": plan, "armed": bool(arm.get("armed")),
            "sentinel_off": bool(arm.get("sentinel_off")), "posix": bool(arm.get("posix")),
            "kind": decision.binding.kind if decision.binding is not None else ""}


def quota_prepare_actions(payload: dict, decision: quota_policy.Decision, now: datetime, *,
                          latch_read, latch_write, plan_writer) -> str:
    """真的做那三件事（出聲／寫任務書／一個視窗一次）。回「這次寫出來的任務書路徑」。"""
    latch = quota_latch_path()
    key = f"prepare@{decision.binding.kind}@{str(binding_resets_at(decision))[:16]}"
    if key in latch_read(latch):
        return ""
    latch_write(latch, key)
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    plan = plan_writer(transcript) if transcript and transcript.is_file() else ""
    sys.stderr.write(quota_prepare_message(decision, plan, now))
    return plan


# ── 6b 第二半：「我現在能派幾個 agent」的**人機出口**（R84／SA-02）─────────────────
# 🔴 立案：全 repo 沒有任何出口能回答這個問題——band／cap／距 reset 只在**被擋下時**才
# 現身（`describe()` 的唯一呼叫端是本檔三個 stderr 寫入點）。實測 `python
# tools/lib/quota_policy.py` → rc=2 只印用法；`quota_meter.py --from-cache --json` → rc=0
# 但全文無 band／cap／pace／recommended。也就是舵手每天派工前需要的那個數字，今天唯一
# 的取得方式是先撞牆。CLI 掛在 `tools/session_resume_planner.py --pace`（那支是既有的
# 人機入口），本檔只提供內容——渲染與判讀在同一個家，不另開第二份。
# 🔴 **零 token**：只讀快取；快取不可用時每 TTL 至多補量一次（`claim_refresh_slot()`），
#   而那一次打的是 `/api/oauth/usage`——**不是模型推論**（見 `quota_meter.USAGE_URL`），
#   不吃額度、不進 5 小時視窗。派工前查一次不會讓被查的那個數字變大。
def pace_state(now: datetime) -> quota_policy.QuotaState:
    """讀快取；不可用且本 TTL 還沒人量過時補量一次。"""
    state = read_quota(now)
    if state.usable() or quota_meter is None or not claim_refresh_slot():
        return state
    reading = quota_meter.measure_detail(QUOTA_SYNC_TIMEOUT_SECONDS)[0]
    if reading is not None:
        quota_meter.write_cache(reading, quota_cache_path())
    return read_quota(datetime.now().astimezone())


# 🔴 R86：多出的第三行是**攤提**（掌舵者不滿的直接原因）。他看到「短窗 16% used／45 分鐘
# 就 reset」卻只能派 2 個，而畫面只寫 `binding=seven_day` ⇒ 讀起來像程式抓錯或過度保守。
# 那一行現在自己回答「為什麼空著也不能衝」：本窗分攤到的長窗配額是多少、已用多少、
# 還剩幾分鐘會蒸發。落款則在同一次呼叫裡 append 一列——**查一次就多一個樣本**，
# 而換算比只能從歷時差分來（見 `record_burn` 上方那段）。
def pace_report(now: datetime | None = None) -> str:
    """`--pace` 的全文：第一行是那個數字，第二行起是逐軸明細（每個 % 都帶 kind 與分鐘）。"""
    now = now or datetime.now().astimezone()
    policy, problems = quota_policy.load_policy(policy_env())
    state = pace_state(now)
    # 🔴 `live` 落款進去是為了**下一輪**：per-agent 燃燒率＝Δpct ÷（Δ分鐘 × 併發數），
    # 而併發數不記下來就永遠算不出來（本輪的 r 只到「每 pp 換幾 pp」這一層）。
    record_burn(state, live_dispatches(fanout_ledger_path(), now))
    ratio, ratio_note = burn_ratio()
    decision = quota_policy.decide(state, now, policy, ratio, ratio_note)
    # 🔴 R86 跨包：引擎（`autoclaude/`）**不准** import 本層（`.importlinter` 的
    # `no-harness-import`）⇒ 唯一的傳遞方式是檔案契約。fail-soft 在 `pace_contract.write`
    # 內（寫不進去只在 stderr 說一次，`--pace` 的 rc 與那一行輸出都不受影響）。
    pace_contract.write(decision, state, policy.max_fanout, policy.halt_pct)
    tail = f"\n⚠️ .env 有設錯：{'；'.join(problems)}" if problems else ""
    return (f"{pace_line(decision)}\n  {quota_policy.describe(decision)}\n"
            f"  {quota_pace.explain(decision.amort)}\n  {posture_line()}\n"
            f"  來源={state.source} 量測於={state.measured_at or '(無)'}{tail}\n")


def posture_line(path: Path | None = None) -> str:
    """派工**前置檢查**那一行：帳號指紋 ＋ credits 姿態（R87／`DEF-200-R87-spend`）。

    🔴 掌舵者裁決逐字：「配置 Agents 前，要先知道 Account Type and Account 是否有
    Usage credits 再進行配置」。事故當下 `--pace` 只講得出水位，講不出
    「訂閱窗用完之後還有沒有救」——而後者才是 13 個 subagent 全滅的直接原因。

    🔴 三種讀不出來的情形一律回報**無 fallback**（保守方向）：快取不可用、
    取數層版本較舊（沒有 `posture` 欄）、欄位形狀不對。「量不到 ≠ 量到零」。
    """
    try:
        data = json.loads((path or quota_cache_path()).read_text(encoding="utf-8"))
        posture = data["posture"]
        fingerprint = tuple(posture["plan_fingerprint"])
    except (OSError, ValueError, KeyError, TypeError):
        return "派工前置：帳號姿態讀不出來 ⇒ 一律當作**無 credits fallback**（保守）"
    if not posture.get("credits_present"):
        state = "此帳號**沒有** usage credits ⇒ 訂閱窗本身即硬牆"
    elif posture.get("fallback_available"):
        state = "credits **可用** ⇒ 訂閱窗用完後仍有 fallback"
    else:
        why = "已耗盡" if posture.get("credits_exhausted") else ""
        why += "、" if why and not posture.get("credits_enabled") else ""
        why += "已停用" if not posture.get("credits_enabled") else ""
        state = f"credits {why} ⇒ **無 fallback**，訂閱窗即硬牆"
    return f"派工前置：方案指紋={'+'.join(fingerprint) or '(空)'}｜{state}"


def quota_throttle_message(decision: quota_policy.Decision, tool: str, live: int,
                           now: datetime) -> str:
    """節流帶的訊息。同 halt：**一個裸百分比都不准出現**（M7），逐軸帶 kind 與剩餘分鐘。"""
    cap, head = decision.cap, f"⚠️  {quota_policy.describe(decision)}\n"
    if tool in UNBOUNDED_FANOUT_TOOLS:
        return (head + f"   ⇒ `{tool}` 本次不執行。理由不是「太多」而是「數不到」："
                "一次 Workflow 啟動會在背景生出未知數量的 agent，而那一刻**沒有任何 hook "
                "會被叫到**（實測：tool_result 47/47 是「launched in background」）⇒ 事後"
                f"界不住。請改逐個派 `Agent`（每 {FANOUT_WINDOW_SECONDS}s 最多 {cap} 個）。\n"
                + throttle_horizon_line(decision, now))
    return (head + f"   ⇒ 少派 agent：每 {FANOUT_WINDOW_SECONDS}s 最多 {cap} 次扇出，"
            f"本視窗已用 {live} 次 ⇒ `{tool}` 本次不執行。\n"
            "   等一下再派，或改做不需要扇出的收斂工作（讀檔／寫檔／跑測試都沒有被擋）。\n"
            + throttle_horizon_line(decision, now)
            + f"   逃生口：設 {QUOTA_OFF_ENV}=1（關掉整條額度節流）；門檻與 cap 一律改 "
            "`.env`（清單＝`python tools/lib/quota_policy.py --print-env-example`）。\n")


# 🔴 R83：`event` 是本函式**唯一**的接線參數，它決定兩件不同的事——
#   · **射程**：`PreToolUse` 只在扇出邊緣判（收斂型工具不受節流）；`PostToolUse` 則對
#     註冊面上的每一個工具都判，因為那條路才是**真的在燒額度**的那條路。立案是量出來的
#     （R83 實測）：配額 5%→90% 的整段，主 session 在派完最後一波 subagent 之後**再也沒有
#     呼叫任何扇出型工具**（後續全是 6 分鐘全樹跑 ×4、24 個 agent 的回傳、大量讀檔），
#     於是本閘從頭到尾**一次都沒有被叫到**。它守的是「我要不要多派人」，而燒掉額度的是
#     「我自己在做事」——那條路上一個觀測者都沒有。
#     ⇒ 這不是參數沒調對，是結構缺口；`event` 就是那個缺的端子。
#   · **派發帳的歸屬**：只有 `PreToolUse` 那一次是「派發」。同一個 `Task` 會先觸發
#     PreToolUse 再觸發 PostToolUse，兩邊都記帳就是同一次派發記兩次（滾動視窗預算當場
#     少一半），所以 PostToolUse 在判讀完成後就返回，不進帳、不擋節流帶。
# 🔴 說明寫成 `#` 而不是 docstring 是**被迫也是被指示的**：`count_loc` 排除純 `#` 行但
# 計入 docstring 行，而本檔 tier 餘裕只有 2 行；`check_loc_budget.py` 自己的輸出逐字建議
# 「說明文字請寫成 `#` 註解而非 docstring」。第一版把這段寫進 docstring ⇒ 當場 410>400 破閘。
def quota_gate(payload: dict, *, blocking, latch_read, latch_write,
               plan_writer, waker, event: str = "PreToolUse") -> int:
    """額度軸的**獨立**判定入口。回 0＝放行、2＝擋下。不讀 context、不碰網路以外的東西。

    五個注入依賴全部來自 hook 端（見檔頭的單向規則）：`blocking`＝阻斷工具名單、
    `latch_read`／`latch_write`＝一次性閂鎖的讀寫、`plan_writer`＝任務書產生器、
    `waker`＝喚醒武裝（回 `{armed, sentinel_off, posix}`）。`event`＝本次是哪個 hook
    事件（射程與派發帳歸屬皆由它決定，見上方那段）。
    """
    tool = str(payload.get("tool_name") or "")
    if event == "PreToolUse" and tool not in blocking:
        return 0  # 扇出邊緣才看名單：收斂（讀檔、寫任務書、跑 git）不受額度節流影響
    # 🔴 R82／C2：逃生口與門檻讀**同一份**合併視圖（`.env` 當預設、真 env 覆寫）。
    # 舊版讀 `os.environ` ⇒ `.env` 裡設的那個開關是假話。判準往下挪一格是**行為等價**的
    # （非扇出型工具兩條路都回 0），換到的是「本檔只讀一次環境」。
    env = policy_env()
    if str(env.get(QUOTA_OFF_ENV, "")).strip():
        return 0
    policy, problems = quota_policy.load_policy(env)
    if problems:
        # 🔴 `.env` 設錯**必須出聲一次**：`load_policy` 已經退回整組預設，而「設了沒生效」
        # 與「設了而且生效」在行為上完全相同 ⇒ 不說就沒有人會知道（訴求 6c 的假交付面）。
        note_degraded("policy-invalid", "；".join(problems), event=event)
    now = datetime.now().astimezone()
    state = read_quota(now)
    if not state.usable() and claim_refresh_slot():
        # 🔴 唯一會碰網路的一格，三個條件同時成立才到得了：扇出型工具 ＋ 已經量不到 ＋
        # 本 TTL 視窗還沒有人量過。理由與實測代價見 `refresh_quota_blocking` 的 WHY。
        refresh_quota_blocking(event=event)
        now = datetime.now().astimezone()
        state = read_quota(now)
    if not state.usable():
        floor = quota_floor_reading(payload, now)
        if floor is None:
            # 🔴 **不節流 ≠ 不出聲**（SD-B2）：這條路此前是零 stderr、零痕跡，與「額度
            # 很健康」外觀一模一樣。而「不節流」那一半已在 R82 被裁決推翻（見下方 cap）。
            note_degraded(state.source or "unknown",
                          "取數失敗，且逐字稿裡沒有未復原的撞線可以當地板", event=event)
        else:
            state = floor  # L3 地板：撞線且未復原 ⇒ 下界 100% ⇒ 落進 halt
    # 🔴 **整支 hook 唯一的判讀入口，恰好呼叫一次**（M10：「函式對了但沒人叫它」是本 repo
    # 反覆記載的『機制蓋好沒接電』）。量不到時 `decide()` 回 `degraded_cap`（不是不設限、
    # 也永不 halt）：R81 複審探針實測「快取過期 600s ＋ 額度 99%」時 42 次派發放行 42。
    decision = quota_policy.decide(state, now, policy)
    if decision.band == quota_policy.BAND_HALT:
        latch = quota_latch_path()
        # 閂鎖鍵帶 (kind, reset 分鐘)：新的視窗＝重新武裝一次。截到分鐘是因為 `resets_at`
        # 有次秒級抖動（它是 now+剩餘算出來的），字串相等比較會每次都判「reset 變了」。
        # 🔴 R83／D2：`kind` 改由 `decision` 直接算，好讓**副作用整段移進閂鎖之內**。
        # 舊順序無條件先跑 `quota_halt_actions()`（它會寫一份任務書 ＋ spawn 一支
        # planner），只有訊息受閂鎖節制。在只有 PreToolUse×扇出會呼叫本閘的年代那還撐得
        # 住；接上 PostToolUse 之後，那就是「95% 之後每一次 Read／Bash 都 spawn 一支
        # planner」＝ spawn 風暴，而它在 halt 帶會一直持續到 reset。⇒ 這一格是接電的
        # **硬前置**，不是順手清理。`binding` 在 halt 帶結構上不可能是 `None`：`decide()`
        # 是唯一的 `Decision` 產生者，而它回 `binding=None` 的那一支把 band 寫死成
        # `BAND_UNMEASURED`（見該檔 `decide()`）。
        key = f"halt@{decision.binding.kind}@{str(binding_resets_at(decision))[:16]}"
        if key not in latch_read(latch):
            latch_write(latch, key)
            act = quota_halt_actions(payload, decision, now,
                                     plan_writer=plan_writer, waker=waker)
            sys.stderr.write(quota_halt_message(decision, act))
        else:
            # 🔴 R83：此句原本逐字說「`{tool}` 仍然不執行」——那在 PostToolUse 上是**假話**
            # （那次 Read／Bash 已經執行完了，PostToolUse 的 exit 2 只回饋 stderr）。訊息裡
            # 混一句假話比少一欄更難看見，故改成對兩個事件都為真的說法。
            sys.stderr.write(f"🔴 {quota_policy.describe(decision)}\n"
                             "   額度仍在停止水位：扇出一律不執行，任務書已在磁碟上。\n")
        return 2
    # 🔴 R84／6C（SA-03）：prepare 帶（85~95%）的準備動作。位置刻意在 halt **之後**、
    # 在下面那道早退**之前**——早退對 `PostToolUse` 與 free 帶無條件 `return 0`，把這一段
    # 放在它後面就等於一行都到不了（那正是本缺陷的形狀：函式對了但沒人叫它）。
    # 🔴 R84／SA84-02 訂正本行的**射程**（原文逐字寫「兩個事件都走這裡」，那是假話）：
    # `PostToolUse` 涵蓋註冊面上的每一個工具；`PreToolUse` 只在**扇出邊緣**到得了這裡
    # ——本函式第一格對 `tool not in blocking` 就 `return 0`，收斂型工具連 `policy_env()`
    # 都沒讀到。實測（86% 快取、`tool=Read`）：`PostToolUse rc=0 stderr=409B prepare=1`／
    # `PreToolUse rc=0 stderr=0B prepare=0`（96% 同形，只是落在 halt 帶而更早返回）。
    # 那不是缺陷而是設計：`test_pre_tool_use_on_a_convergent_tool_is_still_silent_by_design`
    # 正是釘住「PreToolUse×收斂型工具必須靜默」這一格。上面 6C 立案段記的「兩個事件皆
    # 靜默」講的是**接電前**的狀態，與本行講的「誰到得了這裡」是兩件事，別混讀。
    # 本段不改任何 rc。
    if decision.band == quota_policy.BAND_PREPARE:
        quota_prepare_actions(payload, decision, now, latch_read=latch_read,
                              latch_write=latch_write, plan_writer=plan_writer)
    # free 帶＝不設限（維持 shipped 行為：50% 以下無事可做）。
    # 🔴 R83：這道早退**從 halt 之前移到 halt 之後**，且與「PostToolUse 只觀測」併成一道。
    # 移動是行為等價的：`cap is None` ⟺ binding 落在 free 帶，而 halt 帶的 cap 恆為 0
    # ⇒ 兩個條件互斥，先後不影響任何一條路。併成一道是為了不多佔 tier 餘裕（本檔只剩
    # 2 行），而語意上它們確實是同一件事：**這一次不是「派發邊緣」，所以沒有帳要記、
    # 也沒有節流要擋**——派發帳只屬於 PreToolUse 那一刻（見本函式 docstring）。
    if decision.cap is None or event != "PreToolUse":
        return 0
    cap = decision.cap
    # 🔴 R82 訂正判準（舊版是「只要不是 normal 帶就擋 Workflow」）：那條在新階梯下會讓
    # 55% 這種**還很寬鬆**的水位把 `Workflow` 整個鎖死。改成「cap 已收斂到 converge 檔
    # 以下才擋」——notice 帶（cap 8）放行，prepare／halt 仍然擋。
    if tool in UNBOUNDED_FANOUT_TOOLS and cap <= policy.cap_converge:
        sys.stderr.write(quota_throttle_message(decision, tool, 0, now))
        return 2
    root = fanout_ledger_path()
    # 🔴 先記帳再數（含自己這一筆），而不是先數再記：42 個 `Agent` 在同一則 assistant
    # message 裡平行派發時 PreToolUse 是平行觸發的 ⇒ 先數再記會讓它們全部讀到 live<cap
    # 而全數放行。先記再數之後，**目錄項的建立順序**替我們排了序，後到的看得到前面的。
    #
    # 🔴 舊實作的 `undo` 是**第二次 append**，而 append 在 Windows 上跨行程不是原子的 ⇒
    # 20 個平行 Agent 的探針量到 `try=20 undo=17`（各應為 20），`live_dispatches()` 讀回 3、
    # cap=2，於是接著單獨派 1 個 Agent（遠低於 cap）**被幽靈計數擋下**（rc=2）。也就是說
    # 「極端競態下全數擋下是安全方向」那句話掩蓋掉的正是 SA-B6 要治的永久過度節流。
    # 現在記帳與撤銷各自是**一次原子的目錄項變動**（建立／刪除自己那一個），兩個方向的
    # 掉帳都不存在——實測見 `tools/lib/quota_ledger.py` docstring 的三組 barrier 探針。
    entry = claim_dispatch(root, now)
    live = live_dispatches(root, now)
    if live <= cap:
        return 0
    # 🔴 SA-B6：被擋下的呼叫**不得**在帳上留下永久佔位，否則節流期間計數器只增不減，
    # 一旦到 cap 就永遠回不來（即使 quota 已經掉回 50），而失效方向是永久過度節流、
    # 外觀像「額度好像一直很緊」。
    release_dispatch(entry)
    sys.stderr.write(quota_throttle_message(decision, tool, live - 1, now))
    return 2
