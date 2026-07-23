"""可用 bash 解析器 — scripts/tests bash 類測試共用 helper（四方複審第五輪 DEF-101 P3）.

WHY：Windows＋WSL 環境直跑 pytest 時，`shutil.which("bash")` 常解析到
`C:\\Windows\\System32\\bash.exe`（WSL 佔位）——它吃不下 Windows 路徑引數、
也看不到 Windows 側工具，bash 類測試會以「檔案不存在」**紅燈**而非 skip
（第五輪 SD 發現，涵蓋 test_ntfs_length_gate / test_ci_gate_version_resolution /
test_copy_on_evolve / test_pytest_passed_count 四檔共用的 skipif 慣例）。

解析順序（沿 test_copy_on_evolve._bash_with_python 既有慣例）：git 相鄰
Git Bash（隨 git 安裝、繼承 Windows PATH）優先，非 System32 的裸 bash 次之；
每個候選以 `echo ok` 實跑驗活。皆無 → None（呼叫端 skipif）。
macOS/Linux 行為不變（裸 bash 直接驗活回傳）。

R31 Scan-B 修復：System32 排除原本用 `"system32" not in bare...lower()` 任意
子字串命中即排除，較 `tools/integration_gate_core.py::_has_system32_segment()`
（DEF-101-236 修復後的正確版本）寬鬆，會誤傷路徑含 "system32" 子字串但非該
目錄段的合法候選（如 `C:\\MySystem32Tools\\bash.exe`）。本檔與
`tools/integration_gate_core.py` 分屬不同子專案，刻意各自獨立實作（見下方
`usable_bash()` 呼叫端註解），故改用 `PureWindowsPath` 逐段精確比對對齊語意，
而非跨子專案共用 import。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PureWindowsPath


def _has_system32_segment(path_str: str) -> bool:
    """依路徑段精確比對是否含完整 "system32" 段（不分大小寫），對齊
    `tools/integration_gate_core.py::_has_system32_segment()` 的判斷語意
    （DEF-101-236）。"""
    return any(part.lower() == "system32" for part in PureWindowsPath(path_str).parts)


def usable_bash() -> str | None:
    """回傳可跑 repo bash 腳本的 bash 路徑；只有 WSL 佔位 bash 或無 bash → None。"""
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        gp = Path(git).resolve()
        for up in list(gp.parents)[:4]:
            for sub in ("usr/bin/bash.exe", "bin/bash.exe"):
                c = up / sub
                if c.exists():
                    candidates.append(str(c))
    bare = shutil.which("bash")
    if bare and not _has_system32_segment(bare):
        candidates.append(bare)
    for cand in candidates:
        try:
            r = subprocess.run(
                [cand, "-c", "echo ok"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            if r.returncode == 0 and r.stdout.strip() == "ok":
                return cand
        except Exception:
            continue
    return None
