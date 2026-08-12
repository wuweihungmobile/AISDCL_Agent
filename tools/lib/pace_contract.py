"""配速**檔案契約**的寫入端：根層算完的 `Decision` → `<tempdir>/autosdd_pace.json`。"""
# ─────────────────────────────────────────────────────────────────────────────
# WHY 這一支檔存在（R86／SA×Dev 跨包；讀取端與 schema 的權威在引擎側）
# ---------------------------------------------------------------------------
# 引擎（`autoclaude/`）**不准** import 根層護欄層的任何模組——`.importlinter` 的
# `no-harness-import` 契約（R82 落地，實測 KEPT）⇒ 「根層算 cap、引擎用 cap」這件事
# 唯一的傳遞方式是**檔案契約**。讀取端（`autoclaude/infra/adapters/file_quota_meter.py`
# 的 `read_pace()`）與欄位語意（`autoclaude/core/ports/quota_meter.py` 的 `PACE_SCHEMA`
# 那段 docstring）由 Dev 包持有並已上鎖；本檔只做**寫入端**。
#
# 🔴 為何不寫進既有的 `autosdd_quota.json`（`/2`）——Dev 包辯護過，此處轉載理由的核心：
#   兩份檔的**新鮮度判準本來就不同**。`/2` 由量測者整檔重寫 ⇒ `mtime ≡ 量測時刻`；
#   而配速契約可能「拿 30 分鐘前的舊快取、現在算、立刻寫檔」⇒ **mtime 全新、量測很舊**，
#   那個組合的外觀與「剛量到」完全相同。所以契約的 `measured_at` 一律搬
#   `QuotaState.measured_at`（＝額度真正被量到的時刻），**不得**寫 `now`，讀取端也
#   不得讀 mtime。這是本檔最容易寫錯、且寫錯完全靜默的一格。
#
# 🔴 為何新開一支檔而不是塞進 `quota_gate.py`：那支的 LOC tier 餘裕實測只剩個位數
#   （496/500），而本檔要 ~30 行。同時這也是正確的分工：**一份檔案契約的檔名、schema
#   與原子寫法是一個家**（先例＝`quota_meter.py` 持有 `/2` 的 `CACHE_NAME`／`SCHEMA`）。
#
# 🔴 兩個字面（檔名／schema）在 repo 內必然有兩個家（一個在引擎、一個在這裡，而兩邊
#   結構上不准互相 import）⇒ 那個縫必須由**判準**縫起來，不是靠人記得：
#   `tools/tests/test_quota_policy.py` 的
#   `TestR86ThePaceContractWriterMatchesTheEngineReader` 逐字比對兩邊的常數。
#   沒有它，改掉任一邊 ⇒ 寫入者寫一份沒有人讀的檔，而**失敗表徵與成功完全相同**
#   （引擎照跑、只是永遠走保守地板；`quota_cache_path()` 的 docstring 已記載過同型判例）。
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

#: 檔名。**必須**等於 `autoclaude/infra/adapters/file_quota_meter.py:PACE_CACHE_NAME`。
CONTRACT_NAME = "autosdd_pace.json"

#: schema。**必須**等於 `autoclaude/core/ports/quota_meter.py:PACE_SCHEMA`。
CONTRACT_SCHEMA = "autosdd.pace/1"

#: 寫檔失敗時的一次性提示（fail-soft：`--pace` 的 rc 與那一行輸出都不得因此改變）。
WRITE_FAILED_HINT = ("⚠️  配速契約寫不進去（{path}：{why}）⇒ 引擎側會走保守地板 cap"
                     "（**不是**不設限）。`--pace` 本身不受影響。\n")


def contract_path() -> Path:
    """契約檔路徑。與 `autosdd_quota.json` **同目錄**（引擎側以 `with_name` 定位）。"""
    return Path(tempfile.gettempdir()) / CONTRACT_NAME


# 🔴 `cap` 的型別在契約裡是 `int` 且 `>= 0`（讀取端 `type(cap) is int and cap >= 0`），
# 而根層的 `Decision.cap` 可以是 `None`＝**不設限**。映射刻意分兩支：
#   · halt 帶 ⇒ 0（停止派發；`decide()` 本來就給 0）
#   · 其餘的 `None` ⇒ `max_fanout`（＝那個「不設限」在本 repo 的實際上界）
# 寫 `None` 會讓讀取端整份契約判為壞掉 ⇒ 引擎退回保守地板，而那與「根層說不設限」
# 恰好相反：一個最寬鬆的判讀被寫成了最緊的行為，且沒有人會知道。
def payload(decision, state, max_fanout: int, halt_pct: float) -> dict:
    """`Decision` → 契約 dict（純函式；欄位語意的權威＝引擎側 port 的 docstring）。

    `headroom_pct`＝halt 水位 − 最緊那軸的水位（**非負**）；
    `headroom_pct_per_hour`＝它除以「距 reset 幾小時」。
    🔴 這兩格的語意是 Dev 包在 port docstring 上鎖住的那一個，**不是**本輪
    `quota_pace.amortize()` 算的跨窗餘裕（後者帶正負號、單位是長窗攤提後的短窗 pp）。
    兩者不可互換：把帶負號的量寫進一個宣告為非負的欄位是靜默的語意漂移。統一成同一個
    量是下一輪的事（要動的是 port 那份 docstring，而它不在本包的持有面內）。
    """
    cap = decision.cap
    binding = decision.binding.kind if decision.binding is not None else None
    minutes = next((r.minutes for r in decision.per_axis
                    if binding is not None and r.axis.kind == binding), None)
    headroom = (None if not decision.per_axis else
                max(0.0, float(halt_pct) - max(r.axis.pct for r in decision.per_axis)))
    return {
        "schema": CONTRACT_SCHEMA,
        "cap": 0 if cap is None and decision.band == "halt" else (
            int(max_fanout) if cap is None else int(cap)),
        "band": decision.band,
        # 🔴 額度**被量到**的時刻，不是現在（見檔頭：mtime 全新／量測很舊是真實情境）。
        "measured_at": str(state.measured_at),
        "source": str(state.source),
        "headroom_pct": headroom,
        "headroom_pct_per_hour": (None if headroom is None or not minutes else
                                  round(headroom / max(float(minutes) / 60.0, 1e-9), 3)),
        "binding_kind": binding,
        "recommended_fanout": int(decision.recommended_fanout),
    }


# 🔴 原子寫（暫存檔 → `os.replace`），三個細節都是本 repo 既有判例：
#   · `newline="\n"`——不指定時 Windows 會寫出 CRLF（同 `quota_meter.write_cache`）。
#   · 暫存檔名帶 pid——本輪的工作樹是多包並行的，共用一個 `.tmp` 會互相覆寫。
#   · `os.replace` 包在 `except OSError` 裡——根 `CLAUDE.md` 登記過它在 Windows 覆寫
#     **被開著的**目的檔會 WinError 5（`TestDirEntryPrimitivesAreAccountedFor` 守這一族，
#     未處置的站點會讓那本欠債帳轉紅）。而這裡「被開著」不是假想：引擎隨時可能在讀它。
# fail-soft 是硬要求：`--pace` 的既有契約是零 token、且掌舵者每隔幾十分鐘就查一次
# ⇒ 寫檔失敗不得讓它的 rc 變非零、也不得讓它印不出原本那一行。失敗只在 stderr 說一次。
def write(decision, state, max_fanout: int, halt_pct: float,
          path: Path | None = None) -> bool:
    """寫契約。回「有沒有真的寫成」——失敗**不拋例外**，只出聲一次。"""
    target = path or contract_path()
    staging = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(payload(decision, state, max_fanout, halt_pct),
                                      ensure_ascii=False, indent=2),
                           encoding="utf-8", newline="\n")
        os.replace(staging, target)
    except OSError as why:
        sys.stderr.write(WRITE_FAILED_HINT.format(path=target, why=why))
        return False
    return True
