#!/usr/bin/env python
"""Stop 事件 — 偵測 assistant 最後一輪訊息是否含韓/日/簡體字元（warn-only）。

對應 CLAUDE.md §溝通語言規範。Hook 只能 post-facto 提示，
無法直接改變 LLM 內容生成（這是 LLM 自律的 prompt 規範）。

退出碼：
  0  繁中或無法判定（fail-open）
  1  偵測到非繁中字元（warn-only，不阻斷下一輪）
  2  保留給未來嚴格模式（目前不使用）

JSON stdin 協議（Claude Code hooks）：
  { "session_id": "...", "transcript_path": "...", "stop_hook_active": bool, ... }
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "lib"))
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)

# 偵測目標字元集：
#   韓文音節：U+AC00 ~ U+D7A3
#   日文 hiragana：U+3041 ~ U+309F
#   日文 katakana：U+30A0 ~ U+30FF
#   簡體常用字（高頻誤用集；非完整 GB18030，僅取最易跟繁中混淆者）
KOREAN_RE = re.compile(r"[가-힣]")
HIRAGANA_RE = re.compile(r"[ぁ-ゟ]")
KATAKANA_RE = re.compile(r"[゠-ヿ]")
# 簡體 vs 繁體分歧高頻字（僅簡體版本；繁體不會出現）
SIMPLIFIED_HIGH_FREQ = "这个为应实专业无与从让书车马门问题国发对会时间还没"
SIMPLIFIED_RE = re.compile(f"[{re.escape(SIMPLIFIED_HIGH_FREQ)}]")


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


def extract_last_assistant_text(transcript_path: str) -> str:
    """讀 transcript_path（JSONL），取最後一則 assistant 訊息的文字內容。

    Claude Code transcript 為 JSONL，每行一個事件；assistant 訊息形如
    `{"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}`。
    """
    p = Path(transcript_path)
    if not p.exists():
        return ""
    last_text = ""
    try:
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("type") != "assistant":
                continue
            msg = evt.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                last_text = content
            elif isinstance(content, list):
                parts: list[str] = []
                for blk in content:
                    if isinstance(blk, dict) and blk.get("type") == "text":
                        parts.append(blk.get("text", ""))
                if parts:
                    last_text = "\n".join(parts)
    except OSError:
        return ""
    return last_text


def detect_violations(text: str) -> list[str]:
    flags: list[str] = []
    if KOREAN_RE.search(text):
        flags.append("韓文")
    if HIRAGANA_RE.search(text) or KATAKANA_RE.search(text):
        flags.append("日文")
    if SIMPLIFIED_RE.search(text):
        flags.append("簡體中文")
    return flags


def main() -> int:
    payload = read_hook_payload()
    transcript_path = payload.get("transcript_path") or ""
    if not transcript_path:
        return 0  # fail-open
    text = extract_last_assistant_text(transcript_path)
    if not text:
        return 0  # fail-open
    violations = detect_violations(text)
    if not violations:
        return 0
    msg = (
        f"[check_lang] 偵測到非繁中字元：{', '.join(violations)}。"
        "CLAUDE.md §溝通語言規範要求一律繁體中文（專有名詞除外）；"
        "Hook 僅能 post-facto 提示，請於下一輪自我修正。"
    )
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
