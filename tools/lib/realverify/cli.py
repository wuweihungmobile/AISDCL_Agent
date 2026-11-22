"""`tools/realverify.py` 的動詞本體：`sweep`（含 `--dry-run`／`--legacy [--apply]`／`--abandon`）與 `snapshot`。

入口檔只組 argparse 與分派；判準與動作都在 `leases*`／`snapshot`／`sweep_legacy`。
`sweep` 的判決一律 rc 0（末行 `SWEEP_VERDICT=clean|revoked n=<k>|unrevoked n=<k>`），只有真錯誤才非 0——
harness 把背景指令任何非 0 結束都顯示成「failed」，正常判決不得長得像錯誤。
"""  # noqa: E501

from __future__ import annotations

import sys
from pathlib import Path

from . import leases, leases_discover, snapshot, sweep_legacy

RC_USAGE = 3


def _verdict(revoked: int, unrevoked: int, *, dry: bool = False) -> str:
    tail = " dry_run=1" if dry else ""
    if unrevoked:
        return f"SWEEP_VERDICT=unrevoked n={unrevoked}{tail}"
    return f"SWEEP_VERDICT={'clean' if not revoked else f'revoked n={revoked}'}{tail}"


def sweep(*, dry_run: bool = False, legacy: bool = False, apply: bool = False,
          abandon: str | None = None, why: str | None = None) -> int:
    if apply and not legacy:
        print("❌ --apply 只能與 --legacy 併用", file=sys.stderr)
        return RC_USAGE
    if abandon is not None:
        return _abandon(abandon, why or "")
    if legacy:
        return _legacy(apply=apply)
    if dry_run:
        rows = leases.orphan_rows()
        found = leases_discover.scan()
        for kind, ident in rows:
            print(f"將撤（帳列孤兒 {kind}）：{ident}")
        for f in found:
            print(f"{'將處置' if f.action == 'revoke' else '只記錄（abandoned 之下）'}（發現式 {f.kind}）：{f.ident}（{f.why}）")  # noqa: E501
        n = len(rows) + sum(1 for f in found if f.action == "revoke")
        print(_verdict(n, 0, dry=True))
        return 0
    lines, stuck = leases_discover.preflight()
    for ln in lines:
        print(ln)
    for ident, reason in stuck.items():
        print(f"撤不掉：{ident}（{reason}）")
    print(_verdict(sum(1 for ln in lines if ln.startswith("↩")), len(stuck)))
    return 0


def _abandon(run_id: str, why: str) -> int:
    try:
        gone = leases.abandon(run_id, why)
    except (ValueError, FileNotFoundError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    for ident in gone:
        print(f"已放棄（只動帳，不砍行程、不刪檔）：{ident}")
    print(f"SWEEP_ABANDON run_id={run_id} n={len(gone)}")
    return 0


def _legacy(*, apply: bool) -> int:
    found = sweep_legacy.items()
    for it in found:
        print(f"LEGACY {it.tag} {it.path}")
    print(f"永不處置：{'；'.join(sweep_legacy.NEVER)}")
    if apply:
        bad = sweep_legacy.apply(found)
        for path in bad:
            print(f"刪除失敗：{path}")
        print(f"SWEEP_LEGACY applied n={len(found) - len(bad)} failed={len(bad)}")
        return 0 if not bad else 1
    print(f"SWEEP_LEGACY listed n={len(found)}（未加 --apply，一個檔都沒動）")
    return 0


def snapshot_cmd(*, out: str | None, diff: list[str] | None, tokens: str | None) -> int:
    """`snapshot --out <檔>`：拍真環境快照；`snapshot --diff <前> <後> [--tokens <檔>]`：比對（唯讀、rc 0）。"""  # noqa: E501
    if (out is None) == (diff is None):
        print("❌ snapshot 要且只要 --out <檔> 或 --diff <前> <後> 其一", file=sys.stderr)
        return RC_USAGE
    if out is not None:
        snapshot.dump(snapshot.take(), out)
        print(f"SNAPSHOT written={Path(out)}")
        return 0
    before, after = snapshot.load(diff[0]), snapshot.load(diff[1])
    toks = snapshot.read_tokens(tokens) if tokens else None
    items = snapshot.diff(before, after, toks)
    shown = [i for i in items if i["token"]] if toks else items
    for item in shown:
        print(snapshot.fmt(item))
    print(f"SNAPSHOT_DIFF total={len(items)} shown={len(shown)}{' tokens=1' if toks else ''}")
    return 0
