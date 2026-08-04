#!/usr/bin/env python
"""PostToolUse(Edit|Write) — 對剛修改的 .sh 檔做行尾檢查（LF 強制）。

對應 CLAUDE.md §Nightly / CI 取證紀律 #8（SD_09 W0 P0-AUDIT-31 修復項）：
跨 Docker container 執行的 .sh 若被 Windows git autocrlf 轉成 CRLF →
Linux bash 噴 `$'\\r': command not found` + syntax error，視為 P0。

行為：
  - 非 .sh / 非 .bash → exit 0
  - 含 CR (\\r) 行尾 → stderr error（exit 2，阻斷；強制改回 LF）
  - 純 LF → exit 0

對齊：.gitattributes 已強制 `*.sh text eol=lf`；此 hook 為**事中守門**。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[2]
_MONOREPO_ROOT = _AUTOCLAUDE_ROOT.parent

# 🔴 R74（PKG-4 G）：解析基準由 `AutoClaude/` 上移到 **monorepo 根**。
#
# WHY：舊版以 `AutoClaude/` 為根，而 `normalize_rel_path()` 對「resolve 後不在該根底下」
# 的絕對路徑一律回 None ⇒ exit 0。於是在 monorepo 根 session 下編輯
# `tools/*.sh`／`AISDLC_SDD/**/*.sh` 時，本 hook **整支靜默失效**——`AutoClaude/` 之外的
# 每一支 .sh 都沒有事中守門，而本 hook 的立意（紀律 #8：CRLF 的 .sh 在 Linux container
# 內噴 `$'\r': command not found`，視為 P0）與檔案住在哪個子專案完全無關。
# 這正是「鎖射程只圈一個站點」的同型（`DEF-101-757`／`DEF-101-777`）：守衛存在、
# 但它看得見的範圍只有當初落地的那一棵樹。
#
# 相依上本來就已經綁死 monorepo 佈局（下一行 import 的 `platform_utils` 住在
# **根層** `tools/lib/`），故以「根層 tools/lib/platform_utils.py 是否存在」判定
# monorepo checkout；不成立時退回舊行為（獨立 AutoClaude checkout）。
# 變數名沿用 `PROJECT_ROOT`：既有單元測試以 `monkeypatch.setattr(mod, "PROJECT_ROOT", …)`
# 注入假樹，改名會讓那些測試靜默失去注入點（測試會照綠，但驗的是別的東西）。
PROJECT_ROOT = (
    _MONOREPO_ROOT
    if (_MONOREPO_ROOT / "tools" / "lib" / "platform_utils.py").is_file()
    else _AUTOCLAUDE_ROOT
)

sys.path.insert(0, str(_MONOREPO_ROOT / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

SHELL_SUFFIXES = {".sh", ".bash"}


def read_hook_payload() -> dict:
    # zh-TW Windows pipe 預設 cp950：裸 sys.stdin.read() 遇含中文的 UTF-8 payload 會拋
    # UnicodeDecodeError → 阻斷級 hook 靜默失效。改讀 bytes 端以 UTF-8+replace 解碼；
    # 無 buffer（如測試以 StringIO 替身）時回退文字端。
    stdin_buffer = getattr(sys.stdin, "buffer", None)
    if stdin_buffer is not None:
        raw = stdin_buffer.read().decode("utf-8", "replace").strip()
    else:
        raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def normalize_rel_path(file_path: str) -> Path | None:
    if not file_path:
        return None
    try:
        p = Path(file_path)
        if p.is_absolute():
            return p.resolve().relative_to(PROJECT_ROOT)
        return p
    except (ValueError, OSError):
        return None


def has_crlf(abs_path: Path) -> bool:
    try:
        raw = abs_path.read_bytes()
    except OSError:
        return False
    return b"\r\n" in raw or b"\r" in raw.replace(b"\r\n", b"")


def check_sh_eol(rel: Path) -> int:
    if rel.suffix.lower() not in SHELL_SUFFIXES:
        return 0
    abs_path = PROJECT_ROOT / rel
    if not abs_path.exists():
        return 0
    if has_crlf(abs_path):
        print(
            f"[check_sh_eol] BLOCK: '{rel.as_posix()}' 含 CR/CRLF 行尾。"
            f"跨 Docker container 執行的 .sh 必須為 LF（CLAUDE.md 紀律 #8 / .gitattributes）。"
            f" 修復：dos2unix 或編輯器改為 LF。",
            file=sys.stderr,
        )
        return 2
    return 0


def main() -> int:
    payload = read_hook_payload()
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0

    rel = normalize_rel_path(file_path)
    if rel is None:
        return 0

    return check_sh_eol(rel)


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
