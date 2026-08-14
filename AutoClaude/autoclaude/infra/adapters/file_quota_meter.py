# FileQuotaMeterAdapter — QuotaMeterPort 的檔案契約實作（R82 / ACQ-01）。
#
# 只讀一個 JSON 快取檔，**不做網路、不 import harness code**。那個檔今天已經存在於磁碟上
# （由 monorepo 根層的額度量測器寫），AutoClaude 修前一行都沒讀。
# 檔案契約（照抄，勿重新發明）：
# 🔴 R84／ARCH-07（本檔這一半）：下面這行檔名與 `__init__` 內的 `self._path` 都是**照抄**，
# 唯一真相源住在 monorepo 根層 `tools/lib/quota_meter.py` 的 `CACHE_NAME`。
# 之所以必須兩個家而不是一個：`AutoClaude/.importlinter` 明文禁止引擎 import 根層護欄層，
# 唯一合規的接法就是這條**檔案契約**，兩側只好各自持有字面。
# ⇒ 字面兩個家、算法一個判準；對齊由具名機械物守，不靠人記得：
#   `tools/tests/test_quota_policy.py::TestM8bCacheHomeStaysInSync`（比目錄運算式：
#     只有一側搬家即紅，兩側同一次 commit 一起搬才綠——它讀的是這兩支檔的原始碼）
#   `tools/tests/test_quota_policy.py::TestM8SchemaStaysInSync`（下面 SCHEMA 那一半）
# 只改一側的人會讓本 adapter 讀不到檔，而它對「檔不在」的反應是回 None（＝量不到），
# 且那個 None 被它自己的測試釘成正確行為 ⇒ 失效全綠、完全靜默。
# 現查另一個家：`grep -n "CACHE_NAME" tools/lib/quota_meter.py`
#   路徑    Path(tempfile.gettempdir()) / "autosdd_quota.json"
#   schema  必須等於 "autosdd.quota/2"
#   axes[]  每一格＝一條計費線：{kind, pct(0..100 float，**不是** 0..1), resets_at, group…}
#   resets_at  ISO 8601 自帶 offset；缺席（該線沒有 reset 可以等）時為 null
# 任何一項不符、檔不在、或內容過期 ⇒ 回 None（＝量不到），**絕不回 0.0**。
#
# 🔴 R82：`/1` 的頂層 `pct/kind/resets_at` 是量測器用 `worst()`（pct 數值最大、與期程
# 無關）挑出來再投影的，其餘每一條線的 reset 期程就在那兩行被丟掉。對本 adapter 的實際
# 代價：`resume_wait_seconds` 只對 `_WAITABLE_KINDS` 回秒數，而投影上來的 kind 常是
# `weekly_all` ⇒ 額度軸**實質恆回 None**、AutoResumeService 永遠回落寫死延遲。
# 升版**不寫相容層**：快取是 %TEMP% 內 TTL 綁定的衍生物，替它寫遷移是純負債；
# 讀到舊 schema 一律 None（＝量不到），而那正是既有測試釘住的正確行為。
from __future__ import annotations

import json
import logging
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from ...core.ports.quota_meter import (
    BAND_UNMEASURED,
    DEGRADED_CAP,
    FALLBACK_KINDS,
    NO_RESET,
    PACE_SCHEMA,
    PaceDecision,
    QuotaReading,
    reset_instant,
)

_LOG = logging.getLogger(__name__)

SCHEMA = "autosdd.quota/2"
# R86 配速契約的檔名。與 `autosdd_quota.json` **同目錄、不同檔**，刻意不擠進同一份：
# 那份是「原始量測」（schema /2，有既有消費者與既有的兩處字面同步鎖），這份是「已算好的
# 決策」。升 /3 塞進去要改根層量測器的 schema 字面 ⇒ 會與別包的工作面相撞，而兩份檔的
# TTL 判準本來就不同（見下）⇒ 分開才是對的，不是為了省事。
PACE_CACHE_NAME = "autosdd_pace.json"
# 🔴 TTL 的判準不是「挑一個看起來合理的分鐘數」，是一條**結構性不變式**：
#   衍生物的壽命不得超過它的輸入 ⇒ PACE_TTL_SECONDS 必須嚴格小於 DEFAULT_TTL_SECONDS
#   （原始量測的 TTL）。反過來時，配速決策會在它所依據的快取都已作廢之後還被當成有效。
# 這條關係由 `tests/test_r86_pace_contract.py::TestPaceTtlIsBoundedByItsInput` 守；
# 數字只准往下調（往上調＝放寬，而放寬必須有證據）。
# 900 這個值的來歷：harness 有 session 在跑時每 180 秒刷一次快取（`QUOTA_CACHE_TTL_
# SECONDS`）⇒ 容忍連續漏 4 次刷新才降級。訂得比這更短會讓引擎在正常運作下大半時間都在
# 降級帶，而「一直在擋」的守衛會被整個關掉——本 repo 判過那比沒有守衛更糟。
PACE_TTL_SECONDS = 900.0
# 未來時刻的容許量。時鐘偏移**絕不允許把預算調高**（同根層 `axes_of` 對負 minutes 的
# 處置）：不夾的話，一台快 6 小時的機器寫出來的契約會永遠「剛量到」。
PACE_FUTURE_SKEW_SECONDS = 60.0
# TTL 用檔案 mtime 而非 payload 的 measured_at：量測器每次都整檔重寫，兩者等價，
# 而 mtime 不需要解析時間字串（少一條會出錯的路）。30 分鐘＝比額度視窗短得多。
DEFAULT_TTL_SECONDS = 1800.0


class FileQuotaMeterAdapter:
    def __init__(self, path: str | None = None, ttl_seconds: float = DEFAULT_TTL_SECONDS,
                 pace_ttl_seconds: float = PACE_TTL_SECONDS,
                 degraded_cap: int = DEGRADED_CAP):
        # 🔴 R84／ARCH-07：本行是 ARCH-07 的第二處硬編字面（另一處在檔頭那張路徑表）。
        # 搬家或改名必須與根層 `tools/lib/quota_meter.py::CACHE_NAME` **同一次 commit** 一起動，
        # 否則 `tools/tests/test_quota_policy.py::TestM8bCacheHomeStaysInSync` 會紅——
        # 那道鎖比的是本行的**目錄運算式**，不是檔名字串，所以改本行的寫法前先讀它。
        self._path = Path(path) if path else Path(tempfile.gettempdir()) / "autosdd_quota.json"
        self._ttl = float(ttl_seconds)
        # 配速契約住同一個目錄 ⇒ 測試把 `path` 指到 tmp_path 時兩份契約會一起搬過去，
        # 不必再開第二個參數（少一個可以只設一半的旋鈕）。
        self._pace_path = self._path.with_name(PACE_CACHE_NAME)
        self._pace_ttl = float(pace_ttl_seconds)
        self._pace_floor = max(1, int(degraded_cap))

    # 🔴 R82（C3）：**選軸依問題而定**，所以挑選準則是參數，不是寫死在唯一的 read() 裡。
    # 修前只有一個 read()（選 horizon 最短那一軸），而它有**兩個問相反問題的消費者**：
    # `resume_wait_seconds` 問「要等多久」、`TokenGuardPlugin.evaluate_quota` 問「還剩多少」。
    # 後者拿前者挑出來的軸的 `.pct` 當純量去比 80／95 ⇒ 同一份快取，兩端答案相反。實測：
    #   weekly_all 96%@3h + session 10%@20m ⇒ 根層 halt（cap=0），引擎側讀到 10% ⇒ 無動作。
    # 檔頭那句「本 adapter 的**唯一**消費者」在寫下它的同一個 commit 就為假——註解說只有
    # 一個，不會讓第二個消費者消失。
    # `type(...) in (int, float)` 而不是 isinstance：bool 是 int 的子類別，
    # `True` 會被 isinstance 收成 pct=1.0 這種假讀數。
    # 🔴 R89：`keep` 是**選軸準則的第二個維度**（哪些軸有資格當這個問題的答案），刻意與
    # `key`（同一批候選裡誰排第一）分開——兩者回答的不是同一件事，混在 `key` 裡要靠一個
    # 魔術大數字把不合格的軸壓到最後，那種寫法沒有人看得出它在排除誰。
    # 🔴 `[…if keep(a)] or axes` 是 fail-safe，與根層 `decide()` 的 `gate = […] or readings`
    # 逐字同構：萬一某天**全部**的軸都被排除，寧可退回舊行為（全部參與、可能過度保守），
    # 也不要讓這一軸靜默消失（`DEF-200-107` 的形狀：一個軸可以無聲停止 gating）。
    def _pick(self, key, keep=lambda a: True) -> QuotaReading | None:
        try:
            age = time.time() - self._path.stat().st_mtime
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if age > self._ttl or not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            return None
        axes = [a for a in raw.get("axes") or []
                if isinstance(a, dict) and type(a.get("pct")) in (int, float)]
        pick = min([a for a in axes if keep(a)] or axes, key=key, default={})
        return QuotaReading(float(pick["pct"]), str(pick.get("kind") or ""),
                            pick.get("resets_at") or None) if pick else None

    # 最先 reset 的那條線＝唯一「等得到」的那條（`resume_wait_seconds` 問的問題）。
    def read(self) -> QuotaReading | None:
        return self._pick(lambda a: reset_instant(a.get("resets_at")) or NO_RESET)

    # 水位最高的那條線＝最緊的那條（「還剩多少可燒」）。名字刻意不叫 `worst()`：那個符號是
    # R82 的墓碑（它把整條軸投影成一個純量、丟掉每一桶的 reset 期程）；這裡回的是完整一條軸。
    # 🔴 R89：候選集**排除保險軸**（`FALLBACK_KINDS`，憲法依據見 port 那一段）。
    # 「還剩多少可燒」在 `OVERAGE_POLICY=FREEZE` 之下問的只能是**訂閱窗**——付費池結構上
    # 不可燒 ⇒ 它從來就不是這個問題的答案，而不是「答案被過濾掉了」。
    # 🔴 這**不是** `DEF-200-107` 禁止的那件事（取數層把軸整個丟掉、判讀層拿不到輸入）：
    #   上面的 `axes` 仍然逐條解析出每一軸、`read()`（「要等多久」那個面）仍然看得見它們、
    #   磁碟上的快取一格未動。被改的是**這個具名面的選軸準則**，而「選軸依問題而定，所以
    #   port 開兩個具名的面」正是 R82 開這支函式的理由。判讀歸判讀、取數歸取數。
    # 🔴 實帳（不是假想）：`tests/conftest.py` 的 `DEF-200-110` 記載本機活體快取內容逐字
    #   為 `extra_usage 100.0 / spend 100.0` 時，本函式取到那一軸 ⇒ TokenGuard **每一步都
    #   HALT**，而訂閱窗當時還有餘裕。R88 當時把它整個歸因成「測試不密封」（處置＝隔離快取）
    #   並在該段逐字寫「production 端『額度 100% ⇒ halt』是設計行為」——本輪的憲法裁決推翻
    #   了後半句：保險池撞頂不是訂閱窗撞頂，那一半的病到本輪才治。
    def read_worst_pct(self) -> QuotaReading | None:
        return self._pick(lambda a: -float(a["pct"]),
                          lambda a: a.get("kind") not in FALLBACK_KINDS)

    # R86：配速契約的讀取端。**永不回 None**——「缺檔／過期／壞掉」一律回一則 band=
    # unmeasured 的決策，cap 已經填成保守地板。這是與 `read()`／`read_worst_pct()` 刻意
    # 相反的處置，理由是兩者被問的問題不同：
    #   · 那兩支回 None＝「量不到」，而下游（halt 判定）對量不到的正確反應是**不開火**
    #     （不對一個沒量到的值 halt，同根層 `decide()` 的「量不到時永不 halt」）。
    #   · 本支的下游是**併發度**，而它對量不到的正確反應是**收緊**（本 repo 明文判過：
    #     量不到時的上限絕不是不設限）。回 None 會讓 `effective_fanout` 走「功能沒開」
    #     那一支＝fail-open，而 fail-open 的表徵與修好完全相同。
    # 例外類型刻意收得寬（KeyError／TypeError／AttributeError 都在內）：本區塊只做解析，
    # 任何形狀不符一律 fail-closed 到降級，而不是讓一個壞契約把引擎打掛。
    def read_pace(self) -> PaceDecision:
        try:
            raw = json.loads(self._pace_path.read_text(encoding="utf-8"))
            cap, band = raw["cap"], str(raw["band"])
            age = (datetime.now(UTC) - reset_instant(raw["measured_at"])).total_seconds()
            ok = raw["schema"] == PACE_SCHEMA and type(cap) is int and cap >= 0
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            ok, cap, band, age = False, -1, f"{type(exc).__name__}: {exc}"[:90], float("inf")
        if not ok or not -PACE_FUTURE_SKEW_SECONDS <= age <= self._pace_ttl:
            # 🔴 「失效必須可偵測」：契約沒被更新時這裡會出聲，而不是靜默沿用舊值／不設限。
            _LOG.warning("[pace] 契約量不到（path=%s age=%.0fs why=%s）⇒ 走保守側 cap=%d"
                         "（**不是**不設限）。刷新者住 harness；引擎獨立跑時不會有人刷。",
                         self._pace_path, age, band, self._pace_floor)
            return PaceDecision(self._pace_floor, BAND_UNMEASURED, "degraded")
        return PaceDecision(cap, band, str(raw.get("source") or "unknown"))
