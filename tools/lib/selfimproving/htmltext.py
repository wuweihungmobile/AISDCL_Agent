"""SelfImproving HTML → 純文字的確定性擷取（AC-SI-30-9；P6）。

能力類別 `ro`：純函式 `to_plain(raw: bytes) -> bytes`，只用標準庫 `html.parser.HTMLParser`
（`convert_charrefs=True`）。丟棄 `script`、`style`、`noscript`、`svg`、`template`、`head` 內的文字
（巢狀以深度計數）；區塊元素起訖各插一個換行；列內空白收斂為單一空格；至多保留一個連續空行；
非空輸出恰以一個 LF 結尾，無任何文字時輸出空位元組。同位元組輸入必得同位元組輸出。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

_SKIP = frozenset({"script", "style", "noscript", "svg", "template", "head"})
_BLOCK = frozenset({"p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article",
                    "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote"})
_WS = re.compile(r"[ \t\r\f\v ]+")


class _Plain(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in _SKIP:
            self.skip += 1
        elif tag in _BLOCK and not self.skip:
            self.parts.append("\n")

    def handle_endtag(self, tag) -> None:
        if tag in _SKIP:
            self.skip = max(self.skip - 1, 0)
        elif tag in _BLOCK and not self.skip:
            self.parts.append("\n")

    def handle_data(self, data) -> None:
        if not self.skip:
            self.parts.append(data)


def to_plain(raw: bytes) -> bytes:
    """HTML 位元組 → 純文字位元組（見模組說明）。"""
    parser = _Plain()
    parser.feed(raw.decode("utf-8", errors="replace"))
    parser.close()
    lines = "".join(parser.parts).split("\n")
    cleaned: list[str] = []
    for line in lines:
        text = _WS.sub(" ", line).strip()
        if text or (cleaned and cleaned[-1]):
            cleaned.append(text)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return ("\n".join(cleaned) + "\n").encode("utf-8") if cleaned else b""
