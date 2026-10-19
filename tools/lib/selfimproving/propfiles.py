"""SelfImproving 提案內容檔落地：`SelfImproving_Proposals/PROP-SI-NNN/rN.{md,patch}`（TCS-P1 R55）。

能力類別 `rw`。目錄與檔在寫入鎖內建立；寫入一律位元組模式（`.patch` 原樣、`.md` 已換 LF）；
已存在的 `rN.*` 不得覆寫（撞名拋 FileExistsError）；追加事件失敗時由呼叫端以 `remove` 刪回。
"""

from __future__ import annotations

from pathlib import Path

from .events import PROPOSALS_REL


def rel_paths(pid: str, rev: int) -> tuple[str, str]:
    base = f"{PROPOSALS_REL}/{pid}"
    return f"{base}/r{rev}.patch", f"{base}/r{rev}.md"


def write(repo: Path, pid: str, rev: int, patch: bytes, body_text: str) -> list[Path]:
    """寫出兩個內容檔，回「本次新建」的路徑（含新建的目錄，由內而外），供失敗時 `remove`。"""
    patch_rel, body_rel = rel_paths(pid, rev)
    patch_path, body_path = repo / patch_rel, repo / body_rel
    for p in (patch_path, body_path):
        if p.exists():
            raise FileExistsError(str(p))
    created: list[Path] = []
    missing, top = [], patch_path.parent
    while not top.exists():
        missing.append(top)
        top = top.parent
    if missing:
        patch_path.parent.mkdir(parents=True)
        created.extend(reversed(missing))  # 由外而內；`remove` 反向刪回
    try:
        patch_path.write_bytes(patch)
        created.append(patch_path)
        body_path.write_bytes(body_text.replace("\r\n", "\n").encode("utf-8"))
        created.append(body_path)
    except OSError:
        remove(created)
        raise
    return created


def remove(created: list[Path]) -> None:
    """刪除先前 `write` 回報的新建檔與目錄（檔先、目錄後；目錄非空則留）。"""
    for p in reversed(created):
        try:
            p.rmdir() if p.is_dir() else p.unlink()
        except OSError:
            pass
