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

# 判讀原語。**刻意沒有 try/except**：能力提供者可以降級，判讀原語不行——給它
# fallback stub 等於讓同一份字面有第二個家，而且會用錯的答案靜默通過。
import quota_policy  # noqa: E402
from quota_limits import parse_reset_at, unhandled_limit_event  # noqa: E402

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
#: reset 多遠以內才值得「排程等它」。5 小時視窗最遠 5h、週視窗最遠 7 天，中間這個
#: 缺口大到不需要精確：取 6 小時。方向鎖守的是「七天後才 reset 的線不得被排程」。
RESET_ARM_HORIZON_SECONDS = 6 * 3600

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

QUOTA_BRANCH_ARM = "arm"
QUOTA_BRANCH_NOTIFY = "notify"
QUOTA_BRANCH_ESCALATE = "escalate"

#: 🔴 誠實劃界（R82／Q2-07 只做了一半）：月度支出上限唯一會回來的路徑，SSOT 在
#: `tools/lib/quota_escalation.py:USAGE_URL`。本檔**不 import 它**——那支模組在模組層
#: `import context_budget_guard`，本檔一旦 import 它就會在 hook 起動時把 hook 載入第二次
#: （見檔頭的單向規則）。所以這個字面今天還有兩個家；把 URL 下沉到一個雙方都能安全
#: import 的葉子模組（`quota_limits`）是正解，但那支檔不在本包的所有權內，已登記交棒。
#: 在此之前至少把**本檔內**原有的兩處字面收成一處（`reset_horizon_phrase`）。
USAGE_URL = "https://claude.ai/settings/usage"


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


def _aware(raw: object) -> datetime | None:
    """ISO 字串 → aware datetime；解不出來回 `None`。"""
    # 🔴 aware 是硬要求（R80 判準「naive 本地時間戳不得被持久化」）：naive 相減跨 DST
    # 會靜默差 3600 秒。本機時區不實施 DST ⇒ 這個缺陷在本機結構上重現不了。
    try:
        moment = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo is not None else None


def _blank(source: str) -> quota_policy.QuotaState:
    """量不到的 `QuotaState`：`axes == ()`，而**為什麼**量不到寫在 `source`／`reason`。"""
    return quota_policy.QuotaState((), "", source, source)


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
        return _blank("stale-cache")
    return quota_policy.QuotaState(axes, str(data.get("measured_at") or ""), "cache", "ok")


def reset_branch(resets_at: object, now: datetime) -> str:
    """95% 那道該做什麼：`arm`（排程等它）／`notify`（等沒有意義）／`escalate`（沒有 reset）。"""
    # 🔴 分支由**資料**決定，不由桶名決定（禁止寫死桶名清單：live payload 當時 17 個
    # 頂層鍵，`claude.exe` 內嵌名單只有 8 個 ⇒ schema 正在長）。三條線的差別本來就是
    # 「reset 有多遠」：five_hour ≤5h、weekly 最長 7 天、spend **根本沒有 reset**。
    # 這一條是設計洞不是細節：把「95% ⇒ 排程等 reset」寫成無條件，會在週額度上排一支
    # 七天後才響的工作，而痕跡全綠——那與 R59 事故同形。
    moment = _aware(resets_at)
    if moment is None:
        return QUOTA_BRANCH_ESCALATE
    delta = (moment - now).total_seconds()
    return QUOTA_BRANCH_NOTIFY if delta > RESET_ARM_HORIZON_SECONDS else QUOTA_BRANCH_ARM


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
    if quota_ledger is None:
        return False
    mark = Path(tempfile.gettempdir()) / "autosdd_quota_refresh.stamp"
    return quota_ledger.claim_once(mark, QUOTA_CACHE_TTL_SECONDS)


def quota_trace_path() -> Path:
    return Path(tempfile.gettempdir()) / QUOTA_TRACE_NAME


def degraded_stamp_path(source: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in source)
    return Path(tempfile.gettempdir()) / f"{DEGRADED_STAMP_PREFIX}{safe}.stamp"


def note_degraded(source: str, detail: str) -> str:
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
    # 而 L4 依設計必須不節流 ⇒ 換通道不換 rc。射程：`quota_gate()` 只由 PreToolUse 分支
    # 呼叫 ⇒ 事件名恆為真。完整立案與紅綠自證見 `QuotaDegradationReachesTheModelTest`。
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}, ensure_ascii=False))
    return msg


def refresh_quota_blocking(timeout: int = QUOTA_SYNC_TIMEOUT_SECONDS) -> bool:
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
        note_degraded("meter-missing", "取數器 import 不到（共用層不可達）")
        return False
    try:
        # 🔴 走 `measure_detail` 而不是 `measure`：舊版把失效理由丟掉，四種失效在這裡
        # 外觀相同 ⇒ 連要寫進痕跡的東西都不存在。
        reading, reason = quota_meter.measure_detail(timeout)
        if reading is None:
            note_degraded(reason, "同步取數失敗（本 TTL 視窗唯一的一次嘗試）")
            return False
        return quota_meter.write_cache(reading, quota_cache_path())
    except Exception:  # noqa: BLE001 — 取數失敗最多是仍然量不到，不得變成故障源
        note_degraded("meter-crashed", "取數器自己拋了例外（已吞掉，不阻斷）")
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


# 🔴 `reset_branch()` 唯一合法的輸入＝**產生 min 的那一軸**的 `resets_at`。此前餵的是
# `worst()` 挑出來的那一桶（pct 數值最大、與期程無關），於是「session 96%、10 分鐘後
# reset」很可能被 weekly 那一桶的 `resets_at` 蓋掉，分支就從 `arm`（排程等它）翻成
# `notify`（等沒有意義）——排程動作與訊息一起錯，而痕跡全綠。
# 回歸鎖：`test_context_budget_guard.py::QuotaDecisionEntryIsSingleTest`。
def binding_resets_at(decision: quota_policy.Decision) -> object:
    """產生 min 的那一軸的 `resets_at`；量不到（`binding is None`）時回 `None`。"""
    return decision.binding.resets_at if decision.binding is not None else None


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


def reset_horizon_phrase(branch: str, resets_at: object) -> str:
    """三支分支各自的「這條線的 reset 有多遠」——**唯一的家**（R82／Q2-07 的減法那一半）。

    🔴 halt 與 throttle 此前各自寫了一份幾乎逐字相同的三分支句子（含兩處硬寫的 URL），
    而既有鎖只認「沒有 reset 可以等」這個字樣、不認結構 ⇒ 兩份漂移不會有任何東西轉紅。
    收成一份之後，兩支呼叫端各自只補**自己的動作句**（halt＝排程是錯的動作、
    throttle＝這道節流不會自己解除），三支分支的字串仍**彼此不同**——那條不變式
    （否則「不排程」與「排不了」外觀相同）是被保留的，不是被參數化掉的。
    """
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：{USAGE_URL}"
    hours = RESET_ARM_HORIZON_SECONDS // 3600
    if branch == QUOTA_BRANCH_NOTIFY:
        return f"reset 在 {resets_at}（**遠超 {hours} 小時**）"
    return f"reset 在 {resets_at}（{hours} 小時內）"


# 🔴 **開頭不再印裸百分比**（R82／M7）：舊版第一行是「額度水位 54%（≥95%…）」，而裸的
# 「54%」正是掌舵者當場誤讀的**那個**形狀——那個數字沒有說自己是哪一桶、什麼時候 reset。
# 改由 `quota_policy.describe()` 逐軸渲染，每一個 % 都自帶 `kind=` 與剩餘分鐘（或明文
# 「reset 距離不明」），而且**每一軸都說**，不是只說最緊的那一格。
def quota_halt_message(decision: quota_policy.Decision, act: dict) -> str:
    """halt 的一次性訊息。三支分支**字串必須不同**，否則「不排程」與「排不了」外觀相同。"""
    head = (f"🔴 額度到達**停止**水位（最緊的一條＝{act['kind'] or '未知'}）⇒ **停止派發**："
            "所有扇出型工具本次一律不執行。\n"
            f"   {quota_policy.describe(decision)}\n"
            f"   任務書：{act['plan'] or '（寫不出來——逐字稿路徑不可得）'}\n")
    horizon = reset_horizon_phrase(act["branch"], binding_resets_at(decision))
    if act["posix"]:
        # 🔴 SA-B7：mac/Linux 上武裝入口本身就有 `os.name != 'nt'` 早退 ⇒ 若沿用
        # weekly 那支「不排程」的靜默路徑，「不排程」與「排不了」會長得一模一樣。
        return head + ("   ⚠️ 本平台**沒有排程載具**（schtasks 只在 Windows 成立）"
                       "⇒ 已寫任務書，但**沒有武裝任何喚醒**。mac/Linux 請自行以 "
                       "launchd／cron 掛，或留在這裡等人回來。\n")
    if act["branch"] == QUOTA_BRANCH_ARM and act["armed"]:
        return head + (f"   ✅ 已武裝喚醒（{horizon}）。憑證是 "
                       "`NextRunTime` 這個**值**，不是 rc：\n"
                       "      Get-ScheduledTask | Where-Object TaskName -like "
                       "'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo\n")
    if act["branch"] == QUOTA_BRANCH_ARM:
        return head + ("   ⚠️ 這一條的 reset 近在眼前、本來該武裝喚醒，但**這次沒有武裝**："
                       + ("哨兵逃生口有設（AUTOSDD_SENTINEL_OFF）。\n" if act["sentinel_off"]
                          else "拿不到逐字稿路徑 ⇒ 沒有可以掛的任務書。\n"))
    if act["branch"] == QUOTA_BRANCH_NOTIFY:
        return head + (f"   🔴 這一條的 {horizon} ⇒ 「等」幾乎沒有意義，"
                       "本次**刻意不排程**（排一支七天後才響的工作而痕跡全綠＝R59 事故同形）。"
                       "改做不吃額度的工作，或降扇出／切小模型。\n")
    return head + (f"   🔴 這一條{horizon} ⇒ 排程是錯的動作，"
                   "只有人去提額才會回來。\n")


# halt 帶用 `reset_branch()` 分得出 arm／notify／escalate，**throttle 帶此前完全不分**
# ⇒ 週額度偏高時 cap 會連續套用好幾天，與 five_hour 同水位（最多 5 小時）代價差一個
# 數量級，而訊息裡讀不出差別。
# 🔴 R82 訂正本段的舊結語（原文寫「本行只把差別說出來，**不動 cap 的階梯**，因為按 reset
# 距離分檔是政策決定」——那句話已被裁決推翻，故不留著當現行說法）：cap 現在**本來就**是
# `f(pct, horizon)` 的函式，reset 距離已經進了階梯本身；本行說的是同一件事的人話面，
# 兩者同源於 `quota_policy`，不是兩個判準。
def throttle_horizon_line(decision: quota_policy.Decision, now: datetime) -> str:
    """節流帶要說出「這道限制會套多久」。"""
    resets_at = binding_resets_at(decision)
    branch = reset_branch(resets_at, now)
    horizon = reset_horizon_phrase(branch, resets_at)
    if branch == QUOTA_BRANCH_ESCALATE:
        return f"   ⏳ 這一條{horizon} ⇒ 這道節流不會自己解除。\n"
    if branch == QUOTA_BRANCH_NOTIFY:
        return (f"   ⏳ 這一條的 {horizon} ⇒ 這道節流會**連續套用好幾天**，不是等一下"
                "就好。改做不吃額度的工作，或降扇出／切小模型。\n")
    return f"   ⏳ 這一條的 {horizon} ⇒ 這道節流很快就會自己解除。\n"


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


def quota_gate(payload: dict, *, blocking, latch_read, latch_write,
               plan_writer, waker) -> int:
    """額度軸的**獨立**判定入口。回 0＝放行、2＝擋下。不讀 context、不碰網路以外的東西。

    五個注入依賴全部來自 hook 端（見檔頭的單向規則）：`blocking`＝阻斷工具名單、
    `latch_read`／`latch_write`＝一次性閂鎖的讀寫、`plan_writer`＝任務書產生器、
    `waker`＝喚醒武裝（回 `{armed, sentinel_off, posix}`）。
    """
    tool = str(payload.get("tool_name") or "")
    if tool not in blocking:
        return 0  # 收斂（讀檔、寫任務書、跑 git）永遠不受額度節流影響
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
        note_degraded("policy-invalid", "；".join(problems))
    now = datetime.now().astimezone()
    state = read_quota(now)
    if not state.usable() and claim_refresh_slot():
        # 🔴 唯一會碰網路的一格，三個條件同時成立才到得了：扇出型工具 ＋ 已經量不到 ＋
        # 本 TTL 視窗還沒有人量過。理由與實測代價見 `refresh_quota_blocking` 的 WHY。
        refresh_quota_blocking()
        now = datetime.now().astimezone()
        state = read_quota(now)
    if not state.usable():
        floor = quota_floor_reading(payload, now)
        if floor is None:
            # 🔴 **不節流 ≠ 不出聲**（SD-B2）：這條路此前是零 stderr、零痕跡，與「額度
            # 很健康」外觀一模一樣。而「不節流」那一半已在 R82 被裁決推翻（見下方 cap）。
            note_degraded(state.source or "unknown",
                          "取數失敗，且逐字稿裡沒有未復原的撞線可以當地板")
        else:
            state = floor  # L3 地板：撞線且未復原 ⇒ 下界 100% ⇒ 落進 halt
    # 🔴 **整支 hook 唯一的判讀入口，恰好呼叫一次**（M10：「函式對了但沒人叫它」是本 repo
    # 反覆記載的『機制蓋好沒接電』）。量不到時 `decide()` 回 `degraded_cap`（不是不設限、
    # 也永不 halt）：R81 複審探針實測「快取過期 600s ＋ 額度 99%」時 42 次派發放行 42。
    decision = quota_policy.decide(state, now, policy)
    if decision.cap is None:
        return 0  # free 帶＝不設限（維持 shipped 行為：50% 以下無事可做）
    if decision.band == quota_policy.BAND_HALT:
        latch = quota_latch_path()
        act = quota_halt_actions(payload, decision, now,
                                 plan_writer=plan_writer, waker=waker)
        # 閂鎖鍵帶 (kind, reset 分鐘)：新的視窗＝重新武裝一次。截到分鐘是因為 `resets_at`
        # 有次秒級抖動（它是 now+剩餘算出來的），字串相等比較會每次都判「reset 變了」。
        key = f"halt@{act['kind']}@{str(binding_resets_at(decision))[:16]}"
        if key not in latch_read(latch):
            latch_write(latch, key)
            sys.stderr.write(quota_halt_message(decision, act))
        else:
            sys.stderr.write(f"🔴 {quota_policy.describe(decision)}\n"
                             f"   `{tool}` 仍然不執行（閂鎖已觸發過，任務書已在磁碟上）。\n")
        return 2
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
