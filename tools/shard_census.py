#!/usr/bin/env python3
"""tools/shard_census.py — 分片全套的「全集級 skip 判準」彙總（DEF-200-593；薄殼）。

用法：python tools/shard_census.py <分片紀錄目錄>
  目錄內須有每一片 `tools/run_root_unittests.py` 在 `AUTOSDD_TEST_SHARD=i/N` 加
  `AUTOSDD_TEST_SHARD_OUT=<目錄>` 下留下的 `shard-<i>-of-<N>.json`。

為何存在：skip 天花板／M6 id 集合／豁免表 stale 是**全集級**判準——單片只看得到自己那一份
skip，天花板永遠不會紅（失去「skip 變多」偵測）、M6 集合永遠漂移（誤紅）。分片 runner 因此
在這三項上延後（`tools/lib/suite_shard.py::judge`），本工具把各片紀錄合併成一個 result 後，
呼叫與未分片時**同一組函式**判（`run_root_unittests.report_skip_census`／
`report_windows_skip_tag_exemption_problems`），並先驗分片機制本身：缺片、切分摘要不符、
各片測試集合有交集或聯集≠全集一律 rc=1。判準與 WHY 全文＝`tools/lib/suite_shard.py`。
rc：0 通過；1 判準不合格；2 用法錯誤。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import suite_shard  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
import run_root_unittests as runner  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("用法：python tools/shard_census.py <分片紀錄目錄>", file=sys.stderr)
        return 2
    tests = runner._flatten(runner.discover_suite(runner._TESTS_DIR))
    known_ids = {t.id() for t in tests}  # 取在任何 run() 之前（見 windows_skip_tags 同款陷阱）
    merged, problems = suite_shard.merge_records(Path(argv[0]), tests)
    if problems:
        print(f"❌ 分片機制自檢失敗（{len(problems)} 項）：", file=sys.stderr)
        for msg in problems:
            print(f"   - {msg}", file=sys.stderr)
        return 1
    print(f"✅ 分片機制自檢通過：{len(known_ids)} 支測試、各片無交集、聯集＝全集、"
          f"合併後實跑 {merged.testsRun} 支、skip {len(merged.skipped)} 支")
    census_rc = runner.report_skip_census(merged, runner._TESTS_DIR)
    exempt = runner.report_windows_skip_tag_exemption_problems(merged, known_ids=known_ids)
    return 1 if census_rc or exempt else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
