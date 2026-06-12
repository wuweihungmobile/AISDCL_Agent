"""git_verifier.py — git diff 修正驗證（SD_06 W2-T2-13）。

對應 SD_05 W2 公開 API：
  - verify_correction_applied (Gap-009-C，原 _verify_correction_applied)
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional


def _propagate_trace_env() -> dict[str, str]:
    """SD_09 W0 M-04: 將當前 env（含 AUTOCLAUDE_TRACE_ID）傳遞至 subprocess。

    Plugin 邊界（importlinter Rule 7）：禁止直接 import
    `autoclaude.utils.trace_context`。僅讀 os.environ 中已注入的
    AUTOCLAUDE_TRACE_ID（caller 須事先 with_trace_id() + 透過 EventBus 流程啟動）。
    """
    return dict(os.environ)


_WARNING_TEMPLATE = (
    "⚠️ 警告（attempt {attempt}）：你的上一個回應沒有實際修改任何檔案（git diff HEAD 為空）。\n"
    "請確認你真正執行了以下動作：\n"
    "1. 用 Edit 或 Write 工具修改對應的程式檔案\n"
    "2. 修改後的程式碼已儲存到磁碟\n"
    "現在請重新執行修正，這次必須實際修改檔案。"
)


def verify_correction_applied(
    attempt: int, *, cwd: str = ".", timeout: int = 10,
) -> Optional[str]:
    """SD_05 W2-1c：吸收 `_verify_correction_applied`（Gap-009-C）。

    attempt=0 時不檢查；其餘 attempt 後檢查 `git diff --stat HEAD`，若 stdout 為空
    表示修正沒實際變更檔案，回傳警告字串注入下一輪 prompt；否則回傳 None。
    """
    if attempt == 0:
        return None
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=timeout, cwd=cwd,
            env=_propagate_trace_env(),
        )
        if result.returncode == 0 and not result.stdout.strip():
            return _WARNING_TEMPLATE.format(attempt=attempt)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None
