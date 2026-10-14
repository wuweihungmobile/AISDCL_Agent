"""檔案寫入小工具：run.json／checkpoint 歷史一律「寫新檔 → replace」，且不依賴檔案沒被別人開著。

Windows 行為＝`os.replace` 在目的檔被別的行程／執行緒以讀取模式開著時會丟 PermissionError
（POSIX 恆成功）。處置（掌舵者 2026-10-14 跨平台守則 #4）：replace 包在 `try/except OSError`、
短暫重試（讀者把手是毫秒級的），仍失敗就退回直接覆寫——寧可失去原子性，也不讓狀態寫不下。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

_REPLACE_RETRIES = 8
_REPLACE_INTERVAL = 0.02


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    for attempt in range(_REPLACE_RETRIES):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            if attempt < _REPLACE_RETRIES - 1:
                time.sleep(_REPLACE_INTERVAL)
    # 重試用盡：直接覆寫（非原子，但資料到位），並清掉暫存檔。
    try:
        path.write_text(text, encoding="utf-8", newline="\n")
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def write_json_atomic(path: Path, obj: Any) -> None:
    write_text_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any | None:
    """讀 JSON；檔案不存在或損毀回 None（呼叫端決定要不要當成缺失）。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
