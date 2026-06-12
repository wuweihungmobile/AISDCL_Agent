"""mutmut exit code bitmask helper（SD_09 W1 QA #4 — 抽出可單元測試的 SSOT）。

對應 SD_Improving_09 W0 三次 audit P0-F 紀律 #1 / #4：
  - 紀律 #1：stage rc 必須區分「真實失敗」vs「工具標準回報」（bitmask 語義）
  - 紀律 #4：驗證鏡子自身要被驗證 — 把 bitmask 判定抽出至 Python helper，
            提供 ps1 / sh / Python 三種呼叫端 SSOT，並有完整單元測試。

mutmut 2.4.x exit code 為 bitmask（位元欄位，**非固定值**）：
  - bit 0 (1)  = exception / baseline crash      → **真實失敗**（rc & 1 != 0）
  - bit 1 (2)  = surviving mutants > 0           → 觀察期預期，不算失敗
  - bit 2 (4)  = surviving mutants timeout > 0   → 容忍
  - bit 3 (8)  = suspicious mutants > 0          → 容忍

CLI 用法（給 ps1 / sh 呼叫）：
    python tools/mutmut_exit_code.py classify <mutmut_rc>

退出碼：
    0  正常結束（bit0=0，不論其他 bit 是否設定）
    1  真實失敗（bit0=1，baseline crash / exception）
    2  CLI 引數錯誤

並回傳 stdout JSON：
    {"rc": 2, "real_fail": false, "survived": true, "timeout": false, "suspicious": false}
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

# Bitmask 常量（SSOT）— 來自 mutmut 2.4.x source code (`__main__.py::print_status`)
BIT_EXCEPTION = 1   # bit 0：baseline crash / exception during run
BIT_SURVIVED = 2    # bit 1：有 mutant 存活（觀察期預期）
BIT_TIMEOUT = 4     # bit 2：有 mutant timeout
BIT_SUSPICIOUS = 8  # bit 3：有 mutant suspicious


@dataclass(frozen=True)
class MutmutExitStatus:
    """mutmut exit code 解析結果（不可變）。"""
    rc: int
    real_fail: bool
    survived: bool
    timeout: bool
    suspicious: bool

    def to_dict(self) -> dict[str, bool | int]:
        return {
            "rc": self.rc,
            "real_fail": self.real_fail,
            "survived": self.survived,
            "timeout": self.timeout,
            "suspicious": self.suspicious,
        }


def classify(rc: int) -> MutmutExitStatus:
    """解析 mutmut exit code 至各位元語義。

    Args:
        rc: mutmut process exit code（必須 >= 0；負值（如 -1）視為異常 real_fail）

    Returns:
        MutmutExitStatus dataclass

    判定規則（與 tools/run_mutmut_in_docker.sh + tools/run_local_nightly.ps1 對齊）：
      - real_fail 為 True 當且僅當 (rc & 1) != 0 或 rc < 0
      - 其他 bit 提供觀察資訊，但不影響 real_fail
    """
    if rc < 0:
        # 負值通常為 process killed by signal（如 -9 SIGKILL）→ 視為真實失敗
        return MutmutExitStatus(
            rc=rc, real_fail=True, survived=False, timeout=False, suspicious=False,
        )
    return MutmutExitStatus(
        rc=rc,
        real_fail=(rc & BIT_EXCEPTION) != 0,
        survived=(rc & BIT_SURVIVED) != 0,
        timeout=(rc & BIT_TIMEOUT) != 0,
        suspicious=(rc & BIT_SUSPICIOUS) != 0,
    )


def is_real_failure(rc: int) -> bool:
    """單一布林快捷：true = 真實失敗（應 stage fail）；false = 正常結束。"""
    return classify(rc).real_fail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="mutmut exit code bitmask classifier (SD_09 W1 QA #4)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_classify = sub.add_parser(
        "classify", help="解析 mutmut rc → JSON + 退出碼（0=正常 / 1=真實失敗）",
    )
    p_classify.add_argument("rc", type=int, help="mutmut 進程 exit code")
    args = parser.parse_args(argv)

    if args.cmd == "classify":
        status = classify(args.rc)
        sys.stdout.write(json.dumps(status.to_dict(), ensure_ascii=False) + "\n")
        return 1 if status.real_fail else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
