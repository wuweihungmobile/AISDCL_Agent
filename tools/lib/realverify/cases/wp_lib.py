# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族共用 helper（不登記案例）：逐字稿工具呼叫列舉、
等待輪詢。

🔴 不預植 trust：互動視窗案例需改寫全域 ~/.claude.json（掌舵者禁止），一律列「需人工目視」，不在此家族自動化。
"""  # noqa: E501

from __future__ import annotations

import json
import time
from pathlib import Path

from ..sandbox import Sandbox
from ..transcript import Transcript


def tool_uses(tr: Transcript) -> list[tuple[int, str, dict]]:
    """逐字稿內全部 assistant `tool_use`：`(行號, 工具名, input)`。"""
    out = []
    for r in tr.recs:
        m = r.data.get("message")
        if r.data.get("type") != "assistant" or not isinstance(m, dict):
            continue
        for c in m.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                out.append((r.line, str(c.get("name")), c.get("input") or {}))
    return out


def reads_of(tr: Transcript, needle: str) -> list[tuple[int, str, dict]]:
    """逐字稿裡有沒有 `Read` 類工具（或 cat／Get-Content 的 Bash／PowerShell）讀到含 `needle` 的路徑。"""
    out = []
    for line, name, inp in tool_uses(tr):
        blob = json.dumps(inp, ensure_ascii=False)
        if needle in blob and name in ("Read", "Bash", "PowerShell", "Grep"):
            out.append((line, name, inp))
    return out


def wait_until(pred, timeout_s: float, step: float = 2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return pred()


def other_transcript(sb: Sandbox) -> Path | None:
    """沙盒 slug 目錄下 sid 不等於沙盒主 sid 的逐字稿（互動新視窗開出的）。"""
    for d in sb.transcript_dirs():
        for p in d.glob("*.jsonl"):
            if p.stem != sb.sid:
                return p
    return None
