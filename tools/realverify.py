"""realverify 命令列入口（薄殼：只組 argparse 與分派，判準全在 `lib/realverify/`）。

用法：
  python tools/realverify.py list
  python tools/realverify.py sweep [--dry-run]   清孤兒逐字稿目錄＋依租約帳撤孤兒排程
                                                 （末行 SWEEP_VERDICT）
  python tools/realverify.py run --case RV-L1 | --family hooks | --all [--long]
末行 `REALVERIFY_VERDICT=pass|fail n=… fail=[…]`；rc
0＝全過、1＝有失敗、2＝環境缺件（如找不到 claude，不算綠）、3＝用法錯誤。
CI 沒有 Claude 認證，本載具不進 CI（本機／nightly
跑）。設計＝docs/06_quality/CrossPlatform_R215_PendingVerification_Closure.md §4。
"""

from __future__ import annotations

import argparse
import os
import sys

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作
from lib.realverify import leases, runner, sandbox
from lib.realverify.driver import EnvMissing, find_claude


def _sweep_sched(dry_run: bool) -> int:
    """租約帳重放＋發現式掃描（取代舊 `cleanup_all_rv`）；末行 `SWEEP_VERDICT=`，判決 rc 0。"""
    if os.name != "nt":  # 真 schtasks 載具只在 Windows；其他平台沒有帳可撤
        print("SWEEP_VERDICT=clean")
        return 0
    if dry_run:
        names = leases.orphan_idents() + leases.discover_sweep(dry_run=True)
        for n in names:
            print(f"將撤排程：{n}")
        print(f"SWEEP_VERDICT={'clean' if not names else f'revoked n={len(names)}'} dry_run=1")
        return 0
    stuck = leases.replay()
    gone = leases.discover_sweep()
    for n in gone:
        print(f"已撤排程（未登記殘留）：{n}")
    if stuck:
        print(f"SWEEP_VERDICT=unrevoked n={len(stuck)}")
    else:
        print(f"SWEEP_VERDICT={'clean' if not gone else f'revoked n={len(gone)}'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="realverify", description="真機自驗載具")
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("list", help="列出案例（ready／long／planned）")
    sw = sub.add_parser("sweep", help="清孤兒沙盒逐字稿目錄（沙盒根已不在且沒有行程在用）")
    sw.add_argument("--dry-run", action="store_true", help="只列出會刪什麼，不刪")
    rp = sub.add_parser("run", help="跑案例")
    g = rp.add_mutually_exclusive_group(required=True)
    g.add_argument("--case")
    g.add_argument("--family")
    g.add_argument("--all", action="store_true")
    rp.add_argument("--long", action="store_true", help="含長等案例")
    a = ap.parse_args(argv)
    if a.verb == "list":
        print(runner.list_cases())
        return 0
    if a.verb == "sweep":
        res = sandbox.sweep_orphans(dry_run=a.dry_run)
        for name in res["removed"]:
            print(f"{'將刪' if a.dry_run else '已刪'}孤兒逐字稿目錄：{name}")
        for name, why in res["kept"]:
            print(f"保留：{name}（{why}）")
        print(f"REALVERIFY_SWEEP removed={len(res['removed'])} kept={len(res['kept'])}"
              f"{' dry_run=1' if a.dry_run else ''}")
        return _sweep_sched(a.dry_run)
    try:
        find_claude()
    except EnvMissing as e:
        print(f"[ENV] {e}")
        print("REALVERIFY_VERDICT=fail n=0 fail=['env-missing:claude']")
        return 2
    return runner.main_run(a.case, a.family, a.all, a.long)


if __name__ == "__main__":
    sys.exit(main())
