# QuotaMeterPort — 「帳號額度水位」這一軸的抽象（R82 / ACQ-01；ADR-XPLAT-005 §2.4 載體二）。
#
# 🔴 為什麼需要一個新的軸，而不是複用 token_guard 既有的 80/90 兩道門：
#   那兩道門的分母是**該模型的 context window**（token_tracker.py 逐行：
#   used = input + cache_read + cache_creation，window = max(modelUsage[*].contextWindow)），
#   與帳號方案完全無關。使用者要的是「水位用 %、因為啟動帳號不同」＝**額度**那一軸。
#   兩者數字接近（80/90 vs 80/95）反而更危險——名字像有人守，其實守的是別的東西。
#
# 🔴 為什麼是 port 而不是直接 import 根層 tools/lib/quota_meter.py：
#   AutoClaude 是可安裝套件，`tools/` 只是它此刻所在的 monorepo harness；pip install 之後
#   那個模組根本不存在（ADR-XPLAT-004 §4：套件不得依賴 harness 內臟）。
#   合規路徑＝**檔案契約**：adapter 只讀 %TEMP%/autosdd_quota.json。
#   這個方向現在真的有閘門了：.importlinter 的 no-harness-import contract（R82 ACQ-02）。
#
# 🔴 R82／C6 的**誠實劃界：這一軸「已設計、未接線」，缺的是刷新者不是讀者。**
#   全 repo 唯一會寫這份快取的地方是 harness 的 `tools/lib/quota_gate.py::
#   refresh_quota_blocking()`。🔴 R83 訂正本行原先那句射程（原文逐字：「而它唯一的到達
#   路徑是 **Claude Code PreToolUse ＋ 扇出型工具**」——接電之後那句話已為假，故不留著當
#   現行說法）：它現在**也**由 **PostToolUse** 到達，而那個事件的 matcher 覆蓋
#   `Read|Bash|Grep|Glob|…` ⇒ 只要有人在用 Claude Code，每 180 秒（`QUOTA_CACHE_TTL_
#   SECONDS`）就會有人刷新這份快取，不再需要「剛好有人派 agent」。
#   ⇒ 下面那段劃界**縮小但沒有消失**：AutoClaude **獨立跑**（無 Claude Code session）時，
#   沒有任何東西會讓那份快取變新；`DEFAULT_TTL_SECONDS` 一過，adapter 對每一次 read
#   都回 `None`＝量不到，而「量不到」在引擎側的既有行為是**不擋**（見
#   `TokenGuardPlugin.evaluate_quota`：`pct is None` ⇒ 兩道門都不成立）。
#   也就是說：**額度軸會在無人看管那一跑上安靜地不存在**，而遲到時間無上界。
#
#   為什麼本輪不補刷新者（不是忘了，是三條硬邊界的交集）：
#     ① 取數要 OAuth token ＋ 網路 ＋ 端點知識，那整包住在 harness 的 `quota_meter.py`；
#        `autoclaude` 不得反向依賴它（`.importlinter` 的 forbidden contract，見上方 WHY）。
#     ② 走 subprocess 叫那支腳本＝把 harness 路徑寫進套件，pip install 之後不存在（同 ①
#        的理由，只是換一個載體規避）。
#     ③ 在套件內重寫一份取數＝同一份端點知識第二個家，正是本 repo 的頭號病。
#   正解是**第三方寫入者**（排程／哨兵定期刷快取），那是 harness 那一側的工作項。
#   在它落地之前，這裡不得宣稱「AutoClaude 有額度保護」——本段就是那個宣稱的界。
#   機械物：`tests/test_r82_quota_axis_and_shipped_defaults.py::
#   TestTheQuotaAxisHasNoEngineSideRefresher`（引擎側零寫入者＝**量得到的事實**；
#   哪天有人補了寫入者，那條會紅並要求回來改掉本段）。
#
# 本模組刻意只放**純資料 ＋ 純函式**（data tier ≤150），零 I/O、零平台判斷。
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

# 撞線字串判準。刻意**複製**根層 tools/lib/quota_limits.py 的字串而不 import（見上方 WHY）。
# 誠實劃界：字串比對永遠是啟發式，R80 已量過「撞線偵測用文字比對」的假陽性問題；
# 這裡的用途是「別再重試」這種**保守方向**的決策，誤判的代價是早停一步，不是燒額度。
_LIMIT_MARKERS = ("usage limit reached", "claude usage limit", "quota exceeded",
                  "rate limit", "spend limit", "resets at")

# 哪些 kind 的額度「等得到」reset。R81 實測：15 個 episode 沒有一個超過 5 小時，
# 而 weekly/spend 那兩類的 resets_at 距當下可達數天（實測 kind=weekly_all、距 5 天）
# ⇒ 對它們排程等待是錯的動作（記憶：monthly spend limit 沒有 reset 可等）。
_WAITABLE_KINDS = ("session", "five_hour", "5h")


@dataclass(frozen=True)
class QuotaReading:
    pct: float                    # 0..100（**不是** 0..1）——伺服器已算好的百分比
    kind: str                     # session / five_hour / weekly_all / seven_day / spend …
    resets_at: str | None         # ISO 8601，自帶 offset；量不到時為 None


# 🔴 R82／C3：**選軸依問題而定**，port 因此開兩個具名的面，而不是一個 `read()`。
# 病（複審兩方獨立命中）：adapter 選「horizon 最短」那一軸，而 TokenGuardPlugin 拿那一軸的
# `.pct` 當純量去比 80／95 ⇒ 同一份快取下兩端答案相反。實測：
#   weekly_all 96%@3h + session 10%@20m ⇒ 根層 halt（cap=0），AutoClaude 選到 session
#   10% ⇒ **無動作**。額度真的燒完了，而引擎這一側完全看不到。
# 兩個消費者問的本來就是**相反的問題**：
#   · `resume_wait_seconds` 問「要等多久」⇒ 只有最先 reset 的那條線等得到 ⇒ `read()`。
#   · `evaluate_quota` 問「還剩多少可燒」⇒ 最緊的那條線說了算 ⇒ `read_worst_pct()`。
# 這也是為什麼 adapter 檔頭那句「本 adapter 的**唯一**消費者」在寫下的同一個 commit
# 就為假——同一份程式碼有第二個問題要回答時，答案不會因為註解說只有一個而變成一個。
# 🔴 名字刻意**不叫 `worst()`**：那個符號是 R82 的墓碑（回 pct 最大那一桶再投影成純量，
# 把每一桶的 reset 期程丟掉）。這裡回的是**完整的一條軸**（含它自己的 resets_at），
# 而且名字逐字說出它用什麼準則挑（`by pct`），呼叫點讀得出來自己問了什麼。
class QuotaMeterPort(Protocol):
    # 回 None ＝「量不到」（檔不在／schema 不符／過期）。🔴 絕不可回 0.0——
    # 0.0 是「額度很充足」這個**有意義**的值，用它代表量不到會讓所有門檻靜默失效。
    def read(self) -> QuotaReading | None:      # 最先 reset 的那條線（「要等多久」）
        ...

    def read_worst_pct(self) -> QuotaReading | None:   # 水位最高的那條線（「還剩多少」）
        ...


def is_quota_limit_text(text: object) -> bool:
    return isinstance(text, str) and any(m in text.lower() for m in _LIMIT_MARKERS)


def reset_instant(resets_at: object) -> datetime | None:
    # ISO-8601 → **aware** datetime；缺席／解不出／不是字串一律回 None（不猜一個時刻）。
    # R82：此前這段解析只住在 resume_wait_seconds 裡，而 adapter 選軸時需要同一件事
    # ⇒ 抽成一個家（複製第二份的代價是兩邊對 naive 的處置會靜默漂開）。
    # naive 補 UTC 而不是補本地：伺服器給的一律是 UTC 絕對時刻，補本地會讓同一個字串在
    # 兩台機器上差好幾個小時，而那個錯誤沒有任何表徵（本 repo 的 naive/DST 判例同型）。
    try:
        ts = datetime.fromisoformat(str(resets_at))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


# 選軸排序用的「沒有 reset 可以等」哨兵：aware 且晚於任何真實 reset ⇒ 一律墊底。
NO_RESET = datetime.max.replace(tzinfo=UTC)


def resume_wait_seconds(reading: QuotaReading | None, now: datetime | None = None) -> float | None:
    # 回 None ＝「不要等」（沒有 resets_at／不是等得到的 kind／時刻解不出來）。
    # 呼叫端據此走「寫任務書＋通知人」而不是 sleep。刻意不回一個猜出來的秒數：
    # 猜出來的時刻最難看見——它會醒，只是醒在錯的時間（根 CLAUDE.md 記載過的形態）。
    if reading is None or not any(k in (reading.kind or "").lower() for k in _WAITABLE_KINDS):
        return None
    ts = reset_instant(reading.resets_at)
    return None if ts is None else max(0.0, (ts - (now or datetime.now(UTC))).total_seconds())
