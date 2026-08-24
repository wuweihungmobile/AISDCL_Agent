"""可得性軸（`measured`/`unmeasured`）遲滯狀態機與其跨行程持久化。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R102／PRD §4.2.4(a) ＋ R7；此前 repo 全樹對 hysteresis／dwell／  round-label-ok
# slew／遲滯／死區／停留時間／變化率零命中，DEF-200-204 已記載此缺口）
# ---------------------------------------------------------------------------
# 病：`quota_gate.read_quota()` 每次呼叫都**當場**判定 `state.usable()`，零記憶——
# 一次瞬斷（`bad-cache`／`stale-cache`）與剛恢復的第一次成功讀數在 `decide()` 眼裡
# 逐字相同（`axes != ()`）。PRD 的遲滯帶要求「離開 unmeasured 需連續 N 次成功 **且**
# 已停留滿一段時間」——這件事不可能是無狀態的：判定的輸入除了「這次讀到了沒」，
# 還需要「上一次的狀態是什麼、已經連續幾次、進入現狀已經多久」，而這三格必須跨行程
# 存活（hook 每次呼叫都是新行程）。⇒ 本檔的核心是**一個帶持久化的狀態機**，不是
# 又一個純函式判準。
#
# 🔴 為什麼是**新的一支檔**，而不是塞進 `quota_gate.py`（任務書預設建議的落點）
# ------------------------------------------------------------------------------
# 三條理由，各自獨立成立：
#   ① **`quota_gate.py` 是 `guardrail_hub` tier 裡**唯一**一支成員**
#      （`ROOT_TOOLS_HUB_MEMBER_CAP=1`，見 `AutoClaude/tools/check_loc_budget.py`）。
#      落地當回合它已是全 repo `tools/lib/` 裡最大的檔（assertion=366/500）；本狀態機
#      連同持久化＋降級偵測＋測試支援函式落地後估計 +90～120 行，會把餘裕吃掉近乎
#      一半。本 repo 對這一格的既定紀律是「破線後不是調高預算，而是拆職責／抽共用
#      模組」——這裡是在**還沒破線之前**就先做那件事，而不是等破線才做。
#   ② **依賴方向會反過來**。若塞進 `quota_gate.py`，`state.usable()` 產生的那一刻就要
#      呼叫這裡的 `advance()`；但 `quota_escalation.py`（既有）已經是
#      `quota_escalation → quota_gate` 這個方向（它消費 `quota_gate.read_quota`／
#      `policy_env`）。把遲滯狀態機焊進 `quota_gate.py` 本體沒有這個問題，但如果為了
#      複用 `quota_gate.note_degraded()` 的「出聲＋TTL 閂鎖」機制而讓本檔改為
#      `import quota_gate`，那才是真正的風險：本檔**未來**會被 `quota_gate` 呼叫
#      （它是 `read_quota()` 之後的下一步），若本檔也回頭 import `quota_gate`，
#      兩者互為對方的一部分 ⇒ `runpy` 以 `__main__` 起任一邊時會把對方整支載入第二次
#      （本 repo 對 `quota_ledger`／`quota_escalation` 已有這個判例，見 `quota_gate.py`
#      檔頭 R84／ARCH-10 那段）。⇒ 本檔刻意只依賴**葉子模組**
#      （`endurance_env`／`quota_ledger`／`platform_utils`／`quota_messages`），
#      不 import `quota_gate`，也不 import `quota_escalation`。
#   ③ **失效模式不同，測試面也該分開**。這裡的失敗是「跨行程競態」與「磁碟原子性」
#      （同 `quota_ledger.py` 的既有立案理由），而 `quota_gate.py` 的其餘部分是「一次
#      呼叫、一次判定」。混在一個檔裡會讓兩種測試風格（合成注入 vs 檔案系統操作）
#      擠在同一支檔，同 `quota_ledger.py` 檔頭②的既有判詞。
#
# 🔴 落點在 `tools/lib/`：`guardrail_lib` tier（≤400 assertion 行，見
# `check_loc_budget.py` 的 `ROOT_TOOLS_TIERS`）。本檔遠低於該預算。
#
# 🔴 為什麼「退回系統暫存」的偵測**不**在本檔重新推導 `trace_dir()` 的內部邏輯
# ------------------------------------------------------------------------------
# `endurance_env.trace_dir()` 此前把「退化了沒」吞掉，呼叫端只拿得到最終目錄。若本檔
# 自己重算一次「應該是哪裡」（環境變數覆寫 or 家目錄）來跟 `trace_dir()` 的回傳值比對，
# 就是把「家目錄／覆寫優先序」這份知識複製了第二份——本 repo 判過這個形態
# （`Find-GitBash`／`core.quotepath` 判例）。正確做法是讓 SSOT 自己吐出第二格布林：
# `endurance_env.trace_dir_status() -> (dir, degraded)`，本檔只消費那個布林，不重新
# 推導判準本身。`trace_dir()` 對既有呼叫端的行為逐字不變（見該檔的 R102 訂正段）。  round-label-ok
#
# 🔴 誠實劃界（R7 交付範圍）
# ------------------------------------------------------------------------------
#   · 本檔交付：狀態機（`advance`）＋ 持久化（`load_state`／`save_state`，R7 規範性
#     原子寫入形態）＋ 退回系統暫存的三件事（loud 一次／自檢文字／視同 unmeasured）。
#   · 本檔**不**交付：把 `effective_availability()` 接進 `quota_gate.quota_gate()` 或
#     `quota_policy.decide()`（PRD (b)(c)(d) 死區／變化率／最小停留時間，以及 R16 的
#     啟動自檢 H6／H7）——任務書明文本輪範圍只到 (a) 款與 R7，接線與其餘款是後續任務。
#     `evaluate()` 是為那次接線準備的單一入口，見其 docstring。
from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 🔴 刻意只依賴葉子模組（見檔頭②）：一律裸名 import，同 `quota_gate`／`quota_escalation`
# 既有紀律（`tools/lib/*` 互相 import 必須是裸名，`from lib import X` 會讓同一份原始碼
# 在同一行程裡有兩個模組物件，見 `quota_gate.py` 檔頭 R84／ARCH-10 那段）。
import endurance_env  # noqa: E402
import quota_ledger  # noqa: E402  # TTL 閂鎖（`claim_once`），複用既有原子原語
from platform_utils import emit_to_model  # noqa: E402  # 送達模型的唯一發射口
from quota_messages import _aware  # noqa: E402  # ISO 字串 → aware datetime 的唯一解析器

#: 可得性軸的兩個值。**不是** `quota_policy.BAND_*` 的第五個成員——那一族是水位帶，
#: 這一軸答的是完全不同的問題（「這次讀數算不算數」而非「水位多高」）。
AVAILABILITY_MEASURED = "measured"
AVAILABILITY_UNMEASURED = "unmeasured"

#: 🔴 兩個門檻的**出廠值**與 `quota_policy.Policy.availability_exit_streak`／
#: `.availability_min_dwell_seconds` 逐格同步（那裡才是「全部門檻的唯一的家」，見該檔
#: 欄位註解）。本檔重複宣告是因為 `advance()` 必須維持**零 I/O、零 Policy 依賴**的純
#: 函式簽章（呼叫端把值算好餵進來，同 `quota_policy.axis_cap(pct, minutes, p)` 的既有
#: 分工：判讀層的門檻由呼叫端從 `Policy` 讀出，不在函式內部 import 別的模組去現查）。
#: 兩處**必須**同步的斷言見 `tools/tests/test_quota_policy.py::AvailabilityHysteresisTest`。
AVAILABILITY_EXIT_STREAK_DEFAULT = 2
AVAILABILITY_MIN_DWELL_SECONDS_DEFAULT = 360.0

#: 持久化檔名（住 `endurance_env.trace_dir()`）。per-account，不帶 session id——同
#: `quota_gate.QUOTA_TRACE_NAME` 等既有紀律：可得性是帳號層級的事實，不是某一次
#: session 的性質。
STATE_NAME = "autosdd_quota_availability.json"
#: 檔案 schema 字串（升版判準：不等於本字串 ⇒ 視為沒有可信的舊狀態，見 `load_state`）。
SCHEMA = "autosdd.quota_availability.v1"
#: 退回系統暫存那句話的閂鎖 TTL（複用 `quota_ledger.claim_once` 的既有原子原語）。
#: 🔴 刻意是本檔自己的常數、不是 `import quota_gate` 去借 `QUOTA_CACHE_TTL_SECONDS`
#: ——見檔頭②的方向規則。180 秒是同一個量級的**獨立**選擇：這件事發生的頻率上界是
#: 每次 `evaluate()` 呼叫，而呼叫頻率與額度刷新同級，故沿用同一個數量級並不巧合，
#: 但兩者在資料上互不引用。
DEGRADED_TRACE_LATCH_SECONDS = 180.0

#: R7 (ii)：自檢輸出必須逐字含這一段話。
DEGRADED_TRACE_PHRASE = "遲滯已降級"


@dataclass(frozen=True)
class AvailabilityState:
    """可得性軸的**全部持久事實**。`streak` 只在 `unmeasured` 期間有意義（見 `advance`）。"""

    availability: str
    entered_at: str  # 進入*目前*這個 availability 值的時刻（aware ISO 字串）
    streak: int = 0  # unmeasured 期間累積的連續 usable 次數；離開／重新進入時歸零


def _default_state(now: datetime) -> AvailabilityState:
    """沒有可信舊狀態時的起點：`measured`，即刻視為已停留（不得無中生有一段假歷史）。"""
    return AvailabilityState(AVAILABILITY_MEASURED, now.isoformat(timespec="seconds"), 0)


def state_path() -> Path:
    """持久化位置：`endurance_env.trace_dir()`（見該檔——這是**持久**目錄，非 `$TMPDIR`）。"""
    return endurance_env.trace_dir() / STATE_NAME


def load_state(path: Path | None = None, now: datetime | None = None) -> AvailabilityState:
    """讀回上次持久化的狀態；讀不到／格式不對／schema 不符一律回**保守起點**（`measured`）。

    🔴 為什麼壞掉時回 `measured` 而不是 `unmeasured`：這不是「量到了」的假話——起點本身
    不代表任何一次量測，它只是「還沒有可信歷史」。`advance()` 的下一步會立刻用**這一次**
    真實的 `usable` 覆寫它；壞掉的舊檔絕不能讓「這一次明明量得到」被舊資料的 unmeasured
    污染而拖住（那會是對 dwell 時間的偽造）。
    """
    now = now or datetime.now().astimezone()
    try:
        data = json.loads((path or state_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _default_state(now)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return _default_state(now)
    availability = data.get("availability")
    entered_at = data.get("entered_at")
    streak = data.get("streak")
    if (availability not in (AVAILABILITY_MEASURED, AVAILABILITY_UNMEASURED)
            or not isinstance(entered_at, str) or _aware(entered_at) is None):
        return _default_state(now)
    return AvailabilityState(availability, entered_at,
                             int(streak) if isinstance(streak, (int, float)) else 0)


def save_state(state: AvailabilityState, path: Path | None = None) -> bool:
    """R7 規範性原子寫入：`tmp → flush() → os.fsync(fd) → close() → os.replace(tmp, final)`。

    每次寫入**整份取代**那兩欄狀態（`availability`／`availability_entered_at`），不是
    局部修補——同 `AutoClaude/autoclaude/infra/repositories/file_state_repository.py`
    既有寫法的形狀（本檔照抄該檔的原子換名骨架，不重新發明一套：`tmp = target.
    with_suffix(".tmp")` → 開檔寫入 → `flush()` → `fsync(fileno())` → `replace()`）。
    寫不進去回 `False`（**不得**升級為故障源，同本 repo 對「痕跡留不下來」的既有紀律：
    `quota_escalation._write`／`endurance_env.trace_dir` 皆同此方向）。
    """
    target = path or state_path()
    payload = json.dumps({
        "schema": SCHEMA, "availability": state.availability,
        "entered_at": state.entered_at, "streak": state.streak,
    }, ensure_ascii=False)
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


def advance(prev: AvailabilityState, usable: bool, now: datetime, *,
           exit_streak: int = AVAILABILITY_EXIT_STREAK_DEFAULT,
           min_dwell_seconds: float = AVAILABILITY_MIN_DWELL_SECONDS_DEFAULT) -> AvailabilityState:
    """遲滯狀態機的**一步**（純函式，紅綠由呼叫端合成注入自證）。

    PRD §4.2.4(a) 逐字：
      · 進入 `unmeasured`：`usable=False` ⇒ **立即生效**，不受遲滯與 dwell 約束——
        不論目前是哪一個狀態，一旦這次量不到就當場翻（若已在 `unmeasured`，
        `entered_at` 不動：那個時刻是**這一段** unmeasured 的起點，不是「最近一次
        量不到」，重算會偽造成更短的停留時間）。
      · 離開 `unmeasured`：連續 `exit_streak` 次 `usable=True` **且**
        `(now − entered_at) ≥ min_dwell_seconds` 才成立；兩個條件都沒有算分別滿足
        ——`streak` 未達標時**不得**因為 dwell 已過就放行，反之亦然。
      · 單次量測失敗又立即恢復：`usable` 在 `unmeasured` 期間任何一次為 `False`，
        `streak` 當場歸零（見下方 `usable=False` 分支對已在 `unmeasured` 的處理）
        ⇒ 不會因為「這一輪之前已經連續對過幾次」而把這次失敗之後的第一次成功
        誤判成「快滿足了」。
    """
    if not usable:
        if prev.availability == AVAILABILITY_UNMEASURED:
            return AvailabilityState(AVAILABILITY_UNMEASURED, prev.entered_at, 0)
        return AvailabilityState(AVAILABILITY_UNMEASURED, now.isoformat(timespec="seconds"), 0)
    if prev.availability == AVAILABILITY_MEASURED:
        return prev  # 已經是 measured，這次成功什麼都不改變（沒有「停留」這回事）
    streak = prev.streak + 1
    entered = _aware(prev.entered_at)
    dwell = (now - entered).total_seconds() if entered is not None else -1.0
    if streak >= exit_streak and dwell >= min_dwell_seconds:
        return AvailabilityState(AVAILABILITY_MEASURED, now.isoformat(timespec="seconds"), 0)
    return AvailabilityState(AVAILABILITY_UNMEASURED, prev.entered_at, streak)


def _trace_degraded_stamp() -> Path:
    """降級閂鎖檔**必須**落在真的寫得進去的地方——用 `tempfile.gettempdir()` 本身，
    不是 `state_path()`（那條路此刻正是壞的，見呼叫端 `evaluate()` 的判斷順序）。
    """
    return Path(tempfile.gettempdir()) / "autosdd_quota_availability_degraded.stamp"


def trace_degradation_notice(dir_path: Path) -> str:
    """R7 (ii)：自檢輸出的那一句，**逐字**含 `DEGRADED_TRACE_PHRASE` 與退回後的實際路徑。"""
    return (f"⚠️  {DEGRADED_TRACE_PHRASE}：可得性狀態的持久目錄已退回系統暫存 "
            f"（實際路徑：{dir_path}）⇒ 本次判定視同 unmeasured（收緊側）。")


def _note_trace_degraded(dir_path: Path, *, event: str = "PreToolUse") -> str:
    """R7 (i)：loud 一次（TTL 閂鎖，避免每次 `evaluate()` 呼叫都吵）。回「說了什麼」。

    🔴 走 `platform_utils.emit_to_model`（本 repo 送達模型的**唯一**發射口，見
    `quota_gate.py` 檔頭 R91 那段）＋ `stderr`，而不是 `quota_escalation.notify()`
    ——理由見本檔檔頭②（避免回頭 import `quota_gate`／`quota_escalation` 造成循環）
    ＋ 語意不合（`notify()` 是**預設關閉**的桌面彈窗，opt-in；R7 這一格是「持久化本身
    已經退化」，必須不受使用者要不要看桌面通知的偏好影響，同 `note_degraded()` 對
    額度降級的既有紀律：那個管道也是 stderr＋`emit_to_model`，不是桌面通知）。
    """
    if not quota_ledger.claim_once(_trace_degraded_stamp(), DEGRADED_TRACE_LATCH_SECONDS):
        return ""
    msg = trace_degradation_notice(dir_path)
    sys.stderr.write(msg + "\n")
    emit_to_model(event, msg)
    return msg


def evaluate(now: datetime, usable: bool, *, exit_streak: int | None = None,
            min_dwell_seconds: float | None = None, event: str = "PreToolUse") -> AvailabilityState:
    """**唯一正規入口**：讀舊狀態 → 判斷持久目錄是否已退化 → 套用遲滯 → 落地 → 回傳。

    這是為將來接進 `quota_gate.quota_gate()`／`quota_policy.decide()` 準備的單一呼叫點
    （本輪任務範圍不含那次接線，見檔頭〈誠實劃界〉）：呼叫端只需要把「這次 `read_quota()`
    的 `state.usable()`」餵進來，不必自己重算持久化路徑或退化判準。

    🔴 R7 (iii)：持久目錄退化時，**這一次**回傳的 `AvailabilityState` 一律是
    `unmeasured`（`entered_at=now`，不論遲滯狀態機本來要給出什麼答案）——「視同
    unmeasured（走收緊側）」逐字指的是**這一次判定**，不是把磁碟上的舊狀態覆寫成
    一段假的歷史；下一次呼叫若目錄已經復原，遲滯仍然是連續的（因為退化的那一次
    根本沒有被 `save_state()`，見下方分支）。
    """
    exit_streak = AVAILABILITY_EXIT_STREAK_DEFAULT if exit_streak is None else exit_streak
    min_dwell_seconds = (AVAILABILITY_MIN_DWELL_SECONDS_DEFAULT if min_dwell_seconds is None
                         else min_dwell_seconds)
    dir_path, degraded = endurance_env.trace_dir_status()
    if degraded:
        _note_trace_degraded(dir_path, event=event)
        # 🔴 刻意**不**呼叫 `save_state()`：目錄本身就是壞的，寫進去大概率也是
        # `tempfile.gettempdir()`（`state_path()` 會用同一個 `trace_dir()`）——那等於
        # 把「這一次是被迫收緊」持久化成看起來像「真的連續量不到」的歷史，下一次目錄
        # 復原後反而要多等一輪 dwell。不落地才是對「量不到 ≠ 量到零」這條紀律誠實的做法。
        return AvailabilityState(AVAILABILITY_UNMEASURED, now.isoformat(timespec="seconds"), 0)

    def _critical_section() -> AvailabilityState:
        prev = load_state(now=now)
        nxt = advance(prev, usable, now,
                      exit_streak=exit_streak, min_dwell_seconds=min_dwell_seconds)
        save_state(nxt)
        return nxt
    # 🔴 R102 修復（四方審查 F24／QA MUST FIX）：讀-算-寫整段用 `quota_ledger.with_lock()`  round-label-ok  # noqa: E501
    # 互斥，不是只有寫入本身原子——見該函式 docstring 的立案（PRD §4.2.4 R7「不得自己寫
    # check-then-act」）。鎖檔與狀態檔同目錄、同名 `.lock` 尾碼，同 `save_state()` 的
    # `.tmp` 命名慣例。
    lock_path = state_path().with_suffix(state_path().suffix + ".lock")
    return quota_ledger.with_lock(lock_path, _critical_section)
