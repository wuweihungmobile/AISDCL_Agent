"""spawn 前置排除的「自動寫入面」判準（DEF-200-609 SI 自有面；R217 REQ-WP-09 OIR 驅動器自有面）。

`git status --short` 一行的每個路徑（改名兩端皆判）都落在自動寫入面內，就不算「本 session 做到
一半的工作」：SI 巡邏、OIR 驅動器會在無人時自己追加帳本，封存後這些寫入讓工作樹變髒，轉送與 spawn
因此永遠開不了窗。新 session 接手同一棵樹後由有人窗口另開 commit，不會遺失。

兩個來源各自讀不到 ⇒ 該來源不排除（保守，回到原本的拒絕）：SI 自有面 SSOT＝
`selfimproving.sched.OWN_PREFIXES`；驅動器自有面 SSOT＝`OpenItems_Protocol/params.json` 的
`driver_own_prefixes`（只透過資料檔讀，不 import openitems——跨套件只走資料檔）。引號化路徑
（非 ASCII）一律不排除。
"""
from __future__ import annotations

import json
from pathlib import Path


def si_prefixes() -> tuple[str, ...]:
    try:
        from lib.selfimproving.sched import OWN_PREFIXES  # noqa: PLC0415 — 只在要判時付成本
    except Exception:  # noqa: BLE001 — 讀不到 SSOT 就不排除任何一行
        return ()
    return tuple(OWN_PREFIXES)


def driver_prefixes(repo: Path | None) -> tuple[str, ...]:
    try:
        data = json.loads((Path(repo) / "docs/06_quality/OpenItems_Protocol/params.json")
                          .read_text(encoding="utf-8"))
        rows = data["driver_own_prefixes"]
        ok = isinstance(rows, list) and all(isinstance(r, str) and r for r in rows)
        return tuple(rows) if ok else ()
    except Exception:  # noqa: BLE001 — 保守：量不到就不排除
        return ()


def _owned(line: str, prefixes: tuple[str, ...]) -> bool:
    body = line[3:] if len(line) > 3 else ""
    paths = body.split(" -> ") if " -> " in body else [body]
    return bool(prefixes) and all(p and not p.startswith('"') and p.startswith(prefixes)
                                  for p in paths)


def si_owned(line: str) -> bool:
    """只動 SI 自有寫入面（DEF-200-609）。"""
    return _owned(line, si_prefixes())


def auto_owned(line: str, repo: Path | None = None) -> bool:
    """SI 自有面 ∪ OIR 驅動器自有面（REQ-WP-09）。"""
    return _owned(line, si_prefixes() + driver_prefixes(repo))
