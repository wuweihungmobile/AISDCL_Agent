#!/usr/bin/env python
"""PostToolUse(Edit|Write) — 對剛寫入的 PowerShell 腳本自動修復**位元組層**兩件事：
UTF-8 BOM 與 CRLF 行尾（徹底根治 PS5.1 亂碼 ＋ 工作樹行尾漂移）。

問題根因（已多次復發）：Write 工具把含中文的 .ps1 存成 UTF-8 **無 BOM** →
Windows PowerShell 5.1 以系統 ANSI codepage（zh-TW=cp950/Big5）解讀 → 中文亂碼
破壞 parser（MissingArrayIndexExpression / 字串遺漏結尾字元）。

🔴 R79 擴充（行尾）：同一個寫入者也把 `.ps1` 一律寫成 **LF**，連覆寫既有 CRLF 檔
都會就地轉成 LF——而本 hook 過去在同一次呼叫裡明明跑了（BOM 補上了），卻對行尾
一個位元組都沒碰，因為它是 `write_bytes(BOM + raw)` 逐位元組保留。三份治理文件
（`.gitattributes` 的 `*.ps1 text eol=crlf`、`.editorconfig`、CI 第 4 道 EOL 閘）
都宣告 `.ps1` 要 CRLF，**卻沒有任何一份管得到「剛剛那次寫入」**，而寫入正是唯一
會製造漂移的動作。R78 花一整輪把 6 支 LF `.ps1` 修回來，下一次全檔 Write 就會再
製造一支且無人知曉。行尾不是樣式問題：CRLF 對「非 ASCII 且無 BOM」的 `.ps1` 是
**載重**——CR 那個位元組正是擋住 CP950 誤讀吃掉換行的東西。

為何 auto-fix 而非 block（對比 check_sh_eol.py 的 exit 2 阻斷）：
  Write 工具結構上無法輸出 BOM、也結構上就是吐 LF，光「規定要 BOM／要 CRLF」
  永遠滿足不了 → 必須由 hook 在事後自動修，才能真正不復發、零人工/模型介入。
  block 只會把工具鎖死。安全性有硬證明：`.ps1` 在 `.gitattributes` 是
  `text eol=crlf`，LF→CRLF 對它 **blob-neutral**（實測同一份內容兩種行尾
  `git hash-object --path *.ps1` 得到逐字相同的 sha）⇒ 這個自動修復結構上
  不可能改變入庫內容，只會消滅本機工作樹與 CI 的分歧。

行為（best-effort，永遠 exit 0，絕不阻斷工具流）：
  - 非 .ps1/.psm1/.psd1               → no-op
  - 內容**非合法 UTF-8**（UTF-16 BOM/Big5/cp950 等）→ **完全 no-op**（含行尾）。
                                        補 UTF-8 BOM 只會製造雙 BOM 或「宣告 UTF-8
                                        內容卻是 Big5」矛盾檔；而 UTF-16 的 `\\n` 是
                                        `0A 00`，位元組層改行尾會把檔案改成奇數長度
                                        直接毀檔。scope 前提是來源＝Claude Write＝
                                        UTF-8，此分支為縱深防禦。
  - 合法 UTF-8（含純 ASCII）           → ①行尾一律收斂成 CRLF（LF／單獨 CR／混合
                                        三種都收；已是 CRLF 則不動，冪等）；
                                        ②含非 ASCII 且無 BOM 時補 UTF-8 BOM
                                        （純 ASCII 仍不補——PS5.1 解 ASCII 無虞，
                                        免動；維持 R57 起的既有政策）。
                                        位元組真的有變才寫檔並在 stderr 提示。

🔴 射程刻意不擴到 `.sh`：那邊的政策是**相反的**（LF），由 check_sh_eol.py 以阻斷
式 hook ＋ pre-commit 看 blob 三重覆蓋。兩支各守一種副檔名，射程重疊即互相打架。

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


def normalize_ps_bytes(raw: bytes) -> tuple[bytes, list[str]]:
    """純函式：回傳 (正規化後的位元組, 做過哪幾件事)。空 list ＝這份內容已合規。

    抽成純函式的理由：兩件位元組級處置（BOM／行尾）的紅綠自證必須能對「一份內容」
    直接施測，不必先落磁碟——否則測試只能驗端到端，而端到端測不出「是哪一半失效」。
    """
    actions: list[str] = []
    has_bom = raw.startswith(UTF8_BOM)
    body = raw[len(UTF8_BOM):] if has_bom else raw
    try:
        body.decode("utf-8")  # 僅處理合法 UTF-8；UTF-16/Big5/cp950 等 → 一律原樣退回
    except UnicodeDecodeError:
        return raw, actions
    # 行尾：先把三種形態全收成 LF，再一次展開成 CRLF（混合行尾也因此收斂）。
    eol_fixed = body.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")
    if eol_fixed != body:
        actions.append("行尾正規化為 CRLF")
    # BOM：維持既有政策——只有「含非 ASCII」才補；純 ASCII 不動。
    need_bom = has_bom or any(b >= 0x80 for b in eol_fixed)
    if need_bom and not has_bom:
        actions.append("補上 UTF-8 BOM")
    new = (UTF8_BOM if need_bom else b"") + eol_fixed
    return new, actions


def fix_ps1_encoding(abs_path: Path) -> int:
    """回傳 1 = 已改寫檔案，0 = 未動（no-op）。"""
    if abs_path.suffix.lower() not in PS_SUFFIXES:
        return 0
    if not abs_path.exists():
        return 0
    try:
        raw = abs_path.read_bytes()
    except OSError:
        return 0
    new, actions = normalize_ps_bytes(raw)
    if new == raw:  # 冪等：已合規就不重寫（否則每次 Write 都多一次磁碟寫入）
        return 0
    try:
        abs_path.write_bytes(new)
    except OSError:
        return 0
    print(
        f"[check_ps1_encoding] AUTO-FIX: 已為 '{abs_path.name}' {'、'.join(actions)}"
        f"（BOM 防 PowerShell 5.1 ANSI 解讀亂碼破壞 parser；CRLF 對齊 .gitattributes "
        f"的 `*.ps1 text eol=crlf`，對入庫 blob 為中性）。",
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
