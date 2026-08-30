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

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

# 撞線字串判準。刻意**複製**根層 tools/lib/quota_limits.py 的字串而不 import（見上方 WHY）。
# 誠實劃界：字串比對永遠是啟發式，R80 已量過「撞線偵測用文字比對」的假陽性問題；
# 這裡的用途是「別再重試」這種**保守方向**的決策，誤判的代價是早停一步，不是燒額度。
_LIMIT_MARKERS = ("usage limit reached", "claude usage limit", "quota exceeded",
                  "rate limit", "spend limit", "resets at",
                  # R100 P2-C（PRD §8-1 的 AutoClaude 半）：HTTP 那一族的**字**此前不在表內
                  # ⇒ 「辨識詞表真的認得 429／529」在接線之前先是一個詞表缺口，不是接線缺口。
                  # 逐字取自實際會出現的形態：SDK 的 `rate_limit_error`／`overloaded_error`
                  # （`"rate limit"` 帶空白，比不到帶底線的那個）與 HTTP reason phrase。
                  "rate_limit_error", "overloaded_error", "too many requests")

# 🔴 狀態碼**不能**用子字串比：`"429" in text` 會命中 `line 429`／任何雜湊／
# `4290 passed`。  # baseline-ok: 反例引文（引的是會誤命中的形態，不是基線值）
# 兩個 alternation 分支各自要求一側的語境（母體是 CLI 自己的輸出，不是我們造的字串）：
#   ① 碼在前、限流字彙在 24 個非數字字元內跟上（`429 rate limit exceeded`）
#   ② 具名前綴在前、碼在 16 個非數字字元內跟上（`API Error: 429 {...}`／`Error code: 529`）
# 前綴詞彙刻意**不收裸 `error`**：`AssertionError: assert x == 429` 會被它吃成撞線
# （pytest 輸出會經由 CLI stdout 流過本判準）⇒ 那是假紅，而假紅會讓整道判準被關掉。
_LIMIT_CODE_RE = re.compile(
    r"\b(?:429|529)\b(?=[^0-9\n]{0,24}?(?:rate|limit|overload|too\s+many|retry))"
    r"|(?:api[ _-]?error|http|status|code)[^0-9\n]{0,16}\b(?:429|529)\b", re.I)

# 執行器判定「CLI 拒工」時寫進 failure_reason 的前綴。🔴 它必須自己滿足
# `is_quota_limit_text()`——那是「執行器 → TokenGuardPlugin.evaluate_quota」這條縫的
# 全部：plugin 讀的就是 failure_reason，前綴不含任何撞線字彙時 plugin 結構上看不見它。
# 機械物＝tests/test_r100_quota_refusal_false_positive.py::test_the_refusal_prefix_is_
# recognised_by_the_same_judgement（縫斷掉就紅）。
QUOTA_REFUSAL_PREFIX = "[QUOTA_LIMIT] rate limit／撞額度：CLI 輸出顯示本步驟未實際完成"

# 哪些 kind 的額度「等得到」reset。R81 實測：15 個 episode 沒有一個超過 5 小時，
# 而 weekly/spend 那兩類的 resets_at 距當下可達數天（實測 kind=weekly_all、距 5 天）
# ⇒ 對它們排程等待是錯的動作（記憶：monthly spend limit 沒有 reset 可等）。
_WAITABLE_KINDS = ("session", "five_hour", "5h")

# 🔴 R89：**保險軸**——訂閱窗用完之後才「可能」被動用的付費池，不是與訂閱窗平起平坐的
# 節流軸。憲法依據＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md`
# §6 4b（預設 `OVERAGE_POLICY=FREEZE`＝**絕不動用超額**）＋ §15.5 紅線 2（超額用量必須是
# 顯式 opt-in）＋ §0.6 新發現 1（「達到訂閱限制**後**可能可以付費續跑」）。掌舵者裁決逐字：
# 「付費額度是一個保險，你把它當成主要，本末倒置」。
# ⇒ 在 FREEZE 之下這個池子**結構上不可燒**，所以它不是「還剩多少可燒」這個問題的答案；
#   拿它的水位去比 halt 門檻，量的是一個系統本來就不打算動用的東西。
#
# 🔴 為什麼這個字面必須在引擎側再有一份（＝這不是「同一份知識多開一個家」的復發）：
#   `.importlinter` 的 `no-harness-import` 契約禁止 `autoclaude` import 根層 `tools/`
#   ⇒ 跨這條邊界的**字面**只能兩側各自持有，縫由判準縫起來。本檔內已有兩筆同型先例
#   （`_LIMIT_MARKERS` 逐字複製 `tools/lib/quota_limits.py` 的字串、`_WAITABLE_KINDS`
#   就是同一族的 kind 分類），R86 的 `PACE_SCHEMA`／`DEGRADED_CAP` 亦然。體例＝
#   **字面多個家、判準一個家**。三個家的縫由兩道鎖接成一條鏈：
#     · 根層兩家（`quota_policy.FALLBACK_KINDS` ↔ `quota_meter.CREDIT_POOL_KEYS`）＝
#       `tools/tests/test_quota_policy.py::
#        TestR89TheFallbackSetMayNotSwallowASubscriptionAxis`
#     · 根層 ↔ 本檔 ＝ `tests/test_r82_quota_axis_and_shipped_defaults.py::
#       TestTheFallbackKindsMirrorTheRootDeclaration`（讀原始碼／不進生產碼的 import）
# 🔴 它是**分類**不是演算法：沒有門檻、沒有公式、不隨量測改變，唯一會改動它的事件是 PRD
#   的 `OVERAGE_POLICY` 改掉。配速演算法（水位帶 × 期程帶 → cap、跨軸聚合、單調性不變式）
#   仍然只有根層 `quota_policy.decide()` 一個家，引擎照舊只讀 `read_pace()` 的**結論**。
# 🔴 R89 收尾／SA 複審 B-3：`overage`／`seven_day_overage_included` 補入（逐字取自 PRD `:78`
#   §0.6 新發現 1 的額度類型列舉）。取數層把 `item["kind"]` 原樣帶出 ⇒ 伺服器哪天吐這兩個
#   kind，它們會被當訂閱軸進 cap 聚合＝本輪剛治好的病原樣復發。`spend` 不在 PRD 那份列舉
#   裡（端點頂層鍵、不是 `rate_limits` 的 kind），由 payload 實測補入——照實記。
#   ⚠️ 與根層 `quota_meter.CREDIT_POOL_KEYS` 的關係是**包含不是相等**：後者是「美元計價池
#   在 payload 頂層的兩種表述」，命名空間不同；鏡射鎖已由 `==` 改為子集判準。
FALLBACK_KINDS = frozenset({"extra_usage", "spend", "overage", "seven_day_overage_included"})


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
    if not isinstance(text, str):
        return False
    low = text.lower()
    return any(m in low for m in _LIMIT_MARKERS) or _LIMIT_CODE_RE.search(low) is not None


def quota_refusal(text: object) -> str:
    # 「CLI 拒工了嗎」的唯一產生器：回**要給上游的 failure_reason**，空字串＝沒有跡證。
    # 回字串而非 bool，理由同 evaluator.unattended_refusal()：理由若只留在這裡，失效時的
    # 表徵會退化成一次普通的步驟失敗，而人分不出「模型答錯」與「根本沒跑到」。
    if not is_quota_limit_text(text):
        return ""
    return f"{QUOTA_REFUSAL_PREFIX}｜輸出末段：{str(text)[-400:]}"


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


# ══════════════════════════════════════════════════════════════════════════════
# 配速契約（R86 — 掌舵者：「請將演算法落實在程式機制，不是光光靠模型判斷」）
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 為什麼不是「引擎自己照 pct 算 cap」：那會讓配速演算法有**第二個家**。演算法本體
# （水位帶 × 期程帶 → cap／pace 倍率、跨軸聚合、單調性不變式）住在 monorepo 根層
# `tools/lib/quota_policy.py::decide()`，而引擎**不得** import 它（`.importlinter` 的
# no-harness-import contract）。修前引擎確實養了一份簡化版：只拿 `max(pct)` 去比兩道
# 門檻（converge／halt），對「距 reset 幾分鐘」這一軸完全失明 ⇒ 同一份快取下，harness
# 會 halt（cap=0）而引擎無動作的組合實測存在（R82／C3 的病，同型）。
# ⇒ 唯一合規的形狀＝**檔案契約**：根層算完把 `Decision` 寫成一份 JSON，引擎只讀、不算。
#
# 契約檔（照抄，勿重新發明；路徑與 schema 的另一個家在 harness 那一側）：
#   路徑    <tempdir>/autosdd_pace.json（與既有 autosdd_quota.json 同目錄，見 adapter）
#   schema  必須等於 "autosdd.pace/1"
#   cap             int ≥ 0        —— 現在能派幾個並發單位（0＝halt 帶；**沒有 null**）
#   band            str            —— free／notice／converge／prepare／halt／unmeasured
#   measured_at     ISO 8601 自帶 offset —— 🔴 底層**量測**時刻，不是寫檔時刻（見下）
#   source          str            —— endpoint／cache／degraded（這份數字怎麼來的）
#   headroom_pct        float|null —— 本窗還能燒多少（halt 水位 − binding（gate 面）軸
#                                      的水位；保險軸不進本欄，與 band/cap 同一取樣面）
#   headroom_pct_per_hour float|null —— 攤提餘裕＝headroom_pct ÷ (距 reset 小時數)
#   binding_kind    str|null       —— 最緊的是哪一軸（診斷用）
#
# 🔴 為什麼新鮮度必須讀 `measured_at` 而**不是**檔案 mtime（與 `autosdd_quota.json`
# 那份契約的處置刻意不同，這是本輪的設計判定，不是漏抄）：那份快取由**量測者自己**整檔
# 重寫 ⇒ mtime ≡ 量測時刻，兩者等價。本契約是**衍生物**：根層可以拿一份 30 分鐘前的舊
# 快取現算出一個決策並立刻寫檔 ⇒ mtime 很新、底層量測很舊，而那個組合的外觀與「剛量到」
# 完全相同（本 repo 判過最貴的失效形態：假綠與修好長得一樣）。⇒ 一律以 payload 為準。
# 衍生物的壽命不得超過它的輸入，判準見 adapter 的 `PACE_TTL_SECONDS`。
PACE_SCHEMA = "autosdd.pace/1"
# 「量不到」的帶別。刻意不叫 free：free 是**有意義**的值（額度很充足），拿它代表量不到
# 會讓所有下游門檻靜默失效——同本檔上方「絕不可回 0.0」那條的同一個判詞。
BAND_UNMEASURED = "unmeasured"
# 引擎真的有動作的那兩個帶（字面與根層 `quota_policy.py` 的 `BAND_*` 相同，鏡射鎖見上）。
BAND_PREPARE, BAND_HALT = "prepare", "halt"
# 量不到時的上限。🔴 **絕不是「不設限」**——本 repo 已判過這條（根層 `AUTOSDD_QUOTA_
# DEGRADED_CAP` 就是它的既有實作）。此處是引擎側的同一個數字的鏡像；預設值相等由
# `tests/test_r86_pace_contract.py` 讀根層 `ENV_SPEC` 原始碼比對（同既有鏡射鎖體例）。
# 🔴 R100／PRD §4.1.5 R-4.1.5-1：4 → **2**。立案實測「改前 `degraded_cap ==
# cap_converge` 為 `True`」⇒「完全量不到」與「量到 70%」在致動器上是同一個 cap，
# 量不到沒有換來任何收緊。新不變式＝`1 ≤ 本值 ≤ cap_prepare`（根層 cap_prepare 實查 2）。
# 本值是**被上面那道鏡射鎖拉著走的**：根層動了這裡不動就會紅，那正是它存在的理由。
DEGRADED_CAP = 2


@dataclass(frozen=True)
class PaceDecision:
    """根層算完、引擎只讀的一則配速決策。引擎**不得**在此之外自行推導 cap。"""

    cap: int                      # 硬上限；0＝halt 帶。**沒有 None**（見上方 WHY）
    band: str                     # BAND_UNMEASURED ＝這則決策量不到，走保守側
    source: str                   # endpoint／cache／degraded：這份數字怎麼來的


# 🔴 這個函式就是「新機制不得比現行門檻更寬鬆」那條保守原則的**結構性**實作，不是紀律：
# `min` 在數學上不可能回出比 `static_limit` 大的值 ⇒ 任何情境下都不會比修前更寬鬆。
# 猜錯而加速會爆額度，猜錯而減速只是慢一點 ⇒ 加速必須有證據，減速可以無證據。
# `decision is None` 與 `band == unmeasured` 是**兩件不同的事**，刻意分開：
#   · None        ＝根本沒注入 pace port（功能沒開）⇒ 行為與修前位元級相同（同本 repo
#                   既有慣例 `quota_meter=None ⇒ 零行為變化`）。
#   · unmeasured  ＝port 在、但契約缺席／過期／壞掉 ⇒ adapter 已把 cap 填成保守地板。
# 下界夾 1：cap=0（halt 帶）在這裡不得變成「一個都不准派」而讓引擎死鎖——停不停是
# halt 那一軸的決定（`TokenGuardPlugin.evaluate_quota`），不是併發度這一軸的。
def effective_fanout(static_limit: int, decision: PaceDecision | None) -> int:
    if decision is None:
        return max(1, int(static_limit))
    return max(1, min(int(static_limit), int(decision.cap)))


def resume_wait_seconds(reading: QuotaReading | None, now: datetime | None = None) -> float | None:
    # 回 None ＝「不要等」（沒有 resets_at／不是等得到的 kind／時刻解不出來）。
    # 呼叫端據此走「寫任務書＋通知人」而不是 sleep。刻意不回一個猜出來的秒數：
    # 猜出來的時刻最難看見——它會醒，只是醒在錯的時間（根 CLAUDE.md 記載過的形態）。
    if reading is None or not any(k in (reading.kind or "").lower() for k in _WAITABLE_KINDS):
        return None
    ts = reset_instant(reading.resets_at)
    return None if ts is None else max(0.0, (ts - (now or datetime.now(UTC))).total_seconds())
