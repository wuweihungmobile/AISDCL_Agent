"""realverify 命令列入口（薄殼：只組 argparse 與分派，判準全在 `lib/realverify/`）。

用法：
  python tools/realverify.py list
  python tools/realverify.py sweep [--dry-run]    重放租約帳＋發現式掃描，撤孤兒（末行 SWEEP_VERDICT，rc 0）
  python tools/realverify.py sweep --legacy [--apply]   DES §9 既有外洩物：只列／加 --apply 才刪
  python tools/realverify.py sweep --abandon <run_id> --why "<至少 8 字>"   人工出口：只把帳記 abandoned
  python tools/realverify.py snapshot --out <檔> | --diff <前> <後> [--tokens <檔>]   唯讀、rc 0
  python tools/realverify.py run --case RV-L1 | --family hooks | --all [--long]
末行 `REALVERIFY_VERDICT=pass|fail [reason=orphans|leak] n=… fail=[…]`；rc
0＝全過、1＝有失敗、2＝環境缺件或孤兒拒跑（如找不到 claude，不算綠）、3＝用法錯誤。
`run --all` 不含 `sideeffect`／`sideeffect_selftest` 家族（只能 `--family`／`--case` 指名）。
CI 沒有 Claude 認證，本載具不進 CI（本機／nightly
跑）。設計＝docs/06_quality/CrossPlatform_R215_PendingVerification_Closure.md §4；副作用隔離＝
docs/02_architecture/RealVerify_SideEffect_Isolation_Design.md。
"""  # noqa: E501

from __future__ import annotations

import argparse
import sys

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作
from lib.realverify import cli, runner
from lib.realverify.driver import EnvMissing, find_claude


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="realverify", description="真機自驗載具")
    sub = ap.add_subparsers(dest="verb", required=True)
    sub.add_parser("list", help="列出案例（ready／long／planned）")
    sw = sub.add_parser("sweep", help="重放租約帳＋發現式掃描，撤孤兒（沙盒根／排程／行程／逐字稿目錄）")  # noqa: E501
    sw.add_argument("--dry-run", action="store_true", help="只列出會處置什麼，不動")
    sw.add_argument("--legacy", action="store_true", help="列出 DES §9 既有外洩物（X1～X5、X7）")
    sw.add_argument("--apply", action="store_true", help="與 --legacy 併用才真的刪")
    sw.add_argument("--abandon", metavar="RUN_ID", help="人工出口：把該帳未完成列記 abandoned（不砍不刪）")  # noqa: E501
    sw.add_argument("--why", help="--abandon 的理由（至少 8 字）")
    sn = sub.add_parser("snapshot", help="真環境副作用快照（唯讀）")
    sn.add_argument("--out", help="寫快照到這個檔")
    sn.add_argument("--diff", nargs=2, metavar=("BEFORE", "AFTER"), help="比對兩份快照")
    sn.add_argument("--tokens", help="--diff 用：每行一個字樣的檔；給了只列含字樣的項")
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
        return cli.sweep(dry_run=a.dry_run, legacy=a.legacy, apply=a.apply, abandon=a.abandon, why=a.why)  # noqa: E501
    if a.verb == "snapshot":
        return cli.snapshot_cmd(out=a.out, diff=a.diff, tokens=a.tokens)
    try:
        find_claude()
    except EnvMissing as e:
        print(f"[ENV] {e}")
        print("REALVERIFY_VERDICT=fail n=0 fail=['env-missing:claude']")
        return 2
    return runner.main_run(a.case, a.family, a.all, a.long)


if __name__ == "__main__":
    sys.exit(main())
