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

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT.parent / "tools" / "lib"))
# 本檔會被 `runpy.run_path()`（.claude/settings.json 的 shim）與
# `importlib.util.spec_from_file_location()`（單元測試）載入，兩者都**不會**把本檔所在
# 目錄放進 sys.path ⇒ 同層模組必須自己接上，否則 hook 會在 import 期炸掉。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_path_scope import (  # noqa: E402
    repo_relative_posix as _repo_relative_posix,  # type: ignore[import-not-found]
)
from hook_path_scope import (  # noqa: E402
    under_prefix as _under_prefix,  # type: ignore[import-not-found]
)
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)
from platform_utils import read_hook_payload  # noqa: E402,F401

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


def normalize_rel_path(file_path: str) -> str | None:
    """嘗試把絕對路徑轉成相對於 PROJECT_ROOT 的 POSIX 路徑；非專案路徑回 None。

    正規化本體住共用層 `hook_path_scope.py`（與 `check_sh_eol.py` 同一份實作）——
    見該檔檔頭：舊的 `resolve().relative_to()` 在 POSIX 上會讓本 hook 對大小寫變體
    **假陽性硬擋**，而讓姊妹 hook 靜默略過。不在 PROJECT_ROOT 之下 → fail-open。
    """
    return _repo_relative_posix(file_path, PROJECT_ROOT)


def is_allowed_md(rel_posix: str) -> bool:
    # 根層白名單（大小寫不敏感，與目錄前綴同一套語意）
    if "/" not in rel_posix:
        folded = rel_posix.casefold()
        if any(folded == name.casefold() for name in ROOT_WHITELIST):
            return True
    # 目錄前綴：`_under_prefix` 帶目錄邊界，`docs/06_qualityEXTRA/` 不再被收下
    return any(_under_prefix(rel_posix, prefix) for prefix in ALLOWED_DIR_PREFIXES)


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
