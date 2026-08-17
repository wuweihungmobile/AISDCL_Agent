"""配速判讀的第二層：窗長、燃燒率、**跨窗攤提**——純函式、零 I/O、零網路。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R86／SA；三個缺陷同一個根：`quota_policy` 手上只有「距 reset 幾
# 分鐘」這個**絕對**量，而它的意義完全取決於「這一軸的窗有多長」，而窗長伺服器沒有給）
# ---------------------------------------------------------------------------
# 缺陷 A（`FAR_HORIZON_MINUTES=360` 是絕對分鐘數，在兩類軸上造成**相反**的極端）
#   · `five_hour`／`session` 窗長 300 分 ⇒ 距離最多 300 < 360 ⇒ **far 結構上不可達**、
#     這一軸永遠不減速；
#   · `seven_day`／`weekly_all` 窗長 10080 分 ⇒ 360 只佔 3.6% ⇒ **96.4% 的時間恆為 far**
#     ⇒ 週軸吃**恆定** ×0.5，訴求 6b 要的「近 reset 就加速」在週軸上結構上不可能發生。
#   ⇒ 治法：門檻改為**相對於各軸窗長**（`thresholds()`）。
#
# 缺陷 B（瞬時 `pct` 單獨看沒有意義——同一個 74% 在「已過 20% 時間」與「已過 90% 時間」
#   是兩件相反的事，而現行演算法對兩者給出**逐格相同**的 cap）
#   ⇒ 治法：`lead_pp()` 拿 pct 對**線性預算**比，`burn_step()` 把它收成三態。
#
# 缺陷 C（`cap` 是**併發度**旋鈕，卻被用來保護**總量**配額；舵手 R86 立案）
#   · `cap` 限制「同時可派幾個」＝速率；週配額限制「7 天總共能用多少」＝總量。
#   · 降 `cap` 只讓同一批工作花更久，總消耗不變（串行化甚至更貴：舵手在每批之間要
#     重讀狀態、重寫任務書）⇒ 用 `cap` 保護週配額是用錯旋鈕。
#   ⇒ 治法：`amortize()`——**本窗分攤到多少長窗配額**，把「本窗還能燒多少」變成可求值
#     的量。這才是訴求 6b 的正確形式：加速的上限不是短窗的 100%，而是本窗分攤到的
#     長窗配額。🔴 但它**只會收緊**（見 `band_inputs()` 的 `max(raw, …)`）：本輪不拿
#     它去放寬任何東西，理由見下方〈為什麼本輪不動 far×0.5〉。
#
# 🔴 為什麼窗長用**文法**解析而不是寫一張 `kind → 窗長` 的表：
#   `quota_policy` 檔頭既有紀律逐字禁止「寫死桶名清單」（meter 實測 live payload 頂層
#   17 鍵 vs 內嵌名單 8 個 ⇒ 名單一定會漏）。而本輪實測 `schema_keys` 已經有
#   `seven_day_cowork`／`seven_day_oauth_apps`／`seven_day_omelette`／`seven_day_opus`／
#   `seven_day_sonnet` 五個桶——**一張兩列的表對它們整片失明，一條文法全部命中**。
#   桶名本身就是自我描述的時長片語（`five_hour`＝5×60、`weekly_*`＝7 天），所以這裡解析
#   的是**字面語意**，不是身分。這與「不得用桶名選桶／分類 severity」不衝突：後者問的是
#   「該相信哪一桶」（判斷），前者問的是「這個字面是多長」（單位換算）。
#
# 🔴 文法解不出來時**不偽造窗長**，退回 `quota_policy` 既有的絕對門檻（＝今天的行為）。
#   為何不照「未知一律當 far」辦（舵手任務書的字面要求，本檔**刻意部分不從**，理由三條）：
#     ① 生產面零差別：live 快取 7 軸裡文法／繼承解不出的只有 `nimbus_quill`／`spend`，
#        而這兩軸的 `resets_at` 本來就是 `null` ⇒ 早已是 `AXIS_NONE`（×0.5）。也就是說
#        「未知當 far」今天一格都改不到，只改得到合成情境。
#     ② 它會反向推翻 R84／SA-01 才治好的缺陷：`session` 這一軸在**單軸**合成情境下窗長
#        不明（沒有同 reset 的鄰軸可繼承），強制 far 會讓掌舵者錨點①「剩 30 分鐘就
#        reset、還有 100% 沒用 ⇒ 多派」在那一軸永遠少派一半——那正是 SA-01 的病。
#     ③ 保守的正確定義是「**不得比今天更鬆**」，不是「一律更緊」。本檔用
#        `effective_horizon()` 的絕對門檻夾層把①②同時滿足：**無節省證據時，新版永不比
#        絕對門檻版鬆**（機械保證，不靠自律），而未知窗長本身不製造任何新的放行。
#   同一條也是**向後相容**的落點：`AUTOSDD_QUOTA_FAR_HORIZON_MINUTES`／
#   `AUTOSDD_QUOTA_ACCEL_WINDOW_MINUTES` 兩個既有 env 鍵一格都沒有消失，它們現在有
#   **兩個**活消費者：窗長不明時是門檻本身，窗長已知時是「不准比它更鬆」的那道夾層。
#
# 🔴〈為什麼本輪不動 far×0.5〉（誠實劃界，不是疏漏）：舵手指出攤提一旦存在，`far` 的
#   角色就該從「乘法懲罰」降為「蒸發急迫度」，方向與 `far×0.5` 相反。同意那個方向，但
#   **拿掉一個煞車是放寬**，而放寬要有證據；本輪的 per-agent 燃燒率樣本 n 極小（見
#   `estimate_ratio()`）⇒ 本輪只交付取數、落款與收緊，不放寬。已列入交棒。
#
# 🔴 本檔與 `quota_policy` 同樣**維持 Python 3.9 可載入**（POSIX hook 載具的 `python3`
#   在 macOS 原廠常年是 3.9；一旦炸掉，`quota_gate` 的 hard import 會被 try/except 收成
#   `None` ⇒ 整條額度軸零訊息短路）。⇒ 不用 `slots=`／`zip(strict=)`／執行期 `A|B`。
from __future__ import annotations

import json
import statistics
from datetime import datetime
from typing import NamedTuple

#: 時間視野檔位。🔴 由本檔持有（此前住 `quota_policy`）：判定門檻的那段程式搬到這裡，
#: 常數留在原處會讓「同一份知識兩個家」——`quota_policy` 改成再匯出，消費端零改動。
AXIS_NEAR, AXIS_MID, AXIS_FAR, AXIS_NONE = "near", "mid", "far", "none"

#: 由**鬆到緊**。`far` 與 `none` 的乘數相同（皆 `pace_far`），但 `none` 排在更緊那一端：
#: 平手時保留 `none`，因為 `_pace_of()` 對它另有「期程不明不得加速」的否決權。
_TIGHTNESS = (AXIS_NEAR, AXIS_MID, AXIS_FAR, AXIS_NONE)

#: 逐軸 note 的新字面（與 `quota_policy.NOTE_*` 同一族，刻意分得開）。
NOTE_AHEAD, NOTE_THRIFTY, NOTE_AMORT = "burn-ahead", "burn-thrifty", "amortized"

# ── 窗長文法 ────────────────────────────────────────────────────────────────
_UNIT_MINUTES = {"minute": 1, "minutes": 1, "min": 1, "mins": 1,
                 "hour": 60, "hours": 60, "hr": 60, "hrs": 60,
                 "day": 1440, "days": 1440, "week": 10080, "weeks": 10080,
                 "month": 43200, "months": 43200}
_PERIOD_MINUTES = {"hourly": 60, "daily": 1440, "weekly": 10080, "monthly": 43200}
_COUNT_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
                "twelve": 12, "twentyfour": 24, "thirty": 30}

#: 「窗還沒過半 ⇒ 算遠」。🔴 刻意選中點而不是挑一個數字：正規化窗上唯一有語意的分界。
#: 舊的 360 分鐘在 300 分窗上是 120%（結構上不可達）、在 10080 分窗上是 3.6%（恆真），
#: 兩個極端都是「絕對值套在不同尺度上」的產物，換成中點兩邊同時可達。
_MID_FRAC = 0.5

#: near 的相對門檻＝`accel_window_minutes` 佔**5 小時窗**的比例。🔴 參考窗長不寫字面，
#: 由同一條文法解出來（見下方賦值）：掌舵者原句「Token 剩 30Min 就 Reset」講的就是
#: 那個 session 窗 ⇒ 300 分窗上換算回來**仍是 30 分鐘**（逐格與今天相同），而 10080 分
#: 窗上變成 1008 分鐘（≈16.8 小時）＝「週配額快蒸發了」的合理刻度。
_NEAR_REF_MINUTES = 300.0

#: anchor 不確定度上界（分鐘）⇒ 換算成 pp 就是「省」那一側要留的邊際。
#: 🔴 為什麼要留：`elapsed` 是由「窗起點＝reset − 窗長」推導的，而 R86 實測今天兩軸的
#: `resets_at` 皆為 `:59:59.288`（不同窗長、同秒尾）⇒ 這**否證**了「reset＝anchor＋窗長」
#: 的逐秒精確版本，只剩小時精度版本成立。若 snap 是向上取整（今天的觀測支持這一向），
#: 偏差方向是把 `elapsed` **低估** ⇒ `lead` 高估 ⇒ 偏向減速＝安全側；但 snap 的方向本身
#: 未經證實（R79 逐字稿另有 `3:50am`／`12:20pm` 這種分鐘級字面）⇒ 放行側留最壞 1 小時。
_ANCHOR_MINUTES = 60.0

#: 推導出來的水位**永不觸發 halt**（halt＝停止派發，那是絕對的，不由一個推導值開火）。
_HALT_GUARD_PP = 1.0

#: 換算比取中位數所需的最少區段數；不足一律取 min（＝保守側）。
_ROBUST_SEGMENTS = 3

#: 判「翻頁」的容差：pct 是整數 pp 的讀數，微小抖動不算翻頁。
_ROLLOVER_EPS = 0.5

#: `pace_index` 分母下限（elapsed_frac）：窗剛開的一瞬 elapsed→0 比值發散，而 PRD
#: §4.2.8 的原式就寫成 `utilization / max(ε, elapsed_frac)`——窗首 1% 之內的任何讀數
#: 都還不構成配速證據，此值只防爆表，不參與任何方向判定（方向仍由 `lead_pp` 決定）。
_ELAPSED_FLOOR = 0.01


def window_minutes(kind: str) -> float | None:
    """桶名字面 → 窗長（分鐘）。解不出回 `None`（**不猜**）。

    文法：以 `_` 切詞，第一個命中的「週期詞」或「（數量詞＋）單位詞」為準。
    實測：`five_hour`→300、`seven_day`／`seven_day_opus`→10080、`weekly_all`→10080、
    `session`／`nimbus_quill`／`spend`→`None`。
    """
    tokens = [t for t in str(kind).strip().lower().replace("-", "_").split("_") if t]
    for i, token in enumerate(tokens):
        if token in _PERIOD_MINUTES:
            return float(_PERIOD_MINUTES[token])
        if token in _UNIT_MINUTES:
            prev = tokens[i - 1] if i else ""
            count = _COUNT_WORDS.get(prev, float(prev) if prev.isdigit() else 1)
            return float(count) * float(_UNIT_MINUTES[token])
    return None


# 🔴 繼承是**由資料導出的推論**，不是名單：今天 `session` 與 `five_hour` 的 `resets_at`
# 逐字相同（`…14:59:59.288259+00:00`，微秒都一樣），`weekly_all` 與 `seven_day` 亦然
# ⇒ 它們是同一條底層限制被回報兩次。失效模式誠實寫在這裡：相同的**結束時刻**不等於
# 相同的**窗長**（一個日窗與一個週窗可以恰好同時結束）⇒ 繼承取**最短**的鄰軸窗長，因為
# 短窗會讓 near 門檻更小（＝更不容易加速），而加速是唯一會把額度燒掉的方向。
def windows(pairs) -> tuple:
    """`[(kind, resets_at)]` → 逐軸窗長；文法解不出時由**同 reset 的鄰軸**繼承。"""
    rows = list(pairs)
    grammar = [window_minutes(kind) for kind, _ in rows]
    known: dict = {}
    for (_kind, resets_at), win in zip(rows, grammar):
        key = str(resets_at or "").strip()
        if key and win is not None:
            known[key] = min(win, known.get(key, win))
    return tuple(win if win is not None else known.get(str(resets_at or "").strip())
                 for (_kind, resets_at), win in zip(rows, grammar))


def thresholds(window: float | None, accel_abs: float, far_abs: float) -> tuple:
    """`(near, far)` 門檻分鐘數。窗長未知 ⇒ 原封不動沿用兩個**絕對**門檻。

    🔴 `near` 夾在 `far` 之下：`accel_window_minutes` 被調得很大時（例 200），相對化後
    的 near 會超過 far ⇒ mid 檔變空、far 不可達，也就是把缺陷 A 換個尺度再犯一次。
    """
    if window is None or window <= 0:
        return float(accel_abs), float(far_abs)
    far = float(window) * _MID_FRAC
    return min(float(window) * float(accel_abs) / _NEAR_REF_MINUTES, far), far


def horizon(minutes: float | None, window: float | None,
            accel_abs: float, far_abs: float) -> str:
    """由「還剩幾分鐘」＋「窗有多長」導出時間視野。`None` 與負值一律**不得加速**。"""
    if minutes is None:
        return AXIS_NONE
    if minutes < 0:
        return AXIS_MID
    near, far = thresholds(window, accel_abs, far_abs)
    if minutes <= near:
        return AXIS_NEAR
    return AXIS_MID if minutes <= far else AXIS_FAR


def tightest(*labels: str) -> str:
    """取最緊的那一個視野檔位（`near < mid < far ≤ none`）。"""
    return max(labels, key=_TIGHTNESS.index)


def anchor_margin_pp(window: float | None) -> float:
    """「省」那一側要越過的邊際（pp）＝最壞 1 小時 anchor 偏移佔窗長的比例。

    300 分窗 ⇒ 20pp；10080 分窗 ⇒ 0.6pp。窗長未知 ⇒ 100pp（＝這一側結構上不可達）。
    """
    if window is None or window <= 0:
        return 100.0
    return min(100.0, 100.0 * _ANCHOR_MINUTES / float(window))


# 🔴 `elapsed` 是**推導值不是量測值**：窗起點＝`resets_at` − 窗長。對「滾動視窗、錨在該
# 區塊第一次用量」（R79 實測的形狀）這條推導在**逐秒**上成立；但今天的觀測（兩軸同為
# `:59:59`）顯示伺服器另有小時級 snap ⇒ 只在**小時精度**上成立。偏差的處置見
# `anchor_margin_pp()`：煞車側不留邊際（減速可以無證據），放行側留一小時。
# `minutes > window`（伺服器給的 reset 比窗長還遠＝資料自相矛盾）⇒ `elapsed` 夾 0 ⇒
# `lead = pct` ⇒ 一律判超前（保守側），而不是拿一個負的 elapsed 去算。
def lead_pp(pct: float, minutes: float | None, window: float | None) -> float | None:
    """相對線性預算超前幾 pp（正＝燒太快）。`None`＝算不出（窗長或距離不明）。"""
    if minutes is None or minutes < 0 or window is None or window <= 0:
        return None
    elapsed = min(1.0, max(0.0, 1.0 - float(minutes) / float(window)))
    return float(pct) - 100.0 * elapsed


# 🔴 R95／PRD §4.2.8：比值形式（供人讀與校準）與 `lead_pp` 差值形式（供決策）**並存**，
# 不互相取代：差值天生帶 anchor 邊際的 pp 語意（`anchor_margin_pp`），比值才對得上
# CLI 內建判準的參考值（five_hour 1.25、seven_day 1.25/1.43/1.67，見 PRD 該節表格）。
def pace_index(pct: float, minutes: float | None, window: float | None) -> float | None:
    """PACE_INDEX ＝ 利用率 ÷ 窗已流逝比例。`None`＝算不出（與 `lead_pp` 同一組前置）。

    >1＝超前燃燒（會提前用完）、≈1＝照線性預算、<1＝比預算省。
    """
    if minutes is None or minutes < 0 or window is None or window <= 0:
        return None
    elapsed = min(1.0, max(0.0, 1.0 - float(minutes) / float(window)))
    return float(pct) / (100.0 * max(elapsed, _ELAPSED_FLOOR))


# 🔴 R95：`ceiling` 是**可調配速上限**（`AUTOSDD_QUOTA_PACE_CEILING`，SSOT＝
# `quota_policy.ENV_SPEC`）。方向鎖三條，皆為結構保證：
#   ① 預設 1.0 ⇒ `ceiling <= 1.0` 短路 ⇒ 超前判定**逐位元**等於既有 `lead > 0`；
#   ② 調高只會把「超前 ⇒ 強制 far」放回**中性**（`tightest(relative, legacy)`），
#      而中性永不比絕對門檻版鬆（見 `effective_horizon`）⇒ 動不到「無證據不得放寬」；
#   ③ 「省」那一側（負 lead ＋ anchor 邊際）一個字不讀 ceiling ⇒ 它放不出任何加速。
def burn_step(pct: float, minutes: float | None, window: float | None,
              ceiling: float = 1.0) -> tuple:
    """`(-1 省／0 不明或中性／+1 超前, note)`。**不對稱是刻意的**：

    超前 ⇒ 任何幅度都減速（減速猜錯只是慢一點）；省 ⇒ 必須越過 anchor 邊際才放行
    （加速猜錯會爆額度）。
    """
    lead = lead_pp(pct, minutes, window)
    if lead is None:
        return 0, ""
    if lead > 0:
        index = pace_index(pct, minutes, window)
        if float(ceiling) <= 1.0 or (index is not None and index > float(ceiling)):
            return 1, NOTE_AHEAD
        return 0, ""
    if lead <= -anchor_margin_pp(window):
        return -1, NOTE_THRIFTY
    return 0, ""


# 🔴 這一支是**方向鎖的本體**（缺陷 A 的治法與「不得比今天更鬆」的硬約束同住一處）：
#   · 有「省」的證據 ⇒ 相對門檻直接生效（可以比絕對門檻鬆——這正是週軸 96.4% 恆 far
#     的解，而它有證據）；
#   · 沒有證據（含窗長不明）⇒ 與絕對門檻取**較緊**者 ⇒ 結構上不可能比今天鬆；
#   · 超前 ⇒ 再與 `far` 取較緊者 ⇒ 額外一道煞車。
# 為何夾在 label 而不是 cap：`_cap_for`／`_rec_for` 對視野檔位是**單調**的（乘數
# near 2.0 > mid 1.0 > far/none 0.5）⇒ 夾住 label 就等於夾住 cap 與 rec，而消費端
# （`_pace_of`／`describe`／`AxisReading.horizon`）一行都不必改。
def effective_horizon(pct: float, minutes: float | None, window: float | None,
                      accel_abs: float, far_abs: float,
                      ceiling: float = 1.0) -> tuple:
    """`(視野檔位, note)`：相對門檻 ＋ 燃燒率 ＋「無證據不得比絕對門檻鬆」夾層。"""
    relative = horizon(minutes, window, accel_abs, far_abs)
    legacy = horizon(minutes, None, accel_abs, far_abs)
    step, note = burn_step(pct, minutes, window, ceiling)
    if step > 0:
        return tightest(relative, legacy, AXIS_FAR), note
    if step < 0:
        return relative, note
    return tightest(relative, legacy), note


# ── 跨窗攤提（缺陷 C：把「本窗還能燒多少」變成可求值的量）────────────────────────
class Amort(NamedTuple):
    """一次攤提的全部中間量。**每一格都要印得出來**——舵手 R86 的直接要求：
    他看到「短窗還很空、卻只能派 2 個」時，畫面必須自己回答「為什麼空著也不能衝」。
    """

    rate_kind: str
    total_kind: str
    remaining_pp: float
    total_minutes: float
    windows_left: float
    per_window_pp: float
    ratio: float
    ratio_note: str
    allowance_pp: float
    used_pp: float
    headroom_pp: float
    rate_minutes: float
    rate_window: float


# 🔴 誰是速率軸、誰是總量軸**由窗長導出**，不由桶名（同 `windows()` 的紀律）：
#   最短窗＝速率軸（它是「同時可以燒多快」的限制），最長窗＝總量軸（它是「一共能燒
#   多少」的限制）。只有一種窗長時攤提不成立（沒有兩個尺度可以換算）⇒ 回 `None`。
# 同窗長的多軸（今天 `session` 與 `five_hour`、`weekly_all` 與 `seven_day` 各一對）取
# **最保守**的那一格：用量取 max、長窗剩餘分鐘取 max（窗數愈多 ⇒ 每窗配額愈小 ⇒ 愈緊）、
# 短窗剩餘分鐘取 min（最早蒸發）。
def amortize(named_pcts, minutes, wins, ratio, ratio_note: str = ""):
    """跨窗攤提。`None`＝條件不足（缺換算比／只有一種窗長／沒有可用軸）。

    `named_pcts` ＝ `[(kind, pct)]`（桶名只用來**具名回報**，不參與任何判定）。
    """
    live = [(str(k), float(p), float(m), float(w))
            for (k, p), m, w in zip(named_pcts, minutes, wins)
            if m is not None and float(m) >= 0 and w is not None and float(w) > 0]
    if not live or ratio is None or float(ratio) <= 0:
        return None
    rate_window, total_window = min(x[3] for x in live), max(x[3] for x in live)
    if total_window <= rate_window:
        return None
    short = [x for x in live if x[3] == rate_window]
    total = [x for x in live if x[3] == total_window]
    remaining = max(0.0, 100.0 - max(x[1] for x in total))
    total_minutes = max(x[2] for x in total)
    windows_left = max(1.0, total_minutes / rate_window)
    per_window = remaining / windows_left
    allowance = min(100.0, per_window * float(ratio))
    used = max(x[1] for x in short)
    return Amort(short[0][0], total[0][0], remaining, total_minutes, windows_left,
                 per_window, float(ratio), ratio_note, allowance, used,
                 allowance - used, min(x[2] for x in short), rate_window)


# 🔴 R95／掌舵者 2026-08-16 裁決（實案：five_hour 窗尾 33 分、自軸 25%、weekly 46%
# free band，攤提仍把 cap 壓到 1 ⇒ 派工被迫空等 reset）：short 窗剩餘額度 reset 即作廢
# （use-it-or-lose-it）、weekly 是同一消耗池（推遲≠節省）⇒ 長窗自軸還沒踏進 converge
# 錨點（「開始收斂」的那條線）之前，攤提**出聲不收緊**——`Amort` 照算照回（痕跡、
# `explain()` 的第三行、落款一格不少），只是不再調高餵給 `pct_band` 的水位。
# 邊界取 `>= converge 即收緊`（錨點本身算收緊側）＝fail-safe 方向；錨點不明
# （`converge_pct is None`，含所有既有呼叫端）⇒ 逐字維持 R94 行為。
def amort_relaxed(amort, converge_pct) -> bool:
    """長窗自軸未達 converge 錨點 ⇒ 攤提只出聲、不收緊（R95）。"""
    return (amort is not None and converge_pct is not None
            and (100.0 - amort.remaining_pp) < float(converge_pct))


# 🔴 攤提**只會調高**餵給 `pct_band` 的水位（`max(raw, …)`）⇒ 方向鎖無條件成立：
#   `allowance <= 100` ⇒ `100*raw/allowance >= raw`，所以它永遠不可能放寬，連換算比被
#   `AUTOSDD_*` 誤設成一個很大的值也不行。另兩道邊界：
#   · 上界夾在 `halt - 1`：推導值永不觸發停止派發（halt 只由伺服器給的真實水位開火）。
#   · 下界是原始 pct：已經在 halt 帶的軸不會被這一格**放寬**回 prepare。
#   R95 的免除分支不破這條不變式：它回的是原始 pct 本身（`shown == raw` 仍滿足
#   `shown >= raw`），且只在長窗自軸 free/notice 帶成立——收緊面一格都沒鬆。
def band_inputs(named_pcts, minutes, wins, ratio, halt_pct: float,
                ratio_note: str = "", converge_pct: float | None = None) -> tuple:
    """`(逐軸餵給 pct_band 的水位, Amort|None)`。"""
    amort = amortize(named_pcts, minutes, wins, ratio, ratio_note)
    if amort is None:
        return tuple(float(p) for _k, p in named_pcts), None
    if amort_relaxed(amort, converge_pct):
        return tuple(float(p) for _k, p in named_pcts), amort
    ceiling = float(halt_pct) - _HALT_GUARD_PP
    shown = []
    for (_kind, pct), win in zip(named_pcts, wins):
        if win is None or float(win) != amort.rate_window:
            shown.append(float(pct))
        elif amort.allowance_pp <= 0:
            shown.append(max(float(pct), ceiling))
        else:
            shown.append(max(float(pct),
                             min(ceiling, 100.0 * float(pct) / amort.allowance_pp)))
    return tuple(shown), amort


# 🔴 為什麼 `resolve()`／`amort_for()` 這兩個「組裝面」住在本檔而不是 `quota_policy`：
#   後者的 LOC tier 餘裕是**個位數**（實測 395／400），而本案要加的判定有三層。把逐軸
#   組裝整段放這裡，`quota_policy` 那一側就只剩「階梯 → cap/rec」那件它本來就在做的事，
#   淨行數變動為 0。這不是為了逃避預算：分工也更乾淨——**數值與 note 的解析在這裡，
#   水位帶與上限階梯在那裡**，兩邊各只有一個家。
#
# `rows` ＝ `[(kind, pct, resets_at, pct_note)]`（`pct_note` 由 `quota_policy._sane_pct`
# 產生：水位本身壞掉時的字面，本檔不重新實作一份）。
# `deltas` ＝ `[(帶號分鐘|None, note)]`（負值＝時鐘偏移，一路帶進 `horizon()` 才不會變死碼）。
def resolve(rows, deltas, ratio, ratio_note: str, accel_abs: float, far_abs: float,
            halt_pct: float, pace_ceiling: float = 1.0,
            converge_pct: float | None = None) -> tuple:
    """`[(餵給 pct_band 的水位, 視野檔位, 夾 0 的剩餘分鐘|None, 合併後的 note)]`。"""
    wins = windows(tuple((kind, at) for kind, _pct, at, _n in rows))
    shown = band_inputs(tuple((kind, pct) for kind, pct, _at, _n in rows),
                        tuple(d[0] for d in deltas), wins, ratio, halt_pct, ratio_note,
                        converge_pct)[0]
    out = []
    for (_kind, pct, _at, pct_note), (raw, note), win, feed in zip(
            rows, deltas, wins, shown):
        horizon, burn = effective_horizon(pct, raw, win, accel_abs, far_abs, pace_ceiling)
        joined = "+".join(x for x in (pct_note, note, burn,
                                      NOTE_AMORT if feed > pct else "") if x)
        out.append((feed, horizon, None if raw is None else max(0.0, raw), joined))
    return tuple(out)


def amort_for(rows, deltas, ratio, ratio_note: str = ""):
    """`resolve()` 的攤提那一半，單獨拿出來給 `Decision.amort` 用（同一組輸入）。"""
    return amortize(tuple((kind, pct) for kind, pct, _at, _n in rows),
                    tuple(d[0] for d in deltas),
                    windows(tuple((kind, at) for kind, _pct, at, _n in rows)),
                    ratio, ratio_note)


# 🔴 一行內要能回答「為什麼空著也不能衝」。刻意**一個 `%` 都不出現**、全用 `pp`：
#   ① pp（百分點）才是這些量的正確單位——它們是差值與配額，不是比例；
#   ② `quota_policy` 的 M7 判準逐個掃 `%`、要求每一個都自帶 `kind=` 與剩餘分鐘，而攤提
#      算式天生會出現一串中間量 ⇒ 用 pp 讓判準的射程與本行的語意不互相扭曲。
def explain(amort, converge_pct: float | None = None) -> str:
    """攤提的人看版（`--pace` 的第三行）。`None` ⇒ 說出為什麼沒有這一行。"""
    if amort is None:
        return "攤提：只有一種窗長或換算比無樣本 ⇒ 未套用（不偽造換算比）"
    # 🔴 分鐘一律 `int()` **截斷**而不是 `:.0f` 四捨五入：`quota_policy._axis_phrase` 用的是
    # `int()`，兩者不一致時同一個量會在相鄰兩行印出差 1 的兩個數字，而「同一件事兩個數」
    # 正是本 repo 反覆判過的不可信號（讀者會開始懷疑哪一行才是真的）。
    text = (f"攤提：kind={amort.total_kind} 剩 {amort.remaining_pp:.0f}pp／距 reset "
            f"{int(amort.total_minutes)} 分鐘 ÷ {amort.windows_left:.1f} 個 "
            f"kind={amort.rate_kind} 窗 = 每窗 {amort.per_window_pp:.2f}pp"
            f" ×r={amort.ratio:.1f}（{amort.ratio_note}）⇒ 本窗配額 "
            f"{amort.allowance_pp:.1f}pp；kind={amort.rate_kind} 已用 "
            f"{amort.used_pp:.0f}pp 剩 {int(amort.rate_minutes)} 分鐘 ⇒ 本窗餘裕 "
            f"{amort.headroom_pp:+.1f}pp")
    # R95：比值供人讀與校準（對照 PRD §4.2.8 的 CLI 內建參考值），差值仍是決策輸入。
    index = pace_index(amort.used_pp, amort.rate_minutes, amort.rate_window)
    if index is not None:
        text += f"；短窗 pace_index={index:.2f}"
    if amort_relaxed(amort, converge_pct):
        text += (f"；長窗自軸 {100.0 - amort.remaining_pp:.0f}pp 未達 converge "
                 f"{float(converge_pct):.0f}pp ⇒ 出聲不收緊（本次未壓制短窗水位）")
    return text


# ── 換算比 r（短窗 pp／長窗 pp）：只能從觀測來，不能從結構來 ──────────────────────
# 🔴 為什麼不能從結構來：`r = limit_7d / limit_5h`，而伺服器把兩個分母都藏起來
#   （快取的 `denominator.text` 逐字：`five_hour.limit_dollars 為 null`）⇒ 沒有任何
#   算式可以在不觀測的情況下解出它。⇒ 唯一的路是落款＋差分。
#
# 🔴 外部校準基準（R86，repo 至今唯一一筆）：掌舵者貼出 Claude Code CLI 畫面
#   （`Team Current session / Resets in 1 hr 38 min / 1% used`），舵手同一支載具、同一台
#   機器、間隔 52 分鐘量到兩點：`(1pp, 74pp)` → `(16pp, 75pp)`。它此前只活在對話裡
#   （R85 教訓 5：做了但不落磁碟＝沒發生），所以在這裡落成 repo 內的常數，
#   provenance 與逐項對帳＝`docs/06_quality/CrossPlatform_R86_Pace_Calibration.md`。
#   它是**先驗不是現況**：落款一旦累積出真實區段，`estimate_ratio()` 會把它併進同一池。
#
# 🔴 R93／DEF-200-122：第 4 欄 `fp=None`＝**永久排除**（見 `filter_by_signature`）。
#   校準文件全文查無指紋 provenance，回填等於偽造，故承認退場，見證據檔。
SEED_OBSERVATIONS = (("2026-08-12T21:24:00+08:00", 1.0, 74.0, None),
                     ("2026-08-12T22:16:00+08:00", 16.0, 75.0, None))


# 🔴 量化保守：兩軸讀數都是整數 pp（實測 `pct` 皆 `.0`）⇒ 差值的誤差各最多 ±1
#   ⇒ 真值滿足 `Δshort >= 觀測-1`、`Δlong <= 觀測+1` ⇒ 這個組合是 r 的**下界**。
#   為何要下界而不是點估：r 愈大 ⇒ 本窗配額愈大 ⇒ 愈鬆，所以保守側就是小 r。
#   實例：`Δshort=15, Δlong=1` ⇒ 點估 15、下界 7；舵手手算用的是點估 15。
def ratio_of(d_short: float, d_long: float) -> float | None:
    """一個區段的換算比下界。任一差值 ≤0 ⇒ `None`（那不是一次可用的觀測）。"""
    if float(d_short) <= 0 or float(d_long) <= 0:
        return None
    return max(1.0, (float(d_short) - 1.0) / (float(d_long) + 1.0))


def _iso_key(text: str):
    """落款時刻的排序鍵。解不出來的列排到最後（而不是讓整池排序未定義）。"""
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def segments(rows) -> list:
    """把 `(ts, short, long)` 切成「沒有翻頁」的區段。任一軸下降＝視窗翻頁＝斷點。

    🔴 為何以「下降」判翻頁而不是比對 `resets_at`：翻頁的**可觀測後果**就是水位驟降，
    而 `resets_at` 在落款裡是另一份會漂移的資料；用後果判，少一個要維護的家。
    """
    ordered = sorted((r for r in rows if _iso_key(r[0]) is not None),
                     key=lambda r: _iso_key(r[0]))
    out: list = []
    current: list = []
    for row in ordered:
        if current and (row[1] < current[-1][1] - _ROLLOVER_EPS
                        or row[2] < current[-1][2] - _ROLLOVER_EPS):
            out.append(current)
            current = []
        current.append(row)
    if current:
        out.append(current)
    return [seg for seg in out if len(seg) >= 2]


# 🔴 「樣本不足一律走保守側」的落點：區段數 <3 ⇒ 取 **min**（最緊的那個 r）；≥3 ⇒ 取
#   中位數。為何不永遠取 min：min 對樣本數是單調不增的 ⇒ 蒐集愈多資料只會愈來愈緊，
#   最後變成一個永久生效的煞車（本 repo 判過「擋到讓人無法工作的守衛會被整個關掉」）。
def estimate_ratio(rows) -> tuple:
    """`(r|None, note)`。`note` 必須說出樣本數與「為什麼保守」——不准靜默。"""
    pool = [r for r in (ratio_of(seg[-1][1] - seg[0][1], seg[-1][2] - seg[0][2])
                        for seg in segments(rows)) if r is not None]
    if not pool:
        return None, "無可用區段 ⇒ 攤提不套用"
    if len(pool) < _ROBUST_SEGMENTS:
        return min(pool), f"n={len(pool)}<{_ROBUST_SEGMENTS} 樣本不足 ⇒ 保守取 min"
    return statistics.median(pool), f"n={len(pool)} ⇒ 取中位數"


def rows_from_jsonl(text: str) -> list:
    """落款 jsonl → `[(ts, 短窗 pct, 長窗 pct, fp)]`。壞列一律略過（取數不得掛掉）。

    `fp`＝該列的核心方案指紋；**缺席這個鍵的舊格式列一律回 `None`**——provenance
    不明時的正確處置是不採信（見 `filter_by_signature`），不是硬湊近似。
    同一個 `ts` 只取第一列：`--pace` 可能在同一份快取上被連呼數次，重複列會讓區段
    變長卻不帶任何新資訊。
    """
    rows: list = []
    seen = set()
    for line in str(text).splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            data = json.loads(stripped)
            pcts = {str(k): float(v) for k, v in dict(data["pct"]).items()}
            when = str(data["ts"]).strip()
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
        known = {k: w for k, w in ((k, window_minutes(k)) for k in pcts) if w}
        if not when or when in seen or not known:
            continue
        low, high = min(known.values()), max(known.values())
        if high <= low:
            continue
        seen.add(when)
        raw_fp = data.get("fp")
        fp = tuple(str(x) for x in raw_fp) if isinstance(raw_fp, list) else None
        rows.append((when,
                     max(pcts[k] for k in known if known[k] == low),
                     max(pcts[k] for k in known if known[k] == high),
                     fp))
    return rows


def row_of(measured_at: str, pcts, live: int = 0, fp: tuple = ()) -> str:
    """一列落款（含尾端換行）。`live`＝當時的併發派發數；`fp`＝寫入時的**核心方案指紋**
    （R93／DEF-200-122：見 `quota_gate.core_signature`。預設 `()` 給既有呼叫端相容，
    真正的生產呼叫端 `quota_gate.record_burn` 一律顯式帶入）。
    """
    return json.dumps({"ts": str(measured_at),
                       "pct": {str(k): float(v) for k, v in pcts},
                       "live": int(live), "fp": list(fp)},
                      ensure_ascii=False, sort_keys=True) + "\n"


# 🔴 這就是雙向對稱性的來源（R93／DEF-200-122／ADR-XPLAT-009）：換方案不論方向為何，
# 只要核心桶集合改變，舊指紋的列在新指紋的過濾裡結構上絕不會出現，`segments()`／
# `estimate_ratio()` 因而永遠看不到跨方案的樣本混在同一段裡——過濾發生在呼叫它們**之前**，
# 兩者一行都不改。`fp is None`（舊格式列／`SEED_OBSERVATIONS`）永遠不參與任何池子，
# 即使 `signature` 恰好也是 `()`：provenance 不明時的正確處置是不採信，不是碰巧相等就採信。
def filter_by_signature(rows, signature: tuple) -> list:
    """只留 `fp == signature` 的列，回 `(ts, short, long)` 三元組（既有輸入形狀）。"""
    return [(ts, short, long) for ts, short, long, fp in rows
            if fp is not None and fp == signature]
