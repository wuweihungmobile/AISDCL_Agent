#!/usr/bin/env python
"""Stop 事件 — 偵測 assistant 最後一輪訊息是否含韓/日/簡體字元（warn-only）。

對應 CLAUDE.md §溝通語言規範。Hook 只能 post-facto 提示，
無法直接改變 LLM 內容生成（這是 LLM 自律的 prompt 規範）。

退出碼：
  0  繁中、無法判定（fail-open），或偵測到非繁中字元（warn-only：提醒走 stdout 單一
     JSON `systemMessage`，只給使用者看、不續回合；DEF-200-447：CC 只認 0／2，exit 1
     會被顯示成 hook error）
  2  保留給未來嚴格模式（目前不使用）

資料源（DEF-200-449）：優先取 Stop payload 的 `last_assistant_message`（官方：Stop 當下
逐字稿不保證含本回合最後訊息；`claude -p` 實測零 assistant 事件，只讀逐字稿＝恆 fail-open），
缺席或空白才退回解析 `transcript_path`。

JSON stdin 協議（Claude Code hooks）：
  { "session_id": "...", "transcript_path": "...", "stop_hook_active": bool,
    "last_assistant_message": "...", ... }
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
from platform_utils import read_hook_payload  # noqa: E402,F401

# 偵測目標字元集：
#   韓文音節：U+AC00 ~ U+D7A3
#   日文 hiragana：U+3041 ~ U+309F
#   日文 katakana：U+30A0 ~ U+30FF（扣除 U+30FB「・」，見 KATAKANA_RE）
#   簡體常用字（高頻誤用集；非完整 GB18030，僅取最易跟繁中混淆者）
KOREAN_RE = re.compile(r"[가-힣]")
HIRAGANA_RE = re.compile(r"[ぁ-ゟ]")
# U+30FB「・」（KATAKANA MIDDLE DOT）刻意排除：繁中人名／外來語也用它當分隔符（愛因斯坦・阿爾
# 伯特），單獨出現不是日文證據；U+30FC「ー」（長音符）仍算日文。故範圍切成 30A0~30FA、30FC~30FF。
KATAKANA_RE = re.compile(r"[\u30a0-\u30fa\u30fc-\u30ff]")
# 簡體 vs 繁體分歧高頻字（僅簡體版本；繁體不會出現）
SIMPLIFIED_HIGH_FREQ = "这个为应实专业无与从让书车马门问题国发对会时间还没"
SIMPLIFIED_RE = re.compile(f"[{re.escape(SIMPLIFIED_HIGH_FREQ)}]")


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


def last_assistant_text(payload: dict) -> str:
    """本回合最後一則 assistant 文字：`last_assistant_message` 優先（DEF-200-449），
    缺席、非字串或空白才退回解析 `transcript_path`；兩者皆空回 ""（呼叫端 fail-open）。"""
    text = payload.get("last_assistant_message")
    if isinstance(text, str) and text.strip():
        return text
    transcript_path = str(payload.get("transcript_path") or "")
    return extract_last_assistant_text(transcript_path) if transcript_path else ""


def main() -> int:
    text = last_assistant_text(read_hook_payload())
    if not text:
        # fail-open；stderr 在 exit 0 下只進 debug log，但「資料源缺席」與「全是繁中」的外觀
        # 逐位元相同（rc=0、stdout 空，DEF-200-449），這句是唯一能把兩種安靜分開的證據。
        print("[check_lang] 無可判定文字（payload 無 last_assistant_message、"
              "逐字稿無 assistant 事件）⇒ 略過", file=sys.stderr)
        return 0
    violations = detect_violations(text)
    if not violations:
        return 0
    msg = (
        f"[check_lang] 偵測到非繁中字元：{', '.join(violations)}。"
        "CLAUDE.md §溝通語言規範要求一律繁體中文（專有名詞除外）；"
        "若非刻意引用，請要求模型改用繁體中文重述。"
    )
    print(msg, file=sys.stderr)  # exit 0 下只進 debug log
    # 使用者可見的警示＝stdout 單一 JSON `systemMessage`（官方：Warning message shown to the
    # user）；不用 emit_to_model：Stop+additionalContext 會讓模型多跑一回合，語言提醒誤報時
    # 是純噪音回合。只此一行 stdout（兩份相接的 JSON 會讓 CC parse 失敗、兩則一起消失）。
    print(json.dumps({"systemMessage": msg}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    _init_utf8_streams()
    sys.exit(main())
