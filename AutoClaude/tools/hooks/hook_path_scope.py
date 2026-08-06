#!/usr/bin/env python
"""兩支阻斷級 hook 共用的「路徑 → repo 相對路徑」正規化（單一實作）。

消費者：`enforce_docs_path.py`（PreToolUse，exit 2）與 `check_sh_eol.py`（PostToolUse，
exit 2）。兩支此前各自帶一份 `normalize_rel_path()`，都走
`Path.resolve().relative_to(PROJECT_ROOT)`——而**這條路的大小寫語意由 flavour 決定**，
於是同一份判準在兩個平台給出方向相反的錯（本輪 Windows 真機實測 + flavour 對拍）：

  · Windows：`resolve()` 會把路徑改寫成磁碟上的真實大小寫（實測連**不存在的檔**也照改，
    只要父目錄存在），`PureWindowsPath.relative_to` 本身又不分大小寫 ⇒ 大小寫變體被悄悄
    修好，兩支 hook 都判得對。
  · POSIX：`realpath` 不動大小寫、`PurePosixPath.relative_to` 分大小寫 ⇒
      - `enforce_docs_path` 拿到 `<root>/DOCS/06_QUALITY/a.md` 時相對路徑仍是
        `DOCS/06_QUALITY/a.md`，前綴比對落空 → **exit 2 假陽性硬擋**（使用者當場撞到，
        卻只會以為是自己路徑打錯）；
      - `check_sh_eol` 拿到 root 前綴大小寫不同的絕對路徑時 `relative_to` 拋 ValueError
        → 回 None → `main()` 直接 return 0 ⇒ **CRLF 守衛整支靜默略過**（fail-open，
        沒有人會發現）。同一個成因，一個方向是過攔、一個方向是漏擋。

本模組把兩支的正規化收斂成同一份**純字面**實作：逐段 casefold 比對、逐段消掉
`.`／`..`，判決完全不問檔案系統，於是 `PureWindowsPath` 與 `PurePosixPath` 兩種
flavour 對同一組輸入必得同一判決。

🔴 大小寫不敏感是**刻意選的方向**，不是隨手選的：它等同 Windows 現行行為，一次關掉
POSIX 側那個假陽性硬擋與那個靜默略過。代價是在真正大小寫敏感的檔案系統上，
`Docs/06_quality/` 這種變體會被視同 `docs/06_quality/` 而放行——那是「白名單多收一個
不存在的目錄」的小口子，換掉的是「守衛在整個平台上失效」與「使用者被錯擋」兩件大事。

回歸鎖：`tools/tests/test_pre_commit_dispatcher_sigpipe.py` 的
`TestHookPathScopeFlavourParity`（同一組輸入在兩種 flavour 下必須同判決）與
`TestHookPathScopeDirectoryBoundary`（前綴比對必須帶目錄邊界）。
"""
from __future__ import annotations

from pathlib import Path, PurePath

__all__ = ["collapse_segments", "relative_within", "repo_relative_posix", "under_prefix"]


def collapse_segments(parts: tuple[str, ...]) -> list[str] | None:
    """逐段消掉 `''`／`.`／`..`（純字面，不碰檔案系統）。

    往上跳出起點（`..` 多於已累積的段數）回 `None`——對兩支消費者而言「跳出去了」
    就是「不歸我管」，不是「相對於根的某個路徑」。舊實作在相對路徑分支直接
    `p.as_posix()` 原樣回傳，於是 `docs/06_quality/../../x.md` 這種輸入會因為
    `startswith('docs/06_quality')` 成立而被當成合法位置放行。
    """
    out: list[str] = []
    for seg in parts:
        if seg in ("", "."):
            continue
        if seg == "..":
            if not out:
                return None
            out.pop()
            continue
        out.append(seg)
    return out


def _casefold_all(segments: list[str]) -> list[str]:
    return [s.casefold() for s in segments]


def relative_within(target: PurePath, root: PurePath) -> str | None:
    """`target` 落在 `root` 底下 → 回 POSIX 相對路徑字串；否則 `None`。

    純字面判準：不呼叫任何檔案系統 API，故可對 `PureWindowsPath` 與 `PurePosixPath`
    兩種 flavour 直接餵同一組輸入做對拍。相對輸入沿用兩支 hook 的既有語意（視為
    已相對於 root）。
    """
    if not target.is_absolute():
        segments = collapse_segments(target.parts)
        return "/".join(segments) if segments else None
    if not root.is_absolute():
        return None
    if target.anchor.casefold() != root.anchor.casefold():
        return None
    tail = collapse_segments(target.parts[1:])
    base = collapse_segments(root.parts[1:])
    if tail is None or base is None:
        return None
    if len(tail) < len(base):
        return None
    if _casefold_all(tail[: len(base)]) != _casefold_all(base):
        return None
    rest = tail[len(base) :]
    return "/".join(rest) if rest else None


def repo_relative_posix(file_path: str, project_root: PurePath) -> str | None:
    """hook payload 的 `file_path` → 相對 `project_root` 的 POSIX 路徑；不在樹內回 `None`。

    絕對路徑先試 `resolve()`（解 symlink；解析失敗就用原路徑），比對本身仍走
    `relative_within()` 的純字面判準，故最終判決不受平台的 realpath 大小寫行為影響。
    """
    if not file_path:
        return None
    try:
        target: PurePath = Path(file_path)
        base: PurePath = Path(project_root)
        if target.is_absolute():
            try:
                target = Path(target).resolve()
            except OSError:
                pass
        try:
            base = Path(base).resolve()
        except OSError:
            pass
        return relative_within(target, base)
    except (ValueError, OSError):
        return None


def under_prefix(rel_posix: str, prefix: str) -> bool:
    """`rel_posix` 是否位於 `prefix` 目錄之下——**帶目錄邊界**、大小寫不敏感。

    舊實作是裸 `str.startswith(prefix)`，於是 `docs/06_qualityEXTRA/a.md`（本輪實測
    回 True）這種「前綴相同但根本是另一個目錄」的路徑會被白名單收下。
    """
    haystack = rel_posix.casefold()
    needle = prefix.casefold().strip("/")
    if not needle:
        return False
    return haystack == needle or haystack.startswith(needle + "/")
