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
import tempfile
import time
from pathlib import Path

from ...core.ports.quota_meter import NO_RESET, QuotaReading, reset_instant

SCHEMA = "autosdd.quota/2"
# TTL 用檔案 mtime 而非 payload 的 measured_at：量測器每次都整檔重寫，兩者等價，
# 而 mtime 不需要解析時間字串（少一條會出錯的路）。30 分鐘＝比額度視窗短得多。
DEFAULT_TTL_SECONDS = 1800.0


class FileQuotaMeterAdapter:
    def __init__(self, path: str | None = None, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        # 🔴 R84／ARCH-07：本行是 ARCH-07 的第二處硬編字面（另一處在檔頭那張路徑表）。
        # 搬家或改名必須與根層 `tools/lib/quota_meter.py::CACHE_NAME` **同一次 commit** 一起動，
        # 否則 `tools/tests/test_quota_policy.py::TestM8bCacheHomeStaysInSync` 會紅——
        # 那道鎖比的是本行的**目錄運算式**，不是檔名字串，所以改本行的寫法前先讀它。
        self._path = Path(path) if path else Path(tempfile.gettempdir()) / "autosdd_quota.json"
        self._ttl = float(ttl_seconds)

    # 🔴 R82（C3）：**選軸依問題而定**，所以挑選準則是參數，不是寫死在唯一的 read() 裡。
    # 修前只有一個 read()（選 horizon 最短那一軸），而它有**兩個問相反問題的消費者**：
    # `resume_wait_seconds` 問「要等多久」、`TokenGuardPlugin.evaluate_quota` 問「還剩多少」。
    # 後者拿前者挑出來的軸的 `.pct` 當純量去比 80／95 ⇒ 同一份快取，兩端答案相反。實測：
    #   weekly_all 96%@3h + session 10%@20m ⇒ 根層 halt（cap=0），引擎側讀到 10% ⇒ 無動作。
    # 檔頭那句「本 adapter 的**唯一**消費者」在寫下它的同一個 commit 就為假——註解說只有
    # 一個，不會讓第二個消費者消失。
    # `type(...) in (int, float)` 而不是 isinstance：bool 是 int 的子類別，
    # `True` 會被 isinstance 收成 pct=1.0 這種假讀數。
    def _pick(self, key) -> QuotaReading | None:
        try:
            age = time.time() - self._path.stat().st_mtime
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if age > self._ttl or not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            return None
        pick = min((a for a in raw.get("axes") or []
                    if isinstance(a, dict) and type(a.get("pct")) in (int, float)),
                   key=key, default={})
        return QuotaReading(float(pick["pct"]), str(pick.get("kind") or ""),
                            pick.get("resets_at") or None) if pick else None

    # 最先 reset 的那條線＝唯一「等得到」的那條（`resume_wait_seconds` 問的問題）。
    def read(self) -> QuotaReading | None:
        return self._pick(lambda a: reset_instant(a.get("resets_at")) or NO_RESET)

    # 水位最高的那條線＝最緊的那條（「還剩多少可燒」）。名字刻意不叫 `worst()`：那個符號是
    # R82 的墓碑（它把整條軸投影成一個純量、丟掉每一桶的 reset 期程）；這裡回的是完整一條軸。
    def read_worst_pct(self) -> QuotaReading | None:
        return self._pick(lambda a: -float(a["pct"]))
