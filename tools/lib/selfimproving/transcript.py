"""SelfImproving 逐字稿載體：定位、解析、真人發言判準、卡面送達的時序（TCS-SelfImproving-P2 R77）。

只讀、純標準庫、fail-closed：一律以解析後的結構欄位判定（不做整行子字串比對）；逐字稿格式是觀察所得、
非官方契約。`status` 的逐字稿目錄規則（P1）搬到這裡，單一實作。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lib.platform_utils import claude_home


class TranscriptError(Exception):
    """判準不過；`code` 為 R77／R79 的碼，`ne` 為真表示 NOT-EVALUABLE（量不到，不是判紅）。"""

    def __init__(self, code: str, detail: str = "", ne: bool = False) -> None:
        super().__init__(f"{code} {detail}".strip())
        self.code, self.detail, self.ne = code, detail, ne


@dataclass
class Record:
    no: int  # 實體行號（自 1 起，空白行與壞行都計）
    obj: dict | None  # 非 JSON 物件的行為 None


@dataclass
class Human:
    """兩種真人載體的發言；`ts` 為時序欄（附件取 `attachment.timestamp`、user 取頂層）。"""

    no: int
    text: str
    ts: str | None
    carrier: str  # "user" 或 "attachment"


def transcript_dir(repo: Path) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    return claude_home() / "projects" / slug


def path_for(repo: Path, sid: str) -> Path:
    return transcript_dir(repo) / f"{sid}.jsonl"


def load(path: Path) -> list[Record]:
    """逐行解析（去 BOM、行尾單一 CR 容忍）；檔不存在＝TRANSCRIPT-UNAVAILABLE（NE）。"""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise TranscriptError("TRANSCRIPT-UNAVAILABLE", f"{path.name} 讀不到", ne=True) from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    out = []
    for i, seg in enumerate(parts, start=1):
        seg = seg[:-1] if seg.endswith(b"\r") else seg
        try:
            val = json.loads(seg.decode("utf-8")) if seg.strip() else None
        except (ValueError, UnicodeDecodeError):
            val = None
        out.append(Record(i, val if isinstance(val, dict) else None))
    return out


def parse_ts(value) -> datetime | None:
    """ISO 8601（`Z` 視同 `+00:00`）→ aware UTC；不可解析或無 offset＝None。"""
    if not isinstance(value, str) or not value:
        return None
    try:
        t = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return None
    return t.astimezone(UTC) if t.tzinfo is not None else None


def _blocks(content) -> list:
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(b["text"] for b in _blocks(content)
                     if b.get("type") == "text" and isinstance(b.get("text"), str))


def _origin_kind(origin_holder: dict) -> str | None:
    """`origin` 缺＝ORIGIN-MISSING（NE）；`origin` 不是物件＝非真人；物件缺 `kind`＝NE。"""
    if "origin" not in origin_holder:
        raise TranscriptError("ORIGIN-MISSING", "出處欄位缺席（NOT-EVALUABLE）", ne=True)
    origin = origin_holder["origin"]
    if not isinstance(origin, dict):
        raise TranscriptError("NOT-HUMAN-UTTERANCE", "origin 不是物件")
    if not isinstance(origin.get("kind"), str):
        raise TranscriptError("ORIGIN-MISSING", "origin.kind 缺席（NOT-EVALUABLE）", ne=True)
    return origin["kind"]


def human_of(rec: Record) -> Human:
    """記錄須為兩種真人載體之一，且文字非空；否則拋 `TranscriptError`（R77 (c)、(f)）。"""
    obj = rec.obj
    if obj is None:
        raise TranscriptError("RECORD-UNPARSABLE", f"第 {rec.no} 行不是 JSON 物件")
    if obj.get("type") == "attachment":
        att = obj.get("attachment")
        if not isinstance(att, dict) or att.get("type") != "queued_command":
            raise TranscriptError("NOT-HUMAN-UTTERANCE", "不是 queued_command 附件")
        if _origin_kind(att) != "human":
            raise TranscriptError("NOT-HUMAN-UTTERANCE", "附件的 origin.kind 不是 human")
        text = att.get("prompt") if isinstance(att.get("prompt"), str) else ""
        carrier, ts = "attachment", att.get("timestamp")
    elif obj.get("type") == "user":
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        content = msg.get("content")
        if obj.get("isMeta") is True:
            raise TranscriptError("NOT-HUMAN-UTTERANCE", "isMeta 為 true")
        if "origin" not in obj and any(b.get("type") == "tool_result" for b in _blocks(content)):
            raise TranscriptError("NOT-HUMAN-UTTERANCE", "tool_result 不是人類發言")
        if _origin_kind(obj) != "human":
            raise TranscriptError("NOT-HUMAN-UTTERANCE", "origin.kind 不是 human")
        text, carrier, ts = _text_of(content), "user", obj.get("timestamp")
    else:
        raise TranscriptError("NOT-HUMAN-UTTERANCE", f"記錄 type 為 {obj.get('type')!r}")
    if not text.strip():
        raise TranscriptError("TEXT-EMPTY", "發言文字為空")
    return Human(rec.no, text, ts if isinstance(ts, str) else None, carrier)


def assistant_text(rec: Record) -> str | None:
    """`assistant` 記錄的 `text` 區塊以 LF 連接（CRLF 先換 LF）；沒有任何 `text` 區塊＝None。"""
    obj = rec.obj
    if obj is None or obj.get("type") != "assistant":
        return None
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    blocks = [b for b in _blocks(msg.get("content")) if b.get("type") == "text"
              and isinstance(b.get("text"), str)]
    if not blocks:
        return None
    return "\n".join(b["text"] for b in blocks).replace("\r\n", "\n")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _norm(text: str) -> str:
    return text.replace("\\", "/").casefold()


def exposure(repo: Path, needles: list[str], since: datetime) -> str | None:
    """R90 (b) 暴露掃描：`projects/<slug>/subagents/**/*.jsonl`（子代理逐字稿）中，凍結時刻之後的
    assistant `tool_use` 輸入是否含針。命中＝`HELDOUT-EXPOSED`；目錄不存在＝`EXPOSURE-UNKNOWN`；
    無子代理逐字稿＝未命中（可評估）。缺頂層 `timestamp` 或不可解析者視為落在窗口內（保守）。"""
    base = transcript_dir(repo)
    if not base.is_dir():
        return "EXPOSURE-UNKNOWN"
    keys = [_norm(n) for n in needles]
    subdir = base / "subagents"
    for path in sorted(subdir.rglob("*.jsonl")) if subdir.is_dir() else []:
        if path.stat().st_mtime < since.timestamp():
            continue
        try:
            records = load(path)
        except TranscriptError:
            continue
        for rec in records:
            obj = rec.obj
            when = parse_ts(obj.get("timestamp")) if obj else None
            if obj is None or obj.get("type") != "assistant" or (when and when < since):
                continue
            msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            for block in _blocks(msg.get("content")):
                if block.get("type") == "tool_use" and any(
                        k in _norm(s) for s in _strings(block.get("input")) for k in keys):
                    return "HELDOUT-EXPOSED"
    return None


def find_enclosing(records: list[Record], human: Human) -> str:
    """發言之前最近一則含 `text` 區塊的 assistant 訊息文字（R77 (e)）。

    user 載體＝實體行號小於發言行者中最近的一則；附件載體＝頂層 `timestamp` 嚴格早於
    `attachment.timestamp` 者中時間最大的一則（同時刻取行號較大者）。"""
    if human.carrier == "user":
        for rec in reversed([r for r in records if r.no < human.no]):
            text = assistant_text(rec)
            if text is not None:
                return text
        raise TranscriptError("CARD-NOT-DELIVERED", "發言之前沒有含 text 的 assistant 訊息")
    typed = parse_ts(human.ts)
    if typed is None:
        raise TranscriptError("ATTACHMENT-TIME-UNKNOWN", "attachment.timestamp 缺或不可解析",
                              ne=True)
    best: tuple[datetime, int, str] | None = None
    for rec in records:
        text = assistant_text(rec)
        when = parse_ts(rec.obj.get("timestamp")) if text is not None and rec.obj else None
        if text is not None and when is not None and when < typed:
            if best is None or (when, rec.no) > (best[0], best[1]):
                best = (when, rec.no, text)
    if best is None:
        raise TranscriptError("CARD-NOT-DELIVERED", "附件打出之前沒有含 text 的 assistant 訊息")
    return best[2]
