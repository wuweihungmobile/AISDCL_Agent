"""SelfImproving held-out 目錄格式判準（TCS-SelfImproving-P2 R83 (a)）。

只讀、純標準庫：`<dir>/manifest.json`（UTF-8 無 BOM、LF）頂層鍵恰 `schema_rev`、`cases`、`probes`，
選用 `mutation`；`cases`＝`[{id, ref}]`（`ref` 須存在於 OBS 帳本含封存檔或缺陷帳本家族）；`probes`＝
`[{id, argv, [module], n_pop}]`（`argv[0]` 恰為 `{python}`）。`heldout-freeze`、`verify` 共用。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .events import DEF_ID_RE, OBS_ID_RE

MANIFEST = "manifest.json"
_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_TOP = {"schema_rev", "cases", "probes", "mutation"}
_REPARSE = 0x400  # Windows FILE_ATTRIBUTE_REPARSE_POINT：連結與 junction 都帶它
Code = tuple[str, str]


@dataclass
class Loaded:
    data: dict | None = None
    problems: list[Code] = field(default_factory=list)


def _bad(detail: str) -> Code:
    return ("HELDOUT-MANIFEST-INVALID", detail)


def _is_link(entry: os.DirEntry) -> bool:
    if entry.is_symlink():
        return True
    attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attrs & _REPARSE)


def find_links(root: Path) -> list[str]:
    """目錄樹內的符號連結或 junction（相對路徑）；以 `os.scandir` 逐層走，不跟隨連結。"""
    out: list[str] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        with os.scandir(cur) as it:
            for entry in sorted(it, key=lambda e: e.name):
                rel = Path(entry.path).relative_to(root).as_posix()
                if _is_link(entry):
                    out.append(rel)
                elif entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
    return out


def _check_cases(cases) -> tuple[list[Code], list[str]]:
    if not isinstance(cases, list):
        return [_bad("cases 須為陣列")], []
    probs: list[Code] = []
    ids: list[str] = []
    refs: list[str] = []
    for i, c in enumerate(cases):
        ok = (isinstance(c, dict) and set(c) == {"id", "ref"} and isinstance(c["id"], str)
              and c["id"] and isinstance(c["ref"], str)
              and (OBS_ID_RE.match(c["ref"]) or DEF_ID_RE.match(c["ref"])))
        if not ok:
            probs.append(_bad(f"cases[{i}] 須為 {{id, ref}}（ref 為 OBS 或 DEF 號）"))
            continue
        ids.append(c["id"])
        refs.append(c["ref"])
    if len(set(ids)) != len(ids):
        probs.append(_bad("cases 的 id 重複"))
    return probs, refs


def _check_probes(probes) -> list[Code]:
    if not isinstance(probes, list):
        return [_bad("probes 須為陣列")]
    probs: list[Code] = []
    ids: list[str] = []
    for i, p in enumerate(probes):
        keys = set(p) if isinstance(p, dict) else set()
        if not (isinstance(p, dict) and {"id", "argv", "n_pop"} <= keys
                <= {"id", "argv", "module", "n_pop"}):
            probs.append(_bad(f"probes[{i}] 鍵須為 id、argv、n_pop 與選用的 module"))
            continue
        if not (isinstance(p["id"], str) and p["id"]):
            probs.append(_bad(f"probes[{i}].id 須為非空字串"))
        else:
            ids.append(p["id"])
        argv = p["argv"]
        if not (isinstance(argv, list) and argv and all(isinstance(a, str) for a in argv)
                and argv[0] == "{python}"):
            probs.append(_bad(f"probes[{i}].argv 須為字串陣列且第 0 項恰為 {{python}}"))
        if "module" in p and not (isinstance(p["module"], str) and _MODULE_RE.match(p["module"])):
            probs.append(_bad(f"probes[{i}].module 含非法字元"))
        n = p["n_pop"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            probs.append(_bad(f"probes[{i}].n_pop 須為整數 ≥0"))
    if len(set(ids)) != len(ids):
        probs.append(_bad("probes 的 id 重複"))
    return probs


def _check_mutation(root: Path, name) -> list[Code]:
    if not (isinstance(name, str) and name and "/" not in name and "\\" not in name
            and name != ".." and not name.startswith(".")):
        return [_bad("mutation 須為目錄內的檔名（無路徑分隔符、非 ..、不以 . 起頭）")]
    return [] if (root / name).is_file() else [_bad(f"mutation 指向的檔不存在：{name}")]


def load(root: Path, known_refs: set[str] | None = None) -> Loaded:
    """讀並驗 `manifest.json`；`known_refs` 給了才判 `HELDOUT-REF-UNRESOLVED`。"""
    path = root / MANIFEST
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return Loaded(None, [_bad(f"{MANIFEST} 缺、非 UTF-8 或不是 JSON")])
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        return Loaded(None, [_bad(f"{MANIFEST} 須為 UTF-8 無 BOM、LF")])
    if not isinstance(data, dict) or not {"schema_rev", "cases", "probes"} <= set(data) <= _TOP:
        return Loaded(None, [_bad("頂層鍵須恰為 schema_rev、cases、probes 與選用的 mutation")])
    probs: list[Code] = []
    if data["schema_rev"] != 1 or isinstance(data["schema_rev"], bool):
        probs.append(_bad("schema_rev 須為整數 1"))
    case_probs, refs = _check_cases(data["cases"])
    probs += case_probs + _check_probes(data["probes"])
    if "mutation" in data:
        probs += _check_mutation(root, data["mutation"])
    if probs:
        return Loaded(None, probs)
    if not data["cases"]:
        return Loaded(None, [("HELDOUT-EMPTY", "cases 為空（n 須 ≥1）")])
    if known_refs is not None:
        missing = sorted({r for r in refs if r not in known_refs})
        if missing:
            return Loaded(None, [("HELDOUT-REF-UNRESOLVED",
                                  "ref 不在 OBS 帳本或缺陷帳本家族：" + "、".join(missing))])
    return Loaded(data, [])
