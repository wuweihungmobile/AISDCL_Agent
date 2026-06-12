"""tools/validate_mutmut_log.py — mutmut log 真實性驗證器。

SD_Improving_09 觀察期 #2 殘留缺陷修復：
`run_local_nightly.ps1` 的 mutation log 驗證 regex 過於寬鬆
（含 `mutmut` / `to apply a mutant` 等 help fallback 文字也會通過），
導致 mutant cache 為空時假 pass。本 helper 抽出可單元測試的真實性判定邏輯。

設計原則（graceful degradation）：
    - mutmut 全 survived 也算「真實 run」（exit=0）— 只要有 `Killed (N)` 或
      `Survived (N)` 等帶整數計數的 summary 行即視為實際執行過。
    - 只有當 log 全空、不存在、或僅含 help fallback（無數字計數）時
      才視為「未跑」（exit=2）。

退出碼：
    0  log 含真實統計（至少一條 `Killed/Survived/Timeout/Suspicious (\\d+)` 行
       或 `\\d+ out of \\d+` 形式），且至少一個非零或 denom 可計算 = 真實 run
    2  log 不含真實統計（空檔 / help fallback / 缺檔 / 僅 legend 描述）

用法：
    python tools/validate_mutmut_log.py mutation_token_guard.log

對應 ps1 stage：tools/run_local_nightly.ps1 line ~172-186。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Summary 行格式：mutmut 2.4.3 實際輸出帶 emoji（`Survived 🙁 (64)` / `Killed 🎉 (12)` /
# `Timeout ⏰ (0)` / `Suspicious 🤔 (1)` / `Skipped 🔇 (3)`），label 與 `(N)` 之間可能
# 隔著 emoji + 空白；以 `[^\n]{0,8}` 允許中介字元但限長，避免誤吃 legend 句子。
# 必須含括號內整數（排除 legend 描述如 "Killed mutants. The goal..."）。
_SUMMARY_PATTERN = re.compile(
    r"(?im)^\s*(Killed|Survived|Timeout|Suspicious|Skipped)[^\n]{0,8}\(\s*\d+\s*\)"
)

# 備援格式：`5 out of 12 mutants killed` 之類 mutmut 變體輸出。
_OUT_OF_PATTERN = re.compile(r"(?i)\b\d+\s+out\s+of\s+\d+\b")


def is_real_mutmut_run(log_path: Path) -> bool:
    """判定 log 是否為真實 mutmut run。

    真實 run 條件（任一即可）：
        1. 至少一行符合 `<Label> (\\d+)` 形式（mutmut 2.4.x 標準 summary）
        2. 或含 `\\d+ out of \\d+` 形式（其他 mutmut 版本）

    假 run / 未跑（exit=2）：
        - log 檔不存在
        - log 完全為空
        - log 僅含 help fallback（如 "To apply a mutant on disk: ..."）
        - log 僅含 legend 文字（無括號內數字）
    """
    if not log_path.exists():
        return False
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not text.strip():
        return False
    if _SUMMARY_PATTERN.search(text):
        return True
    if _OUT_OF_PATTERN.search(text):
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        sys.stderr.write(
            "usage: python tools/validate_mutmut_log.py <log_path>\n"
        )
        return 2
    log_path = Path(args[0])
    if is_real_mutmut_run(log_path):
        sys.stdout.write(
            f"[validate_mutmut_log] OK: real mutmut run detected ({log_path})\n"
        )
        return 0
    sys.stderr.write(
        f"[validate_mutmut_log] FAIL: no real mutmut summary in {log_path} "
        "(empty / help fallback / missing) — refusing to treat as pass\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
