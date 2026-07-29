#!/usr/bin/env python3
"""跨語言腳本（`.sh`／`.ps1`）掃描面 SSOT（R60 Scan-E E-A-01）。

WHY：本 repo 對「active 的 `.sh`／`.ps1`」有兩套掃描面，過去各自硬編、且**形狀不同**：

  1. **CI 語法／編碼掃描面**——`root-infra-ci.yml` 第 2 道（pwsh `Parser::ParseFile`
     ＋ UTF-8 BOM 守門）與其三份本地鏡射（`tools/tests/test_ps51_compat.scan_trees()`／
     `tools/tests/test_ps1_bom._scan_prefixes()`／`tools/windows_smoke_local.ps1` 的
     `$ps1Trees`）：**遞迴**掃三棵固定樹 `tools/`、`AutoClaude/tools/`、
     `AISDLC_SDD/scripts/`，再加 LATEST 版樹（第 4 棵，路徑動態解析）。
  2. **parity enrollment 發現面**——`tools/check_script_parity.py`：**非遞迴** glob
     一份自己的四目錄名冊 `("tools", "tools/lib", "AutoClaude/tools",
     "AISDLC_SDD/scripts")`，另加 LATEST tools（那條 leg 本來就遞迴）。

形狀不一致的實測後果（R60 量測）：**今日兩邊掃到的檔案集合完全相同（各 35 支
`.sh`／`.ps1`，diff 為空）**——因為現存腳本剛好全躺在名冊逐一列出的目錄裡。但任何人
在既有樹下**新開一層子目錄**放腳本（例：`tools/ops/deploy.sh` ＋ `deploy.ps1`），
CI 的 `-Recurse` 會掃到它（語法／BOM 有守），parity enrollment 卻**看不到**它、不會
fail-loud 要求納管，於是 `check_script_parity` 自述的「新增成對腳本必為機械攔截」
靜默失效；而那份名冊自己**沒有任何完整性鎖**（R60 實查：生產碼、測試、缺陷帳本三面
grep，唯一相關斷言是「`tools/lib` 有沒有在名冊裡」的成員存在性，不是完整性），
所以「掃描面缺一個目錄」這件事沒有人會知道。CI 側早在 R13（CI-4）就為同一風險把
`AISDLC_SDD/scripts` 補上 `-Recurse` 做預防性收斂，parity 側從未跟上。

修法（R60）：掃描根收斂成本檔這一份名冊，且**列舉實作也只留這一份**
（`iter_tree_scripts()`）——parity 因此與 CI 同為遞迴形狀，`tools/lib` 不再需要
單獨列名（遞迴自動涵蓋），名冊由「4 目錄」降為「3 棵樹」。形狀一致性
（本檔名冊 == CI 第 2 道固定樹集合）與遞迴性另由
`tools/tests/test_script_scan_surface_ssot.py` 機械斷言。

消費者（改動本檔請同步檢視）：
  - `tools/check_script_parity.py`：`_PAIR_SCAN_DIRS`／`_discover_scripts()`
  - `tools/tests/test_ps51_compat.py`：`scan_trees()`
  - `tools/tests/test_ps1_bom.py`：`_scan_prefixes()`
  - `tools/tests/test_script_scan_surface_ssot.py`：本檔的守門（形狀一致性鎖）
非 Python 的兩處（`root-infra-ci.yml` 第 2 道、`windows_smoke_local.ps1` 的
`$ps1Trees`）無法 import 本檔，仍由 `tools/tests/_ci_scan_anchors.py` 的抽取錨與
`test_smoke_ci_sync.py` 的三向鎖互鎖；本檔與 CI 那一處的一致性由上述 SSOT 鎖比對。

**不收錄什麼**（避免本檔變成雜物抽屜）：只收「掃描面的根與列舉方式」。per-tree
檔數下限（`test_ps51_compat` 的 8/7/2/4、`test_ps1_bom` 的 `_MIN_FILES`）刻意留在
各消費者——那是各鎖自己的靈敏度參數，不是共用的掃描面定義。
"""
from __future__ import annotations

from pathlib import Path

# 三棵固定掃描樹（一律**遞迴**列舉）。第 4 棵＝AISDLC_SDD LATEST 版樹，其路徑隨
# Copy-on-Evolve 升版而變，由 `AISDLC_SDD/scripts/sdd_version.py` SSOT 動態解析，
# 故刻意不列於此常數（列了就會每次升版失效）。
SCRIPT_SCAN_ROOTS: tuple[str, ...] = ("tools", "AutoClaude/tools", "AISDLC_SDD/scripts")

# LATEST 樹在各消費者裡的正規化 key（升版後登記／斷言不失效）。
LATEST_TREE_KEY = "LATEST"

# 掃描的副檔名（`.sh` POSIX 側、`.ps1` PowerShell 側）。
SCRIPT_SUFFIXES: tuple[str, ...] = (".sh", ".ps1")


def iter_tree_scripts(
    repo_root: Path, suffixes: tuple[str, ...] = SCRIPT_SUFFIXES
) -> list[str]:
    """三棵固定樹底下（**遞迴**）所有指定副檔名檔案的 repo 相對 posix 路徑（排序、去重）。

    這是掃描面的唯一列舉實作——遞迴性只寫在這裡一次，消費者不得自己 glob，
    否則「有人把某一處改回非遞迴」又會變成無訊號（本檔存在的理由）。
    不存在的樹靜默略過（`AISDLC_SDD/` 在極簡 checkout 下可能缺席），與原
    `_discover_scripts()` 的 `if not d.is_dir(): continue` 語意一致。
    """
    found: set[str] = set()
    for rel_root in SCRIPT_SCAN_ROOTS:
        root = repo_root / rel_root
        if not root.is_dir():
            continue
        for suffix in suffixes:
            for path in root.rglob(f"*{suffix}"):
                if path.is_file():
                    found.add(path.relative_to(repo_root).as_posix())
    return sorted(found)
