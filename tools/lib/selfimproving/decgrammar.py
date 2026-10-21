"""SelfImproving 決定語法解析器（TCS-SelfImproving-P2 R78）。

純函式、不碰 I/O、不依賴 PROP 狀態：整則訊息文字 → `Parsed` 或 `GrammarError`（屬性 `code` 為
`GRAMMAR-*` 碼）。動詞表即 PRD §7.2 的九列；動詞與 ID、ID 與理由之間恰一個 ASCII 空格。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

QUOTED_MARK = "--- 以下不計入核心區 ---"
_ID_KIND = {"恢復": "RUN"}  # 其餘八個動詞綁 PROP
# 動詞 → (導出 dkind 候選, 尾隨規則：none／reason／promote)
VERBS: dict[str, tuple[tuple[str, ...], str]] = {
    "核准": (("approve",), "none"), "否決": (("reject", "decline-promote"), "reason"),
    "退回": (("return",), "reason"), "晉升": (("promote",), "promote"),
    "轉交": (("ack-handoff",), "none"), "不轉交": (("reject",), "reason"),
    "回滾": (("rollback",), "reason"), "解除": (("unblock",), "none"),
    "恢復": (("resume",), "reason"),
}
_ACK = "未驗採納"


class GrammarError(Exception):
    """整則訊息不受理；`code` 為 R78 的 `GRAMMAR-*` 碼。"""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code} {detail}".strip())
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class Parsed:
    verb: str
    id: str
    kind_candidates: tuple[str, ...]
    trailing: str
    flags: tuple[str, ...]
    line_no: int


def _verb_of(line: str) -> str | None:
    """行首為「動詞＋恰一個 ASCII 空格＋非空白字元」才是決定行（全形空格或連續空格不是）。"""
    for verb in sorted(VERBS, key=len, reverse=True):
        head = verb + " "
        if line.startswith(head) and len(line) > len(head) and not line[len(head)].isspace():
            return None if "*" in line[len(head):].split(" ", 1)[0] else verb  # 整批用語不是決定行
    return None


def _quoted_card(text: str, lines: list[str]) -> bool:
    return (QUOTED_MARK in text or "決定：核准 ／" in text
            or any(ln.startswith("[PROP-SI-") and "｜digest：" in ln for ln in lines))


def _split_id(verb: str, rest: str) -> tuple[str, str]:
    """ID 與其後文字；ID 形態不合或與動詞不配＝GRAMMAR-ID-FORMAT。"""
    kind = _ID_KIND.get(verb, "PROP")
    m = re.match(rf"{kind}-SI-\d{{3,}}", rest)
    if m is None:
        raise GrammarError("GRAMMAR-ID-FORMAT", f"{verb} 須配 {kind}-SI-<至少 3 位數字>")
    tail = rest[m.end():]
    if tail and not tail.startswith(" ") and tail[0].isascii() and tail[0].isalnum():
        raise GrammarError("GRAMMAR-ID-FORMAT", f"ID 後緊接 {tail[0]!r}")
    return m.group(0), tail


def _trailing(verb: str, tail: str) -> tuple[str, tuple[str, ...]]:
    if tail and not tail.startswith(" "):
        raise GrammarError("GRAMMAR-TRAILING", "ID 後須接一個 ASCII 空格或結束")
    text = tail[1:].strip() if tail else ""
    rule = VERBS[verb][1]
    if rule == "none":
        if text:
            raise GrammarError("GRAMMAR-TRAILING", f"{verb} 之後不得有字")
        return "", ()
    if rule == "promote":
        if text == "":
            return "", ()
        if text == _ACK:
            return "", ("unverified_ack",)
        raise GrammarError("GRAMMAR-FORM", "晉升只准前式或後式「未驗採納」")
    if not text:
        raise GrammarError("GRAMMAR-REASON-MISSING", f"{verb} 的理由必填")
    return text, ()


def parse(text: str) -> Parsed:
    """整則訊息 → 唯一的合法決定行；先判引用卡面，再判決定行個數與形態。"""
    norm = text.replace("\r\n", "\n").strip()
    lines = [ln.strip() for ln in norm.split("\n")]
    if _quoted_card(norm, lines):
        raise GrammarError("GRAMMAR-CARD-QUOTED", "整則含卡面引用，不受理")
    hits = [(i, ln, _verb_of(ln)) for i, ln in enumerate(lines, start=1) if _verb_of(ln)]
    if not hits:
        raise GrammarError("GRAMMAR-NO-DECISION", "沒有決定行")
    if len(hits) > 1:
        raise GrammarError("GRAMMAR-MULTI", f"{len(hits)} 個決定行；一則訊息只受理一個")
    line_no, line, verb = hits[0]
    ident, tail = _split_id(verb, line[len(verb) + 1:])
    trailing, flags = _trailing(verb, tail)
    return Parsed(verb, ident, VERBS[verb][0], trailing, flags, line_no)
