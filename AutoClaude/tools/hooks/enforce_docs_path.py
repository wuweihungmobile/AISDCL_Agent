#!/usr/bin/env python
"""PreToolUse(Write) 事件 — 對 `.md` 寫入強制白名單目錄。

對應 CLAUDE.md §專案文檔目錄規範。違規 → exit 2 阻斷 Write tool 呼叫。

白名單：
  - docs/01_requirements/ ~ docs/08_deployment/（及任何子目錄）
  - 根層白名單：CLAUDE.md, README.md, MEMORY.md
  - tests/ 內任何 .md（測試 fixtures）— 容許

退出碼：
  0  非 .md 檔，或 .md 在白名單內 → 放行
  2  .md 寫入到非白名單目錄 → 阻斷
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

ALLOWED_DIR_PREFIXES = (
    "docs/01_requirements",
    "docs/02_architecture",
    "docs/03_testing",
    "docs/04_planning",
    "docs/05_development",
    "docs/06_quality",
    "docs/07_design",
    "docs/08_deployment",
    "tests/",  # 測試 fixtures（如 mock_playbook.yaml 附帶 .md）
    "AISDLC_v0.09/",  # AISDLC framework 自身文件
)

ROOT_WHITELIST = {
    "CLAUDE.md",
    "README.md",
    "MEMORY.md",
    "ONBOARDING.md",  # /share-onboarding 工作流產物
}


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


def normalize_rel_path(file_path: str) -> str | None:
    """嘗試把絕對路徑轉成相對於 PROJECT_ROOT 的 POSIX 路徑；非專案路徑回 None。"""
    if not file_path:
        return None
    try:
        p = Path(file_path)
        if p.is_absolute():
            rel = p.resolve().relative_to(PROJECT_ROOT)
        else:
            rel = p
        return rel.as_posix()
    except (ValueError, OSError):
        # 不在 PROJECT_ROOT 之下 → 不歸我們管，fail-open
        return None


def is_allowed_md(rel_posix: str) -> bool:
    # 根層白名單
    if "/" not in rel_posix and rel_posix in ROOT_WHITELIST:
        return True
    # 目錄前綴
    for prefix in ALLOWED_DIR_PREFIXES:
        if rel_posix.startswith(prefix):
            return True
    return False


def main() -> int:
    payload = read_hook_payload()
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    # 僅檢查 .md 檔
    if not file_path.lower().endswith(".md"):
        return 0

    rel_posix = normalize_rel_path(file_path)
    if rel_posix is None:
        return 0  # 不在 PROJECT_ROOT，放行

    if is_allowed_md(rel_posix):
        return 0

    msg = (
        f"[enforce_docs_path] 阻斷：文件路徑 '{rel_posix}' 違反 CLAUDE.md §專案文檔目錄規範。\n"
        "  允許位置：docs/0[1-8]_<type>/（八個編號子目錄）\n"
        f"  根層白名單：{sorted(ROOT_WHITELIST)}\n"
        "  若需新增白名單，請更新 tools/hooks/enforce_docs_path.py 的 "
        "ALLOWED_DIR_PREFIXES / ROOT_WHITELIST。"
    )
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
