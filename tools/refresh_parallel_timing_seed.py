#!/usr/bin/env python3
"""tools/refresh_parallel_timing_seed.py — DEF-200-274 第九輪 D2：把本機活體快取
（tools/.parallel_timings.json，gitignored）灌注成 git 追蹤的種子檔
（tools/lib/parallel_timing_seed.json），供 CI 這種「每次全新 runner、無活體
快取」的環境當 LPT 排序的起始猜測。

使用：
  python tools/refresh_parallel_timing_seed.py           # 覆蓋種子檔並印過期性報告
  python tools/refresh_parallel_timing_seed.py --check   # 只印過期性報告，不寫檔

前置條件：先跑過一次真樹全套 `python tools/run_root_unittests.py`（未設
`AUTOSDD_PARALLEL_TESTS`＝auto，真實樹＋多核機器上自動平行）產生活體快取，
否則本工具 fail-loud 拒絕覆蓋種子（見 `_MIN_UNITS_TO_REFRESH`）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _cli_flags  # noqa: E402  # 未知旗標 rc=2 fail-loud 的 SSOT（見該檔檔頭 WHY）
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌/ℹ️) 防崩潰保護

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import parallel_timing_cache  # noqa: E402

#: 與 `parallel_shard._CACHE_PERSIST_MIN_UNITS` 理由相同：活體快取涵蓋的派工單位
#: 太少（例如只跑過幾支合成測試）時，灌進種子檔只會把 CI 的 LPT 起始猜測污染成
#: 幾乎沒有代表性的資料，不如拒絕覆蓋、保留舊種子。
_MIN_UNITS_TO_REFRESH = 20
_KNOWN_ARGV: tuple[str, ...] = ("--check",)


def main(check_only: bool) -> int:
    live = parallel_timing_cache.read_json(parallel_timing_cache.LIVE_CACHE_PATH)
    if len(live) < _MIN_UNITS_TO_REFRESH:
        print(
            f"❌ 活體快取（{parallel_timing_cache.LIVE_CACHE_PATH}）只有 {len(live)} 個"
            f"派工單位（低於 {_MIN_UNITS_TO_REFRESH}）——請先跑一次真樹全套 "
            "`python tools/run_root_unittests.py` 再重試。",
            file=sys.stderr,
        )
        return 1
    seed = parallel_timing_cache.read_json(parallel_timing_cache.SEED_PATH)
    msg = parallel_timing_cache.staleness_report(seed, live)
    print(msg or "ℹ️ 種子檔與活體快取的 Top-N 熱點重疊率在門檻之上，沒有明顯過期。")
    if check_only:
        return 0
    parallel_timing_cache.SEED_PATH.write_text(
        json.dumps(live, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"✅ 已覆寫種子檔：{parallel_timing_cache.SEED_PATH}（{len(live)} 個派工單位）"
          "——請 git add 並提交這個檔案。")
    return 0


def cli(argv: list[str]) -> int:
    rc = _cli_flags.reject_unknown_argv("refresh_parallel_timing_seed.py", argv, _KNOWN_ARGV)
    return main(check_only="--check" in argv) if rc is None else rc


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
