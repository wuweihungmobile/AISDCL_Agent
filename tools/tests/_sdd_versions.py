#!/usr/bin/env python3
"""AISDLC_SDD 版本目錄命名慣例的「測試側」單一真相源（R58 收斂，發現 #8／#20）。

## 為什麼要有這一層

`tools/tests/` 底下原本有**四份**觀測同一個對象的正則：

  * `test_windowsapps_guard_bash_parity.py`：`_FROZEN_SDD_VERSION_RE`（路徑形狀）
  * `test_windowsapps_guard_cross_consistency.py`：同名、函式體逐字相同的第二份
  * `test_component_sanitizer_shared_layer_lock.py`：`_FROZEN_VERSION_DIR_RE`（目錄名形狀）
  * `test_sanitize_component_frozen_sdd_versions_lock.py`：同名的第四份

依 `docs/06_quality/CrossPlatform_Scan_Dimensions.md` 的兩層分診問句裁定為
「應收斂」：第一層（同語言、同執行時機——四份都在 pytest／unittest 行程內求值，
沒有「Python runtime 不可用時仍須執行」這種 bootstrap 悖論）不適用 WindowsApps
guard 那節的「不可收斂」豁免；第二層（是否觀測同一對象）四份觀測的都是磁碟上
`AISDLC_SDD/AISDLC_SDD_v*` 的目錄命名慣例，「目錄名」與「repo-relative 路徑
前綴」只是同一份知識的兩個投影。

## 權威源是誰，以及為什麼不放寬成三段版號

本 repo 對「什麼字串算合法版本目錄名」已經有權威源：
`AISDLC_SDD/scripts/sdd_version.py::VERSION_DIR_RE`（LATEST 解析的 SSOT，
DEF-101-133），它是**兩段式** `vN.M`。因此本檔刻意**不**把樣式放寬成
`v\\d+(?:\\.\\d+)+`「以支援三段版號」——那會讓測試側與權威源語意分歧：
`AISDLC_SDD_v1.0.1` 在放寬後的測試側算凍結版目錄，在 `sdd_version.py` 眼中
卻連合法版本目錄都不是（已實測 `VERSION_DIR_RE.fullmatch()` 回傳 `None`），
等於把「四份一致但可能過時」換成「一份一致但與權威源矛盾」，嚴格更差。

跨子專案邊界**不 import**（本 repo 既有裁定，先例見
`tools/check_script_parity.py::_find_latest_sdd_version` 改用 subprocess 呼叫
`sdd_version.py` CLI 而非 import），故本檔自持一份字面值，並由
`tools/tests/test_sdd_versions.py` 以 `ast` 讀取權威源**檔案文字**（只讀不
import）比對字面等價 + 對抗性樣本行為等價——權威源改了而這裡沒跟，會翻紅。

## 兩個投影不可能各自漂移

`FROZEN_SDD_PATH_PATTERN` 由 `FROZEN_VERSION_DIR_PATTERN` **機械推導**（剝去
錨點後包進路徑樣式），不是第二份手寫字面值；即使有人只改其中一個常數，另一個
也會跟著變，結構上不存在「兩種形狀互相漂移」的狀態。

## 涵蓋面（三段式，誠實記載）

已實測涵蓋：`AISDLC_SDD_v0.01` ~ `AISDLC_SDD_v0.30` 這類兩段版號目錄名；
`AISDLC_SDD/AISDLC_SDD_v0.NN/<任意子路徑>` 形狀的 repo-relative 路徑前綴。
已實測不涵蓋（刻意，與權威源對齊）：三段版號 `AISDLC_SDD_v1.0.1`、`.bak`／
` - Copy` 尾綴、小寫 `aisdlc_sdd_v0.1`、缺次版號 `AISDLC_SDD_v1`。
未窮舉：本檔只管「名字長相」，不管該目錄是否 git tracked（權威源另有
`tracked_version_dirs()` 那一層，測試側呼叫端目前不需要）。
"""
from __future__ import annotations

import re

# 與權威源 `AISDLC_SDD/scripts/sdd_version.py::VERSION_DIR_RE` 語意等價的唯一字面值
# （差別僅在權威源為了取版號帶了兩個 capture group，本檔不需要取值故不帶）。
# 這是本檔**唯一**一處版本目錄正則字面值——`test_sdd_versions.py` 的前瞻掃描會
# 把 `tools/tests/` 下任何其他檔案裡的同類字面值列為違規。
FROZEN_VERSION_DIR_PATTERN = r"^AISDLC_SDD_v\d+\.\d+$"

# 版本目錄的父目錄名（monorepo 下的子專案目錄）。
SDD_ROOT_DIR_NAME = "AISDLC_SDD"

# 路徑投影＝目錄投影機械推導而來（見頂部「兩個投影不可能各自漂移」）。
_VERSION_DIR_CORE = FROZEN_VERSION_DIR_PATTERN.removeprefix("^").removesuffix("$")
FROZEN_SDD_PATH_PATTERN = "^" + SDD_ROOT_DIR_NAME + "/(" + _VERSION_DIR_CORE + ")/"

FROZEN_VERSION_DIR_RE = re.compile(FROZEN_VERSION_DIR_PATTERN)
FROZEN_SDD_PATH_RE = re.compile(FROZEN_SDD_PATH_PATTERN)


def is_frozen_version_dir_name(name: str) -> bool:
    """`name` 是否為合法的 AISDLC_SDD 版本目錄名（含 LATEST——本函式只看名字長相，
    不區分凍結／LATEST，那是呼叫端自己比對 `latest_name` 的責任）。

    刻意用 `fullmatch` 而非 `match`：權威源 `sdd_version.py::_version_key` 用的是
    `fullmatch`，而 `re.match(r"^…$", "AISDLC_SDD_v0.30\\n")` 因 `$` 允許尾隨換行
    而會誤中。收斂前的四份呼叫端全用 `.match()`，此處一併對齊權威源（目錄名實務上
    不含換行，故此差異在現行資料上不會改變任何判讀，是防守性對齊而非行為變更）。
    """
    return FROZEN_VERSION_DIR_RE.fullmatch(name) is not None


def exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """從 repo-relative 路徑清單剔除 AISDLC_SDD 凍結版本（LATEST 以外的全部版本）。

    凍結版依 CLAUDE.md「Copy-on-Evolve」鐵律是歷史快照，不應被新規則追殺：
    `run_self_evolution.sh` 這類模板檔案會被逐字複製進每一個版本目錄，若不剔除，
    任何新掃描都會把歷史快照全部誤判為新缺口（R44 實證）。
    """
    kept: list[str] = []
    for rel in paths:
        m = FROZEN_SDD_PATH_RE.match(rel)
        if m and m.group(1) != latest_name:
            continue
        kept.append(rel)
    return kept
