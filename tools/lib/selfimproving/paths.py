"""SelfImproving patch 解析與路徑判準：`touched` 導出、別名形態、glob 比對（TCS-P1 R51、R52）。

純函式、純標準庫、不起子行程：自寫解析器逐行取全部標頭路徑（聯集、寧多勿漏），`git apply --numstat`
超集檢查走 `git.py`、由呼叫端組裝。LATEST 名由呼叫端以參數注入（解析失敗＝None＝全部凍結）。
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import PurePosixPath

_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
             *(f"lpt{i}" for i in range(1, 10))}
_HUNK_RE = re.compile(rb"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
_ESC = {b"a": 7, b"b": 8, b"f": 12, b"n": 10, b"r": 13, b"t": 9, b"v": 11, b'"': 34, b"\\": 92}
LATEST_GLOB = "AISDLC_SDD/AISDLC_SDD_v*/**"
RULE_GLOB = "AISDLC_SDD/*/governance/rules/R-*.yaml"


class PatchError(Exception):
    """patch 無法解析（碼 PATCH-EMPTY／PATCH-BINARY／PATCH-PARSE）。"""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code, self.detail = code, detail


@dataclass
class FileBlock:
    paths: set[str] = field(default_factory=set)
    old: str | None = None
    new: str | None = None
    has_old: bool = False
    has_new: bool = False
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    new_file: bool = False
    deleted: bool = False


def _unquote(tok: bytes) -> tuple[bytes, bytes]:
    """解 C-style 引號字串（tok 以 `"` 起頭）；回（解碼位元組, 其後剩餘）。"""
    out, i = bytearray(), 1
    while i < len(tok):
        c = tok[i:i + 1]
        if c == b'"':
            return bytes(out), tok[i + 1:]
        if c == b"\\":
            nxt = tok[i + 1:i + 2]
            m = re.match(rb"[0-7]{1,3}", tok[i + 1:])
            if m:
                out.append(int(m.group(0), 8) & 0xFF)
                i += 1 + len(m.group(0))
                continue
            if nxt not in _ESC:
                raise PatchError("PATCH-PARSE", "未知的跳脫序列")
            out.append(_ESC[nxt])
            i += 2
            continue
        out += c
        i += 1
    raise PatchError("PATCH-PARSE", "引號未閉合")


def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchError("PATCH-PARSE", "路徑非 UTF-8") from exc


def _token(rest: bytes, cut_tab: bool) -> tuple[str, bytes]:
    rest = rest.lstrip(b" ")
    if rest.startswith(b'"'):
        raw, tail = _unquote(rest)
        return _decode(raw), tail
    if cut_tab:
        rest = rest.split(b"\t", 1)[0]
    return _decode(rest.rstrip(b" ") if cut_tab else rest), b""


def _strip(path: str, prefix: str) -> str:
    return path[2:] if path.startswith(prefix) else path


def _diff_git_paths(rest: bytes) -> tuple[str, str]:
    rest = rest.rstrip(b"\r")
    if rest.startswith(b'"'):
        a, tail = _unquote(rest)
        b, _ = _token(tail, False)
        return _decode(a), b
    text = _decode(rest)
    half = (len(text) - 1) // 2
    if len(text) % 2 == 1 and text[half] == " " and text[:half][2:] == text[half + 1:][2:]:
        return text[:half], text[half + 1:]
    i = text.find(" b/")
    return (text[:i], text[i + 1:]) if i >= 0 else (text, text)


def parse_patch(raw: bytes) -> list[FileBlock]:
    """unified diff → 檔案區塊；無可辨識標頭拋 PatchError。"""
    if not raw.strip():
        raise PatchError("PATCH-EMPTY")
    if b"GIT binary patch" in raw:
        raise PatchError("PATCH-BINARY")
    blocks: list[FileBlock] = []
    cur: FileBlock | None = None
    old_left = new_left = 0
    for line in raw.split(b"\n"):
        line = line[:-1] if line.endswith(b"\r") else line
        if (old_left > 0 or new_left > 0) and line[:1] in (b" ", b"+", b"-", b"\\") and cur:
            tag = line[:1]
            if tag in (b" ", b"-"):
                old_left -= 1
            if tag in (b" ", b"+"):
                new_left -= 1
            if tag == b"+":
                cur.added.append(line[1:].decode("utf-8", "replace"))
            elif tag == b"-":
                cur.removed.append(line[1:].decode("utf-8", "replace"))
            continue
        old_left = new_left = 0
        if line.startswith(b"diff --git "):
            cur = FileBlock()
            blocks.append(cur)
            a, b = _diff_git_paths(line[11:])
            cur.paths |= {_strip(a, "a/"), _strip(b, "b/")}
        elif line.startswith((b"--- ", b"+++ ")):
            is_old = line.startswith(b"--- ")
            if cur is None or (is_old and cur.has_new):
                cur = FileBlock()
                blocks.append(cur)
            path, _ = _token(line[4:], True)
            side = "old" if is_old else "new"
            setattr(cur, "has_" + side, True)
            if path == "/dev/null":
                cur.new_file |= is_old
                cur.deleted |= not is_old
            else:
                path = _strip(path, "a/" if is_old else "b/")
                setattr(cur, side, path)
                cur.paths.add(path)
        elif cur is not None and re.match(rb"(rename|copy) (from|to) ", line):
            path, _ = _token(line.split(b" ", 2)[2], False)
            cur.paths.add(path)
            if b" from " in line[:12]:
                cur.old = cur.old or path
            else:
                cur.new = cur.new or path
        elif cur is not None and (m := _HUNK_RE.match(line)):
            old_left, new_left = int(m.group(1) or 1), int(m.group(2) or 1)
    if not any(b.paths for b in blocks):
        raise PatchError("PATCH-PARSE", "無可辨識的標頭路徑")
    return blocks


_ENTRY_RE = re.compile(r"^\s*([-*+]\s|\d+[.)]\s|#{1,6}\s)")


def new_entries(blocks: list[FileBlock], only: str | None = None) -> int:
    """新增條目數：新增行中符合清單／編號／標題樣式者，加新檔個數（R54 (b)）。
    `only`＝檔名時只計該檔新增的條目行、不計新檔（歸檔型只計索引檔新增的指標行）。"""
    total = 0
    for b in blocks:
        name = (b.new or b.old or "").rsplit("/", 1)[-1]
        if only is not None and name != only:
            continue
        total += sum(1 for line in b.added if line.strip() and _ENTRY_RE.match(line))
        total += 1 if only is None and b.new_file else 0
    return total


def touch_ratio(blocks: list[FileBlock], base_lines: dict[str, int | None]) -> Fraction:
    """被刪行總數 ÷ 被觸及且 base 已存在之檔的總行數；分母為 0（全為新檔）＝0（R54 (a)）。"""
    denom = sum(n for n in base_lines.values() if n)
    removed = sum(len(b.removed) for b in blocks)
    return Fraction(removed, denom) if denom else Fraction(0)


def touched_of(raw: bytes) -> list[str]:
    """全部標頭路徑的聯集（排序、去重）；新增、刪除、改名兩端皆算。"""
    return sorted({p for b in parse_patch(raw) for p in b.paths})


def touched_sha256(paths: list[str]) -> str:
    blob = json.dumps(sorted(set(paths)), ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def alias_reason(path: str) -> str | None:
    """R51 (c) 別名形態（反斜線先換 `/`）；命中回說明、否則 None。"""
    p = path.replace("\\", "/")
    segs = p.split("/")
    if ".." in segs:
        return "含 .. 段"
    if p.startswith("/"):
        return "以 / 起頭（絕對或 UNC）"
    if ":" in p:
        return "含 :（磁碟機代號或資料流）"
    if any(s not in (".",) and (s.endswith(".") or s != s.rstrip(" ")) for s in segs if s):
        return "有段以點或空白結尾"
    if any(s.split(".", 1)[0].casefold() in _RESERVED for s in segs if s):
        return "含 Windows 保留裝置名"
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in p):
        return "含 NUL 或控制字元"
    return None


def normalize(rel: str, repo_real: str) -> str | None:
    """經 realpath 解符號連結後的 repo 相對 POSIX 形（casefold）；逃出 repo 回 None。"""
    full = os.path.realpath(os.path.join(repo_real, rel.replace("\\", "/")))
    try:
        r = os.path.relpath(full, repo_real)
    except ValueError:
        return None
    if r == ".." or r.startswith(".." + os.sep) or os.path.isabs(r):
        return None
    return PurePosixPath(*r.split(os.sep)).as_posix().casefold()


def _match(pat: list[str], segs: list[str]) -> bool:
    if not pat:
        return not segs
    if pat[0] == "**":
        return any(_match(pat[1:], segs[i:]) for i in range(len(segs) + 1))
    return bool(segs) and fnmatch.fnmatchcase(segs[0], pat[0]) and _match(pat[1:], segs[1:])


def glob_match(pattern: str, rel: str) -> bool:
    """相對 repo 根；`**` 吃零段至多段；兩邊先 casefold。"""
    return _match(pattern.casefold().split("/"), rel.casefold().split("/"))


def is_frozen_version_hit(pattern: str, rel: str, latest_name: str | None) -> bool:
    """`AISDLC_SDD/AISDLC_SDD_v*/**` 的語意是「去掉 LATEST」；LATEST 解析失敗（None）＝全部凍結。"""
    if not glob_match(pattern, rel):
        return False
    if pattern.casefold() != LATEST_GLOB.casefold() or latest_name is None:
        return True
    return rel.split("/")[1].casefold() != latest_name.casefold()
