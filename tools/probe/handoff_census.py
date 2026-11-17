#!/usr/bin/env python3
"""散文交棒判準的真實面假紅普查（事後量測器；不接任何閘門的 rc）。

判準**向 `.claude/hooks/check_pending_handoff.py` 借**（`pending_handoff_hits`／回合邊界／
AskUserQuestion 偵測），本檔不另寫第二份——同一份知識只有一個家。母體＝`~/.claude/projects/
<slug>/*.jsonl` 頂層主 session（刻意不含 `<session>/subagents/`：子代理沒有收尾交棒給掌舵者的
語境）。回合＝兩則真人 role=user 訊息之間；取該回合**最後一則** assistant 文字，命中且同回合無
AskUserQuestion ⇒ 列出。數字是量測值不是常數；用法：

    python tools/probe/handoff_census.py [<projects 目錄>...]
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "check_pending_handoff.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("check_pending_handoff", _HOOK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _assistant_text(rec: dict) -> str:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(c.get("text", "") for c in content
                       if isinstance(c, dict) and c.get("type") == "text")
    return ""


def scan(path: str, hook) -> list[tuple[str, str, str, bool]]:
    """→ `[(sid 短碼, 落款, 回合最後一則 assistant 文字, 本回合有無 AskUserQuestion)]`。"""
    turns: list[tuple[str, str, str, bool]] = []
    sid = os.path.basename(path)[:8]
    text, when, asked = "", "", False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"type"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            if hook._is_operator_turn(rec):
                if text:
                    turns.append((sid, when, text, asked))
                text, when, asked = "", "", False
            elif rec.get("type") == "assistant" and not rec.get("isSidechain"):
                asked = asked or hook._asks_user(rec)
                body = _assistant_text(rec)
                if body.strip():
                    text, when = body, str(rec.get("timestamp") or "")
    if text:
        turns.append((sid, when, text, asked))
    return turns


def _midwork_census(files: list[str], hook) -> int:
    """`--midwork`：回合結尾命中「接下來我還要做事」詞表的數量與前 15 筆（人工判真假陽性）。"""
    turns = hits = 0
    shown: list[str] = []
    for path in files:
        for sid, when, text, asked in scan(path, hook):
            turns += 1
            found = hook.midwork_hits(text)
            if not found:
                continue
            hits += 1
            if len(shown) < 15:
                shown.append(f"[{sid}] {when} ask={asked} {found[0]['word']} :: "
                             f"{found[0]['sentence'][:140]}")
    print("\n".join(shown))
    print(f"files={len(files)} turns={turns} midwork_wording_hits={hits} "
          f"rate={hits / max(1, turns):.4f}")
    return 0


def main(argv: list[str]) -> int:
    hook = _load_hook()
    midwork = "--midwork" in argv  # 半路停工措辭那一半（狀態那一半在 Stop payload，逐字稿重放不到）
    argv = [a for a in argv if a != "--midwork"]
    roots = argv or [os.path.expanduser("~/.claude/projects")]
    files = sorted(f for root in roots for f in glob.glob(os.path.join(root, "*", "*.jsonl")))
    if midwork:
        return _midwork_census(files, hook)
    turns = hits = silenced = 0
    words: Counter = Counter()
    for path in files:
        for sid, when, text, asked in scan(path, hook):
            turns += 1
            found = hook.pending_handoff_hits(text)
            if not found:
                continue
            if asked:
                silenced += 1
                continue
            hits += 1
            words.update(h["word"] for h in found)
            print(f"[{sid}] {when} n={len(found)}")
            for h in found[:3]:
                print(f"    {h['word']} :: {h['sentence'][:160]}")
    print(f"files={len(files)} turns={turns} hits_no_ask={hits} silenced_by_ask={silenced} "
          f"rate={hits / max(1, turns):.4f}")
    print("words:", dict(words.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
