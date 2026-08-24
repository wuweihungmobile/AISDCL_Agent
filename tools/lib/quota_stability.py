"""併發建議值的平穩性機制：死區／變化率限制／最小停留時間（PRD §4.2.4(b)(c)(d)）。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R102 第二棒／PRD §4.2.4(b)(c)(d)；接續 quota_availability.py 的 (a)）  round-label-ok
# ---------------------------------------------------------------------------
# 病：`quota_policy.decide()` 是**無狀態**純函式——每次呼叫只看「這一刻」的水位／horizon，
# 對「上一次給的併發上限是多少、那個值維持了多久」零記憶。水位在帶界附近抖動一下
# （例：61%/59% 反覆跨過 converge_pct=70 的鄰域、或 horizon 在 near/mid 邊界抖動）就會讓
# `cap` 在 8↔4 之間逐次翻動——這正是 PRD §4.2.4 整節要治的「平穩性」缺口。
#
# 解法必須是**跨呼叫的狀態機**（同 `quota_availability.py` 的立案理由）：dead-zone／slew／
# dwell 三者的輸入都需要「上一次穩定值是多少、上次變更是什麼時候」，而 `decide()` 本身
# **不得**因此變成有狀態——同一份純函式必須繼續可以被 `--pace`、`degraded_posture()` 等
# 多個獨立呼叫端各自安全呼叫。⇒ 本檔是 `decide()` **之後**的一層濾波器，不是改寫 `decide()`。
#
# 🔴 為什麼是新檔，不塞進 `quota_policy.py`（零 I/O 的判讀層）或 `quota_gate.py`：
#   · `quota_policy.py` 檔頭明文「零 I/O、零網路」——本檔需要跨行程持久化，落點不合。
#   · `quota_gate.py` 是 `guardrail_hub` tier；接線只加呼叫，機制本體另開檔，同
#     `quota_availability.py` 已示範過的分工（狀態機／持久化 vs 接線）。
#
# 🔴 三個機制在整數域上的收斂形狀（讀這裡的實作前請先讀這段，否則會覺得「死區去哪了」）：
#   (b) 死區：`|C_target − C_current| < 1`。cap 恆為整數 ⇒ 該不等式在整數域上**恰好等價於**
#       `C_target == C_current`——死區不是另一段獨立分支，是下面 clamp 算式在相等時的自然
#       結果（`target == current` 時兩個方向的分支都會算出「不變」）。
#   (c) 變化率限制：**只管放寬方向**——放寬走 `clamp(C_target, C_current, C_current+1)`，
#       每次呼叫至多前進一階。收緊方向（`target < current`，含 `measured→unmeasured`）
#       PRD §4.2.4(c) v2.1.8 逐字「不限速，允許直接到位」，**不分帶別**，一步到位
#       （含直接到 0）——🔴 R102 修復（四方審查 F1/F15/F16/F23）：此前誤把舊版  round-label-ok
#       （v2.0~v2.1.7）「僅升級到 DRAINING／FREEZING 才允許直接歸零」的窄例外當成新
#       條文實作，把範圍收窄回舊版，方向上更不安全（該立刻收緊的保護動作被拖慢）。
#       `SAFETY_BANDS` 常數保留（見其宣告處），但**不再**用來限制收緊速度。
#   (d) 最小停留時間：**只**卡「增加」方向——距上次變更 < `min_dwell_seconds` 時，即使
#       `target > current` 也維持不變；「減少」方向從不被 dwell 卡住（同 (c) 的收緊優先）。
#   `unmeasured=True` 時，「增加」方向被整段關閉（不是變慢，是直接不允許），對應 PRD
#   逐字「放寬方向全部失效」；「減少」方向則永遠视同安全方向，直接到位。
#
# 🔴 `cap is None`（`BAND_FREE`，不設限）刻意**不**進本狀態機、直接放行且清空持久狀態：
#   free 帶代表「水位很寬鬆，沒有任何節流理由」，PRD 平穩性機制要治的是**節流值之間**的
#   抖動，不是「要不要節流」本身；把「回到不設限」也做成漸進爬升，只會讓使用者在明明
#   已經寬鬆的情況下還被人為卡住，且與 R82 訴求 6b「50% 以下無事可做」的既有設計衝突。
#   清空持久狀態的理由：下一次重新進入受限帶時，之前那段「不受限」期間發生了什麼完全
#   不重要（沒有連續性要保），從那一刻起把它當成全新的第一次收斂即可（同 `_default_state`
#   對「沒有可信歷史」的既有處置）。
#
# 🔴 持久化形態逐字照抄 `quota_availability.py`（R7 規範性原子寫入：
#   `tmp → flush() → os.fsync(fd) → close() → os.replace(tmp, final)`），本檔不重新發明。
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import endurance_env  # noqa: E402  # 持久目錄 SSOT（同 quota_availability.py 的依賴面）
import quota_ledger  # noqa: E402  # R102：`with_lock()` 互斥原語（同 quota_availability.py）  round-label-ok
import quota_policy  # noqa: E402  # 帶別常數（BAND_PREPARE／BAND_HALT）；零 I/O，可安全依賴
from quota_messages import _aware  # noqa: E402  # ISO 字串 → aware datetime 的唯一解析器

#: PRD (c) 舊條文（v2.0~v2.1.7）點名的 DRAINING／FREEZING 帶別，逐格對映
#: `quota_gate.DRAINING_BANDS`（R91 既有登記：`(BAND_PREPARE, BAND_HALT)`）。本檔不
#: import `quota_gate`（那是 `guardrail_hub`，會把依賴方向反過來），改由
#: `quota_policy` 的兩個帶別常數自己組——與 `quota_gate.DRAINING_BANDS` 的同步由
#: `tools/tests/test_quota_policy.py::StabilityConstantsTest` 的方向鎖測試直接比對
#: 兩者相等。
#: 🔴 R102 修復（四方審查 F1/F3/F15/F16/F23）：v2.1.8 新條文的收緊不限速範圍是**任何**  round-label-ok
#: `target < current`，不只這個集合——本常數**不再**用來限制收緊速度（`stabilize()`
#: 已拿掉 `band in SAFETY_BANDS` 那個 gate）。保留這個常數只是因為它仍是一個誠實的
#: 事實（「舊條文點名的帶別」），且與 `quota_gate.DRAINING_BANDS` 的同步仍值得鎖住；
#: 它已不對本檔任何行為有影響。
SAFETY_BANDS = frozenset({quota_policy.BAND_PREPARE, quota_policy.BAND_HALT})

#: PRD (d) 逐字出廠值：300 秒。可由 `.env`／`Policy.min_dwell_seconds` 調（見 `quota_policy.py`
#: 該欄位註解），本檔的常數只是**函式簽章的預設值**，不是唯一的家。
MIN_DWELL_SECONDS_DEFAULT = 300.0

#: 持久化檔名（住 `endurance_env.trace_dir()`）。per-account，不帶 session id——理由同
#: `quota_availability.STATE_NAME`：併發上限的平穩歷史是帳號層級的事實。
STATE_NAME = "autosdd_quota_stability.json"
SCHEMA = "autosdd.quota_stability.v1"


@dataclass(frozen=True)
class StabilityState:
    """併發上限平穩機制的**全部持久事實**。`cap` 恆為非負整數（free 帶不落地，見檔頭）。"""

    cap: int
    last_change: str  # 最近一次「數值真的變了」的時刻（aware ISO 字串）


def state_path() -> Path:
    return endurance_env.trace_dir() / STATE_NAME


def load_state(path: Path | None = None) -> StabilityState | None:
    """讀回上次持久化的狀態；讀不到／格式不對／schema 不符一律回 `None`（＝沒有可信歷史，
    下一次 `stabilize()` 會把這一次的目標值當成起點，不偽造一段假的停留時間）。
    """
    try:
        data = json.loads((path or state_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    cap, last_change = data.get("cap"), data.get("last_change")
    if (not isinstance(cap, int) or isinstance(cap, bool) or cap < 0
            or not isinstance(last_change, str) or _aware(last_change) is None):
        return None
    return StabilityState(cap, last_change)


def save_state(state: StabilityState | None, path: Path | None = None) -> bool:
    """R7 同款原子寫入；`state=None` 表示**清空**（free 帶，見檔頭），改為刪除既有檔。"""
    target = path or state_path()
    if state is None:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            return False
        return True
    payload = json.dumps(
        {"schema": SCHEMA, "cap": state.cap, "last_change": state.last_change},
        ensure_ascii=False)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


def stabilize(prev: StabilityState | None, target: int, band: str, now: datetime, *,
             min_dwell_seconds: float = MIN_DWELL_SECONDS_DEFAULT,
             unmeasured: bool = False) -> StabilityState:
    """遲滯的**一步**（純函式，紅綠由呼叫端合成注入自證；同 `quota_availability.advance()`）。

    `target`＝這一刻 `decide()` 算出來的 cap（**呼叫端必須先排除 `None`**，見 `evaluate()`）。
    沒有歷史（`prev is None`）⇒ 直接採用這一刻的目標值，不偽造停留時間（同
    `quota_availability._default_state` 的既有紀律）。
    """
    if prev is None:
        return StabilityState(target, now.isoformat(timespec="seconds"))
    current = prev.cap
    if target == current:
        return prev  # (b) 死區：整數域上 |diff|<1 ⟺ 相等
    if target < current:
        # 收緊方向：PRD §4.2.4(c) v2.1.8 逐字「收緊方向（cap 變小、或 measured→unmeasured）：
        # 不限速，允許直接到位」——沒有帶別限定詞。這裡不分帶別，一律直接到位（含直接歸零）。
        # 🔴 R102 修復（四方審查 F1/F15/F16/F23）：此前誤把舊版（v2.0~v2.1.7）「僅  round-label-ok
        # DRAINING/FREEZING 才不限速」的窄例外當成新條文實作，範圍反而更窄、更不安全
        # （見 `SAFETY_BANDS` 的檔頭註解與新版條文對照）。`band` 參數保留給呼叫端既有介面
        # 相容（`quota_gate.py` 兩處呼叫皆傳入 `decision.band`），本函式內部不再用它限速。
        return StabilityState(target, now.isoformat(timespec="seconds"))
    # target > current：放寬方向
    if unmeasured:
        return prev  # PRD (a) 接線：量不到 ⇒ 放寬方向全部失效，維持不變
    changed_at = _aware(prev.last_change)
    dwell = (now - changed_at).total_seconds() if changed_at is not None else min_dwell_seconds
    if dwell < min_dwell_seconds:
        return prev  # (d) 尚未停留滿：不允許增加
    return StabilityState(current + 1, now.isoformat(timespec="seconds"))  # (c) 至多 +1


def evaluate(target: int | None, band: str, now: datetime, *,
            min_dwell_seconds: float = MIN_DWELL_SECONDS_DEFAULT,
            unmeasured: bool = False) -> int | None:
    """**唯一正規入口**：讀舊狀態 → 套用平穩機制 → 落地 → 回傳穩定後的 cap。

    `target=None`（free 帶）⇒ 直接放行且清空持久狀態（見檔頭），回 `None`。
    """
    if target is None:
        save_state(None)
        return None

    def _critical_section() -> StabilityState:
        nxt = stabilize(load_state(), target, band, now,
                        min_dwell_seconds=min_dwell_seconds, unmeasured=unmeasured)
        save_state(nxt)
        return nxt
    # 🔴 R102 修復（四方審查 F24／QA MUST FIX）：同 `quota_availability.evaluate()`——  round-label-ok
    # 讀-算-寫整段互斥，理由與命名慣例見 `quota_ledger.with_lock()` docstring。
    lock_path = state_path().with_suffix(state_path().suffix + ".lock")
    return quota_ledger.with_lock(lock_path, _critical_section).cap
