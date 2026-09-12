"""tools/lib/parallel_timing_cache.py — DEF-200-274 第九輪 D2：平行派工歷史耗時
快取。兩層讀取：git 追蹤的種子檔（CI 每次全新 runner 用的起始猜測）＋本機
gitignored 活體快取（每次真實跑完寫回，供下次 LPT 排序）。壞掉的 JSON／缺檔
一律吞掉回空 dict——本模組是效能觀測的輔助，不得讓測試套件本身因快取壞掉而炸。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

LIVE_CACHE_PATH = Path(__file__).resolve().parents[1] / ".parallel_timings.json"
SEED_PATH = Path(__file__).resolve().parent / "parallel_timing_seed.json"

#: Top-N 熱點重疊率門檻（見 `staleness_report`）。
_STALENESS_OVERLAP_FLOOR = 0.5
_STALENESS_TOP_N = 15


def read_json(path: Path) -> dict[str, float]:
    """壞掉的 JSON／缺檔／非 dict 一律回空 dict；非 (int,float) 的值逐一濾掉。
    唯一的讀取實作，`load_hints()`／`refresh_parallel_timing_seed.py` 共用。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    # bool 是 int 子類別，`isinstance(True, (int, float))` 為 True——若不排除，
    # 快取檔含 `{"mod": true}` 會被 `float(v)` 轉成 1.0 秒而非被判為非法值剔除。
    return {k: float(v) for k, v in data.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def load_hints(keys) -> dict[str, float]:
    """回傳 `{派工鍵: 秒數}`——種子先讀，活體快取後讀覆蓋（活體較新，本機最準）；
    只回傳出現在 `keys` 內的鍵（呼叫端只關心當次真的會派工的那些鍵）。
    """
    keys = set(keys)
    hints = read_json(SEED_PATH)
    hints.update(read_json(LIVE_CACHE_PATH))
    return {k: v for k, v in hints.items() if k in keys}


def order_dispatch_units(units: dict[str, int], hints: dict[str, float]) -> list[str]:
    """LPT 排序：已知歷史耗時者依秒數遞減先派；其餘（新模組／快取未覆蓋）依測試數
    遞減排在後面——這是舊版全量行為的**子集**：`hints={}` 時等價於
    `sorted(units, key=lambda m: (-units[m], m))`（原本的排序公式），零回歸風險。
    """
    known = sorted((k for k in units if k in hints), key=lambda k: (-hints[k], k))
    unknown = sorted((k for k in units if k not in hints), key=lambda k: (-units[k], k))
    return known + unknown


def save_live_cache(module_timings: dict[str, float]) -> None:
    """`run_parallel()` 結束後把本次量到的 `{派工鍵: 秒數}` 寫回活體快取。原子寫入
    （`os.replace`，Windows 上一樣是原子操作），寫入失敗只印一行 warning，
    不得讓測試套件本身因為快取寫不進去而失敗。
    """
    try:
        tmp = LIVE_CACHE_PATH.with_name(LIVE_CACHE_PATH.name + ".tmp")
        tmp.write_text(
            json.dumps(module_timings, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, LIVE_CACHE_PATH)
    except OSError as exc:
        print(f"⚠️ 平行派工計時快取寫入失敗（{exc}）——不影響本次結果，下次退回既有排序",
              file=sys.stderr)


def staleness_report(seed: dict[str, float], live: dict[str, float],
                      top_n: int = _STALENESS_TOP_N) -> str | None:
    """種子檔與活體快取的 Top-N（耗時最長）熱點重疊率過低時回傳 advisory 訊息，
    否則 `None`。刻意不用 scipy 的 Spearman：避免為了一則顧問性訊息新增第三方
    相依，重疊率是排名分歧的一個更直覺、免相依的近似。純 advisory，呼叫端只印
    不擋。
    """
    if not seed or not live:
        return None
    seed_top = {k for k, _ in sorted(seed.items(), key=lambda kv: -kv[1])[:top_n]}
    live_top = {k for k, _ in sorted(live.items(), key=lambda kv: -kv[1])[:top_n]}
    universe = seed_top | live_top
    if not universe:
        return None
    overlap = len(seed_top & live_top) / len(universe)
    if overlap >= _STALENESS_OVERLAP_FLOOR:
        return None
    return (
        f"⚠️ 平行派工計時種子檔可能已過期：種子與活體快取的 Top-{top_n} 熱點重疊率僅 "
        f"{overlap:.0%}（門檻 {_STALENESS_OVERLAP_FLOOR:.0%}）——考慮執行 "
        "`python tools/refresh_parallel_timing_seed.py` 重新產生種子檔"
    )
