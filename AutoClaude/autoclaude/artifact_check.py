"""artifact-existence evaluator（AutoSDD_improving_96 W-96-1，A 軌 / DEF-95-002）。

職責：給 PRD→playbook 橋接的「doc/spec 產檔步」一個**後端無關**的把關方式——
檢查目標檔案是否真的產生（存在且非空 / 達 min-bytes），而非依賴 LLM 回顯完成
關鍵字（keyword）。後者在 pty `--output-format json` 擷取脆弱時會被吞掉，導致
檔案明明寫對卻被判失敗、整輪 escalated（DEF-95-002）。

為何裝進 `autoclaude` 套件（而非 repo-root `tools/`）：
  evaluator（execution/evaluator.py，subprocess shell=True 無指定 cwd）繼承
  AutoClaude 進程的 cwd＝真跑工作目錄（Claude 在此寫檔）。`python -m tools.X`
  在該目錄解析不到 `tools`；`python -m autoclaude.artifact_check` 因 autoclaude 為
  pip editable-install，**任何 cwd 皆可解析**，且 <path> 相對工作目錄正確（與
  `pytest test_strutils.py` 能在同目錄跑成功同理）。

Mac/Windows 相容性 R52 修復：新增 `autoclaude-artifact-check` console script
（見 pyproject.toml `[project.scripts]`），取代裸 `python -m
autoclaude.artifact_check` 形態——裸 `python` 在 macOS/多數現代 Linux 的乾淨
PATH 上不存在（僅 `python3`），經 `shell=True` 執行恆 `rc=127`；`python -m ...`
用法仍保留供除錯，新產出的 evaluator_command 一律用 console script 形態。

白名單相容（tools/three_tier_to_playbook.py sanitize_evaluator）：
  `autoclaude-artifact-check <path> --min-bytes N` 首 token=`autoclaude-artifact-check`、
  無 shell 元字元 → 通過三層消毒；舊有 `python -m autoclaude.artifact_check <path>
  --min-bytes N` 形態（首 token=python、`-m` 非 `-c`）亦仍通過消毒，向下相容既有
  playbook。

CLI：
  autoclaude-artifact-check SPEC.md --min-bytes 200
  python -m autoclaude.artifact_check SPEC.md --min-bytes 200   # 等效，開發除錯用
  exit 0＝檔案存在且 size >= min-bytes；exit 1＝不存在 / 太小（stderr 說明）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def check_artifact(path: str, min_bytes: int) -> tuple[bool, str]:
    """回傳 (ok, message)。純函式，可單測。"""
    p = Path(path)
    if not p.exists():
        return False, f"artifact 不存在: {path}"
    if not p.is_file():
        return False, f"artifact 不是檔案: {path}"
    size = p.stat().st_size
    if size < min_bytes:
        return False, f"artifact 太小: {path} ({size} bytes < min {min_bytes})"
    return True, f"artifact OK: {path} ({size} bytes >= min {min_bytes})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autoclaude-artifact-check",
        description="檢查 artifact 檔案存在且達 min-bytes（doc/spec 步 backend-robust 把關）。",
    )
    parser.add_argument("path", help="要檢查的 artifact 相對/絕對路徑")
    parser.add_argument(
        "--min-bytes", type=int, default=1,
        help="最小位元組數（預設 1＝非空即可）",
    )
    args = parser.parse_args(argv)
    ok, msg = check_artifact(args.path, args.min_bytes)
    if ok:
        print(msg)
        return 0
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
