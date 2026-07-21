"""ConditionalStrategy 的 shell 安全層 helpers（SD_05 W4 三方審查拆檔）。

職責：
  - ``_SAFE_COND_PATTERN``：白名單字元 regex（Gap-046）
  - ``_DENY_CHARS``：黑名單字元集合（縱深防禦，即便落入白名單也必拒）
  - ``_default_evaluator``：subprocess.run shell=False + shlex.split 預設 evaluator

行數預算：≤ 60 行。
"""
from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess

from ....utils.trace_context import propagate_to_subprocess_env

logger = logging.getLogger(__name__)

# 白名單：英數、空白、`-./=:_` 與引號（SD_05 W4 三方審查 Arch-M1/SD-M2/SA-M1 收窄）
# R16 P2：刻意不含反斜線 —— 即便將來因 Windows 路徑需求想放寬，`_default_evaluator`
# 用 POSIX 模式 shlex.split 會把反斜線當跳脫字元吃掉（`shlex.split(r"C:\Users\dev\x.py")`
# → `['C:Usersdevx.py', ...]`，路徑被靜默破壞而非清楚拒絕），故放寬前必須先把
# _default_evaluator 改用 `shlex.split(cmd, posix=False)` 或等效正規化，兩者需同動；
# 見 conditional.py 模組 docstring「跨平台注意」— 使用者應改寫正斜線路徑。
_SAFE_COND_PATTERN = re.compile(r"^[\w\s\-./=:'\"]+$")
# 黑名單：縱深防禦，即便落入白名單也必拒
_DENY_CHARS = frozenset("!`$~><|&;()*?\\\n\r\t")


def _default_evaluator(cmd: str, timeout: int) -> int:
    """以 subprocess 執行條件指令（shell=False），回傳 exit code。

    SD_05 W4 修復：
      - shell=False + shlex.split：根絕 shell injection
      - 例外收窄為 (subprocess.SubprocessError, OSError, ValueError)，
        避免吞噬 KeyboardInterrupt / SystemExit
    """
    try:
        argv = shlex.split(cmd)
    except ValueError as exc:
        logger.warning("ConditionalStrategy | shlex.split 失敗: %s cmd=%s", exc, cmd[:80])
        return 1
    if not argv:
        return 1
    try:
        proc = subprocess.run(
            argv, shell=False, capture_output=True, timeout=timeout,
            env=propagate_to_subprocess_env(dict(os.environ)),
        )
        return proc.returncode
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("ConditionalStrategy | subprocess.run 失敗: %s cmd=%s", exc, cmd[:80])
        return 1
