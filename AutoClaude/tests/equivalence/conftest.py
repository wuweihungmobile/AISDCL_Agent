"""equivalence 測試共用 fixture。

QA 發現（跨平台四方複審 P3）：未 activate venv、直接以 `.venv/bin/python -m pytest`
呼叫時，fixture yaml 的 `evaluator_command`（如 09_conditional 的 `python -c ...`）
經 ShellEvaluator → subprocess(shell=True) 以裸 `python` 啟動子行程 →
`/bin/sh: python: command not found`（exit 127）→ 快照比對失敗。

修法：autouse fixture 將當前直譯器（sys.executable）所在目錄 prepend 到 PATH，
確保子行程解析到的 `python` == 跑測試的 venv python；已在 PATH 首位時 no-op。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _interpreter_dir_on_path(monkeypatch):
    """讓 evaluator 子行程的裸 `python` 一律解析到當前直譯器（venv 未 activate 亦可）。"""
    py_dir = str(Path(sys.executable).parent)
    path = os.environ.get("PATH", "")
    if path.split(os.pathsep)[:1] != [py_dir]:
        monkeypatch.setenv("PATH", py_dir + os.pathsep + path if path else py_dir)
