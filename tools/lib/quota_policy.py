"""額度水位判讀層：cap ＝ f(pct, 距 reset 幾分鐘)——純函式、零 I/O、零網路。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R82 HELM-04；唯一實作依據＝合議裁決規格 S2~S8）
# ---------------------------------------------------------------------------
# 病：`quota_meter.worst()` 把 (usage%, 距 reset 幾分鐘) 這個**二元組**投影成一個純量，
# 於是「還有 30 分鐘就 reset、水位 0%」與「還有 5 天才 reset、水位 0%」在程式裡是同一件
# 事。實測：`pct=79 @3min` 與 `pct=79 @240min` 的輸出**逐字相同**（tier=normal cap=None），
# 80 倍的時間尺度差完全看不見；使用者要的 50%／70% 兩個錨點在程式裡**結構上不存在**。
#
# 🔴 缺陷的正確陳述（交棒書那句「worst() 永遠回 weekly」為假，已由裁決者證偽）：
#   `worst()` 回的是**pct 數值最大**的那一桶，**與該桶的 reset 期程無關**。兩個方向都會錯：
#     · 長期程桶偏高（weekly 54 > session 34）⇒ 該加速時減速；
#     · 短期程桶偏高（session 61 > weekly 57）⇒ 看起來剛好對，但那是巧合不是機制。
#   ⇒ 機械物不得寫成「不可以回 weekly」（今天就綠、且鎖住錯的性質），
#     必須寫成「**cap 必須是 (pct, horizon) 二元組的函式**」。
#
# 為何新開一支檔（三堵牆都是權威工具量出來的，不是偏好）：
# 🔴 R84／ARCH-03 訂正下面兩個數字的**性質**：它們是 R82 立案當時的量測值，不是常數，
#   而本檔此前把它們寫成現況 ⇒ 兩者今天都已過期（R84 實測 guard raw 已重釘 1089、
#   planner loc 734）。牆還在（兩支都仍是 shrink-only／餘裕個位數），過期的是數字。
#   一律現查：`python AutoClaude/tools/check_loc_budget.py --json`。
#   · `.claude/hooks/context_budget_guard.py` loc=1451 budget=1451 **headroom=0**（立案當時值）
#   · `tools/session_resume_planner.py` loc=749 budget=750 **headroom=1**（立案當時值）
#   · `quota_meter.py` 是取數層（會失敗、會慢），判讀層必須快且確定性；
#     `quota_limits.py` 吃的是逐字稿字串，本檔吃的是數值＋時刻，兩個主題。
#   本檔落在 `tools/lib/` ＝ guardrail_lib tier **≤400 行**（不吃 AutoClaude total cap）。
#
# 🔴 型別層的鎖（這是「用程式控管取錯桶」的本體，不是風格）：
#   `Axis` 刻意**不定義** `__float__`／`__int__`／`__index__`／`__lt__`／`__gt__`；
#   `QuotaState` **沒有** `.pct`、沒有任何無參數的取值出口。
#   ⇒「不指名軸別就拿到一個數字」在型別層變成**不可能**，而不是靠註解勸阻。
#
# 🔴 軸的分類**只由 `resets_at` 導出**，不由桶名、不由 `group`、不由 `is_active`：
#   · 實測 `five_hour`／`seven_day`／`nimbus_quill`／`spend` **一個 `group` 欄都沒有**，
#     後兩者連 `limits[]` 都不在 ⇒ group-first 的分類器對它們整片失明。
#   · `is_active` 五次獨立觀測都恰好等於 argmax(percent)，但**五次一致不構成契約**
#     （伺服器無文件）⇒ 拿它選桶＝把 `worst()` 換個寫法再犯一次。
#   · 禁止寫死桶名清單（meter 檔頭既有紀律：live payload 頂層 17 鍵 vs 內嵌名單 8 個）。
#
# 🔴 時間：`resets_at` 一律保留**伺服器原字串**進出，不轉本地、不重新格式化；時長
#   （分鐘）只活在記憶體、消費時現算。本 repo 已有具名機械物禁止持久化 naive 本地時間戳
#   （跨 DST 的 naive 相減實測差 3600 秒且**完全靜默**）。
#
# 🔴 跨軸聚合：**兩個角色分開聚合**（R82 複驗鏡實測後改寫，見下方三段）
#   病：cap 與 rec 都取 `min(逐軸)` 時，長期程軸（weekly 的 horizon 幾乎恆為 far）
#   的 ×0.5 煞車永遠是 binding，短期程軸的 ×2 加速一次都出不來。實測（固定
#   weekly_all 57%@8233min，把 session 的 reset 從 1 分鐘掃到 6 天＝**差 8640 倍**）：
#   cap/rec/band **逐格相同**（4/2/notice），使用者錨點①「0%+30m ⇒ 多派」在多軸下
#   相異 rec 值只有一個，而且比中性基準（8）還小 ⇒ **本案要治的病原封不動復發**。
#
#   解（兩個角色，兩種聚合，各自對一個方向負責）：
#     · `cap`＝硬上限，**逐軸各自帶自己的 horizon 乘數再取 min**。煞車方向由它承接：
#       加入任何一軸永不放寬（M3 的 property 不變），halt 一票否決。
#     · `rec`＝諮詢值，拆成「水位有多緊」×「此刻有多便宜」：
#         base = min(逐軸 base_rec)      ← 稀缺度是逐軸的，取最緊
#         pace = 最短期程那一軸的乘數    ← 節奏是**此刻**的性質，不是某一軸的
#         rec  = min(clamp(base × pace), cap)
#       加速方向由它承接：某一桶 30 分鐘後就 reset ⇒ 這一刻花掉的那份不花就浪費了。
#   為什麼兩個方向都成立：`rec ≤ cap` 恆成立 ⇒ 加速**只能在最緊那一軸允許的空間內**
#   發生，weekly 撞線時 cap=0 ⇒ rec=0，「不停」結構上不可能；而 cap 被長期程軸釘住
#   時 rec 仍隨最短期程移動 ⇒ 加速訊號不再被吃掉。
#
# 🔴 它在什麼情況下會做錯（誠實劃界，不是免責聲明）：
#   (a) `pace` 只問「最短的那個 reset 有多近」，不問**那是哪一軸**。一個我們並不在乎
#       的桶（例：`nimbus_quill` 0%）快 reset 了，也會把 rec 往 cap 推——即使真正花掉
#       的是 weekly 的額度。危害有界（永遠 ≤ cap），但那個建議比 weekly 單獨看時該給
#       的更積極。
#   (b) 我們**不知道每個桶的視窗有多長**，所以 far 對 weekly（它的常態）與 far 對
#       session（結構上不可能）被當成同一件事。要真正表達「相對於自己的視窗燒得快不
#       快」需要視窗長度，那個欄位伺服器沒有給，本檔拒絕用猜的補（同禁止寫死桶名）。
#   (c) 兩軸同帶同期程時 cap 與 band 會逐格相同——那是**正確的**（真的沒有差別），
#       但它讀起來與 (a)(b) 的失效很像；分辨方法是看 `per_axis`，每一軸都在裡面。
#
# ── 三處對規格的**刻意加寬**（照實記，勿當成疏漏）─────────────────────────────
#  (1) `Decision.per_axis` 規格宣告為 4-tuple `(axis, band, horizon, cap)`；本檔用
#      `AxisReading` 這個 NamedTuple，**前四格逐字同序**，另帶 `recommended/minutes/note`。
#      理由：M7 要求「每一個印出去的 % 都必須帶剩餘分鐘」，而 4-tuple 裡沒有分鐘 ⇒
#      `describe(d: Decision)` 在規格自己的型別下**做不到**它自己要求的事。
#  (2) `Policy.fanout_cap_override`（讀 `AUTOSDD_QUOTA_FANOUT_CAP`）與 `BAND_UNMEASURED`
#      規格未列。前者是 M3 要求「halt 帶不吃覆寫」時的必要載體；後者是「量不到」時的
#      band——把它填成 `converge` 會變成一句沒量到卻宣稱量到的假話。
#  (3) `policy_monotonicity_problems()`／`NOTE_BAD_PCT` 規格未列。它們關的是兩條實測
#      走得到的**「水位愈高、cap 愈鬆」**靜默路徑：`AUTOSDD_QUOTA_CAP_PREPARE=16` 讓
#      90% 拿到 cap 16／60% 拿到 8 而 `problems=[]`；`pct=NaN` 讓所有比較為假、一路
#      落到 `band=free／cap=None／rec=16`＝全場最寬鬆的一格。兩者都不會有人叫。
from __future__ import annotations

import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import NamedTuple

import quota_pace as W

#: 時間視野檔位（由 `resets_at` 導出，**不由桶名**）。🔴 R86：常數與判定門檻一起搬到
#: `quota_pace`（判定的程式在那裡，常數留在這裡就是同一份知識兩個家）；這裡再匯出，
#: 消費端（`Q.AXIS_MID` 等）一行都不必改。bare import 的前提與 `quota_gate` 相同：
#: 每一個消費者都是把 `tools/lib` 放進 `sys.path` 之後 `import quota_policy`（實查全庫
#: 無 `lib.quota_policy` 形態、`tools/lib/` 也沒有 `__init__.py`）。
AXIS_NEAR, AXIS_MID, AXIS_FAR, AXIS_NONE = W.AXIS_NEAR, W.AXIS_MID, W.AXIS_FAR, W.AXIS_NONE

#: 水位帶。四個錨點逐字取自使用者原文：50 開始少派／70 開始收斂／85 準備下一次
#: reset／95 停止並喚醒下一輪。
BAND_FREE, BAND_NOTICE, BAND_CONVERGE, BAND_PREPARE, BAND_HALT = (
    "free", "notice", "converge", "prepare", "halt")

#: 🔴 「量不到」不是任何一個水位帶（規格加寬②）。
BAND_UNMEASURED = "unmeasured"

#: 🔴 R89：**保險軸**——訂閱窗用完之後才會被考慮的付費池，不是與訂閱窗平起平坐的節流軸。
#: 憲法依據＝PRD §6 4b（`OVERAGE_POLICY=FREEZE` 預設＝絕不動用超額）＋§15.5 紅線 2
#: （超額必須顯式 opt-in）＋§0.6 新發現 1（「達到訂閱限制**後**可能可以付費續跑」）。
#: 官方 UI 逐字亦同：「Turn on usage credits to keep using Claude **if you hit a plan limit**」。
#: 消費端只有 `decide()` 的 cap 聚合；**取數層不得因此少量一個軸**（`DEF-200-107` 的教訓）。
#: 未來若實作 PRD 的 `OVERAGE_POLICY=ALLOW_WITH_CAP`，那是讓這些軸重新參與的開關，
#: 不是把本常數刪掉——刪掉會讓「保險」與「主力」再度分不出來。
#:
#: 🔴 R89 收尾／SA 複審 B-3：本集合**不是** `quota_meter.CREDIT_POOL_KEYS` 的同義詞。
#: 兩者的命名空間不同——後者是「美元計價池在 payload **頂層**的兩種表述」（`_credit_pool()`
#: 對每一個鍵有各自的欄位形狀），本集合是「哪些 **bucket kind** 不進 cap 聚合」。R89 第一版
#: 的鏡射鎖寫成 `==`＝把「今天恰好同值」焊成契約，於是**補齊保險軸這件事本身會轉紅**。
#: 正確關係是**包含**：美元池必為保險軸，保險軸可以更多（鎖已改為子集判準）。
#: 🔴 補進來的兩個 kind 逐字取自 PRD `:78`（§0.6 新發現 1 的額度類型列舉）：`overage`／
#: `seven_day_overage_included`。它們今天在 live payload 一次都沒出現過，但
#: `quota_meter.bucket_readings()` 把 `item["kind"]` **原樣**帶出 ⇒ 伺服器哪天吐出來，
#: 它們會被當訂閱軸進 cap 聚合＝本輪剛治好的病原樣復發，而失敗表徵與正常運作相同。
#: 🔴 `spend` **不在** PRD `:78` 的列舉裡（它是端點頂層鍵，不是 `rate_limits` 的 kind），
#: 由 payload 實測補入——照實記，不要讓下一個人以為四個成員都有憲法出處。
FALLBACK_KINDS = frozenset({"extra_usage", "spend", "overage", "seven_day_overage_included"})

#: 🔴 R89 收尾／SA 複審 B-3 末項：**未知 kind 的預設分類**。live 快取當回合實測 7 軸
#: （`session`／`weekly_all`／`weekly_scoped`／`five_hour`／`seven_day`／`nimbus_quill`／
#: `spend`），其中 `nimbus_quill` 不在 PRD 任何列舉裡 ⇒ 它今天**已經**在參與 cap 聚合，
#: 而沒有任何地方說過這件事。定調＝**維持訂閱軸／保守側**（deny-list 的結構性後果：不在
#: `FALLBACK_KINDS` 就進 gate），但必須**出聲**：靜默地把一個沒人看過的 kind 當主力節流軸，
#: 與靜默地當保險軸一樣壞——兩者的失敗表徵都與正常運作相同。
#: 🔴 這**不是**檔頭「禁止寫死桶名清單」那條紀律要禁的東西，差別在**用途**：那條禁的是拿
#: 名單去**選桶／分類**（名單一過期就整片失明、而且會靜默答錯）；本集合一行都不參與分類，
#: 只決定「要不要多說一句」。它過期的後果是**多說**幾句（false unknown），結構上不可能改變
#: 任何一個 cap／band／rec ⇒ 方向是 fail-safe。這條性質由
#: `TestR89UnknownKindsAreLoudButNeverReclassified` 釘住（含合成注入雙向自證）。
KNOWN_KINDS = FALLBACK_KINDS | frozenset({"session", "five_hour", "5h", "seven_day",
    "seven_day_opus", "seven_day_sonnet", "weekly_all", "weekly_scoped"})

#: 逐軸解析的失效字面。`missing`（欄位缺席＝**正常**，實測 weekly_scoped／spend 都是）
#: 與 `bad-horizon`（有字串但解不出 aware＝**伺服器格式變了**）必須分得開——今天兩者
#: 共用一個 `None`，於是格式變更是靜默的。
NOTE_OK, NOTE_MISSING, NOTE_BAD, NOTE_SKEW = "", "missing", "bad-horizon", "clock-skew"
#: 水位本身不是量測值（NaN／±inf／非數字／越界）。與上面三個同樣不得靜默。
#: `unknown-kind`＝伺服器吐出一個本 repo 從未列舉過的 kind（見 `KNOWN_KINDS`）。它與上面
#: 幾個同族：**都只描述取數面發生了什麼，一個都不參與分類**。多重情形以 `+` 串接。
NOTE_BAD_PCT, NOTE_UNKNOWN = "bad-pct", "unknown-kind"

_INF = float("inf")


# 🔴 **本檔刻意維持 Python 3.9 可載入**（R82／C5，SD-B1 的實測鏈路）：
#   POSIX hook 載具 `.claude/hooks/_hook_launcher.py` 的 shebang 是 `#!/usr/bin/env python3`，
#   而 macOS 原廠 `python3` 常年是 3.9 ⇒ 本檔一旦用 3.10+ 的**執行期**構造，
#   `quota_gate.py:65` 的 hard import 會炸 → hook 端 try/except 把 `quota_gate` 收成 `None`
#   → 整條額度軸短路，**零訊息、零痕跡**（`note_degraded()` 自己就住在 quota_gate 裡，
#   結構上叫不到）。也就是說：mac 第一天，額度節流會安靜地不存在。
#   ⇒ 這裡不寫 `slots=True`（3.10+）、不寫 `zip(..., strict=)`（3.10+）。
#   兩者在本檔都**零語意**：`frozen=True` 已擋掉賦值，而每一處 `zip` 的兩個序列
#   長度由建構方式保證相等（`seq` 與 `seq[1:]`、四元組與其 tail），`strict=False`
#   本來就是預設值。回歸鎖：`tools/tests/test_mac_readiness_r82.py` 的 `py39_incompat`
#   （本輪補上 `slots=`／`kw_only=`／`zip(strict=)`／執行期 `A|B`／`pairwise`／
#   `TypeAlias|TypeGuard` 六種形態；此前它對這一族**整片失明**，回空集合）。
@dataclass(frozen=True)
class Axis:
    """單一計費軸的**瞬時事實**（不含任何決策、不含任何時長）。"""

    kind: str
    pct: float
    resets_at: str | None
    group: str | None = None
    is_active: bool | None = None
    severity: str | None = None
    via: str = ""
    # 🔴 刻意不定義 __float__ / __int__ / __index__ / __lt__ / __gt__：
    #    `float(axis)` 與 `axis_a < axis_b` 必須拋 TypeError（見 M5 執行期半）。


@dataclass(frozen=True)
class QuotaState:
    """一次量測的全部事實。🔴 沒有 `.pct`、沒有無參數的取值出口。"""

    axes: tuple[Axis, ...]
    measured_at: str
    source: str
    reason: str = "ok"
    #: 🔴 R93／DEF-200-114（Architect REJECT 承接）：帳號身分訊號，`None`＝量不到
    #: （見 `quota_meter.account_key_of()`）。**新增欄位帶預設值**——所有既有建構點皆傳
    #: 4 個位置參數，本欄不影響任何一處。唯一消費端是 `quota_gate.core_signature()`。
    account_key: str | None = None

    def usable(self) -> bool:
        """有沒有任何一軸可判讀（**指名軸別**才拿得到數字）。"""
        return len(self.axes) > 0


@dataclass(frozen=True)
class Policy:
    """全部門檻的**唯一的家**；由呼叫端從 env 讀進來（本檔不碰 os.environ）。"""

    notice_pct: float = 50.0
    converge_pct: float = 70.0
    prepare_pct: float = 85.0
    halt_pct: float = 95.0
    accel_window_minutes: float = 30.0
    far_horizon_minutes: float = 360.0
    cap_notice: int = 8
    cap_converge: int = 4
    cap_prepare: int = 2
    max_fanout: int = 16
    degraded_cap: int = 4
    # 🔴 R84／SA-01：三檔 horizon 乘數不再是模組層寫死的字面，而是 Policy 的一部分
    # ⇒ 掌舵者要的「加速多積極／減速多保守」可由 `.env` 兩個鍵調（`ENV_SPEC` 同名項），
    # 而**方向**（far ≤ 1 ≤ near）由 `policy_monotonicity_problems()` 機械守。
    pace_near: float = 2.0
    pace_far: float = 0.5
    fanout_cap_override: int | None = None


DEFAULT_POLICY = Policy()


class AxisReading(NamedTuple):
    """逐軸解析結果。前四格＝規格宣告的 `(axis, band, horizon, cap)`，同序。"""

    axis: Axis
    band: str
    horizon: str
    cap: int | None
    recommended: int
    minutes: float | None
    note: str


@dataclass(frozen=True)
class Decision:
    """全域決策。`cap` 是硬上限（None＝不設限）；`recommended_fanout` 是諮詢值。"""

    cap: int | None
    recommended_fanout: int
    band: str
    binding: Axis | None
    per_axis: tuple[AxisReading, ...]
    reason: str
    # 🔴 R86／缺陷 C：跨窗攤提的中間量（`quota_pace.Amort`，`None`＝條件不足）。它必須
    # 隨決策一起走，因為舵手的直接要求是「畫面一行內要能回答為什麼空著也不能衝」——
    # 把它留在 `axes_of` 裡算完就丟，那句話就答不出來（R85 教訓 5 的同型）。
    amort: object = None


# ── 時間：只把伺服器給的瞬時字串轉成「現在還剩幾分鐘」，不持久化任何時長 ──────────
# 解析 ISO-8601；**naive 一律視為解不出**（不可與 aware 相減）。
def _parse_aware(text: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


# 🔴 為何 `_delta_minutes` 不在這裡把負值夾成 0：夾完之後 `horizon_band` 的負值分支
# 就再也到不了（＝死碼），而「時鐘偏移不得加速」那條方向鎖只剩 `axes_of` 裡的一個
# if——同一份知識兩個家、只有一個家被釘住。負號一路帶到 `horizon_band`，那道防線才是
# **活的**（拿掉它，偏移就會落進 near）。對外的 `minutes_to_reset()` 仍照規格回 0.0。
def _delta_minutes(resets_at: str | None, now: datetime) -> tuple[float | None, str]:
    """`(帶號分鐘, note)`。缺席與解不出**分開**；負值原樣回並標 `clock-skew`。"""
    if now.tzinfo is None:
        raise ValueError("now 必須是 aware datetime（naive 相減跨 DST 會靜默差一小時）")
    if resets_at is None or not str(resets_at).strip():
        return None, NOTE_MISSING
    when = _parse_aware(str(resets_at))
    if when is None:
        return None, NOTE_BAD
    minutes = (when - now).total_seconds() / 60.0
    return minutes, (NOTE_SKEW if minutes < 0 else NOTE_OK)


# 🔴 R86：`quota_pace.resolve()`／`amort_for()` 的輸入形狀只有一個家。`pct_note` 由本檔
# 的 `_sane_pct` 產生（水位壞掉的字面判準住這裡，判讀層不重寫第二份）。
def _rows(state: QuotaState) -> tuple:
    """`[(kind, pct, resets_at, pct_note)]`——餵給判定層的逐軸事實。"""
    return tuple((a.kind, a.pct, a.resets_at, _sane_pct(a.pct)[1]) for a in state.axes)


def minutes_to_reset(resets_at: str | None, now: datetime) -> float | None:
    """距 reset 幾分鐘；缺席／解不出回 `None`（**不是 0**），時鐘偏移回 `0.0`。"""
    raw = _delta_minutes(resets_at, now)[0]
    return None if raw is None else max(0.0, raw)


# 負值分支是**生產路徑**（`axes_of` 直接餵帶號分鐘進來）：一台快 6 小時的機器會讓
# 「reset 就在眼前，衝」永遠成立，所以偏移一律當 mid、不當 near。
# 🔴 R86／缺陷 A：門檻本體搬到 `quota_pace.horizon()`，因為它現在要吃**第三個**輸入
# （該軸的窗長），而 `360` 這個絕對分鐘數在 300 分窗上是 120%（far 結構上不可達）、在
# 10080 分窗上是 3.6%（96.4% 的時間恆為 far）——同一個常數在兩類軸上造成相反的極端。
# 本函式的簽章刻意**不變**（`window_minutes` 是選配、預設 `None`＝沿用兩個絕對門檻）：
# 既有呼叫點與既有測試逐格同值，向後相容是機械的、不是宣稱的。
def horizon_band(minutes: float | None, p: Policy,
                 window_minutes: float | None = None) -> str:
    """由「還剩幾分鐘」（＋窗長）導出時間視野。🔴 `None` 與負值一律**不得加速**。"""
    return W.horizon(minutes, window_minutes, p.accel_window_minutes,
                     p.far_horizon_minutes)


def _sane_pct(pct: object) -> tuple[float | None, str]:
    """水位正規化。`None`＝這根本不是一個量測值（NaN／±inf／非數字）。"""
    try:
        value = float(pct)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None, NOTE_BAD_PCT
    if not math.isfinite(value):
        return None, NOTE_BAD_PCT
    if not 0.0 <= value <= 100.0:
        return min(100.0, max(0.0, value)), NOTE_BAD_PCT
    return value, NOTE_OK


# 🔴 水位本身壞掉時 fail-closed 到 `prepare`：比 free 緊得多，但**絕不** halt（不對一個
# 沒量到的值開火，同 S7）。實測 `pct=NaN` 會讓每一個 `>=` 都為假、一路落到 `free` ⇒
# `cap=None／rec=16`，也就是**壞掉的讀數拿到全場最寬鬆的一格**，而且沒有人會叫。
def pct_band(pct: float, p: Policy) -> str:
    """由水位導出帶別（四個錨點皆可由 env 調整，見 `ENV_SPEC`）。"""
    value, _note = _sane_pct(pct)
    if value is None:
        return BAND_PREPARE
    pct = value
    if pct >= p.halt_pct:
        return BAND_HALT
    if pct >= p.prepare_pct:
        return BAND_PREPARE
    if pct >= p.converge_pct:
        return BAND_CONVERGE
    if pct >= p.notice_pct:
        return BAND_NOTICE
    return BAND_FREE


# horizon 三檔乘數。near ×2 ＝ 使用者原句「Token 剩 30Min 就 Reset，還有 100% 沒用，
# 就應該可以加速」；far／none ×0.5 ＝「反之則減速」。🔴 這三個數字是**挑的**，
# 機械物守的是方向與單調性，不是數值。
# 🔴 R84／SA-01：由模組層 dict 改成吃 `Policy` 的函式——兩個係數要能由 `.env` 調
# （掌舵者訴求 6b 逐字：「係數必須可由 env 參數化」），而寫死的字面不可能被參數化。
# mid 恆為 1.0 刻意**不開放**：它是「既不加速也不減速」這個基準本身，不是一個旋鈕。
def _mult(horizon: str, p: Policy) -> float:
    return {AXIS_NEAR: p.pace_near, AXIS_MID: 1.0,
            AXIS_FAR: p.pace_far, AXIS_NONE: p.pace_far}[horizon]


# pct 階梯的第一段：硬上限（`None`＝free 帶不設限，維持 shipped 行為）。
def _base_cap(band: str, p: Policy) -> int | None:
    return {
        BAND_FREE: None,
        BAND_NOTICE: p.cap_notice,
        BAND_CONVERGE: p.cap_converge,
        BAND_PREPARE: p.cap_prepare,
        BAND_HALT: 0,
    }[band]


# 建議值階梯＝上限階梯**往下錯開一格**（不新增常數，只有 prepare 的 1 是字面）。
def _base_rec(band: str, p: Policy) -> int:
    return {
        BAND_FREE: p.cap_notice,
        BAND_NOTICE: p.cap_converge,
        BAND_CONVERGE: p.cap_prepare,
        BAND_PREPARE: 1,
        BAND_HALT: 0,
    }[band]


# 非 halt 一律 `>=1`：**禁止靜默鎖死**；上界 `max_fanout`。
def _clamp(value: int, p: Policy) -> int:
    return max(1, min(value, p.max_fanout))


# 🔴 `rec > cap` 是自相矛盾的建議（「建議派 4 個」而「上限只准 2 個」）。
def _bound(rec: int, cap: int | None) -> int:
    return rec if cap is None else min(rec, cap)


def _cap_for(band: str, horizon: str, p: Policy) -> int | None:
    """兩段相乘。🔴 halt 是絕對的：不吃乘數、不吃 `AUTOSDD_QUOTA_FANOUT_CAP` 覆寫。"""
    if band == BAND_HALT:
        return 0
    base = _base_cap(band, p)
    if base is None:
        return None
    cap = _clamp(int(base * _mult(horizon, p)), p)
    # 🔴 覆寫是**上限**，不是拿去參與乘法的 base。舊寫法 `base = override` 會被
    # horizon 乘數放大——`AUTOSDD_QUOTA_FANOUT_CAP=8` 在 near 檔實得 16，也就是一個
    # 名字叫 CAP 的旋鈕給出了**比使用者要求的還鬆**的值。只收緊、不放寬。
    # 🔴 R93／DEF-200-114：三行併一行是 `guardrail_lib`（≤400 行）騰出 `QuotaState.
    # account_key` 那 1 行淨增的位置——**行為不變**（同一分支，非風格偏好）。
    return cap if p.fanout_cap_override is None else _clamp(min(cap, p.fanout_cap_override), p)


# 單軸建議派工數；恆 `<=` 同軸 cap（見 `_bound`）。
def _rec_for(band: str, horizon: str, p: Policy) -> int:
    if band == BAND_HALT:
        return 0
    return _bound(_clamp(int(_base_rec(band, p) * _mult(horizon, p)), p),
                  _cap_for(band, horizon, p))


#: 水位帶由寬到緊。`policy_monotonicity_problems` 的取樣序就是它。
_BAND_LADDER = (BAND_FREE, BAND_NOTICE, BAND_CONVERGE, BAND_PREPARE, BAND_HALT)


# 🔴 為何需要（實測走得到的靜默路徑）：`AUTOSDD_QUOTA_CAP_PREPARE=16` 之下 90% 拿到
# cap 16、60% 拿到 8——水位愈高反而愈鬆，而 `load_policy` 當時回 `problems=[]`：每個值
# 都落在自己的區間內，而區間檢查看不到「值與值之間的關係」。cap 是階梯常數的函式 ⇒
# 逐帶取樣即為窮舉，不必掃 0~100（那會把 hook 關鍵路徑上的成本放大兩個數量級）。
def policy_monotonicity_problems(p: Policy) -> list[str]:
    """不變式：任一 horizon 下，**pct 愈高 cap／rec 必須單調不增**。違反即出聲。"""
    problems = []
    for horizon in (AXIS_NEAR, AXIS_MID, AXIS_FAR, AXIS_NONE):
        for label, fn in (("cap", _cap_for), ("rec", _rec_for)):
            seq = [_INF if (v := fn(b, horizon, p)) is None else float(v)
                   for b in _BAND_LADDER]
            problems += [
                f"[非單調] horizon={horizon} 的 {label}：{_BAND_LADDER[i]}={a}"
                f" < {_BAND_LADDER[i + 1]}={b} ⇒ 水位愈高反而愈鬆"
                for i, (a, b) in enumerate(zip(seq, seq[1:])) if b > a]
    # 🔴 R84／SA-01：pace 兩個係數開放給 `.env` 之後，**方向**必須被守（`ENV_SPEC` 的
    # lo／hi 只守單鍵值域，守不到「兩個鍵之間的關係」——同上面那段對區間檢查的判詞）。
    # 反了會讓「近 reset ⇒ 加速」變成減速，而 `problems=[]` 讓它完全靜默。
    if not p.pace_far <= 1.0 <= p.pace_near:
        problems.append(f"[方向] pace 倍率必須 far({p.pace_far}) ≤ 1 ≤ near({p.pace_near})"
                        "，否則「近 reset 加速／遠 reset 減速」是反的")
    return problems


def axis_cap(pct: float, minutes: float | None, p: Policy) -> int | None:
    """單軸硬上限 ＝ f(pct, 距 reset 幾分鐘)。**兩個參數缺一不可**（M2）。"""
    return _cap_for(pct_band(pct, p), horizon_band(minutes, p), p)


def axis_recommended(pct: float, minutes: float | None, p: Policy) -> int:
    """單軸建議派工數（諮詢值；恆為 int）。"""
    return _rec_for(pct_band(pct, p), horizon_band(minutes, p), p)


# 🔴 時鐘偏移的方向鎖：`minutes < 0` ⇒ 夾 0 **且強制 mid**。偏移絕不允許把預算調高
# ——一台快 6 小時的機器會讓「reset 就在眼前，衝」永遠成立。
# （說明寫成 `#` 而非 docstring：`count_loc` 計 docstring 行、不計註解行，而本檔 tier
#   餘裕個位數；同 `quota_gate.py`／`session_resume_planner.py` 既有作法，一字未刪。）
# 🔴 R86：這裡多了兩個 `quota_pace` 呼叫，兩者治的是**不同**的缺陷，不要混讀：
#   · `effective_horizon`（缺陷 A＋B）＝逐軸的事：相對窗長的門檻 ＋ 燃燒率，並帶
#     「無節省證據時不得比絕對門檻鬆」的夾層 ⇒ 窗長解不出的軸逐格等於今天的行為。
#   · `band_inputs`（缺陷 C）＝**跨軸**的事：把長窗（總量）配額攤提到本個短窗（速率），
#     只調高餵給 `pct_band` 的水位、永不調低 ⇒ 結構上不可能放寬。
#   `axis.pct` 仍是伺服器給的原值（事實不得被改寫）；被攤提調高過的軸在 note 裡具名。
def axes_of(state: QuotaState, now: datetime, p: Policy,
            ratio: float | None = None, ratio_note: str = "") -> tuple[AxisReading, ...]:
    """逐軸解析的**唯一正規路徑**：`minutes` 只能從 `axis.resets_at` 導出。"""
    resolved = W.resolve(  # 🔴 帶號分鐘進去：負值的 mid 強制在 `horizon()`，不在這裡
        _rows(state), tuple(_delta_minutes(a.resets_at, now) for a in state.axes),
        ratio, ratio_note, p.accel_window_minutes, p.far_horizon_minutes, p.halt_pct)
    readings = []
    for axis, (pct, horizon, minutes, note) in zip(state.axes, resolved):
        band = pct_band(pct, p)
        # 🔴 只加一句話，**不改任何分類**（`band`／`cap`／`rec` 三欄都在這一行之外算完）。
        note = "+".join(x for x in (note, "" if axis.kind in KNOWN_KINDS else NOTE_UNKNOWN) if x)
        readings.append(AxisReading(axis, band, horizon, _cap_for(band, horizon, p),
                                   _rec_for(band, horizon, p), minutes, note))
    return tuple(readings)


# 🔴 期程不明的軸 ⇒ pace 上限夾在 1.0（不准加速）：不知道何時 reset 就沒有「不用會
# 浪費」這個理由，同 M4 的三道 fail-closed。
#
# 🔴 R84／SA-01 訂正**否決權的持有者**（原判準逐字是 `any(r.horizon == AXIS_NONE …)`，
# 那句話在 production 讓「加速」結構上到不了，故不留著當現行說法）：
#   live 快取 7 軸實測有 3 軸 `resets_at=null`（weekly_scoped／nimbus_quill／spend），
#   而它們同時是 0%＝free 帶 ⇒ `cap is None`＝**對 cap 一格煞車力都沒有**。舊判準卻給了
#   它們完整否決權：把 session／five_hour 的 reset 移到 20 分鐘（真 near）後實測
#   `fastest=2.0` 而 `pace=1.0 rec=8`；同一組軸只把三支 null 軸移除 ⇒ `pace=2.0 rec=16`。
#   也就是掌舵者錨點①「剩 30 分鐘就 reset、還有 100% 沒用 ⇒ 多派」在**任何**水位下都
#   永遠少派一半，而否決來自一個零煞車力的軸——那是從後門煞車。
#   ⇒ 不變式：**不參與 cap 的軸不得參與 pace**。判準加一個合取項 `r.cap is not None`。
#   fail-closed 那一半原封不動保留：期程不明**而且真的在煞車**的軸（notice 帶以上）
#   仍然一票否決，實測 `session 75%@3min ＋ spend 55%@None` 改前改後皆 rec=2（拿掉否決會變 4）。
#   回歸鎖（`tools/tests/test_quota_policy.py` 的 `TestM1bAccelerationSurvivesAggregation`）：
#   `test_a_toothless_null_axis_no_longer_vetoes_acceleration`（治本那一半）＋
#   `test_an_axis_with_no_horizon_but_a_real_cap_blocks_acceleration`（fail-closed 那一半）＋
#   `test_red_the_old_any_none_predicate_halves_the_recommendation`（合成注入自證）。
def _pace_of(readings: tuple[AxisReading, ...], p: Policy) -> float:
    """此刻的節奏＝**最短期程**那一軸的乘數（見檔頭「兩個角色分開聚合」）。"""
    fastest = max(_mult(r.horizon, p) for r in readings)
    if any(r.horizon == AXIS_NONE and r.cap is not None for r in readings):
        return min(1.0, fastest)
    return fastest


# 🔴 R84／SA-06 同一條不變式的第二面（回報面）：`remaining = _INF if minutes is None`
# 讓 `-remaining = -inf` 恆為最小 ⇒ cap 平手時期程不明的軸**必勝**，而 cap 平手（七軸
# 全 free）是常態。實測 live 快取 `binding=nimbus_quill`（0%、reset 不明、完全不消耗）
# ——指著一個零消耗的軸說它 binding，正是「裸百分比誤讀」的下一代形態。
# ⇒ 加一格 tie-break：`cap is None`（沒有煞車力）**且**期程不明的軸排到最後。
# 🔴 刻意只降級「cap is None」那一種：halt／節流帶的 null 軸（例：spend 撞線、沒有
# reset 可以等）**必須**保留原本的優先權，否則 `reset_branch()` 會從 `escalate`
# （只有人去提額）翻成 `arm`（排一支等 reset 的工作）＝R59 事故同形。
def _binding_key(r: AxisReading) -> tuple[float, float, float, str]:
    """argmin：cap 最小；平手時零煞車力的無期程軸排最後；再取 horizon 較長；再 kind。"""
    cap = _INF if r.cap is None else float(r.cap)
    remaining = _INF if r.minutes is None else r.minutes
    toothless = 1.0 if (r.cap is None and r.minutes is None) else 0.0
    return (cap, toothless, -remaining, r.axis.kind)


# 🔴 為何 rec 不能也取 `min(逐軸 rec)`（那會讓本案要治的病原封不動復發）：weekly 這種
# 長期程軸的 horizon 幾乎恆為 far ⇒ 它的 ×0.5 永遠 binding，短期程軸的 ×2 一次都出不
# 來。實測固定 weekly 57%@8233min、把 session 的 reset 掃過 8640 倍的範圍，`min(逐軸
# rec)` 給出的相異值只有一個。拆成「稀缺度取 min × 節奏取最短期程」之後加速看得見，
# 而 `rec <= cap` 讓它**只能在最緊那一軸允許的空間內**發生（weekly 撞線 ⇒ cap=0 ⇒ 0）。
# 🔴 `axes == ()`（量不到）⇒ `cap = degraded_cap`，不是 `None`／不設限：R81 複審探針
# 實測「快取過期 600s ＋ 額度 99%」時 42 次派發放行 42。同時**永不 halt**。
def decide(state: QuotaState, now: datetime, p: Policy,
           ratio: float | None = None, ratio_note: str = "") -> Decision:
    # 🔴 `ratio`＝短窗 pp／長窗 pp 的換算比（R86／缺陷 C）。它是**觀測值不是門檻**，所以
    # 刻意不進 `Policy`（那裡是「全部門檻的唯一的家」）：由呼叫端從落款推估後注入，
    # 缺席 ⇒ 攤提整段不套用（不偽造一個 r）。
    """跨軸聚合：`cap = min(逐軸 cap)`＝煞車；`rec = min(base×pace, cap)`＝加速。"""
    readings = axes_of(state, now, p, ratio, ratio_note)
    if not readings:
        return Decision(
            cap=max(1, p.degraded_cap), recommended_fanout=max(1, p.degraded_cap),
            band=BAND_UNMEASURED, binding=None, per_axis=(),
            reason=state.reason or "unmeasurable")
    # 🔴 R89／憲法裁決：**保險池不得一票否決主力**。掌舵者原話「付費額度是一個保險，
    # 你把它當成主要，本末倒置」；官方 UI 逐字「Turn on usage credits to keep using
    # Claude **if you hit a plan limit**」；PRD §6 4b 的預設是 `OVERAGE_POLICY=FREEZE`
    # ＝**絕不動用超額** ⇒ 系統本就不打算用它，它的水位對「訂閱窗還有餘裕時能不能派工」
    # 結構上無關。實帳：訂閱窗只用 48%，卻因這個**關著的**池子帳面超支而 cap=0。
    # 🔴 風險方向此前是**反的**：PRD §15.1 前置檢查 3 把「靜默計費」列為最危險的單一
    # 失敗模式（怕它被偷偷用掉），而守衛做成「它沒得用所以停工」。
    # 🔴 這**不是** `DEF-200-107`（R87）禁止的那件事：那次是在**取數層**
    # （`bucket_readings()`）把兩軸整個丟掉，判讀層因此拿不到輸入；這裡兩軸照樣被量到、
    # 照樣進 `per_axis`（訊息、`--pace`、告警全都看得見），只是不進 **cap 聚合**。
    # 判讀歸判讀、取數歸取數，正是該案要求的方向。
    # 🔴 `or readings` 是 fail-safe：萬一某天全部的軸都是保險軸，寧可退回舊行為（全部
    # 參與、可能過度保守），也不要讓 `min()` 對空序列拋例外而讓整條額度軸消失。
    gate = [r for r in readings if r.axis.kind not in FALLBACK_KINDS] or readings
    binding = min(gate, key=_binding_key)
    # 🔴 `if notes else` 分支是冗餘的（`",".join(["x"])` 不產生尾逗號）——R89 就地簡化，
    # 行為逐字等價。（此處原先接著一句「騰出的餘裕給下面那道地板」，那道地板已於本輪
    # 拆除，故該句一併刪去——留著就是一個指向不存在物的散文。）
    reason = ",".join([state.reason, *sorted({r.note for r in readings if r.note})])
    base = min(_base_rec(r.band, p) for r in gate)
    # ── 墓碑：`if any(halt ∧ FALLBACK_KINDS) ⇒ cap = min(cap, 1)` 那道地板（R89 中段
    #    落地，同輪末拆除；掌舵者裁決＋QA 複審 REJECT）。**刻意不留一個「暫時關掉」的版本**
    #    ——本檔已判過「留一個沒人叫的版本等於把缺陷留在原地等下一個呼叫端」。
    #    三條理由各自獨立成立：
    #    ① **立案事實被落款證偽（引用方向整個反過來）**：舊註解引 `R87_HANDOFF.md:20`
    #       逐字「主力軸只有 1%」當立案事實，而該行住在事故表的「**錯誤的證據①**」那一列
    #       ——它是 R87 自己標記為錯誤的判讀，不是事實。`~/.autosdd/traces/quota_burn.jsonl`
    #       第 5~8 列：`five_hour` 1.0 → 6.0 → 11.0 → **63.0**（22:29:22 → 22:40:56，
    #       11 分鐘、Δ=62pp，與 `R87_HANDOFF.md` 的「Δpct 62」逐字吻合）⇒ 那 13 個 agent
    #       跑了 634 秒、真的燒掉 62pp 訂閱窗才死，**不是被擋在派工口**。舊註解那兩句
    #       「沒有解釋 13/13 全滅」「本機結構上觀測不到」因此都不成立：**R87 的死因至今
    #       未知**，而 `monthly spend limit` 是後果的字面，不是變因。
    #    ② **判準鍵在一個常數上 ⇒ 零鑑別力**：對池子撞頂的帳號，那個 `any(...)` 終生無
    #       條件成立 ⇒ cap 被**永久**釘在 1。它不是「殘餘風險收斂成 1 個 agent」，是把本輪
    #       剛拿掉的否決權（16→0）從後門還回 15/16（16→1）＝掌舵者裁定的「本末倒置」
    #       原樣復發。
    #    ③ **同一個 commit 自帶反證**：`ca9985b` 的 message 逐字「派 1 個 subagent 成功
    #       （63027 tokens / 4.6s）」⇒ 探針已推翻「保險池滿 ⇒ 一定派不出去」，地板卻仍以
    #       「未解釋」為由裝上。
    #    憲法面（就算前提沒被證偽，這道地板仍是明示偏離）：PRD §4.2.3（`:289-298`）是一份
    #    **封閉**的 8 步閘門列舉，任一步命中即短路，而**沒有任何一步讀 overage**；把它掛在
    #    §1.2 原則 5（fail-safe，`:113-114`）之下也不成立——該原則列舉的觸發是「遙測不可得／
    #    逾時／解析失敗／時鐘異常」，**不含**「過去有一次無法解釋的事故」⇒ 那是外推。
    #    附帶效益（拆掉才回來的不變式）：`decision.cap == decision.binding.cap`。地板在時
    #    binding 不再解釋 cap，`quota_messages.throttle_horizon_line()` 取 binding 的
    #    `resets_at` ⇒ 在本輪自己的姿態下會印「這道節流很快就會自己解除」＝假話；而
    #    `quota_gate` 的 free 帶早退寫成 `cap is None`，`cap == 1` 從它底下漏過去。
    #    要保留「先派一個看看」的取證協定是**另案**：正確的鍵不是保險軸的 band，而是
    #    `account_posture()["fallback_available"] is False` **且**訂閱軸已進 prepare 帶；
    #    本輪沒有任何量測支持任何一個門檻值 ⇒ 不在這裡發明數字。
    return Decision(
        cap=binding.cap,
        recommended_fanout=_bound(
            _clamp(int(base * _pace_of(gate, p)), p), binding.cap),
        band=binding.band, binding=binding.axis, per_axis=readings, reason=reason,
        # 🔴 餵**帶號**分鐘（不是 `minutes_to_reset` 那個夾 0 的版本）：時鐘偏移的軸必須
        # 被攤提整個排除。夾 0 之後長窗軸會變成「窗數 1、配額＝全部剩餘」＝**放寬**，
        # 而放寬是本案唯一不准無證據發生的方向（同 `horizon_band` 負值分支的判詞）。
        amort=W.amort_for(_rows(state), tuple(_delta_minutes(a.resets_at, now)
                                              for a in state.axes), ratio, ratio_note))


# M7：每一段只帶**一個** %，且同段必有 `kind=` 與剩餘分鐘（或明文不明）。
def _axis_phrase(r: AxisReading) -> str:
    when = "reset 距離不明" if r.minutes is None else f"剩 {int(r.minutes)} 分鐘"
    note = f" note={r.note}" if r.note else ""
    return (f"kind={r.axis.kind} {r.axis.pct:g}% {when} "
            f"band={r.band} horizon={r.horizon} cap={r.cap}{note}")


def describe(d: Decision) -> str:
    """渲染成人看的一則訊息。🔴 裸的「額度 54%」正是掌舵者當場誤讀的**那個**形狀。"""
    tail = (f"⇒ cap={d.cap} recommended={d.recommended_fanout} band={d.band} "
            f"binding={d.binding.kind if d.binding else '-'} reason={d.reason}")
    if not d.per_axis:
        return f"額度量不到（reason={d.reason}）{tail}"
    return "；".join(_axis_phrase(r) for r in d.per_axis) + "　" + tail


# ── env：門檻的唯一的家，`.env.example` 由它生成（不手寫＝不製造第二個家）─────────
class EnvVar(NamedTuple):
    """一個環境變數的完整宣告。`attr is None` ＝ 逃生口，不進 `Policy`。"""

    name: str
    attr: str | None
    default: object
    kind: str
    lo: float | None
    hi: float | None
    note: str
    section: str


ENV_SPEC: tuple[EnvVar, ...] = (
    EnvVar("AUTOSDD_QUOTA_NOTICE_PCT", "notice_pct", 50.0, "float", 0.0, 100.0,
           "開始注意、少派", "policy"),
    EnvVar("AUTOSDD_QUOTA_CONVERGE_PCT", "converge_pct", 70.0, "float", 0.0, 100.0,
           "開始收斂", "policy"),
    EnvVar("AUTOSDD_QUOTA_PREPARE_PCT", "prepare_pct", 85.0, "float", 0.0, 100.0,
           "準備下一次 Reset", "policy"),
    EnvVar("AUTOSDD_QUOTA_HALT_PCT", "halt_pct", 95.0, "float", 0.0, 100.0,
           "停止並喚醒下一輪", "policy"),
    EnvVar("AUTOSDD_QUOTA_ACCEL_WINDOW_MINUTES", "accel_window_minutes", 30.0,
           "float", 0.0, None, "reset 在這麼近之內 ⇒ 加速（使用者原文的 30m）", "policy"),
    EnvVar("AUTOSDD_QUOTA_FAR_HORIZON_MINUTES", "far_horizon_minutes", 360.0,
           "float", 0.0, None, "超過這麼遠 ⇒ 減速（6h）", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_NOTICE", "cap_notice", 8, "int", 1.0, None,
           "notice 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_CONVERGE", "cap_converge", 4, "int", 1.0, None,
           "converge 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_CAP_PREPARE", "cap_prepare", 2, "int", 1.0, None,
           "prepare 帶的 base cap", "policy"),
    EnvVar("AUTOSDD_QUOTA_PACE_NEAR", "pace_near", 2.0, "float", 1.0, None,
           "reset 近在眼前時的**加速**倍率（下界 1＝不加速；R84／6b）", "policy"),
    EnvVar("AUTOSDD_QUOTA_PACE_FAR", "pace_far", 0.5, "float", 0.0, 1.0,
           "reset 很遠／期程不明時的**減速**倍率（上界 1＝不減速；R84／6b）", "policy"),
    EnvVar("AUTOSDD_QUOTA_MAX_FANOUT", "max_fanout", 16, "int", 1.0, None,
           "加速後的絕對上界", "policy"),
    EnvVar("AUTOSDD_QUOTA_DEGRADED_CAP", "degraded_cap", 4, "int", 1.0, None,
           "量不到時的上限（絕不是「不設限」）", "policy"),
    # 🔴 R91／`DEF-200-097`：本鍵**結構上就是政策鍵**（有 `attr`、型別 `int`、下界 1），
    # 而它先前被渲染在下方〈既有逃生口〉標題底下、夾在兩個 `_OFF` 開關之間 ⇒ 讀者會把它
    # 讀成「關掉某個東西」的開關。逃生口關掉的是守衛，本鍵**永遠只收緊**
    # （`min(cap, override)`，見 `fanout_cap()`），一個字都關不掉 ⇒ 兩者不同族。
    # 修法選的是該列分流欄二擇一裡的「改結構歸類」：`section` 改 `policy`，位置一併上移，
    # 於是結構（`attr`／`kind`）與渲染分節不再互相矛盾。
    EnvVar("AUTOSDD_QUOTA_FANOUT_CAP", "fanout_cap_override", None, "int", 1.0, None,
           "節流帶 cap 的**上限**覆寫（留空＝不覆寫）：只收緊不放寬，halt 帶不吃", "policy"),
    EnvVar("AUTOSDD_QUOTA_GUARD_OFF", None, "", "flag", None, None, "1 ⇒ 額度節流全關", "escape"),
    EnvVar("AUTOSDD_SENTINEL_OFF", None, "", "flag", None, None,
           "1 ⇒ 額度續航哨兵關掉", "escape"),
    EnvVar("AUTOSDD_CONTEXT_GUARD_OFF", None, "", "flag", None, None,
           "1 ⇒ context 阻斷關掉（**與上一個不同的東西**）", "escape"),
    # 🔴 R91：**第四個**逃生口，刻意不與上面三個共用（repo 明文：共用一個會讓「我只是想
    # 暫時別被擋」順手把別的保護一起關掉）。它只關 context 提示的**送達形態**（stdout 的
    # `hookSpecificOutput` ⇒ 退回舊的純 stderr），不關任何判定、不關阻斷、不關哨兵。
    # 上一列刻意壓成一行以騰出這一格：`guardrail_lib` 對本檔的 LOC 預算餘裕實測為 0。
    EnvVar("AUTOSDD_CONTEXT_SIGNAL_OFF", None, "", "flag", None, None, "1 ⇒ 只關送達面", "escape"),
)

_ENV_HEADER = (
    "# ── 額度水位節流：**本檔是範例（.env.example）；實際生效的是 repo 根的 .env** ──",
    "#    用法：copy .env.example .env（原封不動複製即可用），再改你要的那幾個值。",
    "# 🔴 唯一的家＝tools/lib/quota_policy.py 的 ENV_SPEC；本檔是生成物，勿手寫：",
    "#    python tools/lib/quota_policy.py --print-env-example",
    "# 生效路徑三條，優先序 **env > AutoClaude/.env > 根 .env > 出廠預設**：",
    "#   ① repo 根 .env      —— harness 的 hook 讀（tools/lib/quota_gate.py:policy_env）；",
    "#      下方**逃生口那一區也算數**（hook main() 先把這些鍵填成行程級預設，缺席才填）。",
    "#      🔴 本次收斂之前這句對逃生口是假的：三個開關直讀 os.environ ⇒ 在 .env 設也關不掉，",
    "#      而「關掉了」與「沒關掉」外觀完全相同。",
    "#   ② AutoClaude/.env   —— 引擎側讀（autoclaude/utils/config.py:_quota_env）；同名鍵",
    "#      覆寫①。引擎只讀它真的有消費者的那幾個鍵，清單見 AutoClaude/.env.example。",
    "#   ③ .claude/settings.json 的 env 區塊 —— **會**注入 hook 行程（實測：把",
    "#      SDD_ROUTER_QUIET=1 放進去，SessionStart 的 SDD-ROUTER 由 4 行變 0 行）。",
    "# 行內註解（值後面接 ` # …`）會被剝掉 ⇒ 手寫時可以加註解。",
)
_ENV_ESCAPE_HEADER = "# ── 既有逃生口（此前只散落在 hook 註解裡，零使用者可讀清單）──"


# `50.0` 印成 `50`；`None`／空字串印成空（＝未設定）。
def _fmt_default(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# 🔴 R82／C1 的 (b) 半：說明改成**獨立一行**，鍵那一行只剩 `KEY=value`。
# 使用者的標準流程就是 `copy .env.example .env` 再改幾個值 ⇒ 產生器把說明黏在同一行時，
# 那份 `.env` 的每一個值都自帶一段中文說明。(a) 半（`parse_env_text` 剝行內註解）讓手寫
# 的行內註解也不會壞，但**檔案本身乾淨**是另一件事：它讓「複製過去就能用」在肉眼上也成立，
# 而不是靠消費者收拾。兩半都做的理由就是這個——它們各自守住一個方向。
def render_env_example() -> str:
    """生成 `.env.example` 全文（決定性；`.env.example` 不得手寫）。"""
    lines = list(_ENV_HEADER)
    seen_escape = False
    for spec in ENV_SPEC:
        if spec.section == "escape" and not seen_escape:
            seen_escape = True
            lines.extend(("", _ENV_ESCAPE_HEADER))
        hint = "（範例值，可依帳號方案調整）" if spec.section == "policy" else ""
        lines.extend((f"# {spec.note}{hint}",
                      f"{spec.name}={_fmt_default(spec.default)}"))
    return "\n".join(lines) + "\n"


# 🔴 R82／C1：**行內註解必須在這裡被剝掉**，而這一格就是本檔與消費者之間的縫。
# `render_env_example()` 產出的每一行都是 `KEY=值<補白>#說明`（同一行！），而消費者
# `quota_gate.policy_env()` 此前做的是 `partition("=")` 再 `strip()` ⇒ 說明文字整段
# 留在值裡。實測後果：12 個帶值的鍵**全部**解析失敗、全部退回預設，也就是說使用者照
# `.env.example` 抄一份 `.env` 之後，訴求 6c 的「門檻可調」在端到端是完全不成立的；
# 而 `AUTOSDD_QUOTA_GUARD_OFF=` 這種空值鍵更糟——不剝註解時它的值變成非空字串
# `"# 1 ⇒ 整條額度節流關掉"`，於是**照抄範例檔就會把整條額度節流關掉**。
# 逃過的原因是判準的形狀：`env_example_problems()` 拿生成物**跟自己比**，從不呼叫
# 消費者的解析器 ⇒ 兩個家互相一致、都沒對消費者測。回歸鎖＝本檔的 round-trip 判準
# `tools/tests/test_quota_policy.py::TestM6TheGeneratedFileSurvivesItsOwnConsumer`。
# 只認「行首或空白之後的 `#`」：值本身帶 `#` 時不誤剝（未來若有非數值旋鈕）。
def _value_of(raw: str) -> str:
    cut = next((i for i, ch in enumerate(raw)
                if ch == "#" and (i == 0 or raw[i - 1].isspace())), len(raw))
    return raw[:cut].strip()


def parse_env_text(text: str) -> dict[str, str]:
    """`.env`／`.env.example` 文字 → `{鍵: 值}`。**唯一的解析器**（見上方 WHY）。"""
    pairs = (ln.strip().partition("=") for ln in text.splitlines()
             if ln.strip() and not ln.strip().startswith("#") and "=" in ln)
    return {k.strip(): _value_of(v) for k, _, v in pairs}


def env_example_problems(text: str) -> list[str]:
    """`.env.example` ↔ `ENV_SPEC` **雙向**鎖：幽靈鍵／漏鍵／不等於生成物。"""
    problems = []
    keys = list(parse_env_text(text))
    declared = [spec.name for spec in ENV_SPEC]
    problems += [f"[幽靈鍵] {k} 不在 ENV_SPEC（improving_92 清過一批同型）"
                 for k in keys if k not in declared]
    problems += [f"[漏鍵] ENV_SPEC 的 {k} 沒出現在 .env.example"
                 for k in declared if k not in keys]
    if text != render_env_example():
        problems.append("[不同步] 磁碟內容 != render_env_example()（請重生，勿手寫）")
    return problems


def _parse_env_number(raw: str, spec: EnvVar, problems: list[str]) -> float | int | None:
    """壞值一律**進 problems ＋ 回 None（採用預設）**；🔴 不得靜默夾。"""
    try:
        value = float(raw)
    except ValueError:
        problems.append(f"{spec.name}={raw!r} 不是數字 ⇒ 採用預設 {spec.default}")
        return None
    if spec.lo is not None and value < spec.lo:
        problems.append(f"{spec.name}={raw!r} 低於下界 {spec.lo} ⇒ 採用預設 {spec.default}")
        return None
    if spec.hi is not None and value > spec.hi:
        problems.append(f"{spec.name}={raw!r} 高於上界 {spec.hi} ⇒ 採用預設 {spec.default}")
        return None
    return int(value) if spec.kind == "int" else value


# 🔴 `problems` 非空時呼叫端必須出聲一次（`note_degraded()`）——「設了沒生效而沒有人
# 知道」正是 6c 最容易假交付的一格。
def load_policy(env: Mapping[str, str]) -> tuple[Policy, list[str]]:
    """從 mapping（**不是 os.environ**）讀門檻。回 `(policy, problems)`。"""
    problems: list[str] = []
    values: dict[str, object] = {}
    for spec in ENV_SPEC:
        if spec.attr is None:
            continue
        raw = str(env.get(spec.name, "")).strip()
        if not raw:
            continue
        parsed = _parse_env_number(raw, spec, problems)
        if parsed is not None:
            values[spec.attr] = parsed
    policy = replace(DEFAULT_POLICY, **values) if values else DEFAULT_POLICY
    ladder = (policy.notice_pct, policy.converge_pct, policy.prepare_pct, policy.halt_pct)
    if not all(a < b for a, b in zip(ladder, ladder[1:])):
        problems.append(f"四個錨點必須嚴格遞增，實得 {ladder} ⇒ 整組採用預設")
        return DEFAULT_POLICY, problems
    if policy.accel_window_minutes >= policy.far_horizon_minutes:
        problems.append(
            f"accel_window({policy.accel_window_minutes}) 必須小於 "
            f"far_horizon({policy.far_horizon_minutes})，否則 mid 檔是空的 ⇒ 整組採用預設")
        return DEFAULT_POLICY, problems
    mono = policy_monotonicity_problems(policy)
    if mono:
        return DEFAULT_POLICY, problems + [*mono, "⇒ 整組採用預設"]
    return policy, problems


if __name__ == "__main__":  # pragma: no cover
    # 🔴 本檔的 CLI 印中文（用法字串、`.env.example` 的每一行說明），而非 UTF-8 locale
    # 下 stdout 直接 UnicodeEncodeError、stderr 降解成 \uXXXX（DEF-101-789 同型；
    # `tools/tests/test_subprocess_encoding_hygiene.py::TestEntryPointStdioProtection`
    # 就是守這個，落地時實測被它抓到 `用法：`）。保護只掛在 `__main__`：本檔被 hook 與
    # 測試以模組 import，import 期換串流會污染載具。走 SSOT 而非就地 reconfigure，
    # 理由見 `tools/lib/platform_utils.py` 檔頭（那段實作曾被複製 8 份、6 份漏分支），
    # 且就地寫會撞 `test_platform_utils_dedup.py` 的 shrink-only 行內複本棘輪。
    from platform_utils import init_utf8_streams

    init_utf8_streams()
    if "--print-env-example" in sys.argv[1:]:
        sys.stdout.write(render_env_example())
    else:
        sys.stderr.write("用法：python tools/lib/quota_policy.py --print-env-example\n")
        raise SystemExit(2)
