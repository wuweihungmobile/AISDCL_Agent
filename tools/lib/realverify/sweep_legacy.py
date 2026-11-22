"""`realverify sweep --legacy`：DES §9 的既有外洩物清單（X1～X5、X7）與「含已知沙盒 sid 的真 `~/.autosdd` 檔」。

只在掌舵者／主控同意後才 `--apply`（`--legacy` 本身只列、不改任何檔）。**永不觸及** X6（共用只追加帳
`traces/*.jsonl` 的史料列）與 X8（`~/.claude.json` 失效信任鍵，全域設定須掌舵者決定；任何 tools 程式
都不寫它，REQ-SE-51）。清單是有限的固定樣式——不是「看起來像沙盒的都刪」。
"""  # noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import sandbox

#: 已知的幽靈／洩漏沙盒 sid 前綴（DES §9 事故物證；只對真 `~/.autosdd` 的這些子目錄比對檔名開頭）。
KNOWN_SIDS = ("57d0ccad", "ccddda28", "aab03328", "d7ad5eb4")
#: 掃描的真 `~/.autosdd` 子目錄（第一層檔名；不含 `traces/*.jsonl` 帳＝X6）。
SID_DIRS = ("handoff", "handoff/_quarantine", "handoff/_quarantine/handback", "handback", "plans",
            "context_feed", "traces/park")
#: X7：三個沙盒根早已不在的 `~/.claude/projects` 專案目錄（名稱尾碼）。
X7_SUFFIXES = ("78znhvop", "og6lrctv", "truqufqq")
NEVER = ("traces/*.jsonl（X6 共用只追加帳）", "~/.claude.json（X8 全域設定）")


@dataclass(frozen=True)
class Item:
    tag: str
    path: Path


def items(autosdd: Path | None = None, projects: Path | None = None) -> list[Item]:
    """現存的 legacy 項目（唯讀）。X1～X5 與「含已知 sid 的檔」合併成 `X1-5/sid` 一類（同一組樣式的並集）。"""  # noqa: E501
    root = Path(autosdd) if autosdd is not None else sandbox.real_autosdd()
    proj = Path(projects) if projects is not None else sandbox.projects_dir()
    out: list[Item] = []
    seen: set[Path] = set()
    for sub in SID_DIRS:
        base = root / sub
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_file() and p.name.startswith(KNOWN_SIDS) and p not in seen:
                seen.add(p)
                out.append(Item("X1-X5", p))
    if proj.is_dir():
        for p in sorted(proj.iterdir()):
            if p.is_dir() and any(p.name.endswith(s) and "AutoSDD-RV-sbx-" in p.name for s in X7_SUFFIXES):  # noqa: E501
                out.append(Item("X7", p))
    return out


def apply(found: list[Item]) -> list[str]:
    """刪除；回刪除失敗的路徑（空＝全部刪掉）。只刪 `items()` 列出的項目。"""
    bad: list[str] = []
    for it in found:
        try:
            if it.path.is_dir():
                if sandbox._remove_tree(it.path, "legacy"):  # noqa: SLF001 — 同一支「刪完驗證」原語
                    bad.append(str(it.path))
            else:
                it.path.unlink(missing_ok=True)
        except OSError:
            bad.append(str(it.path))
    return bad
