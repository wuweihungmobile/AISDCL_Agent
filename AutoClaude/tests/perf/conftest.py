"""tests/perf/conftest.py — SD_09 W0 Pre-W0 audit B-08 修復（2026-05-20）。

目的：補上 perf-baseline-nightly job 缺失的 `write_perf_results()` caller。

機制：
  1. 各 perf 測試在跑完 `measure(...)` 後，呼叫本模組的 `_PERF_RESULTS.append(baseline)`
     收集 PerfBaseline 物件。
  2. pytest_sessionfinish hook 於整個 session 結束時觸發，
     呼叫 `autoclaude.utils.perf_baseline.write_perf_results()` 序列化為 JSON。
  3. 輸出檔 `perf_results.json` 落在 cwd（與 ci.yml `perf-baseline-nightly` 後續 step
     `[ -f perf_results.json ]` 對齊；改 true 後 perf_regression_check.py 真實執行）。

僅在 `-m perf` 跑且實際收集到 baseline 時寫出，避免污染其他測試輸出。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # pragma: no cover
    from autoclaude.utils.perf_baseline import PerfBaseline


# Module-level registry：perf 測試各自 append；pytest_sessionfinish 統一寫出。
_PERF_RESULTS: "List[PerfBaseline]" = []


def pytest_sessionfinish(session, exitstatus):
    """SD_09 B-08：session 結束時將收集到的 PerfBaseline 寫成 perf_results.json。

    對應 .github/workflows/ci.yml `perf-baseline-nightly` job — 後續 step
    `perf_regression_check.py` 將比對 `perf_results.json` vs `.perf_baseline.toml`。
    """
    if not _PERF_RESULTS:
        return  # 無 perf 測試實際執行（例如未帶 -m perf 跑或 fixture 全 skip）

    # 延遲 import：避免 conftest 載入時拖 autoclaude 套件
    from autoclaude.utils.perf_baseline import write_perf_results

    out_path = Path("perf_results.json")
    try:
        write_perf_results(out_path, list(_PERF_RESULTS))
    except Exception as exc:  # noqa: BLE001 — perf JSON 寫出失敗不應影響 pytest 退出碼
        print(f"[perf conftest] write_perf_results failed: {exc}")
