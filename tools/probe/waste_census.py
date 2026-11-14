#!/usr/bin/env python3
"""浪費帳探針入口（薄殼）：只分派，判準全在 `tools/lib/wastecensus/`。量測探針，不接閘門 rc。

用法：python tools/probe/waste_census.py [--since-days 14] [--sid <sid>] [--out <jsonl>]
      python tools/probe/waste_census.py --replay-hard-ctx [--r1 250000] [--candidates 260000,...]
零 token、只讀逐字稿；逐筆 jsonl 預設寫系統暫存（不寫 repo 內任何檔）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TOOLS))
sys.path.insert(0, str(_TOOLS / "lib"))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
from lib.wastecensus.report import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
