#!/usr/bin/env python3
"""spawn 失敗判準——`stderr` 讀起來像不像行程根本沒 spawn 起來（commit fab2d0e 誤判修復抽出）。

抽出自 `tools/lib/hook_wiring.py`（fab2d0e 修復 `runtime_carrier_verdict()` 誤判：
治理檔保護的非阻斷提醒被誤判成載具沒跑）。獨立成檔純粹是 LOC 記帳——
guardrail_lib tier 400 行上限，這段判準是可獨立測試的純函式，抽出後兩邊
（本檔與 `hook_wiring.py`）都各自更省：先例＝`tools/lib/ci_liveness.py`。

只依賴 stdlib（hook／護欄層執行環境不保證有第三方套件，同 `tools/lib/platform_utils.py`
檔頭的約定）。本模組不得反向 import `hook_wiring`（單向依賴，先例同 `ci_run_status.py`
檔頭對 `ci_liveness.py` 的約定）。
"""
from __future__ import annotations

import re

# `\bspawn\b`（帶尾端字界）會漏掉 `posix_spawn`——底線兩側都是 `\w`，字界判不出來
# （實測：對兩筆真實 ENOENT／EACCES 樣本原判準零命中）。故尾端刻意不帶字界。
_SPAWN_FAILURE_RE = re.compile(
    r"\b(?:ENOENT|EACCES|EPERM|ENOEXEC|EFTYPE|ENOTDIR)\b[^\n]{0,80}spawn", re.IGNORECASE)


def is_spawn_failure(stderr: str) -> bool:
    """`stderr` 讀起來像不像行程根本沒 spawn 起來（而不是跑了但故意回非零）。"""
    return bool(_SPAWN_FAILURE_RE.search(stderr))
