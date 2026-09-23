"""tools/mutmut_cache_counts.py — DEF-200-365：CI 路徑 mutation kill_rate 恆 0.00% 缺口補丁。

WHY（三句話）：
  1. `mutmut results`（mutmut 2.4.3 `cache.py::print_result_cache`）結構上只印
     Timed out／Suspicious／Survived／Untested-skipped 四段，**永不印 Killed**。
  2. `mutation_baseline_lock.py` 的 marker-based parser 缺 marker 時 fallback 只讀
     到 `Survived (N)`，killed 恆讀 0 ⇒ kill_rate 恆 0.00%（雲端 run 35678026352
     逐字 `Survived 🙁 (59)` / `kill_rate=0.00%` 為證）。
  3. 四處 CI job（token_guard／goal_synthesis／coordinator／on-change）皆只跑
     `mutmut results | tee <log>`，缺一步從 `.mutmut-cache`（sqlite）補上 marker 段。

本檔是 `tools/run_mutmut_in_docker.sh` L131-161 內嵌 python（sqlite `Mutant.status`
查詢 + `--- mutmut full counts ... ---` marker 輸出）的可測 Python SSOT 抽出版
（紀律 #4「驗證鏡子自身要被驗證」；比照同目錄 `mutmut_counts_parser.py` /
`mutmut_exit_code.py` 既有「從 .sh 抽出可測 Python SSOT」慣例）。**誠實劃界**：本輪
刻意不改 `.sh`（該實作已在隔離樹內運作良好，兩份實作並存）；若 `.sh` 內嵌 python 的
`label_map` 漂移，由 `tests/tools/test_mutmut_cache_counts.py` 內「與 .sh label_map
五個 status 字面一致」的鎖看守。

CLI：
    python tools/mutmut_cache_counts.py [--cache-path PATH]

輸出（stdout；`mutation_baseline_lock._COUNTS_BEGIN_MARKER` / `_COUNTS_END_MARKER`
必認）：
    <blank>
    --- mutmut full counts (from cache; mutmut_cache_counts.py) ---
    Killed (N)
    Survived (N)
    Timeout (N)
    Suspicious (N)
    Skipped (N)
    --- mutmut full counts (end) ---

退出碼（fail-loud，主控裁決）：
    0  成功（含全 killed／`Survived (0)` 之情形——marker 段 sum>0 不會誤判 empty）
    2  cache 檔不存在／不是檔案／sqlite 查詢失敗（stderr 說明；stdout 不印 marker，
       GitHub Actions `run:` 步驟預設 `bash -e` 會讓該 step 紅——這正是本輪要的
       「不要靜默 0%」，取代原本被 `tee` 吞掉錯誤的沉默失敗）
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# mutmut 2.4.x cache（sqlite 單檔）Mutant.status → 標準 label
# （與 tools/run_mutmut_in_docker.sh L151-157 的 label_map 一致；本檔測試鎖二者同步）。
_STATUS_LABEL_MAP: tuple[tuple[str, str], ...] = (
    ("ok_killed", "killed"),
    ("bad_survived", "survived"),
    ("bad_timeout", "timeout"),
    ("ok_suspicious", "suspicious"),
    ("skipped", "skipped"),
)

_DEFAULT_CACHE_PATH = Path(".mutmut-cache")


def read_status_counts(cache_path: Path) -> dict[str, int]:
    """從 mutmut `.mutmut-cache`（sqlite 單檔）讀出五類 status 計數。

    Args:
        cache_path: mutmut cache sqlite 檔路徑。

    Returns:
        {"killed": N, "survived": N, "timeout": N, "suspicious": N, "skipped": N}

    Raises:
        FileNotFoundError: cache_path 不存在，或存在但不是檔案（例如誤指到目錄）。
        sqlite3.Error: sqlite 查詢失敗（非法 sqlite 檔／缺 Mutant 表等）。
    """
    if not cache_path.exists() or not cache_path.is_file():
        raise FileNotFoundError(f"mutmut cache not found or not a file: {cache_path}")
    conn = sqlite3.connect(str(cache_path))
    try:
        cur = conn.execute("SELECT status, COUNT(*) FROM Mutant GROUP BY status")
        raw_counts = dict(cur.fetchall())
    finally:
        conn.close()
    return {label: raw_counts.get(status_key, 0) for status_key, label in _STATUS_LABEL_MAP}


def format_marker_section(counts: dict[str, int]) -> str:
    """組出 marker 段逐字文字（含前導空行；`mutation_baseline_lock` 必認的單一真相）。"""
    lines = [
        "",
        "--- mutmut full counts (from cache; mutmut_cache_counts.py) ---",
        f"Killed ({counts.get('killed', 0)})",
        f"Survived ({counts.get('survived', 0)})",
        f"Timeout ({counts.get('timeout', 0)})",
        f"Suspicious ({counts.get('suspicious', 0)})",
        f"Skipped ({counts.get('skipped', 0)})",
        "--- mutmut full counts (end) ---",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read mutmut .mutmut-cache and emit the counts marker section "
            "`mutmut results` omits (DEF-200-365)."
        ),
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        default=_DEFAULT_CACHE_PATH,
        help="mutmut cache sqlite 檔路徑（預設 .mutmut-cache，相對 cwd）",
    )
    args = parser.parse_args(argv)

    try:
        counts = read_status_counts(args.cache_path)
    except FileNotFoundError as e:
        print(f"[mutmut_cache_counts] ERROR: {e}", file=sys.stderr)
        return 2
    except sqlite3.Error as e:
        print(
            f"[mutmut_cache_counts] ERROR: sqlite query failed for {args.cache_path}: {e}",
            file=sys.stderr,
        )
        return 2

    sys.stdout.write(format_marker_section(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
