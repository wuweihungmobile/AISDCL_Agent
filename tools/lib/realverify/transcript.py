"""逐字稿讀取與斷言（記錄格式經 2026-11-18 真 `claude -p` 實測，`-p` 與互動模式同形，
見設計稿 §0-2）。

- Stop `decision:block` ⇒ `attachment.type=hook_blocking_error`
  （`hookEvent`、`blockingError.blockingError`）
  ＋一筆 `type=user isMeta` 的 `Stop hook feedback:` ＋ `system/stop_hook_summary`（`hookErrors`）。
- hook 的 systemMessage ⇒ `attachment.type=hook_system_message`（`hookEvent`、`content`）。
- UserPromptSubmit 擋下 ⇒ `type=system subtype=informational preventContinuation=true`，
  `content` 以 `UserPromptSubmit operation blocked by hook:` 開頭。
- 壓縮 ⇒ `type=system subtype=compact_boundary`。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .sandbox import projects_dir

UPS_BLOCK_PREFIX = "UserPromptSubmit operation blocked by hook:"


@dataclass(frozen=True)
class Rec:
    line: int  # 1-based 行號（座標用）
    data: dict

    @property
    def ts(self) -> str:
        return str(self.data.get("timestamp") or "")


def find_transcript(sid: str, base: Path | None = None) -> Path | None:
    """依 sid 在所有專案目錄找 `<sid>.jsonl`（不靠 slug 推算，避開短路徑／大小寫差異）。"""
    root = base if base is not None else projects_dir()
    if not root.is_dir():
        return None
    for d in root.iterdir():
        cand = d / f"{sid}.jsonl"
        if cand.is_file():
            return cand
    return None


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


class Transcript:
    def __init__(self, path: Path, sid: str | None = None):
        self.path = Path(path)
        self.sid = sid or self.path.stem
        self.recs: list[Rec] = []
        for i, ln in enumerate(self.path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):  # noqa: E501
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            if isinstance(d, dict):
                self.recs.append(Rec(i, d))

    @classmethod
    def for_sid(cls, sid: str, base: Path | None = None) -> Transcript:
        p = find_transcript(sid, base)
        if p is None:
            raise FileNotFoundError(f"找不到 sid {sid} 的逐字稿")
        return cls(p, sid)

    # ---- 座標 ----
    def coords(self, rec: Rec) -> str:
        """帳本用座標：`<sid 前 8 碼>:<行號>`。"""
        return f"{self.sid[:8]}:{rec.line}"

    # ---- 取記錄 ----
    def _attachments(self, atype: str, hook_event: str | None = None) -> list[Rec]:
        out = []
        for r in self.recs:
            a = r.data.get("attachment")
            if isinstance(a, dict) and a.get("type") == atype and (hook_event is None or a.get("hookEvent") == hook_event):  # noqa: E501
                out.append(r)
        return out

    def hook_blocking_errors(self, hook_event: str | None = None, contains: str = "") -> list[Rec]:
        out = []
        for r in self._attachments("hook_blocking_error", hook_event):
            be = (r.data["attachment"].get("blockingError") or {})
            text = be.get("blockingError", "") if isinstance(be, dict) else str(be)
            if contains in text:
                out.append(r)
        return out

    def has_blocking_error(self, hook_event: str, contains: str = "") -> bool:
        return bool(self.hook_blocking_errors(hook_event, contains))

    def system_messages(self, hook_event: str | None = None, contains: str = "") -> list[Rec]:
        return [r for r in self._attachments("hook_system_message", hook_event)
                if contains in str(r.data["attachment"].get("content", ""))]

    def has_system_message(self, hook_event: str, contains: str = "") -> bool:
        return bool(self.system_messages(hook_event, contains))

    def stop_hook_summaries(self) -> list[Rec]:
        return [r for r in self.recs if r.data.get("type") == "system" and r.data.get("subtype") == "stop_hook_summary"]  # noqa: E501

    def blocked_user_prompts(self, contains: str = "") -> list[Rec]:
        out = []
        for r in self.recs:
            d = r.data
            if (d.get("type") == "system" and d.get("subtype") == "informational" and d.get("preventContinuation") is True  # noqa: E501
                    and str(d.get("content", "")).startswith(UPS_BLOCK_PREFIX) and contains in str(d.get("content", ""))):  # noqa: E501
                out.append(r)
        return out

    def user_prompt_blocked(self, contains: str = "") -> bool:
        return bool(self.blocked_user_prompts(contains))

    def compact_boundaries(self) -> list[Rec]:
        return [r for r in self.recs if r.data.get("type") == "system" and r.data.get("subtype") == "compact_boundary"]  # noqa: E501

    def has_compact_boundary_after(self, since_iso: str | None = None) -> bool:
        """有沒有 `compact_boundary` 晚於 since_iso（None＝任何一筆）。"""
        bs = self.compact_boundaries()
        if since_iso is None:
            return bool(bs)
        t0 = _parse_ts(since_iso)
        return any((_parse_ts(b.ts) or datetime.min.replace(tzinfo=t0.tzinfo if t0 else None)) > t0 for b in bs) if t0 else bool(bs)  # noqa: E501

    def assistant_texts(self) -> list[str]:
        out = []
        for r in self.recs:
            m = r.data.get("message")
            if r.data.get("type") == "assistant" or (isinstance(m, dict) and m.get("role") == "assistant"):  # noqa: E501
                for c in (m or {}).get("content", []) or []:
                    if isinstance(c, dict) and c.get("type") == "text":
                        out.append(c.get("text", ""))
        return out

    def raw_line(self, rec: Rec, limit: int = 600) -> str:
        return json.dumps(rec.data, ensure_ascii=False)[:limit]
