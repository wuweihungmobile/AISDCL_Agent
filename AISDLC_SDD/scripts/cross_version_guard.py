"""跨版 pytest 同跑 fail-loud guard 的純偵測邏輯（DEF-02-001）.

共享 CI infra：位於 ``AISDLC_SDD/scripts/``（versioned 目錄之外，非任一
``AISDLC_SDD_v0.0X`` 凍結本體，免 Copy-on-Evolve；與 DEF-03-001 修 ``ci-gate.sh`` 同精神）。

根因（AutoSDD_improving_05 §2.2 沙箱實證）：Copy-on-Evolve 下各版共用生產套件名
``tools.fsm_runtime.*``，單一 pytest process 的 ``sys.modules`` 只能裝一版 → 跨版同跑
必衝突（conftest ``ImportPathMismatchError``，或測試誤載到別版生產模組）。任何 import-mode
微調皆不可解。唯一正確隔離 = 每版獨立 process（官方 ``ci-gate.sh`` 的 ``cd vX && pytest``
已正確做到）。本模組僅負責「偵測本次 session 是否誤觸多版」，由 ``conftest.py`` 薄包裝後
raise ``pytest.UsageError`` 把 cryptic 錯誤轉為可行動訊息。
"""
from __future__ import annotations

import os
import re

# DEF-22-001：原 ``v0\.0\d+`` 僅匹配 v0.00–v0.09，對 v0.10+ 失效（DEF-19-002 同根的
# 十位數跨越 regex 失效，當時只修 ci-gate.sh/arch_fitness/test_ci_gate_version_resolution
# 三處 glob，漏此處）→ guard 對現役 v0.10~v0.13 版本偵測失能。放寬為 ``v0\.\d+`` 通則化。
VERSION_RE = re.compile(r"AISDLC_SDD_v0\.\d+")


def _versions_in_path(abspath: str) -> set[str]:
    """從單一絕對路徑抽出其所屬框架版本（取最後一個版本片段）。"""
    m = VERSION_RE.findall(abspath)
    return {m[-1]} if m else set()


def _versions_under_dir(directory: str) -> set[str]:
    """列舉某目錄下所有 ``AISDLC_SDD_v0.0X`` 子目錄（供 bare 呼叫展開）。"""
    found: set[str] = set()
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if VERSION_RE.fullmatch(name):
                found.add(name)
    return found


def _is_path_arg(token: str, cwd: str) -> bool:
    """判定 token 是否為「路徑/節點 id」而非旗標或選項值（如 -m 的 ``not chaos``）。

    含版本片段、或實際存在於檔案系統（絕對或相對 cwd）者視為路徑 arg；其餘忽略。
    """
    if VERSION_RE.search(token):
        return True
    # pytest nodeid 形如 ``path::test_x`` —— 剝除 :: 後綴再判路徑存在，否則
    # ``os.path.exists("檔案.py::test_y")``=False 致誤判「無路徑 arg」走 bare 展開全版
    # 誤報跨版（DEF-12-002）。版本片段偵測在上方 search 已涵蓋故不受影響。
    path_part = token.split("::", 1)[0]
    if os.path.exists(path_part):
        return True
    return os.path.exists(os.path.join(cwd, path_part))


def versions_touched(args: list[str], cwd: str) -> set[str]:
    """回傳本次 pytest session 將觸及的框架版本集合。

    - 每個路徑 arg：若其路徑含版本片段 → 納入該版。
    - 若完全無路徑 arg（bare 呼叫）→ 展開 ``cwd`` 下所有版本目錄。
    """
    path_args = [a for a in args if not a.startswith("-") and _is_path_arg(a, cwd)]
    roots: set[str] = set()
    for a in path_args:
        roots |= _versions_in_path(os.path.abspath(a))
    if not path_args:
        roots |= _versions_under_dir(cwd)
    return roots


def build_guard_message(versions: set[str]) -> str:
    """產出 fail-loud 訊息（含 DEF-02-001 與正確用法）。"""
    listed = ", ".join(sorted(versions))
    return (
        f"跨版 pytest 偵測：{listed} —— Copy-on-Evolve 下各版共用生產套件名 "
        "tools.fsm_runtime.*，單一 process 無法同時載入多版（sys.modules 衝突，"
        "ImportPathMismatchError 或測試誤載別版模組；DEF-02-001）。"
        "請每版獨立執行 `cd <version> && pytest`，或用 `scripts/ci-gate.sh` 雙軌閘門。"
    )
