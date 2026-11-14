"""推送後等 GitHub CI（薄殼：只組 argparse；判準全在 `lib/ciwait/core.py`）。

用法（背景跑、輸出導檔；**不要**手寫 `gh run list` 輪詢迴圈，那個形態會被守衛擋下）：
    python tools/ci_wait.py --commit <rev> > ci_wait.log 2>&1

結束碼：0＝全部通過｜1＝有 workflow 失敗或被取消｜2＝到截止時間仍有未完成｜3＝查不到 run、
查詢持續失敗、gh 缺席或 SHA 解不出。最後一行恆為 `CI_WAIT_VERDICT=<pass|fail|timeout|no-runs>
sha=<完整 SHA> runs=<n>`。`--timeout-min` 是硬上限，須小於背景工具自己的 timeout，讓本工具
自己結束而不是被收掉。
"""
from __future__ import annotations

import argparse
import sys

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作，本檔不另寫
from lib.ciwait import core

_USAGE_RC = core.EXIT_NO_RUNS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="等某個提交的 GitHub workflow 全部跑完。結束碼：0 全過｜1 有失敗或取消｜"
                    "2 到截止時間仍有未完成｜3 查不到 run／查詢持續失敗／SHA 解不出。",
        epilog="--timeout-min 是硬上限，必須小於背景工具的 timeout。")
    ap.add_argument("--commit", default="HEAD", help="提交（預設 HEAD；一律先解成完整 SHA）")
    ap.add_argument("--timeout-min", type=float, default=40.0, help="硬截止時間（分鐘，預設 40）")
    ap.add_argument("--interval-sec", type=float, default=60.0, help="輪詢間隔（秒，預設 60）")
    ap.add_argument("--grace-min", type=float, default=5.0,
                    help="超過這段時間仍查到 0 支 run 就明確失敗（分鐘，預設 5）")
    ap.add_argument("--expect", type=int, default=0, help="至少要有幾支 workflow（選填）")
    ap.add_argument("--workflow", action="append", default=[],
                    help="只等這幾支（可重複；每支都必須出現）")
    ns = ap.parse_args(argv)
    sha, err = core.resolve_sha(ns.commit, core.default_runner)
    if sha is None:
        print(err, file=sys.stderr)
        print("CI_WAIT_VERDICT=no-runs sha=? runs=0")
        return _USAGE_RC
    return core.wait(core.Options(
        sha=sha, timeout_min=ns.timeout_min, interval_sec=ns.interval_sec,
        grace_min=ns.grace_min, expect=ns.expect, workflows=tuple(ns.workflow)),
        emit=lambda s: print(s, flush=True))


if __name__ == "__main__":
    sys.exit(main())
