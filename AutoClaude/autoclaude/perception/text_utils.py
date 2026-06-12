"""感知層文字處理工具：ANSI 控制序列移除等。"""
from __future__ import annotations
import re

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    """移除字串中的所有 ANSI 控制序列（顏色、游標移動等）。"""
    return _ANSI_ESCAPE.sub("", text)
