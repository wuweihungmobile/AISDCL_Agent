"""名冊範圍：預設只列本 repo 專案的背景代理，沙盒專案不污染（DES §6.1／§6.2；REQ-CTL-11～13）。

WHY：名冊原本掃 `~/.claude/projects` 下**所有** slug；真機驗證案例在沙盒 cwd 跑真 `claude`，
留下的子代理逐字稿（2026-11-22 `rv waiter`）被 `status` 列成本專案的「殘局」。判準只有一個家——
沙盒 slug 片段取 `sandbox_scope.SLUG_FRAGMENT`（R218-B 單一家，與 `is_sandbox` 同源），本檔不寫
第二份樣式；本 repo 的 slug 算法取 `handoff._project_dir`（同上，不另寫）。
`scope_dirs` 只回 `(擁有者 sid, subagents 目錄)`；是否在預設範圍內由呼叫端用同一函式的兩次呼叫
（預設範圍 vs 全部）取差集，故「另有 N 支」與 `--all-projects` 的差集必然一致。
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import sandbox_scope


def repo_slug(repo: Path | None = None) -> str:
    """本 repo 在 `~/.claude/projects` 下的 slug（算法在 `handoff._project_dir`，不複製）。"""
    from . import handoff  # noqa: PLC0415 — lazy：handoff 鏈會回頭 import roster（本檔呼叫端）

    return handoff._project_dir(repo if repo is not None else handoff._REPO).name


def is_sandbox_slug(slug: object) -> bool:
    """slug 屬真機驗證沙盒（`sandbox_scope.SLUG_FRAGMENT`；與 `is_sandbox` 同樣先 normcase）。"""
    return os.path.normcase(sandbox_scope.SLUG_FRAGMENT) in os.path.normcase(str(slug or ""))


def scope_dirs(projects: Path, session_id: str | None, all_projects: bool = False, *,
               repo: str | None = None) -> Iterator[tuple[str, Path]]:
    """`(owner_sid, subagents 目錄)`。給 sid ⇒ 該 sid（行為與舊版逐字相同，不看 `all_projects`）；
    無 sid 且非 `all_projects` ⇒ 只回本 repo slug 下的代理（`projects` 本身就是該 slug 目錄也認）；
    `all_projects` ⇒ 全部專案（舊行為；沙盒項由呼叫端以 `is_sandbox_slug` 標記，不在這裡隱藏）。"""
    seen: set[Path] = set()
    try:
        if session_id:
            pats: tuple[str, ...] = (f"{session_id}/subagents", f"*/{session_id}/subagents")
        elif all_projects:
            pats = ("*/subagents", "*/*/subagents")
        else:
            slug = repo if repo is not None else repo_slug()
            pats = (f"{slug}/*/subagents",) + (("*/subagents",) if projects.name == slug else ())
        for pat in pats:
            for path in projects.glob(pat):
                if path.is_dir() and path not in seen:
                    seen.add(path)
                    yield path.parent.name, path
    except OSError:
        return
