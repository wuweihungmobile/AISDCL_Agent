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

R32 Architect 架構最佳化修復 DEF-101-275（R27 開出、連續 5 輪未收斂）：原本只用
`echo ok` 驗活，未驗 coreutils（如 `dirname`），精簡版 Git Bash（缺 coreutils）
會誤判為可用、實際跑腳本才失敗。改用 `tools/lib/bash_probe_spec.py` 提供的
`PROBE_CMD`（串接 echo + dirname 兩段探測）驗活；探測「參數」（指令與期望輸出、
System32 排除段）與 `tools/tests/test_pre_push_dispatcher.py`／
`test_git_hooks_install_common.py` 的獨立重寫版共用同一份規格資料，但驗活的
subprocess 執行邏輯本檔仍獨立寫死，不抽成跨檔共用函式。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))
import bash_probe_spec as _spec  # noqa: E402


def _has_system32_segment(path_str: str) -> bool:
    """依路徑段精確比對是否含完整 "system32" 段（不分大小寫），對齊
    `tools/integration_gate_core.py::_has_system32_segment()` 的判斷語意
    （DEF-101-236）。"""
    return any(part.lower() == _spec.SYSTEM32_SEGMENT for part in PureWindowsPath(path_str).parts)


def usable_bash() -> str | None:
    """回傳可跑 repo bash 腳本的 bash 路徑；只有 WSL 佔位 bash、缺 coreutils
    的殘缺 bash、或無 bash → None（DEF-101-275：coreutils 亦需驗活，非只驗 echo）。
    """
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
                [cand, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15,
            )
            lines = r.stdout.splitlines()
            if (
                r.returncode == 0
                and len(lines) >= 2
                and lines[0].strip() == _spec.PROBE_EXPECT_ECHO
                and lines[1].strip() == _spec.PROBE_EXPECT_DIRNAME
            ):
                return cand
        except Exception:
            continue
    return None
