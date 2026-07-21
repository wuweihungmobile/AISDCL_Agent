#!/usr/bin/env python
"""PostToolUse(Edit|Write) — 對剛寫入的 PowerShell 腳本自動修復編碼（徹底根治 PS5.1 亂碼）。

問題根因（已多次復發）：Write 工具把含中文的 .ps1 存成 UTF-8 **無 BOM** →
Windows PowerShell 5.1 以系統 ANSI codepage（zh-TW=cp950/Big5）解讀 → 中文亂碼
破壞 parser（MissingArrayIndexExpression / 字串遺漏結尾字元）。

為何 auto-fix 而非 block（對比 check_sh_eol.py 的 exit 2 阻斷）：
  Write 工具結構上無法輸出 BOM，光「規定要 BOM」永遠滿足不了 → 必須由 hook
  在事後自動補 BOM，才能真正不復發、零人工/模型介入。

行為（best-effort，永遠 exit 0，絕不阻斷工具流）：
  - 非 .ps1/.psm1/.psd1               → no-op
  - 已含 UTF-8 BOM (EF BB BF)         → no-op
  - 純 ASCII（全部 < 0x80）            → no-op（PS5.1 解 ASCII 無虞，免動）
  - 含非 ASCII 但**非合法 UTF-8**      → no-op（UTF-16 BOM/Big5/cp950 等；補 UTF-8 BOM
                                        只會製造雙 BOM 或「宣告 UTF-8 內容卻是 Big5」矛盾檔，
                                        反而惡化——scope 前提是來源＝Claude Write＝UTF-8，
                                        此分支為縱深防禦）
  - 含非 ASCII 且為合法 UTF-8 且無 BOM → 自動於檔首補 UTF-8 BOM，stderr 提示

root session 不遞迴載子目錄 hook，故本 script 同時 wire 於根 .claude/settings.json
（以 ${CLAUDE_PROJECT_DIR}/AutoClaude/tools/hooks/ 絕對呼叫）與 AutoClaude/.claude。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

PS_SUFFIXES = {".ps1", ".psm1", ".psd1"}
UTF8_BOM = b"\xef\xbb\xbf"


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
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}  # 頂層非 dict（array/number/str）→ 視為空


def resolve_path(file_path: str) -> Path | None:
    if not file_path:
        return None
    try:
        p = Path(file_path)
        return p if p.is_absolute() else p.resolve()
    except (ValueError, OSError, TypeError):  # TypeError：file_path 非 str 時 Path() 會拋
        return None


def fix_ps1_encoding(abs_path: Path) -> int:
    """回傳 1 = 已補 BOM，0 = 未動（no-op）。"""
    if abs_path.suffix.lower() not in PS_SUFFIXES:
        return 0
    if not abs_path.exists():
        return 0
    try:
        raw = abs_path.read_bytes()
    except OSError:
        return 0
    if raw.startswith(UTF8_BOM):
        return 0
    if all(b < 0x80 for b in raw):  # 純 ASCII，PS5.1 無虞
        return 0
    try:
        raw.decode("utf-8")  # 僅對合法 UTF-8 補 BOM；UTF-16/Big5/cp950 等非 UTF-8 → no-op
    except UnicodeDecodeError:
        return 0
    try:
        abs_path.write_bytes(UTF8_BOM + raw)
    except OSError:
        return 0
    print(
        f"[check_ps1_encoding] AUTO-FIX: 已為 '{abs_path.name}' 補上 UTF-8 BOM"
        f"（含非 ASCII 字元；防 PowerShell 5.1 ANSI 解讀亂碼破壞 parser）。",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    payload = read_hook_payload()
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):  # tool_input 為 list/str/null → 安全 no-op
        return 0
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:  # file_path 非 str/空 → 安全 no-op
        return 0
    abs_path = resolve_path(file_path)
    if abs_path is None:
        return 0
    fix_ps1_encoding(abs_path)
    return 0  # auto-fix：永不阻斷


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
