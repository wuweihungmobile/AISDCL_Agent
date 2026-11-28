"""`handoff --ack` 成功後撤原 session 的 park（Control_Handover DES §20.2、D-CT-12、REQ-CTL-47）。

WHY：`park` 掛的是「到點若原 session 沒人在動就由新 session 接手」。新 session 已 `--ack` 接手後，
到點判準雖會對 `.ack` skip（雙駕駛風險已擋），但在到點之前標記仍 `armed`——哨兵讓路、`control:` 行與
`park --status` 顯示「等待中」、備援排程殘留（2026-11-22 靠人手 `park --cancel` 才撤）。
成因（ack 不通知 park）在這裡消除。

規則：包擁有者 ≠ acker 且擁有者有 `armed` 標記 ⇒ `park_cli.cancel_marker(owner, event="acked")`；
擁有者＝acker（自續跑）不撤；無標記／已非 armed ⇒ 無動作、rc 0（冪等）。排程拆除只經
`park_cli`（本檔不含任何排程器原語，不新增排程站點）。
"""
from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from . import handoff, park, park_cli, switch


def _acker(env: Mapping | None) -> str:
    return str((os.environ if env is None else env).get("CLAUDE_CODE_SESSION_ID", "") or "")


def on_ack(pkg, acker_sid: str, env: Mapping | None = None, S: dict | None = None) -> str:
    """回 `"cancelled"`／`"self"`／`"noop"`／`"failed"`；不拋（ack 已寫成，撤 park 失敗只出聲）。"""
    try:
        owner = handoff._sid_of(Path(pkg))
        if not owner or owner == acker_sid:
            return "self"  # 原主人自己回來＝續跑（seal.mark_resumed 路），park 不撤
        marker = park.read_marker(owner)
        if marker is None or marker.get("status") != "armed":
            return "noop"
        rc = park_cli.cancel_marker(owner, S, event="acked")
        switch.trace("park_acked_cancel", sid=owner, acker=acker_sid, rc=rc)
        return "cancelled" if rc == 0 else "failed"
    except Exception as exc:  # noqa: BLE001 — 見 docstring：不得反過來讓已成功的 ack 變 rc≠0
        print(f"⚠️ ack 後撤 park 失敗（不影響接手）：{exc}", file=sys.stderr)
        return "failed"


def after_handoff(rest: list[str], rc: int, env: Mapping | None = None) -> int:
    """`tools/sessionctl.py` 的 `handoff` 分支掛點：`--ack <檔>` 成功（rc 0）才呼叫 `on_ack`；
    原 rc 原樣回傳。"""
    if rc != 0:
        return rc
    given = [a.split("=", 1)[1] for a in rest if a.startswith("--ack=")]
    if "--ack" in rest and rest.index("--ack") + 1 < len(rest):
        given.append(rest[rest.index("--ack") + 1])
    for path in given[:1]:
        on_ack(path, _acker(env), env)
        summarize_and_gc(path, _acker(env), env)
    return rc


def summarize_and_gc(pkg, acker: str, env=None, *, table=..., backend=None) -> None:
    """WP-SW REQ-CTL-53／58：ack 原輸出之後印「封存後事件」摘要，再 GC 舊哨兵殘骸；兩者共用同一次範圍化列舉
    （摘要先印＝顯示 GC 前的舊哨兵現況）。任何例外只印一行警告，ack 的 rc 不變。"""
    try:
        from . import ackevents, othersession, parkearly, sentgc  # noqa: PLC0415

        if table is ...:
            table = sentgc.job_table(env, repo_root=park_cli._REPO, backend=backend)  # noqa: SLF001
        print(ackevents.summary(pkg, acker, env, table=table))
        sentgc.sweep(acker, env, repo_root=park_cli._REPO, table=table, backend=backend,  # noqa: SLF001
                     min_idle_s=othersession.SENTINEL_INTERVAL_SECONDS + parkearly.CHILD_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 — 不得讓已成功的 ack 變 rc≠0
        print(f"⚠️ ack 後摘要／GC 失敗（不影響接手）：{type(exc).__name__}: {exc}", file=sys.stderr)
